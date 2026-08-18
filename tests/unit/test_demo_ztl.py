"""Warrant construction and the ZTL boundary.

The live-kernel tests need an external checkout at the pinned commit and skip
without one. They are not the only protection: the mapping prohibitions, the
bridge's refusal paths and the hash projections are all checked offline, so a
run with no kernel available still fails if the semantics drift.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from oic.demo_ztl import (
    CANONICALIZATION_PROFILE_ID,
    DISPOSITION_TO_EPISTEMIC,
    KERNEL_COMMIT,
    KERNEL_PROFILE_ID,
    PROHIBITED_TRANSITIONS,
    KernelResult,
    WarrantError,
    build_warrant,
    epistemic_status_for,
    expected_formula_hash,
    expected_output_hash,
    invoke_kernel,
    resolve_ztl_path,
    validate_warrant_binding,
)

ZTL_ENV = "OIC_DEMO_ZTL_PATH"

FORMULA = "g_amount_within_limit & g_eligibility_evidence_present"
RENDERED = "(g_amount_within_limit ∧ g_eligibility_evidence_present)"


def _ztl_checkout() -> Path | None:
    value = os.environ.get(ZTL_ENV)
    if not value:
        return None
    path = Path(value)
    if not (path / ".git").exists() and not (path / "ztljudge.py").is_file():
        return None
    return path


live_ztl = pytest.mark.skipif(
    _ztl_checkout() is None,
    reason=f"live ZTL development acceptance requires {ZTL_ENV} at {KERNEL_COMMIT}",
)


def _result(**overrides: object) -> KernelResult:
    base = {
        "rendered_formula": RENDERED,
        "disposition": "EARNED",
        "raw_verdict": "T",
        "warranty_grade": "hereditary",
        "unverified": (),
        "marking": {"g_amount_within_limit": "T", "g_eligibility_evidence_present": "T"},
        "caller_formula": FORMULA,
        "kernel_commit": KERNEL_COMMIT,
    }
    return KernelResult(**{**base, **overrides})  # type: ignore[arg-type]


# --- mapping ---------------------------------------------------------------


def test_the_mapping_is_exactly_the_four_kernel_dispositions() -> None:
    assert DISPOSITION_TO_EPISTEMIC == {
        "EARNED": "ESTABLISHED",
        "ON CREDIT": "CONDITIONALLY_SUPPORTED",
        "OPEN": "UNRESOLVED",
        "REFUTED": "REFUTED",
    }


def test_open_never_becomes_refuted() -> None:
    """Not established is not falsified, and the mapping must not blur them."""
    assert epistemic_status_for("OPEN") == "UNRESOLVED"
    assert ("OPEN", "REFUTED") in PROHIBITED_TRANSITIONS


def test_on_credit_never_becomes_established() -> None:
    """A claim riding an unverified link is not grounded."""
    assert epistemic_status_for("ON CREDIT") == "CONDITIONALLY_SUPPORTED"
    assert ("ON CREDIT", "ESTABLISHED") in PROHIBITED_TRANSITIONS


def test_a_disposition_outside_the_vocabulary_is_refused() -> None:
    with pytest.raises(WarrantError, match="outside the kernel vocabulary"):
        epistemic_status_for("PROBABLY_FINE")


# --- hash projections ------------------------------------------------------


def test_the_formula_hash_is_over_the_kernel_rendering_not_the_caller_string() -> None:
    assert expected_formula_hash(RENDERED) != expected_formula_hash(FORMULA)
    assert expected_formula_hash(RENDERED).startswith("sha384:")


def test_the_output_hash_excludes_presentational_and_input_fields() -> None:
    """`why` and `marking` must not move the output digest."""
    first = expected_output_hash(
        rendered_formula=RENDERED,
        disposition="EARNED",
        raw_verdict="T",
        warranty_grade="hereditary",
        unverified_ground_ids=[],
    )
    warrant = build_warrant(
        _result(),
        warrant_artifact_id="warrant:test",
        claim_id="claim:test",
        ground_epoch={"scope_id": "s", "sequence": 1, "authority_id": "a"},
        ground_set_hash="sha256:" + "0" * 64,
        source_anchor_ids=["anchor:1"],
        admission_ids=["adm:1"],
        generated_at="2027-05-15T00:00:00Z",
        valid_from="2027-05-15T00:00:00Z",
        valid_until=None,
        revocation_references=[],
    )
    assert warrant["output_hash"] == first


# --- warrant artifact ------------------------------------------------------


@pytest.fixture
def warrant() -> dict[str, Any]:
    return build_warrant(
        _result(),
        warrant_artifact_id="warrant:test",
        claim_id="claim:test",
        ground_epoch={"scope_id": "s", "sequence": 1, "authority_id": "a"},
        ground_set_hash="sha256:" + "1" * 64,
        source_anchor_ids=["anchor:1"],
        admission_ids=["adm:1"],
        generated_at="2027-05-15T00:00:00Z",
        valid_from="2027-05-15T00:00:00Z",
        valid_until=None,
        revocation_references=["revocation:x"],
    )


def test_the_warrant_carries_every_required_field(repo_root: Path, warrant: dict[str, Any]) -> None:
    schema = json.loads(
        (repo_root / "schemas" / "proposed" / "warrant-artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    missing = sorted(set(schema["required"]) - set(warrant))
    assert missing == []


def test_the_warrant_validates_against_the_proposed_contract(
    repo_root: Path, warrant: dict[str, Any]
) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (repo_root / "schemas" / "proposed" / "warrant-artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(warrant)


def test_the_warrant_pins_the_profile_and_the_kernel(warrant: dict[str, Any]) -> None:
    assert warrant["kernel_profile_id"] == KERNEL_PROFILE_ID
    assert warrant["canonicalization_profile_id"] == CANONICALIZATION_PROFILE_ID
    assert warrant["kernel_commit"] == KERNEL_COMMIT


def test_dependency_ids_and_unverified_ground_ids_are_disjoint() -> None:
    result = _result(
        disposition="OPEN",
        raw_verdict="F",
        warranty_grade="until-verification",
        unverified=("g_eligibility_evidence_present",),
        marking={"g_amount_within_limit": "T", "g_eligibility_evidence_present": "Z"},
    )
    warrant = build_warrant(
        result,
        warrant_artifact_id="warrant:open",
        claim_id="claim:open",
        ground_epoch={"scope_id": "s", "sequence": 1, "authority_id": "a"},
        ground_set_hash="sha256:" + "2" * 64,
        source_anchor_ids=["anchor:1"],
        admission_ids=["adm:1"],
        generated_at="2027-05-15T00:00:00Z",
        valid_from="2027-05-15T00:00:00Z",
        valid_until=None,
        revocation_references=[],
    )
    dependencies = list(warrant["dependency_ids"])
    unverified = list(warrant["unverified_ground_ids"])
    assert dependencies == ["g_amount_within_limit"]
    assert unverified == ["g_eligibility_evidence_present"]
    assert not set(dependencies) & set(unverified)


def test_the_warrant_states_its_own_limitations(warrant: dict[str, Any]) -> None:
    joined = " ".join(str(item) for item in list(warrant["limitations"]))
    assert "PROPOSED / NOT ADMITTED" in joined
    assert "not an institutional warrant" in joined
    assert "operationally inert" in joined


# --- the bridge ------------------------------------------------------------


def test_resolve_refuses_to_guess_at_a_checkout() -> None:
    with pytest.raises(WarrantError, match="no ZTL checkout supplied"):
        resolve_ztl_path(None, environ={})


def test_the_bridge_refuses_a_checkout_at_the_wrong_commit(repo_root: Path, tmp_path: Path) -> None:
    """Fail closed before the kernel is imported, not after."""
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "adapters" / "ztl" / "demo_bridge.py"),
            "--ztl",
            str(tmp_path),
        ],
        input=json.dumps({"formula": "a", "marking": {"a": "T"}}),
        capture_output=True,
        text=True,
        check=False,
    )
    response = json.loads(completed.stdout)
    assert response["ok"] is False
    assert response["error_code"] in {"ZTL_CHECKOUT_UNREADABLE", "ZTL_PIN_MISMATCH"}


def test_the_bridge_refuses_a_marking_outside_the_alphabet(repo_root: Path, tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "adapters" / "ztl" / "demo_bridge.py"),
            "--ztl",
            str(tmp_path),
        ],
        input=json.dumps({"formula": "a", "marking": {"a": "MAYBE"}}),
        capture_output=True,
        text=True,
        check=False,
    )
    response = json.loads(completed.stdout)
    assert response["ok"] is False
    assert response["error_code"] == "BAD_REQUEST"


@live_ztl
def test_live_kernel_reproduces_the_three_reachable_dispositions(repo_root: Path) -> None:
    """EARNED, REFUTED and OPEN, from the pinned kernel, in one test."""
    ztl = _ztl_checkout()
    assert ztl is not None
    cases = {
        ("T", "T"): ("EARNED", "T", "hereditary"),
        ("F", "T"): ("REFUTED", "F", "hereditary"),
    }
    for (amount, evidence), (disposition, verdict, grade) in cases.items():
        result = invoke_kernel(
            formula=FORMULA,
            marking={"g_amount_within_limit": amount, "g_eligibility_evidence_present": evidence},
            repo_root=repo_root,
            ztl_path=ztl,
        )
        assert (result.disposition, result.raw_verdict, result.warranty_grade) == (
            disposition,
            verdict,
            grade,
        )
        assert result.rendered_formula == RENDERED
        assert result.kernel_commit == KERNEL_COMMIT

    unmarked = invoke_kernel(
        formula=FORMULA,
        marking={"g_amount_within_limit": "T"},
        repo_root=repo_root,
        ztl_path=ztl,
    )
    # Unsupplied means unverified, not false: OPEN, never REFUTED.
    assert unmarked.disposition == "OPEN"
    assert unmarked.unverified == ("g_eligibility_evidence_present",)
    assert epistemic_status_for(unmarked.disposition) == "UNRESOLVED"


# --- runtime warrant-binding validation ------------------------------------


@pytest.fixture
def binding_inputs(repo_root: Path) -> dict[str, Any]:
    """A warrant and the bindings it legitimately satisfies."""
    from oic.demo_compiler import canonical_json_digest
    from oic.demo_runtime import compile_scenario, load_scenario

    scenario = load_scenario(repo_root)
    policy = compile_scenario(scenario)["v1"]
    marking = {"g_amount_within_limit": "T", "g_eligibility_evidence_present": "T"}
    warrant = build_warrant(
        _result(marking=marking),
        warrant_artifact_id="warrant:binding",
        claim_id="claim:binding",
        ground_epoch={"scope_id": scenario.scope_ref, "sequence": 1, "authority_id": "a"},
        ground_set_hash=canonical_json_digest(sorted(marking)),
        source_anchor_ids=[str(a["anchor_id"]) for a in policy.control_envelope["source_anchors"]],
        admission_ids=[str(i) for i in policy.control_envelope["admission_ids"]],
        generated_at="2027-05-15T00:00:00Z",
        valid_from="2027-05-15T00:00:00Z",
        valid_until=None,
        revocation_references=[],
    )
    schema = json.loads(
        (repo_root / "schemas" / "proposed" / "warrant-artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        "warrant": warrant,
        "kwargs": {
            "runtime_binding": policy.runtime_binding,
            "control_envelope": policy.control_envelope,
            "envelope_digest": policy.envelope_digest,
            "source_version_set_hash": canonical_json_digest([policy.source.content_hash]),
            "admission_version": canonical_json_digest(
                [r["admission_id"] for r in policy.admission_records]
            ),
            "ground_set_hash": canonical_json_digest(sorted(marking)),
            "evaluated_at": "2027-05-15T00:00:00Z",
            "schema": schema,
        },
    }


def test_a_legitimate_warrant_binding_validates(binding_inputs: dict[str, Any]) -> None:
    findings = validate_warrant_binding(binding_inputs["warrant"], **binding_inputs["kwargs"])
    assert findings == [], [str(f) for f in findings]


def test_a_mutated_warrant_fails_closed(binding_inputs: dict[str, Any]) -> None:
    """One mutation, one finding — and no other component can repair it."""
    mutations: tuple[tuple[str, Any, str], ...] = (
        ("kernel_profile_id", "some-other-kernel-v9", "WB-002"),
        ("canonicalization_profile_id", "not-the-bound-profile", "WB-002"),
        ("formula_hash", "sha384:" + "0" * 96, "WB-003"),
        ("kernel_commit", "0" * 40, "WB-004"),
        ("admission_ids", ["adm:invented"], "WB-005"),
        ("source_anchor_ids", ["anchor:invented"], "WB-005"),
        ("ground_set_hash", "sha256:" + "0" * 64, "WB-008"),
        ("warranty_grade", "sound", "WB-009"),
        ("output_hash", "sha256:" + "0" * 64, "WB-011"),
    )
    for field, value, rule in mutations:
        mutated = {**binding_inputs["warrant"], field: value}
        findings = validate_warrant_binding(mutated, **binding_inputs["kwargs"])
        assert findings, f"mutating {field} produced no finding"
        assert rule in {finding.rule_id for finding in findings}, field


def test_a_warrant_outside_its_validity_interval_fails(binding_inputs: dict[str, Any]) -> None:
    kwargs = {**binding_inputs["kwargs"], "evaluated_at": "2026-01-01T00:00:00Z"}
    findings = validate_warrant_binding(binding_inputs["warrant"], **kwargs)
    assert "WB-007" in {finding.rule_id for finding in findings}


def test_a_recomputed_version_binding_mismatch_fails(binding_inputs: dict[str, Any]) -> None:
    kwargs = {**binding_inputs["kwargs"], "source_version_set_hash": "sha256:" + "0" * 64}
    findings = validate_warrant_binding(binding_inputs["warrant"], **kwargs)
    assert "WB-006" in {finding.rule_id for finding in findings}


def test_the_runtime_validator_does_not_import_the_test_helper() -> None:
    """A runtime whose contract lives in tests/ has no contract when tests are absent."""
    import ast
    import inspect

    import oic.demo_ztl as module

    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "semantic_conformance" not in node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "semantic_conformance" not in alias.name
