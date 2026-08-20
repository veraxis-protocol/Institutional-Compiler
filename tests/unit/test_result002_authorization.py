"""RESULT-002: the oracle binding, the comparison stage, and the two gates.

DEVELOPMENT_TEST_ONLY. No owner authorization is created, issued or consumed
here, and no claim-bearing execution is performed. The authorization documents
below are test doubles written into ``tmp_path``; the validator rejects every one
of them that should be rejected, which is the point.

``ValidatedExecutionAuthorization`` is constructed directly in the comparison
tests. That deliberately bypasses the validator, and is stated rather than
hidden: those tests are about what the comparison stage does once a validated
authorization exists, not about how one is obtained. The tests that cover how one
is obtained go through ``load_result_bearing_authorization`` and nothing else.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from oic.demo_runtime import (
    AUTHORIZATION_SCHEMA_V2,
    MACHINE_COMPARED_CEILING,
    RESULT_002_COMPARISON_FILENAME,
    RESULT_002_FAIL,
    RESULT_002_ID,
    RESULT_002_PASS,
    DemoRuntimeError,
    ValidatedExecutionAuthorization,
    _git_head,
    _worktree_is_clean,
    load_result_bearing_authorization,
    load_scenario,
    result_status,
    run_semantic_comparison,
    scenario_bundle_digest,
    verify_evidence_graph,
)

ORACLE_RELPATH = "demo/oic-ztl-oam-slice-001/result-002/RESULT-002-SEMANTIC-ORACLE-v0.1.json"


def _require_clean_worktree(repo_root: Path) -> None:
    if not _worktree_is_clean(repo_root):
        pytest.skip(
            "a validated authorization cannot exist over a dirty tree by design; "
            "commit the branch to exercise these"
        )


def _oracle_digest(repo_root: Path) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256((repo_root / ORACLE_RELPATH).read_bytes()).hexdigest()


@pytest.fixture
def v2_template(repo_root: Path, tmp_path: Path) -> dict[str, Any]:
    """A conforming RESULT-002 successor authorization for this tree."""
    scenario = load_scenario(repo_root)
    return {
        "record_class": "OWNER_DEMO_RESULT_BEARING_EXECUTION_AUTHORIZATION",
        "schema_version": AUTHORIZATION_SCHEMA_V2,
        "authorization_id": "OWNER-DEMO-EXEC-TEST-002",
        "slice_id": "OIC-ZTL-OAM-DEMO-SLICE-001",
        "scenario_id": "synthetic-grant-authority",
        "owner": "ARKADIY_MITEIKO",
        "issued_at": "2027-05-15T00:00:00Z",
        "implementation_commit": _git_head(repo_root),
        "scenario_bundle_digest": scenario_bundle_digest(scenario),
        "ztl_commit": "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b",
        "allowed_output_directory": str(tmp_path),
        "claim_ceiling": MACHINE_COMPARED_CEILING,
        "result_id": RESULT_002_ID,
        "semantic_oracle_path": ORACLE_RELPATH,
        "semantic_oracle_sha256": _oracle_digest(repo_root),
        "authorized_case_ids": ["case-1", "case-2", "case-3", "case-4", "case-5"],
        "authorized_reliance_case_ids": ["case-1"],
        "single_use": True,
        "result_bearing_execution_authorized": True,
        "measured_claim_authorized": True,
        "production_claim_authorized": False,
        "institutional_validity_claim_authorized": False,
        "independent_assurance_claim_authorized": False,
        "RUN004_authorized": False,
    }


def _write(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "authorization-v2.json"
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


# --- the oracle binding -----------------------------------------------------


def test_a_v2_authorization_without_the_oracle_digest_is_rejected(
    repo_root: Path, tmp_path: Path, v2_template: dict[str, Any]
) -> None:
    document = {k: v for k, v in v2_template.items() if k != "semantic_oracle_sha256"}
    with pytest.raises(DemoRuntimeError, match="does not satisfy its schema"):
        load_result_bearing_authorization(
            _write(tmp_path, document), repo_root=repo_root, output_directory=tmp_path
        )


def test_a_wrong_oracle_digest_is_rejected(
    repo_root: Path, tmp_path: Path, v2_template: dict[str, Any]
) -> None:
    document = {**v2_template, "semantic_oracle_sha256": "sha256:" + "0" * 64}
    with pytest.raises(DemoRuntimeError, match="semantic_oracle_sha256"):
        load_result_bearing_authorization(
            _write(tmp_path, document), repo_root=repo_root, output_directory=tmp_path
        )


def test_an_absent_oracle_is_rejected(
    repo_root: Path, tmp_path: Path, v2_template: dict[str, Any]
) -> None:
    document = {**v2_template, "semantic_oracle_path": "demo/nowhere/absent-oracle.json"}
    with pytest.raises(DemoRuntimeError, match="semantic oracle is absent"):
        load_result_bearing_authorization(
            _write(tmp_path, document), repo_root=repo_root, output_directory=tmp_path
        )


def test_the_v1_ceiling_does_not_open_the_v2_path(
    repo_root: Path, tmp_path: Path, v2_template: dict[str, Any]
) -> None:
    """A successor authorization may not borrow the older, weaker ceiling."""
    document = {
        **v2_template,
        "claim_ceiling": "MEASURED_INTERNAL_END_TO_END_TECHNICAL_DEMONSTRATION",
    }
    with pytest.raises(DemoRuntimeError, match="does not satisfy its schema|claim_ceiling"):
        load_result_bearing_authorization(
            _write(tmp_path, document), repo_root=repo_root, output_directory=tmp_path
        )


def test_a_valid_v2_authorization_carries_the_verified_oracle_identity(
    repo_root: Path, tmp_path: Path, v2_template: dict[str, Any]
) -> None:
    _require_clean_worktree(repo_root)
    authorization = load_result_bearing_authorization(
        _write(tmp_path, v2_template), repo_root=repo_root, output_directory=tmp_path
    )
    assert authorization.is_machine_compared
    assert authorization.semantic_oracle_sha256 == _oracle_digest(repo_root)
    assert authorization.semantic_oracle_path == repo_root / ORACLE_RELPATH


def test_the_v1_path_is_untouched_by_the_successor(repo_root: Path) -> None:
    """The immutability the owner authorization requires, asserted rather than assumed."""
    assert (repo_root / "schemas" / "demo" / "execution-authorization.schema.json").is_file()
    v1 = json.loads(
        (repo_root / "schemas" / "demo" / "execution-authorization.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert v1["properties"]["schema_version"]["const"] == "OIC-DEMO-EXECUTION-AUTHORIZATION-v0.1"
    assert "semantic_oracle_sha256" not in v1["properties"]


# --- the comparison stage ---------------------------------------------------


def _double(repo_root: Path, tmp_path: Path) -> ValidatedExecutionAuthorization:
    return ValidatedExecutionAuthorization(
        document={"authorization_id": "DOUBLE"},
        path=tmp_path / "unused.json",
        file_sha256="0" * 64,
        implementation_commit="0" * 40,
        scenario_bundle_digest="sha256:" + "0" * 64,
        ztl_commit="0" * 40,
        allowed_output_directory=tmp_path,
        result_id=RESULT_002_ID,
        semantic_oracle_path=repo_root / ORACLE_RELPATH,
        semantic_oracle_sha256=_oracle_digest(repo_root),
    )


def _evidence_tree(
    repo_root: Path,
    tmp_path: Path,
    *,
    mutate: tuple[str, str] | None,
    value: str = "__MUTATED__",
) -> Path:
    """A persisted package whose manifest agrees with the oracle, or does not."""
    oracle = json.loads((repo_root / ORACLE_RELPATH).read_text(encoding="utf-8"))
    cases = {
        case_id: {"semantic_projection": dict(values)}
        for case_id, values in oracle["cases"].items()
    }
    if mutate is not None:
        case_id, field = mutate
        cases[case_id]["semantic_projection"][field] = value

    root = tmp_path / "evidence"
    (root / "05-evidence").mkdir(parents=True)
    payload = (json.dumps({"cases": cases}, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (root / "05-evidence" / "MANIFEST.json").write_bytes(payload)

    import hashlib

    digest = hashlib.sha256(payload).hexdigest()
    (root / "05-evidence" / "SHA256SUMS").write_bytes(
        f"{digest}  05-evidence/MANIFEST.json\n".encode()
    )
    return root


def test_the_comparison_passes_and_is_persisted_and_integrity_bound(
    repo_root: Path, tmp_path: Path
) -> None:
    root = _evidence_tree(repo_root, tmp_path, mutate=None)
    report = run_semantic_comparison(root, _double(repo_root, tmp_path))

    assert report["decision"] == "PASS"
    assert (root / "05-evidence" / RESULT_002_COMPARISON_FILENAME).is_file()
    assert verify_evidence_graph(root)["verified"] is True


def test_the_comparison_fails_and_the_artifact_survives_the_failure(
    repo_root: Path, tmp_path: Path
) -> None:
    """A mismatch is the result of the experiment, not an error to erase."""
    root = _evidence_tree(repo_root, tmp_path, mutate=("case-2", "authority_reason_code_id"))
    report = run_semantic_comparison(root, _double(repo_root, tmp_path))

    assert report["decision"] == "FAIL"
    assert report["mismatch_count"] >= 1
    assert any(
        entry.get("case_id") == "case-2" and entry.get("field") == "authority_reason_code_id"
        for entry in report["mismatches"]
    )
    persisted = json.loads(
        (root / "05-evidence" / RESULT_002_COMPARISON_FILENAME).read_text(encoding="utf-8")
    )
    assert persisted["decision"] == "FAIL"
    assert verify_evidence_graph(root)["verified"] is True


def test_case_5_epistemic_mutation_also_fails(repo_root: Path, tmp_path: Path) -> None:
    root = _evidence_tree(repo_root, tmp_path, mutate=("case-5", "epistemic_status"))
    report = run_semantic_comparison(root, _double(repo_root, tmp_path))
    assert report["decision"] == "FAIL"
    assert any(entry.get("field") == "epistemic_status" for entry in report["mismatches"])


def test_the_comparator_reads_the_persisted_manifest(repo_root: Path, tmp_path: Path) -> None:
    """What is compared is the file on disk, not what a process believed.

    The manifest here disagrees with the oracle; nothing in memory does. A
    comparator reading an in-memory projection would report PASS.
    """
    root = _evidence_tree(repo_root, tmp_path, mutate=("case-1", "execution_disposition"))
    assert run_semantic_comparison(root, _double(repo_root, tmp_path))["decision"] == "FAIL"


def test_a_missing_manifest_fails_closed(repo_root: Path, tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    (root / "05-evidence").mkdir(parents=True)
    (root / "05-evidence" / "SHA256SUMS").write_bytes(b"")
    report = run_semantic_comparison(root, _double(repo_root, tmp_path))
    assert report["decision"] == "FAIL"
    assert report["mismatches"][0]["kind"] == "COMPARATOR_ERROR"


# --- the two gates ----------------------------------------------------------


@pytest.mark.parametrize(
    ("package_ok", "decision", "expected"),
    [
        (True, "PASS", RESULT_002_PASS),
        (True, "FAIL", RESULT_002_FAIL),
        (False, "PASS", RESULT_002_FAIL),
        (False, "FAIL", RESULT_002_FAIL),
    ],
)
def test_completion_requires_both_gates(package_ok: bool, decision: str, expected: str) -> None:
    assert result_status(package_ok=package_ok, comparison={"decision": decision}) == expected


def test_the_result_001_status_is_unchanged_when_no_oracle_is_bound() -> None:
    assert result_status(package_ok=True, comparison=None) == "RESULT_BEARING_EXECUTION_COMPLETE"
    assert result_status(package_ok=False, comparison=None) == "RESULT_BEARING_EXECUTION_INCOMPLETE"


def test_there_is_no_retry_after_a_comparator_failure(repo_root: Path) -> None:
    """Structural, not behavioural: a retry loop must not exist to be reached.

    Asserted over the syntax tree because a behavioural test can only show that
    a retry did not happen on the paths it exercised.
    """
    tree = ast.parse((repo_root / "src" / "oic" / "demo_runtime.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute_result_bearing_run"
    )
    assert not [node for node in ast.walk(function) if isinstance(node, ast.For | ast.While)]
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_semantic_comparison"
    ]
    assert len(calls) == 1


# --- the injected mutations named in the runbook -----------------------------


@pytest.mark.parametrize(
    ("case_id", "field", "injected"),
    [
        ("case-2", "authority_reason_code_id", "A1"),
        ("case-5", "epistemic_status", "ESTABLISHED"),
    ],
)
def test_an_injected_mutation_prevents_completion(
    repo_root: Path, tmp_path: Path, case_id: str, field: str, injected: str
) -> None:
    """A field mutated in the PERSISTED evidence must block completion.

    Not merely make the comparator function return FAIL — block the result. The
    two mutations are the ones the runbook names, and each is chosen from a
    different semantic dimension: case-2 turns an authority that was never
    evaluated into one that proceeded, and case-5 turns a refuted proposition
    into an established one. Both are exactly the kind of change a
    machine-compared conformance claim exists to catch.
    """
    root = _evidence_tree(repo_root, tmp_path, mutate=(case_id, field), value=injected)
    report = run_semantic_comparison(root, _double(repo_root, tmp_path))

    assert report["decision"] == "FAIL"
    assert report["mismatch_count"] >= 1
    offending = [
        entry
        for entry in report["mismatches"]
        if entry.get("case_id") == case_id and entry.get("field") == field
    ]
    assert offending, report
    assert offending[0]["observed"] == injected

    # the package still verifies, because the FAIL artifact is bound into it
    assert verify_evidence_graph(root)["verified"] is True
    persisted = json.loads(
        (root / "05-evidence" / RESULT_002_COMPARISON_FILENAME).read_text(encoding="utf-8")
    )
    assert persisted["decision"] == "FAIL"

    # and completion is unreachable even with a perfect package
    assert result_status(package_ok=True, comparison=report) == RESULT_002_FAIL
