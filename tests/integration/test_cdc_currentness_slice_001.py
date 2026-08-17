"""The 44-test semantic universe of currentness slice 001.

Test identities are reconstructed from
``CURRENTNESS-PROPAGATION-SLICE-001-SEMANTIC-DESIGN-v0.2.md`` §9, and digest
behaviour from ``CURRENTNESS-SLICE-001-DIGEST-DERIVATION-v0.1.md`` §1-§3.  Each
pytest node id is exactly one semantic test id; parameterization is used only
where the semantic design itself enumerates one test per output.

These are development tests establishing conformance to the frozen contract.
They are not the result-bearing slice demonstration, and they produce no frozen
execution package.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from oic.cdc_currentness import (
    CURRENT,
    DENY,
    ELIGIBILITY_DETERMINATION_RECORD,
    FUTURE_SUPERSESSION_SCHEDULED,
    GOVERNED_BASIS_ATTESTATION_PATH,
    HISTORICAL_ARTIFACT_IDENTITY_RECORD,
    INELIGIBLE,
    PROCEED,
    RESOLVER_REASON_CODES,
    SUPERSEDED,
    SUPERSESSION_RECORD,
    SYNTHETIC_CONTROL_PATH,
    UNKNOWN,
    USE_GATE_REASON_CODES,
    BasisCompletenessAttestation,
    CurrentnessIndex,
    CurrentnessIndexError,
    IndexEntry,
    UseGateDecision,
    UseGateProfile,
    UseGateRequest,
    basis_record_digest,
    build_currentness_index,
    canonical_bytes,
    canonical_digest,
    completeness_digest,
    current_requires_attested_complete_basis,
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
from tests.integration.cdc_currentness_fixtures import (
    AFFECTED_OUTPUT_REFS,
    CONTROL_OUTPUT_REF,
    CONTROLLING_SUCCESSOR_ID,
    CORRECTION_EVENT_ID,
    CORRECTION_RESULT_SHA256,
    EVALUATED_AT,
    FROZEN_ARTIFACT_DIGESTS,
    INDEX_ADMITTED_AT,
    INDEX_OBSERVED_AT,
    MISSION_SCOPE_REF,
    PREDECESSOR_CANDIDATE_ID,
    RUN_METADATA,
    SESSION_START_ARTIFACT_DIGESTS,
    SESSION_START_IDENTITIES,
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

PROFILE = UseGateProfile()

LATER = "2026-08-14T22:20:00Z"
FUTURE_EFFECTIVE_AT = "2026-09-01T00:00:00Z"


def _request(output_ref: str, **overrides: object) -> UseGateRequest:
    fields: dict[str, Any] = {
        "output_ref": output_ref,
        "requested_use": "cite the historical output in a new present operation",
        "requested_operation_class": "PRESENT_USE_OF_HISTORICAL_OUTPUT",
        "consequential": True,
        "requesting_scope_ref": MISSION_SCOPE_REF,
        "requested_at": EVALUATED_AT,
    }
    fields.update(overrides)
    return UseGateRequest(**fields)


def _gate(
    output_ref: str,
    artifact: Mapping[str, Any],
    index: CurrentnessIndex,
    **overrides: object,
) -> UseGateDecision:
    return evaluate_present_use(
        request=_request(output_ref, **overrides),
        historical_artifact=artifact,
        currentness_index=index,
        profile=PROFILE,
        run_metadata=RUN_METADATA,
    )


def _supersession_entry(
    output_ref: str,
    *,
    successor_id: str = CONTROLLING_SUCCESSOR_ID,
    effective_at: str = SUPERSEDED_AT,
    predecessor_candidate_id: str = PREDECESSOR_CANDIDATE_ID,
    admitted_at: str = INDEX_ADMITTED_AT,
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
        admitted_at=admitted_at,
        record=record,
    )


# ---------------------------------------------------------------------------
# T-STALE-RES-01..05 — each real output resolves SUPERSEDED
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_ref",
    AFFECTED_OUTPUT_REFS,
    ids=[f"T-STALE-RES-0{n}" for n in range(1, 6)],
)
def test_stale_resolution(output_ref: str) -> None:
    resolution = resolve_currentness(
        output_ref=output_ref,
        historical_artifact=historical_artifact(output_ref),
        index=governed_index(),
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == SUPERSEDED
    assert resolution.reason_code_id == "R2"
    assert resolution.reason_code == RESOLVER_REASON_CODES["R2"]
    assert resolution.controlling_successor_ref == CONTROLLING_SUCCESSOR_ID
    assert resolution.correction_event_ref == CORRECTION_EVENT_ID
    # The pre-existing provenance ineligibility is carried, never collapsed into
    # the supersession fact.
    assert resolution.historical_state == "INELIGIBLE_PROVENANCE_INCOMPLETE"
    assert "ELIGIBILITY_DETERMINATION_ALSO_PRESENT" in resolution.secondary_states


# ---------------------------------------------------------------------------
# T-STALE-GATE-01..05 — each gate DENYs with an addressable pointer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_ref",
    AFFECTED_OUTPUT_REFS,
    ids=[f"T-STALE-GATE-0{n}" for n in range(1, 6)],
)
def test_stale_gate_refusal(output_ref: str) -> None:
    decision = _gate(output_ref, historical_artifact(output_ref), governed_index())
    assert decision.decision == DENY
    assert decision.reason_code_id == "G2"
    assert decision.reason_code == USE_GATE_REASON_CODES["G2"]
    assert decision.next_gate is None
    pointer = decision.controlling_evidence_pointer
    assert pointer is not None
    assert pointer["successor_ref"] == CONTROLLING_SUCCESSOR_ID
    assert pointer["correction_event_ref"] == CORRECTION_EVENT_ID
    # The pointer must address real evidence, not merely name it.
    index = governed_index()
    known = {entry.record_digest for entry in index.entries_for(output_ref)}
    assert set(pointer["basis_record_digests"]) <= known
    assert decision.as_record()["consequential_gate_reached"] is False


# ---------------------------------------------------------------------------
# T-BYTE-01..05 — byte identity across the whole slice
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_ref",
    AFFECTED_OUTPUT_REFS,
    ids=[f"T-BYTE-0{n}" for n in range(1, 6)],
)
def test_historical_bytes_unchanged(output_ref: str) -> None:
    # Exercise the whole path first, then measure.
    _gate(output_ref, historical_artifact(output_ref), governed_index())
    draft = frozen_drafts()[output_ref]
    observed = historical_artifact_digest(draft)
    assert observed == FROZEN_ARTIFACT_DIGESTS[output_ref]
    assert observed == SESSION_START_ARTIFACT_DIGESTS[output_ref]
    assert persisted_file_sha256(stage_2_bytes()) == STAGE_2_RAW_RESULT_SHA256
    assert persisted_file_sha256(stage_2_bytes()) == SESSION_START_IDENTITIES["stage_2_file"]
    assert persisted_file_sha256(correction_bytes()) == CORRECTION_RESULT_SHA256
    assert persisted_file_sha256(control_bytes()) == SYNTHETIC_CONTROL_SHA256


# ---------------------------------------------------------------------------
# T-CTRL-RES-01 / T-CTRL-GATE-01 — the synthetic control, liveness only
# ---------------------------------------------------------------------------


def test_control_resolves_current() -> None:
    """T-CTRL-RES-01."""
    index = governed_index()
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == CURRENT
    assert resolution.reason_code_id == "R1"
    assert current_requires_attested_complete_basis(resolution, index)
    control = control_document()
    assert control["fixture_class"] == "SYNTHETIC_UNAFFECTED_CONTROL"
    assert control["derived_from_real_mission_001_output"] is False


def test_control_gate_proceeds() -> None:
    """T-CTRL-GATE-01."""
    decision = _gate(CONTROL_OUTPUT_REF, control_artifact(), governed_index())
    assert decision.decision == PROCEED
    assert decision.reason_code_id == "G1"
    assert decision.next_gate == "AUTHORITY_AND_ADMISSIBILITY_GATE"


# ---------------------------------------------------------------------------
# T-ADV-A .. T-ADV-R — 18 adversarial cases
# ---------------------------------------------------------------------------


def test_adv_a_currentness_record_removed() -> None:
    """T-ADV-A — record removed → UNKNOWN."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    reduced = derive_index_variant(
        index,
        entries=[entry for entry in index.entries if entry.output_ref != target],
        governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=reduced,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R5"


