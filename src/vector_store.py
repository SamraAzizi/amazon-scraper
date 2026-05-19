from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from typing import List, Dict, Any
import os
import uuid


class QdrantStore:
    def __init__(self, url: str = None, collection: str = "amazon_products", dim: int = 1536):
        url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def _id_to_uuid(self, id_string: str) -> str:
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return str(uuid.uuid5(namespace, id_string))

    def upsert(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        points = [
            PointStruct(
                id=self._id_to_uuid(ids[i]) if isinstance(ids[i], str) else ids[i],
                vector=vectors[i],
                payload=payloads[i]
            )
            for i in range(len(ids))
        ]
        self.client.upsert(self.collection, points=points)

    def search(self, query_vector: List[float], top_k: int = 5, filter_dict: Dict[str, Any] = None):
        query_params = {
            "collection_name": self.collection,
            "query": query_vector,
            "limit": top_k,
            "with_payload": True,
        }