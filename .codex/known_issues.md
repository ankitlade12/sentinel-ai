# Known Issues (Codex)

Shared log with `.claude/known_issues.md` — keep them in sync. Same format:
error signature · root cause · resolution · confidence · date.

## [LLM wiring] — Evals silently skipped after import refactor
- Call the LLM module-qualified (`llm.generate_structured`) and keep the
  `from backend import llm` import; a bare name + ruff autoremoval left a
  `NameError` hidden by the eval try/except. Regression-guarded in
  `backend/tests/integration/test_sentinel_loop.py`. (2026-06-10)

## [Scripts] — `import backend` fails on direct `python scripts/x.py`
- Run via `uv run python scripts/x.py` or set `PYTHONPATH=.`. (2026-06-10)
