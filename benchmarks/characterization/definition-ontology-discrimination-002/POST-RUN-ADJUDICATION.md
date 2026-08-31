# OIC Definition Ontology Discrimination 002 — Post-Run Adjudication

Status: FINAL POST-RUN INTERPRETATION

## Authoritative status

EXECUTION_COMPLETE / ADJUDICABLE / PARTIAL_SUPPORT

The frozen 36-request execution completed exactly once with zero retries after
`OIC-NVIDIA-PROVIDER-QUALIFICATION-002` returned `QUALIFIED` and explicitly
authorized the semantic successor.

All 36 planned observations were accepted. All 18 paired A/B cells were complete,
including all 9 primary-definition pairs and all 9 control pairs. The preregistered
scientific adjudicability gate therefore passed and the semantic decision rule was
legitimately evaluated.

## Evidence binding

- work order: `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002`
- frozen execution commit: `17775d93b93e00e3dd9a8bb10c97ae9eda373ebe`
- frozen plan SHA-256: `d543a24ef8e39fb3fab3c725114913cfd7b502b9258ec07faade962f542fef27`
- frozen instrument SHA-256: `56f496afc6773daf47ca63c5a7bafae0afbe7e622ef9940906e2437568e99fdd`
- provider qualification receipt SHA-256: `2968774c3b817725804184a2e7fb6788151e8e407d5ddba67c47469383464ea5`
- interpretation-proposal receipt SHA-256: `4016c845757478518130a1570b1e2074550943ec46196ec8671c37e85bec4056`
- live execution log SHA-256: `78a551d6339a76c3784e8db325401510721bb170f5430178a70be5f1678a766f`

## Preregistered disposition

`PARTIAL_SUPPORT`

This disposition is accepted as the scientific result of the run.

The preregistered rule defines `PARTIAL_SUPPORT` as no control regression with Arm B
emitting `CONSTITUTIVE_DEFINITION` on 4–7 of 9 primary observations.

Observed result:

- Arm A, frozen span-only: `CONSTITUTIVE_DEFINITION` correct on 0/9 primary observations.
- Arm B, ontology-clarified: `CONSTITUTIVE_DEFINITION` correct on 7/9 primary observations.
- paired primary improvements, B over A: 7/9.
- paired primary cells: 7 `A_ONLY_DEFECT`, 2 `BOTH_DEFECT`, 0 `B_ONLY_DEFECT`, 0 `NEITHER_DEFECT`.
- B-only control-force defects: 0/9.

## Residual primary failures

The two Arm-B force failures were not specimen-wide impossibilities:

- `IIR-005`: Arm B succeeded in runs 1 and 2 and omitted the force label in run 3.
- `IIR-023`: Arm B succeeded in runs 1 and 3 and omitted the force label in run 2.
- `IIR-024`: Arm B succeeded in all three runs.

The model/provider therefore demonstrated the ability to emit the intended
constitutive-definition label for every primary specimen, but did not do so reliably
across repeated executions under the frozen combined proposal task.

## Control result

The ontology clarification did not produce a force-classification regression on the
three controls. Delegation, advisory, and permission remained correctly separated
from `CONSTITUTIVE_DEFINITION`; the B-only control-force defect count was zero.

This supports the narrow proposition that the clarification carries useful semantic
signal without collapsing the control classes.

## Definition-slot preservation

The stronger support rule was not satisfied because definition-slot preservation
declined.

Observed established-slot compatibility:

- Arm A `definiendum`: 9/9 compatible.
- Arm B `definiendum`: 6/9 compatible.
- Arm A `definiens`: 6/6 compatible.
- Arm B `definiens`: 6/6 compatible.

The receipt therefore correctly records `definition_slots_no_decline = false`.

The force-label improvement cannot be promoted to `SUPPORTS_ONTOLOGY_CLARIFICATION`
under the frozen decision rule.

## Scientific finding

The simple explanation that constitutive definitions fail only because the model is
unaware that `normative_force` includes non-deontic institutional relations is not
sufficient.

The ontology clarification materially improved force classification from 0/9 to 7/9
with zero control-force regression, but the combined proposal task remained unstable
and the improvement coincided with reduced `definiendum` preservation.

A bounded successor hypothesis is therefore warranted: force classification and
slot extraction may interfere when required in one generative proposal operation.
That hypothesis is NOT established by this run and requires a new preregistered
successor experiment.

## Claim ceiling

This experiment characterizes one model/provider on six frozen synthetic admitted
propositions only.

It does NOT establish:

- canonical institutional meaning;
- interpretation authority;
- legal interpretation;
- production readiness;
- cross-model generalization;
- a revised Institutional IR ontology;
- a schema split;
- staged proposal construction as the correct production architecture.

`architectural_change_authorized` remains `false`.

No canonicalization was performed.

No Institutional IR runtime was constructed.

No independent validation is claimed.

## Preservation rule

This work order MUST NOT be rerun.

The original receipt, live execution log, provider-qualification receipt, frozen plan,
and frozen instrument remain immutable evidence of this execution.

Any further semantic experiment MUST use a new successor work order.

## Required successor discrimination

A successor experiment should discriminate among at least these explanations without
modifying the production schema in advance:

1. relation-ontology insufficiency;
2. generative task interference between force classification and slot extraction;
3. model/provider instability at the classification boundary.

A force-only classification arm is an appropriate next falsifier because it can test
whether removing slot extraction raises definition-force reliability while preserving
control discrimination. That design must be separately preregistered before any live
provider calls are made.
