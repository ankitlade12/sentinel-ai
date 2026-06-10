"""The ``QuarantineStore`` protocol — verdict audit log + director queue.

Every Sentinel verdict is persisted (the audit trail), and quarantined verdicts
form the director's review queue. Both the mock and Firestore implementations
satisfy this protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.models.verdict import ReviewStatus, SentinelVerdict


@runtime_checkable
class QuarantineStore(Protocol):
    """Persistence for verdicts and the human-review queue."""

    def save_verdict(self, verdict: SentinelVerdict) -> None:
        """Persist (or overwrite) a verdict by id."""
        ...

    def get_verdict(self, verdict_id: str) -> SentinelVerdict | None:
        """Fetch a single verdict, or None if absent."""
        ...

    def list_verdicts(
        self, *, org_id: str = "riverside", limit: int = 500
    ) -> list[SentinelVerdict]:
        """Return recent verdicts (newest first) — the basis for the Trust Report."""
        ...

    def list_quarantined(
        self,
        *,
        org_id: str = "riverside",
        status: ReviewStatus = ReviewStatus.PENDING,
        limit: int = 200,
    ) -> list[SentinelVerdict]:
        """Return quarantined verdicts in a given review state (the director queue)."""
        ...

    def resolve(
        self,
        verdict_id: str,
        *,
        status: ReviewStatus,
        staff_note: str | None,
        corrected_answer: str | None,
        resolved_at: str,
    ) -> SentinelVerdict | None:
        """Record a human decision on a quarantined item; return the updated verdict."""
        ...
