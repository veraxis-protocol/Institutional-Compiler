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
    / "scripts/qualify_nvidia_provider_010.py"
)

MODULE_NAME = (
    "_test_nvidia_provider_qualification_010"
)

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(
    module
)


def load(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def accepted(
    ordinal: int,
    round_index: int,
    position: int,
    seconds: float = 10.0,
) -> dict[str, Any]:
    return {
        "execution_ordinal":
            ordinal,

        "round":
            round_index,

        "position":
            position,

        "outcome":
            "ACCEPTED",

        "marker_valid":
            True,

        "elapsed_seconds":
            seconds,
    }


def nine_accepted(
    *,
    slow_ordinal: int | None = None,
) -> list[dict[str, Any]]:
    rows = []

    ordinal = 0

    for round_index in range(1, 4):
        for position in range(1, 4):
            ordinal += 1

            seconds = (
                45.001
                if ordinal == slow_ordinal
                else 10.0
            )

            rows.append(
                accepted(
                    ordinal,
                    round_index,
                    position,
                    seconds,
                )
            )

    return rows


def test_identity_and_fresh_gate() -> None:
    p = module.verify_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-010"
    )

    assert p[
        "fresh_provider_qualification"
    ] is True

    assert p[
        "qualification_attempt_count"
    ] == 1

    assert p[
        "planned_probe_count"
    ] == 9

    assert p[
        "round_count"
    ] == 3

    assert p[
        "rerun_authorized"
    ] is False


def test_exact_007r1_target_descriptor() -> None:
    p = module.verify_plan()

    assert p[
        "semantic_successor_target"
    ] == module.target_descriptor()

    target = module.target_descriptor()

    assert target["work_order"] == (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
        "PREDICATE-CARRIER-DISCRIMINATION-007R1"
    )

    assert target[
        "semantic_request_count"
    ] == 18

    assert target[
        "pair_count"
    ] == 9

    assert target[
        "qualification_selection_mode"
    ] == "EXPLICIT_PATH_ONLY"

    assert target[
        "specific_qualification_number_hardcoded"
    ] is False


def test_schedule_is_exactly_balanced() -> None:
    p = module.verify_plan()

    schedule = p[
        "probe_schedule"
    ]

    assert len(schedule) == 9

    assert [
        x["ordinal"]
        for x in schedule
    ] == list(range(1, 10))

    counts = Counter(
        x["probe_id"]
        for x in schedule
    )

    assert counts == {
        "BASIC_TEXT": 3,
        "JSON_MODE": 3,
        "PRODUCTION_TOKEN_RESERVATION": 3,
    }

    for probe_id in counts:
        positions = sorted(
            x["position"]
            for x in schedule
            if x["probe_id"] == probe_id
        )

        assert positions == [1, 2, 3]


def test_materialization_exact() -> None:
    actual = load(
        module.MANIFEST_PATH
    )

    assert actual == (
        module.materialization_document()
    )

    assert actual[
        "request_count"
    ] == 9

    assert actual[
        "round_count"
    ] == 3

    assert actual[
        "balanced_probe_positions"
    ] is True


def test_all_nine_projections_exact_source_q009_by_probe_id() -> None:
    actual = load(
        module.MANIFEST_PATH
    )

    source = module.source_rows_by_probe()

    assert len(
        actual["requests"]
    ) == 9

    for row in actual["requests"]:
        old = source[
            row["probe_id"]
        ]

        assert row[
            "request_projection"
        ] == old[
            "request_projection"
        ]

        assert row[
            "request_projection_sha256"
        ] == old[
            "request_projection_sha256"
        ]


def test_marker_text_semantics() -> None:
    projection = {
        "expected_mode":
            "TEXT_MARKER",

        "expected_value":
            "OIC_PROVIDER_OK",
    }

    assert module.validate_marker(
        projection,
        "OIC_PROVIDER_OK",
    ) is True

    assert module.validate_marker(
        projection,
        "wrong",
    ) is False


def test_marker_json_semantics() -> None:
    projection = {
        "expected_mode":
            "JSON_STATUS",

        "expected_value":
            "OIC_PROVIDER_OK",
    }

    assert module.validate_marker(
        projection,
        '{"status":"OIC_PROVIDER_OK"}',
    ) is True

    assert module.validate_marker(
        projection,
        '{"status":"wrong"}',
    ) is False

    assert module.validate_marker(
        projection,
        '{"status":"OIC_PROVIDER_OK","extra":1}',
    ) is False


