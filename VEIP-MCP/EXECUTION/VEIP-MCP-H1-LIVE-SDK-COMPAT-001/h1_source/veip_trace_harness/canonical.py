from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from enum import Enum
from typing import Any

from .hashing import sha256_bytes
from .timeutil import canonical_rfc3339


def _primitive(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _primitive(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, datetime):
        return canonical_rfc3339(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value type: {type(value)!r}")


def canonical_bytes(value: Any) -> bytes:
    primitive = _primitive(value)
    text = json.dumps(
        primitive,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))
