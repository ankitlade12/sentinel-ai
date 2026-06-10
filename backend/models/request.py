"""API request models for the Sentinel service boundary."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """End-user question routed through CASA → Sentinel → verdict."""

    question: str = Field(..., min_length=1)
    org_id: str = Field(default="riverside")
    conversation_id: str | None = None
    include_draft: bool = Field(
        default=True,
        description="Whether to surface the raw CASA draft alongside the verdict (demo split-screen).",
    )


class ReviewActionType(StrEnum):
    """What a director can do with a quarantined item."""

    RELEASE = "release"
    CORRECT = "correct"
    DISMISS = "dismiss"


class ReviewAction(BaseModel):
    """A human decision on a quarantined item (mandatory oversight for high-stakes)."""

    action: ReviewActionType
    staff_id: str = Field(default="staff")
    staff_note: str | None = None
    corrected_answer: str | None = Field(
        default=None,
        description="Required when action == CORRECT: the answer the staff member approves.",
    )
