# Institutional IR Contract v0.1

Status: **OWNER-AUTHORIZED INSTITUTIONAL IR ARCHITECTURE DESIGN AND PREREGISTRATION — NO
IR IMPLEMENTATION**

## The question this contract answers

> What must be true before an admitted source proposition may become a canonical
> computable institutional semantic object?

Admission answered a different question. It established that the institution *may*
interpret this source. It did not establish the interpretation, and nothing in this
contract lets an `ADMITTED` receipt stand in for one.

## Precise definition

An **Institutional IR unit** is one canonical institutional semantic object derived from
exactly one `ADMITTED` candidate normative unit, in which every semantic assertion is
either supported by the admitted source material under an explicit institution-controlled
interpretation basis, or explicitly marked as not established.

It is not a summary, not a paraphrase, not a model's reading, and not a permission.

## The five acts, kept apart

| # | Act | Question | Owner | Output |
| --- | --- | --- | --- | --- |
| 1 | Source grounding | What literal source material was extracted? | Candidate layer (frozen) | Candidate Normative Unit |
| 2 | Admission | Is this source-grounded candidate institutionally eligible for interpretation? | Admission Runtime 001 (frozen) | `AdmissionReceipt` |
| 3 | Interpretation proposal | What semantic structure *might* this admitted proposition express? | Proposer — may be a model | `InterpretationProposal`, `PROVISIONAL` |
| 4 | Institutional interpretation / canonicalization | Which proposed assertions are sufficiently supported and institutionally recognized to become canonical meaning? | Institutional interpretation authority | interpretation decision + evidence |
| 5 | Institutional IR | What exact canonical semantic object may downstream compilation consume? | — | `InstitutionalIRUnit` |

Acts 3, 4 and 5 are three artifacts with three schemas, not three phases of one call.
Collapsing them is the specific failure this design exists to prevent: at the candidate
layer we already observed that a model's semantic decomposition can look complete while
assigning an unsupported actor, losing a condition, losing a target, or dropping a
material qualifier. Repeating that pattern one authority layer higher would let the same
plausible-looking output become *canonical institutional meaning*.

**Act 4 is not filtering of act 3.** Canonicalization reads the admitted source, not only
the proposal. A slot the proposer omitted can still be canonical if the admitted source
plainly supplies it under a permitted basis, and a slot the proposer supplied is canonical
only if the admitted source supports it. That is why a dropped exception (IIR-030) and a
dropped threshold (IIR-031) survive into canonical IR, while an invented actor (IIR-029)
and an invented condition (IIR-032) do not.

## Successor input

Only an `AdmissionReceipt` whose `admission_state` is `ADMITTED` may cross this seam. The
IR unit binds, at minimum:

* the unchanged Candidate Normative Unit and its source anchors;
* the exact admission receipt — its identifier, candidate projection digest, source
  identity/version/digest, authority-evidence references and digests, evaluation time,
  evaluation scope, admission ruleset id/digest, and evaluator id/version;
* the interpretation ruleset id and digest;
* the interpretation evidence backing every established assertion.

A non-`ADMITTED` receipt is an **IR input-boundary failure**. It is not an empty IR, not a
partial IR, and not an IR with everything `NOT_ESTABLISHED`. Vectors IIR-036 through
IIR-040 carry real receipts in `MISSING_AUTHORITY_EVIDENCE`, `OUT_OF_SCOPE`, `REVOKED`,
`CONFLICTING_AUTHORITY` and `ADMISSION_NOT_ESTABLISHED` respectively, and each expects
`IR_INPUT_NOT_ADMITTED` with no canonical unit at all.

## The minimum semantic vocabulary

Eleven slots, every one of them justified in `INTERPRETATION-RULESET-v0.1.json` and every
one of them present in every unit. The candidate dimensions that were considered and
deliberately **excluded or folded** are recorded there too, with reasons: scope,
consequence/remedy, evidence duty, review duty, trigger, delegation source/recipient,
discretion, advisory force, and cross-reference.

