from __future__ import annotations

import pytest

from veip_trace_harness import TraceNotAdmissible, parse_trace_jsonl, reconstruct_claim_snapshot
from conftest import custom_span, span_record


def request(seq=1, at="2026-09-22T18:00:00Z"):
    return custom_span(
        span_id=f"span_request_{seq}",
        name="veip.user_request_received",
        seq=seq,
        at=at,
        data={"text": "Do the task"},
    )


def evidence(seq, at, status="unknown"):
    return custom_span(
        span_id=f"span_evidence_{seq}",
        name="veip.evidence_available",
        seq=seq,
        at=at,
        data={
            "source_system": "test-system",
            "source_native_id": f"obs-{seq}",
            "payload_sha256": (hex(seq)[2:] * 64)[:64].ljust(64, "0"),
            "status": status,
        },
    )


def claim(seq=20, at="2026-09-22T18:00:05Z", text="Done"):
    return custom_span(
        span_id=f"span_claim_{seq}",
        name="veip.user_claim_emitted",
        seq=seq,
        at=at,
        data={"text": text},
    )


def test_post_claim_evidence_is_excluded(write_jsonl):
    path = write_jsonl([
        request(),
        evidence(10, "2026-09-22T18:00:02Z", "pending"),
        claim(),
        evidence(30, "2026-09-22T18:00:10Z", "succeeded"),
    ])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert [e.event_seq for e in snap.evidence_at_claim] == [10]
    assert [e.event_seq for e in snap.evidence_after_claim] == [30]


def test_later_success_cannot_enter_claim_snapshot(write_jsonl):
    path = write_jsonl([
        request(),
        evidence(10, "2026-09-22T18:00:02Z", "pending"),
        claim(text="The refund is complete."),
        evidence(30, "2026-09-22T18:20:00Z", "succeeded"),
    ])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert [e.payload["status"] for e in snap.evidence_at_claim] == ["pending"]
    assert [e.payload["status"] for e in snap.evidence_after_claim] == ["succeeded"]


def test_native_span_never_enters_e_claim(write_jsonl):
    path = write_jsonl([
        request(),
        span_record(span_id="native_tool", ended_at="2026-09-22T18:00:01Z"),
        claim(),
    ])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert snap.evidence_at_claim == ()


def test_seq_before_but_timestamp_after_is_not_admitted(write_jsonl):
    path = write_jsonl([
        request(),
        evidence(10, "2026-09-22T18:00:06Z", "late-clock"),
        claim(seq=20, at="2026-09-22T18:00:05Z"),
    ])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert snap.evidence_at_claim == ()
    assert [e.event_seq for e in snap.evidence_after_claim] == [10]


def test_timestamp_before_but_seq_after_is_not_admitted(write_jsonl):
    path = write_jsonl([
        request(),
        claim(seq=20, at="2026-09-22T18:00:05Z"),
        evidence(30, "2026-09-22T18:00:04Z", "causally-late"),
    ])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert snap.evidence_at_claim == ()
    assert [e.event_seq for e in snap.evidence_after_claim] == [30]


def test_no_claim_marker_is_not_admissible(write_jsonl):
    path = write_jsonl([request(), evidence(10, "2026-09-22T18:00:02Z")])
    with pytest.raises(TraceNotAdmissible, match="exactly one explicit veip.user_claim_emitted"):
        reconstruct_claim_snapshot(parse_trace_jsonl(path))


def test_multiple_claim_markers_are_not_silently_selected(write_jsonl):
    path = write_jsonl([request(), claim(10), claim(20, "2026-09-22T18:00:06Z")])
    with pytest.raises(TraceNotAdmissible, match="exactly one explicit veip.user_claim_emitted"):
        reconstruct_claim_snapshot(parse_trace_jsonl(path))


def test_no_request_marker_is_not_admissible(write_jsonl):
    path = write_jsonl([claim()])
    with pytest.raises(TraceNotAdmissible, match="exactly one explicit veip.user_request_received"):
        reconstruct_claim_snapshot(parse_trace_jsonl(path))


def test_request_must_precede_claim_in_host_sequence(write_jsonl):
    path = write_jsonl([
        claim(seq=10, at="2026-09-22T18:00:05Z"),
        request(seq=20, at="2026-09-22T18:00:06Z"),
    ])
    with pytest.raises(TraceNotAdmissible, match="causally precede"):
        reconstruct_claim_snapshot(parse_trace_jsonl(path))


def test_empty_evidence_set_is_allowed_and_not_inferred_from_native_spans(write_jsonl):
    path = write_jsonl([request(), claim()])
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(path))
    assert snap.evidence_at_claim == ()
    assert snap.evidence_after_claim == ()
