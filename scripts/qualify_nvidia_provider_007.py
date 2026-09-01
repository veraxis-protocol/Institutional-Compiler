#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 007.

Fresh immediate provider-path qualification gate for the exact frozen
Ontology 006 predicate-frame discrimination experiment.

Offline is the default. No provider is constructed without --live.

A live QUALIFIED disposition does not itself authorize Ontology 006.
Formal post-run closure is required before qualification or successor
authorization can become true.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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
    "OIC-NVIDIA-PROVIDER-QUALIFICATION-007"
)

BASE_SHA: Final[str] = (
    "36aa000f583359e7d5df30d4e453d06f90d9730f"
)

ONTOLOGY_006_COMMIT: Final[str] = (
    "34abc1bc44bd89d1b29c0d005a23eabfb78ca196"
)

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-007"

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MANIFEST_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

RECOVERY_RESULT = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-recovery-stability-001/"
      "EXECUTION-RESULT-v0.1.json"
)

RECOVERY_ADJ = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-recovery-stability-001/"
      "POST-RUN-ADJUDICATION.md"
)

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006"
)

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_BINDING = TARGET_DIR / "TREATMENT-BINDING-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"

TARGET_INSTRUMENT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006.py"
)

TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_predicate_frame_discrimination_006.py"
)

TARGET_ADAPTER = ROOT / "src/oic/nvidia_nim.py"
SOURCE_Q006 = ROOT / "scripts/qualify_nvidia_provider_006.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_qualification_007.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-007.json"
)

PLAN_SHA256: Final[str] = (
    "21d75be39a2fc9a3b456bce0abcbb13a013d14fed0adfc9fed4b27842fad57b0"
)
PREREG_SHA256: Final[str] = (
    "661dc83506c688503a5763d8f77cf3c96996aa96aea7ab65a638b178c2efbdf1"
)
FREEZE_V1_SHA256: Final[str] = (
    "88ad9ecd0816b2bf72e51617140d661ef52c79793490ea7668e8d8eedd265bcf"
)

RECOVERY_RESULT_SHA256: Final[str] = (
    "c9c5c1da5b26c439407147e989350bbe869934bb55cbd59494d426d666880178"
)
RECOVERY_ADJ_SHA256: Final[str] = (
    "1a5581285dfff0380ca7b5e02db79246cbe61b69780ecb42a9f2ab9e2ead7311"
)

TARGET_PLAN_SHA256: Final[str] = (
    "4ef705e97e74e4623251975fb0e71d9cd59e5eb380ab6b63ebb1d07571992816"
)
TARGET_PREREG_SHA256: Final[str] = (
    "5da9fd19c17fe24f9560438d047e2f7f201e07580f1990fba171d460176c1825"
)
TARGET_FREEZE_V1_SHA256: Final[str] = (
    "1dba54e248f7761e5c153b18a37d86ded55bba9a92e95bd3c9db52fa3826df27"
)
TARGET_BINDING_SHA256: Final[str] = (
    "f95efb0189adc9368499684e6d3262651751c39fe8a5e422da94f8ef0111920a"
)
TARGET_FREEZE_V2_SHA256: Final[str] = (
    "2acd8e2ebe0a6913721240008f06c28108ea01c85c4484958c1b849ef95b5719"
)
TARGET_MANIFEST_SHA256: Final[str] = (
    "8b45a5755dc0ccc4df8d58f84f2408ef6e06e1847bb9b4e4e11963f3255e17bd"
)
TARGET_INSTRUMENT_SHA256: Final[str] = (
    "ddd069cf7317f86ad3c50b6e48291c4579efafb57a2a0ac3f420a5a4d7e080f8"
)
TARGET_TEST_SHA256: Final[str] = (
    "07231f87fb029a5154a843c6e8fed5fe77a6d5ef23fcdf0af330a7d3dd7b7379"
)
TARGET_ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

SOURCE_Q006_SHA256: Final[str] = (
    "72eb72aeb95f9727a9380902400c7d8e6891fba9447c30694193dad31f467674"
)
PROBE_SPEC_SHA256: Final[str] = (
    "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0
PLANNED_PROBES: Final[int] = 3

_SOURCE_MODULE_NAME: Final[str] = (
    "_oic_q007_source_provider_qualification_006"
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


def verify_frozen_sources() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        RECOVERY_RESULT: RECOVERY_RESULT_SHA256,
        RECOVERY_ADJ: RECOVERY_ADJ_SHA256,
        TARGET_PLAN: TARGET_PLAN_SHA256,
        TARGET_PREREG: TARGET_PREREG_SHA256,
        TARGET_FREEZE_V1: TARGET_FREEZE_V1_SHA256,
        TARGET_BINDING: TARGET_BINDING_SHA256,
        TARGET_FREEZE_V2: TARGET_FREEZE_V2_SHA256,
        TARGET_MANIFEST: TARGET_MANIFEST_SHA256,
        TARGET_INSTRUMENT: TARGET_INSTRUMENT_SHA256,
        TARGET_TEST: TARGET_TEST_SHA256,
        TARGET_ADAPTER: TARGET_ADAPTER_SHA256,
        SOURCE_Q006: SOURCE_Q006_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)

        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}"
            )


