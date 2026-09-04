"""Deterministic reference evaluator for the frozen Admission Boundary 001 contract.

Scope
-----
This module answers exactly one frozen question about one candidate normative unit:
*did the institution's own authority evidence establish eligibility for Institutional IR
interpretation at an explicit evaluation time?* It answers it by reading facts that are
already in the input and comparing them against a frozen, packaged ruleset.

What this module deliberately is not
------------------------------------
No model participates in the answer. No authority is invented, defaulted, widened, or
repaired. No Institutional IR is constructed. No execution is authorized. ``ADMITTED``
means eligible for interpretation and nothing else; every other state means eligibility
was not established, never that the underlying proposition was denied.

Two failure classes, never merged
---------------------------------
1. **Input-boundary failure.** The bytes are not an admissible executable input:
   not UTF-8, not one JSON object, duplicate keys, not the canonical serialization,
   schema-invalid, misordered or duplicated evidence, an evidence digest that does not
   recompute, or a ruleset the packaged frozen ruleset does not attest. These raise
   :class:`AdmissionInputBoundaryError`. They are *not* admission outcomes and are never
   converted into ``ADMISSION_NOT_ESTABLISHED``: a malformed input has not been
   evaluated, and saying otherwise would manufacture institutional evidence out of a
   parse failure.
2. **Valid input.** Exactly one terminal admission state and one immutable receipt.

An unexpected internal defect raises :class:`AdmissionEvaluationError`. It never becomes
a receipt either.

Time
----
Time enters only through ``evaluation_time``. This module reads no clock, no timezone,
and no calendar. Two evaluations of identical bytes are identical forever.

Offline
-------
The four governing specifications are packaged beside this module as byte-identical
copies of the frozen design originals, and schema resolution runs through a
:class:`referencing.Registry` built solely from those bytes. The registry has no
``retrieve`` callback, so an absolute ``$id``/``$ref`` URI resolves locally or fails; it
never becomes a fetch.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from importlib import resources
from typing import Any, Final

from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

__all__ = [
    "ADMISSION_INPUT_SCHEMA_NAME",
    "ADMISSION_RECEIPT_SCHEMA_NAME",
    "AUTHORITY_EVIDENCE_SCHEMA_NAME",
    "CANONICALIZATION_ID",
    "EVALUATOR_ID",
    "EVALUATOR_VERSION",
    "RULESET_DIGEST",
    "RULESET_ID",
    "STATE_INPUT_MAPPING_NAME",
    "AdmissionCanonicalFormError",
    "AdmissionEncodingError",
    "AdmissionError",
    "AdmissionEvaluationError",
    "AdmissionEvidenceIntegrityError",
    "AdmissionEvidenceOrderError",
    "AdmissionInputBoundaryError",
    "AdmissionJSONError",
    "AdmissionReceipt",
    "AdmissionRulesetError",
    "AdmissionSchemaError",
    "AdmissionSpecificationError",
    "AdmissionState",
    "AdmissionTimestampError",
    "ReasonCode",
    "canonical_json",
    "digest_of",
    "evaluate_admission_bytes",
    "packaged_specification_bytes",
    "packaged_state_input_mapping",
]

# JSON documents are arbitrarily shaped; `Any` is the honest annotation at the boundary.
JsonValue = Any

CANONICALIZATION_ID: Final[str] = "OIC-ADMISSION-CANONICAL-JSON-v0.1"
EVALUATOR_ID: Final[str] = "oic-admission-reference-evaluator"
EVALUATOR_VERSION: Final[str] = "0.1-preregistered"
RULESET_ID: Final[str] = "OIC-ADMISSION-BOUNDARY-001"
RULESET_DIGEST: Final[str] = (
    "sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c"
)

STATE_INPUT_MAPPING_NAME: Final[str] = "STATE-INPUT-MAPPING-v0.1.json"
ADMISSION_INPUT_SCHEMA_NAME: Final[str] = "ADMISSION-INPUT-v0.1.schema.json"
AUTHORITY_EVIDENCE_SCHEMA_NAME: Final[str] = "AUTHORITY-EVIDENCE-v0.1.schema.json"
ADMISSION_RECEIPT_SCHEMA_NAME: Final[str] = "ADMISSION-RECEIPT-v0.1.schema.json"

_SPECS_PACKAGE: Final[str] = "oic.admission_specs"
_RECEIPT_ID_PREFIX: Final[str] = "admrec-"
_DIGEST_PREFIX: Final[str] = "sha256:"
_UTF8_BOM: Final[bytes] = b"\xef\xbb\xbf"
#: The only timestamp spelling this evaluator accepts. The executable input contract
#: requires timestamps to be normalized before serialization, so normalizing here would
#: be exactly the silent repair the contract forbids.
_TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%SZ"
#: Two distinct operative authority bases over one evaluation is the frozen conflict
#: condition. The frozen ruleset carries no rule that could resolve them.
_CONFLICT_THRESHOLD: Final[int] = 2


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
#
# Messages carry field names, JSON pointers, counts, and indices. They never carry
# input values, evidence bodies, or any other part of an untrusted payload.


class AdmissionError(RuntimeError):
    """Base class for every error raised by the admission evaluator."""


class AdmissionInputBoundaryError(AdmissionError):
    """The supplied bytes are not an admissible executable input.

    This is not an admission outcome. Nothing was evaluated, so no terminal state and no
    receipt exist. Callers must not translate it into one.
    """


class AdmissionEncodingError(AdmissionInputBoundaryError):
    """The bytes are not BOM-free UTF-8."""


class AdmissionJSONError(AdmissionInputBoundaryError):
    """The bytes are not exactly one JSON object with unique keys."""


class AdmissionCanonicalFormError(AdmissionInputBoundaryError):
    """The bytes are not the canonical JSON serialization of what they decode to."""


class AdmissionSchemaError(AdmissionInputBoundaryError):
    """The decoded input does not satisfy the frozen executable input schema."""


class AdmissionTimestampError(AdmissionInputBoundaryError):
    """A timestamp is not a normalized RFC 3339 UTC ``Z`` instant."""


class AdmissionEvidenceOrderError(AdmissionInputBoundaryError):
    """Authority evidence is misordered or carries a duplicate ``evidence_id``."""


class AdmissionEvidenceIntegrityError(AdmissionInputBoundaryError):
    """A recorded ``evidence_digest`` does not recompute from its own evidence object."""


class AdmissionRulesetError(AdmissionInputBoundaryError):
    """The input names a ruleset this evaluator does not carry."""


class AdmissionSpecificationError(AdmissionError):
    """A packaged frozen specification is missing, unreadable, or not what it attests."""


class AdmissionEvaluationError(AdmissionError):
    """A defect in this evaluator. Never a receipt, never an admission state."""


# ---------------------------------------------------------------------------
# Frozen vocabulary
# ---------------------------------------------------------------------------


class AdmissionState(Enum):
    """The fifteen frozen terminal states, declared in frozen precedence order."""

    CANDIDATE_INPUT_INVALID = "CANDIDATE_INPUT_INVALID"
    AUTHORITY_REGISTRY_UNAVAILABLE = "AUTHORITY_REGISTRY_UNAVAILABLE"
    AUTHORITY_EVIDENCE_STALE = "AUTHORITY_EVIDENCE_STALE"
    SOURCE_NOT_REGISTERED = "SOURCE_NOT_REGISTERED"
    SOURCE_VERSION_MISMATCH = "SOURCE_VERSION_MISMATCH"
    SOURCE_DIGEST_MISMATCH = "SOURCE_DIGEST_MISMATCH"
    MISSING_AUTHORITY_EVIDENCE = "MISSING_AUTHORITY_EVIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    CONFLICTING_AUTHORITY = "CONFLICTING_AUTHORITY"
    ADMISSION_NOT_ESTABLISHED = "ADMISSION_NOT_ESTABLISHED"
    ADMITTED = "ADMITTED"


class ReasonCode(Enum):
    """The frozen primary reason code paired with each terminal state."""

    OIC_ADM_0000 = "OIC-ADM-0000"
    OIC_ADM_1001 = "OIC-ADM-1001"
    OIC_ADM_1002 = "OIC-ADM-1002"
    OIC_ADM_1003 = "OIC-ADM-1003"
    OIC_ADM_1004 = "OIC-ADM-1004"
    OIC_ADM_1005 = "OIC-ADM-1005"
    OIC_ADM_1006 = "OIC-ADM-1006"
    OIC_ADM_1007 = "OIC-ADM-1007"
    OIC_ADM_1008 = "OIC-ADM-1008"
    OIC_ADM_1009 = "OIC-ADM-1009"
    OIC_ADM_1010 = "OIC-ADM-1010"
    OIC_ADM_1011 = "OIC-ADM-1011"
    OIC_ADM_1012 = "OIC-ADM-1012"
    OIC_ADM_1013 = "OIC-ADM-1013"
    OIC_ADM_1099 = "OIC-ADM-1099"


# ---------------------------------------------------------------------------
# Canonical JSON v0.1 and digests
# ---------------------------------------------------------------------------


def canonical_json(value: JsonValue) -> bytes:
    """Serialize ``value`` as ``OIC-ADMISSION-CANONICAL-JSON-v0.1``.

    UTF-8 without a BOM, object keys sorted by Unicode code point, no insignificant
    whitespace, no ASCII-only escaping, no NaN or infinity, array order as recorded, and
    no trailing newline. Canonicalization never reads a clock.
    """
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise AdmissionEvaluationError(
            f"value is not canonically serializable: {type(exc).__name__}"
        ) from exc
    return text.encode("utf-8")


def digest_of(payload: bytes) -> str:
    """Return ``sha256:<64 lowercase hex>`` over ``payload``."""
    return f"{_DIGEST_PREFIX}{hashlib.sha256(payload).hexdigest()}"


def _digest_of_projection(value: JsonValue) -> str:
    return digest_of(canonical_json(value))


def _without(mapping: Mapping[str, JsonValue], key: str) -> dict[str, JsonValue]:
    return {name: item for name, item in mapping.items() if name != key}


# ---------------------------------------------------------------------------
# Packaged frozen specifications
# ---------------------------------------------------------------------------


def packaged_specification_bytes(name: str) -> bytes:
    """Return the packaged bytes of one frozen specification.

    Reads from installed package data, so the evaluator runs from a wheel with no
    ``design/`` tree present.
    """
    try:
        return (resources.files(_SPECS_PACKAGE) / name).read_bytes()
    except (OSError, ModuleNotFoundError) as exc:
        raise AdmissionSpecificationError(
            f"packaged admission specification is unavailable: {name}"
        ) from exc


def _packaged_document(name: str) -> JsonValue:
    raw = packaged_specification_bytes(name)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmissionSpecificationError(
            f"packaged admission specification is not UTF-8 JSON: {name}"
        ) from exc


def packaged_state_input_mapping() -> JsonValue:
    """Return the parsed packaged frozen ruleset, verified against its frozen digest."""
    mapping = _packaged_document(STATE_INPUT_MAPPING_NAME)
    computed = _digest_of_projection(mapping)
    if computed != RULESET_DIGEST:
        raise AdmissionSpecificationError(
            "packaged ruleset does not match the frozen ruleset digest"
        )
    return mapping


def _mapping_entries() -> tuple[tuple[AdmissionState, ReasonCode], ...]:
    """Return (state, reason code) pairs in the ruleset's own precedence order."""
    mapping = packaged_state_input_mapping()
    if not isinstance(mapping, Mapping) or mapping.get("ruleset_id") != RULESET_ID:
        raise AdmissionSpecificationError("packaged ruleset does not declare the frozen ruleset id")
    if mapping.get("first_terminal_state_wins") is not True:
        raise AdmissionSpecificationError("packaged ruleset does not declare first-terminal-wins")
    if mapping.get("runtime_permission_states") != []:
        raise AdmissionSpecificationError("packaged ruleset declares a runtime permission state")
    entries = mapping.get("entries")
    if not isinstance(entries, list):
        raise AdmissionSpecificationError("packaged ruleset has no entries")
    ordered = sorted(entries, key=lambda entry: int(entry["precedence"]))
    if [int(entry["precedence"]) for entry in ordered] != list(range(1, len(ordered) + 1)):
        raise AdmissionSpecificationError("packaged ruleset precedence is not a dense 1..n order")
    try:
        return tuple(
            (AdmissionState(entry["state"]), ReasonCode(entry["reason_code"])) for entry in ordered
        )
    except (KeyError, ValueError) as exc:
        raise AdmissionSpecificationError(
            "packaged ruleset names a state or reason code this evaluator does not carry"
        ) from exc


