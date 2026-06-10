"""Contract tests for the corpus connector.

Runs against the mock connector by default. The same assertions hold for the
Vertex connector (marked live) when GOOGLE_CLOUD_PROJECT is configured.
"""

from __future__ import annotations

import pytest

from backend.connectors.mock_corpus import MockCorpusConnector
from backend.connectors.protocol import CorpusConnector
from backend.models.corpus import CorpusDoc
from backend.models.grounding import SourcePassage

pytestmark = pytest.mark.contract


@pytest.fixture
def corpus() -> CorpusConnector:
    return MockCorpusConnector()


def test_satisfies_protocol(corpus):
    assert isinstance(corpus, CorpusConnector)


def test_retrieve_returns_cited_passages(corpus):
    passages = corpus.retrieve("green card I-90 renewal 30 days", k=3)
    assert passages, "expected at least one passage"
    assert all(isinstance(p, SourcePassage) for p in passages)
    top = passages[0]
    assert top.doc_title
    assert top.last_verified  # provenance is always present
    assert 0.0 <= top.score <= 1.0


def test_retrieval_surfaces_relevant_document(corpus):
    # The hashing embedder is lexical, but should still rank the I-90 doc first
    # for an I-90 query and the FAQ first for an office-hours query.
    i90 = corpus.retrieve("I-90 green card renewal deadline", k=1)[0]
    assert "i-90" in i90.doc_id.lower() or "green" in i90.doc_title.lower()
    hours = corpus.retrieve("what are your office hours", k=1)[0]
    assert "faq" in hours.doc_id.lower() or "hours" in hours.text.lower()


def test_coverage_in_range(corpus):
    assert 0.0 <= corpus.coverage("I-90 renewal") <= 1.0
    assert corpus.coverage("quantum chromodynamics lattice gauge theory") < corpus.coverage(
        "green card renewal"
    )


def test_topics_and_documents(corpus):
    assert set(corpus.topics()) >= {"immigration", "benefits", "housing", "intake"}
    docs = corpus.documents()
    assert docs and all(isinstance(d, CorpusDoc) for d in docs)
