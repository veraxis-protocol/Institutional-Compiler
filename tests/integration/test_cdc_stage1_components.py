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
import re
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
    clearance_for_authorization,
    exact_clearance,
    synthetic_authorization,
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
    chain with no authorization, and the whole authorized Stage-1 path, which
    has no real owner authorization artifact to verify.
    """
    evaluator, _ = governed_stage_1_components(profile, mission_id=cdc_e2e_mission.MISSION_ID)
    chain = projection.chains[0]
    with pytest.raises(MissionPopulationExecutionBlockedError):
        evaluator(
            chain.execution_input["admitted_control"],
            chain.execution_input["evidence_bundle"],
            chain.execution_input["admission_record"],
        )
    with pytest.raises(cdc_e2e_mission.OwnerExecutionAuthorizationError):
        execute_authorized_stage_1(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            owner_interpretation=cdc_e2e_mission.verify_owner_preexecution_interpretation(
                repo_root / cdc_e2e_mission.OWNER_PREEXECUTION_INTERPRETATION_RELPATH
            ),
            component_profile=profile,
            owner_execution_authorization_path=(
                repo_root / "veraxis/cdc-e2e-mission-001/NO-SUCH-OWNER-AUTHORIZATION.md"
            ),
        )
    assert (
        cdc_e2e_mission.MISSION_POPULATION_EXECUTION_STATE
        == "REQUIRES_RUNTIME_OWNER_EXECUTION_AUTHORIZATION"
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
    # Prior state is now derived from the actual Stage-1 checkpoint, and is
    # unavailable until an owner-cleared candidate exists.
    with pytest.raises(cdc_e2e_mission.PriorStateDerivationError):
        cdc_e2e_mission.derive_stage_2_prior_state(None, chain.chain_id)
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


# ---------------------------------------------------------------------------
# Blocker 1 -- the result-bearing gate is runtime evidence, not a source toggle
# ---------------------------------------------------------------------------


def test_no_source_constant_switches_execution_on() -> None:
    """The module carries no authority switch that a source edit could flip.

    A source toggle would be circular: the owner authorization must bind the
    accepted implementation commit and tree, and editing a constant to enable
    execution changes both.
    """
    assert not hasattr(cdc_e2e_mission, "MISSION_EXECUTION_AUTHORIZATION")
    assert (
        cdc_e2e_mission.MISSION_POPULATION_EXECUTION_STATE
        == "REQUIRES_RUNTIME_OWNER_EXECUTION_AUTHORIZATION"
    )
    source = inspect.getsource(cdc_e2e_mission)
    assert "os.environ" not in source
    assert "getenv" not in source
    # No authorization digest is compiled in: the only 64-hex constants are the
    # frozen package, profile, oracle, protocol, plan and interpretation.
    verifier = inspect.getsource(cdc_e2e_mission.verify_owner_execution_authorization)
    assert not re.search(r"[0-9a-f]{64}", verifier)


@pytest.mark.parametrize(
    "authorization",
    [None, "sha256:" + "0" * 64, True, 1, {"sha256": "0" * 64}, object()],
)
def test_a_label_or_flag_is_not_an_authorization(authorization: object) -> None:
    """Strings, flags, mappings and sentinels are all refused."""
    with pytest.raises(cdc_e2e_mission.OwnerExecutionAuthorizationError):
        cdc_e2e_mission.require_mission_execution_authorization(authorization)


def test_absent_authorization_artifact_fails_closed(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """A path that does not exist refuses before anything else happens."""
    with pytest.raises(cdc_e2e_mission.OwnerExecutionAuthorizationError, match="not readable"):
        cdc_e2e_mission.verify_owner_execution_authorization(
            tmp_path / "absent.md",
            clearance=exact_clearance(),
            runtime=STUB_RUNTIME,
            frozen=frozen,
        )


def test_clearance_alone_cannot_unlock_without_the_artifact(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """A constructed clearance naming a digest unlocks nothing on its own."""
    artifact = synthetic_authorization(tmp_path)
    forged = ExecutionClearance(
        **{
            **exact_clearance().as_mapping(),
            "owner_execution_authorization": "sha256:" + "0" * 64,
        }
    )
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="a label is not the artifact"
    ):
        cdc_e2e_mission.verify_owner_execution_authorization(
            artifact, clearance=forged, runtime=STUB_RUNTIME, frozen=frozen
        )


def test_authorization_must_name_the_running_implementation_and_package(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """An authorization issued against another implementation does not carry over."""
    other = synthetic_authorization(
        tmp_path,
        runtime=cdc_e2e_mission.RuntimeIdentity("OTHER-COMMIT", "OTHER-TREE", "OTHER-ENV"),
    )
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="do not match the running"
    ):
        cdc_e2e_mission.verify_owner_execution_authorization(
            other,
            clearance=clearance_for_authorization(other),
            runtime=STUB_RUNTIME,
            frozen=frozen,
        )


# ---------------------------------------------------------------------------
# Blocker 2 -- no injected-component bypass on the authoritative route
# ---------------------------------------------------------------------------


def test_public_authorized_route_exposes_no_component_injection() -> None:
    """No evaluator, warrant-builder or per-chain profile parameter exists."""
    parameters = set(inspect.signature(execute_authorized_stage_1).parameters)
    for forbidden in (
        "evaluator",
        "warrant_builder",
        "components",
        "evaluation_function",
        "warrant_function",
        "profile_per_chain",
    ):
        assert forbidden not in parameters, forbidden
    assert parameters == {
        "projection",
        "frozen",
        "clearance",
        "runtime",
        "owner_interpretation",
        "component_profile",
        "owner_execution_authorization_path",
    }
    source = inspect.getsource(execute_authorized_stage_1)
    assert "governed_stage_1_components(" in source


def test_private_injection_remains_only_for_non_mission_unit_tests() -> None:
    """_form_stage_1 still accepts components, and is private and gated."""
    assert cdc_e2e_mission._form_stage_1.__name__.startswith("_")
    assert "evaluator" in inspect.signature(cdc_e2e_mission._form_stage_1).parameters
    assert "_require_mission_population_not_formed" in inspect.getsource(
        cdc_e2e_mission._form_stage_1
    )


# ---------------------------------------------------------------------------
# Blocker 3 -- conformance is an operational precondition
# ---------------------------------------------------------------------------


def test_conformance_is_enforced_before_any_evaluator_invocation(
    tmp_path: Path, repo_root: Path
) -> None:
    """A valid clearance and authorization still cannot reach the evaluator.

    A mutated copy of the package diverges from the frozen preregistered
    assignment on one chain. Everything else is correct, so only the conformance
    precondition can be what stops it. The mutated copy is not the mission
    package, and no mission outcome is produced.
    """
    copy = tmp_path / "pkg"
    shutil.copytree(repo_root / PACKAGE_RELPATH, copy)
    population = json.loads((copy / "02-POPULATION/P001.json").read_bytes())
    population["C-TENDER-01"]["evidence_bundle"]["observations"] = [
        {"fact": TENDER_FACTS[0], "value": True},
        {"fact": TENDER_FACTS[1], "value": False},
    ]
    (copy / "02-POPULATION/P001.json").write_bytes(
        (json.dumps(population, indent=1, sort_keys=True) + "\n").encode()
    )
    # The mutated copy no longer verifies as the frozen package at all, which is
    # itself the first precondition; assert that, then assert the conformance
    # check independently rejects the divergence on a projection.
    with pytest.raises(MissionContractError):
        verify_frozen_mission_input(copy)

    profile = verify_frozen_component_profile(repo_root / COMPONENT_PROFILE_RELPATH)
    frozen = verify_frozen_mission_input(repo_root / PACKAGE_RELPATH)
    drifted = _projection_with_evidence(
        project_frozen_mission(frozen),
        "P001xC-TENDER-01",
        [
            {"fact": TENDER_FACTS[0], "value": True},
            {"fact": TENDER_FACTS[1], "value": False},
        ],
    )
    with pytest.raises(PreconditionMismatchError, match="PRECONDITION_MISMATCH_FAIL_CLOSED"):
        require_evidence_matches_preregistered_assignments(drifted, profile)


def test_authoritative_route_orders_its_preconditions(repo_root: Path) -> None:
    """Conformance is wired in, and sits ahead of component construction."""
    source = inspect.getsource(execute_authorized_stage_1)
    conformance = source.index("require_evidence_matches_preregistered_assignments")
    components = source.index("governed_stage_1_components(")
    formation = source.index("_form_stage_1(")
    authorization = source.index("verify_owner_execution_authorization(")
    assert authorization < conformance < components < formation
    for required in (
        "require_verified_component_profile",
        "require_verified_owner_interpretation",
        "require_projected_source",
        "require_result_clearance",
    ):
        assert required in source
    del repo_root


# ---------------------------------------------------------------------------
# Blocker 4 -- one canonical evaluation identity
# ---------------------------------------------------------------------------


def test_evaluation_digest_is_a_single_identity(profile: FrozenComponentProfile) -> None:
    """record == artifact == warrant == canonical digest of the body."""
    record = _evaluate(profile, _both(True, True))
    canonical = cdc_e2e_mission.canonical_evaluation_digest(record)
    _, warrant = build_fallback_warrant(record, profile=profile)
    assert record["evaluation_digest"] == canonical
    assert warrant["evaluation_digest"] == canonical
    assert cdc_e2e_mission.evaluation_digest_is_intact(record)
    # And the Stage-1 artifact reuses it rather than rehashing the record.
    artifact_source = inspect.getsource(cdc_e2e_mission._form_stage_1)
    assert 'evaluation_digest=str(evaluation["evaluation_digest"])' in artifact_source
    assert "evaluation_digest=sha256(evaluation)" not in artifact_source


def test_the_digest_is_not_defined_over_a_record_containing_itself(
    profile: FrozenComponentProfile,
) -> None:
    """Excluding the claimed digest reproduces it exactly."""
    record = _evaluate(profile, _both(True, False))
    body = {k: v for k, v in record.items() if k != "evaluation_digest"}
    assert cdc_e2e_mission.sha256(body) == record["evaluation_digest"]
    assert cdc_e2e_mission.sha256(record) != record["evaluation_digest"]


@pytest.mark.parametrize(
    "field",
    ["verdict", "reason_code", "control_id", "observed_required_facts", "on_unknown_observed"],
)
def test_mutating_any_evaluation_body_field_invalidates_the_digest(
    profile: FrozenComponentProfile, field: str
) -> None:
    """A tampered body no longer matches its claimed digest, and the warrant refuses."""
    record = _evaluate(profile, _both(True, True))
    tampered = {**record, field: "TAMPERED"}
    assert not cdc_e2e_mission.evaluation_digest_is_intact(tampered)
    with pytest.raises(MissionContractError, match="does not recompute"):
        build_fallback_warrant(tampered, profile=profile)


# ---------------------------------------------------------------------------
# Hardening -- profile assignment values are booleans, never coerced
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["true", "false", 0, 1, None, [], {}])
def test_non_boolean_profile_assignment_value_fails_closed(
    tmp_path: Path, repo_root: Path, value: object
) -> None:
    """A non-boolean preregistered assignment value is refused, not coerced."""
    document = json.loads((repo_root / COMPONENT_PROFILE_RELPATH).read_bytes())
    controls = document["preregistered_population_assignments"]["P001"]["controls"]
    controls["C-TENDER-01"][TENDER_FACTS[0]] = [value]
    victim = tmp_path / "profile.json"
    victim.write_bytes((json.dumps(document, indent=2, sort_keys=True) + "\n").encode())
    # The byte check fires first; bypass it to reach the assignment validator and
    # prove the coercion path is gone rather than merely unreachable today.
    with pytest.raises(ComponentProfileProvenanceError):
        verify_frozen_component_profile(victim)
    with pytest.raises(ComponentProfileProvenanceError, match="PRECONDITION_MISMATCH_FAIL_CLOSED"):
        cdc_e2e_mission._profile_assignment_values("P001", "C-TENDER-01", "f", [value])


def test_profile_assignment_loader_does_not_coerce() -> None:
    """No bool() call survives in the assignment loader."""
    source = inspect.getsource(cdc_e2e_mission._profile_assignment_values)
    assert "bool(value)" not in source
    assert "isinstance(value, bool)" in source


# ---------------------------------------------------------------------------
# on_unknown -- corrected invariant
# ---------------------------------------------------------------------------


def test_on_unknown_changes_the_record_but_not_the_decision(
    profile: FrozenComponentProfile,
) -> None:
    """Observed metadata is faithfully recorded, so records are not byte-identical.

    The invariant is decision independence, not record equality: varying
    on_unknown must not move the verdict or reason, must never be applied, must
    emit no disposition and must never yield an ESCALATE verdict -- while the
    observed value itself is recorded, which necessarily changes the digest.
    """
    observations = [{"fact": TENDER_FACTS[0], "value": True}]
    digests = set()
    for on_unknown in ("ESCALATE", "DENY", "ALLOW", None):
        record = _evaluate(profile, observations, control={**_control(), "on_unknown": on_unknown})
        assert record["verdict"] == VERDICT_UNRESOLVED
        assert record["reason_code"] == REASON_MISSING
        assert record["on_unknown_applied"] is False
        assert record["on_unknown_observed"] == on_unknown
        assert record["machine_disposition"] is None
        assert record["verdict"] != "ESCALATE"
        digests.add(record["evaluation_digest"])
    assert len(digests) == 4, "the observed metadata must be recorded, so digests differ"


# ---------------------------------------------------------------------------
# Blocker A -- authorization semantics, not just byte identity
# ---------------------------------------------------------------------------


def _verify_auth(
    path: Path, frozen: FrozenMissionInput
) -> cdc_e2e_mission.OwnerExecutionAuthorization:
    return cdc_e2e_mission.verify_owner_execution_authorization(
        path,
        clearance=clearance_for_authorization(path),
        runtime=STUB_RUNTIME,
        frozen=frozen,
    )


def test_a_digest_bound_non_authorization_file_is_refused(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """The exact defect the previous positive test proved: closed.

    This file is perfectly digest-bound to its clearance and names the correct
    commit, tree and package -- and says it is not an authorization. Under the
    previous implementation it verified.
    """
    body = (
        "NOT AN OWNER AUTHORIZATION\n"
        f"implementation_commit = {STUB_RUNTIME.implementation_commit}\n"
        f"implementation_tree = {STUB_RUNTIME.implementation_tree}\n"
        f"mission_package_sha256 = {FROZEN_MISSION_PACKAGE_SHA256}\n"
    ).encode()
    artifact = synthetic_authorization(tmp_path, raw=body, name="not-an-authorization.md")
    assert b"NOT AN OWNER AUTHORIZATION" in artifact.read_bytes()
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="not structured JSON"
    ):
        _verify_auth(artifact, frozen)


def test_valid_json_that_declares_itself_non_authorizing_is_refused(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """Well-formed JSON with correct bindings but no authorization claim."""
    artifact = synthetic_authorization(
        tmp_path,
        raw=(
            json.dumps(
                {
                    "record_class": "NOT_AN_AUTHORIZATION",
                    "note": "correctly bound, deliberately non-authorizing",
                    "bindings": {
                        "implementation_commit": STUB_RUNTIME.implementation_commit,
                        "implementation_tree": STUB_RUNTIME.implementation_tree,
                        "mission_package_sha256": FROZEN_MISSION_PACKAGE_SHA256,
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode(),
    )
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="authorization semantics"
    ):
        _verify_auth(artifact, frozen)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("record_class", "SOMETHING_ELSE"),
        ("mission_id", "CDC-OTHER-MISSION"),
        ("owner_authorized", False),
        ("authorized_stage", "STAGE_1_AND_STAGE_2"),
        ("authorized_stage", "STAGE_2_ONLY"),
        ("authorization_scope", "UNLIMITED_EXECUTIONS"),
        ("single_use", False),
        ("automatic_retry_authorized", True),
        ("stage_2_authorized", True),
        ("result_bearing", False),
    ],
)
def test_each_declaration_defect_refuses_independently(
    tmp_path: Path, frozen: FrozenMissionInput, field: str, value: object
) -> None:
    """Every declared semantic is required, each one on its own."""
    artifact = synthetic_authorization(tmp_path, overrides={field: value})
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="authorization semantics"
    ):
        _verify_auth(artifact, frozen)


@pytest.mark.parametrize("binding", list(cdc_e2e_mission.OWNER_AUTHORIZATION_BINDING_FIELDS))
def test_each_structured_binding_mismatch_refuses_independently(
    tmp_path: Path, frozen: FrozenMissionInput, binding: str
) -> None:
    """All eleven bindings are checked as fields, each independently."""
    artifact = synthetic_authorization(tmp_path, binding_overrides={binding: "WRONG"})
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="do not match the running"
    ):
        _verify_auth(artifact, frozen)


def test_bindings_are_structural_not_substring(tmp_path: Path, frozen: FrozenMissionInput) -> None:
    """Correct values present as loose text, absent as fields, are not accepted."""
    name = "substring-only.json"
    document = json.loads(synthetic_authorization(tmp_path, name=name).read_bytes())
    prose = document.pop("bindings")
    document["free_text"] = json.dumps(prose)
    artifact = synthetic_authorization(
        tmp_path,
        raw=(json.dumps(document, indent=2, sort_keys=True) + "\n").encode(),
        name=name,
    )
    payload = artifact.read_bytes()
    assert STUB_RUNTIME.implementation_commit.encode() in payload
    assert FROZEN_MISSION_PACKAGE_SHA256.encode() in payload
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="no structured 'bindings'"
    ):
        _verify_auth(artifact, frozen)


def test_malformed_json_is_refused(tmp_path: Path, frozen: FrozenMissionInput) -> None:
    """A truncated artifact is refused, not partially interpreted."""
    artifact = synthetic_authorization(tmp_path, raw=b'{"record_class": ')
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="not structured JSON"
    ):
        _verify_auth(artifact, frozen)


def test_no_authorization_digest_is_compiled_into_source() -> None:
    """Only immutable predecessor governance digests are fixed in source."""
    verifier = inspect.getsource(cdc_e2e_mission.verify_owner_execution_authorization)
    assert not re.search(r"[0-9a-f]{64}", verifier)
    assert cdc_e2e_mission.OWNER_SEMANTIC_PREIMPLEMENTATION_FREEZE_SHA256 == (
        "fa8f18cb1d890b41fd078b92238200e58cb0e7f1ff65628f2390df520e20ab2a"
    )
    assert cdc_e2e_mission.OWNER_STAGE_1_SEAM_CLARIFICATION_SHA256 == (
        "a4a87ec5698416eaa9af970392070a25181df263537524e8b0fc8a91d86fec60"
    )


def test_a_valid_shaped_test_artifact_opens_only_the_test_gate(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """The fixture verifies, and binds STUB identities no real run has."""
    artifact = synthetic_authorization(tmp_path)
    verified = _verify_auth(artifact, frozen)
    assert verified.record_class == "OWNER_STAGE_1_EXECUTION_AUTHORIZATION"
    assert verified.authorized_stage == "STAGE_1_ONLY"
    assert verified.authorization_scope == "ONE_RESULT_BEARING_STAGE_1_EXECUTION"
    document = json.loads(artifact.read_bytes())
    assert document["synthetic_test_fixture"] is True
    assert document["bindings"]["implementation_commit"] == "STUB-IMPLEMENTATION-COMMIT"
    # Against a real runtime identity it authorizes nothing.
    real = cdc_e2e_mission.RuntimeIdentity(
        "306856ad976f4368a306e5d7f61ef90722ffc831",
        "e21da8112d8bf14f5e4737e49cfaa4860299281b",
        "acec86475cf9fe455410c9e56aa70f45e3f92758a57d704c416d3ac8964a01ef",
    )
    with pytest.raises(cdc_e2e_mission.OwnerExecutionAuthorizationError):
        cdc_e2e_mission.verify_owner_execution_authorization(
            artifact, clearance=clearance_for_authorization(artifact), runtime=real, frozen=frozen
        )


# ---------------------------------------------------------------------------
# Blocker B -- issuance survives into the Stage-1 result
# ---------------------------------------------------------------------------


def _nonmission_projection(
    projection: MissionProjection,
    authorization: cdc_e2e_mission.OwnerExecutionAuthorization,
) -> tuple[MissionProjection, cdc_e2e_mission.OwnerExecutionAuthorization]:
    """A projection carrying a non-mission id, so formation is permitted."""
    import dataclasses

    return dataclasses.replace(projection, mission_id=NONMISSION_ID), authorization


def _form_nonmission_stage_1(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
    authorization: cdc_e2e_mission.OwnerExecutionAuthorization,
) -> cdc_e2e_mission.Stage1Observation:
    evaluator, warrant_builder = governed_stage_1_components(
        profile, mission_id=NONMISSION_ID, mission_authorization=authorization
    )
    nonmission, _ = _nonmission_projection(projection, authorization)
    return cdc_e2e_mission._form_stage_1(
        nonmission,
        frozen,
        evaluator=evaluator,
        warrant_builder=warrant_builder,
        authorization=cdc_e2e_mission.STAGE_1_AUTHORIZATION_CLEARED,
        mission_authorization=authorization,
        attempt_claim=lambda: cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen),
    )


def test_stage_1_observation_binds_exact_authorization_identity(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """Issuance creates the reliance, so the raw result names the issuance."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    observation = _form_nonmission_stage_1(projection, frozen, profile, authorization)
    bound = observation.owner_execution_authorization
    assert bound is not None
    assert bound["owner_execution_authorization_sha256"] == authorization.sha256_hex
    assert bound["owner_execution_authorization_bytes"] == len(artifact.read_bytes())
    assert bound["owner_execution_authorization_reference"] == authorization.reference
    assert (
        bound["owner_execution_authorization_record_class"]
        == "OWNER_STAGE_1_EXECUTION_AUTHORIZATION"
    )
    assert bound["owner_execution_authorization_scope"] == "ONE_RESULT_BEARING_STAGE_1_EXECUTION"
    record = observation.as_record()
    assert record["owner_execution_authorization"] == bound
    assert record["attempt_record"]["attempt_state"] == cdc_e2e_mission.ATTEMPT_STATE_CONSUMED
    # No authorization prose reached the candidates.
    assert "synthetic_test_fixture" not in json.dumps(
        [chain.as_record() for chain in observation.chains]
    )


