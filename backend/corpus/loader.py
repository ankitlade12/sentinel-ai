"""Load and chunk the trusted-corpus markdown documents.

Each document carries YAML frontmatter (id, title, topic, source_url,
last_verified). The body is split into retrieval chunks that each inherit the
document's provenance, so every chunk can be cited with its source and
last-verified date.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from backend.models.corpus import CorpusChunk, CorpusDoc

logger = logging.getLogger(__name__)

CORPUS_ROOT = Path(__file__).parent
_TARGET_CHARS = 700  # soft upper bound per chunk


def _corpus_dir(org_id: str) -> Path:
    return CORPUS_ROOT / org_id


def _parse_frontmatter(raw: str, *, path: Path) -> tuple[dict[str, str], str]:
    """Split ``---`` frontmatter from the markdown body."""
    if not raw.startswith("---"):
        raise ValueError(f"corpus doc missing frontmatter: {path}")
    _, fm, body = raw.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    return meta, body.strip()


def _chunk_body(body: str) -> list[str]:
    """Group markdown blocks into ~700-char chunks, keeping headings attached."""
    blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for block in blocks:
        is_heading = block.startswith("#")
        # Start a fresh chunk at a heading boundary if the current one has body.
        if is_heading and size > 0:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block)
        if size >= _TARGET_CHARS and not is_heading:
            chunks.append("\n\n".join(current))
            current, size = [], 0
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def load_corpus_docs(org_id: str = "riverside") -> list[CorpusDoc]:
    """Return document-level metadata for every trusted doc in the org's corpus."""
    docs: list[CorpusDoc] = []
    for path in sorted(_corpus_dir(org_id).glob("*.md")):
        meta, _ = _parse_frontmatter(path.read_text(encoding="utf-8"), path=path)
        docs.append(
            CorpusDoc(
                id=str(meta["id"]),
                title=str(meta["title"]),
                topic=str(meta["topic"]),
                source_url=meta.get("source_url"),
                last_verified=str(meta["last_verified"]),
                path=str(path.relative_to(CORPUS_ROOT)),
            )
        )
    return docs


def load_corpus_chunks(org_id: str = "riverside") -> list[CorpusChunk]:
    """Return embeddable chunks for every trusted doc, with provenance attached."""
    chunks: list[CorpusChunk] = []
    for path in sorted(_corpus_dir(org_id).glob("*.md")):
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"), path=path)
        for i, text in enumerate(_chunk_body(body)):
            chunks.append(
                CorpusChunk(
                    id=f"{meta['id']}::{i}",
                    doc_id=str(meta["id"]),
                    doc_title=str(meta["title"]),
                    topic=str(meta["topic"]),
                    source_url=meta.get("source_url"),
                    page=None,
                    last_verified=str(meta["last_verified"]),
                    text=text,
                )
            )
    logger.info("corpus: loaded %d chunks for org=%s", len(chunks), org_id)
    return chunks
