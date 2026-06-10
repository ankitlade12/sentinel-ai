"""Streaming wire events — the SSE vocabulary the dashboard renders progressively.

The agent loop emits these as it works so the demo can show the *visible
decisions*: triage lands, the plan is written, claims appear one by one,
grounding verdicts arrive with their sources, eval scores stream in, then the
final verdict. Two inputs produce two visibly different event sequences — that
is the difference between scoring as an agent and scoring as a filter.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.models.claim import Claim
from backend.models.evaluation import EvalResult
from backend.models.grounding import GroundingResult
from backend.models.triage import SentinelPlan, TriageVerdict
from backend.models.verdict import Decision, SentinelVerdict


class AgentActivity(BaseModel):
    """A narration line — what the agent is doing right now."""

    activity_type: str = Field(..., description="e.g. 'triage', 'tool_call', 'decision'.")
    summary: str
    detail: dict[str, object] = Field(default_factory=dict)


class CasaDrafted(BaseModel):
    """The raw CASA draft, surfaced for the demo split-screen."""

    answer: str
    topic_hint: str = ""


class TriageReady(BaseModel):
    """Triage classification landed."""

    triage: TriageVerdict


class PlanWritten(BaseModel):
    """The agent committed to a plan and a path (light vs full)."""

    plan: SentinelPlan


class ClaimExtracted(BaseModel):
    """One atomic claim was decomposed from the draft."""

    claim: Claim


class GroundingChecked(BaseModel):
    """A claim was checked against the trusted corpus."""

    result: GroundingResult


class EvalScored(BaseModel):
    """A Phoenix evaluator returned a score for the draft answer."""

    result: EvalResult


class VerdictDecided(BaseModel):
    """The graduated decision was made; the full audit record is attached."""

    verdict: SentinelVerdict


class DoneSignal(BaseModel):
    """Terminal success event."""

    verdict_id: str
    decision: Decision


class StreamError(BaseModel):
    """Terminal error event."""

    code: str
    message: str
    recoverable: bool = False
