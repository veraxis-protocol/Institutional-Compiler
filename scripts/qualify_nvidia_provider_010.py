#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 010.

One fresh, balanced, nine-call immediate provider-path qualification gate
for the exact frozen Ontology 007R1 target.

All three request projections are inherited byte-identically by probe_id
from frozen Qualification 009 materialization.

Offline is the default. No provider is constructed without --live.

A live QUALIFIED disposition does not itself authorize Ontology 007R1.
Formal tracked Q010 closure and independent verification are required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Final, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

WORK_ORDER: Final[str] = (
    "OIC-NVIDIA-PROVIDER-QUALIFICATION-010"
)

PREREG_COMMIT: Final[str] = (
    "81fd04441ea0a91de83122e980bb94855e97aed0"
)

BENCH = (
    ROOT
    / "benchmarks/provider-qualification/nvidia-nim-010"
)

SYNTHESIS_PATH = (
    BENCH / "PROVIDER-EVIDENCE-SYNTHESIS-v0.1.json"
)
PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MANIFEST_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE_Q009_MANIFEST = (
    ROOT
    / "benchmarks/provider-qualification/nvidia-nim-009/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-"
      "discrimination-007r1"
)

TARGET_REPAIR = (
    TARGET_DIR / "AUTHORIZATION-REPAIR-BINDING-v0.1.json"
)
TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"

TARGET_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007r1.py"
)

TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007r1.py"
)

SOURCE_O007_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007.py"
)

SOURCE_O007_MANIFEST = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-"
      "discrimination-007/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_qualification_010.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-010.json"
)

SYNTHESIS_SHA256: Final[str] = (
    "0bfb663817a5c749eb52814779068eb216af51cff916132029d955d5f4b05b2c"
)
PLAN_SHA256: Final[str] = (
    "e10a99af5faf748b454897053dc11d8d3894753a183366bbd8ebc15011dc0a71"
)
PREREG_SHA256: Final[str] = (
    "f846c9df165d014f5141c4fce1603f6b6d5bc6a6119a04d1aa55fcf37b2f8eb7"
)
FREEZE_V1_SHA256: Final[str] = (
    "ce57649e41b0e360dadc3dcbd2acb9ff9092d43961e019bbe559f3f2e122e115"
)

SOURCE_Q009_MANIFEST_SHA256: Final[str] = (
    "e725fbf588ff4f304ebb5f1fd48b5f6bad64e1bb54d06aa3e528396c9362a485"
)

TARGET_REPAIR_SHA256: Final[str] = (
    "a6acc0f22a7872d007f39cde8e8da662b12e6bde824869ee6fd9812858bb8b2d"
)
TARGET_PLAN_SHA256: Final[str] = (
    "7558595f9f5caca541b03dd65f9bfeb2dddd8f05138ec9b47c06764904ba785d"
)
TARGET_PREREG_SHA256: Final[str] = (
    "1f550475326da56fb89df660de28967c149d7be7e67146a55e2aa8019a7f354b"
)
TARGET_FREEZE_V1_SHA256: Final[str] = (
    "c696e50eecd9d7416b5ab311dcfc1e41d01f75ec3b7aaa2826484f0cefd09027"
)
TARGET_MANIFEST_SHA256: Final[str] = (
    "9faa8e9881b4bad0f9252cf0a3bdcf689e59e82357307c29488ab4ed5969bc57"
)
TARGET_FREEZE_V2_SHA256: Final[str] = (
    "8411a24dc31f2975af51def6c2352ec284ec6490acdf3269859230412435050d"
)
TARGET_SCRIPT_SHA256: Final[str] = (
    "d3a65a906e3bb165458f0ca6fc0afc96f88d376d1d01bb20f577ab4a9189c830"
)
TARGET_TEST_SHA256: Final[str] = (
    "873c716f55ea0005320866bd21765f3d930faeffb7e7a1aa3ff53945263a430c"
)

