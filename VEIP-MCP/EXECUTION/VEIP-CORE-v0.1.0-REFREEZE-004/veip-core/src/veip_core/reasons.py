"""Frozen reason registry access."""

from __future__ import annotations

from importlib.resources import files
import json
from typing import Any


def _load() -> dict[str, dict[str, Any]]:
    resource = files("veip_core").joinpath("data/VEIP_REASON_CODE_REGISTRY_v0.1.json")
    document = json.loads(resource.read_text(encoding="utf-8"))
    return {item["code"]: item for item in document["reason_codes"]}


REGISTRY = _load()
RESERVED_CODES = frozenset(
    code for code, item in REGISTRY.items() if item["emission_status"] == "RESERVED_NOT_EMITTED"
)