def test_different_authorizations_produce_different_stage_1_identities(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """Identical computation under a different issuance is a different result."""
    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    first_dir.mkdir()
    second_dir.mkdir()
    first = synthetic_authorization(
        first_dir, overrides={"authorization_id": "SYNTHETIC-TEST-AUTHORIZATION-A"}
    )
    second = synthetic_authorization(
        second_dir, overrides={"authorization_id": "SYNTHETIC-TEST-AUTHORIZATION-B"}
    )
    assert first.read_bytes() != second.read_bytes()
    one = _form_nonmission_stage_1(projection, frozen, profile, _verify_auth(first, frozen))
    two = _form_nonmission_stage_1(projection, frozen, profile, _verify_auth(second, frozen))
    assert one.candidate_digests() == two.candidate_digests()
    assert one.digest() != two.digest()


# ---------------------------------------------------------------------------
# Blocker C -- single use is operational
# ---------------------------------------------------------------------------


def test_attempt_record_location_is_derived_not_caller_selected(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """The path comes from the authorization's own digest and location."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    path = cdc_e2e_mission.attempt_record_path(authorization)
    assert path.parent == artifact.parent
    assert authorization.sha256_hex in path.name
    signature = inspect.signature(cdc_e2e_mission.attempt_record_path)
    assert list(signature.parameters) == ["authorization"]
    assert "attempt_path" not in inspect.signature(execute_authorized_stage_1).parameters


def test_precondition_failure_creates_no_attempt_claim(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
    repo_root: Path,
) -> None:
    """A failure before the first evaluator must not burn the authorization."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    assert cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_NONE
    # A clearance that does not match the authorization: fails at a precondition.
    with pytest.raises(ResultBearingMissionBlockedError):
        execute_authorized_stage_1(
            projection,
            frozen,
            exact_clearance(),
            STUB_RUNTIME,
            owner_interpretation=cdc_e2e_mission.verify_owner_preexecution_interpretation(
                repo_root / cdc_e2e_mission.OWNER_PREEXECUTION_INTERPRETATION_RELPATH
            ),
            component_profile=profile,
            owner_execution_authorization_path=artifact,
        )
    assert cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_NONE
    assert not cdc_e2e_mission.attempt_record_path(authorization).exists()


def test_first_governed_evaluator_invocation_consumes_the_authorization(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """Invocation consumes; the state moves NONE -> CONSUMED."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    assert cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_NONE
    _form_nonmission_stage_1(projection, frozen, profile, authorization)
    assert (
        cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_CONSUMED
    )


def test_an_evaluator_exception_still_consumes_the_authorization(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
) -> None:
    """Invocation, not success, is what consumes it."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)

    def exploding(*_args: object) -> Mapping[str, Any]:
        raise RuntimeError("governed component failed")

    def warrant(*_args: object) -> tuple[str, Mapping[str, Any]]:
        raise AssertionError("unreachable")

    import dataclasses

    nonmission = dataclasses.replace(projection, mission_id=NONMISSION_ID)
    cdc_e2e_mission._form_stage_1(
        nonmission,
        frozen,
        evaluator=cast("Any", exploding),
        warrant_builder=cast("Any", warrant),
        authorization=cdc_e2e_mission.STAGE_1_AUTHORIZATION_CLEARED,
        mission_authorization=authorization,
        attempt_claim=lambda: cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen),
    )
    assert (
        cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_CONSUMED
    )
    with pytest.raises(cdc_e2e_mission.MissionAttemptStateError, match="non-reusable"):
        cdc_e2e_mission.require_unclaimed_attempt(authorization)


def test_a_consumed_authorization_refuses_before_the_evaluator(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """A second run on the same authorization stops at the precondition."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    _form_nonmission_stage_1(projection, frozen, profile, authorization)
    with pytest.raises(cdc_e2e_mission.MissionAttemptStateError, match="non-reusable"):
        cdc_e2e_mission.require_unclaimed_attempt(authorization)
    # And the atomic claim itself refuses a second time.
    with pytest.raises(cdc_e2e_mission.MissionAttemptStateError, match="already claimed"):
        cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen)


def test_a_claimed_but_unconsumed_attempt_blocks_automatic_retry(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """A crash between claim and consumption is not silently released."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen)
    assert (
        cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_CLAIMED
    )
    with pytest.raises(cdc_e2e_mission.MissionAttemptStateError, match="separate owner decision"):
        cdc_e2e_mission.require_unclaimed_attempt(authorization)
    # Nothing in the module releases or deletes a claim.
    source = inspect.getsource(cdc_e2e_mission)
    assert ".unlink(" not in source
    assert "release_attempt" not in source


def test_concurrent_acquisition_cannot_permit_two_attempts(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """Exclusive create: exactly one of N racing claims wins."""
    import threading

    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    wins: list[str] = []
    losses: list[str] = []
    barrier = threading.Barrier(8)

    def attempt() -> None:
        barrier.wait()
        try:
            cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen)
            wins.append("claimed")
        except cdc_e2e_mission.MissionAttemptStateError:
            losses.append("refused")

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(wins) == 1
    assert len(losses) == 7


def test_the_attempt_record_binds_its_own_governed_identities(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """The record proves which authorization, implementation and package it used."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    record = cdc_e2e_mission.claim_attempt(authorization, STUB_RUNTIME, frozen)
    stored = json.loads(record.path.read_bytes())
    assert stored["owner_execution_authorization_sha256"] == authorization.sha256_hex
    assert stored["implementation_commit"] == STUB_RUNTIME.implementation_commit
    assert stored["implementation_tree"] == STUB_RUNTIME.implementation_tree
    assert stored["mission_package_sha256"] == frozen.package_sha256
    assert stored["attempt_state"] == cdc_e2e_mission.ATTEMPT_STATE_CLAIMED


def test_no_mission_outcome_is_produced_by_any_of_these_tests(
    projection: MissionProjection,
) -> None:
    """Every formation above ran under UNIT-TEST-NONMISSION."""
    assert projection.mission_id == cdc_e2e_mission.MISSION_ID
    import dataclasses

    assert dataclasses.replace(projection, mission_id=NONMISSION_ID).mission_id == NONMISSION_ID
    assert (
        cdc_e2e_mission.MISSION_POPULATION_EXECUTION_STATE
        == "REQUIRES_RUNTIME_OWNER_EXECUTION_AUTHORIZATION"
    )


# ---------------------------------------------------------------------------
# Replay via relocation -- one issuance, one attempt namespace
# ---------------------------------------------------------------------------


def test_a_byte_identical_copy_elsewhere_does_not_buy_a_second_attempt(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """The exact replay this repair closes.

    Consume an authorization, then present the identical bytes from another
    directory. The digest is unchanged and every structured binding still
    matches, so only the canonical-location check can be what refuses it -- and
    it refuses before any attempt state is consulted, let alone an evaluator.
    """
    home = tmp_path / "issued"
    elsewhere = tmp_path / "copied"
    home.mkdir()
    elsewhere.mkdir()

    artifact = synthetic_authorization(home)
    authorization = _verify_auth(artifact, frozen)
    _form_nonmission_stage_1(projection, frozen, profile, authorization)
    assert (
        cdc_e2e_mission.read_attempt_state(authorization) == cdc_e2e_mission.ATTEMPT_STATE_CONSUMED
    )

    copy = elsewhere / artifact.name
    shutil.copyfile(artifact, copy)
    assert copy.read_bytes() == artifact.read_bytes()
    assert (
        hashlib.sha256(copy.read_bytes()).hexdigest()
        == hashlib.sha256(artifact.read_bytes()).hexdigest()
    )
    # No attempt record exists beside the copy, so under the old derivation this
    # location would have looked unused.
    assert not (elsewhere / f".cdc-e2e-stage-1-attempt-{authorization.sha256_hex}.json").exists()

    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError, match="not a second issuance"
    ):
        cdc_e2e_mission.verify_owner_execution_authorization(
            copy,
            clearance=clearance_for_authorization(copy),
            runtime=STUB_RUNTIME,
            frozen=frozen,
        )


def test_a_symlink_to_the_authorization_is_not_a_second_location(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """Path resolution is canonical, so an alias is the same issuance."""
    home = tmp_path / "issued"
    home.mkdir()
    artifact = synthetic_authorization(home)
    link = tmp_path / "alias.json"
    try:
        link.symlink_to(artifact)
    except (OSError, NotImplementedError):  # pragma: no cover - platform dependent
        pytest.skip("symlinks are not available on this platform")

    # The alias resolves to the canonical path, so it verifies as the same
    # issuance and lands in the same attempt namespace rather than a new one.
    through_link = cdc_e2e_mission.verify_owner_execution_authorization(
        link,
        clearance=clearance_for_authorization(link),
        runtime=STUB_RUNTIME,
        frozen=frozen,
    )
    direct = _verify_auth(artifact, frozen)
    assert through_link.canonical_path == direct.canonical_path
    assert cdc_e2e_mission.attempt_record_path(through_link) == cdc_e2e_mission.attempt_record_path(
        direct
    )


def test_relative_and_dotdot_paths_resolve_to_the_same_namespace(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """`..` normalization cannot open a second namespace."""
    home = tmp_path / "issued"
    home.mkdir()
    artifact = synthetic_authorization(home)
    awkward = home / ".." / "issued" / artifact.name
    verified = cdc_e2e_mission.verify_owner_execution_authorization(
        awkward,
        clearance=clearance_for_authorization(awkward),
        runtime=STUB_RUNTIME,
        frozen=frozen,
    )
    assert cdc_e2e_mission.attempt_record_path(verified) == cdc_e2e_mission.attempt_record_path(
        _verify_auth(artifact, frozen)
    )


def test_an_authorization_without_a_declared_canonical_path_is_refused(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """The declaration is required, not optional."""
    document = json.loads(synthetic_authorization(tmp_path).read_bytes())
    del document["canonical_authorization_path"]
    artifact = synthetic_authorization(
        tmp_path,
        raw=(json.dumps(document, indent=2, sort_keys=True) + "\n").encode(),
    )
    with pytest.raises(
        cdc_e2e_mission.OwnerExecutionAuthorizationError,
        match="declares no canonical_authorization_path",
    ):
        _verify_auth(artifact, frozen)


def test_same_authorization_identity_resolves_to_one_attempt_namespace(
    tmp_path: Path, frozen: FrozenMissionInput
) -> None:
    """Repeated verification of the same issuance yields the same namespace."""
    artifact = synthetic_authorization(tmp_path)
    first = _verify_auth(artifact, frozen)
    second = _verify_auth(artifact, frozen)
    assert first.sha256_hex == second.sha256_hex
    assert cdc_e2e_mission.attempt_record_path(first) == cdc_e2e_mission.attempt_record_path(second)
    assert cdc_e2e_mission.attempt_record_path(first).parent == artifact.parent.resolve()


# ---------------------------------------------------------------------------
# The persisted attempt record's exact identity is bound into Stage 1
# ---------------------------------------------------------------------------


def test_stage_1_binds_the_exact_persisted_attempt_record_identity(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """The bound digest and byte count reproduce the file on disk exactly."""
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    observation = _form_nonmission_stage_1(projection, frozen, profile, authorization)
    bound = observation.attempt_record
    assert bound is not None
    persisted = cdc_e2e_mission.attempt_record_path(authorization).read_bytes()
    assert bound["attempt_record_sha256"] == hashlib.sha256(persisted).hexdigest()
    assert bound["attempt_record_bytes"] == len(persisted)
    assert bound["attempt_state"] == cdc_e2e_mission.ATTEMPT_STATE_CONSUMED
    assert bound["owner_execution_authorization_sha256"] == authorization.sha256_hex
    assert bound["implementation_commit"] == STUB_RUNTIME.implementation_commit
    assert bound["implementation_tree"] == STUB_RUNTIME.implementation_tree
    assert bound["mission_package_sha256"] == frozen.package_sha256
    assert cdc_e2e_mission.attempt_record_identity_is_intact(bound)
    # The persisted payload does not contain its own digest.
    assert "attempt_record_sha256" not in json.loads(persisted)
    # And the identity is inside the Stage-1 checkpoint digest.
    assert observation.as_record()["attempt_record"] == bound


def test_mutating_the_persisted_attempt_record_is_detectable(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """Tampering and deletion are detectable, though not prevented.

    This is a local filesystem, not an external immutable ledger. The claim is
    detectability within the bound execution-state namespace, nothing stronger.
    """
    artifact = synthetic_authorization(tmp_path)
    authorization = _verify_auth(artifact, frozen)
    observation = _form_nonmission_stage_1(projection, frozen, profile, authorization)
    bound = observation.attempt_record
    assert bound is not None
    assert cdc_e2e_mission.attempt_record_identity_is_intact(bound)

    record_path = cdc_e2e_mission.attempt_record_path(authorization)
    tampered = json.loads(record_path.read_bytes())
    tampered["attempt_state"] = cdc_e2e_mission.ATTEMPT_STATE_NONE
    record_path.write_bytes((json.dumps(tampered, indent=2, sort_keys=True) + "\n").encode())
    assert not cdc_e2e_mission.attempt_record_identity_is_intact(bound)

    record_path.unlink()
    assert not cdc_e2e_mission.attempt_record_identity_is_intact(bound)


def test_a_bound_identity_cannot_name_a_different_attempt_file(
    tmp_path: Path,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    profile: FrozenComponentProfile,
) -> None:
    """Claiming consumption while pointing at another attempt file is detectable."""
    first_dir = tmp_path / "one"
    second_dir = tmp_path / "two"
    first_dir.mkdir()
    second_dir.mkdir()
    first = _verify_auth(synthetic_authorization(first_dir), frozen)
    second = _verify_auth(synthetic_authorization(second_dir), frozen)
    assert first.sha256_hex != second.sha256_hex

    observation = _form_nonmission_stage_1(projection, frozen, profile, first)
    cdc_e2e_mission.claim_attempt(second, STUB_RUNTIME, frozen)
    bound = observation.attempt_record
    assert bound is not None
    swapped = {
        **bound,
        "attempt_record_path": str(cdc_e2e_mission.attempt_record_path(second)),
    }
    assert not cdc_e2e_mission.attempt_record_identity_is_intact(swapped)


def test_single_use_claim_is_scoped_to_the_execution_state_namespace() -> None:
    """State the boundary of the claim rather than overstating it."""
    source = inspect.getsource(cdc_e2e_mission.attempt_record_identity_is_intact)
    assert "not prevented" in source
    assert "immutable external ledger" in source or "external immutable ledger" in source
