"""Result-bearing path closure for CDC-END-TO-END-MISSION-001.

Independent review of ``b695592`` found that the verified-byte seam existed but a
legacy result-bearing bypass remained reachable: ``execute_result_bearing_mission``
accepted an arbitrary mapping that merely carried the correct package-digest
label. These tests prove that route is closed and that exactly one authorized
result-bearing route remains.

Structural and stub-driven throughout. Nothing here runs the real frozen
evaluator or warrant contract, creates a real human disposition, emits a real
institutional transition, or adjudicates against Vitaliy's oracle. The stub
components exist so the interlocks can be observed refusing and admitting; what
flows through them is explicitly synthetic.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_e2e_support import (
    CORRECTION_STIMULUS,
    PACKAGE_RELPATH,
    STUB_RUNTIME,
    correction_object,
    disposition_for,
    exact_clearance,
    run_metadata,
    stub_evaluator,
    stub_warrant,
)

from oic.cdc_e2e_mission import (
    DRAFT_KINDS,
    EXPECTED_CHAIN_COUNT,
    HUMAN_ACTION_PLAN_SHA256,
    LEGACY_MAPPING_ENTRYPOINT_STATE,
    STAGE_1_AUTHORIZATION_CLEARED,
    STAGE_1_AUTHORIZATION_HELPER,
    STAGE_2_OUTCOME_STATES,
    CandidateBindingError,
    ExecutionClearance,
    FrozenMissionInput,
    MissionContractError,
    MissionProjection,
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
    sha256,
    unauthorized_stage_1_helper,
    verify_frozen_mission_input,
)

TARGET_CHAIN = "P001xC-TENDER-01"


@pytest.fixture
def frozen(repo_root: Path) -> FrozenMissionInput:
    """Verified frozen input; every member byte is read and hashed."""
    return verify_frozen_mission_input(repo_root / PACKAGE_RELPATH)


@pytest.fixture
def projection(frozen: FrozenMissionInput) -> MissionProjection:
    """Executable projection derived from the verified bytes."""
    return project_frozen_mission(frozen)


@pytest.fixture
def stage_1(projection: MissionProjection, frozen: FrozenMissionInput) -> Stage1Observation:
    """An owner-cleared Stage-1 observation formed with stub components."""
    return execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        evaluator=stub_evaluator,
        warrant_builder=stub_warrant,
    )


def _all_dispositions(
    stage_1: Stage1Observation, projection: MissionProjection
) -> dict[str, Mapping[str, Any]]:
    return {
        chain_id: bind_human_disposition(
            stage_1,
            disposition_for(stage_1, projection, chain_id),
            projection=projection,
            action_plan_sha256=HUMAN_ACTION_PLAN_SHA256,
        )
        for chain_id in stage_1.artifacts()
    }


def _bindings(
    stage_1: Stage1Observation, dispositions: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "stage_1_observation_digest": stage_1.digest(),
        "human_disposition_artifact_digests": sorted(
            sha256(dict(record)) for record in dispositions.values()
        ),
        "correction_stimulus_digest": sha256(CORRECTION_STIMULUS),
    }


def _stage_2(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    *,
    dispositions: Mapping[str, Mapping[str, Any]] | None = None,
    correction: Mapping[str, Any] | None = None,
) -> Stage2Result:
    bound = _all_dispositions(stage_1, projection) if dispositions is None else dispositions
    return execute_authorized_stage_2(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        stage_1=stage_1,
        dispositions=bound,
        correction_stimulus=CORRECTION_STIMULUS,
        correction=correction,
        run_metadata=run_metadata(),
        stage_2_bindings=_bindings(stage_1, bound),
    )


# 1 — the legacy bypass ------------------------------------------------------
def test_legacy_mapping_entrypoint_refuses_a_complete_apparent_clearance(
    frozen: FrozenMissionInput,
) -> None:
    """Arbitrary mapping + correct frozen digest + complete clearance -> REJECTED.

    This goes through the actual legacy public entrypoint, not through
    ``require_projected_source``. Every binding the old path checked is supplied
    correctly, so the refusal cannot be attributed to a missing field.
    """
    del frozen
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


# 2 — Stage 1 requires owner clearance ---------------------------------------
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
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


def test_authorized_stage_1_requires_the_action_plan_digest(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """ExecutionClearance now binds the human action-plan SHA-256."""
    wrong = ExecutionClearance(**{**exact_clearance().as_mapping(), "action_plan_sha256": "0" * 64})
    with pytest.raises(ResultBearingMissionBlockedError, match="action_plan_sha256"):
        execute_authorized_stage_1(
            projection,
            frozen,
            wrong,
            STUB_RUNTIME,
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
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )


# 3 — complete Stage-1 artifacts ---------------------------------------------
def test_stage_1_preserves_complete_candidate_artifacts(stage_1: Stage1Observation) -> None:
    """The observation retains the objects, not merely their digests."""
    assert stage_1.authorization == STAGE_1_AUTHORIZATION_CLEARED
    artifacts = stage_1.artifacts()
    assert len(artifacts) == EXPECTED_CHAIN_COUNT
    artifact = artifacts[TARGET_CHAIN]
    assert artifact.procedure_id == "P-001"
    assert artifact.control_id == "C-TENDER-01"
    assert artifact.ebawu_id == "EBAWU-P-001-C-TENDER-01"
    assert artifact.warrant_class == "ZTL_WARRANT"
    for name in ("evaluation", "warrant", "candidate"):
        assert isinstance(getattr(artifact, name), Mapping)
    assert artifact.evaluation_digest == sha256(artifact.evaluation)
    assert artifact.warrant_digest == sha256(artifact.warrant)
    assert artifact.candidate_digest == sha256(artifact.candidate)
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
        evaluator=stub_evaluator,
        warrant_builder=other_warrant,
    )
    assert other.artifacts()[TARGET_CHAIN].warrant_ref == (
        stage_1.artifacts()[TARGET_CHAIN].warrant_ref
    )
    assert other.digest() != stage_1.digest()


def test_precomputed_reference_answers_stay_out_of_the_candidate(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """Frozen answers remain reference-only and never enter a formed candidate."""
    del projection
    for artifact in stage_1.artifacts().values():
        blob = sha256(artifact.candidate)
        assert blob
        for field in ("deterministic_evaluation", "warrant_artifact", "adjudicated_result"):
            assert field not in artifact.candidate


# 4 — disposition binds actual candidate + frozen standing -------------------
def test_disposition_binds_the_actual_candidate_and_frozen_standing(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """Every required field is bound and the reviewer is validated frozen-side."""
    bound = bind_human_disposition(
        stage_1,
        disposition_for(stage_1, projection, TARGET_CHAIN),
        projection=projection,
        action_plan_sha256=HUMAN_ACTION_PLAN_SHA256,
    )
    artifact = stage_1.artifacts()[TARGET_CHAIN]
    assert bound["candidate_digest"] == artifact.candidate_digest
    assert bound["warrant_digest"] == artifact.warrant_digest
    assert bound["ebawu_id"] == artifact.ebawu_id
    assert bound["stage_1_observation_digest"] == stage_1.digest()
    assert bound["action"] == "ACCEPT_CANDIDATE"
    standing = bound["frozen_standing"]
    assert standing["standing_source"] == "03-AUTHORITY/test-reviewer.json"
    assert standing["caller_supplied_standing_accepted"] is False
    assert standing["revocation_status"] == "NOT_REVOKED"


def test_disposition_missing_a_required_field_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """An incomplete disposition artifact cannot bind."""
    incomplete = dict(disposition_for(stage_1, projection, TARGET_CHAIN))
    del incomplete["reviewer_role"]
    with pytest.raises(MissionContractError, match="missing required fields"):
        bind_human_disposition(
            stage_1, incomplete, projection=projection, action_plan_sha256=HUMAN_ACTION_PLAN_SHA256
        )


def test_disposition_with_a_foreign_reviewer_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """The out-of-scope counterpart in the frozen packet is not an authorized reviewer."""
    counterpart = projection.authority["out_of_scope_counterpart"]
    forged = {
        **disposition_for(stage_1, projection, TARGET_CHAIN),
        "reviewer_id": counterpart["reviewer_id"],
        "authority_scope_ref": counterpart["authority_scope_ref"],
    }
    with pytest.raises(ReviewerStandingError, match="reviewer_id"):
        bind_human_disposition(
            stage_1, forged, projection=projection, action_plan_sha256=HUMAN_ACTION_PLAN_SHA256
        )


def test_disposition_outside_the_validity_window_is_rejected(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """Standing is bounded in time; an expired observation does not authorize."""
    late = {
        **disposition_for(stage_1, projection, TARGET_CHAIN),
        "observed_at": "2027-01-01T00:00:00Z",
    }
    with pytest.raises(MissionContractError):
        bind_human_disposition(
            stage_1, late, projection=projection, action_plan_sha256=HUMAN_ACTION_PLAN_SHA256
        )


def test_disposition_for_a_chain_with_no_candidate_cannot_bind(
    projection: MissionProjection, frozen: FrozenMissionInput
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
        evaluator=failing,
        warrant_builder=stub_warrant,
    )
    assert TARGET_CHAIN not in partial.artifacts()
    complete = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        evaluator=stub_evaluator,
        warrant_builder=stub_warrant,
    )
    stimulus = {
        **disposition_for(complete, projection, TARGET_CHAIN),
        "stage_1_observation_digest": partial.digest(),
    }
    with pytest.raises(MissionContractError):
        bind_human_disposition(
            partial, stimulus, projection=projection, action_plan_sha256=HUMAN_ACTION_PLAN_SHA256
        )


# 5 — exact Stage-2 artifact binding -----------------------------------------
def test_stage_2_rejects_a_nonempty_but_wrong_binding(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """Non-emptiness is not enough; the binding must equal the actual artifacts."""
    dispositions = _all_dispositions(stage_1, projection)
    wrong = {**_bindings(stage_1, dispositions), "stage_1_observation_digest": "0" * 64}
    with pytest.raises(ResultBearingMissionBlockedError, match="stage_1_observation_digest"):
        execute_authorized_stage_2(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            stage_1=stage_1,
            dispositions=dispositions,
            correction_stimulus=CORRECTION_STIMULUS,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=wrong,
        )


def test_stage_2_rejects_a_disposition_digest_set_that_is_not_the_bound_set(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """The disposition digests must be the digests of the artifacts actually bound."""
    dispositions = _all_dispositions(stage_1, projection)
    wrong = {
        **_bindings(stage_1, dispositions),
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
            correction_stimulus=CORRECTION_STIMULUS,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=wrong,
        )


def test_stage_2_rejects_an_unauthorized_stage_1_observation(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """The unit-test helper's output cannot be promoted into the authorized path."""
    helper_observation = unauthorized_stage_1_helper(
        projection, frozen, evaluator=stub_evaluator, warrant_builder=stub_warrant
    )
    assert helper_observation.authorization == STAGE_1_AUTHORIZATION_HELPER
    assert helper_observation.is_owner_cleared() is False
    dispositions = _all_dispositions(helper_observation, projection)
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
            correction_stimulus=CORRECTION_STIMULUS,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=_bindings(helper_observation, dispositions),
        )


