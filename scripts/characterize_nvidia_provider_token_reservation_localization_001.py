#!/usr/bin/env python3
"""NVIDIA token-reservation localization 001.

Fresh paired provider-path characterization comparing two otherwise identical
structured-output requests whose provider-bound difference is max_tokens:
64 versus 4096.

Offline is the default. No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import NvidiaNimConfig, NvidiaNimProvider

WORK_ORDER: Final[str] = (
    "OIC-NVIDIA-PROVIDER-TOKEN-RESERVATION-LOCALIZATION-001"
)

PREREG_COMMIT: Final[str] = (
    "b949efd88e4909f30429a62fa9c825553065233e"
)

BENCH = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-token-reservation-localization-001"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

RS002_RESULT = (
    ROOT
    / "benchmarks/provider-recovery-stability/nvidia-nim-002/"
      "EXECUTION-RESULT-v0.1.json"
)

RS002_ADJ = (
    ROOT
    / "benchmarks/provider-recovery-stability/nvidia-nim-002/"
      "POST-RUN-ADJUDICATION.md"
)

Q009_MANIFEST = (
    ROOT
    / "benchmarks/provider-qualification/nvidia-nim-009/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

Q009_SCRIPT = ROOT / "scripts/qualify_nvidia_provider_009.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_token_reservation_localization_001.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-characterization-receipts/"
      "OIC-NVIDIA-PROVIDER-TOKEN-RESERVATION-LOCALIZATION-001.json"
)

PLAN_SHA256: Final[str] = (
    "68bc0c35f73beec084d951b00f578b63517d9fd17dc962981468c5c025298821"
)
PREREG_SHA256: Final[str] = (
    "25e33d0df3ac5c386d98c9f0d31bbcb7000f463e21fabd5ee2325a5e54b7d6dd"
)
FREEZE_V1_SHA256: Final[str] = (
    "bad9628817e0b62d321078151644526cf663d93b1b69004365f191b35bdd4bbc"
)

RS002_RESULT_SHA256: Final[str] = (
    "b997d47e66652a2fc4ff99d7ae9d133cc2c28e2dcd49bc2b9a02bbd25ea22cf4"
)
RS002_ADJ_SHA256: Final[str] = (
    "8fc1322440b2121fbd69f1a8d999f3cc867f32f1b60ff3639dde4bc975fc754e"
)

Q009_MANIFEST_SHA256: Final[str] = (
    "e725fbf588ff4f304ebb5f1fd48b5f6bad64e1bb54d06aa3e528396c9362a485"
)
Q009_SCRIPT_SHA256: Final[str] = (
    "d7284716642467ace8ce4dd81bc5cbeb0b9219c69ef51ff9a61fa13e0d745363"
)

PROBE_SPEC_SHA256: Final[str] = (
    "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0

PAIR_COUNT: Final[int] = 12
PLANNED_CALLS: Final[int] = 24

ARM_A: Final[str] = "A_JSON_64"
ARM_B: Final[str] = "B_JSON_4096"

_SOURCE_MODULE_NAME: Final[str] = "_localization001_frozen_q009"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise SystemExit(
            f"FAIL expected JSON object: {path}"
        )

    return value


def verify_frozen_sources() -> None:
    expected = {
        PLAN_PATH:
            PLAN_SHA256,

        PREREG_PATH:
            PREREG_SHA256,

        FREEZE_V1_PATH:
            FREEZE_V1_SHA256,

        RS002_RESULT:
            RS002_RESULT_SHA256,

        RS002_ADJ:
            RS002_ADJ_SHA256,

        Q009_MANIFEST:
            Q009_MANIFEST_SHA256,

        Q009_SCRIPT:
            Q009_SCRIPT_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)

        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: "
                f"{path}: {actual} != {expected_sha}"
            )


def source_q009() -> ModuleType:
    verify_frozen_sources()

    if _SOURCE_MODULE_NAME in sys.modules:
        return sys.modules[_SOURCE_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _SOURCE_MODULE_NAME,
        Q009_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise SystemExit(
            "FAIL cannot load frozen Q009 instrument"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    ):
        raise SystemExit(
            "FAIL frozen Q009 identity drift"
        )

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL frozen Q009 probe-spec drift"
        )

    if module.TIMEOUT_SECONDS != TIMEOUT_SECONDS:
        raise SystemExit("FAIL timeout drift")

    if module.LATENCY_HEADROOM_SECONDS != (
        LATENCY_HEADROOM_SECONDS
    ):
        raise SystemExit("FAIL headroom drift")

    if module.PACING_SECONDS != PACING_SECONDS:
        raise SystemExit("FAIL pacing drift")

    return module


def prereg_context() -> dict[str, Any]:
    verify_frozen_sources()

    plan = load_json(PLAN_PATH)
    freeze = load_json(FREEZE_V1_PATH)
    rs002 = load_json(RS002_RESULT)

    assert plan["work_order"] == WORK_ORDER
    assert plan["pair_count"] == PAIR_COUNT
    assert plan["planned_provider_calls"] == PLANNED_CALLS

    assert plan["frozen_provider_bound_delta"][
        "only_changed_field"
    ] == "max_tokens"

    assert plan["frozen_provider_bound_delta"][
        "arm_a_value"
    ] == 64

    assert plan["frozen_provider_bound_delta"][
        "arm_b_value"
    ] == 4096

    assert plan["transport"]["timeout_seconds"] == (
        TIMEOUT_SECONDS
    )

    assert plan["transport"][
        "latency_headroom_seconds"
    ] == LATENCY_HEADROOM_SECONDS

    assert plan["transport"]["pacing_seconds"] == (
        PACING_SECONDS
    )

    assert plan["transport"]["retries"] == 0
    assert plan["transport"][
        "replacement_observations_allowed"
    ] is False

    assert plan[
        "historical_observations_reused_as_new_observations"
    ] is False

    assert plan["recovery_stability_002_rerun"] is False
    assert plan["q010_created"] is False
    assert plan["q010_authorized"] is False

    assert plan["ontology_007_execution_authorized"] is False
    assert plan["ontology_007_executed"] is False

    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False
    assert plan["architecture_change_authorized"] is False

    assert freeze["work_order"] == WORK_ORDER
    assert freeze["pair_count"] == 12
    assert freeze["planned_provider_calls"] == 24
    assert freeze["provider_bound_delta"] == (
        "MAX_TOKENS_ONLY"
    )

    assert freeze["q010_created"] is False
    assert freeze["q010_authorized"] is False
    assert freeze["ontology_007_execution_authorized"] is False
    assert freeze["live_run_executed"] is False

    assert rs002["status"] == (
        "CLOSED_RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE"
    )

    assert rs002["root_cause"] == "NOT_ESTABLISHED"
    assert rs002["rerun_authorized"] is False
    assert rs002["q010_authorized"] is False
    assert rs002["ontology_007_execution_authorized"] is False

    source_q009().verify_plan()

    return plan


def probes_by_arm() -> dict[str, Any]:
    q009 = source_q009()

    by_probe = {
        probe.probe_id: probe
        for probe in q009.probes()
    }

    if "JSON_MODE" not in by_probe:
        raise SystemExit(
            "FAIL frozen JSON_MODE probe missing"
        )

    if "PRODUCTION_TOKEN_RESERVATION" not in by_probe:
        raise SystemExit(
            "FAIL frozen production-reservation probe missing"
        )

    return {
        ARM_A:
            by_probe["JSON_MODE"],

        ARM_B:
            by_probe["PRODUCTION_TOKEN_RESERVATION"],
    }


def source_rows_by_arm() -> dict[str, dict[str, Any]]:
    manifest = load_json(Q009_MANIFEST)

    by_probe = {
        row["probe_id"]: row
        for row in manifest["requests"]
    }

    return {
        ARM_A:
            by_probe["JSON_MODE"],

        ARM_B:
            by_probe["PRODUCTION_TOKEN_RESERVATION"],
    }


def provider_projection(probe: Any) -> dict[str, Any]:
    return {
        "system_prompt":
            probe.system_prompt,

        "user_prompt":
            probe.user_prompt,

        "response_format":
            probe.response_format,

        "temperature":
            0.0,

        "max_tokens":
            probe.max_tokens,
    }


def verify_max_tokens_only_delta() -> None:
    probes = probes_by_arm()

    a = provider_projection(probes[ARM_A])
    b = provider_projection(probes[ARM_B])

    assert a["max_tokens"] == 64
    assert b["max_tokens"] == 4096

    for key in (
        "system_prompt",
        "user_prompt",
        "response_format",
        "temperature",
    ):
        if a[key] != b[key]:
            raise SystemExit(
                f"FAIL provider-bound delta is not max_tokens-only: {key}"
            )


def materialization_document() -> dict[str, Any]:
    plan = prereg_context()
    q009 = source_q009()
    probes = probes_by_arm()
    source_rows = source_rows_by_arm()

    verify_max_tokens_only_delta()

    rows: list[dict[str, Any]] = []

    for item in plan["execution_plan"]:
        arm = item["arm"]
        probe = probes[arm]

        source_projection = q009.request_projection(
            probe
        )

        frozen_source = source_rows[arm]

        if source_projection != frozen_source[
            "request_projection"
        ]:
            raise SystemExit(
                f"FAIL frozen source projection drift: {arm}"
            )

        source_sha = q009.canonical_sha256(
            source_projection
        )

        if source_sha != frozen_source[
            "request_projection_sha256"
        ]:
            raise SystemExit(
                f"FAIL frozen source projection SHA drift: {arm}"
            )

        provider_request = provider_projection(
            probe
        )

        rows.append({
            "execution_ordinal":
                int(item["execution_ordinal"]),

            "pair_index":
                int(item["pair_index"]),

            "position_in_pair":
                int(item["position_in_pair"]),

            "arm":
                arm,

            "source_probe_id":
                probe.probe_id,

            "source_request_projection":
                source_projection,

            "source_request_projection_sha256":
                source_sha,

            "provider_request_projection":
                provider_request,

            "provider_request_projection_sha256":
                canonical_sha256(provider_request),

            "fresh_observation":
                True,

            "historical_live_observation_reused":
                False,

            "provider_constructed":
                False,

            "network_request_made":
                False,
        })

    if len(rows) != 24:
        raise SystemExit(
            "FAIL Localization 001 materialization count"
        )

    a_provider = {
        row["provider_request_projection_sha256"]
        for row in rows
        if row["arm"] == ARM_A
    }

    b_provider = {
        row["provider_request_projection_sha256"]
        for row in rows
        if row["arm"] == ARM_B
    }

    if len(a_provider) != 1 or len(b_provider) != 1:
        raise SystemExit(
            "FAIL arm provider request non-determinism"
        )

    return {
        "work_order":
            WORK_ORDER,

        "status":
            "MATERIALIZED_OFFLINE_NOT_EXECUTED",

        "source_work_order":
            "OIC-NVIDIA-PROVIDER-QUALIFICATION-009",

        "source_q009_request_materialization_sha256":
            Q009_MANIFEST_SHA256,

        "source_probe_spec_sha256":
            PROBE_SPEC_SHA256,

        "pair_count":
            12,

        "request_count":
            24,

        "arm_a_observation_count":
            12,

        "arm_b_observation_count":
            12,

        "arm_a_first_count":
            6,

        "arm_b_first_count":
            6,

        "provider_bound_delta":
            "MAX_TOKENS_ONLY",

        "arm_a_max_tokens":
            64,

        "arm_b_max_tokens":
            4096,

        "retries":
            0,

        "replacement_observations_allowed":
            False,

        "pacing_seconds":
            4.0,

        "historical_observations_reused_as_new_observations":
            False,

        "recovery_stability_002_rerun":
            False,

        "q010_created":
            False,

        "q010_authorized":
            False,

        "ontology_007_execution_authorized":
            False,

        "ontology_007_executed":
            False,

        "provider_constructed":
            False,

        "network_request_made":
            False,

        "live_run_executed":
            False,

        "requests":
            rows,
    }


def materialize() -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP materialization already exists: "
            f"{MATERIALIZATION_PATH}"
        )

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            materialization_document(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print("materialized 24 fresh paired observations")
    print("12 A_JSON_64 / 12 B_JSON_4096")
    print("provider-bound delta: max_tokens only")
    print("provider/model/network calls: ZERO")


def verify_materialization() -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit(
            "FAIL Localization 001 materialization absent"
        )

    actual = load_json(
        MATERIALIZATION_PATH
    )

    expected = materialization_document()

    if actual != expected:
        raise SystemExit(
            "FAIL Localization 001 materialization drift"
        )

    return actual


def classify(
    attempts: Sequence[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    complete_pairs = 0

    for pair_index in range(1, 13):
        rows = [
            x for x in attempts
            if int(x["pair_index"]) == pair_index
        ]

        if len(rows) == 2:
            complete_pairs += 1

    gate = {
        "terminal_observations":
            len(attempts),

        "terminal_observations_required":
            24,

        "complete_pairs":
            complete_pairs,

        "complete_pairs_required":
            12,

        "adjudicable":
            (
                len(attempts) == 24
                and complete_pairs == 12
            ),
    }

    if not gate["adjudicable"]:
        return "INCOMPLETE_LOCALIZATION", gate

    def failed(row: dict[str, Any]) -> bool:
        return (
            row["outcome"] != "ACCEPTED"
            or row.get("marker_valid") is not True
        )

    a_failures = [
        x for x in attempts
        if x["arm"] == ARM_A
        and failed(x)
    ]

    b_failures = [
        x for x in attempts
        if x["arm"] == ARM_B
        and failed(x)
    ]

    if a_failures and b_failures:
        return (
            "SHARED_PROVIDER_PATH_FAILURE_PATTERN",
            gate,
        )

    if len(b_failures) >= 2 and not a_failures:
        return (
            "RESERVATION_SIZE_SPECIFIC_FAILURE_PATTERN",
            gate,
        )

    if len(a_failures) >= 2 and not b_failures:
        return (
            "CONTROL_SPECIFIC_FAILURE_PATTERN",
            gate,
        )

    if len(a_failures) + len(b_failures) == 1:
        return (
            "SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE",
            gate,
        )

    slow = [
        x for x in attempts
        if (
            x["outcome"] == "ACCEPTED"
            and x.get("marker_valid") is True
            and float(x["elapsed_seconds"])
            > LATENCY_HEADROOM_SECONDS
        )
    ]

    if slow:
        return (
            "NO_FAILURE_WITH_LATENCY_DEGRADATION",
            gate,
        )

    return "BOUNDED_NO_FAILURE_WINDOW", gate


def paired_summary(
    attempts: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    def failed(row: dict[str, Any]) -> bool:
        return (
            row["outcome"] != "ACCEPTED"
            or row.get("marker_valid") is not True
        )

    a_failures = 0
    b_failures = 0

    b_only_pairs = 0
    a_only_pairs = 0
    shared_failure_pairs = 0

    for pair_index in range(1, 13):
        rows = [
            x for x in attempts
            if int(x["pair_index"]) == pair_index
        ]

        a = next(
            (
                x for x in rows
                if x["arm"] == ARM_A
            ),
            None,
        )

        b = next(
            (
                x for x in rows
                if x["arm"] == ARM_B
            ),
            None,
        )

        if a is None or b is None:
            continue

        a_failed = failed(a)
        b_failed = failed(b)

        a_failures += int(a_failed)
        b_failures += int(b_failed)

        if b_failed and not a_failed:
            b_only_pairs += 1

        elif a_failed and not b_failed:
            a_only_pairs += 1

        elif a_failed and b_failed:
            shared_failure_pairs += 1

    latency = {}

    for arm in (ARM_A, ARM_B):
        values = [
            float(x["elapsed_seconds"])
            for x in attempts
            if (
                x["arm"] == arm
                and x["outcome"] == "ACCEPTED"
                and x.get("marker_valid") is True
            )
        ]

        latency[arm] = {
            "accepted_count":
                len(values),

            "minimum_seconds":
                min(values) if values else None,

            "maximum_seconds":
                max(values) if values else None,

            "median_seconds":
                statistics.median(values)
                if values
                else None,
        }

    return {
        "failure_count_by_arm": {
            ARM_A: a_failures,
            ARM_B: b_failures,
        },

        "b_only_failure_pairs":
            b_only_pairs,

        "a_only_failure_pairs":
            a_only_pairs,

        "shared_failure_pairs":
            shared_failure_pairs,

        "accepted_latency_by_arm":
            latency,
    }


def verify_freeze_v2() -> dict[str, Any]:
    freeze = load_json(
        FREEZE_V2_PATH
    )

    expected = {
        "plan_sha256":
            sha256(PLAN_PATH),

        "preregistration_sha256":
            sha256(PREREG_PATH),

        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),

        "instrument_sha256":
            sha256(Path(__file__)),

        "contract_test_sha256":
            sha256(CONTRACT_TEST),

        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),

        "recovery_stability_002_execution_result_sha256":
            sha256(RS002_RESULT),

        "recovery_stability_002_post_run_adjudication_sha256":
            sha256(RS002_ADJ),

        "q009_request_materialization_sha256":
            sha256(Q009_MANIFEST),

        "q009_instrument_sha256":
            sha256(Q009_SCRIPT),
    }

    for key, value in expected.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL Localization 001 freeze digest mismatch: "
                f"{key}"
            )

    assert freeze["pair_count"] == 12
    assert freeze["planned_provider_calls"] == 24
    assert freeze["provider_bound_delta"] == (
        "MAX_TOKENS_ONLY"
    )

    assert freeze["arm_a_max_tokens"] == 64
    assert freeze["arm_b_max_tokens"] == 4096

    assert freeze["retries"] == 0
    assert freeze[
        "replacement_observations_allowed"
    ] is False

    assert freeze["q010_created"] is False
    assert freeze["q010_authorized"] is False

    assert freeze["ontology_007_execution_authorized"] is False
    assert freeze["ontology_007_executed"] is False
    assert freeze["live_run_executed"] is False

    return freeze


def static_preflight() -> dict[str, Any]:
    plan = prereg_context()
    verify_materialization()
    verify_max_tokens_only_delta()
    verify_freeze_v2()

    return plan


def execute_live() -> tuple[list[dict[str, Any]], str]:
    static_preflight()

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Localization 001 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    q009 = source_q009()
    source_q006 = q009.source_q006()

    probes = probes_by_arm()
    plan = load_json(PLAN_PATH)

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=q009.DEFAULT_NIM_MODEL,
            base_url=q009.DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []

    for index, item in enumerate(
        plan["execution_plan"]
    ):
        arm = item["arm"]
        probe = probes[arm]

        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        print(
            f"[{item['execution_ordinal']:02d}/24] "
            f"pair={item['pair_index']} "
            f"position={item['position_in_pair']} "
            f"arm={arm} "
            f"max_tokens={probe.max_tokens} START",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(
                request
            )

        except ModelProviderError as exc:
            elapsed = (
                time.monotonic()
                - started
            )

            attempt = {
                "execution_ordinal":
                    int(item["execution_ordinal"]),

                "pair_index":
                    int(item["pair_index"]),

                "position_in_pair":
                    int(item["position_in_pair"]),

                "arm":
                    arm,

                "source_probe_id":
                    probe.probe_id,

                "max_tokens":
                    probe.max_tokens,

                "outcome":
                    "PROVIDER_ERROR",

                "elapsed_seconds":
                    round(elapsed, 3),

                "marker_valid":
                    False,

                "error_type":
                    type(exc).__name__,

                "error_message":
                    str(exc),
            }

        else:
            elapsed = (
                time.monotonic()
                - started
            )

            marker_valid = source_q006.validate_marker(
                probe,
                response.content,
            )

            attempt = {
                "execution_ordinal":
                    int(item["execution_ordinal"]),

                "pair_index":
                    int(item["pair_index"]),

                "position_in_pair":
                    int(item["position_in_pair"]),

                "arm":
                    arm,

                "source_probe_id":
                    probe.probe_id,

                "max_tokens":
                    probe.max_tokens,

                "outcome":
                    (
                        "ACCEPTED"
                        if marker_valid
                        else "RESPONSE_MISMATCH"
                    ),

                "elapsed_seconds":
                    round(elapsed, 3),

                "marker_valid":
                    marker_valid,

                "provider":
                    response.provider,

                "model":
                    response.model,

                "request_id":
                    response.request_id,

                "content_sha256":
                    hashlib.sha256(
                        response.content.encode(
                            "utf-8"
                        )
                    ).hexdigest(),
            }

        attempts.append(
            attempt
        )

        print(
            f"[{item['execution_ordinal']:02d}/24] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={attempt['elapsed_seconds']}",
            flush=True,
        )

        if index < 23:
            time.sleep(
                PACING_SECONDS
            )

    disposition, gate = classify(
        attempts
    )

    summary = paired_summary(
        attempts
    )

    receipt = {
        "work_order":
            WORK_ORDER,

        "preregistration_commit":
            PREREG_COMMIT,

        "instrument_freeze_sha256":
            sha256(FREEZE_V2_PATH),

        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),

        "recovery_stability_002_execution_result_sha256":
            sha256(RS002_RESULT),

        "live_run_executed":
            True,

        "fresh_observation_count":
            len(attempts),

        "pair_count":
            12,

        "attempts":
            attempts,

        "adjudicability":
            gate,

        "paired_summary":
            summary,

        "scientific_disposition":
            disposition,

        "localization_001_formally_closed":
            False,

        "provider_bound_delta":
            "MAX_TOKENS_ONLY",

        "arm_a_max_tokens":
            64,

        "arm_b_max_tokens":
            4096,

        "retries":
            0,

        "replacement_observations_allowed":
            False,

        "pacing_seconds":
            4.0,

        "latency_headroom_seconds":
            45.0,

        "historical_observations_reused_as_new_observations":
            False,

        "recovery_stability_002_rerun":
            False,

        "q010_created":
            False,

        "q010_authorized":
            False,

        "ontology_007_execution_authorized":
            False,

        "ontology_007_executed":
            False,

        "semantic_hypothesis":
            None,

        "semantic_hypothesis_evaluated":
            False,

        "canonicalization_performed":
            False,

        "institutional_ir_constructed":
            False,

        "architecture_change_authorized":
            False,

        "independent_validation_claim":
            False,

        "self_adjudication":
            "NOT SELF-ADJUDICATED",

        "rerun_authorized":
            False,
    }

    RECEIPT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECEIPT_PATH.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"receipt written: {RECEIPT_PATH}"
    )
    print(
        f"scientific disposition: {disposition}"
    )
    print("formal closure: FALSE")
    print("Q010 created: FALSE")
    print("Ontology 007 authorization: FALSE")

    return attempts, disposition


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--materialize",
        action="store_true",
    )

    modes.add_argument(
        "--live",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    if args.materialize:
        prereg_context()
        materialize()
        return 0

    if args.live:
        execute_live()
        return 0

    plan = static_preflight()

    print(
        "PASS frozen Token-Reservation Localization 001 instrument"
    )
    print(
        f"observations: {plan['planned_provider_calls']}"
    )
    print(
        f"pairs: {plan['pair_count']}"
    )
    print("Arm A: JSON / max_tokens 64")
    print("Arm B: same JSON / max_tokens 4096")
    print("provider-bound delta: max_tokens only")
    print("order: AB/BA alternating")
    print("A first: 6")
    print("B first: 6")
    print("headroom: 45 seconds")
    print("retries: ZERO")
    print("replacements: FORBIDDEN")
    print("historical response reuse: FALSE")
    print("Q010 created: FALSE")
    print("Ontology 007 authorization: FALSE")
    print(
        "offline preflight only; "
        "no provider/model/network request made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
