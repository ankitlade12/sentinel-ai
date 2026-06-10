"""Role 3 — Monitoring as memory (the self-improvement loop).

The agent reads back its own accumulated verdicts to compute per-topic
quarantine rates, and feeds that history back into the decision: a topic whose
failure rate is rising raises the support bar, so borderline answers on a
drifting topic are held more readily. This is the bonus criterion — an agent
that uses its own observability data to improve.

These aggregations also render the Trust Report's trend, riskiest/safest, and
corpus-gap sections. The numbers come from the verdict store (durable in
Firestore); the Phoenix MCP server (``mcp.py``) is the runtime-introspection
parity path that exposes the same data to the LLM agent at decision time.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.connectors.store_protocol import QuarantineStore
from backend.models.corpus import CorpusDoc
from backend.models.grounding import GroundingStatus
from backend.models.trust_report import TopicStat
from backend.models.verdict import Decision, SentinelVerdict

logger = logging.getLogger(__name__)

# How much a fully-drifting topic can raise the support bar.
_MAX_ADJUSTMENT = 0.15
_MIN_SAMPLES = 4


def recent_verdicts(
    store: QuarantineStore, *, org_id: str, limit: int = 500
) -> list[SentinelVerdict]:
    return store.list_verdicts(org_id=org_id, limit=limit)


def topic_risk_adjustment(topic: str, store: QuarantineStore, *, org_id: str) -> float:
    """Return a non-negative threshold bump for a topic that has been failing.

    Quarantine rate 0.20 → no bump; 0.50+ → the full +0.15 bump. Below the
    sample floor, returns 0 (not enough history to adapt on).
    """
    verdicts = [
        v for v in recent_verdicts(store, org_id=org_id) if v.topic.lower() == topic.lower()
    ]
    if len(verdicts) < _MIN_SAMPLES:
        return 0.0
    held = sum(1 for v in verdicts if v.decision == Decision.QUARANTINE)
    rate = held / len(verdicts)
    adjustment = max(0.0, min(_MAX_ADJUSTMENT, (rate - 0.20) * 0.5))
    if adjustment > 0:
        logger.info(
            "monitors: topic=%r quarantine_rate=%.2f → risk_adjustment=+%.3f (n=%d)",
            topic,
            rate,
            adjustment,
            len(verdicts),
        )
    return round(adjustment, 4)


def topic_stats(verdicts: list[SentinelVerdict]) -> list[TopicStat]:
    """Aggregate verdicts into per-topic counts (newest-first input is fine)."""
    by_topic: dict[str, TopicStat] = {}
    for v in verdicts:
        stat = by_topic.setdefault(v.topic, TopicStat(topic=v.topic))
        stat.answered += 1
        if v.decision == Decision.ALLOW:
            stat.cleared += 1
        elif v.decision == Decision.REPAIR_ALLOW:
            stat.corrected += 1
        elif v.decision == Decision.QUARANTINE:
            stat.held += 1
    return sorted(by_topic.values(), key=lambda s: s.answered, reverse=True)


def riskiest_and_safest(stats: list[TopicStat]) -> tuple[str, str]:
    """Return (riskiest_topic, safest_topic) by quarantine rate, ties broken by volume."""
    eligible = [s for s in stats if s.answered >= 1]
    if not eligible:
        return "", ""
    riskiest = max(eligible, key=lambda s: (s.quarantine_rate, s.answered))
    safest = min(eligible, key=lambda s: (s.quarantine_rate, -s.answered))
    return riskiest.topic, safest.topic


def corpus_gap_topics(verdicts: list[SentinelVerdict]) -> list[str]:
    """Topics where a claim was 'not found' in the corpus — i.e. coverage gaps."""
    gaps: set[str] = set()
    for v in verdicts:
        if any(g.status == GroundingStatus.NOT_FOUND for g in v.grounding):
            gaps.add(v.topic)
    return sorted(gaps)


def stale_docs(docs: list[CorpusDoc], *, max_age_days: int = 90) -> list[tuple[CorpusDoc, int]]:
    """Return (doc, age_in_days) for documents last verified more than N days ago."""
    today = datetime.now(UTC).date()
    stale: list[tuple[CorpusDoc, int]] = []
    for doc in docs:
        try:
            verified = datetime.fromisoformat(doc.last_verified).date()
        except ValueError:
            continue
        age = (today - verified).days
        if age > max_age_days:
            stale.append((doc, age))
    return sorted(stale, key=lambda pair: pair[1], reverse=True)