# 6 — derived proposal and registry ------------------------------------------
def test_caller_supplied_transition_proposal_cannot_enter(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """A proposal or registry riding along with a disposition is refused."""
    dispositions = dict(_all_dispositions(stage_1, projection))
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
            correction_stimulus=CORRECTION_STIMULUS,
            correction=None,
            run_metadata=run_metadata(),
            stage_2_bindings=_bindings(stage_1, dispositions),
        )


def test_proposal_and_registry_are_derived_from_the_actual_objects(
    projection: MissionProjection, stage_1: Stage1Observation
) -> None:
    """Every derived digest recomputes from the object the registry holds."""
    from oic.cdc_slice import digest as slice_digest

    artifact = stage_1.artifacts()[TARGET_CHAIN]
    disposition = disposition_for(stage_1, projection, TARGET_CHAIN)
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


# 7 — outcomes preserved ------------------------------------------------------
def test_denominator_reconciles_to_nine_across_stage_2(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """Every chain carries exactly one preserved outcome state."""
    result = _stage_2(projection, frozen, stage_1)
    assert set(result.accounting) == set(STAGE_2_OUTCOME_STATES)
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT
    assert len(result.outcomes) == EXPECTED_CHAIN_COUNT
    assert {outcome.outcome_state for outcome in result.outcomes} <= set(STAGE_2_OUTCOME_STATES)


def test_a_non_allow_gate_result_is_preserved_and_emits_no_event(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """REQUEST_EVIDENCE is a permitted disposition whose gate result is not ALLOW."""
    dispositions = {
        chain_id: bind_human_disposition(
            stage_1,
            disposition_for(
                stage_1,
                projection,
                chain_id,
                action="REQUEST_EVIDENCE" if chain_id == TARGET_CHAIN else "ACCEPT_CANDIDATE",
            ),
            projection=projection,
            action_plan_sha256=HUMAN_ACTION_PLAN_SHA256,
        )
        for chain_id in stage_1.artifacts()
    }
    result = _stage_2(projection, frozen, stage_1, dispositions=dispositions)
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    assert target.epistemic_state == "UNRESOLVED"
    assert target.outcome_state in {"transitioned", "refused", "unresolved"}
    if target.outcome_state != "transitioned":
        assert target.transition_event is None
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT


def test_an_escalating_chain_is_preserved_as_unresolved_with_no_event(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """The frozen control declares on_unknown: ESCALATE. That outcome is preserved.

    No transition event is fabricated for a non-ALLOW gate result, and the chain
    still occupies exactly one slot in the denominator.
    """

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
        evaluator=unknown_on_one_chain,
        warrant_builder=stub_warrant,
    )
    result = _stage_2(projection, frozen, cleared, correction=correction_object())
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    assert target.decision == "ESCALATE"
    assert target.reason_code == "REQUIRED_TRANSITION_CONDITION_UNKNOWN"
    assert target.epistemic_state == "UNRESOLVED_CANNOT"
    assert target.outcome_state == "unresolved"
    assert target.transition_event is None
    assert result.accounting["unresolved"] == 1
    assert result.accounting["transitioned"] == EXPECTED_CHAIN_COUNT - 1
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT
    # The correction target sat on the escalating chain, so no correction runs.
    assert result.correction["correction_executed"] is False
    assert result.correction["m12_state"] == "unavailable_incomplete"


def test_a_chain_without_a_disposition_is_blocked_not_dropped(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """A missing disposition is an observed blocked state, not a vanished chain."""
    dispositions = dict(_all_dispositions(stage_1, projection))
    dispositions.pop(TARGET_CHAIN)
    result = _stage_2(projection, frozen, stage_1, dispositions=dispositions)
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    assert target.outcome_state == "blocked"
    assert target.transition_event is None
    assert sum(result.accounting.values()) == EXPECTED_CHAIN_COUNT


# 8 — frozen output definitions ----------------------------------------------
def test_drafts_trace_to_the_frozen_output_definitions(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """Stage 2 renders from 04-OUTPUTS/, preserving each definition's rules."""
    result = _stage_2(projection, frozen, stage_1)
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
        render_drafts(
            hard_coded,
            provenance={},
            french_packet=projection.french_packet,
        )
    with pytest.raises(MissionContractError, match="five frozen output definitions"):
        render_drafts(
            list(projection.output_definitions)[:4],
            provenance={},
            french_packet=projection.french_packet,
        )


# 9 — French packet consumed operationally ------------------------------------
def test_french_partial_state_is_an_operational_render_input(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """PARTIAL limits the render; the named absences survive into every draft."""
    result = _stage_2(projection, frozen, stage_1)
    expected = list(projection.french_packet["substantive_french_support_absent_at"])
    assert expected
    for draft in result.drafts:
        assert draft["french_render_capability"] == "PARTIAL"
        assert draft["french_named_absences"] == expected
        assert draft["french_capability_synthesized"] is False


# 10 — correction integration --------------------------------------------------
def test_correction_executes_only_after_an_eligible_completed_predecessor(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """With an eligible predecessor the correction runs and preserves its bytes."""
    result = _stage_2(projection, frozen, stage_1, correction=correction_object())
    target = next(o for o in result.outcomes if o.chain_id == TARGET_CHAIN)
    correction = result.correction
    if target.outcome_state != "transitioned":
        assert correction["correction_executed"] is False
        assert correction["m12_state"] == "unavailable_incomplete"
        return
    assert correction["correction_executed"] is True
    assert correction["predecessor_before_digest"] == correction["predecessor_after_digest"]
    assert correction["predecessor_mutated"] is False
    assert correction["successor_id"] == "EBAWU-P-001-C-TENDER-01-S2"
    assert correction["supersedes"] == "EBAWU-P-001-C-TENDER-01"
    assert correction["changed_refs"] == ["EVB-P-001-C-TENDER-01"]
    assert correction["affected_output_eligibility"].startswith("INELIGIBLE")


def test_correction_is_not_manufactured_without_a_predecessor(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """No eligible predecessor -> explicit absence, never a fabricated correction."""
    dispositions = dict(_all_dispositions(stage_1, projection))
    dispositions.pop(TARGET_CHAIN)
    result = _stage_2(
        projection, frozen, stage_1, dispositions=dispositions, correction=correction_object()
    )
    assert result.correction["correction_executed"] is False
    assert result.correction["m12_state"] == "unavailable_incomplete"
    assert result.correction["eligible_completed_predecessor"] is False


# 11 — result-aware observations ------------------------------------------------
def test_m10_and_m12_report_observed_facts_not_literals(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
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

    result = _stage_2(projection, frozen, stage_1, correction=correction_object())
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
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """Result-awareness must not smuggle in a verdict. Vitaliy remains the adjudicator."""
    import json

    result = _stage_2(projection, frozen, stage_1, correction=correction_object())
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


# 12 — result-bearing path uniqueness ------------------------------------------
def test_exactly_one_authorized_result_bearing_route_exists(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """The structural uniqueness proof, assembled from the individual refusals."""
    empty = ExecutionClearance(None, None, None, None, None, None, None)

    # (a) the legacy mapping entrypoint always refuses
    with pytest.raises(ResultBearingMissionBlockedError, match="retired"):
        execute_result_bearing_mission(
            {"mission_package_sha256": frozen.package_sha256},
            exact_clearance(),
            STUB_RUNTIME,
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )

    # (b) the raw helper is not an authorized entrypoint: its output is stamped
    helper = unauthorized_stage_1_helper(
        projection, frozen, evaluator=stub_evaluator, warrant_builder=stub_warrant
    )
    assert helper.is_owner_cleared() is False

    # (c) authoritative Stage 1 requires exact clearance
    with pytest.raises(ResultBearingMissionBlockedError):
        execute_authorized_stage_1(
            projection,
            frozen,
            empty,
            STUB_RUNTIME,
            evaluator=stub_evaluator,
            warrant_builder=stub_warrant,
        )

    # (d) Stage 2 requires exact Stage-1, disposition and correction binding
    cleared = execute_authorized_stage_1(
        projection,
        frozen,
        exact_clearance(),
        STUB_RUNTIME,
        evaluator=stub_evaluator,
        warrant_builder=stub_warrant,
    )
    dispositions = _all_dispositions(cleared, projection)
    for field in (
        "stage_1_observation_digest",
        "human_disposition_artifact_digests",
        "correction_stimulus_digest",
    ):
        broken = dict(_bindings(cleared, dispositions))
        broken[field] = "0" * 64
        with pytest.raises(ResultBearingMissionBlockedError):
            execute_authorized_stage_2(
                projection,
                frozen,
                exact_clearance(),
                STUB_RUNTIME,
                stage_1=cleared,
                dispositions=dispositions,
                correction_stimulus=CORRECTION_STIMULUS,
                correction=None,
                run_metadata=run_metadata(),
                stage_2_bindings=broken,
            )

    # (e) a caller-supplied reviewer standing has no parameter to enter through
    import inspect

    signature = inspect.signature(bind_human_disposition)
    assert "standing" not in signature.parameters
    assert "reviewer_standings" not in signature.parameters
    stage_2_signature = inspect.signature(execute_authorized_stage_2)
    for forbidden in ("transition_proposal", "transition_registry", "registry", "proposal"):
        assert forbidden not in stage_2_signature.parameters

    # (f) a forged candidate digest cannot bind
    with pytest.raises(CandidateBindingError):
        bind_human_disposition(
            cleared,
            {**disposition_for(cleared, projection, TARGET_CHAIN), "candidate_digest": "0" * 64},
            projection=projection,
            action_plan_sha256=HUMAN_ACTION_PLAN_SHA256,
        )


# 13 — earlier invariants preserved --------------------------------------------
def test_frozen_package_and_projection_invariants_survive(
    projection: MissionProjection, frozen: FrozenMissionInput, stage_1: Stage1Observation
) -> None:
    """The Stage-1/Stage-2 additions do not disturb the earlier guarantees."""
    assert frozen.package_sha256 == projection.package_sha256
    assert len(projection.chains) == EXPECTED_CHAIN_COUNT
    result = _stage_2(projection, frozen, stage_1, correction=correction_object())
    produced = observation_producer(projection, frozen, stage_1, result)
    assert produced["member_consumption"]["coverage"] == "14/14"
    assert produced["denominator_accounting"] == dict(result.accounting)
    assert result.official_handoff == "PROHIBITED"
    for chain in projection.chains:
        for field in ("deterministic_evaluation", "warrant_artifact", "candidate"):
            assert field not in chain.execution_input
            assert field in chain.reference_only
