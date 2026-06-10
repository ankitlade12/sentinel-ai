"""Contract tests for the quarantine store."""

from __future__ import annotations

import pytest

from backend.connectors.mock_store import MockQuarantineStore
from backend.connectors.store_protocol import QuarantineStore
from backend.models.triage import (
    Coverage,
    PlanStep,
    SentinelPlan,
    Specificity,
    StakesLevel,
    TriageVerdict,
)
from backend.models.verdict import Decision, ReviewStatus, SentinelVerdict

pytestmark = pytest.mark.contract


def _verdict(vid: str, decision: Decision) -> SentinelVerdict:
    plan = SentinelPlan(
        triage=TriageVerdict(
            topic="t",
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
    return SentinelVerdict(
        id=vid,
        created_at="2026-06-10T00:00:00+00:00",
        question="q",
        draft_answer="a",
        topic="t",
        plan=plan,
        decision=decision,
        delivered_answer="a",
        rationale="x",
        requires_human_review=decision == Decision.QUARANTINE,
    )


@pytest.fixture
def store() -> QuarantineStore:
    return MockQuarantineStore()


def test_satisfies_protocol(store):
    assert isinstance(store, QuarantineStore)


def test_save_get_list(store):
    store.save_verdict(_verdict("v1", Decision.ALLOW))
    store.save_verdict(_verdict("v2", Decision.QUARANTINE))
    assert store.get_verdict("v1") is not None
    assert store.get_verdict("missing") is None
    assert len(store.list_verdicts(org_id="riverside")) == 2


def test_quarantine_queue_and_resolve(store):
    store.save_verdict(_verdict("v1", Decision.QUARANTINE))
    pending = store.list_quarantined(org_id="riverside", status=ReviewStatus.PENDING)
    assert [v.id for v in pending] == ["v1"]

    updated = store.resolve(
        "v1",
        status=ReviewStatus.RELEASED,
        staff_note="ok",
        corrected_answer=None,
        resolved_at="2026-06-10T01:00:00+00:00",
    )
    assert updated is not None
    assert updated.review_status == ReviewStatus.RELEASED
    assert store.list_quarantined(org_id="riverside", status=ReviewStatus.PENDING) == []
