"""Synthetic authority and admissibility for integration slice 001.

Implements the frozen contract:

``CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md``
    sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
``INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.3.md``
    sha256 600a8f19eef3bba635ba4349ee1b46e0f23baa66dfe0b87c0d84223d6b686bfd

v0.4 is a narrow successor that incorporates its predecessors by digest.  The
thirteen-step procedure, the object shapes and the epoch definition come out of
those incorporated documents, each verified from Git objects:
v0.3 1c07a24c…, v0.2 8e02820d…, v0.1 f0f250ed…, derivation v0.2 d1a96148…,
derivation v0.1 9d4e61a2….

The authority here is fictional.  Its content demonstrates nothing about any real
institution; only its mechanics — binding, expiry, revocation, refusal — are
exercised.  ``SYNTHETIC`` is visible in every identifier this module produces, and
no object or field may be read as real CDC institutional authority.

The commitment the module exists to hold:

    CURRENTNESS_PASS != AUTHORITY_PASS

Currentness enters an authority evaluation only as two bound digests.  There is no
field through which the authority layer can restate, overwrite or infer a
currentness verdict, and a positive authority decision is never a currentness fact.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from oic.errors import OICError

SEMANTIC_DESIGN_SHA256: Final = "03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173"
DIGEST_DERIVATION_SHA256: Final = "600a8f19eef3bba635ba4349ee1b46e0f23baa66dfe0b87c0d84223d6b686bfd"

ASSURANCE_CLASS: Final = "INTERNAL_TECHNICAL_DEMONSTRATION"
AUTHORITY_CLASS: Final = "SYNTHETIC_BOUNDED_DEMONSTRATION_AUTHORITY"
AUTHORITY_PROFILE_ID: Final = "CDC-SYNTHETIC-AUTHORITY-PROFILE-001"
DERIVED_FROM_REAL_CDC_AUTHORITY: Final = False

# The layer commitment, stated as a value so a test can assert it rather than
# trusting a docstring.
CURRENTNESS_PASS_IS_AUTHORITY_PASS: Final = False

SUBJECT_PRINCIPAL: Final = "SYNTHETIC-SUBJECT-PRINCIPAL-001"
PRODUCER_PRINCIPAL: Final = "SYNTHETIC-PRODUCER-PRINCIPAL-001"
CONSUMER_PRINCIPAL: Final = "SYNTHETIC-CONSUMER-PRINCIPAL-001"

PROCEED: Final = "PROCEED"
DENY: Final = "DENY"
ESCALATE: Final = "ESCALATE"

NOT_REVOKED: Final = "NOT_REVOKED"
REVOKED: Final = "REVOKED"

AUTHORITY_BASIS_CLASS: Final = "SYNTHETIC_AUTHORITY_BASIS"
ADMISSIBILITY_BASIS_CLASS: Final = "SYNTHETIC_ADMISSIBILITY_BASIS"
PRODUCER_PROFILE_CLASS: Final = "SYNTHETIC_PRODUCER_PROFILE"
CONSUMER_PROFILE_CLASS: Final = "SYNTHETIC_RELIANCE_CONSUMER_PROFILE"

AUTHORITY_REASON_CODES: Final[dict[str, str]] = {
    "A1": "AUTHORITY_AND_ADMISSIBILITY_SATISFIED",
    "A2": "PRINCIPAL_NOT_AUTHORIZED_FOR_SCOPE",
    "A3": "REQUESTED_USE_OUTSIDE_SCOPE",
    "A4": "ADMISSIBILITY_BASIS_MISSING",
    "A5": "ADMISSIBILITY_BASIS_INVALID",
    "A6": "AUTHORITY_BASIS_AMBIGUOUS_COMPETING",
    "A7": "AUTHORITY_ESCALATION_REQUIRED",
    "A8": "ARTIFACT_DIGEST_MISMATCH_AT_AUTHORITY",
    "A9": "CURRENTNESS_RESOLUTION_NOT_BOUND",
    "A10": "AUTHORITY_BASIS_REVOKED",
    "A11": "AUTHORITY_BASIS_MISSING",
    "A12": "AUTHORITY_BASIS_INVALID",
    "A13": "ADMISSIBILITY_BASIS_REVOKED",
}
AUTHORITY_REASON_CODE_COUNT: Final = len(AUTHORITY_REASON_CODES)


class AuthorityContractError(OICError):
    """The authority layer refused to evaluate rather than emit a coded decision."""


# ---------------------------------------------------------------------------
# Canonical serialization — derivation v0.3 §1
# ---------------------------------------------------------------------------


def canonical_bytes(value: object) -> bytes:
    """UTF-8, sorted keys, no indentation, ``,``/``:``, literal non-ASCII."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_digest(value: object) -> str:
    """Unprefixed lowercase SHA-256 over the canonical form."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def strip_digest_prefix(value: str) -> str:
    """A ``sha256:`` prefix is presentation and is stripped before comparison."""
    return value[len("sha256:") :] if value.startswith("sha256:") else value


def digests_equal(left: str, right: str) -> bool:
    """Compare digests independently of prefix presentation."""
    return strip_digest_prefix(left) == strip_digest_prefix(right)


def _without(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != field}


# --- Class 1: currentness_epoch_digest (as-of projection) -------------------

EPOCH_RECORD_FIELDS: Final = (
    "record_ref",
    "record_digest",
    "record_class",
    "effective_at",
    "admitted_at",
)


def currentness_epoch_digest(
    *,
    output_ref: str,
    as_of: str,
    governing_records: Iterable[Mapping[str, Any]],
    completeness_attestation_digest: str | None,
) -> str:
    """Project the governing basis for one output as of one instant.

    A record enters only when ``admitted_at <= as_of`` and
    ``effective_at <= as_of``: admitted-but-not-yet-operative is knowledge, not
    operativeness.  ``as_of`` is deliberately NOT a field of the digested object,
    so a clock tick alone can never move the epoch — only a crossing of governed
    effective or admitted time can.
    """
    operative = [
        {field: record[field] for field in EPOCH_RECORD_FIELDS}
        for record in governing_records
        if str(record.get("output_ref")) == output_ref
        and record.get("effective_at") is not None
        and str(record["admitted_at"]) <= as_of
        and str(record["effective_at"]) <= as_of
    ]
    operative.sort(
        key=lambda record: (record["effective_at"], record["admitted_at"], record["record_ref"])
    )
    return canonical_digest(
        {
            "output_ref": output_ref,
            "completeness_attestation_digest": completeness_attestation_digest,
            "operative_basis_records": operative,
        }
    )


# --- Class 2: authority_basis_record_digest --------------------------------


def authority_basis_record_digest(record: Mapping[str, Any]) -> str:
    """Basis record minus its own ``record_digest``; non-reproduction is invalid."""
    return canonical_digest(_without(record, "record_digest"))


# --- Class 8: synthetic_profile_digest -------------------------------------


def synthetic_profile_digest(profile: Mapping[str, Any]) -> str:
    """Profile minus its own ``profile_digest``; the stored value must reproduce."""
    return canonical_digest(_without(profile, "profile_digest"))


# --- Class 3: authority_decision_digest ------------------------------------


def authority_decision_digest(record: Mapping[str, Any]) -> str:
    """Decision minus its own digest; both currentness bindings participate."""
    return canonical_digest(_without(record, "authority_decision_digest"))


# ---------------------------------------------------------------------------
# Frozen object classes
# ---------------------------------------------------------------------------

AUTHORITY_BASIS_FIELDS: Final = (
    "record_class",
    "basis_id",
    "principal_id",
    "scope",
    "permitted_requested_use",
    "validity_from",
    "validity_until",
    "revocation_state",
    "supersedes",
    "superseded_by",
    "admitted_at",
    "effective_at",
)
ADMISSIBILITY_BASIS_FIELDS: Final = (
    "record_class",
    "basis_id",
    "artifact_class_admitted",
    "requested_use_admitted",
    "validity_from",
    "validity_until",
    "revocation_state",
    "admitted_at",
    "effective_at",
)
PROFILE_FIELDS: Final = (
    "record_class",
    "profile_id",
    "principal_id",
    "role",
    "scope",
    "permitted_requested_use",
    "validity_from",
    "validity_until",
    "revocation_state",
    "assurance_class",
)


@dataclass(frozen=True, slots=True, eq=False)
class BasisRecord:
    """One synthetic authority or admissibility basis, as stored."""

    record_class: str
    source: Mapping[str, Any]
    record_digest: str
    digest_reproduces: bool

    @property
    def basis_id(self) -> str:
        """The basis identifier, as stored."""
        return str(self.source["basis_id"])

    def field(self, name: str, default: Any = None) -> Any:  # noqa: ANN401
        """Read one stored field without copying the whole record."""
        return self.source.get(name, default)

    def as_record(self) -> dict[str, Any]:
        """The stored form plus the reproduced digest."""
        return {**dict(self.source), "record_digest": self.record_digest}


def parse_basis_record(source: Mapping[str, Any]) -> BasisRecord:
    """Parse a basis record, recording whether its stored digest reproduces.

    A malformed record or an irreproducible digest is never repaired here: it is
    carried as ``digest_reproduces=False`` so the evaluation procedure can route
    it to A12 (authority) or A5 (admissibility) rather than silently accepting it.
    """
    if not isinstance(source, Mapping):
        raise AuthorityContractError("basis record is not a mapping")
    record_class = str(source.get("record_class", ""))
    if record_class == AUTHORITY_BASIS_CLASS:
        required = set(AUTHORITY_BASIS_FIELDS)
    elif record_class == ADMISSIBILITY_BASIS_CLASS:
        required = set(ADMISSIBILITY_BASIS_FIELDS)
    else:
        raise AuthorityContractError(f"unknown basis record_class: {record_class!r}")
    stored = source.get("record_digest")
    body = _without(source, "record_digest")
    unknown = sorted(set(body) - required)
    missing = sorted(required - set(body))
    reproduced = authority_basis_record_digest(source)
    malformed = bool(unknown or missing)
    reproduces = (
        not malformed and isinstance(stored, str) and digests_equal(str(stored), reproduced)
    )
    return BasisRecord(
        record_class=record_class,
        source=dict(source),
        record_digest=reproduced,
        digest_reproduces=reproduces,
    )


@dataclass(frozen=True, slots=True, eq=False)
class SyntheticProfile:
    """A producer or reliance-consumer profile; the subject has no profile object.

    The requesting subject is represented solely by
    ``SyntheticAuthorityBasisRecord.principal_id`` — deliberately, so subject
    authority has exactly one home and cannot disagree with itself.
    """

    record_class: str
    profile_id: str
    principal_id: str
    role: str
    source: Mapping[str, Any]
    profile_digest: str
    digest_reproduces: bool

    def as_record(self) -> dict[str, Any]:
        """The stored form plus the reproduced digest."""
        return {**dict(self.source), "profile_digest": self.profile_digest}


def parse_profile(source: Mapping[str, Any]) -> SyntheticProfile:
    """Parse a frozen profile and reproduce its digest."""
    if not isinstance(source, Mapping):
        raise AuthorityContractError("profile is not a mapping")
    if str(source.get("record_class")) not in (PRODUCER_PROFILE_CLASS, CONSUMER_PROFILE_CLASS):
        raise AuthorityContractError("unknown profile record_class")
    body = _without(source, "profile_digest")
    if sorted(set(body)) != sorted(PROFILE_FIELDS):
        raise AuthorityContractError("profile schema is not the frozen closed set")
    reproduced = synthetic_profile_digest(source)
    stored = source.get("profile_digest")
    return SyntheticProfile(
        record_class=str(source["record_class"]),
        profile_id=str(source["profile_id"]),
        principal_id=str(source["principal_id"]),
        role=str(source["role"]),
        source=dict(source),
        profile_digest=reproduced,
        digest_reproduces=isinstance(stored, str) and digests_equal(str(stored), reproduced),
    )


AUTHORITY_DECISION_FIELDS: Final = (
    "record_class",
    "decision_id",
    "artifact_ref",
    "artifact_digest",
    "requested_use",
    "scope",
    "requesting_principal",
    "currentness_resolution_digest",
    "currentness_epoch_digest",
    "evaluation_time",
    "authority_basis_refs",
    "admissibility_basis_refs",
    "authority_class",
    "decision",
    "reason_code_id",
    "reason_code",
    "valid_until",
    "assurance_class",
    "authority_decision_digest",
)


@dataclass(frozen=True, slots=True, eq=False)
class AuthorityDecisionRecord:
    """The authority verdict.  PROCEED authorizes exactly one envelope."""

    decision_id: str
    artifact_ref: str
    artifact_digest: str
    requested_use: str
    scope: str
    requesting_principal: str
    currentness_resolution_digest: str | None
    currentness_epoch_digest: str | None
    evaluation_time: str
    authority_basis_refs: tuple[Mapping[str, Any], ...]
    admissibility_basis_refs: tuple[Mapping[str, Any], ...]
    decision: str
    reason_code_id: str
    reason_code: str
    valid_until: str
    authority_decision_digest: str

    def as_record(self) -> dict[str, Any]:
        """The closed 19-field serialized decision."""
        return {
            "record_class": "AUTHORITY_DECISION",
            "decision_id": self.decision_id,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "requested_use": self.requested_use,
            "scope": self.scope,
            "requesting_principal": self.requesting_principal,
            "currentness_resolution_digest": self.currentness_resolution_digest,
            "currentness_epoch_digest": self.currentness_epoch_digest,
            "evaluation_time": self.evaluation_time,
            "authority_basis_refs": [dict(ref) for ref in self.authority_basis_refs],
            "admissibility_basis_refs": [dict(ref) for ref in self.admissibility_basis_refs],
            "authority_class": AUTHORITY_CLASS,
            "decision": self.decision,
            "reason_code_id": self.reason_code_id,
            "reason_code": self.reason_code,
            "valid_until": self.valid_until,
            "assurance_class": ASSURANCE_CLASS,
            "authority_decision_digest": self.authority_decision_digest,
        }


@dataclass(frozen=True, slots=True, eq=False)
class AuthorityRequest:
    """What the authority layer is asked, with currentness entering as digests only."""

    artifact_ref: str
    artifact_digest: str
    recomputed_artifact_digest: str
    requested_use: str
    scope: str
    requesting_principal: str
    currentness_resolution_digest: str | None
    currentness_epoch_digest: str | None
    evaluation_time: str
    valid_until: str
    decision_id: str


def _basis_ref(record: BasisRecord) -> dict[str, Any]:
    return {
        "basis_id": record.basis_id,
        "record_class": record.record_class,
        "record_digest": record.record_digest,
    }


def _operative(record: BasisRecord, moment: str) -> bool:
    return (
        str(record.field("validity_from")) <= moment <= str(record.field("validity_until"))
        and record.field("revocation_state") == NOT_REVOKED
    )


def evaluate_synthetic_authority(
    *,
    request: AuthorityRequest,
    authority_bases: Sequence[BasisRecord],
    admissibility_bases: Sequence[BasisRecord],
    artifact_class: str,
    escalation_predicate: bool = False,
) -> AuthorityDecisionRecord:
    """The frozen thirteen-step procedure; ordered, first match wins, no other route.

    Authority and admissibility keep their own codes throughout: a missing or
    invalid *authority* basis is A11/A12, never A4/A5, and a revoked
    *admissibility* basis is A13, never A10.  Collapsing them would erase the
    distinction between the two object classes the design separates.
    """
    moment = request.evaluation_time
    subject_bases = [
        record
        for record in authority_bases
        if record.field("principal_id") == request.requesting_principal
        and record.field("scope") == request.scope
    ]

    def decide(code: str) -> AuthorityDecisionRecord:
        if code not in AUTHORITY_REASON_CODES:
            raise AuthorityContractError(f"reason code outside the closed set: {code}")
        verdict = PROCEED if code == "A1" else (ESCALATE if code == "A7" else DENY)
        record = AuthorityDecisionRecord(
            decision_id=request.decision_id,
            artifact_ref=request.artifact_ref,
            artifact_digest=request.artifact_digest,
            requested_use=request.requested_use,
            scope=request.scope,
            requesting_principal=request.requesting_principal,
            currentness_resolution_digest=request.currentness_resolution_digest,
            currentness_epoch_digest=request.currentness_epoch_digest,
            evaluation_time=request.evaluation_time,
            authority_basis_refs=tuple(_basis_ref(item) for item in subject_bases),
            admissibility_basis_refs=tuple(_basis_ref(item) for item in admissibility_bases),
            decision=verdict,
            reason_code_id=code,
            reason_code=AUTHORITY_REASON_CODES[code],
            valid_until=request.valid_until,
            authority_decision_digest="",
        )
        body = record.as_record()
        return AuthorityDecisionRecord(
            decision_id=record.decision_id,
            artifact_ref=record.artifact_ref,
            artifact_digest=record.artifact_digest,
            requested_use=record.requested_use,
            scope=record.scope,
            requesting_principal=record.requesting_principal,
            currentness_resolution_digest=record.currentness_resolution_digest,
            currentness_epoch_digest=record.currentness_epoch_digest,
            evaluation_time=record.evaluation_time,
            authority_basis_refs=record.authority_basis_refs,
            admissibility_basis_refs=record.admissibility_basis_refs,
            decision=record.decision,
            reason_code_id=record.reason_code_id,
            reason_code=record.reason_code,
            valid_until=record.valid_until,
            authority_decision_digest=authority_decision_digest(body),
        )

    # 1 artifact identity
    if not digests_equal(request.recomputed_artifact_digest, request.artifact_digest):
        return decide("A8")
    # 2 currentness must be bound, never inferred
    if not request.currentness_resolution_digest or not request.currentness_epoch_digest:
        return decide("A9")
    # 3 authority basis resolvable for (principal, scope)
    if not subject_bases:
        return decide("A11")
    # 4 authority basis malformed or digest irreproducible
    if any(not record.digest_reproduces for record in subject_bases):
        return decide("A12")
    # 5 authority basis revoked or outside validity
    if any(not _operative(record, moment) for record in subject_bases):
        return decide("A10")
    # 6 competing operative authority bases, no frozen precedence
    if len({record.basis_id for record in subject_bases}) > 1:
        return decide("A6")
    # 7 principal bound to scope
    basis = subject_bases[0]
    if basis.field("principal_id") != request.requesting_principal or basis.field("scope") != (
        request.scope
    ):
        return decide("A2")
    # 8 requested use permitted
    permitted = basis.field("permitted_requested_use", [])
    if request.requested_use not in permitted:
        return decide("A3")
    # 9 admissibility basis resolvable
    applicable = [
        record
        for record in admissibility_bases
        if artifact_class in record.field("artifact_class_admitted", [])
        and request.requested_use in record.field("requested_use_admitted", [])
    ]
    if not applicable:
        return decide("A4")
    # 10 admissibility basis malformed or digest irreproducible
    if any(not record.digest_reproduces for record in applicable):
        return decide("A5")
    # 11 admissibility basis revoked or outside validity
    if any(not _operative(record, moment) for record in applicable):
        return decide("A13")
    # 12 escalation predicate of the frozen profile
    if escalation_predicate:
        return decide("A7")
    # 13 otherwise
    return decide("A1")


CLAIM_CEILING: Final[dict[str, str]] = {
    "CURRENTNESS_TO_AUTHORITY_INTEGRATION": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
    "GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY": (
        "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
    ),
    "RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY": (
        "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
    ),
    "POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE": (
        "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
    ),
    "POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE": (
        "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
    ),
    "HISTORICAL_RELIANCE_RECORD_PRESERVATION": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
}

NOT_ESTABLISHED: Final = (
    "real_CDC_institutional_authority",
    "real_CDC_institutional_reliance",
    "official_CDC_issuance",
    "external_consumer_bypass_resistance",
    "production_enforcement",
    "legal_effect",
    "CDC_acceptance",
    "distributed_reliance_consistency",
    "cross_institution_propagation",
)

DESIGN_SPECIFIC_LIMITS: Final = (
    "the authority layer's content is fictional; only its mechanics are measured",
    "propagation is measured across one process boundary on one machine",
    "refusal is measured while obsolescence is not announced by the historical records",
)
