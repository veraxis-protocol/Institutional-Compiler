"""RFC 8785 JSON canonicalization and SHA-256 helpers.

Python integers outside the interoperable I-JSON safe-integer domain are rejected
instead of being emitted with arbitrary precision that ECMAScript cannot preserve.
Float support applies ECMAScript thresholds and exponent normalization to Python's
shortest round-trippable representation.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import math
from typing import Any


_MAX_SAFE_INTEGER = 9007199254740991


def _string(value: str) -> str:
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("JCS rejects lone surrogate code points")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _key(value: str) -> bytes:
    return value.encode("utf-16-be")


def _float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("JCS rejects non-finite numbers")
    if value == 0:
        return "0"
    negative = value < 0
    magnitude = -value if negative else value
    shortest = repr(magnitude).lower()
    if 1e-6 <= magnitude < 1e21:
        rendered = format(Decimal(shortest), "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
    else:
        if "e" not in shortest:
            shortest = format(magnitude, ".15e")
        mantissa, exponent = shortest.split("e", 1)
        mantissa = mantissa.rstrip("0").rstrip(".")
        exponent_number = int(exponent)
        sign = "+" if exponent_number >= 0 else "-"
        rendered = f"{mantissa}e{sign}{abs(exponent_number)}"
    return "-" + rendered if negative else rendered


def _integer(value: int) -> str:
    if value < -_MAX_SAFE_INTEGER or value > _MAX_SAFE_INTEGER:
        raise ValueError(f"JCS integer exceeds safe IEEE-754 domain: {value}")
    return str(value)


def dumps(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, int):
        return _integer(value)
    if isinstance(value, float):
        return _float(value)
    if isinstance(value, list):
        return "[" + ",".join(dumps(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        members = []
        for key in sorted(value, key=_key):
            members.append(_string(key) + ":" + dumps(value[key]))
        return "{" + ",".join(members) + "}"
    raise TypeError(f"Unsupported JSON value type: {type(value).__name__}")


def bytes_(value: Any) -> bytes:
    return dumps(value).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(bytes_(value)).hexdigest()
