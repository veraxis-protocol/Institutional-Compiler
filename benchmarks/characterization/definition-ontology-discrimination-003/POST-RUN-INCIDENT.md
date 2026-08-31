# Ontology 003 — Post-Run Instrument Incident

Status: **CLOSED / EXECUTION ABORTED / NOT SCIENTIFICALLY ADJUDICABLE**

Work order:

`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003`

Frozen execution commit:

`fd07eefae35e3fb0855847bd4d0a911ec3636a9f`

## What happened

Provider Qualification 003 had legitimately returned `QUALIFIED` and
authorized this semantic successor.

The Ontology 003 live process then began from the exact frozen commit.

The first planned request was the combined Arm A observation for IIR-005,
run 1.

The second planned request was the paired force-only Arm B observation.

While constructing the second request, the instrument evaluated the frozen
`user_prompt_template` with Python `str.format(...)`.

That template also contained the literal JSON example:

`{"normative_force":"<ONE_ALLOWED_LABEL>"}`

Those JSON braces were not escaped for Python formatting. Python interpreted
them as a replacement field and raised:

`KeyError: '"normative_force"'`

The failure occurred before the Arm B provider call.

## Partial execution

Exactly one provider call was attempted before the abort: ordinal 1,
combined Arm A, IIR-005 run 1.

Ordinal 2 reached the force-only request-construction path but failed before
`provider.complete()`.

No A/B pair completed.

The instrument writes its structured receipt only after the full request plan,
so no Ontology 003 receipt was produced and the in-memory ordinal-1 attempt
was not persisted as structured experiment evidence.

## Scientific disposition

There is **no semantic disposition**.

The frozen adjudicability gate required all 36 observations and all 18 paired
cells. That gate was not reached.

This incident MUST NOT be classified as
`NOT_ADJUDICABLE_PROVIDER_FAILURE`, because the provider did not cause the
abort.

The appropriate closure state is:

`EXECUTION_ABORTED_INSTRUMENT_DEFECT / NOT_ADJUDICABLE`

No evidence for or against the task-interference hypothesis is established by
this execution.

## Root cause

The defect is in request rendering, not in the experimental semantic design:

- the intended runtime JSON example was valid;
- the frozen template stored literal JSON braces;
- the implementation applied `str.format` to the whole template;
- therefore the JSON braces collided with Python formatting syntax.

## Preservation rule

Ontology 003 MUST NOT be rerun.

The live log is preserved byte-exact.

Live-log SHA-256:

`727fe1ecbdaa422784a227a004640bef47a4d99f10409480f572805154f0ee5e`

Qualification 003 remains a valid historical provider-availability result,
but its one-time authorization was consumed by this attempted successor
execution and MUST NOT be reused for a new work order.

## Required successor

The semantic hypothesis may be carried forward unchanged into a new work
order:

`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A`

The successor must:

1. preserve the 003 semantic design, corpus, arms, ordering, scoring and claim ceiling;
2. replace whole-string `str.format` rendering with a renderer that substitutes
   only `{candidate_span}` and leaves literal JSON braces untouched;
3. add an offline contract test that materializes every planned provider request
   before freeze;
4. verify all 36 request prompts render without exception;
5. verify the force-only runtime prompt contains the literal JSON example exactly;
6. obtain a fresh, separately targeted Provider Qualification 003A authorization;
7. make no architectural change in advance.

No canonicalization was performed.

No Institutional IR runtime was constructed.

No architectural change is authorized.

No independent validation is claimed.
