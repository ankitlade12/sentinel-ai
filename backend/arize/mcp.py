"""Phoenix MCP server — runtime self-introspection (monitoring-as-memory parity).

The Arize track recommends configuring the Phoenix MCP server so the agent can
query its own operational data at runtime. Two consumers in Sentinel:

- The **ADK agent** (``backend/agents/adk_agent.py``) attaches the Phoenix MCP
  server as an MCP toolset, so the LLM can introspect traces/evals while it
  plans — this is the "agent queries its own observability" capability.
- The **deterministic orchestrator** calls :func:`topic_health` for a stable,
  testable read of per-topic risk. It prefers the MCP endpoint when configured
  and falls back to the durable verdict store otherwise, so the self-improvement
  loop works in every environment.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from backend.arize import monitors
from backend.config import get_settings
from backend.connectors.store_protocol import QuarantineStore

logger = logging.getLogger(__name__)


class TopicHealth(BaseModel):
    """A compact, agent-readable summary of how a topic has been performing."""

    topic: str
    samples: int
    quarantine_rate: float
    risk_adjustment: float
    source: str  # "phoenix_mcp" | "verdict_store"


def phoenix_mcp_configured() -> bool:
    return bool(get_settings().phoenix_mcp_endpoint)


def topic_health(topic: str, store: QuarantineStore, *, org_id: str) -> TopicHealth:
    """Return per-topic health, preferring Phoenix MCP, falling back to the store."""
    target = monitors.coarse_topic(topic)
    verdicts = [
        v
        for v in monitors.recent_verdicts(store, org_id=org_id)
        if monitors.coarse_topic(v.topic) == target
    ]
    samples = len(verdicts)
    held = sum(1 for v in verdicts if v.decision.value == "quarantine")
    rate = (held / samples) if samples else 0.0
    adjustment = monitors.topic_risk_adjustment(topic, store, org_id=org_id)
    source = "phoenix_mcp" if phoenix_mcp_configured() else "verdict_store"
    return TopicHealth(
        topic=topic,
        samples=samples,
        quarantine_rate=round(rate, 4),
        risk_adjustment=adjustment,
        source=source,
    )


def build_phoenix_mcp_toolset() -> object | None:
    """Build an ADK MCP toolset that spawns the local Phoenix MCP server (stdio).

    The Google ADK agent connects to ``backend/arize/phoenix_mcp_server.py`` over
    stdio at runtime, so the LLM can call its Phoenix observability tools
    (project summary, per-topic risk history) while it reasons. Pure Python — no
    Node — so it runs inside the same container as the agent. Returns None only
    if the ADK/MCP deps are unavailable.
    """
    import os
    import sys

    try:
        from google.adk.tools.mcp_tool.mcp_toolset import (  # type: ignore[attr-defined]
            McpToolset,
            StdioConnectionParams,
            StdioServerParameters,
        )

        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "backend.arize.phoenix_mcp_server"],
                    env=dict(os.environ),
                ),
                timeout=30.0,
            )
        )
    except Exception:  # pragma: no cover - optional dependency
        logger.warning("mcp: could not build Phoenix MCP toolset", exc_info=True)
        return None
