# OIC Definition Ontology Discrimination 003 — Preregistration

Status: FROZEN DESIGN / NOT EXECUTED

Work order: `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003`

Starting commit: `bef94cdd5a2656c18ba0835dd9f60d97f0a9fc8f`

Successor of: `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002`

## Prior established result

Ontology 002 was fully adjudicable and returned `PARTIAL_SUPPORT`.

Its ontology-clarified combined arm produced the intended
`CONSTITUTIVE_DEFINITION` force on 7/9 primary observations, with seven paired
improvements over the span-only condition and zero B-only control-force defects.

However, definition-slot preservation declined and architectural change remained
unauthorized.

This successor does not reinterpret or overwrite that result.

## Hypothesis

Force classification and slot extraction may interfere when required in one
generative proposal operation.

The falsifiable prediction is that removing slot extraction while keeping the
same six-label ontology and the same constitutive-definition clarification will
improve primary definition-force reliability without degrading control-force
discrimination.

## Experimental arms

### Arm A — combined ontology-clarified

Exact Ontology 002 Arm-B condition.

The candidate span is passed to the frozen Interpretation Proposal task with the
same ontology clarification. The model proposes the full eleven-slot provisional
proposal surface.

No unit-type hint, gold label, authority evidence, warrant, source identity, or
canonical meaning is supplied.

### Arm B — force-only ontology-clarified

The same candidate span is classified using the same six force labels and the
same constitutive-definition clarification.

No slot extraction is requested.

The output is exactly one JSON object containing exactly one key:

`{"normative_force":"<ONE_ALLOWED_LABEL>"}`

No explanation, confidence, authority claim, status, identifier, or additional
semantic slot is allowed.

## Corpus

The same six frozen specimens are used:

- IIR-005 — primary definition
- IIR-006 — delegation control
- IIR-023 — primary definition
- IIR-024 — primary definition
- IIR-027 — advisory control
- IIR-028 — permission control

Three runs per specimen are planned.

Total: 36 requests / 18 paired A-B cells.

Odd runs execute A then B. Even runs execute B then A.

Retries: zero.

Pacing: 4 seconds.

## Provider prerequisite

Live execution is forbidden until a separate
`OIC-NVIDIA-PROVIDER-QUALIFICATION-003` receipt exists with:

- `disposition = QUALIFIED`
- `semantic_successor_authorized = true`
- semantic successor target = `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003`

Qualification 002 is historical evidence and MUST NOT be reused as authorization
for this new semantic work order.

## Adjudicability gate

Semantic adjudication is permitted only if:

- 36/36 observations are ACCEPTED;
- 18/18 A-B pairs are complete;
- 9/9 primary pairs are complete;
- 9/9 control pairs are complete.

Otherwise the only permitted scientific disposition is:

`NOT_ADJUDICABLE_PROVIDER_FAILURE`

## Decision rule

`REGRESSION`

Any force-only B control defect not present in paired combined A.

`REFUTES_FORCE_ONLY_ADVANTAGE`

No control regression, but combined A beats force-only B in at least two paired
primary observations.

`SUPPORTS_TASK_INTERFERENCE_HYPOTHESIS`

No control regression, force-only B is correct on at least 8/9 primary
observations, and B improves at least two paired primary observations over A.

`INCONCLUSIVE`

The experiment is adjudicable, but none of the directional rules above is met.

## Claim ceiling

Even `SUPPORTS_TASK_INTERFERENCE_HYPOTHESIS` does NOT authorize a production
architecture change.

This experiment cannot establish:

- canonical institutional meaning;
- interpretation authority;
- legal validity;
- a revised Institutional IR ontology;
- a schema split;
- staged proposal construction as production architecture;
- cross-model or cross-provider generalization.

`architectural_change_authorized` remains `false`.

No canonicalization is performed.

No Institutional IR runtime is constructed.

No independent validation is claimed.

## Execution state

Provider calls made: ZERO.

Model calls made: ZERO.

Live run executed: NO.

The next step after this preregistration is to implement and statically freeze the
003 instrument and separately preregister Provider Qualification 003.
