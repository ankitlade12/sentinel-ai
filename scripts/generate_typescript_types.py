"""Generate TypeScript types from the Pydantic contract.

Emits ``frontend/types/generated.ts`` from the backend models so the dashboard
renders strongly-typed components and never drifts from the API. Self-contained:
walks each model's JSON schema and converts it to TS interfaces + string-literal
union enums — no Node toolchain required (run via ``make types``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.models import (
    AskRequest,
    CasaAnswer,
    CasaRequest,
    Claim,
    ClaimExtraction,
    CorpusDoc,
    EvalResult,
    GroundingResult,
    ReviewAction,
    SentinelPlan,
    SentinelVerdict,
    SourcePassage,
    TriageVerdict,
    TrustReport,
)
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
from pydantic import BaseModel

OUTPUT = Path(__file__).resolve().parents[1] / "frontend" / "types" / "generated.ts"

# Root models to export; nested models/enums are pulled in via $defs.
ROOTS: list[type[BaseModel]] = [
    TriageVerdict,
    SentinelPlan,
    Claim,
    ClaimExtraction,
    SourcePassage,
    GroundingResult,
    EvalResult,
    SentinelVerdict,
    TrustReport,
    CorpusDoc,
    CasaRequest,
    CasaAnswer,
    AskRequest,
    ReviewAction,
    AgentActivity,
    CasaDrafted,
    TriageReady,
    PlanWritten,
    ClaimExtracted,
    GroundingChecked,
    EvalScored,
    VerdictDecided,
    DoneSignal,
    StreamError,
]


def _collect_schemas() -> dict[str, dict[str, Any]]:
    """Merge every root model's JSON schema (+ its $defs) into one name→schema map."""
    schemas: dict[str, dict[str, Any]] = {}
    for model in ROOTS:
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        for name, defn in schema.pop("$defs", {}).items():
            schemas.setdefault(name, defn)
        schemas.setdefault(schema.get("title", model.__name__), schema)
    return schemas


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _ts_type(prop: dict[str, Any]) -> str:
    if "$ref" in prop:
        return _ref_name(prop["$ref"])
    if "anyOf" in prop:
        parts = [_ts_type(p) for p in prop["anyOf"] if p.get("type") != "null"]
        union = " | ".join(dict.fromkeys(parts)) or "unknown"
        return union  # nullability handled by the caller (optional marker)
    if "enum" in prop:
        return " | ".join(f'"{v}"' for v in prop["enum"])
    type_ = prop.get("type")
    if type_ == "array":
        return f"{_ts_type(prop.get('items', {}))}[]"
    if type_ == "object":
        extra = prop.get("additionalProperties")
        inner = _ts_type(extra) if isinstance(extra, dict) else "unknown"
        return f"Record<string, {inner}>"
    return {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }.get(type_, "unknown")


def _is_optional(prop: dict[str, Any]) -> bool:
    return "null" in [p.get("type") for p in prop.get("anyOf", [])]


def _emit(name: str, schema: dict[str, Any]) -> str:
    # String-literal union for StrEnum-style schemas.
    if "enum" in schema and schema.get("type") == "string":
        union = " | ".join(f'"{v}"' for v in schema["enum"])
        return f"export type {name} = {union};\n"

    if schema.get("type") != "object":
        return f"export type {name} = {_ts_type(schema)};\n"

    required = set(schema.get("required", []))
    lines = [f"export interface {name} {{"]
    for field, prop in schema.get("properties", {}).items():
        optional = field not in required or _is_optional(prop)
        marker = "?" if optional else ""
        ts = _ts_type(prop)
        if _is_optional(prop) and "null" not in ts:
            ts = f"{ts} | null"
        lines.append(f"  {field}{marker}: {ts};")
    lines.append("}\n")
    return "\n".join(lines)


def main() -> None:
    schemas = _collect_schemas()
    header = (
        "// AUTO-GENERATED from backend Pydantic models by "
        "scripts/generate_typescript_types.py\n// Do not edit by hand — run `make types`.\n\n"
    )
    body = "\n".join(_emit(name, schema) for name, schema in sorted(schemas.items()))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(header + body, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(schemas)} types)")


if __name__ == "__main__":
    main()
