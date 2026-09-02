# NVIDIA Provider Recovery Stability 002 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Trigger

Provider Qualification 009 executed exactly once and formally closed:

`CLOSED_EXECUTED_NOT_QUALIFIED`

The immediate gate produced:

- `BASIC_TEXT`: accepted / marker-valid / 0.712s
- `JSON_MODE`: provider timeout / 60.075s
- `PRODUCTION_TOKEN_RESERVATION`: accepted / marker-valid / 0.520s

Q009 may not be rerun.

Ontology 007 remains unauthorized.

## Question

Was the Q009 provider-path failure followed by bounded short-window recovery,
or does a fresh repeated observation window contain another provider-path
failure or latency-headroom violation?

This is not a semantic experiment.

## Probe semantics

Use only the exact three frozen provider probes already bound by Q009:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

No probe text, schema, token reservation, endpoint, model, or expected marker
may change.

## Population

Six rounds.

Three probes per round.

18 total fresh provider observations.

No Q009 live observation is counted in the new population.

## Order control

Use each of the six permutations of the three probes exactly once.

Therefore every probe appears:

- six times total;
- twice in first position;
- twice in second position;
- twice in third position.

This prevents the failed Q009 probe's original second-position placement from
being confounded with the probe identity.

## Transport

- timeout: 60 seconds
- latency headroom: 45 seconds
- retries: ZERO
- replacements: FORBIDDEN
- pacing: 4 seconds

## Adjudicability

All 18 observations and all six rounds must terminate before the recovery
classification is evaluated.

Otherwise:

`INCOMPLETE_CHARACTERIZATION`

## Classification

### RECOVERY_NOT_ESTABLISHED_PROVIDER_PATH_FAILURE

All 18 observations terminate, but at least one is a provider error,
response mismatch, invalid-marker result, or other non-accepted outcome.

### RECOVERY_OBSERVED_WITH_LATENCY_DEGRADATION

All 18 observations are accepted and marker-valid, but one or more exceeds
the frozen 45-second latency headroom.

### BOUNDED_RECOVERY_STABILITY_OBSERVED

All 18 observations are accepted and marker-valid and all are <=45 seconds.

## Boundary

A successful recovery characterization does not itself authorize Ontology 007.

It also does not authorize or create Q010.

If bounded recovery is observed and formally closed, a fresh future provider
qualification must still be separately preregistered and bound to the exact
frozen Ontology 007 target.

## Current state

- provider/model/network calls: ZERO
- Q009 rerun: NO
- Recovery Stability 002 live run: NO
- Q010 created: NO
- Ontology 007 authorized: NO
- Ontology 007 executed: NO
- semantic hypothesis evaluated: NO
- architecture change authorized: NO

## Claim ceiling

This experiment can establish only bounded short-window provider-path
recovery/stability for this endpoint/model and these exact three probes.

It cannot establish persistent reliability, root cause, SLA availability,
cross-provider generalization, Ontology 007 semantic behavior, production
interpretation semantics, Institutional IR, architecture change, or
independent validation.

## Next activity

Implement, contract-test, materialize and statically freeze this
characterization offline.

Do not execute it live.

Do not create Q010.

Do not execute Ontology 007.
