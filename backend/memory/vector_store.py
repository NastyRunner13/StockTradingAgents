"""
NexusTrade — Vector Memory Store
ChromaDB-backed semantic memory for storing and retrieving past trade contexts.
"""

import chromadb
from chromadb.config import Settings
from typing import Optional
import logging
import shutil

from config import CHROMA_DIR

logger = logging.getLogger("nexustrade.vector")


class VectorMemory:
    """Semantic memory using ChromaDB for storing trade situations and outcomes.
    
    Resilient initialization: if ChromaDB fails (e.g. corrupt DB, Rust panic),
    falls back to a no-op mode so the pipeline continues without memory.
    """

    def __init__(self, collection_name: str = "trade_memory"):
        self.collection = None
        self._counter = 0
        self._healthy = False

        try:
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._counter = self.collection.count()
            self._healthy = True
            logger.info(f"✅ VectorMemory initialized ({self._counter} memories)")
        except Exception as e:
            logger.warning(f"⚠️ VectorMemory init failed: {e}")
            logger.warning("   Pipeline will continue without semantic memory.")
            # Try to recover by nuking corrupt DB
            try:
                shutil.rmtree(str(CHROMA_DIR), ignore_errors=True)
                CHROMA_DIR.mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(
                    path=str(CHROMA_DIR),
                    settings=Settings(anonymized_telemetry=False),
                )
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._counter = 0
                self._healthy = True
                logger.info("✅ VectorMemory recovered after DB reset")
            except Exception as e2:
                logger.error(f"❌ VectorMemory recovery also failed: {e2}")
                self._healthy = False

    def add_memory(self, situation: str, recommendation: str, metadata: Optional[dict] = None):
        """Store a trade situation and its outcome/recommendation."""
        if not self._healthy or not self.collection:
            return

        try:
            self._counter += 1
            doc_id = f"mem_{self._counter}"
            
            meta = metadata or {}
            meta["recommendation"] = recommendation[:500]

            self.collection.add(
                documents=[situation],
                metadatas=[meta],
                ids=[doc_id],
            )
        except Exception as e:
            logger.warning(f"VectorMemory.add_memory failed: {e}")

    def add_memories(self, situations_and_advice: list[tuple[str, str]]):
        """Batch add multiple memories."""
        for situation, advice in situations_and_advice:
            self.add_memory(situation, advice)

    def get_memories(self, query: str, n_matches: int = 3) -> list[dict]:
        """Find similar past situations using semantic search."""
        if not self._healthy or not self.collection or self.collection.count() == 0:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_matches, self.collection.count()),
            )

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    memories.append({
                        "matched_situation": doc,
                        "recommendation": meta.get("recommendation", ""),
                        "similarity_score": round(1 - distance, 3),
                        "metadata": meta,
                    })

            return memories
        except Exception as e:
            logger.warning(f"VectorMemory.get_memories failed: {e}")
            return []

    def clear(self):
        """Clear all memories."""
        if not self._healthy or not self.collection:
            return
        try:
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection.name,
                metadata={"hnsw:space": "cosine"},
            )
            self._counter = 0
        except Exception as e:
            logger.warning(f"VectorMemory.clear failed: {e}")

    def count(self) -> int:
        """Get the number of stored memories."""
        if not self._healthy or not self.collection:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0
