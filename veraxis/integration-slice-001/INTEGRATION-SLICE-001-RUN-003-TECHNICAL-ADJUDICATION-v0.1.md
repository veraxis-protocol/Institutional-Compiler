# INTEGRATION SLICE 001 — RUN-003 TECHNICAL ADJUDICATION v0.1

```
owner                      ARKADIY MITEIKO
adjudicator                VITALIY REZNIK
adjudication_class         INTERNAL_TECHNICAL_ADJUDICATION
independent_adjudication   FALSE
independent_review_claim   FALSE
reason                     ADJUDICATOR_AUTHORED_CONTROLLING_SEMANTIC_ARTIFACTS
assurance_class            INTERNAL_TECHNICAL_DEMONSTRATION
result_bearing_execution   NONE
```

I authored the semantic design, the evidence projections and the digest
derivation applied below. This adjudication may support an owner claim decision;
it does not itself create independent assurance. No evidence was modified,
repaired, reconstructed or re-run.

## 1. Bound identities

```
semantic design v0.4        03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
projection v0.1             8fed52234f418bbe4ac8d5e2a98fb31952c69ed514d2e8ea27cb1348eb12db35
projection v0.2             00af89d21fda41adaf4a95d5938d3b6fc90666d4ebf902b9c205aa42e7974db2
projection v0.3             7adcc39f5656fa3fdc837bf3049a7a4a1be38947aed41b2fc0ccc23cc4781298
digest derivation v0.6      dc3613ece70ffd9c3c816750ccb41d0df7e8683a81377f3fa2f419c344f9f6a0
implementation              fa96f5c3590f54118cd926a84370be6022a80b35 / 65a704cd9c70aef983b62ecc8176793e20004772
EXEC-003 issuance           8384217cf97d3c6a836685c9c278c216f0d25238ab345fd12565a9383f0f387c
evidence commit / tree      53a62648c51be9745785252a2e76b950817e907a / 42beb7f790e4a84a9e381b111dbf238bc0f77838
raw package sha / digest    3b3db405b613e81844a8bab47559efa8c74bca363b8551021e75c12bd26f8086 / 62588554f01ad426857fbfcddae6e316b6b367f6765e900076a7d360815b8654
ledger sha / Class-10       2ad338f4c7aef3ce2e1c10c1cdd83c388dc3cd676d554606f7646191f87d8368 / 6c7fa26a7caa0ba9df3a359dfc85fa205eaf4bdd2dbb2f4ec658ec0daff1ebd7
```

## 2. First gate — evidence identity integrity

```
evidence commit / tree                        exact
raw package persisted sha                     exact
raw package digest                            REPRODUCED
ledger persisted sha                          exact
ledger Class-10 digest                        REPRODUCED
criteria_total / observations / unique ids    41 / 41 / 41
criterion_order and observations[] order      exact frozen order
41 observation persisted-file sha256          41/41 reproduce, 0 divergences
41 Class-9 observation digests                41/41 reproduce, 0 divergences
bindings (execution_id, semantic design, projection v0.3,
          implementation commit, implementation tree)   205/205 exact, 0 divergences

evidence_identity_integrity = TRUE
```

**This gate is not the adjudication.** 41 structurally conformant observations are
not 41 semantically satisfied criteria; Class-9 and Class-10 reproduction establish
serialization integrity, not criterion propositions. What follows evaluates content.

## 3. Criterion adjudication — 41 rows

```
SATISFIED_BY_ARCHIVED_EVIDENCE       40
NOT_SATISFIED_BY_ARCHIVED_EVIDENCE    0
INSUFFICIENT_ARCHIVED_EVIDENCE        1   (T-POS-04)
NOT_APPLICABLE_BY_FROZEN_DESIGN       0
```

