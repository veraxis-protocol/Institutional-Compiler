# OIC Definition Ontology Discrimination 001 — Post-Run Adjudication

Status: FINAL POST-RUN INTERPRETATION

## Authoritative status

EXECUTION_COMPLETE / PROVIDER_AVAILABILITY_FAILURE / HYPOTHESIS_NOT_ADJUDICATED

The frozen 36-request execution completed exactly once with zero retries.

All 36 attempts terminated as `PROVIDER_ERROR`.
There were zero accepted model responses and therefore zero semantic observations
capable of supporting or refuting the ontology-clarification hypothesis.

## Instrument-produced disposition

The receipt contains:

`REFUTES_SIMPLE_ONTOLOGY_CLARIFICATION`

That value is preserved as an instrument output but is NOT accepted as the
scientific disposition of this run.

The current adjudicator treats an unavailable provider response as failure to emit
`CONSTITUTIVE_DEFINITION`. When provider availability is zero, this converts absence
of observation into apparent negative semantic evidence.

That inference is invalid.

## Finding

This run exposed a missing experiment-infrastructure invariant:

> Scientific semantic adjudication MUST be gated by a preregistered minimum
> provider-success / paired-observation criterion.

Provider failure must never be transformed into evidence against a semantic
hypothesis.

## Consequence

No conclusion is authorized regarding whether the fixed ontology clarification
repairs constitutive-definition classification.

No conclusion is authorized regarding a revised Institutional IR ontology.

No canonicalization was performed.

No Institutional IR runtime was constructed.

No independent validation is claimed.

## Preservation rule

This work order MUST NOT be rerun.

The original receipt, execution log, execution manifest, frozen plan, and frozen
instrument remain immutable evidence of this execution.

Any further experiment MUST use a new successor work order and MUST first pass a
separately preregistered provider-availability qualification gate.

## Required successor invariant

Before evaluating semantic success, regression, partial support, or refutation,
the successor adjudicator MUST determine whether the required paired observations
actually exist.

If the preregistered availability threshold is not satisfied, the only permitted
scientific disposition is:

`NOT_ADJUDICABLE_PROVIDER_FAILURE`

This check precedes every semantic decision rule.
