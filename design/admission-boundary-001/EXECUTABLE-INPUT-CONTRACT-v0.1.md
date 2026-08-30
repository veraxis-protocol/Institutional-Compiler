# Admission Executable Input Contract v0.1

Status: **OWNER-AUTHORIZED ADMISSION DESIGN-TO-EXECUTABLE CONTRACT CLOSURE — NO
RUNTIME IMPLEMENTATION**

## Confirmed gap and versioning decision

`TEST-VECTORS-v0.1.json` is a historical scenario corpus. Its compact
`authority_evidence` objects are not valid against
`AUTHORITY-EVIDENCE-v0.1.schema.json`, and its candidate/source objects are not exact
future evaluator inputs. That mismatch is confirmed. The historical corpus and its
freeze remain byte-identical; v0.2 is the explicit executable successor.

`AUTHORITY-EVIDENCE-v0.1.schema.json` is sufficient as the executable evidence
object and remains byte-identical. Its required fields are not loosened. The new
`ADMISSION-INPUT-v0.1.schema.json` composes complete candidate, source-registration,
registry-observation, authority-evidence, time, scope, evaluator, and ruleset inputs.

## Exact accepted bytes

A future Admission Runtime 001 evaluator may accept only UTF-8 bytes that:

1. decode as exactly one JSON object with no duplicate object keys;
2. validate against `ADMISSION-INPUT-v0.1.schema.json` and the frozen referenced
   authority-evidence schema;
3. contain timestamps already normalized as RFC 3339 UTC with `Z`; and
4. are byte-identical to the canonical JSON serialization defined below.

Thus insignificant whitespace and alternative key order are rejected at the exact
byte seam rather than silently normalized. Corpus v0.2 stores parsed executable
objects; the accepted standalone bytes for each are its canonical serialization.

The input contains no input digest, receipt identifier, result state, reason code,
receipt aggregate, hidden clock, model confidence, Institutional IR, or runtime
permission field. Those that belong in a receipt are computed after input acceptance.

## Canonical JSON v0.1

`OIC-ADMISSION-CANONICAL-JSON-v0.1` is:

* UTF-8 without a byte-order mark;
* JSON object keys sorted lexicographically by Unicode code point;
* `,` and `:` separators with no insignificant whitespace;
* exact JSON types preserved; no string-to-number/boolean coercion;
* no duplicate keys, NaN, positive/negative infinity, or non-JSON values;
* strings serialized with JSON escaping and without ASCII-only escaping;
* arrays preserve recorded order except `authority_evidence`; and
* all timestamp fields must already be normalized RFC 3339 UTC `Z` values before
  serialization. Canonicalization never reads a clock.

## Evidence ordering

Evidence order has no authority or outcome meaning. Before an executable input is
frozen, its `authority_evidence` array is ordered ascending by the stable tuple
`(evidence_id, evidence_digest)`. Duplicate `evidence_id` values are invalid. The
canonical input, receipt evidence references, receipt evidence digests, and aggregate
evidence digest all use that explicit order. No other array is reordered.

The v0.2 corpus already records evidence in canonical order. A future evaluator does
not silently sort accepted bytes: noncanonical input bytes fail the byte-seam rule.

## Digest projections

Every digest uses lowercase SHA-256 and the `sha256:<64 lowercase hex>` form.

* **Authority `evidence_digest`:** hash Canonical JSON v0.1 of the complete authority
  evidence object with only its top-level `evidence_digest` field omitted. It is not
  a signature and is not computed over itself.
* **Candidate projection digest:** hash canonical JSON of the exact `candidate`
  object in the accepted input.
* **Ruleset digest:** hash canonical JSON of the complete parsed
  `STATE-INPUT-MAPPING-v0.1.json`. The frozen value is
  `sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c`.
* **Input digest:** hash canonical JSON of the entire accepted executable input. The
  input contains no `input_digest`, so the projection is non-self-referential.
* **Receipt aggregate `evidence_digest`:** hash canonical JSON of the ordered array of
  complete authority-evidence objects, including their already-verified individual
  `evidence_digest` values. The receipt aggregate field is outside that array.
* **Admission receipt ID:** hash canonical JSON of the full receipt with only
  `admission_receipt_id` omitted, prefixed `admrec-sha256:`.

`source_registration.source_digest` and warrant/source digests bind source content;
they are supplied source-content claims, not hashes of the source-registration JSON.
The complete source-registration projection is nevertheless bound by `input_digest`.

## Candidate input boundary

The candidate object is an untrusted serialized Candidate Normative Unit projection.
It uses the candidate schema's field names and state values. The executable input
schema deliberately permits an empty `source_anchors` array so the frozen
`CANDIDATE_INPUT_INVALID` terminal state is reachable without making the enclosing
JSON structurally invalid. This does not weaken the frozen candidate schema or alter
candidate extraction; the future admission evaluator must reject the invalid
candidate reference at precedence 1.

`unit_type` is provisional model output and is excluded from every authority-evidence
projection. Changing it cannot create, remove, or expand a warrant.

## Source-registration contract

The inline source-registration object contains only facts consumed by the state
machine: exact source identity/version/content digest; registered status; explicit
registry availability/freshness observation; source standing; jurisdiction and
applicability scope; and adoption, publication, effectiveness, expiration,
supersession, and revocation markers.

It does not duplicate warrant identity, delegation, or warrant scope. Publication is
recorded separately from effectiveness and cannot trigger current effectiveness.

## Registry trust boundary

The future evaluator consumes the source-registration object only through the
institution-controlled authority-registry seam named by `registry_boundary_id`.
That seam is responsible for authenticating the observation before delivery. JSON
does not become trustworthy because it names the seam, and the evaluator does not
perform real-world PKI, issuer authentication, or institutional mandate validation.
It verifies only schema, exact values, digests, source bindings, scope, time, warrant
status, internal consistency, and frozen precedence.

Production issuer authentication, registry transport authentication, signature
format, key lifecycle, freshness duration, authority hierarchy, and conflict
resolution remain unresolved and require separate owner authorization.

## Materialization and no-default-authority rule

v0.2 is not produced by a runtime adapter. It is a frozen corpus whose complete
synthetic fixture facts are visible in each executable input and classified in the
machine-readable crosswalk.

Historical facts are copied or expanded deterministically. Where v0.1 did not state
required fixture facts—such as synthetic issuer/admission-authority identifiers,
evidence issuance/adoption timestamps, or delegation-basis identifiers—v0.2 states
them explicitly and the crosswalk marks them as additions of previously unspecified
design data. These identifiers are test-fixture facts only; they do not assert that a
real person or institution possesses authority.

An empty historical evidence array stays empty. No placeholder evidence or warrant is
created. Unavailable/stale observations and version/digest/scope/time mismatches stay
explicit input facts. Nothing is supplied by a default, environment variable, model,
network, registry implementation, or wall clock.

## Claim ceiling

This closure establishes design consistency and executable-input completeness only.
It does not establish production authority validation, issuer authentication, legal
authority, semantic correctness, runtime admission correctness, Institutional IR
correctness, execution authorization, or independent validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO ADMISSION RUNTIME WAS IMPLEMENTED.**

**NO INSTITUTIONAL IR WAS IMPLEMENTED.**
