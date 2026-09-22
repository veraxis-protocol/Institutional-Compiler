# Parser Assertions — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  
**JSONL source:** `09_LIVE_SDK_EXPORT_STRUCTURE.md` / raw JSONL = `11_LIVE_SDK_RAW_EXPORT.jsonl`

## Assertions verified against live SDK output

| ID | Assertion | Status |
|----|-----------|--------|
| P1 | `evidence_at_claim_status == ["pending"]` | PASS |
| P2 | `evidence_after_claim_status == ["succeeded"]` | PASS |
| P3 | Native span(s) present in parsed events | PASS |
| P4 | All native spans have `agent_visible=False` | PASS |
| P5 | Record count == 5 | PASS |
| P6 | Trace ID == `trace_0123456789abcdef0123456789abcdef` | PASS |
| P7 | Canonical bytes identical across 3 parses of same JSONL | PASS |
| P8 | canonical_sha256 == `f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497` (3 parses) | PASS |

## H1 result JSON (from run 3)

```json
{
  "evidence_after_claim_status": ["succeeded"],
  "evidence_at_claim_status": ["pending"],
  "normalized_sha256": "f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497",
  "probe": "OPENAI_AGENTS_INSTALLED_SDK_EXPORT_COMPATIBILITY",
  "raw_export_sha256": "383f70c1486fdd74f3942a1ec5d0da8166f863da4f80750b8cab3497e1637b44",
  "record_count": 5,
  "result": "PASS",
  "sdk_version": "0.22.3"
}
```
