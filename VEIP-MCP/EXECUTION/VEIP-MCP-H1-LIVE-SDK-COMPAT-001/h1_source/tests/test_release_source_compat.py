from __future__ import annotations

import json
from pathlib import Path

from probe.openai_agents_0_22_3_export_contract import CustomSpanData, SpanImplExportFixture
from veip_trace_harness import parse_trace_jsonl, reconstruct_claim_snapshot

TRACE_ID = "trace_0123456789abcdef0123456789abcdef"


def export_custom(span_id: str, name: str, seq: int, at: str, **extra):
    return SpanImplExportFixture(
        trace_id=TRACE_ID,
        span_id=span_id,
        parent_id=None,
        started_at=at,
        ended_at=at,
        span_data=CustomSpanData(name=name, data={"event_seq": seq, "observed_at": at, **extra}),
    ).export()


def test_upstream_0_22_3_custom_export_shape_is_accepted(tmp_path: Path):
    records = [
        export_custom("request", "veip.user_request_received", 1, "2026-09-22T18:00:00Z", text="do it"),
        export_custom(
            "evidence", "veip.evidence_available", 2, "2026-09-22T18:00:01Z",
            source_system="native", source_native_id="obs1", payload_sha256="a" * 64, status="pending"
        ),
        export_custom("claim", "veip.user_claim_emitted", 3, "2026-09-22T18:00:02Z", text="done"),
    ]
    p = tmp_path / "trace.jsonl"
    p.write_bytes(b"".join(json.dumps(x, separators=(",", ":")).encode() + b"\n" for x in records))
    snap = reconstruct_claim_snapshot(parse_trace_jsonl(p))
    assert snap.claim.payload["text"] == "done"
    assert [e.payload["status"] for e in snap.evidence_at_claim] == ["pending"]