#: Frozen precedence, read from the packaged ruleset rather than restated here.
_PRECEDENCE: Final[tuple[tuple[AdmissionState, ReasonCode], ...]] = _mapping_entries()
_REASON_FOR_STATE: Final[dict[AdmissionState, ReasonCode]] = dict(_PRECEDENCE)

if tuple(state for state, _ in _PRECEDENCE) != tuple(AdmissionState):
    raise AdmissionSpecificationError(
        "packaged ruleset precedence does not match this evaluator's declared state order"
    )


def _build_registry() -> Registry:
    """A registry built only from packaged bytes. No retrieve callback, so no fetch."""
    resources_by_uri: list[tuple[str, Resource]] = []
    for name in (
        ADMISSION_INPUT_SCHEMA_NAME,
        AUTHORITY_EVIDENCE_SCHEMA_NAME,
        ADMISSION_RECEIPT_SCHEMA_NAME,
    ):
        document = _packaged_document(name)
        resource = Resource.from_contents(document, default_specification=DRAFT202012)
        schema_id = document.get("$id") if isinstance(document, Mapping) else None
        if isinstance(schema_id, str) and schema_id:
            resources_by_uri.append((schema_id, resource))
        resources_by_uri.append((name, resource))
    registry: Registry = Registry().with_resources(resources_by_uri)
    return registry


