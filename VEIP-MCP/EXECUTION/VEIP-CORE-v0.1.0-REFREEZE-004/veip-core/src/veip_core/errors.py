"""Frozen VEIP engine-error vocabulary."""

from __future__ import annotations

from typing import Any

ENGINE_VERSION = "0.1.0"
ERROR_CODES = frozenset(
    {
        "SCHEMA_INVALID",
        "ENGINE_VERSION_MISMATCH",
        "DUPLICATE_EVIDENCE_ID",
        "MANIFEST_HASH_MISMATCH",
    }
)


class EngineError(Exception):
    """A non-adjudicative structural or ingestion failure."""

    def __init__(self, error_code: str, message: str, details: dict[str, Any] | None = None):
        if error_code not in ERROR_CODES:
            raise ValueError(f"Unsupported engine error code: {error_code}")
        if not message:
            raise ValueError("EngineError message must be nonempty")
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
            "engine_version": ENGINE_VERSION,
        }
        if self.details is not None:
            result["details"] = self.details
        return result
