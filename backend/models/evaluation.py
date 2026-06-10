"""Evaluation models — Arize/Phoenix evals consumed as a decision input.

These are NOT after-the-fact logs. The agent calls the eval pipeline as a tool
inside its loop, and the quarantine decision consumes the hallucination and
QA-correctness scores as first-class signals, with the retrieved corpus
passages passed as ground-truth context.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvalKind(StrEnum):
    """The Phoenix LLM-as-a-Judge evaluators Sentinel runs."""

    HALLUCINATION = "hallucination"
    QA_CORRECTNESS = "qa_correctness"
    TOXICITY = "toxicity"


class EvalResult(BaseModel):
    """One evaluator's verdict on the draft answer.

    ``score`` is normalized to [0, 1] where *higher = more concerning* for
    HALLUCINATION and TOXICITY, and *higher = more correct* for QA_CORRECTNESS.
    ``passed`` is the evaluator-local pass/fail after applying its threshold,
    so the decider can reason over a uniform boolean as well as the raw score.
    """

    kind: EvalKind
    label: str = Field(
        ..., description="The judge's categorical label, e.g. 'factual' / 'hallucinated'."
    )
    score: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(
        ..., min_length=1, description="The judge's rationale (Phoenix explanation)."
    )
    evaluator: str = Field(
        default="phoenix-llm-judge", description="Which evaluator produced this."
    )
    passed: bool = Field(..., description="Evaluator-local pass/fail after its threshold.")
