# INTEGRATION SLICE 001 — CRITERION EVIDENCE PROJECTION v0.1

```
classification              EVIDENCE_PROJECTION_ONLY
SEMANTIC_CONTROL            FALSE
SEMANTIC_CRITERIA_MODIFIED  FALSE
TEST_COUNT                  41
controlling semantic design CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md
                            sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
                            — unchanged by this document
controlling digest derivation INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.4.md
                            sha256 494c91ace109ba050c40b72cc2f0f1cc64366386376212d50edbb3b9a418d1e7
                            — unchanged by this document
result_bearing_execution    NONE
```

This document adds no criterion, changes no expected outcome, no reason code and
no claim ceiling. It specifies only **what a run must archive** so that a later
adjudicator can determine what each criterion actually tested without opening
implementation or test source. Where this document and the semantic design could
be read as differing, the semantic design governs.

## 0. The defect this projection exists to close

The RUN-001 criteria ledger recorded four fields per criterion —
`{classname, node_name, gate_outcome, time}` — and nothing else. The strongest
archived fact was therefore *the test executed and passed*, from which no
criterion proposition follows. The objective here is stated as a hard target:

```
TEST_EXECUTED_AND_PASSED must no longer be the strongest archived fact
```

## 1. Projection rules

1. **Observed values are archived always, not only on divergence.** A criterion
   that records agreement without recording what agreed has archived nothing.
2. **`expected` and `observed` are separate fields.** They are never collapsed
   into a boolean, and the boolean is never the only survivor.
3. **Every identity that entered the check is archived by digest**, so the
   adjudicator can re-derive rather than trust.
4. **Absence is recorded positively.** `authority_gate_invoked: false`,
   `envelope_produced: false`, `reliance_issued: false` are observations; a
   missing field is not.
5. **No adjudication vocabulary.** The projection carries no `PASS`, `FAIL`,
   `SATISFIED`, `CONFORMANT` as a determination. `node_outcome` may be archived,
   but it is explicitly **not load-bearing** and must be marked so.
6. **Comparisons are archived as data**, not as verdicts: both operands and the
   comparison result, leaving the determination to the adjudicator.
7. **Digests unprefixed**, per the frozen derivation.

## 2. Universal observation envelope — required for all 41

```
CriterionObservation {
  criterion_id                  e.g. T-CASE-K
  node_id                       the executing node identifier
  semantic_reference            section of semantic design v0.4 defining the criterion
  scenario_id                   the fixture/scenario actually exercised
  inputs []                     { role, ref, digest }        every object entering the check
  expected_condition            verbatim from the frozen criterion
  observed_value                the machine value actually produced
  observed_reason_code          code id and name, or NOT_APPLICABLE
  observed_decision             decision/verdict/state, or NOT_APPLICABLE
  outputs []                    { role, ref, digest }        every object the check produced
  not_produced []               objects the criterion required to be absent, named
  evidence_refs []              resolvable pointers to the archived records above
  observed_at
  node_outcome                  archived, NON_LOAD_BEARING: true
  observation_digest            self-excluded
}
```

**Open dependency, flagged rather than assumed.** Two digest classes are implied
and are **not** frozen by this document: `criterion_observation_digest` and
`criterion_ledger_digest`. Derivation v0.4 §11 requires any new class to be
published in a versioned successor **before** the execution that produces it.
A derivation v0.5 must therefore be published before RUN-002. This projection
does not create those classes and must not be read as having frozen them.

## 3. Group projections — additional required fields

### T-EARLY-01..05 · five real outputs, early termination

```
artifact_ref, artifact_digest_expected, artifact_digest_observed (recomputed from bytes)
currentness_index_digest, currentness_epoch_digest (as_of recorded separately)
basis_records []              { record_ref, record_digest, record_class, effective_at, admitted_at }
completeness_attestation_digest   digest or null, with which
observed currentness_state, observed reason_code (id + name)
controlling_successor_ref, correction_event_ref
gate_decision, gate_reason_code
authority_gate_invoked        false — the positive fact this group exists to show
not_produced                  authority_decision, envelope, consumer_validation, reliance_record
resolution_record_digest, use_gate_decision_digest
```

Without `authority_gate_invoked: false` archived explicitly, early termination is
indistinguishable from an authority evaluation that happened to deny.

### T-POS-01..06 · the positive path

