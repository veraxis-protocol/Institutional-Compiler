# Implementation State — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0
**Python version**: 3.11.15

## Source File SHA-256 (Before Test Run)

From `evidence/hashes_before.txt` (generated before any test was run):

| File | SHA-256 |
|------|---------|
| `veip-core/pyproject.toml` | `3050b6a0d40453b661a9f8fc61b6bf498173874f226d57943812a7f1c7aca282` |
| `veip-core/src/veip_core/__init__.py` | `406644d4bc8832b04ba0eebd9740ed14475bbe92ea8387b7860fbefff4179bc0` |
| `veip-core/src/veip_core/canonical.py` | `bfe825de08a1eb365c0b2961ea62002936a43289983827f09a81d924603047cd` |
| `veip-core/src/veip_core/data/VEIP_CORE_SCHEMA_v0.1.json` | `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` |
| `veip-core/src/veip_core/data/VEIP_REASON_CODE_REGISTRY_v0.1.json` | `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` |
| `veip-core/src/veip_core/dimensions.py` | `0fa7812cf94ef89792198ce91798046a1a7f002e4eac8a6ead0affe630d0cd85` |
| `veip-core/src/veip_core/engine.py` | `7603375e9c8962149262d78f599362f8026d5c93775e8d05c03b883d5adc0722` |
| `veip-core/src/veip_core/errors.py` | `dc0f48958245dc54f2ff6ab2a2ce6b0e4ef01836a3271d84d72b8572420ede95` |
| `veip-core/src/veip_core/explain.py` | `b5ad0f74ad0b1cbbd2a41d698fd85f609d18caf6198bda64ae19138f4e74f96e` |
| `veip-core/src/veip_core/manifest.py` | `0a4208946076d68a0733f6be9b3f6fc24bf176d31429eb4025b8713889ef98a0` |
| `veip-core/src/veip_core/reasons.py` | `a94b2a4e0e687102343f1c4ba8f3dad3495b8d49b6f6c5a0dce38d7b855b29eb` |
| `veip-core/src/veip_core/schema.py` | `5b137d1b1f063b53cac698cac1d6e755cc4e2b81fdb22e1b2588ade3d9153842` |

## Critical Policy: Integer Domain

`canonical.py` defines:
```python
_MAX_SAFE_INTEGER = 9007199254740991
```

Integers outside `[-9007199254740991, 9007199254740991]` raise `ValueError`.
This value was NOT widened from the REFREEZE-003 baseline.

## Data File Binding Hash Match

Both data files embedded in the package match the binding hashes exactly:

- `src/veip_core/data/VEIP_CORE_SCHEMA_v0.1.json`:
  `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a` ✓
- `src/veip_core/data/VEIP_REASON_CODE_REGISTRY_v0.1.json`:
  `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a` ✓

These hashes also appear in `inputs/` (the canonical source):
`inputs/VEIP_CORE_SCHEMA_v0.1.json` and
`inputs/VEIP_REASON_CODE_REGISTRY_v0.1.json`.

## Test Installation

Package installed with `pip install -e .` under Python 3.11.15.
No test-time source modifications were made.

---
**NOT SELF-ADJUDICATED**
