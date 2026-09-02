# Canada Manifest Resolution Hypotheses 001

**Work order:** `OIC-CANADA-MANIFEST-RESOLUTION-HYPOTHESES-001`

**Status:** `PREREGISTERED_HYPOTHESES_NOT_EVALUATED`

## Starting evidence

Failure-Surface Characterization 001 is formally closed with:

- 8/8 unresolved fields characterized;
- 0 findings;
- 5 zero-admissible-value surfaces;
- 3 multi-admissible contradiction surfaces;
- causal root cause still `NOT_ESTABLISHED`.

The frozen SOURCE_MANIFEST contract simultaneously requires fixed enums/statuses,
one canonical `source_locator`, and scalar rights/provenance evidence fields,
while prohibiting silent normalization.

## Purpose

Freeze competing resolution mechanisms **before** evaluating them.

This is not a repair.

This is not a manifest revision.

This is not a winner-selection exercise.

## Hypothesis families

For the five zero-admissible fields:

1. **Explicit declaration** — write a manifest-aligned classification/status at
   the source metadata/admission boundary.
2. **Deterministic projection** — define an explicit, replayable projection from
   existing evidence vocabulary, but only where every semantic premise is already
   explicit.

For `source_locator`:

1. **Explicit canonical locator declaration**.
2. **Role-based canonical precedence** over existing locator roles.

For `rights_evidence` and `provenance_evidence`:

1. **Single-reference precedence** while preserving the full evidence set elsewhere.
2. **Typed multi-reference collection** requiring a manifest representation change.

## Evaluation dimensions

Future evaluation may report only structural properties such as:

- current-contract compatibility;
- whether a contract change is required;
- whether new explicit metadata/evidence declaration is required;
- whether a new semantic projection is required;
- whether precedence is required;
- whether all observed distinct values are preserved;
- deterministic replayability;
- semantic-promotion risk;
- whether CA-3 alone can test the mechanism;
- whether held-out validation is required.

## Stop rule

No hypothesis may be adopted in this work order.

No manifest or evidence may be mutated.

No SOURCE_MANIFEST.csv may be created.

CA-3 cannot establish cross-source generality.

## Current state

- hypotheses frozen: **TRUE after commit**
- hypotheses evaluated: **FALSE**
- winner selected: **FALSE**
- preserved Crosswalk receipt inspected by this work order: **FALSE**
- real evidence reread: **FALSE**
- manifest contract change authorized: **FALSE**
- schema mutation authorized: **FALSE**
- SOURCE_MANIFEST.csv creation/population: **FALSE**
- rights/provenance established: **FALSE**
- root cause: **NOT_ESTABLISHED**
- provider/model/network calls: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**

## Next authorized activity after independent verification

Implement and statically freeze a deterministic hypothesis-evaluation instrument
using synthetic support fixtures only.

Do not inspect the preserved real Crosswalk 001 receipt until that implementation
is frozen and independently verified.
