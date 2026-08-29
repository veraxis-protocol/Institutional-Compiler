"""Fail-closed tests for the non-semantic gate-closure evidence verifier."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.contract


def _module(repo_root: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "verify_code_start_gate", repo_root / "scripts/verify_code_start_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evidence(repo_root: Path) -> dict[str, Any]:
    def load(path: str) -> dict[str, Any]:
        value: dict[str, Any] = json.loads((repo_root / path).read_text(encoding="utf-8"))
        return value

    source_set = load("benchmarks/preflight/code-start-v0.1/SOURCE-SET.json")
    return {
        "source_set": source_set,
        "receipts": load("benchmarks/preflight/code-start-v0.1/PROVENANCE.json"),
        "profile": load("docs/contracts/kernel-profiles/ztl-v0.1.json"),
        "veip": load("docs/contracts/VEIP-CODE-START-BOUNDARY-v0.1.json"),
        "gate_text": (
            repo_root / "docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md"
        ).read_text(encoding="utf-8"),
        "source_bytes": {
            item["source_id"]: (repo_root / item["path"]).read_bytes()
            for item in source_set["sources"]
        },
        "active_text": "bounded admitted evidence is current",
        "semantic_paths": [],
    }


def _reject(repo_root: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    module = _module(repo_root)
    evidence = copy.deepcopy(_evidence(repo_root))
    mutate(evidence)
    with pytest.raises(module.GateEvidenceError):
        module.validate_evidence(**evidence)


def _synthetic(evidence: dict[str, Any]) -> dict[str, Any]:
    return next(
        item for item in evidence["source_set"]["sources"] if item["source_id"].startswith("SYN-")
    )


def test_current_evidence_is_valid(repo_root: Path) -> None:
    _module(repo_root).validate_evidence(**_evidence(repo_root))


def test_refuses_synthetic_as_real_authority(repo_root: Path) -> None:
    _reject(
        repo_root,
        lambda e: _synthetic(e).__setitem__("benchmark_authority", "REAL_INSTITUTIONAL_AUTHORITY"),
    )


def test_refuses_missing_synthetic_classification(repo_root: Path) -> None:
    _reject(repo_root, lambda e: _synthetic(e).__setitem__("origin_classification", "UNKNOWN"))


def test_refuses_digest_mutation(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e["source_bytes"].__setitem__("SYN-NS-GOV-1", b"mutated"))


def test_refuses_provenance_mismatch(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e["receipts"]["receipts"][1].__setitem__("sha256", "0" * 64))


def test_refuses_fabricated_government_metadata(repo_root: Path) -> None:
    def mutate(e: dict[str, Any]) -> None:
        item = _synthetic(e)
        item["issuer"] = "Government of Canada"
        item["effective_state"] = "2026-01-01"

    _reject(repo_root, mutate)


@pytest.mark.parametrize(
    ("field", "value"), [("commit", "0" * 40), ("signed_tag", {"name": "wrong"})]
)
def test_refuses_wrong_ztl_identity(repo_root: Path, field: str, value: object) -> None:
    _reject(repo_root, lambda e: e["profile"].__setitem__(field, value))


def test_refuses_wrong_ztl_fixture_index(repo_root: Path) -> None:
    _reject(
        repo_root,
        lambda e: e["profile"]["conformance_fixture_set"].__setitem__("index_sha256", "0" * 64),
    )


def test_refuses_stale_ztl_currentness(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e.__setitem__("active_text", "still in DRAFT pull request #18"))


def test_refuses_tier1_escalation(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e["profile"].__setitem__("tier_1_reproduction", "PASS"))


@pytest.mark.parametrize(
    "field",
    ["executable_runtime_integration", "oic_has_veip_lifecycle_authority", "veip_reinterprets_ztl"],
)
def test_refuses_forbidden_veip_states(repo_root: Path, field: str) -> None:
    _reject(repo_root, lambda e: e["veip"].__setitem__(field, True))


def test_refuses_semantic_implementation(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e.__setitem__("semantic_paths", ["src/oic/semantic_parser.py"]))


def test_refuses_global_manifest_escalation(repo_root: Path) -> None:
    _reject(repo_root, lambda e: e["source_set"].__setitem__("global_manifest_status", "PASS"))


def _isolated_gate_tree(repo_root: Path, tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    required = (
        "src/oic",
        "benchmarks/preflight/code-start-v0.1",
        "benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml",
        "docs/contracts/kernel-profiles/ztl-v0.1.json",
        "docs/contracts/VEIP-CODE-START-BOUNDARY-v0.1.json",
        "docs/contracts/WARRANT-CONTRACT-v0.1.md",
        "adr/ADR-013.md",
        "docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md",
    )
    for relpath in required:
        source = repo_root / relpath
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "model_provider.py",
                    "nvidia_nim.py",
                    "candidate_extraction.py",
                    "review_docket.py",
                ),
            )
        else:
            shutil.copy2(source, target)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    return root


def test_t1_production_detector_accepts_exact_historical_baseline(
    repo_root: Path, tmp_path: Path
) -> None:
    module = _module(repo_root)
    root = _isolated_gate_tree(repo_root, tmp_path)
    assert module.discover_unadmitted_production_paths(root) == []


@pytest.mark.parametrize(
    "relpath",
    ("src/oic/semantic_parser.py", "src/oic/helper.py", "src/oic/newmodule/engine.py"),
)
def test_t2_t3_t4_detector_refuses_any_new_tracked_path(
    repo_root: Path, tmp_path: Path, relpath: str
) -> None:
    module = _module(repo_root)
    root = _isolated_gate_tree(repo_root, tmp_path)
    added = root / relpath
    added.parent.mkdir(parents=True, exist_ok=True)
    added.write_text("# unauthorized pre-gate production path\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", relpath], check=True)
    detected = module.discover_unadmitted_production_paths(root)
    assert relpath in detected
    with pytest.raises(module.GateEvidenceError, match="semantic implementation appeared"):
        module.load_and_validate(root)


def test_t5_detector_refuses_rename_or_substitution(repo_root: Path, tmp_path: Path) -> None:
    module = _module(repo_root)
    root = _isolated_gate_tree(repo_root, tmp_path)
    original = root / "src/oic/paths.py"
    replacement = root / "src/oic/replacement.py"
    original.rename(replacement)
    subprocess.run(["git", "-C", str(root), "add", "-A", "src/oic"], check=True)
    detected = module.discover_unadmitted_production_paths(root)
    assert "src/oic/replacement.py" in detected
    assert "MISSING:src/oic/paths.py" in detected
    with pytest.raises(module.GateEvidenceError, match="semantic implementation appeared"):
        module.load_and_validate(root)


def test_t6_load_and_validate_invokes_discovery_without_manual_parameter(
    repo_root: Path, tmp_path: Path
) -> None:
    module = _module(repo_root)
    root = _isolated_gate_tree(repo_root, tmp_path)
    added = root / "src/oic/helper.py"
    added.write_text("# innocuous name, unauthorized path\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "src/oic/helper.py"], check=True)
    with pytest.raises(module.GateEvidenceError, match="semantic implementation appeared"):
        module.load_and_validate(root)


def test_t7_working_tree_cannot_self_extend_immutable_baseline(
    repo_root: Path, tmp_path: Path
) -> None:
    module = _module(repo_root)
    root = _isolated_gate_tree(repo_root, tmp_path)
    added = root / "src/oic/future_admitted.py"
    added.write_text("# existence does not confer admission\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "src/oic/future_admitted.py"], check=True)
    assert "src/oic/future_admitted.py" not in module.ADMITTED_SRC_OIC_PATHS
    assert module.discover_unadmitted_production_paths(root) == ["src/oic/future_admitted.py"]
