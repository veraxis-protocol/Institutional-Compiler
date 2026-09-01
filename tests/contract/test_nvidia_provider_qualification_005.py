from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-005"

PLAN = BENCH / "PLAN-v0.1.json"
PREREG = BENCH / "PREREGISTRATION.md"
FREEZE = BENCH / "PLAN-FREEZE-v0.1.json"

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_005.py"

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005"
)

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_TRANSPORT = TARGET_DIR / "TRANSPORT-RECOVERY-POLICY-v0.1.json"
TARGET_BINDING = TARGET_DIR / "SEMANTIC-REPLICATION-BINDING-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"

TARGET_INSTRUMENT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_staged_decomposition_005.py"
)

TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_staged_decomposition_005.py"
)

TARGET_ADAPTER = ROOT / "src/oic/nvidia_nim.py"


def sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_freeze_binds_exact_qualification_package() -> None:
    freeze = json.loads(
        FREEZE.read_text(
            encoding="utf-8"
        )
    )

    assert freeze["plan_sha256"] == sha(PLAN)
    assert freeze["preregistration_sha256"] == sha(PREREG)

    assert (
        freeze["qualification_instrument_sha256"]
        == sha(SCRIPT)
    )

    assert freeze["contract_test_sha256"] == sha(Path(__file__))

    assert freeze["provider_call_made"] is False
    assert freeze["model_call_made"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["semantic_successor_authorized"] is False


def test_exact_ontology_005_successor_binding() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    assert plan["semantic_successor_target"] == {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005",
        "commit_sha":
            "713eb9a5f8cbe4b184e163573c30dd9d48cf1541",
        "plan_sha256":
            sha(TARGET_PLAN),
        "preregistration_sha256":
            sha(TARGET_PREREG),
        "preregistration_freeze_v0_1_sha256":
            sha(TARGET_FREEZE_V1),
        "transport_recovery_policy_sha256":
            sha(TARGET_TRANSPORT),
        "semantic_replication_binding_sha256":
            sha(TARGET_BINDING),
        "freeze_v0_2_sha256":
            sha(TARGET_FREEZE_V2),
        "instrument_sha256":
            sha(TARGET_INSTRUMENT),
        "contract_test_sha256":
            sha(TARGET_TEST),
        "request_materialization_sha256":
            sha(TARGET_MANIFEST),
        "provider_adapter_sha256":
            sha(TARGET_ADAPTER),
    }


def test_semantic_target_materialization_is_complete() -> None:
    manifest = json.loads(
        TARGET_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    assert manifest["request_count"] == 54
    assert len(manifest["requests"]) == 54

    counts = Counter(
        item["stage"]
        for item in manifest["requests"]
    )

    assert counts == Counter({
        "A_COMBINED": 18,
        "B1_FORCE": 18,
        "B2_NONFORCE_SLOTS": 18,
    })

    assert manifest["provider_constructed"] is False
    assert manifest["network_request_made"] is False

    assert (
        manifest["ontology_004_semantic_outputs_reused"]
        is False
    )


def test_target_transport_policy_is_bound() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    transport = json.loads(
        TARGET_TRANSPORT.read_text(
            encoding="utf-8"
        )
    )

    target = plan[
        "semantic_successor_target"
    ]

    assert target[
        "transport_recovery_policy_sha256"
    ] == sha(TARGET_TRANSPORT)

    assert transport["retry"][
        "max_retries_per_semantic_request"
    ] == 1

    assert transport["retry"][
        "eligible_exception_type"
    ] == "ModelProviderError"

    assert transport["retry"][
        "eligible_exact_error_message"
    ] == "NVIDIA NIM connection timed out"


def test_qualification_probe_semantics_unchanged() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    assert plan["transport_probe_semantics_vs_004"] == "UNCHANGED"
    assert plan["transport_probe_semantics_vs_003a"] == "UNCHANGED"

    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0

    assert plan["probe_spec_sha256"] == (
        "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
    )

    assert [
        item["probe_id"]
        for item in plan["probes"]
    ] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_qualification_retry_budget_is_zero() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert plan["retries"] == 0

    assert (
        "Qualification measures immediate provider-path availability"
        in plan["qualification_retry_policy"]
    )

    assert "retries must remain zero" in source


def test_fresh_gate_has_no_remediation_dependency() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert plan["fresh_provider_qualification"] is True

    # Narrative may state that this is NOT a remediation work order.
    # Instrument logic must not depend on a remediation artifact.
    assert "provider-remediation" not in source
    assert "REMEDIATION_PATH" not in source


def test_only_qualified_authorizes_ontology_005() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    source = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert plan["authorization_rule"].startswith(
        "Only QUALIFIED"
    )

    assert (
        '"semantic_successor_authorized":'
        in source
    )

    assert (
        'disposition == "QUALIFIED"'
        in source
    )


def test_claim_ceiling_preserved() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    assert plan["semantic_hypothesis"] is None

    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architectural_change_authorized"] is False
    assert plan["independent_validation_claim"] is False
