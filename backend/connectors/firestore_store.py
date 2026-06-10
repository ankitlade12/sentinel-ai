"""Firestore quarantine store — the durable, serverless verdict log (live path).

Verdicts are stored as documents under ``{prefix}_verdicts``. Firestore is
imported lazily so the package loads without the dependency in the test tier.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.config import get_settings
from backend.models.verdict import Decision, ReviewStatus, SentinelVerdict

logger = logging.getLogger(__name__)


class FirestoreQuarantineStore:
    """Persist verdicts in Cloud Firestore."""

    def __init__(self) -> None:
        from google.cloud import firestore

        settings = get_settings()
        self._client = firestore.Client(project=settings.google_cloud_project or None)
        self._collection = f"{settings.firestore_prefix}_verdicts"
        logger.info("firestore store: collection=%s", self._collection)

    def _col(self) -> Any:
        return self._client.collection(self._collection)

    def save_verdict(self, verdict: SentinelVerdict) -> None:
        self._col().document(verdict.id).set(verdict.model_dump(mode="json"))

    def get_verdict(self, verdict_id: str) -> SentinelVerdict | None:
        snap = self._col().document(verdict_id).get()
        if not snap.exists:
            return None
        return SentinelVerdict.model_validate(snap.to_dict())

    def list_verdicts(
        self, *, org_id: str = "riverside", limit: int = 500
    ) -> list[SentinelVerdict]:
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = (
            self._col()
            .where(filter=FieldFilter("org_id", "==", org_id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [SentinelVerdict.model_validate(d.to_dict()) for d in query.stream()]

    def list_quarantined(
        self,
        *,
        org_id: str = "riverside",
        status: ReviewStatus = ReviewStatus.PENDING,
        limit: int = 200,
    ) -> list[SentinelVerdict]:
        # NOTE: three equality filters + order_by requires a Firestore composite
        # index. On first run Firestore returns a one-click "create index" link;
        # see docs/GCP_SETUP.md.
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = (
            self._col()
            .where(filter=FieldFilter("org_id", "==", org_id))
            .where(filter=FieldFilter("decision", "==", Decision.QUARANTINE.value))
            .where(filter=FieldFilter("review_status", "==", status.value))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [SentinelVerdict.model_validate(d.to_dict()) for d in query.stream()]

    def resolve(
        self,
        verdict_id: str,
        *,
        status: ReviewStatus,
        staff_note: str | None,
        corrected_answer: str | None,
        resolved_at: str,
    ) -> SentinelVerdict | None:
        verdict = self.get_verdict(verdict_id)
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
        self.save_verdict(updated)
        return updated
