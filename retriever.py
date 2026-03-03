import numpy as np
from agents.data_types import ChunkPayload
from embedder import Embedder
from qdrant_db import QdrantDBManager
from neo4j_db import Neo4jDBManager
from agents import NodePayload, DataExtractor, Chat, Descriptor, EdgePayload

class Retriever:
    def __init__(self, graph_db:Neo4jDBManager, vector_db:QdrantDBManager, embedder:Embedder, collection_name:str, agentic: bool = False):
        self.graph_db = graph_db
        self.vector_db = vector_db
        self.embedder = embedder
        self.collection_name = collection_name
        self.agentic = agentic
    
    def retrieve_seeds(self, query: str, top_k: int = 5):
        query_embedding = self.embedder.embed_text([query])[0]

        results = self.vector_db.search_points(
            collection_name=self.collection_name,
            query_vector=np.array([query_embedding]),
            limit=top_k,
            point_type=NodePayload.type
        )

        if not results or not results[0]:
            return []

        seeds_id = []
        for response in results:
            for point in response.points:
                if point.payload and "_id" in point.payload:
                    seeds_id.append(point.payload["_id"])

        return seeds_id
    
    def retrieve_entities(self, query: str, chat: Chat):
        data_extractor = DataExtractor(chat=chat)
        descriptor = Descriptor(chat=chat)

        chunk_info = data_extractor(text=query, current_entities=[], current_relations=[])
        chunk_info = descriptor(text=query, graph_info=chunk_info)

        # ---- Extract entities ----
        entities = []
        for name, node_data in chunk_info.get("nodes", {}).items():
            entities.append({
                "name": name,
                "description": node_data.get("description", "")
            })

        # ---- Extract relationships ----
        edges = []
        for edge in chunk_info.get("edges", []):
            edges.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "type": edge.get("type"),
                "description": edge.get("description", "")
            })

        print(entities, edges)
        return entities, edges
    
    def match_entities_vector(self, entities, top_k=3):
        matched_ids = []

        for entity in entities:
            text = f"{entity['name']}. {entity['description']}"
            embedding = self.embedder.embed_text([text])[0]

            results = self.vector_db.search_points(
                collection_name=self.collection_name,
                query_vector=np.array([embedding]),
                limit=top_k,
                point_type=NodePayload.type
            )

            for response in results:
                for point in response.points:
                    if point.payload and "_id" in point.payload:
                        matched_ids.append(point.payload["_id"])

        return matched_ids
    
    def match_relations_vector(self, edges, top_k=3):
        matched_rel_types = set()

        for edge in edges:
            text = f"{edge['type']}. {edge['description']}"
            embedding = self.embedder.embed_text([text])[0]

            results = self.vector_db.search_points(
                collection_name=self.collection_name,
                query_vector=np.array([embedding]),
                limit=top_k,
                point_type=EdgePayload.type
            )

            for response in results:
                for point in response.points:
                    if point.payload and "rel_type" in point.payload:
                        matched_rel_types.add(point.payload["rel_type"])

        return list(matched_rel_types)
    
    def format_subgraph(self, nodes, relationships):
        context_parts = []

        # Deduplicate nodes by elementId
        unique_nodes = {}
        for node in nodes:
            node_id = node.element_id  # IMPORTANT
            if node_id not in unique_nodes:
                unique_nodes[node_id] = node
        # Add node descriptions
        for node in unique_nodes.values():
            props = dict(node)
            name = props.get("name", "Unknown")
            description = props.get("description", "")

            node_text = f"Entity: {name}"
            if description:
                node_text += f"\nDescription: {description}"

            # Include other properties if needed
            other_props = {
                k: v for k, v in props.items()
                if k not in ["name", "description"]
                # if k not in ["name", "description", "uid"]
            }
            if other_props:
                node_text += f"\nAttributes: {other_props}"

            context_parts.append(node_text)

        # Deduplicate relationships
        unique_rels = {}
        for r in relationships:
            rel_id = r.element_id
            if rel_id not in unique_rels:
                unique_rels[rel_id] = r
        # Add relationships
        for r in unique_rels.values():
            start = r.start_node["name"]
            end = r.end_node["name"]
            rel_type = r.type
            props = dict(r)

            context_parts.append(
                f"Relationship: {start} -[{rel_type} {props}]-> {end}"
            )

        return "\n\n".join(context_parts)
    
    def retrieve(self, query: str, top_k: int = 5, depth: int = 1, chat=None):
        # exact_ids = []
        vector_ids = self.retrieve_seeds(query, top_k)
        # Extract entities from query
        if self.agentic and chat is not None:
            print("\t> Extracting informations from query")
            entities, edges = self.retrieve_entities(query, chat)

            exact_ids = self.match_entities_vector(entities)
            matched_rel_types = self.match_relations_vector(edges)

            # exact_ids = list(dict.fromkeys(exact_ids))

            # for entity_name in entities:
            #     matches = self.graph_db.search_nodes_by_name(entity_name)

            #     for match in matches:
            #         exact_ids.append(match["id"])

            seed_ids = list(dict.fromkeys(exact_ids + vector_ids))
            if not seed_ids:
                return ""
            
            subgraph = self.graph_db.get_k_hop_filtered_subgraph(
                seed_ids,
                matched_rel_types,
                depth=depth
            )
            print(subgraph)

        else:
            seed_ids = list(dict.fromkeys(vector_ids))
            if not seed_ids:
                return ""

            subgraph = self.graph_db.get_k_hop_subgraph(seed_ids, depth=depth)

        if not subgraph:
            return ""

        context = self.format_subgraph(
            subgraph["nodes"],
            subgraph["relationships"]
        )

        return context

    def rag(self, query:str, n_chunks_limit:int = 5) -> str:
        """
        Used to retrieve the chunks of text similar to a query
        """
        query_embedding = self.embedder.embed_text(query)
        query_embedding = np.expand_dims(query_embedding, 0)
        similar_points = self.vector_db.search_points(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=n_chunks_limit,
            point_type=ChunkPayload.type
        )

        return [point.payload['text'] for point in similar_points[0].points]
