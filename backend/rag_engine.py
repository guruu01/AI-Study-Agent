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
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=15.0)
            self.client.get_collections()
            print(f"Connected to remote Qdrant Cloud cluster at {self.qdrant_url}")
        except Exception as e:
            local_storage = os.path.join(os.path.dirname(__file__), "..", "qdrant_data")
            os.makedirs(local_storage, exist_ok=True)
            self.client = QdrantClient(path=local_storage)
            print(f"Connected to embedded local Qdrant storage at {local_storage} (Remote notice: {e})")

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
            # Ensure keyword payload indices exist for filtering & deletions
            for field in ["filename", "user_id", "topic"]:
                try:
                    self.client.create_payload_index(
                        collection_name=COLLECTION_NAME,
                        field_name=field,
                        field_schema=models.PayloadSchemaType.KEYWORD
                    )
                except Exception:
                    pass
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

    def index_chunks(self, chunks: List[Dict[str, Any]], user_id: str = "common") -> int:
        """
        Indexes a list of chunks into Qdrant collection for the universal Shared Course Library.
        All uploaded chunks are universally accessible to all students.
        """
        points = []
        for i, chunk in enumerate(chunks):
            vector = self.get_embedding(chunk["text"])
            # Always index into universal shared library ("common")
            chunk_user = "common"
            point_id = int(hashlib.md5(f"common:{chunk['chunk_id']}".encode()).hexdigest()[:15], 16)
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "filename": chunk["filename"],
                    "topic": chunk["topic"],
                    "text": chunk["text"],
                    "user_id": "common"
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

    def search(self, query: str, user_id: Optional[str] = None, topic_filter: Optional[str] = None, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant study chunks for a query from the Shared Course Library.
        All indexed course materials are universally accessible to all students.
        """
        try:
            query_vector = self.get_embedding(query)
            
            filter_conditions = []
            if topic_filter:
                filter_conditions.append(
                    models.FieldCondition(
                        key="topic",
                        match=models.MatchValue(value=topic_filter)
                    )
                )

            query_filter = models.Filter(must=filter_conditions) if filter_conditions else None

            points = []
            try:
                query_res = self.client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit
                )
                points = getattr(query_res, "points", [])
            except Exception:
                try:
                    points = self.client.search(
                        collection_name=COLLECTION_NAME,
                        query_vector=query_vector,
                        query_filter=query_filter,
                        limit=limit
                    )
                except Exception as e:
                    print(f"RAG search execution note: {e}")
                    return []

            results = []
            for hit in points:
                payload = getattr(hit, "payload", None) or {}
                results.append({
                    "score": getattr(hit, "score", 0.0),
                    "filename": payload.get("filename", ""),
                    "topic": payload.get("topic", ""),
                    "text": payload.get("text", ""),
                    "chunk_id": payload.get("chunk_id", ""),
                    "user_id": "common",
                    "is_private": False
                })
            return results
        except Exception as e:
            print(f"RAG search error: {e}")
            return []

    def get_all_topics(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrolls collection to retrieve unique topics and filenames across the Shared Course Library.
        Universal access: all course topics are visible to every student.
        """
        try:
            scroll_result, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            topics = {}
            for point in scroll_result:
                top = point.payload.get("topic", "General")
                fn = point.payload.get("filename", "Unknown")
                if top not in topics:
                    topics[top] = {
                        "topic": top,
                        "files": set(),
                        "chunk_count": 0,
                        "is_private": False
                    }
                topics[top]["files"].add(fn)
                topics[top]["chunk_count"] += 1

            return [
                {
                    "topic": k,
                    "files": sorted(list(v["files"])),
                    "chunk_count": v["chunk_count"],
                    "count": v["chunk_count"],
                    "is_private": False
                }
                for k, v in sorted(topics.items())
            ]
        except Exception as e:
            print(f"Error fetching topics: {e}")
            return []

    def get_user_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all documents in the Shared Course Library.
        Universal access: every student can view and study all course library documents.
        """
        try:
            scroll_result, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            docs = {}
            for point in scroll_result:
                fn = point.payload.get("filename", "Unknown")
                top = point.payload.get("topic", "General")
                if fn not in docs:
                    docs[fn] = {
                        "filename": fn,
                        "topics": set(),
                        "chunk_count": 0,
                        "owner": "Shared Library",
                        "is_private": False
                    }
                docs[fn]["topics"].add(top)
                docs[fn]["chunk_count"] += 1

            return [
                {
                    "filename": k,
                    "topics": sorted(list(v["topics"])),
                    "chunk_count": v["chunk_count"],
                    "chunks": v["chunk_count"],
                    "owner": "Shared Course Library",
                    "is_private": False,
                    "can_delete": True,
                    "privacy_label": "🌐 Shared Library"
                }
                for k, v in sorted(docs.items())
            ]
        except Exception as e:
            print(f"Error fetching user documents: {e}")
            return []

    def get_document_content(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves all chunks, topics, and consolidated text of a document from the Shared Course Library.
        Universal access: any student can read any course library document.
        """
        try:
            scroll_result, _ = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=2000,
                with_payload=True,
                with_vectors=False
            )
            chunks = []
            topics = set()

            for point in scroll_result:
                payload = getattr(point, "payload", {}) or {}
                if payload.get("filename") == filename:
                    topics.add(payload.get("topic", "General"))
                    chunks.append({
                        "chunk_id": payload.get("chunk_id", str(point.id)),
                        "topic": payload.get("topic", "General"),
                        "text": payload.get("text", "")
                    })

            if not chunks:
                return None

            # Sort chunks in natural order (chunk_id e.g. filename_1, filename_2)
            def chunk_sort_key(c):
                cid = str(c.get("chunk_id", ""))
                if "_" in cid:
                    try:
                        return int(cid.rsplit("_", 1)[1])
                    except ValueError:
                        pass
                return cid

            chunks.sort(key=chunk_sort_key)
            full_text = "\n\n".join([f"### {c['topic']}\n\n{c['text']}" for c in chunks])

            return {
                "filename": filename,
                "topics": sorted(list(topics)),
                "chunk_count": len(chunks),
                "chunks": len(chunks),
                "owner": "Shared Course Library",
                "is_private": False,
                "can_delete": True,
                "full_text": full_text,
                "chunk_items": chunks
            }
        except Exception as e:
            print(f"Error fetching document content: {e}")
            return None

    def delete_document(self, filename: str, user_id: str = "default_student") -> Dict[str, Any]:
        """
        Deletes all chunks of a document from the Shared Course Library in Qdrant and removes file from disk.
        """
        try:
            point_ids = []
            try:
                # Scroll points matching filename
                scroll_res, _ = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=2000,
                    with_payload=True,
                    with_vectors=False
                )
                for pt in scroll_res:
                    p_load = pt.payload or {}
                    if p_load.get("filename") == filename:
                        point_ids.append(pt.id)
            except Exception as se:
                print(f"Scroll warning during delete document: {se}")

            # Delete matching points by ID list
            if point_ids:
                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=point_ids
                )
            else:
                # Fallback: try direct filter deletion
                try:
                    filter_conditions = [
                        models.FieldCondition(key="filename", match=models.MatchValue(value=filename))
                    ]
                    self.client.delete(
                        collection_name=COLLECTION_NAME,
                        points_selector=models.FilterSelector(filter=models.Filter(must=filter_conditions))
                    )
                except Exception as fe:
                    print(f"Filter delete warning: {fe}")

            # Clean up local raw file if exists
            safe_name = os.path.basename(filename)
            raw_path = os.path.join(os.path.dirname(__file__), "..", "uploaded_docs", safe_name)
            if os.path.exists(raw_path):
                try:
                    os.remove(raw_path)
                except Exception:
                    pass
            upload_path = os.path.join(os.path.dirname(__file__), "..", "uploads", safe_name)
            if os.path.exists(upload_path):
                try:
                    os.remove(upload_path)
                except Exception:
                    pass

            return {
                "status": "success",
                "filename": filename,
                "deleted_chunks": len(point_ids),
                "message": f"Successfully deleted {filename} and all its indexed chunks from the Shared Course Library."
            }
        except Exception as e:
            print(f"Error deleting document {filename}: {e}")
            return {"status": "error", "message": str(e)}


