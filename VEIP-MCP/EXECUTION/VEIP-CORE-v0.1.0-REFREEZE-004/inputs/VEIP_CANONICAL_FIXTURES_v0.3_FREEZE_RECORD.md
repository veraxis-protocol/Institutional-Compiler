# VEIP Canonical Fixtures v0.3 — Freeze Record

Date: 2026-09-21 / 2026-09-22 UTC boundary
Status: **FROZEN**

## Canonical artifact

- Dropbox path: `/VEIP-MCP/VEIP_CANONICAL_FIXTURES_v0.3.json`
- Dropbox file ID: `id:AdzSIi2kJ_kAAAAAAAAvGg`
- Fixture count: **56** (`V03-001` through `V03-056`)
- SHA-256 of frozen local source bytes before Dropbox upload: `75cd12bb8c0560addcbdcb8e1a8127628709379e4bf462046361981f1d24339d`

## Normative dependencies audited

- `VEIP_CORE_SCHEMA_v0.1.json` SHA-256: `ecb5d1da3dab5ff6933be525fba0e8ac03deda0a3ee2e4a9e59a3ca85cf7705a`
- `VEIP_REASON_CODE_REGISTRY_v0.1.json` SHA-256: `e57869121d9bc44a66d4ead1a67759c57e6a80d75780b984d5576359f65d971a`
- `VEIP_STATE_TRANSITION_RULES_v0.1.md` SHA-256: `917ddc59b59fc910df5975b3689376e4d52e8fa811d484a64e64ec3821442219`

## Adversarial freeze audit

- Result: **PASS**
- Checks: **475 / 475 PASS**
- Schema: exact frozen Dropbox schema bytes materialized and used directly
- Independent semantic regeneration: PASS
- Mutation isolation: PASS
- Decoy invariance: PASS
- Role attribution: PASS
- Composite task-completion propagation: PASS
- Reserved/unreachable reason-code checks: PASS
- Explanation boundary attacks: PASS
- Historical 18-fixture lineage: PASS
- Exact hash reproduction: PASS
- Error precedence coverage added as `V03-053` through `V03-056`: PASS

Audit artifacts:
- `/VEIP-MCP/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md`
- `/VEIP-MCP/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.json`

## Immutability rule

The canonical `VEIP_CANONICAL_FIXTURES_v0.3.json` bytes are frozen. Future corrections MUST be additive errata or a new corpus version; do not edit v0.3 in place.

## Next implementation gate

`VEIP Conformance Runner v0.1` is the first downstream implementation artifact. It contains no VEIP adjudication semantics and compares external engine outputs against this frozen corpus.
