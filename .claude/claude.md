# Sentinel — Project Context for Claude Code

## What This Project Is

Sentinel is a **guardian agent** that watches a legal-aid chatbot (CASA) and
catches confidently-wrong answers before they reach a vulnerable person. For
every draft answer it runs a loop — **triage → tools → decide → report** — and
returns a graduated verdict (allow / repair-and-cite / quarantine) with a full
Arize Phoenix trace as the audit trail.

It is NOT a content moderator and NOT a general fact-checker. It catches the
*factually wrong but fluent* answer that toxicity/PII filters miss, by grounding
each atomic claim against the org's **trusted corpus only** — never the web.

**Read these first, in order:**

1. `docs/Sentinel_PRD.md` — the product spec
2. `docs/ARCHITECTURE.md` — one-page module map
3. `docs/DECISIONS.md` — engineering decisions (D-001…)
4. `docs/ARIZE.md` — how Phoenix is load-bearing
5. `DESIGN.md` — the triage/decide policy in prose

PRD wins on product intent; DECISIONS wins on implementation mechanism.

## Tech Stack

### Backend (Python 3.12, uv-managed)

- **Framework**: FastAPI + SSE (sse-starlette)
- **Agent runtime**: Google ADK (`agents/adk_agent.py`) + a deterministic
  orchestrator (`agents/sentinel.py`) that share the same step modules
- **Reasoning**: Gemini via the Google GenAI SDK (Vertex AI), temperature 0,
  structured output (`backend/llm.py`)
- **Evals / traces / monitors**: Arize Phoenix via OpenInference + Phoenix MCP
  (`backend/arize/`)
- **Corpus RAG**: Vertex AI embeddings + Vector Search; deterministic hashing
  embedder + in-memory cosine for the hermetic path
- **Store**: Firestore (in-memory mock for CI)
- **Validation**: Pydantic v2 for every boundary crossing
- **Lint/format**: ruff. **Types**: mypy strict. **Tests**: pytest.

### Frontend (Node 20+)

- **Next.js 15** (App Router) + React 18 + TypeScript 5, Tailwind + shadcn-style
  primitives, lucide-react. Types are **generated** from Pydantic via
  `make types` — never hand-write API types.

## Architecture Principles — INTERNALIZE

1. **Corpus is the org's voice, not the internet's.** Never web search.
2. **"Not found in corpus" is risk, not pass** (`agents/grounding.py`).
3. **Structured outputs everywhere**; frontend renders typed components.
4. **Thresholds are org policy** (`agents/decide.py` is pure, unit-tested).
5. **Human review mandatory for high-stakes**; REPAIR never fires on high-stakes.
6. **Never silently rewrite; never block without telling the user something true.**
7. **Arize is structural** in three roles (`backend/arize/`, `docs/ARIZE.md`).
8. **Mock ⇄ live parity** via `config.get_corpus()` / `get_store()`.
9. **Triage branching is the agent signal** — visible plans, two paths.

## Code Conventions

### Python

- **uv** only (`uv add`, `uv run`, `uv sync --extra dev`). No pip/poetry, no
  requirements.txt. `pyproject.toml` is the single source for deps + tool config.
- `from __future__ import annotations`; type hints on ALL signatures; Google-style
  docstrings; `pathlib.Path`; stdlib `logging`, never `print`.
- Pydantic models for everything crossing a boundary. `StrEnum` for closed sets.
- PEP 695 generics (`def f[T: BaseModel](...)`), matching the house style.
- Cloud SDKs (google-genai, google-adk, google-cloud-*, phoenix, openinference)
  are **lazy-imported** inside functions so the package imports cleanly in the
  hermetic test tier. If you call an LLM, go through `backend/llm.py` and call it
  module-qualified (`llm.generate_structured`) so it is stubbable in tests.
- Max line length 100 (formatter-enforced; E501 ignored in lint).

### TypeScript

- Functional components, `interface` for shapes, no `any`.
- API types are GENERATED (`make types`) — do not hand-write `SentinelVerdict`
  etc.; they will drift.
- `@/` path alias; client components marked `"use client"`.

### Git

- Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
  One logical change per commit.
- **No author/coauthor tags in commit messages.** Do not add Claude or any AI
  tool as an author, co-author, or contributor.

## Testing

- Tiers: `unit` (models, decide, monitors), `contract` (connector/store
  protocols), `integration` (full loop + FastAPI, stubbed LLM), `live` (real
  GCP/Phoenix). Markers registered in `pyproject.toml`.
- No live LLM and no network in any hermetic tier. The stub lives in
  `backend/tests/conftest.py` and reproduces the hero scenario deterministically.
- Run before claiming done: `make lint` and `make test`.

## When In Doubt

1. Re-read the relevant PRD/ARCHITECTURE/DECISIONS section.
2. Check `.claude/known_issues.md` for prior fixes.
3. Evidence over vibes — every grounding verdict cites a source; every change is
   verified by running `make test`.
