"""The ``CorpusConnector`` protocol — Sentinel's grounding source.

A corpus connector retrieves vetted passages for a claim and reports how well a
question is covered by the org's documents. Both the mock and the Vertex
implementations satisfy this protocol, and the contract test suite runs against
both for parity.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.models.corpus import CorpusDoc
from backend.models.grounding import SourcePassage


@runtime_checkable
class CorpusConnector(Protocol):
    """Retrieval over the org's trusted corpus. Never touches the web."""

    def retrieve(self, query: str, *, k: int = 4, topic: str | None = None) -> list[SourcePassage]:
        """Return the top-``k`` most relevant passages, optionally topic-scoped."""
        ...

    def coverage(self, query: str) -> float:
        """Return the best similarity of ``query`` to any corpus chunk, in [0, 1].

        Used by triage to decide in-corpus vs out-of-corpus — an out-of-corpus
        high-stakes question is a quarantine by policy.
        """
        ...

    def topics(self) -> list[str]:
        """Distinct coarse topics present in the corpus."""
        ...

    def documents(self) -> list[CorpusDoc]:
        """Document-level metadata (title, source, last-verified) for every doc."""
        ...
