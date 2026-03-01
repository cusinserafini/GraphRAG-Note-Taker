import os
from dotenv import load_dotenv
from neo4j_db import Neo4jDBManager
from dataclasses import dataclass, asdict
from qdrant_db import QdrantDBManager
from agents import Chat
from embedder import Embedder
from agents import GraphInfo, DataExtractor, Descriptor, EdgePayload, NodePayload, GraphNode
import numpy as np

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
        self.graph_db = Neo4jDBManager()
        # self.graph_db = Neo4jDBManager(uri=os.getenv("NEO4J_URI"), user=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD"))
        self.vector_db.create_collection('test', 768)

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
        for node_name in graph_info['nodes'].keys():
            nodes_payloads.append(NodePayload().as_dict())

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


    def upload(self, text_chunk:str):
        # TODO: remeber to remove the examples
        
        # extracting informations from the chunk
        print("> Extracting informations")
        data_extractor = DataExtractor(chat=self.chat)
        chunk_info = data_extractor(text=text_chunk)

        print("> Getting descriptions")
        info_example = {'nodes': {'Captain Sarah Jenkins': {'Known For': 'Boisterous laugh, love of vintage jazz', 'Birthplace': 'Nova Scotia', 'Birth Year': 'Unknown'}, 'Oceanus': {'Expedition': 'Mariana Trench Expedition'}, 'Mariana Trench Expedition': {}, 'Luxteuthis': {'Species': 'Bioluminescent squid'}, 'Global Oceanic Institute': {}, 'Dr. Hiroshi Tanaka': {'Occupation': 'Lead Marine Biologist'}}, 'edges': [{'subject': 'Captain Sarah Jenkins', 'relationship': 'Commanded', 'object': 'Oceanus', 'parameters': {'year': '2021'}}, {'subject': 'Oceanus', 'relationship': 'Embarked', 'object': 'Mariana Trench Expedition', 'parameters': {'year': '2023'}}, {'subject': 'Global Oceanic Institute', 'relationship': 'Funded', 'object': 'Mariana Trench Expedition', 'parameters': {'amount': '$1.2 million'}}, {'subject': 'Captain Sarah Jenkins', 'relationship': 'Co-authored', 'object': 'Dr. Hiroshi Tanaka', 'parameters': {'year': '2024'}}]}
        descriptor = Descriptor(chat=self.chat)
        chunk_info = descriptor(text=text_chunk, graph_info=chunk_info)
        
        # embeddings creation
        print("> Embeddings generation")
        info_example = {'nodes': {'Captain Sarah Jenkins': {'Birthplace': 'Nova Scotia', 'Birth Year': 'Unknown', 'description': 'A captain known for her boisterous laugh and love of vintage jazz.'}, 'Oceanus': {'Expedition': 'Mariana Trench Expedition', 'description': 'A research vessel.'}, 'Mariana Trench Expedition': {'description': 'A perilous expedition.'}, 'Luxteuthis': {'Species': 'Bioluminescent Squid', 'description': 'A newly discovered species of bioluminescent squid.'}, 'Global Oceanic Institute': {'description': 'An organization that provided funding.'}, 'Research Paper': {'description': 'A publication of scientific findings.'}, 'Dr. Hiroshi Tanaka': {'description': 'A marine biologist.'}}, 'edges': [{'subject': 'Captain Sarah Jenkins', 'relationship': 'Commanded', 'object': 'Oceanus', 'parameters': {'year': '2021'}, 'description': 'Represents the act of leading or directing a group or entity.'}, {'subject': 'Oceanus', 'relationship': 'Embarked', 'object': 'Mariana Trench Expedition', 'parameters': {'year': '2023'}, 'description': 'Represents the act of beginning a journey or undertaking.'}, {'subject': 'Global Oceanic Institute', 'relationship': 'Funded', 'object': 'Mariana Trench Expedition', 'parameters': {'amount': '$1.2 million'}, 'description': 'Represents the provision of financial resources to support an activity or entity.'}, {'subject': 'Captain Sarah Jenkins', 'relationship': 'Published', 'object': 'Research Paper', 'parameters': {'year': '2024'}, 'description': 'Represents the act of making something available to the public.'}, {'subject': 'Dr. Hiroshi Tanaka', 'relationship': 'Co-authored', 'object': 'Research Paper', 'parameters': {'year': '2024'}, 'description': 'Represents the act of creating a work collaboratively with one or more other individuals.'}]}
        node_embeddings, relation_embeddings, relation_names = self._create_nodes_relations_embeddings(chunk_info)

        # # searching if the same nodes/relations are just present in the DB
        # similar_nodes = self.vector_db.search_points(
        #     collection_name=self.collection_name,
        #     query_vector=node_embeddings,
        #     point_type=NodePayload.type
        # )

        # similar_relations = self.vector_db.search_points(
        #     collection_name=self.collection_name,
        #     query_vector=relation_embeddings,
        #     point_type=EdgePayload.type
        # )

        print("> Uploading informations in the graph")
        nodes_ids = self._load_knowledge_in_graph(graph_info=chunk_info)

        print("> Uploading embeddings into the vector DB")
        self._load_embeddings_into_vector_DB(
            graph_info=chunk_info,
            node_embeddings=node_embeddings,
            nodes_ids=nodes_ids,
            relation_embeddings=relation_embeddings,
            relation_names=relation_names
        )
        

    def delete(self):
        # TODO: to implement
        raise NotImplementedError()

    def update(self):
        # TODO: to implement
        raise NotImplementedError()
