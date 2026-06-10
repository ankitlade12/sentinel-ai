"""Live corpus connector — Vertex AI embeddings + Vector Search.

Two modes, chosen automatically:

1. **Managed index** — when ``VERTEX_VECTOR_INDEX_ENDPOINT`` and
   ``VERTEX_VECTOR_DEPLOYED_INDEX_ID`` are configured, queries are served by a
   deployed Vertex AI Vector Search index (Matching Engine). Chunk text and
   provenance are kept in a local id→chunk map (the index stores only vectors
   and ids), so retrieved neighbours are rehydrated into cited passages.
2. **Embeddings-only fallback** — when the managed index is not yet provisioned,
   the connector still uses real Vertex embeddings but performs nearest-neighbour
   search in-memory. This keeps the full Google Cloud path runnable end-to-end
   while the managed index is being stood up (see ``scripts/index_corpus.py``).
"""

from __future__ import annotations

import logging

from backend.config import get_settings
from backend.connectors._inmemory import InMemoryCorpusIndex
from backend.corpus.loader import load_corpus_chunks
from backend.models.corpus import CorpusChunk, CorpusDoc
from backend.models.grounding import SourcePassage
from backend.vectorstore.embeddings import VertexEmbedder

logger = logging.getLogger(__name__)


class VertexCorpusConnector:
    """Trusted-corpus RAG over Vertex AI."""

    def __init__(self, *, org_id: str = "riverside") -> None:
        self.org_id = org_id
        settings = get_settings()
        self._embedder = VertexEmbedder(settings.embedding_model)
        self._index = InMemoryCorpusIndex(self._embedder, org_id=org_id)
        self._endpoint_name = settings.vertex_vector_index_endpoint
        self._deployed_index_id = settings.vertex_vector_deployed_index_id
        self._managed = bool(self._endpoint_name and self._deployed_index_id)
        self._chunk_by_id: dict[str, CorpusChunk] = {c.id: c for c in load_corpus_chunks(org_id)}
        if self._managed:
            logger.info("vertex corpus: managed Vector Search index mode")
        else:
            logger.info("vertex corpus: embeddings-only fallback (no managed index configured)")

    def _managed_retrieve(self, query: str, *, k: int, topic: str | None) -> list[SourcePassage]:
        from google.cloud import aiplatform

        endpoint = aiplatform.MatchingEngineIndexEndpoint(self._endpoint_name)
        q = self._embedder.embed([query])[0].tolist()
        response = endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[q],
            num_neighbors=max(k * 3, k),  # over-fetch so topic filtering still returns k
        )
        passages: list[SourcePassage] = []
        for neighbor in response[0] if response else []:
            chunk = self._chunk_by_id.get(neighbor.id)
            if chunk is None or (topic is not None and chunk.topic != topic):
                continue
            passages.append(
                SourcePassage(
                    doc_id=chunk.doc_id,
                    doc_title=chunk.doc_title,
                    source_url=chunk.source_url,
                    page=chunk.page,
                    last_verified=chunk.last_verified,
                    text=chunk.text,
                    score=float(1.0 - (neighbor.distance or 0.0)),  # cosine distance → similarity
                )
            )
            if len(passages) >= k:
                break
        return passages

    def retrieve(self, query: str, *, k: int = 4, topic: str | None = None) -> list[SourcePassage]:
        if self._managed:
            return self._managed_retrieve(query, k=k, topic=topic)
        return self._index.retrieve(query, k=k, topic=topic)

    def coverage(self, query: str) -> float:
        # Coverage uses the in-memory embedding scores in both modes (cheap, and
        # the managed index does not return a normalized global-max score).
        return self._index.coverage(query)

    def topics(self) -> list[str]:
        return self._index.topics()

    def documents(self) -> list[CorpusDoc]:
        return self._index.documents()
