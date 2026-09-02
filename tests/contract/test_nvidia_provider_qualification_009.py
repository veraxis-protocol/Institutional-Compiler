from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = ROOT / "scripts/qualify_nvidia_provider_009.py"

MODULE_NAME = "_test_nvidia_provider_qualification_009"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def plan() -> dict[str, Any]:
    return json.loads(
        module.PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )


def manifest() -> dict[str, Any]:
    return json.loads(
        module.MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )


def accepted(seconds: float = 10.0) -> dict[str, Any]:
    return {
        "outcome": "ACCEPTED",
        "marker_valid": True,
        "elapsed_seconds": seconds,
    }


def test_identity_and_fresh_gate() -> None:
    p = module.verify_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    )

    assert p["fresh_provider_qualification"] is True
    assert p["planned_probe_count"] == 3


def test_exact_ontology_007_target_descriptor() -> None:
    p = plan()

    assert p["semantic_successor_target"] == (
        module.target_descriptor()
    )

    target = module.target_descriptor()

    assert target["work_order"] == (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-DISCRIMINATION-007"
    )

    assert target["request_count"] == 18
    assert target["pair_count"] == 9

    assert target["treatment_binding_sha256"] == (
        module.TARGET_BINDING_SHA256
    )


def test_source_probe_semantics_are_exact_q006() -> None:
    source = module.source_q006()

    assert source.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    )

    assert source.PROBE_SPEC_SHA256 == module.PROBE_SPEC_SHA256
    assert source.probe_spec_sha256() == module.PROBE_SPEC_SHA256

    assert [
        x.probe_id
        for x in module.probes()
    ] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_materialization_exact_source_projection() -> None:
    m = manifest()

    assert m == module.materialization_document()
    assert m["request_count"] == 3

    for row, probe in zip(
        m["requests"],
        module.probes(),
        strict=True,
    ):
        projection = module.request_projection(probe)

        assert row["request_projection"] == projection

        assert row["request_projection_sha256"] == (
            module.canonical_sha256(projection)
        )


def test_transport_boundary() -> None:
    p = plan()

    assert p["provider"] == {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "latency_headroom_seconds": 45.0,
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "timeout_seconds": 60.0,
    }

    assert p["retries"] == 0
    assert p["replacement_probes_allowed"] is False
    assert p["pacing_seconds"] == 4.0


def test_decision_qualified() -> None:
    assert module.decide([
        accepted(10.0),
        accepted(20.0),
        accepted(45.0),
    ]) == "QUALIFIED"


def test_decision_degraded() -> None:
    assert module.decide([
        accepted(10.0),
        accepted(45.001),
        accepted(20.0),
    ]) == "DEGRADED"


def test_decision_provider_failure() -> None:
    assert module.decide([
        accepted(),
        {
            "outcome": "PROVIDER_ERROR",
            "marker_valid": False,
            "elapsed_seconds": 60.0,
        },
        accepted(),
    ]) == "NOT_QUALIFIED"


def test_decision_marker_failure() -> None:
    assert module.decide([
        accepted(),
        {
            "outcome": "RESPONSE_MISMATCH",
            "marker_valid": False,
            "elapsed_seconds": 20.0,
        },
        accepted(),
    ]) == "NOT_QUALIFIED"


def test_decision_incomplete_population() -> None:
    assert module.decide([
        accepted(),
        accepted(),
    ]) == "NOT_QUALIFIED"


def test_no_q008_or_historical_observation_reuse() -> None:
    p = plan()
    m = manifest()

    assert p[
        "historical_qualification_observations_reused"
    ] is False

    assert p["q008_observations_reused"] is False
    assert p["q008_authorization_reused"] is False

    assert p[
        "recovery_stability_observations_reused"
    ] is False

    assert m["q008_observations_reused"] is False
    assert m["q008_authorization_reused"] is False


def test_pre_execution_formal_authorization_boundary() -> None:
    p = plan()
    m = manifest()

    assert p["live_run_executed"] is False
    assert p["qualification_009_formally_closed"] is False
    assert p["qualification_009_qualified"] is False
    assert p["provider_qualification_established"] is False
    assert p["ontology_007_execution_authorized"] is False
    assert p["ontology_007_executed"] is False

    assert m["qualification_009_formally_closed"] is False
    assert m["qualification_009_qualified"] is False
    assert m["ontology_007_execution_authorized"] is False


def test_offline_preflight_preserves_gate() -> None:
    p = module.preflight()

    assert p["provider_call_made"] is False
    assert p["model_call_made"] is False
    assert p["network_request_made"] is False
    assert p["live_run_executed"] is False
    assert p["ontology_007_execution_authorized"] is False


def test_exact_target_source_dependencies_are_bound() -> None:
    target = module.target_descriptor()

    assert target["source_o006_instrument_sha256"] == (
        module.SOURCE_O006_SCRIPT_SHA256
    )

    assert target[
        "source_o006_request_materialization_sha256"
    ] == module.SOURCE_O006_MANIFEST_SHA256
