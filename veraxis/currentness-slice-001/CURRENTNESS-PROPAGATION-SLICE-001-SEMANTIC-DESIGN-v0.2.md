# CURRENTNESS PROPAGATION VERTICAL SLICE 001 — SEMANTIC DESIGN v0.2

```
supersedes        CURRENTNESS-PROPAGATION-SLICE-001-SEMANTIC-DESIGN-v0.1.md
                  sha256 4e038eef3f1f44f18f688910f1706bfe40c8cca4c67536b2a7f9e8c10b04307d
                  16364 B, ZTL commit 1115d489571b1c4c5acd5bc94718a37aab406e41
                  — preserved unchanged; this is a successor, not an amendment
assurance_class   INTERNAL_TECHNICAL_DEMONSTRATION
status            READY_FOR_OWNER_REVIEW_v0.2
result_bearing    false
authorizes        nothing
```

## 0. A provenance discrepancy recorded before anything else

Parts of the owner review address a document that is not this author's v0.1.

- §2 of the review asks to remove the universal invariant
  `effective_at ≤ observed_at ≤ admitted_at ≤ evaluated_at`. **No such invariant
  appears in v0.1** (`4e038eef…`). v0.1 states three separate rules: a controlling
  record participates only if `effective_at ≤ evaluated_at`; a resolution is usable
  only for `evaluated_at ≥ admitted_at`; backdating is prohibited.
- §7 states "current listed total = 39" tests and "resolver = 11, use gate = 10,
  total = 21" reason codes. **v0.1 states no test count at all**, and lists **13**
  reason codes as a single closed set, not split by component.

I have therefore not "removed" a rule I never wrote and have not renumbered into
another document's counts. Everything below is derived from v0.1 as frozen, with
the owner's substantive corrections applied. If a second v0.1 exists and is
controlling, say so and I will reconcile against its bytes rather than its
description.

The substance of both corrections is accepted regardless of which document
carried the defect: the temporal semantics below are stated in the corrected
form, and all counts are recomputed and enumerated so they can be recounted.

## 1. Assurance disclosure (frozen)

```
semantic_mechanism_designer        VITALIY_REZNIK
criteria_author                    VITALIY_REZNIK
technical_adjudicator              VITALIY_REZNIK
implementation_author              CLAUDE
self_designed_and_self_adjudicated TRUE
independent_review_claim           FALSE
```

Any adjudication produced against this design may establish **internal
conformance to a frozen semantic contract written by the same person who
designed the mechanism and will judge it**. It may not establish independent
validation or external assurance, and no report may imply otherwise.

## 2. Core commitment (unchanged from v0.1)

Currentness is a relation over (artifact identity, institutional state,
evaluation time), never a property of the artifact. It is never written into the
artifact; it is always recomputed; and `HISTORICALLY_VALID` /
`CURRENTLY_ELIGIBLE` are separate axes that may never be stored in one another's
fields.

## 3. Positive completeness requirement — `BasisCompletenessAttestation`

`CURRENT` requires affirmative evidence that an attested-complete governing basis
was evaluated for this output and scope.

```
BasisCompletenessAttestation {
  scope_ref
  covered_output_ref
  record_kinds_covered []
  basis_snapshot_refs []            positionally paired with digests
  basis_snapshot_digests []
  completeness_as_of
  admitted_at
  fixture_class                     null for real outputs; SYNTHETIC_UNAFFECTED_CONTROL for the fixture
  completeness_digest
}
```

Branch rule:

```
attested-complete basis AND no operative controlling record
    → CURRENT                    R1  NO_OPERATIVE_CONTROLLING_RECORD

attestation absent
    → UNKNOWN                    R5  BASIS_COMPLETENESS_ATTESTATION_MISSING

attestation present but scope/output mismatch, malformed, or digest not reproducible
    → UNKNOWN                    R6  BASIS_COMPLETENESS_ATTESTATION_INVALID

basis searched but coverage not attested complete
    → UNKNOWN                    R4  CURRENTNESS_BASIS_INCOMPLETE
```

Frozen as a sentence: **`NOT_FOUND` ≠ `ABSENT_IN_ATTESTED_COMPLETE_BASIS`.** For
real mission outputs, absence of an attestation can never produce `CURRENT`.

An attestation covers only the outputs and record kinds it names. An attestation
for the synthetic control confers nothing on any real output.

