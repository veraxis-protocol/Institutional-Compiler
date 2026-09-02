# Canada Manifest Resolution Candidate 002

**Work order:** `OIC-CANADA-MANIFEST-RESOLUTION-CANDIDATE-002`

**Status:** `PREREGISTERED_CANDIDATE_NOT_EVALUATED`

## Why a new candidate is justified

Hypotheses 001 closed with sixteen structurally evaluated mechanisms:

- six require new explicit declarations;
- eight require separately frozen projection/precedence/sufficiency rules;
- two typed multi-reference mechanisms preserve evidence multiplicity but require a manifest-contract change.

No mechanism was selected or adopted.

A further contract observation creates a new, narrower hypothesis for the two
evidence-reference fields: the frozen manifest contract permits a
repository-relative tracked evidence reference. Therefore the manifest itself
does not need to inline every evidence reference.

A scalar manifest cell can instead point to a deterministic tracked evidence
bundle that preserves the complete supporting set.

This hypothesis was not part of Hypotheses 001 and is therefore preregistered
here before evaluation.

## Integrated candidate

For these six fields:

- `source_kind`
- `source_locator`
- `rights_basis`
- `rights_status`
- `provenance_status`
- `redistribution_status`

Candidate 002 uses explicit declarations only.

The evaluator may never infer those values from existing workflow, acquisition,
review, capture, or rights vocabulary.

For:

- `rights_evidence`
- `provenance_evidence`

Candidate 002 uses one scalar repository-relative reference to a canonical
tracked evidence bundle.

The bundle hypothesis must preserve every observed distinct admissible evidence
reference without selecting one as superior.

## Why this candidate is worth testing

If structurally feasible, it would avoid all three failure mechanisms observed
so far:

1. no silent semantic projection for zero-admissible classification/status fields;
2. no lossy precedence among multiple admissible evidence references;
3. no change to the frozen SOURCE-MANIFEST contract.

That is only a hypothesis.

## Evaluation boundary

The next study may inspect only tracked frozen artifacts:

- Hypotheses 001 closure result;
- Failure-Surface 001 closure result;
- SOURCE-MANIFEST contract.

It may not inspect the local Crosswalk receipt or real evidence.

It may not create declaration values.

It may not create evidence bundles.

It may not create SOURCE_MANIFEST.csv.

## Success rule

`CANDIDATE_STRUCTURALLY_FEASIBLE_CA3` only if the current contract can
represent all eight mechanisms while preserving the nonpromotion boundaries.

Otherwise:

`CANDIDATE_NOT_STRUCTURALLY_FEASIBLE_FAIL_CLOSED`

## Claim ceiling

A structural PASS would not establish any declaration value, rights,
provenance, legal clearance, evidence sufficiency, manifest admissibility, or
cross-source generality.

## Current state

- candidate preregistered: **TRUE after commit**
- candidate evaluated: **FALSE**
- candidate adopted: **FALSE**
- declaration values created: **FALSE**
- evidence bundles created: **FALSE**
- local Crosswalk receipt inspected: **FALSE**
- real evidence reread: **FALSE**
- manifest contract change authorized: **FALSE**
- SOURCE_MANIFEST.csv creation/population: **FALSE**
- rights/provenance established: **FALSE**
- root cause: **NOT_ESTABLISHED**
- provider/model/network calls: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**

## Next authorized activity after independent verification

Implement and statically freeze a deterministic structural evaluator using
synthetic bundle fixtures only.

Do not create real declarations, evidence bundles, or SOURCE_MANIFEST.csv.
