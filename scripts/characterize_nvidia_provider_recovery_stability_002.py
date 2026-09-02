#!/usr/bin/env python3
"""NVIDIA Provider Recovery Stability 002.

Fresh order-balanced short-window provider-path characterization following
the closed Q009 JSON_MODE timeout.

Offline is the default. No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import NvidiaNimConfig, NvidiaNimProvider

WORK_ORDER: Final[str] = (
    "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-002"
)

PREREG_COMMIT: Final[str] = (
    "609b58bf84eb092f800972adb88e6770a55d9a58"
)

BENCH = (
    ROOT
    / "benchmarks/provider-recovery-stability/nvidia-nim-002"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

Q009_DIR = ROOT / "benchmarks/provider-qualification/nvidia-nim-009"

Q009_RESULT = Q009_DIR / "EXECUTION-RESULT-v0.1.json"
Q009_ADJ = Q009_DIR / "POST-RUN-ADJUDICATION.md"
Q009_MANIFEST = Q009_DIR / "REQUEST-MATERIALIZATION-v0.1.json"
Q009_FREEZE = Q009_DIR / "PLAN-FREEZE-v0.2.json"
Q009_SCRIPT = ROOT / "scripts/qualify_nvidia_provider_009.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_recovery_stability_002.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-recovery-stability-receipts/"
      "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-002.json"
)

PLAN_SHA256: Final[str] = (
    "c12ab314bc31f2bd47187401d629d4926251989c6dc17ac3bf380c855b1dc55a"
)
PREREG_SHA256: Final[str] = (
    "832f1c0d13cb34bc56390feebdcf4306a881be13a2fe0ea9ebadd8b79ae399e1"
)
FREEZE_V1_SHA256: Final[str] = (
    "e98fa13e659354e5770c126b45366fad8460f1c6bd641641a5efa3bcf08c13b7"
)

Q009_RESULT_SHA256: Final[str] = (
    "aec9de532f179b0024eb4a0ea0574deb7a87bf82ea7a54dc45c5dc84b71f74c2"
)
Q009_ADJ_SHA256: Final[str] = (
    "4906070a3a826dbd56886bcea70ba3c62f9c6b8671d19ce56937a0bcb51c4587"
)
Q009_MANIFEST_SHA256: Final[str] = (
    "e725fbf588ff4f304ebb5f1fd48b5f6bad64e1bb54d06aa3e528396c9362a485"
)
Q009_FREEZE_SHA256: Final[str] = (
    "b96a76e0f5496c47fec20e32acb58cc888965556b83b68d16028cb58b8c84634"
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

PLANNED_CALLS: Final[int] = 18
PLANNED_ROUNDS: Final[int] = 6

_SOURCE_MODULE_NAME: Final[str] = "_recovery002_frozen_q009"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path}")

    return value


def verify_frozen_sources() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        Q009_RESULT: Q009_RESULT_SHA256,
        Q009_ADJ: Q009_ADJ_SHA256,
        Q009_MANIFEST: Q009_MANIFEST_SHA256,
        Q009_FREEZE: Q009_FREEZE_SHA256,
        Q009_SCRIPT: Q009_SCRIPT_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)

        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}: "
                f"{actual} != {expected_sha}"
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
        raise SystemExit("FAIL cannot load frozen Q009 instrument")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != "OIC-NVIDIA-PROVIDER-QUALIFICATION-009":
        raise SystemExit("FAIL Q009 source identity drift")

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit("FAIL frozen probe-spec drift")

    if module.TIMEOUT_SECONDS != TIMEOUT_SECONDS:
        raise SystemExit("FAIL timeout drift")

    if module.LATENCY_HEADROOM_SECONDS != LATENCY_HEADROOM_SECONDS:
        raise SystemExit("FAIL headroom drift")

    if module.PACING_SECONDS != PACING_SECONDS:
        raise SystemExit("FAIL pacing drift")

    return module


def prereg_context() -> dict[str, Any]:
    verify_frozen_sources()

    plan = load_json(PLAN_PATH)
    freeze = load_json(FREEZE_V1_PATH)
    q009 = load_json(Q009_RESULT)

    assert plan["work_order"] == WORK_ORDER
    assert plan["round_count"] == PLANNED_ROUNDS
    assert plan["planned_provider_calls"] == PLANNED_CALLS

    assert plan["transport"]["timeout_seconds"] == TIMEOUT_SECONDS
    assert plan["transport"]["latency_headroom_seconds"] == (
        LATENCY_HEADROOM_SECONDS
    )
    assert plan["transport"]["pacing_seconds"] == PACING_SECONDS
    assert plan["transport"]["retries"] == 0
    assert plan["transport"]["replacement_observations_allowed"] is False

    assert plan["q009_rerun"] is False
    assert plan["q009_observations_reused_as_new_observations"] is False
    assert plan["q010_created"] is False
    assert plan["ontology_007_execution_authorized"] is False
    assert plan["ontology_007_executed"] is False

    assert freeze["work_order"] == WORK_ORDER
    assert freeze["round_count"] == 6
    assert freeze["planned_provider_calls"] == 18
    assert freeze["retries"] == 0
    assert freeze["q010_created"] is False
    assert freeze["live_run_executed"] is False

    assert q009["status"] == "CLOSED_EXECUTED_NOT_QUALIFIED"
    assert q009["failed_probe"] == "JSON_MODE"
    assert q009["failure_class"] == "PROVIDER_TIMEOUT"
    assert q009["rerun_authorized"] is False
    assert q009["ontology_007_execution_authorized"] is False

    q009_source = source_q009()
    q009_source.verify_plan()

    return plan


def probes_by_id() -> dict[str, Any]:
    q009 = source_q009()

    values = {
        probe.probe_id: probe
        for probe in q009.probes()
    }

    if set(values) != {
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    }:
        raise SystemExit("FAIL frozen Q009 probe set drift")

    return values


def source_manifest_by_probe() -> dict[str, dict[str, Any]]:
    manifest = load_json(Q009_MANIFEST)

    rows = {
        row["probe_id"]: row
        for row in manifest["requests"]
    }

    if set(rows) != {
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    }:
        raise SystemExit("FAIL Q009 materialized probe population drift")

    return rows


def materialization_document() -> dict[str, Any]:
    plan = prereg_context()
    q009 = source_q009()
    probes = probes_by_id()
    source_rows = source_manifest_by_probe()

    rows: list[dict[str, Any]] = []

    for item in plan["execution_plan"]:
        probe = probes[item["probe_id"]]
        projection = q009.request_projection(probe)
        source_row = source_rows[item["probe_id"]]

        if projection != source_row["request_projection"]:
            raise SystemExit(
                f"FAIL source request projection drift: {item['probe_id']}"
            )

        projection_sha = q009.canonical_sha256(projection)

        if projection_sha != source_row["request_projection_sha256"]:
            raise SystemExit(
                f"FAIL source request projection SHA drift: "
                f"{item['probe_id']}"
            )

        rows.append({
            "execution_ordinal": int(item["ordinal"]),
            "round_index": int(item["round_index"]),
            "position_in_round": int(item["position_in_round"]),
            "probe_id": item["probe_id"],
            "source_probe_ordinal": int(probe.ordinal),
            "request_projection": projection,
            "request_projection_sha256": projection_sha,
            "fresh_observation": True,
            "q009_live_observation_reused": False,
            "provider_constructed": False,
            "network_request_made": False,
        })

    if len(rows) != 18:
        raise SystemExit("FAIL Recovery Stability 002 materialization count")

    return {
        "work_order": WORK_ORDER,
        "status": "MATERIALIZED_OFFLINE_NOT_EXECUTED",
        "source_work_order": "OIC-NVIDIA-PROVIDER-QUALIFICATION-009",
        "source_q009_request_materialization_sha256":
            Q009_MANIFEST_SHA256,
        "source_probe_spec_sha256": PROBE_SPEC_SHA256,
        "round_count": 6,
        "request_count": 18,
        "retries": 0,
        "replacement_observations_allowed": False,
        "pacing_seconds": 4.0,
        "q009_observations_reused_as_new_observations": False,
        "q009_rerun": False,
        "q010_created": False,
        "ontology_007_execution_authorized": False,
        "ontology_007_executed": False,
        "provider_constructed": False,
        "network_request_made": False,
        "live_run_executed": False,
        "requests": rows,
    }


def materialize() -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP materialization already exists: {MATERIALIZATION_PATH}"
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

    print("materialized 18 fresh order-balanced observations")
    print("all source request projections: exact frozen Q009")
    print("provider/model/network calls: ZERO")


def verify_materialization() -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL Recovery Stability 002 materialization absent")

    actual = load_json(MATERIALIZATION_PATH)
    expected = materialization_document()

    if actual != expected:
        raise SystemExit("FAIL Recovery Stability 002 materialization drift")

    return actual


def classify(
    attempts: Sequence[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    complete_rounds = 0

    for round_index in range(1, 7):
        rows = [
            x for x in attempts
            if int(x["round_index"]) == round_index
        ]

        if len(rows) == 3:
            complete_rounds += 1

    terminal_count = len(attempts)

    gate = {
        "terminal_observations": terminal_count,
        "terminal_observations_required": 18,
        "complete_rounds": complete_rounds,
        "complete_rounds_required": 6,
        "adjudicable": (
            terminal_count == 18
            and complete_rounds == 6
        ),
    }

    if not gate["adjudicable"]:
        return "INCOMPLETE_CHARACTERIZATION", gate

    if any(
        x["outcome"] != "ACCEPTED"
        or x.get("marker_valid") is not True
        for x in attempts
    ):
        return (
            "RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE",
            gate,
        )

    if any(
        float(x["elapsed_seconds"]) > LATENCY_HEADROOM_SECONDS
        for x in attempts
    ):
        return (
            "RECOVERY_OBSERVED_WITH_LATENCY_DEGRADATION",
            gate,
        )

    return "BOUNDED_RECOVERY_STABILITY_OBSERVED", gate


def verify_freeze_v2() -> dict[str, Any]:
    freeze = load_json(FREEZE_V2_PATH)

    expected = {
        "plan_sha256": sha256(PLAN_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "preregistration_freeze_v0_1_sha256": sha256(FREEZE_V1_PATH),
        "instrument_sha256": sha256(Path(__file__)),
        "contract_test_sha256": sha256(CONTRACT_TEST),
        "request_materialization_sha256": sha256(MATERIALIZATION_PATH),
        "q009_execution_result_sha256": sha256(Q009_RESULT),
        "q009_post_run_adjudication_sha256": sha256(Q009_ADJ),
        "q009_request_materialization_sha256": sha256(Q009_MANIFEST),
        "q009_static_freeze_sha256": sha256(Q009_FREEZE),
        "q009_instrument_sha256": sha256(Q009_SCRIPT),
    }

    for key, value in expected.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL Recovery Stability 002 freeze digest mismatch: {key}"
            )

    assert freeze["round_count"] == 6
    assert freeze["planned_provider_calls"] == 18
    assert freeze["retries"] == 0
    assert freeze["replacement_observations_allowed"] is False
    assert freeze["q009_rerun"] is False
    assert freeze["q009_observations_reused_as_new_observations"] is False
    assert freeze["q010_created"] is False
    assert freeze["ontology_007_execution_authorized"] is False
    assert freeze["ontology_007_executed"] is False
    assert freeze["live_run_executed"] is False

    return freeze


def static_preflight() -> dict[str, Any]:
    plan = prereg_context()
    verify_materialization()
    verify_freeze_v2()
    return plan


def execute_live() -> tuple[list[dict[str, Any]], str]:
    static_preflight()

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Recovery Stability 002 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    q009 = source_q009()
    source_q006 = q009.source_q006()
    probes = probes_by_id()
    plan = load_json(PLAN_PATH)

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=q009.DEFAULT_NIM_MODEL,
            base_url=q009.DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []

    for index, item in enumerate(plan["execution_plan"]):
        probe = probes[item["probe_id"]]

        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        print(
            f"[{item['ordinal']:02d}/18] "
            f"round={item['round_index']} "
            f"position={item['position_in_round']} "
            f"START {item['probe_id']}",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(request)

        except ModelProviderError as exc:
            elapsed = time.monotonic() - started

            attempt = {
                "execution_ordinal": int(item["ordinal"]),
                "round_index": int(item["round_index"]),
                "position_in_round": int(item["position_in_round"]),
                "probe_id": item["probe_id"],
                "outcome": "PROVIDER_ERROR",
                "elapsed_seconds": round(elapsed, 3),
                "marker_valid": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

        else:
            elapsed = time.monotonic() - started

            marker_valid = source_q006.validate_marker(
                probe,
                response.content,
            )

            attempt = {
                "execution_ordinal": int(item["ordinal"]),
                "round_index": int(item["round_index"]),
                "position_in_round": int(item["position_in_round"]),
                "probe_id": item["probe_id"],
                "outcome": (
                    "ACCEPTED"
                    if marker_valid
                    else "RESPONSE_MISMATCH"
                ),
                "elapsed_seconds": round(elapsed, 3),
                "marker_valid": marker_valid,
                "provider": response.provider,
                "model": response.model,
                "request_id": response.request_id,
                "content_sha256": hashlib.sha256(
                    response.content.encode("utf-8")
                ).hexdigest(),
            }

        attempts.append(attempt)

        print(
            f"[{item['ordinal']:02d}/18] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={attempt['elapsed_seconds']}",
            flush=True,
        )

        if index < 17:
            time.sleep(PACING_SECONDS)

    disposition, gate = classify(attempts)

    probe_counts = Counter(
        x["probe_id"]
        for x in attempts
    )

    position_counts = {
        probe_id: Counter(
            int(x["position_in_round"])
            for x in attempts
            if x["probe_id"] == probe_id
        )
        for probe_id in probe_counts
    }

    receipt = {
        "work_order": WORK_ORDER,
        "preregistration_commit": PREREG_COMMIT,
        "instrument_freeze_sha256": sha256(FREEZE_V2_PATH),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "q009_execution_result_sha256": sha256(Q009_RESULT),
        "live_run_executed": True,
        "fresh_observation_count": len(attempts),
        "round_count": 6,
        "attempts": attempts,
        "adjudicability": gate,
        "probe_observation_counts": dict(probe_counts),
        "probe_position_counts": {
            key: {
                str(position): count
                for position, count in sorted(counter.items())
            }
            for key, counter in position_counts.items()
        },
        "scientific_disposition": disposition,
        "recovery_stability_002_formally_closed": False,
        "retries": 0,
        "replacement_observations_allowed": False,
        "pacing_seconds": 4.0,
        "latency_headroom_seconds": 45.0,
        "q009_rerun": False,
        "q009_observations_reused_as_new_observations": False,
        "q010_created": False,
        "q010_authorized": False,
        "ontology_007_execution_authorized": False,
        "ontology_007_executed": False,
        "semantic_hypothesis": None,
        "semantic_hypothesis_evaluated": False,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "architecture_change_authorized": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
        "rerun_authorized": False,
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

    print(f"receipt written: {RECEIPT_PATH}")
    print(f"scientific disposition: {disposition}")
    print("formal closure: FALSE")
    print("Q010 created: FALSE")
    print("Ontology 007 authorization: FALSE")

    return attempts, disposition


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--materialize",
        action="store_true",
    )

    modes.add_argument(
        "--live",
        action="store_true",
    )

    args = parser.parse_args(argv)

    if args.materialize:
        prereg_context()
        materialize()
        return 0

    if args.live:
        execute_live()
        return 0

    plan = static_preflight()

    print("PASS frozen Recovery Stability 002 instrument")
    print(f"observations: {plan['planned_provider_calls']}")
    print(f"rounds: {plan['round_count']}")
    print("order: all six probe permutations once")
    print("each probe / each position: twice")
    print("source probes: exact frozen Q009")
    print("headroom: 45 seconds")
    print("retries: ZERO")
    print("replacements: FORBIDDEN")
    print("Q009 observation reuse: FALSE")
    print("Q010 created: FALSE")
    print("Ontology 007 authorization: FALSE")
    print(
        "offline preflight only; "
        "no provider/model/network request made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
