# Sentinel — Product Requirements

The canonical, abridged product spec for Sentinel.

## 1. Thesis

Enterprise AI gets million-dollar safety teams; the legal-aid clinic answering a
refugee's visa question gets nothing. Sentinel is the safety layer for everyone
else: an agent that watches another AI, catches the confident-but-wrong answer
before it reaches a vulnerable person, and explains what it did in language a
nonprofit director can read.

The failure mode Sentinel owns is the one content moderation cannot see: a
polite, fluent, plausible, **factually wrong** answer — a wrong filing deadline,
a wrong benefit threshold, a wrong eligibility rule.

## 2. The three components

- **CASA Bot** — "Community Advice & Support Assistant," a deliberately imperfect
  demo legal-aid chatbot for a fictional clinic (Riverside Community Legal Aid).
  A prop, intentionally prone to hallucinating specifics. Gives Sentinel
  something real to catch.
- **Sentinel Agent** — the product. Intercepts every CASA answer and runs the
  loop (§3). 80% of the effort is here.
- **Director Dashboard** — the non-technical interface: live demo, quarantine
  queue with side-by-side sources, and the weekly Trust Report.

## 3. The agent loop

1. **Triage** — classify stakes / specificity / coverage and write a plan;
   branch to a light or full path.
2. **Tools** — claim extraction → trusted-corpus grounding (supported /
   contradicted / not-found) → Phoenix evals → topic risk history.
3. **Decide** — allow / repair-and-cite / quarantine. Org thresholds,
   human-in-the-loop, "not-found is risk."
4. **Report** — one Phoenix trace + one persisted verdict; the Trust Report is
   generated from the accumulated data.

See [`../DESIGN.md`](../DESIGN.md) for the policy in prose.

## 4. The trusted corpus

6–10 vetted documents per org (USCIS form instructions, a state benefits page, a
tenant-rights chapter, the clinic's approved FAQ). Chunked, embedded with Vertex
AI, retrieved from Vertex AI Vector Search. Every chunk carries source metadata
(document, URL, last-verified date) so every grounding verdict cites its source
and the quarantine view shows the claim next to the official text. The corpus is
the org's voice, not the internet's.

## 5. The Trust Report

A weekly, one-page, plain-English document for a non-technical director. Fixed
template, no metric without a sentence of meaning. Sections: headline counts,
what was caught (with sources), trend (incl. a stale-corpus nudge), riskiest and
safest topics, corpus gaps. States plainly that Sentinel reduces risk but does
not eliminate it and that human review is mandatory for high-stakes answers.

## 6. Success criteria (hackathon)

- Reads as an **agent** (visible triage branching + written plans + two-path demo).
- **Arize is load-bearing** in three structural roles ([`ARIZE.md`](ARIZE.md)).
- Answers the "why not built-in safety?" question in the first 25 seconds (the
  confident-wrong-fact distinction).
- A judge can run `make test` (hermetic) or `docker compose up` (full) and read a
  repo that respects their time.

## 7. Non-goals

- Not a chatbot, not a general fact-checker, not a content moderator.
- Never checks claims against the open web.
- Does not replace human review for high-stakes matters.
