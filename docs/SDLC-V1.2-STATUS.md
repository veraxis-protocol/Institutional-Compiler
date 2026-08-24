# SDLC v1.2 status — Institutional Compiler

Baseline: `29daa374b7e5cdc30ca7788310fbabb85f19912b`.

This is a producer disposition and is **NOT SELF-ADJUDICATED**. The governing
`CURRENT-SDLC.md` v1.2 text was not present at the baseline, so missing normative
gate names are not reconstructed. Independent verification must reconcile this
matrix with the authoritative control.

| Gate | Disposition | Evidence / limitation |
|---|---|---|
| E | PASS | Hash-locked install, safe CLI checks, strict lint/type checks, full tests, wheel smoke check, and compose validation are defined in CI. |
| F | PASS | `make falsify` exercises schema, manifest, semantic-contract, and forbidden code-start failures only for implemented infrastructure. |
| G | PASS | `SECURITY.md` states the non-service scope, private reporting route, supported state, and bounded triage. |
| H | PASS | Dependencies are hash-locked; consequential Actions are full-SHA pinned; CI performs dependency review, advisory scanning, SBOM generation, and wheel verification. |
| I | PASS | `VERSIONING.md` defines provisional pre-1.0 CLI, exit-code, schema, manifest, and artifact contracts. |
| J | PASS | README first screen states what exists, what is blocked, safe checks, and the first executable objective; `AGENTS.md` prohibits semantic expansion. |
| K | N/A | No release is authorized or published; the SBOM is candidate evidence, not attestation. |
| L | NOT ESTABLISHED | Independent verification and owner adjudication of this producer change have not occurred. Semantic code-start remains blocked. |
| M | PASS | `AGENTS.md` documents GitHub attribution, contribution trailers, dark local activity, zero telemetry, and unimplemented remote gateway/MCP surfaces. |

The explicit no-license/pending-counsel state remains unchanged.

