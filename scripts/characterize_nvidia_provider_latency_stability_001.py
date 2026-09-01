#!/usr/bin/env python3
"""Frozen NVIDIA provider latency-stability characterization.

Offline by default. No provider is constructed unless --live is explicitly
supplied.

Probe request semantics are sourced from the frozen Provider Qualification 006
instrument after its SHA-256 is verified.
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
    "OIC-NVIDIA-PROVIDER-LATENCY-STABILITY-001"
)

PREREG_COMMIT: Final[str] = (
    "041f41de29c20a87a790bda5207b8d1a64f15116"
)

BENCH = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-latency-stability-001"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MANIFEST_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

QUAL_DIR = (
    ROOT
    / "benchmarks/provider-qualification/nvidia-nim-006"
)

QUAL_PLAN = QUAL_DIR / "PLAN-v0.1.json"
QUAL_PREREG = QUAL_DIR / "PREREGISTRATION.md"
QUAL_FREEZE = QUAL_DIR / "PLAN-FREEZE-v0.1.json"
QUAL_RESULT = QUAL_DIR / "EXECUTION-RESULT-v0.1.json"
QUAL_ADJ = QUAL_DIR / "POST-RUN-ADJUDICATION.md"

QUAL_SCRIPT = ROOT / "scripts/qualify_nvidia_provider_006.py"
QUAL_TEST = (
    ROOT
    / "tests/contract/test_nvidia_provider_qualification_006.py"
)

CONTRACT_TEST = (
    ROOT
    / "tests/contract/test_nvidia_provider_latency_stability_001.py"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"

RECEIPT_PATH = (
    ROOT
    / ".local/provider-characterization-receipts/"
      "OIC-NVIDIA-PROVIDER-LATENCY-STABILITY-001.json"
)

PLAN_SHA256: Final[str] = (
    "e5e86f8c7da381a9e77d8b6149d271fc7d421b4bc79bfe7cc1a36ff68f5943de"
)
PREREG_SHA256: Final[str] = (
    "33a6e567d9b17d128123e6a77e171cd35368792ba0bf390e437739b93e783a13"
)
FREEZE_V1_SHA256: Final[str] = (
    "e470ed16740aa9eaf860da7b72113caa71885eaecf423c525c8750ef41b5edf0"
)

QUAL_PLAN_SHA256: Final[str] = (
    "94016c49fcd848bf32814ab511399c04c8bb12032b955c56387980d57d035c5a"
)
QUAL_PREREG_SHA256: Final[str] = (
    "3dfd1d0314724711427d1861a0f28ad3deb512fedcc4835a05dbe559853baeb6"
)
QUAL_FREEZE_SHA256: Final[str] = (
    "fe81cffb5d0ae1d4d53ed6f30e3fbff8994c4f312921153b9106983fa2f2ea85"
)
QUAL_RESULT_SHA256: Final[str] = (
    "2a1707c16412cf5adf967f644363ad946b893338482a54daa001c36d3f7d2c6d"
)
QUAL_ADJ_SHA256: Final[str] = (
    "7492c77aacea982c7c7c7b206c480a8ebc2c52a347d74f0a5a8e0c0e8c206320"
)
QUAL_SCRIPT_SHA256: Final[str] = (
    "72eb72aeb95f9727a9380902400c7d8e6891fba9447c30694193dad31f467674"
)
QUAL_TEST_SHA256: Final[str] = (
    "3a028cb60212adde7d6408ed928eaf2145f388c9e1bfa5ec7a68c16d61dd0384"
)
ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)
PROBE_SPEC_SHA256: Final[str] = (
    "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0

PLANNED_REQUESTS: Final[int] = 36
CYCLES: Final[int] = 12

REQUEST_PACING_SECONDS: Final[float] = 4.0
CYCLE_PACING_SECONDS: Final[float] = 10.0

_QUAL_MODULE_NAME: Final[str] = (
    "_oic_frozen_provider_qualification_006"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_source_hashes() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        QUAL_PLAN: QUAL_PLAN_SHA256,
        QUAL_PREREG: QUAL_PREREG_SHA256,
        QUAL_FREEZE: QUAL_FREEZE_SHA256,
        QUAL_RESULT: QUAL_RESULT_SHA256,
        QUAL_ADJ: QUAL_ADJ_SHA256,
        QUAL_SCRIPT: QUAL_SCRIPT_SHA256,
        QUAL_TEST: QUAL_TEST_SHA256,
        ADAPTER: ADAPTER_SHA256,
    }

    for path, digest in expected.items():
        if sha256(path) != digest:
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
            "FAIL Qualification 006 probe-spec binding drift"
        )

    if module.probe_spec_sha256() != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL Qualification 006 runtime probe semantics drift"
        )

    return module


def probe_map(module: ModuleType) -> dict[str, Any]:
    return {
        probe.probe_id: probe
        for probe in module.PROBES
    }


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

    plan: dict[str, Any] = json.loads(
        PLAN_PATH.read_text(encoding="utf-8")
    )

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Latency Stability 001 identity drift"
        )

    if plan["starting_sha"] != (
        "752d87e034fc6f614454086fc55571712da1a453"
    ):
        raise SystemExit(
            "FAIL source closure commit drift"
        )

    if plan["planned_provider_requests"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL planned request-count drift"
        )

    if plan["cycles"] != CYCLES:
        raise SystemExit(
            "FAIL cycle-count drift"
        )

    if plan["observations_per_probe"] != 12:
        raise SystemExit(
            "FAIL observations-per-probe drift"
        )

    if plan["latency_headroom_seconds"] != LATENCY_HEADROOM_SECONDS:
        raise SystemExit(
            "FAIL latency-headroom drift"
        )

    if plan["provider"] != {
        "base_url": DEFAULT_NIM_BASE_URL,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }:
        raise SystemExit(
            "FAIL provider envelope drift"
        )

    if plan["retries"] != 0:
        raise SystemExit(
            "FAIL retries must remain zero"
        )

    if plan["replacement_requests_allowed"] is not False:
        raise SystemExit(
            "FAIL replacement requests must remain forbidden"
        )

    if plan["analysis_population"] != "LATENCY_STABILITY_001_ONLY":
        raise SystemExit(
            "FAIL analysis-population drift"
        )

    if plan["qualification_006_observations_reused"] is not False:
        raise SystemExit(
            "FAIL Qualification 006 outputs may not be reused"
        )

    if plan["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 must remain unauthorized"
        )

    if plan["semantic_successor_authorized"] is not False:
        raise SystemExit(
            "FAIL no semantic successor may be authorized"
        )

    request_plan = plan["request_plan"]

    if len(request_plan) != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL request-plan population drift"
        )

    if [
        int(item["ordinal"])
        for item in request_plan
    ] != list(range(1, PLANNED_REQUESTS + 1)):
        raise SystemExit(
            "FAIL request-plan ordinal drift"
        )

    return plan


def build_materialization() -> dict[str, Any]:
    plan = verify_plan()
    q = load_qualification_006()
    probes = probe_map(q)

    requests: list[dict[str, Any]] = []

    for cell in plan["request_plan"]:
        probe = probes[cell["probe_id"]]
        projection = request_projection(probe)

        requests.append({
            "ordinal": cell["ordinal"],
            "cycle_index": cell["cycle_index"],
            "cycle_position": cell["cycle_position"],
            "probe_id": cell["probe_id"],
            "request_projection_sha256":
                canonical_sha256(projection),
            "request_projection":
                projection,
        })

    return {
        "work_order": WORK_ORDER,
        "status": "MATERIALIZED_OFFLINE_NOT_EXECUTED",
        "analysis_population": "LATENCY_STABILITY_001_ONLY",
        "source_qualification_006_instrument_sha256":
            QUAL_SCRIPT_SHA256,
        "source_probe_spec_sha256":
            PROBE_SPEC_SHA256,
        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "request_count": len(requests),
        "cycles": CYCLES,
        "observations_per_probe": 12,
        "retries": 0,
        "replacement_requests_allowed": False,
        "qualification_006_live_outputs_reused": False,
        "provider_call_made": False,
        "model_call_made": False,
        "network_request_made": False,
        "live_run_executed": False,
        "requests": requests,
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
        f"materialized {manifest['request_count']} exact "
        "provider observations"
    )
    print("provider/model/network calls: ZERO")


def verify_manifest(
    plan: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    q = load_qualification_006()
    probes = probe_map(q)

    if manifest["request_count"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL materialized request-count drift"
        )

    if len(manifest["requests"]) != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL materialized population incomplete"
        )

    if manifest["analysis_population"] != "LATENCY_STABILITY_001_ONLY":
        raise SystemExit(
            "FAIL materialized analysis-population drift"
        )

    if manifest["retries"] != 0:
        raise SystemExit(
            "FAIL materialized retries drift"
        )

    if manifest["replacement_requests_allowed"] is not False:
        raise SystemExit(
            "FAIL materialized replacement policy drift"
        )

    if manifest["qualification_006_live_outputs_reused"] is not False:
        raise SystemExit(
            "FAIL Qualification 006 output reuse detected"
        )

    for planned, materialized in zip(
        plan["request_plan"],
        manifest["requests"],
        strict=True,
    ):
        for key in (
            "ordinal",
            "cycle_index",
            "cycle_position",
            "probe_id",
        ):
            if materialized[key] != planned[key]:
                raise SystemExit(
                    f"FAIL materialized plan mismatch: {key}"
                )

        probe = probes[planned["probe_id"]]
        projection = request_projection(probe)

        if materialized["request_projection"] != projection:
            raise SystemExit(
                "FAIL frozen Qualification 006 request semantics drift"
            )

        if (
            materialized["request_projection_sha256"]
            != canonical_sha256(projection)
        ):
            raise SystemExit(
                "FAIL request-projection digest drift"
            )


def preflight() -> dict[str, Any]:
    plan = verify_plan()

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL static freeze v0.2 missing"
        )

    freeze: dict[str, Any] = json.loads(
        FREEZE_V2_PATH.read_text(encoding="utf-8")
    )

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL static-freeze identity drift"
        )

    if freeze["plan_sha256"] != sha256(PLAN_PATH):
        raise SystemExit(
            "FAIL plan digest mismatch"
        )

    if freeze["preregistration_sha256"] != sha256(PREREG_PATH):
        raise SystemExit(
            "FAIL preregistration digest mismatch"
        )

    if freeze["preregistration_freeze_v0_1_sha256"] != sha256(
        FREEZE_V1_PATH
    ):
        raise SystemExit(
            "FAIL preregistration-freeze digest mismatch"
        )

    if freeze["instrument_sha256"] != sha256(Path(__file__)):
        raise SystemExit(
            "FAIL characterization instrument digest mismatch"
        )

    if freeze["contract_test_sha256"] != sha256(CONTRACT_TEST):
        raise SystemExit(
            "FAIL characterization contract-test digest mismatch"
        )

    if freeze["request_materialization_sha256"] != sha256(
        MANIFEST_PATH
    ):
        raise SystemExit(
            "FAIL request-materialization digest mismatch"
        )

    manifest: dict[str, Any] = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    verify_manifest(plan, manifest)

    if freeze["planned_provider_requests"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL static request-count drift"
        )

    if freeze["retries"] != 0:
        raise SystemExit(
            "FAIL static retries drift"
        )

    if freeze["replacement_requests_allowed"] is not False:
        raise SystemExit(
            "FAIL static replacement policy drift"
        )

    if freeze["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL characterization already marked live"
        )

    if freeze["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 authorization drift"
        )

    return plan


def classify(
    observations: list[dict[str, Any]],
) -> str:
    if len(observations) != PLANNED_REQUESTS:
        raise ValueError(
            "classification requires all 36 terminal observations"
        )

    if any(
        item["outcome"] != "ACCEPTED"
        or item.get("marker_valid") is not True
        for item in observations
    ):
        return "PROVIDER_PATH_UNSTABLE"

    violations = sum(
        float(item["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
        for item in observations
    )

    if violations >= 4:
        return "FREQUENT_HEADROOM_VIOLATION"

    if violations >= 1:
        return "INTERMITTENT_HEADROOM_VIOLATION"

    return "STABLE_WITHIN_FROZEN_HEADROOM"


def pacing_after(
    current: dict[str, Any],
    following: dict[str, Any] | None,
) -> float:
    if following is None:
        return 0.0

    if current["cycle_index"] != following["cycle_index"]:
        return CYCLE_PACING_SECONDS

    return REQUEST_PACING_SECONDS


def metrics(
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    by_probe: dict[str, list[float]] = {}

    for item in observations:
        by_probe.setdefault(
            item["probe_id"],
            [],
        ).append(
            float(item["elapsed_seconds"])
        )

    latencies = [
        float(item["elapsed_seconds"])
        for item in observations
    ]

    violations = [
        item
        for item in observations
        if float(item["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
    ]

    per_probe: dict[str, Any] = {}

    for probe_id, values in sorted(by_probe.items()):
        per_probe[probe_id] = {
            "observation_count": len(values),
            "median_latency_seconds":
                round(statistics.median(values), 3),
            "max_latency_seconds":
                round(max(values), 3),
            "headroom_violation_count":
                sum(value > LATENCY_HEADROOM_SECONDS for value in values),
        }

    return {
        "terminal_observation_count":
            len(observations),
        "accepted_marker_valid_count":
            sum(
                item["outcome"] == "ACCEPTED"
                and item.get("marker_valid") is True
                for item in observations
            ),
        "provider_or_response_failure_count":
            sum(
                item["outcome"] != "ACCEPTED"
                or item.get("marker_valid") is not True
                for item in observations
            ),
        "headroom_violation_count":
            len(violations),
        "headroom_violation_rate":
            round(
                len(violations) / PLANNED_REQUESTS,
                6,
            ),
        "overall_median_latency_seconds":
            round(statistics.median(latencies), 3),
        "overall_max_latency_seconds":
            round(max(latencies), 3),
        "per_probe":
            per_probe,
    }


def execute_live() -> tuple[
    list[dict[str, Any]],
    str,
]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP characterization receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    plan = preflight()
    q = load_qualification_006()
    probes = probe_map(q)

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    observations: list[dict[str, Any]] = []
    cells = plan["request_plan"]

    for index, cell in enumerate(cells):
        probe = probes[cell["probe_id"]]

        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        print(
            f"[{cell['ordinal']:02d}/{PLANNED_REQUESTS:02d}] "
            f"cycle={cell['cycle_index']:02d} "
            f"position={cell['cycle_position']} "
            f"START {probe.probe_id}",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(request)
        except ModelProviderError as exc:
            elapsed = time.monotonic() - started

            observation: dict[str, Any] = {
                "ordinal":
                    cell["ordinal"],
                "cycle_index":
                    cell["cycle_index"],
                "cycle_position":
                    cell["cycle_position"],
                "probe_id":
                    probe.probe_id,
                "outcome":
                    "PROVIDER_ERROR",
                "marker_valid":
                    False,
                "elapsed_seconds":
                    round(elapsed, 3),
                "error_type":
                    type(exc).__name__,
                "error_message":
                    str(exc),
            }

        else:
            elapsed = time.monotonic() - started
            marker_valid = q.validate_marker(
                probe,
                response.content,
            )

            observation = {
                "ordinal":
                    cell["ordinal"],
                "cycle_index":
                    cell["cycle_index"],
                "cycle_position":
                    cell["cycle_position"],
                "probe_id":
                    probe.probe_id,
                "outcome":
                    (
                        "ACCEPTED"
                        if marker_valid
                        else "RESPONSE_MISMATCH"
                    ),
                "marker_valid":
                    marker_valid,
                "elapsed_seconds":
                    round(elapsed, 3),
                "response_content":
                    response.content,
                "response_content_sha256":
                    hashlib.sha256(
                        response.content.encode("utf-8")
                    ).hexdigest(),
            }

        observations.append(observation)

        print(
            f"[{cell['ordinal']:02d}/{PLANNED_REQUESTS:02d}] "
            f"DONE outcome={observation['outcome']} "
            f"seconds={observation['elapsed_seconds']}",
            flush=True,
        )

        following = (
            cells[index + 1]
            if index + 1 < len(cells)
            else None
        )

        delay = pacing_after(
            cell,
            following,
        )

        if delay:
            time.sleep(delay)

    disposition = classify(observations)
    computed_metrics = metrics(observations)

    freeze = json.loads(
        FREEZE_V2_PATH.read_text(encoding="utf-8")
    )

    receipt = {
        "work_order":
            WORK_ORDER,
        "live_run_executed":
            True,
        "analysis_population":
            "LATENCY_STABILITY_001_ONLY",
        "provider": {
            "base_url":
                DEFAULT_NIM_BASE_URL,
            "model":
                DEFAULT_NIM_MODEL,
            "timeout_seconds":
                TIMEOUT_SECONDS,
        },
        "planned_provider_requests":
            PLANNED_REQUESTS,
        "terminal_observation_count":
            len(observations),
        "retries":
            0,
        "replacement_requests_allowed":
            False,
        "latency_headroom_seconds":
            LATENCY_HEADROOM_SECONDS,
        "source_qualification_006_instrument_sha256":
            QUAL_SCRIPT_SHA256,
        "probe_spec_sha256":
            PROBE_SPEC_SHA256,
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
        "metrics":
            computed_metrics,
        "classification":
            disposition,
        "qualification_006_reclassified":
            False,
        "qualification_006_observations_reused":
            False,
        "semantic_hypothesis_evaluated":
            False,
        "semantic_successor_authorized":
            False,
        "ontology_006_execution_authorized":
            False,
        "architecture_change_authorized":
            False,
        "independent_validation_claim":
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
        f"receipt written: {RECEIPT_PATH}",
        flush=True,
    )
    print(
        f"classification: {disposition}",
        flush=True,
    )
    print(
        "Ontology 006 authorized: NO",
        flush=True,
    )

    return observations, disposition


def main() -> int:
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--materialize",
        action="store_true",
    )

    mode.add_argument(
        "--live",
        action="store_true",
    )

    args = parser.parse_args()

    if args.materialize:
        materialize()
        return 0

    if args.live:
        execute_live()
        return 0

    plan = preflight()

    print(
        "PASS frozen provider latency-stability 001 instrument verified"
    )
    print(
        f"planned observations: {plan['planned_provider_requests']}"
    )
    print(
        f"cycles: {plan['cycles']}"
    )
    print(
        "source probe semantics: frozen Qualification 006"
    )
    print(
        "retries: ZERO"
    )
    print(
        "replacement requests: FORBIDDEN"
    )
    print(
        "offline preflight only; no provider was constructed "
        "and no request was made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
