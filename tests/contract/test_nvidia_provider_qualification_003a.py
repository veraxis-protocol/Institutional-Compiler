from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-003a"

PLAN = BENCH / "PLAN-v0.1.json"
PREREG = BENCH / "PREREGISTRATION.md"
FREEZE = BENCH / "PLAN-FREEZE-v0.1.json"

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_003a.py"

TARGET_DIR = ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a"

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_FREEZE = TARGET_DIR / "PLAN-FREEZE-v0.2.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"

TARGET_INSTRUMENT = ROOT / "scripts/characterize_definition_ontology_discrimination_003a.py"

TARGET_TEST = ROOT / "tests/test_definition_ontology_discrimination_003a.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_exact_qualification_package() -> None:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))

    assert freeze["plan_sha256"] == sha(PLAN)

    assert freeze["preregistration_sha256"] == sha(PREREG)

    assert freeze["qualification_instrument_sha256"] == sha(SCRIPT)

    assert freeze["contract_test_sha256"] == sha(Path(__file__))

    assert freeze["provider_call_made"] is False
    assert freeze["model_call_made"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["semantic_successor_authorized"] is False


def test_exact_ontology_003a_successor_binding() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    assert plan["semantic_successor_target"] == {
        "work_order": "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A",
        "commit_sha": "33f2504a8da56256cdd397c66237613f45030c40",
        "plan_sha256": sha(TARGET_PLAN),
        "preregistration_sha256": sha(TARGET_PREREG),
        "freeze_v0_2_sha256": sha(TARGET_FREEZE),
        "instrument_sha256": sha(TARGET_INSTRUMENT),
        "contract_test_sha256": sha(TARGET_TEST),
        "request_materialization_sha256": sha(TARGET_MANIFEST),
    }


def test_semantic_target_materialization_is_complete() -> None:
    manifest = json.loads(TARGET_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["request_count"] == 36
    assert manifest["arm_a_count"] == 18
    assert manifest["arm_b_count"] == 18

    assert manifest["provider_constructed"] is False
    assert manifest["network_request_made"] is False
    assert manifest["model_call_made"] is False


def test_probe_semantics_unchanged_from_003() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    assert plan["transport_probe_semantics_vs_003"] == "UNCHANGED"

    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0

    assert plan["probe_spec_sha256"] == (
        "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
    )

    assert [item["probe_id"] for item in plan["probes"]] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_fresh_gate_has_no_remediation_dependency() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    source = SCRIPT.read_text(encoding="utf-8")

    assert plan["fresh_provider_qualification"] is True

    assert "remediation" not in source.casefold()
    assert "remediation" not in json.dumps(plan).casefold()


def test_only_qualified_authorizes_ontology_003a() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    source = SCRIPT.read_text(encoding="utf-8")

    assert plan["authorization_rule"].startswith("Only QUALIFIED")

    assert '"semantic_successor_authorized": disposition == "QUALIFIED"' in source


def test_claim_ceiling_preserved() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    assert plan["semantic_hypothesis"] is None

    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architectural_change_authorized"] is False
    assert plan["independent_validation_claim"] is False
