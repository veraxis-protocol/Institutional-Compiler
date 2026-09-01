# OIC NVIDIA Provider Qualification 007 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Purpose

Freshly qualify the exact NVIDIA hosted inference path immediately before the
already-frozen Ontology 006 semantic experiment.

This is a provider-availability gate only.

It evaluates no semantic hypothesis.

## Prerequisite

Provider Recovery Stability 001 is formally closed:

`BOUNDED_RECOVERY_STABILITY_OBSERVED`

That result permits consideration of a fresh provider qualification but does
not itself constitute qualification.

No Recovery Stability 001 observation is reused here.

## Frozen semantic successor

Qualification 007 is bound to the exact frozen:

`OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006`

at commit:

`34abc1bc44bd89d1b29c0d005a23eabfb78ca196`

The complete bound artifact set includes:

- plan;
- preregistration;
- preregistration freeze v0.1;
- treatment binding;
- static freeze v0.2;
- 18-request materialization;
- semantic instrument;
- contract test;
- NVIDIA adapter.

No target artifact may drift between qualification and semantic execution.

## Provider path

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- retries: ZERO
- replacement probes: FORBIDDEN
- pacing: 4 seconds
- latency headroom: 45 seconds

## Frozen probe semantics

Exactly three probes:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

The implementation must source their exact definitions and validation
semantics from the hash-verified frozen Qualification 006 instrument.

No prompt or probe reconstruction is permitted.

## Decision rule

`QUALIFIED`

- exactly three terminal observations;
- all three probes accepted;
- all expected markers valid;
- all elapsed times at or below 45 seconds.

`DEGRADED`

- all three probes accepted and marker-valid;
- at least one elapsed time exceeds 45 seconds.

`NOT_QUALIFIED`

- any provider error;
- timeout;
- response mismatch;
- invalid marker;
- missing/incomplete probe;
- other non-accepted terminal observation.

## Authorization boundary

Qualification 007 live execution does not by itself authorize Ontology 006.

Only a formally closed `QUALIFIED` Qualification 007 result may authorize the
exact frozen Ontology 006 target.

`DEGRADED` and `NOT_QUALIFIED` leave Ontology 006 blocked.

## Claim ceiling

Qualification 007 establishes only immediate provider-path qualification for
one NVIDIA endpoint/model against three frozen probe shapes.

It establishes no semantic result, historical root cause, canonical
institutional meaning, Institutional IR, production readiness, architecture
change, cross-provider reliability, or independent validation.

## Current state

- provider calls: ZERO
- model calls: ZERO
- live Qualification 007: NOT EXECUTED
- Ontology 006 execution: NOT AUTHORIZED
