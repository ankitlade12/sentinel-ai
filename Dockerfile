# Sentinel backend — FastAPI + SSE on Cloud Run.
# Root Dockerfile (build context = repo root) so `gcloud run deploy --source .`
# picks it up. Uses uv for reproducible installs from pyproject + uv.lock.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv: standalone binary, no pip bootstrap needed.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (layer caches on lockfile changes only).
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

# App code (corpus markdown is re-included via .dockerignore).
COPY backend/ ./backend/

# Cloud Run injects PORT (default 8080); default keeps local docker parity.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", ".venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
