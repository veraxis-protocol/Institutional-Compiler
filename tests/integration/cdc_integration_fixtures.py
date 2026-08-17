"""Fixtures for integration slice 001.

Everything real is read-only: the frozen Mission-001 Stage-2 result, the frozen
RUN-002 correction result and the frozen synthetic control.  Everything synthetic
is declared as such and is built from the reference vectors published in the
frozen derivation document, so the fixtures and the vectors cannot drift apart.

The evaluation instants are the vector instants deliberately:
``t1 = 2026-08-15T10:00:00Z`` and ``t2 = 2026-08-15T13:00:00Z``, with the
synthetic successor admitted 09:00 and effective 12:00 — the same boundary the
published EPOCH-A/EPOCH-B pair crosses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from oic.cdc_authority import (
    ADMISSIBILITY_BASIS_CLASS,
    AUTHORITY_BASIS_CLASS,
    CONSUMER_PRINCIPAL,
    CONSUMER_PROFILE_CLASS,
    PRODUCER_PRINCIPAL,
    PRODUCER_PROFILE_CLASS,
    SUBJECT_PRINCIPAL,
    authority_basis_record_digest,
    currentness_epoch_digest,
    synthetic_profile_digest,
)
from oic.cdc_currentness import (
    CONTROLLING_RECORD_CLASSES,
    CurrentnessIndex,
    IndexEntry,
    basis_record_digest,
    derive_index_variant,
    historical_artifact_digest,
)
from tests.integration.cdc_currentness_fixtures import (
    AFFECTED_OUTPUT_REFS,
    CONTROL_OUTPUT_REF,
    control_artifact,
    control_document,
    governed_index,
)

SCOPE: Final = "CDC-DEMO-SCOPE-001"
REQUESTED_USE: Final = "DEMONSTRATION_READ"
ARTIFACT_CLASS: Final = "SYNTHETIC_FIXTURE_OUTPUT"

T1: Final = "2026-08-15T10:00:00Z"
T2: Final = "2026-08-15T13:00:00Z"
SUCCESSOR_ADMITTED_AT: Final = "2026-08-15T09:00:00Z"
SUCCESSOR_EFFECTIVE_AT: Final = "2026-08-15T12:00:00Z"
DECISION_VALID_UNTIL: Final = "2026-08-15T23:00:00Z"
ENVELOPE_VALID_UNTIL: Final = "2026-08-15T23:00:00Z"

SYNTHETIC_SUCCESSOR_ID: Final = "SYNTH-SUCCESSOR-001"
SYNTHETIC_SUCCESSOR_REF: Final = f"{SYNTHETIC_SUCCESSOR_ID}#{CONTROL_OUTPUT_REF}"

RUN_ID: Final = "CDC-INTEGRATION-SLICE-001-DEVELOPMENT"
TRACE_ID: Final = "CDC-INTEGRATION-SLICE-001-DEVELOPMENT-TRACE"

AUTHORITY_BASIS_BODY: Final[dict[str, Any]] = {
    "record_class": AUTHORITY_BASIS_CLASS,
    "basis_id": "SYNTH-AUTH-BASIS-001",
    "principal_id": SUBJECT_PRINCIPAL,
    "scope": SCOPE,
    "permitted_requested_use": [REQUESTED_USE],
    "validity_from": "2026-08-15T00:00:00Z",
    "validity_until": "2026-08-22T00:00:00Z",
    "revocation_state": "NOT_REVOKED",
    "supersedes": None,
    "superseded_by": None,
    "admitted_at": "2026-08-15T00:00:00Z",
    "effective_at": "2026-08-15T00:00:00Z",
}

ADMISSIBILITY_BASIS_BODY: Final[dict[str, Any]] = {
    "record_class": ADMISSIBILITY_BASIS_CLASS,
    "basis_id": "SYNTH-ADM-BASIS-001",
    "artifact_class_admitted": [ARTIFACT_CLASS],
    "requested_use_admitted": [REQUESTED_USE],
    "validity_from": "2026-08-15T00:00:00Z",
    "validity_until": "2026-08-22T00:00:00Z",
    "revocation_state": "NOT_REVOKED",
    "admitted_at": "2026-08-15T00:00:00Z",
    "effective_at": "2026-08-15T00:00:00Z",
}

PRODUCER_PROFILE_BODY: Final[dict[str, Any]] = {
    "record_class": PRODUCER_PROFILE_CLASS,
    "profile_id": "SYNTH-PRODUCER-PROFILE-001",
    "principal_id": PRODUCER_PRINCIPAL,
    "role": "PRODUCER",
    "scope": SCOPE,
    "permitted_requested_use": [REQUESTED_USE],
    "validity_from": "2026-08-15T00:00:00Z",
    "validity_until": "2026-08-22T00:00:00Z",
    "revocation_state": "NOT_REVOKED",
    "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
}

CONSUMER_PROFILE_BODY: Final[dict[str, Any]] = {
    **PRODUCER_PROFILE_BODY,
    "record_class": CONSUMER_PROFILE_CLASS,
    "profile_id": "SYNTH-CONSUMER-PROFILE-001",
    "principal_id": CONSUMER_PRINCIPAL,
    "role": "RELIANCE_CONSUMER",
}


def stored(body: dict[str, Any], digest_field: str) -> dict[str, Any]:
    """Attach the reproducing self-digest a stored record must carry."""
    computed = (
        authority_basis_record_digest(body)
        if digest_field == "record_digest"
        else synthetic_profile_digest(body)
    )
    return {**body, digest_field: computed}


def authority_basis(**overrides: object) -> dict[str, Any]:
    """The frozen authority basis, optionally varied for a negative case."""
    return stored({**AUTHORITY_BASIS_BODY, **overrides}, "record_digest")


def admissibility_basis(**overrides: object) -> dict[str, Any]:
    """The frozen admissibility basis, optionally varied."""
    return stored({**ADMISSIBILITY_BASIS_BODY, **overrides}, "record_digest")


def producer_profile() -> dict[str, Any]:
    """The frozen producer profile with its reproducing digest."""
    return stored(PRODUCER_PROFILE_BODY, "profile_digest")


def consumer_profile() -> dict[str, Any]:
    """The frozen reliance-consumer profile with its reproducing digest."""
    return stored(CONSUMER_PROFILE_BODY, "profile_digest")


def synthetic_successor_entry() -> IndexEntry:
    """A successor for the synthetic control: admitted 09:00, effective 12:00."""
    record = {
        "output_ref": CONTROL_OUTPUT_REF,
        "record_class": "CORRECTION_SUCCESSOR_RECORD",
        "successor_id": SYNTHETIC_SUCCESSOR_ID,
        "correction_event_id": "SYNTH-CORRECTION-EVT-001",
        "predecessor_candidate_id": "SYNTH-CANDIDATE-001",
        "superseded_at_utc": SUCCESSOR_EFFECTIVE_AT,
    }
    return IndexEntry(
        output_ref=CONTROL_OUTPUT_REF,
        record_ref=SYNTHETIC_SUCCESSOR_REF,
        record_class="CORRECTION_SUCCESSOR_RECORD",
        record_digest=basis_record_digest(record),
        effective_at=SUCCESSOR_EFFECTIVE_AT,
        admitted_at=SUCCESSOR_ADMITTED_AT,
        record=record,
    )


def index_without_successor() -> CurrentnessIndex:
    """The governed index as frozen: the control is CURRENT at t1 and t2."""
    return governed_index()


def index_with_future_successor() -> CurrentnessIndex:
    """The governed index plus one successor that becomes operative at 12:00."""
    base = governed_index()
    return derive_index_variant(
        base,
        entries=[*base.entries, synthetic_successor_entry()],
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )


def index_without_control() -> CurrentnessIndex:
    """The governed index with no synthetic control admitted at all."""
    return governed_index(with_control=False)


def governing_records(index: CurrentnessIndex, output_ref: str) -> list[dict[str, Any]]:
    """The governing records for one output, in the epoch's reduced form."""
    return [
        {
            "output_ref": entry.output_ref,
            "record_ref": entry.record_ref,
            "record_digest": entry.record_digest,
            "record_class": entry.record_class,
            "effective_at": entry.effective_at,
            "admitted_at": entry.admitted_at,
        }
        for entry in index.entries_for(output_ref)
        if entry.record_class in CONTROLLING_RECORD_CLASSES
    ]


def epoch_for(index: CurrentnessIndex, output_ref: str, as_of: str) -> str:
    """The as-of epoch for one output under one index."""
    attestation = index.attestation_for(output_ref)
    return currentness_epoch_digest(
        output_ref=output_ref,
        as_of=as_of,
        governing_records=governing_records(index, output_ref),
        completeness_attestation_digest=(
            None if attestation is None else attestation.completeness_digest
        ),
    )


def control_body_digest() -> str:
    """The synthetic control's artifact digest, recomputed from its bytes."""
    return historical_artifact_digest(control_artifact()["body"])


def write_json(path: Path, payload: Any) -> dict[str, Any]:  # noqa: ANN401
    """Persist a fixture file and return its identity."""
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(data)
    return {"path": str(path), "bytes": len(data)}


def control_fixture_document() -> dict[str, Any]:
    """The whole frozen synthetic control document, read-only."""
    return control_document()
