# CDC CURRENTNESS-TO-RELIANCE INTEGRATION SLICE 001 — SEMANTIC DESIGN v0.2

```
supersedes        …SEMANTIC-DESIGN-v0.1.md
                  sha256 f0f250ed4dbf605fde765e30cd6711385a3d4cf74f74d2b48c462bff039234ec
                  21445 B, ZTL commit 936674495e7f18f15bfdd597537831464a027329
                  — preserved unchanged; successor, not amendment
assurance_class   INTERNAL_TECHNICAL_DEMONSTRATION
self_designed_and_self_adjudicated TRUE   independent_review_claim FALSE
result_bearing_execution NONE             status READY_FOR_OWNER_REVIEW_v0.2
```

## 0. Conceded defect in v0.1

The owner review's §1 is correct and the defect is mine.

v0.1 defined the epoch over a **timeless inventory** of governing records. A
successor admitted before t1 with `effective_at` between t1 and t2 has identical
`record_ref`, `record_digest`, `record_class`, `effective_at`, `admitted_at` at
both instants. The digest is therefore identical at t1 and t2 while currentness
moves `CURRENT → SUPERSEDED`. My epoch would not have moved in exactly the case I
declared central, so `T-CASE-K` could not have produced both `I2` and `I3`.

Corrected in §2 as an **as-of projection**, with computed vectors proving both
halves. Everything else in this document follows from that correction and from the
owner's §2–§8.

## 1. Layer commitments (unchanged)

```
CURRENTNESS_PASS ≠ AUTHORITY_PASS ≠ PROPAGATION ≠ RELIANCE
EVALUATION ESTABLISHES THE PROPERTY · ISSUANCE CREATES THE RELIANCE
```

Each layer yields eligibility to enter the next, never the next layer's property.
The only consequential act in the slice is reliance issuance.

## 2. `currentness_epoch_digest` — as-of projection (CORRECTED)

```
currentness_epoch_digest(output_ref, as_of) = sha256(canonical({
  "output_ref": <literal>,
  "completeness_attestation_digest": <digest or null>,
  "operative_basis_records": [ {record_ref, record_digest, record_class,
                                effective_at, admitted_at}
      for each governing record R of THIS output with
          R.admitted_at <= as_of  AND  R.effective_at <= as_of ]
}))
```

Order: ascending `(effective_at, admitted_at, record_ref)`.

Frozen properties, each verified by a computed vector in the companion derivation
document:

```
future successor admitted but not operative at t1  → excluded from projection
same successor operative at t2                     → included
⇒ epoch_t1 != epoch_t2                             EPOCH-A 407a7c8f… vs EPOCH-B 6858b71d…

unrelated output receives an operative successor   → queried epoch unchanged
                                                    EPOCH-C == EPOCH-A

as_of is NOT a digested field                      → a clock tick alone never moves the epoch
```

**Completeness attestation participates** (owner §2): replacing the attestation
while leaving basis records untouched moves the epoch, because the epistemic basis
for a positive `CURRENT` changed even though the records did not.

Two rules use the epoch:

```
R-EPOCH-1  an authority decision is APPLICABLE only while the epoch it was
           computed against is still the present epoch for that artifact
R-EPOCH-2  currentness is RE-RESOLVED at reliance time, mandatorily;
           epoch equality is necessary, never sufficient
```

## 3. Currentness input — reused unchanged

States `CURRENT / SUPERSEDED / INELIGIBLE / UNKNOWN`; codes `R1–R11`, `G1–G10`;
the asymmetry rule; `UNKNOWN` denies. Not redesigned here. Only `CURRENT` may
reach the authority gate; the other three terminate before it, with
`authority_gate_invoked = FALSE` recorded as a positive fact.

## 4. Three distinct principals (owner §3, §4)

```
SYNTHETIC-SUBJECT-PRINCIPAL-001    the requesting subject whose use was authority-evaluated
SYNTHETIC-PRODUCER-PRINCIPAL-001   the identity that serialized the envelope
SYNTHETIC-CONSUMER-PRINCIPAL-001   the intended reliance consumer

REQUIRED  producer_principal != reliance_consumer_principal
```

No field may carry more than one role. The positive path is not a producer handing
evidence to itself.

## 5. Synthetic authority and admissibility — frozen objects (owner §8)

`synthetic_authority_required = TRUE`, `real_positive_CDC_subject_available =
FALSE`. Never named as CDC authority; `SYNTHETIC` visible in every identifier and
artifact.

```
SyntheticProducerProfile / SyntheticRelianceConsumerProfile {
  record_class, profile_id, principal_id, role, scope,
  permitted_requested_use [], validity_from, validity_until,
  revocation_state  NOT_REVOKED | REVOKED,
  assurance_class, profile_digest
}

SyntheticAuthorityBasisRecord {
  record_class  SYNTHETIC_AUTHORITY_BASIS,
  basis_id, principal_id, scope, permitted_requested_use [],
  validity_from, validity_until, revocation_state,
  supersedes / superseded_by, admitted_at, effective_at, record_digest
}

SyntheticAdmissibilityBasisRecord {
  record_class  SYNTHETIC_ADMISSIBILITY_BASIS,
  basis_id, artifact_class_admitted [], requested_use_admitted [],
  validity_from, validity_until, revocation_state,
  admitted_at, effective_at, record_digest
}
```

