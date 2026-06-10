# Sentinel

**A guardian agent that protects vulnerable communities from confidently-wrong AI.**
*Google Cloud Rapid Agent Hackathon — Arize Track.*

Enterprise AI gets million-dollar safety teams. The legal-aid clinic answering a
refugee's visa question gets nothing. Sentinel is the safety layer for everyone
else — an agent that watches another AI, catches the confident lie before it
reaches a vulnerable person, and explains what it did in language a nonprofit
director can read.

Model safety filters catch toxicity, PII, and policy violations. They do **not**
catch a polite, fluent, plausible, **factually wrong** answer — a wrong filing
deadline, a wrong benefit threshold, a wrong eligibility rule. That failure mode
is invisible to content moderation and catastrophic to the person who trusts it.
**Sentinel exists for exactly that failure mode.**

---

## What it does

```
┌──────────────┐   every    ┌────────────────────────┐   verdict   ┌──────────────┐
│   CASA Bot   │   answer   │     SENTINEL AGENT      │  + trace    │   Director   │
│ (demo legal- │ ─────────▶ │  TRIAGE → TOOLS →       │ ──────────▶ │  Dashboard   │
│  aid chatbot)│            │  DECIDE → REPORT        │             │ + Trust Rpt  │
└──────────────┘            └───────────┬────────────┘             └──────────────┘
       ▲                                │  tools
   end user asks            ┌───────────┴─────────────────────────────┐
   a question               │ • Trusted-corpus RAG grounding (Vertex)  │
                            │ • Phoenix evals (hallucination/QA/tox)    │
                            │ • Risk-history (monitoring-as-memory)     │
                            │ • Quarantine store (Firestore)            │
                            └──────────────────────────────────────────┘
```

For **every** answer the CASA demo bot drafts, Sentinel runs a four-step loop:

1. **Triage** — classify stakes / specificity / corpus-coverage and *write a
   plan*. Low-stakes inputs take a light path; high-stakes checkable claims take
   the full path. (This branching is what makes it an agent, not a filter.)
2. **Tools** — decompose the answer into atomic claims, ground-check each against
   the org's *trusted corpus only*, run Phoenix evals, and read the topic's risk
   history.
3. **Decide** — a graduated, human-in-the-loop verdict: **allow**, **repair &
   cite**, or **quarantine**. Thresholds are org policy, not the agent's. "Not
   found in the corpus" is treated as risk, not as pass.
4. **Report** — the whole run is one Phoenix trace and one persisted verdict; the
   weekly Trust Report is generated from that accumulated data.

The single most persuasive screen shows the bot's claim **side-by-side** with the
official source that contradicts it.

---

## Quick start

### Hermetic (no cloud, for tests + offline dev)

```bash
uv sync --extra dev
SENTINEL_CORPUS=mock SENTINEL_STORE=mock make test     # 32 tests, no network
```

### Full Google Cloud + Arize (the demo path)

```bash
cp .env.example .env          # fill GOOGLE_CLOUD_PROJECT, PHOENIX_API_KEY, …
uv sync --extra dev
gcloud auth application-default login
make index                    # build/refresh the trusted-corpus vector index
make dev-backend              # FastAPI + SSE on :8000   (terminal A)
make dev-frontend             # Next.js dashboard on :3000 (terminal B)
```

Or one command with containers:

```bash
cp .env.example .env
docker compose up -d --build   # backend :8000, dashboard :3000
```

See [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) and [`docs/GCP_SETUP.md`](docs/GCP_SETUP.md).

---

## Arize is load-bearing, not decorative

Phoenix is structural in three distinct ways — see [`docs/ARIZE.md`](docs/ARIZE.md)
and the [`backend/arize/`](backend/arize/) module:

1. **Evals as a decision input** — the quarantine decision *consumes* Phoenix
   hallucination + QA-correctness scores ([`arize/evals.py`](backend/arize/evals.py)),
   with corpus passages as ground-truth context. Not an after-the-fact log.
2. **Tracing as the audit trail** — every run is one OpenInference/Phoenix trace
   ([`arize/tracing.py`](backend/arize/tracing.py)). When an AI-accountability rule
   asks the clinic to "prove oversight," the trace *is* the answer.
3. **Monitoring as memory** — the agent reads back its own per-topic quarantine
   rates ([`arize/monitors.py`](backend/arize/monitors.py),
   [`arize/mcp.py`](backend/arize/mcp.py)) and adapts its thresholds. The
   self-improvement loop the track rewards.

---

## Read first

- [`docs/Sentinel_PRD.md`](docs/Sentinel_PRD.md) — the product spec
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — one-page module map
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — engineering decisions log
- [`docs/ARIZE.md`](docs/ARIZE.md) — the three structural Arize roles
- [`DESIGN.md`](DESIGN.md) — the triage / decide policy in prose

## Tech stack

| Layer | Choice |
|---|---|
| Agent runtime | **Google ADK** (`backend/agents/adk_agent.py`) + a deterministic orchestrator |
| Reasoning | **Gemini** via the Google GenAI SDK (Vertex AI), structured output |
| Evals / traces / monitors | **Arize Phoenix** via OpenInference + Phoenix MCP |
| Corpus RAG | **Vertex AI** embeddings + Vector Search (hermetic mock for CI) |
| Quarantine store | **Firestore** (in-memory mock for CI) |
| API | FastAPI + SSE |
| Dashboard | Next.js + Tailwind |

## Developer workflow

```
make setup     make index    make demo      make test
make lint      make format   make types     make dev-backend / dev-frontend
make docker-up
```

## Repository layout

```
sentinel/
├── backend/
│   ├── models/        ← Pydantic contract (triage, claim, grounding, eval, verdict, …)
│   ├── connectors/    ← CorpusConnector + QuarantineStore protocols (mock + Vertex/Firestore)
│   ├── corpus/        ← the org's vetted trusted documents
│   ├── agents/        ← the loop: triage · claim_extractor · grounding · decide · repair · sentinel
│   │   └── adk_agent  ← Google ADK runtime + function tools
│   ├── arize/         ← evals (decision input) · tracing (audit) · monitors + mcp (memory)
│   ├── casa/          ← the demo legal-aid bot (a prop)
│   ├── reports/       ← the Trust Report generator
│   ├── api/           ← FastAPI app + SSE endpoints
│   └── tests/         ← unit · contract · integration
├── frontend/          ← Next.js director dashboard
├── scripts/           ← index_corpus · eval_scenarios · generate_typescript_types
└── docs/              ← PRD · ARCHITECTURE · DECISIONS · ARIZE · setup
```

## License

MIT — see [`LICENSE`](LICENSE). Built for the people enterprise AI safety forgot.
