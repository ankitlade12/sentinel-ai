# Sentinel — Complete Build Specification
### A guardian agent that protects vulnerable communities from confidently-wrong AI
*Google Cloud Rapid Agent Hackathon — Arize Track*

---

## 1. The One-Line Thesis

Enterprise AI gets million-dollar safety teams. The legal-aid clinic answering a refugee's visa question gets nothing. Sentinel is the safety layer for everyone else — an agent that watches another AI, catches the confident lie before it reaches a vulnerable person, and explains what it did in language a nonprofit director can read.

The critical distinction Sentinel owns (and the answer to "why not built-in safety?"):
model safety filters catch toxicity, PII, and policy violations. They do **not** catch a
polite, fluent, plausible, **factually wrong** answer — a wrong filing deadline, a wrong
benefit eligibility rule, a wrong medication interaction. That failure mode is invisible
to content moderation and catastrophic to the person who trusts it. Sentinel exists for
exactly that failure mode.

---

## 2. System Overview

Three components. Build them in this order.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL SYSTEM                           │
│                                                                  │
│  ┌──────────────┐      ┌───────────────────┐     ┌───────────┐ │
│  │  CASA Bot    │      │  SENTINEL AGENT    │     │  Director │ │
│  │ (demo legal- │─────▶│  (the product)     │────▶│ Dashboard │ │
│  │  aid chatbot)│ every│                    │     │ + Trust   │ │
│  │              │ answer│  Plan → Tools →   │     │   Report  │ │
│  └──────────────┘      │  Decide → Report   │     └───────────┘ │
│         ▲              └────────┬──────────┘            ▲       │
│         │                       │                       │       │
│    end user asks           ┌────┴─────┐          quarantine     │
│    a question              │  TOOLS    │          queue + weekly │
│                            │           │          plain-English  │
│                            │ • Arize MCP (evals, traces, monitors)│
│                            │ • Trusted Corpus RAG (org's docs)   │
│                            │ • Risk Classifier                   │
│                            │ • Quarantine Store                  │
│                            └──────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

**CASA Bot** — "Community Advice & Support Assistant." A deliberately imperfect
demo chatbot for a fictional legal-aid clinic ("Riverside Community Legal Aid").
It answers immigration, housing, and benefits questions. It is a prop: simple
Gemini wrapper over a small FAQ, *intentionally prone to hallucinating specifics*
(deadlines, dollar amounts, form numbers). One day of work, max. Its purpose is
to give Sentinel something real to catch.

**Sentinel Agent** — the actual product. Intercepts every CASA answer before it
reaches the user. Runs the agent loop (Section 3). This is where 80% of effort goes.

**Director Dashboard** — the non-technical interface: live quarantine queue,
per-answer verdicts in plain English, and the weekly Trust Report. This is the
"design" criterion and the emotional payoff of the demo.

---

## 3. The Agent Loop (what makes this an agent, not a pipeline)

The hackathon brief demands an agent that *plans steps and uses tools*, under human
oversight. The trap is building a fixed conveyor belt (every answer → same checks).
Sentinel must make **visible decisions** and take **different paths** for different
inputs. Here is the loop:

### Step 1 — TRIAGE (the planning decision)
For each (question, draft answer) pair, the agent first classifies:

| Dimension | Values | How |
|---|---|---|
| **Stakes** | low / medium / high | Gemini structured-output call with a rubric: does the answer involve deadlines, money, legal rights, health, immigration status, eligibility? |
| **Specificity** | general info / specific factual claim | Does the answer assert a checkable fact (date, amount, form number, rule)? |
| **Coverage** | in-corpus / out-of-corpus | Quick embedding similarity: does the org's trusted corpus even cover this topic? |

The agent then **writes a plan** (and logs it — this is demo gold): e.g.
*"High stakes (visa deadline) + specific claim (a date) + topic covered in corpus
→ plan: extract claims, ground-check each against USCIS corpus docs, run Arize
hallucination eval, decide."* versus *"Low stakes (office hours question), no
factual risk → plan: light toxicity/PII check only, allow."*

**This branching is the difference between scoring as an agent and scoring as a
filter. The demo must show both paths.**

### Step 2 — TOOL EXECUTION (per the plan)
Tools the agent can choose to invoke:

1. **Claim extractor** (Gemini): decomposes the draft answer into atomic, checkable
   claims. "Your I-90 renewal must be filed within 30 days" → claim: {form: I-90,
   assertion: 30-day filing window}.
2. **Trusted-corpus grounding check** (RAG over the org's own documents): for each
   claim, retrieve the most relevant passages from the clinic's vetted sources
   (official agency PDFs, the org's approved FAQ, statute excerpts) and ask Gemini:
   *supported / contradicted / not found*. Crucially, "not found" is treated as
   risk, not as pass — an unsupported specific claim on a high-stakes topic gets
   quarantined. This is the mechanism that catches the confident fabrication.
3. **Arize evaluations** (via Arize MCP server — see Section 4): hallucination
   eval, QA-correctness eval, toxicity eval, with the retrieved corpus passages
   passed as ground-truth context.
4. **Risk-history lookup** (Arize monitoring data): has CASA been drifting on this
   topic recently? A topic with rising failure rates lowers the quarantine threshold.

### Step 3 — DECIDE (graduated, human-in-the-loop)
Three outcomes, and the thresholds are policy the *org* sets, not the agent:

- **ALLOW** — answer passes; delivered to the user with an audit trace.
- **REPAIR & ALLOW** — claims unsupported but a corrected answer is trivially
  derivable from the corpus → agent drafts a corrected version, *labels it as
  corrected*, attaches the source citation, and delivers. (This step is optional
  scope; it's impressive but cuttable.)
- **QUARANTINE** — answer is held; the end user receives an honest fallback
  ("I want to make sure you get accurate information about this — a staff member
  will follow up"), and the item lands in the director's queue with the agent's
  reasoning, the failed claims, and the contradicting source passages side by side.

Never silently rewrite without labeling; never block without telling the user
something true. The dignity of both the end user and the org's staff is a design
requirement, not a nicety.

### Step 4 — REPORT (close the loop)
Every decision — plan, tool calls, eval scores, verdict — is logged as a trace to
Arize. The Trust Report (Section 6) is generated *from* that accumulated data.

---

## 4. Making Arize Load-Bearing (not decorative)

The Arize judges will open the repo. Arize must be structural in three distinct ways:

1. **Evals as a decision input.** The agent's quarantine decision consumes Arize
   eval outputs (hallucination, QA correctness) as first-class signals — not as
   an after-the-fact log. Wire this through the Arize MCP server so the agent
   *calls Arize as a tool inside its loop*.
2. **Tracing as the audit trail.** Every agent run is an Arize trace: triage
   verdict, plan, each tool call, eval scores, final decision. This is the
   compliance artifact — when Texas TRAIGA or HIPAA-style AI risk rules ask
   "show me your oversight," the Arize trace *is* the answer. Say that sentence
   in the video.
3. **Monitoring as memory.** Set up Arize monitors on quarantine rate and eval
   scores per topic. The agent reads this back (Step 2, tool 4) so its own
   thresholds adapt — and the Trust Report's "trend" section is literally a
   plain-English rendering of Arize monitor data. This makes Arize the system's
   long-term memory, which no thin integration can fake.

Repo hygiene for this: a top-level `arize/` module with documented functions for
each of the three roles, referenced from the agent core. Make the dependency
impossible to miss in a 5-minute code review.

---

## 5. The Trusted Corpus

Per-org, vetted, boring on purpose. For the demo clinic:

- 6–10 official documents: USCIS form instructions (I-90, N-400), a state
  benefits eligibility page, a tenant-rights handbook chapter, the clinic's own
  approved FAQ.
- Chunked, embedded (Vertex AI embeddings), stored in a vector index
  (Vertex AI Vector Search keeps the stack all-Google; that's fine — the partner
  requirement is Arize, not the database).
- Each chunk carries source metadata (document, page, URL, last-verified date) so
  every grounding verdict can cite its source — and the quarantine view shows the
  bot's claim *next to* the official text that contradicts it. That side-by-side
  is the single most persuasive screen in the product.

Design principle: **the corpus is the org's voice, not the internet's.** Sentinel
never "checks against the web" — web search would reintroduce the unreliability
it exists to remove. If the corpus doesn't cover it, that's a quarantine, and the
Trust Report tells the director *which topics their corpus is missing* — turning
a limitation into a feature (corpus-gap analysis).

---

## 6. The Trust Report (the design-criterion winner)

A weekly, one-page, plain-English document addressed to a non-technical director.
Generated by Gemini from Arize monitoring data, with a fixed template so it never
rambles:

> **This week, your assistant answered 412 questions.**
> Sentinel cleared 389 automatically, corrected 14 with citations, and held 9 for
> your team's review.
>
> **What was caught:** 3 answers stated a wrong filing deadline for I-90 renewals
> (the assistant said 30 days; USCIS guidance says no deadline applies — source
> attached). 2 answers gave an outdated income threshold for SNAP eligibility.
>
> **Trend:** Immigration-deadline questions are being quarantined more often than
> last week. Your corpus's USCIS documents were last verified 94 days ago —
> consider refreshing them.
>
> **Your riskiest topic:** benefit eligibility amounts. **Your safest:** office
> hours and intake process.

No metric appears without a sentence of meaning. No jargon ("hallucination" is
allowed once, defined in parentheses, then becomes "made-up answer").

---

## 7. Stack

| Layer | Choice | Why |
|---|---|---|
| Agent orchestration | Google Cloud Agent Builder (ADK) | hackathon requirement; use its planner/tool abstractions visibly |
| Reasoning | Gemini (latest) | requirement; use structured output for triage + claim extraction |
| Evals / traces / monitors | **Arize via MCP server** | the track; see Section 4 |
| Corpus RAG | Vertex AI Vector Search + Vertex embeddings | keeps stack coherent |
| Quarantine store | Firestore | simple, serverless |
| Dashboard | Next.js (or Streamlit if solo) on Cloud Run | hosted-URL requirement |
| CASA demo bot | thin Gemini wrapper, Cloud Run | a prop, one day max |

Repo: public GitHub, MIT license visible in About, README with architecture
diagram, a `make demo` (or one `docker compose up`) path so judges can run it,
and a `DESIGN.md` that explains the triage/decide policy in prose. Judges reward
repos that respect their time.

---

## 8. The Demo Video (~3 minutes) — exact beat sheet

1. **0:00–0:25 — The problem, with a face.** "This is Maria. She asked a free
   legal-aid chatbot when she must renew her green card. It answered instantly,
   politely, confidently — and wrongly. No safety filter on earth flags this
   answer, because there's nothing toxic about it. It's just false, and it could
   cost her everything."
2. **0:25–0:55 — The wrong answer, live.** Show CASA bot giving the wrong
   deadline. Then the same question through Sentinel: the answer is held, Maria
   sees the honest fallback, and the quarantine screen shows the bot's claim
   side-by-side with the official USCIS text that contradicts it.
3. **0:55–1:40 — Prove it's an agent.** Split screen: a low-stakes question
   ("what are your office hours?") sails through with a two-line plan; the
   high-stakes question triggers the full plan — show the agent's written plan,
   the claim extraction, the corpus retrieval, the Arize eval scores arriving,
   the decision. Two visibly different paths. Narrate: "Sentinel decides how
   hard to check, based on what's at stake."
4. **1:40–2:15 — The Arize spine.** Show the Arize trace of that run, the
   monitors, and say the compliance line: "When new AI-accountability rules ask
   this clinic to prove oversight, this trace is the proof."
5. **2:15–2:50 — The Trust Report.** Scroll it slowly. "No ML team. No
   dashboard training. A director reads this over coffee and knows exactly what
   her AI did this week — and what it almost did."
6. **2:50–3:00 — Close.** "Enterprises buy AI safety. Communities deserve it.
   Sentinel — the watchdog for everyone else."

---

## 9. Devpost Submission Sections (draft)

**Inspiration** — lead with the asymmetry: 2026's guardrail market (Galileo,
Lakera, GA Guard, Bifrost…) is excellent and entirely enterprise-shaped — VPCs,
SIEMs, OTel pipelines. The orgs serving the most vulnerable people — legal aid,
free health lines, benefits navigators — are deploying chatbots with none of it,
just as state chatbot laws (TRAIGA, Utah HB 452) start requiring oversight.
Stanford's 2026 AI Index: hallucination rates of 22–94% across top models.

**What it does / How we built it** — compress Sections 2–6.

**Challenges** — be honest: the hardest problem was treating "not found in
corpus" as risk rather than pass, and tuning triage so the agent doesn't
quarantine the harmless. Honesty here reads as competence.

**What's next** — onboarding flow where an org uploads its documents and gets a
working Sentinel in an afternoon; partnerships with Parent Training Centers,
211 networks, and legal-aid associations as distribution.

---

## 10. Risk Register (what could sink it, and the mitigation)

| Risk | Mitigation |
|---|---|
| Reads as a classifier, not an agent | Triage branching + visible written plans + two-path demo (Sec. 3) |
| Arize looks bolted-on | Three structural roles (Sec. 4) + dedicated module + traces in video |
| "Why not built-in safety?" judge question | The confident-wrong-fact distinction, stated in the first 25 seconds |
| Scope explosion | CASA bot is a one-day prop; REPAIR step is the designated cut line |
| Impact feels hypothetical | Even one email exchange with a real clinic, quoted (with permission) in the submission |
| False sense of security (ethical) | Trust Report explicitly states Sentinel reduces risk, doesn't eliminate it; quarantine thresholds are org policy, human review is mandatory for high-stakes |

---

## 11. Build Order (sequence, not schedule)

1. Corpus + RAG grounding check (the heart — if this works, everything works)
2. Agent loop with triage branching, on Agent Builder
3. Arize MCP wiring: evals in the loop, then tracing, then monitors
4. Quarantine store + director queue UI
5. CASA demo bot (the prop)
6. Trust Report generator
7. Deploy (Cloud Run), repo hygiene, license
8. Demo video, Devpost form
9. (Stretch) REPAIR-and-cite step, corpus-gap analysis panel
