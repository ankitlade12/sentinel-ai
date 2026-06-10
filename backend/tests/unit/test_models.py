"""Unit tests for the Pydantic contract invariants."""

from __future__ import annotations

import pytest

from backend.models.grounding import GroundingResult, GroundingStatus
from backend.models.trust_report import TopicStat

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (GroundingStatus.SUPPORTED, False),
        (GroundingStatus.CONTRADICTED, True),
        (GroundingStatus.NOT_FOUND, True),  # policy: not-found is risk, not pass
    ],
)
def test_grounding_is_risk(status, expected):
    result = GroundingResult(
        claim_id="c1", claim_text="x", status=status, confidence=0.9, explanation="x"
    )
    assert result.is_risk is expected


def test_topic_stat_quarantine_rate():
    stat = TopicStat(topic="t", answered=4, held=1)
    assert stat.quarantine_rate == 0.25
    assert TopicStat(topic="empty").quarantine_rate == 0.0