def load_source_q006() -> ModuleType:
    verify_frozen_sources()

    if _SOURCE_MODULE_NAME in sys.modules:
        return sys.modules[_SOURCE_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _SOURCE_MODULE_NAME,
        SOURCE_Q006,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "cannot load frozen Qualification 006 source instrument"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != "OIC-NVIDIA-PROVIDER-QUALIFICATION-006":
        raise SystemExit(
            "FAIL source Qualification 006 identity drift"
        )

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL source probe-spec constant drift"
        )

    if module.probe_spec_sha256() != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL source probe semantics drift"
        )

    if module.TIMEOUT_SECONDS != TIMEOUT_SECONDS:
        raise SystemExit(
            "FAIL source timeout drift"
        )

    if module.LATENCY_HEADROOM_SECONDS != LATENCY_HEADROOM_SECONDS:
        raise SystemExit(
            "FAIL source headroom drift"
        )

    if module.PACING_SECONDS != PACING_SECONDS:
        raise SystemExit(
            "FAIL source pacing drift"
        )

    if module.PLANNED_PROBES != PLANNED_PROBES:
        raise SystemExit(
            "FAIL source probe-count drift"
        )

    return module


def probes() -> tuple[Any, ...]:
    module = load_source_q006()
    values = tuple(module.PROBES)

    if [probe.probe_id for probe in values] != [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]:
        raise SystemExit(
            "FAIL source probe order/population drift"
        )

    return values


def expected_target() -> dict[str, Any]:
    return {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006",
        "commit_sha":
            ONTOLOGY_006_COMMIT,
        "plan_sha256":
            TARGET_PLAN_SHA256,
        "preregistration_sha256":
            TARGET_PREREG_SHA256,
        "preregistration_freeze_v0_1_sha256":
            TARGET_FREEZE_V1_SHA256,
        "treatment_binding_sha256":
            TARGET_BINDING_SHA256,
        "freeze_v0_2_sha256":
            TARGET_FREEZE_V2_SHA256,
        "request_materialization_sha256":
            TARGET_MANIFEST_SHA256,
        "instrument_sha256":
            TARGET_INSTRUMENT_SHA256,
        "contract_test_sha256":
            TARGET_TEST_SHA256,
        "provider_adapter_sha256":
            TARGET_ADAPTER_SHA256,
        "request_count":
            18,
        "pair_count":
            9,
        "live_run_executed":
            False,
    }


def request_projection(probe: Any) -> dict[str, Any]:
    return {
        "ordinal": probe.ordinal,
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
    verify_frozen_sources()

    plan = json.loads(
        PLAN_PATH.read_text(encoding="utf-8")
    )

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Qualification 007 identity drift"
        )

    if plan["base_sha"] != BASE_SHA:
        raise SystemExit(
            "FAIL Qualification 007 base drift"
        )

    if plan["fresh_provider_qualification"] is not True:
        raise SystemExit(
            "FAIL fresh-qualification state drift"
        )

    recovery = plan["prerequisite_recovery"]

    if recovery["classification"] != (
        "BOUNDED_RECOVERY_STABILITY_OBSERVED"
    ):
        raise SystemExit(
            "FAIL recovery prerequisite classification drift"
        )

    if recovery[
        "bounded_recovery_stability_established"
    ] is not True:
        raise SystemExit(
            "FAIL recovery prerequisite state drift"
        )

    if recovery[
        "provider_qualification_established"
    ] is not False:
        raise SystemExit(
            "FAIL recovery/provider qualification boundary drift"
        )

    if recovery[
        "qualification_007_consideration_permitted"
    ] is not True:
        raise SystemExit(
            "FAIL Qualification 007 consideration state drift"
        )

    if plan["semantic_successor_target"] != expected_target():
        raise SystemExit(
            "FAIL frozen Ontology 006 successor binding drift"
        )

    expected_provider = {
        "base_url": DEFAULT_NIM_BASE_URL,
        "latency_headroom_seconds": LATENCY_HEADROOM_SECONDS,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }

    if plan["provider"] != expected_provider:
        raise SystemExit(
            "FAIL provider envelope drift"
        )

    source = plan["probe_source"]

    if source["source_work_order"] != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    ):
        raise SystemExit(
            "FAIL source qualification identity drift"
        )

    if source["source_instrument_sha256"] != SOURCE_Q006_SHA256:
        raise SystemExit(
            "FAIL source qualification digest drift"
        )

    if source["probe_spec_sha256"] != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL probe specification binding drift"
        )

    if source["probe_ids"] != [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]:
        raise SystemExit(
            "FAIL probe population drift"
        )

    if plan["planned_probe_count"] != PLANNED_PROBES:
        raise SystemExit(
            "FAIL planned probe-count drift"
        )

    if plan["retries"] != 0:
        raise SystemExit(
            "FAIL Qualification 007 retries must remain zero"
        )

    if plan["replacement_probes_allowed"] is not False:
        raise SystemExit(
            "FAIL replacement probes must remain forbidden"
        )

    if plan["pacing_seconds"] != PACING_SECONDS:
        raise SystemExit(
            "FAIL pacing drift"
        )

    if plan["latency_headroom_seconds"] != LATENCY_HEADROOM_SECONDS:
        raise SystemExit(
            "FAIL latency-headroom drift"
        )

    if plan[
        "historical_qualification_observations_reused"
    ] is not False:
        raise SystemExit(
            "FAIL historical qualification observation reuse"
        )

    if plan[
        "recovery_stability_observations_reused"
    ] is not False:
        raise SystemExit(
            "FAIL recovery observation reuse"
        )

    if plan["semantic_hypothesis"] is not None:
        raise SystemExit(
            "FAIL semantic hypothesis introduced"
        )

    if plan["semantic_hypothesis_evaluated"] is not False:
        raise SystemExit(
            "FAIL semantic-hypothesis state drift"
        )

    if plan["qualification_007_qualified"] is not False:
        raise SystemExit(
            "FAIL pre-execution qualification state drift"
        )

    if plan["ontology_006_executed"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 execution state drift"
        )

    if plan["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 authorization drift"
        )

    return plan


def build_materialization() -> dict[str, Any]:
    verify_plan()
    source = load_source_q006()

    requests = []

    for probe in probes():
        projection = request_projection(probe)

        requests.append({
            "ordinal": probe.ordinal,
            "probe_id": probe.probe_id,
            "request_projection": projection,
            "request_projection_sha256":
                canonical_sha256(projection),
        })

    return {
        "work_order": WORK_ORDER,
        "status": "MATERIALIZED_OFFLINE_NOT_EXECUTED",
        "base_sha": BASE_SHA,
        "semantic_successor_target": expected_target(),
        "source_qualification_006_instrument_sha256":
            SOURCE_Q006_SHA256,
        "source_probe_spec_sha256":
            source.probe_spec_sha256(),
        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
            "latency_headroom_seconds":
                LATENCY_HEADROOM_SECONDS,
        },
        "request_count": len(requests),
        "retries": 0,
        "replacement_probes_allowed": False,
        "pacing_seconds": PACING_SECONDS,
        "historical_qualification_observations_reused": False,
        "recovery_stability_observations_reused": False,
        "provider_call_made": False,
        "model_call_made": False,
        "network_request_made": False,
        "live_run_executed": False,
        "qualification_007_qualified": False,
        "ontology_006_execution_authorized": False,
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
        f"materialized {manifest['request_count']} exact frozen probes"
    )
    print("NVIDIA/provider/model calls: ZERO")


def verify_manifest(
    manifest: dict[str, Any],
) -> None:
    expected = build_materialization()

    if manifest != expected:
        raise SystemExit(
            "FAIL Qualification 007 materialization drift"
        )

    if manifest["request_count"] != PLANNED_PROBES:
        raise SystemExit(
            "FAIL materialized probe count"
        )

    if manifest["retries"] != 0:
        raise SystemExit(
            "FAIL materialized retries"
        )

    if manifest["replacement_probes_allowed"] is not False:
        raise SystemExit(
            "FAIL materialized replacement policy"
        )

    if manifest["qualification_007_qualified"] is not False:
        raise SystemExit(
            "FAIL materialized qualification state"
        )

    if manifest["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL materialized successor authorization"
        )


def decide(
    attempts: list[dict[str, Any]],
) -> str:
    if len(attempts) != PLANNED_PROBES:
        return "NOT_QUALIFIED"

    if any(
        item.get("outcome") != "ACCEPTED"
        or item.get("marker_valid") is not True
        for item in attempts
    ):
        return "NOT_QUALIFIED"

    if any(
        float(item["elapsed_seconds"])
        > LATENCY_HEADROOM_SECONDS
        for item in attempts
    ):
        return "DEGRADED"

    return "QUALIFIED"


