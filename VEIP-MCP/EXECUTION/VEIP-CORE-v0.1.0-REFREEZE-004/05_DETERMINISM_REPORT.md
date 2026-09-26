# Determinism Report — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## Evidence

Two independent in-process runs of the full 56-fixture corpus were executed
in the same Python process, with no state shared between runs. Both runs
replayed all fixtures from `inputs/VEIP_CANONICAL_FIXTURES_v0.3.json`.

| Run | SHA-256 of serialized results | Fixture count |
|-----|------------------------------|---------------|
| Run 1 | `df6973e4ed7e83f39cf4da6768966b9b50b9d259c0a0db6062bef2abc677cb8c` | 56 |
| Run 2 | `df6973e4ed7e83f39cf4da6768966b9b50b9d259c0a0db6062bef2abc677cb8c` | 56 |

**Hashes match: DETERMINISM PASS**

## Methodology

For each run, all 56 fixture inputs were deep-copied (preventing cross-run
contamination), processed through `adjudicate()` or `explain_boundary()`,
and serialized with `json.dumps(..., sort_keys=True, separators=(",", ":"))`.
The SHA-256 of the UTF-8 encoding of the serialized array was computed.

The identical hash confirms that the engine produces the same output for
the same input on repeated invocations within the same environment, with
no hidden mutable state.

## Evidence Files

- `evidence/run_1_results.json` — full result set, run 1
- `evidence/run_2_results.json` — full result set, run 2

---
**NOT SELF-ADJUDICATED**