| Slot | Why a compiler cannot do without it |
| --- | --- |
| `normative_force` | Identical wording produces different consequences as obligation, prohibition, permission, definition, delegation or advice. It is the head of the unit. |
| `bearer` | Who is bound, permitted or empowered. Frequently absent in real text, so it must be able to be unknown without invalidating the unit. |
| `action` | The predicate the force applies to. |
| `object` | What the action reaches. "Approve the request" and "approve the budget" are different norms. |
| `counterparty` | The recipient or target, structurally separate from the bearer, because collapsing them is an observed failure. |
| `condition` | What must hold for the norm to apply. Dropping it makes a conditional norm unconditional. |
| `exception` | What is carved out. Separate from condition because it defeats rather than gates, and negates differently downstream. |
| `temporal_qualifier` | Deadlines, durations, effective moments, temporal triggers. |
| `quantum` | Thresholds, quantities, currency amounts and comparators. |
| `definiendum` | The term a constitutive definition defines. |
| `definiens` | The institutional meaning assigned to it. |

Every unit carries exactly eleven assertions. A slot the source does not supply is present
with status `NOT_ESTABLISHED`; a slot the force does not raise is present with
`NOT_APPLICABLE`. Neither is ever omitted, so a compiler can never mistake a slot nobody
looked at for a slot that was examined and found empty.

## The semantic assertion

Interpretation is a set of individually evidenced assertions, not one opaque object:

```
assertion = slot
          + interpretation_status
          + value (or enumerated alternatives)
          + source support (anchor, quote, content hash)
          + interpretation basis
          + interpretation evidence references
          + material qualifiers
          + normalization (only under a conservative basis)
```

This is what lets a unit say *actor established, condition established, target not
established, exception ambiguous* instead of producing a complete-looking record. Missing
semantic knowledge stays missing.

## Interpretation authority

Four tiers. Not every field needs human approval; not every field can be automated.

| Tier | Basis | Instrument required | Covers |
| --- | --- | --- | --- |
| D | `DETERMINISTIC_NORMALIZATION` | none | conservative, verifiable, syntax-preserving transformation of material already in the admitted source |
| S | `REGISTERED_INTERPRETATION_RULE` | a standing institution-registered machine-verifiable rule | a verbatim contiguous span with exactly one syntactic attachment |
| W | `INSTITUTIONAL_INTERPRETATION_WARRANT` | a specific institutional interpretation act | every reading the source's own structure does not force |
| P | `NONE` | — | proposals; permitted only on `AMBIGUOUS`, `NOT_ESTABLISHED` and `NOT_APPLICABLE` assertions |

**Is a distinct interpretation warrant necessary? Yes — but not for every field.** Tier D
needs none. Tier S needs a registered rule, which is a weaker and machine-verifiable
instrument, not a per-assertion act. Tier W needs a warrant, and these operations are
tier W without exception: `ROLE_ASSIGNMENT`, `FORCE_ASSIGNMENT`, `DEFINITION_RESOLUTION`,
`CROSS_REFERENCE_EXPANSION`, `AGGREGATION`, `CLOSED_WORLD_ASSUMPTION`,
`CANONICAL_EQUIVALENCE`.

A model can hold none of these instruments. `INTERPRETATION-EVIDENCE-v0.1.schema.json`
requires an `interpretation_authority_id` and an institution-controlled `basis_ref`, and
there is no path by which proposer output becomes evidence.

## Normalization, kept apart from interpretation

Conservative normalization is a transformation of material **already written in the
source**: canonical RFC 3339 UTC timestamps, canonical decimals, ISO 4217 currency codes,
ISO 8601 durations, exact source-span references, stable identifier ordering. Each
normalization records its `raw_source_text` beside its `normalized_value`, so it is
checkable rather than trusted.

Normalization may never add an actor, resolve an ambiguity, infer a missing condition,
broaden scope, change modality, infer authority, or infer a definition from general
knowledge. IIR-009 is the boundary case: "within two business days" is *not* normalized,
because "business day" is an institutional term whose meaning depends on a definition the
unit does not carry.

## Definitions

A constitutive definition is a force, with `definiendum` and `definiens` as its own slots
so each carries independent source support and status. A term is never resolved by
ordinary-language or dictionary meaning. Where the definiens lives in another document
(IIR-024), `definiens` is `NOT_ESTABLISHED` and the document appears in
`unresolved_references` — the definition is incomplete and says so. Local scope markers
("For the purposes of this policy") are preserved as a condition on the definition
(IIR-023), because a definition with its scope stripped is a different definition.

Document-level, institution-wide, imported, versioned, superseded and conflicting
definitions are all expressed through the same machinery: a definition unit is bound to a
source instance and a version like any other unit, so two definitions of one term from
different instances are two units, and a conflict between them is visible rather than
resolved. Resolving one against another is `DEFINITION_RESOLUTION` — tier W.

## Cross-references

