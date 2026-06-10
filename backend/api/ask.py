"""The ask endpoint — route an end-user question through CASA → Sentinel.

Two shapes:
- ``POST /api/ask``        — run the loop and return the draft + final verdict.
- ``POST /api/ask/stream`` — Server-Sent Events: the run streams progressively
  so the dashboard can show the agent's visible decisions as they happen.

The orchestrator is synchronous (the Gemini SDK is sync), so streaming runs it
in a worker thread and bridges its ``emit`` callback into an asyncio queue.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

import anyio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.agents.sentinel import SentinelAgent
from backend.api.deps import get_agent_dep, get_casa_dep
from backend.api.event_transform import event_name
from backend.casa.bot import CasaBot
from backend.models.casa import CasaAnswer
from backend.models.request import AskRequest
from backend.models.streaming import CasaDrafted, StreamError
from backend.models.verdict import SentinelVerdict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])

_STREAM_DONE = object()


class AskResponse(BaseModel):
    """Non-streaming result: what CASA drafted and what Sentinel decided."""

    draft: CasaAnswer
    verdict: SentinelVerdict


@router.post("/ask", response_model=AskResponse)
async def ask(
    req: AskRequest,
    agent: Annotated[SentinelAgent, Depends(get_agent_dep)],
    casa: Annotated[CasaBot, Depends(get_casa_dep)],
) -> AskResponse:
    """Run CASA, then Sentinel, and return the draft alongside the verdict."""

    def _work() -> tuple[CasaAnswer, SentinelVerdict]:
        draft = casa.answer(req.question)
        verdict = agent.run(req.question, draft.answer, org_id=req.org_id)
        return draft, verdict

    draft, verdict = await anyio.to_thread.run_sync(_work)
    logger.info("ask: decision=%s topic=%r", verdict.decision, verdict.topic)
    return AskResponse(draft=draft, verdict=verdict)


async def _stream(
    agent: SentinelAgent, casa: CasaBot, req: AskRequest
) -> AsyncIterator[dict[str, str]]:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def emit(event: BaseModel) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def work() -> None:
        try:
            draft = casa.answer(req.question)
            if req.include_draft:
                emit(CasaDrafted(answer=draft.answer, topic_hint=draft.topic_hint))
            agent.run(req.question, draft.answer, org_id=req.org_id, emit=emit)
        except Exception as exc:  # pragma: no cover - surfaced to the client
            logger.exception("ask/stream: run failed")
            emit(StreamError(code="internal_error", message=str(exc) or "Unexpected error."))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _STREAM_DONE)

    future = loop.run_in_executor(None, work)
    try:
        while True:
            event = await queue.get()
            if event is _STREAM_DONE:
                break
            yield {"event": event_name(event), "data": event.model_dump_json()}
    finally:
        await future


@router.post("/ask/stream")
async def ask_stream(
    req: AskRequest,
    agent: Annotated[SentinelAgent, Depends(get_agent_dep)],
    casa: Annotated[CasaBot, Depends(get_casa_dep)],
) -> EventSourceResponse:
    """Stream the CASA draft + the full Sentinel run as Server-Sent Events."""
    logger.info("ask/stream start: question=%r org=%s", req.question, req.org_id)
    return EventSourceResponse(_stream(agent, casa, req))
