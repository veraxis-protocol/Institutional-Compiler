# CURRENTNESS PROPAGATION SLICE 001 — RUN-001 TECHNICAL ADJUDICATION 001

```
semantic_mechanism_designer        VITALIY_REZNIK
criteria_author                    VITALIY_REZNIK
technical_adjudicator              VITALIY_REZNIK
implementation_author              CLAUDE
self_designed_and_self_adjudicated TRUE
independent_review_claim           FALSE
assurance_class                    INTERNAL_TECHNICAL_DEMONSTRATION
```

This adjudication may establish internal conformance to a frozen semantic
contract written by the same person who designed the mechanism and now judges it.
It establishes no independent validation and no external assurance. No execution,
repair, retry or criteria modification was performed.

## 1. Controlling identities — recomputed from bytes

```
semantic design v0.2   82ac78f51439e438eafb31565369f73ba58e530ad1a18b75688f4dcb91ffe0e8  16913 B  MATCH
digest derivation v0.1 8b398291a657ab97e8e9e52b345051e257069c3532b49a8826207315b5c4c5dd   6753 B  MATCH
synthetic control v0.1 2a9158e0561d3ab1886f3f4f52c0b828a76979aadccc66b58c95ccb84914a45d   2275 B  MATCH

implementation commit  6cade50a8ee041cc941eb91fd7295c42b9a8a3e9   verified
implementation tree    c196dd43816cdf10661e598f3901ed7e369792bd   verified (resolved from the commit)

execution authorization 8657729a8bfa381fbf790bdb4eb6ec5621774c07b88264692e15f30342ff2f94  1205 B  MATCH
raw execution package   36fc41dfee9803986e5d8d8a3ee3b00edf49710639019af759c8b4e2c4acaacb  4867 B  MATCH
package_digest          2636c60b6d9e43741399ea449569017e408720cc98eb48521c672a2dbed13517  REPRODUCED
raw evidence commit     77652fd25991c83c4690b7e888e24d77a0887d86   verified
raw evidence tree       18ff888da6059a22c8ef9d76a232fa8c0ff364a1   verified
```

`package_digest` was reproduced under §3.8 of the frozen derivation document —
the first time in this programme that an aggregate digest reproduced on the first
attempt from a published rule rather than by inference.

Execution facts, read from the attempt record and package:

```
result_bearing_execution_invocations  1
automatic_retry_performed             false
second_result_bearing_execution       false
attempt_state                         CONSUMED_AFTER_FIRST_EXECUTION
attempt records present               exactly one, keyed to the authorization digest
semantic_adjudication_performed       false (by the execution actor)
institutional_events_emitted          0
```

## 2. Procedural deviation — classified, not waived

```
pre_execution_working_tree_clean          FALSE
pre_execution_tracked_working_tree_clean  TRUE
sole_untracked_path  docs/operations/CDC-CURRENTNESS-SLICE-001-RESULT-BEARING-EXECUTION-AUTHORIZATION-001.json

procedural_deviation_classification = PROCEDURAL_BOUNDARY_LIMITATION
```

Four findings, in order:

1. **Working-tree cleanliness is not a criterion of the frozen semantic design.**
   v0.2 (`82ac78f5…`) contains no such requirement. Requirement C came from the
   owner's execution instruction, not from the contract I froze, so under the
   criteria being applied here it is `OUTSIDE_SCOPE` as a test and cannot be a
   precondition failure of them.
2. **The property C was protecting is independently established.** The tracked
   tree was clean; untracked files are not part of a git tree; the attempt record
   and the package both bind commit `6cade50a` and tree `c196dd43`; and I resolved
   that commit to that tree myself. The executable source identity against which
   the result was produced is therefore intact regardless of C.
3. **The instruction set was internally unsatisfiable, and that is the real
   finding.** A (persist the authorization before execution), B (keep HEAD exactly
   at `6cade50a`) and C (clean working tree) cannot all hold: persisting a new
   file either dirties the tree or requires a commit that moves HEAD. The only
   escapes not instructed were placing the file outside the repository or
   pre-committing it. The resolution chosen preserved source identity, which is
   the property worth preserving among three that could not coexist. A future
   instruction should state where execution-time authorizations live, or C will
   fail again for the same reason.
4. **It is nonetheless a real deviation and is not waived.** An untracked,
   execution-relevant file was present at execution time. Its mitigation is
   verifiable rather than asserted: it was finalized and hashed before execution,
   reverified by the harness, unmodified afterwards, and committed with the frozen
   evidence, and its digest matches the authorization identity in the attempt
   record and package. Recorded as a boundary limitation and carried into the
   verdict.

## 3. Observation table

Extracted from the per-case evidence records, not from the package's summary
counters.

