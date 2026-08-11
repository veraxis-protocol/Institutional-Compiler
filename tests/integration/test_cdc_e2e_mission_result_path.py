"""Result-bearing path closure for CDC-END-TO-END-MISSION-001.

Two independent reviews shaped this module. The first found that the legacy
``execute_result_bearing_mission`` accepted any mapping carrying the correct
package-digest label. The second found that the human action plan's SHA-256 was
checked but its *bytes* determined nothing: a correct digest label sat beside a
caller's own choice of stimulus. These tests prove both routes closed and that
exactly one authorized result-bearing route remains.

Structural and stub-driven throughout. Nothing here runs the real frozen
evaluator or warrant contract, creates a real human disposition, emits a real
institutional transition, or adjudicates against Vitaliy's oracle. The stub
components exist so the interlocks can be observed refusing and admitting; what
flows through them is explicitly synthetic.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
import sys
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import CodeType
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_e2e_support import (
    ACTION_PLAN_RELPATH,
    OBSERVED_AT,
    OWNER_INTERPRETATION_RELPATH,
    PACKAGE_RELPATH,
    PREDECESSOR_PACKAGE_RELPATH,
    PREDECESSOR_STRUCTURAL_OBSERVED_AT,
    STUB_RUNTIME,
    bindings_for,
    correction_object,
    disposition_for,
    exact_clearance,
    form_stage_1_for_tests,
    run_metadata,
    stub_evaluator,
    stub_warrant,
)

from oic import cdc_e2e_mission
from oic.cdc_e2e_mission import (
    AUTHORITY_EFFECTIVE_UNTIL,
    AUTHORITY_ISSUED_AT,
    DRAFT_KINDS,
    EXPECTED_CHAIN_COUNT,
    FROZEN_MISSION_INPUT_RELPATH,
    HUMAN_ACTION_PLAN_BYTES,
    HUMAN_ACTION_PLAN_SHA256,
    LEGACY_MAPPING_ENTRYPOINT_STATE,
    OWNER_PREEXECUTION_INTERPRETATION_BYTES,
    OWNER_PREEXECUTION_INTERPRETATION_SHA256,
    OWNER_PREEXECUTION_INTERPRETATION_STATUS,
    PREDECESSOR_AUTHORITY_SHA256,
    PREDECESSOR_MISSION_PACKAGE_BYTES,
    PREDECESSOR_MISSION_PACKAGE_SHA256,
    STAGE_1_AUTHORIZATION_CLEARED,
    STAGE_2_OUTCOME_STATES,
    SUPERSESSION_REASON,
    ActionPlanBindingError,
    ActionPlanProvenanceError,
    AuthorityCurrentnessError,
    ExecutionClearance,
    FrozenActionPlan,
    FrozenMissionInput,
    FrozenOwnerInterpretation,
    MissionContractError,
    MissionProjection,
    OwnerInterpretationProvenanceError,
    ProjectionProvenanceError,
    ResultBearingMissionBlockedError,
    ReviewerStandingError,
    Stage1Observation,
    Stage2Result,
    TransitionDerivationError,
    bind_human_disposition,
    derive_transition_proposal,
    derive_transition_registry,
    execute_authorized_stage_1,
    execute_authorized_stage_2,
    execute_result_bearing_mission,
    observation_producer,
    project_frozen_mission,
    render_drafts,
    require_verified_action_plan,
    require_verified_owner_interpretation,
    validate_frozen_reviewer_standing_exact,
    verify_frozen_action_plan,
    verify_frozen_mission_input,
    verify_owner_preexecution_interpretation,
)

TARGET_CHAIN = "P001xC-TENDER-01"

REPO_ROOT = Path(__file__).resolve().parents[2]


def _owner_interpretation() -> FrozenOwnerInterpretation:
    """Verify the owner record from its bytes; used wherever Stage 1 is invoked."""
    return verify_owner_preexecution_interpretation(REPO_ROOT / OWNER_INTERPRETATION_RELPATH)


# The action classes the frozen plan preregisters, transcribed here so the suite
# states them independently of the loader that recovers them.
EXPECTED_ACTION_CLASSES = {
    "HA-P001-C-TENDER-01": "ACCEPT_CANDIDATE",
    "HA-P001-C-EVAL-01": "ACCEPT_CANDIDATE",
    "HA-P001-C-AWARD-01": "ACCEPT_CANDIDATE",
    "HA-P002-C-TENDER-01": "ACCEPT_CANDIDATE",
    "HA-P002-C-EVAL-01": "ACCEPT_CANDIDATE",
    "HA-P002-C-AWARD-01": "ACCEPT_CANDIDATE",
    "HA-P003-C-TENDER-01": "REQUEST_EVIDENCE",
    "HA-P003-C-EVAL-01": "REQUEST_EVIDENCE",
    "HA-P003-C-AWARD-01": "REQUEST_EVIDENCE",
}


@pytest.fixture
def frozen(repo_root: Path) -> FrozenMissionInput:
    """Verified frozen input; every member byte is read and hashed."""
    return verify_frozen_mission_input(repo_root / PACKAGE_RELPATH)


@pytest.fixture
def projection(frozen: FrozenMissionInput) -> MissionProjection:
    """Executable projection derived from the verified bytes."""
    return project_frozen_mission(frozen)


@pytest.fixture
def action_plan(repo_root: Path) -> FrozenActionPlan:
    """The verified frozen human action plan; its bytes are read and hashed."""
    return verify_frozen_action_plan(repo_root / ACTION_PLAN_RELPATH)


@pytest.fixture
def owner_interpretation(repo_root: Path) -> FrozenOwnerInterpretation:
    """The owner pre-execution interpretation record, verified from its bytes."""
    return verify_owner_preexecution_interpretation(repo_root / OWNER_INTERPRETATION_RELPATH)


@pytest.fixture
def stage_1(projection: MissionProjection, frozen: FrozenMissionInput) -> Stage1Observation:
    """An owner-cleared Stage-1 observation formed with stub components."""
    return execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=_owner_interpretation(),
        evaluator=stub_evaluator,
        warrant_builder=stub_warrant,
    )


def _all_dispositions(
    stage_1: Stage1Observation, projection: MissionProjection, plan: FrozenActionPlan
) -> dict[str, Mapping[str, Any]]:
    """Bind the preregistered stimulus for every chain that formed a candidate."""
    return {
        chain_id: bind_human_disposition(
            stage_1,
            disposition_for(stage_1, projection, chain_id, plan),
            projection=projection,
            action_plan=plan,
        )
        for chain_id in stage_1.artifacts()
    }


def _stage_2(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    plan: FrozenActionPlan,
    *,
    dispositions: Mapping[str, Mapping[str, Any]] | None = None,
    correction: Mapping[str, Any] | None = None,
) -> Stage2Result:
    bound = _all_dispositions(stage_1, projection, plan) if dispositions is None else dispositions
    return execute_authorized_stage_2(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        stage_1=stage_1,
        dispositions=bound,
        action_plan=plan,
        correction=correction,
        run_metadata=run_metadata(),
        stage_2_bindings=bindings_for(stage_1, bound, plan),
    )


# ===========================================================================
# A. Frozen action plan: bytes, not a label
# ===========================================================================


def test_frozen_action_plan_identity_is_recomputed_from_bytes(
    action_plan: FrozenActionPlan,
) -> None:
    """The loader reads the exact bytes and independently recomputes the digest."""
    assert action_plan.sha256_hex == HUMAN_ACTION_PLAN_SHA256
    assert action_plan.byte_count == HUMAN_ACTION_PLAN_BYTES
    assert action_plan.byte_count == len(action_plan.path.read_bytes())
    assert action_plan.mission_id == "CDC-TEST-MISSION-001"
    assert action_plan.reviewer_id == "TEST-REVIEWER-001"
    assert action_plan.authority_scope_ref == "CDC-TEST-MISSION-001/TEST-REVIEWER"
    assert action_plan.permitted_action == "APPLY_TEST_DISPOSITION"
    assert len(action_plan.targets) == 9
    assert len(action_plan.permitted_disposition_vocabulary) == 6


def test_changed_action_plan_bytes_are_rejected(tmp_path: Path, repo_root: Path) -> None:
    """One altered byte breaks verification; the loader refuses to project it."""
    source = repo_root / ACTION_PLAN_RELPATH
    copy = tmp_path / "plan.json"
    copy.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(ActionPlanProvenanceError, match="digest is"):
        verify_frozen_action_plan(copy)


def test_arbitrary_mapping_with_the_correct_plan_digest_label_is_rejected() -> None:
    """A mapping carrying the plan's SHA-256 is not the plan."""
    forged = {
        "sha256": HUMAN_ACTION_PLAN_SHA256,
        "mission_id": "CDC-TEST-MISSION-001",
        "disposition_targets": [],
    }
    with pytest.raises(ActionPlanProvenanceError, match="is not the plan"):
        require_verified_action_plan(forged)


