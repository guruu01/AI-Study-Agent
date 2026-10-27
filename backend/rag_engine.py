import os
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models

COLLECTION_NAME = "study_materials"
VECTOR_DIM = 768

class RAGEngine:
    def __init__(self, qdrant_url: Optional[str] = None, gemini_api_key: Optional[str] = None):
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        
        # Connect to remote Qdrant or fallback to embedded local storage
        try:
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=3.0)
            self.client.get_collections()
        except Exception as e:
            local_storage = os.path.join(os.path.dirname(__file__), "..", "qdrant_data")
            os.makedirs(local_storage, exist_ok=True)
            self.client = QdrantClient(path=local_storage)
            print(f"Connected to embedded local Qdrant storage at {local_storage}")

        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(size=VECTOR_DIM, distance=models.Distance.COSINE)
                )
        except Exception as e:
            print(f"Warning ensuring collection: {e}")

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates 768-dim embedding using Google Gemini's text-embedding-004.
        If no API key is provided, returns a high-entropy hash-derived embedding for testing.
        """
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                return result['embedding']
            except Exception as e:
                print(f"Gemini embedding error: {e}. Falling back to local vectorizer.")

        # Fallback local pseudo-embedding (deterministic 768-dim normalized vector)
        words = text.lower().split()
        vec = np.zeros(VECTOR_DIM, dtype=np.float32)
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            idx = h % VECTOR_DIM
            weight = 1.0 / (1.0 + np.log(i + 1))
            vec[idx] += weight
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        else:
            vec[0] = 1.0
        return vec.tolist()

    def index_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Indexes a list of chunks into Qdrant collection.
        """
        points = []
        for i, chunk in enumerate(chunks):
            vector = self.get_embedding(chunk["text"])
            # Generate deterministic numeric id from chunk_id
            point_id = int(hashlib.md5(chunk["chunk_id"].encode()).hexdigest()[:15], 16)
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "filename": chunk["filename"],
                    "topic": chunk["topic"],
                    "text": chunk["text"]
                }
            ))

        # Batch upsert in sizes of 64
        batch_size = 64
        for idx in range(0, len(points), batch_size):
            batch = points[idx:idx + batch_size]
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
        return len(points)

    def search(self, query: str, topic_filter: Optional[str] = None, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant study chunks for a query.
        """
        query_vector = self.get_embedding(query)
        
        filter_query = None
        if topic_filter:
            filter_query = models.Filter(
                should=[
                    models.FieldCondition(
                        key="topic",
                        match=models.MatchText(text=topic_filter)
                    )
                ]
            )

        query_res = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=filter_query,
            limit=limit
        )

        results = []
        for hit in query_res.points:
            results.append({
                "score": hit.score,
                "filename": hit.payload.get("filename", ""),
                "topic": hit.payload.get("topic", ""),
                "text": hit.payload.get("text", ""),
                "chunk_id": hit.payload.get("chunk_id", "")
            })
        return results

    def get_all_topics(self) -> List[Dict[str, Any]]:
        """
        Scrolls collection to retrieve unique topics and filenames.
        """
        try:
            scroll_result, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=200,
                with_payload=True,
                with_vectors=False
            )
            topics = {}
            for point in scroll_result:
                top = point.payload.get("topic", "General")
                fn = point.payload.get("filename", "Unknown")
                if top not in topics:
                    topics[top] = {"topic": top, "files": set(), "chunk_count": 0}
                topics[top]["files"].add(fn)
                topics[top]["chunk_count"] += 1

            return [
                {
                    "topic": k,
                    "files": list(v["files"]),
                    "chunk_count": v["chunk_count"]
                }
                for k, v in topics.items()
            ]
        except Exception as e:
            print(f"Error fetching topics: {e}")
            return []
