# Test Results — VEIP-CORE-v0.1.0-REFREEZE-003

**Date**: 2026-09-22  
**Engine version**: 0.1.0  
**Python**: 3.11.15  
**Node.js**: v22.22.2  

---

## Native pytest Suite

```
collected 20 items
20 passed, 97 subtests passed in 0.11s
```

| Test module | Tests | Result |
|---|---|---|
| test_core.py | 8 | PASS |
| test_integer_boundary.py | 4 | PASS |
| test_jcs_conformance.py | 8 | PASS |

## Conformance Runner (56/56 black-box)

```
56 fixtures
56 PASS
0 FAIL
engine version: 0.1.0
```

Conformance report SHA-256: `c027118143ce2cda37c5d6b8c08d28f8599eafa23919b04a82027bfb5ad9a633`

## IEEE-754 Differential (999,511/999,511)

Corpus generator: `tools/gen_differential_corpus.py` (seed 0xC0FFEE)  
Comparator: `tools/run_differential.js` (Node.js v22.22.2)  

Result: `{"total": 999511, "pass": 999511, "fail": 0}`

## Determinism Evidence (2 identical runs)

Run 1 SHA256: `1c92cfce90659976b070332945b337b942b12f37e6e2836e4821a9df93cba2a8`  
Run 2 SHA256: `1c92cfce90659976b070332945b337b942b12f37e6e2836e4821a9df93cba2a8`  

DETERMINISM: PASS

## Integer Boundary Policy

`_MAX_SAFE_INTEGER = 9007199254740991` = `2^53 - 1`
