# OIC NVIDIA Provider Qualification 004 — Preregistration

Status: FROZEN QUALIFICATION DESIGN / NOT EXECUTED

## Purpose

Freshly qualify the exact NVIDIA hosted inference path immediately before
the frozen `OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-004` experiment.

This qualification tests provider-path availability only. It tests no
semantic hypothesis.

## Frozen successor target

Qualification 004 is bound to the exact frozen Ontology 004:

- plan;
- preregistration;
- v0.2 instrument freeze;
- semantic instrument;
- contract test;
- 54-request offline materialization manifest.

The frozen request population is:

- Arm A: 18;
- Arm B1: 18;
- Arm B2: 18.

No target artifact may drift between qualification and semantic execution.

## Provider path

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- retries: zero
- pacing: 4 seconds
- latency headroom: 45 seconds

## Frozen probes

Probe semantics are byte-semantically unchanged from Provider
Qualification 003A:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

## Decision rule

Only `QUALIFIED` authorizes Ontology 004.

`QUALIFIED` requires all three probes accepted, all expected markers valid,
and every probe at or below 45 seconds.

`DEGRADED` and `NOT_QUALIFIED` leave Ontology 004 unauthorized.

## Fresh-gate boundary

Qualification 004 is not a provider-recovery work order and has no
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

Ontology 004 remains unauthorized.
