"""Act 3 of the institutional pipeline: a provisional, untrusted interpretation proposal.

Admission established that the institution may interpret a source. It did not establish
the interpretation. This module opens the seam where a model is finally allowed to suggest
what an admitted proposition might mean -- and nothing more than suggest.

What the model may do
---------------------
Return two arrays: ``proposed_assertions`` over the frozen eleven-slot vocabulary, and
``proposed_unresolved_references``. That is the whole of its output surface.

What the model may not do
-------------------------
Everything that would make it the institution. It cannot assign an interpretation status
(``ESTABLISHED``, ``AMBIGUOUS``, ``NOT_ESTABLISHED``, ``NOT_APPLICABLE``), an
interpretation basis, a warrant, authority, canonical status, confidence, a score, a
probability, ``ALLOW`` or ``DENY``. Those concepts have no representation in its output and
are refused structurally rather than argued about afterwards.

The envelope is OIC's, not the model's
--------------------------------------
``proposal_id``, ``proposal_schema_id``, ``admission_receipt_id``, ``candidate_unit_id``,
``candidate_projection_digest``, ``proposer``, ``proposal_state`` and ``epistemic_state``
are supplied here. The model is never asked to generate an identifier, an admission
binding, or a status, so it has no opportunity to overwrite one.

Semantic correctness is measured elsewhere, never repaired here
---------------------------------------------------------------
This is the discipline that makes the characterization instrument worth running. A
schema-valid proposal is accepted even when it invents an actor, drops a condition, calls
advisory text an obligation, quotes text that does not support the role it claims, or
misses a cross-reference. Those are exactly the defects the experiment exists to observe.
Rejecting them here would launder model failure into a clean boundary count and leave the
measurement showing nothing.

So refusal is reserved for structural and provider-contract failures: invalid JSON, a
wrong root shape, forbidden keys, an unknown slot, a malformed assertion, an invalid
reference kind, an invented normative force, or a field that asserts authority. Source-quote
grounding is computed and reported by the harness; it is never enforced here and never
repaired.

Non-admitted input is refused before the provider is reached
-----------------------------------------------------------
A receipt in any state other than ``ADMITTED`` raises before a request is built. There is
no provider call, and the result is an input-boundary failure -- never an empty proposal.

Provider neutrality
-------------------
Only :mod:`oic.model_provider` is used. No vendor, endpoint, model family or SDK is named
anywhere in this module.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Final

from oic.model_provider import JsonObject, ModelProvider, ModelProviderError, ModelRequest

__all__ = [
    "ALLOWED_REFERENCE_KINDS",
    "FORCE_VALUES",
    "PROPOSAL_SCHEMA_ID",
    "SLOT_VOCABULARY",
    "AdmittedCandidateBinding",
    "InterpretationProposalError",
    "InterpretationProposalResult",
    "ProposalBoundaryError",
    "ProposalInputBoundaryError",
    "build_proposal_envelope",
    "grounding_key",
    "is_quote_grounded",
    "proposal_identity",
    "propose_interpretation",
]

PROPOSAL_SCHEMA_ID: Final[str] = "OIC-INTERPRETATION-PROPOSAL-v0.1"

#: The frozen eleven-slot vocabulary. No semantic field may be added at this layer.
SLOT_VOCABULARY: Final[tuple[str, ...]] = (
    "normative_force",
    "bearer",
    "action",
    "object",
    "counterparty",
    "condition",
    "exception",
    "temporal_qualifier",
    "quantum",
    "definiendum",
    "definiens",
)

#: The six frozen normative forces. Constraining `normative_force` to these is a
#: provider-response contract enforced at this layer, not a change to the frozen design
#: schema: the schema types `proposed_value` as a string, and an invented force name is a
#: contract failure rather than a semantic opinion about the source.
FORCE_VALUES: Final[tuple[str, ...]] = (
    "OBLIGATION",
    "PROHIBITION",
    "PERMISSION",
    "CONSTITUTIVE_DEFINITION",
    "DELEGATION",
    "ADVISORY",
)

ALLOWED_REFERENCE_KINDS: Final[tuple[str, ...]] = (
    "INTERNAL_PROVISION",
    "EXTERNAL_DOCUMENT",
    "DEFINITION",
    "UNCLASSIFIED",
)

_ROOT_KEYS: Final[frozenset[str]] = frozenset(
    {"proposed_assertions", "proposed_unresolved_references"}
)
_ASSERTION_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {"slot", "proposed_value", "proposed_source_quote"}
)
_ASSERTION_ALLOWED_KEYS: Final[frozenset[str]] = _ASSERTION_REQUIRED_KEYS | {
    "proposed_material_qualifiers"
}
_REFERENCE_KEYS: Final[frozenset[str]] = frozenset({"reference_text", "reference_kind"})

#: Keys a proposer may never emit anywhere in its payload, at any depth. Each would be an
#: attempt to hold an authority the proposer does not have.
_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "admission_receipt_id",
        "admission_state",
        "admitted",
        "allow",
        "authority",
        "authorization",
        "canonical",
        "candidate_unit_id",
        "confidence",
        "deny",
        "enforceability",
        "epistemic_state",
        "established",
        "interpretation_basis",
        "interpretation_evidence",
        "interpretation_evidence_refs",
        "interpretation_status",
        "ir_unit_id",
        "legal_effect",
        "probability",
        "proposal_id",
        "proposal_state",
        "runtime_outcome",
        "score",
        "semantic_equivalence_key",
        "verdict",
        "warrant",
    }
)

#: Interpretation-status tokens. The status vocabulary belongs to canonicalization; a
#: proposer emitting one as a value is claiming an act it may not perform.
_FORBIDDEN_VALUE_TOKENS: Final[frozenset[str]] = frozenset(
    {"established", "ambiguous", "not_established", "not_applicable"}
)

_SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")
_RECEIPT_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^admrec-sha256:[0-9a-f]{64}$")
_UNIT_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^cnu-[0-9a-f]{24}$")
_PROPOSAL_ID_CHARS: Final[int] = 24
_MAX_TOKENS: Final[int] = 4096

_SLOT_LIST: Final[str] = ", ".join(SLOT_VOCABULARY)
_FORCE_LIST: Final[str] = ", ".join(FORCE_VALUES)
_REFERENCE_KIND_LIST: Final[str] = ", ".join(ALLOWED_REFERENCE_KINDS)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class InterpretationProposalError(ModelProviderError):
    """Base class for failures at the interpretation-proposal boundary."""


class ProposalInputBoundaryError(InterpretationProposalError):
    """The input is not an admitted candidate binding.

    Raised before any provider request is built. It is not an empty proposal and must not
    be recorded as one: nothing was proposed because nothing was asked.
    """


class ProposalBoundaryError(InterpretationProposalError):
    """Provider output failed the structural or provider-response contract.

    Never raised for a semantic defect. An invented actor, a dropped exception, a wrong
    force or an ungrounded quote is a schema-valid proposal and is accepted, so that the
    characterization instrument can measure it.
    """


# ---------------------------------------------------------------------------
# Inputs and results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdmittedCandidateBinding:
    """The admitted material a proposal stands on.

    Every field comes from the frozen Admission Runtime receipt and the admitted candidate
    projection. The proposer never sees the authority evidence, the admission warrant, the
    reason code, or any expected interpretation -- only the proposition itself.
    """

    admission_receipt_id: str
    admission_state: str
    candidate_unit_id: str
    candidate_projection_digest: str
    candidate_span: str
    provisional_unit_type: str | None = None

    def __post_init__(self) -> None:
        if _RECEIPT_ID_PATTERN.fullmatch(self.admission_receipt_id) is None:
            raise ValueError("admission_receipt_id must be admrec-sha256:<64 lowercase hex>")
        if _UNIT_ID_PATTERN.fullmatch(self.candidate_unit_id) is None:
            raise ValueError("candidate_unit_id must be cnu-<24 lowercase hex>")
        if _SHA256_PATTERN.fullmatch(self.candidate_projection_digest) is None:
            raise ValueError("candidate_projection_digest must be sha256:<64 lowercase hex>")
        if not self.candidate_span.strip():
            raise ValueError("candidate_span must not be empty")


@dataclass(frozen=True, slots=True)
class InterpretationProposalResult:
    """One accepted provisional proposal plus the provenance needed to audit it."""

    proposal: JsonObject
    provider: str
    model: str
    request_id: str | None
    raw_content_sha256: str

    @property
    def proposal_id(self) -> str:
        identifier: str = self.proposal["proposal_id"]
        return identifier


# ---------------------------------------------------------------------------
# The frozen prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT: Final[str] = f"""You propose. You do not decide.

