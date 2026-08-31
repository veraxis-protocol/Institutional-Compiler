# OIC NVIDIA Provider Qualification 003A — Preregistration

Status: FROZEN QUALIFICATION DESIGN / NOT EXECUTED

## Purpose

Freshly qualify the exact NVIDIA hosted inference path immediately before
the frozen `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A` experiment.

This qualification tests provider-path availability only. It tests no
semantic hypothesis.

## Frozen successor target

Qualification 003A is bound to the exact Ontology 003A:

- plan;
- preregistration;
- v0.2 instrument freeze;
- semantic instrument;
- contract test;
- 36-request offline materialization manifest.

No target artifact may drift between qualification and semantic execution.

## Provider path

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- retries: zero
- pacing: 4 seconds
- latency headroom: 45 seconds

## Frozen probes

Probe semantics are unchanged from Provider Qualification 003:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

## Decision rule

Only `QUALIFIED` authorizes Ontology 003A.

`QUALIFIED` requires all three probes accepted, all expected markers valid,
and every probe at or below 45 seconds.

`DEGRADED` and `NOT_QUALIFIED` leave Ontology 003A unauthorized.

## Fresh-gate boundary

Qualification 003A is not a provider-recovery work order and has no
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

Ontology 003A remains unauthorized.
