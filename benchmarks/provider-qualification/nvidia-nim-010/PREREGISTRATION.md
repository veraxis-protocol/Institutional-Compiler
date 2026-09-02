# NVIDIA Provider Qualification 010

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Purpose

Q010 is one fresh immediate provider-path qualification for the exact
statically frozen Ontology 007R1 target.

It is not a rerun of Q009.

Q009 is permanently closed `NOT_QUALIFIED` and remains untouched.

## Why a new qualification is justified

Q009 targeted frozen Ontology 007.

Ontology 007R1 is a distinct authorization-binding-only successor with
byte-identical semantic requests but a repaired qualification-artifact
contract.

No previous qualification artifact targets the exact frozen 007R1
descriptor.

Intervening provider characterization also did not establish either:

- persistent provider-path failure; or
- an association between `max_tokens=4096` and provider failure.

Therefore one new exact-target qualification is scientifically permissible.

This is not sampling until success:

- Q009 is not rerun;
- Recovery Stability 002 is not rerun;
- Localization 001 is not rerun;
- historical observations are not counted as Q010 observations;
- Q010 has a new frozen population;
- Q010 may execute at most once.

## Population

Nine fresh provider calls.

Three frozen probe types:

1. `BASIC_TEXT`
2. `JSON_MODE`
3. `PRODUCTION_TOKEN_RESERVATION`

Each frozen request projection is inherited byte-identically from the
corresponding Q009 probe specification.

No historical response is reused.

## Balanced execution order

Round 1:

`BASIC_TEXT → JSON_MODE → PRODUCTION_TOKEN_RESERVATION`

Round 2:

`JSON_MODE → PRODUCTION_TOKEN_RESERVATION → BASIC_TEXT`

Round 3:

`PRODUCTION_TOKEN_RESERVATION → BASIC_TEXT → JSON_MODE`

Therefore each probe appears:

- three times total;
- once in position 1;
- once in position 2;
- once in position 3.

## Execution envelope

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- qualification headroom: 45 seconds
- pacing: 4 seconds
- retries: zero
- replacement probes: forbidden

## Frozen disposition

`QUALIFIED`

Exactly 9 terminal observations; 9/9 ACCEPTED; 9/9 expected markers valid;
every accepted latency <=45 seconds.

`DEGRADED`

Exactly 9 terminal observations; 9/9 ACCEPTED and marker-valid; at least one
latency >45 seconds.

`NOT_QUALIFIED`

Exactly 9 terminal observations with any provider error, timeout, response
mismatch, invalid marker, or other non-ACCEPTED observation.

`INCOMPLETE`

Fewer than 9 terminal observations or fewer than 3 complete rounds.

Disposition precedence:

`INCOMPLETE → NOT_QUALIFIED → DEGRADED → QUALIFIED`

Only `QUALIFIED` can establish provider qualification.

## Authorization boundary

A live `QUALIFIED` disposition is not semantic authorization.

Q010 must first be formally closed in a tracked result.

For that result to satisfy 007R1 it must report, at minimum:

- `status = CLOSED_EXECUTED_QUALIFIED`
- `live_disposition = QUALIFIED`
- `provider_qualification_established = true`
- `rerun_authorized = false`
- `semantic_hypothesis = null`
- `semantic_hypothesis_evaluated = false`
- `architecture_change_authorized = false`
- `independent_validation_claim = false`
- an exact `semantic_successor_target` equal to frozen Ontology 007R1

The closure commit must then be independently verified.

Only after that may 007R1 live execution be considered authorized.

## Claim ceiling

Q010 is an immediate bounded provider gate only.

It establishes no persistent NVIDIA reliability, SLA, backend root cause,
max-token defect, semantic result, canonical institutional meaning,
Institutional IR, architecture change, cross-provider generalization, or
independent validation.

## Current state

- Q010 implemented: NO
- Q010 live execution authorized: NO
- Q010 executed: NO
- Q010 rerun authorized: NO
- provider calls: ZERO
- model calls: ZERO
- NVIDIA network calls: ZERO
- Ontology 007R1 execution authorized: NO
- Ontology 007R1 executed: NO

## Next activity

Implement, contract-test, materialize and statically freeze Q010 offline.

Do not execute Q010 live.

Do not execute Ontology 007R1.
