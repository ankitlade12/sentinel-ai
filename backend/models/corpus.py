"""Corpus models — the org's vetted, per-org trusted documents.

Design principle: the corpus is the org's voice, not the internet's. Each chunk
carries source metadata so every grounding verdict can cite its source, and so
the Trust Report can surface stale documents and corpus gaps.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorpusDoc(BaseModel):
    """Metadata for one trusted source document."""

    id: str
    title: str
    topic: str = Field(
        ..., description="Coarse topic, e.g. 'immigration', 'housing', 'benefits', 'intake'."
    )
    source_url: str | None = None
    last_verified: str = Field(..., description="ISO date the org last verified this document.")
    path: str = Field(
        ..., description="Relative path to the source markdown under backend/corpus/."
    )


class CorpusChunk(BaseModel):
    """An embedded, retrievable slice of a trusted document."""

    id: str
    doc_id: str
    doc_title: str
    topic: str
    source_url: str | None = None
    page: str | None = None
    last_verified: str
    text: str = Field(..., min_length=1)
    embedding: list[float] | None = Field(
        default=None,
        description="Dense vector; omitted on the wire, populated in the index.",
    )
