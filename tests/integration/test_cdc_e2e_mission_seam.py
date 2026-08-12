"""Structural tests for the CDC-END-TO-END-MISSION-001 seam closure.

Non-result-bearing. No test here executes the frozen mission: nothing calls the
result-bearing entry point, emits an institutional transition, produces a draft,
or adjudicates anything against the oracle. Stage 1 is exercised with injected
stub components so the seam can be tested without the governed evaluation and
warrant contracts, which are not this module's to supply.

The central property under test is that a caller-supplied mapping carrying the
correct package-digest *label* cannot substitute for the verified frozen bytes.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_e2e_support import (
    ACTION_PLAN_RELPATH,
    PACKAGE_RELPATH,
    STUB_RUNTIME,
    bind_disposition_at,
    disposition_for,
    exact_clearance,
    form_stage_1_for_tests,
)
from cdc_e2e_support import (
    stub_evaluator as _stub_evaluator,
)
from cdc_e2e_support import (
    stub_warrant as _stub_warrant,
)

from oic import cdc_e2e_mission
from oic.cdc_e2e_mission import (
    DENOMINATOR_STATES,
    EXPECTED_CHAIN_COUNT,
    FROZEN_MISSION_PACKAGE_SHA256,
    HUMAN_ACTION_PLAN_SHA256,
    OBSERVATION_IDS,
    REFERENCE_ONLY_CHAIN_FIELDS,
    CandidateBindingError,
    ExecutionClearance,
    FrozenActionPlan,
    FrozenMissionInput,
    HumanDispositionRequiredError,
    MissionContractError,
    MissionProjection,
    PredecessorBindingError,
    ProjectionProvenanceError,
    ResultBearingMissionBlockedError,
    bind_correction,
    member_consumption_ledger,
    observation_producer,
    project_frozen_mission,
    require_human_disposition,
    require_projected_source,
    require_stage_2_clearance,
    verify_frozen_action_plan,
    verify_frozen_mission_input,
)


# Stage-1 candidate formation over the frozen mission population is blocked by
# MissionPopulationExecutionBlockedError until a fresh one-run owner execution
# authorization exists. The owner source-delta authorization explicitly forbids
# producing the mission's actual nine outcomes in any test. These tests are
# preserved in place and re-enable themselves the moment formation is
# authorized; the refusal itself is asserted by
# test_stage_1_over_the_frozen_population_is_blocked.
def _skip_unless_formation_authorized() -> None:
    if cdc_e2e_mission.MISSION_EXECUTION_AUTHORIZATION is None:
        pytest.skip(
            "Stage-1 candidate formation over the frozen mission population is not "
            "authorized (MISSION_POPULATION_EXECUTION_STATE="
            f"{cdc_e2e_mission.MISSION_POPULATION_EXECUTION_STATE})"
        )


@pytest.fixture
def package_root(repo_root: Path) -> Path:
    """The persisted frozen mission package."""
    return repo_root / PACKAGE_RELPATH


@pytest.fixture
def frozen(package_root: Path) -> FrozenMissionInput:
    """Verified frozen input; every member byte is read and hashed."""
    return verify_frozen_mission_input(package_root)


@pytest.fixture
def projection(frozen: FrozenMissionInput) -> MissionProjection:
    """Executable projection derived from the verified bytes."""
    return project_frozen_mission(frozen)


@pytest.fixture
def action_plan(repo_root: Path) -> FrozenActionPlan:
    """The verified frozen human action plan."""
    return verify_frozen_action_plan(repo_root / ACTION_PLAN_RELPATH)


# 1 --------------------------------------------------------------------------
def test_arbitrary_mapping_with_correct_digest_label_is_rejected(
    frozen: FrozenMissionInput,
) -> None:
    """A mapping that merely claims the package digest is not the package."""
    forged = {
        "mission_id": "CDC-TEST-MISSION-001",
        "assurance_mode": "SYNTHETIC_EVALUATION_ONLY",
        "mission_package_sha256": FROZEN_MISSION_PACKAGE_SHA256,
        "admitted_controls": [],
        "population": [],
    }
    with pytest.raises(ProjectionProvenanceError, match="not the package"):
        require_projected_source(forged, frozen)


# 2 --------------------------------------------------------------------------
def test_changed_package_byte_is_rejected(tmp_path: Path, package_root: Path) -> None:
    """One altered byte in any member breaks verification."""
    copy = tmp_path / "pkg"
    copy.mkdir()
    for source in package_root.rglob("*"):
        if source.is_file():
            target = copy / source.relative_to(package_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    victim = copy / "05-FRENCH/french-packet.json"
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(MissionContractError):
        verify_frozen_mission_input(copy)


# 3 --------------------------------------------------------------------------
def test_nine_chain_projection_is_exact(projection: MissionProjection) -> None:
    """Exactly nine procedure/control chains, no more and no fewer."""
    assert len(projection.chains) == EXPECTED_CHAIN_COUNT
    assert projection.chain_ids() == (
        "P001xC-TENDER-01",
        "P001xC-EVAL-01",
        "P001xC-AWARD-01",
        "P002xC-TENDER-01",
        "P002xC-EVAL-01",
        "P002xC-AWARD-01",
        "P003xC-TENDER-01",
        "P003xC-EVAL-01",
        "P003xC-AWARD-01",
    )


# 4 --------------------------------------------------------------------------
def test_precomputed_values_are_not_execution_input(projection: MissionProjection) -> None:
    """Frozen answers cannot reach computation: v0.6 does not carry them at all.

    The earlier packages carried precomputed evaluations, warrants and candidates
    and relied on classifying them reference-only. input-v0.6 removed them, so
    the stronger property now holds: there is nothing to classify.
    """
    for chain in projection.chains:
        for field in REFERENCE_ONLY_CHAIN_FIELDS:
            assert field not in chain.execution_input, f"{chain.chain_id}:{field}"
        assert chain.reference_only == {}, chain.chain_id


# 5 --------------------------------------------------------------------------
def test_frozen_authority_object_is_consumed(projection: MissionProjection) -> None:
    """Standing comes from the package, with every nested dimension present."""
    for dimension in (
        "identity",
        "role",
        "mission",
        "authority_scope_ref",
        "permitted_action",
        "validity",
        "revocation",
    ):
        assert dimension in projection.authority, dimension
    assert projection.authority["identity"]["real_world_identity"].startswith("NONE")


# 6 --------------------------------------------------------------------------
def test_five_frozen_output_definitions_are_consumed(projection: MissionProjection) -> None:
    """All five outputs are read from the package and remain non-official."""
    ids = [str(o["artifact_id"]) for o in projection.output_definitions]
    assert ids == [f"CDC-E2E-OUTPUT-0{n}" for n in range(1, 6)]
    for definition in projection.output_definitions:
        assert definition["official_status"] == "NOT_AUTHORIZED_AS_OFFICIAL"


# 7 --------------------------------------------------------------------------
def test_french_packet_partial_is_consumed_by_exact_field(projection: MissionProjection) -> None:
    """The exact frozen field name is bound; capability is not synthesized."""
    assert projection.french_packet["french_path_state"] == "PARTIAL"
    assert projection.french_packet["substantive_french_support_absent_at"]


# 8 --------------------------------------------------------------------------
def test_package_member_classification_is_complete(frozen: FrozenMissionInput) -> None:
    """Every declared member has exactly one role; no silent-unused member."""
    ledger = member_consumption_ledger(frozen)
    assert ledger["coverage"] == "14/14"
    assert ledger["silent_unused_members"] == 0
    assert ledger["self_excluded_manifest"]["path"] == "PACKAGE-MANIFEST.json"
    assert set(ledger["roles"].values()) <= {
        "EXECUTION_INPUT",
        "POST_EXECUTION_RENDER_INPUT",
        "GOVERNANCE_BINDING",
        "REFERENCE_ONLY",
        "EVALUATION_AID",
        "MANIFEST_INTEGRITY",
    }


# 9 --------------------------------------------------------------------------
def test_human_action_plan_exact_digest_is_bound(repo_root: Path) -> None:
    """The persisted plan matches the digest the module binds."""
    import hashlib

    plan = (
        repo_root
        / "veraxis/cdc-e2e-mission-001/preexecution"
        / "CDC-END-TO-END-MISSION-001-HUMAN-ACTION-PLAN-v0.1.json"
    )
    assert hashlib.sha256(plan.read_bytes()).hexdigest() == HUMAN_ACTION_PLAN_SHA256
    document = json.loads(plan.read_text())
    assert document["counts"] == {"disposition_targets": 9, "correction_targets": 1}
    assert document["candidate_digests_precomputed"] is False


# 10 -------------------------------------------------------------------------
def test_missing_disposition_after_stage_1_holds(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """Stage 1 terminates and holds; no transition, no draft eligibility."""
    _skip_unless_formation_authorized()
    stage_1 = form_stage_1_for_tests(
        projection, frozen, evaluator=_stub_evaluator, warrant_builder=_stub_warrant
    )
    assert stage_1.stage == "EVALUATION_AND_CANDIDATE_FORMATION_COMPLETE"
    assert stage_1.institutional_transition == "NONE"
    assert stage_1.draft_eligibility == "NONE"
    assert stage_1.official_handoff == "PROHIBITED"
    assert stage_1.human_disposition == "NOT_YET_SUPPLIED"
    with pytest.raises(HumanDispositionRequiredError, match="HOLD"):
        require_human_disposition(stage_1, {})


# 11 -------------------------------------------------------------------------
def test_candidate_digest_mismatch_is_rejected(
    projection: MissionProjection, frozen: FrozenMissionInput, action_plan: FrozenActionPlan
) -> None:
    """A disposition must bind the candidate Stage 1 actually formed."""
    _skip_unless_formation_authorized()
    stage_1 = form_stage_1_for_tests(
        projection, frozen, evaluator=_stub_evaluator, warrant_builder=_stub_warrant
    )
    chain_id = "P001xC-TENDER-01"
    base = disposition_for(stage_1, projection, chain_id, action_plan)
    with pytest.raises(CandidateBindingError, match="candidate_digest"):
        bind_disposition_at(
            stage_1,
            {**base, "candidate_digest": "0" * 64},
            projection=projection,
            action_plan=action_plan,
        )
    observed = stage_1.candidate_digests()[chain_id]
    bound = bind_disposition_at(stage_1, base, projection=projection, action_plan=action_plan)
    assert bound["candidate_digest"] == observed


# 12 -------------------------------------------------------------------------
def test_correction_predecessor_mismatch_is_rejected() -> None:
    """A correction binds the actual predecessor and must not mutate it."""
    predecessor = {"ebawu_id": "EBAWU-P-001-C-TENDER-01", "state": "ACCEPTED_CANDIDATE"}
    correction = {
        "new_ebawu_or_successor_id": "EBAWU-P-001-C-TENDER-01-S2",
        "new_candidate_digest": "1" * 64,
        "correction_reason": "synthetic correction stimulus",
        "changed_fact_or_control_refs": ["EVB-P-001-C-TENDER-01"],
        "new_state": "QUALIFIED",
        "correction_event_id": "CORR-EVT-001",
        "predecessor_digest": "0" * 64,
    }
    with pytest.raises(PredecessorBindingError):
        bind_correction(predecessor, correction)

    from oic.cdc_e2e_mission import sha256 as canonical_sha256

    correction["predecessor_digest"] = canonical_sha256(predecessor)
    record = bind_correction(predecessor, correction)
    assert record["predecessor_before_digest"] == record["predecessor_after_digest"]
    assert record["predecessor_mutated"] is False


# 13 -------------------------------------------------------------------------
def test_observation_producer_covers_m01_to_m12(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """Twelve observations, no adjudication vocabulary."""
    produced = observation_producer(projection, frozen)
    assert produced["coverage"] == "12/12"
    assert set(produced["observations"]) == set(OBSERVATION_IDS)
    assert produced["adjudication_present"] is False
    blob = json.dumps(produced)
    for token in ("SEMANTIC_VIOLATION", "FORBIDDEN_PROMOTION", "PRECONDITION_MISMATCH"):
        assert token not in blob, token


# 14 -------------------------------------------------------------------------
def test_result_interlock_without_exact_clearance_is_rejected(
    projection: MissionProjection, frozen: FrozenMissionInput, action_plan: FrozenActionPlan
) -> None:
    """Stage-2 continuation refuses without every exact binding."""
    _skip_unless_formation_authorized()
    empty = ExecutionClearance(None, None, None, None, None, None, None)
    stage_1 = form_stage_1_for_tests(
        projection, frozen, evaluator=_stub_evaluator, warrant_builder=_stub_warrant
    )
    with pytest.raises(ResultBearingMissionBlockedError, match="missing result-bearing clearance"):
        require_stage_2_clearance(
            empty,
            STUB_RUNTIME,
            projection,
            frozen,
            stage_1=stage_1,
            dispositions={},
            action_plan=action_plan,
            stage_2_bindings={},
        )
    with pytest.raises(
        ResultBearingMissionBlockedError, match="not produced under owner clearance"
    ):
        require_stage_2_clearance(
            exact_clearance(),
            STUB_RUNTIME,
            projection,
            frozen,
            stage_1=stage_1,
            dispositions={},
            action_plan=action_plan,
            stage_2_bindings={},
        )


# denominator ----------------------------------------------------------------
def test_denominator_survives_individual_chain_failure(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """An early failure must not erase the remaining population."""
    _skip_unless_formation_authorized()

    def failing(
        member: Mapping[str, Any], control: Mapping[str, Any], evidence: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        del control, evidence
        if member["control_ref"] == "C-EVAL-01":
            raise RuntimeError("injected component failure")
        return _stub_evaluator(member, member, member)

    stage_1 = form_stage_1_for_tests(
        projection, frozen, evaluator=failing, warrant_builder=_stub_warrant
    )
    assert sum(stage_1.accounting.values()) == EXPECTED_CHAIN_COUNT
    assert set(stage_1.accounting) == set(DENOMINATOR_STATES)
    assert stage_1.accounting["non_evaluable"] == 3
    assert stage_1.accounting["completed"] == 6


def test_historical_governance_field_is_not_normalized(projection: MissionProjection) -> None:
    """The pre-binding snapshot is preserved and marked non-controlling."""
    historical = projection.historical_governance_field
    assert historical["observed_value"] == "PENDING_FROZEN_GOVERNANCE_INPUT"
    assert historical["status"] == "PRE_BINDING_CONSTRUCTION_SNAPSHOT"
    assert historical["controlling"] is False
    assert historical["normalized_or_rewritten"] is False
    assert projection.governance_binding["binding_state"] == "FROZEN_GOVERNANCE_BOUND"


def test_stage_1_observation_digest_is_stable(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """The Stage-1 checkpoint digest is deterministic over identical inputs."""
    _skip_unless_formation_authorized()
    first = form_stage_1_for_tests(
        projection, frozen, evaluator=_stub_evaluator, warrant_builder=_stub_warrant
    )
    second = form_stage_1_for_tests(
        projection, frozen, evaluator=_stub_evaluator, warrant_builder=_stub_warrant
    )
    assert first.digest() == second.digest()
