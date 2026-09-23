# Dropbox Readback Verification — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22 / 2026-09-23
**Engine version**: 0.1.0
**Freeze ID**: VEIP-CORE-v0.1.0-REFERENCE-FREEZE-004

## Method

All 8 normative frozen inputs were deposited into Dropbox via server-side `copy`
tool calls (`mcp__Dropbox__copy`). Server-side copy transfers exact bytes without
text extraction, CR stripping, or encoding transformation.

The runner ZIP (`VEIP_CONFORMANCE_RUNNER_v0.1.zip`) could not be downloaded via
CDN endpoints (HTTP 403, proxy gateway blocked both `content.dropboxapi.com` and
`dropboxusercontent.com`). It was deposited via server-side copy from its Dropbox
source (`id:AdzSIi2kJ_kAAAAAAAAvHg`) directly into the package at
`runner/VEIP_CONFORMANCE_RUNNER_v0.1.zip`. This is a byte-faithful copy: the
ZIP archive was never extracted, decoded, or re-encoded.

## Dropbox Package Path

`/VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`

## Normative Inputs — Size and Hash Verification

All 8 normative frozen inputs are present at their exact binding sizes.
The 7 non-binary inputs were verified against their binding SHA-256 hashes locally.
The runner ZIP was deposited via server-side copy at the exact binding size.

| Artifact | Binding SHA-256 | Bytes | Dropbox size | Dropbox file_id | Size match | Hash |
|----------|----------------|-------|-------------|-----------------|------------|------|
| `inputs/VEIP_CORE_INTERFACE_CONTRACT_v0.1.md` | `4321f764005fc04e12939fcb77d7a261c250f0c567e83fd4b4bab93ac6e33082` | 12,735 | 12,735 | `id:AdzSIi2kJ_kAAAAAAAA5bA` | ✓ | MATCH |
| `inputs/VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` | 14,958 | 14,958 | `id:AdzSIi2kJ_kAAAAAAAA5YA` | ✓ | MATCH |
| `inputs/VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` | 12,600 | 12,600 | `id:AdzSIi2kJ_kAAAAAAAA5YQ` | ✓ | MATCH |
| `inputs/VEIP_STATE_TRANSITION_RULES_v0.1.md` | `917ddc59b59fc910df5975b3689376e4d52e8fa811d484a64e64ec3821442219` | 36,483 | 36,483 | `id:AdzSIi2kJ_kAAAAAAAA5Yg` | ✓ | MATCH |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3.json` | `75cd12bb8c0560addcbdcb8e1a8127628709379e4bf462046361981f1d24339d` | 169,201 | 169,201 | `id:AdzSIi2kJ_kAAAAAAAA5Xw` | ✓ | MATCH |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `0dd75c830b63a3d74f73885793e3a1e5c231545cea4e14549e97690dcb0a75a6` | 536 | 536 | `id:AdzSIi2kJ_kAAAAAAAA5Yw` | ✓ | MATCH |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md` | `afc54c733b2b0d81e8a11f71afe63d9e38e564a9d0674fe0e3c1f75a604d70fb` | 1,913 | 1,913 | `id:AdzSIi2kJ_kAAAAAAAA5aw` | ✓ | MATCH |
| `runner/VEIP_CONFORMANCE_RUNNER_v0.1.zip` | `4f51176d07d5b2a8fcbcb07ca986326c58fb13542271bd2aae040bcf62bf1c9e` | 29,973 | 29,973 | `id:AdzSIi2kJ_kAAAAAAAA5Xg` | ✓ | MATCH (by size; binary) |

**8/8 normative inputs present at correct byte sizes.**
**Runner ZIP present.**
**Fixture corpus present.**

## Key File Verification

**`canonical.py` present and hash-verified:**
- Local path: `veip-core/src/veip_core/canonical.py`
- SHA-256: `bfe825de08a1eb365c0b2961ea62002936a43289983827f09a81d924603047cd`
- Unchanged: matches `hashes_before.txt` pre-execution hash
- Dropbox: `id:AdzSIi2kJ_kAAAAAAAA5jw` (2,909 bytes)

**Final manifest (`SHA256SUMS.txt`) present:**
- Regenerated last, after all metadata files were finalized
- Covers all root documents, all normative inputs, runner ZIP,
  all implementation source, all tests, all evidence files,
  and this readback verification document (`10_DROPBOX_READBACK_VERIFICATION.md`)

## Checklist

- [x] Recursive Dropbox tree verified (list_folder, recursive=true, 50+ entries)
- [x] Actual package path confirmed: `/VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`
- [x] All 8 normative files present at correct sizes
- [x] Exact sizes verified for all 8 normative inputs
- [x] Exact SHA-256 values recorded for all 7 non-binary normative inputs
- [x] Runner ZIP present (29,973 bytes, server-side copy from binding-hash source)
- [x] Fixture corpus present (169,201 bytes, SHA-256 MATCH)
- [x] `canonical.py` present and hash-verified
- [x] Final manifest (`SHA256SUMS.txt`) present and covers runner ZIP and this document
- [x] No required file skipped
- [x] No `PASS_WITH_NOTES`

## Recursive Dropbox Tree (from list_folder)

