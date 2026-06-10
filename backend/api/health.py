"""Liveness + readiness endpoints (also used by the container healthcheck)."""

from __future__ import annotations

from fastapi import APIRouter

from backend.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    """Report liveness and the active backend selection (no secrets)."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "sentinel",
        "corpus_backend": settings.corpus_backend,
        "store_backend": settings.store_backend,
        "llm_provider": settings.llm_provider,
        "tracing_enabled": settings.tracing_enabled,
    }
