#!/usr/bin/env python3
"""Bounded NVIDIA provider-path incident localization.

Offline by default.

No DNS, socket, TLS, HTTP, NVIDIA, provider, or model operation occurs
unless --live is explicitly supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import os
import signal
import socket
import ssl
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Iterator

from oic.model_provider import ModelRequest
from oic.nvidia_nim import build_chat_payload

ROOT = Path(__file__).resolve().parents[1]

WORK_ORDER: Final[str] = (
    "OIC-NVIDIA-PROVIDER-PATH-INCIDENT-001"
)

PREREG_COMMIT: Final[str] = (
    "27d9a003b561445d60382a35f977045115c0e3d9"
)

SOURCE_CLOSURE_COMMIT: Final[str] = (
    "69e77bfa7e09a371a1e3675fd8742d0f6fe1cf0b"
)

BENCH = (
    ROOT
    / "benchmarks/provider-incidents/nvidia-nim-path-001"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = (
    BENCH / "DIAGNOSTIC-MATERIALIZATION-v0.1.json"
)
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE_RESULT = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-latency-stability-001/"
      "EXECUTION-RESULT-v0.1.json"
)

SOURCE_ADJ = (
    ROOT
    / "benchmarks/provider-characterization/"
      "nvidia-nim-latency-stability-001/"
      "POST-RUN-ADJUDICATION.md"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"

QUAL006_SCRIPT = (
    ROOT / "scripts/qualify_nvidia_provider_006.py"
)

CONTRACT_TEST = (
    ROOT
    / "tests/contract/"
      "test_nvidia_provider_path_incident_001.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/provider-incident-receipts/"
      "OIC-NVIDIA-PROVIDER-PATH-INCIDENT-001.json"
)

PLAN_SHA256: Final[str] = (
    "a62862a0e3a366e0c6f33524d4937df57c7dc929b480d31aefebcc86cd1d0560"
)
PREREG_SHA256: Final[str] = (
    "b1632970b5329a007ad67fbd9e7d8a26e3f6dc45093cec10ac297f523fdaf629"
)
FREEZE_V1_SHA256: Final[str] = (
    "060ae8cb0dee87f4f2fbeb9b680192c7c393dd44913fbd7e611a0205798ad3d9"
)

SOURCE_RESULT_SHA256: Final[str] = (
    "bde77412e37282083034b22c03b14dc93ee3320ca70957e97811fae3983e0ab8"
)
SOURCE_ADJ_SHA256: Final[str] = (
    "f11d8f5772f3afa72513eed42d04f0c56df421dd1ff7090d7ae5acf37e6d3582"
)

ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)
QUAL006_SCRIPT_SHA256: Final[str] = (
    "72eb72aeb95f9727a9380902400c7d8e6891fba9447c30694193dad31f467674"
)
PROBE_SPEC_SHA256: Final[str] = (
    "262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1"
)

HOST: Final[str] = "integrate.api.nvidia.com"
PORT: Final[int] = 443
CHAT_PATH: Final[str] = "/v1/chat/completions"

MODEL: Final[str] = (
    "nvidia/nemotron-3.5-lightning-30b-a3b"
)

DNS_TIMEOUT: Final[float] = 10.0
TCP_TIMEOUT: Final[float] = 10.0
TLS_TIMEOUT: Final[float] = 10.0
HTTP_TIMEOUT: Final[float] = 15.0
AUTH_TIMEOUT: Final[float] = 15.0
TARGET_TIMEOUT: Final[float] = 60.0

_QUAL_MODULE_NAME: Final[str] = (
    "_oic_incident_source_qualification_006"
)


class DiagnosticDeadlineExceeded(TimeoutError):
    """One frozen incident-diagnostic wall-clock deadline expired."""


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
        SOURCE_RESULT: SOURCE_RESULT_SHA256,
        SOURCE_ADJ: SOURCE_ADJ_SHA256,
        ADAPTER: ADAPTER_SHA256,
        QUAL006_SCRIPT: QUAL006_SCRIPT_SHA256,
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
        QUAL006_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "cannot load frozen Qualification 006 instrument"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[_QUAL_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if (
        module.WORK_ORDER
        != "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    ):
        raise SystemExit(
            "FAIL Qualification 006 identity drift"
        )

    if module.PROBE_SPEC_SHA256 != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL Qualification 006 probe binding drift"
        )

    if module.probe_spec_sha256() != PROBE_SPEC_SHA256:
        raise SystemExit(
            "FAIL Qualification 006 probe semantics drift"
        )

    return module


def frozen_basic_probe() -> Any:
    module = load_qualification_006()

    probes = [
        probe
        for probe in module.PROBES
        if probe.probe_id == "BASIC_TEXT"
    ]

    if len(probes) != 1:
        raise SystemExit(
            "FAIL frozen BASIC_TEXT probe cardinality"
        )

    return probes[0]


def basic_text_payload() -> dict[str, Any]:
    probe = frozen_basic_probe()

    request = ModelRequest(
        system_prompt=probe.system_prompt,
        user_prompt=probe.user_prompt,
        response_format=probe.response_format,
        temperature=0.0,
        max_tokens=probe.max_tokens,
    )

    payload = build_chat_payload(
        request,
        model=MODEL,
    )

    if probe.response_format is not None:
        raise SystemExit(
            "FAIL frozen BASIC_TEXT unexpectedly structured"
        )

    return payload


def basic_text_expected_marker() -> str:
    probe = frozen_basic_probe()

    if probe.expected_mode != "TEXT_MARKER":
        raise SystemExit(
            "FAIL BASIC_TEXT expected-mode drift"
        )

    return probe.expected_value


def load_plan() -> dict[str, Any]:
    verify_source_hashes()

    plan = json.loads(
        PLAN_PATH.read_text(encoding="utf-8")
    )

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL incident identity drift")

    if plan["starting_sha"] != SOURCE_CLOSURE_COMMIT:
        raise SystemExit(
            "FAIL incident starting-SHA drift"
        )

    if plan["maximum_live_diagnostics"] != 6:
        raise SystemExit(
            "FAIL diagnostic ceiling drift"
        )

    if plan["maximum_model_inference_requests"] != 1:
        raise SystemExit(
            "FAIL model-call ceiling drift"
        )

    if plan["retries"] != 0:
        raise SystemExit(
            "FAIL incident retries must remain zero"
        )

    if plan["replacement_requests_allowed"] is not False:
        raise SystemExit(
            "FAIL replacement diagnostics must remain forbidden"
        )

    if plan["stop_on_earliest_layer_failure"] is not True:
        raise SystemExit(
            "FAIL early-stop rule drift"
        )

    if plan["qualification_007_authorized"] is not False:
        raise SystemExit(
            "FAIL Qualification 007 authorization drift"
        )

    if plan["ontology_006_execution_authorized"] is not False:
        raise SystemExit(
            "FAIL Ontology 006 authorization drift"
        )

    expected_ids = [
        "DNS_RESOLUTION",
        "TCP_CONNECT",
        "TLS_HANDSHAKE",
        "HTTP_ROUTE",
        "AUTH_VALIDATION",
        "TARGET_BASIC_TEXT",
    ]

    sequence = plan["diagnostic_sequence"]

    if [
        item["diagnostic_id"]
        for item in sequence
    ] != expected_ids:
        raise SystemExit(
            "FAIL incident diagnostic-order drift"
        )

    return plan


def materialized_diagnostics() -> list[dict[str, Any]]:
    plan = load_plan()

    route_body = {
        "incident_probe":
            "deliberately_unauthenticated_and_invalid"
    }

    auth_body = {
        "temperature": 0.0,
    }

    target_body = basic_text_payload()

    projections = {
        "DNS_RESOLUTION": {
            "host": HOST,
            "port": PORT,
            "operation": "socket.getaddrinfo",
        },
        "TCP_CONNECT": {
            "host": HOST,
            "port": PORT,
            "operation": "socket.create_connection",
        },
        "TLS_HANDSHAKE": {
            "host": HOST,
            "port": PORT,
            "server_hostname": HOST,
            "certificate_verification": True,
        },
        "HTTP_ROUTE": {
            "method": "POST",
            "host": HOST,
            "port": PORT,
            "path": CHAT_PATH,
            "headers": {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "body": route_body,
            "authentication": None,
        },
        "AUTH_VALIDATION": {
            "method": "POST",
            "host": HOST,
            "port": PORT,
            "path": CHAT_PATH,
            "headers": {
                "Accept": "application/json",
                "Authorization":
                    "Bearer <RUNTIME_NVIDIA_API_KEY>",
                "Content-Type": "application/json",
            },
            "body": auth_body,
            "model_inference_intended": False,
        },
        "TARGET_BASIC_TEXT": {
            "method": "POST",
            "host": HOST,
            "port": PORT,
            "path": CHAT_PATH,
            "headers": {
                "Accept": "application/json",
                "Authorization":
                    "Bearer <RUNTIME_NVIDIA_API_KEY>",
                "Content-Type": "application/json",
            },
            "body": target_body,
            "expected_marker":
                basic_text_expected_marker(),
            "source_probe_spec_sha256":
                PROBE_SPEC_SHA256,
            "model_inference_intended": True,
        },
    }

    output: list[dict[str, Any]] = []

    for item in plan["diagnostic_sequence"]:
        projection = projections[
            item["diagnostic_id"]
        ]

        output.append({
            "ordinal":
                item["ordinal"],
            "diagnostic_id":
                item["diagnostic_id"],
            "timeout_seconds":
                item["timeout_seconds"],
            "maximum_attempts":
                item["maximum_attempts"],
            "credential_required":
                item["credential_required"],
            "model_inference":
                item["model_inference"],
            "request_projection":
                projection,
            "request_projection_sha256":
                canonical_sha256(projection),
        })

    return output


def build_materialization() -> dict[str, Any]:
    diagnostics = materialized_diagnostics()

    return {
        "work_order":
            WORK_ORDER,

        "status":
            "MATERIALIZED_OFFLINE_NOT_EXECUTED",

        "diagnostic_count":
            len(diagnostics),

        "maximum_live_diagnostics":
            6,

        "maximum_model_inference_requests":
            1,

        "retries":
            0,

        "replacement_requests_allowed":
            False,

        "diagnostic_order_fixed":
            True,

        "stop_on_earliest_layer_failure":
            True,

        "credential_materialized":
            False,

        "source_qualification_006_probe_spec_sha256":
            PROBE_SPEC_SHA256,

        "provider_diagnostic_call_made":
            False,

        "model_call_made":
            False,

        "nvidia_network_request_made":
            False,

        "live_run_executed":
            False,

        "diagnostics":
            diagnostics,
    }


def materialize() -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            "STOP diagnostic materialization already exists"
        )

    doc = build_materialization()

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            doc,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print("six diagnostics materialized")
    print("credential materialized: FALSE")
    print("NVIDIA/provider/model calls: ZERO")


@contextmanager
def wall_deadline(
    seconds: float,
) -> Iterator[None]:
    """Bound one diagnostic by one wall-clock deadline on POSIX."""

    previous_handler = signal.getsignal(signal.SIGALRM)

    def _expired(
        _signum: int,
        _frame: Any,
    ) -> None:
        raise DiagnosticDeadlineExceeded(
            f"diagnostic deadline exceeded: {seconds}s"
        )

    signal.signal(
        signal.SIGALRM,
        _expired,
    )
    signal.setitimer(
        signal.ITIMER_REAL,
        seconds,
    )

    try:
        yield
    finally:
        signal.setitimer(
            signal.ITIMER_REAL,
            0.0,
        )
        signal.signal(
            signal.SIGALRM,
            previous_handler,
        )


def diagnostic_dns() -> dict[str, Any]:
    started = time.monotonic()

    try:
        with wall_deadline(DNS_TIMEOUT):
            results = socket.getaddrinfo(
                HOST,
                PORT,
                type=socket.SOCK_STREAM,
            )
    except (
        DiagnosticDeadlineExceeded,
        socket.gaierror,
        OSError,
    ) as exc:
        return {
            "diagnostic_id": "DNS_RESOLUTION",
            "outcome": "FAIL",
            "elapsed_seconds":
                round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    addresses = sorted({
        item[4][0]
        for item in results
        if item[4]
    })

    return {
        "diagnostic_id": "DNS_RESOLUTION",
        "outcome": "PASS",
        "elapsed_seconds":
            round(time.monotonic() - started, 3),
        "address_count": len(addresses),
        "addresses": addresses,
    }


def diagnostic_tcp() -> dict[str, Any]:
    started = time.monotonic()
    sock: socket.socket | None = None

    try:
        with wall_deadline(TCP_TIMEOUT):
            sock = socket.create_connection(
                (HOST, PORT),
                timeout=TCP_TIMEOUT,
            )

            peer = sock.getpeername()

    except (
        DiagnosticDeadlineExceeded,
        TimeoutError,
        socket.timeout,
        OSError,
    ) as exc:
        return {
            "diagnostic_id": "TCP_CONNECT",
            "outcome": "FAIL",
            "elapsed_seconds":
                round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    finally:
        if sock is not None:
            sock.close()

    return {
        "diagnostic_id": "TCP_CONNECT",
        "outcome": "PASS",
        "elapsed_seconds":
            round(time.monotonic() - started, 3),
        "peer_host": peer[0],
        "peer_port": peer[1],
    }


def diagnostic_tls() -> dict[str, Any]:
    started = time.monotonic()

    raw_sock: socket.socket | None = None
    tls_sock: ssl.SSLSocket | None = None

    try:
        with wall_deadline(TLS_TIMEOUT):
            raw_sock = socket.create_connection(
                (HOST, PORT),
                timeout=TLS_TIMEOUT,
            )

            raw_sock.settimeout(TLS_TIMEOUT)

            context = ssl.create_default_context()

            tls_sock = context.wrap_socket(
                raw_sock,
                server_hostname=HOST,
            )

            cert_der = tls_sock.getpeercert(
                binary_form=True
            )

            protocol = tls_sock.version()
            cipher_info = tls_sock.cipher()

    except (
        DiagnosticDeadlineExceeded,
        TimeoutError,
        socket.timeout,
        ssl.SSLError,
        OSError,
    ) as exc:
        return {
            "diagnostic_id": "TLS_HANDSHAKE",
            "outcome": "FAIL",
            "elapsed_seconds":
                round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    finally:
        if tls_sock is not None:
            tls_sock.close()
        elif raw_sock is not None:
            raw_sock.close()

    return {
        "diagnostic_id": "TLS_HANDSHAKE",
        "outcome": "PASS",
        "elapsed_seconds":
            round(time.monotonic() - started, 3),
        "tls_protocol": protocol,
        "cipher":
            cipher_info[0]
            if cipher_info
            else None,
        "certificate_sha256":
            hashlib.sha256(
                cert_der or b""
            ).hexdigest(),
        "hostname_verified": True,
    }


def _http_exchange(
    *,
    diagnostic_id: str,
    body: dict[str, Any],
    timeout_seconds: float,
    authorization: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    connection_started = started

    conn = http.client.HTTPSConnection(
        HOST,
        PORT,
        timeout=timeout_seconds,
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if authorization is not None:
        headers["Authorization"] = authorization

    encoded = json.dumps(
        body,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    try:
        with wall_deadline(timeout_seconds):
            conn.connect()

            connected = time.monotonic()

            conn.request(
                "POST",
                CHAT_PATH,
                body=encoded,
                headers=headers,
            )

            request_sent = time.monotonic()

            response = conn.getresponse()

            headers_received = time.monotonic()

            raw = response.read()

            body_complete = time.monotonic()

            response_headers = {
                key.lower(): value
                for key, value
                in response.getheaders()
            }

    except (
        DiagnosticDeadlineExceeded,
        TimeoutError,
        socket.timeout,
        ssl.SSLError,
        OSError,
        http.client.HTTPException,
    ) as exc:
        return {
            "diagnostic_id": diagnostic_id,
            "outcome": "TRANSPORT_FAILURE",
            "elapsed_seconds":
                round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

    finally:
        conn.close()

    return {
        "diagnostic_id": diagnostic_id,
        "outcome": "HTTP_RESPONSE",
        "elapsed_seconds":
            round(body_complete - started, 3),
        "connection_seconds":
            round(connected - connection_started, 3),
        "request_send_seconds":
            round(request_sent - connected, 3),
        "response_headers_seconds":
            round(headers_received - request_sent, 3),
        "response_body_seconds":
            round(body_complete - headers_received, 3),
        "http_status": response.status,
        "http_reason": response.reason,
        "response_body_length": len(raw),
        "response_body_sha256":
            hashlib.sha256(raw).hexdigest(),
        "content_type":
            response_headers.get("content-type"),
        "request_id_header":
            (
                response_headers.get("x-request-id")
                or response_headers.get("request-id")
            ),
        "_raw_response_body": raw,
    }


def diagnostic_http_route() -> dict[str, Any]:
    record = _http_exchange(
        diagnostic_id="HTTP_ROUTE",
        body={
            "incident_probe":
                "deliberately_unauthenticated_and_invalid"
        },
        timeout_seconds=HTTP_TIMEOUT,
        authorization=None,
    )

    record.pop(
        "_raw_response_body",
        None,
    )

    if record["outcome"] == "HTTP_RESPONSE":
        record["route_reachable"] = True

    return record


def diagnostic_auth_validation(
    api_key: str,
) -> dict[str, Any]:
    record = _http_exchange(
        diagnostic_id="AUTH_VALIDATION",
        body={
            "temperature": 0.0,
        },
        timeout_seconds=AUTH_TIMEOUT,
        authorization=f"Bearer {api_key}",
    )

    record.pop(
        "_raw_response_body",
        None,
    )

    if record["outcome"] != "HTTP_RESPONSE":
        return record

    status = int(record["http_status"])

    if status in (401, 403):
        record["outcome"] = "AUTH_REJECTED"
        record["explicit_auth_or_account_rejection"] = True
        return record

    if status in (400, 422):
        record["outcome"] = "VALIDATION_REACHED"
        record["explicit_auth_or_account_rejection"] = False
        return record

    record["outcome"] = "UNEXPECTED_HTTP_RESPONSE"
    record["explicit_auth_or_account_rejection"] = False
    return record


def _extract_target_content(
    raw: bytes,
) -> tuple[
    str | None,
    str | None,
]:
    try:
        decoded = json.loads(
            raw.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None, None

    if not isinstance(decoded, dict):
        return None, None

    request_id = (
        decoded.get("id")
        if isinstance(decoded.get("id"), str)
        else None
    )

    choices = decoded.get("choices")

    if (
        not isinstance(choices, list)
        or not choices
        or not isinstance(choices[0], dict)
    ):
        return None, request_id

    message = choices[0].get("message")

    if not isinstance(message, dict):
        return None, request_id

    content = message.get("content")

    if not isinstance(content, str):
        return None, request_id

    return content, request_id


def diagnostic_target_basic_text(
    api_key: str,
) -> dict[str, Any]:
    record = _http_exchange(
        diagnostic_id="TARGET_BASIC_TEXT",
        body=basic_text_payload(),
        timeout_seconds=TARGET_TIMEOUT,
        authorization=f"Bearer {api_key}",
    )

    raw = record.pop(
        "_raw_response_body",
        None,
    )

    if record["outcome"] != "HTTP_RESPONSE":
        record["outcome"] = "TIMEOUT_OR_TRANSPORT_FAILURE"
        return record

    status = int(record["http_status"])

    if not (200 <= status < 300):
        record["outcome"] = "HTTP_ERROR"
        return record

    if not isinstance(raw, bytes):
        record["outcome"] = "RESPONSE_FAILURE"
        return record

    content, response_id = _extract_target_content(raw)

    record["response_id"] = response_id

    if content is None:
        record["outcome"] = "RESPONSE_FAILURE"
        record["marker_valid"] = False
        return record

    marker_valid = (
        content.strip()
        == basic_text_expected_marker()
    )

    record["response_content_sha256"] = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    record["marker_valid"] = marker_valid

    record["outcome"] = (
        "ACCEPTED"
        if marker_valid
        else "RESPONSE_FAILURE"
    )

    return record


def classification(
    observations: list[dict[str, Any]],
) -> str:
    by_id = {
        item["diagnostic_id"]: item
        for item in observations
    }

    dns = by_id.get("DNS_RESOLUTION")

    if dns is None or dns["outcome"] != "PASS":
        return "DNS_RESOLUTION_FAILURE"

    tcp = by_id.get("TCP_CONNECT")

    if tcp is None or tcp["outcome"] != "PASS":
        return "TCP_CONNECT_FAILURE"

    tls = by_id.get("TLS_HANDSHAKE")

    if tls is None or tls["outcome"] != "PASS":
        return "TLS_HANDSHAKE_FAILURE"

    route = by_id.get("HTTP_ROUTE")

    if (
        route is None
        or route["outcome"] != "HTTP_RESPONSE"
    ):
        return "HTTP_ROUTE_OR_GATEWAY_FAILURE"

    auth = by_id.get("AUTH_VALIDATION")

    if auth is None:
        return "INCONCLUSIVE"

    if auth["outcome"] == "AUTH_REJECTED":
        return "AUTH_OR_ACCOUNT_FAILURE"

    if auth["outcome"] != "VALIDATION_REACHED":
        return "INCONCLUSIVE"

    target = by_id.get("TARGET_BASIC_TEXT")

    if target is None:
        return "INCONCLUSIVE"

    if (
        target["outcome"]
        == "TIMEOUT_OR_TRANSPORT_FAILURE"
    ):
        return "TARGET_INFERENCE_PATH_TIMEOUT"

    if target["outcome"] == "ACCEPTED":
        return "TARGET_PATH_RESPONDED_DURING_INCIDENT_PROBE"

    return "TARGET_INFERENCE_HTTP_OR_RESPONSE_FAILURE"


def should_continue(
    observation: dict[str, Any],
) -> bool:
    diagnostic_id = observation["diagnostic_id"]
    outcome = observation["outcome"]

    if diagnostic_id in {
        "DNS_RESOLUTION",
        "TCP_CONNECT",
        "TLS_HANDSHAKE",
    }:
        return outcome == "PASS"

    if diagnostic_id == "HTTP_ROUTE":
        return outcome == "HTTP_RESPONSE"

    if diagnostic_id == "AUTH_VALIDATION":
        return outcome == "VALIDATION_REACHED"

    return False


def verify_materialization(
    plan: dict[str, Any],
    materialization: dict[str, Any],
) -> None:
    expected = build_materialization()

    if materialization != expected:
        raise SystemExit(
            "FAIL diagnostic materialization drift"
        )

    if materialization["diagnostic_count"] != 6:
        raise SystemExit(
            "FAIL diagnostic-count drift"
        )

    if materialization[
        "maximum_model_inference_requests"
    ] != 1:
        raise SystemExit(
            "FAIL model-call ceiling drift"
        )

    if materialization["retries"] != 0:
        raise SystemExit(
            "FAIL retries drift"
        )

    if materialization[
        "replacement_requests_allowed"
    ] is not False:
        raise SystemExit(
            "FAIL replacement policy drift"
        )

    if materialization[
        "credential_materialized"
    ] is not False:
        raise SystemExit(
            "FAIL credential materialization detected"
        )

    if [
        item["diagnostic_id"]
        for item in materialization["diagnostics"]
    ] != [
        item["diagnostic_id"]
        for item in plan["diagnostic_sequence"]
    ]:
        raise SystemExit(
            "FAIL diagnostic order/materialization mismatch"
        )


def preflight() -> dict[str, Any]:
    plan = load_plan()

    if not MATERIALIZATION_PATH.exists():
        raise SystemExit(
            "FAIL diagnostic materialization missing"
        )

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL static freeze v0.2 missing"
        )

    materialization = json.loads(
        MATERIALIZATION_PATH.read_text(
            encoding="utf-8"
        )
    )

    verify_materialization(
        plan,
        materialization,
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
        "diagnostic_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "provider_adapter_sha256":
            sha256(ADAPTER),
        "source_qualification_006_instrument_sha256":
            sha256(QUAL006_SCRIPT),
    }

    for key, expected in checks.items():
        if freeze.get(key) != expected:
            raise SystemExit(
                f"FAIL static-freeze digest mismatch: {key}"
            )

    if freeze["maximum_live_diagnostics"] != 6:
        raise SystemExit(
            "FAIL static diagnostic ceiling drift"
        )

    if freeze[
        "maximum_model_inference_requests"
    ] != 1:
        raise SystemExit(
            "FAIL static model ceiling drift"
        )

    if freeze["retries"] != 0:
        raise SystemExit(
            "FAIL static retries drift"
        )

    if freeze[
        "replacement_requests_allowed"
    ] is not False:
        raise SystemExit(
            "FAIL static replacement drift"
        )

    if freeze["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL incident already marked executed"
        )

    if freeze[
        "qualification_007_authorized"
    ] is not False:
        raise SystemExit(
            "FAIL Qualification 007 authorization drift"
        )

    if freeze[
        "ontology_006_execution_authorized"
    ] is not False:
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
            f"STOP incident receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    preflight()

    api_key = os.environ.get(
        "NVIDIA_API_KEY"
    )

    if api_key is None or not api_key.strip():
        raise SystemExit(
            "STOP NVIDIA_API_KEY must be present before "
            "the one-shot incident investigation begins"
        )

    api_key = api_key.strip()

    observations: list[dict[str, Any]] = []

    diagnostics = (
        lambda: diagnostic_dns(),
        lambda: diagnostic_tcp(),
        lambda: diagnostic_tls(),
        lambda: diagnostic_http_route(),
        lambda: diagnostic_auth_validation(api_key),
        lambda: diagnostic_target_basic_text(api_key),
    )

    for index, run in enumerate(
        diagnostics,
        start=1,
    ):
        print(
            f"[{index:02d}/06] START",
            flush=True,
        )

        observation = run()
        observation["ordinal"] = index

        observations.append(
            observation
        )

        print(
            f"[{index:02d}/06] "
            f"{observation['diagnostic_id']} "
            f"{observation['outcome']} "
            f"{observation.get('elapsed_seconds')}s",
            flush=True,
        )

        if index < 6 and not should_continue(
            observation
        ):
            print(
                "EARLY STOP: frozen layer boundary reached",
                flush=True,
            )
            break

    disposition = classification(
        observations
    )

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

        "incident_source":
            "OIC-NVIDIA-PROVIDER-LATENCY-STABILITY-001",

        "source_closure_commit":
            SOURCE_CLOSURE_COMMIT,

        "planned_maximum_diagnostics":
            6,

        "executed_diagnostics":
            len(observations),

        "maximum_model_inference_requests":
            1,

        "actual_model_inference_requests":
            sum(
                item["diagnostic_id"]
                == "TARGET_BASIC_TEXT"
                for item in observations
            ),

        "retries":
            0,

        "replacement_requests_allowed":
            False,

        "observations":
            observations,

        "classification":
            disposition,

        "semantic_hypothesis_evaluated":
            False,

        "qualification_006_reclassified":
            False,

        "qualification_007_authorized":
            False,

        "ontology_006_execution_authorized":
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

        "diagnostic_materialization_sha256":
            freeze[
                "diagnostic_materialization_sha256"
            ],

        "static_freeze_v0_2_sha256":
            sha256(FREEZE_V2_PATH),
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
        "Qualification 007 authorized: NO",
        flush=True,
    )
    print(
        "Ontology 006 authorized: NO",
        flush=True,
    )

    return observations, disposition


def main() -> int:
    parser = argparse.ArgumentParser()

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--materialize",
        action="store_true",
    )

    modes.add_argument(
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
        "PASS frozen NVIDIA provider-path incident 001 instrument"
    )
    print(
        f"diagnostic layers: "
        f"{len(plan['diagnostic_sequence'])}"
    )
    print(
        "maximum model inference requests: 1"
    )
    print("retries: ZERO")
    print("replacements: FORBIDDEN")
    print(
        "offline preflight only; "
        "no DNS/socket/TLS/HTTP/provider/model call made"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