_REGISTRY: Final[Registry] = _build_registry()
_INPUT_VALIDATOR: Final[Draft202012Validator] = Draft202012Validator(
    _packaged_document(ADMISSION_INPUT_SCHEMA_NAME), registry=_REGISTRY
)
_RECEIPT_VALIDATOR: Final[Draft202012Validator] = Draft202012Validator(
    _packaged_document(ADMISSION_RECEIPT_SCHEMA_NAME), registry=_REGISTRY
)


def _pointer(error: ValidationError) -> str:
    return "".join(
        "/" + str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path
    )


# ---------------------------------------------------------------------------
# Byte boundary
# ---------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    seen: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in seen:
            raise AdmissionJSONError(f"duplicate object key: {key!r}")
        seen[key] = value
    return seen


def _reject_constant(name: str) -> JsonValue:
    """Refuse ``NaN``/``Infinity``/``-Infinity``, which Python accepts but JSON has not.

    Raised here rather than at canonicalization so a non-JSON literal is classified as
    what it is: an input-boundary failure, not a defect in this evaluator.
    """
    raise AdmissionJSONError(f"admission input carries the non-JSON literal {name}")


def _decode(input_bytes: bytes) -> JsonValue:
    if not isinstance(input_bytes, bytes | bytearray):
        raise AdmissionEncodingError(
            f"admission input must be bytes, received {type(input_bytes).__name__}"
        )
    payload = bytes(input_bytes)
    if payload.startswith(_UTF8_BOM):
        raise AdmissionEncodingError("admission input carries a UTF-8 byte-order mark")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdmissionEncodingError("admission input is not valid UTF-8") from exc
    try:
        document: JsonValue = json.loads(
            text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
        )
    except json.JSONDecodeError as exc:
        raise AdmissionJSONError(f"admission input is not one JSON value: {exc.msg}") from exc
    if not isinstance(document, dict):
        raise AdmissionJSONError(
            f"admission input must be a JSON object, found {type(document).__name__}"
        )
    return document