| criterion | observed content relied upon | adjudication |
|---|---|---|
| T-EARLY-01..05 | per output: artifact digest expected = observed; `authority_gate_invoked: false`; decision DENY / `R2 OUTPUT_SUPERSEDED`; basis records with digests; four `not_produced` entries — authority decision, envelope, consumer validation, reliance | SATISFIED ×5 |
| T-POS-01 | CURRENT / `R1`; completeness attestation digest present and reproducing; basis coverage | SATISFIED |
| T-POS-02 | PROCEED / `A1`; decision digest; bound currentness resolution and epoch digests; authority and admissibility basis refs with digests | SATISFIED |
| T-POS-03 | envelope materialized; recorded digest = recomputed digest; persisted path and bytes; three principal roles distinct | SATISFIED |
| T-POS-04 | see §4 | **INSUFFICIENT** |
| T-POS-05 | all sixteen checks archived with `check_id` 1..16, each carrying expected and observed operands; re-resolution CURRENT; epoch applicable; propagated decision fresh; reliance-time re-evaluation PROCEED; issuance gate last | SATISFIED |
| T-POS-06 | see §5 | SATISFIED |
| T-CASE-A | authority DENY / `A10`; no envelope, no consumer validation, no reliance | SATISFIED |
| T-CASE-B | ESCALATE / `A7`; no reliance | SATISFIED |
| T-CASE-C/D/E/F/H/O | consumer REFUSED / `I6` with the mutated operand recorded; downstream not produced | SATISFIED ×6 |
| T-CASE-G | check 12 observed `{valid_until 11:00, now 13:00} → passed false`; `check_15_reached: false`; REFUSED / `I4` | SATISFIED |
| T-CASE-I | REFUSED / `I7` | SATISFIED |
| T-CASE-J | REFUSED / `I8`; first-use attempt and disposition archived | SATISFIED |
| T-CASE-K | see §6 | SATISFIED |
| T-CASE-L | see §7 | SATISFIED |
| T-CASE-M | REFUSED / `I9` | SATISFIED |
| T-CASE-N | DENY / `A6`; competing basis refs archived | SATISFIED |
| T-CASE-P | see §6 | SATISFIED |
| T-CASE-Q/R/S | DENY / `A11` / `A12` / `A13`; basis object and digest-reproduction result archived per case | SATISFIED ×3 |
| T-DIG-01..08 | canonical byte counts and computed digests archived per class; DIG-01 185 B `407a7c8f…` = published EPOCH-A, DIG-02 431 B `7ad84cfb…` = published BASIS-AUTH-1, DIG-08 398 B `1c7ac979…` = published PROFILE-PRODUCER-1; DIG-03..07 carry byte counts and digests for classes that have no published fixture vector | SATISFIED ×8 |
| T-EPOCH-A/B/C | A 185 B `407a7c8f…`; B 414 B `6858b71d…`; C 185 B `407a7c8f…`. Recomputed against derivation v0.6, not taken from the archived boolean: **A ≠ B** and **C = A** both hold | SATISFIED ×3 |

## 4. T-POS-04 — special review

```
A  SEPARATE_OS_PROCESS_BOUNDARY_ESTABLISHED     = TRUE
B  PATH_ONLY_CONSUMER_INPUT_ESTABLISHED         = TRUE
C  FULL_T_POS_04_PROJECTED_EVIDENCE_MINIMUM_SATISFIED = FALSE
D  DEVELOPMENT identities affect EVIDENTIARY BINDING, not the separation proposition
E  the null persisted-envelope identity weakens but does not destroy independent
   support for the consumer-read proposition
```

**A.** Producer process 66048, consumer process 66058, `processes_distinct: true`,
`producer_state_shared: false`, and the consumer identity is marked *"emitted by
the consumer process in its own result"* — self-reported by the other process
rather than asserted by the producer. Two distinct OS processes are established.

**B.** Eight input paths enumerated, `consumer_inputs_were_paths_only: true`, no
shared producer state. Established.

**C.** Two projected fields are absent and I do not normalize them into success:

- `consumer_process_identity.run_id` and `.trace_id` are **absent**; the object
  carries `consumer_principal` and `source` instead. Projection v0.1 §3 names all
  three explicitly. The raw `RUN-003-PROCESS-BOUNDARY-OBSERVATION` has the same
  shape, so the gap is not curable from another archived record.
- `persisted_envelope_path: "None"` (a stringified null) and
  `persisted_envelope_sha256: null`.

**A misdescribed comparison, recorded rather than smoothed.** The field
`digest_matches_persisted_envelope: true` compares
`consumer_validation_envelope_digest` with
`envelope_digest_recorded_in_envelope` — both `e3ad5904…`. Neither operand is the
sha256 of a persisted envelope file; that value is `null` in the same record. The
field name therefore claims a comparison the record does not perform.

**E.** Partial cure from archived artifacts, stated precisely. The envelope **is**
archived at `run-003/evidence/pipeline/positive/envelope.json`, 2012 bytes,
persisted sha256 `d58eb91afa460af0cba13d9c74ffa5de5373de1e140019636c4103e33b04e065`;
its internal `envelope_digest` recomputes to `e3ad5904…`, equal to the consumer's
validation digest. So the consumer computed, over 2012 bytes, a digest identical
to the one derivable from the archived envelope — strong support that it processed
that content. What remains unestablished is the recorded link from *that file's
persisted identity* to the consumer's read, because the observation nulled it.

