"""The M12 correction-successor boundary over frozen RUN-001 evidence.

Nothing here re-executes Stage 1 or Stage 2. The frozen RUN-001 result, attempt
record and route trace are read from the archived evidence in this repository and
must still hash to their frozen identities when each test finishes.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from oic.cdc_e2e_mission import (
    ADJUDICATION_PROTOCOL_SHA256,
    CORRECTION_ATTEMPT_STATE_CLAIMED,
    CORRECTION_ATTEMPT_STATE_CONSUMED,
    CORRECTION_ATTEMPT_STATE_NONE,
    CORRECTION_IMPACT_AFFECTED,
    CORRECTION_INELIGIBILITY_STATE,
    CORRECTION_SUCCESSOR_BINDING_FIELDS,
    CORRECTION_SUCCESSOR_DECLARATIONS,
    EXPERIMENT_ID,
    FROZEN_MISSION_INPUT_RELPATH,
    HUMAN_ACTION_PLAN_RELPATH,
    MISSION_ID,
    ORACLE_SHA256,
    OWNER_ADJUDICATION_ACCEPTANCE_COMMIT,
    OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
    SOURCE_RUN_ID,
    SOURCE_STAGE_2_RAW_RESULT_SHA256,
    SOURCE_STAGE_2_RESULT_DIGEST,
    STAGE_2_ADJUDICATION_COMMIT,
    STAGE_2_ADJUDICATION_SHA256,
    STAGE_2_EVIDENCE_COMMIT,
    STAGE_2_EVIDENCE_TREE,
    CorrectionAttemptStateError,
    CorrectionExecutionClearance,
    CorrectionSuccessorAuthorizationError,
    CorrectionSuccessorBlockedError,
    CorrectionSuccessorResult,
    FrozenActionPlan,
    FrozenMissionInput,
    FrozenStage2Evidence,
    PredecessorBindingError,
    PredecessorMutationDetectedError,
    RuntimeIdentity,
    Stage1ChainArtifact,
    Stage1ChainObservation,
    Stage1Observation,
    correction_successor_attempt_record_path,
    execute_authorized_correction_successor,
    read_correction_successor_attempt_state,
    sha256,
    verify_frozen_action_plan,
    verify_frozen_mission_input,
    verify_frozen_stage_2_evidence,
    verify_owner_correction_successor_authorization,
)

EVIDENCE = Path("veraxis/cdc-e2e-mission-001/executions/STAGE-2-RUN-001")
RAW_RESULT_NAME = "CDC-END-TO-END-MISSION-001-STAGE-2-RAW-RESULT-v0.1.json"
ROUTE_TRACE_NAME = "CDC-END-TO-END-MISSION-001-STAGE-2-ROUTE-TRACE-v0.1.json"
ATTEMPT_NAME = (
    ".cdc-e2e-stage-2-attempt-42b3c3d1285a0fddc36558875cc9df2e90b283ec79d96a56408b0fbc6f8c5f41.json"
)

PREDECESSOR_EBAWU = "EBAWU-P-001-C-TENDER-01"
PREDECESSOR_CHAIN = "P001xC-TENDER-01"
PREDECESSOR_CANDIDATE = "CAND-P001-C-TENDER-01"
SUCCESSOR_ID = "EBAWU-P-001-C-TENDER-01-S02"

UNUSED_IN_THIS_BOUNDARY = "not-read-by-the-correction-boundary"

RUNTIME_COMMIT = "0" * 40
RUNTIME_TREE = "1" * 40
ENVIRONMENT_SHA = "2" * 64


@pytest.fixture
def evidence_dir(repo_root: Path) -> Path:
    return repo_root / EVIDENCE


@pytest.fixture
def raw_result_bytes(evidence_dir: Path) -> bytes:
    return (evidence_dir / RAW_RESULT_NAME).read_bytes()


@pytest.fixture
def frozen_input(repo_root: Path) -> FrozenMissionInput:
    return verify_frozen_mission_input(repo_root / FROZEN_MISSION_INPUT_RELPATH)


@pytest.fixture
def action_plan(repo_root: Path) -> FrozenActionPlan:
    return verify_frozen_action_plan(repo_root / HUMAN_ACTION_PLAN_RELPATH)


def _stage_1(mission_id: str = MISSION_ID) -> Stage1Observation:
    """A Stage-1 observation carrying only the predecessor's artifact.

    The correction route reads the artifact's identity, so a focused observation
    is enough; nothing here re-executes Stage 1.
    """
    candidate = {"candidate_id": PREDECESSOR_CANDIDATE, "claim": "synthetic tender candidate"}
    artifact = Stage1ChainArtifact(
        chain_id=PREDECESSOR_CHAIN,
        procedure_id="P001",
        control_id="C-TENDER-01",
        ebawu_id=PREDECESSOR_EBAWU,
        input_digest=sha256({"input": PREDECESSOR_CHAIN}),
        evaluation={"evaluation_id": "EVAL-P001-C-TENDER-01"},
        evaluation_digest=sha256({"evaluation_id": "EVAL-P001-C-TENDER-01"}),
        warrant_class="ZTL_WARRANT",
        warrant_ref="WAR-P001-C-TENDER-01",
        warrant={"warrant_artifact_id": "WAR-P001-C-TENDER-01"},
        warrant_digest=sha256({"warrant_artifact_id": "WAR-P001-C-TENDER-01"}),
        candidate_id=PREDECESSOR_CANDIDATE,
        candidate=candidate,
        candidate_digest=sha256(candidate),
        outcome_state="completed",
    )
    return Stage1Observation(
        mission_id=mission_id,
        package_sha256=UNUSED_IN_THIS_BOUNDARY,
        provenance_token=UNUSED_IN_THIS_BOUNDARY,
        stage="STAGE_1",
        chains=(
            Stage1ChainObservation(
                chain_id=PREDECESSOR_CHAIN,
                outcome_state="completed",
                candidate_digest=artifact.candidate_digest,
                input_digest=artifact.input_digest,
                detail="rehydrated for the correction successor",
                artifact=artifact,
            ),
        ),
        accounting={},
        authorization="",
        owner_interpretation_sha256="",
        owner_execution_authorization=None,
        attempt_record=None,
        institutional_transition=UNUSED_IN_THIS_BOUNDARY,
        draft_eligibility=UNUSED_IN_THIS_BOUNDARY,
        official_handoff=UNUSED_IN_THIS_BOUNDARY,
        human_disposition=UNUSED_IN_THIS_BOUNDARY,
    )


def _predecessor(raw_result_bytes: bytes) -> dict[str, Any]:
    record = json.loads(raw_result_bytes)
    outcome = next(item for item in record["outcomes"] if item["chain_id"] == PREDECESSOR_CHAIN)
    candidate = {"candidate_id": PREDECESSOR_CANDIDATE, "claim": "synthetic tender candidate"}
    return {
        "ebawu_id": PREDECESSOR_EBAWU,
        "state": outcome["transition_event"]["new_state"],
        "candidate_id": PREDECESSOR_CANDIDATE,
        "candidate_digest": sha256(candidate),
    }


def _correction(successor_id: str = SUCCESSOR_ID) -> dict[str, Any]:
    return {
        "new_ebawu_or_successor_id": successor_id,
        "new_candidate_digest": sha256({"candidate_id": successor_id}),
        "correction_reason": "tender condition restated after the corrected control reference",
        "changed_fact_or_control_refs": ["CTRL-C-TENDER-01", "EVID-P001-C-TENDER-01"],
        "new_state": "CANDIDATE_FORMED",
        "correction_event_id": "CDC-E2E-CORRECTION-EVT-001",
        "correction_stimulus_id": "HA-CORRECTION-001",
        "affected_output_refs": ["CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"],
    }


def _authorization_document(
    canonical: Path,
    action_plan: FrozenActionPlan,
    frozen_input: FrozenMissionInput,
    *,
    successor_id: str = SUCCESSOR_ID,
    overrides: Mapping[str, Any] | None = None,
    binding_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A non-authoritative AUTH-003 test fixture.

    It is written under a temporary path, never at a canonical runtime location,
    and it authorizes nothing outside this test process.
    """
    document: dict[str, Any] = {
        **CORRECTION_SUCCESSOR_DECLARATIONS,
        "authorization_id": "TEST-FIXTURE-NOT-AN-ISSUED-AUTHORIZATION",
        "fixture": "NON_AUTHORITATIVE_TEST_FIXTURE",
        "canonical_authorization_path": str(canonical),
        "bindings": {
            "implementation_commit": RUNTIME_COMMIT,
            "implementation_tree": RUNTIME_TREE,
            "environment_manifest_sha256": ENVIRONMENT_SHA,
            "mission_package_sha256": frozen_input.package_sha256,
            "oracle_sha256": ORACLE_SHA256,
            "adjudication_protocol_sha256": ADJUDICATION_PROTOCOL_SHA256,
            "action_plan_sha256": action_plan.sha256_hex,
            "action_plan_provenance_token": action_plan.provenance_token,
            "correction_stimulus_digest": action_plan.correction.digest(),
            "source_run_id": SOURCE_RUN_ID,
            "source_stage_2_result_digest": SOURCE_STAGE_2_RESULT_DIGEST,
            "source_stage_2_raw_result_sha256": SOURCE_STAGE_2_RAW_RESULT_SHA256,
            "stage_2_evidence_commit": STAGE_2_EVIDENCE_COMMIT,
            "stage_2_evidence_tree": STAGE_2_EVIDENCE_TREE,
            "owner_acceptance_commit": OWNER_ADJUDICATION_ACCEPTANCE_COMMIT,
            "owner_acceptance_sha256": OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
            "adjudication_commit": STAGE_2_ADJUDICATION_COMMIT,
            "adjudication_sha256": STAGE_2_ADJUDICATION_SHA256,
            "predecessor_ebawu_ref": action_plan.correction.predecessor_ebawu_ref,
            "correction_target_id": action_plan.correction.target_id,
            "successor_id": successor_id,
        },
    }
    if binding_overrides:
        document["bindings"].update(binding_overrides)
    if overrides:
        document.update(overrides)
    return document


