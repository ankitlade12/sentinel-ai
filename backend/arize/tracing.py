"""Role 2 — Tracing as the audit trail (OpenInference → Phoenix).

``setup_tracing()`` registers the Phoenix OTel exporter and the OpenInference
auto-instrumentors for Google GenAI, Google ADK, and Vertex AI, so every Gemini
call inside the loop is captured without per-call wiring. ``agent_span()`` opens
one span per Sentinel run that all tool calls nest under — that span is the
compliance artifact, and its id deep-links into Phoenix.

Everything here is defensive: tracing must never crash the request path. If
Phoenix is not configured or a dependency is missing, calls degrade to no-ops.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from backend.config import get_settings

logger = logging.getLogger(__name__)

_TRACING_ACTIVE = False


def setup_tracing() -> bool:
    """Idempotently wire Phoenix tracing + OpenInference instrumentors.

    Returns True when tracing is live. Safe to call at every app startup.
    """
    global _TRACING_ACTIVE
    if _TRACING_ACTIVE:
        return True
    settings = get_settings()
    if not settings.tracing_enabled:
        logger.info("tracing: disabled (no PHOENIX_COLLECTOR_ENDPOINT)")
        return False
    try:
        from phoenix.otel import register

        # Phoenix Cloud's OTLP HTTP ingest path is <collector>/v1/traces. Passing
        # an explicit endpoint skips Phoenix's auto-append, so we add it ourselves
        # (otherwise the exporter POSTs to the UI base and gets a 405).
        endpoint = settings.phoenix_collector_endpoint.rstrip("/")
        if not endpoint.endswith("/v1/traces"):
            endpoint = f"{endpoint}/v1/traces"

        tracer_provider = register(
            project_name=settings.phoenix_project_name,
            endpoint=endpoint,
            auto_instrument=False,  # we attach the Google-stack instrumentors explicitly
        )
        _instrument(tracer_provider)
        _TRACING_ACTIVE = True
        logger.info(
            "tracing: Phoenix active project=%s endpoint=%s",
            settings.phoenix_project_name,
            settings.phoenix_collector_endpoint,
        )
        return True
    except Exception:  # pragma: no cover - depends on optional cloud deps
        logger.warning("tracing: setup failed; continuing without tracing", exc_info=True)
        return False


def _instrument(tracer_provider: Any) -> None:
    """Attach the Google-stack OpenInference instrumentors, ignoring any missing."""
    for module_path, class_name in (
        ("openinference.instrumentation.google_genai", "GoogleGenAIInstrumentor"),
        ("openinference.instrumentation.google_adk", "GoogleADKInstrumentor"),
        ("openinference.instrumentation.vertexai", "VertexAIInstrumentor"),
    ):
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)().instrument(tracer_provider=tracer_provider)
            logger.info("tracing: instrumented %s", class_name)
        except Exception:  # pragma: no cover - optional per instrumentor
            logger.debug("tracing: %s unavailable", class_name)


@dataclass
class SpanHandle:
    """A thin handle over the active run span (or a no-op when tracing is off)."""

    trace_id: str | None = None
    trace_url: str | None = None
    _span: Any = field(default=None, repr=False)

    def set_attribute(self, key: str, value: Any) -> None:
        if self._span is not None:
            with contextlib.suppress(Exception):  # pragma: no cover - defensive
                self._span.set_attribute(key, value)


def _trace_url(trace_id: str | None) -> str | None:
    if not trace_id:
        return None
    settings = get_settings()
    base = settings.phoenix_collector_endpoint.rstrip("/")
    if not base:
        return None
    return f"{base}/projects/{settings.phoenix_project_name}/traces/{trace_id}"


@contextlib.contextmanager
def agent_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[SpanHandle]:
    """Open one span for a Sentinel run; all tool calls nest under it.

    Yields a :class:`SpanHandle` carrying the trace id + deep link, which are
    persisted onto the verdict so the dashboard can link to the Phoenix trace.
    """
    if not _TRACING_ACTIVE:
        yield SpanHandle()
        return
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("sentinel")
        with tracer.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                span.set_attribute(key, value)
            ctx = span.get_span_context()
            trace_id = format(ctx.trace_id, "032x") if ctx and ctx.trace_id else None
            yield SpanHandle(trace_id=trace_id, trace_url=_trace_url(trace_id), _span=span)
    except Exception:  # pragma: no cover - defensive
        logger.debug("tracing: agent_span failed; using no-op", exc_info=True)
        yield SpanHandle()


def record_evals(span: SpanHandle, evals: list[Any]) -> None:
    """Annotate the run span with each eval label + score (visible in Phoenix)."""
    for e in evals:
        span.set_attribute(f"eval.{e.kind.value}.label", e.label)
        span.set_attribute(f"eval.{e.kind.value}.score", float(e.score))