**D.** `job_run_id` and `job_trace_id` are `CDC-INTEGRATION-SLICE-001-DEVELOPMENT`
and `…-DEVELOPMENT-TRACE`, not the execution being adjudicated. The separation
proposition rests on process ids and path-only inputs, not on run labels, so no
semantic proposition changes. But the pipeline objects carry a run identity that
does not match RUN-003 while the observation binds RUN-003 — an **evidentiary
binding gap**: these artifacts are not self-identified as belonging to the
execution under adjudication.

`T-POS-04 = INSUFFICIENT_ARCHIVED_EVIDENCE.`

## 5. T-POS-06 — special review

```
A  RELIANCE_ISSUANCE_OBSERVED                        = TRUE
B  CAUSAL_AUTHORIZATION_ATTEMPT_RELIANCE_ORDER_SUPPORTED = TRUE
C  FULL_T_POS_06_PROJECTED_EVIDENCE_MINIMUM_SATISFIED    = TRUE (via §5.1)
D  null attempt_state = a projection-fidelity defect in the observation, CURED by a
   frozen artifact the observation itself identifies
```

Reliance ISSUED / `I1`. The digest chain is complete and every comparison archives
both operands:

```
authorization persisted sha  943194222a22b137dbf3c4536f515811e69c660c7dc3981c0438703d4322d9a0
  = issuance_authorization_digest_bound_in_attempt      EQUAL
  = issuance_authorization_digest_bound_in_reliance     EQUAL
attempt persisted sha        c2c350e078713f9be411cb64195a5002afef5288ecc65653c18482cd5a8447a4
  = attempt_record_digest_bound_in_reliance             EQUAL
evidence_basis DIGEST_CHAIN · filesystem_timestamp_consulted false
```

Ordering therefore rests where projection v0.3 placed it: a digest cannot be bound
to bytes that do not yet exist.

### 5.1 The null `attempt_state`, and why the cure is not substitution

The observation records `attempt_state: null`. The required state is carried by
the frozen artifact:

```
path   veraxis/integration-slice-001/run-003/evidence/pipeline/positive/attempt.json
bytes  493
sha256 c2c350e078713f9be411cb64195a5002afef5288ecc65653c18482cd5a8447a4
content  attempt_state = "CONSUMED_AT_FIRST_ISSUANCE_ATTEMPT"
```

This is not evidence substitution for three reasons. The file is inside the frozen
evidence commit. Its persisted sha256 is **the very value the observation archives
as `attempt_record_digest`** and that the reliance record binds — so the artifact
is identified by the observation itself, not selected by me. And I read the object
the observation already points at, rather than supplying a different one. Had the
digest not matched, no cure would have been available.

### 5.2 A defect that errs conservatively, recorded anyway

The observation states `claimed_at: null` with
`claimed_at_status: ABSENT_IN_GOVERNED_RECORD`, and therefore records the temporal
corroboration as `NOT_EVALUABLE`. The governed attempt record **does** contain
`claimed_at: 2026-08-15T10:00:00Z`, and `issued_at` is the same instant, so the
comparison was in fact evaluable and would have held. The observation under-reports
its own governed source. It errs toward claiming less than it had, which is the
safe direction — but it is a projection-fidelity defect and the harness should be
corrected before any successor run.

## 6. Primary TOCTOU criteria — distinct propositions, not collapsed

**T-CASE-K — currentness TOCTOU.** t1 `CURRENT` → t2 `SUPERSEDED`; epoch moved
`92dc18d2…` → `556add1f…`; the `I3` object archives both operands with
`applicable: false`; reliance REFUSED / `I2`; no issuance.
`T-CASE-K = SATISFIED_BY_ARCHIVED_EVIDENCE.`

**T-CASE-P — authority TOCTOU.** Artifact remains `CURRENT`; propagated decision
**not** expired — check 12 observed `{valid_until 2026-08-15T23:00:00Z, now
13:00:00Z} → passed: true`; epoch applicable; check 15 **reached**; authority basis
`NOT_REVOKED → REVOKED`; reliance-time authority decision DENY /
`A10 AUTHORITY_BASIS_REVOKED`; reliance REFUSED / `I11`; no issuance.
`T-CASE-P = SATISFIED_BY_ARCHIVED_EVIDENCE.`

The two are demonstrably distinct in the archive, and the pair that separates them
is exactly the one the projection made mandatory: in **G** the decision is expired
(11:00 < 13:00) and check 15 is *not reached*; in **P** the decision is fresh
(23:00 > 13:00), check 15 *is* reached, and the failure comes from the revoked
basis. Neither invalidation is collapsed into the other.

## 7. T-CASE-L — historical reliance

Issued historical reliance existed; a later correction became operative; the
issued record's persisted sha256 before equals after
(`byte_identity_preserved: true`); the issued record does not mention its own
supersession; the later attempt is REFUSED / `I2`; no new issuance.
`T-CASE-L = SATISFIED_BY_ARCHIVED_EVIDENCE`, with the boundary intact:
`HISTORICAL_RELIANCE_RECORD ≠ CURRENT_RELIANCE_ELIGIBILITY`.

