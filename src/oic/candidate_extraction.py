"""Minimal, source-grounded discovery of candidate normative material.

OIC-CANDIDATE-SEMANTICS-003 gives the model only ``candidate_span`` and provisional
``unit_type``. Semantic-role decomposition is not a pre-admission responsibility.
Identity, state, and source anchoring remain deterministic OIC outputs. Nothing here
admits, authorizes, or constructs Institutional IR.

OIC-CANDIDATE-SEMANTICS-004 changes the prompt contract only. The schema, the parser, the
fail-closed grounding rule and the deterministic identity material are all unchanged. What
004 adds is a quoting rule: the span should hold the normative proposition, not the
source's separable commentary about that proposition's own status. A fragment that marks
itself a draft, a hypothetical, an illustration or an unverified extract is still saying
something normative, and the framing is source context rather than part of what is said.

Framing separation is asked of the provider and is never imposed afterwards. There is no
phrase list, no regex, no post-generation trimming, and no repair anywhere in this module:
a span that carries framing is accepted exactly as returned and recorded as an
observation. The alternative -- stripping recognized prefixes -- would make OIC the author
of the span it then reports as source-grounded.

Excluding framing is a quoting decision, not a finding about the source. It decides
nothing about whether the proposition is authoritative, adopted, valid, admitted,
enforceable, or legally operative, and the source anchor keeps the framing either way.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from oic.model_provider import JsonObject, ModelProvider, ModelProviderError, ModelRequest

_UNIT_TYPES: tuple[str, ...] = (
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
)
_ALLOWED_UNIT_TYPES = frozenset(_UNIT_TYPES)
_UNIT_TYPE_LIST = ", ".join(_UNIT_TYPES)
_MODEL_ALLOWED_KEYS = frozenset({"candidate_span", "unit_type"})
_REMOVED_SEMANTIC_ROLE_KEYS = frozenset(
    {"actor", "action", "object", "target", "conditions", "exceptions", "evidence_requirements"}
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
        "admitted",
        "authority",
        "authorization",
        "enforceability",
        "legal_effect",
        "verdict",
        "allow",
        "deny",
        "runtime_outcome",
        "institutional_ir",
        "institutional_ir_state",
    }
)
_SOURCE_ANCHOR_REQUIRED_KEYS = frozenset({"anchor_id", "source_id", "node_id", "content_hash"})
_SOURCE_ANCHOR_ALLOWED_KEYS = frozenset(
    {"anchor_id", "source_id", "node_id", "quote", "page", "bbox", "content_hash"}
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

_SYSTEM_PROMPT = f"""You are a bounded extraction worker inside the Open Institutional Compiler.

Find source-grounded normative propositions. A candidate is only material that appears to
express one apparent normative function from this provisional vocabulary:
{_UNIT_TYPE_LIST}.

Return a literal, contiguous candidate_span copied from the source. Include enough
surrounding source language to preserve the material proposition and every material
qualifier needed to understand it, including conditions, thresholds, time limits,
exceptions, recipients, and trigger/consequence language. Do not rewrite, normalize,
summarize, paraphrase, complete, or infer. Passive voice does not require actor inference:
preserve the proposition as source text. If the fragment contains two independently
meaningful normative propositions, return two source-grounded candidate spans.

Quote the proposition, not the source's commentary about the proposition. Where the
fragment separately marks its own status as a draft, a proposal, a hypothetical, an
illustration, an example, a quotation of another party, or as unadopted, unverified or
non-authoritative, and that marking is grammatically separable from the proposition, leave
it outside the span. Framing that is itself part of what the proposition says stays in:
a circumstance the rule applies to governs conduct and belongs in the span.

Never buy a shorter span with material content. Every threshold, amount, deadline,
condition, exception, recipient, prohibition, advisory wording, trigger and consequence
stays inside the span. Dropping material content is a worse error than including framing.

Worked example, worded so it matches no fragment you will be given:
  Fragment: INTERNAL WORKING TEXT - SUPERSEDED. Each grant over 5,000 euro must be
  countersigned by the Programme Director.
  Correct span: Each grant over 5,000 euro must be countersigned by the Programme
  Director.
  Over-extraction: the whole fragment, carrying INTERNAL WORKING TEXT - SUPERSEDED.
  Under-extraction: must be countersigned, which loses the amount and the role.

unit_type is the only classification and the only proposed field that need not occur in
the source. It is provisional and epistemically uncertain. Advisory language remains
candidate material when supported by the source.

Source standing is not a discovery criterion. Draft, hypothetical, synthetic, unverified,
and non-authoritative framing must not suppress a candidate that appears in the fragment.
Leaving that framing outside the span is a quoting decision and not a finding: it does not
decide whether the proposition is authoritative, adopted, valid, admitted, enforceable, or
legally operative. The source anchor keeps the framing.

