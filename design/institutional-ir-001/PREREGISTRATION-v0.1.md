# Institutional IR 001 Preregistration

## Frozen hypothesis

An admitted, source-grounded institutional proposition can be turned into a canonical
computable semantic object without any model, extractor, parser or compiler manufacturing
institutional meaning — by separating the interpretation *proposal* from the institutional
*canonicalization decision*, evidencing every assertion individually against the admitted
source, and keeping unknown and ambiguous as first-class outcomes rather than gaps to be
filled.

## Method frozen before implementation

`TEST-VECTORS-v0.1.json` holds 40 vectors: 35 positive and 5 IR input-boundary. Every
vector's admission receipt is **real** — produced by running the frozen Admission Runtime
001 evaluator over the vector's own admission input through the public byte boundary — so
no expected outcome depends on a hand-written receipt. Every positive vector's receipt is
`ADMITTED`; each boundary vector carries a genuine receipt in `MISSING_AUTHORITY_EVIDENCE`,
`OUT_OF_SCOPE`, `REVOKED`, `CONFLICTING_AUTHORITY` or `ADMISSION_NOT_ESTABLISHED`.

`scripts/build_institutional_ir_corpus.py` is design tooling, not IR runtime. It is
committed so the corpus is reproducible, it imports nothing from an IR implementation
because none exists, and re-running it must reproduce the frozen bytes. It refuses to emit
any `ESTABLISHED` assertion, alternative, material qualifier, normalization source or
reference text that is not literally contained in the admitted candidate span.

Design-level contract tests verify corpus byte identity, schema validity, the admission
binding, lineage, invariants and threat coverage. **They do not execute a future IR
runtime**, because there is none.

Correcting a vector after seeing an implementation's behavior would invalidate this
preregistration. Any correction requires a successor corpus and an explicit record.

## Falsification questions

Each is falsified by an observable property of a canonical IR unit.

1. **Admission does not itself establish semantic interpretation.** Falsified if any IR
   unit's assertions can be derived from the admission receipt alone, or if an `ADMITTED`
   receipt is sufficient for an `ESTABLISHED` assertion with no interpretation basis.
2. **A model proposal does not establish canonical meaning.** Falsified if a proposal can
   carry confidence, evidence, authority or canonical status, or if canonical content
   tracks the proposal rather than the admitted source (IIR-029 … IIR-032).
3. **Unsupported semantic assertions cannot enter canonical IR.** Falsified if any
   `ESTABLISHED` value, alternative, qualifier or normalization source is absent from the
   admitted span.
4. **Semantic force cannot be strengthened without evidence.** Falsified if a forbidden
   force transition appears with `interpretation_basis` other than
   `INSTITUTIONAL_INTERPRETATION_WARRANT` (IIR-027, IIR-028).
5. **Material qualifiers cannot disappear.** Falsified if a threshold, currency, duration,
   deadline, condition, exception, recipient, scope qualifier, discretion marker, advisory
   hedge, negation or defined term present in a vector's source is absent from its unit.
6. **Ambiguity is preserved rather than guessed away.** Falsified if an `AMBIGUOUS`
   assertion carries a value, carries fewer than two alternatives, or becomes
   `ESTABLISHED` without a warrant (IIR-017, IIR-018, IIR-034).
7. **Definitions remain source and version bound.** Falsified if a definiens is supplied
   from outside the admitted source, or a definition unit loses its source instance
   binding (IIR-023, IIR-024).
8. **Unresolved references remain unresolved.** Falsified if a reference is dropped, or
   resolved without `CROSS_REFERENCE_EXPANSION` and a target carrying its own admission
   receipt (IIR-025, IIR-026).
9. **Every canonical assertion is reconstructable.** Falsified if any `ESTABLISHED`
   assertion lacks source support, or any non-`NONE` basis lacks evidence references.
10. **Source-instance identity survives semantic normalization.** Falsified if two units
    from different source instances or versions share an `ir_unit_id`, or if their semantic
    similarity stops being observable (IIR-021, IIR-033).
11. **IR remains separate from ALLOW/DENY.** Falsified if any schema admits a runtime
    permission state, execution decision or transaction result.
12. **Non-ADMITTED material cannot enter IR.** Falsified if any canonical unit stands on a
    non-`ADMITTED` receipt, or if a boundary refusal is recorded as an empty IR
    (IIR-036 … IIR-040).

## Acceptance criteria for a future implementation

* Every vector's admission receipt reproduces exactly through the frozen evaluator, with
  no vector bytes mutated.
* Every positive vector's canonical unit validates against
  `INSTITUTIONAL-IR-v0.1.schema.json` and matches the frozen expected unit.
* Every boundary vector produces an IR input-boundary failure and no unit.
* Identical inputs, ruleset and interpretation evidence produce identical `ir_unit_id`
  values; a change to any of them changes it.
* Interpretation time enters only through an explicit supplied value.
* No canonical assertion is established without a permitted basis and, where the basis is
  not deterministic normalization, an interpretation instrument.
* The implementation is provider-neutral: it names no model vendor, endpoint or family.

## Known limitations and unresolved questions

The institution must still authorize: who the interpretation authority is and how it is
authenticated; the registry of registered interpretation rules; the lifecycle and
revocation semantics of interpretation warrants; whether `AGGREGATION` across provisions
belongs in IR or in compilation; how conflicting definitions across source instances are
adjudicated; whether the historical generic IR envelope can carry these units; and what a
compiler is permitted to do with an `AMBIGUOUS` slot. None of these is chosen here.

The corpus is synthetic. Its expected units were authored by the same process that designed
the schemas; the build-time literal-support check is a real constraint but is not
independent validation.

## Claim ceiling

This package is preregistered design evidence. It does not establish semantic correctness,
a universal institutional ontology, legal interpretation, production interpretation
authority, cross-model reliability, successful IR construction, OCE compilation, runtime
authorization, compliance, production readiness, or independent validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**

**NO OCE OR REGO WAS IMPLEMENTED.**

**NO EXECUTION AUTHORIZATION WAS IMPLEMENTED.**

**NO MODEL CALL WAS MADE.**
