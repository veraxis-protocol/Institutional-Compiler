"""The M12 correction-successor boundary over frozen RUN-001 evidence.

Nothing here re-executes Stage 1 or Stage 2. The frozen RUN-001 result, attempt
record and route trace are read from the archived evidence in this repository, at
the location the authorization binds, and must still hash to their frozen
identities when each test finishes.

The archive observation is patched at its internal seam rather than injected
through the public route, which deliberately exposes no such parameter.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

import pytest

from oic import cdc_e2e_mission as mission
from oic.cdc_e2e_mission import (
    ADJUDICATION_PROTOCOL_SHA256,
    ARCHIVE_OBSERVATION_SOURCE,
    CORRECTION_ATTEMPT_STATE_CLAIMED,
    CORRECTION_ATTEMPT_STATE_CONSUMED,
    CORRECTION_ATTEMPT_STATE_NONE,
    CORRECTION_IMPACT_AFFECTED,
    CORRECTION_INELIGIBILITY_STATE,
    CORRECTION_SUCCESSOR_BINDING_FIELDS,
    CORRECTION_SUCCESSOR_DECLARATIONS,
    EVIDENCE_BRANCH,
    EVIDENCE_REPOSITORY,
    EXPERIMENT_ID,
    FROZEN_MISSION_INPUT_RELPATH,
    HUMAN_ACTION_PLAN_RELPATH,
    MISSION_ID,
    ORACLE_SHA256,
    OWNER_ADJUDICATION_ACCEPTANCE_COMMIT,
    OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
    RESULT_STATUS_FAILED_POST_CONSTRUCTION,
    SOURCE_RUN_ID,
    SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME,
    SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256,
    SOURCE_STAGE_2_RAW_RESULT_FILENAME,
    SOURCE_STAGE_2_RAW_RESULT_SHA256,
    SOURCE_STAGE_2_RESULT_DIGEST,
    SOURCE_STAGE_2_ROUTE_TRACE_FILENAME,
    SOURCE_STAGE_2_ROUTE_TRACE_SHA256,
    STAGE_2_ADJUDICATION_COMMIT,
    STAGE_2_ADJUDICATION_SHA256,
    STAGE_2_EVIDENCE_COMMIT,
    STAGE_2_EVIDENCE_TREE,
    CorrectionAttemptStateError,
    CorrectionEvidenceInfrastructureError,
    CorrectionExecutionClearance,
    CorrectionSuccessorAuthorizationError,
    CorrectionSuccessorBlockedError,
    CorrectionSuccessorResult,
    FrozenActionPlan,
    FrozenMissionInput,
    OwnerCorrectionSuccessorAuthorization,
    PostConstructionIntegrityError,
    PredecessorBindingError,
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
    verify_owner_correction_successor_authorization,
)

EVIDENCE = Path("veraxis/cdc-e2e-mission-001/executions/STAGE-2-RUN-001")

PREDECESSOR_EBAWU = "EBAWU-P-001-C-TENDER-01"
PREDECESSOR_CHAIN = "P001xC-TENDER-01"
PREDECESSOR_CANDIDATE = "CAND-P001-C-TENDER-01"
SUCCESSOR_ID = "EBAWU-P-001-C-TENDER-01-S02"

UNUSED_IN_THIS_BOUNDARY = "not-read-by-the-correction-boundary"

RUNTIME_COMMIT = "0" * 40
RUNTIME_TREE = "1" * 40
ENVIRONMENT_SHA = "2" * 64

EVIDENCE_FILENAMES = (
    SOURCE_STAGE_2_RAW_RESULT_FILENAME,
    SOURCE_STAGE_2_ROUTE_TRACE_FILENAME,
    SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME,
)


@pytest.fixture
def evidence_dir(repo_root: Path) -> Path:
    return repo_root / EVIDENCE


@pytest.fixture
def frozen_input(repo_root: Path) -> FrozenMissionInput:
    return verify_frozen_mission_input(repo_root / FROZEN_MISSION_INPUT_RELPATH)


@pytest.fixture
def action_plan(repo_root: Path) -> FrozenActionPlan:
    return verify_frozen_action_plan(repo_root / HUMAN_ACTION_PLAN_RELPATH)


def _matching_archive(repo_root: Path, branch: str) -> dict[str, str]:
    del repo_root
    return {
        "repository_remote_url": f"https://github.com/{EVIDENCE_REPOSITORY}.git",
        "repository_normalized": EVIDENCE_REPOSITORY,
        "branch": branch,
        "observation_source": ARCHIVE_OBSERVATION_SOURCE,
        "remote_commit": STAGE_2_EVIDENCE_COMMIT,
        "remote_commit_tree": STAGE_2_EVIDENCE_TREE,
        "remote_commit_tree_source": "LOCAL_OBJECT_FOR_ORIGIN_SUPPLIED_SHA",
    }


@pytest.fixture
def archive_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the internal archive observation so tests do not depend on git state."""
    monkeypatch.setattr(mission, "_observe_git_archive_identity", _matching_archive)


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


