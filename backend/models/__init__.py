"""Pydantic contract for Sentinel.

Every boundary crossing — API, agent output, corpus retrieval, eval, store — is
a Pydantic-validated payload. The frontend renders typed components from these
models (generated to TypeScript via ``scripts/generate_typescript_types.py``).
"""

from backend.models.casa import CasaAnswer, CasaRequest
from backend.models.claim import Claim, ClaimExtraction, ClaimType
from backend.models.corpus import CorpusChunk, CorpusDoc
from backend.models.evaluation import EvalKind, EvalResult
from backend.models.grounding import GroundingResult, GroundingStatus, SourcePassage
from backend.models.request import AskRequest, ReviewAction, ReviewActionType
from backend.models.streaming import (
    AgentActivity,
    CasaDrafted,
    ClaimExtracted,
    DoneSignal,
    EvalScored,
    GroundingChecked,
    PlanWritten,
    StreamError,
    TriageReady,
    VerdictDecided,
)
from backend.models.triage import (
    Coverage,
    PlanStep,
    SentinelPlan,
    Specificity,
    StakesLevel,
    TriageVerdict,
)
from backend.models.trust_report import TopicStat, TrustReport
from backend.models.verdict import Decision, ReviewStatus, SentinelVerdict

__all__ = [
    # casa
    "CasaRequest",
    "CasaAnswer",
    # claim
    "Claim",
    "ClaimExtraction",
    "ClaimType",
    # corpus
    "CorpusChunk",
    "CorpusDoc",
    # evaluation
    "EvalKind",
    "EvalResult",
    # grounding
    "GroundingResult",
    "GroundingStatus",
    "SourcePassage",
    # request
    "AskRequest",
    "ReviewAction",
    "ReviewActionType",
    # triage
    "Coverage",
    "PlanStep",
    "SentinelPlan",
    "Specificity",
    "StakesLevel",
    "TriageVerdict",
    # trust report
    "TopicStat",
    "TrustReport",
    # verdict
    "Decision",
    "ReviewStatus",
    "SentinelVerdict",
    # streaming
    "AgentActivity",
    "CasaDrafted",
    "ClaimExtracted",
    "DoneSignal",
    "EvalScored",
    "GroundingChecked",
    "PlanWritten",
    "StreamError",
    "TriageReady",
    "VerdictDecided",
]
