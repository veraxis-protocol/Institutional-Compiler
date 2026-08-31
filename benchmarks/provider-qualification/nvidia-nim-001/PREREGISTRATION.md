# OIC NVIDIA Provider Qualification 001

Status: PREREGISTERED / PROVIDER-ONLY / NO SEMANTIC HYPOTHESIS

## Purpose

`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-001` completed 36/36 planned calls
as `PROVIDER_ERROR`, leaving zero semantic observations. Its authoritative
status is `HYPOTHESIS_NOT_ADJUDICATED`.

This work order isolates the exact NVIDIA NIM provider path before any
successor semantic experiment is authorized.

## Frozen provider path

- base commit: `c4a87eb8483c3bd965612b601399463e005bd73e`
- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- retries: 0
- pacing: 4 seconds between probes

## Three probes

1. `BASIC_TEXT` — minimal text response, 16-token ceiling.
2. `JSON_MODE` — JSON-object response mode, 64-token ceiling.
3. `PRODUCTION_TOKEN_RESERVATION` — JSON-object response mode with
   `max_tokens=4096`, matching the current Interpretation Proposal request ceiling.

No probe asks for institutional interpretation. No probe can establish or refute
an OIC semantic hypothesis.

## Qualification rule

`QUALIFIED` requires all three probes to be accepted, all transport markers
to be valid, and every observed latency to be at most 45 seconds.

`DEGRADED` means all three responses arrived but the provider lacked the
preregistered latency headroom.

`NOT_QUALIFIED` means any provider error, response mismatch, missing probe,
or incomplete execution.

Only `QUALIFIED` authorizes a successor semantic experiment.

## Evidence discipline

The live qualification runs exactly once and writes a gitignored local receipt.
No retry is permitted. The NVIDIA credential is read only from the existing
local environment and is never written to repository artifacts or receipts.

No canonicalization is performed.
No Institutional IR runtime is constructed.
No independent validation is claimed.
