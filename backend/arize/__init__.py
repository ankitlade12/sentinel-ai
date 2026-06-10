"""The Arize spine — Phoenix made structural, not decorative.

Three distinct, load-bearing roles (build spec Section 4):

1. **Evals as a decision input** (``evals.py``) — the quarantine decision consumes
   Phoenix hallucination + QA-correctness + toxicity scores as first-class
   signals, with the retrieved corpus passages passed as ground-truth context.
2. **Tracing as the audit trail** (``tracing.py``) — every agent run is one
   OpenInference/Phoenix trace: triage, plan, each tool call, eval scores, the
   decision. When an AI-accountability rule asks the clinic to prove oversight,
   the trace *is* the answer.
3. **Monitoring as memory** (``monitors.py`` + ``mcp.py``) — the agent reads back
   its own per-topic quarantine rates (via the Phoenix MCP server at runtime, or
   the verdict store) so its thresholds adapt. This is the self-improvement loop.
"""
