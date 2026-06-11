"""Project-wide settings + the mock/live swap points.

Settings are read from the environment (loaded from ``.env`` via python-dotenv
at app startup). Two factories are the single places where Sentinel chooses
between hermetic and cloud-backed implementations — agents and API handlers
call ``get_corpus()`` / ``get_store()`` rather than importing implementations
directly:

- ``get_corpus()`` → trusted-corpus RAG (Vertex AI Vector Search, or in-memory mock)
- ``get_store()``  → quarantine + verdict store (Firestore, or in-memory mock)

This keeps the same agent code runnable both against full Google Cloud (the
demo + production path) and offline in CI (the hermetic test path).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.connectors.protocol import CorpusConnector
    from backend.connectors.store_protocol import QuarantineStore

CorpusChoice = Literal["vertex", "mock"]
StoreChoice = Literal["firestore", "mock"]
LLMProvider = Literal["vertex", "ai_studio"]


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{key} must be a float, got {raw!r}") from exc


class Settings(BaseModel):
    """Runtime settings. Held as a process-wide singleton by ``get_settings()``."""

    corpus_backend: CorpusChoice = Field(default="mock")
    store_backend: StoreChoice = Field(default="mock")

    # Reasoning — Gemini.
    llm_provider: LLMProvider = Field(default="vertex")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_api_key: str = Field(
        default="", description="Only used when llm_provider == 'ai_studio'."
    )

    # Google Cloud.
    google_cloud_project: str = Field(default="")
    google_cloud_location: str = Field(default="us-central1")
    embedding_model: str = Field(default="text-embedding-005")
    vertex_vector_index_endpoint: str = Field(default="")
    vertex_vector_deployed_index_id: str = Field(default="")
    firestore_prefix: str = Field(default="sentinel")

    # Arize Phoenix.
    phoenix_collector_endpoint: str = Field(default="")
    phoenix_api_key: str = Field(default="")
    phoenix_project_name: str = Field(default="sentinel")
    phoenix_mcp_endpoint: str = Field(default="")

    # Org policy — quarantine thresholds (the ORG sets these, not the agent).
    quarantine_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    hallucination_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    enable_repair: bool = Field(default=True)

    @property
    def tracing_enabled(self) -> bool:
        """Tracing is live when a Phoenix endpoint is configured."""
        return bool(self.phoenix_collector_endpoint)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton, parsed from env."""
    corpus = _env("SENTINEL_CORPUS", "mock").lower()
    if corpus not in ("vertex", "mock"):
        raise ValueError(f"SENTINEL_CORPUS must be 'vertex' or 'mock', got {corpus!r}")

    store = _env("SENTINEL_STORE", "mock").lower()
    if store not in ("firestore", "mock"):
        raise ValueError(f"SENTINEL_STORE must be 'firestore' or 'mock', got {store!r}")

    provider = _env("SENTINEL_LLM_PROVIDER", "vertex").lower()
    if provider not in ("vertex", "ai_studio"):
        raise ValueError(f"SENTINEL_LLM_PROVIDER must be 'vertex' or 'ai_studio', got {provider!r}")

    return Settings(
        corpus_backend=corpus,
        store_backend=store,
        llm_provider=provider,
        gemini_model=_env("SENTINEL_GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_api_key=_env("GEMINI_API_KEY"),
        google_cloud_project=_env("GOOGLE_CLOUD_PROJECT"),
        google_cloud_location=_env("GOOGLE_CLOUD_LOCATION", "us-central1"),
        embedding_model=_env("SENTINEL_EMBEDDING_MODEL", "text-embedding-005"),
        vertex_vector_index_endpoint=_env("VERTEX_VECTOR_INDEX_ENDPOINT"),
        vertex_vector_deployed_index_id=_env("VERTEX_VECTOR_DEPLOYED_INDEX_ID"),
        firestore_prefix=_env("SENTINEL_FIRESTORE_PREFIX", "sentinel"),
        phoenix_collector_endpoint=_env("PHOENIX_COLLECTOR_ENDPOINT"),
        phoenix_api_key=_env("PHOENIX_API_KEY"),
        phoenix_project_name=_env("PHOENIX_PROJECT_NAME", "sentinel"),
        phoenix_mcp_endpoint=_env("PHOENIX_MCP_ENDPOINT"),
        quarantine_threshold=_env_float("SENTINEL_QUARANTINE_THRESHOLD", 0.55),
        hallucination_threshold=_env_float("SENTINEL_HALLUCINATION_THRESHOLD", 0.5),
        enable_repair=_env_bool("SENTINEL_ENABLE_REPAIR", True),
    )


def get_corpus() -> CorpusConnector:
    """Return the configured trusted-corpus connector (the grounding source)."""
    settings = get_settings()
    match settings.corpus_backend:
        case "mock":
            from backend.connectors.mock_corpus import MockCorpusConnector

            return MockCorpusConnector()
        case "vertex":
            from backend.connectors.vertex_corpus import VertexCorpusConnector

            return VertexCorpusConnector()


def get_store() -> QuarantineStore:
    """Return the configured quarantine + verdict store."""
    settings = get_settings()
    match settings.store_backend:
        case "mock":
            from backend.connectors.mock_store import MockQuarantineStore

            return MockQuarantineStore()
        case "firestore":
            from backend.connectors.firestore_store import FirestoreQuarantineStore

            return FirestoreQuarantineStore()