**Deterministic evaluation procedure**, ordered; first match wins; no other route:

```
1  artifact digest recomputed from bytes ≠ bound digest        → DENY  A8
2  no currentness_resolution_digest + epoch bound in request    → DENY  A9
3  no authority basis resolvable for (principal, scope)         → DENY  A4
4  authority basis present but malformed / digest irreproducible→ DENY  A5
5  authority basis revocation_state = REVOKED, or outside its
   validity interval at evaluation_time                         → DENY  A10
6  ≥2 operative authority bases conflict, no frozen precedence   → DENY  A6
7  principal not bound to scope                                  → DENY  A2
8  requested_use ∉ permitted_requested_use                       → DENY  A3
9  admissibility basis missing / invalid / revoked               → DENY  A4/A5/A10
10 escalation predicate of the frozen profile satisfied          → ESCALATE A7
11 otherwise                                                     → PROCEED  A1
```

"Valid admissibility basis" is thereby defined here, not left to implementation.

## 6. Authority decision record

Adds nothing to v0.1 except that `currentness_epoch_digest` is now the as-of
projection, and `valid_until` remains mandatory. A `PROCEED` authorizes exactly
one envelope; it creates no reliance and emits no event.

## 7. Propagation across a real boundary

Unchanged from v0.1 (A–E: serialize, materialize, separate consumer process reads
the file, validates independently, holds no producer in-memory state), with the
envelope now binding three roles separately:

```
GovernedPropagationEnvelope {
  envelope_id, schema_version,
  artifact_ref, artifact_digest, requested_use, scope,
  requesting_subject_principal,          ← whose use was authority-evaluated
  producer_identity {producer_principal, process_id, run_id, trace_id},
  intended_consumer_principal,           ← who may rely on this envelope
  currentness_resolution_digest, currentness_index_digest, currentness_epoch_digest,
  authority_decision_digest, authority_basis_refs [], admissibility_basis_refs [],
  evidence_refs [], produced_at, valid_until, assurance_class,
  envelope_digest
}
```

Closed schema: unknown field → `P8`; missing binding → `P9`; digest mismatch →
`P2`.

## 8. Consumer revalidation — fifteen checks (owner §5)

```
 1 envelope integrity            recompute envelope_digest                → P2
 2 schema closure                no unknown fields                        → P8
 3 envelope freshness            produced_at ≤ now ≤ valid_until          → P3
 4 artifact identity             recomputed from bytes                    → P4
 5 scope binding                                                          → P5
 6 subject-principal binding                                              → P6
 7 requested-use binding                                                  → P7
 8 INTENDED-CONSUMER binding     consumer_profile.principal_id ==
                                 envelope.intended_consumer_principal     → P12
 9 evidence resolvability        every evidence_ref resolves              → P9
10 producer identity verified    against the frozen producer profile      → P10
11 propagated authority identity recompute its digest                     → I5/I6
12 CURRENTNESS RE-RESOLUTION     resolve again, now                       → I2 / I9
13 EPOCH APPLICABILITY           epoch_now == epoch bound in the decision → I3
14 AUTHORITY RE-EVALUATION       full §5 procedure against the basis
                                 available to the consumer now            → I11
15 issuance only if 12, 13 and 14 all pass contemporaneously
```

Check 14 is the owner's §5 correction and it matters independently of 13: an
authority basis can be revoked or newly conflicting while both the decision's own
`valid_until` and the currentness epoch remain intact. Expiry of a decision is not
a proxy for the continued validity of what justified it.

**The propagated authority decision is evidence of the earlier evaluation. It is
never the reliance-time authority value of record.**

## 9. Reliance issuance — binds both moments (owner §6)

```
RelianceIssuanceRecord {
  record_class, reliance_id, consumer_id,
  artifact_ref, artifact_digest, requested_use, scope,
  requesting_subject_principal, consumer_principal,
  propagation_envelope_digest,
  currentness_resolution_digest          ← the RE-RESOLVED one
  currentness_epoch_digest               ← as observed at issuance
  propagated_authority_decision_digest   ← input to validation
  reliance_time_authority_decision_digest← the value relied upon
  issued_at, reliance_disposition ISSUED|REFUSED, reason_code,
  issuance_authorization_digest, attempt_record_digest,
  reliance_class SYNTHETIC_BOUNDED_DEMONSTRATION_RELIANCE,
  assurance_class, evidence_refs [], reliance_record_digest
}
```

Single-use per issuance authorization, attempt ledger keyed to the authorization
digest, consumed at first attempt, no automatic retry. Replay → `I8`.

## 10. Historical reliance preservation