## 4. Temporal semantics (corrected)

Knowledge ordering, required only for what the resolution could have known:

```
observed_at ≤ admitted_at ≤ evaluated_at
```

`effective_at` is **not** in that chain. It is treated separately:

```
effective_at ≤ evaluated_at    → the successor may be operative
effective_at >  evaluated_at    → the successor EXISTS but is NOT YET OPERATIVE
```

For a future-effective successor with an attested-complete basis:

```
currentness_state  CURRENT
secondary_states   [FUTURE_SUPERSESSION_SCHEDULED]
reason_code        R1 NO_OPERATIVE_CONTROLLING_RECORD
scheduled_supersession { successor_ref, effective_at }   recorded, addressable
```

The artifact is **not** labelled `SUPERSEDED` before the effective instant. And
`CURRENT` here still requires the attested-complete basis of §3 — a scheduled
supersession does not relax the completeness requirement, and `R11
EFFECTIVE_TIME_NOT_YET_REACHED` is recorded as the reason the successor was set
aside, not as the reason currency was granted.

Backdating remains prohibited: `effective_at` is owner-issued prospective time,
never a clock reading chosen after the fact. `observed_at` and `effective_at`
may not be substituted for one another.

## 5. Competing successors

Conflict detection runs **before** any controlling successor is selected.

```
if ≥2 simultaneously operative successor records claim control over the same
   predecessor/output, and frozen governance contains no deterministic authority
   rule resolving them:

     currentness_state         UNKNOWN
     reason_code               R7  AMBIGUOUS_CONTROLLING_SUCCESSORS
     controlling_successor_ref NONE
     competing_refs []         all claimants, addressable
     use gate                  DENY
```

The resolver must not invent institutional precedence. Selecting one claimant
because it is newer, first, or lexically smaller would be fabricating authority
the governance does not confer.

## 6. Use gate — caller cannot assert currency

The v0.1 signature is replaced. The gate derives currentness itself:

```
evaluate_present_use(request, historical_artifact, currentness_index, profile, run_metadata)

  internally:
    resolution = resolve_currentness(
        output_ref        = request.output_ref,
        historical_artifact = historical_artifact,
        index             = currentness_index,
        evaluated_at      = request.requested_at)
    then evaluate that internally derived resolution
```

There is **no caller argument through which `CURRENT` can be asserted**. A
precomputed resolution may be retained only as a performance hint: the gate
recomputes the expected governed resolution and requires exact
`resolution_digest` equality before use; any difference is `G9
DENY_PRECOMPUTED_RESOLUTION_DIGEST_MISMATCH`. A caller-supplied currentness
assertion is refused explicitly as `G8`, so the attempt appears in evidence
rather than being silently ignored.

Governed origin is established by digest against the index, never by Python class
identity, type name, or object provenance.

Gate precedence:

```
1  integrity mismatch              G5  DENY_ARTIFACT_INTEGRITY_MISMATCH
2  index identity mismatch         G10 DENY_INDEX_IDENTITY_MISMATCH
3  resolution binding mismatch     G6  DENY_RESOLUTION_BINDING_MISMATCH
4  precomputed digest mismatch     G9  DENY_PRECOMPUTED_RESOLUTION_DIGEST_MISMATCH
5  resolution stale/expired        G7  DENY_RESOLUTION_STALE_REEVALUATION_REQUIRED
6  caller-asserted currentness     G8  DENY_CALLER_SUPPLIED_CURRENTNESS_REJECTED
7  UNKNOWN                         G4  DENY_CURRENTNESS_UNKNOWN_FAIL_CLOSED
8  SUPERSEDED                      G2  DENY_OUTPUT_SUPERSEDED         + successor pointer
9  INELIGIBLE                      G3  DENY_OUTPUT_INELIGIBLE         + record pointer
10 CURRENT                         G1  PROCEED_TO_NEXT_GATE
```

`UNKNOWN_DISPOSITION = DENY`, fixed for this slice, for consequential and
non-consequential use alike. `G1` is not an authorization: the gate emits no
institutional event, performs no transition, and its output is `PROCEED`, never
`ALLOWED`.

## 7. Different-output successors — one frozen rule

v0.1 was self-conflicting here. Frozen resolution:

