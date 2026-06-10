"""Triage models — the planning decision (Agent Loop Step 1).

For each (question, draft answer) pair, Sentinel first classifies stakes,
specificity, and corpus coverage, then *writes a plan*. The written plan is
what makes Sentinel score as an agent rather than a fixed filter: low-stakes
inputs take a light path, high-stakes specific claims take the full path.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class StakesLevel(StrEnum):
    """How much is riding on the answer being correct."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Specificity(StrEnum):
    """Whether the draft answer asserts a checkable fact."""

    GENERAL_INFO = "general_info"
    SPECIFIC_CLAIM = "specific_claim"


class Coverage(StrEnum):
    """Whether the org's trusted corpus even covers this topic."""

    IN_CORPUS = "in_corpus"
    OUT_OF_CORPUS = "out_of_corpus"


class TriageVerdict(BaseModel):
    """Structured output of the triage classifier (a Gemini structured call).

    ``risk_signals`` enumerates the concrete reasons stakes were judged high —
    deadlines, money, legal rights, health, immigration status, eligibility —
    so the written plan and the audit trail can cite *why* the path was chosen.
    """

    topic: str = Field(
        ..., min_length=1, description="Short topic label, e.g. 'I-90 renewal deadline'."
    )
    stakes: StakesLevel
    specificity: Specificity
    coverage: Coverage
    coverage_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Embedding similarity of the question to the trusted corpus.",
    )
    risk_signals: list[str] = Field(
        default_factory=list,
        description="Concrete stake drivers detected: deadline, money, legal_right, health, immigration, eligibility.",
    )
    reasoning: str = Field(
        ..., min_length=1, description="One-paragraph plain-English justification."
    )


class PlanStep(BaseModel):
    """A single tool the agent intends to invoke, with its justification."""

    tool: str = Field(
        ...,
        description="Tool name, e.g. 'claim_extractor', 'corpus_grounding', 'hallucination_eval'.",
    )
    why: str = Field(..., min_length=1, description="Why this step is warranted for this input.")


class SentinelPlan(BaseModel):
    """The agent's written plan for one answer — logged and shown in the demo.

    ``path`` is the visible branch: 'light' for low-risk inputs (a toxicity/PII
    glance, then allow), 'full' for high-stakes checkable claims (extract,
    ground-check each claim, run evals, decide).
    """

    triage: TriageVerdict
    path: Literal["light", "full"]
    steps: list[PlanStep]
    summary: str = Field(
        ...,
        min_length=1,
        description="The written plan in one or two sentences — demo gold.",
    )
