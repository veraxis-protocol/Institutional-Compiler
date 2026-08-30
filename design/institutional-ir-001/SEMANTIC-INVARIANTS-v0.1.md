# Semantic Invariants v0.1

Frozen invariants for Institutional IR 001. Each is stated so that a violation is
observable in a canonical IR unit rather than only arguable in prose.

## I1 — No semantic invention

> Institutional IR may contain no semantic assertion whose support exceeds the admitted
> source material plus explicit institution-controlled interpretation evidence.

Operationally: every assertion whose `interpretation_status` is `ESTABLISHED` carries
`source_support` whose `quote` is literally contained in the admitted candidate span, and
an `interpretation_basis` that is not `NONE`. Every `AMBIGUOUS` alternative carries the
same support. Nothing else may appear.

Consequences, each with a corpus vector:

* a passive sentence with no named actor does not acquire one (IIR-015, IIR-029);
* a recipient does not become the actor (IIR-016);
* a document title does not become authority semantics — the IR unit has no slot in which
  document metadata could be written, and authority lives in the admission binding only;
* an implied business convention does not become a condition (IIR-032);
* advisory language does not become mandate (IIR-004, IIR-027);
* permission does not become obligation (IIR-003, IIR-028);
* a deadline does not disappear (IIR-014);
* a quantitative threshold is not broadened (IIR-012, IIR-031);
* an exception is not dropped (IIR-011, IIR-030);
* the absence of a further exception does not imply that none exists, unless
  `exception_closure` is `CLOSED_BY_WARRANT` backed by a `CLOSED_WORLD_ASSUMPTION`
  instrument (IIR-011).

## I2 — Semantic force conservation

Force is never strengthened without an institutional interpretation warrant. These
transitions are forbidden outright in the absence of one:

| From | To |
| --- | --- |
| `ADVISORY` | `OBLIGATION` |
| `ADVISORY` | `PROHIBITION` |
| `ADVISORY` | `CONSTITUTIVE_DEFINITION` |
| `PERMISSION` | `OBLIGATION` |
| `PERMISSION` | `PROHIBITION` |
| `PERMISSION` | `DELEGATION` |

And structurally:

* *may* does not become *must*;
* *eligible* does not become *entitled*;
* *review* does not become *approval*;
* *recipient* does not become *responsible actor*;
* *default* does not become *universal rule*;
* *conditional* does not become *unconditional*;
* *exception-bearing* does not become *exceptionless*;
* *not established* does not become *false*.

A model prediction is not the evidence that authorizes any of these. The proposal schema
has no field in which a proposer could assert one, and `FORCE_ASSIGNMENT` and
`ROLE_ASSIGNMENT` are permitted operations on institution-issued instruments only.

## I3 — Material content conservation

All materially operative source content survives into canonical IR, attached to the slot
it qualifies:

| Content | Where it lives | Vector |
| --- | --- | --- |
| thresholds, quantities | `quantum` value + `COMPARATOR` qualifier | IIR-012, IIR-031 |
| currencies | `quantum` + `CURRENCY` qualifier + normalization | IIR-013 |
| durations | `temporal_qualifier` + `DURATION` normalization | IIR-001 |
| deadlines | `temporal_qualifier` + `TIMESTAMP` normalization | IIR-014 |
| conditions | `condition` | IIR-010, IIR-009 |
| exceptions | `exception` + `exception_closure` | IIR-011, IIR-030 |
| recipients | `counterparty` | IIR-016, IIR-019 |
| scope qualifiers | `SCOPE_QUALIFIER` qualifier | IIR-023 |
| temporal triggers | `condition` or `temporal_qualifier` | IIR-009 |
| discretion markers | `DISCRETION` qualifier | IIR-019 |
| advisory wording | `HEDGE` qualifier | IIR-004, IIR-027 |
| explicit negation | `NEGATION` qualifier | IIR-002 |
| defined terms | `definiendum` / `definiens` | IIR-005, IIR-023, IIR-024 |
| references to other provisions | `unresolved_references` | IIR-025, IIR-026 |

## I4 — Ambiguity is preserved, not resolved by preference

An `AMBIGUOUS` assertion carries `value: null` and at least two enumerated `alternatives`,
each with its own source support. Selecting one of them is `ROLE_ASSIGNMENT` or
`FORCE_ASSIGNMENT` and requires a tier-W instrument (IIR-017, IIR-018, IIR-034). A model
choosing one interpretation resolves nothing.

## I5 — Unknown is not false

`NOT_ESTABLISHED` means the admitted source does not supply the slot. It is never a
finding that the slot is empty in the world, and never a licence for a compiler to
substitute a default (IIR-015, IIR-035).

`NOT_APPLICABLE` means the force does not raise the slot at all, so that a compiler is not
forced to fail closed on a question the norm never asked.

## I6 — Definitions stay source-bound and version-bound

A definition is bound to a source instance and version through the admission binding like
any other unit. A term is never resolved by ordinary-language meaning. An absent definiens
stays `NOT_ESTABLISHED` with the referenced document recorded (IIR-024). Resolving one
definition against another is `DEFINITION_RESOLUTION`, tier W.

## I7 — Unresolved references stay unresolved

A cross-reference is expanded only under `CROSS_REFERENCE_EXPANSION`, and only to a target
that names its own source id, version, digest and **admission receipt**. There is no
resolution status meaning "the interpreter read it". A reference is never silently dropped
(IIR-025, IIR-026).

## I8 — Every canonical assertion is reconstructable

Every `ESTABLISHED` assertion resolves to exact source bytes and to the authority that
made it interpretable. See `IR-LINEAGE-v0.1.md` for the minimum projection. No IR field is
provenance-free.

## I9 — Source-instance identity survives semantic normalization

Two units may share a `semantic_equivalence_key` and must not share an `ir_unit_id` when
they stand on different source instances or versions (IIR-021, IIR-033). Semantic
equivalence is observable; institutional instance identity is preserved.

## I10 — IR is not execution

No `ALLOW`, no `DENY`, no execution decision, no transaction result, no runtime permission
state. The schemas contain no field that could hold one, and every schema is
`additionalProperties: false`.

## I11 — Only ADMITTED material enters

A receipt in any non-`ADMITTED` state is an IR input-boundary failure, never an empty or
partial IR (IIR-036 … IIR-040).

## I12 — The proposer never owns the outcome

A proposal is `PROVISIONAL` and `uncertain` by construction, carries no confidence field,
and cannot reference interpretation evidence. Canonicalization reads the admitted source,
so a proposal that drops material does not erase it (IIR-030, IIR-031) and a proposal that
adds material does not create it (IIR-029, IIR-032).

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
