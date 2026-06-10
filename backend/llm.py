"""Shared Gemini client for Sentinel agents.

Single entry point for all reasoning calls — triage, claim extraction, the
grounding judge, eval rationales, and Trust Report prose. Two reasons it is
centralized:

1. **Determinism.** Pipeline-critical calls run at ``temperature=0`` so the
   same draft answer triages and grounds the same way every time.
2. **Observability.** Every call here is auto-traced by the OpenInference
   GenAI instrumentor (see ``backend/arize/tracing.py``), which is what makes
   Arize structural rather than decorative — the trace *is* the audit trail.

The ``google-genai`` import is deferred so the package imports cleanly in the
hermetic test tier, where agents are exercised with a stubbed LLM and no Gemini
credentials are present.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import BaseModel

from backend.config import get_settings

if TYPE_CHECKING:
    from google.genai import Client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_genai_client() -> Client:
    """Build the Gemini client for the configured provider.

    - ``vertex``    → Vertex AI backend, authenticated via Application Default
      Credentials (the demo + production path).
    - ``ai_studio`` → Google AI Studio backend, authenticated via ``GEMINI_API_KEY``.
    """
    from google import genai

    settings = get_settings()
    if settings.llm_provider == "vertex":
        if not settings.google_cloud_project:
            raise RuntimeError(
                "SENTINEL_LLM_PROVIDER=vertex requires GOOGLE_CLOUD_PROJECT to be set."
            )
        return genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
    if not settings.gemini_api_key:
        raise RuntimeError("SENTINEL_LLM_PROVIDER=ai_studio requires GEMINI_API_KEY to be set.")
    return genai.Client(api_key=settings.gemini_api_key)


def generate_structured[T: BaseModel](
    schema: type[T],
    *,
    system: str,
    prompt: str,
    temperature: float = 0.0,
    model: str | None = None,
) -> T:
    """Call Gemini with hard structured output and return a validated model.

    Uses ``response_schema`` so Gemini emits JSON conforming to ``schema``; the
    result is parsed and Pydantic-validated. Raises on a response that cannot be
    coerced into ``schema`` — callers never receive free-text.
    """
    from google.genai import types

    settings = get_settings()
    client = get_genai_client()
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema,
    )
    response = client.models.generate_content(
        model=model or settings.gemini_model,
        contents=prompt,
        config=config,
    )

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty structured response.")
    logger.debug("structured: falling back to manual JSON parse for %s", schema.__name__)
    return schema.model_validate(json.loads(text))


def generate_text(
    *,
    system: str,
    prompt: str,
    temperature: float = 0.0,
    model: str | None = None,
) -> str:
    """Call Gemini for free-text output (Trust Report prose, CASA answers)."""
    from google.genai import types

    settings = get_settings()
    client = get_genai_client()
    config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    response = client.models.generate_content(
        model=model or settings.gemini_model,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()
