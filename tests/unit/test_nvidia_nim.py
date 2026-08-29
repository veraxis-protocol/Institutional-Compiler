from __future__ import annotations

import pytest

from oic.model_provider import ModelProviderError, ModelRequest
from oic.nvidia_nim import DEFAULT_NIM_MODEL, NvidiaNimConfig, build_chat_payload


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
