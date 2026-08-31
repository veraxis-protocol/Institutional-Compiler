#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 003.

Fresh provider-availability qualification gate for the exact NVIDIA NIM path
required by the already-preregistered and statically frozen Definition Ontology
Discrimination 003 experiment.

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
WORK_ORDER: Final[str] = "OIC-NVIDIA-PROVIDER-QUALIFICATION-003"
BASE_SHA: Final[str] = "fd07eefae35e3fb0855847bd4d0a911ec3636a9f"

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-003"
PLAN_PATH = BENCH / "PLAN-v0.1.json"
FREEZE_PATH = BENCH / "PLAN-FREEZE-v0.1.json"

TARGET_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003/PLAN-v0.1.json"
)
TARGET_FREEZE = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003/"
    "PLAN-FREEZE-v0.2.json"
)

RECEIPT_PATH = (
    ROOT / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-003.json"
)
CONTRACT_TEST = ROOT / "tests/contract/test_nvidia_provider_qualification_003.py"

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0
PLANNED_PROBES: Final[int] = 3

TARGET_PLAN_SHA256: Final[str] = "1643851ed0afddeafaba5731abd9308695c4f374b0be567fb8fae9ce6168b570"
TARGET_FREEZE_SHA256: Final[str] = (
    "e50310eecf97fc3aedfd3f673ca80fd800f02f7ac3bfaf1afc82f0a2cd5cb62d"
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
        raise SystemExit("FAIL Qualification 003 instrument digest mismatch")
    if freeze.get("contract_test_sha256") != sha256(CONTRACT_TEST):
        raise SystemExit("FAIL Qualification 003 contract-test digest mismatch")
    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit("FAIL provider-qualification 003 plan digest mismatch")
    plan: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    if plan["work_order"] != WORK_ORDER or plan["base_sha"] != BASE_SHA:
        raise SystemExit("FAIL qualification 003 identity mismatch")

    if sha256(TARGET_PLAN) != TARGET_PLAN_SHA256:
        raise SystemExit("FAIL target Ontology 003 plan digest mismatch")
    if sha256(TARGET_FREEZE) != TARGET_FREEZE_SHA256:
        raise SystemExit("FAIL target Ontology 003 freeze digest mismatch")

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
        raise SystemExit(f"STOP Qualification 003 receipt already exists: {RECEIPT_PATH}")

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
    print(f"PASS frozen provider-qualification 003 plan verified; {len(PROBES)} probes")
    print(f"endpoint: {plan['provider']['base_url']}")
    print(f"model: {plan['provider']['model']}")
    print("semantic hypothesis: NONE")
    print("semantic successor target: OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    attempts, disposition = execute_live()

    receipt = {
        "work_order": WORK_ORDER,
        "base_sha": BASE_SHA,
        "semantic_successor_target": {
            "work_order": "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003",
            "commit_sha": BASE_SHA,
            "plan_sha256": TARGET_PLAN_SHA256,
            "freeze_v0_2_sha256": TARGET_FREEZE_SHA256,
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
