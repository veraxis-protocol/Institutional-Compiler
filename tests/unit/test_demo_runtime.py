"""OAM composition, the action gate, and the result-bearing refusal.

These tests exercise the composition directly, without the kernel, so the
separations they check are checked even where no ZTL checkout exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from oic.cdc_authority import AuthorityRequest, evaluate_synthetic_authority, parse_basis_record
from oic.cdc_currentness import CURRENT, SUPERSEDED, resolve_currentness
from oic.demo_runtime import (
    ACTION_BLOCKED,
    ACTION_ESCALATED,
    ACTION_GATE_CLASS,
    ACTION_PERMITTED,
    ALLOW,
    AUTHORIZED,
    BLOCK,
    CASE_IDS,
    CONTROL_REQUIREMENT,
    ESCALATE,
    EVIDENCE_DIRECTORIES,
    PRECAUTIONARY,
    PROCEDURAL,
    REFUSED,
    RESULT_BEARING_EXECUTION_NOT_AUTHORIZED,
    SUBSTANTIVE,
    UNRESOLVED,
    DemoRuntimeError,
    ExecutionContext,
    _action_state,
    _admissibility_basis,
    _authority_bases_for,
    _components,
    _compose,
    build_currentness_index,
    compile_scenario,
    load_result_bearing_authorization,
    load_scenario,
    validate_scenario,
)


@pytest.fixture(scope="module")
def state(repo_root: Path) -> dict[str, Any]:
    scenario = load_scenario(repo_root)
    compiled = compile_scenario(scenario)
    return {
        "scenario": scenario,
        "compiled": compiled,
        "index": build_currentness_index(scenario, compiled),
    }


def _authority(state: dict[str, Any], case_id: str, at: str) -> Any:  # noqa: ANN401
    scenario, compiled, index = state["scenario"], state["compiled"], state["index"]
    policy = compiled["v1"]
    output_ref = scenario.output_ref("v1")
    from oic.cdc_currentness import historical_artifact_digest

    digest = historical_artifact_digest(policy.control_envelope)
    resolution = resolve_currentness(
        output_ref=output_ref,
        historical_artifact={"body": policy.control_envelope, "historical_state": "X"},
        index=index,
        evaluated_at=at,
    )
    return evaluate_synthetic_authority(
        request=AuthorityRequest(
            artifact_ref=output_ref,
            artifact_digest=digest,
            recomputed_artifact_digest=digest,
            requested_use="SYNTHETIC_GRANT_DISBURSEMENT_DECISION",
            scope=scenario.scope_ref,
            requesting_principal="SYNTH-DISBURSING-OFFICER-001",
            currentness_resolution_digest=resolution.resolution_digest,
            currentness_epoch_digest="0" * 64,
            evaluation_time=at,
            valid_until="2027-12-31T23:59:59Z",
            decision_id="d",
        ),
        authority_bases=[parse_basis_record(r) for r in _authority_bases_for(scenario, case_id)],
        admissibility_bases=[parse_basis_record(_admissibility_basis(scenario))],
        artifact_class="SYNTHETIC_COMPILED_CONTROL_ENVELOPE",
    )


# --- the execution-context distinction -------------------------------------


def test_the_two_execution_contexts_are_distinct_and_named() -> None:
    values = {member.value for member in ExecutionContext}
    assert values == {"DEVELOPMENT_TEST_ONLY", "OWNER_AUTHORIZED_RESULT_BEARING"}
    assert len(values) == len(ExecutionContext)


def test_a_result_bearing_run_refuses_without_an_authorization() -> None:
    with pytest.raises(DemoRuntimeError, match=RESULT_BEARING_EXECUTION_NOT_AUTHORIZED):
        load_result_bearing_authorization(None)


def test_a_result_bearing_run_refuses_a_missing_artifact(tmp_path: Path) -> None:
    with pytest.raises(DemoRuntimeError, match=RESULT_BEARING_EXECUTION_NOT_AUTHORIZED):
        load_result_bearing_authorization(tmp_path / "absent.json")


def test_a_result_bearing_run_refuses_an_artifact_that_does_not_authorize(tmp_path: Path) -> None:
    """Presenting an artifact is not the same as being authorized by one."""
    path = tmp_path / "auth.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "OIC-DEMO-EXECUTION-AUTHORIZATION-v0.1",
                "scenario_id": "synthetic-grant-authority",
                "result_bearing_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DemoRuntimeError, match="does not authorize a result-bearing execution"):
        load_result_bearing_authorization(path)


def test_a_result_bearing_run_refuses_an_authorization_for_another_scenario(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "OIC-DEMO-EXECUTION-AUTHORIZATION-v0.1",
                "scenario_id": "some-other-scenario",
                "result_bearing_execution_authorized": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DemoRuntimeError, match="authorizes scenario"):
        load_result_bearing_authorization(path)


# --- currentness -----------------------------------------------------------


def test_v1_is_current_before_v2_takes_effect_and_superseded_after(state: dict[str, Any]) -> None:
    scenario, compiled, index = state["scenario"], state["compiled"], state["index"]
    artifact = {"body": compiled["v1"].control_envelope, "historical_state": "X"}
    before = resolve_currentness(
        output_ref=scenario.output_ref("v1"),
        historical_artifact=artifact,
        index=index,
        evaluated_at=scenario.time("before_v2_effective"),
    )
    after = resolve_currentness(
        output_ref=scenario.output_ref("v1"),
        historical_artifact=artifact,
        index=index,
        evaluated_at=scenario.time("after_v2_effective"),
    )
    assert before.currentness_state == CURRENT
    assert after.currentness_state == SUPERSEDED
    assert after.reason_code_id == "R2"


def test_currentness_is_not_authority(state: dict[str, Any]) -> None:
    """A CURRENT control with a revoked delegation still fails at authority."""
    scenario = state["scenario"]
    decision = _authority(state, "case-3", scenario.time("before_v2_effective"))
    assert decision.reason_code_id == "A10"


def test_competing_operative_bases_are_a6_not_a11(state: dict[str, Any]) -> None:
    """Competing is not absent, and the codes must not be collapsed."""
    scenario = state["scenario"]
    decision = _authority(state, "case-4", scenario.time("before_v2_effective"))
    assert decision.reason_code_id == "A6"


# --- composition -----------------------------------------------------------


def _compose_for(state: dict[str, Any], **overrides: Any) -> tuple[str, str, str, list[str]]:  # noqa: ANN401
    scenario, compiled = state["scenario"], state["compiled"]
    policy = compiled["v1"]
    at = scenario.time("before_v2_effective")
    authority = overrides.pop("authority", _authority(state, "case-1", at))
    from oic.cdc_currentness import UseGateProfile, UseGateRequest, evaluate_present_use

    gate = evaluate_present_use(
        request=UseGateRequest(
            output_ref=scenario.output_ref("v1"),
            requested_use="SYNTHETIC_GRANT_DISBURSEMENT_DECISION",
            requested_operation_class="SYNTHETIC_BOUNDED_DEMONSTRATION",
            consequential=True,
            requesting_scope_ref=scenario.scope_ref,
            requested_at=at,
        ),
        historical_artifact={"body": policy.control_envelope, "historical_state": "X"},
        currentness_index=state["index"],
        profile=UseGateProfile(),
        run_metadata={
            "run_id": "r",
            "trace_id": "t",
            "producer": "p",
            "producer_version": "0",
            "occurred_at": at,
            "recorded_at": at,
        },
    )
    arguments: dict[str, Any] = {
        "epistemic_status": "ESTABLISHED",
        "warranty_grade": "hereditary",
        "unverified_ground_ids": [],
        "gate_decision": gate,
        "authority": authority,
        "compiled": policy,
        "binding_ok": True,
        "evidence_ok": True,
        "proposal_id": "proposal:x",
    }
    arguments.update(overrides)
    components = _components(**arguments)
    return _compose(components, authority=authority)


def test_all_preconditions_met_authorizes_and_allows(state: dict[str, Any]) -> None:
    assert _compose_for(state) == (AUTHORIZED, ALLOW, SUBSTANTIVE, [])


def test_a_refuted_claim_blocks_on_a_substantive_basis(state: dict[str, Any]) -> None:
    status, disposition, basis, _ = _compose_for(state, epistemic_status="REFUTED")
    assert (status, disposition, basis) == (REFUSED, BLOCK, SUBSTANTIVE)


def test_an_unresolved_claim_blocks_on_a_precautionary_basis(state: dict[str, Any]) -> None:
    """UNRESOLVED fails closed without becoming substantively false."""
    status, disposition, basis, _ = _compose_for(state, epistemic_status="UNRESOLVED")
    assert (status, disposition, basis) == (REFUSED, BLOCK, PRECAUTIONARY)


def test_an_insufficient_grade_blocks_on_a_control_requirement(state: dict[str, Any]) -> None:
    status, disposition, basis, reasons = _compose_for(state, warranty_grade="sound")
    assert (status, disposition, basis) == (REFUSED, BLOCK, CONTROL_REQUIREMENT)
    assert "usable_logical_warrant" in reasons


def test_an_unverified_ground_under_forbid_blocks_on_a_control_requirement(
    state: dict[str, Any],
) -> None:
    status, disposition, basis, _ = _compose_for(
        state, unverified_ground_ids=["g_eligibility_evidence_present"]
    )
    assert (status, disposition, basis) == (REFUSED, BLOCK, CONTROL_REQUIREMENT)


def test_competing_authority_escalates_and_never_states_the_claim_is_false(
    state: dict[str, Any],
) -> None:
    scenario = state["scenario"]
    authority = _authority(state, "case-4", scenario.time("before_v2_effective"))
    status, disposition, basis, _ = _compose_for(state, authority=authority)
    assert (status, disposition, basis) == (UNRESOLVED, ESCALATE, PRECAUTIONARY)


def test_compose_cannot_see_the_epistemic_status_at_all(state: dict[str, Any]) -> None:
    """The separation is structural, not a rule someone has to remember.

    ``_compose`` returns three fields and never the epistemic one, and is not
    even handed it, so no authority or currentness path can rewrite it.
    """
    import inspect

    parameters = set(inspect.signature(_compose).parameters)
    assert "epistemic_status" not in parameters


def test_authority_refusal_does_not_rewrite_the_epistemic_status(state: dict[str, Any]) -> None:
    """The delegation is revoked; the proposition is still ESTABLISHED."""
    scenario = state["scenario"]
    authority = _authority(state, "case-3", scenario.time("before_v2_effective"))
    status, disposition, basis, _ = _compose_for(
        state, authority=authority, epistemic_status="ESTABLISHED"
    )
    assert (status, disposition, basis) == (REFUSED, BLOCK, PROCEDURAL)


def test_missing_evidence_blocks(state: dict[str, Any]) -> None:
    status, disposition, _, reasons = _compose_for(state, evidence_ok=False)
    assert (status, disposition) == (REFUSED, BLOCK)
    assert "required_evidence" in reasons


# --- the action gate -------------------------------------------------------


def test_the_action_gate_maps_each_disposition_to_one_state() -> None:
    assert _action_state(ALLOW) == ACTION_PERMITTED
    assert _action_state(BLOCK) == ACTION_BLOCKED
    assert _action_state(ESCALATE) == ACTION_ESCALATED


def test_the_action_gate_claims_only_what_it_is() -> None:
    assert ACTION_GATE_CLASS == "BOUNDED_DEMO_EXECUTION_GATE"
    assert "NON_BYPASSABLE" not in ACTION_GATE_CLASS
    assert "PRODUCTION" not in ACTION_GATE_CLASS


# --- shape -----------------------------------------------------------------


def test_the_evidence_graph_declares_all_six_stages() -> None:
    assert EVIDENCE_DIRECTORIES == (
        "00-source",
        "01-oic",
        "02-ztl",
        "03-runtime",
        "04-reliance",
        "05-evidence",
    )


def test_there_are_exactly_five_cases() -> None:
    assert len(CASE_IDS) == 5


def test_validate_executes_nothing(repo_root: Path) -> None:
    report = validate_scenario(repo_root)
    assert report["execution_performed"] is False
    assert report["result_bearing_execution"] is False


def test_the_demo_schemas_are_valid_draft_2020_12(repo_root: Path) -> None:
    for name in ("runtime-binding", "oam-decision", "execution-authorization"):
        document = json.loads(
            (repo_root / "schemas" / "demo" / f"{name}.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(document)
