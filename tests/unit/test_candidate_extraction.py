"""SEMANTIC-001 fail-closed tests for bounded candidate extraction."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from oic.candidate_extraction import (
    CandidateExtractionError,
    CandidateExtractionResult,
    _extract_text,
    extract_authorized_candidates,
)


def _result(repo_root: Path) -> CandidateExtractionResult:
    return extract_authorized_candidates(repo_root)


def _isolated(repo_root: Path, tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relpath in (
        "benchmarks/preflight/code-start-v0.1/SOURCE-SET.json",
        "benchmarks/preflight/code-start-v0.1/sources",
    ):
        source = repo_root / relpath
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return root


def _schema_validator(repo_root: Path, name: str) -> Draft202012Validator:
    documents: dict[str, Any] = {}
    for path in (repo_root / "schemas/draft").glob("*.schema.json"):
        document = json.loads(path.read_text("utf-8"))
        documents[document["$id"]] = document
    registry: Registry[Any] = Registry()
    for identifier, document in documents.items():
        registry = registry.with_resource(identifier, Resource.from_contents(document, DRAFT202012))
    schema = documents[f"https://openinstitutionalcompiler.org/schemas/draft/{name}"]
    return Draft202012Validator(schema, registry=registry)


def test_expected_candidate_set_and_counts(repo_root: Path) -> None:
    result = _result(repo_root)
    fixture = json.loads(
        (repo_root / "benchmarks/preflight/semantic-001/EXPECTED-CANDIDATES.json").read_text(
            "utf-8"
        )
    )
    observed = {
        (
            unit["source_anchors"][0]["source_id"],
            unit["unit_type"],
            unit["actor"],
            unit["action"],
            unit["object"],
            tuple(unit["conditions"]),
        )
        for unit in result.units
    }
    expected = {
        (
            item["source_id"],
            item["unit_type"],
            item["actor"],
            item["action"],
            item["object"],
            tuple(item["conditions"]),
        )
        for item in fixture["candidates"]
    }
    assert observed == expected
    assert len(result.units) == fixture["expected_total"] == 14
    assert Counter(u["source_anchors"][0]["source_id"] for u in result.units) == {
        "SYN-NS-GOV-1": 11,
        "SYN-NS-PROC-1": 1,
        "SYN-NS-AMEND-2": 2,
    }


def test_nodes_units_and_anchors_validate_and_refer(repo_root: Path) -> None:
    result = _result(repo_root)
    node_validator = _schema_validator(repo_root, "source-node.schema.json")
    unit_validator = _schema_validator(repo_root, "candidate-normative-unit.schema.json")
    anchor_validator = _schema_validator(repo_root, "source-anchor.schema.json")
    nodes = {node["node_id"]: node for node in result.nodes}
    assert len(nodes) == len(result.nodes)
    for node in result.nodes:
        node_validator.validate(node)
    for unit in result.units:
        unit_validator.validate(unit)
        assert len(unit["source_anchors"]) == 1
        anchor = unit["source_anchors"][0]
        anchor_validator.validate(anchor)
        node = nodes[anchor["node_id"]]
        digest = f"sha256:{hashlib.sha256(anchor['quote'].encode()).hexdigest()}"
        assert anchor["source_id"] == node["source_id"]
        assert anchor["quote"] == node["text"]
        assert anchor["content_hash"] == node["content_hash"] == digest


def test_extraction_is_byte_deterministic(repo_root: Path) -> None:
    first = _result(repo_root)
    second = _result(repo_root)
    assert first == second
    assert json.dumps(first.nodes, sort_keys=True) == json.dumps(second.nodes, sort_keys=True)
    assert json.dumps(first.units, sort_keys=True) == json.dumps(second.units, sort_keys=True)


def test_machine_state_ceilings_and_no_admission_artifacts(repo_root: Path) -> None:
    result = _result(repo_root)
    assert all(unit["interpretation_state"] == "extracted" for unit in result.units)
    assert all(unit["epistemic_state"] == "uncertain" for unit in result.units)
    assert all(unit["confidence"] is None for unit in result.units)
    assert all(unit["alternatives"] == [] for unit in result.units)
    assert not hasattr(result, "admissions")
    assert not hasattr(result, "institutional_ir")
    assert not hasattr(result, "control_envelopes")


def test_currentness_stale_visibility_and_independent_support(repo_root: Path) -> None:
    result = _result(repo_root)
    high = [u for u in result.units if u["action"] == "TEST_PURCHASE_HIGH"]
    by_source = {u["source_anchors"][0]["source_id"]: u for u in high}
    assert by_source["SYN-NS-PROC-1"]["lifecycle_state"] == "superseded"
    assert by_source["SYN-NS-GOV-1"]["lifecycle_state"] == "proposed"
    assert by_source["SYN-NS-AMEND-2"]["lifecycle_state"] == "proposed"
    assert by_source["SYN-NS-GOV-1"]["unit_id"] != by_source["SYN-NS-AMEND-2"]["unit_id"]


def test_emergency_and_referral_meanings_remain_separate(repo_root: Path) -> None:
    result = _result(repo_root)
    emergency = next(u for u in result.units if u["action"] == "TEST_EMERGENCY")
    assert emergency["conditions"] == ["emergency record present", "Approver-A approval present"]
    referral = [u for u in result.units if u["action"] in {"refer", "treat referral as approval"}]
    assert len(referral) == 2


def test_unsupported_normative_looking_text_is_diagnostic_only() -> None:
    result = _extract_text(
        "SYN-TEST-NEW",
        "Managers should generally use reasonable judgment.",
        "proposed",
    )
    assert result.units == ()
    assert len(result.nodes) == 1
    assert result.diagnostics[0]["code"] == "UNSUPPORTED_NORMATIVE_PATTERN"


def test_controlled_grammar_is_not_keyed_to_northstar_identity() -> None:
    result = _extract_text(
        "SYN-OTHER-1",
        "Operator means a fictional reviewer. TEST_PURCHASE_LOW requires Approver-Z.",
        "proposed",
    )
    assert {(u["unit_type"], u["actor"], u["action"]) for u in result.units} == {
        ("definition", "Operator", "means"),
        ("condition", None, "TEST_PURCHASE_LOW"),
    }


def test_mutated_source_bytes_are_refused(repo_root: Path, tmp_path: Path) -> None:
    root = _isolated(repo_root, tmp_path)
    path = root / (
        "benchmarks/preflight/code-start-v0.1/sources/SYNTHETIC-NORTHSTAR-GOVERNANCE-v1.txt"
    )
    path.write_text(path.read_text("utf-8") + "mutation", encoding="utf-8")
    with pytest.raises(CandidateExtractionError, match="source digest mismatch"):
        extract_authorized_candidates(root)


@pytest.mark.parametrize("field", ["path", "sha256", "source_id"])
def test_source_set_mismatch_is_refused(repo_root: Path, tmp_path: Path, field: str) -> None:
    root = _isolated(repo_root, tmp_path)
    path = root / "benchmarks/preflight/code-start-v0.1/SOURCE-SET.json"
    source_set = json.loads(path.read_text("utf-8"))
    item = next(i for i in source_set["sources"] if i["source_id"] == "SYN-NS-GOV-1")
    item[field] = "wrong"
    path.write_text(json.dumps(source_set), encoding="utf-8")
    with pytest.raises(CandidateExtractionError, match="source-set mismatch"):
        extract_authorized_candidates(root)


def test_header_currentness_mismatch_is_refused_before_meaning(
    repo_root: Path, tmp_path: Path
) -> None:
    root = _isolated(repo_root, tmp_path)
    source_path = root / (
        "benchmarks/preflight/code-start-v0.1/sources/SYNTHETIC-NORTHSTAR-PROCEDURE-v1.txt"
    )
    payload = source_path.read_text("utf-8").replace("SYNTHETIC_SUPERSEDED", "SYNTHETIC_CURRENT")
    source_path.write_text(payload, encoding="utf-8")
    set_path = root / "benchmarks/preflight/code-start-v0.1/SOURCE-SET.json"
    source_set = json.loads(set_path.read_text("utf-8"))
    item = next(i for i in source_set["sources"] if i["source_id"] == "SYN-NS-PROC-1")
    item["sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    set_path.write_text(json.dumps(source_set), encoding="utf-8")
    with pytest.raises(CandidateExtractionError, match="source-set mismatch"):
        extract_authorized_candidates(root)


def test_ca3_is_outside_semantic_scope(repo_root: Path) -> None:
    result = _result(repo_root)
    assert all(node["source_id"] != "CA-3" for node in result.nodes)