def preflight() -> dict[str, Any]:
    plan = verify_plan()

    if not MANIFEST_PATH.exists():
        raise SystemExit(
            "FAIL Qualification 007 request materialization missing"
        )

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL Qualification 007 static freeze v0.2 missing"
        )

    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    verify_manifest(
        manifest
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
        "qualification_instrument_sha256":
            sha256(Path(__file__)),
        "contract_test_sha256":
            sha256(CONTRACT_TEST),
        "request_materialization_sha256":
            sha256(MANIFEST_PATH),
        "recovery_execution_result_sha256":
            sha256(RECOVERY_RESULT),
        "recovery_post_run_adjudication_sha256":
            sha256(RECOVERY_ADJ),
        "source_qualification_006_instrument_sha256":
            sha256(SOURCE_Q006),
        "provider_adapter_sha256":
            sha256(TARGET_ADAPTER),
    }

    for key, expected in checks.items():
        if freeze.get(key) != expected:
            raise SystemExit(
                f"FAIL Qualification 007 static-freeze digest: {key}"
            )

    if freeze["planned_probe_count"] != PLANNED_PROBES:
        raise SystemExit("FAIL frozen probe count")

    if freeze["retries"] != 0:
        raise SystemExit("FAIL frozen retry policy")

    if freeze["replacement_probes_allowed"] is not False:
        raise SystemExit("FAIL frozen replacement policy")

    if freeze["latency_headroom_seconds"] != LATENCY_HEADROOM_SECONDS:
        raise SystemExit("FAIL frozen headroom")

    if freeze["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 already marked executed"
        )

    if freeze["qualification_007_qualified"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 prematurely qualified"
        )

    if freeze["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 prematurely authorized"
        )

    return plan


def execute_live() -> tuple[
    list[dict[str, Any]],
    str,
]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Qualification 007 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    preflight()

    source = load_source_q006()

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []

    for index, probe in enumerate(
        probes()
    ):
        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        print(
            f"[{probe.ordinal:02d}/{PLANNED_PROBES:02d}] "
            f"START {probe.probe_id}",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(
                request
            )

        except ModelProviderError as exc:
            elapsed = time.monotonic() - started

            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome": "PROVIDER_ERROR",
                "elapsed_seconds": round(elapsed, 3),
                "marker_valid": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }

        else:
            elapsed = time.monotonic() - started

            marker_valid = source.validate_marker(
                probe,
                response.content,
            )

            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome":
                    "ACCEPTED"
                    if marker_valid
                    else "RESPONSE_MISMATCH",
                "elapsed_seconds": round(elapsed, 3),
                "marker_valid": marker_valid,
                "provider": response.provider,
                "model": response.model,
                "request_id": response.request_id,
                "content_sha256":
                    hashlib.sha256(
                        response.content.encode("utf-8")
                    ).hexdigest(),
            }

        attempts.append(
            attempt
        )

        print(
            f"[{probe.ordinal:02d}/{PLANNED_PROBES:02d}] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={attempt['elapsed_seconds']}",
            flush=True,
        )

        if index < PLANNED_PROBES - 1:
            time.sleep(
                PACING_SECONDS
            )

    disposition = decide(
        attempts
    )

    receipt = {
        "work_order": WORK_ORDER,
        "base_sha": BASE_SHA,
        "semantic_successor_target": expected_target(),
        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
            "latency_headroom_seconds":
                LATENCY_HEADROOM_SECONDS,
        },
        "attempts": attempts,
        "terminal_observation_count": len(attempts),
        "disposition": disposition,
        "qualified_disposition_observed":
            disposition == "QUALIFIED",
        "qualification_007_formally_closed": False,
        "qualification_007_qualified": False,
        "ontology_006_execution_authorized": False,
        "formal_closure_required": True,
        "live_run_executed": True,
        "retries": 0,
        "replacement_probes_allowed": False,
        "pacing_seconds": PACING_SECONDS,
        "historical_qualification_observations_reused": False,
        "recovery_stability_observations_reused": False,
        "semantic_hypothesis": None,
        "semantic_hypothesis_evaluated": False,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "architecture_change_authorized": False,
        "independent_validation_claim": False,
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

    print(
        f"receipt written: {RECEIPT_PATH}",
        flush=True,
    )
    print(
        f"disposition: {disposition}",
        flush=True,
    )
    print(
        "Qualification 007 formally closed: NO",
        flush=True,
    )
    print(
        "Ontology 006 authorized: NO",
        flush=True,
    )

    return attempts, disposition


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
        "PASS frozen Provider Qualification 007 instrument"
    )
    print(
        f"probes: {plan['planned_probe_count']}"
    )
    print(
        "source probe spec: Qualification 006 / "
        f"{PROBE_SPEC_SHA256}"
    )
    print("headroom: 45 seconds")
    print("retries: ZERO")
    print("replacement probes: FORBIDDEN")
    print("Ontology 006 authorization: FALSE")
    print(
        "offline preflight only; "
        "no provider/model/network request made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