Real population — all five identical in shape:

| field | OUTPUT-01 … OUTPUT-05 |
|---|---|
| historical_artifact_digest_before / _after | equal for each; `historical_artifact_digest_preserved` true |
| historical_state | `INELIGIBLE_PROVENANCE_INCOMPLETE` |
| currentness_state | `SUPERSEDED` |
| reason_code / id | `OUTPUT_SUPERSEDED` / `R2` |
| controlling_successor_ref | `EBAWU-P-001-C-TENDER-01-CORR-002` |
| correction_event_ref | `CDC-E2E-M12-CORRECTION-EVT-002` |
| gate_decision | `DENY` |
| gate_reason_code / id | `DENY_OUTPUT_SUPERSEDED` / `G2` |
| next_gate | none reached |
| institutional_event_emitted | `false` |
| consequential_gate_reached | `false` |
| basis_completeness_attestation_present | `false` |

Per-artifact digests (immutability observation), expected = observed for all five,
`mismatched: []`, `byte_identity_preserved: true`,
`historical_evidence_cleaned_or_rewritten: false`:

```
OUTPUT-01 239f0d67…   OUTPUT-02 66dd4f15…   OUTPUT-03 a6f24f71…
OUTPUT-04 17595a42…   OUTPUT-05 6d211ed3…
```

Synthetic control:

```
output_ref                              CDC-SYNTHETIC-UNAFFECTED-001/SYNTH-OUTPUT-01
currentness_state                       CURRENT
reason_code / id                        NO_OPERATIVE_CONTROLLING_RECORD / R1
controlling_successor_ref               null
secondary_states                        []
basis_completeness_attestation_present  true
basis_completeness_reproduces           true   (a9ffff71… reproduced)
gate_decision / reason                  PROCEED / PROCEED_TO_NEXT_GATE (G1)
next_gate                               AUTHORITY_AND_ADMISSIBILITY_GATE
institutional_event_emitted             false
derived_from_real_mission_001_output    false
fixture_class                           SYNTHETIC_UNAFFECTED_CONTROL
```

**The two axes were not collapsed.** Each real resolution records
`historical_state = INELIGIBLE_PROVENANCE_INCOMPLETE` *and*
`currentness_state = SUPERSEDED` as separate fields. The pre-existing
provenance-incompleteness from RUN-001 was not folded into the supersession
result, which §8 of the work order required and which is the same axis discipline
whose violation produced the M11 finding in Mission-001.

**A consequence of the asymmetry rule, visible in the data.** The five real
outputs carry `basis_completeness_attestation_present: false` and still resolve
`SUPERSEDED`. That is correct and is the design working: completeness attestation
gates `CURRENT` only. `SUPERSEDED` rests on positive evidence of a controlling
record and needs no completeness claim.

## 4. Criterion matrix — 44, independently counted

Evidence pointers: `RESOLUTION-OBSERVATIONS`, `USE-GATE-OBSERVATIONS`,
`IMMUTABILITY-OBSERVATION`, `ADVERSARIAL-OBSERVATIONS`, `DIGEST-OBSERVATIONS`,
all at evidence commit `77652fd2…`.

| group | ids | required | observed | class |
|---|---|---|---|---|
| stale resolve | T-STALE-RES-01..05 | `SUPERSEDED` / `R2` / CORR-002 | 5/5 exactly | **SATISFIED ×5** |
| stale gate | T-STALE-GATE-01..05 | `DENY` / `G2`, no event, consequential not reached | 5/5 exactly | **SATISFIED ×5** |
| byte identity | T-BYTE-01..05 | before = after | 5/5, `mismatched: []` | **SATISFIED ×5** |
| control resolve | T-CTRL-RES-01 | `CURRENT` / `R1` under attested-complete basis | as recorded, attestation reproduces | **SATISFIED** |
| control gate | T-CTRL-GATE-01 | `PROCEED` / `G1`, next gate named | `AUTHORITY_AND_ADMISSIBILITY_GATE` | **SATISFIED** |
| adversarial | T-ADV-A..R | expected reason per case | 18/18 `match: true` | **SATISFIED ×18** |
| digest | T-DIG-01..09 | published rule reproduces | 9/9 `match: true`, 24 nested checks, 0 divergences | **SATISFIED ×9** |

Adversarial, expected → observed, each verified individually:

```
A R5 · B R9 · C G5 · D G7 · E G8 · F G5 · G R5 · H R8 · I R1
J G4 (resolver R7 recorded in detail) · K R5 · L R6 · M R6 · N R1
O G2 · P G9 · Q G10 · R G4
```

```
criteria_total          44
criteria_satisfied      44
criteria_not_satisfied   0
criteria_not_observable  0
criteria_outside_scope   0
```