## 8. Five real outputs

All five archive: real artifact ref with expected digest equal to observed;
currentness `SUPERSEDED` / `R2`; gate DENY; `authority_gate_invoked: false`; and
authority decision, envelope, consumer validation and reliance each named as
`not_produced`. Collectively they establish the bounded early-termination
behaviour across all five real outputs — with `authority_gate_invoked: false`
archived as a positive fact, which is what distinguishes early termination from an
authority evaluation that happened to deny.

## 9. Authority-procedure coverage

```
FULL_AUTHORITY_PROCEDURE_BRANCH_COVERAGE = NOT_ESTABLISHED
```

Observed authority reason codes across the archive: `A1`, `A6`, `A7`, `A10`,
`A11`, `A12`, `A13`. Not observed: `A2` — which the frozen implementation findings
record as **structurally unreachable** under the frozen procedure — and `A3`, `A4`,
`A5`, `A8`, `A9`. The 41-result population is not padded to cover them, and no
report may state that the authority procedure was exercised across all thirteen
steps.

## 10. Six maxima

| maximum | adjudication | basis and any deficiency |
|---|---|---|
| **A** CURRENTNESS_TO_AUTHORITY_INTEGRATION | **SUPPORTED_BY_RUN_003_AT_FROZEN_ASSURANCE** — `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | T-EARLY-01..05, T-POS-01, T-POS-02, T-CASE-A/B/N/Q/R/S. Currentness terminates before authority on all five real outputs; authority evaluates only on a CURRENT subject |
| **B** GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY | **PARTIALLY_SUPPORTED_BY_RUN_003** | T-POS-03 and T-POS-05 fully support materialization and revalidation; T-POS-04 is INSUFFICIENT. Deficiency **is material** to this maximum specifically, because the propagation claim is about crossing a boundary and the consumer-side identity of that crossing is incompletely recorded |
| **C** RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY | **SUPPORTED_BY_RUN_003_AT_FROZEN_ASSURANCE** — `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | T-POS-05 (sixteen checks with operands), T-POS-06 (issued only after them), T-CASE-G/I/J/M and the six `I6` refusals. Deficiencies in T-POS-04 are not material here: the gating decisions and their operands are archived independently of the consumer process identity |
| **D** POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE | **SUPPORTED_BY_RUN_003_AT_FROZEN_ASSURANCE** — `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | T-CASE-K with both epoch operands, re-resolution and refusal |
| **E** POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE | **SUPPORTED_BY_RUN_003_AT_FROZEN_ASSURANCE** — `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | T-CASE-P with fresh decision, reached check 15, revoked basis, `A10` → `I11` |
| **F** HISTORICAL_RELIANCE_RECORD_PRESERVATION | **SUPPORTED_BY_RUN_003_AT_FROZEN_ASSURANCE** — `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | T-CASE-L byte identity preserved across an operative correction, later reliance refused |

## 11. Claim ceiling — non-negotiable

```
real CDC institutional authority        NOT ESTABLISHED
real CDC institutional reliance         NOT ESTABLISHED
official CDC issuance                   NOT ESTABLISHED
CDC acceptance                          NOT ESTABLISHED
production enforcement                  NOT ESTABLISHED
legal effect                            NOT ESTABLISHED
external consumer bypass resistance     NOT ESTABLISHED
distributed reliance consistency        NOT ESTABLISHED
cross-institution propagation           NOT ESTABLISHED
```

Authority content remains synthetic. Propagation remains one process boundary on
one machine. Historical record preservation does not mean historical records
announce their own obsolescence — T-CASE-L confirms the opposite, and that is by
design.

## 12. Verdict

```
RUN_003_TECHNICAL_ADJUDICATION =
  CRITERIA_SUBSTANTIALLY_SATISFIED_WITH_ONE_INSUFFICIENT_OBSERVATION;
  FIVE OF SIX MAXIMA SUPPORTED, ONE PARTIALLY SUPPORTED
```

RUN-003 is the first execution in this slice whose archive lets a criterion
proposition be determined without opening test source. `TEST_EXECUTED_AND_PASSED`
is no longer the strongest archived fact — the observations carry operands,
digests, absences and both sides of every comparison. That is the projection
working. The one insufficiency and the two fidelity defects are named above rather
than absorbed, and they are the agenda for a successor run, not a reason to
discount this one.

```
source_modified            FALSE
evidence_modified          FALSE
semantic_design_modified   FALSE
result_bearing_execution   NONE
```
