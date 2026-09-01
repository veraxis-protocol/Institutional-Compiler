from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_007.py"

MODULE_NAME = "_test_nvidia_provider_qualification_007"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load_plan() -> dict[str, Any]:
    return json.loads(
        module.PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )


def load_manifest() -> dict[str, Any]:
    return json.loads(
        module.MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )


def accepted(
    elapsed: float = 10.0,
) -> dict[str, Any]:
    return {
        "outcome": "ACCEPTED",
        "marker_valid": True,
        "elapsed_seconds": elapsed,
    }


def test_identity_and_fresh_gate() -> None:
    plan = module.verify_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-007"
    )

    assert plan["fresh_provider_qualification"] is True
    assert plan["planned_probe_count"] == 3

    assert plan[
        "historical_qualification_observations_reused"
    ] is False

    assert plan[
        "recovery_stability_observations_reused"
    ] is False


def test_recovery_prerequisite_is_bounded_not_qualification() -> None:
    plan = load_plan()
    recovery = plan["prerequisite_recovery"]

    assert recovery["classification"] == (
        "BOUNDED_RECOVERY_STABILITY_OBSERVED"
    )

    assert recovery[
        "bounded_recovery_stability_established"
    ] is True

    assert recovery[
        "provider_qualification_established"
    ] is False

    assert recovery[
        "qualification_007_consideration_permitted"
    ] is True


def test_exact_frozen_ontology_006_successor_binding() -> None:
    plan = load_plan()

    assert plan[
        "semantic_successor_target"
    ] == module.expected_target()

    target = module.expected_target()

    assert target["commit_sha"] == (
        "34abc1bc44bd89d1b29c0d005a23eabfb78ca196"
    )

    assert target["request_count"] == 18
    assert target["pair_count"] == 9
    assert target["live_run_executed"] is False


def test_source_q006_exact_probe_binding() -> None:
    module.verify_frozen_sources()

    source = module.load_source_q006()

    assert source.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    )

    assert source.PROBE_SPEC_SHA256 == module.PROBE_SPEC_SHA256
    assert source.probe_spec_sha256() == module.PROBE_SPEC_SHA256

    assert [
        probe.probe_id
        for probe in module.probes()
    ] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_materialization_is_exact_source_projection() -> None:
    manifest = load_manifest()

    module.verify_manifest(
        manifest
    )

    source_probes = module.probes()

    assert manifest["request_count"] == 3

    for row, probe in zip(
        manifest["requests"],
        source_probes,
        strict=True,
    ):
        projection = module.request_projection(
            probe
        )

        assert row["request_projection"] == projection

        assert row[
            "request_projection_sha256"
        ] == module.canonical_sha256(
            projection
        )


def test_transport_boundary() -> None:
    plan = load_plan()

    assert plan["provider"] == {
        "base_url":
            "https://integrate.api.nvidia.com/v1",
        "latency_headroom_seconds":
            45.0,
        "model":
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        "timeout_seconds":
            60.0,
    }

    assert plan["retries"] == 0
    assert plan["replacement_probes_allowed"] is False
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0


def test_decision_qualified() -> None:
    attempts = [
        accepted(10.0),
        accepted(20.0),
        accepted(45.0),
    ]

    assert module.decide(attempts) == "QUALIFIED"


def test_decision_degraded() -> None:
    attempts = [
        accepted(10.0),
        accepted(45.001),
        accepted(20.0),
    ]

    assert module.decide(attempts) == "DEGRADED"


def test_decision_not_qualified_provider_failure() -> None:
    attempts = [
        accepted(10.0),
        {
            "outcome": "PROVIDER_ERROR",
            "marker_valid": False,
            "elapsed_seconds": 60.0,
        },
        accepted(20.0),
    ]

    assert module.decide(attempts) == "NOT_QUALIFIED"


def test_decision_not_qualified_marker_failure() -> None:
    attempts = [
        accepted(10.0),
        {
            "outcome": "RESPONSE_MISMATCH",
            "marker_valid": False,
            "elapsed_seconds": 20.0,
        },
        accepted(30.0),
    ]

    assert module.decide(attempts) == "NOT_QUALIFIED"


def test_decision_not_qualified_incomplete() -> None:
    assert module.decide([
        accepted(10.0),
        accepted(20.0),
    ]) == "NOT_QUALIFIED"


def test_pre_execution_authorization_boundary() -> None:
    plan = load_plan()
    manifest = load_manifest()

    assert plan["qualification_007_qualified"] is False
    assert plan["ontology_006_executed"] is False
    assert plan["ontology_006_execution_authorized"] is False

    assert manifest["qualification_007_qualified"] is False
    assert manifest["ontology_006_execution_authorized"] is False

    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False


def test_offline_preflight_preserves_gate() -> None:
    plan = module.preflight()

    assert plan["provider_call_made"] is False
    assert plan["model_call_made"] is False
    assert plan["live_run_executed"] is False
    assert plan["qualification_007_qualified"] is False
    assert plan["ontology_006_execution_authorized"] is False
