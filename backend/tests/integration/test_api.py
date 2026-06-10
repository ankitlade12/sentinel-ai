"""Integration tests for the FastAPI surface (TestClient, stubbed LLM)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client(stub_llm):
    from backend.main import create_app

    return TestClient(create_app())


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ask_quarantines_hero(client):
    resp = client.post("/api/ask", json={"question": "When do I have to renew my green card?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["draft"]["answer"]  # CASA's intercepted draft
    assert body["verdict"]["decision"] == "quarantine"
    assert body["verdict"]["trace_id"] is None or isinstance(body["verdict"]["trace_id"], str)


def test_ask_allows_office_hours(client):
    resp = client.post("/api/ask", json={"question": "What are your office hours?"})
    assert resp.status_code == 200
    assert resp.json()["verdict"]["decision"] == "allow"


def test_quarantine_queue_and_resolve(client):
    client.post("/api/ask", json={"question": "When do I have to renew my green card?"})
    queue = client.get("/api/quarantine").json()
    assert queue, "expected a quarantined item in the queue"
    verdict_id = queue[0]["id"]

    resolved = client.post(
        f"/api/quarantine/{verdict_id}/resolve",
        json={"action": "release", "staff_id": "alex", "staff_note": "verified"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["review_status"] == "released"
    # No longer pending.
    assert client.get("/api/quarantine").json() == []


def test_trust_report_endpoint(client):
    client.post("/api/ask", json={"question": "When do I have to renew my green card?"})
    report = client.get("/api/report").json()
    assert report["total_answered"] >= 1
    assert "disclaimer" in report


def test_corpus_endpoint(client):
    docs = client.get("/api/corpus").json()
    assert docs and any("i90" in d["id"].lower() for d in docs)
