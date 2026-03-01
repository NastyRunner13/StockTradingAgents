"""
NexusTrade — Vector Memory Store
ChromaDB-backed semantic memory for storing and retrieving past trade contexts.
"""

import chromadb
from chromadb.config import Settings
from typing import Optional
from config import CHROMA_DIR


class VectorMemory:
    """Semantic memory using ChromaDB for storing trade situations and outcomes."""

    def __init__(self, collection_name: str = "trade_memory"):
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._counter = self.collection.count()

    def add_memory(self, situation: str, recommendation: str, metadata: Optional[dict] = None):
        """Store a trade situation and its outcome/recommendation."""
        self._counter += 1
        doc_id = f"mem_{self._counter}"
        
        meta = metadata or {}
        meta["recommendation"] = recommendation[:500]

        self.collection.add(
            documents=[situation],
            metadatas=[meta],
            ids=[doc_id],
        )

    def add_memories(self, situations_and_advice: list[tuple[str, str]]):
        """Batch add multiple memories."""
        for situation, advice in situations_and_advice:
            self.add_memory(situation, advice)

    def get_memories(self, query: str, n_matches: int = 3) -> list[dict]:
        """Find similar past situations using semantic search."""
        if self.collection.count() == 0:
            return []

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
                    "similarity_score": round(1 - distance, 3),  # Convert distance to similarity
                    "metadata": meta,
                })

        return memories

    def clear(self):
        """Clear all memories."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )
        self._counter = 0

    def count(self) -> int:
        """Get the number of stored memories."""
        return self.collection.count()
