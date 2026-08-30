# Ambiguity and Unknown v0.1

## Why a four-value vocabulary, and why not ZTL's

The obvious choice is the three-value set the work order names: `ESTABLISHED`,
`AMBIGUOUS`, `NOT_ESTABLISHED`. Three values are not quite enough, and importing ZTL's
disposition vocabulary would be worse than either: ZTL states describe *link* verification
under a trust profile, not whether an institution has settled what a proposition means.
Reusing them would make two unrelated questions look like one.

The IR-specific derivation:

| Status | The source… | A compiler should… |
| --- | --- | --- |
| `ESTABLISHED` | supports exactly one reading, and an institutional basis recognizes it | compute with the value |
| `AMBIGUOUS` | supports two or more readings, and no permitted basis selects between them | refuse, or ask; the alternatives are enumerated for it |
| `NOT_ESTABLISHED` | does not supply this slot at all | refuse; never substitute a default |
| `NOT_APPLICABLE` | was never asked this question, because the force does not raise the slot | proceed; this is not missing information |

`AMBIGUOUS` and `NOT_ESTABLISHED` are genuinely different. In the first, the source *did*
say something and what it said is unsettled; in the second, the source is silent. Merging
them would either hide competing readings or manufacture a fake choice.

`NOT_APPLICABLE` was added because without it a compiler cannot distinguish "no threshold
applies to this definition" from "the threshold is unknown". Treating the first as unknown
makes the system fail closed on questions nobody asked; treating the second as
inapplicable makes it fail open. That is a real distinction, so it gets a value.

There is deliberately **no** `RESOLVED_BY_PREFERENCE`, no `LIKELY`, no `CONFIDENT`, and no
numeric score anywhere in the schemas.

## The ten ambiguity situations

| Situation | Representation | Vector |
| --- | --- | --- |
| multiple plausible actors | `bearer` `AMBIGUOUS`, both enumerated | IIR-017 |
| unclear attachment of a condition | the attached slot `AMBIGUOUS`, condition still `ESTABLISHED` | IIR-018 |
| ambiguous recipient | `counterparty` `AMBIGUOUS` | same shape as IIR-017 |
| unclear exception scope | `exception` `AMBIGUOUS`, `exception_closure` stays `OPEN` | IIR-018 threat tag |
| undefined cross-reference | reference kept `UNRESOLVED`; dependent slot `NOT_ESTABLISHED` | IIR-024, IIR-026 |
| vague temporal phrase | `temporal_qualifier` `ESTABLISHED` on the literal phrase, **not** normalized | IIR-009 |
| ambiguous pronoun | the slot the pronoun would fill is `AMBIGUOUS` | IIR-017 |
| conflicting definitions | two definition units, one per source instance; no merge | IIR-033 shape |
| incomplete delegation | the missing role `NOT_ESTABLISHED`; force stays `DELEGATION` | IIR-006 threat tag |
| unclear normative force | `normative_force` `AMBIGUOUS`; the unit still exists | vocabulary permits it |

A vague temporal phrase is worth dwelling on. "Within two business days" is not ambiguous
about *what it says* — it is precise text whose institutional meaning depends on a
definition of "business day" that this unit does not carry. So it is `ESTABLISHED` as a
literal qualifier and left un-normalized. Normalizing it to 48 hours would be the invention
this whole design exists to prevent.

## Resolving ambiguity

Only an institutional interpretation warrant carrying `ROLE_ASSIGNMENT` or
`FORCE_ASSIGNMENT` can move an assertion from `AMBIGUOUS` to `ESTABLISHED`, and the result
is a **different IR unit** with a different `ir_unit_id` and a different
`semantic_equivalence_key` — IIR-034 records exactly this pair. Canonical meaning is
warrant-dependent, and the record shows which warrant produced it.

Nothing moves an assertion from `NOT_ESTABLISHED` to `ESTABLISHED` except a warrant, and
nothing at all moves it to `false`.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
