"""Step 2, tool 2 — TRUSTED-CORPUS GROUNDING CHECK (the catch mechanism).

For each checkable claim, retrieve the most relevant passages from the org's
vetted corpus and ask Gemini whether the claim is supported, contradicted, or
not found — judging ONLY against those passages, never outside knowledge.

"not found" is treated as risk, not as pass. An unsupported specific claim on a
high-stakes topic is the confident fabrication Sentinel exists to catch.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from backend import llm
from backend.agents.prompt_loader import load_prompt
from backend.connectors.protocol import CorpusConnector
from backend.models.claim import Claim
from backend.models.grounding import GroundingResult, GroundingStatus, SourcePassage

logger = logging.getLogger(__name__)

_RETRIEVE_K = 6


class _GroundingJudgment(BaseModel):
    """The judge's verdict for one claim against the provided sources."""

    status: GroundingStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., min_length=1)
    corrected_text: str | None = None


def _format_sources(passages: list[SourcePassage]) -> str:
    if not passages:
        return "(no sources retrieved)"
    blocks = []
    for i, p in enumerate(passages, start=1):
        blocks.append(f"[Source {i}] {p.doc_title} (last verified {p.last_verified}):\n{p.text}")
    return "\n\n".join(blocks)


def ground_claim(
    claim: Claim,
    *,
    corpus: CorpusConnector,
    topic: str | None = None,
) -> GroundingResult:
    """Retrieve trusted passages for one claim and judge it against them."""
    passages = corpus.retrieve(claim.text, k=_RETRIEVE_K, topic=topic)
    judgment = llm.generate_structured(
        _GroundingJudgment,
        system=load_prompt("grounding"),
        prompt=f"CLAIM:\n{claim.text}\n\nSOURCES:\n{_format_sources(passages)}",
    )
    result = GroundingResult(
        claim_id=claim.id,
        claim_text=claim.text,
        status=judgment.status,
        confidence=judgment.confidence,
        passages=passages,
        explanation=judgment.explanation,
        corrected_text=judgment.corrected_text,
    )
    logger.info(
        "grounding: claim=%s status=%s confidence=%.2f passages=%d",
        claim.id,
        result.status,
        result.confidence,
        len(passages),
    )
    return result


def ground_claims(claims: list[Claim], *, corpus: CorpusConnector) -> list[GroundingResult]:
    """Ground every checkable claim; non-checkable claims are skipped."""
    return [ground_claim(c, corpus=corpus) for c in claims if c.checkable]