SOURCE_O007_SCRIPT_SHA256: Final[str] = (
    "be752c975a6da03e9a0237aa7df09f38caf81a2e416b23584e3d86d998fa0834"
)
SOURCE_O007_MANIFEST_SHA256: Final[str] = (
    "02567faee5aa55e830207b271023bf555a6f02417433731319ab0a869020f96a"
)

ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0

PLANNED_PROBES: Final[int] = 9
ROUND_COUNT: Final[int] = 3


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


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
        SYNTHESIS_PATH:
            SYNTHESIS_SHA256,

        PLAN_PATH:
            PLAN_SHA256,

        PREREG_PATH:
            PREREG_SHA256,

        FREEZE_V1_PATH:
            FREEZE_V1_SHA256,

        SOURCE_Q009_MANIFEST:
            SOURCE_Q009_MANIFEST_SHA256,

        TARGET_REPAIR:
            TARGET_REPAIR_SHA256,

        TARGET_PLAN:
            TARGET_PLAN_SHA256,

        TARGET_PREREG:
            TARGET_PREREG_SHA256,

        TARGET_FREEZE_V1:
            TARGET_FREEZE_V1_SHA256,

        TARGET_MANIFEST:
            TARGET_MANIFEST_SHA256,

        TARGET_FREEZE_V2:
            TARGET_FREEZE_V2_SHA256,

        TARGET_SCRIPT:
            TARGET_SCRIPT_SHA256,

        TARGET_TEST:
            TARGET_TEST_SHA256,

        SOURCE_O007_SCRIPT:
            SOURCE_O007_SCRIPT_SHA256,

        SOURCE_O007_MANIFEST:
            SOURCE_O007_MANIFEST_SHA256,

        ADAPTER:
            ADAPTER_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)

        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: "
                f"{path}: {actual} != {expected_sha}"
            )


def target_descriptor() -> dict[str, Any]:
    return {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-"
            "DISCRIMINATION-007R1",

        "preregistration_commit":
            "9505b78eb58d38795ca1075b3c0b48414470977e",

        "authorization_repair_binding_sha256":
            TARGET_REPAIR_SHA256,

        "plan_sha256":
            TARGET_PLAN_SHA256,

        "preregistration_sha256":
            TARGET_PREREG_SHA256,

        "preregistration_freeze_v0_1_sha256":
            TARGET_FREEZE_V1_SHA256,

        "freeze_v0_2_sha256":
            TARGET_FREEZE_V2_SHA256,

        "instrument_sha256":
            TARGET_SCRIPT_SHA256,

        "contract_test_sha256":
            TARGET_TEST_SHA256,

        "request_materialization_sha256":
            TARGET_MANIFEST_SHA256,

        "source_o007_instrument_sha256":
            SOURCE_O007_SCRIPT_SHA256,

        "source_o007_request_materialization_sha256":
            SOURCE_O007_MANIFEST_SHA256,

        "semantic_request_count":
            18,

        "pair_count":
            9,

        "semantic_request_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007",

        "qualification_selection_mode":
            "EXPLICIT_PATH_ONLY",

        "specific_qualification_number_hardcoded":
            False,
    }


def source_rows_by_probe() -> dict[str, dict[str, Any]]:
    verify_frozen_sources()

    source = load_json(
        SOURCE_Q009_MANIFEST
    )

    if source["request_count"] != 3:
        raise SystemExit(
            "FAIL source Q009 probe count drift"
        )

    rows = {
        row["probe_id"]: row
        for row in source["requests"]
    }

    if set(rows) != {
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    }:
        raise SystemExit(
            "FAIL source Q009 probe population drift"
        )

    return rows


