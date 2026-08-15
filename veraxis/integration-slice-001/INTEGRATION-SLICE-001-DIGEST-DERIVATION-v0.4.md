# INTEGRATION SLICE 001 — DIGEST DERIVATION v0.4

```
supersedes      INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.3.md
                sha256 600a8f19eef3bba635ba4349ee1b46e0f23baa66dfe0b87c0d84223d6b686bfd
                6555 B — preserved unchanged as a historical artifact
controlling semantic design  …SEMANTIC-DESIGN-v0.4.md
                sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
                — unchanged by this document
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
```

**Sole change from v0.3:** §2 now publishes the *complete* inputs for all three
epoch vectors. No rule, class, count or semantic property is altered.

## 0. The defect being repaired

v0.1–v0.3 published the epoch vector *results* and the inclusion rules, but for
EPOCH-B they did not publish the successor basis record's `record_digest`. That
value enters the digested object, so an implementer holding only the published
document could not reconstruct EPOCH-B. This is a pre-execution reproducibility
defect and it is mine: I verified my own vectors against my own inputs, which is
exactly the check that cannot catch a missing input.

**The original input was recovered, not reconstructed.** The `record_digest`
below is the value that actually entered the computation which produced
`6858b71d…`; it is not a value chosen to obtain that result. Its provenance is
the frozen Currentness Slice RUN-001 evidence, where it appears as the
`basis_record_digest` bound to `CDC-E2E-OUTPUT-01` for the controlling successor
`EBAWU-P-001-C-TENDER-01-CORR-002`. Recovery was confirmed by recomputation
before publication: 414 canonical bytes and the identical digest.

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

## 2. Class 1 — `currentness_epoch_digest` (as-of projection) — COMPLETE INPUTS

```
currentness_epoch_digest(output_ref, as_of) = sha256(canonical({
  "output_ref": <literal>,
  "completeness_attestation_digest": <digest or null>,
  "operative_basis_records": [ {record_ref, record_digest, record_class,
                                effective_at, admitted_at}
      for each governing record R of THIS output with
          R.admitted_at <= as_of  AND  R.effective_at <= as_of ]
}))
```

Ordering: ascending `(effective_at, admitted_at, record_ref)`. `as_of` is **not**
a digested field.

### Shared fixture used by all three vectors

```
output_ref  CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01

completeness attestation (its digest is what enters the epoch):
  eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7

successor basis record S:
  output_ref     CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01
  record_ref     EBAWU-P-001-C-TENDER-01-CORR-002#CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01
  record_digest  943affbf3e86d8a1b6831eb3deafb2efeac902989d8ee75fe85daea6f82e1e3c
  record_class   CORRECTION_SUCCESSOR_RECORD
  effective_at   2026-08-15T12:00:00Z
  admitted_at    2026-08-15T09:00:00Z
```

### VECTOR EPOCH-A — `as_of = 2026-08-15T10:00:00Z`

S is admitted (09:00 ≤ 10:00) but **not operative** (12:00 > 10:00) → excluded.
State is CURRENT, so the attestation participates.

```
exact reduced object entering the digest:
{"completeness_attestation_digest":"eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7","operative_basis_records":[],"output_ref":"CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"}

canonical bytes 185
digest          407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46
```

### VECTOR EPOCH-B — `as_of = 2026-08-15T13:00:00Z`

The same S is now operative (12:00 ≤ 13:00) → included. State is no longer
CURRENT, so `completeness_attestation_digest` is `null`.

```
exact reduced object entering the digest:
{"completeness_attestation_digest":null,"operative_basis_records":[{"admitted_at":"2026-08-15T09:00:00Z","effective_at":"2026-08-15T12:00:00Z","record_class":"CORRECTION_SUCCESSOR_RECORD","record_digest":"943affbf3e86d8a1b6831eb3deafb2efeac902989d8ee75fe85daea6f82e1e3c","record_ref":"EBAWU-P-001-C-TENDER-01-CORR-002#CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"}],"output_ref":"CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"}

canonical bytes 414
digest          6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac
```