def test_nine_preregistered_action_classes_are_recovered_from_bytes(
    action_plan: FrozenActionPlan, repo_root: Path
) -> None:
    """All nine classes are recovered from the file, matching an independent read."""
    recovered = action_plan.action_classes()
    assert recovered == EXPECTED_ACTION_CLASSES
    # Independently re-read the file rather than trusting the loader's own object.
    document = json.loads((repo_root / ACTION_PLAN_RELPATH).read_bytes())
    direct = {
        target["target_id"]: target["preregistered_reviewer_action_class"]
        for target in document["disposition_targets"]
    }
    assert recovered == direct
    for target in action_plan.targets:
        assert action_plan.target_for(target.procedure_id, target.control_ref) is target
        assert target.runtime_binding_requirement


def test_a_mutated_plan_object_does_not_recompute_its_token(
    action_plan: FrozenActionPlan,
) -> None:
    """Editing a constructed FrozenActionPlan breaks its byte-derived token."""
    tampered = dataclasses.replace(
        action_plan,
        targets=tuple(
            dataclasses.replace(target, preregistered_action_class="QUALIFY")
            for target in action_plan.targets
        ),
    )
    with pytest.raises(ActionPlanProvenanceError, match="does not recompute"):
        require_verified_action_plan(tampered)


# ===========================================================================
# B. Dispositions are the preregistered stimuli
# ===========================================================================


