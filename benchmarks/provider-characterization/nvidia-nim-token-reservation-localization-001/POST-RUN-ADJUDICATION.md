# Token-Reservation Localization 001 — Post-Run Adjudication

**Work order:** `OIC-NVIDIA-PROVIDER-TOKEN-RESERVATION-LOCALIZATION-001`

**Final scientific disposition:** `SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE`

## Executive adjudication

Token-Reservation Localization 001 is CLOSED as an executed, fully adjudicable
provider-path characterization.

All 24 frozen observations terminated and all 12 matched pairs completed.

The frozen provider-bound contrast was `max_tokens` only:

- Arm A: `max_tokens = 64`
- Arm B: `max_tokens = 4096`

Observed result:

- Arm A: 12/12 accepted and marker-valid;
- Arm B: 11/12 accepted and marker-valid;
- one Arm-B-only failure;
- failure ordinal: 15;
- pair: 8;
- position: 1;
- outcome: `RESPONSE_MISMATCH`;
- no accepted observation exceeded the 45-second latency headroom.

## Frozen decision-rule application

The preregistered
`RESERVATION_SIZE_SPECIFIC_FAILURE_PATTERN`
classification required:

- at least two Arm-B failures; and
- zero Arm-A failures.

Observed:

- Arm-B failures: 1;
- Arm-A failures: 0.

The threshold was therefore **not met**.

The preregistered disposition is:

`SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE`

## What is established

A single asymmetric failure occurred in the `max_tokens = 4096` arm during this
complete matched-pair window.

That observation is real and preserved.

## What is not established

The result does **not** establish:

- a reservation-size-specific provider failure pattern;
- an association between `max_tokens = 4096` and provider failure;
- NVIDIA backend root cause;
- persistent NVIDIA unreliability;
- a general token-reservation defect;
- a position effect;
- a temporal effect;
- SLA availability;
- cross-provider or cross-model generalization;
- Ontology 007 semantic behavior;
- the syntactic predicate-carrier hypothesis;
- canonical institutional meaning;
- Institutional IR;
- production architecture;
- independent validation.

Causal root cause remains **NOT ESTABLISHED**.

## Evidence

Both primary evidence objects were available and independently hash-verified at
closure:

- primary live receipt;
- auxiliary live log.

Neither evidence object was reconstructed.

## Downstream state

- Localization 001 rerun authorized: **NO**
- successor provider qualification automatically authorized: **NO**
- Q010 created: **NO**
- Q010 authorized: **NO**
- Ontology 007 execution authorized: **NO**
- Ontology 007 executed: **NO**
- semantic hypothesis evaluated: **NO**
- canonicalization performed: **NO**
- Institutional IR constructed: **NO**
- architecture change authorized: **NO**

## Next activity

Do not rerun Localization 001.

Do not create Q010.

Do not execute Ontology 007.

Any further provider-path characterization requires a new, separately justified
and preregistered work order.