def test_adv_b_wrong_successor_pointer() -> None:
    """T-ADV-B — successor bound to a predecessor the artifact never referenced."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    entries = [entry for entry in index.entries if entry.output_ref != target]
    entries.append(
        IndexEntry(
            output_ref=target,
            record_ref=f"ARTIFACT-IDENTITY#{target}",
            record_class=HISTORICAL_ARTIFACT_IDENTITY_RECORD,
            record_digest=basis_record_digest({"output_ref": target}),
            effective_at=None,
            admitted_at=INDEX_ADMITTED_AT,
            record={
                "output_ref": target,
                "historical_artifact_digest": FROZEN_ARTIFACT_DIGESTS[target],
            },
        )
    )
    entries.append(_supersession_entry(target, predecessor_candidate_id="CAND-NOT-REFERENCED"))
    variant = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R9"


def test_adv_c_output_ref_artifact_mismatch() -> None:
    """T-ADV-C — ref and artifact disagree."""
    decision = _gate(
        AFFECTED_OUTPUT_REFS[0], historical_artifact(AFFECTED_OUTPUT_REFS[1]), governed_index()
    )
    assert decision.decision == DENY
    assert decision.reason_code_id == "G5"
    assert decision.currentness_state == UNKNOWN


def test_adv_d_expired_resolution() -> None:
    """T-ADV-D — a precomputed resolution older than the profile window."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    stale = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    )
    decision = _gate(
        target,
        historical_artifact(target),
        index,
        requested_at=LATER,
        precomputed_resolution=stale.as_record(),
    )
    assert decision.decision == DENY
    assert decision.reason_code_id == "G7"


