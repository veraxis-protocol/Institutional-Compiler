# Canada Evidence-to-Manifest Crosswalk 001

**Work order:** `OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001`

**Status:** `PREREGISTERED_NOT_EXECUTED`

## Why this successor now exists

Canada Evidence Vocabulary Inventory 001 is formally closed
`INVENTORY_COMPLETE`:

- 11/11 primary machine-readable evidence artifacts inventoried;
- 1,529 inventory records;
- 202 unique exact keys;
- zero findings.

The prior exact-key reconciliation failed because only two of twelve manifest
fields were directly represented under its frozen exact-key rule.

The completed vocabulary inventory now gives us a bounded empirical surface on
which to test a distinct question:

> Can the existing evidence vocabulary be mapped to all twelve frozen
> SOURCE_MANIFEST fields under an explicit, traceable, non-promotional
> crosswalk?

## Important distinction

This work order does **not** assume that a crosswalk exists.

It does **not** treat similar names as equivalent.

It does **not** infer legal rights or provenance from public availability,
government authorship, internal-use permission, drafted requests, silence,
filenames, or workflow state.

The crosswalk must earn every field.

## Inputs

The future execution may inspect only the preserved one-shot inventory receipt
already produced by Inventory 001.

It may not reopen:

- the real evidence files;
- corroborating Markdown;
- CA-3.xml;
- network resources;
- any unlisted artifact.

## Target population

Exactly one source:

- `CA-3`

## Target fields

Exactly twelve:

1. source_id
2. source_kind
3. source_locator
4. local_path
5. content_hash
6. rights_basis
7. rights_evidence
8. rights_status
9. provenance_evidence
10. provenance_status
11. redistribution_status
12. acquired_or_generated_at

## Candidate-key freeze

For each target, only the exact candidate key names frozen in
`CROSSWALK-CONTRACT-v0.1.json` may be inspected as mapping candidates.

No post-observation candidate-key expansion is permitted.

Candidate presence is not mapping.

## Establishment rule

A target field is established only if:

1. the candidate record is traceable to exact artifact path, Git blob and JSON
   pointer;
2. the candidate is explicitly scoped to CA-3 under a frozen allowed scope rule;
3. any transformation is deterministic and uses only explicit evidence premises;
4. no prohibited promotion or inference occurs;
5. no unresolved conflict remains;
6. exactly one target value survives.

Otherwise the field remains NOT_ESTABLISHED.

## Decision rule

`CROSSWALK_COMPLETE` only if all twelve fields are established.

Otherwise:

`CROSSWALK_INCOMPLETE_FAIL_CLOSED`

## Rights/provenance safety boundary

This study may establish a **mapping**.

It may not establish that the underlying legal rights or provenance claims are
true merely because the mapping exists.

Manifest population remains a separate later gate.

## Current state

- crosswalk executed: **FALSE**
- record-level inventory receipt inspected by this preregistration: **FALSE**
- real evidence reread: **FALSE**
- source XML inspected: **FALSE**
- SOURCE_MANIFEST.csv created: **FALSE**
- SOURCE_MANIFEST.csv population authorized: **FALSE**
- rights established: **FALSE**
- provenance established: **FALSE**
- provider/model/network calls: **ZERO**
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime: **FALSE**

## Next authorized activity after independent verification

Implement and statically freeze the crosswalk instrument using synthetic fixture
records only.

Do not inspect the preserved real inventory receipt until that instrument is
frozen and independently verified.