```
HISTORICAL_RELIANCE_RECORD ≠ CURRENT_RELIANCE_ELIGIBILITY
```

A later correction never rewrites an issued record. Declared boundary, as before:
the post-correction determination lives on the successor side; the historical
record stays byte-identical and does not announce its own obsolescence.

## 11. Reason codes — actual counts

Reused unchanged: `R1–R11` (11), `G1–G10` (10) = 21.

New authority `A1–A10` (10) — `A10 AUTHORITY_BASIS_REVOKED` added, since revoked
is distinct from missing (`A4`) and from malformed (`A5`).

New propagation/consumer `P1–P12` (12) — `P12
ENVELOPE_INTENDED_CONSUMER_MISMATCH` added per owner §4.

New reliance `I1–I11` (11) — `I11
RELIANCE_REFUSED_AUTHORITY_NOT_CURRENT_AT_RELIANCE` added per owner §5/§7, so that
reliance-time authority failure is not collapsed into `I5` (decision not positive)
or `I4` (decision expired), neither of which is true in the authority-TOCTOU case.

```
new_reason_code_count  33   (A 10 · P 12 · I 11)
reused                 21
```

## 12. Test universe — recomputed

```
T-EARLY-01..05   (5)  five real outputs: currentness refuses; authority_gate_invoked FALSE;
                      no envelope; no reliance
T-POS-01..06     (6)  CURRENT → PROCEED → envelope materialized → separate consumer process →
                      re-resolution CURRENT + epoch unchanged + authority re-evaluated PROCEED →
                      reliance issued
T-CASE-A..N     (14)  as frozen in v0.1
T-CASE-O         (1)  wrong intended consumer                     → P12   (owner §4)
T-CASE-P         (1)  AUTHORITY-TOCTOU: authority standing revoked between t1 and t2 while the
                      artifact remains CURRENT → reliance-time re-evaluation fails → I11,
                      no issuance                                          (owner §7)
T-DIG-01..07     (7)  one per digest class
T-EPOCH-A/B/C    (3)  effective-time crossing moves the epoch; unrelated-output control does not
```

```
test_count = 5 + 6 + 14 + 1 + 1 + 7 + 3 = 37
```

`T-CASE-P` uses one frozen deterministic variant — revocation of the authority
standing — and combines no other mechanism. `T-CASE-K` (currentness TOCTOU) and
`T-CASE-P` (authority TOCTOU) are the two primary criteria: together they show
that neither layer can be rescued by the other's earlier verdict. `T-CASE-L`
remains measurable only if `T-POS-06` actually issues; otherwise it is recorded
unmeasurable, not failed.

## 13. Evidence artifacts

As v0.1, plus: the reliance-time authority decision record alongside the
propagated one; the three principal profiles; and process-boundary evidence
carrying producer and consumer identities, run ids and trace ids, with the
consumer's inputs recorded as paths only.

## 14. Digest classes

Seven, frozen with computed vectors in
`INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.1.md`: `currentness_epoch`,
`authority_basis_record`, `authority_decision`, `envelope`, `consumer_validation`,
`reliance_record`, `integration_package`.

## 15. Claim ceiling

```
CURRENTNESS_TO_AUTHORITY_INTEGRATION                  MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY       MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY  MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE    MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
HISTORICAL_RELIANCE_RECORD_PRESERVATION               MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
                                                       — only if T-POS-06 and T-CASE-L are exercised
```

Never shortened to bare `MEASURED`. Not established: real CDC institutional
authority; real CDC institutional reliance; official CDC issuance; external
consumer bypass resistance; production enforcement; legal effect; CDC acceptance;
distributed reliance consistency; cross-institution propagation. Plus the three
design-specific ceilings: the authority layer's content is fictional and only its
mechanics are measured; propagation is measured across one process boundary on one
machine; and refusal is measured while obsolescence is not announced by the
historical records themselves.

## 16. Return

```
INTEGRATION_SLICE_SEMANTIC_DESIGN = READY_FOR_OWNER_REVIEW_v0.2

currentness_epoch_is_as_of_projection            TRUE
currentness_epoch_binds_completeness_attestation TRUE
effective_time_crossing_moves_epoch              TRUE   (EPOCH-A ≠ EPOCH-B, computed)
unrelated_output_change_moves_epoch              FALSE  (EPOCH-C = EPOCH-A, computed)
producer_and_consumer_distinct                   TRUE
envelope_binds_intended_consumer                 TRUE
authority_revalidated_at_reliance                TRUE
reliance_record_binds_revalidated_authority      TRUE
authority_TOCTOU_case_present                    TRUE   (T-CASE-P)
synthetic_authority_objects_frozen               TRUE
synthetic_admissibility_semantics_frozen         TRUE
test_count                                       37
new_reason_code_count                            33
new_digest_class_count                            7
self_designed_and_self_adjudicated               TRUE
independent_review_claim                         FALSE
source_modified                                  FALSE
result_bearing_execution                         NONE
```
