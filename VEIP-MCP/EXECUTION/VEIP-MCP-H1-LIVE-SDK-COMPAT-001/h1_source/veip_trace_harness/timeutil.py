from __future__ import annotations

from datetime import datetime, timezone


class InvalidTimestamp(ValueError):
    """Timestamp is absent, malformed, or lacks an explicit UTC offset."""


def parse_rfc3339(value: str) -> datetime:
    """Parse an offset-aware RFC3339-like ISO timestamp.

    This removes timezone/offset ambiguity for comparison. It does NOT establish
    synchronization between clocks on different systems.
    """
    if not isinstance(value, str) or not value:
        raise InvalidTimestamp("timestamp must be a non-empty string")

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidTimestamp(f"invalid timestamp: {value}") from exc

    if dt.tzinfo is None or dt.utcoffset() is None:
        raise InvalidTimestamp("naive timestamps are prohibited")
    return dt


def canonical_rfc3339(dt: datetime) -> str:
    """Canonical UTC form with fixed microsecond precision."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise InvalidTimestamp("naive timestamps are prohibited")
    utc = dt.astimezone(timezone.utc)
    return utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