def verify_plan() -> dict[str, Any]:
    verify_frozen_sources()

    plan = load_json(
        PLAN_PATH
    )

    assert plan["work_order"] == WORK_ORDER
    assert plan["fresh_provider_qualification"] is True
    assert plan["qualification_attempt_count"] == 1
    assert plan["rerun_authorized"] is False

    assert plan["planned_probe_count"] == 9
    assert plan["round_count"] == 3

    assert plan["provider"] == {
        "base_url":
            DEFAULT_NIM_BASE_URL,

        "latency_headroom_seconds":
            LATENCY_HEADROOM_SECONDS,

        "model":
            DEFAULT_NIM_MODEL,

        "provider_adapter_sha256":
            ADAPTER_SHA256,

        "timeout_seconds":
            TIMEOUT_SECONDS,
    }

    assert plan["pacing_seconds"] == PACING_SECONDS
    assert plan["retries"] == 0
    assert plan["replacement_probes_allowed"] is False

    assert plan["probe_source"]["source_work_order"] == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    )

    assert plan["probe_source"][
        "source_request_materialization_sha256"
    ] == SOURCE_Q009_MANIFEST_SHA256

    assert plan["probe_source"][
        "request_projection_semantics"
    ] == "BYTE_IDENTICAL_BY_PROBE_ID"

    assert plan[
        "semantic_successor_target"
    ] == target_descriptor()

    schedule = plan[
        "probe_schedule"
    ]

    if len(schedule) != 9:
        raise SystemExit(
            "FAIL Q010 schedule count"
        )

    if [
        x["ordinal"]
        for x in schedule
    ] != list(range(1, 10)):
        raise SystemExit(
            "FAIL Q010 schedule ordinal drift"
        )

    counts = Counter(
        x["probe_id"]
        for x in schedule
    )

    if counts != {
        "BASIC_TEXT": 3,
        "JSON_MODE": 3,
        "PRODUCTION_TOKEN_RESERVATION": 3,
    }:
        raise SystemExit(
            "FAIL Q010 probe balance drift"
        )

    for probe_id in counts:
        positions = sorted(
            x["position"]
            for x in schedule
            if x["probe_id"] == probe_id
        )

        if positions != [1, 2, 3]:
            raise SystemExit(
                f"FAIL Q010 position balance drift: "
                f"{probe_id}"
            )

    assert plan["decision_precedence"] == [
        "INCOMPLETE",
        "NOT_QUALIFIED",
        "DEGRADED",
        "QUALIFIED",
    ]

    assert plan["qualification_009_rerun"] is False
    assert plan["recovery_stability_002_rerun"] is False
    assert plan["localization_001_rerun"] is False

    assert plan[
        "historical_qualification_observations_reused"
    ] is False

    assert plan[
        "recovery_stability_observations_reused"
    ] is False

    assert plan[
        "token_reservation_localization_observations_reused"
    ] is False

    assert plan[
        "qualification_010_live_execution_authorized"
    ] is False

    assert plan["qualification_010_executed"] is False

    assert plan[
        "provider_qualification_established"
    ] is False

    assert plan[
        "ontology_007r1_execution_authorized"
    ] is False

    assert plan["ontology_007r1_executed"] is False

    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False
    assert plan["architecture_change_authorized"] is False
    assert plan["independent_validation_claim"] is False

    return plan


def validate_marker(
    projection: dict[str, Any],
    content: str,
) -> bool:
    mode = projection["expected_mode"]
    expected = projection["expected_value"]

    if mode == "TEXT_MARKER":
        return (
            content.strip()
            == expected
        )

    if mode == "JSON_STATUS":
        try:
            parsed: Any = json.loads(
                content
            )
        except json.JSONDecodeError:
            return False

        return (
            isinstance(parsed, dict)
            and set(parsed) == {"status"}
            and parsed["status"] == expected
        )

    raise ValueError(
        f"unknown expected mode: {mode}"
    )