Counted by enumerating the groups above: 5+5+5+1+1+18+9 = 44, matching the frozen
universe.

**One recording observation, non-blocking.** Reason codes appear in evidence as
identifiers (`R2`, `G4`, `R7`), and in the resolution records also by name
(`OUTPUT_SUPERSEDED`, `NO_OPERATIVE_CONTROLLING_RECORD`). The string
`AMBIGUOUS_CONTROLLING_SUCCESSORS` appears nowhere: T-ADV-J records `R7` only as
`detail.resolver_reason_code_id`. The mapping is 1:1 and unambiguous against the
frozen closed set, so this is conformant — but a reader matching on code *names*
rather than ids would wrongly conclude R7 was never exercised.

## 5. Semantic invariants (§12)

| invariant | established by |
|---|---|
| `CURRENT` requires attested-complete basis | T-ADV-K/L/M: attestation missing → R5, invalid → R6, forged → R6 via digest non-reproduction; and the control's `CURRENT` carries a reproducing attestation |
| `NOT_FOUND` does not imply `CURRENT` | T-ADV-G: successor hidden, predecessor only → R5, never CURRENT |
| caller cannot assert `CURRENT` | T-ADV-E → G8; T-ADV-P → G9 on digest divergence of a precomputed resolution |
| future-effective successor not prematurely `SUPERSEDED` | T-ADV-I → R1, not R2 |
| competing successors fail closed | T-ADV-J → UNKNOWN / G4, `controlling_successor_ref: null`, both claimants recorded |
| `UNKNOWN` denied | T-ADV-J and T-ADV-R → G4, including the non-consequential profile |
| historical validity separate from current eligibility | both fields present and distinct in all five real resolutions |
| currentness not written into the historical artifact | five artifact digests unchanged; currentness lives only in resolution/gate records |

All eight established by result-bearing evidence.

## 6. Verdict

```
CURRENTNESS_SLICE_001_TECHNICAL_ADJUDICATION = PASS_WITH_BOUNDARY_LIMITATION
```

All 44 frozen criteria are satisfied and the eight semantic invariants hold on
result-bearing evidence. The qualifier carries three boundaries, each material to
interpreting the pass rather than a complaint about unfinished architecture:

1. **The procedural deviation of §2** — an untracked, execution-relevant file was
   present at execution against a stated requirement, mitigated verifiably but
   not absent.
2. **`CURRENT` was observed only on a declared synthetic fixture.** The frozen
   population contains no unaffected real output, so the positive path has been
   exercised on a fixture and on nothing else.
3. **Refusal was measured; propagation was not.** The gate protects only paths
   that call it. A consumer reading the five historical artifacts directly is
   entirely unaffected, and nothing in this evidence changes that.

```
ESTABLISHED
  EXECUTABLE_CURRENTNESS_RESOLUTION                           MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
  STALE_OUTPUT_PRESENT_USE_REFUSAL                            MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
  HISTORICAL_ARTIFACT_PRESERVATION_DURING_CURRENTNESS_CHANGE   MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION

  in the exact form: five historical artifacts remained byte-identical across the
  whole slice while an independently maintained currentness layer resolved each as
  SUPERSEDED, refused present use at the gate, named the controlling successor and
  correction event, emitted no institutional event, reached no consequential gate,
  and refused equally in all eighteen adversarial cases where the basis for
  asserting currency was absent, incomplete, unattested, ambiguous, mis-bound,
  expired, forged or caller-supplied.

NOT_ESTABLISHED
  real_unaffected_CDC_output_resolves_CURRENT
  consumer_bypass_resistance
  institutional_currentness_propagation
  institutional_reliance
  official_CDC_issuance
  legal_effect
  production_conformance
  CDC_acceptance
  general_rollback_resistance
  distributed_consistency_across_institutions
```

None of the three established properties may be shortened to a bare `MEASURED` in
any report.

## 7. Preservation

RUN-001, RUN-002, their raw evidence, the currentness RUN-001 evidence, the
implementation, the semantic design, the digest derivation and the synthetic
control were not modified by this adjudication. Mission-001 classifications
remain historical facts: Stage-2 RUN-001 aggregate `FAIL` with M11
`SEMANTIC_VIOLATION`; the M12 correction attempt `INFRASTRUCTURE_BLOCKED`;
correction RUN-002 `PASS_WITH_BOUNDARY_LIMITATION`. Nothing here re-measures any
of them.

Scope ceiling: `INTERNAL_TECHNICAL_DEMONSTRATION`. OBSERVATION ≠ CRITERIA ≠
ADJUDICATION ≠ OWNER CLAIM DECISION.
