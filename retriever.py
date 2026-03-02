import numpy as np

from agents import NodePayload

class Retriever:
    def __init__(self, graph_db, vector_db, embedder, collection_name):
        self.graph_db = graph_db
        self.vector_db = vector_db
        self.embedder = embedder
        self.collection_name = collection_name

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

        # Extract matched node IDs
        for response in results:
            seed_list = response.points
            seeds_id = [seed.id for seed in seed_list]
        return seeds_id
    
    # def format_subgraph(self, nodes, relationships):
    #     triples = []

    #     for r in relationships:
    #         start = r.start_node["name"]
    #         end = r.end_node["name"]
    #         rel_type = r.type
    #         props = dict(r)

    #         triples.append(
    #             f"{start} -[{rel_type} {props}]-> {end}"
    #         )

    #     return "\n".join(triples)
    
    def format_subgraph(self, nodes, relationships):
        context_parts = []

        # ---- Add node descriptions ----
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

        # ---- Add relationships ----
        for r in relationships:
            start = r.start_node["name"]
            end = r.end_node["name"]
            rel_type = r.type
            props = dict(r)

            context_parts.append(
                f"Relationship: {start} -[{rel_type} {props}]-> {end}"
            )

        return "\n\n".join(context_parts)
    
    def retrieve(self, query: str, depth: int = 1):
        seed_ids = self.retrieve_seeds(query)

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