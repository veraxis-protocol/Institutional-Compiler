# CDC CURRENTNESS-TO-RELIANCE INTEGRATION SLICE 001 — SEMANTIC DESIGN v0.3

```
supersedes        …SEMANTIC-DESIGN-v0.2.md
                  sha256 8e02820dab3bb939f91de86f9cc98135ee0adbb512b53de6ae50cbfab1af11fd
                  15728 B, ZTL commit de32cb166133d33911189b9b38b21af80244d2f6
                  — preserved unchanged as a historical artifact
companion         INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.2.md
assurance_class   INTERNAL_TECHNICAL_DEMONSTRATION
self_designed_and_self_adjudicated TRUE   independent_review_claim FALSE
result_bearing_execution NONE             status READY_FOR_OWNER_REVIEW_v0.3
```

**Narrow successor revision.** Four specification inconsistencies are resolved.
The architecture of v0.2 is unchanged: the as-of currentness epoch, mandatory
reliance-time re-resolution, epoch applicability of authority decisions, real
process-boundary propagation, reliance-time authority re-evaluation, and the
two TOCTOU criteria all stand exactly as frozen.

## 1. Basis-record digest — circularity removed

v0.2 gave both basis record types a `record_digest` field while derivation v0.1
declared that basis records carry no self-digest. Both could not be true; the
defect is mine. Owner decision adopted:

```
record_digest = sha256(canonical(record minus record_digest))
the stored record_digest MUST equal that recomputation
```

Non-reproduction is an invalidity finding, not a warning: `A12` for an authority
basis, `A5` for an admissibility basis. This is what makes the validation branches
independently checkable rather than self-asserted. Vectors `BASIS-AUTH-1`
(`7ad84cfb…`, 431 B) and `BASIS-ADM-1` (`bf29f3d7…`, 371 B) are published in the
companion document.

## 2. Profile objects — count stated honestly, digest class added

**There are two profile objects, not three.** v0.2 named three principals under a
heading that then defined only producer and consumer profiles, which reads as a
claim of three profile objects. Stated explicitly:

```
SyntheticProducerProfile          → SYNTHETIC-PRODUCER-PRINCIPAL-001
SyntheticRelianceConsumerProfile  → SYNTHETIC-CONSUMER-PRINCIPAL-001

the requesting SUBJECT principal (SYNTHETIC-SUBJECT-PRINCIPAL-001) has NO separate
profile object; it is represented solely by SyntheticAuthorityBasisRecord.principal_id
```

That is deliberate — the subject's standing *is* the authority basis, and giving
it a second home would create two places where subject authority could disagree.

`synthetic_profile_digest` is added as digest **Class 8**, since consumer check
P10 verifies producer identity against the frozen profile and v0.2 left the rule
undefined:

```
profile_digest = sha256(canonical(profile minus profile_digest))
```

Vectors `PROFILE-PRODUCER-1` (`1c7ac979…`, 398 B) and `PROFILE-CONSUMER-1`
(`889ab97b…`, 416 B) are published in the companion document.

```
new_digest_class_count   7 → 8
```

## 3. Authority / admissibility codes — misbinding corrected

v0.2's deterministic procedure routed *authority*-basis failures to `A4`/`A5`,
whose names describe *admissibility*, and routed admissibility revocation to
`A10 AUTHORITY_BASIS_REVOKED`. Having separated the two object classes, collapsing
their codes was a real error. Three codes added and the whole set rebound:

```
A11 AUTHORITY_BASIS_MISSING          A4  ADMISSIBILITY_BASIS_MISSING
A12 AUTHORITY_BASIS_INVALID          A5  ADMISSIBILITY_BASIS_INVALID
A10 AUTHORITY_BASIS_REVOKED          A13 ADMISSIBILITY_BASIS_REVOKED
```

`A6 AUTHORITY_BASIS_AMBIGUOUS_COMPETING` is retained for competing **authority**
bases only; no admissibility-conflict code is added, and no
admissibility-conflict case is claimed.

Corrected deterministic procedure — ordered, first match wins, no other route:

