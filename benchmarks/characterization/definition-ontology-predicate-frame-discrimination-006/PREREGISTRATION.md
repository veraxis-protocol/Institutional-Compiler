# OIC Definition Ontology Predicate-Frame Discrimination 006

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Scientific question

Ontology 005 successfully preserved staged normative-force classification but
regressed on the non-force `action` slot for control specimen IIR-027.

This experiment asks whether that localized regression was caused by the B2
non-force prompt receiving the slot names but not the already-frozen
Institutional IR role semantics for `action` and `object`.

## Frozen predecessor observation

Ontology 005 is closed as `REGRESSION`.

It produced:

- 54/54 accepted semantic observations;
- 9/9 primary staged-force correctness;
- zero staged-B-only control-force defects;
- two staged-B-only non-force defects;
- both defects were IIR-027 / `action`, runs 1 and 3.

Ontology 005 is not rerun and none of its live outputs are reused as Ontology
006 observations.

## Treatment

Arm A reproduces the exact frozen Ontology 005 B2 non-force prompt.

Arm B changes only one thing: it appends the verbatim already-frozen
Institutional IR justifications for `action` and `object`.

No example is added. No gold value is added. No new ontology rule is invented.

The candidate's normative-force value is not visible.

B1 output is not visible.

Both arms receive candidate-span text only.

## Population

Three frozen specimens:

- IIR-027 — target predicate-frame specimen;
- IIR-006 — safety control;
- IIR-028 — safety control.

Three runs per specimen and two paired arms produce:

- 9 paired observations;
- 18 provider requests.

Fresh outputs only.

## Primary endpoint

For IIR-027, evaluator-only gold defines `action = consider`.

Support requires:

- role-guided action compatible 3/3;
- at least two paired observations in which baseline is defective and
  role-guided is compatible;
- zero role-guided-only safety regression.

## Safety endpoint

A role-guided-only omission or incompatibility on a gold-expected non-force
slot, where the paired baseline arm is compatible, is `REGRESSION`.

This applies to IIR-006 and IIR-028 and to non-target expected slots on
IIR-027.

## Transport

Transport is not the scientific treatment.

One retry is permitted only for the exact preregistered condition:

`ModelProviderError: NVIDIA NIM connection timed out`

The retry must use the same `ModelRequest` object and identical request
projection SHA256. Both attempts must be preserved.

## Provider gate

Before any live Ontology 006 execution, a fresh
`OIC-NVIDIA-PROVIDER-QUALIFICATION-006` must be separately preregistered,
statically frozen, executed once, and return `QUALIFIED`.

## Claim ceiling

This experiment can establish only bounded evidence about the localized
predicate-frame hypothesis for one model/provider and three frozen synthetic
specimens.

It cannot establish canonical institutional meaning, interpretation authority,
legal validity, a revised Institutional IR ontology, production architecture,
cross-model or cross-provider generalization, or independent validation.

No architecture change is authorized by this work order.
