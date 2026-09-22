# Integer Boundary Policy — VEIP-CORE-v0.1.0-REFREEZE-003

**Frozen**: 2026-09-22  
**Engine version**: 0.1.0  

## Policy

`_MAX_SAFE_INTEGER = 9007199254740991`  

This value MUST NOT be widened without a versioned interoperability decision.

## Rationale

RFC 8785 JCS requires integers in ECMAScript safe integer domain: `[-(2^53-1), 2^53-1]`.

## Boundary Values

| Value | Result |
|-------|--------|
| `9007199254740991` (2^53-1) | Accepted |
| `-9007199254740991` (-(2^53-1)) | Accepted |
| `9007199254740992` (2^53) | ValueError |
| `2^68` | ValueError |

Source: `veip-core/src/veip_core/canonical.py` SHA-256: `bfe825de08a1eb365c0b2961ea62002936a43289983827f09a81d924603047cd`
