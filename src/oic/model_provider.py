"""Provider-neutral model boundary for OIC candidate-generation assistance.

Model providers can propose candidate material. They do not establish source authority,
institutional admission, canonical meaning, executable controls, or runtime authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

JsonObject = dict[str, Any]


class ModelProviderError(RuntimeError):
    """Raised when a model provider cannot satisfy a bounded OIC request."""


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """A bounded request to a replaceable model provider."""

    system_prompt: str
    user_prompt: str
    response_format: JsonObject | None = None
    temperature: float = 0.0
    max_tokens: int = 4096


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Provider response plus the minimum provenance needed by OIC."""

    provider: str
    model: str
    content: str
    request_id: str | None
    raw: JsonObject


class ModelProvider(Protocol):
    """Replaceable provider contract. Implementations have no semantic authority."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Return one provider completion without changing OIC state."""
        ...
