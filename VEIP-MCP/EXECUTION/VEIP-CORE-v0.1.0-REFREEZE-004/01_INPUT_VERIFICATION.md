# Input Verification — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0
**Result**: ALL 7 INPUTS VERIFIED

All SHA-256 hashes were verified against the binding hashes specified in the
work order before any file was used.

## Verified Inputs

| File | Expected SHA-256 | Bytes | Encoding | Status |
|------|-----------------|-------|----------|--------|
| `VEIP_CORE_INTERFACE_CONTRACT_v0.1.md` | `4321f764005fc04e12939fcb77d7a261c250f0c567e83fd4b4bab93ac6e33082` | 12,735 | LF | VERIFIED |
| `VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` | 14,958 | CRLF | VERIFIED |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` | 12,600 | CRLF | VERIFIED |
| `VEIP_STATE_TRANSITION_RULES_v0.1.md` | `917ddc59b59fc910df5975b3689376e4d52e8fa811d484a64e64ec3821442219` | 36,483 | LF | VERIFIED |
| `VEIP_CANONICAL_FIXTURES_v0.3.json` | `75cd12bb8c0560addcbdcb8e1a8127628709379e4bf462046361981f1d24339d` | 169,201 | LF | VERIFIED |
| `VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `0dd75c830b63a3d74f73885793e3a1e5c231545cea4e14549e97690dcb0a75a6` | 536 | LF | VERIFIED |
| `VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md` | `afc54c733b2b0d81e8a11f71afe63d9e38e564a9d0674fe0e3c1f75a604d70fb` | 1,913 | LF | VERIFIED |

## CRLF Reconstruction Note

`VEIP_CORE_SCHEMA_v0.1.json` and `VEIP_REASON_CODE_REGISTRY_v0.1.json` are
stored in Dropbox with CRLF line endings. The Dropbox `fetch` MCP tool strips
CR bytes from text extraction and adds exactly one trailing LF. The exact
byte recovery algorithm is:

1. Receive raw bytes from Dropbox `fetch` tool
2. Strip exactly the one trailing `\n` appended by the fetch tool
3. Convert all remaining `\n` bytes to `\r\n`
4. Verify SHA-256 against binding hash

This algorithm was validated prior to writing the files. See
`06_INTEGRITY_AUDIT.md` for full details.

## Dropbox Source References

| File | Dropbox File ID | Dropbox Path |
|------|----------------|--------------|
| `VEIP_CORE_SCHEMA_v0.1.json` | `id:AdzSIi2kJ_kAAAAAAAAvDg` | `/VEIP-MCP/VEIP_CORE_SCHEMA_v0.1.json` |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `id:AdzSIi2kJ_kAAAAAAAAvDw` | `/VEIP-MCP/VEIP_REASON_CODE_REGISTRY_v0.1.json` |
| `VEIP_STATE_TRANSITION_RULES_v0.1.md` | `id:AdzSIi2kJ_kAAAAAAAAvFQ` | `/VEIP-MCP/VEIP_STATE_TRANSITION_RULES_v0.1.md` |
| `VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `id:AdzSIi2kJ_kAAAAAAAAvGw` | `/VEIP-MCP/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` |
| `VEIP_CANONICAL_FIXTURES_v0.3.json` | `id:AdzSIi2kJ_kAAAAAAAAvGg` | `/VEIP-MCP/VEIP_CANONICAL_FIXTURES_v0.3.json` |

**Note**: The correct schema and registry source files are at the
`/VEIP-MCP/` root path, NOT at `/VEIP-MCP/EXECUTION/`. The EXECUTION
directory contains a different (wrong-version) copy of these files.

---
**NOT SELF-ADJUDICATED**
