#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 003A.

Fresh provider-availability qualification gate for the exact NVIDIA NIM path
required by the already-preregistered and statically frozen Definition Ontology
Discrimination 003A experiment.

No semantic hypothesis is tested here. Offline is the default; no provider is
constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

ROOT = Path(__file__).resolve().parents[1]
WORK_ORDER: Final[str] = "OIC-NVIDIA-PROVIDER-QUALIFICATION-003A"
BASE_SHA: Final[str] = "33f2504a8da56256cdd397c66237613f45030c40"

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-003a"
PLAN_PATH = BENCH / "PLAN-v0.1.json"
FREEZE_PATH = BENCH / "PLAN-FREEZE-v0.1.json"

TARGET_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a/PLAN-v0.1.json"
)
TARGET_FREEZE = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a/"
    "PLAN-FREEZE-v0.2.json"
)

TARGET_PREREG = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a/PREREGISTRATION.md"
)
TARGET_INSTRUMENT = ROOT / "scripts/characterize_definition_ontology_discrimination_003a.py"
TARGET_TEST = ROOT / "tests/test_definition_ontology_discrimination_003a.py"
TARGET_MANIFEST = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a/"
    "REQUEST-MATERIALIZATION-v0.1.json"
)

RECEIPT_PATH = (
    ROOT / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-003A.json"
)
CONTRACT_TEST = ROOT / "tests/contract/test_nvidia_provider_qualification_003a.py"

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0
PLANNED_PROBES: Final[int] = 3

TARGET_PLAN_SHA256: Final[str] = "e0d90bf41adf76402bd03cd1183feaffdbc8528c2a897874a266fe183d11cae1"
TARGET_FREEZE_SHA256: Final[str] = (
    "0b796021f03cf6fd4514167b003de2b2fa5227a8739eeef15b4b8332e6f24710"
)

TARGET_PREREG_SHA256: Final[str] = (
    "49b40628b5e9e44af3944ff5954847ef358d55c85385f8dfd941ad0e1bce7348"
)
TARGET_INSTRUMENT_SHA256: Final[str] = (
    "dee47076199b104888092aaa6adbc57709003c78765f275c2b4031dc9701ddd3"
)
TARGET_TEST_SHA256: Final[str] = "8836b984d3c03b3c2d1946f070df43bfd003f908a6e20cc1620902387478959a"
TARGET_MANIFEST_SHA256: Final[str] = (
    "15cc46b20df2ba27c354dc2d1be9b5bb8815c3dd7d5f0efa0dd03a1b2f816b51"
)


@dataclass(frozen=True, slots=True)
class Probe:
    ordinal: int
    probe_id: str
    response_format: dict[str, Any] | None
    max_tokens: int
    system_prompt: str
    user_prompt: str
    expected_mode: str
    expected_value: str

    def to_plan_json(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "probe_id": self.probe_id,
            "response_format": self.response_format,
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
            "expected_mode": self.expected_mode,
            "expected_value": self.expected_value,
        }


