"""Exact-request replay of locally frozen synthetic output, never a live model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from oic.model_provider import ModelProviderError, ModelRequest, ModelResponse


def request_digest(request: ModelRequest) -> str:
    """Bind all request fields, not just a source fragment or prompt substring."""
    return hashlib.sha256(
        json.dumps(asdict(request), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class FrozenSyntheticProvider:
    """Fail-closed finite replay; credentials and network have no role."""

    def __init__(self, fixture: Path, *, expected_sha256: str) -> None:
        try:
            raw = fixture.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected_sha256:
                raise ModelProviderError("synthetic fixture digest mismatch")
            document = json.loads(raw)
            if not isinstance(document, dict) or set(document) != {"format", "exchanges"}:
                raise ModelProviderError("malformed synthetic fixture")
            exchanges = document["exchanges"]
            if document["format"] != "SYNTHETIC-REPLAY-001" or not isinstance(exchanges, list):
                raise ModelProviderError("malformed synthetic fixture")
            if not exchanges:
                raise ModelProviderError("empty synthetic fixture")
            for entry in exchanges:
                if (
                    not isinstance(entry, dict)
                    or set(entry) != {"request_sha256", "content", "model"}
                    or not all(isinstance(value, str) and value for value in entry.values())
                    or len(entry["request_sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in entry["request_sha256"])
                ):
                    raise ModelProviderError("malformed synthetic exchange")
                if not isinstance(json.loads(entry["content"]), dict):
                    raise ModelProviderError("synthetic response must be an object")
            self._exchanges = exchanges
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModelProviderError("unreadable or malformed synthetic fixture") from exc
        self._position = 0

    @property
    def consumed(self) -> int:
        """Number of successful exact-request replays; not an authority score."""
        return self._position

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return only the next frozen response, or refuse without advancing."""
        if self._position >= len(self._exchanges):
            raise ModelProviderError("synthetic fixture exhausted")
        entry = self._exchanges[self._position]
        if request_digest(request) != entry["request_sha256"]:
            raise ModelProviderError("synthetic request mismatch")
        self._position += 1
        return ModelResponse(
            provider="frozen-synthetic",
            model=entry["model"],
            content=entry["content"],
            request_id=f"synthetic-{self._position}",
            raw={"synthetic": True, "live_model": False},
        )
