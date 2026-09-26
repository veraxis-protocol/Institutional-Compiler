# Live SDK Export Structure — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  
**SDK:** openai-agents==0.22.3  
**JSONL SHA-256:** `383f70c1486fdd74f3942a1ec5d0da8166f863da4f80750b8cab3497e1637b44`  
**Records:** 5  

## Record structure

Each record confirmed to have: `object`, `id`, `trace_id`, `parent_id`, `started_at`, `ended_at`, `span_data`, `error`  
Top-level `object` field: `trace.span` (all records)  

### Record 0: `span_data.type=custom` name=`veip.user_request_received`

- `object`: `trace.span`
- `id`: `span_fbe06b2965eb42b780d9bfb6`
- `trace_id`: `trace_0123456789abcdef0123456789abcdef`
- `parent_id`: `None`
- `span_data.type`: `custom`
- `span_data.name`: `veip.user_request_received`
- `span_data.data` keys: ['event_seq', 'observed_at', 'text']

### Record 1: `span_data.type=function` name=`refund_api`

- `object`: `trace.span`
- `id`: `span_83bab1c8d9ef4f888145d263`
- `trace_id`: `trace_0123456789abcdef0123456789abcdef`
- `parent_id`: `None`
- `span_data.type`: `function`
- `span_data.name`: `refund_api`
- `span_data.input`: `{"amount":250}`
- `span_data.output`: `{"status":"accepted"}`

### Record 2: `span_data.type=custom` name=`veip.evidence_available`

- `object`: `trace.span`
- `id`: `span_239ce82a4859496da7d1bb17`
- `trace_id`: `trace_0123456789abcdef0123456789abcdef`
- `parent_id`: `None`
- `span_data.type`: `custom`
- `span_data.name`: `veip.evidence_available`
- `span_data.data` keys: ['event_seq', 'observed_at', 'source_system', 'source_native_id', 'payload_sha256', 'status']

### Record 3: `span_data.type=custom` name=`veip.user_claim_emitted`

- `object`: `trace.span`
- `id`: `span_5ae0fc61e0ba43ce8cfb022c`
- `trace_id`: `trace_0123456789abcdef0123456789abcdef`
- `parent_id`: `None`
- `span_data.type`: `custom`
- `span_data.name`: `veip.user_claim_emitted`
- `span_data.data` keys: ['event_seq', 'observed_at', 'text']

### Record 4: `span_data.type=custom` name=`veip.evidence_available`

- `object`: `trace.span`
- `id`: `span_321b907404b34f249a01223e`
- `trace_id`: `trace_0123456789abcdef0123456789abcdef`
- `parent_id`: `None`
- `span_data.type`: `custom`
- `span_data.name`: `veip.evidence_available`
- `span_data.data` keys: ['event_seq', 'observed_at', 'source_system', 'source_native_id', 'payload_sha256', 'status']

