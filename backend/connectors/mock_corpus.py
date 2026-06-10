"""Hermetic corpus connector — in-memory RAG with deterministic embeddings.

Requires no Google Cloud credentials. Used by the test tiers and offline
development. Behaviourally identical to the Vertex connector's fallback mode,
differing only in the embedder.
"""

from __future__ import annotations

from backend.connectors._inmemory import InMemoryCorpusIndex
from backend.models.corpus import CorpusDoc
from backend.models.grounding import SourcePassage
from backend.vectorstore.embeddings import HashingEmbedder


class MockCorpusConnector:
    """In-memory trusted-corpus RAG backed by :class:`HashingEmbedder`."""

    def __init__(self, *, org_id: str = "riverside") -> None:
        self._index = InMemoryCorpusIndex(HashingEmbedder(), org_id=org_id)

    def retrieve(self, query: str, *, k: int = 4, topic: str | None = None) -> list[SourcePassage]:
        return self._index.retrieve(query, k=k, topic=topic)

    def coverage(self, query: str) -> float:
        return self._index.coverage(query)

    def topics(self) -> list[str]:
        return self._index.topics()

    def documents(self) -> list[CorpusDoc]:
        return self._index.documents()
