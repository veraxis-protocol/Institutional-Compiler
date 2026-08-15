"""Governed propagation across a real process boundary, integration slice 001.

Implements the closed ``GovernedPropagationEnvelope`` frozen by
``…SEMANTIC-DESIGN-v0.4.md`` (03ca22e9…) and digest Class 4 of
``INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.3.md`` (600a8f19…).

Propagation is not a return value.  The producer serializes a closed envelope,
materializes it durably with an fsync, and only then publishes a ready marker by
exclusive creation, so a consumer can never read a partially written file.  A
separate process reads that file.  An in-process object handoff is not propagation
and this module gives no way to perform one: the envelope leaves as bytes.

Three roles are bound separately and no field carries more than one of them —
the requesting subject whose use was authority-evaluated, the producer that
serialized the envelope, and the intended reliance consumer.  The positive path is
therefore never a producer handing evidence to itself.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from oic.cdc_authority import (
    ASSURANCE_CLASS,
    canonical_bytes,
    canonical_digest,
    digests_equal,
)
from oic.errors import OICError

ENVELOPE_RECORD_CLASS: Final = "GOVERNED_PROPAGATION_ENVELOPE"
ENVELOPE_SCHEMA_VERSION: Final = "CDC-INTEGRATION-SLICE-001-ENVELOPE-v0.4"
READY_MARKER_SUFFIX: Final = ".ready"

PROPAGATION_REASON_CODES: Final[dict[str, str]] = {
    "P1": "ENVELOPE_VALID",
    "P2": "ENVELOPE_DIGEST_MISMATCH",
    "P3": "ENVELOPE_EXPIRED",
    "P4": "ENVELOPE_ARTIFACT_MISMATCH",
    "P5": "ENVELOPE_SCOPE_MISMATCH",
    "P6": "ENVELOPE_PRINCIPAL_MISMATCH",
    "P7": "ENVELOPE_REQUESTED_USE_MISMATCH",
    "P8": "ENVELOPE_UNKNOWN_FIELD_PRESENT",
    "P9": "ENVELOPE_EVIDENCE_BINDING_INCOMPLETE",
    "P10": "ENVELOPE_PRODUCER_IDENTITY_UNVERIFIED",
    "P11": "ENVELOPE_SUBSTITUTED",
    "P12": "ENVELOPE_INTENDED_CONSUMER_MISMATCH",
}
PROPAGATION_REASON_CODE_COUNT: Final = len(PROPAGATION_REASON_CODES)

ENVELOPE_FIELDS: Final = (
    "record_class",
    "envelope_id",
    "schema_version",
    "artifact_ref",
    "artifact_digest",
    "requested_use",
    "scope",
    "requesting_subject_principal",
    "producer_identity",
    "intended_consumer_principal",
    "currentness_resolution_digest",
    "currentness_index_digest",
    "currentness_epoch_digest",
    "authority_decision_digest",
    "authority_basis_refs",
    "admissibility_basis_refs",
    "evidence_refs",
    "produced_at",
    "valid_until",
    "assurance_class",
    "envelope_digest",
)
PRODUCER_IDENTITY_FIELDS: Final = ("producer_principal", "process_id", "run_id", "trace_id")

# Bindings whose absence is an incomplete envelope rather than an unknown field.
REQUIRED_BINDINGS: Final = (
    "artifact_ref",
    "artifact_digest",
    "requested_use",
    "scope",
    "requesting_subject_principal",
    "intended_consumer_principal",
    "currentness_resolution_digest",
    "currentness_index_digest",
    "currentness_epoch_digest",
    "authority_decision_digest",
)


class PropagationError(OICError):
    """The envelope could not be built or materialized under the frozen contract."""


def envelope_digest(record: Mapping[str, Any]) -> str:
    """Class 4 — envelope minus its own digest; three roles participate."""
    return canonical_digest(
        {key: value for key, value in record.items() if key != "envelope_digest"}
    )


@dataclass(frozen=True, slots=True, eq=False)
class ProducerIdentity:
    """Who serialized the envelope, and in which process."""

    producer_principal: str
    process_id: int
    run_id: str
    trace_id: str

    def as_record(self) -> dict[str, Any]:
        """The four-field identity carried in the envelope."""
        return {
            "producer_principal": self.producer_principal,
            "process_id": self.process_id,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
        }


@dataclass(frozen=True, slots=True, eq=False)
class GovernedPropagationEnvelope:
    """A closed, self-digesting envelope; unknown field fails closed."""

    envelope_id: str
    artifact_ref: str
    artifact_digest: str
    requested_use: str
    scope: str
    requesting_subject_principal: str
    producer_identity: ProducerIdentity
    intended_consumer_principal: str
    currentness_resolution_digest: str
    currentness_index_digest: str
    currentness_epoch_digest: str
    authority_decision_digest: str
    authority_basis_refs: tuple[Mapping[str, Any], ...]
    admissibility_basis_refs: tuple[Mapping[str, Any], ...]
    evidence_refs: tuple[Mapping[str, Any], ...]
    produced_at: str
    valid_until: str
    envelope_digest: str

    def as_record(self) -> dict[str, Any]:
        """The closed 21-field serialized envelope."""
        return {
            "record_class": ENVELOPE_RECORD_CLASS,
            "envelope_id": self.envelope_id,
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "requested_use": self.requested_use,
            "scope": self.scope,
            "requesting_subject_principal": self.requesting_subject_principal,
            "producer_identity": self.producer_identity.as_record(),
            "intended_consumer_principal": self.intended_consumer_principal,
            "currentness_resolution_digest": self.currentness_resolution_digest,
            "currentness_index_digest": self.currentness_index_digest,
            "currentness_epoch_digest": self.currentness_epoch_digest,
            "authority_decision_digest": self.authority_decision_digest,
            "authority_basis_refs": [dict(ref) for ref in self.authority_basis_refs],
            "admissibility_basis_refs": [dict(ref) for ref in self.admissibility_basis_refs],
            "evidence_refs": [dict(ref) for ref in self.evidence_refs],
            "produced_at": self.produced_at,
            "valid_until": self.valid_until,
            "assurance_class": ASSURANCE_CLASS,
            "envelope_digest": self.envelope_digest,
        }


def build_envelope(
    *,
    envelope_id: str,
    artifact_ref: str,
    artifact_digest: str,
    requested_use: str,
    scope: str,
    requesting_subject_principal: str,
    producer_identity: ProducerIdentity,
    intended_consumer_principal: str,
    currentness_resolution_digest: str,
    currentness_index_digest: str,
    currentness_epoch_digest: str,
    authority_decision_digest: str,
    authority_basis_refs: Sequence[Mapping[str, Any]],
    admissibility_basis_refs: Sequence[Mapping[str, Any]],
    evidence_refs: Sequence[Mapping[str, Any]],
    produced_at: str,
    valid_until: str,
) -> GovernedPropagationEnvelope:
    """Build an envelope, refusing the producer/consumer collapse outright."""
    if producer_identity.producer_principal == intended_consumer_principal:
        raise PropagationError(
            "producer_principal must differ from the intended reliance consumer"
        )
    envelope = GovernedPropagationEnvelope(
        envelope_id=envelope_id,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
        requested_use=requested_use,
        scope=scope,
        requesting_subject_principal=requesting_subject_principal,
        producer_identity=producer_identity,
        intended_consumer_principal=intended_consumer_principal,
        currentness_resolution_digest=currentness_resolution_digest,
        currentness_index_digest=currentness_index_digest,
        currentness_epoch_digest=currentness_epoch_digest,
        authority_decision_digest=authority_decision_digest,
        authority_basis_refs=tuple(authority_basis_refs),
        admissibility_basis_refs=tuple(admissibility_basis_refs),
        evidence_refs=tuple(evidence_refs),
        produced_at=produced_at,
        valid_until=valid_until,
        envelope_digest="",
    )
    digest = envelope_digest(envelope.as_record())
    return GovernedPropagationEnvelope(
        envelope_id=envelope.envelope_id,
        artifact_ref=envelope.artifact_ref,
        artifact_digest=envelope.artifact_digest,
        requested_use=envelope.requested_use,
        scope=envelope.scope,
        requesting_subject_principal=envelope.requesting_subject_principal,
        producer_identity=envelope.producer_identity,
        intended_consumer_principal=envelope.intended_consumer_principal,
        currentness_resolution_digest=envelope.currentness_resolution_digest,
        currentness_index_digest=envelope.currentness_index_digest,
        currentness_epoch_digest=envelope.currentness_epoch_digest,
        authority_decision_digest=envelope.authority_decision_digest,
        authority_basis_refs=envelope.authority_basis_refs,
        admissibility_basis_refs=envelope.admissibility_basis_refs,
        evidence_refs=envelope.evidence_refs,
        produced_at=envelope.produced_at,
        valid_until=envelope.valid_until,
        envelope_digest=digest,
    )


def materialize_envelope(record: Mapping[str, Any], path: Path) -> dict[str, Any]:
    """Write, flush, fsync, then publish a ready marker by exclusive creation.

    The marker is the commit point.  A consumer that requires the marker cannot
    observe a partially written envelope, and the marker cannot be created twice.
    """
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    marker = path.with_name(path.name + READY_MARKER_SUFFIX)
    marker_payload = (
        json.dumps(
            {
                "envelope_path": str(path),
                "envelope_bytes": len(payload),
                "envelope_file_sha256": hashlib.sha256(payload).hexdigest(),
                "commit_discipline": "FSYNC_THEN_EXCLUSIVE_READY_MARKER",
            },
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    marker_descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(marker_descriptor, "wb") as handle:
        handle.write(marker_payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "envelope_path": str(path),
        "ready_marker_path": str(marker),
        "envelope_bytes": len(payload),
        "envelope_file_sha256": hashlib.sha256(payload).hexdigest(),
        "durably_materialized": True,
        "fsync_performed": True,
    }


@dataclass(frozen=True, slots=True, eq=False)
class EnvelopeParse:
    """The outcome of parsing an envelope against the frozen closed schema."""

    accepted: bool
    reason_code_id: str
    reason_code: str
    record: Mapping[str, Any] | None
    unknown_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    recomputed_digest: str | None


def parse_envelope(payload: bytes) -> EnvelopeParse:
    """Parse against the closed schema; unknown or missing fields fail closed.

    Integrity is checked before closure only in the sense that a document that is
    not JSON at all cannot be digested; a structurally valid document with an
    unknown field is P8, and one missing a required binding is P9.
    """

    def refuse(code: str, **extra: Any) -> EnvelopeParse:  # noqa: ANN401
        return EnvelopeParse(
            accepted=False,
            reason_code_id=code,
            reason_code=PROPAGATION_REASON_CODES[code],
            record=extra.get("record"),
            unknown_fields=tuple(extra.get("unknown", ())),
            missing_fields=tuple(extra.get("missing", ())),
            recomputed_digest=extra.get("recomputed"),
        )

    try:
        record = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return refuse("P11")
    if not isinstance(record, Mapping):
        return refuse("P11")
    unknown = sorted(set(record) - set(ENVELOPE_FIELDS))
    if unknown:
        return refuse("P8", record=record, unknown=unknown)
    missing = sorted(set(ENVELOPE_FIELDS) - set(record))
    if missing:
        return refuse("P9", record=record, missing=missing)
    if record.get("record_class") != ENVELOPE_RECORD_CLASS or record.get("schema_version") != (
        ENVELOPE_SCHEMA_VERSION
    ):
        return refuse("P11", record=record)
    identity = record.get("producer_identity")
    if not isinstance(identity, Mapping) or sorted(identity) != sorted(PRODUCER_IDENTITY_FIELDS):
        return refuse("P9", record=record, missing=["producer_identity"])
    empty = [name for name in REQUIRED_BINDINGS if not record.get(name)]
    if empty:
        return refuse("P9", record=record, missing=empty)
    recomputed = envelope_digest(record)
    if not digests_equal(str(record.get("envelope_digest", "")), recomputed):
        return refuse("P2", record=record, recomputed=recomputed)
    return EnvelopeParse(
        accepted=True,
        reason_code_id="P1",
        reason_code=PROPAGATION_REASON_CODES["P1"],
        record=record,
        unknown_fields=(),
        missing_fields=(),
        recomputed_digest=recomputed,
    )


def read_materialized_envelope(path: Path) -> bytes:
    """Read an envelope only once its ready marker exists."""
    marker = path.with_name(path.name + READY_MARKER_SUFFIX)
    if not marker.is_file():
        raise PropagationError(f"envelope has no ready marker; refusing partial read: {path}")
    return path.read_bytes()


__all__ = [
    "ENVELOPE_FIELDS",
    "ENVELOPE_RECORD_CLASS",
    "ENVELOPE_SCHEMA_VERSION",
    "PROPAGATION_REASON_CODES",
    "PROPAGATION_REASON_CODE_COUNT",
    "EnvelopeParse",
    "GovernedPropagationEnvelope",
    "ProducerIdentity",
    "PropagationError",
    "build_envelope",
    "canonical_bytes",
    "envelope_digest",
    "materialize_envelope",
    "parse_envelope",
    "read_materialized_envelope",
]
