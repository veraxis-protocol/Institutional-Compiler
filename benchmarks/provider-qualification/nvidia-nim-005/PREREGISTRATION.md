# OIC NVIDIA Provider Qualification 005 — Preregistration

Status: FROZEN QUALIFICATION DESIGN / NOT EXECUTED

## Purpose

Freshly qualify the exact NVIDIA hosted inference path immediately before the
frozen `OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005` experiment.

This qualification tests provider-path availability only. It tests no semantic
hypothesis.

## Frozen successor target

Qualification 005 is bound to the exact frozen Ontology 005 artifact set:

- plan;
- preregistration;
- preregistration freeze v0.1;
- transport-recovery policy;
- semantic-replication binding;
- instrument freeze v0.2;
- semantic instrument;
- contract test;
- 54-request offline materialization;
- NVIDIA adapter bytes used by the target transport policy.

The frozen semantic request population is:

- Arm A: 18;
- Arm B1: 18;
- Arm B2: 18.

No target artifact may drift between qualification and semantic execution.

## Provider path

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- qualification retries: zero
- pacing: 4 seconds
- latency headroom: 45 seconds

Qualification retries remain zero intentionally. The one-time exact-timeout
retry preregistered for Ontology 005 belongs to semantic execution and is not
consumed or simulated by this availability gate.

## Frozen probes

Probe semantics are unchanged from Provider Qualifications 003A and 004:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

## Decision rule

Only `QUALIFIED` authorizes Ontology 005.

`QUALIFIED` requires all three probes accepted, all expected markers valid,
and every probe at or below 45 seconds.

`DEGRADED` and `NOT_QUALIFIED` leave Ontology 005 unauthorized.

## Fresh-gate boundary

Qualification 005 is not a provider-remediation work order and has no
remediation prerequisite.

## Claim ceiling

This work order establishes provider-path availability only.

It establishes no semantic result, canonical institutional meaning,
Institutional IR, production readiness, architecture change, cross-provider
reliability, or independent validation.

## Execution state

Provider calls: ZERO.

Model calls: ZERO.

Live qualification: NOT EXECUTED.

Ontology 005 remains unauthorized.