def test_adv_e_caller_asserts_current() -> None:
    """T-ADV-E — a caller-supplied currency assertion is refused explicitly."""
    target = AFFECTED_OUTPUT_REFS[0]
    decision = _gate(
        target,
        historical_artifact(target),
        governed_index(),
        asserted_currentness_state=CURRENT,
    )
    assert decision.decision == DENY
    assert decision.reason_code_id == "G8"
    assert decision.currentness_state == SUPERSEDED


def test_adv_f_historical_bytes_modified() -> None:
    """T-ADV-F — a mutated copy of the artifact fails integrity."""
    target = AFFECTED_OUTPUT_REFS[0]
    artifact = historical_artifact(target)
    tampered = {**artifact, "body": {**artifact["body"], "label_en": "tampered"}}
    decision = _gate(target, tampered, governed_index())
    assert decision.decision == DENY
    assert decision.reason_code_id == "G5"
    # The real frozen artifact was never the mutated one.
    assert historical_artifact_digest(frozen_drafts()[target]) == FROZEN_ARTIFACT_DIGESTS[target]


def test_adv_g_successor_hidden() -> None:
    """T-ADV-G — hiding the successor cannot manufacture currency."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    entries = [
        entry
        for entry in index.entries
        if entry.output_ref != target or entry.record_class == HISTORICAL_ARTIFACT_IDENTITY_RECORD
    ]
    hidden = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=hidden,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.currentness_state != CURRENT
    assert resolution.reason_code_id == "R5"
    # Nor can a completeness attestation be admitted for an output the governed
    # source is known to control.
    forged = parse_basis_completeness_attestation(
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
    with pytest.raises(CurrentnessIndexError, match="governed source holds a controlling"):
        derive_index_variant(
            index,
            entries=entries,
            attestations=[forged],
            governed_controlling_output_refs=AFFECTED_OUTPUT_REFS,
        )


def test_adv_h_successor_for_another_output_asserted() -> None:
    """T-ADV-H — asserting another output's successor is a binding error."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    other = index.entries_for(AFFECTED_OUTPUT_REFS[1])
    asserted = next(entry.record for entry in other if entry.record_class == SUPERSESSION_RECORD)
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=EVALUATED_AT,
        asserted_controlling_record=asserted,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R8"


def test_adv_i_future_effective_successor() -> None:
    """T-ADV-I — a scheduled successor does not make the artifact superseded."""
    index = governed_index()
    entries = [
        *index.entries,
        _supersession_entry(
            CONTROL_OUTPUT_REF,
            successor_id="SYNTH-SUCCESSOR-FUTURE",
            effective_at=FUTURE_EFFECTIVE_AT,
            predecessor_candidate_id="SYNTH-CANDIDATE",
        ),
    ]
    variant = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == CURRENT
    assert resolution.reason_code_id == "R1"
    assert FUTURE_SUPERSESSION_SCHEDULED in resolution.secondary_states
    scheduled = resolution.scheduled_supersession
    assert scheduled is not None
    assert scheduled["successor_ref"] == "SYNTH-SUCCESSOR-FUTURE"
    assert scheduled["effective_at"] == FUTURE_EFFECTIVE_AT
    assert scheduled["set_aside_reason_code_id"] == "R11"


