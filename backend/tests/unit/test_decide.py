"""Unit tests for the decision policy — pure, no LLM, no network."""

from __future__ import annotations

import pytest

from backend.agents.decide import decide
from backend.config import Settings
from backend.models.evaluation import EvalKind, EvalResult
from backend.models.grounding import GroundingResult, GroundingStatus, SourcePassage
from backend.models.triage import (
    Coverage,
    PlanStep,
    SentinelPlan,
    Specificity,
    StakesLevel,
    TriageVerdict,
)
from backend.models.verdict import Decision

pytestmark = pytest.mark.unit


def _plan(stakes=StakesLevel.HIGH, path="full", coverage=Coverage.IN_CORPUS) -> SentinelPlan:
    verdict = TriageVerdict(
        topic="I-90 renewal",
        stakes=stakes,
        specificity=Specificity.SPECIFIC_CLAIM,
        coverage=coverage,
        coverage_score=0.6,
        risk_signals=["immigration", "deadline"],
        reasoning="test",
    )
    return SentinelPlan(
        triage=verdict,
        path=path,
        steps=[PlanStep(tool="decide", why="x")],
        summary="test plan",
    )


def _passage() -> SourcePassage:
    return SourcePassage(
        doc_id="d1",
        doc_title="USCIS I-90",
        last_verified="2026-03-07",
        text="No 30-day deadline.",
        score=0.9,
    )


def _grounding(
    status, *, claim_id="c1", confidence=0.9, corrected="the corpus value"
) -> GroundingResult:
    return GroundingResult(
        claim_id=claim_id,
        claim_text="claim",
        status=status,
        confidence=confidence,
        passages=[_passage()],
        explanation="x",
        corrected_text=corrected if status == GroundingStatus.CONTRADICTED else None,
    )


def _settings(**kw) -> Settings:
    base = dict(quarantine_threshold=0.55, hallucination_threshold=0.5, enable_repair=True)
    base.update(kw)
    return Settings(**base)


def test_allow_when_all_supported():
    outcome = decide(
        plan=_plan(),
        grounding=[_grounding(GroundingStatus.SUPPORTED)],
        evals=[
            EvalResult(
                kind=EvalKind.HALLUCINATION,
                label="factual",
                score=0.05,
                explanation="x",
                passed=True,
            )
        ],
        settings=_settings(),
    )
    assert outcome.decision == Decision.ALLOW
    assert outcome.requires_human_review is False


def test_quarantine_when_contradicted_high_stakes():
    outcome = decide(
        plan=_plan(stakes=StakesLevel.HIGH),
        grounding=[_grounding(GroundingStatus.CONTRADICTED)],
        evals=[],
        settings=_settings(),
    )
    # High stakes never auto-repairs — a human must see it.
    assert outcome.decision == Decision.QUARANTINE
    assert outcome.requires_human_review is True
    assert outcome.failed_claim_ids == ["c1"]
    assert outcome.user_message


def test_repair_when_contradicted_medium_stakes():
    outcome = decide(
        plan=_plan(stakes=StakesLevel.MEDIUM),
        grounding=[_grounding(GroundingStatus.CONTRADICTED)],
        evals=[],
        settings=_settings(),
    )
    assert outcome.decision == Decision.REPAIR_ALLOW
    assert outcome.should_repair is True


def test_not_found_is_risk_not_pass():
    outcome = decide(
        plan=_plan(stakes=StakesLevel.HIGH),
        grounding=[_grounding(GroundingStatus.NOT_FOUND)],
        evals=[],
        settings=_settings(),
    )
    assert outcome.decision == Decision.QUARANTINE


def test_light_path_allows_without_claims():
    outcome = decide(
        plan=_plan(stakes=StakesLevel.LOW, path="light"),
        grounding=[],
        evals=[
            EvalResult(
                kind=EvalKind.TOXICITY, label="non-toxic", score=0.0, explanation="x", passed=True
            )
        ],
        settings=_settings(),
    )
    assert outcome.decision == Decision.ALLOW


def test_risk_adjustment_tightens_support_bar():
    # A supported claim at 0.6 confidence passes at base threshold 0.55…
    base = decide(
        plan=_plan(),
        grounding=[_grounding(GroundingStatus.SUPPORTED, confidence=0.6)],
        evals=[],
        settings=_settings(),
    )
    assert base.decision == Decision.ALLOW
    # …but a drifting topic (+0.15) raises the bar to 0.70, making it risk.
    drifted = decide(
        plan=_plan(),
        grounding=[_grounding(GroundingStatus.SUPPORTED, confidence=0.6)],
        evals=[],
        settings=_settings(),
        risk_adjustment=0.15,
    )
    assert drifted.decision == Decision.QUARANTINE


def test_repair_disabled_falls_back_to_quarantine():
    outcome = decide(
        plan=_plan(stakes=StakesLevel.MEDIUM),
        grounding=[_grounding(GroundingStatus.CONTRADICTED)],
        evals=[],
        settings=_settings(enable_repair=False),
    )
    assert outcome.decision == Decision.QUARANTINE
