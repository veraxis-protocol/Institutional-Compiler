# CDC CURRENTNESS-TO-RELIANCE INTEGRATION SLICE 001 — SEMANTIC DESIGN v0.1

```
assurance_class                    INTERNAL_TECHNICAL_DEMONSTRATION
semantic_mechanism_designer        VITALIY_REZNIK
criteria_author                    VITALIY_REZNIK
self_designed_and_self_adjudicated TRUE   (if this author later adjudicates the slice)
independent_review_claim           FALSE
result_bearing_execution           NONE
status                             READY_FOR_OWNER_REVIEW
```

This slice may demonstrate executable institutional-computation mechanics. It may
not establish real CDC authority, official CDC issuance, legal effect, production
reliance, or external institutional acceptance. Architecture and semantics only —
no implementation, no source changes, no desired verdict.

---

## 1. The commitment everything follows from

Each layer produces **eligibility to enter the next layer**, never the next
layer's property.

```
CURRENTNESS_PASS  ≠  AUTHORITY_PASS
AUTHORITY_PASS    ≠  PROPAGATION
PROPAGATION       ≠  RELIANCE

EVALUATION ESTABLISHES THE PROPERTY
ISSUANCE   CREATES  THE RELIANCE
```

Three consequences carried into the schemas below: no layer stores another
layer's verdict as its own fact; every cross-layer assertion travels as a *claim
with an epoch and an expiry*; and the only consequential act in the entire slice
is reliance issuance.

## 2. The central mechanism — `currentness_epoch_digest`

The TOCTOU case of §8 is not defended by a check bolted on at the end. It is made
structurally impossible by binding, and this is the one design idea the slice
stands or falls on.

```
currentness_epoch_digest =
    sha256(canonical(ordered basis records governing THIS output, each reduced to
                     {record_ref, record_digest, record_class, effective_at, admitted_at}))
```

Artifact-scoped deliberately. It moves when the governing basis **for this
output** moves, and does not move when an unrelated output is corrected — so
fail-closed does not degrade into fail-noisy.

Two rules use it:

```
R-EPOCH-1  An authority decision is APPLICABLE only while the currentness epoch it
           was computed against is still the present epoch for that artifact.
           epoch_at_reliance ≠ epoch_bound_in_decision  →  the decision does not
           apply; reliance is refused; fresh authority evaluation is required.

R-EPOCH-2  Currentness is RE-RESOLVED at reliance time, mandatorily. Epoch equality
           is necessary but never sufficient.
```

Why both, and why re-resolution is mandatory rather than preferred: epoch equality
proves the basis did not move. It does not prove the basis is *reachable and
attested* now. If it is unreachable at reliance time, re-resolution yields
`UNKNOWN` and the slice fails closed — which an epoch comparison alone would
silently pass. §7's "strongly prefer" is therefore promoted to a requirement, and
the fallback it contemplates is not used.

**An old positive authority decision can never outrank newer currentness**, because
the decision's applicability is defined in terms of the epoch, not in terms of its
own timestamp.

## 3. Currentness input — reused, not redesigned

Currentness Slice 001 semantics are consumed unchanged: states `CURRENT`,
`SUPERSEDED`, `INELIGIBLE`, `UNKNOWN`; resolver codes `R1`–`R11`; gate codes
`G1`–`G10`; the asymmetry rule (`CURRENT` requires an attested-complete basis);
`UNKNOWN` denies. Nothing in this slice may modify or reinterpret them.

```
CURRENT                          → may proceed to authority/admissibility
SUPERSEDED / INELIGIBLE / UNKNOWN → TERMINATE before the authority gate
```

Required observable on every path:

```
authority_gate_invoked  TRUE | FALSE
```

For a terminated path it must be `FALSE` — recorded as a fact, not inferred from
the absence of an authority record.

## 4. Authority / admissibility — bounded, and visibly synthetic

```
synthetic_authority_required      TRUE
real_positive_CDC_subject_available FALSE
```

