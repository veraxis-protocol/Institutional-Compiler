# CDC CURRENTNESS-TO-RELIANCE INTEGRATION SLICE 001 — SEMANTIC DESIGN v0.4

```
supersedes        …SEMANTIC-DESIGN-v0.3.md
                  sha256 1c07a24c9be0e4aba1f05d707f5979e1a10c02edcd1b512a7c9439eb891dc307
                  8862 B, ZTL commit a17bd06cb7c14e389b803a9b08d2ba36cc1ec684
                  — preserved unchanged as a historical artifact
companion         INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.3.md
assurance_class   INTERNAL_TECHNICAL_DEMONSTRATION
self_designed_and_self_adjudicated TRUE   independent_review_claim FALSE
result_bearing_execution NONE             status READY_FOR_OWNER_REVIEW_v0.4
```

**Narrow successor.** One correction. The architecture, schemas, reason codes,
test universe, digest classes and claim ceiling of v0.3 are otherwise unchanged.

## 1. Conceded defect

v0.1 carried a distinct consumer check for the freshness of the propagated
authority decision (`now ≤ decision.valid_until` → `I4`). When v0.2 added the
intended-consumer binding (check 8) and the reliance-time authority re-evaluation
(check 14), that freshness check was absorbed into the identity check and
disappeared as a separate step. The result: **`I4` became an orphan code with no
check able to produce it**, even though `T-CASE-G` exists to exercise exactly that
branch. The defect is mine and it is the same species as the previous two — a step
lost while compressing a list, not a disagreement about semantics.

## 2. Consumer revalidation — frozen at sixteen checks

```
 1  envelope integrity                  recompute envelope_digest              → P2
 2  schema closure                      no unknown fields                      → P8
 3  envelope freshness                  produced_at ≤ now ≤ valid_until        → P3
 4  artifact identity                   recomputed from bytes                  → P4
 5  scope binding                                                              → P5
 6  subject-principal binding                                                  → P6
 7  requested-use binding                                                      → P7
 8  intended-consumer binding           consumer_profile.principal_id ==
                                        envelope.intended_consumer_principal   → P12
 9  evidence resolvability              every evidence_ref resolves            → P9
10  producer identity verified          against the frozen producer profile    → P10
11  propagated authority-decision identity   recompute its digest              → I5 / I6
12  propagated authority-decision FRESHNESS  now ≤ decision.valid_until        → I4
13  currentness RE-RESOLUTION           resolve again, now                     → I2 / I9
14  epoch applicability                 epoch_now == epoch bound in decision   → I3
15  authority/admissibility RE-EVALUATION at reliance time, full §5 procedure  → I11
16  issuance only if all required checks pass
```

Checks 11–15 are five distinct properties and none substitutes for another:
*is it the decision that was propagated* (11), *is that decision still within its
own life* (12), *is the world still as it was resolved* (13), *does that decision
still speak about this state* (14), *would the authority basis still say yes now*
(15).

## 3. The rule the new check exists to enforce

```
fresh_revalidation_can_revive_expired_propagated_decision = FALSE
```

If check 12 fails, the consumer refuses with `I4` and does **not** proceed to
check 15 in the hope that a fresh evaluation rescues the path. A reliance-time
re-evaluation returning `PROCEED` would authorize a *new* envelope; it does not
extend the life of a decision that has already lapsed, and the envelope in hand
was produced under that lapsed decision. Allowing revival would make `valid_until`
decorative — an expiry that any later success silently annuls is not an expiry.

This is why check 12 sits **before** checks 13–15 in the frozen order, and why its
failure is terminal for this envelope rather than advisory.

`T-CASE-G` (expired authority decision → refuse) remains the existing
result-bearing case for check 12. No new semantic case is introduced.

## 4. Everything else — unchanged from v0.3

The as-of `currentness_epoch_digest` with its three computed vectors; completeness
attestation participating in the epoch; `R-EPOCH-1` applicability and `R-EPOCH-2`
mandatory re-resolution; two profile objects with the subject represented solely
by `SyntheticAuthorityBasisRecord.principal_id`; the corrected thirteen-step
authority procedure with `A11`/`A12`/`A13` bound to their own object classes;
basis-record and profile self-digests excluded from their own computation with
mandatory reproduction; persisted-file rules for
`issuance_authorization_digest` and `attempt_record_digest` with the write
ordering that excludes an identity cycle; the reliance record binding both
authority moments and the re-resolved currentness; `T-CASE-K` and `T-CASE-P` as
the two primary criteria; the declared `A2`/`A3`/`A4`/`A5` coverage gap; and the
claim ceiling with its six assurance-qualified maxima and three design-specific
limits.

## 5. Return

```
INTEGRATION_SLICE_SEMANTIC_DESIGN = READY_FOR_OWNER_REVIEW_v0.4

consumer_revalidation_check_count                        16
propagated_authority_freshness_explicit                  TRUE   (check 12)
propagated_authority_expiry_reason                       I4
reliance_time_authority_revalidation_distinct            TRUE   (check 15, separate from 12)
fresh_revalidation_can_revive_expired_propagated_decision FALSE
T_CASE_G_exercises_authority_decision_expiry             TRUE

test_count              41   unchanged
new_reason_code_count   36   unchanged (A 13 · P 12 · I 11)
new_digest_class_count   8   unchanged
source_modified         FALSE
result_bearing_execution NONE
```
