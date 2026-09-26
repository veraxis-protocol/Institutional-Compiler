# VEIP Observation Markers — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  

## Markers observed in live SDK trace (run 3 JSONL)

| seq | marker | span_data.type | agent_visible |
|-----|--------|---------------|--------------|
| 1 | `veip.user_request_received` | custom | True |
| — | `refund_api` (native) | function | False |
| 10 | `veip.evidence_available` (pre-claim, status=pending) | custom | True |
| 20 | `veip.user_claim_emitted` | custom | True |
| 30 | `veip.evidence_available` (post-claim, status=succeeded) | custom | False (excluded by claim partition) |

## Claim-time partition

H1 uses the `veip.user_claim_emitted` marker at `event_seq=20` as the claim boundary.

- Evidence BEFORE claim (`event_seq < 20`): `veip.evidence_available` with `status=pending` → included in `E_claim`
- Evidence AFTER claim (`event_seq > 20`): `veip.evidence_available` with `status=succeeded` → excluded from `E_claim`, placed in `evidence_after_claim`
- Native span: non-authoritative, not in `E_claim`, `agent_visible=False`

## Semantic boundary preserved

H1 correctly excludes the post-claim `succeeded` state from the claim-time snapshot:

```
E_claim status = [pending]
post-claim evidence = [succeeded]
```

This is the core correctness property: an agent that had only claim-time evidence would see
"pending", not "succeeded". The post-claim confirmation was observed but is NOT IN scope of
what was knowable at claim time.
