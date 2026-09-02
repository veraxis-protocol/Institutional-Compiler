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
    / "scripts/characterize_nvidia_provider_recovery_stability_002.py"
)

MODULE_NAME = "_test_nvidia_provider_recovery_stability_002"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def accepted(
    *,
    ordinal: int,
    round_index: int,
    position: int,
    probe_id: str,
    seconds: float = 1.0,
) -> dict[str, Any]:
    return {
        "execution_ordinal": ordinal,
        "round_index": round_index,
        "position_in_round": position,
        "probe_id": probe_id,
        "outcome": "ACCEPTED",
        "marker_valid": True,
        "elapsed_seconds": seconds,
    }


def full_accepted_population(
    *,
    one_slow: bool = False,
) -> list[dict[str, Any]]:
    plan = load(module.PLAN_PATH)
    rows = []

    for item in plan["execution_plan"]:
        seconds = (
            45.001
            if one_slow and item["ordinal"] == 2
            else 1.0
        )

        rows.append(
            accepted(
                ordinal=item["ordinal"],
                round_index=item["round_index"],
                position=item["position_in_round"],
                probe_id=item["probe_id"],
                seconds=seconds,
            )
        )

    return rows


def test_identity_and_population() -> None:
    plan = module.prereg_context()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-002"
    )

    assert plan["round_count"] == 6
    assert plan["planned_provider_calls"] == 18


def test_order_balance_exact() -> None:
    plan = module.prereg_context()
    rows = plan["execution_plan"]

    assert len(rows) == 18

    for probe_id in (
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ):
        selected = [
            x for x in rows
            if x["probe_id"] == probe_id
        ]

        assert len(selected) == 6

        positions = Counter(
            x["position_in_round"]
            for x in selected
        )

        assert positions == Counter({
            1: 2,
            2: 2,
            3: 2,
        })


def test_source_probe_semantics_exact_q009() -> None:
    q009 = module.source_q009()

    assert q009.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    )

    assert q009.PROBE_SPEC_SHA256 == (
        module.PROBE_SPEC_SHA256
    )

    assert [
        x.probe_id
        for x in q009.probes()
    ] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]


def test_materialization_exact_source_projection() -> None:
    actual = load(module.MATERIALIZATION_PATH)
    expected = module.materialization_document()

    assert actual == expected
    assert actual["request_count"] == 18
    assert actual["round_count"] == 6

    source = module.source_manifest_by_probe()

    for row in actual["requests"]:
        frozen = source[row["probe_id"]]

        assert row["request_projection"] == (
            frozen["request_projection"]
        )

        assert row["request_projection_sha256"] == (
            frozen["request_projection_sha256"]
        )

        assert row["fresh_observation"] is True
        assert row["q009_live_observation_reused"] is False


def test_transport_boundary() -> None:
    plan = module.prereg_context()
    transport = plan["transport"]

    assert transport["timeout_seconds"] == 60.0
    assert transport["latency_headroom_seconds"] == 45.0
    assert transport["retries"] == 0
    assert transport["replacement_observations_allowed"] is False
    assert transport["pacing_seconds"] == 4.0


def test_classify_bounded_recovery() -> None:
    disposition, gate = module.classify(
        full_accepted_population()
    )

    assert gate["adjudicable"] is True
    assert disposition == (
        "BOUNDED_RECOVERY_STABILITY_OBSERVED"
    )


def test_classify_latency_degradation() -> None:
    disposition, gate = module.classify(
        full_accepted_population(
            one_slow=True,
        )
    )

    assert gate["adjudicable"] is True
    assert disposition == (
        "RECOVERY_OBSERVED_WITH_LATENCY_DEGRADATION"
    )


def test_classify_provider_failure_precedence() -> None:
    rows = full_accepted_population()

    rows[1] = {
        **rows[1],
        "outcome": "PROVIDER_ERROR",
        "marker_valid": False,
        "elapsed_seconds": 60.0,
        "error_type": "ModelProviderError",
        "error_message": "NVIDIA NIM connection timed out",
    }

    disposition, gate = module.classify(rows)

    assert gate["adjudicable"] is True
    assert disposition == (
        "RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE"
    )


def test_classify_response_mismatch_as_failure() -> None:
    rows = full_accepted_population()

    rows[4] = {
        **rows[4],
        "outcome": "RESPONSE_MISMATCH",
        "marker_valid": False,
    }

    disposition, gate = module.classify(rows)

    assert gate["adjudicable"] is True
    assert disposition == (
        "RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE"
    )


def test_classify_incomplete() -> None:
    rows = full_accepted_population()[:-1]

    disposition, gate = module.classify(rows)

    assert gate["adjudicable"] is False
    assert disposition == "INCOMPLETE_CHARACTERIZATION"


def test_q009_not_reused() -> None:
    plan = module.prereg_context()
    manifest = load(module.MATERIALIZATION_PATH)

    assert plan["q009_rerun"] is False
    assert plan[
        "q009_observations_reused_as_new_observations"
    ] is False

    assert manifest["q009_rerun"] is False
    assert manifest[
        "q009_observations_reused_as_new_observations"
    ] is False


def test_downstream_authorization_boundary() -> None:
    plan = module.prereg_context()

    assert plan["q010_created"] is False
    assert plan["q010_authorized"] is False
    assert plan["ontology_007_execution_authorized"] is False
    assert plan["ontology_007_executed"] is False
    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False
    assert plan["architecture_change_authorized"] is False


def test_offline_preflight() -> None:
    plan = module.static_preflight()

    assert plan["live_run_executed"] is False
    assert plan["q010_created"] is False
    assert plan["ontology_007_execution_authorized"] is False
