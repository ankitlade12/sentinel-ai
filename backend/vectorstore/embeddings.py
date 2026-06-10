"""Embedders + cosine similarity.

Two implementations behind one Protocol:

- :class:`HashingEmbedder` — deterministic, dependency-free, offline. Used by
  the mock corpus connector so the hermetic test tier and offline development
  need no Google Cloud credentials. It captures lexical overlap, which is
  sufficient to retrieve the right passage for grounding in tests.
- :class:`VertexEmbedder` — Vertex AI text embeddings (the live path), reusing
  the shared GenAI client so calls are auto-traced by OpenInference.
"""

from __future__ import annotations

import hashlib
import itertools
import logging
import re
from typing import Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+")


def cosine_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of one query vector against a (n, dim) matrix.

    Inputs are assumed L2-normalized, so this is a dot product clamped to
    [0, 1] for stability when vectors are near-orthogonal.
    """
    if matrix.size == 0:
        return np.zeros((0,), dtype=np.float32)
    sims = matrix @ query
    clipped: np.ndarray = np.clip(sims, 0.0, 1.0)
    return clipped


@runtime_checkable
class Embedder(Protocol):
    """Maps text to dense, L2-normalized vectors."""

    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:  # (len(texts), dim)
        ...


class HashingEmbedder:
    """Deterministic hashing embedder over unigrams + bigrams.

    Stable across processes (uses md5, not Python's salted ``hash()``), so the
    same corpus always indexes identically — important for reproducible tests.
    """

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _index(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dim

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _TOKEN.findall(text.lower())
        for tok in tokens:
            vec[self._index(tok)] += 1.0
        for a, b in itertools.pairwise(tokens):
            vec[self._index(f"{a}_{b}")] += 1.0
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self._embed_one(t) for t in texts])


class VertexEmbedder:
    """Vertex AI text embeddings via the shared GenAI client (live path)."""

    def __init__(self, model: str | None = None) -> None:
        from backend.config import get_settings

        settings = get_settings()
        self.model = model or settings.embedding_model
        self.dim = 768  # text-embedding-005 default output dimensionality

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        from backend.llm import get_genai_client

        client = get_genai_client()
        result = client.models.embed_content(model=self.model, contents=texts)
        vectors = [np.asarray(e.values, dtype=np.float32) for e in (result.embeddings or [])]
        if not vectors:
            return np.zeros((0, self.dim), dtype=np.float32)
        matrix = np.vstack(vectors)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized: np.ndarray = (matrix / norms).astype(np.float32)
        return normalized