def _require_canonical(document: JsonValue, payload: bytes) -> None:
    if canonical_json(document) != payload:
        raise AdmissionCanonicalFormError(
            "admission input bytes are not the canonical JSON serialization of their own "
            f"content ({CANONICALIZATION_ID}); the evaluator does not normalize and continue"
        )


def _require_schema_valid(document: JsonValue) -> None:
    errors = sorted(_INPUT_VALIDATOR.iter_errors(document), key=lambda error: _pointer(error))
    if errors:
        first = errors[0]
        raise AdmissionSchemaError(
            f"admission input violates {ADMISSION_INPUT_SCHEMA_NAME} at "
            f"{_pointer(first) or '#'}: failed keyword {first.validator!r} "
            f"({len(errors)} violation(s) total)"
        )


def _require_frozen_ruleset(document: Mapping[str, JsonValue]) -> None:
    ruleset = document["ruleset"]
    if ruleset["ruleset_id"] != RULESET_ID:
        raise AdmissionRulesetError("admission input names an unknown ruleset id")
    if ruleset["ruleset_digest"] != RULESET_DIGEST:
        raise AdmissionRulesetError(
            "admission input names a ruleset digest this evaluator does not carry; "
            "caller-selected admission rules are not accepted"
        )


def _require_evidence_integrity(evidence: Sequence[Mapping[str, JsonValue]]) -> None:
    seen_ids: set[str] = set()
    previous: tuple[str, str] | None = None
    for index, item in enumerate(evidence):
        evidence_id = item["evidence_id"]
        recorded = item["evidence_digest"]
        if evidence_id in seen_ids:
            raise AdmissionEvidenceOrderError(
                f"authority_evidence[{index}] repeats an earlier evidence_id"
            )
        seen_ids.add(evidence_id)
        key = (evidence_id, recorded)
        if previous is not None and key <= previous:
            raise AdmissionEvidenceOrderError(
                f"authority_evidence[{index}] is not in ascending "
                "(evidence_id, evidence_digest) order; the evaluator does not reorder input"
            )
        previous = key
        computed = _digest_of_projection(_without(item, "evidence_digest"))
        if computed != recorded:
            raise AdmissionEvidenceIntegrityError(
                f"authority_evidence[{index}] evidence_digest does not recompute"
            )


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------


