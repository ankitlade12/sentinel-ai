"""Build / refresh the trusted-corpus vector index.

- With ``SENTINEL_CORPUS=vertex`` and a configured managed index, this embeds
  every chunk with Vertex AI and upserts the datapoints into Vertex AI Vector
  Search (so retrieval is served by the managed index).
- Otherwise it loads + chunks + (optionally) embeds the corpus and prints a
  summary, which is enough for the embeddings-only fallback and for verifying
  the corpus parses and chunks correctly.
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv(override=False)

from backend.config import get_settings  # noqa: E402
from backend.corpus.loader import load_corpus_chunks, load_corpus_docs  # noqa: E402

logging.basicConfig(level="INFO", format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("index_corpus")


def _upsert_managed(chunks: list, settings) -> None:
    from backend.vectorstore.embeddings import VertexEmbedder
    from google.cloud import aiplatform

    embedder = VertexEmbedder(settings.embedding_model)
    matrix = embedder.embed([c.text for c in chunks])
    index = aiplatform.MatchingEngineIndex(settings.vertex_vector_index_endpoint)
    datapoints = [
        {"datapoint_id": chunk.id, "feature_vector": matrix[i].tolist()}
        for i, chunk in enumerate(chunks)
    ]
    index.upsert_datapoints(datapoints=datapoints)
    logger.info("upserted %d datapoints into Vertex Vector Search", len(datapoints))


def main() -> None:
    settings = get_settings()
    docs = load_corpus_docs()
    chunks = load_corpus_chunks()
    logger.info("corpus: %d documents, %d chunks", len(docs), len(chunks))
    for doc in docs:
        logger.info("  - %s (%s, verified %s)", doc.title, doc.topic, doc.last_verified)

    if settings.corpus_backend == "vertex" and settings.vertex_vector_index_endpoint:
        _upsert_managed(chunks, settings)
    else:
        logger.info(
            "No managed Vertex index configured; using embeddings-only retrieval. "
            "Set VERTEX_VECTOR_INDEX_ENDPOINT + VERTEX_VECTOR_DEPLOYED_INDEX_ID to upsert."
        )


if __name__ == "__main__":
    main()
