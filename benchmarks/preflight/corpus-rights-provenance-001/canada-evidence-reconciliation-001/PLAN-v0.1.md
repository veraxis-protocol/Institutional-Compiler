# OIC Canada Corpus Evidence Reconciliation 001

**Work order:** `OIC-CANADA-CORPUS-EVIDENCE-RECONCILIATION-001`

**Status:** `PREREGISTRATION_ONLY_NOT_EXECUTED`

## Purpose

Freeze the exact bounded Canada corpus population and the closed evidence surface
that may be inspected in a later execution step for the repository's
`SOURCE_MANIFEST.csv` rights/provenance preflight.

This work order exists because the repository already contains a frozen Canada
corpus and rights-resolution artifacts. It therefore does not authorize creation
of a replacement or synthetic corpus.

## Frozen population

Exactly one source is in scope:

- source_id: `CA-3`
- source object: `benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml`
- source Git blob: `9d89e621e40854a192a41193a507a766af30214b`
- acquisition receipt: `benchmarks/corpus/canada/freeze-v0.1/receipts/CA-3.receipt.json`
- receipt Git blob: `52f8585f8733b1e37ac4fb6c72dcdbad84ccec1e`

No other source may be silently added.

No source may be silently removed.

Population inference from directory contents during execution is forbidden; the
population is the explicit list above.

## Source-content boundary

The future reconciliation execution may compute a byte-level SHA-256 digest of
`CA-3.xml` solely to verify source-object identity.

It may not parse, render, extract text from, summarize, semantically inspect, or
otherwise use the XML content.

Provider/model/network access is forbidden.

## Evidence inspection boundary

No evidence contents are inspected by this preregistration.

A future execution may read only the files frozen in
`EVIDENCE-ALLOWLIST-v0.1.json`.

Primary PASS-critical facts must be explicitly supported by the frozen
machine-readable evidence.

Human-readable twin/supporting files may corroborate but cannot alone manufacture
a missing PASS-critical fact and cannot override a primary-evidence conflict.

No network fetch, live terms lookup, permission-request send, external action, or
new evidence creation is permitted.

## Frozen reconciliation target

The future execution must determine whether the frozen evidence is sufficient to
populate every required `SOURCE_MANIFEST.csv` field for `CA-3` under
`OIC-SOURCE-MANIFEST-CONTRACT-001 v0.1`.

The required fields are:

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

`notes` is optional.

## Frozen sufficiency rule

The reconciliation result may be
`READY_FOR_MANIFEST_POPULATION` only if all of the following are true:

- the explicit population remains exactly `CA-3`;
- the source Git blob and every allowlisted evidence Git blob still match this
  preregistration;
- every required manifest field has explicit support in the allowlisted evidence
  or, for content_hash only, the permitted byte-level SHA-256 computation;
- source_kind can be supported as exactly `public` or `synthetic`;
- rights_basis maps exactly to one contract-allowed value;
- rights_status is explicitly supportable as `verified`;
- provenance_status is explicitly supportable as `verified`;
- redistribution_status is explicitly supportable as `permitted` or
  `not_permitted`, never `unknown`;
- source_locator is explicit and stable;
- acquired_or_generated_at is explicitly supportable as RFC 3339 with timezone;
- no PASS-critical fact is inferred from public availability, filename,
  jurisdiction, government authorship, a permission request, silence, absence of
  objection, or a synthetic assumption;
- no PASS-critical primary evidence conflicts with another PASS-critical primary
  evidence item;
- no required value remains missing, ambiguous, conditional, pending, unknown,
  rejected, or unverified.

Otherwise the only permitted result is:

`EVIDENCE_INSUFFICIENT_FAIL_CLOSED`

## Conflict rule

No post-observation discretionary precedence may be invented.

If two primary machine-readable evidence artifacts materially conflict on a
PASS-critical field and the conflict cannot be resolved by an explicit
machine-readable status/version/supersession relation already contained in the
frozen evidence, reconciliation fails closed.

Corroborating Markdown cannot override that failure.

## Permission-request rule

The existence of a permission-request artifact is not permission.

A drafted, sent, pending, unanswered, or unaccepted request cannot establish
`rights_status=verified`.

Only explicit allowlisted evidence establishing the applicable rights basis may
support that status.

## Output boundary for later execution

The later execution may create only:

- a tracked evidence-reconciliation result; and
- a tracked post-reconciliation adjudication.

It may **not** create or populate root `SOURCE_MANIFEST.csv` yet.

Manifest population requires independent verification of the reconciliation
result followed by a separately authorized bounded population step.

## Claim ceiling

`READY_FOR_MANIFEST_POPULATION` would establish only that the frozen evidence
appears structurally sufficient to populate the frozen preflight manifest contract
for the exact one-source `CA-3` population.

It would not itself establish legal advice, universal copyright clearance,
downstream redistribution rights beyond the explicit recorded basis, semantic
correctness, institutional authority, benchmark validity, production readiness,
enterprise readiness, or permission to execute any semantic/runtime/provider
work.

`EVIDENCE_INSUFFICIENT_FAIL_CLOSED` would establish only that the frozen
evidence cannot support the manifest under the frozen contract. It would not
establish infringement or invalidity of the source.

## Current state

- evidence contents inspected by this work order: **FALSE**
- source XML content inspected: **FALSE**
- root SOURCE_MANIFEST.csv created: **FALSE**
- rights established: **FALSE**
- provenance established: **FALSE**
- 007R1 authorized: **FALSE**
- Q011 authorized: **FALSE**
- canonicalization/IR/OCE/Rego/runtime authorized: **FALSE**
- provider/model/network calls: **ZERO**
