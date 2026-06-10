"""FastAPI application entrypoint for Sentinel.

``create_app()`` is the factory used by uvicorn and the tests. Per the service
wiring pattern, the corpus connector, quarantine store, CASA bot, and Sentinel
agent are constructed once at startup and stored on ``app.state``; route handlers
retrieve them via the dependencies in ``backend/api/deps.py``.

``.env`` is loaded at import time so env vars are populated before any module
that reads ``os.environ`` at import runs, and Phoenix tracing is registered once
at startup so every Gemini/ADK call in the loop is captured.
"""

from __future__ import annotations

import logging
import os
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(override=False)

from backend.agents.sentinel import SentinelAgent  # noqa: E402
from backend.api import agent, ask, health, quarantine, report  # noqa: E402
from backend.arize.tracing import setup_tracing  # noqa: E402
from backend.casa.bot import CasaBot  # noqa: E402
from backend.config import get_corpus, get_settings, get_store  # noqa: E402

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("SENTINEL_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _package_version() -> str:
    try:
        return version("sentinel")
    except PackageNotFoundError:
        return "0.1.0"


def _cors_origins() -> list[str]:
    raw = os.environ.get("SENTINEL_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """Construct the Sentinel FastAPI app with all services wired to app.state."""
    _configure_logging()
    setup_tracing()

    app = FastAPI(
        title="Sentinel",
        description="A guardian agent that catches confidently-wrong AI answers.",
        version=_package_version(),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings = get_settings()
    app.state.settings = settings
    app.state.corpus = get_corpus()
    app.state.store = get_store()
    app.state.casa = CasaBot()
    app.state.agent = SentinelAgent(
        corpus=app.state.corpus,
        store=app.state.store,
        settings=settings,
    )
    logger.info(
        "sentinel up: corpus=%s store=%s llm=%s tracing=%s",
        settings.corpus_backend,
        settings.store_backend,
        settings.llm_provider,
        settings.tracing_enabled,
    )

    # Health is exposed both unprefixed (container probe) and under /api.
    app.include_router(health.router)
    app.include_router(health.router, prefix="/api")
    app.include_router(ask.router, prefix="/api")
    app.include_router(quarantine.router, prefix="/api")
    app.include_router(report.router, prefix="/api")
    app.include_router(agent.router, prefix="/api")
    return app


app = create_app()
