# Supersession and Repair History — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## Prior Freeze Attempts

Four attempts have been made to produce the authoritative VEIP Core v0.1.0
reference freeze. The first three were rejected and are preserved as
failed provenance at their respective execution paths. None were modified
or deleted.

### CODEX-001 (First attempt)

- **Path**: (outside EXECUTION directory — not tracked here)
- **Disposition**: REJECTED
- **Reason**: Wrong schema bytes; reconstruction rather than byte-faithful copy

### REFREEZE-002 (Second attempt)

- **Path**: (outside EXECUTION directory — not tracked here)
- **Disposition**: REJECTED
- **Reason**: Wrong schema bytes; wrong registry bytes

### REFREEZE-003 (Third attempt)

- **Path**: `VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-003/`
- **Disposition**: **REJECTED — preserved as failed provenance, NOT modified**
- **Rejection reasons** (8 total):
  1. Wrong schema bytes (used 15,351-byte version from EXECUTION path, not 14,958-byte binding-hash version from `/VEIP-MCP/` root)
  2. Wrong registry bytes (used 12,370-byte version, not 12,600-byte binding-hash version)
  3. Truncated transition rules (182 bytes vs. 36,483-byte binding hash)
  4. Fixture corpus not deposited to Dropbox
  5. Runner ZIP not deposited to Dropbox
  6. Adversarial freeze audit was omitted
  7. Git substituted for Dropbox deposit (work order prohibits this)
  8. `PASS_WITH_NOTES` reported (work order requires only `DROPBOX_READBACK = PASS` or `FAIL`)

### REFREEZE-004 (This attempt — current)

- **Path**: `VEIP-MCP/EXECUTION/VEIP-CORE-v0.1.0-REFREEZE-004/`
- **All three prior rejection items resolved**:
  - Schema and registry: correct bytes obtained via Dropbox `fetch` + CRLF
    reconstruction algorithm, verified against binding hashes before use
  - Transition rules: correct 36,483-byte LF file fetched from Dropbox
    `id:AdzSIi2kJ_kAAAAAAAAvFQ`, hash verified
  - Fixtures corpus: correct 169,201-byte file fetched from Dropbox
    `id:AdzSIi2kJ_kAAAAAAAAvGg`, hash verified
  - Adversarial freeze audit: included at `inputs/` with verified hash
  - All 7 inputs verified before use
- **Remaining STOP condition**:
  - Runner ZIP (29,973 bytes) cannot be deposited; Dropbox CDN blocked
    (see `04_VEIP_CONFORMANCE_REPORT.md`)

---
**NOT SELF-ADJUDICATED**