No executable real-CDC authority primitive exists to reuse, and the frozen
population contains no real output that is both currently eligible and genuinely
authorized. The slice therefore uses a declared synthetic authority profile.

**Naming discipline, absolute:** the synthetic profile is never called CDC
authority. Its identifiers, its records and every artifact that references it
carry `SYNTHETIC` visibly:

```
authority_profile_id   CDC-SYNTHETIC-AUTHORITY-PROFILE-001
principal_id           SYNTHETIC-PRINCIPAL-001
authority_class        SYNTHETIC_BOUNDED_DEMONSTRATION_AUTHORITY
derived_from_real_cdc_authority  false
```

`AuthorityDecisionRecord`:

```
record_class                   AUTHORITY_DECISION
decision_id
artifact_ref
artifact_digest
requested_use
scope
requesting_principal
currentness_resolution_digest        the exact resolution this decision consumed
currentness_epoch_digest             §2 — the binding that governs applicability
evaluation_time
authority_basis_refs []              + per-ref digests
admissibility_basis_refs []          + per-ref digests
authority_class                      SYNTHETIC_BOUNDED_DEMONSTRATION_AUTHORITY
decision                             PROCEED | DENY | ESCALATE
reason_code / reason_code_id
valid_until                          decisions expire; absence of expiry is prohibited
assurance_class                      INTERNAL_TECHNICAL_DEMONSTRATION
authority_decision_digest            self-excluded
```

**Currently eligible ≠ institutionally authorized**, and the schema enforces the
distinction structurally: currentness enters only as two bound digests, never as a
field the authority layer can restate or overwrite.

A `PROCEED` authorizes exactly one thing: production of one propagation envelope.
It creates no reliance and emits no event.

## 5. Governed propagation — a real boundary, not a return value

Propagation qualifies only if all five hold, and the evidence must show each:

```
A  producer serializes a closed envelope
B  the envelope is durably materialized at a path
C  a SEPARATE CONSUMER PROCESS reads that file
D  the consumer independently validates identity, binding and evidence
E  the consumer holds no reference to producer in-memory state
```

Concretely: the consumer is invoked as its own process whose entire input is three
paths — envelope file, frozen governed state directory, consumer profile — and
whose evidence records its own process identity, run id and trace id, distinct
from the producer's. An in-process object handoff is not propagation and must not
be reported as one.

`GovernedPropagationEnvelope`:

```
record_class                    GOVERNED_PROPAGATION_ENVELOPE
envelope_id
schema_version
artifact_ref
artifact_digest
requested_use
scope
requesting_principal
currentness_resolution_digest
currentness_index_digest
currentness_epoch_digest
authority_decision_digest
authority_basis_refs []
admissibility_basis_refs []
evidence_refs []                 every record a consumer must be able to resolve
produced_at
valid_until
producer_identity                {producer_id, process_id, run_id, trace_id}
assurance_class
envelope_digest                  self-excluded
```

**Closed schema.** An unknown field, a missing binding, or a digest mismatch fails
closed — `P8`, `P9`, `P2` respectively. The envelope is parsed against the frozen
schema, not merged into it.

## 6. Consumer revalidation — mandatory, and it re-resolves

The consumer may never reason *"authority was positive earlier, therefore reliance
is allowed now."* At reliance time it establishes, independently:

```
1  envelope integrity            recompute envelope_digest                    → P2
2  envelope schema closure       no unknown fields                            → P8
3  envelope freshness            produced_at ≤ now ≤ valid_until              → P3
4  artifact identity             recompute artifact digest from bytes         → P4
5  scope binding                                                             → P5
6  principal binding                                                         → P6
7  requested-use binding                                                     → P7
8  evidence resolvability        every evidence_ref resolves                  → P9
9  producer identity verified    against the frozen producer profile          → P10
10 authority decision identity   recompute authority_decision_digest          → I5/I6
11 authority decision freshness  now ≤ decision.valid_until                   → I4
12 CURRENTNESS RE-RESOLUTION     resolve again, now                           → I2 / I9
13 EPOCH APPLICABILITY           epoch_now == epoch_bound_in_decision         → I3
```

