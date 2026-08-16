# INTEGRATION SLICE 001 — RUN-001 TECHNICAL ADJUDICATION 001

```
semantic_mechanism_designer        VITALIY_REZNIK
criteria_author                    VITALIY_REZNIK
technical_adjudicator              VITALIY_REZNIK
implementation_author              CLAUDE
self_designed_and_self_adjudicated TRUE
independent_review_claim           FALSE
assurance_class                    INTERNAL_TECHNICAL_DEMONSTRATION
```

RUN-001 is spent. No rerun was requested, inferred or simulated. No development
evidence was substituted for observations RUN-001 did not produce. Absence of a
pipeline observation is treated as absence, never as a negative observation:
`NOT_PRODUCED ≠ FAILED_PROPERTY`. No source was modified.

## 0. Identities recomputed from bytes

```
evidence commit  e0d491b19a39a799ca9c10fa547eec1df0d53f77   verified
evidence tree    688f9d8480690d4ba0219050862cfe7e63dbd141   verified

execution issuance  0ed920c1a1ba090c366fb1939d5d9bdb716f48150b6c8609afd6b8bdd17bfe4f  MATCH  2473 B
semantic design v0.4  03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173  MATCH  5848 B
digest derivation v0.4 494c91ace109ba050c40b72cc2f0f1cc64366386376212d50edbb3b9a418d1e7  MATCH  8950 B
```

The issuance binds, and each binding was verified against the archived object:

```
implementation      fa96f5c3590f54118cd926a84370be6022a80b35 / tree 65a704cd…
execution harness   …HARNESS-v0.2.py   a371ca5d…  51719 B    archive matches
authorization cand. …AUTHORIZATION-v0.2.CANDIDATE.json  55ea2142…  2699 B  archive matches
implementation findings  96d3181748132274fb92b7fef7d0f7d9ed1dc6aa81487a8442fec4b0ca0a6f6c  archive matches
semantic design / digest derivation  the two controlling objects above
owner_decision AUTHORIZED · result_bearing_execution_authorized TRUE · single_use TRUE · automatic_retry FALSE
```

Raw execution package: `package_digest` **reproduced** under the frozen Class 7
rule, and all five declared members verified byte-exact against their archived
copies (0 divergences).

**A trap in the evidence directory, named so it cannot mislead later.** The file
`docs/operations/…AUTHORIZATION-001.json` carries
`authorization_state: CANDIDATE_NOT_CONSUMED`,
`result_bearing_execution_authorized: false`, and binds harness **v0.1**
(`becbea9b…`, 40970 B). A reader opening that file alone would conclude the run
was unauthorized and executed an unbound harness. Both conclusions would be
wrong: the operative instrument is the **issuance** `0ed920c1…`, which authorizes
the execution and binds harness **v0.2**, and the archived v0.2 matches its
declared identity exactly. The stale candidate is simply not marked superseded.
That is a bookkeeping defect in the evidence set, not an authority defect in the
run.

## A. Execution authority and procedure — VALID

```
criteria_phase_execution_valid = TRUE
```

Phase sequence, read from the failure observation and corroborated by the package
and attempt records:

```
verify_execution_authority        VALID
preflight                         PASS_45_OF_45
preflight_zero_invocation_check   0_RESULT_BEARING_INVOCATIONS
attempt_state_check               NO_ATTEMPT_RECORD          (state before consumption)
consume_ordinal                   CONSUMED
run_criteria                      COMPLETED_41_OF_41
pipeline_observations             RAISED
```

The attempt record shows `CONSUMED_BEFORE_RESULT_BEARING_INVOCATION` — the
ordinal was spent *before* the result-bearing phase, which is the correct
single-use discipline rather than a defect. One attempt record exists, keyed to
the issuance digest; `automatic_retry_performed` false;
`second_result_bearing_execution` false; `attempt_record_modified_after_consumption`
false; `harness_modified_after_consumption` false.

Implementation identity `fa96f5c3` / `65a704cd` is bound identically in five
independent records (issuance, attempt, criteria ledger, preservation
observation, raw package). The preservation observation shows
`implementation_head_after_run` and `implementation_tree_after_run` identical to
the bound values, both worktrees porcelain-empty, `source_modified: false`.

## B. The frozen 41-criterion population — what the archive actually supports

```
frozen_criteria_observed     41/41
frozen_criteria_machine_pass 41/41   (junit: tests 41, failures 0, errors 0, skipped 0)
```

The 41 node identifiers map **one-to-one** onto the frozen universe of semantic
design v0.4: `T-EARLY` ×5, `test_pos_01..06` ×6, `test_case_a..s` ×19 (A–N, plus
O, P, Q, R, S), `test_dig_01..08` ×8, `test_epoch_a/b/c` ×3 — 5+6+19+8+3 = 41.
Nothing is missing and nothing extra appears.

**The bounded determination, and it is the central finding of this adjudication.**
Each criteria-ledger entry contains exactly four fields:

```
{classname, node_name, gate_outcome, time}
```

There is no expected value, no observed value, no bound digest, no artifact
identity, no scenario state — for any of the 41. The ledger is a transcription of
pytest node outcomes, and the record itself declares its source: *"pytest
junit-xml emitted by harness v0.2 during the consumed run"*, with
`semantic_adjudication_performed: false`.

Therefore:

```
criteria_level_properties_supported =
  that 41 named test nodes, whose identifiers correspond one-to-one to the frozen
  criterion universe, executed and asserted successfully under bound implementation
  identity fa96f5c3/65a704cd within a validly issued single-use execution.

criteria_level_properties_NOT_supported =
  the semantic proposition of any individual criterion. The archive carries no
  observation content, so from the evidence alone it cannot be established WHAT any
  criterion checked or against WHICH data. Recovering that would require reading the
  implementation's test source, which is outside this review.
```

