# Sentinel backend — FastAPI + SSE on Cloud Run.
# Uses uv for reproducible, fast installs from pyproject + uv.lock.
FROM python:3.12-slim AS base

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

# App code.
COPY backend/ ./backend/

# Cloud Run injects PORT; default to 8000 for local/compose parity.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uv run --no-dev uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
