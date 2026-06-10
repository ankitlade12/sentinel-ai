"""In-memory quarantine store — hermetic, for tests and offline development."""

from __future__ import annotations

import logging

from backend.models.verdict import Decision, ReviewStatus, SentinelVerdict

logger = logging.getLogger(__name__)


class MockQuarantineStore:
    """A process-local dict of verdicts. Not durable; resets on restart."""

    def __init__(self) -> None:
        self._verdicts: dict[str, SentinelVerdict] = {}

    def save_verdict(self, verdict: SentinelVerdict) -> None:
        self._verdicts[verdict.id] = verdict

    def get_verdict(self, verdict_id: str) -> SentinelVerdict | None:
        return self._verdicts.get(verdict_id)

    def _ordered(self, org_id: str) -> list[SentinelVerdict]:
        items = [v for v in self._verdicts.values() if v.org_id == org_id]
        return sorted(items, key=lambda v: v.created_at, reverse=True)

    def list_verdicts(
        self, *, org_id: str = "riverside", limit: int = 500
    ) -> list[SentinelVerdict]:
        return self._ordered(org_id)[:limit]

    def list_quarantined(
        self,
        *,
        org_id: str = "riverside",
        status: ReviewStatus = ReviewStatus.PENDING,
        limit: int = 200,
    ) -> list[SentinelVerdict]:
        items = [
            v
            for v in self._ordered(org_id)
            if v.decision == Decision.QUARANTINE and v.review_status == status
        ]
        return items[:limit]

    def resolve(
        self,
        verdict_id: str,
        *,
        status: ReviewStatus,
        staff_note: str | None,
        corrected_answer: str | None,
        resolved_at: str,
    ) -> SentinelVerdict | None:
        verdict = self._verdicts.get(verdict_id)
        if verdict is None:
            return None
        updated = verdict.model_copy(
            update={
                "review_status": status,
                "staff_note": staff_note,
                "resolved_at": resolved_at,
                "corrected_answer": corrected_answer or verdict.corrected_answer,
            }
        )
        self._verdicts[verdict_id] = updated
        return updated
