from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_nvidia_provider_token_reservation_localization_001.py"
)

MODULE_NAME = (
    "_test_nvidia_provider_token_reservation_localization_001"
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
spec.loader.exec_module(module)


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def accepted_population(
    *,
    slow_ordinal: int | None = None,
) -> list[dict[str, Any]]:
    plan = load(
        module.PLAN_PATH
    )

    rows = []

    for item in plan["execution_plan"]:
        arm = item["arm"]

        rows.append({
            "execution_ordinal":
                item["execution_ordinal"],

            "pair_index":
                item["pair_index"],

            "position_in_pair":
                item["position_in_pair"],

            "arm":
                arm,

            "max_tokens":
                (
                    64
                    if arm == module.ARM_A
                    else 4096
                ),

            "outcome":
                "ACCEPTED",

            "marker_valid":
                True,

            "elapsed_seconds":
                (
                    45.001
                    if item["execution_ordinal"]
                    == slow_ordinal
                    else 1.0
                ),
        })

    return rows


def fail(
    rows: list[dict[str, Any]],
    ordinal: int,
) -> None:
    row = rows[
        ordinal - 1
    ]

    row.update({
        "outcome":
            "PROVIDER_ERROR",

        "marker_valid":
            False,

        "elapsed_seconds":
            60.0,

        "error_type":
            "ModelProviderError",

        "error_message":
            "NVIDIA NIM connection timed out",
    })


def test_identity_and_population() -> None:
    plan = module.prereg_context()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-TOKEN-RESERVATION-LOCALIZATION-001"
    )

    assert plan["pair_count"] == 12
    assert plan["planned_provider_calls"] == 24


def test_exact_max_tokens_only_delta() -> None:
    module.verify_max_tokens_only_delta()

    probes = module.probes_by_arm()

    a = module.provider_projection(
        probes[module.ARM_A]
    )

    b = module.provider_projection(
        probes[module.ARM_B]
    )

    assert a["max_tokens"] == 64
    assert b["max_tokens"] == 4096

    for key in (
        "system_prompt",
        "user_prompt",
        "response_format",
        "temperature",
    ):
        assert a[key] == b[key]


def test_order_balance() -> None:
    plan = module.prereg_context()
    rows = plan["execution_plan"]

    assert len(rows) == 24

    assert sum(
        x["arm"] == module.ARM_A
        for x in rows
    ) == 12

    assert sum(
        x["arm"] == module.ARM_B
        for x in rows
    ) == 12

    assert sum(
        x["arm"] == module.ARM_A
        and x["position_in_pair"] == 1
        for x in rows
    ) == 6

    assert sum(
        x["arm"] == module.ARM_B
        and x["position_in_pair"] == 1
        for x in rows
    ) == 6


def test_materialization_exact_source_parity() -> None:
    actual = load(
        module.MATERIALIZATION_PATH
    )

    expected = module.materialization_document()

    assert actual == expected

    assert actual["request_count"] == 24
    assert actual["pair_count"] == 12

    assert actual["provider_bound_delta"] == (
        "MAX_TOKENS_ONLY"
    )


def test_classify_shared_failure() -> None:
    rows = accepted_population()

    # Pair 1: A ordinal 1, B ordinal 2.
    fail(rows, 1)
    fail(rows, 2)

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "SHARED_PROVIDER_PATH_FAILURE_PATTERN"
    )


def test_classify_reservation_specific() -> None:
    rows = accepted_population()

    # B ordinals in odd pairs.
    fail(rows, 2)
    fail(rows, 6)

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "RESERVATION_SIZE_SPECIFIC_FAILURE_PATTERN"
    )


def test_classify_control_specific() -> None:
    rows = accepted_population()

    fail(rows, 1)
    fail(rows, 5)

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "CONTROL_SPECIFIC_FAILURE_PATTERN"
    )


def test_classify_single_failure_inconclusive() -> None:
    rows = accepted_population()

    fail(rows, 2)

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE"
    )


def test_classify_latency_degradation() -> None:
    rows = accepted_population(
        slow_ordinal=2
    )

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "NO_FAILURE_WITH_LATENCY_DEGRADATION"
    )


def test_classify_bounded_no_failure() -> None:
    disposition, gate = module.classify(
        accepted_population()
    )

    assert gate["adjudicable"] is True

    assert disposition == (
        "BOUNDED_NO_FAILURE_WINDOW"
    )


def test_classify_incomplete() -> None:
    rows = accepted_population()[:-1]

    disposition, gate = module.classify(
        rows
    )

    assert gate["adjudicable"] is False

    assert disposition == (
        "INCOMPLETE_LOCALIZATION"
    )


def test_paired_summary() -> None:
    rows = accepted_population()

    fail(rows, 2)
    fail(rows, 6)

    summary = module.paired_summary(
        rows
    )

    assert summary[
        "failure_count_by_arm"
    ][module.ARM_A] == 0

    assert summary[
        "failure_count_by_arm"
    ][module.ARM_B] == 2

    assert summary[
        "b_only_failure_pairs"
    ] == 2

    assert summary[
        "a_only_failure_pairs"
    ] == 0

    assert summary[
        "shared_failure_pairs"
    ] == 0


def test_downstream_boundary() -> None:
    plan = module.prereg_context()

    assert plan[
        "historical_observations_reused_as_new_observations"
    ] is False

    assert plan[
        "recovery_stability_002_rerun"
    ] is False

    assert plan["q010_created"] is False
    assert plan["q010_authorized"] is False

    assert plan[
        "ontology_007_execution_authorized"
    ] is False

    assert plan[
        "ontology_007_executed"
    ] is False

    assert plan["semantic_hypothesis"] is None

    assert plan[
        "semantic_hypothesis_evaluated"
    ] is False

    assert plan[
        "architecture_change_authorized"
    ] is False


def test_offline_preflight() -> None:
    plan = module.static_preflight()

    assert plan[
        "provider_call_made"
    ] is False

    assert plan[
        "model_call_made"
    ] is False

    assert plan[
        "network_request_made"
    ] is False

    assert plan[
        "live_run_executed"
    ] is False

    assert plan[
        "q010_created"
    ] is False
