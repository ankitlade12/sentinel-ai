"""Function tools for the Sentinel ADK agent.

These are plain, well-documented Python functions — Google ADK introspects their
signatures and docstrings to expose them to Gemini. They return JSON-serializable
dicts. The corpus and store are built once and reused across tool calls.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from backend.agents import claim_extractor, grounding, triage
from backend.arize import evals, mcp
from backend.config import get_corpus, get_store
from backend.connectors.protocol import CorpusConnector
from backend.connectors.store_protocol import QuarantineStore
from backend.models.claim import Claim, ClaimType
from backend.models.evaluation import EvalKind

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _corpus() -> CorpusConnector:
    return get_corpus()


@lru_cache(maxsize=1)
def _store() -> QuarantineStore:
    return get_store()


def triage_answer(question: str, draft_answer: str) -> dict[str, Any]:
    """Classify a chatbot answer's stakes, specificity, and corpus coverage, and
    return a written plan with the path to take (light vs full).

    Args:
        question: The end user's question.
        draft_answer: The chatbot's draft answer to evaluate.

    Returns:
        The triage verdict and the agent's plan as a dict.
    """
    plan = triage.triage(question, draft_answer, corpus=_corpus())
    return plan.model_dump(mode="json")


def extract_claims(draft_answer: str) -> dict[str, Any]:
    """Decompose a draft answer into atomic, checkable claims.

    Args:
        draft_answer: The chatbot's draft answer.

    Returns:
        A dict with the list of claims and a summary.
    """
    return claim_extractor.extract_claims(draft_answer).model_dump(mode="json")


def ground_claim(claim_text: str, claim_type: str = "other", subject: str = "") -> dict[str, Any]:
    """Check one claim against the organization's trusted corpus only.

    Returns supported / contradicted / not_found with the cited source passages.
    'not_found' is a risk signal, not a pass.

    Args:
        claim_text: The atomic assertion to check.
        claim_type: One of date, deadline, amount, form_number, eligibility,
            legal_rule, procedure, contact, other.
        subject: What the claim is about (optional).

    Returns:
        The grounding result as a dict, including the source passages.
    """
    try:
        ctype = ClaimType(claim_type)
    except ValueError:
        ctype = ClaimType.OTHER
    claim = Claim(
        id="c1", text=claim_text, claim_type=ctype, subject=subject or claim_text, checkable=True
    )
    return grounding.ground_claim(claim, corpus=_corpus()).model_dump(mode="json")


def run_quality_evals(question: str, answer: str) -> dict[str, Any]:
    """Run the Phoenix hallucination + QA-correctness evals on an answer, using
    the trusted corpus as the ground-truth reference.

    Args:
        question: The user's question.
        answer: The answer to evaluate.

    Returns:
        A dict mapping each eval kind to its label, score, and pass/fail.
    """
    reference = _corpus().retrieve(question, k=4)
    results = evals.run_evals(
        question, answer, reference, kinds=[EvalKind.HALLUCINATION, EvalKind.QA_CORRECTNESS]
    )
    return {r.kind.value: r.model_dump(mode="json") for r in results}


def check_topic_history(topic: str, org_id: str = "riverside") -> dict[str, Any]:
    """Read back how a topic has been performing (quarantine rate, drift) so the
    agent can adapt its threshold — the self-improvement / monitoring-as-memory loop.

    Args:
        topic: The topic label to look up.
        org_id: The organization id (default 'riverside').

    Returns:
        A TopicHealth dict: samples, quarantine_rate, risk_adjustment, source.
    """
    return mcp.topic_health(topic, _store(), org_id=org_id).model_dump(mode="json")


# The toolset the ADK agent is configured with.
SENTINEL_TOOLS = [
    triage_answer,
    extract_claims,
    ground_claim,
    run_quality_evals,
    check_topic_history,
]
