# Handoff

**Date:** 2026-06-10  ·  **Branch:** `main`  ·  Initial build of Sentinel.

## What landed

The full system end-to-end:

- **Contract** — Pydantic models for triage, claims, grounding, evals, verdicts,
  corpus, trust report, and SSE events (`backend/models/`).
- **The heart** — trusted-corpus RAG with a real Vertex path and a hermetic
  hashing-embedder mock; 7 vetted Riverside corpus documents
  (`backend/corpus/`, `backend/connectors/`).
- **The loop** — triage (written plan, light/full branching) → claim extraction →
  per-claim grounding → Phoenix evals → risk-history → graduated decide →
  repair-and-cite (`backend/agents/`), plus a Google ADK agent runtime.
- **Arize spine** — evals as a decision input, OpenInference tracing as the audit
  trail, monitors + Phoenix MCP as memory/self-improvement (`backend/arize/`).
- **CASA bot** (scripted hero lie + Gemini fallback), **Trust Report** generator,
  FastAPI + SSE API, Firestore + mock stores.
- **Dashboard** — Next.js live demo, quarantine queue with side-by-side sources,
  Trust Report (`frontend/`).
- **Docs** — PRD, ARCHITECTURE, DECISIONS, ARIZE, DESIGN, LOCAL_DEV, GCP_SETUP.

## Verification (re-run before any PR)

```bash
# Backend — hermetic, no cloud
SENTINEL_CORPUS=mock SENTINEL_STORE=mock uv run pytest      # 32 passing
uv run ruff check backend/ scripts/                         # clean
uv run ruff format --check backend/ scripts/

# Frontend
cd frontend && npm run typecheck && npm run build           # clean

# Types in sync
make types && git diff --exit-code frontend/types/generated.ts
```

Backend was verified with a lean venv (pydantic, numpy, pyyaml, fastapi,
sse-starlette, anyio, httpx, pytest); the full `uv sync --extra dev` pulls the
cloud SDKs (google-adk, google-genai, google-cloud-*, arize-phoenix,
openinference) needed for the live path.

## Next steps

1. `uv sync --extra dev` and run the live path against a real GCP project +
   Phoenix Cloud (`docs/GCP_SETUP.md`).
2. Provision the Vertex AI Vector Search managed index and `make index`.
3. Record the demo video (beat sheet in `sentinel-build-spec.md` §8).
4. Optional: seed a week of verdicts so the Trust Report + drift demo are full.