Steps 12 and 13 are the continuity mechanism. Step 12 asks *what is true now*;
step 13 asks *whether the earlier authorization still speaks about now*. Passing
12 without 13 would let an authority decision computed against a superseded basis
survive; passing 13 without 12 would trust a stale attestation. Both are required.

## 7. Reliance issuance — the only consequential act

```
RelianceIssuanceRecord {
  record_class                  RELIANCE_ISSUANCE
  reliance_id
  consumer_id
  artifact_ref
  artifact_digest
  requested_use
  scope
  principal
  propagation_envelope_digest
  currentness_resolution_digest        the RE-RESOLVED one, not the propagated one
  currentness_epoch_digest             as observed at issuance
  authority_decision_digest
  issued_at
  reliance_disposition                 ISSUED | REFUSED
  reason_code / reason_code_id
  issuance_authorization_digest        single-use authority for this issuance
  attempt_record_digest
  assurance_class                      INTERNAL_TECHNICAL_DEMONSTRATION
  reliance_class                       SYNTHETIC_BOUNDED_DEMONSTRATION_RELIANCE
  evidence_refs []
  reliance_record_digest               self-excluded
}
```

Note the field that matters: the record binds the **re-resolved** currentness
resolution, not the one that travelled in the envelope. The propagated value is
input to validation; it is never the value of record.

Issuance is single-use per issuance authorization, with an attempt ledger keyed to
the authorization digest, consumed at first issuance attempt, no automatic retry —
the pattern already frozen in this programme. Replay of a consumed authorization
is `I8`.

A positive record means exactly: *a bounded synthetic reliance transition occurred
under the frozen demonstration profile*. It may not be labelled official CDC
reliance anywhere.

## 8. Reliance refusal conditions (frozen)

No issuance if any hold — each with its own code, none collapsed:

```
currentness ≠ CURRENT at reliance time              I2
currentness epoch moved since authority evaluation  I3
authority decision expired                          I4
authority decision not PROCEED                      I5
envelope invalid (any P-failure)                    I6
caller attempts to assert reliance directly         I7
issuance authorization already consumed             I8
currentness basis missing/unreachable at reliance    I9
authority basis competing/unresolved                I10
scope / principal / use / artifact-digest mismatch  P5 / P6 / P7 / P4 → I6
envelope tampered or substituted                    P2 / P11 → I6
evidence binding incomplete                         P9 → I6
```

## 9. Historical reliance preservation

```
HISTORICAL_RELIANCE_RECORD  ≠  CURRENT_RELIANCE_ELIGIBILITY
```

A later correction never rewrites an issued reliance record. The record remains
evidence that reliance occurred at time *t* under the state then obtaining; the
correction governs *subsequent* eligibility only.

**A boundary declared now rather than discovered later.** As in the M12 correction
successor, the post-correction eligibility determination will live on the
successor side. The historical reliance record stays byte-identical and carries no
marker that it has been overtaken. What the slice can measure is that *later*
reliance is refused — not that the earlier record announces its own obsolescence.
That limit belongs in the claim ceiling from the start.

## 10. Ordering

```
currentness resolve
   → [CURRENT only] authority/admissibility evaluate        authority_gate_invoked = TRUE
      → [PROCEED only] envelope produce + durably materialize
         → separate consumer process reads the file
            → consumer revalidates (13 checks, incl. re-resolution + epoch)
               → [all pass] issuance authorization consumed → reliance issued
```

Every arrow is a refusal point. No arrow may be skipped, and no downstream stage
may be entered on an upstream assertion that was not independently revalidated.

## 11. Reason-code universe

Reused unchanged from Currentness Slice 001: resolver `R1`–`R11` (11), use gate
`G1`–`G10` (10).

New, authority `A1`–`A9` (9):

