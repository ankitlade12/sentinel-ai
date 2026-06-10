"""The Sentinel orchestrator — runs the full agent loop for one answer.

This is the deterministic, streamable production path the API uses. It executes
the visible plan (different paths for different inputs), calls each tool, applies
the org's decision policy, repairs-or-holds, and persists one auditable verdict
wrapped in one Phoenix trace. An optional ``emit`` callback receives typed wire
events so the dashboard can render the run progressively.

The same underlying step functions are exposed to a Google ADK ``LlmAgent`` in
``adk_agent.py`` — that is the code-owned agent runtime the Arize track requires;
this orchestrator is its reliable, instrumented sibling.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from backend.agents import claim_extractor, decide, grounding, repair, triage
from backend.arize import evals, monitors
from backend.arize.tracing import agent_span, record_evals
from backend.config import Settings, get_corpus, get_settings, get_store
from backend.connectors.protocol import CorpusConnector
from backend.connectors.store_protocol import QuarantineStore
from backend.models.evaluation import EvalKind, EvalResult
from backend.models.grounding import GroundingResult, GroundingStatus, SourcePassage
from backend.models.streaming import (
    AgentActivity,
    ClaimExtracted,
    DoneSignal,
    EvalScored,
    GroundingChecked,
    PlanWritten,
    TriageReady,
    VerdictDecided,
)
from backend.models.verdict import Decision, SentinelVerdict

logger = logging.getLogger(__name__)

Emit = Callable[[BaseModel], None]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dedupe_passages(grounding_results: list[GroundingResult]) -> list[SourcePassage]:
    seen: set[tuple[str, str]] = set()
    passages: list[SourcePassage] = []
    for g in grounding_results:
        for p in g.passages:
            key = (p.doc_id, p.text)
            if key not in seen:
                seen.add(key)
                passages.append(p)
    return passages


class SentinelAgent:
    """Runs the guardian loop over a single (question, draft answer) pair."""

    def __init__(
        self,
        *,
        corpus: CorpusConnector,
        store: QuarantineStore,
        settings: Settings,
    ) -> None:
        self.corpus = corpus
        self.store = store
        self.settings = settings

    def run(
        self,
        question: str,
        draft_answer: str,
        *,
        org_id: str = "riverside",
        emit: Emit | None = None,
    ) -> SentinelVerdict:
        """Execute the loop and return the persisted verdict."""
        started = datetime.now(UTC)

        def _emit(event: BaseModel) -> None:
            if emit is not None:
                emit(event)

        with agent_span(
            "sentinel.run",
            {"sentinel.question": question, "sentinel.org_id": org_id},
        ) as span:
            # ── Step 1 — TRIAGE + PLAN ──
            _emit(
                AgentActivity(
                    activity_type="triage",
                    summary="Classifying stakes, specificity, and corpus coverage…",
                )
            )
            plan = triage.triage(question, draft_answer, corpus=self.corpus)
            _emit(TriageReady(triage=plan.triage))
            _emit(PlanWritten(plan=plan))
            _emit(
                AgentActivity(
                    activity_type="plan", summary=plan.summary, detail={"path": plan.path}
                )
            )
            span.set_attribute("sentinel.path", plan.path)
            span.set_attribute("sentinel.stakes", plan.triage.stakes.value)
            span.set_attribute("sentinel.topic", plan.triage.topic)

            claims_list = []
            grounding_results: list[GroundingResult] = []
            eval_results: list[EvalResult] = []

            if plan.path == "full":
                # ── Step 2, tool 1 — CLAIMS ──
                _emit(
                    AgentActivity(
                        activity_type="tool_call",
                        summary="Extracting atomic claims…",
                        detail={"tool": "claim_extractor"},
                    )
                )
                extraction = claim_extractor.extract_claims(draft_answer)
                claims_list = extraction.claims
                for claim in claims_list:
                    _emit(ClaimExtracted(claim=claim))

                # ── Step 2, tool 2 — GROUNDING ──
                _emit(
                    AgentActivity(
                        activity_type="tool_call",
                        summary="Ground-checking each claim against the trusted corpus…",
                        detail={"tool": "corpus_grounding"},
                    )
                )
                for claim in claims_list:
                    if not claim.checkable:
                        continue
                    result = grounding.ground_claim(claim, corpus=self.corpus)
                    grounding_results.append(result)
                    _emit(GroundingChecked(result=result))

                # ── Step 2, tool 3 — EVALS (decision input) ──
                reference = _dedupe_passages(grounding_results) or self.corpus.retrieve(
                    question, k=4
                )
                _emit(
                    AgentActivity(
                        activity_type="tool_call",
                        summary="Running Phoenix hallucination + QA-correctness evals…",
                        detail={"tool": "arize_evals"},
                    )
                )
                eval_results = evals.run_evals(
                    question,
                    draft_answer,
                    reference,
                    kinds=[EvalKind.HALLUCINATION, EvalKind.QA_CORRECTNESS],
                )
                for e in eval_results:
                    _emit(EvalScored(result=e))
            else:
                # ── Light path — safety check only ──
                _emit(
                    AgentActivity(
                        activity_type="tool_call",
                        summary="Running a light safety check…",
                        detail={"tool": "toxicity_eval"},
                    )
                )
                eval_results = evals.run_evals(
                    question, draft_answer, [], kinds=[EvalKind.TOXICITY]
                )
                for e in eval_results:
                    _emit(EvalScored(result=e))

            # ── Step 2, tool 4 — RISK HISTORY (monitoring as memory) ──
            risk_adjustment = monitors.topic_risk_adjustment(
                plan.triage.topic, self.store, org_id=org_id
            )
            if risk_adjustment > 0:
                _emit(
                    AgentActivity(
                        activity_type="tool_call",
                        summary=f"This topic has been drifting — tightening the support bar by +{risk_adjustment:.2f}.",
                        detail={"tool": "risk_history", "risk_adjustment": risk_adjustment},
                    )
                )

            # ── Step 3 — DECIDE ──
            outcome = decide.decide(
                plan=plan,
                grounding=grounding_results,
                evals=eval_results,
                settings=self.settings,
                risk_adjustment=risk_adjustment,
            )

            # Assemble the delivered answer per the decision.
            corrected_answer: str | None = None
            if outcome.should_repair:
                correctable = [
                    g
                    for g in grounding_results
                    if g.status == GroundingStatus.CONTRADICTED and g.corrected_text
                ]
                corrected_answer, _ = repair.draft_repair(question, correctable)
                delivered = corrected_answer
            elif outcome.decision == Decision.QUARANTINE:
                delivered = outcome.user_message or decide.QUARANTINE_FALLBACK
            else:
                delivered = draft_answer

            latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            verdict = SentinelVerdict(
                id=uuid.uuid4().hex,
                org_id=org_id,
                created_at=_now(),
                question=question,
                draft_answer=draft_answer,
                topic=plan.triage.topic,
                plan=plan,
                claims=claims_list,
                grounding=grounding_results,
                evals=eval_results,
                decision=outcome.decision,
                delivered_answer=delivered,
                user_message=outcome.user_message,
                corrected_answer=corrected_answer,
                rationale=outcome.rationale,
                failed_claim_ids=outcome.failed_claim_ids,
                requires_human_review=outcome.requires_human_review,
                trace_id=span.trace_id,
                trace_url=span.trace_url,
                latency_ms=latency_ms,
                policy_snapshot={
                    "quarantine_threshold": self.settings.quarantine_threshold,
                    "hallucination_threshold": self.settings.hallucination_threshold,
                    "risk_adjustment": risk_adjustment,
                    "effective_threshold": min(
                        1.0, self.settings.quarantine_threshold + risk_adjustment
                    ),
                },
            )

            record_evals(span, eval_results)
            span.set_attribute("sentinel.decision", verdict.decision.value)
            span.set_attribute("sentinel.requires_human_review", verdict.requires_human_review)

            self.store.save_verdict(verdict)
            logger.info(
                "verdict id=%s decision=%s topic=%r latency_ms=%d",
                verdict.id,
                verdict.decision,
                verdict.topic,
                latency_ms,
            )
            _emit(VerdictDecided(verdict=verdict))
            _emit(DoneSignal(verdict_id=verdict.id, decision=verdict.decision))
            return verdict


def build_default_agent() -> SentinelAgent:
    """Construct a SentinelAgent from the configured corpus/store/settings."""
    return SentinelAgent(corpus=get_corpus(), store=get_store(), settings=get_settings())