def _predecessor(evidence_dir: Path) -> dict[str, Any]:
    record = json.loads((evidence_dir / SOURCE_STAGE_2_RAW_RESULT_FILENAME).read_bytes())
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
    evidence_root: Path,
    *,
    successor_id: str = SUCCESSOR_ID,
    overrides: Mapping[str, Any] | None = None,
    binding_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """A non-authoritative AUTH-003 test fixture.

    Written under a temporary path, never at a canonical runtime location, and it
    authorizes nothing outside this test process.
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
            "source_evidence_root": str(evidence_root),
            "source_stage_1_observation_digest": _stage_1().digest(),
            "source_stage_2_result_digest": SOURCE_STAGE_2_RESULT_DIGEST,
            "source_stage_2_raw_result_sha256": SOURCE_STAGE_2_RAW_RESULT_SHA256,
            "source_stage_2_attempt_record_sha256": SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256,
            "source_stage_2_route_trace_sha256": SOURCE_STAGE_2_ROUTE_TRACE_SHA256,
            "evidence_repository": EVIDENCE_REPOSITORY,
            "evidence_branch": EVIDENCE_BRANCH,
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
        owner_correction_authorization=f"sha256:{hashlib.sha256(payload).hexdigest()}",
        implementation_commit=RUNTIME_COMMIT,
        implementation_tree=RUNTIME_TREE,
        environment_manifest_sha256=ENVIRONMENT_SHA,
        mission_package_sha256=UNUSED_IN_THIS_BOUNDARY,
        oracle_sha256=ORACLE_SHA256,
        adjudication_protocol_sha256=ADJUDICATION_PROTOCOL_SHA256,
        action_plan_sha256=UNUSED_IN_THIS_BOUNDARY,
        owner_acceptance_sha256=OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
        source_stage_2_result_digest=SOURCE_STAGE_2_RESULT_DIGEST,
    )


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


def _execute(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    *,
    correction: Mapping[str, Any] | None = None,
    stage_1: Stage1Observation | None = None,
    document: Mapping[str, Any] | None = None,
    authorization_path: Path | None = None,
) -> CorrectionSuccessorResult:
    canonical = authorization_path or (tmp_path / "AUTH-003.json")
    payload = _write_authorization(
        canonical,
        document or _authorization_document(canonical, action_plan, frozen_input, evidence_dir),
    )
    return execute_authorized_correction_successor(
        stage_1=stage_1 or _stage_1(),
        frozen=frozen_input,
        action_plan=action_plan,
        correction=correction or _correction(),
        clearance=_clearance(payload),
        runtime=_runtime(),
        run_metadata=_run_metadata(),
        owner_correction_authorization_path=canonical,
    )


def _authorization(
    canonical: Path, action_plan: FrozenActionPlan, frozen_input: FrozenMissionInput, root: Path
) -> OwnerCorrectionSuccessorAuthorization:
    payload = _write_authorization(
        canonical, _authorization_document(canonical, action_plan, frozen_input, root)
    )
    return verify_owner_correction_successor_authorization(
        canonical,
        clearance=_clearance(payload),
        runtime=_runtime(),
        frozen=frozen_input,
        action_plan=action_plan,
    )


# ----------------------------------------------------- evidence-source authority


def test_public_route_exposes_no_archive_observer_parameter() -> None:
    assert (
        "archive_observer"
        not in inspect.signature(execute_authorized_correction_successor).parameters
    )


def test_public_route_exposes_no_caller_selectable_evidence_paths() -> None:
    parameters = set(inspect.signature(execute_authorized_correction_successor).parameters)
    forbidden = {
        "raw_result_path",
        "attempt_record_path",
        "route_trace_path",
        "stage_2_raw_result_bytes",
        "archive_observer",
    }
    assert parameters & forbidden == set()
    # The instrument presented for verification is the only path the caller supplies.
    assert "owner_correction_authorization_path" in parameters


def test_evidence_is_read_from_the_bound_location_only(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    empty_root = tmp_path / "elsewhere"
    empty_root.mkdir()
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(canonical, action_plan, frozen_input, empty_root)
    with pytest.raises(CorrectionSuccessorBlockedError, match="not readable"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


def test_relocated_but_tampered_evidence_cannot_substitute(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    relocated = tmp_path / "relocated-evidence"
    relocated.mkdir()
    for name in EVIDENCE_FILENAMES:
        shutil.copyfile(evidence_dir / name, relocated / name)
    (relocated / SOURCE_STAGE_2_RAW_RESULT_FILENAME).write_bytes(b"{}\n")
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(canonical, action_plan, frozen_input, relocated)
    with pytest.raises(CorrectionSuccessorBlockedError, match="hashes to"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


def test_archive_verifier_observes_only_the_bound_identity(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def observed(repo_root: Path, branch: str) -> dict[str, str]:
        seen["repo_root"] = repo_root
        seen["branch"] = branch
        return _matching_archive(repo_root, branch)

    monkeypatch.setattr(mission, "_observe_git_archive_identity", observed)
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert seen["branch"] == EVIDENCE_BRANCH
    identity = result.archive_identity
    assert identity["expected_commit"] == STAGE_2_EVIDENCE_COMMIT
    assert identity["expected_tree"] == STAGE_2_EVIDENCE_TREE
    assert identity["expected_repository"] == EVIDENCE_REPOSITORY
    assert identity["expected_branch"] == EVIDENCE_BRANCH
    assert identity["observation_source"] == ARCHIVE_OBSERVATION_SOURCE
    assert identity["remote_commit"] == STAGE_2_EVIDENCE_COMMIT
    assert identity["remote_commit_tree"] == STAGE_2_EVIDENCE_TREE
    assert identity["archive_identity_verified"] is True
    assert identity["local_branch_consulted"] is False
    assert identity["caller_injectable"] is False


def test_unobservable_archive_is_infrastructure_failure_not_a_match(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(repo_root: Path, branch: str) -> dict[str, str]:
        del repo_root, branch
        raise CorrectionEvidenceInfrastructureError("git is unavailable")

    monkeypatch.setattr(mission, "_observe_git_archive_identity", unavailable)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "CorrectionEvidenceInfrastructureError" in caught.value.observation["failure"]


def test_stage_1_observation_must_match_the_bound_digest(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical,
        action_plan,
        frozen_input,
        evidence_dir,
        binding_overrides={"source_stage_1_observation_digest": "0" * 64},
    )
    with pytest.raises(CorrectionSuccessorBlockedError, match="the authorization binds"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


# --------------------------------------------------------------------- success


def test_successor_supersedes_the_frozen_predecessor_both_ways(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    record = result.as_record()
    predecessor = _predecessor(evidence_dir)

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
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    correction = _correction()
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan, correction=correction)
    assert result.correction_reason == correction["correction_reason"]
    assert list(result.changed_fact_or_control_refs) == correction["changed_fact_or_control_refs"]


def test_predecessor_digest_is_unchanged_across_the_correction(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    immutability = result.predecessor_immutability
    assert (
        immutability["level_1_in_memory_digest_before"]
        == (immutability["level_1_in_memory_digest_after"])
    )
    assert immutability["level_1_preserved"] is True
    assert immutability["level_2_preserved"] is True
    assert immutability["predecessor_byte_identity_preserved"] is True


def test_frozen_run_001_artifacts_are_byte_identical_afterwards(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    before = {name: (evidence_dir / name).read_bytes() for name in EVIDENCE_FILENAMES}
    _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    after = {name: (evidence_dir / name).read_bytes() for name in EVIDENCE_FILENAMES}
    assert before == after


def test_stage_2_attempt_namespace_is_never_created(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert not list(tmp_path.glob(".cdc-e2e-stage-2-*"))
    assert len(list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))) == 1


def test_downstream_eligibility_is_recomputed_over_the_frozen_drafts(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    frozen_drafts = json.loads((evidence_dir / SOURCE_STAGE_2_RAW_RESULT_FILENAME).read_bytes())[
        "drafts"
    ]
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
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
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
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    record = _execute(tmp_path, evidence_dir, frozen_input, action_plan).as_record()
    embedded = record["correction_successor_result_digest"]
    body = {k: v for k, v in record.items() if k != "correction_successor_result_digest"}
    assert embedded == sha256(body)
    assert record["experiment_id"] == EXPERIMENT_ID
    assert record["runtime_mission_id"] == MISSION_ID
    assert record["experiment_id"] != record["runtime_mission_id"]
    assert record["successor_construction_invoked"] is True
    assert record["successor_constructed"] is True
    assert record["stage_2_reexecuted"] is False
    assert record["run_001_modified"] is False
    assert record["m11_repaired"] is False
    assert record["official_handoff"] == "PROHIBITED"
    assert record["evidence_locations"]["caller_selectable"] is False


# --------------------------------------------------------- attempt state machine


def test_precondition_failure_before_claim_leaves_no_attempt_record(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    with pytest.raises(CorrectionSuccessorBlockedError):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            correction=_correction("EBAWU-SOMETHING-ELSE"),
        )
    assert not list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))
    authorization = _authorization(tmp_path / "probe.json", action_plan, frozen_input, evidence_dir)
    assert read_correction_successor_attempt_state(authorization) == CORRECTION_ATTEMPT_STATE_NONE


def test_failure_after_claim_before_construction_leaves_the_attempt_claimed(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_construction(*args: object, **kwargs: object) -> dict[str, Any]:
        raise RuntimeError("construction failed before a successor existed")

    monkeypatch.setattr(mission, "bind_correction", failing_construction)
    with pytest.raises(RuntimeError, match="before a successor existed"):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    claimed = list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))
    assert len(claimed) == 1
    document = json.loads(claimed[0].read_bytes())
    assert document["attempt_state"] == CORRECTION_ATTEMPT_STATE_CLAIMED
    assert document["successor_constructed"] is False


@pytest.mark.parametrize(
    ("seam", "failure"),
    [
        ("recompute_affected_output_eligibility", RuntimeError("eligibility failed")),
        ("observe_stale_predecessor_proposal_refusal", RuntimeError("stale observation failed")),
        ("build_predecessor_supersession_record", RuntimeError("supersession failed")),
        ("observe_predecessor_immutability", OSError("persistence failed")),
    ],
)
def test_post_construction_failures_leave_the_attempt_consumed(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
    monkeypatch: pytest.MonkeyPatch,
    seam: str,
    failure: Exception,
) -> None:
    def failing(*args: object, **kwargs: object) -> NoReturn:
        raise failure

    monkeypatch.setattr(mission, seam, failing)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)

    observation = caught.value.observation
    assert observation["result_status"] == RESULT_STATUS_FAILED_POST_CONSTRUCTION
    assert observation["successor_construction_invoked"] is True
    assert observation["successor_constructed"] is True
    assert observation["successor_id"] == SUCCESSOR_ID
    assert observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED
    assert observation["automatic_retry"] is False
    assert observation["predecessor_before_digest"] == observation["predecessor_after_digest"]

    consumed = list(tmp_path.glob(".cdc-e2e-correction-successor-attempt-*"))
    assert len(consumed) == 1
    document = json.loads(consumed[0].read_bytes())
    assert document["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED
    assert document["successor_constructed"] is True


def test_local_integrity_failure_after_construction_consumes_the_attempt(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mismatched(**kwargs: object) -> dict[str, Any]:
        return {
            "level_1_preserved": True,
            "level_2_preserved": False,
            "mismatched": ["raw_result_sha256"],
            "predecessor_byte_identity_preserved": False,
        }

    monkeypatch.setattr(mission, "observe_predecessor_immutability", mismatched)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "PREDECESSOR_MUTATION_DETECTED" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def test_archive_verification_failure_after_construction_consumes_the_attempt(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def moved(repo_root: Path, branch: str) -> dict[str, str]:
        return {**_matching_archive(repo_root, branch), "remote_commit": "f" * 40}

    monkeypatch.setattr(mission, "_observe_git_archive_identity", moved)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "archive identity" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def test_a_consumed_attempt_never_retries_after_a_post_construction_failure(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    monkeypatch.setattr(mission, "_observe_git_archive_identity", _matching_archive)
    working = mission.recompute_affected_output_eligibility

    def failing(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("eligibility failed")

    monkeypatch.setattr(mission, "recompute_affected_output_eligibility", failing)
    with pytest.raises(PostConstructionIntegrityError):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical)

    # Even with the transient failure gone, the exercised authority stays spent.
    monkeypatch.setattr(mission, "recompute_affected_output_eligibility", working)
    with pytest.raises(CorrectionAttemptStateError, match="permanently non-reusable"):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical)


def test_attempt_is_claimed_then_consumed(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    authorization = _authorization(canonical, action_plan, frozen_input, evidence_dir)
    assert read_correction_successor_attempt_state(authorization) == CORRECTION_ATTEMPT_STATE_NONE
    result = _execute(
        tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical
    )
    assert (
        read_correction_successor_attempt_state(authorization) == CORRECTION_ATTEMPT_STATE_CONSUMED
    )
    attempt = result.attempt_record
    assert attempt is not None
    assert attempt["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


# -------------------------------------------------------------------- refusals


def test_second_construction_is_refused_without_automatic_retry(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    _execute(tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical)
    with pytest.raises(CorrectionAttemptStateError, match="permanently non-reusable"):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical)


def test_claimed_but_unconsumed_attempt_requires_a_separate_owner_decision(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    authorization = _authorization(canonical, action_plan, frozen_input, evidence_dir)
    correction_successor_attempt_record_path(authorization).write_bytes(
        json.dumps({"attempt_state": CORRECTION_ATTEMPT_STATE_CLAIMED}).encode()
    )
    with pytest.raises(CorrectionAttemptStateError, match="separate owner decision"):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan, authorization_path=canonical)


def test_relocated_authorization_copy_is_not_a_second_issuance(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(canonical, action_plan, frozen_input, evidence_dir)
    relocated = tmp_path / "relocated" / "AUTH-003.json"
    relocated.parent.mkdir()
    with pytest.raises(CorrectionSuccessorAuthorizationError, match="not a second issuance"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=relocated,
        )


def test_instrument_asserting_its_own_issuance_state_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical, action_plan, frozen_input, evidence_dir, overrides={"issuance_observed": True}
    )
    with pytest.raises(CorrectionSuccessorAuthorizationError, match="asserts its own issuance"):
        _execute(
            tmp_path,
            evidence_dir,
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
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
    declaration: str,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical, action_plan, frozen_input, evidence_dir, overrides={declaration: True}
    )
    with pytest.raises(
        CorrectionSuccessorAuthorizationError, match="correction-successor semantics"
    ):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


@pytest.mark.parametrize("field", sorted(CORRECTION_SUCCESSOR_BINDING_FIELDS))
def test_every_binding_field_is_actually_compared(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
    field: str,
) -> None:
    canonical = tmp_path / "AUTH-003.json"
    document = _authorization_document(
        canonical,
        action_plan,
        frozen_input,
        evidence_dir,
        binding_overrides={field: "WRONG-VALUE"},
    )
    with pytest.raises((CorrectionSuccessorAuthorizationError, CorrectionSuccessorBlockedError)):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            document=document,
            authorization_path=canonical,
        )


def test_successor_id_must_match_the_authorized_successor(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    with pytest.raises(CorrectionSuccessorBlockedError, match="the authorization binds"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            correction=_correction("EBAWU-SOMETHING-ELSE"),
        )


def test_supplied_predecessor_digest_must_match_the_derived_one(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    correction = {**_correction(), "predecessor_digest": "0" * 64}
    with pytest.raises(PredecessorBindingError, match="correction binds predecessor"):
        _execute(tmp_path, evidence_dir, frozen_input, action_plan, correction=correction)


def test_experiment_identity_may_not_stand_in_for_the_runtime_mission(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    archive_seam: None,
) -> None:
    with pytest.raises(CorrectionSuccessorBlockedError, match="runtime mission"):
        _execute(
            tmp_path,
            evidence_dir,
            frozen_input,
            action_plan,
            stage_1=_stage_1(mission_id=EXPERIMENT_ID),
        )


# ------------------------------------------------- origin archive observation


class _FakeGit:
    """Drives the real observer through its single git seam.

    The observer's own parsing, ambiguity handling and tree derivation run for
    real; only the git process is replaced.
    """

    def __init__(
        self,
        *,
        ls_remote: str | Exception,
        local_branch_commit: str = "d" * 40,
        objects: tuple[str, ...] = (STAGE_2_EVIDENCE_COMMIT,),
        trees: Mapping[str, str] | None = None,
    ) -> None:
        self.ls_remote = ls_remote
        self.local_branch_commit = local_branch_commit
        self.objects = set(objects)
        self.trees = dict(
            trees if trees is not None else {STAGE_2_EVIDENCE_COMMIT: STAGE_2_EVIDENCE_TREE}
        )
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, repo_root: Path, *arguments: str) -> str:
        del repo_root
        self.calls.append(arguments)
        if arguments[0] == "ls-remote":
            if isinstance(self.ls_remote, Exception):
                raise self.ls_remote
            return self.ls_remote
        if arguments[0] == "remote":
            return f"https://github.com/{EVIDENCE_REPOSITORY}.git"
        if arguments[0] == "cat-file":
            sha = arguments[2].removesuffix("^{commit}")
            if sha not in self.objects:
                raise CorrectionEvidenceInfrastructureError(f"missing object {sha}")
            return ""
        if arguments[0] == "fetch":
            self.objects.add(arguments[-1])
            return ""
        if arguments[0] == "rev-parse":
            target = arguments[1]
            if target.endswith("^{tree}"):
                sha = target.removesuffix("^{tree}")
                if sha not in self.trees:
                    raise CorrectionEvidenceInfrastructureError(f"no tree for {sha}")
                return self.trees[sha]
            # A local branch ref. Reaching this at all would be the defect.
            return self.local_branch_commit
        raise AssertionError(f"unexpected git call: {arguments}")


def _ref_line(commit: str, branch: str = EVIDENCE_BRANCH) -> str:
    return f"{commit}\trefs/heads/{branch}\n"


def test_archive_identity_is_read_from_origin_not_the_local_branch(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The local branch disagrees with origin; origin must control.
    git = _FakeGit(ls_remote=_ref_line(STAGE_2_EVIDENCE_COMMIT), local_branch_commit="a" * 40)
    monkeypatch.setattr(mission, "_git", git)
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    identity = result.archive_identity

    assert identity["archive_identity_verified"] is True
    assert identity["observation_source"] == ARCHIVE_OBSERVATION_SOURCE
    assert identity["remote_commit"] == STAGE_2_EVIDENCE_COMMIT
    assert identity["remote_commit_tree"] == STAGE_2_EVIDENCE_TREE
    assert identity["remote_commit"] != git.local_branch_commit

    assert any(call[0] == "ls-remote" for call in git.calls)
    # No remote_* value may come from resolving a local branch ref.
    assert not any(call[0] == "rev-parse" and not call[1].endswith("^{tree}") for call in git.calls)
    assert not any(EVIDENCE_BRANCH in call[1:] for call in git.calls if call[0] == "rev-parse")


def test_local_branch_correct_but_origin_wrong_fails_after_construction(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moved = "b" * 40
    git = _FakeGit(
        ls_remote=_ref_line(moved),
        local_branch_commit=STAGE_2_EVIDENCE_COMMIT,
        objects=(moved,),
        trees={moved: STAGE_2_EVIDENCE_TREE},
    )
    monkeypatch.setattr(mission, "_git", git)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    observation = caught.value.observation
    assert "archive identity" in observation["failure"]
    assert observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED
    assert observation["result_status"] == RESULT_STATUS_FAILED_POST_CONSTRUCTION
    assert observation["automatic_retry"] is False


def test_absent_origin_branch_is_an_infrastructure_failure(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mission, "_git", _FakeGit(ls_remote=""))
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "publishes no branch" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def test_ambiguous_origin_refs_are_an_infrastructure_failure(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ambiguous = _ref_line(STAGE_2_EVIDENCE_COMMIT) + _ref_line("c" * 40)
    monkeypatch.setattr(mission, "_git", _FakeGit(ls_remote=ambiguous))
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "ambiguous" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def test_unreachable_origin_never_degrades_to_local_verification(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git = _FakeGit(
        ls_remote=CorrectionEvidenceInfrastructureError("could not read from remote repository"),
        local_branch_commit=STAGE_2_EVIDENCE_COMMIT,
    )
    monkeypatch.setattr(mission, "_git", git)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "CorrectionEvidenceInfrastructureError" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED
    assert not any(call[0] == "rev-parse" and not call[1].endswith("^{tree}") for call in git.calls)


def test_missing_commit_object_is_fetched_narrowly_before_the_tree_is_derived(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git = _FakeGit(ls_remote=_ref_line(STAGE_2_EVIDENCE_COMMIT), objects=())
    monkeypatch.setattr(mission, "_git", git)
    result = _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert result.archive_identity["archive_identity_verified"] is True
    assert result.archive_identity["remote_commit_tree_source"] == (
        "FETCHED_OBJECT_FOR_ORIGIN_SUPPLIED_SHA"
    )
    fetches = [call for call in git.calls if call[0] == "fetch"]
    assert len(fetches) == 1
    assert fetches[0][-1] == STAGE_2_EVIDENCE_COMMIT
    assert "--depth" in fetches[0]


def test_an_underivable_tree_is_an_infrastructure_failure(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git = _FakeGit(ls_remote=_ref_line(STAGE_2_EVIDENCE_COMMIT), trees={})
    monkeypatch.setattr(mission, "_git", git)
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "no tree for" in caught.value.observation["failure"]
    assert caught.value.observation["attempt_state"] == CORRECTION_ATTEMPT_STATE_CONSUMED


def test_a_non_sha_origin_response_is_refused(
    tmp_path: Path,
    evidence_dir: Path,
    frozen_input: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mission, "_git", _FakeGit(ls_remote=f"not-a-sha\trefs/heads/{EVIDENCE_BRANCH}\n")
    )
    with pytest.raises(PostConstructionIntegrityError) as caught:
        _execute(tmp_path, evidence_dir, frozen_input, action_plan)
    assert "not a commit SHA" in caught.value.observation["failure"]
