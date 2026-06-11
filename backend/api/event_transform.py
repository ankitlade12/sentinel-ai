"""Map streaming wire-event models → SSE event names.

The dashboard subscribes to these named events to render the run progressively
(triage lands, plan written, claims appear, grounding verdicts arrive, evals
score, final verdict).
"""

from __future__ import annotations

from pydantic import BaseModel

_EVENT_NAMES: dict[str, str] = {
    "AgentActivity": "agent_activity",
    "CasaDrafted": "casa_drafted",
    "TriageReady": "triage_ready",
    "PlanWritten": "plan_written",
    "ClaimExtracted": "claim_extracted",
    "GroundingChecked": "grounding_checked",
    "EvalScored": "eval_scored",
    "VerdictDecided": "verdict_decided",
    "DoneSignal": "done",
    "StreamError": "error",
}


def event_name(event: BaseModel) -> str:
    """Return the SSE event name for a wire-event model."""
    return _EVENT_NAMES.get(type(event).__name__, type(event).__name__.lower())
