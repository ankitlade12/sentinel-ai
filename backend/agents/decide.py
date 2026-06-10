"""Step 3 — DECIDE: the graduated, human-in-the-loop verdict.

Three outcomes — ALLOW, REPAIR_ALLOW, QUARANTINE — and the thresholds are policy
the *org* sets, not the agent. Two non-negotiable rules from the spec:

- Never silently rewrite without labeling (REPAIR_ALLOW always labels + cites).
- Never block without telling the user something true (QUARANTINE returns an
  honest fallback, and human review is mandatory for high-stakes).

This module is pure policy over already-computed signals (grounding + evals), so
it is fully unit-testable without any LLM or network.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from backend.config import Settings
from backend.models.evaluation import EvalKind, EvalResult
from backend.models.grounding import GroundingResult, GroundingStatus
from backend.models.triage import SentinelPlan, StakesLevel
from backend.models.verdict import Decision

logger = logging.getLogger(__name__)

QUARANTINE_FALLBACK = (
    "I want to make sure you get accurate information about this. The details here "
    "really matter, so I've asked a staff member at Riverside Community Legal Aid to "
    "follow up with you personally rather than risk giving you the wrong answer. "
    "Please call us Monday-Friday, 9am-5pm, or leave your contact details and we'll "
    "reach out."
)


class DecisionOutcome(BaseModel):
    """Internal result of the decision policy (assembled into a verdict upstream)."""

    decision: Decision
    rationale: str
    failed_claim_ids: list[str]
    requires_human_review: bool
    should_repair: bool
    user_message: str | None = None


def _find(evals: list[EvalResult], kind: EvalKind) -> EvalResult | None:
    return next((e for e in evals if e.kind == kind), None)


def decide(
    *,
    plan: SentinelPlan,
    grounding: list[GroundingResult],
    evals: list[EvalResult],
    settings: Settings,
    risk_adjustment: float = 0.0,
) -> DecisionOutcome:
    """Apply the org's policy to the grounding + eval signals.

    ``risk_adjustment`` comes from the self-improvement loop (Section 4.3): a
    topic that has been failing more often lately raises the support bar, so
    borderline answers on a drifting topic are held more readily.
    """
    stakes = plan.triage.stakes
    threshold = min(1.0, max(0.0, settings.quarantine_threshold + risk_adjustment))

    toxicity = _find(evals, EvalKind.TOXICITY)
    hallucination = _find(evals, EvalKind.HALLUCINATION)

    # ── Light path: low factual risk. Allow unless the safety check trips. ──
    if plan.path == "light":
        if toxicity is not None and not toxicity.passed:
            return DecisionOutcome(
                decision=Decision.QUARANTINE,
                rationale="The safety check flagged this answer; holding it for staff review.",
                failed_claim_ids=[],
                requires_human_review=True,
                should_repair=False,
                user_message=QUARANTINE_FALLBACK,
            )
        return DecisionOutcome(
            decision=Decision.ALLOW,
            rationale=(
                f"Low factual risk ({plan.triage.topic}); no checkable claims to verify. "
                "Cleared after a light safety check."
            ),
            failed_claim_ids=[],
            requires_human_review=False,
            should_repair=False,
        )

    # ── Full path: weigh grounding + evals. ──
    contradicted = [g for g in grounding if g.status == GroundingStatus.CONTRADICTED]
    not_found = [g for g in grounding if g.status == GroundingStatus.NOT_FOUND]
    low_confidence = [
        g for g in grounding if g.status == GroundingStatus.SUPPORTED and g.confidence < threshold
    ]
    hallucinated = (
        hallucination is not None and hallucination.score >= settings.hallucination_threshold
    )
    toxic = toxicity is not None and not toxicity.passed

    failed = [*contradicted, *not_found, *low_confidence]
    failed_ids = [g.claim_id for g in failed]
    has_risk = bool(failed) or hallucinated or toxic

    if not has_risk:
        return DecisionOutcome(
            decision=Decision.ALLOW,
            rationale=(
                f"All {len(grounding)} checkable claim(s) are supported by the trusted corpus"
                + (" and the hallucination eval is clean." if hallucination else ".")
            ),
            failed_claim_ids=[],
            requires_human_review=False,
            should_repair=False,
        )

    # There IS risk. Can we cleanly repair from the corpus instead of holding?
    correctable = [g for g in contradicted if g.corrected_text]
    repairable = (
        settings.enable_repair
        and stakes != StakesLevel.HIGH  # high-stakes always gets a human
        and bool(correctable)
        and not not_found  # a gap in the corpus is not repairable
        and not toxic
        and plan.triage.coverage.value == "in_corpus"
    )

    if repairable:
        sources = ", ".join(sorted({p.doc_title for g in correctable for p in g.passages}))
        return DecisionOutcome(
            decision=Decision.REPAIR_ALLOW,
            rationale=(
                f"{len(correctable)} claim(s) contradicted the trusted corpus, but a correction is "
                f"cleanly derivable from {sources}. Delivering a corrected, cited answer "
                "(labeled as corrected) rather than holding."
            ),
            failed_claim_ids=failed_ids,
            requires_human_review=False,
            should_repair=True,
        )

    reasons: list[str] = []
    if contradicted:
        reasons.append(f"{len(contradicted)} claim(s) contradicted by the trusted corpus")
    if not_found:
        reasons.append(
            f"{len(not_found)} specific claim(s) not found in the corpus (treated as risk)"
        )
    if low_confidence:
        reasons.append(f"{len(low_confidence)} claim(s) only weakly supported")
    if hallucinated and hallucination is not None:
        reasons.append(f"hallucination eval scored {hallucination.score:.2f}")
    if toxic:
        reasons.append("safety check failed")

    rationale = (
        f"Held for staff review: {'; '.join(reasons)}. On a {stakes.value}-stakes "
        f"{plan.triage.topic} question, human review is required."
    )
    logger.info("decide: QUARANTINE stakes=%s reasons=%s", stakes, reasons)
    return DecisionOutcome(
        decision=Decision.QUARANTINE,
        rationale=rationale,
        failed_claim_ids=failed_ids,
        requires_human_review=True,
        should_repair=False,
        user_message=QUARANTINE_FALLBACK,
    )
