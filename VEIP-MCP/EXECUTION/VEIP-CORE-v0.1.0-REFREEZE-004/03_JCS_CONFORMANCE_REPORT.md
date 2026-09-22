# JCS Conformance Report — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0
**Python version**: 3.11.15
**Standard**: RFC 8785 (JSON Canonicalization Scheme)
**Result**: ALL 24 APPENDIX B VECTORS PASS

## RFC 8785 Appendix B Number Serialization Vectors

All 24 test vectors from RFC 8785 Appendix B were verified against
`veip_core.canonical.dumps()`.

| Bits (hex) | Expected | Result |
|-----------|---------|--------|
| `0000000000000000` | `0` | PASS |
| `8000000000000000` | `0` | PASS |
| `0000000000000001` | `5e-324` | PASS |
| `8000000000000001` | `-5e-324` | PASS |
| `7fefffffffffffff` | `1.7976931348623157e+308` | PASS |
| `ffefffffffffffff` | `-1.7976931348623157e+308` | PASS |
| `4340000000000000` | `9007199254740992` | PASS |
| `c340000000000000` | `-9007199254740992` | PASS |
| `4430000000000000` | `295147905179352830000` | PASS |
| `44b52d02c7e14af5` | `9.999999999999997e+22` | PASS |
| `44b52d02c7e14af6` | `1e+23` | PASS |
| `44b52d02c7e14af7` | `1.0000000000000001e+23` | PASS |
| `444b1ae4d6e2ef4e` | `999999999999999700000` | PASS |
| `444b1ae4d6e2ef4f` | `999999999999999900000` | PASS |
| `444b1ae4d6e2ef50` | `1e+21` | PASS |
| `3eb0c6f7a0b5ed8c` | `9.999999999999997e-7` | PASS |
| `3eb0c6f7a0b5ed8d` | `0.000001` | PASS |
| `41b3de4355555553` | `333333333.3333332` | PASS |
| `41b3de4355555554` | `333333333.33333325` | PASS |
| `41b3de4355555555` | `333333333.3333333` | PASS |
| `41b3de4355555556` | `333333333.3333334` | PASS |
| `41b3de4355555557` | `333333333.33333343` | PASS |
| `becbf647612f3696` | `-0.0000033333333333333333` | PASS |
| `43143ff3c1cb0959` | `1424953923781206.2` | PASS |

**Summary: 24/24 PASS, 0 FAIL**

## Full Test Suite Results

The full `tests/test_jcs_conformance.py` test file (8 test cases, 32 subtests)
passed as part of the native test run documented in `evidence/native_tests.txt`:

- `test_rfc_8785_sample` — PASS
- `test_rfc_8785_appendix_b_number_vectors` — 24 subtests PASS
- `test_non_finite_numbers_are_rejected` — PASS
- `test_integer_domain_boundary` — PASS
- `test_utf16_property_order` — PASS
- `test_control_character_escaping` — PASS
- `test_lone_surrogates_are_rejected` — PASS
- `test_nested_payload_digest` — PASS

## Evidence

Raw vector results: `evidence/jcs_vector_results.json`

---
**NOT SELF-ADJUDICATED**
