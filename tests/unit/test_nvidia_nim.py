from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pytest

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import (
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
    build_chat_payload,
)


def test_payload_disables_thinking_for_structured_candidate_output() -> None:
    request = ModelRequest(
        system_prompt="system",
        user_prompt="user",
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=123,
    )
    payload = build_chat_payload(request, model=DEFAULT_NIM_MODEL)
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["temperature"] == 0.0


def test_remote_http_endpoint_is_rejected() -> None:
    with pytest.raises(ModelProviderError, match="https"):
        NvidiaNimConfig(base_url="http://example.com/v1").validate_endpoint()


def test_loopback_http_endpoint_is_allowed_for_self_hosted_nim() -> None:
    NvidiaNimConfig(base_url="http://localhost:8000/v1").validate_endpoint()


# --------------------------------------------------------------------------
# OIC-NIM-TIMEOUT-BOUNDARY-001: transport error normalization
#
# A live OIC-CANDIDATE-SEMANTICS-002 characterization aborted on request 60 of 120 when a
# read timeout surfaced as a bare TimeoutError. That is a sibling of urllib.error.URLError
# under OSError, not a subclass, so it escaped the provider boundary and killed the run
# instead of becoming one recorded PROVIDER_ERROR.
#
# These tests drive urlopen through a monkeypatch and open no socket. The suite disables
# sockets anyway, so a test that reached the network would fail rather than pass quietly.
# --------------------------------------------------------------------------

SENTINEL_KEY = "nvapi-TEST-SENTINEL-DO-NOT-COMMIT-000000"
REQUEST_BODY_MARKER = "SENSITIVE-REQUEST-BODY-MARKER"


class _Response:
    """A minimal urlopen context manager. Optionally times out mid-read."""

    def __init__(self, body: bytes = b"{}", *, read_raises: BaseException | None = None) -> None:
        self.body = body
        self.read_raises = read_raises

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        if self.read_raises is not None:
            raise self.read_raises
        return self.body


def _patch_urlopen(
    monkeypatch: pytest.MonkeyPatch, behaviour: Callable[[], object]
) -> list[object]:
    """Replace urlopen with ``behaviour`` and record every call made to it."""
    calls: list[object] = []

    def fake_urlopen(request: object, timeout: float | None = None) -> object:
        calls.append(request)
        del timeout
        return behaviour()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def _request() -> ModelRequest:
    return ModelRequest(
        system_prompt="system",
        user_prompt=REQUEST_BODY_MARKER,
        response_format={"type": "json_object"},
    )


def _provider(monkeypatch: pytest.MonkeyPatch) -> NvidiaNimProvider:
    monkeypatch.setenv("NVIDIA_API_KEY", SENTINEL_KEY)
    return NvidiaNimProvider(NvidiaNimConfig())


def test_a_timeout_opening_the_connection_becomes_a_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout() -> object:
        raise TimeoutError("timed out")

    calls = _patch_urlopen(monkeypatch, raise_timeout)
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError, match="NVIDIA NIM connection timed out") as excinfo:
        provider.complete(_request())
    assert isinstance(excinfo.value.__cause__, TimeoutError)
    assert len(calls) == 1


def test_a_timeout_reading_an_opened_response_becomes_a_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact live failure: the connection opened, then the read timed out."""
    read_timeout = TimeoutError("The read operation timed out")
    calls = _patch_urlopen(monkeypatch, lambda: _Response(read_raises=read_timeout))
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError, match="NVIDIA NIM connection timed out") as excinfo:
        provider.complete(_request())
    assert excinfo.value.__cause__ is read_timeout
    assert len(calls) == 1


def test_the_timeout_message_carries_no_credential_endpoint_or_request_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_urlopen(monkeypatch, lambda: _Response(read_raises=TimeoutError("x")))
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError) as excinfo:
        provider.complete(_request())
    message = str(excinfo.value)
    assert message == "NVIDIA NIM connection timed out"
    for leaked in (
        SENTINEL_KEY,
        REQUEST_BODY_MARKER,
        "Bearer",
        "Authorization",
        "nvapi-",
        "https://",
    ):
        assert leaked not in message, leaked
    del calls


def test_a_timeout_is_reported_as_a_timeout_and_not_as_a_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TimeoutError is a sibling of URLError under OSError, not a subclass of it."""
    assert not issubclass(TimeoutError, urllib.error.URLError)
    _patch_urlopen(monkeypatch, lambda: _Response(read_raises=TimeoutError("x")))
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError) as excinfo:
        provider.complete(_request())
    assert "connection failed" not in str(excinfo.value)


def test_a_timeout_wrapped_in_a_url_error_still_reports_as_a_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-existing path, unchanged: urllib sometimes wraps a connect timeout itself."""

    def raise_wrapped() -> object:
        raise urllib.error.URLError(TimeoutError("timed out"))

    _patch_urlopen(monkeypatch, raise_wrapped)
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError, match="NVIDIA NIM connection failed"):
        provider.complete(_request())


def test_http_error_behaviour_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_http() -> object:
        raise urllib.error.HTTPError("https://example.invalid/v1", 503, "busy", {}, None)  # type: ignore[arg-type]

    calls = _patch_urlopen(monkeypatch, raise_http)
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError, match="NVIDIA NIM HTTP error: 503") as excinfo:
        provider.complete(_request())
    assert isinstance(excinfo.value.__cause__, urllib.error.HTTPError)
    assert len(calls) == 1


def test_url_error_behaviour_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_url() -> object:
        raise urllib.error.URLError("name resolution failed")

    calls = _patch_urlopen(monkeypatch, raise_url)
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError, match="name resolution failed") as excinfo:
        provider.complete(_request())
    assert isinstance(excinfo.value.__cause__, urllib.error.URLError)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "behaviour",
    [
        "open_timeout",
        "read_timeout",
        "http_error",
        "url_error",
    ],
)
def test_no_transport_failure_is_ever_retried(
    monkeypatch: pytest.MonkeyPatch, behaviour: str
) -> None:
    """One request in, one attempt out. Retrying would hide transport evidence."""

    def act() -> object:
        if behaviour == "open_timeout":
            raise TimeoutError("timed out")
        if behaviour == "read_timeout":
            return _Response(read_raises=TimeoutError("timed out"))
        if behaviour == "http_error":
            raise urllib.error.HTTPError("https://example.invalid/v1", 500, "e", {}, None)  # type: ignore[arg-type]
        raise urllib.error.URLError("unreachable")

    calls = _patch_urlopen(monkeypatch, act)
    provider = _provider(monkeypatch)
    with pytest.raises(ModelProviderError):
        provider.complete(_request())
    assert len(calls) == 1


def test_a_successful_response_is_unaffected_by_the_timeout_clause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = json.dumps(
        {"id": "chatcmpl-test", "choices": [{"message": {"content": '{"candidates":[]}'}}]}
    ).encode()
    calls = _patch_urlopen(monkeypatch, lambda: _Response(body))
    provider = _provider(monkeypatch)
    response = provider.complete(_request())
    assert response.provider == "nvidia-nim"
    assert response.content == '{"candidates":[]}'
    assert response.request_id == "chatcmpl-test"
    assert len(calls) == 1


def test_the_adapter_declares_no_retry_machinery(repo_root: Path) -> None:
    source = (repo_root / "src/oic/nvidia_nim.py").read_text(encoding="utf-8")
    for forbidden in ("retry", "retries", "backoff", "attempt", "while True", "for _ in range"):
        assert forbidden not in source, forbidden