```
a valid successor record governing some OTHER output, merely present in the
corpus                                    → IGNORED; it is not evidence about
                                             the queried output either way

that same record ASSERTED as the controlling successor for the queried output
                                          → UNKNOWN
                                             R8 SUCCESSOR_ADDRESSES_DIFFERENT_OUTPUT
```

Presence is not relevance; assertion is a binding error. Both branches are
independently tested (T-ADV-N and T-ADV-H).

## 8. Reason codes — closed sets, actual counts

Resolver, **11**:

```
R1  NO_OPERATIVE_CONTROLLING_RECORD
R2  OUTPUT_SUPERSEDED
R3  OUTPUT_INELIGIBLE_PENDING_REGENERATION_OR_EXPLICIT_HUMAN_RESOLUTION
R4  CURRENTNESS_BASIS_INCOMPLETE
R5  BASIS_COMPLETENESS_ATTESTATION_MISSING
R6  BASIS_COMPLETENESS_ATTESTATION_INVALID
R7  AMBIGUOUS_CONTROLLING_SUCCESSORS
R8  SUCCESSOR_ADDRESSES_DIFFERENT_OUTPUT
R9  SUCCESSOR_BINDING_MISMATCH
R10 ARTIFACT_INTEGRITY_MISMATCH
R11 EFFECTIVE_TIME_NOT_YET_REACHED
```

Use gate, **10**: `G1`–`G10` as listed in §6.

```
resolver_reason_code_count  11
use_gate_reason_code_count  10
total                       21
```

No code outside these sets may appear; adding one after execution is a criteria
modification and is prohibited.

## 9. Test universe — enumerated, then counted

```
T-STALE-RES-01..05   (5)  each real output resolves SUPERSEDED, controlling successor
                          EBAWU-P-001-C-TENDER-01-CORR-002
T-STALE-GATE-01..05  (5)  each gate DENYs with an addressable pointer to the successor
                          and correction event
T-BYTE-01..05        (5)  each output byte-identical before and after the whole slice
T-CTRL-RES-01        (1)  synthetic control resolves CURRENT under attested-complete basis
T-CTRL-GATE-01       (1)  synthetic control gate returns PROCEED_TO_NEXT_GATE

T-ADV-A  (1)  currentness record removed              → UNKNOWN
T-ADV-B  (1)  wrong successor pointer                 → R9
T-ADV-C  (1)  output_ref / artifact digest mismatch   → refusal per precedence
T-ADV-D  (1)  expired resolution supplied             → G7
T-ADV-E  (1)  caller asserts CURRENT                  → G8
T-ADV-F  (1)  historical bytes modified               → G5
T-ADV-G  (1)  successor hidden, predecessor only      → UNKNOWN, never CURRENT
T-ADV-H  (1)  successor for another output asserted   → R8
T-ADV-I  (1)  future-effective successor              → CURRENT + FUTURE_SUPERSESSION_SCHEDULED
T-ADV-J  (1)  competing operative successors          → R7
T-ADV-K  (1)  completeness attestation missing        → R5
T-ADV-L  (1)  completeness attestation invalid        → R6
T-ADV-M  (1)  completeness attestation forged         → R6 via digest non-reproduction
T-ADV-N  (1)  unrelated record present in corpus      → ignored; CURRENT stands
T-ADV-O  (1)  precomputed resolution, digest equal    → accepted
T-ADV-P  (1)  precomputed resolution, digest differs  → G9
T-ADV-Q  (1)  index identity mismatch                 → G10
T-ADV-R  (1)  UNKNOWN under non-consequential use     → still DENY (profile fixed)
                                                    adversarial subtotal 18

T-DIG-01..09 (9)  one per digest class in the frozen derivation document:
                  historical_artifact, basis_record, completeness, index, resolution,
                  use_gate_decision, observation, package, persisted-file — each
                  reproduces its published rule and, where given, its test vector
```

```
test_count = 5 + 5 + 5 + 1 + 1 + 18 + 9 = 44
```

Method note, since the number matters: I enumerated first and counted after. The
first enumeration produced 45 and contained a duplicate — a standalone
"index digest reproducible" case already covered by `T-DIG-04` — which I removed.
The total then coincides with the figure mentioned in the review. I record that I
did not adjust the enumeration to reach it, and the enumeration is printed above
so it can be recounted.