PROBES: Final[tuple[Probe, ...]] = (
    Probe(
        1,
        "BASIC_TEXT",
        None,
        16,
        ("You are a provider transport qualification probe. Follow the requested output exactly."),
        "Return exactly OIC_PROVIDER_OK and nothing else.",
        "TEXT_MARKER",
        "OIC_PROVIDER_OK",
    ),
    Probe(
        2,
        "JSON_MODE",
        {"type": "json_object"},
        64,
        (
            "You are a provider structured-output qualification probe. "
            "Return only the requested JSON object."
        ),
        'Return exactly {"status":"OIC_PROVIDER_OK"} as JSON and nothing else.',
        "JSON_STATUS",
        "OIC_PROVIDER_OK",
    ),
    Probe(
        3,
        "PRODUCTION_TOKEN_RESERVATION",
        {"type": "json_object"},
        4096,
        (
            "You are a provider structured-output qualification probe. "
            "Return only the requested JSON object."
        ),
        'Return exactly {"status":"OIC_PROVIDER_OK"} as JSON and nothing else.',
        "JSON_STATUS",
        "OIC_PROVIDER_OK",
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe_spec_sha256() -> str:
    spec = {
        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "probes": [probe.to_plan_json() for probe in PROBES],
        "retries": 0,
        "pacing_seconds": PACING_SECONDS,
        "latency_headroom_seconds": LATENCY_HEADROOM_SECONDS,
    }
    raw = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_marker(probe: Probe, content: str) -> bool:
    if probe.expected_mode == "TEXT_MARKER":
        return content.strip() == probe.expected_value
    if probe.expected_mode == "JSON_STATUS":
        try:
            parsed: Any = json.loads(content)
        except json.JSONDecodeError:
            return False
        return (
            isinstance(parsed, dict)
            and set(parsed) == {"status"}
            and parsed["status"] == probe.expected_value
        )
    raise ValueError(f"unknown expected mode: {probe.expected_mode}")


def decide(attempts: list[dict[str, Any]]) -> str:
    if len(attempts) != PLANNED_PROBES:
        return "NOT_QUALIFIED"
    if any(item["outcome"] != "ACCEPTED" for item in attempts):
        return "NOT_QUALIFIED"
    if any(float(item["elapsed_seconds"]) > LATENCY_HEADROOM_SECONDS for item in attempts):
        return "DEGRADED"
    return "QUALIFIED"


def preflight() -> dict[str, Any]:
    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("qualification_instrument_sha256") != sha256(Path(__file__)):
        raise SystemExit("FAIL Qualification 003A instrument digest mismatch")
    if freeze.get("contract_test_sha256") != sha256(CONTRACT_TEST):
        raise SystemExit("FAIL Qualification 003A contract-test digest mismatch")
    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit("FAIL provider-qualification 003A plan digest mismatch")
    plan: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    if plan["work_order"] != WORK_ORDER or plan["base_sha"] != BASE_SHA:
        raise SystemExit("FAIL qualification 003A identity mismatch")

    if sha256(TARGET_PLAN) != TARGET_PLAN_SHA256:
        raise SystemExit("FAIL target Ontology 003A plan digest mismatch")
    if sha256(TARGET_FREEZE) != TARGET_FREEZE_SHA256:
        raise SystemExit("FAIL target Ontology 003A freeze digest mismatch")

    if sha256(TARGET_PREREG) != TARGET_PREREG_SHA256:
        raise SystemExit("FAIL target Ontology 003A preregistration digest mismatch")

    if sha256(TARGET_INSTRUMENT) != TARGET_INSTRUMENT_SHA256:
        raise SystemExit("FAIL target Ontology 003A instrument digest mismatch")

    if sha256(TARGET_TEST) != TARGET_TEST_SHA256:
        raise SystemExit("FAIL target Ontology 003A contract-test digest mismatch")

    if sha256(TARGET_MANIFEST) != TARGET_MANIFEST_SHA256:
        raise SystemExit("FAIL target Ontology 003A request-manifest digest mismatch")

    expected_target = {
        "work_order": "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A",
        "commit_sha": BASE_SHA,
        "plan_sha256": TARGET_PLAN_SHA256,
        "preregistration_sha256": TARGET_PREREG_SHA256,
        "freeze_v0_2_sha256": TARGET_FREEZE_SHA256,
        "instrument_sha256": TARGET_INSTRUMENT_SHA256,
        "contract_test_sha256": TARGET_TEST_SHA256,
        "request_materialization_sha256": TARGET_MANIFEST_SHA256,
    }

    if plan["semantic_successor_target"] != expected_target:
        raise SystemExit("FAIL Qualification 003A semantic-successor target drift")

    if plan["provider"] != {
        "base_url": DEFAULT_NIM_BASE_URL,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }:
        raise SystemExit("FAIL provider path drift")

    if plan["probes"] != [probe.to_plan_json() for probe in PROBES]:
        raise SystemExit("FAIL probe plan drift")

    if plan["probe_spec_sha256"] != probe_spec_sha256():
        raise SystemExit("FAIL probe specification digest mismatch")

    return plan


def execute_live() -> tuple[list[dict[str, Any]], str]:
    if RECEIPT_PATH.exists():
        raise SystemExit(f"STOP Qualification 003A receipt already exists: {RECEIPT_PATH}")

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts: list[dict[str, Any]] = []
    for index, probe in enumerate(PROBES):
        request = ModelRequest(
            system_prompt=probe.system_prompt,
            user_prompt=probe.user_prompt,
            response_format=probe.response_format,
            temperature=0.0,
            max_tokens=probe.max_tokens,
        )
        print(
            f"[{probe.ordinal:02d}/{PLANNED_PROBES:02d}] START {probe.probe_id}",
            flush=True,
        )
        started = time.monotonic()
        try:
            response = provider.complete(request)
        except ModelProviderError as exc:
            elapsed = time.monotonic() - started
            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome": "PROVIDER_ERROR",
                "elapsed_seconds": round(elapsed, 3),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        else:
            elapsed = time.monotonic() - started
            marker_valid = validate_marker(probe, response.content)
            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome": "ACCEPTED" if marker_valid else "RESPONSE_MISMATCH",
                "elapsed_seconds": round(elapsed, 3),
                "marker_valid": marker_valid,
                "provider": response.provider,
                "model": response.model,
                "request_id": response.request_id,
                "content_sha256": hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
            }
        print(
            f"[{probe.ordinal:02d}/{PLANNED_PROBES:02d}] DONE "
            f"outcome={attempt['outcome']} seconds={elapsed:.1f}",
            flush=True,
        )
        attempts.append(attempt)
        if index < len(PROBES) - 1:
            time.sleep(PACING_SECONDS)

    return attempts, decide(attempts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    plan = preflight()
    print(f"PASS frozen provider-qualification 003A plan verified; {len(PROBES)} probes")
    print(f"endpoint: {plan['provider']['base_url']}")
    print(f"model: {plan['provider']['model']}")
    print("semantic hypothesis: NONE")
    print("semantic successor target: OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    attempts, disposition = execute_live()

    receipt = {
        "work_order": WORK_ORDER,
        "base_sha": BASE_SHA,
        "semantic_successor_target": {
            "work_order": "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A",
            "commit_sha": BASE_SHA,
            "plan_sha256": TARGET_PLAN_SHA256,
            "preregistration_sha256": TARGET_PREREG_SHA256,
            "freeze_v0_2_sha256": TARGET_FREEZE_SHA256,
            "instrument_sha256": TARGET_INSTRUMENT_SHA256,
            "contract_test_sha256": TARGET_TEST_SHA256,
            "request_materialization_sha256": TARGET_MANIFEST_SHA256,
        },
        "provider": {
            "base_url": DEFAULT_NIM_BASE_URL,
            "model": DEFAULT_NIM_MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
        },
        "attempts": attempts,
        "disposition": disposition,
        "semantic_successor_authorized": disposition == "QUALIFIED",
        "live_run_executed": True,
        "retries": 0,
        "pacing_seconds": PACING_SECONDS,
        "semantic_hypothesis": None,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"receipt written: {RECEIPT_PATH}")
    print(f"disposition: {disposition}")
    print("semantic successor authorized: " + ("YES" if disposition == "QUALIFIED" else "NO"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
