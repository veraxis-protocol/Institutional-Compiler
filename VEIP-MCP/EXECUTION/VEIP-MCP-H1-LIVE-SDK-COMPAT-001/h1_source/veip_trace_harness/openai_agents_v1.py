from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import TraceParseError
from .hashing import sha256_bytes
from .models import CanonicalEvent, EventKind, ParsedTrace, SourceRef
from .timeutil import InvalidTimestamp, parse_rfc3339

SOURCE_FORMAT = "OPENAI_AGENTS_SPAN_EXPORT_JSONL_V1"

VEIP_CUSTOM_EVENTS: dict[str, EventKind] = {
    "veip.user_request_received": EventKind.USER_REQUEST,
    "veip.evidence_available": EventKind.EVIDENCE_AVAILABLE,
    "veip.user_claim_emitted": EventKind.USER_CLAIM,
    "veip.independent_state_observed": EventKind.INDEPENDENT_STATE,
}


def _require_nonempty_string(value: Any, label: str, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise TraceParseError(f"record {index}: {label} must be a non-empty string")
    return value


def _parse_time(value: Any, label: str, index: int):
    if not isinstance(value, str):
        raise TraceParseError(f"record {index}: {label} must be a timestamp string")
    try:
        return parse_rfc3339(value)
    except InvalidTimestamp as exc:
        raise TraceParseError(f"record {index}: invalid {label}: {exc}") from exc


def _parse_veip_event(
    *,
    item: dict[str, Any],
    span_data: dict[str, Any],
    kind: EventKind,
    index: int,
    raw_hash: str,
    source_file_sha256: str,
) -> CanonicalEvent:
    data = span_data.get("data")
    if not isinstance(data, dict):
        raise TraceParseError(f"record {index}: VEIP custom span requires data object")

    seq = data.get("event_seq")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        raise TraceParseError(f"record {index}: event_seq must be a non-negative integer")

    observed_at = _parse_time(data.get("observed_at"), "observed_at", index)

    if kind is EventKind.USER_CLAIM:
        _require_nonempty_string(data.get("text"), "claim text", index)
    elif kind is EventKind.USER_REQUEST:
        _require_nonempty_string(data.get("text"), "request text", index)
    elif kind is EventKind.EVIDENCE_AVAILABLE:
        _require_nonempty_string(data.get("source_system"), "source_system", index)
        _require_nonempty_string(data.get("source_native_id"), "source_native_id", index)
        _require_nonempty_string(data.get("payload_sha256"), "payload_sha256", index)

    source_system = data.get("source_system", "instrumented_host")
    if not isinstance(source_system, str) or not source_system:
        raise TraceParseError(f"record {index}: invalid source_system")

    return CanonicalEvent(
        event_id=item["id"],
        trace_id=item["trace_id"],
        event_seq=seq,
        kind=kind,
        observed_at=observed_at,
        source_system=source_system,
        agent_visible=(kind is EventKind.EVIDENCE_AVAILABLE),
        payload=data,
        source_ref=SourceRef(
            source_file_sha256=source_file_sha256,
            raw_record_sha256=raw_hash,
            record_index=index,
            native_id=item["id"],
        ),
    )


def parse_trace_jsonl(path: Path) -> ParsedTrace:
    """Parse exactly one JSONL stream of OpenAI Agents SDK Span.export() records.

    H1 deliberately accepts no undocumented wrapper shape. Every nonblank record
    must itself be a trace.span export.
    """
    raw_file = path.read_bytes()
    if not raw_file:
        raise TraceParseError("trace file is empty")

    source_file_sha256 = sha256_bytes(raw_file)
    events: list[CanonicalEvent] = []
    trace_ids: set[str] = set()
    span_ids: set[str] = set()
    veip_event_seqs: set[int] = set()

    for index, raw_line in enumerate(raw_file.splitlines(keepends=True)):
        if not raw_line.strip():
            continue
        raw_hash = sha256_bytes(raw_line)

        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise TraceParseError(f"record {index}: invalid JSON") from exc

        if not isinstance(item, dict):
            raise TraceParseError(f"record {index}: JSON record must be an object")
        if item.get("object") != "trace.span":
            raise TraceParseError(f"record {index}: unsupported object; expected trace.span")

        span_id = _require_nonempty_string(item.get("id"), "span id", index)
        trace_id = _require_nonempty_string(item.get("trace_id"), "trace id", index)
        if span_id in span_ids:
            raise TraceParseError(f"record {index}: duplicate span id {span_id}")
        span_ids.add(span_id)
        trace_ids.add(trace_id)

        span_data = item.get("span_data")
        if not isinstance(span_data, dict):
            raise TraceParseError(f"record {index}: span_data must be an object")

        if span_data.get("type") == "custom" and span_data.get("name") in VEIP_CUSTOM_EVENTS:
            event = _parse_veip_event(
                item=item,
                span_data=span_data,
                kind=VEIP_CUSTOM_EVENTS[span_data["name"]],
                index=index,
                raw_hash=raw_hash,
                source_file_sha256=source_file_sha256,
            )
            assert event.event_seq is not None
            if event.event_seq in veip_event_seqs:
                raise TraceParseError(f"record {index}: duplicate VEIP event_seq {event.event_seq}")
            veip_event_seqs.add(event.event_seq)
            events.append(event)
            continue

        ended_at = item.get("ended_at")
        if ended_at is None:
            raise TraceParseError(f"record {index}: unfinished native span")

        event = CanonicalEvent(
            event_id=span_id,
            trace_id=trace_id,
            event_seq=None,
            kind=EventKind.NATIVE_SPAN,
            observed_at=_parse_time(ended_at, "ended_at", index),
            source_system="openai_agents_sdk",
            agent_visible=False,
            payload=item,
            source_ref=SourceRef(
                source_file_sha256=source_file_sha256,
                raw_record_sha256=raw_hash,
                record_index=index,
                native_id=span_id,
            ),
        )
        events.append(event)

    if not events:
        raise TraceParseError("trace contains no supported records")
    if len(trace_ids) != 1:
        raise TraceParseError(f"expected exactly one trace_id, found {sorted(trace_ids)}")

    return ParsedTrace(
        trace_id=next(iter(trace_ids)),
        events=tuple(events),
        source_file_sha256=source_file_sha256,
        source_format=SOURCE_FORMAT,
    )
