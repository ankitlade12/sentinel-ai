"""Phoenix MCP server — runtime self-introspection for the Sentinel agent.

A Model Context Protocol (MCP) server that exposes the agent's Arize Phoenix
observability data as callable tools. The Google ADK agent spawns this over
stdio (see ``backend/arize/mcp.py``) and calls it while it reasons, so the agent
can query its own Phoenix traces and per-topic history at decision time — the
"monitoring as memory" capability the Arize track recommends.

Run standalone for debugging:  python -m backend.arize.phoenix_mcp_server
"""

from __future__ import annotations

import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=False)

from mcp.server.fastmcp import FastMCP  # noqa: E402

logger = logging.getLogger(__name__)

mcp = FastMCP("sentinel-phoenix")


@mcp.tool()
def phoenix_project_summary() -> dict[str, Any]:
    """Query Arize Phoenix for the Sentinel project's observability — how many
    traces the guardian agent has recorded so far. Call this to ground a
    decision in what the team has actually seen recently.
    """
    from backend.config import get_settings

    settings = get_settings()
    out: dict[str, Any] = {
        "project": settings.phoenix_project_name,
        "endpoint": settings.phoenix_collector_endpoint,
        "source": "arize_phoenix",
    }
    try:
        from phoenix.client import Client

        client = Client()
        projects = client.projects.list()
        out["projects_visible"] = len(projects) if projects is not None else 0
        try:
            df = client.spans.get_spans_dataframe(project_name=settings.phoenix_project_name)
            out["spans"] = len(df)
            if "name" in df.columns:
                out["agent_runs"] = int((df["name"] == "sentinel.run").sum())
        except Exception:  # pragma: no cover - span query is best effort
            logger.debug("phoenix mcp: span dataframe query failed", exc_info=True)
    except Exception as exc:  # pragma: no cover - reachability is best effort
        out["note"] = f"Phoenix reachability check: {str(exc)[:120]}"
    return out


@mcp.tool()
def topic_risk_history(topic: str) -> dict[str, Any]:
    """Look up how a topic has been performing for the team — its quarantine rate
    and the drift-based risk adjustment — so the agent can tighten its support
    bar on a topic that has been failing more often lately.
    """
    try:
        from backend.arize.mcp import topic_health
        from backend.config import get_store

        return topic_health(topic, get_store(), org_id="riverside").model_dump(mode="json")
    except Exception as exc:  # pragma: no cover
        return {"topic": topic, "error": str(exc)[:120]}


if __name__ == "__main__":
    mcp.run()
