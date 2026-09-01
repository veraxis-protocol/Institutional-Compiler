from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006r1.py"
)

MODULE_NAME = "_test_ontology_006r1"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load_manifest() -> dict:
    return json.loads(
        module.MATERIALIZATION_PATH.read_text(
            encoding="utf-8"
        )
    )


def test_repair_identity() -> None:
    plan = module.verify_repair_plan()

    assert module.WORK_ORDER == (
        "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006R1"
    )

    assert plan["revision_of"] == (
        "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006"
    )

    assert plan["planned_provider_requests"] == 18
    assert plan["planned_pairs"] == 9


def test_original_implementation_is_hash_frozen() -> None:
    module.verify_frozen_sources()

    assert module.sha256(module.ORIGINAL_SCRIPT) == (
        module.ORIGINAL_SCRIPT_SHA256
    )

    assert module.sha256(module.ORIGINAL_MANIFEST) == (
        module.ORIGINAL_MANIFEST_SHA256
    )


def test_semantic_execution_delegates_to_original_o006() -> None:
    source = module.original()

    assert source.WORK_ORDER == (
        "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006"
    )

    for name in (
        "request_for",
        "semantic_materialization",
        "bounded_provider",
        "execute_request",
        "execute_plan",
        "adjudicability",
        "analyze",
        "decide",
    ):
        assert callable(getattr(source, name))


def test_all_18_request_projections_are_byte_identical() -> None:
    source = module.original()
    ctx = module.original_context()

    recomputed = source.semantic_materialization(ctx)

    original = json.loads(
        module.ORIGINAL_MANIFEST.read_text(
            encoding="utf-8"
        )
    )["requests"]

    assert len(recomputed) == 18
    assert len(original) == 18

    for current, frozen in zip(
        recomputed,
        original,
        strict=True,
    ):
        assert current["ordinal"] == frozen["ordinal"]
        assert current["specimen_id"] == frozen["specimen_id"]
        assert current["run_index"] == frozen["run_index"]
        assert current["arm"] == frozen["arm"]
        assert current["request"] == frozen["request"]
        assert current["request_sha256"] == frozen["request_sha256"]


def test_repaired_materialization_exact() -> None:
    manifest = load_manifest()

    assert manifest == module.materialization_document()

    assert manifest["request_count"] == 18
    assert manifest["pair_count"] == 9
    assert manifest["baseline_request_count"] == 9
    assert manifest["treatment_request_count"] == 9

    assert manifest["semantic_execution_delegation"] == (
        "DIRECT_TO_HASH_FROZEN_ONTOLOGY_006_IMPLEMENTATION"
    )

    assert manifest["q007_observations_reused"] is False
    assert manifest["q007_authorization_reused"] is False


def test_transport_semantics_are_original_o006_transport() -> None:
    source = module.original()

    assert source.TIMEOUT_SECONDS == 60.0
    assert source.PACING_SECONDS == 4.0
    assert source.TRANSPORT_CALL_CEILING == 36

    plan = json.loads(
        source.PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )

    transport = plan["transport_policy"]

    assert transport["maximum_retries_per_semantic_request"] == 1

    assert transport["retry_only_on_exact"] == {
        "error_type": "ModelProviderError",
        "error_message": "NVIDIA NIM connection timed out",
    }


def test_q008_is_only_live_authorization_gate() -> None:
    plan = module.verify_repair_plan()

    assert plan["provider_prerequisite"]["work_order"] == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-008"
    )

    assert plan["provider_prerequisite"][
        "authority_artifact_type"
    ] == "FORMALLY_CLOSED_TRACKED_EXECUTION_RESULT"

    assert plan["q007_authorization_reused"] is False
    assert plan["q007_observations_reused"] is False


def test_static_preflight_does_not_require_q008() -> None:
    assert not module.QUALIFICATION_RESULT.exists()

    ctx = module.static_preflight()

    assert ctx is not None


def test_q008_gate_occurs_before_provider_construction() -> None:
    text = SCRIPT.read_text(
        encoding="utf-8"
    )

    qpos = text.index(
        "qualification = qualification_prerequisite()"
    )

    ppos = text.index(
        "provider = NvidiaNimProvider(",
        qpos,
    )

    assert qpos < ppos


def test_old_q006_receipt_is_not_execution_authority() -> None:
    text = SCRIPT.read_text(
        encoding="utf-8"
    )

    assert (
        ".local/provider-qualification-receipts/"
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006.json"
    ) not in text

    assert "QUALIFICATION_RESULT" in text
    assert "nvidia-nim-008/EXECUTION-RESULT-v0.1.json" in text


def test_pre_execution_state_remains_unauthorized() -> None:
    plan = module.verify_repair_plan()
    freeze = module.verify_freeze_v2()

    assert plan["ontology_006r1_execution_authorized"] is False
    assert plan["live_run_executed"] is False

    assert freeze["qualification_008_created"] is False
    assert freeze["qualification_008_executed"] is False
    assert freeze["qualification_008_qualified"] is False
    assert freeze["ontology_006r1_execution_authorized"] is False
    assert freeze["live_run_executed"] is False


def test_no_semantic_or_architecture_result_pre_execution() -> None:
    plan = module.verify_repair_plan()

    assert plan["semantic_hypothesis_evaluated"] is False
    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architecture_change_authorized"] is False
