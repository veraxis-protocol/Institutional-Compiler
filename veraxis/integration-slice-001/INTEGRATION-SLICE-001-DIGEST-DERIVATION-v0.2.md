# INTEGRATION SLICE 001 — DIGEST DERIVATION v0.2

```
supersedes      INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.1.md
                sha256 9d4e61a2b99f412be4de72d11b73d192eb3063a46156f03d2133ef226c0b3dc0
                7355 B — preserved unchanged as a historical artifact
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
```

Changes from v0.1: Class 2 corrected (basis records **do** carry a self-digest,
now excluded from their own computation, with two computed vectors); new Class 8
`synthetic_profile_digest` with two computed vectors; explicit rules for
`issuance_authorization_digest` and `attempt_record_digest`; explicit write
ordering to exclude an identity cycle. Nothing else is altered.

## 1. Canonical serialization

Unchanged from v0.1 and reproduced so this document stands alone:

```
UTF-8 · keys sorted lexicographically · ensure_ascii=false · no indentation
item separator ","  ·  key separator ":"  ·  no trailing newline in hashed bytes
SHA-256 · lowercase hex · UNPREFIXED · null participates
self-digest excluded by KEY REMOVAL, never by null substitution
array order preserved as constructed
```

Micro-vector: `{"b": 2, "a": "é"}` → `{"a":"é","b":2}` →
`06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de`

## 2. Class 1 — `currentness_epoch_digest` (as-of projection)

Unchanged from v0.1 §2, including inclusion rules, ordering, the exclusion of
`as_of` from the digested object, and the participation of
`completeness_attestation_digest`. Vectors carried forward verbatim:

```
EPOCH-A  as_of 2026-08-15T10:00:00Z  successor admitted, NOT operative → excluded
         185 B   407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46
EPOCH-B  as_of 2026-08-15T13:00:00Z  same successor operative → included
         414 B   6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac
EPOCH-C  control, unrelated output changed
                 407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46

REQUIRED  EPOCH-A ≠ EPOCH-B   and   EPOCH-C = EPOCH-A     both verified
```

## 3. Class 2 — `authority_basis_record_digest` (CORRECTED)

v0.1 stated that basis records carry no self-digest, contradicting the semantic
design, which gives both basis record types a `record_digest` field. The owner
decision is adopted: **the field is kept and excluded from its own computation.**

```
domain    one SyntheticAuthorityBasisRecord or SyntheticAdmissibilityBasisRecord
excluded  record_digest
rule      record_digest = sha256(canonical(record minus record_digest))
required  the stored record_digest MUST equal that recomputation; a record whose
          stored digest does not reproduce is INVALID — A12 for an authority
          basis, A5 for an admissibility basis
```

One class serves both record types; they are distinguished by `record_class`, not
by a separate rule. The reproducibility requirement is what makes the
authority/admissibility validation branches independently checkable rather than
self-asserted.

### Vector BASIS-AUTH-1

```
{"record_class":"SYNTHETIC_AUTHORITY_BASIS","basis_id":"SYNTH-AUTH-BASIS-001",
 "principal_id":"SYNTHETIC-SUBJECT-PRINCIPAL-001","scope":"CDC-DEMO-SCOPE-001",
 "permitted_requested_use":["DEMONSTRATION_READ"],
 "validity_from":"2026-08-15T00:00:00Z","validity_until":"2026-08-22T00:00:00Z",
 "revocation_state":"NOT_REVOKED","supersedes":null,"superseded_by":null,
 "admitted_at":"2026-08-15T00:00:00Z","effective_at":"2026-08-15T00:00:00Z"}

canonical bytes 431
record_digest   7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e
```

### Vector BASIS-ADM-1

```
{"record_class":"SYNTHETIC_ADMISSIBILITY_BASIS","basis_id":"SYNTH-ADM-BASIS-001",
 "artifact_class_admitted":["SYNTHETIC_FIXTURE_OUTPUT"],
 "requested_use_admitted":["DEMONSTRATION_READ"],
 "validity_from":"2026-08-15T00:00:00Z","validity_until":"2026-08-22T00:00:00Z",
 "revocation_state":"NOT_REVOKED",
 "admitted_at":"2026-08-15T00:00:00Z","effective_at":"2026-08-15T00:00:00Z"}

canonical bytes 371
record_digest   bf29f3d75a313301c223fd12183f6f7c134cb1683c8d388d7377fb401d2219e3
```

