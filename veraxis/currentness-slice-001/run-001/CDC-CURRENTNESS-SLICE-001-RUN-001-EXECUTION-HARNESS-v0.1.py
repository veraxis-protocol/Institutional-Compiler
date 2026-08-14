"""Single-use result-bearing execution harness for currentness slice 001.

Authority: OWNER-AUTHORIZATION-CURRENTNESS-SLICE-001-EXEC-001, single use, no
automatic retry.  ``execute_slice`` is the only result-bearing entry point; it
claims an exclusive attempt record before doing anything and refuses a second
invocation in the same process or a later one.

The harness observes.  It does not adjudicate, and it never repairs a failing
observation into a passing one: every case records actual alongside expected and
a boolean match, whichever way the match falls.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final = Path("/private/tmp/claude-501/cleanroom")
RUNTIME_ROOT: Final = Path("/private/tmp/cdc-currentness-slice-001-run-001")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from oic.cdc_currentness import (  # noqa: E402
    CURRENT,
    DENY,
    ELIGIBILITY_DETERMINATION_RECORD,
    FUTURE_SUPERSESSION_SCHEDULED,
    GOVERNED_BASIS_ATTESTATION_PATH,
    HISTORICAL_ARTIFACT_IDENTITY_RECORD,
    PROCEED,
    SUPERSEDED,
    SUPERSESSION_RECORD,
    SYNTHETIC_CONTROL_PATH,
    UNKNOWN,
    BasisCompletenessAttestation,
    CurrentnessIndex,
    CurrentnessIndexError,
    IndexEntry,
    UseGateProfile,
    UseGateRequest,
    basis_record_digest,
    build_currentness_index,
    canonical_bytes,
    canonical_digest,
    completeness_digest,
    currentness_index_digest,
    derive_index_variant,
    evaluate_present_use,
    historical_artifact_digest,
    observation_digest,
    package_digest,
    parse_basis_completeness_attestation,
    persisted_file_sha256,
    resolution_digest,
    resolve_currentness,
    use_gate_decision_digest,
)
from tests.integration.cdc_currentness_fixtures import (  # noqa: E402
    AFFECTED_OUTPUT_REFS,
    CONTROL_OUTPUT_REF,
    CORRECTION_EVENT_ID,
    CORRECTION_RESULT_PATH,
    CORRECTION_RESULT_SHA256,
    CONTROLLING_SUCCESSOR_ID,
    EVALUATED_AT,
    FROZEN_ARTIFACT_DIGESTS,
    INDEX_ADMITTED_AT,
    MISSION_SCOPE_REF,
    PREDECESSOR_CANDIDATE_ID,
    STAGE_2_RAW_RESULT_PATH,
    STAGE_2_RAW_RESULT_SHA256,
    SUPERSEDED_AT,
    SYNTHETIC_CONTROL_SHA256,
    control_artifact,
    control_bytes,
    control_document,
    correction_bytes,
    frozen_drafts,
    governed_index,
    historical_artifact,
    stage_2_bytes,
)

EXECUTION_AUTHORIZATION_PATH: Final = (
    REPO_ROOT
    / "docs/operations/CDC-CURRENTNESS-SLICE-001-RESULT-BEARING-EXECUTION-AUTHORIZATION-001.json"
)
EXECUTION_AUTHORIZATION_SHA256: Final = (
    "8657729a8bfa381fbf790bdb4eb6ec5621774c07b88264692e15f30342ff2f94"
)
IMPLEMENTATION_COMMIT: Final = "6cade50a8ee041cc941eb91fd7295c42b9a8a3e9"
IMPLEMENTATION_TREE: Final = "c196dd43816cdf10661e598f3901ed7e369792bd"
RUN_ID: Final = "CDC-CURRENTNESS-SLICE-001-RUN-001"
TRACE_ID: Final = "CDC-CURRENTNESS-SLICE-001-TRACE-001"

PROFILE: Final = UseGateProfile()
LATER: Final = "2026-08-14T22:20:00Z"
FUTURE_EFFECTIVE_AT: Final = "2026-09-01T00:00:00Z"

ATTEMPT_RECORD: Final = (
    RUNTIME_ROOT / f".cdc-currentness-slice-001-attempt-{EXECUTION_AUTHORIZATION_SHA256}.json"
)

_INVOCATIONS = {"execute_slice": 0}


class HarnessRefusalError(RuntimeError):
    """The harness refused to proceed rather than exceed its authority."""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim_single_use_attempt() -> dict[str, Any]:
    """Claim the one authorized attempt by exclusive creation."""
    record = {
        "attempt_class": "CDC_CURRENTNESS_SLICE_001_RESULT_BEARING_ATTEMPT",
        "authorization_id": "OWNER-AUTHORIZATION-CURRENTNESS-SLICE-001-EXEC-001",
        "execution_authorization_sha256": EXECUTION_AUTHORIZATION_SHA256,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "run_id": RUN_ID,
        "trace_id": TRACE_ID,
        "claimed_at": _now(),
        "attempt_state": "CLAIMED_NOT_CONSUMED",
    }
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    try:
        descriptor = os.open(ATTEMPT_RECORD, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise HarnessRefusalError(
            "the single authorized attempt is already claimed; no retry is authorized"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
    return record


def _verify_authority() -> dict[str, Any]:
    """Refuse to run unless the authorization bytes are the frozen ones."""
    payload = EXECUTION_AUTHORIZATION_PATH.read_bytes()
    observed = persisted_file_sha256(payload)
    if observed != EXECUTION_AUTHORIZATION_SHA256:
        raise HarnessRefusalError(
            f"execution authorization identity mismatch: observed {observed}"
        )
    authorization = json.loads(payload.decode("utf-8"))
    for field, expected in (
        ("authorization_id", "OWNER-AUTHORIZATION-CURRENTNESS-SLICE-001-EXEC-001"),
        ("authorization_class", "SINGLE_USE_RESULT_BEARING_EXECUTION"),
        ("implementation_commit", IMPLEMENTATION_COMMIT),
        ("implementation_tree", IMPLEMENTATION_TREE),
        ("run_id", RUN_ID),
        ("trace_id", TRACE_ID),
    ):
        if authorization.get(field) != expected:
            raise HarnessRefusalError(f"authorization field {field} is not the frozen value")
    if authorization.get("result_bearing_execution_authorized") is not True:
        raise HarnessRefusalError("the instrument does not authorize result-bearing execution")
    if authorization.get("single_use") is not True or authorization.get("automatic_retry") is not (
        False
    ):
        raise HarnessRefusalError("the instrument is not single-use without retry")
    return {
        "execution_authorization_path": str(EXECUTION_AUTHORIZATION_PATH),
        "execution_authorization_bytes": len(payload),
        "execution_authorization_sha256": observed,
        "authorization_id": authorization["authorization_id"],
        "official_handoff_authorized": authorization["official_handoff_authorized"],
        "institutional_reliance_authorized": authorization["institutional_reliance_authorized"],
        "production_claim_authorized": authorization["production_claim_authorized"],
    }


def _artifact_identities() -> dict[str, str]:
    """Hash everything whose preservation the slice claims, at one instant."""
    identities = {
        f"artifact::{ref}": historical_artifact_digest(frozen_drafts()[ref])
        for ref in AFFECTED_OUTPUT_REFS
    }
    identities["file::stage_2_raw_result"] = persisted_file_sha256(stage_2_bytes())
    identities["file::correction_successor_result"] = persisted_file_sha256(correction_bytes())
    identities["file::synthetic_control"] = persisted_file_sha256(control_bytes())
    return identities


def _observe(output_ref: str, artifact: dict[str, Any], index: CurrentnessIndex) -> dict[str, Any]:
    """One real observation: resolve, then gate, then record both verbatim."""
    digest_before = historical_artifact_digest(artifact["body"])
    resolution = resolve_currentness(
        output_ref=output_ref,
        historical_artifact=artifact,
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    )
    decision = evaluate_present_use(
        request=UseGateRequest(
            output_ref=output_ref,
            requested_use="cite the historical output in a new present operation",
            requested_operation_class="PRESENT_USE_OF_HISTORICAL_OUTPUT",
            consequential=True,
            requesting_scope_ref=MISSION_SCOPE_REF,
            requested_at=EVALUATED_AT,
        ),
        historical_artifact=artifact,
        currentness_index=index,
        profile=PROFILE,
        run_metadata=_run_metadata(),
    )
    digest_after = historical_artifact_digest(artifact["body"])
    attestation = index.attestation_for(output_ref)
    return {
        "output_ref": output_ref,
        "historical_artifact_digest_before": digest_before,
        "historical_artifact_digest_after": digest_after,
        "historical_artifact_digest_preserved": digest_before == digest_after,
        "historical_state": resolution.historical_state,
        "currentness_state": resolution.currentness_state,
        "eligibility": resolution.eligibility,
        "reason_code_id": resolution.reason_code_id,
        "reason_code": resolution.reason_code,
        "secondary_states": list(resolution.secondary_states),
        "controlling_successor_ref": resolution.controlling_successor_ref,
        "correction_event_ref": resolution.correction_event_ref,
        "competing_refs": list(resolution.competing_refs),
        "scheduled_supersession": resolution.scheduled_supersession,
        "basis_completeness_attestation_present": attestation is not None,
        "basis_completeness_attestation_digest": (
            None if attestation is None else attestation.completeness_digest
        ),
        "basis_completeness_reproduces": (
            None
            if attestation is None
            else completeness_digest(attestation.source) == attestation.completeness_digest
        ),
        "basis_records": [dict(record) for record in resolution.basis_records],
        "resolution_digest": resolution.resolution_digest,
        "gate_decision": decision.decision,
        "gate_reason_code_id": decision.reason_code_id,
        "gate_reason_code": decision.reason_code,
        "controlling_evidence_pointer": (
            None
            if decision.controlling_evidence_pointer is None
            else dict(decision.controlling_evidence_pointer)
        ),
        "next_gate": decision.next_gate,
        "use_gate_decision_digest": decision.use_gate_decision_digest,
        "institutional_event_emitted": False,
        "index_digest": index.index_digest,
        "evaluated_at": EVALUATED_AT,
    }


def _run_metadata() -> dict[str, str]:
    return {
        "run_id": RUN_ID,
        "trace_id": TRACE_ID,
        "producer": "CDC-CURRENTNESS-SLICE-001-RUN-001-EXECUTION-HARNESS-v0.1.py",
        "producer_version": persisted_file_sha256(Path(__file__).read_bytes()),
        "occurred_at": EVALUATED_AT,
        "recorded_at": EVALUATED_AT,
    }


def _gate_for(
    output_ref: str, artifact: dict[str, Any], index: CurrentnessIndex, **overrides: Any
) -> Any:
    fields: dict[str, Any] = {
        "output_ref": output_ref,
        "requested_use": "adversarial present-use attempt",
        "requested_operation_class": "PRESENT_USE_OF_HISTORICAL_OUTPUT",
        "consequential": True,
        "requesting_scope_ref": MISSION_SCOPE_REF,
        "requested_at": EVALUATED_AT,
    }
    fields.update(overrides)
    return evaluate_present_use(
        request=UseGateRequest(**fields),
        historical_artifact=artifact,
        currentness_index=index,
        profile=PROFILE,
        run_metadata=_run_metadata(),
    )


def _supersession_entry(
    output_ref: str,
    *,
    successor_id: str = CONTROLLING_SUCCESSOR_ID,
    effective_at: str = SUPERSEDED_AT,
    predecessor_candidate_id: str = PREDECESSOR_CANDIDATE_ID,
) -> IndexEntry:
    record = {
        "output_ref": output_ref,
        "record_class": SUPERSESSION_RECORD,
        "successor_id": successor_id,
        "correction_event_id": CORRECTION_EVENT_ID,
        "predecessor_candidate_id": predecessor_candidate_id,
        "superseded_at_utc": effective_at,
    }
    return IndexEntry(
        output_ref=output_ref,
        record_ref=f"{successor_id}#{output_ref}",
        record_class=SUPERSESSION_RECORD,
        record_digest=basis_record_digest(record),
        effective_at=effective_at,
        admitted_at=INDEX_ADMITTED_AT,
        record=record,
    )


def _case(
    case_id: str,
    mutation: str,
    *,
    expected_state: str,
    expected_decision: str | None,
    expected_reason_code: str,
    actual_state: str,
    actual_decision: str | None,
    actual_reason_code: str,
    subject_refs: list[str],
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "case_id": case_id,
        "mutation_applied": mutation,
        "expected_reason_code": expected_reason_code,
        "observed_reason_code": actual_reason_code,
        "observed_state": actual_state,
        "subject_refs": subject_refs,
        "evaluated_at": EVALUATED_AT,
    }
    return {
        **record,
        "expected_state": expected_state,
        "expected_decision": expected_decision,
        "observed_decision": actual_decision,
        "match": (
            actual_state == expected_state
            and actual_decision == expected_decision
            and actual_reason_code == expected_reason_code
        ),
        "detail": detail or {},
        "observation_digest": observation_digest(record),
    }


def _adversarial_observations(index: CurrentnessIndex) -> list[dict[str, Any]]:
    """The frozen T-ADV-A..R universe, executed here rather than cited."""
    target = AFFECTED_OUTPUT_REFS[0]
    artifact = historical_artifact(target)
    observations: list[dict[str, Any]] = []

    reduced = derive_index_variant(
        index,
        entries=[entry for entry in index.entries if entry.output_ref != target],
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )
    resolution = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=reduced, evaluated_at=EVALUATED_AT
    )
    observations.append(
        _case(
            "T-ADV-A",
            "every currentness record for the output removed from the index",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R5",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[target],
        )
    )

    entries = [entry for entry in index.entries if entry.output_ref != target]
    identity_record = {
        "output_ref": target,
        "historical_artifact_digest": FROZEN_ARTIFACT_DIGESTS[target],
    }
    entries.append(
        IndexEntry(
            output_ref=target,
            record_ref=f"ARTIFACT-IDENTITY#{target}",
            record_class=HISTORICAL_ARTIFACT_IDENTITY_RECORD,
            record_digest=basis_record_digest(identity_record),
            effective_at=None,
            admitted_at=INDEX_ADMITTED_AT,
            record=identity_record,
        )
    )
    entries.append(_supersession_entry(target, predecessor_candidate_id="CAND-NOT-REFERENCED"))
    variant = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=variant, evaluated_at=EVALUATED_AT
    )
    observations.append(
        _case(
            "T-ADV-B",
            "successor bound to a predecessor the artifact never referenced",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R9",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[target],
        )
    )

    decision = _gate_for(target, historical_artifact(AFFECTED_OUTPUT_REFS[1]), index)
    observations.append(
        _case(
            "T-ADV-C",
            "output_ref of OUTPUT-01 presented with the artifact of OUTPUT-02",
            expected_state=UNKNOWN,
            expected_decision=DENY,
            expected_reason_code="G5",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target, AFFECTED_OUTPUT_REFS[1]],
        )
    )

    stale = resolve_currentness(
        output_ref=target,
        historical_artifact=artifact,
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    )
    decision = _gate_for(
        target, artifact, index, requested_at=LATER, precomputed_resolution=stale.as_record()
    )
    observations.append(
        _case(
            "T-ADV-D",
            "precomputed resolution older than the frozen profile window",
            expected_state=SUPERSEDED,
            expected_decision=DENY,
            expected_reason_code="G7",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
        )
    )

    decision = _gate_for(target, artifact, index, asserted_currentness_state=CURRENT)
    observations.append(
        _case(
            "T-ADV-E",
            "caller asserts CURRENT through the request",
            expected_state=SUPERSEDED,
            expected_decision=DENY,
            expected_reason_code="G8",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
        )
    )

    tampered = {**artifact, "body": {**artifact["body"], "label_en": "tampered"}}
    decision = _gate_for(target, tampered, index)
    observations.append(
        _case(
            "T-ADV-F",
            "historical artifact bytes modified in an isolated copy",
            expected_state=UNKNOWN,
            expected_decision=DENY,
            expected_reason_code="G5",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
            detail={
                "frozen_artifact_digest_unchanged": (
                    historical_artifact_digest(frozen_drafts()[target])
                    == FROZEN_ARTIFACT_DIGESTS[target]
                )
            },
        )
    )

    hidden_entries = [
        entry
        for entry in index.entries
        if entry.output_ref != target or entry.record_class == HISTORICAL_ARTIFACT_IDENTITY_RECORD
    ]
    hidden = derive_index_variant(
        index, entries=hidden_entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=hidden, evaluated_at=EVALUATED_AT
    )
    forged_attestation = parse_basis_completeness_attestation(
        {
            "scope_ref": MISSION_SCOPE_REF,
            "covered_output_ref": target,
            "record_kinds_covered": [SUPERSESSION_RECORD, ELIGIBILITY_DETERMINATION_RECORD],
            "basis_snapshot_refs": [],
            "basis_snapshot_digests": [],
            "completeness_as_of": INDEX_ADMITTED_AT,
            "admitted_at": INDEX_ADMITTED_AT,
            "fixture_class": None,
        },
        admission_path=GOVERNED_BASIS_ATTESTATION_PATH,
    )
    try:
        derive_index_variant(
            index,
            entries=hidden_entries,
            attestations=[forged_attestation],
            governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
        )
        admission_refused = False
    except CurrentnessIndexError:
        admission_refused = True
    observations.append(
        _case(
            "T-ADV-G",
            "successor hidden; only the predecessor identity presented",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R5",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[target],
            detail={
                "completeness_attestation_admission_refused": admission_refused,
                "current_returned": resolution.currentness_state == CURRENT,
            },
        )
    )

    other = next(
        entry.record
        for entry in index.entries_for(AFFECTED_OUTPUT_REFS[1])
        if entry.record_class == SUPERSESSION_RECORD
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=artifact,
        index=index,
        evaluated_at=EVALUATED_AT,
        asserted_controlling_record=other,
    )
    observations.append(
        _case(
            "T-ADV-H",
            "another output's valid successor asserted as controlling",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R8",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[target, AFFECTED_OUTPUT_REFS[1]],
        )
    )

    future = derive_index_variant(
        index,
        entries=[
            *index.entries,
            _supersession_entry(
                CONTROL_OUTPUT_REF,
                successor_id="SYNTH-SUCCESSOR-FUTURE",
                effective_at=FUTURE_EFFECTIVE_AT,
                predecessor_candidate_id="SYNTH-CANDIDATE",
            ),
        ],
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=future,
        evaluated_at=EVALUATED_AT,
    )
    observations.append(
        _case(
            "T-ADV-I",
            "successor effective in the future",
            expected_state=CURRENT,
            expected_decision=None,
            expected_reason_code="R1",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
            detail={
                "secondary_states": list(resolution.secondary_states),
                "future_supersession_scheduled": (
                    FUTURE_SUPERSESSION_SCHEDULED in resolution.secondary_states
                ),
                "scheduled_supersession": resolution.scheduled_supersession,
                "labelled_superseded_before_effective_instant": (
                    resolution.currentness_state == SUPERSEDED
                ),
            },
        )
    )

    competing = derive_index_variant(
        index,
        entries=[
            *index.entries,
            _supersession_entry(target, successor_id="EBAWU-P-001-C-TENDER-01-CORR-999"),
        ],
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )
    resolution = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=competing, evaluated_at=EVALUATED_AT
    )
    decision = _gate_for(target, artifact, competing)
    observations.append(
        _case(
            "T-ADV-J",
            "two simultaneously operative successors claim the same output",
            expected_state=UNKNOWN,
            expected_decision=DENY,
            expected_reason_code="G4",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
            detail={
                "resolver_reason_code_id": resolution.reason_code_id,
                "resolver_reason_code_expected": "R7",
                "competing_refs": list(resolution.competing_refs),
                "controlling_successor_ref": resolution.controlling_successor_ref,
            },
        )
    )

    stripped = derive_index_variant(
        index, attestations=[], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=stripped,
        evaluated_at=EVALUATED_AT,
    )
    observations.append(
        _case(
            "T-ADV-K",
            "basis completeness attestation removed",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R5",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
        )
    )

    source = dict(control_document()["basis_completeness_attestation"])
    source["scope_ref"] = "SOME-OTHER-SCOPE"
    invalid = parse_basis_completeness_attestation(source, admission_path=SYNTHETIC_CONTROL_PATH)
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=derive_index_variant(
            index, attestations=[invalid], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
        ),
        evaluated_at=EVALUATED_AT,
    )
    observations.append(
        _case(
            "T-ADV-L",
            "attestation whose scope does not cover the queried output",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R6",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
        )
    )

    genuine = parse_basis_completeness_attestation(
        control_document()["basis_completeness_attestation"],
        admission_path=SYNTHETIC_CONTROL_PATH,
    )
    forged = BasisCompletenessAttestation(
        scope_ref=genuine.scope_ref,
        covered_output_ref=genuine.covered_output_ref,
        record_kinds_covered=genuine.record_kinds_covered,
        basis_snapshot_refs=genuine.basis_snapshot_refs,
        basis_snapshot_digests=genuine.basis_snapshot_digests,
        completeness_as_of=genuine.completeness_as_of,
        admitted_at=genuine.admitted_at,
        fixture_class=genuine.fixture_class,
        completeness_digest="0" * 64,
        source=genuine.source,
        admission_path=SYNTHETIC_CONTROL_PATH,
    )
    parse_refused = False
    try:
        parse_basis_completeness_attestation(
            {**dict(genuine.source), "completeness_digest": "0" * 64},
            admission_path=SYNTHETIC_CONTROL_PATH,
        )
    except CurrentnessIndexError:
        parse_refused = True
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=derive_index_variant(
            index, attestations=[forged], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
        ),
        evaluated_at=EVALUATED_AT,
    )
    observations.append(
        _case(
            "T-ADV-M",
            "attestation carrying a forged completeness digest",
            expected_state=UNKNOWN,
            expected_decision=None,
            expected_reason_code="R6",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
            detail={"admission_parse_refused_forged_digest": parse_refused},
        )
    )

    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=EVALUATED_AT,
    )
    observations.append(
        _case(
            "T-ADV-N",
            "valid successor records for other outputs merely present in the corpus",
            expected_state=CURRENT,
            expected_decision=None,
            expected_reason_code="R1",
            actual_state=resolution.currentness_state,
            actual_decision=None,
            actual_reason_code=resolution.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
            detail={
                "foreign_supersession_records_present": sum(
                    1 for entry in index.entries if entry.record_class == SUPERSESSION_RECORD
                )
            },
        )
    )

    precomputed = resolve_currentness(
        output_ref=target,
        historical_artifact=artifact,
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    )
    decision = _gate_for(target, artifact, index, precomputed_resolution=precomputed.as_record())
    observations.append(
        _case(
            "T-ADV-O",
            "precomputed resolution whose digest equals the governed recomputation",
            expected_state=SUPERSEDED,
            expected_decision=DENY,
            expected_reason_code="G2",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
            detail={"hint_accepted": decision.reason_code_id not in {"G6", "G7", "G9"}},
        )
    )

    tampered_hint = precomputed.as_record()
    tampered_hint["currentness_state"] = CURRENT
    decision = _gate_for(target, artifact, index, precomputed_resolution=tampered_hint)
    observations.append(
        _case(
            "T-ADV-P",
            "precomputed resolution body mutated to CURRENT, digest field left stale",
            expected_state=SUPERSEDED,
            expected_decision=DENY,
            expected_reason_code="G9",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
        )
    )

    decision = _gate_for(target, artifact, index, expected_index_digest="0" * 64)
    observations.append(
        _case(
            "T-ADV-Q",
            "caller's expected index identity does not match the index",
            expected_state=SUPERSEDED,
            expected_decision=DENY,
            expected_reason_code="G10",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[target],
        )
    )

    without_control = governed_index(with_control=False)
    decision = _gate_for(
        CONTROL_OUTPUT_REF, control_artifact(), without_control, consequential=False
    )
    observations.append(
        _case(
            "T-ADV-R",
            "UNKNOWN currentness under explicitly non-consequential use",
            expected_state=UNKNOWN,
            expected_decision=DENY,
            expected_reason_code="G4",
            actual_state=decision.currentness_state,
            actual_decision=decision.decision,
            actual_reason_code=decision.reason_code_id,
            subject_refs=[CONTROL_OUTPUT_REF],
            detail={"profile_unknown_disposition": PROFILE.unknown_disposition},
        )
    )
    return observations


def _digest_observations(index: CurrentnessIndex) -> list[dict[str, Any]]:
    """T-DIG-01..09, each recording actual against the frozen rule or vector."""
    control = control_document()
    body = control["historical_artifact"]["body"]
    attestation = control["basis_completeness_attestation"]
    target = AFFECTED_OUTPUT_REFS[0]
    artifact = historical_artifact(target)
    cases: list[dict[str, Any]] = []

    micro_actual = canonical_digest({"b": 2, "a": "é"})
    body_actual = historical_artifact_digest(body)
    cases.append(
        {
            "case_id": "T-DIG-01",
            "digest_class": "historical_artifact_digest",
            "checks": [
                {
                    "name": "canonical micro-vector bytes",
                    "actual": canonical_bytes({"b": 2, "a": "é"}).decode("utf-8"),
                    "expected": '{"a":"é","b":2}',
                },
                {
                    "name": "canonical micro-vector sha256",
                    "actual": micro_actual,
                    "expected": (
                        "06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de"
                    ),
                },
                {
                    "name": "control body canonical bytes",
                    "actual": len(canonical_bytes(body)),
                    "expected": 341,
                },
                {
                    "name": "control body sha256",
                    "actual": body_actual,
                    "expected": (
                        "6f9fe1ccbabd6195d474f09a365a5ca4cc32f7ed8cf1f41e8acddd22e592eed0"
                    ),
                },
            ],
        }
    )

    record = {"output_ref": "X", "record_class": SUPERSESSION_RECORD, "successor_id": "S"}
    cases.append(
        {
            "case_id": "T-DIG-02",
            "digest_class": "basis_record_digest",
            "checks": [
                {
                    "name": "record hashed exactly as stored",
                    "actual": basis_record_digest(record),
                    "expected": canonical_digest(record),
                },
                {
                    "name": "no field excluded",
                    "actual": basis_record_digest(record)
                    != canonical_digest({"output_ref": "X", "record_class": SUPERSESSION_RECORD}),
                    "expected": True,
                },
            ],
        }
    )

    paired = {
        **attestation,
        "basis_snapshot_refs": ["b", "a"],
        "basis_snapshot_digests": ["2", "1"],
    }
    reordered = {
        **attestation,
        "basis_snapshot_refs": ["a", "b"],
        "basis_snapshot_digests": ["1", "2"],
    }
    cases.append(
        {
            "case_id": "T-DIG-03",
            "digest_class": "completeness_digest",
            "checks": [
                {
                    "name": "attestation canonical bytes",
                    "actual": len(canonical_bytes(attestation)),
                    "expected": 617,
                },
                {
                    "name": "attestation sha256",
                    "actual": completeness_digest(attestation),
                    "expected": (
                        "a9ffff71467a0880f77e3fec8b4740a0cdb74953e8fb9d743b1fdd7617ce66c6"
                    ),
                },
                {
                    "name": "paired arrays are not independently sorted",
                    "actual": completeness_digest(paired) != completeness_digest(reordered),
                    "expected": True,
                },
            ],
        }
    )

    reversed_index = derive_index_variant(
        index,
        entries=tuple(reversed(index.entries)),
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )
    cases.append(
        {
            "case_id": "T-DIG-04",
            "digest_class": "currentness_index_digest",
            "checks": [
                {
                    "name": "insertion order independence",
                    "actual": reversed_index.index_digest,
                    "expected": index.index_digest,
                },
                {
                    "name": "recomputed from reduced entries",
                    "actual": currentness_index_digest(
                        scope_ref=MISSION_SCOPE_REF,
                        entries=[entry.reduced() for entry in index.entries],
                        attestations=[att.as_record() for att in index.attestations],
                        admitted_at=INDEX_ADMITTED_AT,
                    ),
                    "expected": index.index_digest,
                },
                {
                    "name": "record bodies not embedded",
                    "actual": all("record" not in entry.reduced() for entry in index.entries),
                    "expected": True,
                },
            ],
        }
    )

    first = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=index, evaluated_at=EVALUATED_AT
    )
    later = resolve_currentness(
        output_ref=target, historical_artifact=artifact, index=index, evaluated_at=LATER
    )
    cases.append(
        {
            "case_id": "T-DIG-05",
            "digest_class": "resolution_digest",
            "checks": [
                {
                    "name": "self-exclusion reproduces",
                    "actual": resolution_digest(first.as_record()),
                    "expected": first.resolution_digest,
                },
                {
                    "name": "evaluation time inside the domain",
                    "actual": first.resolution_digest != later.resolution_digest,
                    "expected": True,
                },
                {
                    "name": "same state at both instants",
                    "actual": first.currentness_state == later.currentness_state,
                    "expected": True,
                },
            ],
        }
    )

    decision = _gate_for(target, artifact, index)
    decision_record = decision.as_record()
    cases.append(
        {
            "case_id": "T-DIG-06",
            "digest_class": "use_gate_decision_digest",
            "checks": [
                {
                    "name": "self-exclusion reproduces",
                    "actual": use_gate_decision_digest(decision_record),
                    "expected": decision_record["use_gate_decision_digest"],
                },
                {
                    "name": "binds the resolution digest",
                    "actual": decision_record["resolution_digest"],
                    "expected": decision.resolution_digest,
                },
                {
                    "name": "binds the observed artifact digest",
                    "actual": decision_record["artifact_observed_digest"],
                    "expected": FROZEN_ARTIFACT_DIGESTS[target],
                },
            ],
        }
    )

    observation = {
        "case_id": "T-DIG-07-PROBE",
        "mutation_applied": "none",
        "expected_reason_code": "R1",
        "observed_reason_code": "R1",
        "observed_state": CURRENT,
        "subject_refs": [CONTROL_OUTPUT_REF],
        "evaluated_at": EVALUATED_AT,
    }
    cases.append(
        {
            "case_id": "T-DIG-07",
            "digest_class": "observation_digest",
            "checks": [
                {
                    "name": "seven-field domain",
                    "actual": observation_digest(observation),
                    "expected": canonical_digest(observation),
                },
                {
                    "name": "extra fields excluded from the domain",
                    "actual": observation_digest(
                        {**observation, "observation_digest": "x", "note": "y"}
                    ),
                    "expected": canonical_digest(observation),
                },
            ],
        }
    )

    package_probe = {
        "record_class": "CDC_CURRENTNESS_SLICE_001_RAW_EXECUTION_PACKAGE",
        "members": [{"path": "a.json", "bytes": 10, "sha256": "ab" * 32}],
        "package_digest": "0" * 64,
    }
    cases.append(
        {
            "case_id": "T-DIG-08",
            "digest_class": "package_digest",
            "checks": [
                {
                    "name": "self-exclusion, member identities only",
                    "actual": package_digest(package_probe),
                    "expected": canonical_digest(
                        {
                            key: value
                            for key, value in package_probe.items()
                            if key != "package_digest"
                        }
                    ),
                }
            ],
        }
    )

    payload = control_bytes()
    cases.append(
        {
            "case_id": "T-DIG-09",
            "digest_class": "persisted_file_sha256",
            "checks": [
                {"name": "persisted bytes", "actual": len(payload), "expected": 2275},
                {
                    "name": "persisted file sha256",
                    "actual": persisted_file_sha256(payload),
                    "expected": SYNTHETIC_CONTROL_SHA256,
                },
                {
                    "name": "distinct from the canonical-form digest",
                    "actual": canonical_digest(json.loads(payload.decode("utf-8")))
                    != persisted_file_sha256(payload),
                    "expected": True,
                },
            ],
        }
    )

    for case in cases:
        case["match"] = all(check["actual"] == check["expected"] for check in case["checks"])
    return cases


def execute_slice() -> dict[str, Any]:
    """The one authorized result-bearing execution.  Called exactly once."""
    if _INVOCATIONS["execute_slice"]:
        raise HarnessRefusalError("a second result-bearing execution is not authorized")
    _INVOCATIONS["execute_slice"] += 1
    authority = _verify_authority()
    attempt = _claim_single_use_attempt()
    started_at = _now()

    identities_before = _artifact_identities()
    index = governed_index()

    resolutions: list[dict[str, Any]] = []
    for output_ref in AFFECTED_OUTPUT_REFS:
        resolutions.append(_observe(output_ref, historical_artifact(output_ref), index))
    control_observation = _observe(CONTROL_OUTPUT_REF, control_artifact(), index)
    control_observation["fixture_class"] = "SYNTHETIC_UNAFFECTED_CONTROL"
    control_observation["derived_from_real_mission_001_output"] = False
    control_observation["represents_a_real_unaffected_CDC_output"] = False

    adversarial = _adversarial_observations(index)
    digests = _digest_observations(index)
    identities_after = _artifact_identities()
    completed_at = _now()

    ATTEMPT_RECORD.write_bytes(
        (
            json.dumps(
                {**attempt, "attempt_state": "CONSUMED_AFTER_FIRST_EXECUTION"},
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        ).encode()
    )

    return {
        "run_id": RUN_ID,
        "trace_id": TRACE_ID,
        "authority": authority,
        "run_metadata": _run_metadata(),
        "started_at": started_at,
        "completed_at": completed_at,
        "index_digest": index.index_digest,
        "index_scope_ref": index.scope_ref,
        "basis_source_identities": dict(index.basis_source_identities),
        "real_resolutions": resolutions,
        "control_resolution": control_observation,
        "adversarial": adversarial,
        "digests": digests,
        "identities_before": identities_before,
        "identities_after": identities_after,
        "execute_slice_invocations": _INVOCATIONS["execute_slice"],
        "attempt_state": "CONSUMED_AFTER_FIRST_EXECUTION",
        "semantic_adjudication_performed": False,
        "institutional_events_emitted": 0,
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "self_designed_and_self_adjudicated": True,
        "independent_review_claim": False,
    }


def _write(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = RUNTIME_ROOT / name
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(data)
    return {"path": str(path), "bytes": len(data), "sha256": persisted_file_sha256(data)}


def persist(result: dict[str, Any]) -> dict[str, Any]:
    """Freeze the run's observations, then the package that identifies them."""
    common = {
        "run_id": result["run_id"],
        "trace_id": result["trace_id"],
        "authorization_id": result["authority"]["authorization_id"],
        "execution_authorization_sha256": result["authority"]["execution_authorization_sha256"],
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "semantic_adjudication_performed": False,
    }
    members = [
        _write(
            "CDC-CURRENTNESS-SLICE-001-RUN-001-RESOLUTION-OBSERVATIONS-v0.1.json",
            {
                **common,
                "record_class": "CDC_CURRENTNESS_SLICE_001_RESOLUTION_OBSERVATIONS",
                "index_digest": result["index_digest"],
                "real_population": result["real_resolutions"],
                "synthetic_liveness_control": result["control_resolution"],
            },
        ),
        _write(
            "CDC-CURRENTNESS-SLICE-001-RUN-001-USE-GATE-OBSERVATIONS-v0.1.json",
            {
                **common,
                "record_class": "CDC_CURRENTNESS_SLICE_001_USE_GATE_OBSERVATIONS",
                "profile": {
                    "profile_id": PROFILE.profile_id,
                    "unknown_disposition": PROFILE.unknown_disposition,
                    "max_resolution_age_seconds": PROFILE.max_resolution_age_seconds,
                    "next_gate_on_current": PROFILE.next_gate_on_current,
                },
                "decisions": [
                    {
                        "output_ref": observation["output_ref"],
                        "requested_use": (
                            "cite the historical output in a new present operation"
                        ),
                        "requested_operation_class": "PRESENT_USE_OF_HISTORICAL_OUTPUT",
                        "consequential": True,
                        "gate_decision": observation["gate_decision"],
                        "gate_reason_code_id": observation["gate_reason_code_id"],
                        "gate_reason_code": observation["gate_reason_code"],
                        "controlling_successor_ref": observation["controlling_successor_ref"],
                        "controlling_evidence_pointer": observation[
                            "controlling_evidence_pointer"
                        ],
                        "next_gate": observation["next_gate"],
                        "consequential_gate_reached": observation["gate_decision"] == PROCEED,
                        "institutional_event_emitted": False,
                        "use_gate_decision_digest": observation["use_gate_decision_digest"],
                    }
                    for observation in (
                        *result["real_resolutions"],
                        result["control_resolution"],
                    )
                ],
            },
        ),
        _write(
            "CDC-CURRENTNESS-SLICE-001-RUN-001-ADVERSARIAL-OBSERVATIONS-v0.1.json",
            {
                **common,
                "record_class": "CDC_CURRENTNESS_SLICE_001_ADVERSARIAL_OBSERVATIONS",
                "cases_expected": 18,
                "cases_observed": len(result["adversarial"]),
                "cases_matching_frozen_expectation": sum(
                    1 for case in result["adversarial"] if case["match"]
                ),
                "cases": result["adversarial"],
            },
        ),
        _write(
            "CDC-CURRENTNESS-SLICE-001-RUN-001-DIGEST-OBSERVATIONS-v0.1.json",
            {
                **common,
                "record_class": "CDC_CURRENTNESS_SLICE_001_DIGEST_OBSERVATIONS",
                "digest_classes_expected": 9,
                "digest_classes_observed": len(result["digests"]),
                "digest_classes_matching": sum(1 for case in result["digests"] if case["match"]),
                "cases": result["digests"],
            },
        ),
        _write(
            "CDC-CURRENTNESS-SLICE-001-RUN-001-IMMUTABILITY-OBSERVATION-v0.1.json",
            {
                **common,
                "record_class": "CDC_CURRENTNESS_SLICE_001_IMMUTABILITY_OBSERVATION",
                "identities_before": result["identities_before"],
                "identities_after": result["identities_after"],
                "expected_frozen_artifact_digests": dict(FROZEN_ARTIFACT_DIGESTS),
                "expected_stage_2_raw_result_sha256": STAGE_2_RAW_RESULT_SHA256,
                "expected_correction_result_sha256": CORRECTION_RESULT_SHA256,
                "mismatched": sorted(
                    name
                    for name, value in result["identities_after"].items()
                    if result["identities_before"][name] != value
                ),
                "byte_identity_preserved": result["identities_before"]
                == result["identities_after"],
                "historical_evidence_cleaned_or_rewritten": False,
                "sources": {
                    "stage_2_raw_result_path": str(STAGE_2_RAW_RESULT_PATH),
                    "correction_result_path": str(CORRECTION_RESULT_PATH),
                },
            },
        ),
    ]

    package = {
        **common,
        "record_class": "CDC_CURRENTNESS_SLICE_001_RAW_EXECUTION_PACKAGE",
        "schema_version": "CDC-CURRENTNESS-SLICE-001-RAW-EXECUTION-PACKAGE-v0.1",
        "runtime_root": str(RUNTIME_ROOT),
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "run_metadata": result["run_metadata"],
        "execution_authorization_path": result["authority"]["execution_authorization_path"],
        "execution_authorization_bytes": result["authority"]["execution_authorization_bytes"],
        "index_digest": result["index_digest"],
        "basis_source_identities": result["basis_source_identities"],
        "result_bearing_execution_invocations": result["execute_slice_invocations"],
        "automatic_retry_performed": False,
        "second_result_bearing_execution": False,
        "attempt_state": result["attempt_state"],
        "attempt_record": {
            "path": str(ATTEMPT_RECORD),
            "bytes": len(ATTEMPT_RECORD.read_bytes()),
            "sha256": persisted_file_sha256(ATTEMPT_RECORD.read_bytes()),
        },
        "members": members,
        "real_outputs_observed": len(result["real_resolutions"]),
        "real_outputs_resolved_superseded": sum(
            1
            for item in result["real_resolutions"]
            if item["currentness_state"] == SUPERSEDED and item["reason_code_id"] == "R2"
        ),
        "real_outputs_gate_deny_g2": sum(
            1
            for item in result["real_resolutions"]
            if item["gate_decision"] == DENY and item["gate_reason_code_id"] == "G2"
        ),
        "synthetic_control_current_r1": (
            result["control_resolution"]["currentness_state"] == CURRENT
            and result["control_resolution"]["reason_code_id"] == "R1"
        ),
        "synthetic_control_proceed_g1": (
            result["control_resolution"]["gate_decision"] == PROCEED
            and result["control_resolution"]["gate_reason_code_id"] == "G1"
        ),
        "adversarial_cases_observed": len(result["adversarial"]),
        "adversarial_cases_matching": sum(1 for c in result["adversarial"] if c["match"]),
        "digest_cases_observed": len(result["digests"]),
        "digest_cases_matching": sum(1 for c in result["digests"] if c["match"]),
        "byte_identity_preserved": result["identities_before"] == result["identities_after"],
        "institutional_events_emitted": 0,
        "official_handoff": "PROHIBITED",
        "claim_ceiling_if_supported": {
            "EXECUTABLE_CURRENTNESS_RESOLUTION": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
            "STALE_OUTPUT_PRESENT_USE_REFUSAL": "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION",
            "HISTORICAL_ARTIFACT_PRESERVATION_DURING_CURRENTNESS_CHANGE": (
                "MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION"
            ),
        },
        "not_established": [
            "real_unaffected_CDC_output_resolves_CURRENT",
            "consumer_bypass_resistance",
            "institutional_currentness_propagation",
            "institutional_reliance",
            "official_CDC_issuance",
            "legal_effect",
            "production_conformance",
            "CDC_acceptance",
            "general_rollback_resistance",
            "distributed_consistency_across_institutions",
        ],
        "self_designed_and_self_adjudicated": True,
        "independent_review_claim": False,
        "package_digest": "",
    }
    package["package_digest"] = package_digest(package)
    identity = _write(
        "CDC-CURRENTNESS-SLICE-001-RUN-001-RAW-EXECUTION-PACKAGE-v0.1.json", package
    )
    return {"members": members, "package": package, "package_identity": identity}


if __name__ == "__main__":
    outcome = execute_slice()
    frozen = persist(outcome)
    print(json.dumps(frozen["package_identity"], indent=2, sort_keys=True))
