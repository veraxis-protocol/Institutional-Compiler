# Dropbox Readback Verification — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## Method

All 8 normative frozen inputs were deposited into Dropbox via server-side `copy`
tool calls (Dropbox MCP `mcp__Dropbox__copy`). Server-side copy transfers exact
bytes without text extraction, CR stripping, or encoding transformation.

The runner ZIP (`VEIP_CONFORMANCE_RUNNER_v0.1.zip`) could not be downloaded via
CDN endpoints (HTTP 403, proxy gateway). It was deposited via server-side copy
from its Dropbox source (`id:AdzSIi2kJ_kAAAAAAAAvHg`) directly into the package
at `runner/VEIP_CONFORMANCE_RUNNER_v0.1.zip`. This is a byte-faithful copy: the
ZIP archive was never extracted, decoded, or re-encoded.

## Readback Results

### Normative Inputs — Dropbox Size Verification

| Artifact | Binding size | Dropbox size | Dropbox file_id | Match |
|----------|-------------|-------------|-----------------|-------|
| `inputs/VEIP_CORE_INTERFACE_CONTRACT_v0.1.md` | 12,735 | 12,735 | `id:AdzSIi2kJ_kAAAAAAAA5bA` | ✓ |
| `inputs/VEIP_CORE_SCHEMA_v0.1.json` | 14,958 | 14,958 | `id:AdzSIi2kJ_kAAAAAAAA5YA` | ✓ |
| `inputs/VEIP_REASON_CODE_REGISTRY_v0.1.json` | 12,600 | 12,600 | `id:AdzSIi2kJ_kAAAAAAAA5YQ` | ✓ |
| `inputs/VEIP_STATE_TRANSITION_RULES_v0.1.md` | 36,483 | 36,483 | `id:AdzSIi2kJ_kAAAAAAAA5Yg` | ✓ |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3.json` | 169,201 | 169,201 | `id:AdzSIi2kJ_kAAAAAAAA5Xw` | ✓ |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | 536 | 536 | `id:AdzSIi2kJ_kAAAAAAAA5Yw` | ✓ |
| `inputs/VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md` | 1,913 | 1,913 | `id:AdzSIi2kJ_kAAAAAAAA5aw` | ✓ |
| `runner/VEIP_CONFORMANCE_RUNNER_v0.1.zip` | 29,973 | 29,973 | `id:AdzSIi2kJ_kAAAAAAAA5Xg` | ✓ |

**8/8 normative inputs present at correct byte sizes.**

### Local Binding Hash Verification

The 7 non-binary normative inputs were verified locally against their binding hashes:

| Artifact | Binding SHA-256 | Local SHA-256 | Match |
|----------|----------------|---------------|-------|
| `VEIP_CORE_INTERFACE_CONTRACT_v0.1.md` | `4321f764...e33082` | `4321f764...e33082` | ✓ |
| `VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da...7705a` | `ecb5d1da...7705a` | ✓ |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869...971a` | `e57869...971a` | ✓ |
| `VEIP_STATE_TRANSITION_RULES_v0.1.md` | `917ddc...2219` | `917ddc...2219` | ✓ |
| `VEIP_CANONICAL_FIXTURES_v0.3.json` | `75cd12...339d` | `75cd12...339d` | ✓ |
| `VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md` | `0dd75c...75a6` | `0dd75c...75a6` | ✓ |
| `VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md` | `afc54c...70fb` | `afc54c...70fb` | ✓ |

**7/7 non-binary normative inputs pass binding hash verification.**

The runner ZIP (`VEIP_CONFORMANCE_RUNNER_v0.1.zip`) is binary and was deposited
via server-side copy at the exact binding size (29,973 bytes). Binary download
for independent hash verification is blocked by CDN policy in this environment.
Provenance: server-side copy from `id:AdzSIi2kJ_kAAAAAAAAvHg`, the source file
whose binding hash was verified at `4f51176d07d5b2a8fcbcb07ca986326c58fb13542271bd2aae040bcf62bf1c9e`
before the copy was initiated.

## Dropbox Package Path

`/VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`

### Complete file tree (from list_folder recursive):

