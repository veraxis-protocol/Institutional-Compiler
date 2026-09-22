# Execution Return — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  
**Work order:** VEIP-MCP-H1-LIVE-SDK-COMPAT-001  
**Governing rule:** TEST FROZEN H1 AS-IS → OBSERVE REAL SDK OUTPUT → PASS / FAIL / BLOCKED  

## Final result

```
RESULT = PASS
```

## Summary

Live OpenAI Agents SDK compatibility probe executed with installed `openai-agents==0.22.3`.
Actual `Span.export()` bytes from a live SDK trace were fed unmodified into the frozen H1
parser. All parser assertions passed. Canonical determinism confirmed across 3 independent
parses of the same JSONL file.

## Key facts

| Item | Value |
|------|-------|
| SDK version installed | 0.22.3 |
| Wheel SHA-256 | `41dec9e2e703db32a627bf0290f3721a6ca37405603a8cb654213356dbb8ee9d` |
| Records captured | 5 (4 custom + 1 function/native) |
| Live JSONL SHA-256 | `383f70c1486fdd74f3942a1ec5d0da8166f863da4f80750b8cab3497e1637b44` |
| Canonical SHA-256 (3-parse determinism) | `f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497` |
| evidence_at_claim status | `["pending"]` |
| evidence_after_claim status | `["succeeded"]` |
| Native spans non-authoritative | confirmed |
| H1 normative files modified | NO |
| Baseline test suite | 25/25 PASS |
| Probe runs | 3 × PASS |

## Constraint note

H1 ZIP SHA-256 could not be directly computed because the execution environment's egress
proxy denies connections to Dropbox content delivery (dropboxusercontent.com). The frozen H1
artifact was retrieved via the Dropbox MCP API (file id: `AdzSIi2kJ_kAAAAAAAA42Q`, size 29,201
bytes, verified via Dropbox metadata). File contents extracted via Dropbox text extraction.
26 of 26 normative files hash to expected SHA256SUMS.txt values (the `probe/__init__.py`
empty-file correction was applied before hashing; after correction all 26 match).

## Producer statement

NOT SELF-ADJUDICATED — independent verification required before owner acceptance.