def materialization_document() -> dict[str, Any]:
    plan = verify_plan()
    source = source_rows_by_probe()

    rows: list[dict[str, Any]] = []

    for item in plan["probe_schedule"]:
        source_row = source[
            item["probe_id"]
        ]

        projection = source_row[
            "request_projection"
        ]

        if canonical_sha256(projection) != (
            source_row[
                "request_projection_sha256"
            ]
        ):
            raise SystemExit(
                f"FAIL source Q009 projection digest: "
                f"{item['probe_id']}"
            )

        rows.append({
            "execution_ordinal":
                int(item["ordinal"]),

            "round":
                int(item["round"]),

            "position":
                int(item["position"]),

            "probe_id":
                item["probe_id"],

            "source_q009_ordinal":
                int(source_row["ordinal"]),

            "request_projection":
                projection,

            "request_projection_sha256":
                source_row[
                    "request_projection_sha256"
                ],

            "provider_constructed":
                False,

            "network_request_made":
                False,
        })

    return {
        "work_order":
            WORK_ORDER,

        "status":
            "MATERIALIZED_OFFLINE_NOT_EXECUTED",

        "semantic_successor_target":
            target_descriptor(),

        "source_q009_request_materialization_sha256":
            SOURCE_Q009_MANIFEST_SHA256,

        "request_projection_semantics":
            "BYTE_IDENTICAL_BY_PROBE_ID",

        "provider": {
            "base_url":
                DEFAULT_NIM_BASE_URL,

            "model":
                DEFAULT_NIM_MODEL,

            "timeout_seconds":
                TIMEOUT_SECONDS,

            "latency_headroom_seconds":
                LATENCY_HEADROOM_SECONDS,
        },

        "request_count":
            9,

        "round_count":
            3,

        "balanced_probe_positions":
            True,

        "retries":
            0,

        "replacement_probes_allowed":
            False,

        "pacing_seconds":
            PACING_SECONDS,

        "historical_observations_reused":
            False,

        "qualification_009_rerun":
            False,

        "recovery_stability_002_rerun":
            False,

        "localization_001_rerun":
            False,

        "provider_call_made":
            False,

        "model_call_made":
            False,

        "network_request_made":
            False,

        "live_run_executed":
            False,

        "qualification_010_formally_closed":
            False,

        "qualification_010_qualified":
            False,

        "provider_qualification_established":
            False,

        "ontology_007r1_execution_authorized":
            False,

        "ontology_007r1_executed":
            False,

        "requests":
            rows,
    }