You are given one institutional proposition that has already been admitted for
interpretation. Admission means an institution established that this proposition may be
interpreted. It did not establish what the proposition means. That is not your decision and
it is not decided here.

Your task is to propose what semantic structure the proposition might express, using a
fixed vocabulary of eleven slots: {_SLOT_LIST}.

Everything you return is provisional and untrusted. It will be reviewed by an institutional
authority that decides, separately, which of your proposals become canonical meaning. Your
output is a suggestion, not a finding.

How to propose

Inspect only the proposition supplied. Nothing else is available to you and nothing else
may be used.

Propose a slot only when the proposition itself supplies it. For every proposed slot, quote
the literal supporting text from the proposition in proposed_source_quote. If no literal
text supports the value, set proposed_source_quote to null rather than inventing a quote,
and prefer omitting the slot to proposing an unsupported value.

Do not fill a slot because it is usual in business practice. A proposition that names no
actor has no actor to propose. An unstated timing, threshold, approval step or working-hours
convention is not part of what the proposition says, however common it is elsewhere.

Distinguish bearer from counterparty. The bearer is who is bound, permitted or empowered.
The counterparty is who the act runs toward - a recipient, an addressee, a delegate. They
are different slots and the party a duty is owed to is not the party who owes it.

Preserve what the proposition actually carries. Conditions, exceptions, temporal
qualifiers and quantities are material: a condition dropped makes a conditional
proposition unconditional, an exception dropped makes it exceptionless, and a threshold
dropped makes it unbounded. Keep comparators, currencies, negations, hedges and discretion
markers with the slot they qualify, in proposed_material_qualifiers.