```
 1  recomputed artifact digest ≠ bound digest                      → DENY  A8
 2  no currentness_resolution_digest + epoch bound in the request   → DENY  A9
 3  no authority basis resolvable for (principal, scope)            → DENY  A11
 4  authority basis malformed, or stored record_digest not reproducible → DENY  A12
 5  authority basis REVOKED, or outside its validity interval       → DENY  A10
 6  ≥2 operative authority bases conflict, no frozen precedence     → DENY  A6
 7  principal not bound to scope                                    → DENY  A2
 8  requested_use ∉ permitted_requested_use                         → DENY  A3
 9  no admissibility basis resolvable                               → DENY  A4
10  admissibility basis malformed / digest not reproducible         → DENY  A5
11  admissibility basis REVOKED, or outside its validity interval   → DENY  A13
12  escalation predicate of the frozen profile satisfied            → ESCALATE A7
13  otherwise                                                       → PROCEED  A1
```

```
authority codes  A1–A13   13
propagation      P1–P12   12
reliance         I1–I11   11
new_reason_code_count     36
reused unchanged          21   (R1–R11, G1–G10)
```

## 4. Issuance authorization and attempt digests — frozen, with ordering

Neither is a canonical object digest. Both are persisted-file identities:

```
issuance_authorization_digest = sha256(exact persisted bytes of the authorization file)
attempt_record_digest         = sha256(exact persisted bytes of the attempt record file)
```

Write ordering, which removes any identity cycle:

```
1  authorization file finalized and persisted        → digest exists
2  attempt record written binding that digest, then FROZEN  → digest exists
3  RelianceIssuanceRecord written only after step 2, binding both
```

The attempt record never needs the reliance record's digest. A reliance record
written before its attempt record was frozen is invalid by construction.

## 5. Test universe — recomputed

v0.2's 37 cases stand. Added, one per genuinely new semantic branch that would
otherwise never be exercised:

```
T-CASE-Q   authority basis missing                   → A11, no propagation
T-CASE-R   authority basis invalid (digest not reproducible) → A12, no propagation
T-CASE-S   admissibility basis revoked               → A13, no propagation
T-DIG-08   synthetic_profile_digest class, both vectors reproduce
```

```
test_count = 37 + 3 + 1 = 41
```

**Declared coverage gap, recorded rather than hidden.** Codes `A2` (principal not
bound to scope), `A3` (requested use outside scope), `A4` (admissibility basis
missing), `A5` (admissibility basis invalid) and `A7` (escalation) have **no
dedicated result case** in this universe. `A7` is partially reached through
`T-CASE-B` (authority ESCALATE), but `A2`, `A3`, `A4` and `A5` are unexercised
branches of a closed set. They are not padded into the count to look complete;
they are named here so that a later report cannot claim the authority procedure
was exercised end to end. Closing them is a separate, larger test-coverage
decision and is not taken as part of a narrow revision.

## 6. Everything else — unchanged from v0.2

The as-of epoch definition and its three computed vectors; completeness
attestation participating in the epoch; `R-EPOCH-1` applicability and `R-EPOCH-2`
mandatory re-resolution; three distinct principals with
`producer_principal ≠ reliance_consumer_principal`; the closed envelope binding
subject, producer and intended consumer separately; the fifteen consumer checks
including reliance-time authority re-evaluation; the reliance record binding both
authority moments and the re-resolved currentness; single-use issuance with an
attempt ledger; historical reliance preservation and its declared
recorded-≠-propagated boundary; the evidence artifacts; and the claim ceiling with
its six assurance-qualified maxima and three design-specific limits.

## 7. Return

```
INTEGRATION_SLICE_SEMANTIC_DESIGN = READY_FOR_OWNER_REVIEW_v0.3

basis_record_digest_excludes_record_digest             TRUE
basis_authority_vector_present                         TRUE   BASIS-AUTH-1  7ad84cfb…
basis_admissibility_vector_present                     TRUE   BASIS-ADM-1   bf29f3d7…
synthetic_profile_digest_defined                       TRUE   Class 8
producer_profile_vector_present                        TRUE   1c7ac979…
consumer_profile_vector_present                        TRUE   889ab97b…
authority_missing_has_authority_specific_code          TRUE   A11
authority_invalid_has_authority_specific_code          TRUE   A12
admissibility_revoked_has_admissibility_specific_code  TRUE   A13
issuance_authorization_digest_rule_frozen              TRUE   persisted-file bytes
attempt_record_digest_rule_frozen                      TRUE   persisted-file bytes

test_count              41
new_reason_code_count   36   (A 13 · P 12 · I 11)
new_digest_class_count   8
source_modified         FALSE
result_bearing_execution NONE
```