def test_adv_j_competing_successors() -> None:
    """T-ADV-J — two operative claimants, no invented precedence."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    entries = [
        *index.entries,
        _supersession_entry(target, successor_id="EBAWU-P-001-C-TENDER-01-CORR-999"),
    ]
    variant = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R7"
    assert resolution.controlling_successor_ref is None
    assert len(resolution.competing_refs) == 2
    decision = _gate(target, historical_artifact(target), variant)
    assert decision.decision == DENY
    assert decision.reason_code_id == "G4"


def test_adv_k_attestation_missing() -> None:
    """T-ADV-K — no attestation, no CURRENT."""
    index = governed_index()
    variant = derive_index_variant(
        index, attestations=[], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R5"


def test_adv_l_attestation_invalid() -> None:
    """T-ADV-L — an attestation whose scope does not cover the queried output."""
    index = governed_index()
    source = dict(control_document()["basis_completeness_attestation"])
    source["scope_ref"] = "SOME-OTHER-SCOPE"
    invalid = parse_basis_completeness_attestation(source, admission_path=SYNTHETIC_CONTROL_PATH)
    variant = derive_index_variant(
        index, attestations=[invalid], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R6"


def test_adv_m_attestation_forged() -> None:
    """T-ADV-M — a forged completeness digest does not reproduce."""
    source = dict(control_document()["basis_completeness_attestation"])
    source["completeness_digest"] = "0" * 64
    with pytest.raises(CurrentnessIndexError, match="does not reproduce"):
        parse_basis_completeness_attestation(source, admission_path=SYNTHETIC_CONTROL_PATH)

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
    index = governed_index()
    variant = derive_index_variant(
        index, attestations=[forged], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == UNKNOWN
    assert resolution.reason_code_id == "R6"


def test_adv_n_unrelated_record_present() -> None:
    """T-ADV-N — presence is not relevance; CURRENT stands."""
    index = governed_index()
    assert any(entry.record_class == SUPERSESSION_RECORD for entry in index.entries)
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == CURRENT
    assert resolution.reason_code_id == "R1"


def test_adv_o_precomputed_resolution_digest_equal() -> None:
    """T-ADV-O — a matching hint is accepted and does not change the outcome."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    precomputed = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    )
    decision = _gate(
        target, historical_artifact(target), index, precomputed_resolution=precomputed.as_record()
    )
    assert decision.reason_code_id == "G2"
    assert decision.resolution_digest == precomputed.resolution_digest


def test_adv_p_precomputed_resolution_digest_differs() -> None:
    """T-ADV-P — a tampered hint is refused, not silently discarded."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    precomputed = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=EVALUATED_AT,
        ttl_seconds=PROFILE.max_resolution_age_seconds,
    ).as_record()
    precomputed["currentness_state"] = CURRENT
    decision = _gate(target, historical_artifact(target), index, precomputed_resolution=precomputed)
    assert decision.decision == DENY
    assert decision.reason_code_id == "G9"


def test_adv_q_index_identity_mismatch() -> None:
    """T-ADV-Q — the caller's expected index identity must hold."""
    target = AFFECTED_OUTPUT_REFS[0]
    decision = _gate(
        target,
        historical_artifact(target),
        governed_index(),
        expected_index_digest="0" * 64,
    )
    assert decision.decision == DENY
    assert decision.reason_code_id == "G10"


def test_adv_r_unknown_under_non_consequential_use() -> None:
    """T-ADV-R — the profile is fixed; non-consequential UNKNOWN still denies."""
    index = governed_index(with_control=False)
    decision = _gate(
        CONTROL_OUTPUT_REF,
        control_artifact(),
        index,
        consequential=False,
    )
    assert decision.decision == DENY
    assert decision.reason_code_id == "G4"
    assert decision.currentness_state == UNKNOWN


# ---------------------------------------------------------------------------
# T-DIG-01..09 — one per frozen digest class
# ---------------------------------------------------------------------------