Keep the strength the proposition has. Advice is not obligation. Permission is not
obligation. May is not must. Eligible is not entitled. Review is not approval. Propose the
force the words carry, not the force a reader might prefer.

Where the proposition points at another provision or document - a section, an annex, a named
policy, a term defined elsewhere - surface it in proposed_unresolved_references. Do not
supply the referenced content from general knowledge, and do not resolve a term whose
institutional meaning the proposition does not give.

Output contract

Return exactly one JSON object with at most these two top-level keys:
proposed_assertions and proposed_unresolved_references. Return no other root key.

Each proposed assertion has exactly the keys slot, proposed_value and
proposed_source_quote, and may additionally have proposed_material_qualifiers, an array of
strings. slot must be one of: {_SLOT_LIST}. proposed_value and proposed_source_quote are a
string or null.

For the slot normative_force, proposed_value must be exactly one of: {_FORCE_LIST}. Do not
invent another force name.

Each proposed unresolved reference has exactly the keys reference_text and reference_kind.
reference_kind must be one of: {_REFERENCE_KIND_LIST}.

Never emit a status, a basis, a warrant, evidence, authority, admission, canonical status,
confidence, a score, a probability, allow, deny, a runtime outcome, or an identifier of any
kind. Never emit the words ESTABLISHED, AMBIGUOUS, NOT_ESTABLISHED or NOT_APPLICABLE as a
value. Those belong to an institutional act you are not performing.

