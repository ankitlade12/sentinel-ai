# Known Issues

Accumulated non-obvious fixes across sessions. Format:

```
## [Category] — Short description
- **Error signature**: the message or symptom
- **Root cause**: what caused it
- **Resolution**: how to fix it
- **Confidence**: HIGH / MEDIUM / LOW
- **Date**: YYYY-MM-DD
```

---

## [LLM wiring] — Evals silently skipped after import refactor

- **Error signature**: hallucination/QA evals never appear on a verdict; no
  error surfaces (the eval try/except in `run_evals` swallows it).
- **Root cause**: `arize/evals.py` was changed to `from backend import llm` but
  the call sites still used the bare name `generate_structured`; ruff then
  removed the now-"unused" `llm` import, leaving a `NameError` that the eval
  loop's broad `except Exception` hid.
- **Resolution**: always call the LLM module-qualified (`llm.generate_structured`)
  AND keep the `from backend import llm` import. The integration test now asserts
  evals actually ran (regression guard in `test_sentinel_loop.py`).
- **Confidence**: HIGH
- **Date**: 2026-06-10

## [Tests] — `import backend` fails when running scripts directly

- **Error signature**: `ModuleNotFoundError: No module named 'backend'` running
  `python scripts/x.py`.
- **Root cause**: the project isn't installed in that interpreter; cwd isn't on
  `sys.path`.
- **Resolution**: run scripts via `uv run python scripts/x.py` (uv installs the
  project), or set `PYTHONPATH=.`.
- **Confidence**: HIGH
- **Date**: 2026-06-10