def _write_authorization(path: Path, document: Mapping[str, Any]) -> bytes:
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    return payload


def _clearance(payload: bytes) -> CorrectionExecutionClearance:
    return CorrectionExecutionClearance(
        owner_correction_authorization=f"sha256:{sha256_hex(payload)}",
        implementation_commit=RUNTIME_COMMIT,
        implementation_tree=RUNTIME_TREE,
        environment_manifest_sha256=ENVIRONMENT_SHA,
        mission_package_sha256="unused-by-the-correction-clearance",
        oracle_sha256=ORACLE_SHA256,
        adjudication_protocol_sha256=ADJUDICATION_PROTOCOL_SHA256,
        action_plan_sha256="unused-by-the-correction-clearance",
        owner_acceptance_sha256=OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
        source_stage_2_result_digest=SOURCE_STAGE_2_RESULT_DIGEST,
    )


def sha256_hex(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _runtime() -> RuntimeIdentity:
    return RuntimeIdentity(
        implementation_commit=RUNTIME_COMMIT,
        implementation_tree=RUNTIME_TREE,
        environment_manifest_sha256=ENVIRONMENT_SHA,
    )


def _run_metadata() -> dict[str, str]:
    return {
        "run_id": "CDC-E2E-CORRECTION-SUCCESSOR-RUN-001",
        "trace_id": "CDC-E2E-CORRECTION-SUCCESSOR-RUN-001-TRACE-001",
        "producer": "oic.cdc_e2e_mission.execute_authorized_correction_successor",
        "producer_version": RUNTIME_COMMIT,
        "occurred_at": "2026-08-13T18:00:00Z",
        "recorded_at": "2026-08-13T18:00:00Z",
    }


def _archive_observer() -> Mapping[str, str]:
    return {"commit": STAGE_2_EVIDENCE_COMMIT, "tree": STAGE_2_EVIDENCE_TREE}


def _execute(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    *,
    correction: Mapping[str, Any] | None = None,
    stage_1: Stage1Observation | None = None,
    document: Mapping[str, Any] | None = None,
    authorization_path: Path | None = None,
    raw_bytes: bytes | None = None,
    raw_result_path: Path | None = None,
    archive_observer: Callable[[], Mapping[str, str]] | None = _archive_observer,
) -> CorrectionSuccessorResult:
    canonical = authorization_path or (tmp_path / "AUTH-003.json")
    payload = _write_authorization(
        canonical,
        document or _authorization_document(canonical, action_plan, frozen_input),
    )
    return execute_authorized_correction_successor(
        stage_2_raw_result_bytes=raw_bytes if raw_bytes is not None else raw_result_bytes,
        stage_1=stage_1 or _stage_1(),
        frozen=frozen_input,
        action_plan=action_plan,
        correction=correction or _correction(),
        clearance=_clearance(payload),
        runtime=_runtime(),
        run_metadata=_run_metadata(),
        owner_correction_authorization_path=canonical,
        raw_result_path=raw_result_path or (evidence_dir / RAW_RESULT_NAME),
        attempt_record_path=evidence_dir / ATTEMPT_NAME,
        route_trace_path=evidence_dir / ROUTE_TRACE_NAME,
        archive_observer=archive_observer,
    )


# --------------------------------------------------------------------- success


def test_successor_supersedes_the_frozen_predecessor_both_ways(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    result = _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    record = result.as_record()
    predecessor = _predecessor(raw_result_bytes)

    assert record["successor"]["successor_id"] == SUCCESSOR_ID
    assert record["successor"]["supersedes"] == PREDECESSOR_EBAWU
    backlink = record["predecessor_supersession_record"]
    assert backlink["predecessor_id"] == PREDECESSOR_EBAWU
    assert backlink["superseded_by"] == SUCCESSOR_ID
    assert backlink["predecessor_mutated"] is False
    assert backlink["predecessor_rewritten"] is False
    assert record["predecessor"] == predecessor
    assert record["predecessor_digest"] == sha256(predecessor)


def test_correction_reason_and_changed_refs_are_carried_exactly(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    correction = _correction()
    result = _execute(
        tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan, correction=correction
    )
    assert result.correction_reason == correction["correction_reason"]
    assert list(result.changed_fact_or_control_refs) == correction["changed_fact_or_control_refs"]


def test_predecessor_digest_is_unchanged_across_the_correction(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    result = _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    immutability = result.predecessor_immutability
    assert (
        immutability["level_1_in_memory_digest_before"]
        == (immutability["level_1_in_memory_digest_after"])
    )
    assert immutability["level_1_preserved"] is True
    assert immutability["level_2_preserved"] is True
    assert immutability["level_3_preserved"] is True
    assert immutability["predecessor_byte_identity_preserved"] is True


def test_frozen_run_001_artifacts_are_byte_identical_afterwards(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    before = {
        name: (evidence_dir / name).read_bytes()
        for name in (RAW_RESULT_NAME, ROUTE_TRACE_NAME, ATTEMPT_NAME)
    }
    _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    after = {
        name: (evidence_dir / name).read_bytes()
        for name in (RAW_RESULT_NAME, ROUTE_TRACE_NAME, ATTEMPT_NAME)
    }
    assert before == after


def test_stage_2_attempt_namespace_is_never_created(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    assert not list(tmp_path.glob(".cdc-e2e-stage-2-*"))
    assert len(list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))) == 1


def test_downstream_eligibility_is_recomputed_over_the_frozen_drafts(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    result = _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    frozen_drafts = json.loads(raw_result_bytes)["drafts"]
    determinations = list(result.affected_output_eligibility)
    assert len(determinations) == len(frozen_drafts)
    for determination, draft in zip(determinations, frozen_drafts, strict=True):
        assert determination["draft_id"] == draft["draft_id"]
        assert determination["correction_impact"] == CORRECTION_IMPACT_AFFECTED
        assert determination["post_correction_reliance_state"] == CORRECTION_INELIGIBILITY_STATE
        # The pre-existing provenance state is preserved beside the new one.
        assert determination["pre_correction_frozen_eligibility"] == draft["eligibility_state"]
        assert (
            determination["pre_correction_frozen_eligibility"]
            != (determination["post_correction_reliance_state"])
        )
        assert determination["frozen_draft_modified"] is False
        assert determination["basis"]["successor_id"] == SUCCESSOR_ID


def test_stale_predecessor_proposal_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    result = _execute(tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan)
    observation = result.stale_proposal_refusal_observation
    assert observation["candidate_id"] == PREDECESSOR_CANDIDATE
    assert observation["stale_candidate_ids"] == [PREDECESSOR_CANDIDATE]
    assert observation["decision"] == "DENY"
    assert observation["reason_code"] == "CANDIDATE_SUPERSEDED_OR_CORRECTED"
    assert observation["gate_invoked"] is False
    assert observation["transition_event_emitted"] is False


def test_result_carries_its_own_recomputable_digest(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    record = _execute(
        tmp_path, evidence_dir, raw_result_bytes, frozen_input, action_plan
    ).as_record()
    embedded = record["correction_successor_result_digest"]
    body = {k: v for k, v in record.items() if k != "correction_successor_result_digest"}
    assert embedded == sha256(body)
    assert record["experiment_id"] == EXPERIMENT_ID
    assert record["runtime_mission_id"] == MISSION_ID
    assert record["experiment_id"] != record["runtime_mission_id"]
    assert record["stage_2_reexecuted"] is False
    assert record["run_001_modified"] is False
    assert record["m11_repaired"] is False
    assert record["official_handoff"] == "PROHIBITED"


def test_attempt_is_claimed_then_consumed(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    payload = _write_authorization(
        canonical, _authorization_document(canonical, action_plan, frozen_input)
    )
    authorization = verify_owner_correction_successor_authorization(
        canonical,
        clearance=_clearance(payload),
        runtime=_runtime(),
        frozen=frozen_input,
        action_plan=action_plan,
        evidence=_evidence(raw_result_bytes),
    )
    assert read_correction_successor_attempt_state(authorization) == CORRECTION_ATTEMPT_STATE_NONE
    result = _execute(
        tmp_path,
        evidence_dir,
        raw_result_bytes,
        frozen_input,
        action_plan,
        authorization_path=canonical,
    )
    assert (
        read_correction_successor_attempt_state(authorization) == CORRECTION_ATTEMPT_STATE_CONSUMED
    )
    attempt = result.attempt_record
    assert attempt is not None
    assert attempt["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def _evidence(payload: bytes) -> FrozenStage2Evidence:
    return verify_frozen_stage_2_evidence(payload)


# -------------------------------------------------------------------- refusals


def test_second_construction_is_refused_without_automatic_retry(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    _execute(
        tmp_path,
        evidence_dir,
        raw_result_bytes,
        frozen_input,
        action_plan,
        authorization_path=canonical,
    )
    with pytest.raises(CorrectionAttemptStateError, match="permanently non-reusable"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            authorization_path=canonical,
        )


def test_claimed_but_unconsumed_attempt_requires_a_separate_owner_decision(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    payload = _write_authorization(
        canonical, _authorization_document(canonical, action_plan, frozen_input)
    )
    authorization = verify_owner_correction_successor_authorization(
        canonical,
        clearance=_clearance(payload),
        runtime=_runtime(),
        frozen=frozen_input,
        action_plan=action_plan,
        evidence=_evidence(raw_result_bytes),
    )
    correction_successor_attempt_record_path(authorization).write_bytes(
        json.dumps({"attempt_state": CORRECTION_ATTEMPT_STATE_CLAIMED}).encode()
    )
    with pytest.raises(CorrectionAttemptStateError, match="separate owner decision"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            authorization_path=canonical,
        )


def test_relocated_authorization_copy_is_not_a_second_issuance(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(canonical, action_plan, frozen_input)
    relocated = tmp_path / "relocated" / "AUTH-003.json"
    relocated.parent.mkdir()
    with pytest.raises(CorrectionSuccessorAuthorizationError, match="not a second issuance"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=relocated,
        )


def test_instrument_asserting_its_own_issuance_state_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical, action_plan, frozen_input, overrides={"issuance_observed": True}
    )
    with pytest.raises(CorrectionSuccessorAuthorizationError, match="asserts its own issuance"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


@pytest.mark.parametrize(
    "declaration",
    [
        "stage_2_reexecution_authorized",
        "transition_evaluation_authorized",
        "transition_event_emission_authorized",
        "draft_rendering_authorized",
        "run_001_modification_authorized",
        "m11_repair_authorized",
        "official_handoff_authorized",
    ],
)
def test_an_instrument_claiming_a_forbidden_scope_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    declaration: str,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical, action_plan, frozen_input, overrides={declaration: True}
    )
    with pytest.raises(
        CorrectionSuccessorAuthorizationError, match="correction-successor semantics"
    ):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


@pytest.mark.parametrize("field", sorted(CORRECTION_SUCCESSOR_BINDING_FIELDS))
def test_every_binding_field_is_actually_compared(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    field: str,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical, action_plan, frozen_input, binding_overrides={field: "WRONG-VALUE"}
    )
    with pytest.raises((CorrectionSuccessorAuthorizationError, CorrectionSuccessorBlockedError)):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


def test_successor_id_must_match_the_authorized_successor(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    with pytest.raises(CorrectionSuccessorBlockedError, match="the authorization binds"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            correction=_correction("EBAWU-SOMETHING-ELSE"),
        )


def test_tampered_frozen_result_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    tampered = json.loads(raw_result_bytes)
    tampered["accounting"]["transitioned"] = 8
    payload = (json.dumps(tampered, indent=2, sort_keys=True) + "\n").encode()
    with pytest.raises(CorrectionSuccessorBlockedError, match="hashes to"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            raw_bytes=payload,
        )


def test_supplied_predecessor_digest_must_match_the_derived_one(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    correction = {**_correction(), "predecessor_digest": "0" * 64}
    with pytest.raises(PredecessorBindingError, match="correction binds predecessor"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            correction=correction,
        )


def test_experiment_identity_may_not_stand_in_for_the_runtime_mission(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    with pytest.raises(CorrectionSuccessorBlockedError, match="runtime mission"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            stage_1=_stage_1(mission_id=EXPERIMENT_ID),
        )


def test_a_mutated_frozen_file_is_detected_after_construction(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    decoy = tmp_path / "mutated-raw-result.json"
    decoy.write_bytes(raw_result_bytes + b"\n")
    with pytest.raises(PredecessorMutationDetectedError, match="PREDECESSOR_MUTATION_DETECTED"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            raw_result_path=decoy,
        )


def test_a_moved_evidence_archive_is_detected_after_construction(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    def moved() -> Mapping[str, str]:
        return {"commit": "f" * 40, "tree": STAGE_2_EVIDENCE_TREE}

    with pytest.raises(PredecessorMutationDetectedError, match="origin_evidence_commit"):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            archive_observer=moved,
        )


def test_mutation_detection_leaves_the_attempt_claimed_not_consumed(
    tmp_path: Path,
    evidence_dir: Path,
    raw_result_bytes: bytes,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    canonical = tmp_path / "AUTH-003.json"

    def moved() -> Mapping[str, str]:
        return {"commit": "f" * 40, "tree": STAGE_2_EVIDENCE_TREE}

    with pytest.raises(PredecessorMutationDetectedError):
        _execute(
            tmp_path,
            evidence_dir,
            raw_result_bytes,
            frozen_input,
            action_plan,
            authorization_path=canonical,
            archive_observer=moved,
        )
    claimed = list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))
    assert len(claimed) == 1
    document = json.loads(claimed[0].read_bytes())
    assert document["attempt_state"] == CORRECTION_ATTEMPT_STATE_CLAIMED
