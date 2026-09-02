# OIC NVIDIA Provider Qualification 008 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Purpose

Freshly qualify the NVIDIA hosted inference path immediately before the
repaired and statically frozen Ontology 006R1 semantic experiment.

This is a provider-path gate only.

It evaluates no semantic hypothesis.

## Exact semantic successor

Qualification 008 is bound to the exact frozen:

`OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006R1`

The bound target includes:

- O006R1 plan;
- preregistration;
- authorization-binding repair contract;
- preregistration freeze v0.1;
- static freeze v0.2;
- repaired executable;
- contract test;
- 18-request materialization;
- NVIDIA provider adapter;
- exact request count and pair count.

Any target drift invalidates qualification authorization.

## Provider probes

Exactly three frozen provider probes:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

Probe semantics remain exactly those of the frozen provider qualification
probe specification:

`262445c71ca34f41dd9d173a978ebcaa7bd71df2f313f0c9b090b9fd4a8925d1`

## Transport boundary

- timeout: 60 seconds
- latency headroom: 45 seconds
- retries: ZERO
- replacements: FORBIDDEN
- pacing: 4 seconds

## Decision rule

`QUALIFIED` requires:

- exactly 3 terminal observations;
- 3/3 accepted;
- 3/3 expected markers valid;
- every elapsed time <=45 seconds.

`DEGRADED` means all probes are accepted and valid but one or more exceed
45 seconds.

`NOT_QUALIFIED` includes any provider failure, timeout, response mismatch,
invalid marker, missing probe, or incomplete execution.

## Formal-closure boundary

A live `QUALIFIED` disposition does not authorize O006R1.

O006R1 accepts only the tracked, formally closed Qualification 008 execution
result.

The formal result must:

- be `CLOSED_QUALIFIED`;
- state Qualification 008 formally closed;
- state Qualification 008 qualified;
- state provider qualification established;
- explicitly authorize O006R1;
- contain the exact frozen O006R1 target descriptor.

## Non-inheritance

No Q007 observation or authorization is reused.

No Recovery Stability observation is reused.

Qualification 008 is a fresh gate for the repaired target.

## Current state

- provider calls: ZERO
- model calls: ZERO
- network calls: ZERO
- live Q008: NOT EXECUTED
- Q008 formally closed: FALSE
- Q008 qualified: FALSE
- O006R1 authorized: FALSE
- O006R1 executed: FALSE

## Claim ceiling

Provider-path qualification only.

No semantic result, canonical institutional meaning, Institutional IR,
production readiness, architecture change, cross-provider reliability,
historical root cause, or independent validation is established.

## Next activity

Implement, test, materialize and statically freeze Q008 offline.

Do not execute Q008 live.

Do not execute O006R1.