A cross-reference is a relation, not a slot. It stays in `unresolved_references` with
`resolution_status: UNRESOLVED` unless an interpretation instrument carrying
`CROSS_REFERENCE_EXPANSION` supplies a `resolved_target` that identifies the referenced
source, its version and digest, and *its own admission receipt*. There is no status value
meaning "resolved by the interpreter's own reading". A reference is never dropped either:
losing "except as provided in Policy B" would silently remove an exception.

## Composition

v0.1 canonicalizes **one proposition at a time**. Cross-provision and cross-document
composition is deliberately out of scope: the corpus contains no aggregate unit, and
`AGGREGATION` is a tier-W operation that no vector exercises. What v0.1 provides for later
composition is the minimum that makes it possible without redesign — a stable
content-derived unit identity, explicit unresolved references that name their targets, and
`supersedes_ir_unit_id`. Premature global graph semantics would have to be guessed now and
lived with later.

## Identity

`ir_unit_id` is `iir-sha256:<hex>` over the canonical JSON of the complete unit with only
`ir_unit_id` omitted. It therefore binds the semantic projection, the admission receipt,
the source instance, the interpretation ruleset digest, and the interpretation evidence
references. No random UUID, no wall clock.

`semantic_equivalence_key` is a **separate** digest over the semantic projection alone —
statuses, values, alternatives, qualifiers, normalized values, exception closure and
reference texts — with no admission or source-instance binding.

The two together give the property the work order asks for. In IIR-021 the same
proposition at two source versions, and in IIR-033 the same wording from two different
authoritative source instances, each produce **two distinct `ir_unit_id` values and one
shared `semantic_equivalence_key`**: their similarity is observable, and they do not
collapse into one institutional instance. In IIR-034 the same proposition under a
different interpretation instrument produces two distinct ids *and* two distinct keys,
because the canonical meaning genuinely changed.

## Temporality

An IR unit built from a receipt evaluated at time *T* is not timeless truth. Every unit
binds the source version, the admission `evaluation_time`, the admission ruleset digest,
its own explicit `interpretation_time`, the interpretation ruleset digest, and the
interpretation evidence whose lifecycle it depends on. No interpreter clock is consulted,
exactly as in admission.

Later evidence never mutates a unit. It produces a **successor** unit that names its
predecessor in `supersedes_ir_unit_id` (IIR-022). Where later evidence makes the source no
longer admissible, there is no successor unit at all — the admission boundary refuses, and
the predecessor stands as immutable evidence of what was established at its own time.

## What IR does not contain

No `ALLOW`. No `DENY`. No execution decision, transaction result, or runtime permission
state. The schemas have no field in which one could be written. Institutional IR states
canonical meaning; computing consequences is a later stage that is not designed here.

## Minimum downstream compiler interface

A future compiler consuming canonical IR must never need to re-read natural language to
discover hidden semantics. What IR therefore makes explicit:

1. `normative_force`, as a closed vocabulary, with its own status and basis.
2. Every one of the eleven slots, always present, each with an explicit status — so the
   compiler can refuse on `AMBIGUOUS` or `NOT_ESTABLISHED` rather than guess.
3. Enumerated `alternatives` wherever a slot is ambiguous, so the compiler sees the
   competing readings rather than one arbitrary pick.
4. `material_qualifiers` attached to the slot they qualify, typed by kind.
5. `normalization` with both raw and normalized forms, so a compiler can compute on the
   normalized value and still audit it.
6. `exception_closure`, so the compiler knows whether the absence of a further exception
   is a finding or merely silence.
7. `unresolved_references`, so incompleteness is data rather than absence.
8. The complete admission binding and per-assertion source support, so any value is
   traceable without re-reading the document.

That is the whole interface. Consequence computation, conflict resolution across units,
and policy emission are not designed here, and no Rego is generated.

## Relation to the historical schema

`schemas/draft/institutional-ir.schema.json` remains byte-identical and untouched. It is
historical, generic and provisional: `ir_id`, `schema_version`, `nodes`, `edges`,
`admission_records`, optional `source_hashes`. This design does not overwrite it, does not
redefine its meaning, and **claims no migration between the two**. Whether a graph of
`InstitutionalIRUnit` objects can be expressed in that historical envelope is an open
question, deliberately left open.

## Claim ceiling

This contract is preregistered design evidence. It does not establish semantic
correctness, a universal institutional ontology, legal interpretation, production
interpretation authority, cross-model reliability, successful IR construction, OCE
compilation, runtime authorization, compliance, production readiness, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**