This applies even where the proposition is otherwise legible. `test_dig_01` and
`test_epoch_a/b/c` correspond to vectors whose complete inputs are published in
digest derivation v0.4 — but the ledger records neither the computed bytes nor the
computed digests, so what is in evidence is *"the test asserting that vector
passed"*, not *"the vector reproduced"*. A pytest PASS is not amplified here into
its criterion's proposition, in accordance with the work order.

## C. Observability completeness — INCOMPLETE

```
pipeline_observation_package_complete = FALSE
pipeline_phase_completed              = false   (raw package)
```

Not produced, each recorded as absent rather than failed:

```
positive-path pipeline observation             NOT_PRODUCED
currentness TOCTOU pipeline observation        NOT_PRODUCED
authority TOCTOU pipeline observation          NOT_PRODUCED
five-real-output pipeline observation          NOT_PRODUCED
historical-reliance observation                NOT_PRODUCED   (explicitly false in the failure record)
standalone digest-vector observation           NOT_PRODUCED
```

Corroborated structurally: the evidence set contains no propagation envelope
file, no currentness resolution record, no authority decision record, no consumer
validation record and no reliance issuance record — the artefacts the design
requires as evidence of the pipeline.

**Target claims that therefore remain unsupported by RUN-001** — all six
assurance-qualified maxima of the design, without exception:

```
CURRENTNESS_TO_AUTHORITY_INTEGRATION                    UNSUPPORTED
GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY         UNSUPPORTED
RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY    UNSUPPORTED
POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE      UNSUPPORTED
POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE  UNSUPPORTED
HISTORICAL_RELIANCE_RECORD_PRESERVATION                 UNSUPPORTED
```

Each is a property of a *pipeline execution crossing a real process boundary*.
None of them is established, and none of them is refuted.

## D. Failure classification — CONFIRMED

```
harness_scaffolding_defect_confirmed = TRUE
implementation_source_implicated     = FALSE
```

Observed: `FileNotFoundError`, `[Errno 2] No such file or directory:
'/private/tmp/cdc-integration-slice-001-run-001/pipeline/positive/control.json'`,
raised in phase `pipeline_observations` after `run_criteria` completed
41-of-41. The evidence locates the defect in
`…EXECUTION-HARNESS-v0.2.py`, function `_pipeline_observations`: the harness
created the shared `pipeline` directory but not the per-scenario subdirectories it
then passed onward.

I confirm the classification on four independent grounds from the evidence, not
from the producer's label:

1. the missing path lies inside the runtime evidence root, not inside the
   implementation tree, and names a scaffolding directory rather than a governed
   artifact;
2. the failing phase is the harness's own observation phase, reached only after the
   criteria phase had completed;
3. the preservation observation shows the implementation head and tree unchanged
   across the run with an empty porcelain status, so no implementation mutation
   participated;
4. `harness_modified_after_consumption: false` — the harness that failed is the
   one the issuance bound (`a371ca5d…`), verified byte-exact.

**Boundary:** I did not open the harness source. The `.py` files in the evidence
directory were left unread, for the same reason as in every prior slice — reading
source there is indistinguishable from implementation inspection. The
confirmation above is therefore *consistent-with-evidence*, not a code-level
diagnosis.

## E. Run status

```
RUN_001_TECHNICAL_ADJUDICATION =
  CRITERIA_PHASE_COMPLETE ·
  OBSERVATION_PACKAGE_INCOMPLETE ·
  HARNESS_INFRASTRUCTURE_FAILURE_AFTER_CRITERIA
```

`EXECUTION_INCOMPLETE` is subsumed and is not stated separately: the execution is
incomplete precisely because the observation package is. Neither PASS nor FAIL is
appropriate — the frozen criteria phase completed without a single failure, and
the properties the slice exists to demonstrate were never observed. Forcing either
label would misreport one half of that.

```
RUN_001_sufficient_for_full_integration_slice_closure = FALSE
```

## F. Claim ceiling from RUN-001

```
ESTABLISHED
  Under owner issuance 0ed920c1…, with single-use consumed exactly once and no retry,
  a criteria phase of 41 named test nodes — identifiers corresponding one-to-one to the
  frozen 41-criterion universe — executed and passed under bound implementation identity
  fa96f5c3/65a704cd, with the implementation tree unchanged across the run, and the
  resulting evidence package internally consistent and byte-verifiable.

NOT ESTABLISHED
  every semantic proposition of every individual criterion; all six pipeline maxima of
  the design; and, unchanged from the design, real CDC institutional authority, real CDC
  institutional reliance, official CDC issuance, external consumer bypass resistance,
  production enforcement, legal effect, CDC acceptance, distributed reliance consistency
  and cross-institution propagation.
```

## G. Carried disclosure — A2

The archived implementation findings (`96d31817…`, classified
`IMPLEMENTATION_OBSERVATION_ONLY`, `SEMANTIC_CONTROL FALSE`) record that `A2` is
**structurally unreachable** under the frozen procedure, because the authority
basis lookup resolves by `(principal_id, scope)` and any mismatch terminates
earlier at step 3 with `A11`. That is stronger than the "declared uncovered"
disclosure in semantic design v0.3/v0.4, and it is correctly held as an
implementation observation with no semantic control. It is carried here so the
stronger statement is on the adjudication record: **no report of this slice may
state that the authority procedure was exercised across all thirteen steps.**
Whether the resolution key, the step ordering or the `A2` binding should change is
a semantic question, not answered by this adjudication.

```
source_modified = FALSE
```

Scope ceiling: `INTERNAL_TECHNICAL_DEMONSTRATION`. OBSERVATION ≠ CRITERIA ≠
ADJUDICATION ≠ OWNER CLAIM DECISION.
