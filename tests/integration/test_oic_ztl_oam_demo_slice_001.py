"""The five semantic cases, end to end, against the live pinned kernel.

DEVELOPMENT TESTS ONLY. Every run here is ``DEVELOPMENT_TEST_ONLY`` and no
result it produces may be labelled a measured demonstration. The claim-bearing
execution is a separate owner-authorized act that this suite cannot perform and
does not attempt.

The suite skips without an external ZTL checkout at the pinned commit, because
fixture replay is not sufficient for this lane: the point is that the kernel is
actually called.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from oic.demo_runtime import (
    ACTION_BLOCKED,
    ACTION_ESCALATED,
    ACTION_PERMITTED,
    CASE_IDS,
    ExecutionContext,
    build_currentness_index,
    compile_scenario,
    decision_semantic_projection,
    load_scenario,
    run_all_cases,
    run_case,
    verify_evidence_graph,
    write_evidence_graph,
)
from oic.demo_ztl import KERNEL_COMMIT

ZTL_ENV = "OIC_DEMO_ZTL_PATH"


def _ztl_checkout() -> Path | None:
    value = os.environ.get(ZTL_ENV)
    if not value:
        return None
    path = Path(value)
    return path if (path / "ztljudge.py").is_file() else None


pytestmark = pytest.mark.skipif(
    _ztl_checkout() is None,
    reason=(
        f"the demo slice calls ZTL live; set {ZTL_ENV} to a checkout at {KERNEL_COMMIT}. "
        "Fixture replay is deliberately not accepted as a substitute."
    ),
)


@pytest.fixture(scope="module")
def outcomes(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    ztl = _ztl_checkout()
    assert ztl is not None
    work = tmp_path_factory.mktemp("demo-slice-001")
    return dict(
        run_all_cases(
            repo_root=repo_root,
            ztl_path=ztl,
            execution_context=ExecutionContext.DEVELOPMENT_TEST_ONLY,
            work_dir=work,
        )
    )


def _projection(outcomes: dict[str, Any], case_id: str) -> dict[str, Any]:
    return decision_semantic_projection(outcomes[case_id])


# --- the execution-context boundary ----------------------------------------


def test_every_case_ran_as_a_development_test(outcomes: dict[str, Any]) -> None:
    for outcome in outcomes.values():
        assert outcome.execution_context is ExecutionContext.DEVELOPMENT_TEST_ONLY
        assert outcome.oam_decision["execution_context"] == "DEVELOPMENT_TEST_ONLY"
        assert outcome.oam_decision["measured_end_to_end_claim"] is False


def test_no_record_claims_a_measured_demonstration(outcomes: dict[str, Any]) -> None:
    for outcome in outcomes.values():
        serialized = json.dumps(outcome.oam_decision)
        assert "MEASURED_INTERNAL_END_TO_END_TECHNICAL_DEMONSTRATION" not in serialized
        assert outcome.oam_decision["claim_ceiling"] == (
            "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"
        )


def test_the_bounded_action_performs_no_real_world_effect(outcomes: dict[str, Any]) -> None:
    for outcome in outcomes.values():
        action = outcome.oam_decision["bounded_action"]
        assert action["performs_real_world_effect"] is False
        assert action["gate_class"] == "BOUNDED_DEMO_EXECUTION_GATE"


# --- CASE 1: valid rule, valid authority -----------------------------------


def test_case_1_permits_the_action_and_issues_reliance(outcomes: dict[str, Any]) -> None:
    assert _projection(outcomes, "case-1") == {
        "case_id": "case-1",
        "version": "v1",
        "epistemic_status": "ESTABLISHED",
        "institutional_authorization_status": "AUTHORIZED",
        "execution_disposition": "ALLOW",
        "decision_basis": "SUBSTANTIVE",
        "currentness_state": "CURRENT",
        "currentness_reason_code_id": "G1",
        "authority_decision": "PROCEED",
        "authority_reason_code_id": "A1",
        "ztl_disposition": "EARNED",
        "ztl_warranty_grade": "hereditary",
        "ztl_raw_verdict": "T",
        "action_state": ACTION_PERMITTED,
        "reliance_disposition": "ISSUED",
        "reliance_reason_code_id": "I1",
    }


def test_case_1_reliance_came_from_a_separate_consumer_process(outcomes: dict[str, Any]) -> None:
    """Producer and consumer are different principals in different processes."""
    outcome = outcomes["case-1"]
    validation = outcome.consumer_validation
    assert validation is not None
    assert validation["decision"] == "PROCEED_TO_ISSUANCE"
    assert len(validation["checks"]) == 16
    assert all(check["passed"] for check in validation["checks"])
    consumer = outcome.reliance["consumer_principal"]
    assert consumer != outcome.oam_decision["decision_id"]
    assert validation["consumer_identity"]["process_id"] != os.getpid()


def test_case_1_consumer_re_resolved_and_re_evaluated_for_itself(outcomes: dict[str, Any]) -> None:
    validation = outcomes["case-1"].consumer_validation
    assert validation is not None
    by_name = {check["check_name"]: check for check in validation["checks"]}
    assert by_name["currentness_re_resolution"]["passed"]
    assert by_name["authority_admissibility_re_evaluation"]["passed"]
    assert validation["re_resolved_currentness_resolution_digest"]
    assert validation["reliance_time_authority_decision_digest"]


# --- CASE 2: v1 used after v2 becomes effective ----------------------------


def test_case_2_blocks_on_currentness_while_the_logic_still_holds(
    outcomes: dict[str, Any],
) -> None:
    projection = _projection(outcomes, "case-2")
    # The logical result is untouched by the institutional refusal.
    assert projection["epistemic_status"] == "ESTABLISHED"
    assert projection["ztl_disposition"] == "EARNED"
    assert projection["currentness_state"] == "SUPERSEDED"
    assert projection["currentness_reason_code_id"] == "G2"
    assert projection["institutional_authorization_status"] == "REFUSED"
    assert projection["execution_disposition"] == "BLOCK"
    assert projection["action_state"] == ACTION_BLOCKED
    assert projection["decision_basis"] == "PROCEDURAL"


def test_case_2_never_evaluated_authority_at_all(outcomes: dict[str, Any]) -> None:
    """The gate refused, so authority was not asked — and an A1 was not invented.

    Evaluating authority anyway would put a PROCEED on the record for an operation
    that had already been stopped, and a PROCEED that meant nothing is
    indistinguishable from one that did.
    """
    outcome = outcomes["case-2"]
    assert outcome.authority_decision is None
    observation = outcome.oam_decision["authority_observation"]
    assert observation["authority_evaluated"] is False
    assert observation["authority_not_evaluated_reason"] == "CURRENTNESS_GATE_DID_NOT_PROCEED"
    assert observation["decision"] == "NOT_EVALUATED"
    assert _projection(outcomes, "case-2")["authority_reason_code_id"] == "NOT_EVALUATED"


def test_cases_3_and_4_still_reach_authority_because_currentness_is_g1(
    outcomes: dict[str, Any],
) -> None:
    for case_id, expected in (("case-3", "A10"), ("case-4", "A6")):
        outcome = outcomes[case_id]
        assert outcome.gate_decision.reason_code_id == "G1"
        assert outcome.authority_decision is not None
        assert outcome.authority_decision.reason_code_id == expected
        assert outcome.oam_decision["authority_observation"]["authority_evaluated"] is True


def test_case_2_issued_no_reliance_and_said_why(outcomes: dict[str, Any]) -> None:
    outcome = outcomes["case-2"]
    assert outcome.reliance is None
    assert outcome.absent_artifacts
    assert outcome.absent_artifacts[0]["execution_disposition"] == "BLOCK"


# --- CASE 3: delegation revoked --------------------------------------------


def test_case_3_blocks_on_authority_while_currentness_and_logic_hold(
    outcomes: dict[str, Any],
) -> None:
    projection = _projection(outcomes, "case-3")
    assert projection["epistemic_status"] == "ESTABLISHED"
    assert projection["currentness_state"] == "CURRENT"
    assert projection["currentness_reason_code_id"] == "G1"
    assert projection["authority_reason_code_id"] == "A10"
    assert projection["institutional_authorization_status"] == "REFUSED"
    assert projection["execution_disposition"] == "BLOCK"
    assert projection["reliance_disposition"] is None


def test_case_3_revocation_did_not_rewrite_the_epistemic_result(outcomes: dict[str, Any]) -> None:
    decision = outcomes["case-3"].oam_decision
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["ztl_observation"]["disposition"] == "EARNED"
    assert decision["authority_observation"]["reason_code_id"] == "A10"


# --- CASE 4: competing operative authority bases ---------------------------


def test_case_4_is_unresolved_and_escalates(outcomes: dict[str, Any]) -> None:
    projection = _projection(outcomes, "case-4")
    assert projection["authority_reason_code_id"] == "A6"
    assert projection["institutional_authorization_status"] == "UNRESOLVED"
    assert projection["execution_disposition"] in {"BLOCK", "ESCALATE"}
    assert projection["action_state"] in {ACTION_BLOCKED, ACTION_ESCALATED}
    assert projection["decision_basis"] == "PRECAUTIONARY"
    assert projection["reliance_disposition"] is None


def test_case_4_never_states_that_the_proposition_is_false(outcomes: dict[str, Any]) -> None:
    """Unresolved authority is not a finding of falsity, and must not read as one."""
    decision = outcomes["case-4"].oam_decision
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["epistemic_status"] != "REFUTED"
    assert decision["institutional_authorization_status"] == "UNRESOLVED"


# --- CASE 5: correction / change -------------------------------------------


def test_case_5_re_runs_ztl_under_v2_and_is_refuted(outcomes: dict[str, Any]) -> None:
    projection = _projection(outcomes, "case-5")
    assert projection["version"] == "v2"
    assert projection["ztl_disposition"] == "REFUTED"
    assert projection["epistemic_status"] == "REFUTED"
    assert projection["execution_disposition"] == "BLOCK"
    assert projection["decision_basis"] == "SUBSTANTIVE"
    assert projection["reliance_disposition"] is None


def test_case_5_did_not_reuse_the_case_1_warrant(outcomes: dict[str, Any]) -> None:
    """The kernel was called again, not consulted from a cache."""
    first = outcomes["case-1"].warrant
    fifth = outcomes["case-5"].warrant
    assert first["input_hash"] != fifth["input_hash"]
    assert first["output_hash"] != fifth["output_hash"]
    assert first["warrant_artifact_id"] != fifth["warrant_artifact_id"]


def test_case_5_left_the_historical_reliance_bytes_untouched(outcomes: dict[str, Any]) -> None:
    """A later correction may never rewrite a reliance already issued."""
    historical = outcomes["case-1"].reliance
    assert historical is not None
    assert historical["reliance_disposition"] == "ISSUED"
    from oic.cdc_reliance import reliance_record_digest

    body = {k: v for k, v in historical.items() if k != "reliance_record_digest"}
    assert (
        reliance_record_digest({**body, "reliance_record_digest": ""})
        == historical["reliance_record_digest"]
    )


def test_future_v1_use_is_refused_by_currentness_after_the_change(
    outcomes: dict[str, Any],
) -> None:
    assert _projection(outcomes, "case-2")["currentness_state"] == "SUPERSEDED"
    assert _projection(outcomes, "case-1")["currentness_state"] == "CURRENT"


def test_every_case_established_evidence_from_an_observation(outcomes: dict[str, Any]) -> None:
    """Satisfaction came from opened bytes, not from the requirement existing."""
    for outcome in outcomes.values():
        observation = outcome.oam_decision["evidence_observation"]
        assert observation["observed_digest"].startswith("sha256:")
        assert observation["observed_evidence_id"] == "signed_eligibility_evidence"
        assert observation["evidence_state"] == "SIGNED"
        assert observation["satisfaction"] is True
        assert observation["findings"] == []


def test_every_warrant_binding_was_validated_at_runtime(outcomes: dict[str, Any]) -> None:
    for outcome in outcomes.values():
        validation = outcome.oam_decision["warrant_binding_validation"]
        assert validation["validated"] is True, validation["findings"]
        assert outcome.warrant_findings == ()


def test_case_1_evidence_refs_are_byte_resolvable(outcomes: dict[str, Any]) -> None:
    """A consumer can check each reference, not merely read an identifier off it."""
    validation = outcomes["case-1"].consumer_validation
    assert validation is not None
    resolvability = next(
        check for check in validation["checks"] if check["check_name"] == "evidence_resolvability"
    )
    assert resolvability["passed"]
    assert resolvability["observed"]["unresolved"] == 0
    assert resolvability["observed"]["count"] >= 2


# --- determinism -----------------------------------------------------------


def test_the_semantic_projection_is_deterministic(
    repo_root: Path, tmp_path: Path, outcomes: dict[str, Any]
) -> None:
    """Same scenario and same declared logical time, same decision-affecting output.

    Process ids and paths differ between the two runs by construction; none of
    them may appear in the projection or move a single field of it.
    """
    ztl = _ztl_checkout()
    assert ztl is not None
    scenario = load_scenario(repo_root)
    compiled = compile_scenario(scenario)
    index = build_currentness_index(scenario, compiled)
    for case_id in CASE_IDS:
        repeat = run_case(
            case_id,
            scenario=scenario,
            compiled=compiled,
            index=index,
            repo_root=repo_root,
            ztl_path=ztl,
            execution_context=ExecutionContext.DEVELOPMENT_TEST_ONLY,
            work_dir=None,
        )
        first = dict(decision_semantic_projection(outcomes[case_id]))
        second = dict(decision_semantic_projection(repeat))
        # The repeat runs without a working directory, so it never reaches the
        # reliance leg; every other field must match exactly.
        first.pop("reliance_disposition")
        first.pop("reliance_reason_code_id")
        second.pop("reliance_disposition")
        second.pop("reliance_reason_code_id")
        assert first == second


def test_a_declared_operational_observation_does_not_change_the_decision(
    outcomes: dict[str, Any],
) -> None:
    """Real process ids vary and are recorded; they move nothing semantic."""
    projection = json.dumps(_projection(outcomes, "case-1"))
    assert str(os.getpid()) not in projection
    assert "process_id" not in projection


# --- the evidence graph ----------------------------------------------------


def test_the_evidence_graph_is_traversable_and_records_absences(
    outcomes: dict[str, Any], tmp_path: Path, repo_root: Path
) -> None:
    manifest = write_evidence_graph(outcomes, tmp_path, scenario=load_scenario(repo_root))
    for name in ("00-source", "01-oic", "02-ztl", "03-runtime", "04-reliance", "05-evidence"):
        assert (tmp_path / name).is_dir()
    for case_id, entry in manifest["cases"].items():
        assert entry["written"]["02-ztl"]["sha256"]
        if entry["semantic_projection"]["reliance_disposition"] is None:
            assert entry["absent_artifacts"], f"{case_id} records no reason for the absence"
    assert manifest["measured_end_to_end_claim"] is False
    assert manifest["claim_ceiling"] == "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"

    # 05-evidence must carry the causal chain, the manifest and the digests.
    for name in ("causal-chain.json", "MANIFEST.json", "SHA256SUMS"):
        assert (tmp_path / "05-evidence" / name).is_file(), name


def test_the_written_package_verifies_against_its_own_digests(
    outcomes: dict[str, Any], tmp_path: Path, repo_root: Path
) -> None:
    write_evidence_graph(outcomes, tmp_path, scenario=load_scenario(repo_root))
    verification = verify_evidence_graph(tmp_path)
    assert verification["verified"] is True, verification["failures"]
    assert verification["checked"] >= 21


def test_a_tampered_package_fails_self_verification(
    outcomes: dict[str, Any], tmp_path: Path, repo_root: Path
) -> None:
    """Self-verification that cannot fail would prove nothing about the package."""
    write_evidence_graph(outcomes, tmp_path, scenario=load_scenario(repo_root))
    target = tmp_path / "03-runtime" / "case-1-runtime.json"
    target.write_bytes(target.read_bytes() + b"\n")
    verification = verify_evidence_graph(tmp_path)
    assert verification["verified"] is False
    assert any("case-1-runtime.json" in failure for failure in verification["failures"])


def test_the_causal_chain_resolves_to_persisted_bytes(
    outcomes: dict[str, Any], tmp_path: Path, repo_root: Path
) -> None:
    write_evidence_graph(outcomes, tmp_path, scenario=load_scenario(repo_root))
    chain = json.loads((tmp_path / "05-evidence" / "causal-chain.json").read_text(encoding="utf-8"))
    from oic.cdc_reliance import persisted_file_sha256

    for case_id, entry in chain["cases"].items():
        assert entry["source_content_hash"].startswith("sha256:")
        assert entry["warrant_output_hash"].startswith("sha256:")
        for stage, artifact in entry["artifacts"].items():
            path = tmp_path / stage / artifact["path"]
            assert path.is_file(), f"{case_id}/{stage}"
            assert persisted_file_sha256(path.read_bytes()) == artifact["sha256"]


def test_every_oam_decision_validates_against_the_demo_schema(
    repo_root: Path, outcomes: dict[str, Any]
) -> None:
    document = json.loads(
        (repo_root / "schemas" / "demo" / "oam-decision.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(document)
    for outcome in outcomes.values():
        validator.validate(outcome.oam_decision)


def test_every_warrant_validates_against_the_proposed_contract(
    repo_root: Path, outcomes: dict[str, Any]
) -> None:
    document = json.loads(
        (repo_root / "schemas" / "proposed" / "warrant-artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(document)
    for outcome in outcomes.values():
        validator.validate(outcome.warrant)


def test_every_warrant_passes_the_existing_semantic_conformance_rules(
    outcomes: dict[str, Any],
) -> None:
    """The demo warrants are held to the repository's own warrant semantics."""
    from tests.contract.semantic_conformance import check_warrant_artifact

    for outcome in outcomes.values():
        findings = check_warrant_artifact(
            outcome.warrant,
            marking=outcome.kernel_result.marking,
            rendered_formula=outcome.kernel_result.rendered_formula,
        )
        assert findings == [], f"{outcome.case_id}: {[str(f) for f in findings]}"


