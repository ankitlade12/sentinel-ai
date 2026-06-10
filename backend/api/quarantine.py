"""The director's queue — list verdicts, inspect one, and resolve quarantines.

Resolving an item is the mandatory human-in-the-loop step for high-stakes
answers: a staff member releases, corrects, or dismisses, and the action is
recorded on the verdict's audit trail.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_store_dep
from backend.connectors.store_protocol import QuarantineStore
from backend.models.request import ReviewAction, ReviewActionType
from backend.models.verdict import ReviewStatus, SentinelVerdict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["review"])

_ACTION_TO_STATUS: dict[ReviewActionType, ReviewStatus] = {
    ReviewActionType.RELEASE: ReviewStatus.RELEASED,
    ReviewActionType.CORRECT: ReviewStatus.CORRECTED,
    ReviewActionType.DISMISS: ReviewStatus.DISMISSED,
}


@router.get("/quarantine", response_model=list[SentinelVerdict])
def list_quarantine(
    store: Annotated[QuarantineStore, Depends(get_store_dep)],
    org_id: str = "riverside",
    status: ReviewStatus = ReviewStatus.PENDING,
) -> list[SentinelVerdict]:
    """Return quarantined verdicts in a given review state (default: pending)."""
    return store.list_quarantined(org_id=org_id, status=status)


@router.get("/verdicts", response_model=list[SentinelVerdict])
def list_verdicts(
    store: Annotated[QuarantineStore, Depends(get_store_dep)],
    org_id: str = "riverside",
    limit: int = 100,
) -> list[SentinelVerdict]:
    """Return recent verdicts (newest first) — the live activity feed."""
    return store.list_verdicts(org_id=org_id, limit=limit)


@router.get("/verdicts/{verdict_id}", response_model=SentinelVerdict)
def get_verdict(
    verdict_id: str,
    store: Annotated[QuarantineStore, Depends(get_store_dep)],
) -> SentinelVerdict:
    """Fetch one verdict's full audit record."""
    verdict = store.get_verdict(verdict_id)
    if verdict is None:
        raise HTTPException(status_code=404, detail="verdict not found")
    return verdict


@router.post("/quarantine/{verdict_id}/resolve", response_model=SentinelVerdict)
def resolve_quarantine(
    verdict_id: str,
    action: ReviewAction,
    store: Annotated[QuarantineStore, Depends(get_store_dep)],
) -> SentinelVerdict:
    """Record a staff decision on a quarantined item."""
    if action.action == ReviewActionType.CORRECT and not action.corrected_answer:
        raise HTTPException(
            status_code=422, detail="corrected_answer is required to correct an item"
        )

    note = action.staff_note
    if action.staff_id:
        note = f"[{action.staff_id}] {note}" if note else f"[{action.staff_id}]"

    updated = store.resolve(
        verdict_id,
        status=_ACTION_TO_STATUS[action.action],
        staff_note=note,
        corrected_answer=action.corrected_answer,
        resolved_at=datetime.now(UTC).isoformat(),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="verdict not found")
    logger.info("review: verdict=%s action=%s by=%s", verdict_id, action.action, action.staff_id)
    return updated