## 10. Synthetic control — frozen artifact

```
path    veraxis/currentness-slice-001/
        CDC-CURRENTNESS-SLICE-001-SYNTHETIC-UNAFFECTED-CONTROL-v0.1.json
bytes   2275
sha256  2a9158e0561d3ab1886f3f4f52c0b828a76979aadccc66b58c95ccb84914a45d

output_ref                            CDC-SYNTHETIC-UNAFFECTED-001/SYNTH-OUTPUT-01
fixture_class                         SYNTHETIC_UNAFFECTED_CONTROL
derived_from_real_mission_001_output   false
historical_artifact_digest             6f9fe1ccbabd6195d474f09a365a5ca4cc32f7ed8cf1f41e8acddd22e592eed0
completeness_digest                    a9ffff71467a0880f77e3fec8b4740a0cdb74953e8fb9d743b1fdd7617ce66c6
index_admission_path                   SYNTHETIC_CONTROL_PATH_ONLY
```

Its completeness attestation claims completeness **only** for
`CDC-SYNTHETIC-UNAFFECTED-001/SYNTH-OUTPUT-01`, with an empty but *attested*
basis — emptiness here is an attested fact, not an unsearched absence. Admissible
to the index only through the separately identified synthetic-control path; no
arbitrary caller-provided index entry may reference this fixture class.

## 11. Digest derivation

Frozen separately, before implementation:

```
path    veraxis/currentness-slice-001/CURRENTNESS-SLICE-001-DIGEST-DERIVATION-v0.1.md
```

Covers all nine digest classes with canonical serialization, exclusion rules,
ordering rules, prefix handling, trailing-newline handling and reference test
vectors. Any digest class introduced later requires a versioned successor
published before the execution that produces it.

## 12. Claim ceiling — assurance-qualified, not neutral

If measured:

```
EXECUTABLE_CURRENTNESS_RESOLUTION                           MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
STALE_OUTPUT_PRESENT_USE_REFUSAL                            MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
HISTORICAL_ARTIFACT_PRESERVATION_DURING_CURRENTNESS_CHANGE   MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION
```

These may not be shortened to a bare `MEASURED` in any external report.

Not established, and to be carried verbatim:

```
real_unaffected_CDC_output_resolves_CURRENT   NOT_ESTABLISHED
consumer_bypass_resistance                    NOT_ESTABLISHED
institutional_currentness_propagation         NOT_ESTABLISHED
institutional_reliance                        NOT_ESTABLISHED
official_CDC_issuance                         NOT_ESTABLISHED
legal_effect                                  NOT_ESTABLISHED
production_conformance                        NOT_ESTABLISHED
CDC_acceptance                                NOT_ESTABLISHED
general_rollback_resistance                   NOT_ESTABLISHED
distributed_consistency_across_institutions   NOT_ESTABLISHED
```

The first two deserve emphasis because they are the ones most likely to be
over-read. There is no unaffected real output in the frozen population, so a
`CURRENT` result exists only on a declared synthetic fixture. And the gate
protects only paths that call it: a consumer reading the historical bytes
directly is entirely unaffected, so what can be measured is refusal at the gate,
not propagation to consumers.

## 13. Success condition

Not: *the five outputs were marked stale.*

But: **the five historical outputs remained byte-identical across the entire
slice, while an independently maintained currentness layer refused their present
use and named the controlling successor evidence — and refused equally in every
case where the basis for asserting currency was absent, incomplete, unattested,
ambiguous, mis-bound, expired, forged or caller-supplied.**

## 14. Return

```
CURRENTNESS_SLICE_DESIGN = READY_FOR_OWNER_REVIEW_v0.2

current_requires_attested_complete_basis  TRUE
future_effective_successor_handled        TRUE
competing_successors_fail_closed          TRUE
caller_can_assert_current                 FALSE
unknown_disposition                       DENY
test_count                                44
resolver_reason_code_count                11
use_gate_reason_code_count                10
self_designed_and_self_adjudicated        TRUE
independent_review_claim                  FALSE
source_modified                           FALSE
result_bearing_execution                  NONE
prior_history_modified                    FALSE
exact_source_changes                      NOT SUPPLIED — implementer's lane

NEXT_GATE = OWNER_AUTHORIZATION_TO_IMPLEMENT_CURRENTNESS_SLICE_001
```
