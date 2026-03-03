import os
from retriever import Retriever
from agents.data_types import ChunkPayload
from utils import chunk_markdown_files
import numpy as np
from agents import Chat
from neo4j_db import Neo4jDBManager
from qdrant_db import QdrantDBManager
from embedder import Embedder
from agents.properties_merger import PropertiesMerger
from agents.node_relation_merger import NodeRelationMerger
from agents import GraphInfo, DataExtractor, Descriptor, EdgePayload, NodePayload, GraphNode

class KnowledgeManager():
    """
    Used to manage all the actions that can be performed on the stored knowledge
    """
    def __init__(self, chat:Chat, embedder:Embedder, collection_name:str):
        self.chat = chat
        self.embedder = embedder
        self.collection_name = collection_name
        qdrant_url = os.environ.get("QDRANT_URL")
        if qdrant_url:
            self.vector_db = QdrantDBManager(url=qdrant_url)
        else:
            self.vector_db = QdrantDBManager(location=":localhost:")
        self.vector_db.create_collection('test', 1024)
        
        neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
        self.graph_db = Neo4jDBManager(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        self.retriever = Retriever(
            graph_db=self.graph_db,
            vector_db=self.vector_db, 
            embedder=self.embedder,
            collection_name=self.collection_name
        )
        # agents
        self.data_extractor = DataExtractor(chat=self.chat)
        self.descriptor = Descriptor(chat=self.chat)
        self.node_relation_merger = NodeRelationMerger(self.chat)
        self.properties_merger = PropertiesMerger(self.chat)


    def _create_nodes_relations_embeddings(self, graph_info:GraphInfo):
        """
        Creates the embeddings of nodes and relations given their description.
        """
        rel_names = []
        text_to_embed = []

        for node_name, node_attributes in zip(graph_info['nodes'].keys(), graph_info['nodes'].values()):
            node_description = node_attributes['description']
            text_to_embed.append(f"NAME={node_name}\nDESCRIPTION={node_description}")

        for edge in graph_info['edges']:
            rel_name = edge['relationship']
            # since its easier that the relationships have duplicates, let's filter them by name
            if rel_name not in rel_names:
                rel_description = edge['description']
                text_to_embed.append(f"NAME={rel_name}\nDESCRIPTION={rel_description}")
                rel_names.append(rel_name)

        embeddings = self.embedder.embed_text(text_to_embed)
        node_embeddings = embeddings[:-len(rel_names)]
        rel_embeddings = embeddings[-len(rel_names):]
        return node_embeddings, rel_embeddings, rel_names

    def _load_knowledge_in_graph(self, graph_info:GraphInfo):
        # loading nodes
        nodes_ids = []
        for node_name in graph_info['nodes'].keys():
            node_properties = graph_info['nodes'][node_name]
            node_properties['name'] = node_name
            node_id = self.graph_db.create_node(**GraphNode(properties=node_properties).as_dict())
            nodes_ids.append(node_id)
            graph_info['nodes'][node_name]['_id'] = node_id


        # loading relationships
        for edge in graph_info['edges']:
            start_node_name = edge['subject']
            end_node_name = edge['object']
            start_node_id = graph_info['nodes'][start_node_name]['_id']
            end_node_id = graph_info['nodes'][end_node_name]['_id']
            self.graph_db.create_relationship(
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                rel_type=edge['relationship'],
                properties=edge['parameters']
            )

        return nodes_ids

    def _load_embeddings_into_vector_DB(
        self, 
        graph_info:GraphInfo, 
        node_embeddings:np.ndarray,
        nodes_ids:list,
        relation_embeddings:np.array,
        relation_names:list[str]
    ):
        # creating nodes payloads
        nodes_payloads = []
        for node_id, node_name in zip(nodes_ids, graph_info['nodes'].keys()):
            nodes_payloads.append(NodePayload(_id=node_id).as_dict())

        # creating relations payloads
        relations_payloads = []
        for rel_name in relation_names:
            for relation in graph_info['edges']:
                if rel_name == relation['relationship']:
                    relations_payloads.append(
                        EdgePayload(
                            name=rel_name,
                            description=relation['description']
                        ).as_dict()
                    )

        self.vector_db.insert_points(
            collection_name=self.collection_name,
            points=np.concat([node_embeddings, relation_embeddings]),
            payloads=nodes_payloads + relations_payloads
        )
    
    def _get_similar_nodes_relations(self, node_embeddings:np.ndarray, relation_embeddings:np.ndarray):
        nodes_query = self.vector_db.search_points(
            collection_name=self.collection_name,
            query_vector=node_embeddings,
            point_type=NodePayload.type
        )

        relations_query = self.vector_db.search_points(
            collection_name=self.collection_name,
            query_vector=relation_embeddings,
            point_type=EdgePayload.type
        )
        
        similar_nodes = []
        for nodes_list in nodes_query:
            nodes_id = [node.payload['_id'] for node in nodes_list.points]
            _nodes = [{"_id": _id, **self.graph_db.get_node(_id)} for _id in nodes_id]
            similar_nodes.append(_nodes)
                
        similar_relations:list[list[EdgePayload]] = []
        for relations_list in relations_query:
            _relations = [EdgePayload(**relation.payload).as_dict() for relation in relations_list.points]
            similar_relations.append(_relations)

        return similar_nodes, similar_relations

    def _merge_node_names(self, similar_nodes:list, node_embeddings:np.array, graph_info:GraphInfo):
        nodes_to_upload_idx = list(range(node_embeddings.shape[0])) # used to understand which nodes are new and so which ones need to be updated in the vectorDB
        node_names = list(graph_info['nodes'].keys())
        
        for i, node_name in enumerate(node_names):
            proposal = {"name": node_name, "description": graph_info['nodes'][node_name]['description']}
            selected_node_idx = self.node_relation_merger(proposal=proposal, data_list=similar_nodes[i])
            if selected_node_idx is not None:
                # updating the node's name and description
                nodes_to_upload_idx.remove(i)   # removing the node from the updating list of the vector DB
                selected_node_idx -= 1  # the LLM returns indexes that starts from 1
                selected_node_id = similar_nodes[i][selected_node_idx]['_id']
                selected_node_name = similar_nodes[i][selected_node_idx]['name']
                selected_node_description = similar_nodes[i][selected_node_idx]['description']
                graph_info['nodes'][selected_node_name] = graph_info['nodes'][node_name]
                graph_info['nodes'][selected_node_name]['_id'] = selected_node_id
                graph_info['nodes'][selected_node_name]['description'] = selected_node_description
                print(f"\tSubstituting {node_name} -> {selected_node_name}")
                if selected_node_name != node_name:
                    # if the proposed name is different from the one in the graph, let's remove the old one
                    del graph_info['nodes'][node_name]
                    # let's update the node names in the edges
                    for edge in graph_info['edges']:
                        edge['subject'] = selected_node_name if node_name == edge['subject'] else edge['subject']
                        edge['object'] = selected_node_name if node_name == edge['object'] else edge['object']

                # merging the new properties name with the old ones
                proposal_properties = list(graph_info['nodes'][selected_node_name].keys())
                proposal_properties.remove('description')
                existing_properties = list(similar_nodes[i][selected_node_idx].keys())
                existing_properties.remove('name')
                existing_properties.remove('description')
                if len(existing_properties) != 0 and len(proposal_properties) != 0:
                    equal_properties = self.properties_merger(proposals=proposal_properties, existing=existing_properties)
                    for proposed, existing in zip(equal_properties.keys(), equal_properties.values()):
                        graph_info['nodes'][selected_node_name][existing] = graph_info['nodes'][selected_node_name][proposed]
                        if proposed != existing:
                            del graph_info['nodes'][selected_node_name][proposed]
        
        return nodes_to_upload_idx, graph_info

    def _merge_relation_names(self, similar_relations:list, relation_embeddings:np.ndarray, relation_names:list, graph_info:GraphInfo):
        relations_to_upload_idx = list(range(relation_embeddings.shape[0])) # used to understand which relations are new and so need to be updated in the vectorDB
        for i, relation_name in enumerate(relation_names):
            proposal = {"name": relation_name}
            for edge in graph_info['edges']:
                if edge['relationship'] == relation_name:
                    proposal['description'] = edge['description']
                    break

            selected_relation_idx = self.node_relation_merger(proposal=proposal, data_list=similar_relations[i])
            if selected_relation_idx is not None:
                relations_to_upload_idx.remove(i)   # removing the relation from the updating list of the vector DB
                selected_relation_idx -= 1  # the LLM returns indexes that starts from 1
                selected_relation_name = similar_relations[i][selected_relation_idx]['name']
                print(f"\tSubstituting {relation_name} -> {selected_relation_name}")
                
                # let's update the edges having relation_name
                for edge in graph_info['edges']:
                    if relation_name == edge['relationship']:
                        edge['relationship'] = selected_relation_name  

                        # merging proposed properties with the existing ones (if they exist)
                        subject_name = edge['subject']
                        object_name = edge['object']

                        subject_id = None
                        if '_id' in graph_info['nodes'][subject_name].keys():
                            subject_id = graph_info['nodes'][subject_name]['_id']
                            
                        object_id = None
                        if '_id' in graph_info['nodes'][object_name].keys():
                            object_id = graph_info['nodes'][object_name]['_id']

                        # if both the nodes are present in the graph merge  the properties    
                        if subject_id is not None and object_id is not None:
                            existing_properties = self.graph_db.get_relationship_properties(subject_id, object_id, edge['relationship'])
                            
                            # if there are parameters loaded in the graph and new proposals parameters, let's merge them if needed
                            if existing_properties is not None and len(list(edge['parameters'].keys())) != 0:
                                equal_properties = self.properties_merger(proposals=list(edge['parameters'].keys()), existing=list(existing_properties.keys()))
                                for proposed, existing in zip(equal_properties.keys(), equal_properties.values()):
                                    edge['parameters'][existing] = edge['parameters'][proposed]
                                    if proposed != existing:
                                        # deleting the old property
                                        del edge['parameters'][proposed]
                                edge['parameters'] = {**existing_properties, **edge['parameters']}  # the order is important, in this way we override the existing values with the new ones
                
        return relations_to_upload_idx, graph_info

    def _extract_info_from_document(self, chunks_list:list):
        currently_used_entities = []
        currently_used_relations = []
        graph_info = GraphInfo(nodes={}, edges=[])
        for i, chunk in enumerate(chunks_list):
            print(f"> Chunk {i+1}/{len(chunks_list)}")
            text_chunk = chunk.text
            print("\t> Extracting informations")
            chunk_info = self.data_extractor(text=text_chunk, current_entities=currently_used_entities, current_relations=currently_used_relations)

            # merging current entities with new entities
            # TODO: can be improved
            entities = list(chunk_info['nodes'].keys())
            for entity_name in entities:
                if entity_name in graph_info['nodes'].keys():
                    graph_info['nodes'][entity_name] = {**graph_info['nodes'][entity_name], **chunk_info['nodes'][entity_name]}
                    del chunk_info['nodes'][entity_name]
                else:
                    graph_info['nodes'][entity_name] = chunk_info['nodes'][entity_name]
            
            # merging current edges with new edges
            _chunk_info_edges = [] + chunk_info['edges']
            _graph_info_edges = [] + graph_info['edges']
            for edge in _chunk_info_edges:
                for current_edge in _graph_info_edges:
                    
                    if edge['subject'] == current_edge['subject'] and edge['relationship'] == current_edge['relationship'] and edge['object'] == current_edge['object']:
                        current_edge['parameters'] = {**current_edge['parameters'], **edge['parameters']}
                        chunk_info['edges'].remove(edge)
                    else:
                        graph_info['edges'].append(edge)

                    if edge['relationship'] == current_edge['relationship']:
                        chunk_info['edges'].remove(edge)

            if len(graph_info['edges']) == 0:
                graph_info['edges'] = chunk_info['edges']

            print("\t> Getting descriptions")
            chunk_info = self.descriptor(text=text_chunk, graph_info=chunk_info)

            # TODO: can be improved
            # merging current entities with new entities
            for entity_name in chunk_info['nodes'].keys():
                if entity_name in graph_info['nodes'].keys():
                    graph_info['nodes'][entity_name] = {**graph_info['nodes'][entity_name], **chunk_info['nodes'][entity_name]}
                else:
                    graph_info['nodes'][entity_name] = chunk_info['nodes'][entity_name]
                    currently_used_entities.append({'name': entity_name, 'description': chunk_info['nodes'][entity_name]['description']})

            # updating currently found entities and relations
            for entity_name in chunk_info['nodes'].keys():
                currently_used_entities.append({'name': entity_name, 'description': chunk_info['nodes'][entity_name]['description']})
            for edge in chunk_info['edges']:   
                currently_used_relations.append({'name': edge['relationship'], 'description': edge['description']})
        
        return graph_info

    def _load_chunk_embeddings(self, chunks_list:list):
        chunk_texts = [chunk.text for chunk in chunks_list]
        embeddings = self.embedder.embed_text(chunk_texts)
            
        self.vector_db.insert_points(
            collection_name=self.collection_name,
            points=embeddings,
            payloads=[ChunkPayload(text=text).as_dict() for text in chunk_texts]
        )
        

    def upload(self, file_name:str):
        chunks_list = chunk_markdown_files([file_name])
        print("> Loading chunk embeddings")
        self._load_chunk_embeddings(chunks_list)
        print("> Extracting graph info")
        graph_info = self._extract_info_from_document(chunks_list)
            
        print("> Embeddings generation")
        node_embeddings, relation_embeddings, relation_names = self._create_nodes_relations_embeddings(graph_info)

        similar_nodes, similar_relations = self._get_similar_nodes_relations(node_embeddings, relation_embeddings)

        print("> Merging nodes name")
        nodes_to_upload_idx, graph_info = self._merge_node_names(similar_nodes, node_embeddings, graph_info)

        print("> Merging relations name")
        relations_to_upload_idx, graph_info = self._merge_relation_names(similar_relations, relation_embeddings, relation_names, graph_info)

        print("> Uploading informations in the graph")
        nodes_ids = self._load_knowledge_in_graph(graph_info=graph_info)

        print("> Uploading embeddings into the vector DB")
        self._load_embeddings_into_vector_DB(
            graph_info=graph_info,
            node_embeddings=node_embeddings[nodes_to_upload_idx],
            nodes_ids=list(np.array(nodes_ids)[nodes_to_upload_idx]),   # TODO: improve this part
            relation_embeddings=relation_embeddings[relations_to_upload_idx],
            relation_names=relation_names
        )

    def ask_question(self, query:str):
        text_chunks = self.retriever.rag(query=query)
        context = "CONTEXT:\n"
        for text in text_chunks:
            context += f"{text}\n\n"
        
        messages = [
            {"role": "system", "content": "Answer using ONLY the provided context. If not present, say 'Not found in context.'"},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]

        for token in self.chat.ask(messages, streaming=True):
            yield token

    def delete(self):
        # TODO: to implement
        raise NotImplementedError()

    def update(self):
        # TODO: to implement
        raise NotImplementedError()
