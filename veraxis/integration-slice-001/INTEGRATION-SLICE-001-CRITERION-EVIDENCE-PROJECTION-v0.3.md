# INTEGRATION SLICE 001 — CRITERION EVIDENCE PROJECTION v0.3

```
supersedes                  INTEGRATION-SLICE-001-CRITERION-EVIDENCE-PROJECTION-v0.2.md
                            sha256 00af89d21fda41adaf4a95d5938d3b6fc90666d4ebf902b9c205aa42e7974db2
                            7714 B — preserved unchanged
                            (v0.1, 8fed5223…, 11720 B, likewise preserved)
classification              EVIDENCE_PROJECTION_ONLY
SEMANTIC_CONTROL            FALSE
SEMANTIC_CRITERIA_MODIFIED  FALSE
TEST_COUNT                  41
result_bearing_execution    NONE
controlling semantic design CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md
                            sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
                            — unchanged by this document
```

**Narrow successor.** One evidence minimum is corrected: `T-POS-06`. Everything
else in v0.1 and v0.2 — the universal envelope, the five group projections, the
other criterion-specific minima, the identity bindings, `node_accounting` and the
`CriterionEvidenceLedger` — is carried forward unchanged.

## 1. Conceded defect

Projection v0.1 §3 required, for `T-POS-06`:

> write-order timestamps for the three files

The governed issuance-authorization object has **no timestamp field**. The
requirement was therefore unsatisfiable from governed records alone, and the only
way to satisfy it as written would have been to read a filesystem `mtime` — which
is precisely the substitution that must never occur. I specified an evidence
minimum that could only be met by an inadmissible source. The defect is mine.

The correction below is **not a weakening**. Ordering was already established in
semantic design v0.3 §4 (carried unchanged into v0.4 §4) by digest chaining, and
a digest binding is the stronger fact: it proves the bound object *existed in its
final bytes* at the moment of binding. A timestamp only asserts when a writer
believed it was writing.

## 2. `T-POS-06` — corrected evidence minimum

Replaces the three-timestamp requirement. Ordering to be established:

```
AUTHORIZATION → ATTEMPT → RELIANCE
```

### A. Issuance authorization

```
authorization_path
authorization_persisted_file_bytes
authorization_persisted_file_sha256
authorization_timestamp           actual governed timestamp if the record has one, otherwise null
authorization_timestamp_status    PRESENT_IN_GOVERNED_RECORD | ABSENT_IN_GOVERNED_RECORD
```

`ABSENT_IN_GOVERNED_RECORD` is a complete and acceptable observation. No
filesystem `mtime`, `ctime`, `birthtime` or any other filesystem metadata may be
recorded in `authorization_timestamp`, and none may be substituted for a governed
timestamp anywhere in this projection.

### B. Attempt record

```
attempt_path
attempt_persisted_file_bytes
attempt_persisted_file_sha256
claimed_at
issuance_authorization_digest_bound_in_attempt
```

Required comparison, archived with both operands and its result:

```
issuance_authorization_digest_bound_in_attempt == authorization_persisted_file_sha256
```

### C. Reliance record

```
reliance_path
reliance_persisted_file_bytes
reliance_persisted_file_sha256
issued_at
issuance_authorization_digest_bound_in_reliance
attempt_record_digest_bound_in_reliance
```

Required comparisons, each archived with both operands and its result:

```
issuance_authorization_digest_bound_in_reliance == authorization_persisted_file_sha256
attempt_record_digest_bound_in_reliance         == attempt_persisted_file_sha256
```

### D. Temporal corroboration, where timestamps exist

```
claimed_at <= issued_at      operands and comparison result archived
```

If either timestamp is absent from its governed record, the comparison is archived
as `NOT_EVALUABLE` with the reason, never as a pass and never as a failure.

## 3. Ordering interpretation — frozen

```
AUTHORIZATION_PRECEDES_ATTEMPT
  established by the attempt record binding the digest of the already-persisted
  authorization bytes. A digest cannot be bound to bytes that do not yet exist.

ATTEMPT_PRECEDES_RELIANCE
  established by the reliance record binding the persisted attempt-record digest,
  by the same argument.

timestamps on attempt and reliance
  corroborating temporal observations only; they neither establish nor defeat the
  causal ordering, which rests on the digest chain.

an authorization timestamp
  NOT REQUIRED when the governed authorization record has none.

filesystem metadata
  may never substitute for a governed timestamp, in any field, for any purpose.
```

Two consequences worth stating plainly. First, an archive in which all three
timestamps are absent still establishes the full ordering, because the digest
chain carries it. Second, an archive in which the timestamps are present and
consistent but a digest comparison fails does **not** establish the ordering — the
corroborating observation cannot rescue the load-bearing one.

## 4. No relaxation

Semantic design v0.4 is unchanged. `T-POS-06` is unchanged. The 41 criteria, their
expected outcomes, the 36 reason codes and the claim ceiling are unchanged. What
changed is only *which observations a run must archive* to establish a property
that was already frozen, aligned to the ordering semantic design v0.3 §4 already
specified:

```
authorization persisted → attempt binds authorization digest → reliance binds
attempt and authorization identities
```

## 5. Unchanged from v0.1 and v0.2

The universal observation envelope and its identity bindings; `node_accounting`;
the `CriterionEvidenceLedger` with 41 entries in frozen order, binding content
identity and persisted-file identity separately, with no aggregate verdict field;
the frozen criterion order; the no-self-reference rule and the write ordering of
the criterion layer; and the standing prohibition on converting an observation
into an adjudication.

The two digest classes bound to this projection's identity —
`criterion_observation_digest` (Class 9) and `criterion_ledger_digest` (Class 10) —
require a derivation successor carrying this document's sha256, since their
reference fixtures bind `criterion_evidence_projection_sha256`.

This projection still adjudicates nothing, and still supports no target claim of
the slice.
