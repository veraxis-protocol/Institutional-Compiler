from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_nvidia_provider_recovery_stability_001.py"
)

MODULE_NAME = "_test_nvidia_provider_recovery_stability_001"

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


def test_frozen_identity_and_population() -> None:
    plan = module.verify_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-001"
    )

    assert plan["population"]["cycles"] == 6
    assert plan["population"]["planned_provider_requests"] == 18
    assert plan["population"]["observations_per_probe"] == 6


def test_exact_balanced_request_plan() -> None:
    plan = load_plan()
    rows = plan["population"]["request_plan"]

    assert len(rows) == 18

    assert [
        row["ordinal"]
        for row in rows
    ] == list(range(1, 19))

    counts = Counter(
        row["probe_id"]
        for row in rows
    )

    assert counts == Counter({
        "BASIC_TEXT": 6,
        "JSON_MODE": 6,
        "PRODUCTION_TOKEN_RESERVATION": 6,
    })

    positions = Counter(
        (
            row["probe_id"],
            row["cycle_position"],
        )
        for row in rows
    )

    for probe_id in counts:
        for position in (1, 2, 3):
            assert positions[
                (probe_id, position)
            ] == 2


def test_frozen_qualification_006_probe_binding() -> None:
    module.verify_source_hashes()

    q = module.load_qualification_006()

    assert q.PROBE_SPEC_SHA256 == module.PROBE_SPEC_SHA256
    assert q.probe_spec_sha256() == module.PROBE_SPEC_SHA256

    probes = module.probe_map(q)

    assert set(probes) == {
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    }


def test_materialization_exact_and_no_reuse() -> None:
    plan = load_plan()
    manifest = load_manifest()

    module.verify_manifest(
        plan,
        manifest,
    )

    assert manifest["request_count"] == 18
    assert manifest["cycles"] == 6
    assert manifest["observations_per_probe"] == 6

    assert manifest["historical_observations_reused"] is False
    assert manifest["incident_001_observation_reused"] is False

    assert manifest["provider_call_made"] is False
    assert manifest["model_call_made"] is False
    assert manifest["network_request_made"] is False
    assert manifest["live_run_executed"] is False


def test_materialization_contains_exact_probe_prompts() -> None:
    q = module.load_qualification_006()
    probes = module.probe_map(q)

    manifest = load_manifest()

    for row in manifest["requests"]:
        probe = probes[row["probe_id"]]

        expected = module.request_projection(
            probe
        )

        assert row["request_projection"] == expected

        assert row[
            "request_projection_sha256"
        ] == module.canonical_sha256(expected)


def test_transport_boundary() -> None:
    plan = load_plan()

    transport = plan["transport"]

    assert transport["timeout_seconds"] == 60.0
    assert transport["retries"] == 0
    assert transport["replacement_requests_allowed"] is False
    assert transport["pacing_seconds_within_cycle"] == 4.0
    assert transport["pacing_seconds_between_cycles"] == 10.0


def test_no_semantic_or_successor_authorization() -> None:
    plan = load_plan()

    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False

    assert plan["qualification_007_created"] is False
    assert plan["qualification_007_authorized"] is False

    assert plan["ontology_006_executed"] is False
    assert plan["ontology_006_execution_authorized"] is False

    assert plan["canonicalization_performed"] is False
    assert plan["institutional_ir_constructed"] is False
    assert plan["architecture_change_authorized"] is False


def test_classification_bounded_stability() -> None:
    observations = [
        accepted(10.0)
        for _ in range(18)
    ]

    assert module.classify(
        observations
    ) == "BOUNDED_RECOVERY_STABILITY_OBSERVED"


def test_classification_headroom_unstable() -> None:
    observations = [
        accepted(10.0)
        for _ in range(18)
    ]

    observations[7]["elapsed_seconds"] = 45.001

    assert module.classify(
        observations
    ) == "RECOVERY_HEADROOM_UNSTABLE"


def test_classification_provider_failure_precedence() -> None:
    observations = [
        accepted(10.0)
        for _ in range(18)
    ]

    observations[2] = {
        "outcome": "PROVIDER_ERROR",
        "marker_valid": False,
        "elapsed_seconds": 60.0,
    }

    assert module.classify(
        observations
    ) == "RECOVERY_PATH_UNSTABLE"


def test_classification_marker_failure_precedence() -> None:
    observations = [
        accepted(10.0)
        for _ in range(18)
    ]

    observations[5]["marker_valid"] = False
    observations[5]["outcome"] = "RESPONSE_MISMATCH"

    assert module.classify(
        observations
    ) == "RECOVERY_PATH_UNSTABLE"


def test_classification_incomplete_population() -> None:
    observations = [
        accepted(10.0)
        for _ in range(17)
    ]

    assert module.classify(
        observations
    ) == "RECOVERY_PATH_UNSTABLE"


def test_offline_preflight_preserves_non_authorization() -> None:
    plan = module.preflight()

    assert plan["provider_call_made"] is False
    assert plan["model_call_made"] is False
    assert plan["live_run_executed"] is False
    assert plan["qualification_007_authorized"] is False
    assert plan["ontology_006_execution_authorized"] is False
