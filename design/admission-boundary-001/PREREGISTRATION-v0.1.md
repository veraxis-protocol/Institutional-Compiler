# Admission Boundary 001 Preregistration

## Frozen hypothesis

A deterministic admission seam can preserve the frozen source-grounded candidate,
require explicit institution-controlled authority and an admission warrant, and
emit reconstructable fail-closed eligibility evidence without conferring authority
through extraction or implementing semantic interpretation or runtime authorization.

The frozen vector corpus tests this hypothesis at the design-contract level only.
No live model, admission runtime, Institutional IR compiler, or execution system is
part of the test method.

## Method frozen before implementation

Each vector records candidate input, source metadata, authority evidence,
`evaluation_time`, expected state (or deliberately bounded acceptable set), reason
code, falsifier, and claim ceiling. Design-level contract tests verify corpus byte
identity, schema validity, complete threat coverage, state/reason vocabulary, and
unchanged candidate/production trees. They do not execute a future evaluator.

When implementation is separately authorized, it must be evaluated against this
unchanged corpus. Any test-vector correction requires a successor corpus and an
explicit record; silently editing expected results after seeing implementation
behavior would invalidate the preregistration.

## Falsification questions

1. **Extraction cannot confer authority.** Falsified if any vector becomes
   `ADMITTED` solely because model confidence, `candidate_span`, provisional
   `unit_type`, institutional wording, or repeated extraction asserts authority.
2. **Provenance alone cannot confer authority.** Falsified if complete source
   anchors and matching bytes are sufficient without a registered authority basis
   and exact admission warrant.
3. **Admission cannot exceed supporting warrants.** Falsified if admission succeeds
   outside source identity/version/digest, jurisdiction, applicability scope, or
   effective interval established by evidence.
4. **Missing institutional authority fails closed.** Falsified if absent,
   unavailable, stale, ambiguous, unauthenticated, or conflicting evidence produces
   `ADMITTED`.
5. **Admission is reconstructable.** Falsified if a receipt cannot establish the
   candidate, source instance, evidence references/digests, rules, evaluator,
   explicit time, scope, state, and reason used.
6. **Admission is temporally explicit.** Falsified if hidden wall-clock time,
   retrieval time, publication alone, or an unspecified version-as-of can change an
   outcome.
7. **Admission remains separate from runtime outcomes.** Falsified if this package
   creates a runtime permission state, treats `ADMITTED` as execution authorization,
   or implements OCE/OAM/ZTL/VEIP consequences.
8. **A model cannot self-admit.** Falsified if a model can issue or expand a warrant,
   resolve a conflict, select an authority rank, or write `ADMITTED`.

## Acceptance criteria for future implementation

* All frozen vectors produce their exact expected state/reason or declared
  acceptable state set without mutation of vector bytes.
* Repeated identical canonical inputs produce identical receipt projections.
* Time changes only through explicit `evaluation_time`; later lifecycle evidence
  creates a new receipt while preserving prior receipts.
* Positive admission requires at least one exact registry-authenticated authority
  evidence reference and warrant.
* No candidate field or model output appears in the authority derivation path except
  as the identity of the material being evaluated.
* Only `ADMITTED` can be handed to the successor IR interface, and that interface
  also receives receipt and authority reconstruction references.

## Known limitations and unresolved questions

The institution must still authorize issuer authentication, freshness bounds,
authority hierarchy/precedence, conflict-resolution governance, jurisdiction and
scope vocabularies, signature format, evidence storage, and privacy/retention rules.
This package deliberately does not choose them. Universal authority semantics
cannot be inferred from this corpus.

## Claim ceiling

Every vector is bounded to admission-design contract behavior. Passing the corpus
would not establish legal validity, universal authority semantics, production
readiness, runtime safety, compliance, successful IR compilation, execution
authorization, or independent validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO ADMISSION RUNTIME WAS IMPLEMENTED.**

**NO INSTITUTIONAL IR WAS IMPLEMENTED.**
