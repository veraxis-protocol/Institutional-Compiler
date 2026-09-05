"""Offline acceptance and fail-closed mutation checks for the bounded promotion."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.contract


def gate(root: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "bounded_gate", root / "scripts/verify_code_start_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_demo(root: Path) -> bytes:
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(token in key.upper() for token in ("API_KEY", "NVIDIA", "ANTHROPIC"))
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    program = (
        "import socket,runpy; "
        "socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('NETWORK FORBIDDEN')); "
        "socket.create_connection=socket.socket; "
        "runpy.run_path('scripts/demo_bounded_semantic_path.py',run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], cwd=root, env=env, capture_output=True, check=True
    )
    assert result.stderr == b""
    return result.stdout


def test_demo_two_runs_are_identical_and_do_not_write(repo_root: Path) -> None:
    before = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all"], cwd=repo_root
    )
    first, second = run_demo(repo_root), run_demo(repo_root)
    assert first == second
    assert (
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=all"], cwd=repo_root
        )
        == before
    )
    output = json.loads(first)
    assert (
        first
        == json.dumps(
            output, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    assert output["scope"] == "SYNTHETIC_BOUNDED_REFERENCE_IMPLEMENTATION"
    assert output["review"]["agreement_state"] == "DIVERGENT"
    assert len(output["review"]["proposal_sets"]) == 2
    assert output["review"]["institutional_admission"] is False
    assert output["admission"]["admission_state"] == "ADMITTED"
    assert output["proposal"]["proposal_state"] == "PROVISIONAL"
    assert output["proposal"]["epistemic_state"] == "uncertain"
    assert output["negative_path"] == {
        "missing_authority_state": "MISSING_AUTHORITY_EVIDENCE",
        "interpretation": "REFUSED_BEFORE_PROVIDER",
        "malformed_authority": "REFUSED_AT_INPUT_BOUNDARY",
    }
    assert output["ceilings"]["independent_validation"] is False
    source = (repo_root / "benchmarks/demo/bounded-semantic-path/SOURCE.txt").read_text()
    for candidate in output["review"]["candidates_by_id"].values():
        assert candidate["candidate_span"] in source
    slots = {a["slot"] for a in output["proposal"]["proposed_assertions"]}
    assert len(slots) == 11
    assert {"condition", "exception", "temporal_qualifier", "definiendum", "definiens"} <= slots
    assert output["proposal"]["proposed_unresolved_references"] == [
        {"reference_text": "section SYN-9", "reference_kind": "INTERNAL_PROVISION"}
    ]


@pytest.fixture
def gate_tree(repo_root: Path, tmp_path: Path) -> Path:
    """Copy bounded files only; do not copy experiment refs or execute providers."""
    matrix = json.loads((repo_root / "docs/capabilities/CAPABILITY_MATRIX.json").read_bytes())
    paths = set(matrix["authorized_maximum_paths"]) | set(gate(repo_root).ADMITTED_SRC_OIC_PATHS)
    paths.add("docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md")
    for name in paths:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / name, dest)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_self_extension_is_refused(repo_root: Path, gate_tree: Path) -> None:
    module = gate(repo_root)
    path = gate_tree / "docs/capabilities/CAPABILITY_MATRIX.json"
    matrix = json.loads(path.read_bytes())
    matrix["authorized_maximum_paths"].append("src/oic/unauthorized.py")
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.GateEvidenceError, match="self-extend"):
        module.validate_bounded_record(gate_tree)


def test_untracked_semantic_extension_is_refused(repo_root: Path, gate_tree: Path) -> None:
    module = gate(repo_root)
    (gate_tree / "src/oic/unauthorized.py").write_text("# not admitted\n")
    with pytest.raises(module.GateEvidenceError, match="unauthorized production"):
        module.validate_bounded_record(gate_tree)


def test_missing_required_path_is_refused(repo_root: Path, gate_tree: Path) -> None:
    module = gate(repo_root)
    (gate_tree / "src/oic/frozen_synthetic_provider.py").unlink()
    with pytest.raises(module.GateEvidenceError, match="missing required"):
        module.validate_bounded_record(gate_tree)


def test_historical_gate_rewrite_is_refused(repo_root: Path, gate_tree: Path) -> None:
    module = gate(repo_root)
    (gate_tree / "docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md").write_text("OPEN")
    with pytest.raises(module.GateEvidenceError, match="historical gate"):
        module.validate_bounded_record(gate_tree)


@pytest.mark.parametrize(
    "key,value",
    [
        ("nvidia", "QUALIFIED"),
        ("canada_redistribution", "CLEAR"),
        ("runtime_authorization", "ESTABLISHED"),
        ("production_compilation", "ESTABLISHED"),
        ("ontology_007r1", "EXECUTED"),
    ],
)
def test_claim_escalation_is_refused(
    repo_root: Path, gate_tree: Path, key: str, value: str | bool
) -> None:
    module = gate(repo_root)
    path = gate_tree / "docs/capabilities/CAPABILITY_MATRIX.json"
    matrix = json.loads(path.read_bytes())
    matrix["ceilings"][key] = value
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.GateEvidenceError, match="ceiling"):
        module.validate_bounded_record(gate_tree)


def test_frozen_source_and_inherited_manifests_are_unchanged(repo_root: Path) -> None:
    base = "9ad37fc80d8f34318c6212ed702de5eab3551cf5"
    for name in ("benchmarks/preflight/SOURCE_MANIFEST.csv", "BOOTSTRAP_MANIFEST.json"):
        assert (repo_root / name).read_bytes() == subprocess.check_output(
            ["git", "show", f"{base}:{name}"], cwd=repo_root
        )


def test_capability_claim_self_extension_is_refused(repo_root: Path, gate_tree: Path) -> None:
    module = gate(repo_root)
    path = gate_tree / "docs/capabilities/CAPABILITY_MATRIX.json"
    matrix = json.loads(path.read_bytes())
    matrix["capabilities"][0]["independent_validation"] = True
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.GateEvidenceError, match="capability claim expanded"):
        module.validate_bounded_record(gate_tree)


def test_independent_validation_evidence_removal_is_refused(
    repo_root: Path, gate_tree: Path
) -> None:
    module = gate(repo_root)
    path = gate_tree / "docs/capabilities/CAPABILITY_MATRIX.json"
    matrix = json.loads(path.read_bytes())
    del matrix["independent_validation_evidence"]
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.GateEvidenceError):
        module.validate_bounded_record(gate_tree)


def test_forged_independent_validation_evidence_is_refused(
    repo_root: Path, gate_tree: Path
) -> None:
    module = gate(repo_root)
    path = gate_tree / "docs/capabilities/CAPABILITY_MATRIX.json"
    matrix = json.loads(path.read_bytes())
    matrix["independent_validation_evidence"]["candidate_commit"] = "0" * 40
    path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(module.GateEvidenceError, match="evidence forged"):
        module.validate_bounded_record(gate_tree)