```
A1 AUTHORITY_AND_ADMISSIBILITY_SATISFIED        → PROCEED
A2 PRINCIPAL_NOT_AUTHORIZED_FOR_SCOPE           → DENY
A3 REQUESTED_USE_OUTSIDE_SCOPE                  → DENY
A4 ADMISSIBILITY_BASIS_MISSING                  → DENY
A5 ADMISSIBILITY_BASIS_INVALID                  → DENY
A6 AUTHORITY_BASIS_AMBIGUOUS_COMPETING          → DENY (fail closed, no precedence invented)
A7 AUTHORITY_ESCALATION_REQUIRED                → ESCALATE
A8 ARTIFACT_DIGEST_MISMATCH_AT_AUTHORITY        → DENY
A9 CURRENTNESS_RESOLUTION_NOT_BOUND             → DENY
```

New, propagation/consumer `P1`–`P11` (11):

```
P1  ENVELOPE_VALID
P2  ENVELOPE_DIGEST_MISMATCH
P3  ENVELOPE_EXPIRED
P4  ENVELOPE_ARTIFACT_MISMATCH
P5  ENVELOPE_SCOPE_MISMATCH
P6  ENVELOPE_PRINCIPAL_MISMATCH
P7  ENVELOPE_REQUESTED_USE_MISMATCH
P8  ENVELOPE_UNKNOWN_FIELD_PRESENT
P9  ENVELOPE_EVIDENCE_BINDING_INCOMPLETE
P10 ENVELOPE_PRODUCER_IDENTITY_UNVERIFIED
P11 ENVELOPE_SUBSTITUTED
```

New, reliance `I1`–`I10` (10): as listed in §8, with `I1 RELIANCE_ISSUED`.

```
reused_reason_codes  21
new_reason_codes     30   (A 9 + P 11 + I 10)
total_in_play        51
```

Closed sets. Adding a code after execution is a criteria modification and is
prohibited.

## 12. Test universe — enumerated, then counted

```
T-EARLY-01..05    (5)  the five real historical outputs: currentness refuses;
                       authority_gate_invoked FALSE; no envelope; no reliance
T-POS-01          (1)  synthetic subject resolves CURRENT
T-POS-02          (1)  authority PROCEED under the synthetic profile
T-POS-03          (1)  envelope produced and durably materialized at a path
T-POS-04          (1)  separate consumer process reads the file; distinct process identity
T-POS-05          (1)  consumer revalidates: re-resolution CURRENT and epoch unchanged
T-POS-06          (1)  reliance issuance record produced, single-use consumed

T-CASE-A          (1)  CURRENT + authority DENY        → no propagation, no reliance
T-CASE-B          (1)  CURRENT + authority ESCALATE    → no reliance
T-CASE-C          (1)  tampered envelope               → P2 → I6
T-CASE-D          (1)  wrong artifact                  → P4 → I6
T-CASE-E          (1)  wrong scope                     → P5 → I6
T-CASE-F          (1)  wrong principal                 → P6 → I6
T-CASE-G          (1)  expired authority decision      → I4
T-CASE-H          (1)  expired envelope                → P3 → I6
T-CASE-I          (1)  caller asserts reliance directly→ I7
T-CASE-J          (1)  replay consumed authorization   → I8
T-CASE-K          (1)  TOCTOU: correction operative between authority and reliance
                       → re-resolution SUPERSEDED and epoch moved → I2 with I3 recorded
T-CASE-L          (1)  issued reliance, later correction → historical record byte-identical,
                       subsequent reliance refused
T-CASE-M          (1)  currentness basis missing at reliance → I9 (fail closed)
T-CASE-N          (1)  competing/unresolved authority basis → A6 → no propagation

T-DIG-01..07      (7)  one per new digest class:
                       currentness_epoch, authority_decision, envelope,
                       consumer_validation, reliance_record, authority_basis_record,
                       integration_package
```

```
test_count = 5 + 6 + 14 + 7 = 32
```

