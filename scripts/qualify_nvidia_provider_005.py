#!/usr/bin/env python3
"""OIC NVIDIA Provider Qualification 005.

Fresh provider-availability qualification gate for the exact NVIDIA NIM path
required by the preregistered and statically frozen Definition Ontology Staged
Decomposition 005 experiment.

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

WORK_ORDER: Final[str] = "OIC-NVIDIA-PROVIDER-QUALIFICATION-005"

BASE_SHA: Final[str] = (
    "713eb9a5f8cbe4b184e163573c30dd9d48cf1541"
)

BENCH = ROOT / "benchmarks/provider-qualification/nvidia-nim-005"

PLAN_PATH = BENCH / "PLAN-v0.1.json"
FREEZE_PATH = BENCH / "PLAN-FREEZE-v0.1.json"

TARGET_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005"
)

TARGET_PLAN = TARGET_DIR / "PLAN-v0.1.json"
TARGET_PREREG = TARGET_DIR / "PREREGISTRATION.md"
TARGET_FREEZE_V1 = TARGET_DIR / "PLAN-FREEZE-v0.1.json"
TARGET_TRANSPORT = TARGET_DIR / "TRANSPORT-RECOVERY-POLICY-v0.1.json"
TARGET_BINDING = TARGET_DIR / "SEMANTIC-REPLICATION-BINDING-v0.1.json"
TARGET_FREEZE_V2 = TARGET_DIR / "PLAN-FREEZE-v0.2.json"
TARGET_MANIFEST = TARGET_DIR / "REQUEST-MATERIALIZATION-v0.1.json"

TARGET_INSTRUMENT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_staged_decomposition_005.py"
)

TARGET_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_staged_decomposition_005.py"
)

TARGET_ADAPTER = ROOT / "src/oic/nvidia_nim.py"

RECEIPT_PATH = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-005.json"
)

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_qualification_005.py"
)

TIMEOUT_SECONDS: Final[float] = 60.0
LATENCY_HEADROOM_SECONDS: Final[float] = 45.0
PACING_SECONDS: Final[float] = 4.0
PLANNED_PROBES: Final[int] = 3

TARGET_PLAN_SHA256: Final[str] = "2dc022747d3eb4c9051e36d85f3a9d21fdf8330207057fdeb5c3a2883361ccfb"
TARGET_PREREG_SHA256: Final[str] = "df37d10254bd7e4b96329aaae1764494663619711a7bee2187fc447e27465b73"
TARGET_FREEZE_V1_SHA256: Final[str] = "1d210d2dcdb99904fa3ef9a600edd271935f98929eaab1b15bc7ed80e60c0a85"
TARGET_TRANSPORT_SHA256: Final[str] = "13cdf153a8394dfcb9ce64a468de2fda73cc5c705e02f4a7feb54147622d250f"
TARGET_BINDING_SHA256: Final[str] = "58204132703e9c613db68367c834c65a4008a671e3dcee92ef868029ea7bca14"
TARGET_FREEZE_V2_SHA256: Final[str] = "95220471ac0cb183791df5627bdf5c3d5d27436ac8301b6199332dfa76a1285a"
TARGET_INSTRUMENT_SHA256: Final[str] = "4a638722c680f3ed400b5987cdc023d8493e146bc7600f299371808fed9cf265"
TARGET_TEST_SHA256: Final[str] = "4a5b1e6045418f83ae50b0e0d3966c9ee005d070084dca0ffffd8252744cfb4d"
TARGET_MANIFEST_SHA256: Final[str] = "3c867101c0ef4ae1e27add45a8d980bd389c0f38f3608321557c0941d371bf29"
TARGET_ADAPTER_SHA256: Final[str] = "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"

PROBE_SPEC_SHA256: Final[str] = "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"


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
        (
            "You are a provider transport qualification probe. "
            "Follow the requested output exactly."
        ),
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
        "probes": [
            probe.to_plan_json()
            for probe in PROBES
        ],
        "retries": 0,
        "pacing_seconds": PACING_SECONDS,
        "latency_headroom_seconds":
            LATENCY_HEADROOM_SECONDS,
    }

    raw = json.dumps(
        spec,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def validate_marker(
    probe: Probe,
    content: str,
) -> bool:
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

    raise ValueError(
        f"unknown expected mode: {probe.expected_mode}"
    )


def decide(
    attempts: list[dict[str, Any]],
) -> str:
    if len(attempts) != PLANNED_PROBES:
        return "NOT_QUALIFIED"

    if any(
        item["outcome"] != "ACCEPTED"
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


def expected_target() -> dict[str, Any]:
    return {
        "work_order":
            "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005",
        "commit_sha":
            BASE_SHA,
        "plan_sha256":
            TARGET_PLAN_SHA256,
        "preregistration_sha256":
            TARGET_PREREG_SHA256,
        "preregistration_freeze_v0_1_sha256":
            TARGET_FREEZE_V1_SHA256,
        "transport_recovery_policy_sha256":
            TARGET_TRANSPORT_SHA256,
        "semantic_replication_binding_sha256":
            TARGET_BINDING_SHA256,
        "freeze_v0_2_sha256":
            TARGET_FREEZE_V2_SHA256,
        "instrument_sha256":
            TARGET_INSTRUMENT_SHA256,
        "contract_test_sha256":
            TARGET_TEST_SHA256,
        "request_materialization_sha256":
            TARGET_MANIFEST_SHA256,
        "provider_adapter_sha256":
            TARGET_ADAPTER_SHA256,
    }


def preflight() -> dict[str, Any]:
    freeze: dict[str, Any] = json.loads(
        FREEZE_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        freeze.get("qualification_instrument_sha256")
        != sha256(Path(__file__))
    ):
        raise SystemExit(
            "FAIL Qualification 005 instrument digest mismatch"
        )

    if (
        freeze.get("contract_test_sha256")
        != sha256(CONTRACT_TEST)
    ):
        raise SystemExit(
            "FAIL Qualification 005 contract-test digest mismatch"
        )

    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit(
            "FAIL provider-qualification 005 plan digest mismatch"
        )

    plan: dict[str, Any] = json.loads(
        PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        plan["work_order"] != WORK_ORDER
        or plan["base_sha"] != BASE_SHA
    ):
        raise SystemExit(
            "FAIL Qualification 005 identity mismatch"
        )

    target_hashes = {
        TARGET_PLAN: TARGET_PLAN_SHA256,
        TARGET_PREREG: TARGET_PREREG_SHA256,
        TARGET_FREEZE_V1: TARGET_FREEZE_V1_SHA256,
        TARGET_TRANSPORT: TARGET_TRANSPORT_SHA256,
        TARGET_BINDING: TARGET_BINDING_SHA256,
        TARGET_FREEZE_V2: TARGET_FREEZE_V2_SHA256,
        TARGET_INSTRUMENT: TARGET_INSTRUMENT_SHA256,
        TARGET_TEST: TARGET_TEST_SHA256,
        TARGET_MANIFEST: TARGET_MANIFEST_SHA256,
        TARGET_ADAPTER: TARGET_ADAPTER_SHA256,
    }

    for path, expected in target_hashes.items():
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen Ontology 005 target drift: {path}"
            )

    if plan["semantic_successor_target"] != expected_target():
        raise SystemExit(
            "FAIL Qualification 005 semantic-successor target drift"
        )

    expected_provider = {
        "base_url": DEFAULT_NIM_BASE_URL,
        "model": DEFAULT_NIM_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
    }

    if plan["provider"] != expected_provider:
        raise SystemExit(
            "FAIL NVIDIA provider path drift"
        )

    if plan["probes"] != [
        probe.to_plan_json()
        for probe in PROBES
    ]:
        raise SystemExit(
            "FAIL probe plan drift"
        )

    actual_probe_spec = probe_spec_sha256()

    if actual_probe_spec != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL probe semantics differ from frozen 004/003A probes"
        )

    if plan["probe_spec_sha256"] != actual_probe_spec:
        raise SystemExit(
            "FAIL probe specification digest mismatch"
        )

    if plan["retries"] != 0:
        raise SystemExit(
            "FAIL Qualification 005 retries must remain zero"
        )

    target_freeze = json.loads(
        TARGET_FREEZE_V2.read_text(
            encoding="utf-8"
        )
    )

    if (
        target_freeze["live_run_executed"] is not False
        or target_freeze["provider_qualification_005_executed"]
        is not False
    ):
        raise SystemExit(
            "FAIL target Ontology 005 is no longer pre-qualification"
        )

    return plan


def execute_live() -> tuple[
    list[dict[str, Any]],
    str,
]:
    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Qualification 005 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

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
            elapsed = (
                time.monotonic()
                - started
            )

            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome": "PROVIDER_ERROR",
                "elapsed_seconds":
                    round(elapsed, 3),
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
                probe,
                response.content,
            )

            attempt = {
                "ordinal": probe.ordinal,
                "probe_id": probe.probe_id,
                "outcome": (
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

        print(
            f"[{probe.ordinal:02d}/{PLANNED_PROBES:02d}] "
            f"DONE outcome={attempt['outcome']} "
            f"seconds={elapsed:.1f}",
            flush=True,
        )

        attempts.append(
            attempt
        )

        if index < len(PROBES) - 1:
            time.sleep(
                PACING_SECONDS
            )

    return (
        attempts,
        decide(attempts),
    )


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--live",
        action="store_true",
    )

    args = parser.parse_args(
        argv
    )

    plan = preflight()

    print(
        "PASS frozen provider-qualification 005 plan verified; "
        f"{len(PROBES)} probes"
    )

    print(
        f"endpoint: {plan['provider']['base_url']}"
    )

    print(
        f"model: {plan['provider']['model']}"
    )

    print(
        "semantic hypothesis: NONE"
    )

    print(
        "qualification retries: ZERO"
    )

    print(
        "semantic successor target: "
        "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005"
    )

    if not args.live:
        print(
            "offline preflight only; no provider was constructed "
            "and no request was made"
        )

        return 0

    attempts, disposition = (
        execute_live()
    )

    receipt = {
        "work_order":
            WORK_ORDER,
        "base_sha":
            BASE_SHA,
        "semantic_successor_target":
            expected_target(),
        "provider": {
            "base_url":
                DEFAULT_NIM_BASE_URL,
            "model":
                DEFAULT_NIM_MODEL,
            "timeout_seconds":
                TIMEOUT_SECONDS,
        },
        "attempts":
            attempts,
        "disposition":
            disposition,
        "semantic_successor_authorized":
            disposition == "QUALIFIED",
        "live_run_executed":
            True,
        "retries":
            0,
        "pacing_seconds":
            PACING_SECONDS,
        "semantic_hypothesis":
            None,
        "canonicalization_performed":
            False,
        "institutional_ir_constructed":
            False,
        "architectural_change_authorized":
            False,
        "independent_validation_claim":
            False,
        "self_adjudication":
            "NOT SELF-ADJUDICATED",
    }

    RECEIPT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECEIPT_PATH.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"receipt written: {RECEIPT_PATH}"
    )

    print(
        f"disposition: {disposition}"
    )

    print(
        "semantic successor authorized: "
        + (
            "YES"
            if disposition == "QUALIFIED"
            else "NO"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
