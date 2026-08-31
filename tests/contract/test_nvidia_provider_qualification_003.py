from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-003"
PLAN = BENCH / "PLAN-v0.1.json"
PREREG = BENCH / "PREREGISTRATION.md"
FREEZE = BENCH / "PLAN-FREEZE-v0.1.json"

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_003.py"

TARGET_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003/PLAN-v0.1.json"
)

TARGET_FREEZE = (
    ROOT / "benchmarks/characterization/"
    "definition-ontology-discrimination-003/PLAN-FREEZE-v0.2.json"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_plan_instrument_and_test() -> None:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))

    assert freeze["plan_sha256"] == sha(PLAN)
    assert freeze["preregistration_sha256"] == sha(PREREG)
    assert freeze["qualification_instrument_sha256"] == sha(SCRIPT)
    assert freeze["contract_test_sha256"] == sha(Path(__file__))

    assert freeze["provider_call_made"] is False
    assert freeze["model_call_made"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["semantic_successor_authorized"] is False


def test_target_ontology_003_is_exactly_bound() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    target = plan["semantic_successor_target"]

    assert target["work_order"] == ("OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003")

    assert target["commit_sha"] == ("fd07eefae35e3fb0855847bd4d0a911ec3636a9f")

    assert target["plan_sha256"] == sha(TARGET_PLAN)
    assert target["freeze_v0_2_sha256"] == sha(TARGET_FREEZE)


def test_probe_semantics_are_preserved() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    assert plan["predecessor_002_probe_plan_semantics"] == "UNCHANGED"
    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0

    assert [item["probe_id"] for item in plan["probes"]] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_no_remediation_gate_exists() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source = SCRIPT.read_text(encoding="utf-8")

    assert "remediation_prerequisite" not in source
    assert "remediation_prerequisite" not in plan
    assert plan["fresh_provider_qualification"] is True


def test_only_qualified_authorizes_successor() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source = SCRIPT.read_text(encoding="utf-8")

    assert plan["authorization_rule"].startswith("Only QUALIFIED")

    assert '"semantic_successor_authorized": disposition == "QUALIFIED"' in source


def test_no_semantic_or_ir_claim() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    assert plan["semantic_hypothesis"] is None
    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architectural_change_authorized"] is False
    assert plan["independent_validation_claim"] is False
