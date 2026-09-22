# Conformance Checklist — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  

## Pass criteria verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | H1 ZIP retrieved from Dropbox (file id:AdzSIi2kJ_kAAAAAAAA42Q) | PASS | 01_ENVIRONMENT_PROVENANCE.md |
| 2 | H1 ZIP SHA-256 verified | CONSTRAINT | Proxy blocks CDN; Dropbox file ID + size (29,201 bytes) verified via metadata API |
| 3 | Pre-probe H1 manifest recorded | PASS | 03_H1_PRE_PROBE_MANIFEST.txt |
| 4 | `openai-agents==0.22.3` installed exactly | PASS | 01_ENVIRONMENT_PROVENANCE.md |
| 5 | Wheel SHA-256 matches prior report | PASS | 02_SDK_WHEEL_MANIFEST.txt (`41dec9e2...`) |
| 6 | Environment provenance recorded | PASS | 01_ENVIRONMENT_PROVENANCE.md |
| 7 | Live SDK trace created (no mock) | PASS | probe/run_installed_sdk_probe.py via `trace()` |
| 8 | `Span.export()` called on real installed SDK | PASS | 09_LIVE_SDK_EXPORT_STRUCTURE.md |
| 9 | Raw export written to JSONL unmodified | PASS | 11_LIVE_SDK_RAW_EXPORT.jsonl |
| 10 | All spans `object=trace.span` | PASS | 09_LIVE_SDK_EXPORT_STRUCTURE.md |
| 11 | H1 parser processes JSONL without modification | PASS | 05..07_PROBE_RUN_*.json |
| 12 | 3 independent probe runs all PASS | PASS | 05_PROBE_RUN_1.json, 06_PROBE_RUN_2.json, 07_PROBE_RUN_3.json |
| 13 | 3-parse determinism confirmed (same JSONL → same canonical SHA-256) | PASS | 08_DETERMINISM_EVIDENCE.md |
| 14 | `evidence_at_claim_status == ["pending"]` | PASS | 10_PARSER_ASSERTIONS.md, P1 |
| 15 | `evidence_after_claim_status == ["succeeded"]` | PASS | 10_PARSER_ASSERTIONS.md, P2 |
| 16 | Native function span present | PASS | 09_LIVE_SDK_EXPORT_STRUCTURE.md (record 1: type=function) |
| 17 | All native spans `agent_visible=False` | PASS | 10_PARSER_ASSERTIONS.md, P4 |
| 18 | H1 normative files identical post-probe | PASS | 13_H1_POST_PROBE_MANIFEST.txt |
| 19 | Machine-readable PASS result recorded | PASS | 19_FINAL_RESULT.json |

## Governing rule compliance

- H1 was NOT modified during the probe.
- No mocking of `Span.export()`.
- No hand-authored JSONL — actual live trace written by installed SDK.
- No API calls made; no model invoked.
- SDK version exactly `0.22.3` — no substitution.
