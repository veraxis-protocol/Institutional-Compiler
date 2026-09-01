# NVIDIA Provider Recovery Stability 001 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Trigger

Latency Stability 001 previously observed 36/36 provider timeouts.

Provider Path Incident 001 later reached all six path layers and returned one
accepted frozen BASIC_TEXT inference response.

Incident 001 therefore demonstrated that the historical timeout state was not
persistent at that later observation instant.

It did not establish stable provider recovery.

## Question

Does the same NVIDIA endpoint/model now exhibit bounded recovery stability
across a fresh, preregistered population containing all three frozen provider
probe shapes?

## Fresh population

Six cycles.

Three provider requests per cycle.

Total fresh provider observations: **18**.

Each frozen probe appears six times:

- BASIC_TEXT: 6
- JSON_MODE: 6
- PRODUCTION_TOKEN_RESERVATION: 6

Three cyclic request orders are repeated twice so each probe occurs exactly
twice in each within-cycle position.

No observation from Latency Stability 001 or Incident 001 is reused as a
primary observation.

## Frozen probe semantics

The implementation must hash-verify and source the exact probe semantics from
the frozen Provider Qualification 006 instrument.

Independent reconstruction of those prompts is not permitted.

## Transport

- timeout: 60 seconds
- frozen latency headroom: 45 seconds
- retries: ZERO
- replacement requests: FORBIDDEN
- within-cycle pacing: 4 seconds
- between-cycle pacing: 10 seconds

Every one of the 18 planned positions must terminate as an observation.

A provider error or timeout remains an observation. It is never replaced.

## Classification

### RECOVERY_PATH_UNSTABLE

Any provider error, timeout, HTTP/response failure, response-format mismatch,
invalid expected marker, or incomplete 18-observation execution.

### RECOVERY_HEADROOM_UNSTABLE

All 18 observations are accepted and marker-valid, but at least one exceeds
45 seconds.

### BOUNDED_RECOVERY_STABILITY_OBSERVED

All 18 observations are accepted and marker-valid and all are at or below
45 seconds.

## Qualification boundary

This is characterization, not provider qualification.

Even `BOUNDED_RECOVERY_STABILITY_OBSERVED` does not authorize Ontology 006 and
does not itself create or pass Qualification 007.

A clean recovery result may only permit consideration of a separately
preregistered fresh provider qualification.

## Semantic boundary

No semantic hypothesis is evaluated.

No Ontology 006 request may execute under this work order.

No canonicalization or Institutional IR construction is authorized.

## Claim ceiling

This experiment can establish only bounded post-incident recovery behavior for
one NVIDIA endpoint/model across one fresh 18-observation population.

It establishes no historical root cause, semantic correctness, canonical
institutional meaning, Institutional IR, production readiness, provider
qualification, cross-provider reliability, architecture change, or independent
validation.
