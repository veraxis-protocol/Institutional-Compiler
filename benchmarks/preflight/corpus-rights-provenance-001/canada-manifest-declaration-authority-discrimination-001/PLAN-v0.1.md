# Canada Manifest Declaration Authority Discrimination 001

**Work order:** `OIC-CANADA-MANIFEST-DECLARATION-AUTHORITY-DISCRIMINATION-001`

**Status:** `PREREGISTERED_HYPOTHESES_NOT_EVALUATED`

## Starting point

The CA-3 representation problem has been narrowed successfully.

Two evidence-reference fields now have frozen tracked bundle objects:

- `rights_evidence`
- `provenance_evidence`

Six required scalar fields remain unresolved:

- `source_kind`
- `source_locator`
- `rights_basis`
- `rights_status`
- `provenance_status`
- `redistribution_status`

Candidate 002 established that explicit declarations are structurally feasible
for these six fields. It did **not** establish who has standing to make those
declarations.

## Research question

For each remaining field:

**What already-existing institutional source, actor, or frozen rule has standing
to establish the value?**

This is an authority-discrimination study, not a value-selection study.

## Candidate establishment channels

The preregistered candidate channels include:

- explicit source-origin declaration;
- publisher canonical-locator declaration;
- external rights-authority declaration;
- institutional admission declaration;
- institutional rights-adjudication declaration;
- institutional provenance-admission declaration;
- already-existing contract-defined derivation.

The evaluator is not an authority channel.

## Standing test

A channel may pass only when the future frozen inputs explicitly establish the
required standing dimensions, including authority identity, authority basis,
scope, target-field coverage, explicit act/rule, evidence binding where
required, temporal/version scope where required, manifest-shape compatibility,
and non-self-issuance.

A rule-based channel additionally requires an already-existing frozen rule with
deterministic replay.

The study may not invent such a rule.

## Critical nonpromotion boundary

The following substitutions are forbidden:

- evidence presence → rights_basis;
- rights instrument → rights_status;
- acquisition success → provenance_status;
- observed URL → source_locator;
- public accessibility → source_kind;
- rights_basis or rights_status → redistribution_status;
- workflow/reviewer state → manifest value absent an authorized declaration
  channel.

## Possible outcome

A field may end with:

`AUTHORITY_NOT_ESTABLISHED`

That is a valid result.

The study is not required to find an authority channel for every field.

## Future input discipline

Before evaluation, the static implementation freeze must enumerate every tracked
authority/governance artifact it will inspect by exact repository path and
SHA-256.

No wildcard evidence reading is permitted.

Source XML, Crosswalk receipts, real underlying evidence, and network access are
forbidden.

Tracked rights/provenance governance artifacts may be used only to evaluate
standing, actor roles, explicit authority bases, and transition-gate semantics.
Their contents may not be promoted directly into manifest declaration values.

## Claim ceiling

A PASS establishes only that the authority surface was completely discriminated
for the frozen CA-3 candidate channels.

It does not establish:

- any declaration value;
- rights;
- provenance truth;
- legal clearance;
- redistribution permission;
- Candidate 002 adoption;
- SOURCE_MANIFEST admissibility;
- cross-source generality.

## Current state

- target declaration fields: **6**
- authority channels evaluated: **FALSE**
- declaration values created: **FALSE**
- authority channel selected: **FALSE**
- new derivation rule created: **FALSE**
- tracked evidence bundles modified: **FALSE**
- Candidate 002 adopted: **FALSE**
- SOURCE_MANIFEST.csv creation/population: **FALSE**
- root cause: **NOT_ESTABLISHED**
- provider/model/network: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**

## Next authorized activity after independent verification

Construct a tracked authority-source inventory and static evaluator.

The implementation freeze must bind every inspected tracked input by exact path
and SHA-256 before any authority-channel evaluation occurs.
