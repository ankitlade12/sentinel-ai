"""Grounding models — the heart of Sentinel.

Each checkable claim is checked against the org's *trusted corpus only* (never
the web). The verdict is one of supported / contradicted / not-found. The
critical policy: "not found" is treated as RISK, not as pass — an unsupported
specific claim on a high-stakes topic is the confident fabrication Sentinel
exists to catch.

Every grounding result carries the source passages it relied on, so the
quarantine view can show the bot's claim side-by-side with the official text.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GroundingStatus(StrEnum):
    """Verdict for a single claim against the trusted corpus."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


class SourcePassage(BaseModel):
    """A retrieved corpus passage with full provenance — a citable source.

    The provenance fields (``doc_title``, ``source_url``, ``page``,
    ``last_verified``) are what make every grounding verdict auditable and let
    the Trust Report flag stale corpus documents.
    """

    doc_id: str
    doc_title: str
    source_url: str | None = None
    page: str | None = None
    last_verified: str | None = Field(
        default=None, description="ISO date the org last verified this source."
    )
    text: str = Field(
        ..., min_length=1, description="The exact passage text shown side-by-side with the claim."
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Retrieval similarity score.")


class GroundingResult(BaseModel):
    """Grounding verdict for one claim, with the evidence it relied on."""

    claim_id: str
    claim_text: str
    status: GroundingStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    passages: list[SourcePassage] = Field(
        default_factory=list,
        description="Corpus passages that support or contradict the claim.",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Plain-English: why supported / contradicted / not found.",
    )
    corrected_text: str | None = Field(
        default=None,
        description="What the corpus actually says, when the claim is contradicted (feeds the REPAIR path).",
    )

    @property
    def is_risk(self) -> bool:
        """CONTRADICTED is always risk; NOT_FOUND is risk by policy (Section 3.2)."""
        return self.status in (GroundingStatus.CONTRADICTED, GroundingStatus.NOT_FOUND)
