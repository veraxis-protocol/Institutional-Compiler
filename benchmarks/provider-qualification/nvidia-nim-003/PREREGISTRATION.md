# OIC NVIDIA Provider Qualification 003 — Preregistration

Status: FROZEN QUALIFICATION DESIGN / NOT EXECUTED

## Purpose

Freshly qualify the exact NVIDIA hosted inference path required by the frozen
`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003` experiment.

This work order tests provider availability only. It tests no semantic
hypothesis.

## Provider path

- base endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- retries: zero
- pacing: 4 seconds
- latency headroom: 45 seconds

## Fixed probes

1. `BASIC_TEXT` — exact text marker, 16 tokens.
2. `JSON_MODE` — exact JSON marker, 64 tokens.
3. `PRODUCTION_TOKEN_RESERVATION` — exact JSON marker, 4096 tokens.

Probe semantics are unchanged from Provider Qualification 002.

## Decision rule

`QUALIFIED` requires 3/3 `ACCEPTED`, valid markers, and every probe at or
below 45 seconds.

`DEGRADED` means 3/3 accepted but one or more probes exceeded 45 seconds.

`NOT_QUALIFIED` means any provider error, response mismatch, missing probe, or
incomplete run.

Only `QUALIFIED` may authorize Ontology 003.

## No remediation prerequisite

Qualification 003 is a fresh pre-semantic provider qualification. It is not a
recovery work order and carries no remediation-marker prerequisite.

## Claim ceiling

This work order establishes provider-path availability only.

It does not evaluate the Ontology 003 semantic hypothesis, canonicalize
institutional meaning, construct Institutional IR, authorize architecture
changes, or claim independent validation.

## Execution state

Provider calls: ZERO.

Model calls: ZERO.

Live qualification: NOT EXECUTED.

Ontology 003 remains unauthorized.