Return only the requested JSON object."""


def _user_prompt(binding: AdmittedCandidateBinding) -> str:
    """Build the request body. Only the proposition itself crosses to the provider.

    Deliberately absent: authority evidence, the admission warrant, reason codes, the
    evaluation scope, the source identity, any expected interpretation, any interpretation
    evidence or warrant. The fact of positive admission is enough, and authority metadata
    would only bias a semantic reading.
    """
    hint = ""
    if binding.provisional_unit_type is not None:
        hint = (
            "\n\nAn earlier stage proposed the provisional, uncertain type "
            f"{binding.provisional_unit_type!r} for this proposition. It is another "
            "model's guess, it carries no authority, and it may be wrong. Do not treat it "
            "as the normative force."
        )
    return (
        "Propose provisional semantic structure for this admitted institutional "
        "proposition.\n\n"
        "Return exactly one JSON object using this envelope:\n"
        '{"proposed_assertions":[{"slot":"...","proposed_value":"...",'
        '"proposed_source_quote":"..."}],"proposed_unresolved_references":[]}\n'
        "Propose no slot the proposition does not supply. Quote literal supporting text, "
        "or use null. Surface references rather than resolving them."
        f"{hint}\n\n"
        f"ADMITTED PROPOSITION:\n{binding.candidate_span}"
    )


# ---------------------------------------------------------------------------
# Grounding, measured and never enforced
# ---------------------------------------------------------------------------


def grounding_key(value: str) -> str:
    """Case-fold and collapse whitespace for comparison, without rewriting anything."""
    return " ".join(value.split()).casefold()


def is_quote_grounded(quote: str, *, candidate_span: str) -> bool:
    """Whether a proposed quote is literal material of the admitted proposition.

    A metric, not a gate. Unlike the candidate layer's grounding contract, an ungrounded
    quote here is recorded and reported: a proposal is explicitly untrusted, and refusing
    one for being wrong would hide the defect the experiment is measuring.
    """
    return grounding_key(quote) in grounding_key(candidate_span)


# ---------------------------------------------------------------------------
# The provider-response contract
# ---------------------------------------------------------------------------


def _forbidden_keys_in(node: object, found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_KEYS:
                found.add(key)
            _forbidden_keys_in(value, found)
    elif isinstance(node, list):
        for item in node:
            _forbidden_keys_in(item, found)


def _forbidden_value_tokens_in(node: object, found: set[str]) -> None:
    if isinstance(node, str):
        if node.strip().casefold() in _FORBIDDEN_VALUE_TOKENS:
            found.add(node)
    elif isinstance(node, dict):
        for value in node.values():
            _forbidden_value_tokens_in(value, found)
    elif isinstance(node, list):
        for item in node:
            _forbidden_value_tokens_in(item, found)


def _parse_payload(content: str) -> JsonObject:
    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProposalBoundaryError("provider proposal output is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ProposalBoundaryError("provider proposal output root must be an object")
    unexpected = set(parsed) - _ROOT_KEYS
    if unexpected:
        raise ProposalBoundaryError(
            f"provider proposal output has unexpected root keys: {sorted(unexpected)}"
        )
    forbidden: set[str] = set()
    _forbidden_keys_in(parsed, forbidden)
    if forbidden:
        raise ProposalBoundaryError(
            f"provider attempted to emit authority-controlled fields: {sorted(forbidden)}"
        )
    tokens: set[str] = set()
    _forbidden_value_tokens_in(parsed, tokens)
    if tokens:
        raise ProposalBoundaryError(
            f"provider emitted an interpretation-status value it may not assign: {sorted(tokens)}"
        )
    return parsed


def _normalize_assertion(item: object, index: int) -> JsonObject:
    """Validate one proposed assertion structurally. Duplicate slots are preserved."""
    if not isinstance(item, dict):
        raise ProposalBoundaryError(f"proposed assertion {index} must be an object")
    unexpected = set(item) - _ASSERTION_ALLOWED_KEYS
    if unexpected:
        raise ProposalBoundaryError(
            f"proposed assertion {index} has unexpected fields: {sorted(unexpected)}"
        )
    missing = _ASSERTION_REQUIRED_KEYS - set(item)
    if missing:
        raise ProposalBoundaryError(
            f"proposed assertion {index} is missing required fields: {sorted(missing)}"
        )
    slot = item["slot"]
    if not isinstance(slot, str) or slot not in SLOT_VOCABULARY:
        raise ProposalBoundaryError(f"proposed assertion {index} has invalid slot: {slot!r}")
    value = item["proposed_value"]
    if value is not None and not isinstance(value, str):
        raise ProposalBoundaryError(
            f"proposed assertion {index} proposed_value must be a string or null"
        )
    quote = item["proposed_source_quote"]
    if quote is not None and not isinstance(quote, str):
        raise ProposalBoundaryError(
            f"proposed assertion {index} proposed_source_quote must be a string or null"
        )
    if slot == "normative_force" and value is not None and value not in FORCE_VALUES:
        raise ProposalBoundaryError(
            f"proposed assertion {index} proposes a normative force outside the frozen "
            f"vocabulary: {value!r}"
        )
    normalized: JsonObject = {
        "slot": slot,
        "proposed_value": value,
        "proposed_source_quote": quote,
    }
    if "proposed_material_qualifiers" in item:
        qualifiers = item["proposed_material_qualifiers"]
        if not isinstance(qualifiers, list) or any(
            not isinstance(entry, str) for entry in qualifiers
        ):
            raise ProposalBoundaryError(
                f"proposed assertion {index} proposed_material_qualifiers must be an array "
                "of strings"
            )
        normalized["proposed_material_qualifiers"] = list(qualifiers)
    return normalized


def _normalize_reference(item: object, index: int) -> JsonObject:
    if not isinstance(item, dict):
        raise ProposalBoundaryError(f"proposed unresolved reference {index} must be an object")
    if set(item) != _REFERENCE_KEYS:
        raise ProposalBoundaryError(
            f"proposed unresolved reference {index} must have exactly {sorted(_REFERENCE_KEYS)}"
        )
    text = item["reference_text"]
    if not isinstance(text, str) or not text.strip():
        raise ProposalBoundaryError(
            f"proposed unresolved reference {index} reference_text must be a non-empty string"
        )
    kind = item["reference_kind"]
    if not isinstance(kind, str) or kind not in ALLOWED_REFERENCE_KINDS:
        raise ProposalBoundaryError(
            f"proposed unresolved reference {index} has invalid reference_kind: {kind!r}"
        )
    return {"reference_text": text, "reference_kind": kind}


def _model_payload(parsed: JsonObject) -> tuple[list[JsonObject], list[JsonObject]]:
    raw_assertions = parsed.get("proposed_assertions", [])
    if not isinstance(raw_assertions, list):
        raise ProposalBoundaryError("proposed_assertions must be an array")
    raw_references = parsed.get("proposed_unresolved_references", [])
    if not isinstance(raw_references, list):
        raise ProposalBoundaryError("proposed_unresolved_references must be an array")
    # Order is preserved and duplicate slots are kept. Deduplicating here would silently
    # repair a proposer that contradicted itself, and that contradiction is evidence.
    assertions = [_normalize_assertion(item, index) for index, item in enumerate(raw_assertions)]
    references = [_normalize_reference(item, index) for index, item in enumerate(raw_references)]
    return assertions, references


# ---------------------------------------------------------------------------
# Deterministic identity and the OIC envelope
# ---------------------------------------------------------------------------


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def proposal_identity(
    *,
    binding: AdmittedCandidateBinding,
    proposer_id: str,
    assertions: list[JsonObject],
    references: list[JsonObject],
) -> str:
    """Deterministic proposal identity over the admitted binding and the exact payload.

    No UUID, no clock, no randomness. Identical payloads for the same admitted binding and
    proposer produce the same identifier; any change to the payload changes it.

    This is proposal identity and nothing more. It is not IR identity: it binds no
    interpretation ruleset, no interpretation evidence, and no canonical meaning, because a
    proposal has none of those.
    """
    projection = {
        "admission_receipt_id": binding.admission_receipt_id,
        "candidate_projection_digest": binding.candidate_projection_digest,
        "candidate_unit_id": binding.candidate_unit_id,
        "payload": {
            "proposed_assertions": assertions,
            "proposed_unresolved_references": references,
        },
        "proposal_schema": PROPOSAL_SCHEMA_ID,
        "proposer_id": proposer_id,
    }
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    return f"iip-{digest[:_PROPOSAL_ID_CHARS]}"


def build_proposal_envelope(
    *,
    binding: AdmittedCandidateBinding,
    proposer_kind: str,
    proposer_id: str,
    assertions: list[JsonObject],
    references: list[JsonObject],
) -> JsonObject:
    """Wrap a model payload in the envelope OIC controls.

    Every binding and identity field is written here from the admitted receipt. The model
    was never asked for one, so none of these can be overwritten by its output.
    """
    if proposer_kind not in {"MODEL", "HUMAN", "DETERMINISTIC_RULE"}:
        raise ValueError(f"unsupported proposer_kind: {proposer_kind!r}")
    if not proposer_id.strip():
        raise ValueError("proposer_id must not be empty")
    envelope: JsonObject = {
        "proposal_id": proposal_identity(
            binding=binding,
            proposer_id=proposer_id,
            assertions=assertions,
            references=references,
        ),
        "proposal_schema_id": PROPOSAL_SCHEMA_ID,
        "admission_receipt_id": binding.admission_receipt_id,
        "candidate_unit_id": binding.candidate_unit_id,
        "candidate_projection_digest": binding.candidate_projection_digest,
        "proposer": {"proposer_kind": proposer_kind, "proposer_id": proposer_id},
        "proposal_state": "PROVISIONAL",
        "epistemic_state": "uncertain",
        "proposed_assertions": assertions,
    }
    if references:
        envelope["proposed_unresolved_references"] = references
    return envelope


# ---------------------------------------------------------------------------
# The public seam
# ---------------------------------------------------------------------------


def propose_interpretation(
    *,
    binding: AdmittedCandidateBinding,
    provider: ModelProvider,
    proposer_id: str,
    proposer_kind: str = "MODEL",
) -> InterpretationProposalResult:
    """Request one provisional interpretation proposal for an admitted proposition.

    Args:
        binding: the admitted candidate and its admission receipt binding. Its
            ``provisional_unit_type`` is included in the request only when it is not
            ``None``; Characterization 001 pins it to ``None`` so the interpretation stage
            does not inherit and reinforce an earlier model's classification.
        provider: any :class:`~oic.model_provider.ModelProvider`. No vendor is assumed.
        proposer_id: an opaque institution-chosen label for whoever proposed.
        proposer_kind: ``MODEL``, ``HUMAN`` or ``DETERMINISTIC_RULE``.

    Returns:
        The accepted proposal envelope with provider provenance.

    Raises:
        ProposalInputBoundaryError: the receipt is not ``ADMITTED``. Raised before the
            request is built, so no provider call occurs. This is not an empty proposal.
        ProposalBoundaryError: the provider response failed the structural or
            provider-response contract. Never raised for a semantic defect.
    """
    if binding.admission_state != "ADMITTED":
        raise ProposalInputBoundaryError(
            "interpretation proposal requires an ADMITTED admission receipt; received "
            f"{binding.admission_state!r}. Nothing was proposed and no provider was called."
        )
    request = ModelRequest(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=_user_prompt(binding),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=_MAX_TOKENS,
    )
    # Exactly one attempt. There is no retry and no backoff here: a repeated request would
    # change the sampling distribution the characterization is measuring.
    response = provider.complete(request)
    assertions, references = _model_payload(_parse_payload(response.content))
    envelope = build_proposal_envelope(
        binding=binding,
        proposer_kind=proposer_kind,
        proposer_id=proposer_id,
        assertions=assertions,
        references=references,
    )
    return InterpretationProposalResult(
        proposal=envelope,
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
        raw_content_sha256=hashlib.sha256(response.content.encode()).hexdigest(),
    )
