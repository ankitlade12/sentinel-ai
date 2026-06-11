# Engineering Decisions

Append-only log of decisions with lasting consequences. When the PRD and this
log conflict on *mechanism*, this log wins; on *product intent*, the PRD wins.

---

## D-001 — Two-layer agent: deterministic orchestrator + ADK runtime

**Status:** Accepted

The live product path is a deterministic orchestrator (`agents/sentinel.py`) that
runs the loop, streams typed SSE events, and is fully unit-testable. The Arize
track requires a code-owned agent runtime, so the *same step functions* are also
exposed to a Google ADK `LlmAgent` (`agents/adk_agent.py`) that plans with
Gemini and calls them as tools. One source of truth (the step modules), two
drivers. The orchestrator gives reliability and a rich UI; the ADK agent gives
the tool-planning runtime + ADK instrumentation.

## D-002 — "Not found in corpus" is risk, not pass

**Status:** Accepted

The mechanism that catches confident fabrications. An unsupported specific claim
on a high-stakes topic is quarantined. See [`../DESIGN.md`](../DESIGN.md). The
risk is over-quarantining the harmless; the mitigation is triage (only the full
path grounds) + per-claim checkability.

## D-003 — The corpus is the org's voice, never the web

**Status:** Accepted

Sentinel grounds only against the org's vetted documents. Web search would
reintroduce the unreliability it exists to remove. No-coverage becomes a
quarantine and a corpus-gap entry in the Trust Report.

## D-004 — Connector + store protocols; mock ⇄ live parity

**Status:** Accepted

`CorpusConnector` and `QuarantineStore` are protocols. `config.get_corpus()` /
`get_store()` are the single swap points between hermetic mocks (CI/offline) and
Vertex AI Vector Search + Firestore (demo/prod). Contract tests run against the
mock; the same suite is `@pytest.mark.live` against the real services.

## D-005 — Structured outputs everywhere; TS generated from Pydantic

**Status:** Accepted

Every agent output is a Pydantic model. The frontend never hand-writes API
types — `scripts/generate_typescript_types.py` emits `frontend/types/generated.ts`
(`make types`). No drift between backend and dashboard.

## D-006 — Gemini via the unified Google GenAI SDK, temperature 0

**Status:** Accepted

All reasoning goes through `backend/llm.py` at temperature 0 for pipeline-critical
determinism. Provider is `vertex` (ADC) by default, `ai_studio` (API key) as an
alternative. Centralizing the entry point is also what makes every call
auto-traceable by the OpenInference GenAI instrumentor.

## D-007 — Arize is structural in three roles

**Status:** Accepted

Evals as a decision input, tracing as the audit trail, monitoring as memory. See
[`ARIZE.md`](ARIZE.md). A dedicated top-level `backend/arize/` module makes the
dependency impossible to miss in a 5-minute review.

## D-008 — Triage branching is the agent signal

**Status:** Accepted

Light path vs full path, with a written plan logged on every run. Without visible
branching the system reads as a classifier. The demo must show both paths.

## D-009 — Deterministic Trust Report, not free-form generation

**Status:** Accepted

The Trust Report's statistics are computed deterministically and rendered from a
fixed template. More reliable for a live demo than a Gemini free-write, and it
guarantees "no metric without a sentence of meaning." A Gemini polish pass is a
future option, not the default.

## D-010 — REPAIR never fires on high-stakes

**Status:** Accepted

REPAIR & ALLOW delivers a corrected, labeled, cited answer — but only for
medium-stakes contradictions with a clean corpus correction. High-stakes always
quarantines so a human sees it. Reconciles "auto-correct is impressive" with
"human review is mandatory for high-stakes." Gated by `SENTINEL_ENABLE_REPAIR`
(the designated scope cut line).

## D-011 — Self-improvement via per-topic risk adjustment

**Status:** Accepted

`monitors.topic_risk_adjustment` raises the support bar for topics with rising
quarantine rates (capped at +0.15, with a sample floor). Adaptive but bounded
and recorded on `policy_snapshot` — predictable, not a black box.

## D-012 — CASA hero answers are scripted; everything else is Gemini

**Status:** Accepted

CASA returns a scripted wrong answer for the canonical demo questions (the
green-card "30-day" lie) so the hero scenario reproduces deterministically, and
calls Gemini for everything else. CASA is a prop; do not copy its prompt.

## D-013 — SSE bridges a synchronous loop via a worker thread

**Status:** Accepted

The Gemini SDK is synchronous. The streaming endpoint runs the orchestrator in a
thread and bridges its `emit` callback into an asyncio queue
(`api/ask.py`). Keeps the loop simple and testable while still streaming the
agent's visible decisions.