def _instant(value: str, field: str) -> datetime:
    """Parse one already-normalized RFC 3339 UTC ``Z`` timestamp.

    No clock, no timezone database, no locale. A timestamp that is not already in the
    frozen normalized spelling is refused at the input boundary rather than repaired.
    """
    try:
        return datetime.strptime(value, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except (TypeError, ValueError) as exc:
        raise AdmissionTimestampError(
            f"{field} is not a normalized RFC 3339 UTC 'Z' instant"
        ) from exc


def _optional_instant(value: JsonValue, field: str) -> datetime | None:
    if value is None:
        return None
    return _instant(value, field)


# ---------------------------------------------------------------------------
# The frozen ordered evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Lifecycle:
    """The lifecycle facts of one record, already parsed to instants."""

    effective_from: datetime
    effective_until: datetime | None
    superseded_at: datetime | None
    revoked_at: datetime | None

    def not_yet_effective(self, at: datetime) -> bool:
        return at < self.effective_from

    def expired(self, at: datetime) -> bool:
        return self.effective_until is not None and at >= self.effective_until

    def superseded(self, at: datetime) -> bool:
        return self.superseded_at is not None and at >= self.superseded_at

    def revoked(self, at: datetime) -> bool:
        return self.revoked_at is not None and at >= self.revoked_at


def _lifecycle(record: Mapping[str, JsonValue], where: str) -> _Lifecycle:
    return _Lifecycle(
        effective_from=_instant(record["effective_from"], f"{where}.effective_from"),
        effective_until=_optional_instant(
            record.get("effective_until"), f"{where}.effective_until"
        ),
        superseded_at=_optional_instant(record.get("superseded_at"), f"{where}.superseded_at"),
        revoked_at=_optional_instant(record.get("revoked_at"), f"{where}.revoked_at"),
    )


def _covers(record: Mapping[str, JsonValue], jurisdiction: str, applicability: str) -> bool:
    """Scope containment, read literally. Nothing is widened, inferred, or defaulted."""
    scope = record["applicability_scope"]
    return record["jurisdiction"] == jurisdiction and applicability in scope


def _all(items: Iterable[bool]) -> bool:
    """``all`` over a non-empty iterable. An empty relevant set never proves a lifecycle
    state; the caller has already established that the set is non-empty."""
    values = list(items)
    if not values:
        raise AdmissionEvaluationError("lifecycle check reached an empty evidence set")
    return all(values)


@dataclass(frozen=True, slots=True)
class _Evidence:
    """One authority-evidence object with its parsed lifecycle facts."""

    body: Mapping[str, JsonValue]
    lifecycle: _Lifecycle
    warrant: Mapping[str, JsonValue]
    warrant_lifecycle: _Lifecycle

    @property
    def authority_basis_ref(self) -> str:
        ref: str = self.body["authority_basis_ref"]
        return ref

    def binds_version(self, version: str) -> bool:
        return bool(
            self.body["source_version"] == version and self.warrant["source_version"] == version
        )

    def binds_digest(self, source_digest: str) -> bool:
        return bool(
            self.body["source_digest"] == source_digest
            and self.warrant["source_digest"] == source_digest
        )

    def covers(self, jurisdiction: str, applicability: str) -> bool:
        return _covers(self.body, jurisdiction, applicability) and _covers(
            self.warrant, jurisdiction, applicability
        )

    def not_yet_effective(self, at: datetime) -> bool:
        return self.lifecycle.not_yet_effective(at) or self.warrant_lifecycle.not_yet_effective(at)

    def expired(self, at: datetime) -> bool:
        return self.lifecycle.expired(at) or self.warrant_lifecycle.expired(at)

    def superseded(self, at: datetime) -> bool:
        return self.lifecycle.superseded(at)

    def revoked(self, at: datetime) -> bool:
        return (
            self.lifecycle.revoked(at)
            or self.warrant_lifecycle.revoked(at)
            or self.warrant["status"] == "REVOKED"
        )

    def operative(self, at: datetime, jurisdiction: str, applicability: str) -> bool:
        """True when this evidence and its warrant are, on their face, in force here.

        Deliberately independent of which source version the registration names: an
        overlapping authority that speaks to a different version of the same source is
        still an authority claim over this evaluation, and the conflict check has to see
        it. Nothing here ranks one authority above another.
        """
        return (
            self.covers(jurisdiction, applicability)
            and not self.not_yet_effective(at)
            and not self.expired(at)
            and not self.superseded(at)
            and not self.revoked(at)
            and self.warrant["status"] == "ACTIVE"
        )


def _evaluate_state(document: Mapping[str, JsonValue]) -> AdmissionState:
    """Return the first terminal state, in the frozen precedence order.

    Checks are written in the ruleset's order and are never reordered, collapsed, or
    extended. There is no ALLOW and no DENY.
    """
    candidate = document["candidate"]
    registration = document["source_registration"]
    raw_evidence: Sequence[Mapping[str, JsonValue]] = document["authority_evidence"]
    at = _instant(document["evaluation_time"], "evaluation_time")
    scope = document["evaluation_scope"]
    jurisdiction: str = scope["jurisdiction"]
    applicability: str = scope["applicability"]
    source_id: str = registration["source_id"]
    source_version: str = registration["source_version"]
    source_digest: str = registration["source_digest"]

    # 1. Candidate reference check. The candidate is not re-extracted, trimmed,
    #    classified, or repaired; only its reference to the registered source is checked.
    anchors: Sequence[Mapping[str, JsonValue]] = candidate["source_anchors"]
    if not anchors:
        return AdmissionState.CANDIDATE_INPUT_INVALID
    if any(anchor["source_id"] != source_id for anchor in anchors):
        return AdmissionState.CANDIDATE_INPUT_INVALID

    # 2-3. Registry availability, then freshness.
    observation = registration["registry_observation"]
    if observation["availability"] == "UNAVAILABLE":
        return AdmissionState.AUTHORITY_REGISTRY_UNAVAILABLE
    if observation["availability"] == "AVAILABLE" and observation["freshness"] == "STALE":
        return AdmissionState.AUTHORITY_EVIDENCE_STALE

    # 4. Source registration.
    if registration["registered"] is False:
        return AdmissionState.SOURCE_NOT_REGISTERED

    relevant = tuple(
        _Evidence(
            body=item,
            lifecycle=_lifecycle(item, f"authority_evidence[{index}]"),
            warrant=item["admission_warrant"],
            warrant_lifecycle=_lifecycle(
                item["admission_warrant"], f"authority_evidence[{index}].admission_warrant"
            ),
        )
        for index, item in enumerate(raw_evidence)
        if item["source_id"] == source_id
    )

    # 5. Version binding. Evidence that is present but binds no evidence or warrant to the
    #    registered version leaves the registered instance unwarranted.
    version_bound = tuple(item for item in relevant if item.binds_version(source_version))
    if raw_evidence and not version_bound:
        return AdmissionState.SOURCE_VERSION_MISMATCH

    # 6. Digest binding, candidate anchors first.
    if any(anchor["content_hash"] != source_digest for anchor in anchors):
        return AdmissionState.SOURCE_DIGEST_MISMATCH
    bound = tuple(item for item in version_bound if item.binds_digest(source_digest))
    if raw_evidence and not bound:
        return AdmissionState.SOURCE_DIGEST_MISMATCH

    # 7. Authority basis and warrant sufficiency. No default authority exists, so an
    #    absent basis or warrant is never supplied from elsewhere.
    if not bound:
        return AdmissionState.MISSING_AUTHORITY_EVIDENCE

    # 8. Scope, for the source registration and for the bound evidence and warrants.
    if not _covers(registration, jurisdiction, applicability):
        return AdmissionState.OUT_OF_SCOPE
    scoped = tuple(item for item in bound if item.covers(jurisdiction, applicability))
    if not scoped:
        return AdmissionState.OUT_OF_SCOPE

    # 9-12. Temporal lifecycle, in the frozen order. Intervals are half-open.
    registration_lifecycle = _lifecycle(registration, "source_registration")
    if registration_lifecycle.not_yet_effective(at) or _all(
        item.not_yet_effective(at) for item in scoped
    ):
        return AdmissionState.NOT_YET_EFFECTIVE
    if registration_lifecycle.expired(at) or _all(item.expired(at) for item in scoped):
        return AdmissionState.EXPIRED
    if registration_lifecycle.superseded(at) or _all(item.superseded(at) for item in scoped):
        return AdmissionState.SUPERSEDED
    if registration_lifecycle.revoked(at) or _all(item.revoked(at) for item in scoped):
        return AdmissionState.REVOKED

    # 13. Conflict. All relevant authority records are collected first, then compared.
    #     The frozen ruleset carries no institutional precedence rule, so two operative
    #     authority bases over the same evaluation are unresolvable here by construction.
    #     Recency, rank, order, and version are never used to pick a winner.
    operative = tuple(item for item in relevant if item.operative(at, jurisdiction, applicability))
    if len({item.authority_basis_ref for item in operative}) >= _CONFLICT_THRESHOLD:
        return AdmissionState.CONFLICTING_AUTHORITY

    # 14. No specific state applies, and no exact operative warrant establishes the
    #     requested scope and time: a disputed or suspended condition, never a denial.
    qualifying = tuple(item for item in scoped if item.operative(at, jurisdiction, applicability))
    if not qualifying:
        return AdmissionState.ADMISSION_NOT_ESTABLISHED

    # 15. Eligible for Institutional IR interpretation. Not permission to execute.
    return AdmissionState.ADMITTED


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AdmissionReceipt:
    """One immutable admission receipt.

    Every field is derived from the accepted input, the frozen ruleset, and the frozen
    evaluator identity. No random value, no wall clock, no generated-at timestamp, no
    mutable sequence, no host or network metadata participates.
    """

    admission_receipt_id: str
    candidate_unit_id: str
    candidate_projection_digest: str
    source_id: str
    source_version: str
    source_digest: str
    authority_evidence_refs: tuple[str, ...]
    authority_evidence_digests: tuple[str, ...]
    evaluation_time: str
    evaluation_scope: Mapping[str, str]
    admission_state: AdmissionState
    reason_code: ReasonCode
    evaluator_id: str
    evaluator_version: str
    ruleset_id: str
    ruleset_digest: str
    input_digest: str
    evidence_digest: str

    def to_json(self) -> dict[str, JsonValue]:
        """The receipt projection, exactly as the frozen receipt schema requires it."""
        return {
            "admission_receipt_id": self.admission_receipt_id,
            "candidate_unit_id": self.candidate_unit_id,
            "candidate_projection_digest": self.candidate_projection_digest,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "source_digest": self.source_digest,
            "authority_evidence_refs": list(self.authority_evidence_refs),
            "authority_evidence_digests": list(self.authority_evidence_digests),
            "evaluation_time": self.evaluation_time,
            "evaluation_scope": dict(self.evaluation_scope),
            "admission_state": self.admission_state.value,
            "reason_code": self.reason_code.value,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "ruleset_id": self.ruleset_id,
            "ruleset_digest": self.ruleset_digest,
            "input_digest": self.input_digest,
            "evidence_digest": self.evidence_digest,
        }

    def canonical_bytes(self) -> bytes:
        """Canonical JSON v0.1 of the complete receipt projection."""
        return canonical_json(self.to_json())


def _build_receipt(
    document: Mapping[str, JsonValue], payload: bytes, state: AdmissionState
) -> AdmissionReceipt:
    evidence: Sequence[Mapping[str, JsonValue]] = document["authority_evidence"]
    registration = document["source_registration"]
    reason = _REASON_FOR_STATE[state]
    projection: dict[str, JsonValue] = {
        "candidate_unit_id": document["candidate"]["unit_id"],
        "candidate_projection_digest": _digest_of_projection(document["candidate"]),
        "source_id": registration["source_id"],
        "source_version": registration["source_version"],
        "source_digest": registration["source_digest"],
        "authority_evidence_refs": [item["evidence_id"] for item in evidence],
        "authority_evidence_digests": [item["evidence_digest"] for item in evidence],
        "evaluation_time": document["evaluation_time"],
        "evaluation_scope": dict(document["evaluation_scope"]),
        "admission_state": state.value,
        "reason_code": reason.value,
        "evaluator_id": EVALUATOR_ID,
        "evaluator_version": EVALUATOR_VERSION,
        "ruleset_id": RULESET_ID,
        "ruleset_digest": RULESET_DIGEST,
        # The accepted bytes are canonical by construction, so hashing them and hashing
        # their canonical re-serialization are the same value.
        "input_digest": digest_of(payload),
        "evidence_digest": _digest_of_projection(list(evidence)),
    }
    receipt_id = f"{_RECEIPT_ID_PREFIX}{_digest_of_projection(projection)}"
    complete = {"admission_receipt_id": receipt_id, **projection}

    errors = sorted(_RECEIPT_VALIDATOR.iter_errors(complete), key=lambda error: _pointer(error))
    if errors:
        first = errors[0]
        raise AdmissionEvaluationError(
            f"constructed receipt violates {ADMISSION_RECEIPT_SCHEMA_NAME} at "
            f"{_pointer(first) or '#'}: failed keyword {first.validator!r}"
        )

    return AdmissionReceipt(
        admission_receipt_id=receipt_id,
        candidate_unit_id=projection["candidate_unit_id"],
        candidate_projection_digest=projection["candidate_projection_digest"],
        source_id=projection["source_id"],
        source_version=projection["source_version"],
        source_digest=projection["source_digest"],
        authority_evidence_refs=tuple(projection["authority_evidence_refs"]),
        authority_evidence_digests=tuple(projection["authority_evidence_digests"]),
        evaluation_time=projection["evaluation_time"],
        evaluation_scope=projection["evaluation_scope"],
        admission_state=state,
        reason_code=reason,
        evaluator_id=EVALUATOR_ID,
        evaluator_version=EVALUATOR_VERSION,
        ruleset_id=RULESET_ID,
        ruleset_digest=RULESET_DIGEST,
        input_digest=projection["input_digest"],
        evidence_digest=projection["evidence_digest"],
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_admission_bytes(input_bytes: bytes) -> AdmissionReceipt:
    """Evaluate one executable admission input, supplied as its exact accepted bytes.

    The parameter is bytes and not a parsed object on purpose: encoding, duplicate keys,
    canonical form, schema conformance, evidence ordering, evidence integrity, and the
    frozen ruleset binding are all properties of the bytes. A caller handed an object
    entry point could skip every one of them.

    Returns:
        One immutable :class:`AdmissionReceipt` carrying exactly one terminal state.

    Raises:
        AdmissionInputBoundaryError: the bytes are not an admissible input. Nothing was
            evaluated; this is not ``ADMISSION_NOT_ESTABLISHED`` and must not be
            recorded as an admission outcome.
        AdmissionSpecificationError: a packaged frozen specification is not intact.
        AdmissionEvaluationError: a defect in this evaluator.
    """
    payload = bytes(input_bytes) if isinstance(input_bytes, bytes | bytearray) else input_bytes
    document = _decode(payload)
    _require_canonical(document, payload)
    _require_schema_valid(document)
    _require_frozen_ruleset(document)
    _require_evidence_integrity(document["authority_evidence"])

    try:
        state = _evaluate_state(document)
    except AdmissionError:
        # Input-boundary and specification failures stay in their own class.
        raise
    except Exception as exc:
        # An unexpected defect must not become a valid institutional receipt.
        raise AdmissionEvaluationError(
            f"admission evaluation failed unexpectedly: {type(exc).__name__}"
        ) from exc

    return _build_receipt(document, payload, state)