`T-CASE-K` is the primary criterion of the slice. `T-CASE-L` is the only test that
can establish historical reliance preservation, and it is the only one requiring a
successful issuance first — if `T-POS-06` does not occur, `T-CASE-L` is
unmeasurable and must be recorded as such rather than assumed.

## 13. Evidence artifacts

Immutable, hash-addressable, none dependent on console text:

- currentness resolution records (producer side and reliance-time re-resolution — **both**, so the pair can be compared);
- authority decision records, with basis refs and digests;
- the materialized envelope **file** (the durable boundary object itself);
- consumer validation records: all 13 checks, each with expected/observed;
- reliance issuance records, issued or refused, with reason codes;
- issuance attempt ledger keyed to the issuance authorization digest;
- process-boundary evidence: producer and consumer process identities, run ids, trace ids, and the fact that the consumer's inputs were paths only;
- adversarial ledger for the 14 cases: mutation applied, expected code, observed code;
- digest observations for the 7 new classes, with reference vectors;
- an integration raw execution package binding all member identities.

## 14. Digest classes and derivation

Seven new classes, each to be specified in
`INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.1.md` **before implementation**, using
the canonical rule already frozen for this programme (UTF-8, sorted keys,
`ensure_ascii=false`, separators `,` and `:`, no indentation, no trailing newline,
self-digest excluded by key removal, unprefixed lowercase hex):

```
currentness_epoch_digest        ordered basis records, reduced form per §2
authority_decision_digest       decision minus authority_decision_digest
envelope_digest                 envelope minus envelope_digest
consumer_validation_digest      validation record minus its own digest
reliance_record_digest          reliance record minus reliance_record_digest
authority_basis_record_digest   one basis record as stored
integration_package_digest      package minus package_digest, members as {path,bytes,sha256}
```

Real reference vectors are to be computed and published in that document before any
execution, as was done for Currentness Slice 001 — where the package digest then
reproduced on the first attempt from the published rule.

## 15. Claim ceiling

Candidate maxima, each assurance-qualified and never shortened to bare `MEASURED`:

```
CURRENTNESS_TO_AUTHORITY_INTEGRATION                  MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY       MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY  MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE    MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
HISTORICAL_RELIANCE_RECORD_PRESERVATION               MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
                                                       — only if T-POS-06 and T-CASE-L are actually exercised
```

Not established:

```
real_CDC_institutional_authority          real_CDC_institutional_reliance
official_CDC_issuance                     external_consumer_bypass_resistance
production_enforcement                    legal_effect
CDC_acceptance                            distributed_reliance_consistency
cross_institution_propagation
```

Three further ceilings that follow from this design specifically and belong in the
frozen list:

- **The authority layer's content is fictional; only its mechanics are measured.**
  A `PROCEED` from a synthetic profile demonstrates that the gate binds, expires
  and refuses correctly. It demonstrates nothing about whether any real authority
  would have said yes.
- **Propagation is measured across one process boundary on one machine.** Nothing
  here bears on network transport, multiple consumers, or consistency between
  them.
- **Refusal is measured; obsolescence is not announced.** Per §9, a historical
  reliance record does not carry its own supersession. A consumer that reads the
  record directly, without the eligibility path, is unaffected — the same
  recorded-≠-propagated boundary that governs the artifacts, now governing the
  reliance records too.

## 16. Return

```
INTEGRATION_SLICE_SEMANTIC_DESIGN = READY_FOR_OWNER_REVIEW

synthetic_authority_required           TRUE
real_positive_CDC_subject_available    FALSE
test_count                             32
new_reason_codes                       30   (A 9 · P 11 · I 10)
reused_reason_codes                    21   (R 11 · G 10, unchanged)
new_digest_classes                      7
self_designed_and_self_adjudicated     TRUE
independent_review_claim               FALSE
result_bearing_execution               NONE
prior_evidence_modified                FALSE
exact_source_changes                   NOT SUPPLIED — implementer's lane
```

Frozen before implementation so that it can serve as the pre-result criteria
record. The digest-derivation document is a required companion and must be frozen
before any execution.
