from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = (
    ROOT
    / "scripts/investigate_nvidia_provider_path_incident_001.py"
)

MODULE_NAME = "_test_nvidia_provider_path_incident_001"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load_plan() -> dict[str, Any]:
    return json.loads(
        module.PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )


def load_materialization() -> dict[str, Any]:
    return json.loads(
        module.MATERIALIZATION_PATH.read_text(
            encoding="utf-8"
        )
    )


def record(
    diagnostic_id: str,
    outcome: str,
) -> dict[str, Any]:
    return {
        "diagnostic_id": diagnostic_id,
        "outcome": outcome,
    }


def passed_prefix() -> list[dict[str, Any]]:
    return [
        record("DNS_RESOLUTION", "PASS"),
        record("TCP_CONNECT", "PASS"),
        record("TLS_HANDSHAKE", "PASS"),
        record("HTTP_ROUTE", "HTTP_RESPONSE"),
        record("AUTH_VALIDATION", "VALIDATION_REACHED"),
    ]


def test_frozen_identity_and_six_layer_order() -> None:
    plan = load_plan()

    assert module.WORK_ORDER == (
        "OIC-NVIDIA-PROVIDER-PATH-INCIDENT-001"
    )

    assert [
        item["diagnostic_id"]
        for item in plan["diagnostic_sequence"]
    ] == [
        "DNS_RESOLUTION",
        "TCP_CONNECT",
        "TLS_HANDSHAKE",
        "HTTP_ROUTE",
        "AUTH_VALIDATION",
        "TARGET_BASIC_TEXT",
    ]

    assert plan["maximum_live_diagnostics"] == 6
    assert plan["maximum_model_inference_requests"] == 1


def test_frozen_sources_and_basic_probe_binding() -> None:
    module.verify_source_hashes()

    q = module.load_qualification_006()
    probe = module.frozen_basic_probe()

    assert q.PROBE_SPEC_SHA256 == module.PROBE_SPEC_SHA256
    assert q.probe_spec_sha256() == module.PROBE_SPEC_SHA256

    assert probe.probe_id == "BASIC_TEXT"
    assert probe.expected_mode == "TEXT_MARKER"
    assert probe.expected_value == "OIC_PROVIDER_OK"
    assert probe.max_tokens == 16
    assert probe.response_format is None


def test_target_payload_is_exact_adapter_projection() -> None:
    probe = module.frozen_basic_probe()

    request = module.ModelRequest(
        system_prompt=probe.system_prompt,
        user_prompt=probe.user_prompt,
        response_format=probe.response_format,
        temperature=0.0,
        max_tokens=probe.max_tokens,
    )

    expected = module.build_chat_payload(
        request,
        model=module.MODEL,
    )

    assert module.basic_text_payload() == expected


def test_materialization_is_exact_and_secret_free() -> None:
    plan = load_plan()
    materialization = load_materialization()

    module.verify_materialization(
        plan,
        materialization,
    )

    assert materialization["diagnostic_count"] == 6
    assert materialization[
        "maximum_model_inference_requests"
    ] == 1

    assert materialization["credential_materialized"] is False

    raw = module.MATERIALIZATION_PATH.read_text(
        encoding="utf-8"
    )

    assert "RUNTIME_NVIDIA_API_KEY" in raw
    assert "nvapi-" not in raw


def test_zero_retry_non_authorization_boundary() -> None:
    plan = load_plan()
    materialization = load_materialization()

    assert plan["retries"] == 0
    assert plan["replacement_requests_allowed"] is False
    assert plan["qualification_007_authorized"] is False
    assert plan["ontology_006_execution_authorized"] is False
    assert plan["architecture_change_authorized"] is False

    assert materialization["retries"] == 0
    assert materialization[
        "replacement_requests_allowed"
    ] is False