def materialize() -> None:
    if MANIFEST_PATH.exists():
        raise SystemExit(
            f"STOP Q010 materialization already exists: "
            f"{MANIFEST_PATH}"
        )

    MANIFEST_PATH.write_text(
        json.dumps(
            materialization_document(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        "PASS Q010 materialized 9 fresh planned observations"
    )
    print(
        "three probe types × three balanced positions: PASS"
    )
    print(
        "source Q009 request-projection parity: 9/9"
    )
    print(
        "provider/model/network calls: ZERO"
    )


def verify_materialization() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "FAIL Q010 materialization missing"
        )

    actual = load_json(
        MANIFEST_PATH
    )

    expected = materialization_document()

    if actual != expected:
        raise SystemExit(
            "FAIL Q010 materialization drift"
        )

    source = source_rows_by_probe()

    for row in actual["requests"]:
        old = source[
            row["probe_id"]
        ]

        if row["request_projection"] != (
            old["request_projection"]
        ):
            raise SystemExit(
                f"FAIL request projection drift: "
                f"{row['probe_id']}"
            )

        if row["request_projection_sha256"] != (
            old["request_projection_sha256"]
        ):
            raise SystemExit(
                f"FAIL request projection SHA drift: "
                f"{row['probe_id']}"
            )

    return actual


def complete_round_count(
    attempts: Sequence[dict[str, Any]],
) -> int:
    complete = 0

    for round_index in range(
        1,
        ROUND_COUNT + 1,
    ):
        positions = {
            int(x["position"])
            for x in attempts
            if int(x["round"]) == round_index
        }

        if positions == {1, 2, 3}:
            complete += 1

    return complete


def decide(
    attempts: list[dict[str, Any]],
) -> str:
    if (
        len(attempts) != PLANNED_PROBES
        or complete_round_count(attempts)
        != ROUND_COUNT
    ):
        return "INCOMPLETE"

    if any(
        x.get("outcome") != "ACCEPTED"
        or x.get("marker_valid") is not True
        for x in attempts
    ):
        return "NOT_QUALIFIED"

    if any(
        float(x["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
        for x in attempts
    ):
        return "DEGRADED"

    return "QUALIFIED"


def preflight() -> dict[str, Any]:
    plan = verify_plan()

    verify_materialization()

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL Q010 static freeze v0.2 missing"
        )

    freeze = load_json(
        FREEZE_V2_PATH
    )

    checks = {
        "provider_evidence_synthesis_sha256":
            sha256(SYNTHESIS_PATH),

        "plan_sha256":
            sha256(PLAN_PATH),

        "preregistration_sha256":
            sha256(PREREG_PATH),

        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),

        "qualification_instrument_sha256":
            sha256(Path(__file__)),

        "contract_test_sha256":
            sha256(CONTRACT_TEST),

        "request_materialization_sha256":
            sha256(MANIFEST_PATH),

        "source_q009_request_materialization_sha256":
            sha256(SOURCE_Q009_MANIFEST),

        "provider_adapter_sha256":
            sha256(ADAPTER),

        "target_authorization_repair_binding_sha256":
            sha256(TARGET_REPAIR),

        "target_plan_sha256":
            sha256(TARGET_PLAN),

        "target_preregistration_sha256":
            sha256(TARGET_PREREG),

        "target_preregistration_freeze_v0_1_sha256":
            sha256(TARGET_FREEZE_V1),

        "target_request_materialization_sha256":
            sha256(TARGET_MANIFEST),

        "target_freeze_v0_2_sha256":
            sha256(TARGET_FREEZE_V2),

        "target_instrument_sha256":
            sha256(TARGET_SCRIPT),

        "target_contract_test_sha256":
            sha256(TARGET_TEST),

        "source_o007_instrument_sha256":
            sha256(SOURCE_O007_SCRIPT),

        "source_o007_request_materialization_sha256":
            sha256(SOURCE_O007_MANIFEST),
    }

    for key, value in checks.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL Q010 static-freeze digest mismatch: "
                f"{key}"
            )

    assert freeze["planned_probe_count"] == 9
    assert freeze["round_count"] == 3
    assert freeze["balanced_probe_positions"] is True

    assert freeze["retries"] == 0
    assert freeze["replacement_probes_allowed"] is False
    assert freeze["latency_headroom_seconds"] == 45.0
    assert freeze["pacing_seconds"] == 4.0

    assert freeze["live_run_executed"] is False

    assert freeze[
        "qualification_010_formally_closed"
    ] is False

    assert freeze[
        "qualification_010_qualified"
    ] is False

    assert freeze[
        "provider_qualification_established"
    ] is False

    assert freeze[
        "ontology_007r1_execution_authorized"
    ] is False

    assert freeze[
        "ontology_007r1_executed"
    ] is False

    assert freeze["semantic_hypothesis"] is None
    assert freeze["semantic_hypothesis_evaluated"] is False
    assert freeze["architecture_change_authorized"] is False

    return plan


