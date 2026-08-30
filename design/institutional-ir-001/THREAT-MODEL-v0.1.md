# Institutional IR 001 Threat Model v0.1

The threats are all versions of one failure: *plausible output becoming canonical
institutional meaning*. Each is listed with the structural feature that blocks it and the
corpus vector that would expose its absence.

## A. Invention

| Threat | Blocked by | Vector |
| --- | --- | --- |
| `invented_actor` — a bearer appears that the source never names | `ESTABLISHED` requires `source_support.quote` literally inside the admitted span | IIR-015, IIR-029 |
| `invented_condition` — an implied business convention becomes a condition | same | IIR-032 |
| `definition_invention` — an absent definiens is filled from general knowledge | `definiens` stays `NOT_ESTABLISHED`; the target is an unresolved reference | IIR-024 |
| `reference_expansion` — referenced content is inlined | `RESOLVED_BY_WARRANT` requires `CROSS_REFERENCE_EXPANSION` and a target with its own admission receipt | IIR-025, IIR-026 |

## B. Strengthening

| Threat | Blocked by | Vector |
| --- | --- | --- |
| `force_strengthening` — advisory or permission becomes obligation | forbidden force transitions; `FORCE_ASSIGNMENT` is tier W | IIR-027, IIR-028 |
| `review_becomes_approval` | force and action carry independent source support | IIR-008 |
| `recipient_becomes_actor` | `bearer` and `counterparty` are separate slots | IIR-016 |
| `closed_world` — absence of an exception read as exhaustiveness | `exception_closure` defaults `OPEN`; closing it needs `CLOSED_WORLD_ASSUMPTION` | IIR-011 |
| `unknown_as_false` — `NOT_ESTABLISHED` read as a negative finding | status vocabulary distinguishes unknown from inapplicable, and neither is false | IIR-015, IIR-035 |

## C. Loss

| Threat | Blocked by | Vector |
| --- | --- | --- |
| `exception_preservation` — an exception is dropped | canonicalization reads the admitted source, not only the proposal | IIR-011, IIR-030 |
| `threshold_preservation` — a threshold is dropped or broadened | `quantum` slot + `COMPARATOR` qualifier + raw/normalized pair | IIR-012, IIR-031 |
| `currency_preservation` — a currency is dropped or guessed | `CURRENCY` qualifier + explicit normalization | IIR-013 |
| `temporal_preservation` — a deadline or duration disappears or shifts | `temporal_qualifier` + raw/normalized pair | IIR-001, IIR-009, IIR-014 |
| `condition_preservation` | `condition` slot | IIR-010 |
| `qualifier_loss` — a discretion marker is dropped | `material_qualifiers` typed by kind | IIR-019 |
| `negation_preservation` | `NEGATION` qualifier | IIR-002 |
| `advisory_wording` | `HEDGE` qualifier | IIR-004, IIR-027 |
| `definition_scope_loss` — a local scope marker is stripped | scope kept as a condition on the definition | IIR-023 |
| `reference_loss` — a cross-reference vanishes | references are first-class array members | IIR-026 |
| `definition_source_loss` | definitions bound to a source instance through admission | IIR-005, IIR-023 |

## D. Identity and authority

| Threat | Blocked by | Vector |
| --- | --- | --- |
| `instance_collapse` — identical wording from two sources becomes one instance | `ir_unit_id` binds the admission receipt; equivalence lives in a separate key | IIR-033 |
| `version_collapse` — two source versions become one unit | same | IIR-021 |
| `warrant_independence` — canonical meaning unchanged by the instrument that authorized it | evidence refs are inside the identity projection | IIR-034 |
| `standing_leaks_into_meaning` — DRAFT standing alters semantics | source standing is an admission fact; no IR slot carries it | IIR-020 |
| `silent_mutation` — a historical unit is edited when evidence changes | successor units with `supersedes_ir_unit_id` | IIR-022 |
| `non_admitted_material` — meaning built on a fail-closed receipt | `admission_state` is `const: ADMITTED` | IIR-036 … IIR-040 |

## E. Ambiguity and structure

| Threat | Blocked by | Vector |
| --- | --- | --- |
| `ambiguity_guessed_away` | `AMBIGUOUS` requires ≥2 enumerated alternatives and forbids a value | IIR-017, IIR-018 |
| `ambiguous_pronoun` | same | IIR-017 |
| `unclear_exception_scope` | same | IIR-018 |
| `vague_temporal_phrase` — normalized into false precision | normalization is restricted to material already written in the source | IIR-009 |
| `undefined_term` | unresolved reference plus `NOT_ESTABLISHED` definiens | IIR-024 |
| `incomplete_delegation` | delegation roles are ordinary slots and may be unknown | IIR-006 |
| `slot_minimality` — the vocabulary grows a slot per phenomenon | evidence and review duties are representable as obligations | IIR-007, IIR-008 |

## F. Process threats without a vector

Recorded honestly as unaddressed by this design:

* **A compromised interpretation authority.** Everything here assumes the institution's
  interpretation instruments are genuine. Issuer authentication is out of scope, exactly as
  it is for admission.
* **A correct-looking but institutionally wrong reading that a real warrant authorizes.**
  This design constrains *who* may decide and *what must support* the decision. It cannot
  make a properly warranted decision correct.
* **Corpus authorship bias.** Every vector's expected IR was authored by the same process
  that designed the schemas. The build script enforces literal source support, which is a
  real check; it is not independent validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
