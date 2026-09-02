from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007r1.py"
)

MODULE_NAME = "_test_ontology_007r1"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_qualification() -> dict[str, Any]:
    return {
        "work_order":
            "OIC-NVIDIA-PROVIDER-QUALIFICATION-FUTURE",
        "status":
            "CLOSED_EXECUTED_QUALIFIED",
        "provider_qualification_established":
            True,
        "live_disposition":
            "QUALIFIED",
        "semantic_successor_target":
            module.static_target_descriptor(),
        "rerun_authorized":
            False,
        "semantic_hypothesis":
            None,
        "semantic_hypothesis_evaluated":
            False,
        "architecture_change_authorized":
            False,
        "independent_validation_claim":
            False,
    }


def test_identity_and_repair_class() -> None:
    source, _ = module.prereg_context()

    assert module.WORK_ORDER == (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
        "PREDICATE-CARRIER-DISCRIMINATION-007R1"
    )

    assert source.WORK_ORDER == (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
        "PREDICATE-CARRIER-DISCRIMINATION-007"
    )

    repair = load(module.REPAIR_PATH)

    assert repair["repair_class"] == (
        "AUTHORIZATION_BINDING_ONLY"
    )


def test_all_18_semantic_rows_exactly_equal_frozen_o007() -> None:
    rows = module.semantic_materialization()
    frozen = load(module.SOURCE_MANIFEST)["requests"]

    assert len(rows) == 18
    assert rows == frozen


def test_all_request_projections_and_hashes_equal_o007() -> None:
    current = module.semantic_materialization()
    frozen = load(module.SOURCE_MANIFEST)["requests"]

    assert len(current) == len(frozen) == 18

    for r1, old in zip(current, frozen, strict=True):
        assert r1["ordinal"] == old["ordinal"]
        assert r1["specimen_id"] == old["specimen_id"]
        assert r1["run_index"] == old["run_index"]
        assert r1["arm"] == old["arm"]
        assert r1["request"] == old["request"]
        assert r1["request_sha256"] == old["request_sha256"]


def test_materialization_exact() -> None:
    actual = load(module.MATERIALIZATION_PATH)
    expected = module.materialization_document()

    assert actual == expected
    assert actual["request_count"] == 18
    assert actual["pair_count"] == 9
    assert actual["semantic_request_equivalence"] == (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )


def test_semantic_decision_logic_delegated_not_reimplemented() -> None:
    source, _ = module.prereg_context()

    assert source.decide(
        target_treatment_compatible=3,
        paired_improvements=2,
        safety_defect_count=0,
    ) == "SUPPORTS_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"

    assert source.decide(
        target_treatment_compatible=1,
        paired_improvements=0,
        safety_defect_count=0,
    ) == "REFUTES_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"

    assert source.decide(
        target_treatment_compatible=3,
        paired_improvements=3,
        safety_defect_count=1,
    ) == "REGRESSION"


def test_no_specific_qualification_number_hardcoded() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "nvidia-nim-009/EXECUTION-RESULT" not in text
    assert "nvidia-nim-010/EXECUTION-RESULT" not in text

    repair = load(module.REPAIR_PATH)

    contract = repair["qualification_artifact_contract"]

    assert contract["specific_qualification_number_hardcoded"] is False
    assert contract["implicit_latest_selection"] is False
    assert contract["selection_mode"] == "EXPLICIT_PATH_ONLY"


def test_valid_qualification_document_contract() -> None:
    module.validate_qualification_document(
        valid_qualification()
    )


def test_qualification_rejects_wrong_status() -> None:
    q = valid_qualification()
    q["status"] = "CLOSED_EXECUTED_NOT_QUALIFIED"

    with pytest.raises(SystemExit):
        module.validate_qualification_document(q)


def test_qualification_rejects_wrong_target() -> None:
    q = valid_qualification()
    q["semantic_successor_target"] = {
        "work_order": "WRONG"
    }

    with pytest.raises(SystemExit):
        module.validate_qualification_document(q)


def test_qualification_rejects_semantic_result() -> None:
    q = valid_qualification()
    q["semantic_hypothesis"] = {
        "result": "forbidden"
    }

    with pytest.raises(SystemExit):
        module.validate_qualification_document(q)


def test_qualification_rejects_architecture_authority() -> None:
    q = valid_qualification()
    q["architecture_change_authorized"] = True

    with pytest.raises(SystemExit):
        module.validate_qualification_document(q)


def test_static_preflight_requires_no_qualification_artifact() -> None:
    source, source_ctx = module.static_preflight()

    assert source_ctx.plan["live_run_executed"] is False
    assert source.WORK_ORDER.endswith("-007")


def test_live_gate_precedes_provider_construction() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    qpos = text.index(
        "qualification_path, qualification = qualification_prerequisite("
    )

    ppos = text.index(
        "provider = NvidiaNimProvider(",
        qpos,
    )

    assert qpos < ppos


def test_no_production_or_architecture_change() -> None:
    repair = load(module.REPAIR_PATH)
    plan = load(module.PLAN_PATH)
    freeze = module.verify_freeze_v2()

    assert repair["semantic_preservation_contract"][
        "production_interpretation_ruleset_changed"
    ] is False

    assert plan["production_interpretation_ruleset_changed"] is False
    assert plan["architecture_change_authorized"] is False

    assert freeze["production_interpretation_ruleset_changed"] is False
    assert freeze["architecture_change_authorized"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["ontology_007r1_execution_authorized"] is False
