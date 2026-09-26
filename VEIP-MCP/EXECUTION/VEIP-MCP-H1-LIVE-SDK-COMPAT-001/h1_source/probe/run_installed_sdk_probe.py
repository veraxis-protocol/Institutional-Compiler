"""Final H1 live installed-SDK compatibility probe.

Requires: openai-agents==0.22.3 (or an explicitly reviewed later version).
No model call or API key is required. The script replaces default trace processors
with a local capture processor, emits native/custom spans through the installed SDK,
writes exact Span.export() JSONL bytes, then runs the H1 parser twice.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from veip_trace_harness import canonical_bytes, canonical_sha256, parse_trace_jsonl, reconstruct_claim_snapshot

TRACE_ID = "trace_0123456789abcdef0123456789abcdef"


def main() -> None:
    try:
        import importlib.metadata as metadata
        from agents import custom_span, function_span, set_trace_processors, trace
        from agents.tracing import TracingProcessor
    except Exception as exc:
        raise SystemExit(f"LIVE_SDK_UNAVAILABLE: {type(exc).__name__}: {exc}") from exc

    version = metadata.version("openai-agents")

    class CaptureProcessor(TracingProcessor):
        def __init__(self):
            self.records: list[dict] = []

        def on_trace_start(self, trace):
            pass

        def on_trace_end(self, trace):
            pass

        def on_span_start(self, span):
            pass

        def on_span_end(self, span):
            exported = span.export()
            if exported is not None:
                self.records.append(exported)

        def shutdown(self):
            pass

        def force_flush(self):
            pass

    capture = CaptureProcessor()
    set_trace_processors([capture])

    def emit_custom(name: str, seq: int, **data):
        from datetime import datetime, timezone
        observed_at = datetime.now(timezone.utc).isoformat()
        with custom_span(
            name,
            {"event_seq": seq, "observed_at": observed_at, **data},
        ):
            pass

    with trace("veip-h1-live-sdk-probe", trace_id=TRACE_ID):
        emit_custom("veip.user_request_received", 1, text="Issue the refund")
        with function_span(name="refund_api", input='{"amount":250}', output='{"status":"accepted"}'):
            pass
        emit_custom(
            "veip.evidence_available",
            10,
            source_system="payment_processor",
            source_native_id="refund_123",
            payload_sha256="a" * 64,
            status="pending",
        )
        emit_custom("veip.user_claim_emitted", 20, text="The refund is complete.")
        emit_custom(
            "veip.evidence_available",
            30,
            source_system="payment_processor",
            source_native_id="refund_123_update",
            payload_sha256="b" * 64,
            status="succeeded",
        )

    out_dir = ROOT / "tests" / "fixtures" / "openai_agents_live_sdk"
    out_dir.mkdir(parents=True, exist_ok=True)
    trace_path = out_dir / f"openai_agents_{version}_export.jsonl"
    raw = b"".join(
        json.dumps(r, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        for r in capture.records
    )
    trace_path.write_bytes(raw)

    parsed1 = parse_trace_jsonl(trace_path)
    parsed2 = parse_trace_jsonl(trace_path)
    snap = reconstruct_claim_snapshot(parsed1)

    assert canonical_bytes(parsed1) == canonical_bytes(parsed2)
    assert canonical_sha256(parsed1) == canonical_sha256(parsed2)
    assert [e.payload.get("status") for e in snap.evidence_at_claim] == ["pending"]
    assert [e.payload.get("status") for e in snap.evidence_after_claim] == ["succeeded"]
    assert any(e.kind.value == "native_span" for e in parsed1.events)
    assert all(not e.agent_visible for e in parsed1.events if e.kind.value == "native_span")

    result = {
        "probe": "OPENAI_AGENTS_INSTALLED_SDK_EXPORT_COMPATIBILITY",
        "sdk_version": version,
        "raw_export_sha256": hashlib.sha256(raw).hexdigest(),
        "normalized_sha256": canonical_sha256(parsed1),
        "record_count": len(capture.records),
        "evidence_at_claim_status": [e.payload.get("status") for e in snap.evidence_at_claim],
        "evidence_after_claim_status": [e.payload.get("status") for e in snap.evidence_after_claim],
        "result": "PASS",
    }
    result_path = ROOT / "H1_LIVE_SDK_COMPATIBILITY_RESULT.json"
    result_path.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
