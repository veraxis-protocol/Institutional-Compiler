"""Mutation contract for the RESULT-002 semantic comparator.

DEVELOPMENT_TEST_ONLY. Nothing here invokes the result-bearing path, issues or
consumes an owner authorization, or observes a RESULT-002 result. It proves that
every declared comparison field can independently falsify the comparison, that a
missing or extra case is caught, and that malformed inputs fail closed rather
than passing quietly.

The candidate package shipped this as a standalone script. It is converted to
pytest here without changing a single comparison rule; the comparator module
itself is byte-equivalent in AST to the authoritative candidate.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from oic.result002_compare import compare, main

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.contract

ORACLE_RELPATH = "demo/oic-ztl-oam-slice-001/result-002/RESULT-002-SEMANTIC-ORACLE-v0.1.json"

#: Loaded at import time because the mutation domain is the parametrisation.
REPO_ROOT = Path(__file__).resolve().parents[2]
ORACLE: dict[str, Any] = json.loads((REPO_ROOT / ORACLE_RELPATH).read_text(encoding="utf-8"))
CASE_FIELD_PAIRS = [
    (case_id, field) for case_id in sorted(ORACLE["cases"]) for field in ORACLE["comparison_fields"]
]


def manifest_from_oracle() -> dict[str, Any]:
    """A persisted-manifest shape that agrees with the oracle exactly."""
    return {
        "cases": {
            case_id: {"semantic_projection": copy.deepcopy(values)}
            for case_id, values in ORACLE["cases"].items()
        }
    }


def test_mutation_domain_is_five_cases_by_thirteen_fields() -> None:
    """The 65 is a fact about the oracle, not a number carried in prose."""
    assert len(ORACLE["cases"]) == 5
    assert len(ORACLE["comparison_fields"]) == 13
    assert len(CASE_FIELD_PAIRS) == 65


def test_baseline_passes() -> None:
    report = compare(manifest_from_oracle(), ORACLE)
    assert report["decision"] == "PASS", report
    assert report["mismatch_count"] == 0


@pytest.mark.parametrize(("case_id", "field"), CASE_FIELD_PAIRS)
def test_every_field_can_falsify(case_id: str, field: str) -> None:
    """65 independent mutations, each attributed to its own case and field."""
    manifest = manifest_from_oracle()
    old = manifest["cases"][case_id]["semantic_projection"][field]
    if old is None:
        new: Any = "__MUTATED__"
    elif isinstance(old, bool):
        new = not old
    else:
        new = f"{old}__MUTATED__"
    manifest["cases"][case_id]["semantic_projection"][field] = new

    report = compare(manifest, ORACLE)
    assert report["decision"] == "FAIL", report
    assert any(
        entry.get("case_id") == case_id and entry.get("field") == field
        for entry in report["mismatches"]
    ), report


def test_missing_case_fails() -> None:
    manifest = manifest_from_oracle()
    del manifest["cases"]["case-2"]
    report = compare(manifest, ORACLE)
    assert report["decision"] == "FAIL"
    assert {"case_id": "case-2", "kind": "MISSING_CASE"} in report["mismatches"]


def test_extra_case_fails() -> None:
    manifest = manifest_from_oracle()
    manifest["cases"]["case-extra"] = {"semantic_projection": {}}
    report = compare(manifest, ORACLE)
    assert report["decision"] == "FAIL"
    assert {"case_id": "case-extra", "kind": "EXTRA_CASE"} in report["mismatches"]


def test_missing_field_fails() -> None:
    manifest = manifest_from_oracle()
    del manifest["cases"]["case-1"]["semantic_projection"]["decision_basis"]
    report = compare(manifest, ORACLE)
    assert report["decision"] == "FAIL"
    assert {
        "case_id": "case-1",
        "field": "decision_basis",
        "kind": "MISSING_FIELD",
    } in report["mismatches"]


def test_missing_semantic_projection_fails() -> None:
    manifest = manifest_from_oracle()
    manifest["cases"]["case-3"] = {}
    report = compare(manifest, ORACLE)
    assert report["decision"] == "FAIL"
    assert {
        "case_id": "case-3",
        "kind": "MISSING_SEMANTIC_PROJECTION",
    } in report["mismatches"]


@pytest.fixture
def evidence_root(tmp_path: Path) -> Iterator[Path]:
    """A persisted evidence tree whose manifest agrees with the oracle."""
    root = tmp_path / "evidence"
    (root / "05-evidence").mkdir(parents=True)
    (root / "05-evidence" / "MANIFEST.json").write_text(
        json.dumps(manifest_from_oracle()), encoding="utf-8"
    )
    yield root


def _run_cli(
    monkeypatch: pytest.MonkeyPatch, evidence_root: Path, oracle_path: Path, out: Path
) -> int:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "result002_compare",
            "--evidence-root",
            str(evidence_root),
            "--oracle",
            str(oracle_path),
            "--out",
            str(out),
        ],
    )
    return main()


def test_cli_passes_on_agreeing_manifest(
    monkeypatch: pytest.MonkeyPatch, evidence_root: Path, tmp_path: Path
) -> None:
    out = tmp_path / "report.json"
    assert _run_cli(monkeypatch, evidence_root, REPO_ROOT / ORACLE_RELPATH, out) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["decision"] == "PASS"


def test_cli_fails_closed_on_malformed_oracle(
    monkeypatch: pytest.MonkeyPatch, evidence_root: Path, tmp_path: Path
) -> None:
    bad = tmp_path / "bad-oracle.json"
    bad.write_text("{ not json", encoding="utf-8")
    out = tmp_path / "report.json"

    assert _run_cli(monkeypatch, evidence_root, bad, out) == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "FAIL"
    assert report["mismatches"][0]["kind"] == "COMPARATOR_ERROR"


def test_cli_fails_closed_on_malformed_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "evidence"
    (root / "05-evidence").mkdir(parents=True)
    (root / "05-evidence" / "MANIFEST.json").write_text("{ not json", encoding="utf-8")
    out = tmp_path / "report.json"

    assert _run_cli(monkeypatch, root, REPO_ROOT / ORACLE_RELPATH, out) == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["decision"] == "FAIL"
    assert report["mismatches"][0]["kind"] == "COMPARATOR_ERROR"


def test_cli_fails_closed_on_absent_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out = tmp_path / "report.json"
    assert _run_cli(monkeypatch, tmp_path / "nowhere", REPO_ROOT / ORACLE_RELPATH, out) == 2
    assert json.loads(out.read_text(encoding="utf-8"))["decision"] == "FAIL"
