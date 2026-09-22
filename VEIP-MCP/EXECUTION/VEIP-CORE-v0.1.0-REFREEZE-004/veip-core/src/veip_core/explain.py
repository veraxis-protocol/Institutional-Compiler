"""Deterministic, non-strengthening boundary explanation."""

from __future__ import annotations

from typing import Any

from .canonical import sha256
from .errors import ENGINE_VERSION, EngineError
from .reasons import REGISTRY
from .schema import ValidationFailure, validate_definition


def explain_boundary(request_json: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_definition(request_json, "ExplanationRequest")
    except (ValidationFailure, TypeError, ValueError) as exc:
        raise EngineError("SCHEMA_INVALID", f"Request failed frozen schema validation: {exc}") from None

    if request_json.get("expected_engine_version") not in (None, ENGINE_VERSION):
        raise EngineError(
            "ENGINE_VERSION_MISMATCH",
            f"Expected engine version must equal {ENGINE_VERSION}.",
        )

    target = request_json["adjudication_target"]
    without_hash = {key: value for key, value in target.items() if key != "canonical_hash"}
    if sha256(without_hash) != target["canonical_hash"]:
        raise EngineError("SCHEMA_INVALID", "Adjudication target canonical_hash mismatch.")
    if target["reason_codes"] != sorted(target["reason_codes"]):
        raise EngineError("SCHEMA_INVALID", "Adjudication target reason_codes are not sorted.")

    breakdown: list[dict[str, str]] = []
    descriptions: list[str] = []
    for code in target["reason_codes"]:
        item = REGISTRY[code]
        description = item["summary"]
        descriptions.append(description)
        breakdown.append(
            {
                "code": code,
                "description": description,
                "dimension_impact": ",".join(sorted(item["affected_dimensions"])),
            }
        )
    return {
        "engine_version": ENGINE_VERSION,
        "target_canonical_hash": target["canonical_hash"],
        "summary": " ".join(descriptions) if descriptions else "No reason codes emitted.",
        "code_breakdown": breakdown,
    }