@pytest.mark.parametrize(
    ("observations", "expected"),
    [
        (
            [
                record("DNS_RESOLUTION", "FAIL"),
            ],
            "DNS_RESOLUTION_FAILURE",
        ),
        (
            [
                record("DNS_RESOLUTION", "PASS"),
                record("TCP_CONNECT", "FAIL"),
            ],
            "TCP_CONNECT_FAILURE",
        ),
        (
            [
                record("DNS_RESOLUTION", "PASS"),
                record("TCP_CONNECT", "PASS"),
                record("TLS_HANDSHAKE", "FAIL"),
            ],
            "TLS_HANDSHAKE_FAILURE",
        ),
        (
            [
                record("DNS_RESOLUTION", "PASS"),
                record("TCP_CONNECT", "PASS"),
                record("TLS_HANDSHAKE", "PASS"),
                record("HTTP_ROUTE", "TRANSPORT_FAILURE"),
            ],
            "HTTP_ROUTE_OR_GATEWAY_FAILURE",
        ),
        (
            passed_prefix()[:-1]
            + [
                record(
                    "AUTH_VALIDATION",
                    "AUTH_REJECTED",
                ),
            ],
            "AUTH_OR_ACCOUNT_FAILURE",
        ),
        (
            passed_prefix()
            + [
                record(
                    "TARGET_BASIC_TEXT",
                    "TIMEOUT_OR_TRANSPORT_FAILURE",
                ),
            ],
            "TARGET_INFERENCE_PATH_TIMEOUT",
        ),
        (
            passed_prefix()
            + [
                record(
                    "TARGET_BASIC_TEXT",
                    "HTTP_ERROR",
                ),
            ],
            "TARGET_INFERENCE_HTTP_OR_RESPONSE_FAILURE",
        ),
        (
            passed_prefix()
            + [
                record(
                    "TARGET_BASIC_TEXT",
                    "ACCEPTED",
                ),
            ],
            "TARGET_PATH_RESPONDED_DURING_INCIDENT_PROBE",
        ),
    ],
)
def test_frozen_classification_precedence(
    observations: list[dict[str, Any]],
    expected: str,
) -> None:
    assert module.classification(observations) == expected


def test_unexpected_auth_http_is_inconclusive() -> None:
    observations = passed_prefix()[:-1] + [
        record(
            "AUTH_VALIDATION",
            "UNEXPECTED_HTTP_RESPONSE",
        ),
    ]

    assert module.classification(
        observations
    ) == "INCONCLUSIVE"


@pytest.mark.parametrize(
    ("diagnostic_id", "outcome", "expected"),
    [
        ("DNS_RESOLUTION", "PASS", True),
        ("DNS_RESOLUTION", "FAIL", False),
        ("TCP_CONNECT", "PASS", True),
        ("TLS_HANDSHAKE", "PASS", True),
        ("HTTP_ROUTE", "HTTP_RESPONSE", True),
        ("HTTP_ROUTE", "TRANSPORT_FAILURE", False),
        ("AUTH_VALIDATION", "VALIDATION_REACHED", True),
        ("AUTH_VALIDATION", "AUTH_REJECTED", False),
        ("TARGET_BASIC_TEXT", "ACCEPTED", False),
    ],
)
def test_early_stop_semantics(
    diagnostic_id: str,
    outcome: str,
    expected: bool,
) -> None:
    assert module.should_continue(
        record(diagnostic_id, outcome)
    ) is expected


def test_offline_preflight_performs_no_live_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = (
        "diagnostic_dns",
        "diagnostic_tcp",
        "diagnostic_tls",
        "diagnostic_http_route",
        "diagnostic_auth_validation",
        "diagnostic_target_basic_text",
    )

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(
            "live diagnostic called during offline preflight"
        )

    for name in forbidden:
        monkeypatch.setattr(
            module,
            name,
            fail,
        )

    plan = module.preflight()

    assert plan["live_run_executed"] is False
    assert plan["qualification_007_authorized"] is False
    assert plan["ontology_006_execution_authorized"] is False
