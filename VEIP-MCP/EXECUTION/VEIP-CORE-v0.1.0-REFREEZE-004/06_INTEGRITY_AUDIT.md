# Integrity Audit — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## Source Code Unchanged

SHA-256 hashes of all source files were recorded in `evidence/hashes_before.txt`
before any test was run. The files were not modified during execution.
No test-time patching, monkey-patching, or sys.path manipulation that
would substitute a different implementation was performed.

## CRLF Reconstruction Algorithm

Two required input files are stored in Dropbox with CRLF line endings:
- `VEIP_CORE_SCHEMA_v0.1.json` (14,958 bytes)
- `VEIP_REASON_CODE_REGISTRY_v0.1.json` (12,600 bytes)

The Dropbox `fetch` MCP tool performs text extraction. For CRLF files it:
1. Strips all CR (`\r`) bytes from the content
2. Appends exactly one trailing LF (`\n`) to the extracted result

The exact byte-recovery algorithm used:
```python
import hashlib, pathlib

data = pathlib.Path('lf_extracted.json').read_bytes()
# Strip the one trailing LF added by the fetch tool:
last_lf = data.rfind(b'\n')
trimmed = data[:last_lf] + data[last_lf+1:]
# Convert all remaining bare LF to CRLF:
converted = trimmed.replace(b'\n', b'\r\n')
h = hashlib.sha256(converted).hexdigest()
# Verify h == binding hash before writing
```

This algorithm was validated independently for both files before writing:

| File | Expected hash | Computed hash | Match |
|------|--------------|---------------|-------|
| `VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` | ✓ |
| `VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` | ✓ |

**IMPORTANT: The Write tool on Linux strips CR bytes**. Therefore the Python
`pathlib.Path.write_bytes()` call was used to write the reconstructed CRLF
bytes directly, bypassing the text pipeline. The hash was verified after
writing by reading back with `read_bytes()` and computing SHA-256.

## EXECUTION vs. ROOT Dropbox Path Discrepancy

The Dropbox directory `/VEIP-MCP/EXECUTION/` contains WRONG versions of the
schema and registry files:
- `/VEIP-MCP/EXECUTION/VEIP_CORE_SCHEMA_v0.1.json`: 15,351 bytes (different hash)
- `/VEIP-MCP/EXECUTION/VEIP_REASON_CODE_REGISTRY_v0.1.json`: 9,862 bytes (different hash)

Only the `/VEIP-MCP/` root files (`id:AdzSIi2kJ_kAAAAAAAAvDg` and
`id:AdzSIi2kJ_kAAAAAAAAvDw`) match the binding hashes and were used.

## Data Files in Package Match Inputs

The embedded data files at `veip-core/src/veip_core/data/` are identical to
the input files at `inputs/`:

```
ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a
  inputs/VEIP_CORE_SCHEMA_v0.1.json
  veip-core/src/veip_core/data/VEIP_CORE_SCHEMA_v0.1.json

e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a
  inputs/VEIP_REASON_CODE_REGISTRY_v0.1.json
  veip-core/src/veip_core/data/VEIP_REASON_CODE_REGISTRY_v0.1.json
```

---
**NOT SELF-ADJUDICATED**
