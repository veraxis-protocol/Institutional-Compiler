# OIC Definition Ontology Discrimination 001

Status: **PREREGISTERED — NO LIVE MODEL CALL MADE**

Starting implementation: `f060dc60620c5ee4f72be7846915b80872afa00f`

Empirical trigger receipt SHA-256: `a1cdf8bde3826074e74b0d907d55e3dab6b78fbe06760d572aef69647560369a`

## Why this experiment exists

The preceding Unit-Type A/B 001A did not repair constitutive-definition force labeling. Arm B emitted `CONSTITUTIVE_DEFINITION` on 0/9 planned definition observations even though the provisional upstream type was `definition`. At the same time, both arms preserved the definition-specific structure: 9/9 compatible `definiendum` observations and 6/6 compatible `definiens` observations. The same A/B recorded zero B-only sentinel defects.

That pattern supports a narrower hypothesis than “the model cannot recognize definitions”: the current output ontology may under-explain that the field named `normative_force` contains both deontic modalities and the constitutive-definition label.

This experiment tests that hypothesis without changing the frozen Institutional IR design.

## Hypothesis

A fixed clarification of the existing output contract will cause the model to emit `CONSTITUTIVE_DEFINITION` when the literal proposition itself constitutes term meaning, while preserving force classification on nearby non-definition controls.

The clarification is not a specimen hint. It does not supply `unit_type`, gold labels, authority metadata, expected interpretation, examples, or external knowledge.

## Frozen specimens

Primary definitions:

- `IIR-005` — constitutive definition
- `IIR-023` — local definition
- `IIR-024` — unresolved external definition

Controls:

- `IIR-006` — delegation; nearest force-label confound
- `IIR-027` — advisory; non-deontic control
- `IIR-028` — permission; deontic control

The source corpus remains byte-frozen at SHA-256:

`462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817`

## Arms

### Arm A — `A_FROZEN_SPAN_ONLY`

Exact frozen Characterization 001 span-only proposal prompt.

### Arm B — `B_ONTOLOGY_CLARIFIED_FORCE_LABEL`

Arm A plus exactly one fixed block:

> ONTOLOGY CLARIFICATION FOR THIS OUTPUT CONTRACT:
> The field name `normative_force` is used here for all six allowed institutional relation labels, not only deontic modalities. `CONSTITUTIVE_DEFINITION` is therefore the required `normative_force` label when, and only when, the literal proposition itself constitutes what a term means. This label is provisional description only: it does not establish authority or canonical institutional meaning. Infer it only from the proposition; do not infer or resolve anything from outside text.

No provisional `unit_type` is supplied.

## Execution

- 6 specimens
- 3 runs per specimen
- 2 arms
- 36 planned provider requests
- odd runs: A then B
- even runs: B then A
- exactly one provider call per planned request
- no retries
- external pacing only
- same NVIDIA provider/model configuration as the preceding characterization

## Primary diagnostic

For `IIR-005`, `IIR-023`, and `IIR-024`, measure whether each arm emits:

`normative_force = CONSTITUTIVE_DEFINITION`

Planned denominator: 9 observations per arm.

Also preserve and compare `definiendum` and `definiens` compatibility.

## Regression controls

For `IIR-006`, `IIR-027`, and `IIR-028`, compare the expected force between paired A/B observations.

Any B-only control force defect is a regression.

## Frozen disposition rule

1. `REGRESSION` if any B-only control force defect occurs.
2. `SUPPORTS_ONTOLOGY_CLARIFICATION` if there is no regression, Arm B emits `CONSTITUTIVE_DEFINITION` on at least 8/9 primary observations, at least 6 paired primary observations improve from A to B with both provider calls accepted, and definition-slot compatibility does not decline.
3. `PARTIAL_SUPPORT` if there is no regression and Arm B emits `CONSTITUTIVE_DEFINITION` on 4–7/9 primary observations.
4. `INCONCLUSIVE_EFFECT` if there is no regression and Arm B emits `CONSTITUTIVE_DEFINITION` on at least 8/9 primary observations but one or more paired-improvement or definition-slot-preservation support criteria are not met.
5. `REFUTES_SIMPLE_ONTOLOGY_CLARIFICATION` if there is no regression and Arm B emits `CONSTITUTIVE_DEFINITION` on 0–3/9 primary observations.

Provider errors are recorded as missing/defective planned observations and are never retried. A paired improvement is counted only when both calls were accepted.

## Claim ceiling

This experiment can characterize whether a fixed output-ontology clarification changes one model/provider's provisional force labeling on six frozen synthetic admitted propositions.

It cannot establish:

- a revised Institutional IR ontology;
- canonical institutional meaning;
- interpretation authority;
- legal interpretation;
- production readiness;
- cross-model generalization;
- canonicalization correctness;
- an Institutional IR runtime.

No production file is changed. No canonicalization is implemented. No Institutional IR runtime is implemented.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