def test_every_chain_binds_its_preregistered_action(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """Each of the nine chains binds exactly the class the frozen plan names."""
    bound = _all_dispositions(stage_1, projection, action_plan)
    assert len(bound) == EXPECTED_CHAIN_COUNT
    observed = {
        str(record["action_plan_target_id"]): str(record["action"]) for record in bound.values()
    }
    assert observed == EXPECTED_ACTION_CLASSES
    for record in bound.values():
        assert record["action"] == record["preregistered_action_class"]
        assert record["action_plan_sha256"] == HUMAN_ACTION_PLAN_SHA256
        assert record["action_plan_provenance_token"] == action_plan.provenance_token


def test_authority_permitted_but_nonpreregistered_action_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """QUALIFY on a P001 target: inside the standing, outside the plan -> REJECT.

    The refusal must be attributable to the action plan, not to authority. Both
    are asserted: the exception is the action-plan one, and the very same
    reviewer, scope and validity are separately shown to be accepted for the
    preregistered class, so nothing about the standing changed between the two.
    """
    assert "QUALIFY" in action_plan.permitted_disposition_vocabulary
    assert "QUALIFY" in projection.authority["permitted_action"]["permitted_dispositions"]
    substitute = disposition_for(stage_1, projection, TARGET_CHAIN, action_plan, action="QUALIFY")
    with pytest.raises(ActionPlanBindingError) as caught:
        bind_human_disposition(stage_1, substitute, projection=projection, action_plan=action_plan)
    message = str(caught.value)
    assert "action-plan mismatch on HA-P001-C-TENDER-01" in message
    assert "authority ceiling" in message
    assert not isinstance(caught.value, ReviewerStandingError)

    # Same reviewer, same scope, same validity: accepted for the preregistered class.
    accepted = bind_human_disposition(
        stage_1,
        disposition_for(stage_1, projection, TARGET_CHAIN, action_plan),
        projection=projection,
        action_plan=action_plan,
    )
    assert accepted["action"] == "ACCEPT_CANDIDATE"
    assert accepted["reviewer_id"] == substitute["reviewer_id"]
    assert accepted["authority_scope_ref"] == substitute["authority_scope_ref"]
    assert accepted["observed_at"] == substitute["observed_at"]


def test_p003_chains_require_request_evidence_not_accept(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """ACCEPT_CANDIDATE is refused where the plan preregisters REQUEST_EVIDENCE."""
    chain_id = "P003xC-EVAL-01"
    assert action_plan.target_for("P-003", "C-EVAL-01").preregistered_action_class == (
        "REQUEST_EVIDENCE"
    )
    wrong = disposition_for(stage_1, projection, chain_id, action_plan, action="ACCEPT_CANDIDATE")
    with pytest.raises(ActionPlanBindingError, match="HA-P003-C-EVAL-01"):
        bind_human_disposition(stage_1, wrong, projection=projection, action_plan=action_plan)


def test_disposition_carrying_a_stale_plan_digest_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """The disposition's own action-plan digest must match the verified plan."""
    stale = {
        **disposition_for(stage_1, projection, TARGET_CHAIN, action_plan),
        "action_plan_sha256": "0" * 64,
    }
    with pytest.raises(ActionPlanBindingError, match="verified action-plan digest"):
        bind_human_disposition(stage_1, stale, projection=projection, action_plan=action_plan)


def test_a_mapping_cannot_be_passed_as_the_action_plan(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """bind_human_disposition refuses a caller mapping in the plan position."""
    disposition = disposition_for(stage_1, projection, TARGET_CHAIN, action_plan)
    with pytest.raises(ActionPlanProvenanceError, match="is not the plan"):
        bind_human_disposition(
            stage_1,
            disposition,
            projection=projection,
            action_plan={"sha256": HUMAN_ACTION_PLAN_SHA256},
        )


# ===========================================================================
# C. Correction target comes from the frozen bytes
# ===========================================================================


def test_correction_target_is_recovered_from_frozen_bytes(action_plan: FrozenActionPlan) -> None:
    """The exact frozen correction target, read from the plan."""
    correction = action_plan.correction
    assert correction.correction_stimulus_id == "HA-CORRECTION-001"
    assert correction.target_id == "HA-P001-C-TENDER-01"
    assert correction.procedure_id == "P-001"
    assert correction.control_ref == "C-TENDER-01"
    assert correction.predecessor_ebawu_ref == "EBAWU-P-001-C-TENDER-01"
    assert correction.predecessor_mutation_prohibited is True
    assert "eligible completed transition" in correction.precondition


def test_no_interface_lets_a_caller_select_the_correction_target() -> None:
    """There is no correction-target parameter anywhere on the authoritative path."""
    for function in (
        execute_authorized_stage_2,
        cdc_e2e_mission.integrate_correction,
        cdc_e2e_mission.require_stage_2_clearance,
    ):
        parameters = set(inspect.signature(function).parameters)
        for forbidden in (
            "correction_stimulus",
            "correction_target",
            "correction_target_id",
            "predecessor_ebawu_ref",
        ):
            assert forbidden not in parameters, f"{function.__name__}:{forbidden}"


def test_a_caller_supplied_p002_correction_target_is_impossible(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Redirecting the correction to P002 requires a plan that no longer verifies."""
    redirected = dataclasses.replace(
        action_plan,
        correction=dataclasses.replace(
            action_plan.correction,
            target_id="HA-P002-C-TENDER-01",
            procedure_id="P-002",
            predecessor_ebawu_ref="EBAWU-P-002-C-TENDER-01",
        ),
    )
    dispositions = _all_dispositions(stage_1, projection, action_plan)
    with pytest.raises(ActionPlanProvenanceError, match="does not recompute"):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=redirected,
            correction=correction_object(),
            run_metadata=run_metadata(),
            stage_2_bindings=bindings_for(stage_1, dispositions, redirected),
        )


def test_stage_2_binds_the_plan_derived_correction_digest(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """A caller mapping cannot define the controlling correction-stimulus digest."""
    dispositions = _all_dispositions(stage_1, projection, action_plan)
    caller_choice = {
        **bindings_for(stage_1, dispositions, action_plan),
        "correction_stimulus_digest": cdc_e2e_mission.sha256(
            {"correction_stimulus_id": "HA-CORRECTION-001", "target_id": "HA-P002-C-TENDER-01"}
        ),
    }
    with pytest.raises(ResultBearingMissionBlockedError, match="correction_stimulus_digest"):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=action_plan,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=caller_choice,
        )


def test_stage_2_binds_the_action_plan_identity(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Stage-2 clearance binds both the plan digest and its byte-derived token."""
    dispositions = _all_dispositions(stage_1, projection, action_plan)
    for field in ("action_plan_sha256", "action_plan_provenance_token"):
        broken = {**bindings_for(stage_1, dispositions, action_plan), field: "0" * 64}
        with pytest.raises(ResultBearingMissionBlockedError, match=field):
            execute_authorized_stage_2(
                projection,
                frozen,
                exact_clearance(),
                STUB_RUNTIME,
                stage_1=stage_1,
                dispositions=dispositions,
                action_plan=action_plan,
                correction=None,
                run_metadata=run_metadata(),
                stage_2_bindings=broken,
            )


# ===========================================================================
# D. No public unauthorized candidate-forming route
# ===========================================================================


def _reaches(code: CodeType, name: str) -> bool:
    """True if this code object, or any nested one, references ``name``."""
    if name in code.co_names or name in code.co_freevars:
        return True
    return any(
        _reaches(constant, name) for constant in code.co_consts if isinstance(constant, CodeType)
    )


def test_no_public_callable_can_form_candidates_without_clearance() -> None:
    """execute_authorized_stage_1 is the only exposed route to candidate formation.

    Proved at bytecode level rather than by reading prose: every public function
    defined in the module is inspected for a reference to the private forming
    helper, including inside nested code objects.
    """
    assert not hasattr(cdc_e2e_mission, "unauthorized_stage_1_helper")
    public = {
        name: value
        for name, value in vars(cdc_e2e_mission).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and getattr(value, "__module__", None) == cdc_e2e_mission.__name__
    }
    assert "execute_authorized_stage_1" in public
    reaching = sorted(
        name for name, function in public.items() if _reaches(function.__code__, "_form_stage_1")
    )
    assert reaching == ["execute_authorized_stage_1"]

    # And that one route cannot skip the interlock.
    source = inspect.getsource(execute_authorized_stage_1)
    assert "require_projected_source" in source
    assert "require_result_clearance" in source


def test_a_test_support_observation_cannot_enter_stage_2(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    action_plan: FrozenActionPlan,
) -> None:
    """Even the test-support wrapper's output is refused by Stage 2."""
    helper_observation = form_stage_1_for_tests(
        projection, frozen, evaluator=stub_evaluator, warrant_builder=stub_warrant
    )
    assert helper_observation.is_owner_cleared() is False
    dispositions = _all_dispositions(helper_observation, projection, action_plan)
    with pytest.raises(
        ResultBearingMissionBlockedError, match="not produced under owner clearance"
    ):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=helper_observation,
            dispositions=dispositions,
            action_plan=action_plan,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=bindings_for(helper_observation, dispositions, action_plan),
        )


# ===========================================================================
# E. The legacy bypass stays closed
# ===========================================================================


def test_legacy_mapping_entrypoint_refuses_a_complete_apparent_clearance() -> None:
    """Arbitrary mapping + correct frozen digest + complete clearance -> REJECTED."""
    reached: list[str] = []

    def forbidden_evaluator(*_args: object) -> Mapping[str, Any]:
        reached.append("evaluator")
        raise AssertionError("the retired entrypoint reached an evaluator")

    def forbidden_warrant(*_args: object) -> tuple[str, Mapping[str, Any]]:
        reached.append("warrant_builder")
        raise AssertionError("the retired entrypoint reached a warrant builder")

    forged = {
        "mission_id": "CDC-TEST-MISSION-001",
        "assurance_mode": "SYNTHETIC_EVALUATION_ONLY",
        "mission_package_sha256": (
            "414d321dad9fe70671508848a19802f35635d27de60b932417f3305b961364f1"
        ),
        "admitted_controls": [
            {
                "control_id": "C-TENDER-01",
                "admission_record_ref": "ADM-P-001-C-TENDER-01",
                "source_ref": "SRC-P-001",
                "control_version": "v1",
            }
        ],
        "population": [{"procedure_id": "P-001"}],
    }
    with pytest.raises(ResultBearingMissionBlockedError, match="retired"):
        execute_result_bearing_mission(
            forged,
            exact_clearance(),
            STUB_RUNTIME,
            evaluator=forbidden_evaluator,
            warrant_builder=forbidden_warrant,
        )
    assert reached == []
    assert LEGACY_MAPPING_ENTRYPOINT_STATE == "RETIRED_FAIL_CLOSED"


# ===========================================================================
# F. Stage-1 clearance
# ===========================================================================


def test_authorized_stage_1_requires_every_exact_binding(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """No clearance -> no Stage-1 candidate."""
    empty = ExecutionClearance(None, None, None, None, None, None, None)
    with pytest.raises(ResultBearingMissionBlockedError, match="missing result-bearing clearance"):
        execute_authorized_stage_1(
            projection,
            frozen,
            empty,
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_authorized_stage_1_requires_the_action_plan_digest(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """ExecutionClearance binds the human action-plan SHA-256."""
    wrong = ExecutionClearance(**{**exact_clearance().as_mapping(), "action_plan_sha256": "0" * 64})
    with pytest.raises(ResultBearingMissionBlockedError, match="action_plan_sha256"):
        execute_authorized_stage_1(
            projection,
            frozen,
            wrong,
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )
    assert exact_clearance().action_plan_sha256 == HUMAN_ACTION_PLAN_SHA256


def test_authorized_stage_1_refuses_a_mapping_source(frozen: FrozenMissionInput) -> None:
    """The authoritative Stage-1 entrypoint will not accept a mapping either."""
    with pytest.raises(ProjectionProvenanceError, match="not the package"):
        execute_authorized_stage_1(
            {"mission_package_sha256": frozen.package_sha256},
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_authorized_stage_1_passes_structurally(stage_1: Stage1Observation) -> None:
    """Under exact clearance, Stage 1 forms nine complete artifacts and stops."""
    assert stage_1.authorization == STAGE_1_AUTHORIZATION_CLEARED
    assert stage_1.is_owner_cleared() is True
    assert stage_1.stage == "EVALUATION_AND_CANDIDATE_FORMATION_COMPLETE"
    assert stage_1.institutional_transition == "NONE"
    assert stage_1.draft_eligibility == "NONE"
    assert stage_1.official_handoff == "PROHIBITED"
    assert len(stage_1.artifacts()) == EXPECTED_CHAIN_COUNT


# ===========================================================================
# G. Complete Stage-1 artifacts
# ===========================================================================


def test_stage_1_preserves_complete_candidate_artifacts(stage_1: Stage1Observation) -> None:
    """The observation retains the objects, not merely their digests."""
    artifact = stage_1.artifacts()[TARGET_CHAIN]
    assert artifact.procedure_id == "P-001"
    assert artifact.control_id == "C-TENDER-01"
    assert artifact.ebawu_id == "EBAWU-P-001-C-TENDER-01"
    assert artifact.warrant_class == "ZTL_WARRANT"
    for name in ("evaluation", "warrant", "candidate"):
        assert isinstance(getattr(artifact, name), Mapping)
    assert artifact.evaluation_digest == cdc_e2e_mission.sha256(artifact.evaluation)
    assert artifact.warrant_digest == cdc_e2e_mission.sha256(artifact.warrant)
    assert artifact.candidate_digest == cdc_e2e_mission.sha256(artifact.candidate)
    assert artifact.input_digest


def test_stage_1_digest_binds_the_objects_not_only_the_digests(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """Changing a warrant body changes the Stage-1 observation digest."""

    def other_warrant(
        evaluation: Mapping[str, Any], control: Mapping[str, Any]
    ) -> tuple[str, Mapping[str, Any]]:
        del control
        return "ZTL_WARRANT", {
            "warrant_id": f"STUB-W-{evaluation['evaluation_id']}",
            "extra": "a different warrant body under the same reference",
        }

    other = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=_owner_interpretation(),
        evaluator=stub_evaluator,
        warrant_builder=other_warrant,
    )
    assert other.artifacts()[TARGET_CHAIN].warrant_ref == (
        stage_1.artifacts()[TARGET_CHAIN].warrant_ref
    )
    assert other.digest() != stage_1.digest()


def test_precomputed_reference_answers_stay_out_of_the_candidate(
    stage_1: Stage1Observation,
) -> None:
    """Frozen answers remain reference-only and never enter a formed candidate."""
    for artifact in stage_1.artifacts().values():
        for field in ("deterministic_evaluation", "warrant_artifact", "adjudicated_result"):
            assert field not in artifact.candidate


# ===========================================================================
# H. Disposition binding and frozen standing
# ===========================================================================


def test_disposition_binds_the_actual_candidate_and_frozen_standing(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """Every required field is bound and the reviewer is validated frozen-side."""
    bound = bind_human_disposition(
        stage_1,
        disposition_for(stage_1, projection, TARGET_CHAIN, action_plan),
        projection=projection,
        action_plan=action_plan,
    )
    artifact = stage_1.artifacts()[TARGET_CHAIN]
    assert bound["candidate_digest"] == artifact.candidate_digest
    assert bound["warrant_digest"] == artifact.warrant_digest
    assert bound["ebawu_id"] == artifact.ebawu_id
    assert bound["stage_1_observation_digest"] == stage_1.digest()
    standing = bound["frozen_standing"]
    assert standing["standing_source"] == "03-AUTHORITY/test-reviewer.json"
    assert standing["caller_supplied_standing_accepted"] is False
    assert standing["revocation_status"] == "NOT_REVOKED"


def test_disposition_missing_a_required_field_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """An incomplete disposition artifact cannot bind."""
    incomplete = dict(disposition_for(stage_1, projection, TARGET_CHAIN, action_plan))
    del incomplete["reviewer_role"]
    with pytest.raises(MissionContractError, match="missing required fields"):
        bind_human_disposition(stage_1, incomplete, projection=projection, action_plan=action_plan)


def test_disposition_with_a_foreign_reviewer_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """The out-of-scope counterpart in the frozen packet is not an authorized reviewer."""
    counterpart = projection.authority["out_of_scope_counterpart"]
    forged = {
        **disposition_for(stage_1, projection, TARGET_CHAIN, action_plan),
        "reviewer_id": counterpart["reviewer_id"],
        "authority_scope_ref": counterpart["authority_scope_ref"],
    }
    with pytest.raises(ReviewerStandingError, match="reviewer_id"):
        bind_human_disposition(stage_1, forged, projection=projection, action_plan=action_plan)


def test_disposition_outside_the_validity_window_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """Standing is bounded in time; an expired observation does not authorize."""
    late = {
        **disposition_for(stage_1, projection, TARGET_CHAIN, action_plan),
        "observed_at": "2027-01-01T00:00:00Z",
    }
    with pytest.raises(MissionContractError):
        bind_human_disposition(stage_1, late, projection=projection, action_plan=action_plan)


def test_disposition_for_a_chain_with_no_candidate_cannot_bind(
    projection: MissionProjection, frozen: FrozenMissionInput, action_plan: FrozenActionPlan
) -> None:
    """A stimulus for a chain that formed nothing is refused, not accommodated."""

    def failing(
        member: Mapping[str, Any], control: Mapping[str, Any], evidence: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        if member["control_ref"] == "C-TENDER-01":
            raise RuntimeError("injected component failure")
        return stub_evaluator(member, control, evidence)

    partial = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=_owner_interpretation(),
        evaluator=failing,
        warrant_builder=stub_warrant,
    )
    assert TARGET_CHAIN not in partial.artifacts()
    complete = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=_owner_interpretation(),
        evaluator=stub_evaluator,
        warrant_builder=stub_warrant,
    )
    stimulus = {
        **disposition_for(complete, projection, TARGET_CHAIN, action_plan),
        "stage_1_observation_digest": partial.digest(),
    }
    with pytest.raises(MissionContractError):
        bind_human_disposition(partial, stimulus, projection=projection, action_plan=action_plan)


# ===========================================================================
# I. Exact Stage-2 artifact binding
# ===========================================================================


def test_stage_2_rejects_a_nonempty_but_wrong_binding(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Non-emptiness is not enough; the binding must equal the actual artifacts."""
    dispositions = _all_dispositions(stage_1, projection, action_plan)
    wrong = {
        **bindings_for(stage_1, dispositions, action_plan),
        "stage_1_observation_digest": "0" * 64,
    }
    with pytest.raises(ResultBearingMissionBlockedError, match="stage_1_observation_digest"):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=action_plan,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=wrong,
        )


def test_stage_2_rejects_a_disposition_digest_set_that_is_not_the_bound_set(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """The disposition digests must be the digests of the artifacts actually bound."""
    dispositions = _all_dispositions(stage_1, projection, action_plan)
    wrong = {
        **bindings_for(stage_1, dispositions, action_plan),
        "human_disposition_artifact_digests": ["1" * 64],
    }
    with pytest.raises(
        ResultBearingMissionBlockedError, match="human_disposition_artifact_digests"
    ):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=action_plan,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=wrong,
        )


# ===========================================================================
# J. Derived proposal and registry
# ===========================================================================


def test_caller_supplied_transition_proposal_cannot_enter(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """A proposal or registry riding along with a disposition is refused."""
    dispositions = dict(_all_dispositions(stage_1, projection, action_plan))
    dispositions[TARGET_CHAIN] = {
        **dispositions[TARGET_CHAIN],
        "transition_proposal": {"requested_disposition": "ACCEPT_CANDIDATE"},
    }
    with pytest.raises(TransitionDerivationError, match="derived, never accepted"):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=action_plan,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=bindings_for(stage_1, dispositions, action_plan),
        )


def test_proposal_and_registry_are_derived_from_the_actual_objects(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """Every derived digest recomputes from the object the registry holds."""
    from oic.cdc_slice import digest as slice_digest

    artifact = stage_1.artifacts()[TARGET_CHAIN]
    disposition = disposition_for(stage_1, projection, TARGET_CHAIN, action_plan)
    registry = derive_transition_registry(projection, artifact)
    proposal = derive_transition_proposal(projection, artifact, disposition)
    assert proposal["candidate_digest"] == slice_digest(
        registry["candidates"][artifact.candidate_id]
    )
    assert proposal["ZTL_warrant_digest"] == slice_digest(
        registry["warrants"][artifact.warrant_ref]
    )
    assert proposal["prior_institutional_state"] == registry["states"][artifact.ebawu_id]
    assert proposal["requested_new_institutional_state"] == "ACCEPTED_CANDIDATE"
    assert set(registry["reviewers"]) == {disposition["reviewer_id"]}


# ===========================================================================
# K. Outcome preservation and denominator
# ===========================================================================


def test_authorized_stage_2_passes_structurally(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Under exact bindings Stage 2 completes and reconciles to nine."""
    result = _stage_2(projection, frozen, stage_1, action_plan)
    assert set(result.accounting) == set(STAGE_2_OUTCOME_STATES)
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT
    assert len(result.outcomes) == EXPECTED_CHAIN_COUNT
    assert result.official_handoff == "PROHIBITED"
    assert result.stage_1_observation_digest == stage_1.digest()


def test_an_escalating_chain_is_preserved_as_unresolved_with_no_event(
    projection: MissionProjection, frozen: FrozenMissionInput, action_plan: FrozenActionPlan
) -> None:
    """The frozen control declares on_unknown: ESCALATE. That outcome is preserved."""

    def unknown_on_one_chain(
        member: Mapping[str, Any], control: Mapping[str, Any], evidence: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        evaluation = dict(stub_evaluator(member, control, evidence))
        if member["control_ref"] == "C-TENDER-01" and member["procedure_id"] == "P-001":
            evaluation["required_condition_state"] = "UNKNOWN"
        return evaluation

    cleared = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=_owner_interpretation(),
        evaluator=unknown_on_one_chain,
        warrant_builder=stub_warrant,
    )
    result = _stage_2(projection, frozen, cleared, action_plan, correction=correction_object())
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    assert target.decision == "ESCALATE"
    assert target.reason_code == "REQUIRED_TRANSITION_CONDITION_UNKNOWN"
    assert target.epistemic_state == "UNRESOLVED_CANNOT"
    assert target.outcome_state == "unresolved"
    assert target.transition_event is None
    assert result.accounting["unresolved"] == 1
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT
    # The correction target sat on the escalating chain, so no correction runs.
    assert result.correction["correction_executed"] is False
    assert result.correction["m12_state"] == "unavailable_incomplete"


def test_a_chain_without_a_disposition_is_blocked_not_dropped(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """A missing disposition is an observed blocked state, not a vanished chain."""
    dispositions = dict(_all_dispositions(stage_1, projection, action_plan))
    dispositions.pop(TARGET_CHAIN)
    result = _stage_2(projection, frozen, stage_1, action_plan, dispositions=dispositions)
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    assert target.outcome_state == "blocked"
    assert target.transition_event is None
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT


# ===========================================================================
# L. Frozen output definitions and French
# ===========================================================================


def test_drafts_trace_to_the_frozen_output_definitions(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Stage 2 renders from 04-OUTPUTS/, preserving each definition's rules."""
    result = _stage_2(projection, frozen, stage_1, action_plan)
    assert len(result.drafts) == 5
    assert [d["output_definition_artifact_id"] for d in result.drafts] == [
        f"CDC-E2E-OUTPUT-0{n}" for n in range(1, 6)
    ]
    for draft, definition in zip(result.drafts, projection.output_definitions, strict=True):
        assert draft["official_status"] == definition["official_status"]
        assert draft["content_state_rule"] == definition["content_state"]
        assert draft["eligibility_determination"] == definition["eligibility_determination"]
        assert draft["provenance_requirements"] == list(definition["required_data_bindings"])
        assert draft["official_handoff"] == "PROHIBITED"
        assert draft["status"] == "SYNTHETIC_DRAFT_NOT_OFFICIAL"


def test_hard_coded_draft_kinds_cannot_substitute_for_frozen_outputs(
    projection: MissionProjection,
) -> None:
    """The historical five-kind vocabulary is not an output source."""
    assert len(DRAFT_KINDS) == 5
    # Deliberately the wrong type: the cast exists so mypy permits the test to
    # supply the hard-coded vocabulary that the runtime must refuse.
    hard_coded = cast("list[Mapping[str, Any]]", list(DRAFT_KINDS))
    with pytest.raises(MissionContractError, match="not a frozen object"):
        render_drafts(hard_coded, provenance={}, french_packet=projection.french_packet)
    with pytest.raises(MissionContractError, match="five frozen output definitions"):
        render_drafts(
            list(projection.output_definitions)[:4],
            provenance={},
            french_packet=projection.french_packet,
        )


def test_french_partial_state_is_an_operational_render_input(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """PARTIAL limits the render; the named absences survive into every draft."""
    result = _stage_2(projection, frozen, stage_1, action_plan)
    expected = list(projection.french_packet["substantive_french_support_absent_at"])
    assert expected
    for draft in result.drafts:
        assert draft["french_render_capability"] == "PARTIAL"
        assert draft["french_named_absences"] == expected
        assert draft["french_capability_synthesized"] is False


# ===========================================================================
# M. Correction execution and preservation
# ===========================================================================


def test_correction_executes_only_after_an_eligible_completed_predecessor(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """With an eligible predecessor the correction runs and preserves its bytes."""
    result = _stage_2(projection, frozen, stage_1, action_plan, correction=correction_object())
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    correction = result.correction
    assert correction["correction_target_id"] == "HA-P001-C-TENDER-01"
    assert correction["correction_target_source"] == "FROZEN_ACTION_PLAN_BYTES"
    if target.outcome_state != "transitioned":
        assert correction["correction_executed"] is False
        return
    assert correction["correction_executed"] is True
    assert correction["predecessor_before_digest"] == correction["predecessor_after_digest"]
    assert correction["predecessor_mutated"] is False
    assert correction["successor_id"] == "EBAWU-P-001-C-TENDER-01-S2"
    assert correction["supersedes"] == "EBAWU-P-001-C-TENDER-01"
    assert correction["changed_refs"] == ["EVB-P-001-C-TENDER-01"]
    assert correction["affected_output_eligibility"].startswith("INELIGIBLE")


def test_correction_is_not_manufactured_without_a_predecessor(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """No eligible predecessor -> explicit absence, never a fabricated correction."""
    dispositions = dict(_all_dispositions(stage_1, projection, action_plan))
    dispositions.pop(TARGET_CHAIN)
    result = _stage_2(
        projection,
        frozen,
        stage_1,
        action_plan,
        dispositions=dispositions,
        correction=correction_object(),
    )
    assert result.correction["correction_executed"] is False
    assert result.correction["m12_state"] == "unavailable_incomplete"
    assert result.correction["eligible_completed_predecessor"] is False


# ===========================================================================
# N. Result-aware observations
# ===========================================================================


def test_m10_and_m12_report_observed_facts_not_literals(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """M10 reports the transitions actually observed; M12 reports the correction."""
    before = observation_producer(projection, frozen)
    assert (
        before["observations"]["M10_VEIP_TRANSITION_AFTER_VALID_DISPOSITION"][
            "transition_events_emitted"
        ]
        == "NOT_YET_OBSERVED"
    )
    assert (
        before["observations"]["M12_CORRECTION_AND_PREDECESSOR_PRESERVATION"]["m12_state"]
        == "precondition_not_yet_reached"
    )

    result = _stage_2(projection, frozen, stage_1, action_plan, correction=correction_object())
    after = observation_producer(projection, frozen, stage_1, result)
    m10 = after["observations"]["M10_VEIP_TRANSITION_AFTER_VALID_DISPOSITION"]
    assert m10["stage_2_observed"] is True
    assert m10["transition_events_emitted"] == len(result.transition_events())
    assert m10["outcome_states"] == dict(result.accounting)
    assert m10["denominator"] == EXPECTED_CHAIN_COUNT
    assert set(m10["per_chain"]) == set(projection.chain_ids())

    m12 = after["observations"]["M12_CORRECTION_AND_PREDECESSOR_PRESERVATION"]
    assert m12["stage_2_observed"] is True
    assert m12["correction_executed"] == result.correction["correction_executed"]
    assert m12["m12_state"] == result.correction["m12_state"]


def test_observations_carry_no_adjudication_vocabulary(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """Result-awareness must not smuggle in a verdict. Vitaliy remains the adjudicator."""
    result = _stage_2(projection, frozen, stage_1, action_plan, correction=correction_object())
    produced = observation_producer(projection, frozen, stage_1, result)
    assert produced["coverage"] == "12/12"
    assert produced["adjudication_present"] is False
    assert "adjudication" not in produced["observations"]
    blob = json.dumps(produced)
    for token in (
        "SEMANTIC_VIOLATION",
        "FORBIDDEN_PROMOTION",
        "PRECONDITION_MISMATCH",
        "ORACLE_MATCH",
        "CONFORMANT",
        "NON_CONFORMANT",
    ):
        assert token not in blob, token


# ===========================================================================
# O. Earlier invariants preserved
# ===========================================================================


def test_frozen_package_and_projection_invariants_survive(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    action_plan: FrozenActionPlan,
) -> None:
    """The action-plan seam does not disturb the earlier guarantees."""
    assert frozen.package_sha256 == projection.package_sha256
    assert len(projection.chains) == EXPECTED_CHAIN_COUNT
    result = _stage_2(projection, frozen, stage_1, action_plan, correction=correction_object())
    produced = observation_producer(projection, frozen, stage_1, result)
    assert produced["member_consumption"]["coverage"] == "14/14"
    assert produced["denominator_accounting"] == dict(result.accounting)
    for chain in projection.chains:
        for field in ("deterministic_evaluation", "warrant_artifact", "candidate"):
            assert field not in chain.execution_input
            assert field in chain.reference_only


# ===========================================================================
# P. Owner pre-execution interpretation record
# ===========================================================================


def test_owner_interpretation_exact_bytes_are_accepted(
    owner_interpretation: FrozenOwnerInterpretation, repo_root: Path
) -> None:
    """The persisted record verifies byte-for-byte against the owner's identity."""
    payload = (repo_root / OWNER_INTERPRETATION_RELPATH).read_bytes()
    assert len(payload) == OWNER_PREEXECUTION_INTERPRETATION_BYTES == 9311
    assert (
        hashlib.sha256(payload).hexdigest()
        == OWNER_PREEXECUTION_INTERPRETATION_SHA256
        == "8242ccf9612531dc7b3b1d648625a934c4f616d8b8565c61d958a6825d7f2f84"
    )
    assert owner_interpretation.sha256_hex == OWNER_PREEXECUTION_INTERPRETATION_SHA256
    assert owner_interpretation.byte_count == OWNER_PREEXECUTION_INTERPRETATION_BYTES
    assert owner_interpretation.status == OWNER_PREEXECUTION_INTERPRETATION_STATUS
    assert owner_interpretation.role == "INTERPRETIVE_AUTHORITY_NOT_COMPUTATIONAL_INPUT"


def test_one_byte_mutation_of_the_owner_record_is_rejected(tmp_path: Path, repo_root: Path) -> None:
    """A single altered byte breaks verification."""
    payload = (repo_root / OWNER_INTERPRETATION_RELPATH).read_bytes()
    mutated = tmp_path / "owner.md"
    mutated.write_bytes(payload[:-1] + bytes([payload[-1] ^ 0x01]))
    assert len(mutated.read_bytes()) == len(payload)
    with pytest.raises(OwnerInterpretationProvenanceError, match="digest is"):
        verify_owner_preexecution_interpretation(mutated)


def test_arbitrary_mapping_with_the_owner_digest_label_is_rejected() -> None:
    """A mapping carrying the record's SHA-256 is not the record."""
    forged = {
        "sha256": OWNER_PREEXECUTION_INTERPRETATION_SHA256,
        "bytes": OWNER_PREEXECUTION_INTERPRETATION_BYTES,
        "status": OWNER_PREEXECUTION_INTERPRETATION_STATUS,
    }
    with pytest.raises(OwnerInterpretationProvenanceError, match="is not the record"):
        require_verified_owner_interpretation(forged)


def test_missing_owner_interpretation_clearance_field_blocks_stage_1(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """An otherwise-complete clearance without the field fails closed."""
    incomplete = ExecutionClearance(
        **{**exact_clearance().as_mapping(), "owner_preexecution_interpretation_sha256": None}
    )
    with pytest.raises(
        ResultBearingMissionBlockedError,
        match="owner_preexecution_interpretation_sha256",
    ):
        execute_authorized_stage_1(
            projection,
            frozen,
            incomplete,
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_empty_owner_interpretation_clearance_field_blocks_stage_1(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """An empty string is absence, not a value."""
    empty_field = ExecutionClearance(
        **{**exact_clearance().as_mapping(), "owner_preexecution_interpretation_sha256": ""}
    )
    with pytest.raises(
        ResultBearingMissionBlockedError,
        match="owner_preexecution_interpretation_sha256",
    ):
        execute_authorized_stage_1(
            projection,
            frozen,
            empty_field,
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_wrong_owner_interpretation_digest_blocks_stage_1(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """A different digest is refused; no new digest is ever adopted."""
    wrong = ExecutionClearance(
        **{**exact_clearance().as_mapping(), "owner_preexecution_interpretation_sha256": "0" * 64}
    )
    with pytest.raises(
        ResultBearingMissionBlockedError,
        match="owner_preexecution_interpretation_sha256",
    ):
        execute_authorized_stage_1(
            projection,
            frozen,
            wrong,
            STUB_RUNTIME,
            owner_interpretation=_owner_interpretation(),
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_stage_1_binds_the_verified_object_not_a_digest_label(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """A caller-supplied label cannot stand in for the verified record."""
    with pytest.raises(OwnerInterpretationProvenanceError, match="is not the record"):
        execute_authorized_stage_1(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            owner_interpretation={"sha256": OWNER_PREEXECUTION_INTERPRETATION_SHA256},
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_verified_owner_interpretation_admits_stage_1_structurally(
    stage_1: Stage1Observation,
) -> None:
    """With the verified record and every other exact binding, Stage 1 is admitted."""
    assert stage_1.is_owner_cleared() is True
    assert stage_1.owner_interpretation_sha256 == OWNER_PREEXECUTION_INTERPRETATION_SHA256
    assert len(stage_1.artifacts()) == EXPECTED_CHAIN_COUNT
    # The interpretation is bound into the Stage-1 checkpoint digest.
    assert stage_1.as_record()["owner_interpretation_sha256"] == (
        OWNER_PREEXECUTION_INTERPRETATION_SHA256
    )


def test_owner_interpretation_prose_never_reaches_the_computation(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    action_plan: FrozenActionPlan,
    owner_interpretation: FrozenOwnerInterpretation,
    repo_root: Path,
) -> None:
    """The record is interpretive authority, never computational input.

    Two independent checks. First, the verified object holds no document text at
    all, so there is nothing for a component to read. Second, the evaluator and
    warrant builder are wrapped and every argument they receive is scanned for
    distinctive phrases from the record; none appears, and neither does any of it
    reach the resulting evaluations, warrants, candidates, dispositions,
    transitions or drafts.
    """
    document = (repo_root / OWNER_INTERPRETATION_RELPATH).read_text(encoding="utf-8")
    phrases = (
        "TERMINOLOGICAL_SHORTHAND_ONLY",
        "INCOMPLETE_OBSERVATION",
        "RUN_UNTIL_PASS",
        "OWNER_FROZEN_PREEXECUTION_INTERPRETATION",
        "pre-execution interpretive authority artifact",
    )
    for phrase in phrases:
        assert phrase in document, phrase

    # The verified object carries identity only.
    identity = json.dumps(owner_interpretation.as_record())
    for phrase in phrases:
        if phrase == "OWNER_FROZEN_PREEXECUTION_INTERPRETATION":
            continue  # the status marker is identity, not prose
        assert phrase not in identity, phrase
    assert len(identity) < 400

    seen: list[str] = []

    def watching_evaluator(
        member: Mapping[str, Any], control: Mapping[str, Any], evidence: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        seen.append(json.dumps([member, control, evidence], default=str))
        return stub_evaluator(member, control, evidence)

    def watching_warrant(
        evaluation: Mapping[str, Any], control: Mapping[str, Any]
    ) -> tuple[str, Mapping[str, Any]]:
        seen.append(json.dumps([evaluation, control], default=str))
        return stub_warrant(evaluation, control)

    cleared = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        owner_interpretation=owner_interpretation,
        evaluator=watching_evaluator,
        warrant_builder=watching_warrant,
    )
    assert seen
    result = _stage_2(projection, frozen, cleared, action_plan, correction=correction_object())
    produced = json.dumps(
        {
            "stage_1": cleared.as_record(),
            "stage_2": result.as_record(),
            "observations": observation_producer(projection, frozen, cleared, result),
        },
        default=str,
    )
    for blob in (*seen, produced):
        for phrase in phrases:
            if phrase == "OWNER_FROZEN_PREEXECUTION_INTERPRETATION":
                continue
            assert phrase not in blob, phrase


# ===========================================================================
# Q. Reviewer-authority currentness (input-v0.2 successor)
# ===========================================================================


def _v1_authority(repo_root: Path) -> Mapping[str, Any]:
    return cast(
        "Mapping[str, Any]",
        json.loads(
            (
                repo_root / PREDECESSOR_PACKAGE_RELPATH / "03-AUTHORITY/test-reviewer.json"
            ).read_bytes()
        ),
    )


def _validate_at(authority: Mapping[str, Any], observed_at: str) -> dict[str, Any]:
    return validate_frozen_reviewer_standing_exact(
        authority,
        mission_id="CDC-TEST-MISSION-001",
        reviewer_id="TEST-REVIEWER-001",
        reviewer_role="CDC_TEST_CONTROLLER",
        authority_scope_ref="CDC-TEST-MISSION-001/TEST-REVIEWER",
        action_class="APPLY_TEST_DISPOSITION",
        disposition="ACCEPT_CANDIDATE",
        observed_at=observed_at,
    )


def test_v1_expired_authority_rejects_a_current_real_time_disposition(
    repo_root: Path,
) -> None:
    """The v0.1 standing lapsed on 2026-08-11T00:00:00Z and cannot authorize now."""
    authority = _v1_authority(repo_root)
    assert authority["validity"]["effective_until"] == "2026-08-11T00:00:00Z"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert now > authority["validity"]["effective_until"]
    with pytest.raises(AuthorityCurrentnessError, match="not current"):
        _validate_at(authority, now)


def test_v1_historical_structural_timestamp_remains_usable_only_in_tests(
    repo_root: Path,
) -> None:
    """The v0.1 window still validates a structural timestamp, and only that.

    This is the distinction the successor exists to draw: the historical
    timestamp is a legitimate fixture for exercising v0.1's structure, and is
    simultaneously not a permissible observation for any real later disposition,
    which the preceding test shows being refused.
    """
    authority = _v1_authority(repo_root)
    record = _validate_at(authority, PREDECESSOR_STRUCTURAL_OBSERVED_AT)
    assert record["observed_at"] == PREDECESSOR_STRUCTURAL_OBSERVED_AT
    assert record["caller_supplied_standing_accepted"] is False
    # And the same timestamp is now outside the controlling v0.2 window.
    current = json.loads(
        (repo_root / PACKAGE_RELPATH / "03-AUTHORITY/test-reviewer.json").read_bytes()
    )
    with pytest.raises(AuthorityCurrentnessError, match="not current"):
        _validate_at(current, PREDECESSOR_STRUCTURAL_OBSERVED_AT)


def test_v2_before_effective_from_is_rejected(projection: MissionProjection) -> None:
    """A disposition observed before issuance is not authorized."""
    effective_from = projection.authority["validity"]["effective_from"]
    with pytest.raises(AuthorityCurrentnessError, match="not current"):
        _validate_at(projection.authority, "2026-08-11T00:00:00Z")
    assert effective_from == AUTHORITY_ISSUED_AT


def test_v2_inside_the_validity_interval_is_accepted(projection: MissionProjection) -> None:
    """Inside the issued window the standing authorizes structurally."""
    record = _validate_at(projection.authority, OBSERVED_AT)
    assert record["revocation_status"] == "NOT_REVOKED"
    assert record["standing_source"] == "03-AUTHORITY/test-reviewer.json"


def test_v2_after_effective_until_is_rejected(projection: MissionProjection) -> None:
    """The successor standing is bounded too; it expires on 2026-08-18."""
    assert projection.authority["validity"]["effective_until"] == AUTHORITY_EFFECTIVE_UNTIL
    with pytest.raises(AuthorityCurrentnessError, match="not current"):
        _validate_at(projection.authority, "2026-08-18T00:00:01Z")


def test_revoked_v2_authority_is_rejected(projection: MissionProjection) -> None:
    """Revocation is checked at disposition time, inside a valid window."""
    revoked = deepcopy(dict(projection.authority))
    revoked["revocation"] = {**revoked["revocation"], "status": "REVOKED"}
    with pytest.raises(ReviewerStandingError):
        _validate_at(revoked, OBSERVED_AT)


def test_caller_cannot_override_observed_at_or_validity(
    projection: MissionProjection, stage_1: Stage1Observation, action_plan: FrozenActionPlan
) -> None:
    """No standing substitute, and a real clock cannot be contradicted."""
    signature = inspect.signature(bind_human_disposition)
    for forbidden in ("standing", "reviewer_standings", "authority", "validity"):
        assert forbidden not in signature.parameters

    # A disposition claiming a different time than the observed clock is refused.
    disposition = disposition_for(stage_1, projection, TARGET_CHAIN, action_plan)
    with pytest.raises(AuthorityCurrentnessError, match="must state the observed clock"):
        bind_human_disposition(
            stage_1,
            disposition,
            projection=projection,
            action_plan=action_plan,
            observed_now="2026-08-13T09:00:00Z",
        )
    # Agreeing with the clock, inside the window, is admitted.
    bound = bind_human_disposition(
        stage_1,
        disposition,
        projection=projection,
        action_plan=action_plan,
        observed_now=OBSERVED_AT,
    )
    assert bound["observed_at"] == OBSERVED_AT

    # The validity window itself comes from the verified bytes, not the caller.
    on_disk = json.loads(
        (REPO_ROOT / FROZEN_MISSION_INPUT_RELPATH / "03-AUTHORITY/test-reviewer.json").read_bytes()
    )
    assert projection.authority["validity"] == on_disk["validity"]


def test_v1_remains_immutable_and_addressable(repo_root: Path) -> None:
    """The predecessor package is retained byte-for-byte and still verifies."""
    v1 = repo_root / PREDECESSOR_PACKAGE_RELPATH
    assert v1.is_dir()
    manifest = json.loads((v1 / "PACKAGE-MANIFEST.json").read_bytes())
    identities = [
        {
            "path": member["path"],
            "bytes": len((v1 / member["path"]).read_bytes()),
            "sha256": hashlib.sha256((v1 / member["path"]).read_bytes()).hexdigest(),
            "sha512": hashlib.sha512((v1 / member["path"]).read_bytes()).hexdigest(),
        }
        for member in manifest["members"]
    ]
    for observed, declared in zip(identities, manifest["members"], strict=True):
        assert observed == {name: declared[name] for name in observed}
    recomputed = hashlib.sha256(
        json.dumps(identities, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    assert recomputed == PREDECESSOR_MISSION_PACKAGE_SHA256
    assert (
        sum(path.stat().st_size for path in v1.rglob("*") if path.is_file())
        == PREDECESSOR_MISSION_PACKAGE_BYTES
    )
    assert (
        hashlib.sha256((v1 / "03-AUTHORITY/test-reviewer.json").read_bytes()).hexdigest()
        == PREDECESSOR_AUTHORITY_SHA256
    )


def test_v2_supersedes_v1_for_authority_currentness_only(
    projection: MissionProjection, repo_root: Path
) -> None:
    """Exactly one substantive member changed, and it changed only its validity."""
    v1 = repo_root / PREDECESSOR_PACKAGE_RELPATH
    v2 = repo_root / PACKAGE_RELPATH
    manifest = json.loads((v2 / "PACKAGE-MANIFEST.json").read_bytes())
    assert manifest["supersession_reason"] == SUPERSESSION_REASON
    assert manifest["supersedes"] == "CDC-END-TO-END-MISSION-001-INPUT-v0.1"
    assert manifest["predecessor_package_sha256"] == PREDECESSOR_MISSION_PACKAGE_SHA256
    assert manifest["predecessor_retained_immutable"] is True
    assert manifest["result_bearing_execution_seen_before_supersession"] is False

    differing = [
        member["path"]
        for member in manifest["members"]
        if (v1 / member["path"]).read_bytes() != (v2 / member["path"]).read_bytes()
    ]
    assert differing == ["03-AUTHORITY/test-reviewer.json", "SHA256SUMS"]

    before = _v1_authority(repo_root)
    after = projection.authority
    for key in (
        "identity",
        "role",
        "mission",
        "authority_scope_ref",
        "permitted_action",
        "assurance_mode",
        "authority_basis",
        "revocation",
        "record_id",
        "authorization_representation",
    ):
        assert after[key] == before[key], key
    assert after["validity"] != before["validity"]
    supersession = after["supersession"]
    assert supersession["supersession_reason"] == SUPERSESSION_REASON
    assert supersession["predecessor_authority_sha256"] == PREDECESSOR_AUTHORITY_SHA256
    assert supersession["result_bearing_execution_seen_before_supersession"] is False
    assert "synthetic test authority only" in supersession["claim_ceiling"]
