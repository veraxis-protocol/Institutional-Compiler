# OIC NVIDIA Provider Qualification 006 — Preregistration

Status: **FROZEN QUALIFICATION DESIGN / NOT EXECUTED**

## Purpose

Freshly qualify the exact NVIDIA hosted inference path immediately before
`OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006`.

This work order tests provider-path availability only. It tests no semantic
hypothesis.

## Exact successor target

Qualification 006 is bound to the frozen Ontology 006 artifact set:

- plan;
- preregistration;
- treatment binding;
- preregistration freeze v0.1;
- semantic instrument;
- contract test;
- 18-request offline materialization;
- static instrument freeze v0.2;
- inherited frozen Ontology 005 transport instrument;
- NVIDIA provider adapter.

Ontology 006 contains 18 semantic requests forming nine paired observations:
nine exact Ontology 005-B2 baselines and nine role-guided treatments.

No target artifact may drift between qualification and semantic execution.

## Provider path

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- qualification retries: zero
- pacing: 4 seconds
- latency headroom: 45 seconds

Qualification retries remain zero intentionally.

Ontology 006's separately preregistered one-time exact-timeout recovery
belongs exclusively to semantic execution and is not consumed, simulated, or
broadened by this provider gate.

## Frozen probes

Probe semantics remain unchanged:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

## Decision rule

Only `QUALIFIED` authorizes Ontology 006.

`QUALIFIED` requires all three probes accepted, all expected markers valid,
and every probe at or below 45 seconds.

`DEGRADED` and `NOT_QUALIFIED` leave Ontology 006 unauthorized.

## Claim ceiling

This work order establishes provider-path availability only.

It establishes no predicate-frame result, semantic correctness, canonical
institutional meaning, Institutional IR, production readiness, architecture
change, cross-provider reliability, or independent validation.

## Execution state

Provider calls: ZERO.

Model calls: ZERO.

Live qualification: NOT EXECUTED.

Ontology 006 remains unauthorized.
