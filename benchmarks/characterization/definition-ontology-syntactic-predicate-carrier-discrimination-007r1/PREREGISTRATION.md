# Ontology 007R1 — Authorization-Binding Repair

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Established defect

Frozen Ontology 007 is bound to:

`OIC-NVIDIA-PROVIDER-QUALIFICATION-009`

and to the fixed result path:

`benchmarks/provider-qualification/nvidia-nim-009/EXECUTION-RESULT-v0.1.json`

Q009 is now formally closed `NOT_QUALIFIED` and may not be rerun.

Therefore frozen Ontology 007 cannot be authorized by a future Q010 or later
qualification artifact without changing the frozen experiment.

Frozen Ontology 007 itself will not be modified.

## Provider evidence boundary

Subsequent provider characterization did not establish that `max_tokens=4096`
causes the observed provider-path failures.

Recovery Stability 002 did not establish bounded recovery stability.

Token-Reservation Localization 001 closed
`SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE`.

Provider root cause remains `NOT_ESTABLISHED`.

These findings justify no semantic change to Ontology 007.

## Repair

007R1 is an authorization-binding-only successor.

All 18 semantic requests must be byte-identical to frozen Ontology 007.

The following remain unchanged:

- specimens;
- run count;
- arm ordering;
- Arm A;
- Arm B;
- treatment guidance;
- semantic request bytes;
- analysis population;
- scoring;
- decision rules;
- claim ceiling.

No production interpretation rule is changed.

## Qualification-artifact contract

007R1 must not hard-code a particular qualification number such as Q010.

At execution, a qualification artifact must be supplied explicitly.

There is no implicit “latest qualification” selection.

The supplied artifact must:

- be a tracked repository artifact;
- be consumed only from a clean repository state;
- report `CLOSED_EXECUTED_QUALIFIED`;
- report provider qualification established;
- report live disposition `QUALIFIED`;
- bind exactly to the statically frozen 007R1 target;
- report qualification rerun unauthorized;
- contain no semantic hypothesis result;
- authorize no architecture change.

The qualification work-order number itself confers no authority.

A future Q010 or later qualification may satisfy the contract only if its
contents bind exactly to 007R1 and satisfy every frozen eligibility condition.

## Current state

- 007R1 implemented: NO
- 007R1 statically frozen: NO
- Q010 created: NO
- Q010 authorized: NO
- provider calls: ZERO
- semantic calls: ZERO
- 007R1 live execution: NO
- production ruleset changed: NO
- architecture change authorized: NO

## Next activity

Implement 007R1 offline.

Prove all 18 semantic requests are byte-identical to frozen Ontology 007.

Prove analysis and decision-rule parity.

Implement only the qualification-artifact resolution/validation repair.

Then statically freeze.

Do not create Q010 yet.

Do not execute Ontology 007 or 007R1.
