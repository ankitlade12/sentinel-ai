"""Shared fixtures + a deterministic LLM stub for the hermetic test tiers.

No test makes a network call or needs Google Cloud credentials. ``stub_llm``
replaces ``backend.llm.generate_structured`` / ``generate_text`` with a
scenario-aware responder so the *whole* agent loop — triage, claim extraction,
grounding, evals, repair — runs end to end and produces the verdict the demo
expects (the green-card "30-day" lie is quarantined; office hours is allowed).
"""

from __future__ import annotations

import os

import pytest

# Force hermetic backends before any settings are read. PHOENIX_* are set to ""
# (override) so the app's load_dotenv(override=False) can't re-enable tracing from
# a developer's .env — no network or span export in the test tiers.
os.environ["SENTINEL_CORPUS"] = "mock"
os.environ["SENTINEL_STORE"] = "mock"
os.environ["SENTINEL_LLM_PROVIDER"] = "ai_studio"
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = ""
os.environ["PHOENIX_API_KEY"] = ""

from backend.config import get_settings
from backend.connectors.mock_corpus import MockCorpusConnector
from backend.connectors.mock_store import MockQuarantineStore
from backend.models.claim import Claim, ClaimExtraction, ClaimType


def _classify(prompt: str):
    from backend.agents.triage import _TriageClassification
    from backend.models.triage import Specificity, StakesLevel

    low = prompt.lower()
    if "office hours" in low or "open" in low or "hours" in low:
        return _TriageClassification(
            topic="clinic office hours",
            stakes=StakesLevel.LOW,
            specificity=Specificity.GENERAL_INFO,
            risk_signals=[],
            reasoning="Logistics question with no factual risk.",
        )
    if "snap" in low or "income" in low or "food" in low:
        return _TriageClassification(
            topic="SNAP income eligibility",
            stakes=StakesLevel.HIGH,
            specificity=Specificity.SPECIFIC_CLAIM,
            risk_signals=["eligibility", "money"],
            reasoning="Benefits eligibility with a specific dollar threshold.",
        )
    if "deposit" in low or "landlord" in low or "tenant" in low:
        return _TriageClassification(
            topic="security deposit return",
            stakes=StakesLevel.MEDIUM,
            specificity=Specificity.SPECIFIC_CLAIM,
            risk_signals=["money"],
            reasoning="A specific deposit-return timeframe; medium stakes, recoverable.",
        )
    # Default: immigration deadline (the hero scenario).
    return _TriageClassification(
        topic="I-90 green card renewal deadline",
        stakes=StakesLevel.HIGH,
        specificity=Specificity.SPECIFIC_CLAIM,
        risk_signals=["immigration", "deadline"],
        reasoning="Immigration deadline with a specific number of days.",
    )


def _extract(prompt: str) -> ClaimExtraction:
    low = prompt.lower()
    if "30 days" in low or "i-90" in low or "green card" in low:
        return ClaimExtraction(
            claims=[
                Claim(
                    id="c1",
                    text="Form I-90 must be filed within 30 days of the green card's expiration.",
                    claim_type=ClaimType.DEADLINE,
                    subject="I-90 renewal",
                    checkable=True,
                ),
                Claim(
                    id="c2",
                    text="Missing the 30-day window automatically ends permanent resident status.",
                    claim_type=ClaimType.LEGAL_RULE,
                    subject="permanent resident status",
                    checkable=True,
                ),
            ],
            summary="Two specific claims about I-90 timing and status loss.",
        )
    if "snap" in low or "$2,200" in low or "income" in low:
        return ClaimExtraction(
            claims=[
                Claim(
                    id="c1",
                    text="The SNAP gross monthly income limit for a household of three is $2,200.",
                    claim_type=ClaimType.AMOUNT,
                    subject="SNAP income limit",
                    checkable=True,
                )
            ],
            summary="A specific SNAP income threshold.",
        )
    if "deposit" in low or "60 days" in low:
        return ClaimExtraction(
            claims=[
                Claim(
                    id="c1",
                    text="The landlord must return the security deposit within 60 days.",
                    claim_type=ClaimType.DEADLINE,
                    subject="security deposit",
                    checkable=True,
                )
            ],
            summary="A specific deposit-return deadline.",
        )
    return ClaimExtraction(
        claims=[
            Claim(
                id="c1",
                text=prompt[:80],
                claim_type=ClaimType.OTHER,
                subject="general",
                checkable=False,
            )
        ],
        summary="No checkable specifics.",
    )