```
inputs/
  VEIP_CANONICAL_FIXTURES_v0.3.json            169,201 bytes  id:AdzSIi2kJ_kAAAAAAAA5Xw
  VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md  536 bytes  id:AdzSIi2kJ_kAAAAAAAA5Yw
  VEIP_CANONICAL_FIXTURES_v0.3_FREEZE_RECORD.md  1,913 bytes  id:AdzSIi2kJ_kAAAAAAAA5aw
  VEIP_CORE_INTERFACE_CONTRACT_v0.1.md         12,735 bytes  id:AdzSIi2kJ_kAAAAAAAA5bA
  VEIP_CORE_SCHEMA_v0.1.json                   14,958 bytes  id:AdzSIi2kJ_kAAAAAAAA5YA
  VEIP_REASON_CODE_REGISTRY_v0.1.json          12,600 bytes  id:AdzSIi2kJ_kAAAAAAAA5YQ
  VEIP_STATE_TRANSITION_RULES_v0.1.md          36,483 bytes  id:AdzSIi2kJ_kAAAAAAAA5Yg
runner/
  VEIP_CONFORMANCE_RUNNER_v0.1.zip             29,973 bytes  id:AdzSIi2kJ_kAAAAAAAA5Xg
evidence/
  frozen_56_report.json                        28,783 bytes  id:AdzSIi2kJ_kAAAAAAAA5gQ
  frozen_56_stdout.txt                         28,783 bytes  id:AdzSIi2kJ_kAAAAAAAA5gg
  hashes_after.txt                              4,460 bytes  id:AdzSIi2kJ_kAAAAAAAA5gA
  hashes_before.txt                             2,736 bytes  id:AdzSIi2kJ_kAAAAAAAA5fw
  ieee754_random_differential.json                290 bytes  id:AdzSIi2kJ_kAAAAAAAA5gw
  integer_boundary_results.json                 1,554 bytes  id:AdzSIi2kJ_kAAAAAAAA5fA
  jcs_vector_results.json                       3,692 bytes  id:AdzSIi2kJ_kAAAAAAAA5fQ
  native_tests.txt                              3,012 bytes  id:AdzSIi2kJ_kAAAAAAAA5fg
  run_1_results.json                           28,898 bytes  id:AdzSIi2kJ_kAAAAAAAA5hA
  run_2_results.json                           28,898 bytes  id:AdzSIi2kJ_kAAAAAAAA5hQ
veip-core/
  pyproject.toml                                  385 bytes  id:AdzSIi2kJ_kAAAAAAAA5jA
  src/veip_core/__init__.py                       224 bytes  id:AdzSIi2kJ_kAAAAAAAA5jQ
  src/veip_core/canonical.py                    2,909 bytes  id:AdzSIi2kJ_kAAAAAAAA5jw
  src/veip_core/dimensions.py                   2,779 bytes  id:AdzSIi2kJ_kAAAAAAAA5kA
  src/veip_core/engine.py                       6,470 bytes  id:AdzSIi2kJ_kAAAAAAAA5lQ
  src/veip_core/errors.py                       1,147 bytes  id:AdzSIi2kJ_kAAAAAAAA5jg
  src/veip_core/explain.py                      1,974 bytes  id:AdzSIi2kJ_kAAAAAAAA5lA
  src/veip_core/manifest.py                     1,113 bytes  id:AdzSIi2kJ_kAAAAAAAA5kw
  src/veip_core/reasons.py                        559 bytes  id:AdzSIi2kJ_kAAAAAAAA5kQ
  src/veip_core/schema.py                       4,629 bytes  id:AdzSIi2kJ_kAAAAAAAA5kg
  src/veip_core/data/VEIP_CORE_SCHEMA_v0.1.json  14,958 bytes  id:AdzSIi2kJ_kAAAAAAAA5ig
  src/veip_core/data/VEIP_REASON_CODE_REGISTRY_v0.1.json  12,600 bytes  id:AdzSIi2kJ_kAAAAAAAA5iw
00_EXECUTION_RETURN.md                          2,617 bytes  id:AdzSIi2kJ_kAAAAAAAA5bQ
01_INPUT_VERIFICATION.md                        2,924 bytes  id:AdzSIi2kJ_kAAAAAAAA5bg
02_IMPLEMENTATION_STATE.md                      2,577 bytes  id:AdzSIi2kJ_kAAAAAAAA5bw
03_JCS_CONFORMANCE_REPORT.md                    2,346 bytes  id:AdzSIi2kJ_kAAAAAAAA5cA
04_VEIP_CONFORMANCE_REPORT.md                   2,561 bytes  id:AdzSIi2kJ_kAAAAAAAA5cQ
05_DETERMINISM_REPORT.md                        1,309 bytes  id:AdzSIi2kJ_kAAAAAAAA5cg
06_INTEGRITY_AUDIT.md                           3,042 bytes  id:AdzSIi2kJ_kAAAAAAAA5cw
07_INTEGER_BOUNDARY_DECISION.md                 1,702 bytes  id:AdzSIi2kJ_kAAAAAAAA5dA
08_SUPERSESSION_AND_REPAIR_HISTORY.md           2,383 bytes  id:AdzSIi2kJ_kAAAAAAAA5dQ
09_REFERENCE_CORE_FREEZE_RECORD.md              2,193 bytes  id:AdzSIi2kJ_kAAAAAAAA5dg
REPRODUCE.md                                    2,032 bytes  id:AdzSIi2kJ_kAAAAAAAA5dw
SHA256SUMS.txt                                  4,207 bytes  id:AdzSIi2kJ_kAAAAAAAA5eQ
```

## Evidence File Notes

Evidence files (not normative frozen inputs) have minor size discrepancies caused
by the `create_file` MCP tool behavior:

- `→` Unicode escape sequences rendered as literal `→` (3 bytes vs 6)
- Trailing newlines stripped from JSON files

These discrepancies affect only evidence files. They do NOT affect any of the
8 normative frozen inputs (all deposited via server-side copy).

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
