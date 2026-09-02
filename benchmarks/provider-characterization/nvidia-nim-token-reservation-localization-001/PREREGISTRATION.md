# NVIDIA Provider Token-Reservation Localization 001 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Trigger

Recovery Stability 002 is formally closed:

`CLOSED_RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE`

Its 18-observation window produced:

- `BASIC_TEXT`: 6/6 accepted;
- `JSON_MODE`: 6/6 accepted;
- `PRODUCTION_TOKEN_RESERVATION`: 4/6 accepted;
- two `PRODUCTION_TOKEN_RESERVATION` provider timeouts.

Root cause remains:

`NOT ESTABLISHED`

Recovery Stability 002 may not be rerun.

Q010 is not created or authorized.

Ontology 007 remains unauthorized.

## Localization question

The frozen `JSON_MODE` and `PRODUCTION_TOKEN_RESERVATION` provider requests
use the same:

- system prompt;
- user prompt;
- JSON response format;
- temperature;
- expected marker.

Their provider-bound experimental difference is the requested token ceiling:

- Arm A: `max_tokens = 64`
- Arm B: `max_tokens = 4096`

This experiment asks whether those two otherwise identical request conditions
show different provider-path failure patterns in a fresh paired window.

## Important provenance boundary

This hypothesis was generated after observing Recovery Stability 002.

It is not independent discovery.

A positive result would support a bounded association with the requested token
reservation condition. It would not establish backend root cause.

## Design

12 matched pairs.

24 fresh provider calls.

Odd pairs:

`A_JSON_64 → B_JSON_4096`

Even pairs:

`B_JSON_4096 → A_JSON_64`

Therefore:

- each arm is observed 12 times;
- each arm appears first in six pairs;
- each arm appears second in six pairs;
- both arms are distributed throughout the full observation window.

## Transport

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- latency headroom: 45 seconds
- pacing: 4 seconds
- retries: ZERO
- replacement observations: FORBIDDEN

## Adjudicability

All 24 observations and all 12 pairs must terminate.

Otherwise:

`INCOMPLETE_LOCALIZATION`

## Frozen classifications

### SHARED_PROVIDER_PATH_FAILURE_PATTERN

Both arms contain at least one provider-path failure.

### RESERVATION_SIZE_SPECIFIC_FAILURE_PATTERN

`B_JSON_4096` contains at least two provider-path failures while
`A_JSON_64` contains zero.

This supports an association with the 4096-token request condition within the
frozen scope only.

### CONTROL_SPECIFIC_FAILURE_PATTERN

`A_JSON_64` contains at least two provider-path failures while
`B_JSON_4096` contains zero.

### SINGLE_FAILURE_ASYMMETRY_INCONCLUSIVE

Exactly one provider-path failure occurs in the full 24-call population.

### NO_FAILURE_WITH_LATENCY_DEGRADATION

All 24 responses are accepted and marker-valid, but one or more exceeds the
45-second latency headroom.

### BOUNDED_NO_FAILURE_WINDOW

All 24 responses are accepted and marker-valid and all are <=45 seconds.

## Scientific boundary

This experiment does not test Ontology 007.

It does not create or authorize Q010.

It does not evaluate an institutional semantic hypothesis.

## Claim ceiling

At most, this experiment can establish a bounded association pattern between
requested `max_tokens` (64 versus 4096) and provider-path behavior for one
endpoint/model and one exact structured-output request.

It cannot establish:

- NVIDIA backend root cause;
- persistent provider unreliability;
- a general token-reservation defect;
- SLA availability;
- cross-model/provider generalization;
- Ontology 007 semantic behavior;
- canonical institutional meaning;
- Institutional IR;
- architecture change;
- independent validation.

## Next activity

Implement, contract-test, materialize and statically freeze this localization
offline.

Do not execute it live.

Do not create Q010.

Do not execute Ontology 007.