Both vectors omit `record_digest` from the object shown, because that is exactly
what the rule excludes.

## 4. Class 3 — `authority_decision_digest`

Unchanged from v0.1: domain is the whole decision, `authority_decision_digest`
excluded; `currentness_resolution_digest`, `currentness_epoch_digest`,
`valid_until`, `evaluation_time`, `decision` and `reason_code` all participate. A
reliance-time re-evaluation is a different record and therefore a different
digest, which is intended.

## 5. Class 4 — `envelope_digest`

Unchanged from v0.1, with all three principal roles participating as separate
fields. Closed schema: an unknown field is a validation failure (`P8`), never a
field silently hashed over.

## 6. Class 5 — `consumer_validation_digest`

Unchanged from v0.1, except that the frozen check order is now **1..15** (the
reliance-time authority re-evaluation is check 14, issuance gate is 15).
`evaluated_at` participates, deliberately, because a validation is an observation
at an instant.

## 7. Class 6 — `reliance_record_digest`

Unchanged from v0.1: both authority moments participate
(`propagated_authority_decision_digest` and
`reliance_time_authority_decision_digest`), together with the re-resolved
currentness resolution digest and the observed epoch digest.

## 8. Class 7 — `integration_package_digest`

Unchanged from v0.1: package minus `package_digest`; members as
`{path, bytes, sha256}`; member bodies not embedded.

## 9. Class 8 — `synthetic_profile_digest` (NEW)

Required because consumer check P10 verifies producer identity against the frozen
profile, and v0.1 defined no rule for `profile_digest`.

```
domain    one SyntheticProducerProfile or SyntheticRelianceConsumerProfile
excluded  profile_digest
rule      profile_digest = sha256(canonical(profile minus profile_digest))
required  the stored profile_digest MUST equal that recomputation
```

One class for both, distinguished by `record_class` / `profile_id`.

### Vector PROFILE-PRODUCER-1

```
{"record_class":"SYNTHETIC_PRODUCER_PROFILE","profile_id":"SYNTH-PRODUCER-PROFILE-001",
 "principal_id":"SYNTHETIC-PRODUCER-PRINCIPAL-001","role":"PRODUCER",
 "scope":"CDC-DEMO-SCOPE-001","permitted_requested_use":["DEMONSTRATION_READ"],
 "validity_from":"2026-08-15T00:00:00Z","validity_until":"2026-08-22T00:00:00Z",
 "revocation_state":"NOT_REVOKED","assurance_class":"INTERNAL_TECHNICAL_DEMONSTRATION"}

canonical bytes 398
profile_digest  1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c
```

### Vector PROFILE-CONSUMER-1

```
same shape with
  record_class "SYNTHETIC_RELIANCE_CONSUMER_PROFILE"
  profile_id   "SYNTH-CONSUMER-PROFILE-001"
  principal_id "SYNTHETIC-CONSUMER-PRINCIPAL-001"
  role         "RELIANCE_CONSUMER"

canonical bytes 416
profile_digest  889ab97b43b110cf738bb2954dcc0ca19ed352f14a05207437dbb92192d0d5ec
```

## 10. Persisted-file identities — `issuance_authorization_digest` and `attempt_record_digest`

Neither is a canonical object digest. Both use the persisted-file rule, frozen
here so implementation has no choice to make:

```
issuance_authorization_digest = sha256(exact persisted bytes of the issuance
                                       authorization file, including any trailing
                                       newline the file actually has)

attempt_record_digest         = sha256(exact persisted bytes of the attempt
                                       record file, same rule)
```

**Write ordering, to exclude an identity cycle:**

```
1  the issuance authorization file is finalized and persisted   → its digest exists
2  the attempt record is written, binding the authorization digest, and is
   FROZEN — its bytes do not change afterwards                  → its digest exists
3  the RelianceIssuanceRecord is written only after step 2, binding both digests
```

The attempt record therefore never needs to know the reliance record's digest, and
no object depends on a digest computed over itself or over a later object. A
reliance record written before its attempt record was frozen is invalid by
construction.

## 11. Prefix handling, count, freeze

All digests unprefixed; a `sha256:` prefix on any interoperating object is
presentation and is stripped before comparison.

```
canonical digest classes frozen here   8
separately frozen file-identity rules  2  (issuance authorization, attempt record)
                                          plus the general persisted-file rule
```

Any class introduced later requires a versioned successor to this document,
published before the execution that produces it.
