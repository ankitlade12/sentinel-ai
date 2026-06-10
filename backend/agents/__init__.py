"""The Sentinel agent.

The loop, per the build spec Section 3:

1. TRIAGE  — classify stakes / specificity / coverage and *write a plan*.
2. TOOLS   — execute the plan: extract claims, ground-check each against the
   trusted corpus, run Arize/Phoenix evals, read risk history.
3. DECIDE  — a graduated, human-in-the-loop verdict (allow / repair / quarantine);
   thresholds are org policy, not the agent's.
4. REPORT  — the whole run is one Phoenix trace and one persisted verdict.

The branching in step 1 — light path for low-stakes inputs, full path for
high-stakes checkable claims — is what makes Sentinel an agent rather than a
fixed filter.
"""
