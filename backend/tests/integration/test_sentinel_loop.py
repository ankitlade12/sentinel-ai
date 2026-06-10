"""Integration tests — the full agent loop end to end with a stubbed LLM.

Proves the two visibly different paths and the hero catch: the confident
"30-day" green-card lie is held; the office-hours question sails through.
"""

from __future__ import annotations

import pytest

from backend.models.verdict import Decision

pytestmark = pytest.mark.integration

_GREEN_CARD_LIE = (
    "You must file Form I-90 to renew your green card within 30 days of its expiration. "
    "If you miss this 30-day deadline, your permanent resident status is automatically lost."
)
_OFFICE_HOURS = "We're open Monday through Friday, 9:00 a.m. to 5:00 p.m."
_DEPOSIT_OVERSTATE = "Your landlord must return your security deposit within 60 days of move-out."


def test_hero_scenario_is_quarantined(agent, store, stub_llm):
    verdict = agent.run("When do I have to renew my green card?", _GREEN_CARD_LIE)
    assert verdict.decision == Decision.QUARANTINE
    assert verdict.requires_human_review is True
    assert verdict.plan.path == "full"
    assert verdict.failed_claim_ids  # at least one claim failed grounding
    assert verdict.user_message  # the honest fallback
    # Evals actually ran and fed the decision (regression guard).
    assert {e.kind.value for e in verdict.evals} >= {"hallucination", "qa_correctness"}
    assert verdict.delivered_answer == verdict.user_message
    # Persisted to the store for the director queue + audit trail.
    assert store.get_verdict(verdict.id) is not None
    # The contradicting source is attached for the side-by-side view.
    contradicted = [g for g in verdict.grounding if g.status.value == "contradicted"]
    assert contradicted and contradicted[0].passages


def test_low_stakes_is_allowed(agent, stub_llm):
    verdict = agent.run("What are your office hours?", _OFFICE_HOURS)
    assert verdict.decision == Decision.ALLOW
    assert verdict.plan.path == "light"
    assert verdict.delivered_answer == _OFFICE_HOURS


def test_repair_path_corrects_and_cites(agent, stub_llm):
    # Medium-stakes contradiction with a clean corpus correction → REPAIR & ALLOW.
    verdict = agent.run(
        "How many days does my landlord have to return my security deposit?",
        _DEPOSIT_OVERSTATE,
    )
    assert verdict.decision == Decision.REPAIR_ALLOW
    assert verdict.requires_human_review is False
    assert verdict.corrected_answer is not None
    assert verdict.delivered_answer == verdict.corrected_answer
    assert "Corrected by Sentinel" in verdict.delivered_answer


def test_trust_report_after_runs(agent, store, stub_llm):
    agent.run("When do I have to renew my green card?", _GREEN_CARD_LIE)
    agent.run("What are your office hours?", _OFFICE_HOURS)
    from backend.reports.trust_report import generate_trust_report

    report = generate_trust_report(store, org_id="riverside")
    assert report.total_answered == 2
    assert report.held == 1
    assert report.cleared == 1
    assert report.what_was_caught  # at least one plain-English catch bullet
