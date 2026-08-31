"""Contract tests for Definition Ontology Discrimination 001."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.contract

SCRIPT = Path("scripts/characterize_definition_ontology_discrimination.py")
PLAN = Path("benchmarks/characterization/definition-ontology-discrimination-001/PLAN-v0.1.json")
FREEZE_V1 = Path(
    "benchmarks/characterization/definition-ontology-discrimination-001/PLAN-FREEZE-v0.1.json"
)
FREEZE_V2 = Path(
    "benchmarks/characterization/definition-ontology-discrimination-001/PLAN-FREEZE-v0.2.json"
)
CONTRACT_TEST = Path("tests/contract/test_definition_ontology_discrimination_001.py")
CORPUS = Path("benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json")
PRODUCTION = Path("src/oic/interpretation_proposal.py")

STARTING_SHA = "f060dc60620c5ee4f72be7846915b80872afa00f"
PLAN_SHA = "eda5025fbdcb2a8ef4154930ef6e5a9794d0e472696c863639ef3b5cd617a4f3"
CORPUS_SHA = "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
PRODUCTION_SHA = "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"
ORIGINAL_INSTRUMENT_SHA = "c4d15aaed9010586dc47600ef9e4283a5abf167c55fad112136798d5e6a818b6"


def _load_script(repo_root: Path) -> ModuleType:
    path = repo_root / SCRIPT
    spec = importlib.util.spec_from_file_location("_definition_ontology_001", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _load_script(repo_root)


@pytest.fixture(scope="module")
def plan(repo_root: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((repo_root / PLAN).read_text(encoding="utf-8"))
    return value


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((repo_root / CORPUS).read_text(encoding="utf-8"))
    return value


def test_frozen_inputs_and_plan_hashes(repo_root: Path, plan: dict[str, Any]) -> None:
    freeze_v1 = json.loads((repo_root / FREEZE_V1).read_text(encoding="utf-8"))
    freeze_v2 = json.loads((repo_root / FREEZE_V2).read_text(encoding="utf-8"))
    assert (
        freeze_v1["starting_sha"]
        == freeze_v2["starting_sha"]
        == plan["starting_sha"]
        == STARTING_SHA
    )
    assert hashlib.sha256((repo_root / PLAN).read_bytes()).hexdigest() == PLAN_SHA
    assert freeze_v1["plan_sha256"] == freeze_v2["plan_sha256"] == PLAN_SHA
    assert hashlib.sha256((repo_root / CORPUS).read_bytes()).hexdigest() == CORPUS_SHA
    assert hashlib.sha256((repo_root / PRODUCTION).read_bytes()).hexdigest() == PRODUCTION_SHA
    assert plan["production_interpretation_proposal_sha256"] == PRODUCTION_SHA

    freeze_v1_sha = hashlib.sha256((repo_root / FREEZE_V1).read_bytes()).hexdigest()
    assert freeze_v1["instrument_sha256"] == ORIGINAL_INSTRUMENT_SHA
    assert freeze_v2["supersedes_freeze_sha256"] == freeze_v1_sha
    assert freeze_v2["prior_instrument_sha256"] == ORIGINAL_INSTRUMENT_SHA
    assert (
        hashlib.sha256((repo_root / SCRIPT).read_bytes()).hexdigest()
        == freeze_v2["instrument_sha256"]
    )
    assert (
        hashlib.sha256((repo_root / CONTRACT_TEST).read_bytes()).hexdigest()
        == freeze_v2["contract_test_sha256"]
    )
    assert freeze_v2["semantic_change"] is False
    assert freeze_v2["plan_preserved_unchanged"] is True
    assert freeze_v2["live_run_executed"] is False
    assert freeze_v2["model_call_made"] is False


def test_exact_six_specimens_and_36_request_plan(
    harness: ModuleType, corpus: dict[str, Any], plan: dict[str, Any]
) -> None:
    assert harness.SELECTED_SPECIMENS == (
        "IIR-005",
        "IIR-006",
        "IIR-023",
        "IIR-024",
        "IIR-027",
        "IIR-028",
    )
    assert harness.PRIMARY_DEFINITIONS == ("IIR-005", "IIR-023", "IIR-024")
    assert harness.CONTROL_SPECIMENS == ("IIR-006", "IIR-027", "IIR-028")
    materialized = harness.build_plan(corpus)
    harness.validate_plan(corpus, materialized)
    assert len(materialized) == plan["planned_requests"] == 36
    assert [item.to_json() for item in materialized] == plan["request_plan"]


def test_deterministic_paired_interleaving(harness: ModuleType, corpus: dict[str, Any]) -> None:
    materialized = harness.build_plan(corpus)
    for specimen_id in harness.SELECTED_SPECIMENS:
        for run_index in (1, 2, 3):
            pair = [
                item.arm
                for item in materialized
                if item.specimen_id == specimen_id and item.run_index == run_index
            ]
            expected = list(harness.ARMS if run_index % 2 else tuple(reversed(harness.ARMS)))
            assert pair == expected


def test_arm_a_is_production_and_arm_b_has_exactly_one_fixed_delta(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    v2 = harness.load_v2()
    v1 = v2.load_v1()
    scoped = harness.selected_corpus(corpus)
    for specimen in scoped["specimens"]:
        arm_a = harness.arm_a_user_prompt(v2, v1, specimen)
        arm_b = harness.arm_b_user_prompt(v2, v1, specimen)
        assert harness.ONTOLOGY_CLARIFICATION_BLOCK not in arm_a
        assert arm_b.count(harness.ONTOLOGY_CLARIFICATION_BLOCK) == 1
        assert arm_b.replace(harness.ONTOLOGY_CLARIFICATION_BLOCK, "", 1) == arm_a


def test_clarification_contains_no_specimen_hint_or_gold(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    block = harness.ONTOLOGY_CLARIFICATION_BLOCK
    folded = block.casefold()
    assert "unit_type" not in folded
    assert "earlier stage proposed" not in folded
    assert "gold" not in folded
    assert "expected" not in folded
    assert "iir-" not in folded
    assert "constitutive_definition" in folded
    assert "literal proposition" in folded

    for specimen in harness.selected_corpus(corpus)["specimens"]:
        unit_type = specimen["candidate"]["unit_type"]
        # No specimen-specific candidate type is interpolated into the block.
        if unit_type.casefold() not in {"definition"}:
            assert unit_type.casefold() not in folded


def test_controls_cover_nearest_confound_and_nondefinition_forces(plan: dict[str, Any]) -> None:
    roles = {item["specimen_id"]: item for item in plan["selected_specimens"]}
    assert roles["IIR-006"]["expected_force"] == "DELEGATION"
    assert roles["IIR-027"]["expected_force"] == "ADVISORY"
    assert roles["IIR-028"]["expected_force"] == "PERMISSION"


def test_decision_rule_is_load_bearing_for_b_only_control_regression(
    harness: ModuleType,
) -> None:
    assert (
        harness.decide(
            b_definition_correct=9,
            paired_primary_improvements=9,
            b_only_control_force_defects=1,
            definition_slots_no_decline=True,
        )
        == "REGRESSION"
    )
    assert (
        harness.decide(
            b_definition_correct=9,
            paired_primary_improvements=9,
            b_only_control_force_defects=0,
            definition_slots_no_decline=True,
        )
        == "SUPPORTS_ONTOLOGY_CLARIFICATION"
    )
    assert (
        harness.decide(
            b_definition_correct=9,
            paired_primary_improvements=5,
            b_only_control_force_defects=0,
            definition_slots_no_decline=True,
        )
        == "INCONCLUSIVE_EFFECT"
    )
    assert (
        harness.decide(
            b_definition_correct=3,
            paired_primary_improvements=3,
            b_only_control_force_defects=0,
            definition_slots_no_decline=True,
        )
        == "REFUTES_SIMPLE_ONTOLOGY_CLARIFICATION"
    )


def test_offline_preflight_constructs_no_provider_or_receipt(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, harness: ModuleType
) -> None:
    target = repo_root / ".local/definition-ontology-should-not-exist.json"
    monkeypatch.setattr(harness, "RECEIPT_PATH", target)
    assert harness.main([]) == 0
    assert not target.exists()


def test_claim_ceiling_and_no_architectural_overreach(plan: dict[str, Any]) -> None:
    assert plan["live_run_executed"] is False
    assert plan["model_call_made"] is False
    assert plan["canonicalization_implemented"] is False
    assert plan["institutional_ir_runtime_implemented"] is False
    assert plan["production_prompt_changed"] is False
    assert plan["independent_validation_claim"] is False
    assert plan["self_adjudication"] == "NOT SELF-ADJUDICATED"
    assert "revised Institutional IR ontology" in plan["claim_ceiling"]
