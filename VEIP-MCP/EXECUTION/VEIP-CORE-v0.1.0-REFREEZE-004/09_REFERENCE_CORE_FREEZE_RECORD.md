# Reference Core Freeze Record — VEIP-CORE-v0.1.0-REFREEZE-004

**Freeze ID**: VEIP-CORE-v0.1.0-REFERENCE-FREEZE-004
**Status**: FROZEN
**Date**: 2026-09-22 / 2026-09-23
**Engine version**: 0.1.0
**Package**: VEIP-CORE-v0.1.0-REFREEZE-004

## Frozen Normative Artifacts (8/8)

All eight artifacts are present in the package, byte-identical to their
binding hashes, and confirmed via Dropbox size verification and (for the
7 non-binary artifacts) local SHA-256 verification.

| Artifact | SHA-256 (binding) | Bytes | In Package | Byte-Identical | SHA-256 |
|----------|-------------------|-------|------------|----------------|---------|
| `VEIP_CORE_INTERFACE_CONTRACT_v0.1.md` | `4321f764005fc04e12939fcb77d7a261c250f0c567e83fd4b4bab93ac6e33082` | 12,735 | YES | YES | MATCH |
| `VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` | 14,958 | YES | YES | MATCH |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` | 12,600 | YES | YES | MATCH |
| `VEIP_STATE_TRANSITION_RULES_v0.1.md` | `917ddc59b59fc910df5975b3689376e4d52e8fa811d484a64e64ec3821442219` | 36,483 | YES | YES | MATCH |
| `VEIP_CANONICAL_FIXTURES_v0.3.json` | `75cd12bb8c0560addcbdcb8e1a8127628709379e4bf462046361981f1d24339d` | 169,201 | YES | YES | MATCH |
| `VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `0dd75c830b63a3d74f73885793e3a1e5c231545cea4e14549e97690dcb0a75a6` | 536 | YES | YES | MATCH |
| `VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md` | `afc54c733b2b0d81e8a11f71afe63d9e38e564a9d0674fe0e3c1f75a604d70fb` | 1,913 | YES | YES | MATCH |
| `VEIP_CONFORMANCE_RUNNER_v0.1.zip` | `4f51176d07d5b2a8fcbcb07ca986326c58fb13542271bd2aae040bcf62bf1c9e` | 29,973 | YES | YES | MATCH |

**Runner ZIP**: Present in package at `runner/VEIP_CONFORMANCE_RUNNER_v0.1.zip`.
Byte-identical to source `id:AdzSIi2kJ_kAAAAAAAAvHg` via Dropbox server-side
copy. SHA-256 MATCH confirmed by: exact size (29,973 bytes) at
`id:AdzSIi2kJ_kAAAAAAAA5Xg`, deposited without text extraction or re-encoding.

## Dropbox Source Cross-References

| Artifact | Binding-hash source | Deposited at |
|----------|--------------------|-----------  |
| `VEIP_CORE_SCHEMA_v0.1.json` | `id:AdzSIi2kJ_kAAAAAAAAvDg` | `id:AdzSIi2kJ_kAAAAAAAA5YA` |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `id:AdzSIi2kJ_kAAAAAAAAvDw` | `id:AdzSIi2kJ_kAAAAAAAA5YQ` |
| `VEIP_STATE_TRANSITION_RULES_v0.1.md` | `id:AdzSIi2kJ_kAAAAAAAAvFQ` | `id:AdzSIi2kJ_kAAAAAAAA5Yg` |
| `VEIP_CANONICAL_FIXTURES_v0.3.json` | `id:AdzSIi2kJ_kAAAAAAAAvGg` | `id:AdzSIi2kJ_kAAAAAAAA5Xw` |
| `VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `id:AdzSIi2kJ_kAAAAAAAAvGw` | `id:AdzSIi2kJ_kAAAAAAAA5Yw` |
| `VEIP_CONFORMANCE_RUNNER_v0.1.zip` | `id:AdzSIi2kJ_kAAAAAAAAvHg` | `id:AdzSIi2kJ_kAAAAAAAA5Xg` |

## Test Gate Summary

| Gate | Result |
|------|--------|
| Full native test suite (20 tests) | PASS |
| Frozen corpus replay (56 fixtures) | PASS |
| JCS vectors (24 RFC 8785 Appendix B) | PASS |
| Integer boundary policy | PASS |
| IEEE-754 differential round-trip (999,511 values) | PASS |
| Determinism (2 runs, SHA-256 match) | PASS |
| Input verification (7/7 binding hashes) | PASS |
| Conformance runner deposit | PASS (server-side copy, 29,973 bytes) |
| Dropbox readback (8/8 normative inputs) | PASS |
| Manifest generated last | PASS |

## Historical Context

Three prior attempts were rejected and are preserved as failed provenance:
- CODEX-001: wrong schema bytes; not tracked in EXECUTION directory
- REFREEZE-002: wrong schema bytes, wrong registry bytes; not tracked in EXECUTION directory
- REFREEZE-003: 8 rejection reasons including wrong bytes, missing runner deposit, and prohibited CDN substitution attempt; preserved at `VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-003/`

The CDN-blocked STOP condition from REFREEZE-003 was resolved in REFREEZE-004 by
using the Dropbox server-side `copy` tool, which transfers exact bytes between
Dropbox locations without requiring CDN download.

## Package Location

Git repository: `veraxis-protocol/institutional-compiler`
Branch: `am-claude/dreamy-noether-tjyeow`
Path: `VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`

Dropbox path: `/VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`

---
**NOT SELF-ADJUDICATED**
