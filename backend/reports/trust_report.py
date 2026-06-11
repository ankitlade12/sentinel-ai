"""Generate the weekly Trust Report from accumulated verdicts + monitor data.

The structured statistics are computed deterministically (so the same data
always renders the same report), and the prose follows a fixed template so it
never rambles. No metric appears without a sentence of meaning, and "made-up
answer" stands in for the one allowed, parenthetically-defined use of
"hallucination".

The ethical guardrail is stated on every report: Sentinel reduces risk, it does
not eliminate it; quarantine thresholds are the org's policy; human review is
mandatory for high-stakes answers.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime

from backend.arize import monitors
from backend.connectors.store_protocol import QuarantineStore
from backend.models.grounding import GroundingStatus
from backend.models.trust_report import TrustReport
from backend.models.verdict import Decision, ReviewStatus, SentinelVerdict

logger = logging.getLogger(__name__)


def _caught_bullets(verdicts: list[SentinelVerdict]) -> list[str]:
    """One plain-English bullet per topic that was corrected or held."""
    by_topic: dict[str, list[SentinelVerdict]] = defaultdict(list)
    for v in verdicts:
        if v.decision in (Decision.QUARANTINE, Decision.REPAIR_ALLOW):
            by_topic[v.topic].append(v)

    bullets: list[str] = []
    for topic, items in sorted(by_topic.items(), key=lambda kv: len(kv[1]), reverse=True):
        # Find a representative contradiction with what the sources actually say.
        detail = ""
        for v in items:
            contradiction = next(
                (
                    g
                    for g in v.grounding
                    if g.status == GroundingStatus.CONTRADICTED and g.corrected_text
                ),
                None,
            )
            if contradiction is not None:
                detail = f" The assistant said something the sources contradict; {contradiction.corrected_text}"
                break
            not_found = next(
                (g for g in v.grounding if g.status == GroundingStatus.NOT_FOUND), None
            )
            if not_found is not None:
                detail = " The assistant stated a specific the trusted sources do not confirm."
                break
        count = len(items)
        plural = "answer" if count == 1 else "answers"
        bullets.append(f"{count} {plural} about {topic}.{detail} (Source attached.)")
    return bullets


def _trend(verdicts: list[SentinelVerdict]) -> str:
    """Compose the trend paragraph, including a stale-corpus nudge."""
    from backend.corpus.loader import load_corpus_docs

    parts: list[str] = []

    # Stale-corpus nudge from document metadata.

    stale = monitors.stale_docs(load_corpus_docs(), max_age_days=90)
    if stale:
        doc, age = stale[0]
        parts.append(
            f"Your corpus's {doc.title} was last verified {age} days ago — "
            "answers on that topic are being held more often; consider refreshing it."
        )

    # Volume note.
    held = sum(1 for v in verdicts if v.decision == Decision.QUARANTINE)
    if held:
        parts.append(
            f"{held} answer(s) were held this period; each is in your review queue with the "
            "claim and the contradicting source side by side."
        )
    if not parts:
        parts.append("No notable drift this period. Your assistant's answers held steady.")
    return " ".join(parts)


def generate_trust_report(
    store: QuarantineStore,
    *,
    org_id: str = "riverside",
    org_name: str = "Riverside Community Legal Aid",
    week_of: str | None = None,
) -> TrustReport:
    """Build the Trust Report for an org from its persisted verdicts."""
    verdicts = store.list_verdicts(org_id=org_id, limit=1000)
    stats = monitors.topic_stats(verdicts)
    riskiest, safest = monitors.riskiest_and_safest(stats)

    total = len(verdicts)
    cleared = sum(1 for v in verdicts if v.decision == Decision.ALLOW)
    corrected = sum(1 for v in verdicts if v.decision == Decision.REPAIR_ALLOW)
    quarantined = [v for v in verdicts if v.decision == Decision.QUARANTINE]
    # "Held" is what still needs the team's eyes; once a director acts on an item
    # it moves to "reviewed" — so clearing the queue updates the report.
    held = sum(1 for v in quarantined if v.review_status == ReviewStatus.PENDING)
    reviewed = sum(1 for v in quarantined if v.review_status != ReviewStatus.PENDING)

    now = datetime.now(UTC)
    report = TrustReport(
        org_name=org_name,
        week_of=week_of or now.date().isoformat(),
        generated_at=now.isoformat(),
        total_answered=total,
        cleared=cleared,
        corrected=corrected,
        held=held,
        reviewed=reviewed,
        headline=f"This week, your assistant answered {total} question{'s' if total != 1 else ''}.",
        what_was_caught=_caught_bullets(verdicts),
        trend=_trend(verdicts),
        riskiest_topic=riskiest,
        safest_topic=safest,
        corpus_gaps=monitors.corpus_gap_topics(verdicts),
        topic_stats=stats,
    )
    logger.info(
        "trust report: org=%s total=%d cleared=%d corrected=%d held=%d",
        org_id,
        total,
        cleared,
        corrected,
        held,
    )
    return report