def _ground(prompt: str):
    from backend.agents.grounding import _GroundingJudgment
    from backend.models.grounding import GroundingStatus

    low = prompt.lower()
    if "30 days" in low or "30-day" in low:
        return _GroundingJudgment(
            status=GroundingStatus.CONTRADICTED,
            confidence=0.95,
            explanation="The USCIS Form I-90 page states there is no 30-day deadline; you may file when the card is expiring or expired.",
            corrected_text="USCIS guidance says there is no 30-day deadline — you may file when your card is expiring or has expired, and your status does not end when the card expires.",
        )
    if "status" in low and ("end" in low or "lost" in low or "loses" in low):
        return _GroundingJudgment(
            status=GroundingStatus.CONTRADICTED,
            confidence=0.92,
            explanation="The corpus states permanent resident status does not end when the card expires.",
            corrected_text="Your status as a permanent resident does not end when your green card expires.",
        )
    if "$2,200" in low or "2,200" in low:
        return _GroundingJudgment(
            status=GroundingStatus.CONTRADICTED,
            confidence=0.9,
            explanation="The SNAP source lists the household-of-three gross limit as $2,798, not $2,200.",
            corrected_text="The SNAP gross monthly income limit for a household of three is about $2,798.",
        )
    if "60 days" in low or "deposit" in low:
        return _GroundingJudgment(
            status=GroundingStatus.CONTRADICTED,
            confidence=0.9,
            explanation="The tenant-rights handbook says deposits are returned within 14 to 30 days, not 60.",
            corrected_text="Your landlord must return your security deposit within 14 to 30 days, not 60.",
        )
    return _GroundingJudgment(
        status=GroundingStatus.SUPPORTED,
        confidence=0.85,
        explanation="Supported by the trusted corpus.",
        corrected_text=None,
    )


def _eval(schema_name: str, prompt: str):
    from backend.arize.evals import _HallucinationJudgment, _QAJudgment, _ToxicityJudgment

    low = prompt.lower()
    risky = "30 days" in low or "$2,200" in low or "2,200" in low
    if schema_name == "_HallucinationJudgment":
        return _HallucinationJudgment(
            label="hallucinated" if risky else "factual",
            hallucination_score=0.85 if risky else 0.08,
            explanation="Heuristic stub judgment.",
        )
    if schema_name == "_QAJudgment":
        return _QAJudgment(
            label="incorrect" if risky else "correct",
            correctness_score=0.15 if risky else 0.9,
            explanation="Heuristic stub judgment.",
        )
    return _ToxicityJudgment(label="non-toxic", toxicity_score=0.01, explanation="No toxicity.")


def _stub_generate_structured(schema, *, system, prompt, temperature=0.0, model=None):
    name = schema.__name__
    if name == "_TriageClassification":
        return _classify(prompt)
    if name == "ClaimExtraction":
        return _extract(prompt)
    if name == "_GroundingJudgment":
        return _ground(prompt)
    if name in ("_HallucinationJudgment", "_QAJudgment", "_ToxicityJudgment"):
        return _eval(name, prompt)
    raise AssertionError(f"stub_llm has no handler for schema {name}")


def _stub_generate_text(*, system, prompt, temperature=0.0, model=None) -> str:
    return "Based on your clinic's trusted sources, here is the corrected guidance."


@pytest.fixture
def stub_llm(monkeypatch):
    """Patch the Gemini entry points with the deterministic responder."""
    monkeypatch.setattr("backend.llm.generate_structured", _stub_generate_structured)
    monkeypatch.setattr("backend.llm.generate_text", _stub_generate_text)


@pytest.fixture
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def corpus():
    return MockCorpusConnector()


@pytest.fixture
def store():
    return MockQuarantineStore()


@pytest.fixture
def agent(corpus, store, settings):
    from backend.agents.sentinel import SentinelAgent

    return SentinelAgent(corpus=corpus, store=store, settings=settings)
