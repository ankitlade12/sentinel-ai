"""Step 2, tool 1 — CLAIM EXTRACTOR.

Decomposes a fluent draft answer into atomic, checkable claims. This is what
lets Sentinel catch a single fabricated specific (a wrong deadline) buried in an
otherwise-correct paragraph: each specific is isolated and grounded on its own.
"""

from __future__ import annotations

import logging

from backend import llm
from backend.agents.prompt_loader import load_prompt
from backend.models.claim import ClaimExtraction

logger = logging.getLogger(__name__)


def extract_claims(draft_answer: str) -> ClaimExtraction:
    """Return the atomic claims asserted by the draft answer, with stable ids."""
    extraction = llm.generate_structured(
        ClaimExtraction,
        system=load_prompt("claim_extractor"),
        prompt=f"DRAFT ANSWER:\n{draft_answer}",
    )
    # Renumber to guarantee stable, unique ids regardless of what the model emits.
    for i, claim in enumerate(extraction.claims, start=1):
        claim.id = f"c{i}"
    logger.info(
        "claims: extracted=%d checkable=%d",
        len(extraction.claims),
        sum(1 for c in extraction.claims if c.checkable),
    )
    return extraction
