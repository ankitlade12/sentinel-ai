"""The ADK agent endpoint — the code-owned agent runtime demonstration.

Runs the Google ADK ``LlmAgent`` (Gemini-driven, tool-planning) over a question
+ CASA draft and returns its narrated decision. The live dashboard uses the
deterministic orchestrator; this endpoint exists to exercise and trace the ADK
runtime the Arize track requires.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.agents.adk_agent import run_adk
from backend.api.deps import get_casa_dep
from backend.casa.bot import CasaBot
from backend.models.request import AskRequest

router = APIRouter(tags=["agent"])


class AgentResponse(BaseModel):
    question: str
    draft_answer: str
    agent_summary: str


@router.post("/agent", response_model=AgentResponse)
async def run_agent(
    req: AskRequest,
    casa: Annotated[CasaBot, Depends(get_casa_dep)],
) -> AgentResponse:
    """Run the ADK Sentinel agent over CASA's draft and return its summary."""
    draft = casa.answer(req.question)
    summary = await run_adk(req.question, draft.answer)
    return AgentResponse(question=req.question, draft_answer=draft.answer, agent_summary=summary)