Every field is now published; the object above is byte-exact and needs no
inference.

### VECTOR EPOCH-C — control, `as_of = 2026-08-15T10:00:00Z`

Identical query while an unrelated output (`CDC-E2E-OUTPUT-02`) receives an
operative successor. That record's `output_ref` differs, so it never enters this
output's projection at any `as_of`; the digested object is byte-identical to
EPOCH-A.

```
canonical bytes 185
digest          407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46
```

### Required properties

```
EPOCH-A != EPOCH-B     effective-time crossing moves the epoch        verified
EPOCH-C == EPOCH-A     unrelated output change does not               verified
as_of not digested     a clock tick alone never moves the epoch       by construction
```

## 3. Class 2 — `authority_basis_record_digest`

Unchanged.

```
domain    SyntheticAuthorityBasisRecord or SyntheticAdmissibilityBasisRecord
excluded  record_digest
rule      record_digest = sha256(canonical(record minus record_digest))
required  stored value MUST reproduce; non-reproduction is INVALID —
          A12 for an authority basis, A5 for an admissibility basis

BASIS-AUTH-1   431 B  7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e
BASIS-ADM-1    371 B  bf29f3d75a313301c223fd12183f6f7c134cb1683c8d388d7377fb401d2219e3
```

The full field lists for both vectors are published in v0.2 §3 and are unchanged.

## 4. Class 3 — `authority_decision_digest`

Unchanged: decision minus `authority_decision_digest`;
`currentness_resolution_digest`, `currentness_epoch_digest`, `valid_until`,
`evaluation_time`, `decision`, `reason_code` all participate.

## 5. Class 4 — `envelope_digest`

Unchanged: envelope minus `envelope_digest`; three principal roles as separate
fields; closed schema, unknown field → `P8`.

## 6. Class 5 — `consumer_validation_digest`

Unchanged from v0.3: `checks[]` frozen in order **1..16**, each entry
`{check_id, check_name, expected, observed, passed}`, array never re-sorted,
`check_id` ascending 1..16:

```
 1 envelope_integrity              9 evidence_resolvability
 2 schema_closure                 10 producer_identity
 3 envelope_freshness             11 propagated_authority_decision_identity
 4 artifact_identity              12 propagated_authority_decision_freshness
 5 scope_binding                  13 currentness_re_resolution
 6 subject_principal_binding      14 epoch_applicability
 7 requested_use_binding          15 authority_admissibility_re_evaluation
 8 intended_consumer_binding      16 issuance_gate
```

`evaluated_at` participates.

## 7. Class 6 — `reliance_record_digest`

Unchanged: both authority moments participate, with the re-resolved currentness
resolution digest and the observed epoch digest.

## 8. Class 7 — `integration_package_digest`

Unchanged: package minus `package_digest`; members as `{path, bytes, sha256}`.

## 9. Class 8 — `synthetic_profile_digest`

Unchanged.

```
domain    SyntheticProducerProfile or SyntheticRelianceConsumerProfile
excluded  profile_digest
rule      profile_digest = sha256(canonical(profile minus profile_digest))

PROFILE-PRODUCER-1   398 B  1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c
PROFILE-CONSUMER-1   416 B  889ab97b43b110cf738bb2954dcc0ca19ed352f14a05207437dbb92192d0d5ec
```

Full field lists are published in v0.2 §9 and are unchanged.

## 10. Persisted-file identities

Unchanged.

```
issuance_authorization_digest = sha256(exact persisted bytes of the authorization file)
attempt_record_digest         = sha256(exact persisted bytes of the attempt record file)

write ordering: authorization persisted → attempt record written and FROZEN →
                RelianceIssuanceRecord written, binding both
```

## 11. Standing requirement introduced by this repair

Every future vector in this slice must be published as the **exact object entering
the digest**, not as a result plus a prose description of its inputs. A vector that
cannot be recomputed from the document alone is not a vector; it is an assertion.
This applies to any successor document.

```
canonical digest classes frozen here   8
separately frozen file-identity rules  2   plus the general persisted-file rule
```
