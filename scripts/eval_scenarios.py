"""`make demo` — run the canonical scenarios through CASA → Sentinel and print
the verdicts. Demonstrates the two visibly different paths and the hero catch.

Runs against whatever backend is configured: full Google Cloud + Gemini + Phoenix
when set up, or the hermetic mock corpus/store for an offline structural check
(the LLM still needs credentials unless you stub it in tests).
"""

from __future__ import annotations

import json
import logging

from dotenv import load_dotenv

load_dotenv(override=False)

from backend.agents.sentinel import build_default_agent  # noqa: E402
from backend.arize.tracing import setup_tracing  # noqa: E402
from backend.casa.bot import CasaBot  # noqa: E402

logging.basicConfig(level="WARNING")

SCENARIOS = [
    "When do I have to renew my green card?",
    "What are your office hours?",
    "What's the income limit for SNAP for a family of three?",
    "How long until I can apply for citizenship?",
]


def main() -> None:
    setup_tracing()  # stream the runs to Phoenix
    casa = CasaBot()
    agent = build_default_agent()
    print("=" * 88)
    for question in SCENARIOS:
        draft = casa.answer(question)
        verdict = agent.run(question, draft.answer)
        print(f"Q: {question}")
        print(f"  CASA draft : {draft.answer[:110]}...")
        print(f"  Path       : {verdict.plan.path}   Stakes: {verdict.plan.triage.stakes.value}")
        print(f"  Decision   : {verdict.decision.value.upper()}   ({verdict.rationale[:90]})")
        if verdict.trace_url:
            print(f"  Trace      : {verdict.trace_url}")
        print("-" * 88)

    print("\nTrust Report preview:")
    from backend.reports.trust_report import generate_trust_report

    report = generate_trust_report(agent.store)
    print(json.dumps(report.model_dump(), indent=2)[:700])


if __name__ == "__main__":
    main()
