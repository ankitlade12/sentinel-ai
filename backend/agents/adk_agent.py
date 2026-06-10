"""The Sentinel agent on Google ADK — the code-owned agent runtime.

The Arize track requires a code-owned agent runtime (Gemini CLI, Google ADK,
Agent Runtime, or Cloud Run). This module builds a Google ADK ``LlmAgent`` driven
by Gemini, equipped with Sentinel's function tools and — when configured — the
Phoenix MCP server as a toolset so the agent can introspect its own traces and
evals at runtime. ADK calls are auto-instrumented by OpenInference, so an agent
run shows up as a full Phoenix trace.

The FastAPI service uses the deterministic orchestrator for the live dashboard;
this agent is exposed at ``/api/agent`` and used by ``scripts/`` to demonstrate
the autonomous, tool-planning runtime the track asks for.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from backend.agents.prompt_loader import load_prompt
from backend.agents.tools.sentinel_tools import SENTINEL_TOOLS
from backend.arize.mcp import build_phoenix_mcp_toolset
from backend.config import get_settings

logger = logging.getLogger(__name__)

_APP_NAME = "sentinel"


@lru_cache(maxsize=1)
def build_sentinel_adk_agent() -> Any:
    """Construct the Gemini-driven ADK agent with Sentinel's tools + Phoenix MCP."""
    from google.adk.agents import LlmAgent

    settings = get_settings()
    tools: list[Any] = list(SENTINEL_TOOLS)
    mcp_toolset = build_phoenix_mcp_toolset()
    if mcp_toolset is not None:
        tools.append(mcp_toolset)
        logger.info("adk: Phoenix MCP toolset attached (runtime self-introspection)")

    return LlmAgent(
        name="sentinel",
        model=settings.gemini_model,
        instruction=load_prompt("sentinel_agent"),
        description="Watches a legal-aid chatbot and holds confidently-wrong answers.",
        tools=tools,
    )


async def run_adk(question: str, draft_answer: str, *, user_id: str = "demo") -> str:
    """Run the ADK agent over one (question, answer) pair and return its summary.

    Best-effort: returns a readable error string rather than raising, so the demo
    endpoint degrades gracefully if the ADK runtime or Gemini credentials are
    unavailable.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        agent = build_sentinel_adk_agent()
        session_service = InMemorySessionService()  # type: ignore[no-untyped-call]
        session = await session_service.create_session(app_name=_APP_NAME, user_id=user_id)
        runner = Runner(agent=agent, app_name=_APP_NAME, session_service=session_service)

        message = types.Content(
            role="user",
            parts=[types.Part(text=f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{draft_answer}")],
        )
        final = ""
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(part.text or "" for part in event.content.parts)
        return final or "(agent produced no final response)"
    except Exception as exc:  # pragma: no cover - depends on ADK runtime + creds
        logger.warning("adk: run failed", exc_info=True)
        return f"ADK runtime unavailable: {exc}"
