"""Smoke-test the Phoenix tracing connection.

Registers tracing via the same code path the app uses, emits one span, and
force-flushes it to Phoenix. If it succeeds, a `sentinel` project with a
`sentinel.connectivity_test` trace appears in your Phoenix space.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(override=False)

from backend.arize.tracing import agent_span, setup_tracing  # noqa: E402


def main() -> None:
    active = setup_tracing()
    print(f"setup_tracing active={active}")
    if not active:
        print("Tracing is not active — check PHOENIX_COLLECTOR_ENDPOINT / PHOENIX_API_KEY.")
        return

    with agent_span("sentinel.connectivity_test", {"smoke": True}) as span:
        span.set_attribute("sentinel.note", "hello from the connectivity smoke test")
        print(f"emitted span trace_id={span.trace_id}")
        if span.trace_url:
            print(f"trace_url={span.trace_url}")

    # Force the batch processor to export before the process exits.
    from opentelemetry import trace

    provider = trace.get_tracer_provider()
    flush = getattr(provider, "force_flush", None)
    if callable(flush):
        flush()
    print("flushed — check the 'sentinel' project in Phoenix")


if __name__ == "__main__":
    main()
