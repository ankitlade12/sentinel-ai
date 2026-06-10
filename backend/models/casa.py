"""CASA bot models — the demo legal-aid chatbot Sentinel watches.

CASA ("Community Advice & Support Assistant") is a deliberately imperfect prop:
a thin Gemini wrapper over a small FAQ, intentionally prone to hallucinating
specifics (deadlines, dollar amounts, form numbers). Its purpose is to give
Sentinel something real to catch.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CasaRequest(BaseModel):
    """A question from an end user to the CASA bot."""

    question: str = Field(..., min_length=1)
    conversation_id: str | None = None


class CasaAnswer(BaseModel):
    """CASA's draft answer — intercepted by Sentinel before it reaches the user."""

    answer: str = Field(..., min_length=1)
    topic_hint: str = Field(
        default="", description="CASA's own guess at the topic (advisory only)."
    )
    model: str = Field(default="gemini")
    generated_at: str
