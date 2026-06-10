"""Shared in-memory cosine retrieval over corpus chunks.

Backs the mock connector directly, and backs the Vertex connector whenever a
managed Vector Search index is not configured — in that mode it still uses real
Vertex embeddings, just with local nearest-neighbour search. This keeps the full
Google Cloud path runnable before the managed index is provisioned.
"""

from __future__ import annotations

import logging

import numpy as np

from backend.corpus.loader import load_corpus_chunks, load_corpus_docs
from backend.models.corpus import CorpusChunk, CorpusDoc
from backend.models.grounding import SourcePassage
from backend.vectorstore.embeddings import Embedder, cosine_matrix

logger = logging.getLogger(__name__)


class InMemoryCorpusIndex:
    """Embed every chunk once, then answer retrieval / coverage by cosine."""

    def __init__(self, embedder: Embedder, *, org_id: str = "riverside") -> None:
        self.org_id = org_id
        self.embedder = embedder
        self.chunks: list[CorpusChunk] = load_corpus_chunks(org_id)
        self._docs: list[CorpusDoc] = load_corpus_docs(org_id)
        texts = [c.text for c in self.chunks]
        self.matrix: np.ndarray = embedder.embed(texts)
        logger.info(
            "corpus index ready: org=%s chunks=%d dim=%d embedder=%s",
            org_id,
            len(self.chunks),
            self.matrix.shape[1] if self.matrix.size else 0,
            type(embedder).__name__,
        )

    def _scores(self, query: str) -> np.ndarray:
        q = self.embedder.embed([query])[0]
        return cosine_matrix(q, self.matrix)

    def retrieve(self, query: str, *, k: int = 4, topic: str | None = None) -> list[SourcePassage]:
        if not self.chunks:
            return []
        scores = self._scores(query)
        order = np.argsort(scores)[::-1]
        passages: list[SourcePassage] = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            if topic is not None and chunk.topic != topic:
                continue
            passages.append(
                SourcePassage(
                    doc_id=chunk.doc_id,
                    doc_title=chunk.doc_title,
                    source_url=chunk.source_url,
                    page=chunk.page,
                    last_verified=chunk.last_verified,
                    text=chunk.text,
                    score=float(scores[int(idx)]),
                )
            )
            if len(passages) >= k:
                break
        return passages

    def coverage(self, query: str) -> float:
        if not self.chunks:
            return 0.0
        return float(self._scores(query).max())

    def topics(self) -> list[str]:
        return sorted({c.topic for c in self.chunks})

    def documents(self) -> list[CorpusDoc]:
        return list(self._docs)