def execute_live() -> tuple[list[dict[str, Any]], str]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Q010 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    preflight()

    manifest = verify_materialization()

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []

    for index, item in enumerate(
        manifest["requests"]
    ):
        projection = item[
            "request_projection"
        ]

        request = ModelRequest(
            system_prompt=
                projection["system_prompt"],

            user_prompt=
                projection["user_prompt"],

            response_format=
                projection["response_format"],

            temperature=
                float(projection["temperature"]),

            max_tokens=
                int(projection["max_tokens"]),
        )

        ordinal = int(
            item["execution_ordinal"]
        )

        print(
            f"[{ordinal:02d}/09] START "
            f"round={item['round']} "
            f"position={item['position']} "
            f"probe={item['probe_id']}",
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
                    ordinal,

                "round":
                    int(item["round"]),

                "position":
                    int(item["position"]),

                "probe_id":
                    item["probe_id"],

                "source_q009_ordinal":
                    int(
                        item[
                            "source_q009_ordinal"
                        ]
                    ),

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

            marker_valid = validate_marker(
                projection,
                response.content,
            )

            attempt = {
                "execution_ordinal":
                    ordinal,

                "round":
                    int(item["round"]),

                "position":
                    int(item["position"]),

                "probe_id":
                    item["probe_id"],

                "source_q009_ordinal":
                    int(
                        item[
                            "source_q009_ordinal"
                        ]
                    ),

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
            f"[{ordinal:02d}/09] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={attempt['elapsed_seconds']}",
            flush=True,
        )

        if index < (
            len(manifest["requests"]) - 1
        ):
            time.sleep(
                PACING_SECONDS
            )

    disposition = decide(
        attempts
    )

    receipt = {
        "work_order":
            WORK_ORDER,

        "preregistration_commit":
            PREREG_COMMIT,

        "semantic_successor_target":
            target_descriptor(),

        "source_q009_request_materialization_sha256":
            SOURCE_Q009_MANIFEST_SHA256,

        "request_materialization_sha256":
            sha256(MANIFEST_PATH),

        "instrument_freeze_sha256":
            sha256(FREEZE_V2_PATH),

        "provider": {
            "base_url":
                DEFAULT_NIM_BASE_URL,

            "model":
                DEFAULT_NIM_MODEL,

            "timeout_seconds":
                TIMEOUT_SECONDS,

            "latency_headroom_seconds":
                LATENCY_HEADROOM_SECONDS,
        },

        "attempts":
            attempts,

        "terminal_observation_count":
            len(attempts),

        "complete_round_count":
            complete_round_count(
                attempts
            ),

        "planned_probe_count":
            9,

        "round_count":
            3,

        "balanced_probe_positions":
            True,

        "live_disposition":
            disposition,

        "qualified_disposition_observed":
            disposition == "QUALIFIED",

        "qualification_010_formally_closed":
            False,

        "qualification_010_qualified":
            False,

        "provider_qualification_established":
            False,

        "ontology_007r1_execution_authorized":
            False,

        "ontology_007r1_executed":
            False,

        "formal_closure_required":
            True,

        "live_run_executed":
            True,

        "retries":
            0,

        "replacement_probes_allowed":
            False,

        "pacing_seconds":
            PACING_SECONDS,

        "historical_qualification_observations_reused":
            False,

        "recovery_stability_observations_reused":
            False,

        "token_reservation_localization_observations_reused":
            False,

        "qualification_009_rerun":
            False,

        "recovery_stability_002_rerun":
            False,

        "localization_001_rerun":
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
        f"live disposition: {disposition}"
    )
    print(
        "Q010 formally closed: FALSE"
    )
    print(
        "provider qualification established: FALSE"
    )
    print(
        "Ontology 007R1 execution authorized: FALSE"
    )
    print(
        "rerun authorized: FALSE"
    )

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
        materialize()
        return 0

    if args.live:
        execute_live()
        return 0

    plan = preflight()

    print(
        "PASS frozen Provider Qualification 010 instrument"
    )
    print(
        f"probes: {plan['planned_probe_count']}"
    )
    print(
        f"rounds: {plan['round_count']}"
    )
    print(
        "balance: each probe each position exactly once"
    )
    print(
        "target: exact frozen Ontology 007R1"
    )
    print(
        "source probe projections: exact frozen Q009 by probe_id"
    )
    print(
        "headroom: 45 seconds"
    )
    print(
        "retries: ZERO"
    )
    print(
        "replacements: FORBIDDEN"
    )
    print(
        "Q009 rerun: FALSE"
    )
    print(
        "Q010 formally closed: FALSE"
    )
    print(
        "Ontology 007R1 authorization: FALSE"
    )
    print(
        "offline preflight only; "
        "no provider/model/network request made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
