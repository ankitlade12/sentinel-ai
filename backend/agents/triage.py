"""Step 1 — TRIAGE: the planning decision.

Classifies stakes / specificity / coverage, then writes a plan and chooses a
path. Coverage is an embedding-similarity signal from the trusted corpus (not an
LLM guess); stakes and specificity are a Gemini structured call. The written
plan is generated deterministically from the triage facts so it is fast and
always consistent with the classification it describes.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from backend import llm
from backend.agents.prompt_loader import load_prompt
from backend.connectors.protocol import CorpusConnector
from backend.models.triage import (
    Coverage,
    PlanStep,
    SentinelPlan,
    Specificity,
    StakesLevel,
    TriageVerdict,
)

logger = logging.getLogger(__name__)

# Embedder-dependent; coverage is informational (grounding is decisive), so a
# modest bar is fine. Out-of-corpus high-stakes questions still get the full path.
_COVERAGE_THRESHOLD = 0.15


class _TriageClassification(BaseModel):
    """The portion of triage the LLM produces (coverage is computed separately)."""

    topic: str = Field(..., min_length=1)
    stakes: StakesLevel
    specificity: Specificity
    risk_signals: list[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=1)


def _classify(question: str, draft_answer: str) -> _TriageClassification:
    prompt = f"QUESTION:\n{question}\n\nDRAFT ANSWER:\n{draft_answer}"
    return llm.generate_structured(
        _TriageClassification,
        system=load_prompt("triage"),
        prompt=prompt,
    )


def _stakes_phrase(verdict: TriageVerdict) -> str:
    signals = ", ".join(verdict.risk_signals) if verdict.risk_signals else verdict.topic
    return f"{verdict.stakes.value} stakes ({signals})"


def _write_plan(verdict: TriageVerdict, path: str) -> tuple[list[PlanStep], str]:
    """Produce the visible plan steps and the one-sentence written plan."""
    if path == "light":
        steps = [
            PlanStep(
                tool="safety_check", why="Low factual risk — a light toxicity/PII glance suffices."
            ),
            PlanStep(tool="decide", why="Allow unless the safety check flags something."),
        ]
        summary = (
            f"{_stakes_phrase(verdict)}, no checkable factual claim "
            f"→ plan: light safety check only, then allow."
        )
        return steps, summary

    coverage_phrase = (
        "topic covered in corpus"
        if verdict.coverage == Coverage.IN_CORPUS
        else "topic NOT in corpus"
    )
    steps = [
        PlanStep(tool="claim_extractor", why="Decompose the answer into atomic, checkable claims."),
        PlanStep(
            tool="corpus_grounding",
            why="Ground-check each claim against the org's trusted sources only.",
        ),
        PlanStep(
            tool="hallucination_eval",
            why="Run the Phoenix hallucination eval with corpus passages as context.",
        ),
        PlanStep(
            tool="qa_correctness_eval",
            why="Run the Phoenix QA-correctness eval against the grounded sources.",
        ),
        PlanStep(
            tool="risk_history",
            why="Check whether this topic has been drifting (adapts the threshold).",
        ),
        PlanStep(
            tool="decide", why="Apply the org's graduated policy: allow / repair / quarantine."
        ),
    ]
    summary = (
        f"{_stakes_phrase(verdict)} + {verdict.specificity.value.replace('_', ' ')} + {coverage_phrase} "
        f"→ plan: extract claims, ground-check each against the trusted corpus, "
        f"run hallucination + QA-correctness evals, check risk history, then decide."
    )
    return steps, summary


def triage(question: str, draft_answer: str, *, corpus: CorpusConnector) -> SentinelPlan:
    """Classify the (question, answer) pair and return the agent's written plan."""
    coverage_score = corpus.coverage(f"{question}\n{draft_answer}")
    coverage = (
        Coverage.IN_CORPUS if coverage_score >= _COVERAGE_THRESHOLD else Coverage.OUT_OF_CORPUS
    )

    classification = _classify(question, draft_answer)
    verdict = TriageVerdict(
        topic=classification.topic,
        stakes=classification.stakes,
        specificity=classification.specificity,
        coverage=coverage,
        coverage_score=round(coverage_score, 4),
        risk_signals=classification.risk_signals,
        reasoning=classification.reasoning,
    )

    # The visible branch. High stakes always gets the full path; medium stakes
    # gets it when the answer asserts a checkable specific.
    full = verdict.stakes == StakesLevel.HIGH or (
        verdict.stakes == StakesLevel.MEDIUM and verdict.specificity == Specificity.SPECIFIC_CLAIM
    )
    path = "full" if full else "light"
    steps, summary = _write_plan(verdict, path)

    logger.info(
        "triage: topic=%r stakes=%s specificity=%s coverage=%s(%.3f) path=%s",
        verdict.topic,
        verdict.stakes,
        verdict.specificity,
        verdict.coverage,
        coverage_score,
        path,
    )
    return SentinelPlan(triage=verdict, path=path, steps=steps, summary=summary)
