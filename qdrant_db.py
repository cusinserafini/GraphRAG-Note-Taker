import uuid
import numpy as np
from qdrant_client import QdrantClient, models
from typing import List, Dict, Any, Union
from qdrant_client.http.models import PointStruct, VectorParams, Distance, UpdateResult, Filter, FieldCondition, MatchValue

class QdrantDBManager:
    """
    A class to manage a Qdrant database with basic CRUD operations.
    """
    def __init__(self, location: str = ":memory:", host: str = "localhost", port: int = 6333):
        """
        Initializes the Qdrant DB Manager.
        
        Args:
            location (str): The location of the Qdrant DB. Use ":memory:" for local testing.
                To use a running Qdrant instance, set location=None and provide host/port.
            host (str): Qdrant host.
            port (int): Qdrant port.
        """
        if location == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(host=host, port=port)

    def generate_unique_id(self, collection_name: str) -> str:
        """
        Generates a unique string UUID that is not already present in the collection.
        """
        while True:
            new_id = str(uuid.uuid4())
            existing = self.client.retrieve(
                collection_name=collection_name,
                ids=[new_id]
            )
            if not existing:
                return new_id

    def create_collection(self, collection_name: str, vector_size: int, distance: Distance = Distance.COSINE) -> bool:
        """
        Creates a new collection if it does not already exist.
        """
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )
            return True
        return False

    def insert_points(self, collection_name: str, points: np.ndarray, payloads:list[dict], ids:list=False) -> UpdateResult:
        """
        Create/Update (Upsert) points into a collection in Qdrant.
        """
        # TODO: ci serve mantenere gli ids se non li utilizziamo?
        return self.client.upload_collection(
            collection_name=collection_name,
            vectors=points,
            payload=payloads,
            # ids=ids
        )

    def retrieve_points(self, collection_name: str, point_ids: List[Union[int, str]]) -> List[Any]:
        """
        Read / Retrieve specific points by their IDs.
        """
        return self.client.retrieve(
            collection_name=collection_name,
            ids=point_ids
        )

    def search_points(self, collection_name: str, query_vector: np.ndarray, limit: int = 5, point_type: Union[str, None] = None) -> List[Any]:
        """
        Read / Search for nearest neighbors based on a query vector.
        """
        query_filter = None
        if point_type:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="type",
                        match=MatchValue(value=point_type)
                    )
                ]
            )

        search_queries = []
        for query in query_vector:
            search_queries.append(models.QueryRequest(query=query, filter=query_filter, limit=limit, with_payload=True)) 

        output = self.client.query_batch_points(collection_name=collection_name, requests=search_queries)

        return output

    def update_payload(self, collection_name: str, point_ids: List[Union[int, str]], payload: Dict[str, Any]) -> UpdateResult:
        """
        Update the payload (metadata) of existing points.
        """
        return self.client.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=point_ids
        )

    def delete_points(self, collection_name: str, point_ids: List[Union[int, str]]) -> UpdateResult:
        """
        Delete specific points by their IDs.
        """
        return self.client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )
