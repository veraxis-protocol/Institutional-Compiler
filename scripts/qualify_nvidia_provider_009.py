#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 009.

Fresh immediate provider-path qualification gate for the exact frozen
Ontology 007 semantic target.

Offline is the default. No provider is constructed without --live.

A live QUALIFIED disposition does not authorize Ontology 007.
Formal tracked post-run closure is required.
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

WORK_ORDER: Final[str] = "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-009"

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MANIFEST_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-discrimination-007"
)

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_BINDING = TARGET_DIR / "TREATMENT-BINDING-v0.1.json"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"

TARGET_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_predicate_carrier_discrimination_007.py"
)

TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_syntactic_predicate_carrier_discrimination_007.py"
)

TARGET_ADAPTER = ROOT / "src/oic/nvidia_nim.py"

SOURCE_O006_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006.py"
)

SOURCE_O006_MANIFEST = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

SOURCE_Q006 = ROOT / "scripts/qualify_nvidia_provider_006.py"

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_qualification_009.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-009.json"
)

PLAN_SHA256: Final[str] = (
    "f583963fed90cd4e7729ec245a3550884ce005775c0920f0c5fafd377810c900"
)
PREREG_SHA256: Final[str] = (
    "4a21043dc9626e4c29aa20ac9a6af5bcd0f0c73d8cae8eb09f09cdbfe2643542"
)
FREEZE_V1_SHA256: Final[str] = (
    "6f232960009331fbf854fc5ba40584f5eb69ed0fcdec4b6e45c5ea9a5eff1391"
)

TARGET_PREREG_COMMIT: Final[str] = (
    "227354320680151789409ec8722a183a4e093596"
)
TARGET_PLAN_SHA256: Final[str] = (
    "3e57e122ed718372bbe89bca33c9103bc9f47caca83ce86436ac5bbe63cc64ad"
)
TARGET_PREREG_SHA256: Final[str] = (
    "a186e0fc3e46a2d277c5960b323ae9ffad8d012b5780264c595aab2996ec626e"
)
TARGET_BINDING_SHA256: Final[str] = (
    "35d4eedc13ae6d1c2e510bd0feb53e717a363f4dd71aa8c5d6954138b0bc158b"
)
TARGET_FREEZE_V1_SHA256: Final[str] = (
    "b6ed2b7648e9c9c7cdfc421b73030f1004c40c94358e8638cde99a6bc27e0e9d"
)
TARGET_MANIFEST_SHA256: Final[str] = (
    "02567faee5aa55e830207b271023bf555a6f02417433731319ab0a869020f96a"
)
TARGET_FREEZE_V2_SHA256: Final[str] = (
    "7fbe8fe83f410acae85b5890ec4d32c39e54ce24d33dfd61c974cd235af976bb"
)
TARGET_SCRIPT_SHA256: Final[str] = (
    "be752c975a6da03e9a0237aa7df09f38caf81a2e416b23584e3d86d998fa0834"
)
TARGET_TEST_SHA256: Final[str] = (
    "c1ef0b1568fc16c70e6302d853a7a4a03c74dcf3ebfed18807b872c6f4887365"
)
TARGET_ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

SOURCE_O006_SCRIPT_SHA256: Final[str] = (
    "ddd069cf7317f86ad3c50b6e48291c4579efafb57a2a0ac3f420a5a4d7e080f8"
)
SOURCE_O006_MANIFEST_SHA256: Final[str] = (
    "8b45a5755dc0ccc4df8d58f84f2408ef6e06e1847bb9b4e4e11963f3255e17bd"
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

_SOURCE_MODULE_NAME: Final[str] = "_oic_q009_source_q006"


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
        TARGET_PLAN: TARGET_PLAN_SHA256,
        TARGET_PREREG: TARGET_PREREG_SHA256,
        TARGET_BINDING: TARGET_BINDING_SHA256,
        TARGET_FREEZE_V1: TARGET_FREEZE_V1_SHA256,
        TARGET_MANIFEST: TARGET_MANIFEST_SHA256,
        TARGET_FREEZE_V2: TARGET_FREEZE_V2_SHA256,
        TARGET_SCRIPT: TARGET_SCRIPT_SHA256,
        TARGET_TEST: TARGET_TEST_SHA256,
        TARGET_ADAPTER: TARGET_ADAPTER_SHA256,
        SOURCE_O006_SCRIPT: SOURCE_O006_SCRIPT_SHA256,
        SOURCE_O006_MANIFEST: SOURCE_O006_MANIFEST_SHA256,
        SOURCE_Q006: SOURCE_Q006_SHA256,
    }

    for path, expected_sha in expected.items():
        if sha256(path) != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}"
            )


def source_q006() -> ModuleType:
    verify_frozen_sources()

    if _SOURCE_MODULE_NAME in sys.modules:
        return sys.modules[_SOURCE_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _SOURCE_MODULE_NAME,
        SOURCE_Q006,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("FAIL cannot load frozen Qualification 006")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != "OIC-NVIDIA-PROVIDER-QUALIFICATION-006":
        raise SystemExit("FAIL source qualification identity drift")

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit("FAIL probe-spec constant drift")

    if module.probe_spec_sha256() != PROBE_SPEC_SHA256:
        raise SystemExit("FAIL exact probe semantics drift")

    if module.TIMEOUT_SECONDS != TIMEOUT_SECONDS:
        raise SystemExit("FAIL timeout drift")

    if module.LATENCY_HEADROOM_SECONDS != LATENCY_HEADROOM_SECONDS:
        raise SystemExit("FAIL headroom drift")

    if module.PACING_SECONDS != PACING_SECONDS:
        raise SystemExit("FAIL pacing drift")

    if module.PLANNED_PROBES != PLANNED_PROBES:
        raise SystemExit("FAIL probe-count drift")

    return module


def probes() -> tuple[Any, ...]:
    values = tuple(source_q006().PROBES)

    if [x.probe_id for x in values] != [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]:
        raise SystemExit("FAIL probe population/order drift")

    return values


def target_descriptor() -> dict[str, Any]:
    return {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-DISCRIMINATION-007",

        "preregistration_commit":
            TARGET_PREREG_COMMIT,

        "plan_sha256":
            TARGET_PLAN_SHA256,

        "preregistration_sha256":
            TARGET_PREREG_SHA256,

        "treatment_binding_sha256":
            TARGET_BINDING_SHA256,

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

        "provider_adapter_sha256":
            TARGET_ADAPTER_SHA256,

        "source_o006_instrument_sha256":
            SOURCE_O006_SCRIPT_SHA256,

        "source_o006_request_materialization_sha256":
            SOURCE_O006_MANIFEST_SHA256,

        "request_count":
            18,

        "pair_count":
            9,
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
        PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )

    assert plan["work_order"] == WORK_ORDER
    assert plan["fresh_provider_qualification"] is True

    assert plan["provider"] == {
        "base_url": DEFAULT_NIM_BASE_URL,
        "latency_headroom_seconds": LATENCY_HEADROOM_SECONDS,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }

    assert plan["probe_source"]["source_work_order"] == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    )

    assert plan["probe_source"]["source_instrument_sha256"] == (
        SOURCE_Q006_SHA256
    )

    assert plan["probe_source"]["probe_spec_sha256"] == (
        PROBE_SPEC_SHA256
    )

    assert plan["probe_source"]["probe_ids"] == [
        "BASIC_TEXT",
        "JSON_MODE",
        "PRODUCTION_TOKEN_RESERVATION",
    ]

    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["replacement_probes_allowed"] is False
    assert plan["pacing_seconds"] == 4.0
    assert plan["latency_headroom_seconds"] == 45.0

    assert plan["semantic_successor_target"] == target_descriptor()

    assert plan["historical_qualification_observations_reused"] is False
    assert plan["q008_observations_reused"] is False
    assert plan["q008_authorization_reused"] is False
    assert plan["recovery_stability_observations_reused"] is False

    assert plan["live_run_executed"] is False
    assert plan["qualification_009_formally_closed"] is False
    assert plan["qualification_009_qualified"] is False
    assert plan["provider_qualification_established"] is False

    assert plan["ontology_007_execution_authorized"] is False
    assert plan["ontology_007_executed"] is False

    assert plan["semantic_hypothesis"] is None
    assert plan["semantic_hypothesis_evaluated"] is False
    assert plan["architecture_change_authorized"] is False

    return plan


def materialization_document() -> dict[str, Any]:
    verify_plan()
    source = source_q006()

    rows = []

    for probe in probes():
        projection = request_projection(probe)

        rows.append({
            "ordinal":
                probe.ordinal,

            "probe_id":
                probe.probe_id,

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

        "semantic_successor_target":
            target_descriptor(),

        "source_qualification_006_instrument_sha256":
            SOURCE_Q006_SHA256,

        "source_probe_spec_sha256":
            source.probe_spec_sha256(),

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
            3,

        "retries":
            0,

        "replacement_probes_allowed":
            False,

        "pacing_seconds":
            PACING_SECONDS,

        "historical_qualification_observations_reused":
            False,

        "q008_observations_reused":
            False,

        "q008_authorization_reused":
            False,

        "recovery_stability_observations_reused":
            False,

        "provider_call_made":
            False,

        "model_call_made":
            False,

        "network_request_made":
            False,

        "live_run_executed":
            False,

        "qualification_009_formally_closed":
            False,

        "qualification_009_qualified":
            False,

        "provider_qualification_established":
            False,

        "ontology_007_execution_authorized":
            False,

        "ontology_007_executed":
            False,

        "requests":
            rows,
    }


def materialize() -> None:
    if MANIFEST_PATH.exists():
        raise SystemExit(
            f"STOP Q009 materialization already exists: {MANIFEST_PATH}"
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

    print("materialized 3 exact frozen probes")
    print("provider/model/network calls: ZERO")


def verify_materialization() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise SystemExit("FAIL Q009 materialization missing")

    actual = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    expected = materialization_document()

    if actual != expected:
        raise SystemExit("FAIL Q009 materialization drift")

    return actual


def decide(attempts: list[dict[str, Any]]) -> str:
    if len(attempts) != 3:
        return "NOT_QUALIFIED"

    if any(
        x.get("outcome") != "ACCEPTED"
        or x.get("marker_valid") is not True
        for x in attempts
    ):
        return "NOT_QUALIFIED"

    if any(
        float(x["elapsed_seconds"]) > LATENCY_HEADROOM_SECONDS
        for x in attempts
    ):
        return "DEGRADED"

    return "QUALIFIED"


def preflight() -> dict[str, Any]:
    plan = verify_plan()
    verify_materialization()

    if not FREEZE_V2_PATH.exists():
        raise SystemExit("FAIL Q009 static freeze v0.2 missing")

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

        "target_plan_sha256":
            sha256(TARGET_PLAN),

        "target_preregistration_sha256":
            sha256(TARGET_PREREG),

        "target_treatment_binding_sha256":
            sha256(TARGET_BINDING),

        "target_preregistration_freeze_v0_1_sha256":
            sha256(TARGET_FREEZE_V1),

        "target_freeze_v0_2_sha256":
            sha256(TARGET_FREEZE_V2),

        "target_instrument_sha256":
            sha256(TARGET_SCRIPT),

        "target_contract_test_sha256":
            sha256(TARGET_TEST),

        "target_request_materialization_sha256":
            sha256(TARGET_MANIFEST),

        "provider_adapter_sha256":
            sha256(TARGET_ADAPTER),

        "source_o006_instrument_sha256":
            sha256(SOURCE_O006_SCRIPT),

        "source_o006_request_materialization_sha256":
            sha256(SOURCE_O006_MANIFEST),

        "source_probe_instrument_sha256":
            sha256(SOURCE_Q006),
    }

    for key, value in checks.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL Q009 static-freeze digest mismatch: {key}"
            )

    assert freeze["planned_probe_count"] == 3
    assert freeze["retries"] == 0
    assert freeze["replacement_probes_allowed"] is False
    assert freeze["latency_headroom_seconds"] == 45.0

    assert freeze["live_run_executed"] is False
    assert freeze["qualification_009_formally_closed"] is False
    assert freeze["qualification_009_qualified"] is False
    assert freeze["provider_qualification_established"] is False
    assert freeze["ontology_007_execution_authorized"] is False
    assert freeze["ontology_007_executed"] is False

    return plan


def execute_live() -> tuple[list[dict[str, Any]], str]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Q009 receipt already exists: {RECEIPT_PATH}"
        )

    preflight()

    source = source_q006()

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []

    for index, probe in enumerate(probes()):
        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )

        print(
            f"[{probe.ordinal:02d}/03] START {probe.probe_id}",
            flush=True,
        )

        started = time.monotonic()

        try:
            response = provider.complete(request)

        except ModelProviderError as exc:
            elapsed = time.monotonic() - started

            attempt = {
                "ordinal":
                    probe.ordinal,

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

            marker_valid = source.validate_marker(
                probe,
                response.content,
            )

            attempt = {
                "ordinal":
                    probe.ordinal,

                "probe_id":
                    probe.probe_id,

                "outcome":
                    "ACCEPTED"
                    if marker_valid
                    else "RESPONSE_MISMATCH",

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

        attempts.append(attempt)

        print(
            f"[{probe.ordinal:02d}/03] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={attempt['elapsed_seconds']}",
            flush=True,
        )

        if index < 2:
            time.sleep(PACING_SECONDS)

    disposition = decide(attempts)

    receipt = {
        "work_order":
            WORK_ORDER,

        "semantic_successor_target":
            target_descriptor(),

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

        "disposition":
            disposition,

        "qualified_disposition_observed":
            disposition == "QUALIFIED",

        "qualification_009_formally_closed":
            False,

        "qualification_009_qualified":
            False,

        "provider_qualification_established":
            False,

        "ontology_007_execution_authorized":
            False,

        "ontology_007_executed":
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

        "q008_observations_reused":
            False,

        "q008_authorization_reused":
            False,

        "recovery_stability_observations_reused":
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

    print(f"receipt written: {RECEIPT_PATH}")
    print(f"disposition: {disposition}")
    print("Q009 formally closed: FALSE")
    print("Ontology 007 execution authorized: FALSE")

    return attempts, disposition


def main(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv)

    if args.materialize:
        materialize()
        return 0

    if args.live:
        execute_live()
        return 0

    plan = preflight()

    print("PASS frozen Provider Qualification 009 instrument")
    print(f"probes: {plan['planned_probe_count']}")
    print(f"probe spec: {PROBE_SPEC_SHA256}")
    print("target: exact frozen Ontology 007")
    print("headroom: 45 seconds")
    print("retries: ZERO")
    print("replacements: FORBIDDEN")
    print("Q008 inheritance: FALSE")
    print("Q009 formally closed: FALSE")
    print("Ontology 007 authorization: FALSE")
    print(
        "offline preflight only; "
        "no provider/model/network request made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
