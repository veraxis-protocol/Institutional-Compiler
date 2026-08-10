# CDC-EXEC-VERTICAL-SLICE-001 — Semantic Review Notes v0.1

Reviewer: Vitaliy Reznik
Review result: SEMANTIC_CONTRACT_CONFORMANT_v0.1
Date: 2026-08-10

These notes record two non-blocking interpretations supplied by the semantic/logical-boundary reviewer. They do not amend the owner-attested contract.

## N-1 — fallback warrant

For §7 condition 7 (`ZTL/fallback warrant artifact exists where required`):

- a fallback artifact is recorded as its own artifact class;
- it is never represented as a ZTL warrant;
- `ZTL_warrant_digest` is not populated with the fallback artifact;
- uncertainty about `where required` resolves through ESCALATE/CANNOT under §11, never through ALLOW.

## N-2 — DENY versus CANNOT

- DENY is an operational default-deny on the proposed transition, not an epistemic refutation.
- If a CANNOT condition is operationally mapped to DENY, the epistemic state must remain preserved in the §8 reason-code/event record.
- Epistemic status and operational decision remain separate state dimensions.

Status:
`NON_BLOCKING_INTERPRETATION_NOTES`
`CONTRACT_SEMANTICS_CHANGED = FALSE`
