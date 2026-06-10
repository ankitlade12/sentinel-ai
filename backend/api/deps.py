"""FastAPI dependency providers.

The corpus connector, quarantine store, CASA bot, and Sentinel agent are
constructed once at app startup and stored on ``app.state`` (see
``backend/main.py``); handlers retrieve them through these providers so routes
stay thin and testable.
"""

from __future__ import annotations

from typing import cast

from fastapi import Request

from backend.agents.sentinel import SentinelAgent
from backend.casa.bot import CasaBot
from backend.connectors.protocol import CorpusConnector
from backend.connectors.store_protocol import QuarantineStore


def get_agent_dep(request: Request) -> SentinelAgent:
    return cast(SentinelAgent, request.app.state.agent)


def get_store_dep(request: Request) -> QuarantineStore:
    return cast(QuarantineStore, request.app.state.store)


def get_corpus_dep(request: Request) -> CorpusConnector:
    return cast(CorpusConnector, request.app.state.corpus)


def get_casa_dep(request: Request) -> CasaBot:
    return cast(CasaBot, request.app.state.casa)
