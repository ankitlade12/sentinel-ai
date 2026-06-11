# Architecture

One page. Where to look for what, the module map, and the non-negotiable
principles. For product intent see the [README](../README.md); for engineering
decisions see [`DECISIONS.md`](DECISIONS.md).

## Where to look

| You want to understand… | Look at |
|---|---|
| The data contract | `backend/models/` |
| How a question is judged | `backend/agents/sentinel.py` (the loop) |
| The grounding catch mechanism | `backend/agents/grounding.py` + `backend/connectors/` |
| The decision policy | `backend/agents/decide.py` + [`DECISIONS.md`](DECISIONS.md) |
| Arize / Phoenix | `backend/arize/` ([`ARIZE.md`](ARIZE.md)) |
| The agent runtime | `backend/agents/adk_agent.py` |
| The API | `backend/api/` |
| The dashboard | `frontend/` |

## The loop (one run)

```
question + CASA draft
        │
        ▼
  TRIAGE  ── triage.py ──▶ SentinelPlan (stakes · specificity · coverage · path · written plan)
        │
   light │ full
        ▼
  TOOLS   ── claim_extractor.py ─▶ claims
          ── grounding.py ───────▶ GroundingResult per claim  (supported/contradicted/not_found)
          ── arize/evals.py ─────▶ hallucination + QA-correctness (light path: toxicity)
          ── arize/monitors.py ──▶ risk_adjustment for this topic
        ▼
  DECIDE  ── decide.py ──▶ allow | repair_allow | quarantine   (org thresholds)
        │                    └─ repair.py drafts a cited correction
        ▼
  REPORT  ── one Phoenix trace (arize/tracing.py) + one persisted SentinelVerdict (store)
```

Everything inside `agent_span()` is one trace. Every Gemini call is auto-traced
by the OpenInference GenAI instrumentor.

## Module layout

```
backend/
├── models/        Pydantic contract. Every boundary crossing is validated.
├── connectors/    CorpusConnector + QuarantineStore protocols; mock + Vertex/Firestore impls.
├── corpus/        The org's vetted trusted documents + loader/chunker.
├── vectorstore/   Embedders (Vertex + deterministic hashing) + cosine.
├── agents/        triage · claim_extractor · grounding · decide · repair · sentinel (orchestrator)
│   ├── adk_agent  Google ADK LlmAgent runtime (the code-owned runtime the track requires)
│   ├── tools/     ADK function tools wrapping the step modules
│   └── prompts/   System prompts as markdown
├── arize/         evals (decision input) · tracing (audit) · monitors + mcp + phoenix_mcp_server (memory)
├── casa/          The demo legal-aid bot (a prop, intentionally imperfect)
├── reports/       The Trust Report generator
├── api/           FastAPI app + SSE endpoints
└── tests/         unit · contract · integration
```

## Non-negotiable principles

1. **The corpus is the org's voice, not the internet's.** Sentinel never checks
   claims against the web. No-coverage is a quarantine, not a guess.
2. **"Not found" is risk, not pass.** An unsupported specific on a high-stakes
   topic is the confident fabrication we exist to catch (`grounding.py`).
3. **Structured outputs everywhere.** Every agent output is Pydantic-validated;
   the frontend renders typed components from generated TS (`make types`).
4. **Thresholds are org policy.** `decide.py` is pure policy over computed
   signals — fully unit-testable, no LLM, no network.
5. **Human review is mandatory for high-stakes.** REPAIR never fires on
   high-stakes; those always reach a person.
6. **Never silently rewrite; never block without telling the user something
   true.** REPAIR labels + cites; QUARANTINE returns an honest fallback.
7. **Arize is structural** (three roles — [`ARIZE.md`](ARIZE.md)).
8. **Mock ⇄ live parity.** The same agent code runs against hermetic mocks
   (CI/offline) and full Google Cloud (demo/prod); the swap point is
   `config.get_corpus()` / `get_store()`.

## Testing

- **unit** — models, decision policy, monitors. Fast, isolated, no LLM.
- **contract** — `CorpusConnector` / `QuarantineStore` conformance (mock + live).
- **integration** — the full loop + the FastAPI surface, with a stubbed LLM
  (`backend/tests/conftest.py`) so the hero scenario is reproduced deterministically.

No live LLM and no network in any hermetic tier.
