"""Unit tests for the self-improvement monitors (monitoring as memory)."""

from __future__ import annotations

import pytest

from backend.arize import monitors
from backend.connectors.mock_store import MockQuarantineStore
from backend.models.grounding import GroundingResult, GroundingStatus
from backend.models.triage import (
    Coverage,
    PlanStep,
    SentinelPlan,
    Specificity,
    StakesLevel,
    TriageVerdict,
)
from backend.models.verdict import Decision, SentinelVerdict

pytestmark = pytest.mark.unit


def _verdict(
    topic: str, decision: Decision, *, idx: int, not_found: bool = False
) -> SentinelVerdict:
    plan = SentinelPlan(
        triage=TriageVerdict(
            topic=topic,
            stakes=StakesLevel.HIGH,
            specificity=Specificity.SPECIFIC_CLAIM,
            coverage=Coverage.IN_CORPUS,
            coverage_score=0.5,
            reasoning="x",
        ),
        path="full",
        steps=[PlanStep(tool="decide", why="x")],
        summary="x",
    )
    grounding = []
    if not_found:
        grounding = [
            GroundingResult(
                claim_id="c1",
                claim_text="x",
                status=GroundingStatus.NOT_FOUND,
                confidence=0.4,
                explanation="x",
            )
        ]
    return SentinelVerdict(
        id=f"v{idx}",
        created_at=f"2026-06-{idx:02d}T00:00:00+00:00",
        question="q",
        draft_answer="a",
        topic=topic,
        plan=plan,
        grounding=grounding,
        decision=decision,
        delivered_answer="a",
        rationale="x",
    )


def test_topic_risk_adjustment_rises_with_quarantine_rate():
    store = MockQuarantineStore()
    # 4 verdicts on one topic, 3 quarantined → rate 0.75 → bump capped at 0.15.
    store.save_verdict(_verdict("deadlines", Decision.QUARANTINE, idx=1))
    store.save_verdict(_verdict("deadlines", Decision.QUARANTINE, idx=2))
    store.save_verdict(_verdict("deadlines", Decision.QUARANTINE, idx=3))
    store.save_verdict(_verdict("deadlines", Decision.ALLOW, idx=4))
    adj = monitors.topic_risk_adjustment("deadlines", store, org_id="riverside")
    assert adj == pytest.approx(0.15)


def test_topic_risk_adjustment_zero_below_sample_floor():
    store = MockQuarantineStore()
    store.save_verdict(_verdict("rare", Decision.QUARANTINE, idx=1))
    assert monitors.topic_risk_adjustment("rare", store, org_id="riverside") == 0.0


def test_topic_stats_and_riskiest_safest():
    store = MockQuarantineStore()
    store.save_verdict(_verdict("benefits", Decision.QUARANTINE, idx=1))
    store.save_verdict(_verdict("benefits", Decision.QUARANTINE, idx=2))
    store.save_verdict(_verdict("intake", Decision.ALLOW, idx=3))
    store.save_verdict(_verdict("intake", Decision.ALLOW, idx=4))
    stats = monitors.topic_stats(store.list_verdicts(org_id="riverside"))
    riskiest, safest = monitors.riskiest_and_safest(stats)
    assert riskiest == "benefits"
    assert safest == "intake"


def test_corpus_gap_topics_from_not_found():
    store = MockQuarantineStore()
    store.save_verdict(_verdict("evictions", Decision.QUARANTINE, idx=1, not_found=True))
    gaps = monitors.corpus_gap_topics(store.list_verdicts(org_id="riverside"))
    assert "evictions" in gaps
