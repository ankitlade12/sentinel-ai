"""Verdict models — the graduated, human-in-the-loop decision (Loop Step 3)
and the full audit record (Loop Step 4).

The ``SentinelVerdict`` is the compliance artifact: it carries the plan, every
claim, every grounding result, every eval score, the decision, and the Arize
trace link. When an AI-accountability rule asks the clinic to "prove oversight,"
this record — and its linked trace — is the answer.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from backend.models.claim import Claim
from backend.models.evaluation import EvalResult
from backend.models.grounding import GroundingResult
from backend.models.triage import SentinelPlan


class Decision(StrEnum):
    """The three graduated outcomes. Thresholds are org policy, not the agent's."""

    ALLOW = "allow"
    REPAIR_ALLOW = "repair_allow"
    QUARANTINE = "quarantine"


class ReviewStatus(StrEnum):
    """Lifecycle of a quarantined item in the director's queue."""

    PENDING = "pending"
    RELEASED = "released"
    CORRECTED = "corrected"
    DISMISSED = "dismissed"


class SentinelVerdict(BaseModel):
    """The complete, auditable record of one Sentinel run."""

    id: str
    org_id: str = Field(default="riverside")
    created_at: str = Field(..., description="ISO-8601 UTC timestamp.")

    question: str
    draft_answer: str = Field(..., description="The raw CASA answer Sentinel intercepted.")
    topic: str

    plan: SentinelPlan
    claims: list[Claim] = Field(default_factory=list)
    grounding: list[GroundingResult] = Field(default_factory=list)
    evals: list[EvalResult] = Field(default_factory=list)

    decision: Decision
    delivered_answer: str = Field(
        ...,
        description="What the end user actually sees: original, labeled-corrected, or honest fallback.",
    )
    user_message: str | None = Field(
        default=None,
        description="The honest fallback shown to the user when quarantined.",
    )
    corrected_answer: str | None = Field(
        default=None,
        description="A corpus-grounded corrected answer (REPAIR path), labeled as corrected.",
    )

    rationale: str = Field(..., min_length=1, description="Plain-English: why this decision.")
    failed_claim_ids: list[str] = Field(
        default_factory=list,
        description="Claims that drove a quarantine (contradicted or unsupported on a high-stakes topic).",
    )
    requires_human_review: bool = Field(default=False)

    # Arize spine — the audit trail link.
    trace_id: str | None = None
    trace_url: str | None = Field(
        default=None, description="Deep link to the Phoenix trace for this run."
    )

    latency_ms: int = Field(default=0, ge=0)
    policy_snapshot: dict[str, float] = Field(
        default_factory=dict,
        description="Org thresholds in effect at decision time, incl. any drift-based adjustment.",
    )

    # Director-queue lifecycle (set when a human acts on a quarantined item).
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    staff_note: str | None = None
    resolved_at: str | None = None
