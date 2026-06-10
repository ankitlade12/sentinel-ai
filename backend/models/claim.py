"""Claim models — atomic, checkable assertions decomposed from a draft answer.

The claim extractor (Gemini) turns a fluent paragraph into a list of discrete
factual claims. Only checkable claims proceed to grounding; this is what lets
Sentinel catch a *single* fabricated specific (a wrong deadline) buried inside
an otherwise-correct answer.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimType(StrEnum):
    """Category of factual assertion — drives how grounding scores risk."""

    DATE = "date"
    DEADLINE = "deadline"
    AMOUNT = "amount"
    FORM_NUMBER = "form_number"
    ELIGIBILITY = "eligibility"
    LEGAL_RULE = "legal_rule"
    PROCEDURE = "procedure"
    CONTACT = "contact"
    OTHER = "other"


class Claim(BaseModel):
    """One atomic assertion extracted from the draft answer.

    Example: "Your I-90 renewal must be filed within 30 days" decomposes to a
    claim with ``claim_type=DEADLINE`` and ``subject="I-90 renewal"``.
    """

    id: str = Field(..., description="Stable id within a single verdict, e.g. 'c1'.")
    text: str = Field(
        ..., min_length=1, description="The assertion, quoted or tightly paraphrased."
    )
    claim_type: ClaimType
    subject: str = Field(..., description="What the claim is about, e.g. 'I-90 renewal'.")
    checkable: bool = Field(
        ...,
        description="Whether this is a verifiable fact (vs opinion / pleasantry / generic guidance).",
    )


class ClaimExtraction(BaseModel):
    """Envelope returned by the claim extractor."""

    claims: list[Claim]
    summary: str = Field(
        ..., min_length=1, description="One line: what kind of claims this answer makes."
    )
