import os
import json
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class VectorMemory:
    """
    Wrapper for Qdrant vector database memory.
    This stores procedural memory evaluation loop results (the delta
    between agent suggestion and human approved action) using the 
    6 acoustic features as the vector space.
    """
    def __init__(self):
        self.persist_dir = os.path.join(os.path.dirname(__file__), "qdrant_db")
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = QdrantClient(path=self.persist_dir)
        
        self.collection_name = "procedural_memory"
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=6, distance=Distance.COSINE),
            )
        print(f"VectorMemory initialized at {self.persist_dir} with Qdrant.")

    def _extract_vector(self, features_json: str) -> list[float]:
        try:
            data = json.loads(features_json)
            f = data.get("features", {})
            return [
                float(f.get("lufs_integrated", 0.0) or 0.0),
                float(f.get("rms_mean", 0.0) or 0.0),
                float(f.get("spectral_centroid_mean_hz", 0.0) or 0.0),
                float(f.get("peak_amplitude_dbfs", 0.0) or 0.0),
                float(f.get("crest_factor", 0.0) or 0.0),
                float(f.get("stereo_correlation_mean", 0.0) or 0.0)
            ]
        except Exception as e:
            print(f"VectorMemory Extract Error: {e}")
            return [0.0] * 6

    def store_delta(self, features_json: str, suggestion: dict, approved_action: dict):
        """
        Embeds the acoustic context and stores it alongside the delta payload.
        """
        vector = self._extract_vector(features_json)
        point_id = int(hashlib.md5(features_json.encode('utf-8')).hexdigest()[:15], 16)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "features": features_json,
                        "suggestion": suggestion,
                        "approved_action": approved_action
                    }
                )
            ]
        )
        print(f"VectorMemory: Stored delta for acoustic context via Qdrant")

    def retrieve_similar_contexts(self, features_json: str, n_results: int = 3):
        """
        Queries the DB for past similar acoustic states and decisions.
        """
        vector = self._extract_vector(features_json)
        
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=n_results
            )
            results = []
            for hit in hits:
                # Require at least some similarity, cosine distance > 0.8 is a decent heuristic for vectors this small
                if hit.score > 0.8:
                    results.append(hit.payload)
            return results
        except Exception as e:
            print(f"VectorMemory Retrieve Error: {e}")
            return []
