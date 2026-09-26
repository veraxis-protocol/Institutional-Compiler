"""Host-side marker contract for H1.

This module is intentionally SDK-independent. It defines the data payloads the
host must place in OpenAI Agents SDK custom spans. Actual `custom_span(...)`
integration belongs in the instrumented host application.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def user_request_marker(*, event_seq: int, text: str, observed_at: str) -> dict[str, Any]:
    return {"event_seq": event_seq, "observed_at": observed_at, "text": text}


def evidence_available_marker(
    *, event_seq: int, observed_at: str, source_system: str,
    source_native_id: str, payload_sha256: str,
) -> dict[str, Any]:
    return {
        "event_seq": event_seq,
        "observed_at": observed_at,
        "source_system": source_system,
        "source_native_id": source_native_id,
        "payload_sha256": payload_sha256,
    }


def user_claim_marker(*, event_seq: int, text: str, observed_at: str) -> dict[str, Any]:
    return {"event_seq": event_seq, "observed_at": observed_at, "text": text}


def independent_state_marker(
    *, event_seq: int, observed_at: str, source_system: str, payload_sha256: str,
) -> dict[str, Any]:
    return {
        "event_seq": event_seq,
        "observed_at": observed_at,
        "source_system": source_system,
        "payload_sha256": payload_sha256,
    }
