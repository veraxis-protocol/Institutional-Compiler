"""Bounded model-assisted extraction of candidate normative units.

A candidate normative unit is **source-grounded candidate material**, not Institutional IR.
The distinction is the whole point of this module. Identification and segmentation of what
the source says happen here; normalization of what it institutionally means does not, and
is not authorized to. Canonicalizing paraphrases, resolving ambiguity into institutional
fact, and supplying participants the source leaves unstated all belong after admission.

So the model is asked for two different kinds of thing, held to two different standards:

* ``unit_type`` is a classification. It is an epistemically uncertain proposal about the
  candidate's primary normative function, and OIC stamps every candidate ``uncertain``.
* every textual role -- actor, action, object, target, conditions, exceptions,
  evidence_requirements -- must be a verbatim span of the source fragment. That is checked
  deterministically, by literal containment, and a value that is not in the source fails
  the whole response closed. Nothing is stripped, repaired, or silently accepted.

Requiring verbatim spans is what makes a deterministic grounding check honest. The
alternative -- letting the model paraphrase and then trying to judge whether the paraphrase
is supported -- needs a similarity engine or a second model to adjudicate, and both would
put semantic authority back inside the candidate layer.

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

# Ordered so the outbound instructions and the parser cannot drift: the vocabulary the
# model is offered is generated from the same tuple the parser accepts.
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
#: Model-proposed semantic fields. ``target`` is the one role added by
#: OIC-CANDIDATE-SEMANTICS-002: an explicitly stated recipient or destination had nowhere
#: to go, so it was landing in ``object`` in some runs and vanishing in others.
_MODEL_ALLOWED_KEYS = frozenset(
    {
        "unit_type",
        "actor",
        "action",
        "object",
        "target",
        "conditions",
        "exceptions",
        "evidence_requirements",
    }
)
#: Textual roles. Every value here must be a verbatim span of the source fragment.
#: ``unit_type`` is deliberately absent: it is a classification, not source text.
_GROUNDED_SCALAR_KEYS = ("actor", "action", "object", "target")
_GROUNDED_ARRAY_KEYS = ("conditions", "exceptions", "evidence_requirements")
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

# The worker has to be told four separate things, because collapsing any two of them
# breaks extraction in a different way: what a candidate *is*; that the source's
# institutional standing is not part of that question; that every textual role is a
# verbatim source span rather than a normalized restatement; and that it decides no
# authority. Only the last of those is enforced by trust -- the span rule is checked
# deterministically below, and the authority rule is enforced by the parser.
_SYSTEM_PROMPT = f"""You are an extraction worker inside the Open Institutional Compiler.

Your task is source-grounded semantic identification only. Read the supplied source
fragment and identify every span that literally expresses institutional normative content.

A candidate normative unit is the literal source expression of any one of these:
{_UNIT_TYPE_LIST}.

Whether the source is authoritative, admitted, enforceable, legally effective, approved,
or institutionally controlling is NOT a criterion for deciding whether candidate material
exists. Those questions belong to later stages and are decided elsewhere, not by you.
Identify the candidate even when the standing of the source is unknown, draft, synthetic,
hypothetical, or unverified.

You are reporting what the fragment says, not what it institutionally means. Every textual
field you return must be copied verbatim from the fragment: an exact, contiguous run of
characters that appears in it. Do not paraphrase, re-inflect, pluralize, expand an
abbreviation, or tidy grammar. A field whose text is not a literal span of the fragment
fails the whole response.

Never supply a participant the fragment does not name. If the fragment is passive or
otherwise names nobody who acts, actor is null. Do not infer an actor from the passive
voice, and do not invent a recipient, approver, owner, payee, department, office, role, or
authority that the fragment does not state. A missing participant is null, never a guess.

Never drop material qualifying language. Explicit if, when, where, unless, provided that
and similar clauses, monetary and quantitative thresholds, and stated time limits are part
of what the fragment says and must appear in the candidate.