def test_transport_boundary() -> None:
    p = module.verify_plan()

    assert p["provider"] == {
        "base_url":
            "https://integrate.api.nvidia.com/v1",

        "latency_headroom_seconds":
            45.0,

        "model":
            "nvidia/nemotron-3.5-lightning-30b-a3b",

        "provider_adapter_sha256":
            "c1c02303cec29eaef8cb96d1baeec735"
            "ef724d9c8a06e20a61b91388d4350339",

        "timeout_seconds":
            60.0,
    }

    assert p[
        "pacing_seconds"
    ] == 4.0

    assert p[
        "retries"
    ] == 0

    assert p[
        "replacement_probes_allowed"
    ] is False


def test_decision_qualified() -> None:
    assert module.decide(
        nine_accepted()
    ) == "QUALIFIED"


def test_decision_degraded() -> None:
    assert module.decide(
        nine_accepted(
            slow_ordinal=5
        )
    ) == "DEGRADED"


def test_decision_provider_failure() -> None:
    rows = nine_accepted()

    rows[4] = {
        **rows[4],
        "outcome":
            "PROVIDER_ERROR",
        "marker_valid":
            False,
        "elapsed_seconds":
            60.0,
    }

    assert module.decide(
        rows
    ) == "NOT_QUALIFIED"


def test_decision_marker_failure() -> None:
    rows = nine_accepted()

    rows[7] = {
        **rows[7],
        "outcome":
            "RESPONSE_MISMATCH",
        "marker_valid":
            False,
    }

    assert module.decide(
        rows
    ) == "NOT_QUALIFIED"


def test_decision_incomplete_population() -> None:
    rows = (
        nine_accepted()[:-1]
    )

    assert module.decide(
        rows
    ) == "INCOMPLETE"


def test_decision_incomplete_round() -> None:
    rows = nine_accepted()

    rows[-1]["round"] = 2

    assert module.decide(
        rows
    ) == "INCOMPLETE"


def test_no_historical_observation_reuse_or_rerun() -> None:
    p = module.verify_plan()
    m = load(
        module.MANIFEST_PATH
    )

    assert p[
        "historical_qualification_observations_reused"
    ] is False

    assert p[
        "recovery_stability_observations_reused"
    ] is False

    assert p[
        "token_reservation_localization_observations_reused"
    ] is False

    assert p[
        "qualification_009_rerun"
    ] is False

    assert p[
        "recovery_stability_002_rerun"
    ] is False

    assert p[
        "localization_001_rerun"
    ] is False

    assert m[
        "historical_observations_reused"
    ] is False

    assert m[
        "qualification_009_rerun"
    ] is False


def test_pre_execution_formal_authorization_boundary() -> None:
    p = module.verify_plan()
    m = load(
        module.MANIFEST_PATH
    )

    assert p[
        "qualification_010_live_execution_authorized"
    ] is False

    assert p[
        "qualification_010_executed"
    ] is False

    assert p[
        "provider_qualification_established"
    ] is False

    assert p[
        "ontology_007r1_execution_authorized"
    ] is False

    assert p[
        "ontology_007r1_executed"
    ] is False

    assert m[
        "live_run_executed"
    ] is False

    assert m[
        "qualification_010_formally_closed"
    ] is False

    assert m[
        "qualification_010_qualified"
    ] is False

    assert m[
        "provider_qualification_established"
    ] is False

    assert m[
        "ontology_007r1_execution_authorized"
    ] is False


def test_offline_preflight_preserves_gate() -> None:
    p = module.preflight()

    assert p[
        "provider_call_made"
    ] is False

    assert p[
        "model_call_made"
    ] is False

    assert p[
        "network_request_made"
    ] is False

    assert p[
        "qualification_010_live_execution_authorized"
    ] is False

    assert p[
        "qualification_010_executed"
    ] is False

    assert p[
        "ontology_007r1_execution_authorized"
    ] is False


def test_provider_construction_only_inside_live_execution() -> None:
    text = SCRIPT.read_text(
        encoding="utf-8"
    )

    live_pos = text.index(
        "def execute_live()"
    )

    preflight_pos = text.index(
        "preflight()",
        live_pos,
    )

    provider_pos = text.index(
        "provider = NvidiaNimProvider(",
        live_pos,
    )

    assert (
        live_pos
        < preflight_pos
        < provider_pos
    )


def test_no_semantic_or_architecture_change() -> None:
    p = module.verify_plan()
    freeze = module.preflight()

    assert p[
        "semantic_hypothesis"
    ] is None

    assert p[
        "semantic_hypothesis_evaluated"
    ] is False

    assert p[
        "canonicalization_performed"
    ] is False

    assert p[
        "institutional_ir_constructed"
    ] is False

    assert p[
        "architecture_change_authorized"
    ] is False

    assert freeze[
        "architecture_change_authorized"
    ] is False
