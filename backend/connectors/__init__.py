"""Connectors — the swap points between hermetic and cloud-backed backends.

- Corpus: :class:`CorpusConnector` (mock in-memory RAG vs Vertex AI Vector Search)
- Store:  :class:`QuarantineStore` (mock in-memory vs Firestore)

Agents and API handlers depend on the protocols here, never on a concrete
implementation. ``backend.config.get_corpus()`` / ``get_store()`` choose which
one is live, exactly as GoldMind's ``get_connector()`` selects mock vs Databricks.
"""
