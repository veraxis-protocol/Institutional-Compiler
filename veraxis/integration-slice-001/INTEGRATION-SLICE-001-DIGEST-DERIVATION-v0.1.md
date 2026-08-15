# INTEGRATION SLICE 001 — DIGEST DERIVATION v0.1

```
author          Vitaliy Reznik (semantics)
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
```

## 1. Canonical serialization

Identical to the rule frozen for Currentness Slice 001, reproduced here so this
document stands alone:

```
encoding          UTF-8
key order         lexicographic by code point
ensure_ascii      false
indentation       none
item separator    ","
key separator     ":"
array order       preserved as constructed; never re-sorted at serialization time
trailing newline  none in the hashed byte sequence
algorithm         SHA-256
digest form       lowercase hex, UNPREFIXED
null              a value; participates; never omitted
self-digest       excluded by key removal, never by null substitution
```

Reference micro-vector (unchanged, verifies separators, ordering, non-ASCII):

```
{"b": 2, "a": "é"}  →  {"a":"é","b":2}
                    →  06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de
```

## 2. Class 1 — `currentness_epoch_digest` (AS-OF PROJECTION)

The load-bearing class. Definition:

```
currentness_epoch_digest(output_ref, as_of) = sha256(canonical({
    "output_ref": <literal>,
    "completeness_attestation_digest": <digest or null>,
    "operative_basis_records": [
        {record_ref, record_digest, record_class, effective_at, admitted_at}
        for each governing record R such that
            R.admitted_at  <= as_of      AND
            R.effective_at <= as_of      AND
            R.output_ref   == output_ref
    ]
}))
```

Ordering of `operative_basis_records`: ascending by
`(effective_at, admitted_at, record_ref)`. Deterministic, independent of index
insertion order.

Inclusion rules, frozen:

- **Scope**: only records governing the queried `output_ref`. Records governing
  other outputs never enter, at any `as_of`.
- **Admission**: `admitted_at <= as_of` — a record not yet admitted is not
  knowledge.
- **Operativeness**: `effective_at <= as_of` — a record admitted but not yet
  effective is known and **not operative**, so it is excluded from the projection.
- **Completeness attestation**: its digest participates, or `null` when none
  supports the state. Replacing the attestation while leaving basis records
  untouched therefore moves the epoch.
- **`as_of` itself is NOT a field of the digested object.** The epoch changes
  because governed effective/admitted state crossed a boundary, never because the
  clock advanced.

### Reference vectors — computed, not illustrative

Common subject `CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01`; one successor record
admitted `2026-08-15T09:00:00Z`, effective `2026-08-15T12:00:00Z`; attestation
digest `eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7`.

```
VECTOR EPOCH-A   as_of = 2026-08-15T10:00:00Z
  successor admitted but NOT yet operative → excluded; attestation present
  canonical bytes 185
  digest  407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46

VECTOR EPOCH-B   as_of = 2026-08-15T13:00:00Z
  the SAME successor, now operative → included; state no longer CURRENT so
  attestation is null
  canonical bytes 414
  digest  6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac

REQUIRED: EPOCH-A != EPOCH-B                                     verified

VECTOR EPOCH-C   control — as_of = 2026-08-15T10:00:00Z, identical query, while an
  unrelated output (CDC-E2E-OUTPUT-02) receives a new operative successor
  digest  407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46

REQUIRED: EPOCH-C == EPOCH-A                                     verified
```

The two requirements together are the whole point: **fail closed without fail
noisy.** A crossing of effective time moves the epoch; a change to a different
output does not; and no vector depends on `evaluated_at`.

## 3. Class 2 — `authority_basis_record_digest`

```
domain    one synthetic authority or admissibility basis record exactly as stored
excluded  nothing (basis records carry no self-digest)
rule      sha256(canonical(record))
```

Both authority-basis and admissibility-basis records use this one class; they are
distinguished by their `record_class` field, not by a separate digest rule.

## 4. Class 3 — `authority_decision_digest`

```
domain    the AuthorityDecisionRecord
excluded  authority_decision_digest
included  currentness_resolution_digest, currentness_epoch_digest, valid_until,
          evaluation_time, decision, reason_code — all participate
rule      sha256(canonical(decision minus authority_decision_digest))
```

A decision evaluated at reliance time is a *different record* from the propagated
one and therefore has a different digest even when its outcome matches. That is
intended: §6 of the design binds both.

## 5. Class 4 — `envelope_digest`

```
domain    the GovernedPropagationEnvelope
excluded  envelope_digest
included  all three principal roles (requesting subject, producer identity,
          intended consumer) as separate fields
rule      sha256(canonical(envelope minus envelope_digest))
```

The envelope schema is closed: any field not in the frozen schema is a validation
failure (`P8`), not a field to be hashed over silently.

## 6. Class 5 — `consumer_validation_digest`

```
domain    {envelope_digest, checks[], decision, reason_code, consumer_identity,
           evaluated_at, re_resolved_currentness_resolution_digest,
           observed_currentness_epoch_digest,
           reliance_time_authority_decision_digest}
checks[]  each {check_id, expected, observed, passed}, in frozen check order 1..15
excluded  consumer_validation_digest
rule      sha256(canonical(record minus consumer_validation_digest))
```

`evaluated_at` participates here deliberately: a validation is an observation at
an instant, unlike an epoch which is a projection of state.

## 7. Class 6 — `reliance_record_digest`

```
domain    the RelianceIssuanceRecord
excluded  reliance_record_digest
included  BOTH authority moments — propagated_authority_decision_digest and
          reliance_time_authority_decision_digest — and the RE-RESOLVED
          currentness_resolution_digest and observed currentness_epoch_digest
rule      sha256(canonical(record minus reliance_record_digest))
```

## 8. Class 7 — `integration_package_digest`

```
domain    the raw execution package
excluded  package_digest
members   member identities as {path, bytes, sha256}; member bodies not embedded
rule      sha256(canonical(package minus package_digest))
```

## 9. Persisted-file SHA-256

Distinct from every class above and never conflated with them:

```
rule  sha256 over the exact bytes of the persisted file, including any trailing
      newline the file actually has
```

The hashed canonical form carries no trailing newline; a persisted file may. Both
are legitimate and they differ — that difference is the point, and any comparison
that mixes them is an implementation defect.

## 10. Prefix handling and freeze

All digests are recorded unprefixed. Where a record must interoperate with an
object using `sha256:`, the prefix is presentation and is stripped before any
comparison.

Seven digest classes are frozen here. Any class introduced later requires a
versioned successor to this document, published before the execution that produces
it.
