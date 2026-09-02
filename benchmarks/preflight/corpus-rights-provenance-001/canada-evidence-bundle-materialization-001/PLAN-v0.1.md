# Canada Evidence-Bundle Materialization 001

**Work order:** `OIC-CANADA-EVIDENCE-BUNDLE-MATERIALIZATION-001`

**Status:** `PREREGISTERED_NOT_EXECUTED`

## Starting point

Candidate 002 is formally closed as structurally feasible for CA-3.

The evidence-reference seam is now narrower than the declaration seam:

- `rights_evidence` can be represented by one tracked bundle reference while
  preserving all four observed admissible evidence references;
- `provenance_evidence` can be represented by one tracked bundle reference
  while preserving all three observed admissible evidence references;
- no precedence among those references is structurally required;
- no manifest-contract change is structurally required.

The six declaration fields remain outside this work order.

## Purpose

Materialize only the two evidence-reference bundles, deterministically and
without authority promotion.

This work order does not adopt Candidate 002 as a whole.

It does not create or infer declaration values.

## Frozen extraction rule

Future execution may read only the preserved Crosswalk 001 receipt.

For each target field:

1. inspect only support records for that exact field;
2. take only non-null `mapped_value` strings already present;
3. deduplicate by exact string identity only;
4. sort lexicographically for serialization only;
5. preserve the exact set;
6. do not fetch, normalize, translate, rank, supplement, or infer.

Expected distinct counts are frozen from the closed Candidate 002 result:

- `rights_evidence`: 4
- `provenance_evidence`: 3

## Bundle semantics

The bundle order has no evidentiary or institutional priority.

Bundle membership does not establish legal sufficiency.

Underlying evidence is not rewritten.

## One-shot rule

The future real receipt read is one-shot.

A permanent STARTED lock must exist before receipt content is opened.

Execution writes only local observed bundle candidates and receipts.

Tracked bundle files are created only during formal closure from the exact
observed bytes.

No rerun is permitted after STARTED.

## Out of scope

- all six declaration fields;
- real underlying evidence reread;
- rights/legal adjudication;
- provenance adjudication;
- candidate adoption;
- SOURCE_MANIFEST.csv;
- provider/model/network;
- 007R1 / Q011 / canonicalization / IR / OCE / Rego / runtime.

## Claim ceiling

A successful run establishes deterministic bundle bytes only.

It does not establish rights, provenance truth, legal clearance, declaration
values, manifest admissibility, or cross-source generality.

## Next authorized activity after independent verification

Implement and statically freeze the bundle materializer using synthetic receipt
fixtures only.

Do not open the preserved Crosswalk receipt yet.
