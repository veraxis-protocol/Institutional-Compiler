from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = (
    ROOT
    / "scripts/characterize_nvidia_provider_latency_stability_001.py"
)

MODULE_NAME = "_test_provider_latency_stability_001"

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
        module.PLAN_PATH.read_text(encoding="utf-8")
    )


def load_manifest() -> dict[str, Any]:
    return json.loads(
        module.MANIFEST_PATH.read_text(encoding="utf-8")
    )


def accepted(
    elapsed: float = 1.0,
) -> dict[str, Any]:
    return {
        "outcome": "ACCEPTED",
        "marker_valid": True,
        "elapsed_seconds": elapsed,
    }


def test_identity_and_frozen_population() -> None:
    plan = load_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-LATENCY-STABILITY-001"
    )
    assert plan["planned_provider_requests"] == 36
    assert plan["cycles"] == 12
    assert plan["observations_per_probe"] == 12
    assert len(plan["request_plan"]) == 36


def test_source_qualification_006_is_exactly_bound() -> None:
    module.verify_source_hashes()
    q = module.load_qualification_006()

    assert q.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    )
    assert q.PROBE_SPEC_SHA256 == module.PROBE_SPEC_SHA256
    assert q.probe_spec_sha256() == module.PROBE_SPEC_SHA256


def test_materialization_matches_frozen_request_plan() -> None:
    plan = load_plan()
    manifest = load_manifest()

    module.verify_manifest(
        plan,
        manifest,
    )

    assert manifest["request_count"] == 36
    assert len(manifest["requests"]) == 36

    assert [
        item["ordinal"]
        for item in manifest["requests"]
    ] == list(range(1, 37))


def test_materialized_request_semantics_are_qualification_006() -> None:
    manifest = load_manifest()
    q = module.load_qualification_006()
    probes = module.probe_map(q)

    for item in manifest["requests"]:
        expected = module.request_projection(
            probes[item["probe_id"]]
        )

        assert item["request_projection"] == expected
        assert (
            item["request_projection_sha256"]
            == module.canonical_sha256(expected)
        )


def test_balanced_probe_and_position_population() -> None:
    manifest = load_manifest()

    probes = Counter(
        item["probe_id"]
        for item in manifest["requests"]
    )

    assert probes == Counter({
        "BASIC_TEXT": 12,
        "JSON_MODE": 12,
        "PRODUCTION_TOKEN_RESERVATION": 12,
    })

    positions = Counter(
        (
            item["probe_id"],
            item["cycle_position"],
        )
        for item in manifest["requests"]
    )

    for probe_id in probes:
        for position in (1, 2, 3):
            assert positions[(probe_id, position)] == 4


def test_zero_retry_and_non_authorization_boundary() -> None:
    plan = load_plan()
    manifest = load_manifest()

    assert plan["retries"] == 0
    assert plan["replacement_requests_allowed"] is False
    assert plan["qualification_006_observations_reused"] is False
    assert plan["ontology_006_execution_authorized"] is False
    assert plan["semantic_successor_authorized"] is False

    assert manifest["retries"] == 0
    assert manifest["replacement_requests_allowed"] is False
    assert manifest["qualification_006_live_outputs_reused"] is False


def test_classification_stable_within_headroom() -> None:
    observations = [
        accepted(10.0)
        for _ in range(36)
    ]

    assert module.classify(observations) == (
        "STABLE_WITHIN_FROZEN_HEADROOM"
    )


@pytest.mark.parametrize(
    "violations",
    [1, 2, 3],
)
def test_classification_intermittent(
    violations: int,
) -> None:
    observations = [
        accepted(10.0)
        for _ in range(36)
    ]

    for index in range(violations):
        observations[index]["elapsed_seconds"] = 45.001

    assert module.classify(observations) == (
        "INTERMITTENT_HEADROOM_VIOLATION"
    )


@pytest.mark.parametrize(
    "violations",
    [4, 12, 36],
)
def test_classification_frequent(
    violations: int,
) -> None:
    observations = [
        accepted(10.0)
        for _ in range(36)
    ]

    for index in range(violations):
        observations[index]["elapsed_seconds"] = 45.001

    assert module.classify(observations) == (
        "FREQUENT_HEADROOM_VIOLATION"
    )


def test_provider_path_unstable_has_precedence() -> None:
    observations = [
        accepted(60.0)
        for _ in range(36)
    ]

    observations[10] = {
        "outcome": "PROVIDER_ERROR",
        "marker_valid": False,
        "elapsed_seconds": 60.0,
    }

    assert module.classify(observations) == (
        "PROVIDER_PATH_UNSTABLE"
    )


def test_classification_requires_all_36_observations() -> None:
    with pytest.raises(ValueError):
        module.classify([
            accepted()
            for _ in range(35)
        ])


def test_pacing_is_frozen() -> None:
    same_cycle = (
        {"cycle_index": 1},
        {"cycle_index": 1},
    )
    next_cycle = (
        {"cycle_index": 1},
        {"cycle_index": 2},
    )

    assert module.pacing_after(*same_cycle) == 4.0
    assert module.pacing_after(*next_cycle) == 10.0
    assert module.pacing_after(
        {"cycle_index": 12},
        None,
    ) == 0.0


def test_offline_preflight_does_not_construct_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForbiddenProvider:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError(
                "provider constructed during offline preflight"
            )

    monkeypatch.setattr(
        module,
        "NvidiaNimProvider",
        ForbiddenProvider,
    )

    plan = module.preflight()

    assert plan["live_run_executed"] is False
