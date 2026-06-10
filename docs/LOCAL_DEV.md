# Local development

## Prerequisites

- Python 3.12 (managed by `uv`)
- Node 20+
- `uv`, and for the full path the `gcloud` CLI

## Hermetic mode (no cloud, no credentials)

The fastest way to run the backend and the whole test suite offline. Uses the
in-memory corpus + store and a stubbed LLM in tests.

```bash
uv sync --extra dev
SENTINEL_CORPUS=mock SENTINEL_STORE=mock make test    # 32 tests, no network
make lint                                             # ruff + mypy
```

To run the API against the hermetic backends (the agent loop still needs Gemini
for real grounding — set `SENTINEL_LLM_PROVIDER=ai_studio` + `GEMINI_API_KEY`,
or `vertex` + ADC):

```bash
SENTINEL_CORPUS=mock SENTINEL_STORE=mock make dev-backend
```

## Full mode (Google Cloud + Phoenix)

```bash
cp .env.example .env        # fill GOOGLE_CLOUD_PROJECT, PHOENIX_API_KEY, …
uv sync --extra dev
gcloud auth application-default login
make index                  # build/refresh the corpus vector index
make dev-backend            # terminal A → http://localhost:8000  (/api/docs)
make dev-frontend           # terminal B → http://localhost:3000
```

See [`GCP_SETUP.md`](GCP_SETUP.md) for project + Vertex + Firestore setup.

## The dashboard

```bash
cd frontend
npm install
npm run dev                 # http://localhost:3000 (proxies /api → :8000)
```

The dashboard calls `/api/*` same-origin; Next.js proxies to the backend via
`SENTINEL_API_TARGET` (default `http://localhost:8000`).

## Common tasks

```bash
make demo      # run the canonical scenarios through CASA → Sentinel
make types     # regenerate frontend/types/generated.ts from Pydantic models
make format    # ruff --fix + format
make test      # pytest (unit + contract + integration)
```

## Test tiers

```bash
uv run pytest -m unit          # models, decision policy, monitors
uv run pytest -m contract      # corpus + store protocol conformance
uv run pytest -m integration   # full loop + FastAPI (stubbed LLM)
uv run pytest -m live          # hits real GCP/Phoenix; needs credentials
```

## Troubleshooting

- **`RuntimeError: …requires GOOGLE_CLOUD_PROJECT`** — you're on the Vertex
  provider without a project. Set it, or use `SENTINEL_LLM_PROVIDER=ai_studio`.
- **App startup is slow on first run with `SENTINEL_CORPUS=vertex`** — it embeds
  the corpus via Vertex at startup. Use `mock` for offline work.
- **No Phoenix traces** — `PHOENIX_COLLECTOR_ENDPOINT` / `PHOENIX_API_KEY` not
  set. Tracing degrades to no-ops; the agent still runs.