Your output is candidate material only and has no institutional authority. Do not decide
admission, authority, authorization, enforceability, legal effect, runtime outcome, allow
or deny, or any confidence standing for admission. Do not invent source anchors. Return
only the requested JSON object."""


class CandidateBoundaryError(ModelProviderError):
    """Raised when provider output attempts to cross the candidate-only boundary."""


class CandidateGroundingError(CandidateBoundaryError):
    """Raised when a model-proposed textual role is not a verbatim span of the source.

    A subclass rather than a separate error so every existing fail-closed handler keeps
    catching it, while a receipt can still tell an ungrounded value apart from a malformed
    envelope or an attempted authority claim.
    """


@dataclass(frozen=True, slots=True)
class CandidateExtractionResult:
    """Candidate units plus provider provenance; never an admitted record."""

    candidates: tuple[JsonObject, ...]
    source_anchor: JsonObject
    provider: str
    model: str
    request_id: str | None
    raw_content_sha256: str


def _grounding_key(value: str) -> str:
    """Casefolded, whitespace-collapsed form used only for comparison.

    Neither side of the comparison is stored in this form and no candidate value is
    rewritten by it. Collapsing runs of whitespace and ignoring case cannot let an absent
    phrase pass -- text the fragment never contains is still absent under both -- so this
    only removes false rejections over line wrapping and capitalization.
    """
    return " ".join(value.split()).casefold()


def _require_source_span(value: str, *, key: str, index: int, haystack: str) -> None:
    if not value.strip():
        raise CandidateGroundingError(
            f"candidate {index} field {key} is blank; use null or an empty array instead"
        )
    if _grounding_key(value) not in haystack:
        raise CandidateGroundingError(
            f"candidate {index} field {key} is not a verbatim span of the source fragment: "
            f"{value!r}"
        )


def check_source_grounding(item: JsonObject, *, source_text: str, index: int = 0) -> None:
    """Fail closed unless every textual role is a literal span of the source fragment.

    Deliberately literal containment and nothing more: no similarity model, no second model
    adjudicating the first, no stemming, no synonym table. A phrase the fragment does not
    contain -- an inferred approver, an invented payee, a department nobody named -- has no
    way through. The cost is that a legitimate paraphrase is refused too, which is why the
    contract requires verbatim spans rather than paraphrase.

    Nothing is repaired. An ungrounded value fails the response it arrived in.
    """
    haystack = _grounding_key(source_text)
    for key in _GROUNDED_SCALAR_KEYS:
        value = item.get(key)
        if isinstance(value, str):
            _require_source_span(value, key=key, index=index, haystack=haystack)
    for key in _GROUNDED_ARRAY_KEYS:
        entries = item.get(key, [])
        if not isinstance(entries, list):
            continue
        for position, entry in enumerate(entries):
            if isinstance(entry, str):
                _require_source_span(
                    entry, key=f"{key}[{position}]", index=index, haystack=haystack
                )


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
            "Extract zero or more candidate normative units from this exact source "
            "fragment.\n"
            "Identifying candidate material is not a finding that the source is "
            "authoritative, admitted, enforceable, legally effective, approved, or "
            "institutionally controlling. Do not withhold a candidate on those grounds.\n\n"
            "Return exactly one JSON object with exactly one top-level key named "
            "candidates.\n"
            "Use exactly this envelope:\n"
            '{"candidates":[{"unit_type":"...","actor":null,"action":null,'
            '"object":null,"target":null,"conditions":[],"exceptions":[],'
            '"evidence_requirements":[]}]}\n'
            'For zero candidates, return exactly {"candidates":[]}.\n'
            "Never return a candidate directly at the JSON root. Never add another root "
            "key.\n\n"
            "For each candidate use only these keys: unit_type, actor, action, object, "
            "target, conditions, exceptions, evidence_requirements.\n\n"
            "unit_type is your classification of the candidate's PRIMARY normative "
            "function. It is the one field that is not copied text, and it is understood "
            "to be an uncertain proposal.\n"
            f"Choose the closest of: {_UNIT_TYPE_LIST}.\n"
            "Classify by what the fragment principally does. An explicit duty to retain, "
            "produce or record proof is normally evidence_duty. An explicit recommendation "
            "or encouragement is normally advisory, and remains candidate material even "
            "though it compels nothing. An explicit referral of an unresolved matter "
            "onward is normally escalation. An if, when, where, unless, quantitative or "
            "temporal qualifier normally belongs in conditions and does not replace the "
            "primary function it qualifies. These are guides, not a precedence table; "
            "institutional language is often genuinely ambiguous, and a defensible reading "
            "is what is being asked for.\n\n"
            "EVERY OTHER FIELD MUST BE COPIED VERBATIM FROM THE FRAGMENT. Each value must "
            "be an exact contiguous run of characters that appears in the fragment above. "
            "Do not paraphrase, re-inflect, pluralize, expand abbreviations, or repair "
            "grammar. A value that is not a literal span of the fragment fails the whole "
            "response.\n"
            "- actor: the span naming who acts or bears the duty. If the fragment names "
            "nobody, use null. Never infer an actor from the passive voice and never "
            "invent one.\n"
            "- action: the span carrying the governed operative act. When a clause states "
            "a trigger and a consequence, the operative act is the consequence, not the "
            "trigger; the trigger belongs in conditions.\n"
            "- object: the span naming what the act applies to.\n"
            "- target: the span naming an explicitly stated recipient, destination, "
            "beneficiary, or counterparty the act is directed toward. Use null unless the "
            "fragment states one.\n"
            "- conditions: spans stating circumstances, triggers, thresholds or time "
            "limits that qualify the unit, one per entry.\n"
            "- exceptions: spans stating carve-outs, one per entry.\n"
            "- evidence_requirements: spans stating records, proof or retention that is "
            "required.\n"
            "Use null for an absent actor, action, object or target, and an empty array "
            "for an absent list. Do not infer, complete, or supply anything the fragment "
            "does not say.\n"
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
        _normalize_candidate(
            item, source_anchor=source_anchor, source_text=source_text, index=index
        )
        for index, item in enumerate(_candidate_items(payload))
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


def _normalize_candidate(
    item: JsonObject, *, source_anchor: JsonObject, source_text: str, index: int
) -> JsonObject:
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
    # Grounding runs before anything is kept, so an ungrounded value can never reach a
    # normalized candidate even transiently.
    check_source_grounding(item, source_text=source_text, index=index)
    semantic: JsonObject = {
        "unit_type": unit_type,
        "actor": _nullable_string(item, "actor"),
        "action": _nullable_string(item, "action"),
        "object": _nullable_string(item, "object"),
        "target": _nullable_string(item, "target"),
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
