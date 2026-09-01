from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-006"

PLAN = BENCH / "PLAN-v0.1.json"
PREREG = BENCH / "PREREGISTRATION.md"
FREEZE = BENCH / "PLAN-FREEZE-v0.1.json"

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_006.py"

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006"
)

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_BINDING = TARGET_DIR / "TREATMENT-BINDING-v0.1.json"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_INSTRUMENT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006.py"
)
TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_predicate_frame_discrimination_006.py"
)
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"

SOURCE005_TRANSPORT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_staged_decomposition_005.py"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"


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

    assert (
        freeze["contract_test_sha256"]
        == sha(Path(__file__))
    )

    assert freeze["provider_call_made"] is False
    assert freeze["model_call_made"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["semantic_successor_authorized"] is False


def test_exact_ontology_006_successor_binding() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    assert plan["semantic_successor_target"] == {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006",

        "commit_sha":
            "34abc1bc44bd89d1b29c0d005a23eabfb78ca196",

        "plan_sha256":
            sha(TARGET_PLAN),

        "preregistration_sha256":
            sha(TARGET_PREREG),

        "treatment_binding_sha256":
            sha(TARGET_BINDING),

        "preregistration_freeze_v0_1_sha256":
            sha(TARGET_FREEZE_V1),

        "instrument_sha256":
            sha(TARGET_INSTRUMENT),

        "contract_test_sha256":
            sha(TARGET_TEST),

        "request_materialization_sha256":
            sha(TARGET_MANIFEST),

        "freeze_v0_2_sha256":
            sha(TARGET_FREEZE_V2),

        "source_ontology_005_transport_instrument_sha256":
            sha(SOURCE005_TRANSPORT),

        "provider_adapter_sha256":
            sha(ADAPTER),
    }


def test_target_population_and_state() -> None:
    freeze = json.loads(
        TARGET_FREEZE_V2.read_text(
            encoding="utf-8"
        )
    )

    manifest = json.loads(
        TARGET_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    assert freeze["instrument_frozen"] is True
    assert freeze["live_run_executed"] is False
    assert freeze["provider_qualification_006_executed"] is False

    assert manifest["request_count"] == 18
    assert manifest["pair_count"] == 9

    assert Counter(
        x["arm"]
        for x in manifest["requests"]
    ) == Counter({
        "A_BASELINE_B2": 9,
        "B_ROLE_GUIDED_B2": 9,
    })

    assert manifest["ontology_005_live_outputs_reused"] is False


def test_probe_semantics_unchanged() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

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

    assert (
        plan["transport_probe_semantics_vs_005"]
        == "UNCHANGED"
    )


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
        "does not consume or simulate"
        in plan["qualification_retry_policy"]
    )

    assert "retries must remain zero" in source


def test_only_qualified_authorizes_successor() -> None:
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
        'disposition == "QUALIFIED"'
        in source
    )


def test_claim_ceiling_and_fresh_gate() -> None:
    plan = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    assert plan["fresh_provider_qualification"] is True
    assert plan["semantic_hypothesis"] is None
    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architectural_change_authorized"] is False
    assert plan["independent_validation_claim"] is False