```
T-POS-01  observed currentness_state, reason_code, epoch digest + as_of,
          completeness_attestation_digest and whether it reproduced, basis coverage
T-POS-02  authority_decision_digest, observed decision + reason_code,
          bound currentness_resolution_digest and currentness_epoch_digest,
          valid_until, authority/admissibility basis refs + digests,
          principal, scope, requested_use
T-POS-03  envelope file path, persisted-file sha256, recomputed envelope_digest,
          produced_at, valid_until, and the three principal fields separately:
          requesting_subject_principal, producer_identity, intended_consumer_principal
T-POS-04  producer_process_identity { process_id, run_id, trace_id }
          consumer_process_identity { process_id, run_id, trace_id }
          processes_distinct: true/false as an observed comparison
          consumer_inputs []  the paths, and only the paths, the consumer received
          consumer_read_record  evidence the consumer read the file from disk
T-POS-05  checks [] all sixteen: { check_id 1..16, check_name, expected, observed, passed }
          re_resolved_currentness_resolution_digest, observed_currentness_epoch_digest,
          epoch_bound_in_decision, reliance_time_authority_decision_digest,
          consumer_validation_digest
T-POS-06  reliance_record_digest, reliance_disposition, reason_code,
          propagated_authority_decision_digest, reliance_time_authority_decision_digest,
          re-resolved currentness_resolution_digest, currentness_epoch_digest,
          issuance_authorization_digest (persisted-file), attempt_record_digest
          (persisted-file), attempt_state, write-order timestamps for the three files
```

`T-POS-04` is the criterion the RUN-001 ledger could least support: a node outcome
cannot distinguish a separate process from a function call. Two distinct process
identities and the consumer's input paths are the minimum that can.

### T-CASE-A..S · nineteen adversarial cases

Every case archives, in addition to the universal envelope:

```
mutation_applied              exact description of what was altered
mutated_object                { ref, digest_before, digest_after }  where a mutation applies
terminating_layer             CURRENTNESS | AUTHORITY | PROPAGATION | CONSUMER | ISSUANCE
expected_reason_code / observed_reason_code      both, as id + name
downstream_not_produced []    named, per rule 4
```

Case-specific minima:

```
A  observed authority decision DENY + reason; envelope not produced
B  observed ESCALATE + A7; reliance not produced
C  envelope_digest before and after tampering; observed P2
D/E/F/O  the mismatched field: expected value and observed value, separately
         (D artifact, E scope, F subject principal, O intended consumer)
G  decision valid_until, evaluation instant, observed I4,
   AND check_15_reached: false  — the freshness failure must be shown to be terminal
H  envelope valid_until, evaluation instant, observed P3
I  the caller assertion attempt as submitted, observed I7
J  authorization digest, first-use attempt_record digest and state,
   replay attempt outcome, observed I8
K  epoch_before and epoch_after with both as_of values, re-resolved currentness state,
   observed I2, and I3 recorded alongside — both, since the case is the conjunction
L  reliance_record_digest BEFORE the later correction and AFTER it (must be identical),
   correction record identity, and the subsequent reliance attempt with its refusal code
M  the basis reference that could not be resolved, observed I9
N  competing basis refs and digests (all claimants), controlling_successor_ref: null,
   observed A6
P  authority basis revocation_state before and after, artifact currentness observed as
   CURRENT at the reliance instant, decision valid_until NOT expired, observed I11
   — the last two fields are what distinguish P from G
Q/R/S  the basis object, its stored record_digest, the recomputed digest and whether
       they agree; observed A11 / A12 / A13 respectively
```

`T-CASE-P` and `T-CASE-G` are otherwise confusable in an archive: both end without
reliance. Only the pair *(decision still fresh, authority basis revoked)* versus
*(decision expired)* separates them, so both fields are mandatory in both cases.

### T-DIG-01..08 · one per digest class

```
digest_class
digested_object_reference     what exactly was digested, by reference
canonical_byte_count          observed
computed_digest               observed
published_reference_vector    vector id and its published digest, where one exists
comparison_result             observed equality as data, not as a verdict
```

The computed digest and the byte count are the load-bearing observations. Without
them the archive shows that a test asserting a vector passed, not that the vector
reproduced.

### T-EPOCH-A/B/C · the as-of projection

```
as_of                         the instant used
reduced_object                the exact object entering the digest, verbatim
canonical_byte_count          observed
computed_digest               observed
published_vector              EPOCH-A / EPOCH-B / EPOCH-C with its published digest
comparison_result             A vs B, and C vs A, each as observed operands + result
```

Since derivation v0.4 publishes the complete inputs for all three, these three
criteria become fully independently recomputable once the reduced object and the
computed digest are archived.

## 4. Index — all 41

```
T-EARLY-01..05    5   §3.1   early termination, per real output
T-POS-01..06      6   §3.2   positive path, six stages
T-CASE-A..S      19   §3.3   adversarial, nineteen cases
T-DIG-01..08      8   §3.4   digest classes 1..8
T-EPOCH-A/B/C     3   §3.5   as-of projection vectors
                 ---
                  41
```

Node identifiers observed in RUN-001 map one-to-one onto this set and are carried
unchanged; this projection renames nothing.

## 5. What this projection does not do

It does not adjudicate. It fixes no outcome, asserts no criterion result, and
grants no claim. An archive built to this projection may still record observations
that a later adjudicator finds insufficient, divergent or unsupportive — that
determination is the adjudicator's and is deliberately left open here.

It also does not, by itself, make any target claim of the slice supported. The six
pipeline maxima remain properties of an executed pipeline, and no projection of
what to archive can substitute for having run it.
