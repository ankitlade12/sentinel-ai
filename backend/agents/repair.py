"""Optional Step 3b — REPAIR & ALLOW.

When claims are contradicted but a correction is trivially derivable from the
corpus, the agent drafts a corrected answer grounded only in the trusted
sources, labels it as corrected, and attaches the citation. Never an unlabeled
rewrite. This step is impressive but cuttable scope (gated by SENTINEL_ENABLE_REPAIR).
"""

from __future__ import annotations

import logging

from backend import llm
from backend.agents.prompt_loader import load_prompt
from backend.models.grounding import GroundingResult, SourcePassage

logger = logging.getLogger(__name__)

CORRECTION_LABEL = "✅ Corrected by Sentinel and verified against your clinic's trusted sources:"


def draft_repair(question: str, failed: list[GroundingResult]) -> tuple[str, list[SourcePassage]]:
    """Draft a corpus-grounded corrected answer and the sources it cites."""
    sources: list[SourcePassage] = []
    seen: set[str] = set()
    for g in failed:
        for p in g.passages:
            if p.doc_id not in seen:
                seen.add(p.doc_id)
                sources.append(p)

    failed_lines = "\n".join(
        f"- Claim: {g.claim_text}\n  Sources say: {g.corrected_text or g.explanation}"
        for g in failed
    )
    source_blocks = "\n\n".join(f"{p.doc_title}:\n{p.text}" for p in sources) or "(none)"
    body = llm.generate_text(
        system=load_prompt("repair"),
        prompt=(
            f"QUESTION:\n{question}\n\nFAILED CLAIMS:\n{failed_lines}\n\nSOURCES:\n{source_blocks}"
        ),
    )
    citation = "  •  ".join(
        f"{p.doc_title}" + (f" ({p.source_url})" if p.source_url else "") for p in sources
    )
    corrected = f"{CORRECTION_LABEL}\n\n{body}"
    if citation:
        corrected += f"\n\nSource: {citation}"
    logger.info("repair: drafted corrected answer citing %d source(s)", len(sources))
    return corrected, sources
