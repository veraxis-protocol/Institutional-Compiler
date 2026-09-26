from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from probe.openai_agents_0_22_3_export_contract import (  # noqa: E402
    CustomSpanData,
    FunctionSpanData,
    SpanImplExportFixture,
)
from veip_trace_harness import canonical_bytes, canonical_sha256, parse_trace_jsonl, reconstruct_claim_snapshot  # noqa: E402

TRACE_ID = "trace_0123456789abcdef0123456789abcdef"
START = "2026-09-22T18:00:00.000000Z"


def span(span_id, ended_at, data):
    return SpanImplExportFixture(
        trace_id=TRACE_ID,
        span_id=span_id,
        parent_id=None,
        started_at=START,
        ended_at=ended_at,
        span_data=data,
    ).export()


def c(name, seq, at, **data):
    return span(
        f"span_{seq}",
        at,
        CustomSpanData(name=name, data={"event_seq": seq, "observed_at": at, **data}),
    )


def main():
    records = [
        c("veip.user_request_received", 1, "2026-09-22T18:00:00.000000Z", text="Issue the refund"),
        span(
            "span_native_function",
            "2026-09-22T18:00:01.000000Z",
            FunctionSpanData(name="refund_api", input='{"amount":250}', output={"status":"accepted"}),
        ),
        c(
            "veip.evidence_available", 10, "2026-09-22T18:00:02.000000Z",
            source_system="payment_processor", source_native_id="refund_123",
            payload_sha256="a"*64, status="pending",
        ),
        c("veip.user_claim_emitted", 20, "2026-09-22T18:00:05.000000Z", text="The refund is complete."),
        c(
            "veip.evidence_available", 30, "2026-09-22T18:20:00.000000Z",
            source_system="payment_processor", source_native_id="refund_123_update",
            payload_sha256="b"*64, status="succeeded",
        ),
    ]

    raw = b"".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n" for r in records)
    fixture_dir = ROOT / "tests" / "fixtures" / "openai_agents_release_source_v0_22_3"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    trace_path = fixture_dir / "sdk_export_probe.jsonl"
    trace_path.write_bytes(raw)

    parsed1 = parse_trace_jsonl(trace_path)
    snap1 = reconstruct_claim_snapshot(parsed1)
    parsed2 = parse_trace_jsonl(trace_path)
    snap2 = reconstruct_claim_snapshot(parsed2)

    normalized1 = canonical_bytes(parsed1)
    normalized2 = canonical_bytes(parsed2)
    assert normalized1 == normalized2
    assert canonical_sha256(parsed1) == canonical_sha256(parsed2)
    assert [e.payload.get("status") for e in snap1.evidence_at_claim] == ["pending"]
    assert [e.payload.get("status") for e in snap1.evidence_after_claim] == ["succeeded"]
    assert all(not e.agent_visible for e in parsed1.events if e.kind.value == "native_span")

    result = {
        "probe": "OPENAI_AGENTS_0_22_3_RELEASE_SOURCE_EXPORT_COMPATIBILITY",
        "sdk_version": "0.22.3",
        "publishing_commit": "fdf21db62c303a3db54b0dfbee82de2141fa2799",
        "pypi_wheel_sha256_expected": "41dec9e2e703db32a627bf0290f3721a6ca37405603a8cb654213356dbb8ee9d",
        "upstream_spans_py_blob_sha": "8f564beedb8354f14295868bae54a557b8883892",
        "upstream_span_data_py_blob_sha": "57b7fe6226c99aeb8a97544c49390b9b66961739",
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_sha256": canonical_sha256(parsed1),
        "records": len(records),
        "evidence_at_claim_status": [e.payload.get("status") for e in snap1.evidence_at_claim],
        "evidence_after_claim_status": [e.payload.get("status") for e in snap1.evidence_after_claim],
        "parser_result": "PASS",
        "determinism_result": "PASS",
        "installed_live_sdk_result": "NOT_EXECUTED_ENVIRONMENT_BLOCKED",
        "h1_freeze_disposition": "NOT_FROZEN",
    }
    out = ROOT / "H1_RELEASE_SOURCE_COMPATIBILITY_RESULT_2026-09-22.json"
    out.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
