from __future__ import annotations

import json

import pytest

from veip_trace_harness import EventKind, TraceParseError, canonical_bytes, canonical_sha256, parse_trace_jsonl
from veip_trace_harness.hashing import sha256_bytes
from veip_trace_harness.timeutil import InvalidTimestamp, parse_rfc3339
from conftest import custom_span, span_record

TRACE_ID = "trace_0123456789abcdef0123456789abcdef"


def minimum_records():
    return [
        custom_span(
            span_id="span_request",
            name="veip.user_request_received",
            seq=1,
            at="2026-09-22T18:00:00Z",
            data={"text": "Deploy version abc123"},
        ),
        span_record(span_id="span_native", ended_at="2026-09-22T18:00:01Z"),
        custom_span(
            span_id="span_evidence",
            name="veip.evidence_available",
            seq=2,
            at="2026-09-22T18:00:02Z",
            data={
                "source_system": "deployment-api",
                "source_native_id": "deploy-42",
                "payload_sha256": "a" * 64,
                "status": "accepted",
            },
        ),
        custom_span(
            span_id="span_claim",
            name="veip.user_claim_emitted",
            seq=3,
            at="2026-09-22T18:00:03Z",
            data={"text": "Deployment request accepted."},
        ),
    ]


def test_source_file_hash_matches_exact_bytes(write_jsonl):
    path = write_jsonl(minimum_records())
    parsed = parse_trace_jsonl(path)
    assert parsed.source_file_sha256 == sha256_bytes(path.read_bytes())


def test_each_record_hash_preserves_exact_jsonl_record_bytes(write_jsonl):
    path = write_jsonl(minimum_records())
    parsed = parse_trace_jsonl(path)
    lines = path.read_bytes().splitlines(keepends=True)
    for event in parsed.events:
        idx = event.source_ref.record_index
        assert event.source_ref.raw_record_sha256 == sha256_bytes(lines[idx])


def test_parser_is_deterministic_and_canonical_output_byte_identical(write_jsonl):
    path = write_jsonl(minimum_records())
    a = parse_trace_jsonl(path)
    b = parse_trace_jsonl(path)
    assert canonical_bytes(a) == canonical_bytes(b)
    assert canonical_sha256(a) == canonical_sha256(b)


def test_native_span_is_not_agent_visible_evidence(write_jsonl):
    path = write_jsonl(minimum_records())
    parsed = parse_trace_jsonl(path)
    native = next(e for e in parsed.events if e.kind is EventKind.NATIVE_SPAN)
    assert native.agent_visible is False
    assert native.event_seq is None


def test_evidence_marker_is_explicit_agent_visible_evidence(write_jsonl):
    path = write_jsonl(minimum_records())
    parsed = parse_trace_jsonl(path)
    event = next(e for e in parsed.events if e.kind is EventKind.EVIDENCE_AVAILABLE)
    assert event.agent_visible is True
    assert event.event_seq == 2


def test_undocumented_wrapper_shape_is_rejected(tmp_path):
    record = {"item": minimum_records()[0]}
    path = tmp_path / "wrapped.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(TraceParseError, match="expected trace.span"):
        parse_trace_jsonl(path)


def test_non_span_object_is_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"object": "trace", "id": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(TraceParseError, match="expected trace.span"):
        parse_trace_jsonl(path)


def test_invalid_json_fails_closed(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_bytes(b'{"object":"trace.span"\n')
    with pytest.raises(TraceParseError, match="invalid JSON"):
        parse_trace_jsonl(path)


def test_duplicate_span_id_rejected(write_jsonl):
    records = minimum_records()
    records.append(span_record(span_id="span_native"))
    path = write_jsonl(records)
    with pytest.raises(TraceParseError, match="duplicate span id"):
        parse_trace_jsonl(path)


def test_duplicate_veip_event_seq_rejected(write_jsonl):
    records = minimum_records()
    records[-1] = custom_span(
        span_id="span_claim",
        name="veip.user_claim_emitted",
        seq=2,
        at="2026-09-22T18:00:03Z",
        data={"text": "Done"},
    )
    path = write_jsonl(records)
    with pytest.raises(TraceParseError, match="duplicate VEIP event_seq"):
        parse_trace_jsonl(path)


def test_multiple_trace_ids_rejected(write_jsonl):
    records = minimum_records()
    records.append(span_record(span_id="span_other", trace_id="trace_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))
    path = write_jsonl(records)
    with pytest.raises(TraceParseError, match="exactly one trace_id"):
        parse_trace_jsonl(path)


def test_unfinished_native_span_rejected(write_jsonl):
    record = span_record(span_id="span_open")
    record["ended_at"] = None
    path = write_jsonl([record])
    with pytest.raises(TraceParseError, match="unfinished native span"):
        parse_trace_jsonl(path)


def test_naive_timestamp_rejected():
    with pytest.raises(InvalidTimestamp, match="naive timestamps"):
        parse_rfc3339("2026-09-22T18:00:00")


def test_offset_timestamp_normalizes_deterministically(write_jsonl):
    records = minimum_records()
    records[0] = custom_span(
        span_id="span_request",
        name="veip.user_request_received",
        seq=1,
        at="2026-09-22T14:00:00-04:00",
        data={"text": "Deploy version abc123"},
    )
    path = write_jsonl(records)
    parsed = parse_trace_jsonl(path)
    raw = canonical_bytes(parsed)
    assert b"2026-09-22T18:00:00.000000Z" in raw