def test_dig_01_historical_artifact_digest() -> None:
    """T-DIG-01 — §1 micro-vector and the §3.1 published body vector."""
    assert canonical_bytes({"b": 2, "a": "é"}) == b'{"a":"\xc3\xa9","b":2}'
    assert (
        canonical_digest({"b": 2, "a": "é"})
        == "06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de"
    )
    body = control_document()["historical_artifact"]["body"]
    assert len(canonical_bytes(body)) == 341
    assert (
        historical_artifact_digest(body)
        == "6f9fe1ccbabd6195d474f09a365a5ca4cc32f7ed8cf1f41e8acddd22e592eed0"
    )


def test_dig_02_basis_record_digest() -> None:
    """T-DIG-02 — the record exactly as stored; nothing excluded."""
    record = {"output_ref": "X", "record_class": SUPERSESSION_RECORD, "successor_id": "S"}
    assert basis_record_digest(record) == canonical_digest(record)
    assert basis_record_digest(record) != canonical_digest(
        {key: value for key, value in record.items() if key != "successor_id"}
    )


def test_dig_03_completeness_digest() -> None:
    """T-DIG-03 — the §3.3 published vector, with paired arrays unsorted."""
    attestation = control_document()["basis_completeness_attestation"]
    assert len(canonical_bytes(attestation)) == 617
    assert (
        completeness_digest(attestation)
        == "a9ffff71467a0880f77e3fec8b4740a0cdb74953e8fb9d743b1fdd7617ce66c6"
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
    assert completeness_digest(paired) != completeness_digest(reordered)


def test_dig_04_currentness_index_digest() -> None:
    """T-DIG-04 — insertion-order independence, bodies not embedded."""
    index = governed_index()
    reversed_entries = tuple(reversed(index.entries))
    variant = derive_index_variant(
        index, entries=reversed_entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    assert variant.index_digest == index.index_digest
    entries = [entry.reduced() for entry in index.entries]
    assert all(set(entry) == set(index.entries[0].reduced()) for entry in entries)
    assert all("record" not in entry for entry in entries)
    assert index.index_digest == currentness_index_digest(
        scope_ref=MISSION_SCOPE_REF,
        entries=entries,
        attestations=[att.as_record() for att in index.attestations],
        admitted_at=INDEX_ADMITTED_AT,
    )


def test_dig_05_resolution_digest() -> None:
    """T-DIG-05 — self-exclusion, and evaluation time inside the domain."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    first = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=EVALUATED_AT,
    )
    later = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=index,
        evaluated_at=LATER,
    )
    record = first.as_record()
    assert record["resolution_digest"] == resolution_digest(record)
    assert first.currentness_state == later.currentness_state
    assert first.resolution_digest != later.resolution_digest


def test_dig_06_use_gate_decision_digest() -> None:
    """T-DIG-06 — the decision digest binds resolution and observed artifact."""
    target = AFFECTED_OUTPUT_REFS[0]
    decision = _gate(target, historical_artifact(target), governed_index())
    record = decision.as_record()
    assert record["use_gate_decision_digest"] == use_gate_decision_digest(record)
    assert record["resolution_digest"] == decision.resolution_digest
    assert record["artifact_observed_digest"] == FROZEN_ARTIFACT_DIGESTS[target]


def test_dig_07_observation_digest() -> None:
    """T-DIG-07 — exactly the seven named fields, extras ignored."""
    observation = {
        "case_id": "T-ADV-A",
        "mutation_applied": "currentness record removed",
        "expected_reason_code": "R5",
        "observed_reason_code": "R5",
        "observed_state": UNKNOWN,
        "subject_refs": [AFFECTED_OUTPUT_REFS[0]],
        "evaluated_at": EVALUATED_AT,
    }
    expected = canonical_digest(observation)
    assert observation_digest(observation) == expected
    assert observation_digest({**observation, "observation_digest": "x", "note": "y"}) == expected
    with pytest.raises(CurrentnessIndexError, match="missing fields"):
        observation_digest({"case_id": "T-ADV-A"})


def test_dig_08_package_digest() -> None:
    """T-DIG-08 — member identities participate; member bodies do not."""
    package = {
        "record_class": "CDC_CURRENTNESS_SLICE_001_RAW_EXECUTION_PACKAGE",
        "members": [{"path": "a.json", "bytes": 10, "sha256": "ab" * 32}],
        "package_digest": "0" * 64,
    }
    expected = canonical_digest(
        {key: value for key, value in package.items() if key != "package_digest"}
    )
    assert package_digest(package) == expected


def test_dig_09_persisted_file_sha256() -> None:
    """T-DIG-09 — the §3.9 published vector, distinct from the canonical form."""
    payload = control_bytes()
    assert len(payload) == 2275
    assert persisted_file_sha256(payload) == SYNTHETIC_CONTROL_SHA256
    canonical = canonical_digest(json.loads(payload.decode("utf-8")))
    assert canonical != persisted_file_sha256(payload)


# ---------------------------------------------------------------------------
# INV-01 — structural invariant required by the implementation authorization.
# Reported separately; not one of the 44 semantic tests.
# ---------------------------------------------------------------------------


def test_inv_01_current_implies_attested_complete_basis() -> None:
    index = governed_index()
    observed_current = 0
    for output_ref, artifact in (
        *((ref, historical_artifact(ref)) for ref in AFFECTED_OUTPUT_REFS),
        (CONTROL_OUTPUT_REF, control_artifact()),
    ):
        resolution = resolve_currentness(
            output_ref=output_ref,
            historical_artifact=artifact,
            index=index,
            evaluated_at=EVALUATED_AT,
        )
        assert current_requires_attested_complete_basis(resolution, index)
        if resolution.currentness_state == CURRENT:
            observed_current += 1
            assert index.attestation_for(output_ref) is not None
    # Only the declared synthetic fixture can reach CURRENT in this population.
    assert observed_current == 1

    # And no real mission output can acquire an attestation at all.
    stripped = derive_index_variant(
        index, attestations=[], governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    for output_ref in AFFECTED_OUTPUT_REFS:
        resolution = resolve_currentness(
            output_ref=output_ref,
            historical_artifact=historical_artifact(output_ref),
            index=stripped,
            evaluated_at=EVALUATED_AT,
        )
        assert resolution.currentness_state != CURRENT


def test_index_refuses_substituted_evidence() -> None:
    """A governed index cannot be built over bytes other than the declared ones."""
    with pytest.raises(CurrentnessIndexError, match="byte identity mismatch"):
        build_currentness_index(
            scope_ref=MISSION_SCOPE_REF,
            stage_2_raw_result_bytes=stage_2_bytes(),
            expected_stage_2_sha256=STAGE_2_RAW_RESULT_SHA256,
            correction_result_bytes=correction_bytes()[:-10],
            expected_correction_sha256=CORRECTION_RESULT_SHA256,
            observed_at=INDEX_OBSERVED_AT,
            admitted_at=INDEX_ADMITTED_AT,
        )


def test_reason_code_sets_are_closed_and_counted() -> None:
    """The frozen sets are 11 and 10; nothing may be added after freezing."""
    assert len(RESOLVER_REASON_CODES) == 11
    assert len(USE_GATE_REASON_CODES) == 10
    assert set(RESOLVER_REASON_CODES) == {f"R{n}" for n in range(1, 12)}
    assert set(USE_GATE_REASON_CODES) == {f"G{n}" for n in range(1, 11)}


def test_attestation_schema_is_closed() -> None:
    """Unknown or missing attestation fields are refused."""
    source = dict(control_document()["basis_completeness_attestation"])
    with pytest.raises(CurrentnessIndexError, match="unknown fields"):
        parse_basis_completeness_attestation(
            {**source, "override": True}, admission_path=SYNTHETIC_CONTROL_PATH
        )
    del source["scope_ref"]
    with pytest.raises(CurrentnessIndexError, match="missing required fields"):
        parse_basis_completeness_attestation(source, admission_path=SYNTHETIC_CONTROL_PATH)


def test_ineligible_state_is_reachable_without_supersession() -> None:
    """R3 is not dead code: an eligibility record alone denies with G3."""
    index = governed_index()
    target = AFFECTED_OUTPUT_REFS[0]
    entries = [
        entry
        for entry in index.entries
        if entry.output_ref != target or entry.record_class != SUPERSESSION_RECORD
    ]
    variant = derive_index_variant(
        index, entries=entries, governed_controlling_output_refs=AFFECTED_OUTPUT_REFS
    )
    resolution = resolve_currentness(
        output_ref=target,
        historical_artifact=historical_artifact(target),
        index=variant,
        evaluated_at=EVALUATED_AT,
    )
    assert resolution.currentness_state == INELIGIBLE
    assert resolution.reason_code_id == "R3"
    decision = _gate(target, historical_artifact(target), variant)
    assert decision.reason_code_id == "G3"
