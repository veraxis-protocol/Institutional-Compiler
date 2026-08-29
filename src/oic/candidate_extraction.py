"""Bounded model-assisted extraction of candidate normative units.

This module deliberately stops before review, admission, Institutional IR construction,
control-envelope generation, compilation, or runtime authorization.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from oic.model_provider import JsonObject, ModelProvider, ModelProviderError, ModelRequest

_ALLOWED_UNIT_TYPES = frozenset(
    {
        "definition",
        "mandate",
        "delegation",
        "obligation",
        "prohibition",
        "permission",
        "power",
        "condition",
        "exception",
        "evidence_duty",
        "review_duty",
        "escalation",
        "remedy",
        "temporal_trigger",
        "discretion",
        "advisory",
    }
)
_MODEL_ALLOWED_KEYS = frozenset(
    {"unit_type", "actor", "action", "object", "conditions", "exceptions", "evidence_requirements"}
)
_MODEL_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "unit_id",
        "interpretation_state",
        "epistemic_state",
        "lifecycle_state",
        "confidence",
        "source_anchors",
        "admission",
        "authority",
        "verdict",
        "allow",
    }
)
_SOURCE_ANCHOR_REQUIRED_KEYS = frozenset({"anchor_id", "source_id", "node_id", "content_hash"})
_SOURCE_ANCHOR_ALLOWED_KEYS = frozenset(
    {"anchor_id", "source_id", "node_id", "quote", "page", "bbox", "content_hash"}
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_SYSTEM_PROMPT = """You are an extraction worker inside the Open Institutional Compiler.
You may identify candidate normative units in the supplied source fragment. Your output
is candidate material only and has no institutional authority. Do not decide admission,
authorization, enforceability, legal effect, or runtime outcome. Do not invent source
anchors. Return only the requested JSON object."""


class CandidateBoundaryError(ModelProviderError):
    """Raised when provider output attempts to cross the candidate-only boundary."""


@dataclass(frozen=True, slots=True)
class CandidateExtractionResult:
    """Candidate units plus provider provenance; never an admitted record."""

    candidates: tuple[JsonObject, ...]
    source_anchor: JsonObject
    provider: str
    model: str
    request_id: str | None
    raw_content_sha256: str


def propose_candidate_units(
    *, source_text: str, source_anchor: JsonObject, provider: ModelProvider
) -> CandidateExtractionResult:
    """Ask a provider for candidate units and enforce the candidate-only boundary."""
    if not source_text.strip():
        raise ValueError("source_text must not be empty")
    _validate_source_anchor(source_anchor)
    request = ModelRequest(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            "Extract zero or more candidate normative units from this exact source fragment.\n\n"
            "Return exactly one JSON object with exactly one top-level key named candidates.\n"
            "Use exactly this envelope:\n"
            '{"candidates":[{"unit_type":"...","actor":null,"action":null,'
            '"object":null,"conditions":[],"exceptions":[],'
            '"evidence_requirements":[]}]}\n'
            'For zero candidates, return exactly {"candidates":[]}.\n'
            "Never return a candidate directly at the JSON root. Never add another root key.\n\n"
            "For each candidate use only these keys: unit_type, actor, action, object, "
            "conditions, exceptions, evidence_requirements.\n"
            "Do not emit unit_id, source_anchors, interpretation_state, epistemic_state, "
            "lifecycle_state, confidence, admission, authority, verdict, or allow.\n\n"
            f"SOURCE FRAGMENT:\n{source_text}"
        ),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=4096,
    )
    response = provider.complete(request)
    payload = _parse_provider_json(response.content)
    normalized = tuple(
        _normalize_candidate(item, source_anchor=source_anchor)
        for item in _candidate_items(payload)
    )
    return CandidateExtractionResult(
        candidates=normalized,
        source_anchor=dict(source_anchor),
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
        raw_content_sha256=hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
    )


def _validate_source_anchor(anchor: JsonObject) -> None:
    missing = _SOURCE_ANCHOR_REQUIRED_KEYS - set(anchor)
    if missing:
        raise ValueError(f"source_anchor missing required fields: {sorted(missing)}")
    unexpected = set(anchor) - _SOURCE_ANCHOR_ALLOWED_KEYS
    if unexpected:
        raise ValueError(f"source_anchor has unexpected fields: {sorted(unexpected)}")
    for key in ("anchor_id", "source_id", "node_id"):
        value = anchor.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"source_anchor field {key} must be a non-empty string")
    content_hash = anchor.get("content_hash")
    if not isinstance(content_hash, str) or _SHA256_PATTERN.fullmatch(content_hash) is None:
        raise ValueError("source_anchor content_hash must be sha256:<64 lowercase hex>")
    quote = anchor.get("quote")
    if quote is not None and not isinstance(quote, str):
        raise ValueError("source_anchor quote must be a string when present")
    page = anchor.get("page")
    if page is not None and (not isinstance(page, int) or isinstance(page, bool)):
        raise ValueError("source_anchor page must be an integer or null")
    bbox = anchor.get("bbox")
    if bbox is not None and (
        not isinstance(bbox, list)
        or any(not isinstance(value, int | float) or isinstance(value, bool) for value in bbox)
    ):
        raise ValueError("source_anchor bbox must be an array of numbers or null")


def _parse_provider_json(content: str) -> JsonObject:
    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise CandidateBoundaryError("provider candidate output is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise CandidateBoundaryError("provider candidate output root must be an object")
    extra_root = set(parsed) - {"candidates"}
    if extra_root:
        raise CandidateBoundaryError(
            f"provider candidate output has unexpected root keys: {sorted(extra_root)}"
        )
    return parsed


def _candidate_items(payload: JsonObject) -> tuple[JsonObject, ...]:
    value = payload.get("candidates")
    if not isinstance(value, list):
        raise CandidateBoundaryError("provider candidate output must contain a candidates array")
    items: list[JsonObject] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise CandidateBoundaryError(f"candidate {index} is not an object")
        items.append(item)
    return tuple(items)


def _normalize_candidate(item: JsonObject, *, source_anchor: JsonObject) -> JsonObject:
    forbidden = set(item) & _MODEL_FORBIDDEN_AUTHORITY_KEYS
    if forbidden:
        raise CandidateBoundaryError(
            f"provider attempted to emit authority-controlled candidate fields: {sorted(forbidden)}"
        )
    unexpected = set(item) - _MODEL_ALLOWED_KEYS
    if unexpected:
        raise CandidateBoundaryError(
            f"provider emitted unexpected candidate fields: {sorted(unexpected)}"
        )
    unit_type = item.get("unit_type")
    if not isinstance(unit_type, str) or unit_type not in _ALLOWED_UNIT_TYPES:
        raise CandidateBoundaryError(f"invalid candidate unit_type: {unit_type!r}")
    semantic: JsonObject = {
        "unit_type": unit_type,
        "actor": _nullable_string(item, "actor"),
        "action": _nullable_string(item, "action"),
        "object": _nullable_string(item, "object"),
        "conditions": _string_array(item, "conditions"),
        "exceptions": _string_array(item, "exceptions"),
        "evidence_requirements": _string_array(item, "evidence_requirements"),
    }
    return {
        "unit_id": _candidate_id(semantic=semantic, source_anchor=source_anchor),
        **semantic,
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "source_anchors": [dict(source_anchor)],
    }


def _nullable_string(item: JsonObject, key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CandidateBoundaryError(f"candidate field {key} must be string or null")
    return value


def _string_array(item: JsonObject, key: str) -> list[str]:
    value = item.get(key, [])
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise CandidateBoundaryError(f"candidate field {key} must be an array of strings")
    return list(value)


def _candidate_id(*, semantic: JsonObject, source_anchor: JsonObject) -> str:
    canonical = json.dumps(
        {"semantic": semantic, "source_anchor": source_anchor},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"cnu-{hashlib.sha256(canonical).hexdigest()[:24]}"
