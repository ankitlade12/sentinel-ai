# Arize Phoenix — three load-bearing roles

The Arize judges will open `backend/arize/`. Phoenix is structural here in three
distinct ways. None of them is a thin "we also log to Phoenix" bolt-on.

## 1. Evals as a decision input — `arize/evals.py`

The quarantine decision **consumes** Phoenix-style LLM-as-a-Judge scores as
first-class signals. Three evaluators run as Gemini structured calls with the
retrieved corpus passages passed as ground-truth context:

- `hallucination` — is every specific grounded in the reference?
- `qa_correctness` — does the answer correctly answer the question per the reference?
- `toxicity` — is the answer harmful? (the light path's safety glance)

`decide.py` reads the hallucination score against `SENTINEL_HALLUCINATION_THRESHOLD`
and the toxicity pass/fail directly. The integration test asserts the evals
actually ran and fed the verdict — they are not after-the-fact logs.

## 2. Tracing as the audit trail — `arize/tracing.py`

`setup_tracing()` registers the Phoenix OTel exporter and the OpenInference
auto-instrumentors for **Google GenAI, Google ADK, and Vertex AI**. Every
Sentinel run opens one span (`agent_span`) that all tool calls and Gemini calls
nest under. The span carries the triage verdict, the path, the decision, and
every eval score, and its trace id deep-links into Phoenix from the verdict.

> When Texas TRAIGA, Utah HB 452, or a HIPAA-style AI-risk rule asks this clinic
> to "show me your oversight," the Phoenix trace **is** the answer. We say that
> sentence in the video.

Required PyPI instrumentors (in `pyproject.toml`):
`openinference-instrumentation-google-genai`,
`openinference-instrumentation-google-adk`,
`openinference-instrumentation-vertexai`.

## 3. Monitoring as memory — `arize/monitors.py` + `arize/mcp.py` + `arize/phoenix_mcp_server.py`

The agent reads back its own accumulated verdicts to compute per-topic
quarantine rates, and feeds that history into the next decision: a topic whose
failure rate is rising raises the support bar (`topic_risk_adjustment`), so
borderline answers on a drifting topic are held more readily. This is the
**self-improvement loop** the track awards bonus points for.

`arize/phoenix_mcp_server.py` is a Python **Phoenix MCP server** (FastMCP) that
exposes the agent's observability as callable tools — `phoenix_project_summary`
queries Arize Phoenix Cloud **live** for the `sentinel` project's trace count,
and `topic_risk_history` surfaces per-topic drift. The **Google ADK agent spawns
this MCP server over stdio** (`build_phoenix_mcp_toolset` in `arize/mcp.py`,
using ADK's `StdioConnectionParams`), and the agent prompt directs it to call
`phoenix_project_summary` first — so the partner's MCP server is genuinely
imported and **called at runtime** (verified: the call returns a live `HTTP 200`
from Phoenix Cloud during `/api/agent`). The MCP server runs in-process over
stdio — no external endpoint required. The deterministic orchestrator calls
`topic_health()` for a stable, testable read of the same signal. Same memory,
two consumers.

The Trust Report's "trend" section is a plain-English rendering of this monitor
data, including the stale-corpus nudge (`stale_docs`).

## Setup

1. Create a free Phoenix Cloud account → https://app.phoenix.arize.com
2. Set in `.env`:
   ```
   PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
   PHOENIX_API_KEY=<your key>
   PHOENIX_PROJECT_NAME=sentinel
   ```
3. Run the agent. Traces, evals, and spans appear under the `sentinel` project.
   The ADK agent (`/api/agent`) spawns the Phoenix MCP server in-process and
   calls it at runtime — no extra configuration or endpoint needed.

If Phoenix is not configured, tracing degrades to no-ops — the agent still runs,
it just isn't observed. Tracing must never crash the request path.

## Resources

- Phoenix Cloud — https://app.phoenix.arize.com
- Phoenix docs — https://arize.com/docs/phoenix
- Phoenix MCP server — https://arize.com/docs/phoenix/integrations/phoenix-mcp-server
- OpenInference — https://github.com/Arize-ai/openinference
- LLM-as-a-Judge evals — https://arize.com/docs/phoenix/evaluation/llm-evals
