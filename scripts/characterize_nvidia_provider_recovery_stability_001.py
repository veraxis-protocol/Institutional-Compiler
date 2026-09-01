#!/usr/bin/env python3
"""Frozen NVIDIA provider recovery-stability characterization.

Offline by default. No provider is constructed unless --live is supplied.

The exact provider-probe semantics are sourced from the hash-verified frozen
Provider Qualification 006 instrument.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Final

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

ROOT = Path(__file__).resolve().parents[1]

WORK_ORDER: Final[str] = (
    "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-001"
)

PREREG_COMMIT: Final[str] = (
    "41b06db74f609a8c229f23ee76a67de8715748f2"
)

SOURCE_INCIDENT_COMMIT: Final[str] = (
    "3eeb1b3b3948490dc79bb14a0226006984531b30"
)

BENCH = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-recovery-stability-001"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MANIFEST_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

INCIDENT_RESULT = (
    ROOT
    / "benchmarks/provider-incidents/"
      "nvidia-nim-path-001/EXECUTION-RESULT-v0.1.json"
)

INCIDENT_ADJ = (
    ROOT
    / "benchmarks/provider-incidents/"
      "nvidia-nim-path-001/POST-RUN-ADJUDICATION.md"
)

QUAL_SCRIPT = ROOT / "scripts/qualify_nvidia_provider_006.py"
ADAPTER = ROOT / "src/oic/nvidia_nim.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_recovery_stability_001.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-characterization-receipts/"
      "OIC-NVIDIA-PROVIDER-RECOVERY-STABILITY-001.json"
)

PLAN_SHA256: Final[str] = (
    "6a5f7ffa2fd075ae3f3a6dcd3e9ca729ee9424a0421af868920d2b5c21a2b65c"
)
PREREG_SHA256: Final[str] = (
    "a132330604497a47deae8e8a2f278706dd63ac2aadc4d6b7e6bd1467ad6c2fbc"
)
FREEZE_V1_SHA256: Final[str] = (
    "4bba81a05b87442b4db8d36ec1627e937a2c114f809170b89b1666c62c9ab109"
)

INCIDENT_RESULT_SHA256: Final[str] = (
    "17f872a3bb746bd3fa5a2a686a0c5428b80befe77547697d557e31442f99a100"
)
INCIDENT_ADJ_SHA256: Final[str] = (
    "cd889ad5083a8f6c5f63b8501a679aa5fd0a4bb92dcd2a05738a5e85c5aa4fb2"
)

QUAL_SCRIPT_SHA256: Final[str] = (
    "72eb72aeb95f9727a9380902400c7d8e6891fba9447c30694193dad31f467674"
)
PROBE_SPEC_SHA256: Final[str] = (
    "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
)
ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PLANNED_REQUESTS: Final[int] = 18
CYCLES: Final[int] = 6
OBSERVATIONS_PER_PROBE: Final[int] = 6
REQUEST_PACING_SECONDS: Final[float] = 4.0
CYCLE_PACING_SECONDS: Final[float] = 10.0

_QUAL_MODULE_NAME: Final[str] = (
    "_oic_recovery_stability_source_qualification_006"
)


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


def verify_source_hashes() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        INCIDENT_RESULT: INCIDENT_RESULT_SHA256,
        INCIDENT_ADJ: INCIDENT_ADJ_SHA256,
        QUAL_SCRIPT: QUAL_SCRIPT_SHA256,
        ADAPTER: ADAPTER_SHA256,
    }

    for path, digest in expected.items():
        actual = sha256(path)
        if actual != digest:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}"
            )


def load_qualification_006() -> ModuleType:
    verify_source_hashes()

    if _QUAL_MODULE_NAME in sys.modules:
        return sys.modules[_QUAL_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _QUAL_MODULE_NAME,
        QUAL_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "cannot load frozen Qualification 006 instrument"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[_QUAL_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != "OIC-NVIDIA-PROVIDER-QUALIFICATION-006":
        raise SystemExit(
            "FAIL Qualification 006 identity drift"
        )

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL frozen probe-spec binding drift"
        )

    if module.probe_spec_sha256() != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL frozen runtime probe semantics drift"
        )

    return module


def probe_map(module: ModuleType) -> dict[str, Any]:
    probes = {
        probe.probe_id: probe
        for probe in module.PROBES
    }

    expected = {
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    }

    if set(probes) != expected:
        raise SystemExit(
            "FAIL frozen probe population drift"
        )

    return probes


def request_projection(probe: Any) -> dict[str, Any]:
    return {
        "probe_id": probe.probe_id,
        "system_prompt": probe.system_prompt,
        "user_prompt": probe.user_prompt,
        "response_format": probe.response_format,
        "temperature": 0.0,
        "max_tokens": probe.max_tokens,
        "expected_mode": probe.expected_mode,
        "expected_value": probe.expected_value,
    }


def verify_plan() -> dict[str, Any]:
    verify_source_hashes()

    plan = json.loads(
        PLAN_PATH.read_text(encoding="utf-8")
    )

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Recovery Stability 001 identity drift"
        )

    if plan["starting_sha"] != SOURCE_INCIDENT_COMMIT:
        raise SystemExit(
            "FAIL source incident commit drift"
        )

    provider = plan["provider"]

    if provider != {
        "base_url": DEFAULT_NIM_BASE_URL,
        "latency_headroom_seconds": LATENCY_HEADROOM_SECONDS,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }:
        raise SystemExit(
            "FAIL provider envelope drift"
        )

    population = plan["population"]

    if population["population_id"] != (
        "PROVIDER_RECOVERY_STABILITY_001_ONLY"
    ):
        raise SystemExit(
            "FAIL analysis population drift"
        )

    if population["cycles"] != CYCLES:
        raise SystemExit(
            "FAIL cycle-count drift"
        )

    if population["planned_provider_requests"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL request-count drift"
        )

    if population["observations_per_probe"] != OBSERVATIONS_PER_PROBE:
        raise SystemExit(
            "FAIL observations-per-probe drift"
        )

    request_plan = population["request_plan"]

    if len(request_plan) != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL request population incomplete"
        )

    if [
        int(item["ordinal"])
        for item in request_plan
    ] != list(range(1, PLANNED_REQUESTS + 1)):
        raise SystemExit(
            "FAIL ordinal drift"
        )

    counts = Counter(
        item["probe_id"]
        for item in request_plan
    )

    if counts != Counter({
        "BASIC_TEXT": 6,
        "JSON_MODE": 6,
        "PRODUCTION_TOKEN_RESERVATION": 6,
    }):
        raise SystemExit(
            "FAIL probe-count balance drift"
        )

    position_counts = Counter(
        (
            item["probe_id"],
            int(item["cycle_position"]),
        )
        for item in request_plan
    )

    for probe_id in counts:
        for position in (1, 2, 3):
            if position_counts[(probe_id, position)] != 2:
                raise SystemExit(
                    "FAIL cycle-position balance drift"
                )

    transport = plan["transport"]

    if transport != {
        "all_planned_positions_are_terminal_observations": True,
        "pacing_seconds_between_cycles": CYCLE_PACING_SECONDS,
        "pacing_seconds_within_cycle": REQUEST_PACING_SECONDS,
        "replacement_requests_allowed": False,
        "retries": 0,
        "timeout_seconds": TIMEOUT_SECONDS,
    }:
        raise SystemExit(
            "FAIL frozen transport envelope drift"
        )

    historical = plan["historical_context"]

    if historical["historical_observations_reused"] is not False:
        raise SystemExit(
            "FAIL historical-output reuse detected"
        )

    if historical[
        "incident_001_target_observation_reused"
    ] is not False:
        raise SystemExit(
            "FAIL incident-output reuse detected"
        )

    if plan["semantic_hypothesis"] is not None:
        raise SystemExit(
            "FAIL semantic hypothesis introduced"
        )

    if plan["semantic_hypothesis_evaluated"] is not False:
        raise SystemExit(
            "FAIL semantic hypothesis state drift"
        )

    if plan["qualification_007_created"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 creation drift"
        )

    if plan["qualification_007_authorized"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 authorization drift"
        )

    if plan["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 authorization drift"
        )

    if plan["architecture_change_authorized"] is not False:
        raise SystemExit(
            "FAIL architecture authorization drift"
        )

    return plan


def build_materialization() -> dict[str, Any]:
    plan = verify_plan()
    module = load_qualification_006()
    probes = probe_map(module)

    requests: list[dict[str, Any]] = []

    for cell in plan["population"]["request_plan"]:
        probe = probes[cell["probe_id"]]
        projection = request_projection(probe)

        requests.append({
            "ordinal": int(cell["ordinal"]),
            "cycle": int(cell["cycle"]),
            "cycle_position": int(cell["cycle_position"]),
            "probe_id": cell["probe_id"],
            "request_projection":
                projection,
            "request_projection_sha256":
                canonical_sha256(projection),
        })

    return {
        "work_order":
            WORK_ORDER,

        "status":
            "MATERIALIZED_OFFLINE_NOT_EXECUTED",

        "population_id":
            "PROVIDER_RECOVERY_STABILITY_001_ONLY",

        "source_qualification_006_instrument_sha256":
            QUAL_SCRIPT_SHA256,

        "source_probe_spec_sha256":
            PROBE_SPEC_SHA256,

        "provider_adapter_sha256":
            ADAPTER_SHA256,

        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
            "latency_headroom_seconds":
                LATENCY_HEADROOM_SECONDS,
        },

        "request_count":
            len(requests),

        "cycles":
            CYCLES,

        "observations_per_probe":
            OBSERVATIONS_PER_PROBE,

        "retries":
            0,

        "replacement_requests_allowed":
            False,

        "historical_observations_reused":
            False,

        "incident_001_observation_reused":
            False,

        "provider_call_made":
            False,

        "model_call_made":
            False,

        "network_request_made":
            False,

        "live_run_executed":
            False,

        "requests":
            requests,
    }


def materialize() -> None:
    if MANIFEST_PATH.exists():
        raise SystemExit(
            f"STOP materialization already exists: {MANIFEST_PATH}"
        )

    manifest = build_materialization()

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"materialized {manifest['request_count']} "
        "exact provider observations"
    )
    print("provider/model/network calls: ZERO")


def verify_manifest(
    plan: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    expected = build_materialization()

    if manifest != expected:
        raise SystemExit(
            "FAIL request materialization drift"
        )

    if manifest["request_count"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL materialized request-count drift"
        )

    if manifest["retries"] != 0:
        raise SystemExit(
            "FAIL materialized retry drift"
        )

    if manifest[
        "replacement_requests_allowed"
    ] is not False:
        raise SystemExit(
            "FAIL replacement-request drift"
        )

    if manifest[
        "historical_observations_reused"
    ] is not False:
        raise SystemExit(
            "FAIL historical observation reuse"
        )

    if manifest[
        "incident_001_observation_reused"
    ] is not False:
        raise SystemExit(
            "FAIL incident observation reuse"
        )

    planned = plan["population"]["request_plan"]

    for source, frozen in zip(
        planned,
        manifest["requests"],
        strict=True,
    ):
        for key in (
            "ordinal",
            "cycle",
            "cycle_position",
            "probe_id",
        ):
            if frozen[key] != source[key]:
                raise SystemExit(
                    f"FAIL materialized plan mismatch: {key}"
                )


def classify(
    observations: list[dict[str, Any]],
) -> str:
    if len(observations) != PLANNED_REQUESTS:
        return "RECOVERY_PATH_UNSTABLE"

    if any(
        item.get("outcome") != "ACCEPTED"
        or item.get("marker_valid") is not True
        for item in observations
    ):
        return "RECOVERY_PATH_UNSTABLE"

    if any(
        float(item["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
        for item in observations
    ):
        return "RECOVERY_HEADROOM_UNSTABLE"

    return "BOUNDED_RECOVERY_STABILITY_OBSERVED"


def preflight() -> dict[str, Any]:
    plan = verify_plan()

    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "FAIL request materialization missing"
        )

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL static freeze v0.2 missing"
        )

    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    verify_manifest(
        plan,
        manifest,
    )

    freeze = json.loads(
        FREEZE_V2_PATH.read_text(
            encoding="utf-8"
        )
    )

    checks = {
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
            sha256(MANIFEST_PATH),
        "incident_execution_result_sha256":
            sha256(INCIDENT_RESULT),
        "incident_post_run_adjudication_sha256":
            sha256(INCIDENT_ADJ),
        "source_qualification_006_instrument_sha256":
            sha256(QUAL_SCRIPT),
        "provider_adapter_sha256":
            sha256(ADAPTER),
    }

    for key, expected in checks.items():
        if freeze.get(key) != expected:
            raise SystemExit(
                f"FAIL static-freeze digest mismatch: {key}"
            )

    if freeze["planned_provider_requests"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL frozen request count"
        )

    if freeze["cycles"] != CYCLES:
        raise SystemExit(
            "FAIL frozen cycle count"
        )

    if freeze["observations_per_probe"] != OBSERVATIONS_PER_PROBE:
        raise SystemExit(
            "FAIL frozen probe count"
        )

    if freeze["latency_headroom_seconds"] != LATENCY_HEADROOM_SECONDS:
        raise SystemExit(
            "FAIL frozen headroom"
        )

    if freeze["retries"] != 0:
        raise SystemExit(
            "FAIL frozen retries"
        )

    if freeze[
        "replacement_requests_allowed"
    ] is not False:
        raise SystemExit(
            "FAIL frozen replacement policy"
        )

    if freeze["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL live-run state drift"
        )

    if freeze["qualification_007_created"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 creation state drift"
        )

    if freeze["qualification_007_authorized"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 authorization drift"
        )

    if freeze["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 authorization drift"
        )

    return plan


def execute_live() -> tuple[
    list[dict[str, Any]],
    str,
]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP recovery receipt already exists: {RECEIPT_PATH}"
        )

    plan = preflight()

    module = load_qualification_006()
    probes = probe_map(module)

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    observations: list[dict[str, Any]] = []

    cells = plan["population"]["request_plan"]

    for index, cell in enumerate(cells):
        probe = probes[cell["probe_id"]]

        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        ordinal = int(cell["ordinal"])

        print(
            f"[{ordinal:02d}/{PLANNED_REQUESTS:02d}] "
            f"START cycle={cell['cycle']} "
            f"position={cell['cycle_position']} "
            f"probe={probe.probe_id}",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(
                request
            )

        except ModelProviderError as exc:
            elapsed = time.monotonic() - started

            observation = {
                "ordinal":
                    ordinal,
                "cycle":
                    int(cell["cycle"]),
                "cycle_position":
                    int(cell["cycle_position"]),
                "probe_id":
                    probe.probe_id,
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
            elapsed = time.monotonic() - started

            marker_valid = module.validate_marker(
                probe,
                response.content,
            )

            observation = {
                "ordinal":
                    ordinal,
                "cycle":
                    int(cell["cycle"]),
                "cycle_position":
                    int(cell["cycle_position"]),
                "probe_id":
                    probe.probe_id,
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
                        response.content.encode("utf-8")
                    ).hexdigest(),
            }

        observations.append(
            observation
        )

        print(
            f"[{ordinal:02d}/{PLANNED_REQUESTS:02d}] "
            f"DONE outcome={observation['outcome']} "
            f"seconds={observation['elapsed_seconds']}",
            flush=True,
        )

        if index < len(cells) - 1:
            current_cycle = int(cell["cycle"])
            next_cycle = int(cells[index + 1]["cycle"])

            delay = (
                REQUEST_PACING_SECONDS
                if next_cycle == current_cycle
                else CYCLE_PACING_SECONDS
            )

            time.sleep(delay)

    disposition = classify(
        observations
    )

    latencies = [
        float(item["elapsed_seconds"])
        for item in observations
    ]

    accepted_valid = sum(
        item["outcome"] == "ACCEPTED"
        and item["marker_valid"] is True
        for item in observations
    )

    failures = PLANNED_REQUESTS - accepted_valid

    violations = sum(
        float(item["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
        for item in observations
    )

    per_probe: dict[str, Any] = {}

    for probe_id in (
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ):
        rows = [
            item
            for item in observations
            if item["probe_id"] == probe_id
        ]

        values = [
            float(item["elapsed_seconds"])
            for item in rows
        ]

        per_probe[probe_id] = {
            "observation_count":
                len(rows),
            "accepted_marker_valid":
                sum(
                    item["outcome"] == "ACCEPTED"
                    and item["marker_valid"] is True
                    for item in rows
                ),
            "headroom_violation_count":
                sum(
                    float(item["elapsed_seconds"])
                    > LATENCY_HEADROOM_SECONDS
                    for item in rows
                ),
            "median_latency_seconds":
                round(statistics.median(values), 3),
            "max_latency_seconds":
                round(max(values), 3),
        }

    freeze = json.loads(
        FREEZE_V2_PATH.read_text(
            encoding="utf-8"
        )
    )

    receipt = {
        "work_order":
            WORK_ORDER,

        "live_run_executed":
            True,

        "analysis_population":
            "PROVIDER_RECOVERY_STABILITY_001_ONLY",

        "planned_provider_requests":
            PLANNED_REQUESTS,

        "terminal_observation_count":
            len(observations),

        "cycles":
            CYCLES,

        "observations_per_probe":
            OBSERVATIONS_PER_PROBE,

        "accepted_marker_valid_count":
            accepted_valid,

        "provider_or_response_failure_count":
            failures,

        "headroom_violation_count_gt_45_seconds":
            violations,

        "latency_headroom_seconds":
            LATENCY_HEADROOM_SECONDS,

        "overall_latency_median_seconds":
            round(statistics.median(latencies), 3),

        "overall_latency_max_seconds":
            round(max(latencies), 3),

        "per_probe":
            per_probe,

        "retries":
            0,

        "replacement_requests_allowed":
            False,

        "historical_observations_reused":
            False,

        "incident_001_observation_reused":
            False,

        "classification":
            disposition,

        "semantic_hypothesis_evaluated":
            False,

        "qualification_006_reclassified":
            False,

        "qualification_007_created":
            False,

        "qualification_007_authorized":
            False,

        "ontology_006_executed":
            False,

        "ontology_006_execution_authorized":
            False,

        "canonicalization_performed":
            False,

        "institutional_ir_constructed":
            False,

        "architecture_change_authorized":
            False,

        "rerun_authorized":
            False,

        "plan_sha256":
            sha256(PLAN_PATH),

        "preregistration_sha256":
            sha256(PREREG_PATH),

        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),

        "instrument_sha256":
            freeze["instrument_sha256"],

        "contract_test_sha256":
            freeze["contract_test_sha256"],

        "request_materialization_sha256":
            freeze["request_materialization_sha256"],

        "static_freeze_v0_2_sha256":
            sha256(FREEZE_V2_PATH),

        "observations":
            observations,
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
        f"classification: {disposition}",
        flush=True,
    )
    print(
        f"accepted/valid: {accepted_valid}/{PLANNED_REQUESTS}",
        flush=True,
    )
    print(
        f"headroom violations: {violations}",
        flush=True,
    )
    print(
        "Qualification 007 authorized: NO",
        flush=True,
    )
    print(
        "Ontology 006 authorized: NO",
        flush=True,
    )

    return observations, disposition


def main(
    argv: list[str] | None = None,
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
        "PASS frozen NVIDIA provider recovery stability 001 instrument"
    )
    print(
        f"fresh observations: "
        f"{plan['population']['planned_provider_requests']}"
    )
    print(
        f"cycles: {plan['population']['cycles']}"
    )
    print(
        "observations/probe: 6"
    )
    print(
        "latency headroom: 45 seconds"
    )
    print(
        "retries: ZERO"
    )
    print(
        "replacements: FORBIDDEN"
    )
    print(
        "offline preflight only; "
        "no provider/model/network call made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
