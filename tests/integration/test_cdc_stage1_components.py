"""Stage-1 governed component tests for CDC-END-TO-END-MISSION-001.

Every semantic test here runs on explicitly non-mission fixtures under
``mission_id = UNIT-TEST-NONMISSION`` with ``T-00x`` procedure identities that
cannot be confused with P001/P002/P003 mission output. No test in this module
produces the mission's actual nine outcomes; the interlock that makes that
structural is itself asserted below, and no artifact produced here is reusable
as a CDC mission result.

The implementation authorization covers building and testing these components.
It does not authorize Stage-1 result-bearing execution, Stage 2, human
disposition, transition evaluation or adjudication.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_e2e_support import (
    COMPONENT_PROFILE_RELPATH,
    PACKAGE_RELPATH,
    STUB_RUNTIME,
    exact_clearance,
)

from oic import cdc_e2e_mission
from oic.cdc_e2e_mission import (
    FALLBACK_WARRANT_CLASS,
    FROZEN_MISSION_MANIFEST_SHA256,
    FROZEN_MISSION_PACKAGE_BYTES,
    FROZEN_MISSION_PACKAGE_SHA256,
    NO_ZTL_DERIVATION,
    ON_UNKNOWN_NON_APPLICATION_REASON,
    REASON_ALL_SATISFIED,
    REASON_CONFLICTING,
    REASON_MISSING,
    REASON_NOT_SATISFIED,
    STAGE_1_COMPONENT_PROFILE_SHA256,
    VERDICT_BREACH,
    VERDICT_SATISFIED,
    VERDICT_UNRESOLVED,
    ComponentProfileProvenanceError,
    ExecutionClearance,
    FrozenComponentProfile,
    FrozenMissionInput,
    MissionContractError,
    MissionPopulationExecutionBlockedError,
    MissionProjection,
    PreconditionMismatchError,
    ResultBearingMissionBlockedError,
    build_fallback_warrant,
    evaluate_control,
    execute_authorized_stage_1,
    governed_stage_1_components,
    project_frozen_mission,
    require_evidence_matches_preregistered_assignments,
    require_result_clearance,
    require_verified_component_profile,
    verify_frozen_component_profile,
    verify_frozen_mission_input,
)

NONMISSION_ID = "UNIT-TEST-NONMISSION"
TENDER_FACTS = ("competition_notice_published", "minimum_competition_period_met")
EVAL_FACTS = ("scoring_record_complete", "declared_criteria_only")
AWARD_FACTS = ("award_traceable_to_scoring", "required_approvals_present")

HISTORICAL_STAGE_1_AUTHORIZATION = (
    "108703e871438b634931a088ba05e5f17c96ab3f330f7262c05b5679b3444aba"
)


@pytest.fixture
def profile(repo_root: Path) -> FrozenComponentProfile:
    """The component profile, verified from its exact bytes."""
    return verify_frozen_component_profile(repo_root / COMPONENT_PROFILE_RELPATH)


@pytest.fixture
def frozen(repo_root: Path) -> FrozenMissionInput:
    """input-v0.6, verified. Loading and validating it is permitted."""
    return verify_frozen_mission_input(repo_root / PACKAGE_RELPATH)


@pytest.fixture
def projection(frozen: FrozenMissionInput) -> MissionProjection:
    """The nine-chain projection. Projecting is not evaluating."""
    return project_frozen_mission(frozen)


def _control(control_id: str = "C-TENDER-01") -> dict[str, Any]:
    return {
        "control_id": control_id,
        "procedure_id": "T-001",
        "on_unknown": "ESCALATE",
        "decision_mode": "DETERMINISTIC",
    }


def _evidence(observations: list[dict[str, Any]]) -> dict[str, Any]:
    return {"evidence_bundle_id": "EVB-NONMISSION-T-001", "observations": observations}


def _admission() -> dict[str, Any]:
    return {"admission_id": "ADM-NONMISSION-T-001", "disposition": "ADMITTED"}


def _evaluate(
    profile: FrozenComponentProfile,
    observations: list[dict[str, Any]],
    control: dict[str, object] | None = None,
) -> dict[str, Any]:
    return evaluate_control(
        _control() if control is None else control,
        _evidence(observations),
        _admission(),
        profile=profile,
        mission_id=NONMISSION_ID,
    )


def _both(first: bool, second: bool) -> list[dict[str, Any]]:
    return [
        {"fact": TENDER_FACTS[0], "value": first},
        {"fact": TENDER_FACTS[1], "value": second},
    ]


# 1, 2 -- profile exact-byte verification ------------------------------------
def test_exact_profile_sha_mismatch_fails_closed(tmp_path: Path, repo_root: Path) -> None:
    """A profile whose digest differs is refused."""
    victim = tmp_path / "profile.json"
    victim.write_bytes((repo_root / COMPONENT_PROFILE_RELPATH).read_bytes() + b" ")
    with pytest.raises(ComponentProfileProvenanceError, match="digest is"):
        verify_frozen_component_profile(victim)


def test_profile_content_mutation_fails_before_semantic_use(
    tmp_path: Path, repo_root: Path
) -> None:
    """A rewritten rule never reaches interpretation.

    The mutated profile is semantically 'valid' JSON with a changed decision
    procedure. It is refused on bytes, so its rule is never parsed, let alone
    applied.
    """
    document = json.loads((repo_root / COMPONENT_PROFILE_RELPATH).read_bytes())
    document["decision_procedure"]["ordered_rules"][0]["verdict"] = VERDICT_BREACH
    victim = tmp_path / "profile.json"
    victim.write_bytes((json.dumps(document, indent=2, sort_keys=True) + "\n").encode())
    with pytest.raises(ComponentProfileProvenanceError, match="digest is"):
        verify_frozen_component_profile(victim)


def test_a_mapping_is_not_the_profile() -> None:
    """A caller mapping carrying the digest label is refused."""
    with pytest.raises(ComponentProfileProvenanceError, match="is not the profile"):
        require_verified_component_profile({"sha256": STAGE_1_COMPONENT_PROFILE_SHA256})


# 3, 4, 5, 6 -- package verification -----------------------------------------
def test_v0_6_member_byte_mutation_fails(tmp_path: Path, repo_root: Path) -> None:
    """One altered member byte breaks verification."""
    copy = tmp_path / "pkg"
    shutil.copytree(repo_root / PACKAGE_RELPATH, copy)
    victim = copy / "02-POPULATION/P002.json"
    victim.write_bytes(victim.read_bytes() + b" ")
    with pytest.raises(MissionContractError, match="member identity mismatch"):
        verify_frozen_mission_input(copy)


def test_manifest_member_identity_mismatch_fails(tmp_path: Path, repo_root: Path) -> None:
    """A manifest that misdescribes a member is refused."""
    copy = tmp_path / "pkg"
    shutil.copytree(repo_root / PACKAGE_RELPATH, copy)
    manifest = json.loads((copy / "PACKAGE-MANIFEST.json").read_bytes())
    manifest["members"][0]["sha256"] = "0" * 64
    (copy / "PACKAGE-MANIFEST.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    )
    with pytest.raises(MissionContractError, match="member identity mismatch"):
        verify_frozen_mission_input(copy)


def test_published_aggregate_digest_reproduces(frozen: FrozenMissionInput) -> None:
    """The published rule yields 3921 / b62f3966… on input-v0.6."""
    manifest = json.loads((frozen.root / "PACKAGE-MANIFEST.json").read_bytes())
    identities = [
        {"path": m["path"], "bytes": m["bytes"], "sha256": m["sha256"], "sha512": m["sha512"]}
        for m in manifest["members"]
    ]
    serialized = json.dumps(identities, sort_keys=True, ensure_ascii=False).encode()
    assert len(serialized) == 3921
    assert hashlib.sha256(serialized).hexdigest() == FROZEN_MISSION_PACKAGE_SHA256
    assert frozen.package_sha256 == FROZEN_MISSION_PACKAGE_SHA256
    assert frozen.manifest_sha256 == FROZEN_MISSION_MANIFEST_SHA256
    assert frozen.package_bytes == FROZEN_MISSION_PACKAGE_BYTES


def test_member_verification_happens_in_addition_to_the_aggregate_digest(
    tmp_path: Path, repo_root: Path
) -> None:
    """A package can satisfy the aggregate digest and still be refused.

    Here the manifest is left untouched, so the declared identities -- and
    therefore the aggregate digest -- still reproduce exactly. Only a member's
    bytes were changed. If the aggregate digest were treated as sufficient this
    would pass; member-byte verification is what catches it.
    """
    copy = tmp_path / "pkg"
    shutil.copytree(repo_root / PACKAGE_RELPATH, copy)
    victim = copy / "05-FRENCH/french-packet.json"
    victim.write_bytes(victim.read_bytes().replace(b"PARTIAL", b"COMPLETE", 1))
    manifest = json.loads((copy / "PACKAGE-MANIFEST.json").read_bytes())
    identities = [
        {"path": m["path"], "bytes": m["bytes"], "sha256": m["sha256"], "sha512": m["sha512"]}
        for m in manifest["members"]
    ]
    unchanged_aggregate = hashlib.sha256(
        json.dumps(identities, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    assert unchanged_aggregate == FROZEN_MISSION_PACKAGE_SHA256
    with pytest.raises(MissionContractError, match="member identity mismatch"):
        verify_frozen_mission_input(copy)


# 7, 8, 9 -- evidence-source boundary ----------------------------------------
def test_package_evidence_conforms_to_the_preregistered_assignments(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """All nine chains match the frozen constraint; it is a check, not a source."""
    report = require_evidence_matches_preregistered_assignments(projection, profile)
    assert report["constraint"] == "PREEXECUTION_CONFORMANCE_CONSTRAINT_ONLY"
    assert report["assignments_are_runtime_evidence"] is False
    assert report["fallback_to_profile_assignments"] is False
    assert report["runtime_evidence_source"] == "input-v0.6 evidence_bundle"
    assert len(report["chains_checked"]) == 9


def _projection_with_evidence(
    projection: MissionProjection, chain_id: str, observations: list[dict[str, Any]]
) -> MissionProjection:
    import dataclasses

    chains = []
    for chain in projection.chains:
        if chain.chain_id != chain_id:
            chains.append(chain)
            continue
        evidence = {**chain.execution_input["evidence_bundle"], "observations": observations}
        chains.append(
            dataclasses.replace(
                chain, execution_input={**chain.execution_input, "evidence_bundle": evidence}
            )
        )
    return dataclasses.replace(projection, chains=tuple(chains))


def test_profile_assignment_mismatch_with_package_evidence_fails_closed(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """Divergence between package evidence and the constraint is fail-closed."""
    drifted = _projection_with_evidence(projection, "P001xC-TENDER-01", _both(True, False))
    with pytest.raises(PreconditionMismatchError, match="PRECONDITION_MISMATCH_FAIL_CLOSED"):
        require_evidence_matches_preregistered_assignments(drifted, profile)


def test_profile_assignment_cannot_fill_missing_package_evidence(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """An absent fact stays absent: the constraint is never read in its place."""
    stripped = _projection_with_evidence(
        projection, "P001xC-TENDER-01", [{"fact": TENDER_FACTS[0], "value": True}]
    )
    with pytest.raises(PreconditionMismatchError):
        require_evidence_matches_preregistered_assignments(stripped, profile)
    # And the evaluator sees the absence rather than the preregistered value.
    record = _evaluate(profile, [{"fact": TENDER_FACTS[0], "value": True}])
    assert record["verdict"] == VERDICT_UNRESOLVED
    assert record["reason_code"] == REASON_MISSING
    assert record["observed_required_facts"][TENDER_FACTS[1]] == []


def test_profile_assignment_cannot_resolve_conflicting_package_evidence(
    profile: FrozenComponentProfile,
) -> None:
    """A conflict stays a conflict; the preregistered value does not break the tie."""
    record = _evaluate(
        profile,
        [
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[1], "value": True},
            {"fact": TENDER_FACTS[1], "value": False},
        ],
    )
    assert record["verdict"] == VERDICT_UNRESOLVED
    assert record["reason_code"] == REASON_CONFLICTING
    assert sorted(record["observed_required_facts"][TENDER_FACTS[1]]) == [False, True]


# 10 -- no coercion -----------------------------------------------------------
@pytest.mark.parametrize("value", ["true", "false", 0, 1, None, [], {}, 1.0])
def test_non_boolean_observation_fails_closed_with_no_coercion(
    profile: FrozenComponentProfile, value: object
) -> None:
    """Only JSON booleans are admitted. 0 and 1 are refused, not read as bools."""
    with pytest.raises(PreconditionMismatchError, match="PRECONDITION_MISMATCH_FAIL_CLOSED"):
        _evaluate(
            profile,
            [{"fact": TENDER_FACTS[0], "value": value}, {"fact": TENDER_FACTS[1], "value": True}],
        )


# 11-15 -- the four rules and their order ------------------------------------
def test_missing_required_fact_is_unresolved(profile: FrozenComponentProfile) -> None:
    """Absence is not false."""
    record = _evaluate(profile, [{"fact": TENDER_FACTS[0], "value": True}])
    assert (record["verdict"], record["reason_code"]) == (VERDICT_UNRESOLVED, REASON_MISSING)


def test_conflicting_required_fact_is_unresolved(profile: FrozenComponentProfile) -> None:
    """Conflict is not resolved by precedence or recency."""
    record = _evaluate(
        profile,
        [
            {"fact": TENDER_FACTS[0], "value": False},
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[1], "value": True},
        ],
    )
    assert (record["verdict"], record["reason_code"]) == (VERDICT_UNRESOLVED, REASON_CONFLICTING)


def test_all_required_facts_true_is_satisfied(profile: FrozenComponentProfile) -> None:
    """Rule 3."""
    record = _evaluate(profile, _both(True, True))
    assert (record["verdict"], record["reason_code"]) == (VERDICT_SATISFIED, REASON_ALL_SATISFIED)


def test_present_unconflicted_false_is_breach(profile: FrozenComponentProfile) -> None:
    """Rule 4."""
    record = _evaluate(profile, _both(True, False))
    assert (record["verdict"], record["reason_code"]) == (VERDICT_BREACH, REASON_NOT_SATISFIED)
    assert record["reason_detail_facts"] == [TENDER_FACTS[1]]


def test_missing_and_conflict_cannot_fall_through_into_breach(
    profile: FrozenComponentProfile,
) -> None:
    """Ordering test: a false fact alongside absence or conflict still resolves UNRESOLVED.

    If the rules were evaluated in any other order -- or if absence were read as
    false -- both of these would return BREACH.
    """
    absent_and_false = _evaluate(profile, [{"fact": TENDER_FACTS[1], "value": False}])
    assert absent_and_false["verdict"] == VERDICT_UNRESOLVED
    assert absent_and_false["reason_code"] == REASON_MISSING

    conflict_and_false = _evaluate(
        profile,
        [
            {"fact": TENDER_FACTS[0], "value": False},
            {"fact": TENDER_FACTS[1], "value": True},
            {"fact": TENDER_FACTS[1], "value": False},
        ],
    )
    assert conflict_and_false["verdict"] == VERDICT_UNRESOLVED
    assert conflict_and_false["reason_code"] == REASON_CONFLICTING


def test_every_control_vocabulary_is_the_frozen_one(profile: FrozenComponentProfile) -> None:
    """Three control-specific vocabularies, recovered from the profile bytes."""
    assert profile.facts_for("C-TENDER-01") == TENDER_FACTS
    assert profile.facts_for("C-EVAL-01") == EVAL_FACTS
    assert profile.facts_for("C-AWARD-01") == AWARD_FACTS
    with pytest.raises(PreconditionMismatchError, match="no required facts"):
        profile.facts_for("C-NOT-DESIGNATED")


# 16 -- distinct interface ----------------------------------------------------
def test_evaluator_receives_three_distinct_inputs() -> None:
    """The interface names three inputs and the Stage-1 path passes three."""
    signature = list(inspect.signature(evaluate_control).parameters)
    assert signature[:3] == ["admitted_control", "evidence_bundle", "admission_record"]
    source = inspect.getsource(cdc_e2e_mission._form_stage_1)
    assert "evaluator(admitted_control, evidence_bundle, admission_record)" in source
    assert "evaluator(\n                chain.execution_input, chain.execution_input" not in source


def test_the_three_inputs_are_semantically_distinct(profile: FrozenComponentProfile) -> None:
    """Each of the three contributes something no other one carries."""
    record = evaluate_control(
        _control(),
        _evidence(_both(True, True)),
        _admission(),
        profile=profile,
        mission_id=NONMISSION_ID,
    )
    assert record["control_id"] == "C-TENDER-01"  # from admitted_control
    assert record["evidence_bundle_ref"] == "EVB-NONMISSION-T-001"  # from evidence_bundle
    assert record["admission_record_ref"] == "ADM-NONMISSION-T-001"  # from admission_record


# 17-20 -- on_unknown is observed, never applied ------------------------------
def test_on_unknown_is_observed_but_not_applied(profile: FrozenComponentProfile) -> None:
    """ESCALATE is preserved metadata and non-operative at Stage 1."""
    for observations in (_both(True, True), [{"fact": TENDER_FACTS[0], "value": True}]):
        record = _evaluate(profile, observations)
        assert record["on_unknown_observed"] == "ESCALATE"
        assert record["on_unknown_applied"] is False
        assert record["non_application_reason"] == ON_UNKNOWN_NON_APPLICATION_REASON


def test_evaluator_emits_no_disposition(profile: FrozenComponentProfile) -> None:
    """No machine disposition, under any branch."""
    for observations in (
        _both(True, True),
        _both(True, False),
        [{"fact": TENDER_FACTS[0], "value": True}],
        [
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[1], "value": True},
            {"fact": TENDER_FACTS[1], "value": False},
        ],
    ):
        record = _evaluate(profile, observations)
        assert record["machine_disposition"] is None
        assert "disposition" not in {key for key in record if key not in {"machine_disposition"}}


def test_evaluator_cannot_emit_escalate(profile: FrozenComponentProfile) -> None:
    """ESCALATE is never a verdict, even where on_unknown says ESCALATE."""
    for observations in (
        _both(True, True),
        _both(False, False),
        [{"fact": TENDER_FACTS[0], "value": True}],
        [
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[0], "value": False},
            {"fact": TENDER_FACTS[1], "value": True},
        ],
    ):
        record = _evaluate(profile, observations)
        assert record["verdict"] in {VERDICT_SATISFIED, VERDICT_BREACH, VERDICT_UNRESOLVED}
        assert record["verdict"] != "ESCALATE"
        assert record["reason_code"] != "ESCALATE"


def test_no_machine_path_triggers_apply_test_disposition(
    profile: FrozenComponentProfile,
) -> None:
    """Neither component mentions or reaches the transition event type."""
    record = _evaluate(profile, [{"fact": TENDER_FACTS[0], "value": True}])
    _, warrant = build_fallback_warrant(record, profile=profile)
    blob = json.dumps([record, warrant])
    assert "APPLY_TEST_DISPOSITION" not in blob
    for function in (evaluate_control, build_fallback_warrant):
        assert "APPLY_TEST_DISPOSITION" not in inspect.getsource(function)
        assert "emit_transition_event" not in inspect.getsource(function)


# 21-24 -- fallback warrant ---------------------------------------------------
def test_fallback_warrant_fixed_fields_are_exact(profile: FrozenComponentProfile) -> None:
    """Every fixed value and every required field, checked by name."""
    record = _evaluate(profile, _both(True, True))
    warrant_class, warrant = build_fallback_warrant(record, profile=profile)
    assert warrant_class == FALLBACK_WARRANT_CLASS
    assert warrant["warrant_class"] == "FALLBACK_WARRANT"
    assert warrant["logical_warrant_status"] == "NOT_ESTABLISHED"
    assert warrant["ztl_kernel_invoked"] is False
    assert warrant["fallback_basis"] == "DETERMINISTIC_EVALUATION_RECORD"
    assert set(warrant) == {
        "warrant_id",
        "warrant_class",
        "mission_id",
        "procedure_id",
        "control_id",
        "evaluation_id",
        "evaluation_digest",
        "evaluation_verdict",
        "logical_warrant_status",
        "ztl_kernel_invoked",
        "fallback_basis",
        "limitations",
    }
    assert warrant["evaluation_digest"] == record["evaluation_digest"]


def test_fallback_warrant_always_carries_no_ztl_derivation(
    profile: FrozenComponentProfile,
) -> None:
    """The limitation is present on every branch."""
    for observations in (
        _both(True, True),
        _both(True, False),
        [{"fact": TENDER_FACTS[0], "value": True}],
    ):
        record = _evaluate(profile, observations)
        _, warrant = build_fallback_warrant(record, profile=profile)
        assert NO_ZTL_DERIVATION in warrant["limitations"]


def test_fallback_warrant_carries_no_ztl_digest_and_invokes_no_ztl(
    profile: FrozenComponentProfile,
) -> None:
    """No ZTL field, no ZTL claim, no ZTL import."""
    record = _evaluate(profile, _both(True, True))
    _, warrant = build_fallback_warrant(record, profile=profile)
    assert not [key for key in warrant if "ztl" in key.lower() and key != "ztl_kernel_invoked"]
    assert "ztl_warrant_digest" not in warrant
    assert warrant["logical_warrant_status"] == "NOT_ESTABLISHED"
    source = inspect.getsource(build_fallback_warrant)
    for token in ("import ztl", "kernel(", "ztl_warrant_digest"):
        assert token not in source
    assert "ztl_kernel_invoked" in source


def test_unresolved_cannot_be_promoted_by_the_warrant_builder(
    profile: FrozenComponentProfile,
) -> None:
    """UNRESOLVED survives the warrant unchanged."""
    for observations in (
        [{"fact": TENDER_FACTS[0], "value": True}],
        [
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[1], "value": True},
            {"fact": TENDER_FACTS[1], "value": False},
        ],
    ):
        record = _evaluate(profile, observations)
        assert record["verdict"] == VERDICT_UNRESOLVED
        _, warrant = build_fallback_warrant(record, profile=profile)
        assert warrant["evaluation_verdict"] == VERDICT_UNRESOLVED
        assert warrant["logical_warrant_status"] == "NOT_ESTABLISHED"


# 25, 26 -- reference-only and design labels cannot enter ---------------------
def test_reference_only_results_cannot_enter_the_components(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """input-v0.6 carries no result objects, and the evaluator reads none.

    A control salted with a historical evaluation, warrant and candidate still
    produces a record derived only from the required facts.
    """
    for chain in projection.chains:
        assert chain.reference_only == {}
        for field in ("deterministic_evaluation", "warrant_artifact", "candidate"):
            assert field not in chain.execution_input

    salted = {
        **_control(),
        "deterministic_evaluation": {"verdict": VERDICT_SATISFIED},
        "warrant_artifact": {"warrant_id": "ZTL-SHOULD-NOT-BE-READ"},
        "candidate": {"candidate_id": "CAND-SHOULD-NOT-BE-READ"},
    }
    record = evaluate_control(
        salted,
        _evidence(_both(True, False)),
        _admission(),
        profile=profile,
        mission_id=NONMISSION_ID,
    )
    assert record["verdict"] == VERDICT_BREACH
    blob = json.dumps(record)
    assert "ZTL-SHOULD-NOT-BE-READ" not in blob
    assert "CAND-SHOULD-NOT-BE-READ" not in blob


def test_design_shape_labels_cannot_enter_the_components(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """A shape label on the control changes nothing and is not carried through."""
    for chain in projection.chains:
        assert "shape" not in chain.execution_input
    salted = {**_control(), "shape": "CLEAN"}
    clean = _evaluate(profile, _both(True, False))
    salted_record = evaluate_control(
        salted,
        _evidence(_both(True, False)),
        _admission(),
        profile=profile,
        mission_id=NONMISSION_ID,
    )
    assert salted_record["verdict"] == clean["verdict"] == VERDICT_BREACH
    assert "CLEAN" not in json.dumps(salted_record)


# 27, 28 -- clearance ---------------------------------------------------------
def test_clearance_rejects_missing_or_wrong_component_profile_digest() -> None:
    """The new binding fails closed on absent, empty and wrong."""
    for bad in (None, "", "0" * 64):
        clearance = ExecutionClearance(
            **{**exact_clearance().as_mapping(), "stage_1_component_profile_sha256": bad}
        )
        with pytest.raises(
            ResultBearingMissionBlockedError, match="stage_1_component_profile_sha256"
        ):
            require_result_clearance(
                clearance,
                STUB_RUNTIME,
                {"mission_package_sha256": FROZEN_MISSION_PACKAGE_SHA256},
            )
    assert exact_clearance().stage_1_component_profile_sha256 == STAGE_1_COMPONENT_PROFILE_SHA256


def test_historical_stage_1_authorization_is_not_reusable(repo_root: Path) -> None:
    """The old owner authorization cannot stand for this successor.

    It named implementation commit c37e82b7 and tree a531ac6f. This branch is a
    successor to that commit, so its identity no longer matches, and the
    implementation delta itself is what invalidates it.
    """
    clearance = ExecutionClearance(
        **{
            **exact_clearance().as_mapping(),
            "owner_execution_authorization": f"sha256:{HISTORICAL_STAGE_1_AUTHORIZATION}",
        }
    )
    # The reference is accepted as a non-empty string -- the implementation never
    # authenticated the owner -- but it grants nothing: formation still refuses.
    require_result_clearance(
        clearance, STUB_RUNTIME, {"mission_package_sha256": FROZEN_MISSION_PACKAGE_SHA256}
    )
    freeze = json.loads(
        (
            repo_root
            / "veraxis/cdc-e2e-mission-001/preexecution"
            / "CDC-END-TO-END-MISSION-001-OWNER-SEMANTIC-PREIMPLEMENTATION-FREEZE-v0.1.json"
        ).read_bytes()
    )
    prior = freeze["authorization_boundaries"]["prior_stage_1_authorization"]
    assert prior["sha256"] == HISTORICAL_STAGE_1_AUTHORIZATION
    assert prior["state"] == "HISTORICAL_UNCONSUMED_AND_NON_REUSABLE"


# 29, 30 -- nothing result-bearing runs ---------------------------------------
def test_stage_1_over_the_frozen_population_is_blocked(
    projection: MissionProjection,
    profile: FrozenComponentProfile,
    frozen: FrozenMissionInput,
    repo_root: Path,
) -> None:
    """The mission's actual nine outcomes cannot be produced by this suite.

    Both routes refuse: the governed evaluator called directly on a mission
    chain, and the whole authorized Stage-1 path with any injected components.
    """
    evaluator, warrant_builder = governed_stage_1_components(
        profile, mission_id=cdc_e2e_mission.MISSION_ID
    )
    chain = projection.chains[0]
    with pytest.raises(MissionPopulationExecutionBlockedError):
        evaluator(
            chain.execution_input["admitted_control"],
            chain.execution_input["evidence_bundle"],
            chain.execution_input["admission_record"],
        )
    with pytest.raises(MissionPopulationExecutionBlockedError, match="not"):
        execute_authorized_stage_1(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            owner_interpretation=cdc_e2e_mission.verify_owner_preexecution_interpretation(
                repo_root / cdc_e2e_mission.OWNER_PREEXECUTION_INTERPRETATION_RELPATH
            ),
            evaluator=evaluator,
            warrant_builder=warrant_builder,
        )
    assert cdc_e2e_mission.MISSION_EXECUTION_AUTHORIZATION is None
    assert (
        cdc_e2e_mission.MISSION_POPULATION_EXECUTION_STATE
        == "AWAITING_FRESH_OWNER_EXECUTION_AUTHORIZATION"
    )


def test_a_stub_evaluator_cannot_bypass_the_interlock(
    projection: MissionProjection, frozen: FrozenMissionInput
) -> None:
    """The interlock sits above the injected components, not inside them."""

    def permissive(*_args: object) -> Mapping[str, Any]:
        raise AssertionError("an evaluator was reached over the mission population")

    def permissive_warrant(*_args: object) -> tuple[str, Mapping[str, Any]]:
        raise AssertionError("a warrant builder was reached over the mission population")

    with pytest.raises(MissionPopulationExecutionBlockedError):
        cdc_e2e_mission._form_stage_1(
            projection,
            frozen,
            evaluator=cast("Any", permissive),
            warrant_builder=cast("Any", permissive_warrant),
            authorization="TEST",
        )


def test_stage_2_remains_untouched_and_unexecuted(
    projection: MissionProjection, profile: FrozenComponentProfile, repo_root: Path
) -> None:
    """No Stage-2 path is reachable, and v0.6 cannot even furnish a proposal."""
    del profile
    chain = projection.chains[0]
    assert "prior_institutional_state" not in chain.execution_input
    with pytest.raises(MissionContractError, match="no prior_institutional_state"):
        cdc_e2e_mission._require_prior_institutional_state(chain)
    manifest = json.loads((repo_root / PACKAGE_RELPATH / "01-MISSION-MANIFEST.json").read_bytes())
    assert manifest["stage_1_input_state"] == "PRE_CANDIDATE"
    assert manifest["candidate_count"] == 0


# ---------------------------------------------------------------------------
# Mutation tests for the semantic promotion risks.
#
# Each mutation is applied to a *copy* of the component's logic or its inputs
# and must be observably rejected or produce a different result. A mutation
# that changes nothing is a hole in the guard, so each case asserts the
# unmutated behaviour first and then that the mutation cannot be reached.
# ---------------------------------------------------------------------------


def test_mutation_absence_read_as_false_would_change_the_verdict(
    profile: FrozenComponentProfile,
) -> None:
    """If absence were coerced to false the verdict would be BREACH, not UNRESOLVED."""
    observations = [{"fact": TENDER_FACTS[0], "value": True}]
    record = _evaluate(profile, observations)
    assert record["verdict"] == VERDICT_UNRESOLVED

    # The mutant: treat an absent fact as false.
    values = {TENDER_FACTS[0]: [True], TENDER_FACTS[1]: []}
    mutant = {fact: (vals or [False]) for fact, vals in values.items()}
    mutant_verdict = VERDICT_SATISFIED if all(v[0] for v in mutant.values()) else VERDICT_BREACH
    assert mutant_verdict == VERDICT_BREACH
    assert record["verdict"] != mutant_verdict


def test_mutation_conflict_resolved_by_precedence_would_change_the_verdict(
    profile: FrozenComponentProfile,
) -> None:
    """First-wins and last-wins both produce a verdict; the implementation produces neither."""
    observations = [
        {"fact": TENDER_FACTS[0], "value": True},
        {"fact": TENDER_FACTS[1], "value": True},
        {"fact": TENDER_FACTS[1], "value": False},
    ]
    record = _evaluate(profile, observations)
    assert record["verdict"] == VERDICT_UNRESOLVED
    assert record["reason_code"] == REASON_CONFLICTING
    first_wins = [True, True]
    last_wins = [True, False]
    assert (VERDICT_SATISFIED if all(first_wins) else VERDICT_BREACH) == VERDICT_SATISFIED
    assert (VERDICT_SATISFIED if all(last_wins) else VERDICT_BREACH) == VERDICT_BREACH
    assert record["verdict"] not in {VERDICT_SATISFIED, VERDICT_BREACH}


def test_mutation_non_boolean_falsy_coercion_is_not_performed(
    profile: FrozenComponentProfile,
) -> None:
    """bool(0) is False and bool("false") is True; neither is reachable."""
    assert bool(0) is False
    assert bool("false") is True
    for value in (0, "false"):
        with pytest.raises(PreconditionMismatchError):
            _evaluate(
                profile,
                [
                    {"fact": TENDER_FACTS[0], "value": value},
                    {"fact": TENDER_FACTS[1], "value": True},
                ],
            )


def test_mutation_on_unknown_cannot_become_a_machine_escalate(
    profile: FrozenComponentProfile,
) -> None:
    """Changing on_unknown does not change any evaluation output."""
    baseline = _evaluate(profile, [{"fact": TENDER_FACTS[0], "value": True}])
    for on_unknown in ("ESCALATE", "DENY", "ALLOW", None):
        record = _evaluate(
            profile,
            [{"fact": TENDER_FACTS[0], "value": True}],
            control={**_control(), "on_unknown": on_unknown},
        )
        assert record["verdict"] == baseline["verdict"] == VERDICT_UNRESOLVED
        assert record["on_unknown_applied"] is False
        assert record["on_unknown_observed"] == on_unknown
        assert record["machine_disposition"] is None


def test_mutation_fallback_warrant_cannot_become_ztl_like(
    profile: FrozenComponentProfile,
) -> None:
    """A profile that permits ZTL is refused by the builder rather than obeyed."""
    import dataclasses

    record = _evaluate(profile, _both(True, True))
    for mutant in (
        dataclasses.replace(profile, ztl_warrant_state="PERMITTED"),
        dataclasses.replace(profile, permitted_warrant_classes=("ZTL_WARRANT",)),
        dataclasses.replace(profile, permitted_warrant_classes=("FALLBACK_WARRANT", "ZTL_WARRANT")),
    ):
        with pytest.raises(ComponentProfileProvenanceError, match="does not recompute"):
            build_fallback_warrant(record, profile=mutant)


def test_mutation_profile_assignments_cannot_become_a_runtime_fallback(
    projection: MissionProjection, profile: FrozenComponentProfile
) -> None:
    """The conformance checker compares and refuses; it never supplies a value."""
    source = inspect.getsource(require_evidence_matches_preregistered_assignments)
    assert "PRECONDITION_MISMATCH_FAIL_CLOSED" in source
    stripped = _projection_with_evidence(
        projection, "P002xC-EVAL-01", [{"fact": EVAL_FACTS[0], "value": True}]
    )
    with pytest.raises(PreconditionMismatchError):
        require_evidence_matches_preregistered_assignments(stripped, profile)
    # The evaluator, given the same stripped evidence, still sees absence.
    record = evaluate_control(
        _control("C-EVAL-01"),
        _evidence([{"fact": EVAL_FACTS[0], "value": True}]),
        _admission(),
        profile=profile,
        mission_id=NONMISSION_ID,
    )
    assert record["verdict"] == VERDICT_UNRESOLVED
    assert record["reason_code"] == REASON_MISSING


def test_mutation_profile_hash_mismatch_is_never_accepted(tmp_path: Path, repo_root: Path) -> None:
    """Every entry point that takes a profile verifies it from bytes."""
    document = json.loads((repo_root / COMPONENT_PROFILE_RELPATH).read_bytes())
    document["controls"]["C-TENDER-01"]["required_facts"] = [TENDER_FACTS[0]]
    victim = tmp_path / "profile.json"
    victim.write_bytes((json.dumps(document, indent=2, sort_keys=True) + "\n").encode())
    with pytest.raises(ComponentProfileProvenanceError):
        verify_frozen_component_profile(victim)
    for entry in (evaluate_control, build_fallback_warrant, governed_stage_1_components):
        assert "require_verified_component_profile" in inspect.getsource(entry)
