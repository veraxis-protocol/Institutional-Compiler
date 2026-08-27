"""Fail-closed tests for the non-semantic gate-closure evidence verifier."""

from __future__ import annotations

import copy
import importlib.util
import json
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
