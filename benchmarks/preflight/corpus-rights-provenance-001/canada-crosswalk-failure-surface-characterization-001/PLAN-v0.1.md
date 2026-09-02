# Canada Crosswalk Failure-Surface Characterization 001

**Work order:** `OIC-CANADA-CROSSWALK-FAILURE-SURFACE-CHARACTERIZATION-001`

**Status:** `PREREGISTERED_NOT_EXECUTED`

## Why this study is required

Crosswalk 001 is formally closed
`CROSSWALK_INCOMPLETE_FAIL_CLOSED`.

Four of twelve manifest fields were established.

Eight were not:

- source_kind
- source_locator
- rights_basis
- rights_evidence
- rights_status
- provenance_evidence
- provenance_status
- redistribution_status

The closure does not establish the causal root cause and does not authorize a
schema repair, normalization, precedence rule, or manifest write.

Therefore the next question must remain descriptive:

> What exact candidate-key, artifact, value, mapping and transformation surface
> produced the eight unresolved Crosswalk 001 fields?

## Input

Future execution may inspect only the preserved one-shot Crosswalk 001 receipt
bound by SHA-256.

It may not inspect:

- original Canada evidence files;
- the prior Inventory 001 receipt;
- CA-3.xml;
- corroborating Markdown;
- network resources;
- unlisted files.

## Frozen output

For each of the eight unresolved fields, record deterministic frequencies for:

- exact candidate keys;
- artifact paths;
- source-scope pointers;
- canonical raw-value fingerprints;
- preserved mapped values;
- mapping classes;
- preserved transformations.

No new semantic mapping may be created.

No winner may be selected.

No precedence may be assigned.

No enum translation may be introduced.

No evidence or schema may be changed.

## Frozen surface classes

A field with multiple candidates and zero admissible values is classified:

`ZERO_ADMISSIBLE_VALUE_SURFACE`

A field with multiple distinct admissible values is classified:

`MULTI_ADMISSIBLE_CONTRADICTION_SURFACE`

Anything inconsistent with the closed Crosswalk 001 result is:

`UNEXPECTED_SURFACE_FAIL_CLOSED`

## Success rule

`FAILURE_SURFACE_CHARACTERIZED` only if all eight fields reproduce their
closed Crosswalk 001 state/counts and receive complete descriptive profiles.

Otherwise:

`FAILURE_SURFACE_INCOMPLETE_FAIL_CLOSED`

## Claim ceiling

Even a complete characterization does not establish:

- causal root cause;
- a correct normalization;
- a correct precedence rule;
- legal rights;
- provenance truth;
- evidence sufficiency;
- authorization to alter evidence;
- authorization to alter the manifest contract;
- authorization to populate SOURCE_MANIFEST.csv.

## Current state

- Crosswalk 001 rerun: **FALSE**
- preserved Crosswalk 001 receipt contents inspected by this preregistration: **FALSE**
- real evidence reread: **FALSE**
- source XML inspected: **FALSE**
- schema resolution authorized: **FALSE**
- normalization authorized: **FALSE**
- precedence selection authorized: **FALSE**
- SOURCE_MANIFEST.csv creation/population: **FALSE**
- rights/provenance established: **FALSE**
- provider/model/network calls: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**

## Next authorized activity after independent verification

Implement and statically freeze the characterization instrument using synthetic
Crosswalk-receipt fixtures only.

Do not open the preserved real Crosswalk 001 receipt until that implementation
is frozen and independently verified.
