# OIC Definition Ontology Staged Decomposition 004 — Preregistration

Status: **FROZEN DESIGN / NOT EXECUTED**

Work order:

`OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-004`

Starting commit:

`f3eff10c7311783b6a7a8c97caf8cfd1c1b90473`

## Predecessor result

Ontology 003A closed with:

`SUPPORTS_TASK_INTERFERENCE_HYPOTHESIS`

Measured predecessor result:

- 36/36 accepted;
- 18/18 complete A/B pairs;
- force-only primary result: 9/9;
- B improvements over combined A: 4;
- A improvements over force-only B: 0;
- B-only control force defects: 0;
- combined `definiendum`: 6/9 compatible, 3 omitted;
- combined `definiens`: 6/6 compatible.

Ontology 003A did **not** authorize an architecture change.

## Question

Can staged semantic decomposition simultaneously preserve:

1. the 9/9 force-classification performance observed in 003A; and
2. the expected definition slots that remained unstable in the combined task?

## Arm A — combined

Arm A reproduces the exact combined ontology-clarified proposal condition from
Ontology 003A.

One provider request produces the full provisional proposal.

## Arm B — staged decomposition

Arm B uses two independent requests over the same admitted proposition.

### B1 — force-only

B1 reproduces the exact force-only ontology-clarified condition from Ontology
003A.

It returns only:

`{"normative_force":"<ONE_ALLOWED_LABEL>"}`

### B2 — non-force slots only

B2 receives only the same candidate span.

It does **not** receive B1 output.

It does **not** classify or return `normative_force`.

Its allowed slot vocabulary is exactly:

- bearer
- action
- object
- counterparty
- condition
- exception
- temporal_qualifier
- quantum
- definiendum
- definiens

B2 may also surface unresolved references under the existing provisional
proposal boundary.

### Deterministic merge

The two staged outputs are merged locally without another model call.

The model may not rewrite, reconcile, repair, rank, or canonicalize the two
outputs.

The deterministic merge creates no institutional act.

## Experimental size

- six frozen specimens;
- three runs per specimen;
- 18 paired A/B composite observations;
- 54 provider requests total;
- zero retries;
- 4-second pacing.

Odd runs:

`A -> B1 -> B2`

Even runs:

`B1 -> B2 -> A`

## Mandatory offline materialization

Before instrument freeze, all **54 exact provider requests** must be
materialized offline.

No provider may be constructed.

No network request may occur.

Failure to materialize every exact request blocks instrument freeze.

## Adjudicability

No semantic decision may be evaluated unless:

- 54/54 provider requests are accepted;
- 18/18 A/B composite pairs are complete;
- 9/9 primary pairs are complete;
- 9/9 control pairs are complete.

## Strict support rule

`SUPPORTS_STAGED_DECOMPOSITION_VIABILITY` requires:

- no staged-only control regression;
- staged primary force = 9/9;
- staged `definiendum` = 9/9 compatible;
- staged `definiens` = 6/6 compatible;
- zero expected definition-slot omissions;
- zero expected definition-slot incompatibilities.

This is intentionally stricter than merely outperforming Arm A.

## Regression rule

`REGRESSION` applies if staged B introduces:

- any B-only control force defect; or
- any B-only critical non-force control-slot defect.

## Refutation rule

`REFUTES_STAGED_DECOMPOSITION_VIABILITY` applies when no control regression is
present but staged B reaches <=7/9 primary force accuracy or creates at least two
expected definition-slot omissions/incompatibilities.

Other adjudicable outcomes are `INCONCLUSIVE`.

## Fresh provider gate

This experiment requires a new:

`OIC-NVIDIA-PROVIDER-QUALIFICATION-004`

Qualification 003A must not be reused.

## Claim ceiling

Even a positive result does **not** authorize:

- canonical institutional meaning;
- interpretation authority;
- legal validity;
- a schema split;
- a revised Institutional IR ontology;
- production staging;
- production architecture change;
- cross-model generalization;
- cross-provider generalization.

A positive result would authorize only a **separate architecture adjudication**
on whether staged proposal operations should enter the reference implementation.

## Current execution state

Provider calls under 004: ZERO.

Model calls under 004: ZERO.

Live run: NOT EXECUTED.

Canonicalization: NOT IMPLEMENTED.

Institutional IR runtime: NOT IMPLEMENTED.

Architectural change: NOT AUTHORIZED.

Independent validation: NOT CLAIMED.
