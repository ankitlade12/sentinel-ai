"""Load agent system prompts from ``backend/agents/prompts/*.md``.

Keeping prompts as markdown files (rather than inline strings) makes them
reviewable in diffs and editable without touching code — the same convention
GoldMind uses for its agent prompts.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@cache
def load_prompt(name: str) -> str:
    """Return the text of ``prompts/{name}.md``."""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()