Candidate material has no institutional authority. Do not decide or propose admission,
authority, authorization, enforceability, legal effect, runtime outcome, allow, deny,
confidence as an admission proxy, or Institutional IR state. Do not assign semantic roles
such as actor, action, object, target, conditions, exceptions, or evidence requirements.
Return only the requested JSON object."""


class CandidateBoundaryError(ModelProviderError):
    """Provider output crossed the minimal candidate boundary."""


class CandidateGroundingError(CandidateBoundaryError):
    """A proposed candidate span is not literal source material."""


@dataclass(frozen=True, slots=True)
class CandidateExtractionResult:
    """Candidate material plus provider provenance; never an admitted record."""

    candidates: tuple[JsonObject, ...]
    source_anchor: JsonObject
    provider: str
    model: str
    request_id: str | None
    raw_content_sha256: str


def _grounding_key(value: str) -> str:
    """Case-fold and collapse whitespace for comparison without rewriting output."""
    return " ".join(value.split()).casefold()


def check_source_grounding(item: JsonObject, *, source_text: str, index: int = 0) -> None:
    """Require a nonblank literal contiguous span; never repair or fuzz-match."""
    value = item.get("candidate_span")
    if not isinstance(value, str):
        raise CandidateBoundaryError("candidate field candidate_span must be a string")
    if not value.strip():
        raise CandidateGroundingError(f"candidate {index} field candidate_span is blank")
    if _grounding_key(value) not in _grounding_key(source_text):
        raise CandidateGroundingError(
            f"candidate {index} field candidate_span is not a literal contiguous span "
            f"of the source fragment: {value!r}"
        )


def propose_candidate_units(
    *, source_text: str, source_anchor: JsonObject, provider: ModelProvider
) -> CandidateExtractionResult:
    """Request minimal candidates and enforce the fail-closed boundary."""
    if not source_text.strip():
        raise ValueError("source_text must not be empty")
    _validate_source_anchor(source_anchor)
    request = ModelRequest(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            "Extract zero or more source-grounded candidate normative propositions from "
            "this exact source fragment. Source standing does not suppress discovery.\n\n"
            "Return exactly one JSON object with exactly one top-level key named "
            "candidates. Use exactly this envelope:\n"
            '{"candidates":[{"candidate_span":"...","unit_type":"..."}]}\n'
            'For zero candidates, return exactly {"candidates":[]}. Never return a '
            "candidate directly at the JSON root. Never add another root key.\n\n"
            "Each candidate must have exactly these two keys: candidate_span and unit_type. "
            "candidate_span must be one literal, contiguous source span preserving the "
            "complete material proposition and its material qualifiers; do not paraphrase, "
            "repair, infer, or split qualifiers into semantic roles. Leave out separable "
            "framing that states the source's own status - draft, proposal, hypothetical, "
            "illustration, attribution, unverified, non-authoritative - rather than forming "
            "part of the proposition, and never drop material proposition content in order "
            "to do so. unit_type is an "
            "uncertain provisional classification and need not be source text. "
            f"Choose the closest of: {_UNIT_TYPE_LIST}.\n\n"
            "Never emit actor, action, object, target, conditions, exceptions, or "
            "evidence_requirements. Never emit unit_id, interpretation_state, "
            "epistemic_state, lifecycle_state, confidence, source_anchors, admission, "
            "admitted, authority, authorization, enforceability, legal_effect, verdict, "
            "allow, deny, runtime_outcome, institutional_ir, or institutional_ir_state.\n\n"
            f"SOURCE FRAGMENT:\n{source_text}"
        ),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=4096,
    )
    response = provider.complete(request)
    payload = _parse_provider_json(response.content)
    normalized = tuple(
        _normalize_candidate(item, source_anchor=source_anchor, source_text=source_text, index=i)
        for i, item in enumerate(_candidate_items(payload))
    )
    return CandidateExtractionResult(
        candidates=normalized,
        source_anchor=dict(source_anchor),
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
        raw_content_sha256=hashlib.sha256(response.content.encode()).hexdigest(),
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
    if any(not isinstance(item, dict) for item in value):
        raise CandidateBoundaryError("every candidate must be an object")
    return tuple(value)


def _normalize_candidate(
    item: JsonObject, *, source_anchor: JsonObject, source_text: str, index: int
) -> JsonObject:
    forbidden = set(item) & _MODEL_FORBIDDEN_AUTHORITY_KEYS
    if forbidden:
        raise CandidateBoundaryError(
            f"provider attempted to emit authority-controlled candidate fields: {sorted(forbidden)}"
        )
    removed = set(item) & _REMOVED_SEMANTIC_ROLE_KEYS
    if removed:
        raise CandidateBoundaryError(
            f"provider emitted removed semantic-role fields outside the 003 candidate "
            f"contract: {sorted(removed)}"
        )
    unexpected = set(item) - _MODEL_ALLOWED_KEYS
    if unexpected:
        raise CandidateBoundaryError(
            f"provider emitted unexpected candidate fields: {sorted(unexpected)}"
        )
    if set(item) != _MODEL_ALLOWED_KEYS:
        raise CandidateBoundaryError(
            f"candidate is missing required fields: {sorted(_MODEL_ALLOWED_KEYS - set(item))}"
        )
    unit_type = item.get("unit_type")
    if not isinstance(unit_type, str) or unit_type not in _ALLOWED_UNIT_TYPES:
        raise CandidateBoundaryError(f"invalid candidate unit_type: {unit_type!r}")
    check_source_grounding(item, source_text=source_text, index=index)
    span = item["candidate_span"]
    if not isinstance(span, str):  # defensive type narrowing; grounding already checked it
        raise CandidateBoundaryError("candidate field candidate_span must be a string")
    semantic: JsonObject = {"candidate_span": span, "unit_type": unit_type}
    return {
        "unit_id": _candidate_id(semantic=semantic, source_anchor=source_anchor),
        **semantic,
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "source_anchors": [dict(source_anchor)],
    }


def _candidate_id(*, semantic: JsonObject, source_anchor: JsonObject) -> str:
    """003 identity: candidate span, provisional type, source anchor, and schema tag."""
    canonical = json.dumps(
        {"candidate_schema": "003", "semantic": semantic, "source_anchor": source_anchor},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"cnu-{hashlib.sha256(canonical).hexdigest()[:24]}"
