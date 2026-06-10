# Sentinel — GitHub Copilot Instructions

Mirrors `.claude/claude.md`. Read `docs/Sentinel_PRD.md`, `docs/ARCHITECTURE.md`,
`docs/DECISIONS.md`, and `docs/ARIZE.md` before non-trivial work.

## What this is

A guardian agent that watches a legal-aid chatbot (CASA) and catches
confidently-wrong answers before they reach a vulnerable person. Loop:
**triage → tools (claims · grounding · evals · risk history) → decide → report**,
producing a graduated verdict (allow / repair-and-cite / quarantine) and a
Phoenix trace as the audit trail.

## Do

- Route all reasoning through `backend/llm.py` (Gemini, temperature 0), called
  module-qualified (`llm.generate_structured`) so it is stubbable in tests.
- Ground claims against the **trusted corpus only** (`agents/grounding.py`).
  Treat "not found" as risk, not pass.
- Keep `agents/decide.py` pure (no LLM/network) — it is the unit-tested policy.
- Add Pydantic models for every boundary; regenerate TS with `make types`.
- Lazy-import cloud SDKs (google-genai, google-adk, google-cloud-*, phoenix,
  openinference) inside functions, so the package imports in the hermetic tier.
- Use `from __future__ import annotations`, full type hints, Google docstrings,
  `pathlib`, stdlib logging, PEP 695 generics, `StrEnum` for closed sets.

## Don't

- Don't check claims against the web.
- Don't return free-text agent output — use a Pydantic schema.
- Don't auto-repair high-stakes answers (they always reach a human).
- Don't hand-write frontend API types (they're generated).
- Don't add Claude or any AI tool as an author/co-author/contributor in commits.

## Verify

`make lint` (ruff + mypy) and `make test` (pytest) before claiming done. No live
LLM and no network in unit/contract/integration tiers.

## Key models (backend/models/)

`TriageVerdict` · `SentinelPlan` · `Claim` · `GroundingResult` (+ `SourcePassage`)
· `EvalResult` · `SentinelVerdict` · `TrustReport`.
