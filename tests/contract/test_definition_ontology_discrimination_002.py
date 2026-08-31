from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks/characterization/definition-ontology-discrimination-002"
PLAN = BENCH / "PLAN-v0.1.json"
FREEZE_V1 = BENCH / "PLAN-FREEZE-v0.1.json"
FREEZE_V2 = BENCH / "PLAN-FREEZE-v0.2.json"
FREEZE_V3 = BENCH / "PLAN-FREEZE-v0.3.json"
SCRIPT = ROOT / "scripts/characterize_definition_ontology_discrimination_002.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_plan_freeze_binds_current_bytes() -> None:
    freeze_v1 = json.loads(FREEZE_V1.read_text(encoding="utf-8"))
    freeze_v2 = json.loads(FREEZE_V2.read_text(encoding="utf-8"))
    freeze_v3 = json.loads(FREEZE_V3.read_text(encoding="utf-8"))

    assert sha(PLAN) == freeze_v1["plan_sha256"]
    assert freeze_v2["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v3["plan_sha256"] == freeze_v2["plan_sha256"]

    assert freeze_v2["supersedes_freeze_sha256"] == sha(FREEZE_V1)
    assert freeze_v3["supersedes_freeze_sha256"] == sha(FREEZE_V2)

    assert freeze_v2["instrument_sha256"] == (
        "17523ac56f352d5058bf17886a62783e2f8e72a5c156b173bc33d52566298030"
    )
    assert sha(SCRIPT) == freeze_v3["instrument_sha256"]
    assert sha(Path(__file__)) == freeze_v3["contract_test_sha256"]

    assert freeze_v3["semantic_change"] is False
    assert freeze_v3["provider_call_made"] is False
    assert freeze_v3["model_call_made"] is False
    assert freeze_v3["static_format_and_evidence_binding_only_change"] is True


def test_semantic_design_is_explicitly_unchanged() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["semantic_design_change_from_001"] is False
    assert plan["planned_requests"] == 36
    assert plan["retry_policy"].startswith("none")


def test_provider_qualification_002_is_mandatory() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "OIC-NVIDIA-PROVIDER-QUALIFICATION-002" in text
    assert 'disposition") != "QUALIFIED"' in text
    assert "semantic_successor_authorized" in text


def test_adjudicability_gate_precedes_semantic_analysis() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    gate = source.index('if adjudicability["adjudicable"]:')
    analyze = source.index("source.analyze_attempts", gate)
    failure = source.index('"NOT_ADJUDICABLE_PROVIDER_FAILURE"', gate)
    assert gate < analyze
    assert gate < failure


def test_gate_requires_all_36_and_all_pairs() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    gate = plan["adjudicability_gate"]
    assert gate["accepted_observations_required"] == 36
    assert gate["complete_ab_pairs_required"] == 18
    assert gate["primary_complete_pairs_required"] == 9
    assert gate["control_complete_pairs_required"] == 9
    assert gate["failure_disposition"] == "NOT_ADJUDICABLE_PROVIDER_FAILURE"


def test_no_canonicalization_or_ir_runtime() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["canonicalization_implemented"] is False
    assert plan["institutional_ir_runtime_implemented"] is False
    assert plan["independent_validation_claim"] is False
