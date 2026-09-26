# Determinism Evidence — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  

## Intra-run determinism (per probe run)

Each of the 3 probe runs internally parses the captured JSONL twice and asserts:

```python
assert canonical_bytes(parsed1) == canonical_bytes(parsed2)
assert canonical_sha256(parsed1) == canonical_sha256(parsed2)
```

All 3 runs passed this assertion.

## Cross-parse determinism (single JSONL, 3 parses)

The JSONL from run 3 was parsed 3 additional times after the probe completed:

| Parse | canonical_sha256 |
|-------|-----------------|
| 1 | `f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497` |
| 2 | `f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497` |
| 3 | `f1ca2e5805342e2bb69ca27aa04bffa6261faf29023fe1c9def52f6df5543497` |

All 3 parses identical: **DETERMINISM CONFIRMED**

## Note on inter-run normalized SHA-256 variation

The 3 probe runs produce different normalized_sha256 values because each run captures
live wall-clock timestamps from `datetime.now(timezone.utc)` in the custom span data.
This is expected and correct: different live captures produce distinct trace bytes.
The determinism property is that parsing a GIVEN JSONL file produces the same result
every time — not that independent live traces produce the same bytes.

| Run | raw_export_sha256 | normalized_sha256 |
|-----|-------------------|-------------------|
| 1 | `0b4f1890...` | `e13cda6c...` |
| 2 | `dff00215...` | `78a2cd01...` |
| 3 | `383f70c1...` | `f1ca2e58...` |
