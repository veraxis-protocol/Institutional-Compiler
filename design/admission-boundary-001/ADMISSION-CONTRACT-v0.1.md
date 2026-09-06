# Admission Contract v0.1

## Normative design statement

The admission boundary consumes one frozen Candidate Normative Unit containing
`unit_id`, literal `candidate_span`, provisional `unit_type`, `source_anchors`,
`interpretation_state`, and `epistemic_state`. It returns one immutable admission
receipt. It does not modify the candidate.

Admission means **eligible for Institutional IR interpretation**. It is neither a
finding that the candidate is correctly interpreted nor permission to execute any
action.

## Seam ownership

| Responsibility | Owner | May not do |
| --- | --- | --- |
| Define admission policy, delegate admission warrants, and resolve conflicts | Institutional Admission Authority | Delegate authority to a model merely because it extracted a candidate |
| Register source identities, versions, digests, standing, scope, and lifecycle evidence | Institution-controlled Authority Registry and evidence custodian | Infer authority from wording, popularity, or provenance alone |
| Evaluate frozen rules and emit deterministic receipts | Future Admission Boundary Evaluator | Invent, extend, or repair evidence; resolve discretionary conflicts |
| Propose `candidate_span` and provisional `unit_type` | Candidate-discovery model | Issue authority evidence, approve admission, select an overriding warrant, or write admitted institutional meaning |
| Interpret an admitted proposition | Future Institutional IR construction stage | Treat admission as canonical meaning or runtime authorization |

Automatic evaluation may yield `ADMITTED` only when the registry supplies an
active, unambiguous, machine-verifiable `admission_warrant` whose delegation covers
the exact source identity, version, digest, scope, and evaluation time. A human or
institutional governance act is required to create or broaden a warrant, resolve
overlapping or contradictory authority, override a fail-closed result, or decide a
case whose evidence is not machine-verifiable. Any such act becomes new authority
evidence; it is not an evaluator exception.

## Minimum sufficient authority-evidence model

The draft `AUTHORITY-EVIDENCE-v0.1.schema.json` requires only fields necessary to
answer a frozen admission question:

* `evidence_id`, `evidence_digest`, and `issued_at` identify and bind the evidence
  projection used by the receipt.
* `source_id`, `source_version`, and `source_digest` bind evidence to the exact
  registered source instance rather than similar text.
* `issuer_id` and `authority_basis_ref` identify who asserts standing and the
  institution-controlled basis for that assertion.
* `jurisdiction`, `applicability_scope`, and `source_standing` describe the warrant's
  bounded reach without interpreting the candidate's semantics.
* `adopted_at`, `effective_from`, and optional `effective_until`, `superseded_at`,
  and `revoked_at` make lifecycle status evaluable at an explicit time. Publication
  time is deliberately not a substitute for effectiveness.
* `admission_warrant` identifies the Admission Authority's delegation, its exact
  source binding, scope, validity interval, and status.

Cryptographic signature mechanics and a global authority-ranking ontology are not
silently invented here. `evidence_digest` is a content-integrity binding, not proof
that the issuer was entitled to issue the evidence. Issuer authentication and
authority-basis verification are prerequisites supplied by the institution's
trusted registry. The design fails closed if either is unavailable or disputed.

Provenance and authority remain different: **provenance answers where this came
from; authority answers why the institution is entitled to treat it as operative
meaning.** A perfect provenance chain is not an authority warrant.

## Authority conservation

> A candidate cannot acquire greater institutional standing through extraction or
> admission than is established by its supporting authority evidence.

Consequently, authority never arises from model output, candidate type, semantic
similarity, repeated extraction, source popularity, or provenance alone. The
evaluator cannot strengthen `source_standing`, expand scope, extend effective time,
or prefer one authority based on its language.

## Deterministic input and receipt projection

An admission evaluation input consists of:

1. the immutable Candidate Normative Unit projection;
2. registered source metadata for its anchored source instance;
3. zero or more canonical authority-evidence projections;
4. explicit `evaluation_time` in UTC;
5. requested `evaluation_scope`;
6. evaluator identifier/version and admission-ruleset identifier/digest.

Objects are canonicalized as UTF-8 JSON using lexicographically sorted object keys,
no insignificant whitespace, and array order as recorded. Timestamps are normalized
to RFC 3339 UTC with `Z`. The input digest is SHA-256 over that full canonical input.
The evidence digest is SHA-256 over the ordered canonical evidence array.

The receipt projection contains exactly the fields required by
`ADMISSION-RECEIPT-v0.1.schema.json`. `admission_receipt_id` is
`admrec-sha256:<hex>`, where `<hex>` is SHA-256 over the canonical receipt projection
with `admission_receipt_id` omitted. The explicit `evaluation_time` therefore enters
both input and receipt identity. No hidden wall clock, retrieval time, random value,
or model output may affect the result.

Identical canonical inputs under the same evaluator version, ruleset digest, and
evaluation time must yield the identical state, reason code, digests, and receipt
identifier. Re-evaluation at a later time creates a new receipt. An earlier receipt
is never mutated when later revocation or supersession evidence arrives.

## Successor interface

Only `ADMITTED` may cross into Institutional IR construction. The minimum successor
bundle is:

* the unchanged admitted Candidate Normative Unit;
* the admission receipt or immutable receipt reference;
* the candidate's source anchors; and
* the authority-evidence references and digests necessary for reconstruction.

No other admission state is a denial of the underlying proposition. It means only
that eligibility for interpretation was not established for this evaluation.
Institutional IR will represent canonical institutional meaning. A later OCE/runtime
stage may compute consequences; OAM/ZTL may constrain operational authority; and
VEIP may record or verify execution consequences. None is designed or implemented
here.

## Claim ceiling

This contract is preregistered design evidence. It does not establish legal
validity, universal authority semantics, production readiness, runtime safety,
compliance, successful IR compilation, execution authorization, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
