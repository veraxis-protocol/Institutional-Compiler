# CURRENTNESS SLICE 001 — DIGEST DERIVATION v0.1

```
author          Vitaliy Reznik (semantics)
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
purpose         no adjudicator shall have to reverse-engineer a serialization again
```

## 1. Canonical serialization — one rule, used by every digest class below

```
encoding              UTF-8
object key order      lexicographic by code point (sort_keys)
ensure_ascii          false          (non-ASCII characters emitted literally, not escaped)
indentation           none
item separator        ","            (no space)
key separator         ":"            (no space)
array order           preserved as given; never re-sorted
trailing newline      none in the hashed byte sequence
digest algorithm      SHA-256
digest form           lowercase hexadecimal, UNPREFIXED
normalization         none applied to values; no Unicode normalization, no whitespace
                      stripping, no number reformatting. Values are hashed as they
                      appear in the object.
null handling         null is a value and participates; it is not omitted
```

**Reference micro-vector** (verifies separators, ordering and `ensure_ascii=false`
in four bytes of payload):

```
input      {"b": 2, "a": "é"}
canonical  {"a":"é","b":2}
sha256     06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de
```

An implementation that produces `{"a":"é","b":2}` or inserts spaces will fail
this vector immediately.

## 2. Self-digest exclusion

Every record that carries its own digest excludes **only** that one field before
canonicalization, and excludes it by key removal, not by null substitution:

```
digest(record) = sha256(canonical(record without its own digest field))
```

| object class | self-digest field excluded |
|---|---|
| CurrentnessResolution | `resolution_digest` |
| UseGateDecision | `use_gate_decision_digest` |
| BasisCompletenessAttestation | `completeness_digest` |
| CurrentnessIndex | `index_digest` |
| AdversarialObservation | `observation_digest` |
| RawExecutionPackage | `package_digest` |

## 3. Per-class derivation

### 3.1 historical_artifact_digest

```
domain      the historical artifact BODY only — the deliverable content object
excluded    every wrapper field of the fixture or archive that carries it
            (fixture_class, claim_ceiling, times, index_admission_path, …)
rule        sha256(canonical(body))
```

Rationale for the narrow domain: the digest must be stable against the wrapper the
artifact happens to be transported in, and must change if and only if the
deliverable content changes. This is the digest that carries the slice's headline
claim of byte preservation, so it may not drift with packaging.

**Test vector** — the frozen synthetic control's
`historical_artifact.body`:

```
canonical bytes  341
sha256           6f9fe1ccbabd6195d474f09a365a5ca4cc32f7ed8cf1f41e8acddd22e592eed0
```

### 3.2 basis_record_digest

```
domain      one governing record exactly as stored in the index
excluded    nothing; records carry no self-digest
rule        sha256(canonical(record))
```

### 3.3 completeness_digest — BasisCompletenessAttestation

```
domain      the attestation object
excluded    completeness_digest
ordering    basis_snapshot_refs and basis_snapshot_digests are POSITIONALLY PAIRED
            and must not be sorted independently; refs[i] corresponds to digests[i]
rule        sha256(canonical(attestation minus completeness_digest))
```

**Test vector** — the frozen synthetic control's
`basis_completeness_attestation`:

```
canonical bytes  617
sha256           a9ffff71467a0880f77e3fec8b4740a0cdb74953e8fb9d743b1fdd7617ce66c6
```

### 3.4 currentness_index_digest

```
domain      { scope_ref, entries[], attestations[], admitted_at }
entries     each entry reduced to {output_ref, record_ref, record_digest, record_class,
            effective_at, admitted_at} — the full record bodies are NOT re-embedded
ordering    entries sorted by (output_ref, record_ref) before digesting, so index
            identity is independent of insertion order
excluded    index_digest
rule        sha256(canonical(reduced index minus index_digest))
```

### 3.5 resolution_digest — CurrentnessResolution

```
domain      the whole resolution record
excluded    resolution_digest
included    times.evaluated_at and times.expires_at ARE included — a resolution
            computed at a different instant is a different resolution
rule        sha256(canonical(resolution minus resolution_digest))
```

### 3.6 use_gate_decision_digest — UseGateDecision

```
domain      the whole decision record, including the resolution_digest it bound and
            the artifact_observed_digest it verified
excluded    use_gate_decision_digest
rule        sha256(canonical(decision minus use_gate_decision_digest))
```

### 3.7 observation_digest — AdversarialObservation

```
domain      {case_id, mutation_applied, expected_reason_code, observed_reason_code,
            observed_state, subject_refs, evaluated_at}
excluded    observation_digest
rule        sha256(canonical(observation minus observation_digest))
```

### 3.8 package_digest — RawExecutionPackage

```
domain      the whole package record
excluded    package_digest
members     member identities are included as {path, bytes, sha256}; member BODIES
            are not embedded
rule        sha256(canonical(package minus package_digest))
```

### 3.9 persisted-file SHA-256

Distinct from every digest above and never conflated with them:

```
rule        sha256 over the exact bytes of the persisted file, including any
            trailing newline the file actually has
```

**Test vector** — the frozen synthetic control file as persisted:

```
bytes    2275
sha256   2a9158e0561d3ab1886f3f4f52c0b828a76979aadccc66b58c95ccb84914a45d
```

Note the deliberate contrast between §3.9 and §1: the *hashed canonical form*
carries no trailing newline; the *persisted file* may. Both vectors above are
computed from the same artifact and differ, which is the point.

## 4. Prefix handling

All digests in this slice are recorded **unprefixed** (`6f9fe1cc…`, not
`sha256:6f9fe1cc…`). Where a record must interoperate with an existing object that
uses the `sha256:` prefix, the prefix is a presentation concern of that record and
is stripped before any comparison. A comparison that fails because one side
carried a prefix is an implementation defect, not a mismatch.

## 5. Freeze

This document is frozen before implementation. Any digest class introduced later
requires a versioned successor to this document, published before the execution
that produces it. No digest class may be introduced during implementation without
one.