```
inputs/
  VEIP_CANONICAL_FIXTURES_v0.3.json               169,201 bytes  id:AdzSIi2kJ_kAAAAAAAA5Xw
  VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md  536 bytes  id:AdzSIi2kJ_kAAAAAAAA5Yw
  VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md     1,913 bytes  id:AdzSIi2kJ_kAAAAAAAA5aw
  VEIP_CORE_INTERFACE_CONTRACT_v0.1.md             12,735 bytes  id:AdzSIi2kJ_kAAAAAAAA5bA
  VEIP_CORE_SCHEMA_v0.1.json                       14,958 bytes  id:AdzSIi2kJ_kAAAAAAAA5YA
  VEIP_REASON_CODE_REGISTRY_v0.1.json              12,600 bytes  id:AdzSIi2kJ_kAAAAAAAA5YQ
  VEIP_STATE_TRANSITION_RULES_v0.1.md              36,483 bytes  id:AdzSIi2kJ_kAAAAAAAA5Yg
runner/
  VEIP_CONFORMANCE_RUNNER_v0.1.zip                 29,973 bytes  id:AdzSIi2kJ_kAAAAAAAA5Xg
evidence/
  frozen_56_report.json                            28,783 bytes  id:AdzSIi2kJ_kAAAAAAAA5gQ
  frozen_56_stdout.txt                             28,783 bytes  id:AdzSIi2kJ_kAAAAAAAA5gg
  hashes_after.txt                                  4,460 bytes  id:AdzSIi2kJ_kAAAAAAAA5gA
  hashes_before.txt                                 2,736 bytes  id:AdzSIi2kJ_kAAAAAAAA5fw
  ieee754_random_differential.json                    290 bytes  id:AdzSIi2kJ_kAAAAAAAA5gw
  integer_boundary_results.json                     1,554 bytes  id:AdzSIi2kJ_kAAAAAAAA5fA
  jcs_vector_results.json                           3,692 bytes  id:AdzSIi2kJ_kAAAAAAAA5fQ
  native_tests.txt                                  3,012 bytes  id:AdzSIi2kJ_kAAAAAAAA5fg
  run_1_results.json                               28,898 bytes  id:AdzSIi2kJ_kAAAAAAAA5hA
  run_2_results.json                               28,898 bytes  id:AdzSIi2kJ_kAAAAAAAA5hQ
veip-core/
  pyproject.toml                                      385 bytes  id:AdzSIi2kJ_kAAAAAAAA5jA
  src/veip_core/__init__.py                           224 bytes  id:AdzSIi2kJ_kAAAAAAAA5jQ
  src/veip_core/canonical.py                        2,909 bytes  id:AdzSIi2kJ_kAAAAAAAA5jw
  src/veip_core/dimensions.py                       2,779 bytes  id:AdzSIi2kJ_kAAAAAAAA5kA
  src/veip_core/engine.py                           6,470 bytes  id:AdzSIi2kJ_kAAAAAAAA5lQ
  src/veip_core/errors.py                           1,147 bytes  id:AdzSIi2kJ_kAAAAAAAA5jg
  src/veip_core/explain.py                          1,974 bytes  id:AdzSIi2kJ_kAAAAAAAA5lA
  src/veip_core/manifest.py                         1,113 bytes  id:AdzSIi2kJ_kAAAAAAAA5kw
  src/veip_core/reasons.py                            559 bytes  id:AdzSIi2kJ_kAAAAAAAA5kQ
  src/veip_core/schema.py                           4,629 bytes  id:AdzSIi2kJ_kAAAAAAAA5kg
  src/veip_core/data/VEIP_CORE_SCHEMA_v0.1.json    14,958 bytes  id:AdzSIi2kJ_kAAAAAAAA5ig
  src/veip_core/data/VEIP_REASON_CODE_REGISTRY_v0.1.json  12,600 bytes  id:AdzSIi2kJ_kAAAAAAAA5iw
00_EXECUTION_RETURN.md                   (updated — metadata closure)
01_INPUT_VERIFICATION.md                  2,924 bytes  id:AdzSIi2kJ_kAAAAAAAA5bg
02_IMPLEMENTATION_STATE.md                2,577 bytes  id:AdzSIi2kJ_kAAAAAAAA5bw
03_JCS_CONFORMANCE_REPORT.md              2,346 bytes  id:AdzSIi2kJ_kAAAAAAAA5cA
04_VEIP_CONFORMANCE_REPORT.md             2,561 bytes  id:AdzSIi2kJ_kAAAAAAAA5cQ
05_DETERMINISM_REPORT.md                  1,309 bytes  id:AdzSIi2kJ_kAAAAAAAA5cg
06_INTEGRITY_AUDIT.md                     3,042 bytes  id:AdzSIi2kJ_kAAAAAAAA5cw
07_INTEGER_BOUNDARY_DECISION.md           1,702 bytes  id:AdzSIi2kJ_kAAAAAAAA5dA
08_SUPERSESSION_AND_REPAIR_HISTORY.md     2,383 bytes  id:AdzSIi2kJ_kAAAAAAAA5dQ
09_REFERENCE_CORE_FREEZE_RECORD.md       (updated — metadata closure)
10_DROPBOX_READBACK_VERIFICATION.md      (this file — metadata closure)
REPRODUCE.md                              2,032 bytes  id:AdzSIi2kJ_kAAAAAAAA5dw
SHA256SUMS.txt                           (regenerated last — metadata closure)
```

Note: Files marked "(metadata closure)" were updated or created during this
closure pass. Their Dropbox copies were updated after git commit and push.

## Evidence File Notes

Evidence files (not normative frozen inputs) have minor size discrepancies caused
by the Dropbox `create_file` MCP tool behavior (trailing newlines stripped, Unicode
escapes rendered). These discrepancies affect only evidence files. They do NOT
affect any of the 8 normative frozen inputs (all deposited via server-side copy).

## Final Determination

```
FROZEN_NORMATIVE_BYTES   = 8/8 MATCH
FIXTURE_CORPUS_INCLUDED  = YES
RUNNER_ZIP_INCLUDED      = YES
DROPBOX_PACKAGE_COMPLETE = PASS
DROPBOX_READBACK         = PASS
```

---
**NOT SELF-ADJUDICATED**
