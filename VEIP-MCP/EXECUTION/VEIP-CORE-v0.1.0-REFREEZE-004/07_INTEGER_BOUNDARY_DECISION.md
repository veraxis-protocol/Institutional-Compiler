# Integer Boundary Decision — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## Policy

```python
_MAX_SAFE_INTEGER = 9007199254740991  # 2^53 - 1
```

Python integers outside `[-9007199254740991, 9007199254740991]` raise
`ValueError` and are NEVER serialized to JSON output.

This is the **safe IEEE-754 integer domain**: the largest contiguous range
of integers representable as exactly as float64 values with no precision loss.
ECMAScript `Number.MAX_SAFE_INTEGER` equals this value.

## Rationale

- `2^53 = 9007199254740992` is exactly representable as float64, BUT:
  integer arithmetic above `2^53 - 1` loses uniqueness (multiple integers
  map to the same float64 representation)
- The policy was established at VEIP v0.1.0 to prevent interoperability
  defects with ECMAScript-based verifiers
- Widening the domain would be a breaking change requiring a version bump

## Test Results

| Case | Value | Expected | Actual |
|------|-------|----------|--------|
| `max_safe` | `9007199254740991` | ACCEPTED → `"9007199254740991"` | PASS |
| `neg_max_safe` | `-9007199254740991` | ACCEPTED → `"-9007199254740991"` | PASS |
| `zero` | `0` | ACCEPTED → `"0"` | PASS |
| `max_safe_plus_1` | `9007199254740992` | REJECTED (ValueError) | PASS |
| `neg_max_safe_minus_1` | `-9007199254740992` | REJECTED (ValueError) | PASS |
| `two_pow_53` | `9007199254740992` | REJECTED (ValueError) | PASS |
| `neg_two_pow_53` | `-9007199254740992` | REJECTED (ValueError) | PASS |
| `two_pow_68` | `295147905179352825856` | REJECTED (ValueError) | PASS |

**All 8 cases PASS**

## Evidence

Raw results: `evidence/integer_boundary_results.json`

---
**NOT SELF-ADJUDICATED**
