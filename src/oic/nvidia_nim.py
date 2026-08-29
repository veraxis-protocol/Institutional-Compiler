"""NVIDIA NIM provider adapter for bounded OIC model assistance.

The adapter speaks the OpenAI-compatible NIM chat-completions API directly with the
Python standard library. No NVIDIA credential is ever persisted by this module.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from oic.model_provider import JsonObject, ModelProviderError, ModelRequest, ModelResponse

DEFAULT_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NIM_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(frozen=True, slots=True)
class NvidiaNimConfig:
    """Connection configuration for hosted or loopback self-hosted NIM."""

    model: str = DEFAULT_NIM_MODEL
    base_url: str = DEFAULT_NIM_BASE_URL
    api_key: str | None = None
    api_key_env: str = "NVIDIA_API_KEY"
    timeout_seconds: float = 60.0

    def resolved_api_key(self) -> str:
        """Resolve the credential from explicit configuration or the environment."""
        key = self.api_key or os.environ.get(self.api_key_env)
        if key is None or not key.strip():
            raise ModelProviderError(
                f"NVIDIA NIM credential is missing; set {self.api_key_env} in the local environment"
            )
        return key.strip()

    def validate_endpoint(self) -> None:
        """Require TLS for remote NIM endpoints; allow HTTP only on loopback."""
        parsed = urlsplit(self.base_url)
        if parsed.scheme == "https":
            return
        if parsed.scheme == "http" and parsed.hostname in _LOOPBACK_HOSTS:
            return
        raise ModelProviderError(
            "NVIDIA NIM base_url must use https unless it targets a loopback self-hosted endpoint"
        )


def build_chat_payload(request: ModelRequest, *, model: str) -> JsonObject:
    """Build the deterministic NIM request body used by the adapter."""
    payload: JsonObject = {
        "model": model,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if request.response_format is not None:
        payload["response_format"] = request.response_format
    return payload


class NvidiaNimProvider:
    """Replaceable NVIDIA NIM implementation of the OIC model-provider boundary."""

    provider_name = "nvidia-nim"

    def __init__(self, config: NvidiaNimConfig | None = None) -> None:
        self.config = config or NvidiaNimConfig()
        self.config.validate_endpoint()

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Submit one bounded request and return literal provider output."""
        api_key = self.config.resolved_api_key()
        body = json.dumps(
            build_chat_payload(request, model=self.config.model),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        http_request = urllib.request.Request(  # noqa: S310 - endpoint is validated above
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 - endpoint is validated above
                http_request, timeout=self.config.timeout_seconds
            ) as response:
                raw_bytes = response.read()
        except urllib.error.HTTPError as exc:
            raise ModelProviderError(f"NVIDIA NIM HTTP error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"NVIDIA NIM connection failed: {exc.reason}") from exc

        try:
            decoded: Any = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelProviderError("NVIDIA NIM returned a non-JSON response") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError("NVIDIA NIM response root is not a JSON object")
        request_id_value = decoded.get("id")
        return ModelResponse(
            provider=self.provider_name,
            model=self.config.model,
            content=_extract_content(decoded),
            request_id=request_id_value if isinstance(request_id_value, str) else None,
            raw=decoded,
        )


def _extract_content(payload: JsonObject) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelProviderError("NVIDIA NIM response has no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ModelProviderError("NVIDIA NIM first choice is not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ModelProviderError("NVIDIA NIM first choice has no message object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ModelProviderError("NVIDIA NIM message content is empty")
    return content
