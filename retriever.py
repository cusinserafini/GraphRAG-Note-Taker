import numpy as np

from agents import NodePayload, DataExtractor, Chat

class Retriever:
    def __init__(self, graph_db, vector_db, embedder, collection_name, agentic: bool = False):
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
        chunk_info = data_extractor(text=query, current_entities=[], current_relations=[])
        entities = list(chunk_info['nodes'].keys())
        return entities
    
    def format_subgraph(self, nodes, relationships):
        context_parts = []

        # Add node descriptions
        for node in nodes:
            props = dict(node)
            name = props.get("name", "Unknown")
            description = props.get("description", "")

            node_text = f"Entity: {name}"
            if description:
                node_text += f"\nDescription: {description}"

            # Include other properties if needed
            other_props = {
                k: v for k, v in props.items()
                if k not in ["name", "description", "uid"]
            }
            if other_props:
                node_text += f"\nAttributes: {other_props}"

            context_parts.append(node_text)

        # Add relationships
        for r in relationships:
            start = r.start_node["name"]
            end = r.end_node["name"]
            rel_type = r.type
            props = dict(r)

            context_parts.append(
                f"Relationship: {start} -[{rel_type} {props}]-> {end}"
            )

        return "\n\n".join(context_parts)
    
    def retrieve(self, query: str, depth: int = 1, chat=None):
        exact_ids = []
        # Extract entities from query
        if self.agentic and chat is not None:
            print("\t> Extracting informations from query")
            entities = self.retrieve_entities(query, chat)

            for entity_name in entities:
                matches = self.graph_db.search_nodes_by_name(entity_name)

                for match in matches:
                    exact_ids.append(match["id"])

        # Fallback to vector search
        vector_ids = self.retrieve_seeds(query)
        seed_ids = list(dict.fromkeys(exact_ids + vector_ids))

        if not seed_ids:
            return ""

        # Expand subgraph
        subgraph = self.graph_db.get_k_hop_subgraph(seed_ids, depth=depth)

        if not subgraph:
            return ""

        context = self.format_subgraph(
            subgraph["nodes"],
            subgraph["relationships"]
        )

        return context
        