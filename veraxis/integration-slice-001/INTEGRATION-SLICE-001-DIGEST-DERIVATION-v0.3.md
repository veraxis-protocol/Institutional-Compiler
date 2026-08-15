# INTEGRATION SLICE 001 — DIGEST DERIVATION v0.3

```
supersedes      INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.2.md
                sha256 d1a961489f7bcba08be5afaf5c90ffbdea11e0de734bc90c2f03d895ac350a6f
                8731 B — preserved unchanged as a historical artifact
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
```

Sole change from v0.2: Class 5 `consumer_validation_digest` now freezes `checks[]`
in order **1..16**, following the semantic design v0.4 correction that restores the
propagated authority-decision freshness check. All other classes, rules and
vectors are carried forward byte-identically in meaning.

## 1. Canonical serialization

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

Unchanged. Inclusion: records governing this `output_ref` with
`admitted_at ≤ as_of` **and** `effective_at ≤ as_of`; ordered by
`(effective_at, admitted_at, record_ref)`; `completeness_attestation_digest`
participates; `as_of` is **not** a digested field.

```
EPOCH-A  as_of 2026-08-15T10:00:00Z   185 B
         407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46
EPOCH-B  as_of 2026-08-15T13:00:00Z   414 B
         6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac
EPOCH-C  control, unrelated output changed
         407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46

REQUIRED  EPOCH-A ≠ EPOCH-B   and   EPOCH-C = EPOCH-A     both verified
```

## 3. Class 2 — `authority_basis_record_digest`

```
domain    SyntheticAuthorityBasisRecord or SyntheticAdmissibilityBasisRecord
excluded  record_digest
rule      record_digest = sha256(canonical(record minus record_digest))
required  stored value MUST reproduce; non-reproduction is INVALID —
          A12 for an authority basis, A5 for an admissibility basis
```

```
BASIS-AUTH-1   431 B  7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e
BASIS-ADM-1    371 B  bf29f3d75a313301c223fd12183f6f7c134cb1683c8d388d7377fb401d2219e3
```

## 4. Class 3 — `authority_decision_digest`

Unchanged: decision minus `authority_decision_digest`;
`currentness_resolution_digest`, `currentness_epoch_digest`, `valid_until`,
`evaluation_time`, `decision`, `reason_code` all participate. A reliance-time
re-evaluation is a different record with a different digest — which is precisely
why check 11 (identity) and check 15 (re-evaluation) are separate steps.

## 5. Class 4 — `envelope_digest`

Unchanged: envelope minus `envelope_digest`; the three principal roles
participate as separate fields; closed schema, unknown field → `P8`.

## 6. Class 5 — `consumer_validation_digest` (CHANGED)

```
domain    {envelope_digest, checks[], decision, reason_code, consumer_identity,
           evaluated_at, re_resolved_currentness_resolution_digest,
           observed_currentness_epoch_digest,
           reliance_time_authority_decision_digest}
checks[]  FROZEN ORDER 1..16, one entry per check, each
          {check_id, check_name, expected, observed, passed}
          array order is NEVER re-sorted; check_id 1..16 must appear ascending
excluded  consumer_validation_digest
rule      sha256(canonical(record minus consumer_validation_digest))
```

Frozen `checks[]` order, matching semantic design v0.4 §2:

```
 1 envelope_integrity              9 evidence_resolvability
 2 schema_closure                 10 producer_identity
 3 envelope_freshness             11 propagated_authority_decision_identity
 4 artifact_identity              12 propagated_authority_decision_freshness   ← restored
 5 scope_binding                  13 currentness_re_resolution
 6 subject_principal_binding      14 epoch_applicability
 7 requested_use_binding          15 authority_admissibility_re_evaluation
 8 intended_consumer_binding      16 issuance_gate
```

A validation record whose `checks[]` is shorter than 16, or out of order, is
malformed — the digest is not the place where that is discovered, but the order is
frozen here so that two implementations cannot produce different digests for the
same observations.

`evaluated_at` participates, deliberately: a validation is an observation at an
instant, unlike an epoch, which is a projection of state.

## 7. Class 6 — `reliance_record_digest`

Unchanged: both authority moments participate
(`propagated_authority_decision_digest`,
`reliance_time_authority_decision_digest`), with the re-resolved currentness
resolution digest and the observed epoch digest.

## 8. Class 7 — `integration_package_digest`

Unchanged: package minus `package_digest`; members as `{path, bytes, sha256}`;
member bodies not embedded.

## 9. Class 8 — `synthetic_profile_digest`

```
domain    SyntheticProducerProfile or SyntheticRelianceConsumerProfile
excluded  profile_digest
rule      profile_digest = sha256(canonical(profile minus profile_digest))
required  stored value MUST reproduce
```

```
PROFILE-PRODUCER-1   398 B  1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c
PROFILE-CONSUMER-1   416 B  889ab97b43b110cf738bb2954dcc0ca19ed352f14a05207437dbb92192d0d5ec
```

## 10. Persisted-file identities

```
issuance_authorization_digest = sha256(exact persisted bytes of the authorization file)
attempt_record_digest         = sha256(exact persisted bytes of the attempt record file)
```

Write ordering, excluding an identity cycle:

```
1  authorization file finalized and persisted                    → digest exists
2  attempt record written binding it, then FROZEN                 → digest exists
3  RelianceIssuanceRecord written only after step 2, binding both
```

A reliance record written before its attempt record was frozen is invalid by
construction.

## 11. Prefix handling, count, freeze

Digests are recorded unprefixed; a `sha256:` prefix on an interoperating object is
presentation and is stripped before comparison.

```
canonical digest classes frozen here   8
separately frozen file-identity rules  2   plus the general persisted-file rule
```

Any class introduced later requires a versioned successor published before the
execution that produces it.
