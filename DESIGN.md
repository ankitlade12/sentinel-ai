# DESIGN — the triage and decide policy, in prose

This explains *why* Sentinel decides the way it does. The code is
`backend/agents/triage.py` and `backend/agents/decide.py`; this is the reasoning
behind it.

## Triage: how hard to check

For each (question, draft answer) Sentinel classifies three things:

- **Stakes** (low / medium / high) — does the answer touch a deadline, money,
  legal rights, health, immigration status, or eligibility? A Gemini structured
  call with a rubric. A wrong answer on any of these can cost someone their
  case, their benefits, or their status.
- **Specificity** (general info / specific claim) — does it assert a checkable
  particular (a date, amount, form number, rule)?
- **Coverage** (in-corpus / out-of-corpus) — an embedding-similarity check
  against the org's trusted documents. Coverage is informational; grounding is
  decisive.

Then it **writes a plan** and chooses a path:

- **Full path** — high stakes, *or* medium stakes with a checkable specific.
  Extract claims → ground-check each → run hallucination + QA-correctness evals →
  read risk history → decide.
- **Light path** — everything else (low stakes, no checkable claim). A toxicity
  glance, then allow.

The branching is the point. A fixed conveyor belt that runs the same checks on
every answer scores as a filter; an agent that decides *how hard to check based
on what's at stake* scores as an agent. The demo shows both paths.

## Grounding: why "not found" is risk

Each checkable claim is checked **only** against retrieved trusted passages —
never the agent's own knowledge, never the web. The judge returns supported,
contradicted, or not-found.

The crucial policy: **not-found is treated as risk, not as pass.** A confident
fabrication — "your I-90 must be filed within 30 days" — looks exactly like a
true statement the corpus happens not to mention. If we passed unsupported
specifics, we would pass the fabrications. So an unsupported specific on a
high-stakes topic is held. This is the hardest and most important design
choice, and tuning it so the agent doesn't quarantine the harmless is the real
engineering work.

## Decide: graduated, human-in-the-loop

Pure policy over the computed signals (`decide.py`, fully unit-tested):

- **ALLOW** — every checkable claim is supported above the confidence bar and
  evals are clean. The original answer is delivered.
- **REPAIR & ALLOW** — a claim is contradicted but a correction is cleanly
  derivable from the corpus. The agent drafts a corrected answer, **labels it as
  corrected**, attaches the citation, and delivers it. Never fires on
  high-stakes (those always reach a human). Gated by `SENTINEL_ENABLE_REPAIR`.
- **QUARANTINE** — a claim is contradicted or unsupported on a high-stakes
  topic, the hallucination eval is over threshold, or the safety check fails.
  The answer is held; the user receives an honest fallback ("a staff member will
  follow up"), and the item lands in the director's queue with the claim and the
  contradicting source side by side.

Two rules are absolute: **never silently rewrite without labeling**, and **never
block without telling the user something true.** The dignity of both the end
user and the org's staff is a design requirement.

## Thresholds are the org's, and they adapt

`SENTINEL_QUARANTINE_THRESHOLD` and `SENTINEL_HALLUCINATION_THRESHOLD` are policy
the clinic sets, not the agent. On top of that, the self-improvement loop
(`arize/monitors.py`) adds a per-topic `risk_adjustment`: a topic that has been
failing more often lately raises the support bar, so the agent holds borderline
answers on a drifting topic more readily. Memory makes the policy adaptive
without making it unpredictable — every effective threshold is recorded on the
verdict's `policy_snapshot`.

## Ethics

Sentinel reduces risk; it does not eliminate it. The Trust Report says so on
every page. Human review is mandatory for high-stakes answers. The corpus-gap
analysis turns "we don't cover this" into a feature — the report tells the
director which topics their corpus is missing rather than letting the agent
guess.
