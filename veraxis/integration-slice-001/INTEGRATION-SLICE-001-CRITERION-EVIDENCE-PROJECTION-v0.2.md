# INTEGRATION SLICE 001 — CRITERION EVIDENCE PROJECTION v0.2

```
supersedes                  INTEGRATION-SLICE-001-CRITERION-EVIDENCE-PROJECTION-v0.1.md
                            sha256 8fed52234f418bbe4ac8d5e2a98fb31952c69ed514d2e8ea27cb1348eb12db35
                            11720 B — preserved unchanged; v0.1 remains the substantive evidence model
classification              EVIDENCE_PROJECTION_ONLY
SEMANTIC_CONTROL            FALSE
SEMANTIC_CRITERIA_MODIFIED  FALSE
TEST_COUNT                  41
result_bearing_execution    NONE
controlling semantic design CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md
                            sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
                            — unchanged by this document
```

**Narrow successor.** Adds identity bindings, normalizes node accounting, and
defines the ledger object, so that two digest classes can be frozen in a
derivation successor. The substantive per-criterion evidence model of v0.1 — the
universal envelope, the five group projections and the criterion-specific minima —
is carried forward unchanged and is not restated here.

## 1. Universal identity bindings

Every `CriterionObservation` binds, in addition to every field frozen in v0.1 §2
and §3:

```
record_class    CDC_INTEGRATION_SLICE_001_CRITERION_OBSERVATION
schema_version  INTEGRATION-SLICE-001-CRITERION-OBSERVATION-v0.1

execution_id
trace_id

semantic_design_sha256               03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
criterion_evidence_projection_sha256 <persisted-file sha256 of THIS document, v0.2>
implementation_commit                fa96f5c3590f54118cd926a84370be6022a80b35
implementation_tree                  65a704cd9c70aef983b62ecc8176793e20004772

criterion_id
node_id
… all universal and criterion-specific observation fields frozen in v0.1 …
node_accounting                      §2 below
observation_digest                   self-excluded
```

**On the projection's own identity.** This document cannot contain its own
sha256; the field above is specified here and its value is supplied at freeze
time, in the publication return and in the derivation successor's reference
vector. No cycle arises: the projection is frozen before any
`CriterionObservation` exists, so every observation can bind a value that already
exists when the observation is written.

## 2. Node accounting — normalized

The v0.1 pairing of `node_outcome` with a `NON_LOAD_BEARING` marker is replaced
by one object, so the marker cannot become detached from the value it qualifies:

```
node_accounting {
  outcome           the machine test-runner outcome, verbatim
  runner            the runner that produced it
  duration_seconds  as reported, or null
  non_load_bearing  true          — constant; any other value is malformed
}
```

Bookkeeping only. `node_accounting` is never evidence of a criterion proposition
by itself, and an adjudicator may not derive one from it. It is retained solely so
that a run's machine accounting remains reconcilable against its observations.

## 3. `CriterionEvidenceLedger`

```
CriterionEvidenceLedger {
  record_class     CDC_INTEGRATION_SLICE_001_CRITERION_EVIDENCE_LEDGER
  schema_version   INTEGRATION-SLICE-001-CRITERION-EVIDENCE-LEDGER-v0.1
  execution_id
  trace_id
  semantic_design_sha256                03ca22e9…
  criterion_evidence_projection_sha256  <this document, v0.2>
  implementation_commit                 fa96f5c3…
  implementation_tree                   65a704cd…
  criteria_total                        41
  criterion_order []                    the exact frozen order, §4
  observations []                       exactly 41 entries, in criterion_order
  pytest_accounting_ref                 reference to the runner's own accounting artifact
  ledger_digest                         self-excluded
}
```

Each `observations[]` entry, at minimum:

```
{ criterion_id, observation_path, persisted_file_bytes,
  persisted_file_sha256, observation_digest }
```

**The ledger binds two distinct identities and they are never collapsed:**

```
observation_digest    semantic / content identity — what was observed
persisted_file_sha256 exact persisted-file identity — the bytes that were stored
```

A content digest proves what the observation says; a file digest proves which
bytes were archived. Either alone leaves a gap, and equating them would hide the
difference between a re-serialized record and the record that was written.

Requirements, all mandatory:

```
exactly 41 entries
41 unique criterion_id values
the exact frozen criterion universe — no substitution, no addition
the exact frozen order of §4 — observations[] is NEVER re-sorted
no aggregate semantic PASS / FAIL / SATISFIED field anywhere in the ledger
pytest_accounting_ref is secondary and non-load-bearing
```

The prohibition on an aggregate semantic field is deliberate: a ledger that could
carry a summary verdict would recreate, one level up, exactly the defect this
projection exists to close.

## 4. Frozen criterion order

```
 1 T-EARLY-01      2 T-EARLY-02      3 T-EARLY-03      4 T-EARLY-04
 5 T-EARLY-05      6 T-POS-01        7 T-POS-02        8 T-POS-03
 9 T-POS-04       10 T-POS-05       11 T-POS-06       12 T-CASE-A
13 T-CASE-B       14 T-CASE-C       15 T-CASE-D       16 T-CASE-E
17 T-CASE-F       18 T-CASE-G       19 T-CASE-H       20 T-CASE-I
21 T-CASE-J       22 T-CASE-K       23 T-CASE-L       24 T-CASE-M
25 T-CASE-N       26 T-CASE-O       27 T-CASE-P       28 T-CASE-Q
29 T-CASE-R       30 T-CASE-S       31 T-DIG-01       32 T-DIG-02
33 T-DIG-03       34 T-DIG-04       35 T-DIG-05       36 T-DIG-06
37 T-DIG-07       38 T-DIG-08       39 T-EPOCH-A      40 T-EPOCH-B
41 T-EPOCH-C
```

This is the order of semantic design v0.4 §12, unchanged. It is a *frozen
sequence*, not a sortable list: any canonicalization that reorders it produces a
different ledger and is malformed.

## 5. No self-reference

```
a CriterionObservation MUST NOT contain its own persisted-file sha256
```

Its `observation_digest` is computed from its contents alone. The ledger, written
**after** the observation files are persisted, binds `observation_digest`,
`persisted_file_sha256`, `persisted_file_bytes` and `observation_path` together.

Write ordering, so no object depends on a digest computed over itself or over a
later object:

```
1  projection v0.2 frozen and persisted                    → its sha256 exists
2  each CriterionObservation written and persisted         → content digest + file digest exist
3  CriterionEvidenceLedger written, binding all 41 pairs   → ledger digest exists
```

A ledger written before its observation files were persisted is invalid by
construction.

## 6. Dependency, restated

The two digest classes implied by this projection — `criterion_observation_digest`
and `criterion_ledger_digest` — are **not frozen by this document**. Derivation
v0.4 §11 requires any new class to be published in a versioned successor before
the execution that produces it. `INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.5.md`
must therefore be frozen before RUN-002.

## 7. Unchanged

Semantic design v0.4, the 41 criteria, their expected outcomes, the 36 reason
codes and the claim ceiling are untouched by this document. So is the substantive
per-criterion model of projection v0.1, which remains the reference for *what* to
observe; this successor governs only *how the observation and ledger objects are
identified*.

This projection still adjudicates nothing, and it still supports no target claim
of the slice: the six pipeline maxima remain properties of an executed pipeline.
