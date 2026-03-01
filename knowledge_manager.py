import os
import numpy as np
from agents import Chat
from dotenv import load_dotenv
from neo4j_db import Neo4jDBManager
from qdrant_db import QdrantDBManager
from embedder import Embedder
from agents.properties_merger import PropertiesMerger
from agents.node_relation_merger import NodeRelationMerger
from agents import GraphInfo, DataExtractor, Descriptor, EdgePayload, NodePayload, GraphNode

load_dotenv()

class KnowledgeManager():
    """
    Used to manage all the actions that can be performed on the stored knowledge
    """
    def __init__(self, chat:Chat, embedder:Embedder, collection_name:str):
        self.chat = chat
        self.embedder = embedder
        self.collection_name = collection_name
        self.vector_db = QdrantDBManager(location=":localhost:")
        self.vector_db.create_collection('test', 768)
        self.graph_db = Neo4jDBManager()
        # self.graph_db = Neo4jDBManager(uri=os.getenv("NEO4J_URI"), user=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD"))
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
                rel_type=edge['relationship'].upper(),
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
        relations_ids = []
        for rel_name in relation_names:
            for relation in graph_info['edges']:
                if rel_name == relation['relationship']:
                    relation_id = self.vector_db.generate_unique_id(self.collection_name)
                    relations_ids.append(relation_id)
                    relations_payloads.append(
                        EdgePayload(
                            name=rel_name,
                            description=relation['description']
                        ).as_dict()
                    )

        self.vector_db.insert_points(
            collection_name=self.collection_name,
            points=np.concat([node_embeddings, relation_embeddings]),
            payloads=nodes_payloads + relations_payloads,
            ids=nodes_ids + relations_ids
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
            _nodes = [self.graph_db.get_node(_id) for _id in nodes_id]
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
                selected_node_name = similar_nodes[i][selected_node_idx]['name']
                selected_node_description = similar_nodes[i][selected_node_idx]['description']
                graph_info['nodes'][selected_node_name] = graph_info['nodes'][node_name]
                graph_info['nodes'][selected_node_name]['description'] = selected_node_description
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
                for edge in graph_info['edges']:
                    edge['relationship'] = selected_relation_name if relation_name == edge['relationship'] else edge['relationship']

        return relations_to_upload_idx, graph_info

    def upload(self, text_chunk:str):
        # TODO: remeber to remove the examples
        
        print("> Extracting informations")
        chunk_info = self.data_extractor(text=text_chunk)

        print("> Getting descriptions")
        info_example = {'nodes': {'Captain Sarah Jenkins': {'Known For': 'Boisterous laugh, love of vintage jazz', 'Birthplace': 'Nova Scotia', 'Birth Year': 'Unknown'}, 'Oceanus': {'Expedition': 'Mariana Trench Expedition'}, 'Mariana Trench Expedition': {}, 'Luxteuthis': {'Species': 'Bioluminescent squid'}, 'Global Oceanic Institute': {}, 'Dr. Hiroshi Tanaka': {'Occupation': 'Lead Marine Biologist'}}, 'edges': [{'subject': 'Captain Sarah Jenkins', 'relationship': 'Commanded', 'object': 'Oceanus', 'parameters': {'year': '2021'}}, {'subject': 'Oceanus', 'relationship': 'Embarked', 'object': 'Mariana Trench Expedition', 'parameters': {'year': '2023'}}, {'subject': 'Global Oceanic Institute', 'relationship': 'Funded', 'object': 'Mariana Trench Expedition', 'parameters': {'amount': '$1.2 million'}}, {'subject': 'Captain Sarah Jenkins', 'relationship': 'Co-authored', 'object': 'Dr. Hiroshi Tanaka', 'parameters': {'year': '2024'}}]}
        chunk_info = self.descriptor(text=text_chunk, graph_info=chunk_info)
        
        print("> Embeddings generation")
        info_example = {'nodes': {'Captain Sarah Jenkins': {'Birthplace': 'Nova Scotia', 'Birth Year': '2012', 'description': 'A captain known for her boisterous laugh and love of vintage jazz.'}, 'Oceanus': {'Expedition': 'Mariana Trench Expedition', 'description': 'A research vessel.'}, 'Mariana Trench Expedition': {'description': 'A perilous expedition.'}, 'Luxteuthis': {'Species': 'Bioluminescent Squid', 'description': 'A newly discovered species of bioluminescent squid.'}, 'Global Oceanic Institute': {'description': 'An organization that provided funding.'}, 'Research Paper': {'description': 'A publication of scientific findings.'}, 'Dr. Hiroshi Tanaka': {'description': 'A marine biologist.'}}, 'edges': [{'subject': 'Captain Sarah Jenkins', 'relationship': 'Commanded', 'object': 'Oceanus', 'parameters': {'year': '2021'}, 'description': 'Represents the act of leading or directing a group or entity.'}, {'subject': 'Oceanus', 'relationship': 'Embarked', 'object': 'Mariana Trench Expedition', 'parameters': {'year': '2023'}, 'description': 'Represents the act of beginning a journey or undertaking.'}, {'subject': 'Global Oceanic Institute', 'relationship': 'Funded', 'object': 'Mariana Trench Expedition', 'parameters': {'amount': '$1.2 million'}, 'description': 'Represents the provision of financial resources to support an activity or entity.'}, {'subject': 'Captain Sarah Jenkins', 'relationship': 'Published', 'object': 'Research Paper', 'parameters': {'year': '2024'}, 'description': 'Represents the act of making something available to the public.'}, {'subject': 'Dr. Hiroshi Tanaka', 'relationship': 'Co-authored', 'object': 'Research Paper', 'parameters': {'year': '2024'}, 'description': 'Represents the act of creating a work collaboratively with one or more other individuals.'}]}
        node_embeddings, relation_embeddings, relation_names = self._create_nodes_relations_embeddings(chunk_info)

        similar_nodes, similar_relations = self._get_similar_nodes_relations(node_embeddings, relation_embeddings)

        print("> Merging nodes name")
        nodes_to_upload_idx, chunk_info = self._merge_node_names(similar_nodes, node_embeddings, chunk_info)

        print("> Merging relations name")
        relations_to_upload_idx, chunk_info = self._merge_relation_names(similar_relations, relation_embeddings, relation_names, chunk_info)

        print("> Uploading informations in the graph")
        nodes_ids = self._load_knowledge_in_graph(graph_info=chunk_info)

        print("> Uploading embeddings into the vector DB")
        self._load_embeddings_into_vector_DB(
            graph_info=chunk_info,
            node_embeddings=node_embeddings[nodes_to_upload_idx],
            nodes_ids=list(np.array(nodes_ids)[nodes_to_upload_idx]),   # TODO: improve this part
            relation_embeddings=relation_embeddings[relations_to_upload_idx],
            relation_names=relation_names
        )

    def delete(self):
        # TODO: to implement
        raise NotImplementedError()

    def update(self):
        # TODO: to implement
        raise NotImplementedError()
