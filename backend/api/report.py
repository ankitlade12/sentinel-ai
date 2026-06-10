"""Trust Report + corpus endpoints for the director dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.deps import get_corpus_dep, get_store_dep
from backend.connectors.protocol import CorpusConnector
from backend.connectors.store_protocol import QuarantineStore
from backend.corpus.loader import load_corpus_docs
from backend.models.corpus import CorpusDoc
from backend.models.trust_report import TrustReport
from backend.reports.trust_report import generate_trust_report

router = APIRouter(tags=["report"])


@router.get("/report", response_model=TrustReport)
def trust_report(
    store: Annotated[QuarantineStore, Depends(get_store_dep)],
    org_id: str = "riverside",
) -> TrustReport:
    """Generate the weekly Trust Report from accumulated verdicts."""
    return generate_trust_report(store, org_id=org_id)


@router.get("/corpus", response_model=list[CorpusDoc])
def corpus_documents(
    corpus: Annotated[CorpusConnector, Depends(get_corpus_dep)],
    org_id: str = "riverside",
) -> list[CorpusDoc]:
    """List the trusted documents and their last-verified dates (corpus-gap panel)."""
    # Prefer the live connector's view; fall back to the on-disk manifest.
    docs = corpus.documents()
    return docs or load_corpus_docs(org_id)
