from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def span_record(
    *,
    span_id: str,
    trace_id: str = "trace_0123456789abcdef0123456789abcdef",
    ended_at: str = "2026-09-22T18:00:00Z",
    span_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "object": "trace.span",
        "id": span_id,
        "trace_id": trace_id,
        "parent_id": None,
        "started_at": "2026-09-22T17:59:59Z",
        "ended_at": ended_at,
        "span_data": span_data or {"type": "function", "name": "tool", "input": "{}", "output": "ok", "mcp_data": None},
        "error": None,
    }


def custom_span(
    *,
    span_id: str,
    name: str,
    seq: int,
    at: str,
    data: dict[str, Any] | None = None,
    trace_id: str = "trace_0123456789abcdef0123456789abcdef",
) -> dict[str, Any]:
    payload = {"event_seq": seq, "observed_at": at}
    payload.update(data or {})
    return span_record(
        span_id=span_id,
        trace_id=trace_id,
        ended_at=at,
        span_data={"type": "custom", "name": name, "data": payload},
    )


@pytest.fixture
def write_jsonl(tmp_path: Path):
    def _write(records: list[dict[str, Any]], filename: str = "trace.jsonl") -> Path:
        path = tmp_path / filename
        raw = b"".join(
            json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
            for record in records
        )
        path.write_bytes(raw)
        return path
    return _write