# --- evidence byte resolution, from the consumer's side ---------------------


def test_the_consumer_refuses_an_unresolvable_evidence_reference(tmp_path: Path) -> None:
    """Each mutation must be caught. A check that cannot fail is not a check.

    The consumer opens the referenced bytes and recomputes the digest, so a
    substituted, corrupted or absent artifact resolves differently from the real
    one rather than equally well.
    """
    from oic.cdc_reliance import persisted_file_sha256

    def resolve(reference: dict[str, Any]) -> bool:
        location = reference.get("path")
        bound = reference.get("sha256")
        if not isinstance(location, str) or not isinstance(bound, str) or not bound:
            return False
        target = Path(location)
        if not target.is_file():
            return False
        if persisted_file_sha256(target.read_bytes()) != bound:
            return False
        return bool(reference.get("evidence_id")) and bool(reference.get("evidence_class"))

    for index, mutation in enumerate(("wrong_digest", "missing_file", "substituted_bytes")):
        payload = b'{"evidence_id": "signed_eligibility_evidence"}\n'
        path = tmp_path / f"evidence-{index}.json"
        path.write_bytes(payload)
        ref: dict[str, Any] = {
            "evidence_id": "signed_eligibility_evidence",
            "evidence_class": "SYNTHETIC_ELIGIBILITY_EVIDENCE",
            "path": str(path),
            "sha256": persisted_file_sha256(payload),
        }
        assert resolve(ref) is True, mutation

        if mutation == "wrong_digest":
            ref["sha256"] = "0" * 64
        elif mutation == "missing_file":
            path.unlink()
        else:
            path.write_bytes(payload + b"tampered\n")
        assert resolve(ref) is False, mutation


def test_the_propagated_evidence_refs_carry_locators_and_digests(
    outcomes: dict[str, Any],
) -> None:
    """An identifier alone gives a consumer nothing it can verify."""
    validation = outcomes["case-1"].consumer_validation
    assert validation is not None
    envelope_check = next(
        check for check in validation["checks"] if check["check_name"] == "evidence_resolvability"
    )
    assert envelope_check["passed"]
    assert envelope_check["observed"]["count"] >= 2
    assert envelope_check["observed"]["unresolved"] == 0
