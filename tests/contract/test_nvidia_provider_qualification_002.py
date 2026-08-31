from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-002"
PLAN = BENCH / "PLAN-v0.1.json"
FREEZE_V1 = BENCH / "PLAN-FREEZE-v0.1.json"
FREEZE_V2 = BENCH / "PLAN-FREEZE-v0.2.json"
FREEZE_V3 = BENCH / "PLAN-FREEZE-v0.3.json"
SCRIPT = ROOT / "scripts/qualify_nvidia_provider_002.py"

TARGET_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-002/PLAN-v0.1.json"
)
TARGET_FREEZE = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-002/"
    "PLAN-FREEZE-v0.3.json"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_binds_plan_and_instrument() -> None:
    freeze_v1 = json.loads(FREEZE_V1.read_text(encoding="utf-8"))
    freeze_v2 = json.loads(FREEZE_V2.read_text(encoding="utf-8"))
    freeze_v3 = json.loads(FREEZE_V3.read_text(encoding="utf-8"))

    assert sha(PLAN) == freeze_v1["plan_sha256"]
    assert freeze_v2["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v3["plan_sha256"] == freeze_v2["plan_sha256"]

    assert freeze_v2["supersedes_freeze_sha256"] == sha(FREEZE_V1)
    assert freeze_v3["supersedes_freeze_sha256"] == sha(FREEZE_V2)

    assert freeze_v3["v0_2_instrument_sha256"] == (
        "6566b218a83f8ef95aeb3eb83862989b537b69823b86925b2f08bc84ee5d3476"
    )
    assert freeze_v3["v0_2_contract_test_sha256"] == (
        "ed0c4bcdea73ad7826865fe36cbafb9c60b731bb682440a38f34449090479152"
    )

    assert sha(SCRIPT) == freeze_v3["instrument_sha256"]
    assert sha(Path(__file__)) == freeze_v3["contract_test_sha256"]

    assert freeze_v3["semantic_change"] is False
    assert freeze_v3["provider_call_made"] is False
    assert freeze_v3["model_call_made"] is False
    assert freeze_v3["remediation_marker_created"] is False
    assert freeze_v3["static_format_and_evidence_binding_only_change"] is True


def test_target_ontology_002_is_exactly_bound() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    target = plan["semantic_successor_target"]
    assert target["work_order"] == "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002"
    assert target["commit_sha"] == "17775d93b93e00e3dd9a8bb10c97ae9eda373ebe"
    assert sha(TARGET_PLAN) == target["plan_sha256"]
    assert sha(TARGET_FREEZE) == target["freeze_v0_3_sha256"]


def test_recovery_probe_semantics_are_unchanged_from_001() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["predecessor_001_probe_plan_semantics"] == "UNCHANGED"
    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0
    assert [p["probe_id"] for p in plan["probes"]] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_live_execution_requires_remediation_marker() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    gate = plan["remediation_prerequisite"]
    assert gate["required_work_order"] == "OIC-NVIDIA-PROVIDER-QUALIFICATION-002"
    assert gate["required_remediation_confirmed"] is True
    source = SCRIPT.read_text(encoding="utf-8")
    assert "remediation_prerequisite()" in source
    assert "execute_live()" in source


def test_only_qualified_authorizes_semantic_successor() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["authorization_rule"].startswith("Only QUALIFIED")
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"semantic_successor_authorized": disposition == "QUALIFIED"' in source


def test_no_semantic_or_ir_claim() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["semantic_hypothesis"] is None
    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["independent_validation_claim"] is False
