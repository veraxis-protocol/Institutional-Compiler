# OIC Definition Ontology Discrimination 003A — Preregistration

Status: FROZEN DESIGN / NOT EXECUTED

Work order:

`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A`

Starting commit:

`1d3833b9be6caef7906aef75016967dc709c3931`

Successor of:

`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003`

## Why a successor exists

Ontology 003 was executed once and aborted during request construction.

The abort was caused by an instrument defect: the force-only prompt template
contained a literal JSON object while the implementation applied Python
`str.format(...)` to the entire template.

One combined Arm-A provider call had already been attempted. The paired
force-only request failed before its provider call.

Therefore:

- Ontology 003 is permanently closed;
- zero A/B pairs completed;
- no Ontology 003 receipt exists;
- no semantic decision was evaluated;
- no evidence for or against the semantic hypothesis was established.

003A is a new work order. It is not a rerun of 003.

## Semantic-design preservation

The Ontology 003 semantic experiment is preserved unchanged.

003A preserves exactly:

- the same six specimens;
- the same primary and control assignments;
- the same two semantic arms;
- the same ontology clarification;
- the same force vocabulary;
- the same three runs per specimen;
- the same 36-request / 18-pair design;
- the same odd/even paired interleaving;
- the same zero-retry policy;
- the same 4-second pacing;
- the same endpoints;
- the same semantic decision rule;
- the same secondary descriptive endpoints;
- the same claim ceiling.

No semantic prompt wording is changed.

## Instrument repair

The repair is mechanical only.

The force-only user prompt MUST NOT be rendered with whole-string
`str.format(...)`.

The implementation must substitute only the exact literal token:

`{candidate_span}`

All other characters in the frozen prompt template must remain literal.

In particular the runtime prompt must preserve exactly:

`{"normative_force":"<ONE_ALLOWED_LABEL>"}`

## Mandatory offline request materialization

Before the instrument may be frozen, all 36 planned provider requests must be
materialized offline.

The materialization step must construct no provider and make no network call.

A frozen materialization manifest must establish that:

1. all 36 requests materialize without exception;
2. all ordinal/specimen/run/arm identities match the frozen request plan;
3. the 18 Arm-A requests preserve the Ontology 003 combined condition;
4. the 18 Arm-B requests substitute only `{candidate_span}`;
5. every Arm-B runtime prompt contains the literal JSON example exactly;
6. no unresolved `{candidate_span}` token remains;
7. no gold label is exposed;
8. no authority metadata is exposed.

Failure of any materialization check blocks instrument freeze.

## Provider prerequisite

Provider Qualification 003 is historical evidence only. Its one-time
authorization was consumed by the attempted Ontology 003 execution.

003A therefore requires a new:

`OIC-NVIDIA-PROVIDER-QUALIFICATION-003A`

receipt with:

- `disposition = QUALIFIED`;
- `semantic_successor_authorized = true`;
- semantic-successor target =
  `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A`.

## Adjudicability

The semantic adjudicability gate is unchanged:

- 36/36 observations ACCEPTED;
- 18/18 A/B pairs complete;
- 9/9 primary pairs complete;
- 9/9 control pairs complete.

No semantic decision may be evaluated unless the full gate passes.

## Claim ceiling

Unchanged from Ontology 003.

Even a positive result cannot establish canonical institutional meaning,
interpretation authority, legal validity, a revised Institutional IR ontology,
a schema split, production staging, cross-model generalization, or an
architectural change.

`architectural_change_authorized = false`

No canonicalization is performed.

No Institutional IR runtime is constructed.

No independent validation is claimed.

## Execution state

Provider calls made by 003A: ZERO.

Model calls made by 003A: ZERO.

Live 003A execution: NOT EXECUTED.

Provider Qualification 003A: NOT EXECUTED.

The next authorized activity is implementation of the 003A instrument plus
complete offline materialization of all 36 frozen requests.
