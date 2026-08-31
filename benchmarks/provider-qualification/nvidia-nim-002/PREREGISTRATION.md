# OIC NVIDIA Provider Qualification 002 — Preregistration

Status: FROZEN / PRE-LIVE / REMEDIATION-BLOCKED

Base / semantic-successor commit: `17775d93b93e00e3dd9a8bb10c97ae9eda373ebe`

Target semantic work order: `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002`

## Why 002 exists

`OIC-NVIDIA-PROVIDER-QUALIFICATION-001` is permanently closed as
`NOT_QUALIFIED`. It must not be rerun.

The failure was subsequently localized below OIC semantics:
authenticated `/v1/models` succeeded, the exact Nemotron model was visible,
a raw `stream=false` chat request still received zero bytes before timeout,
and an alternative account-visible model returned HTTP 404 with
`Function ... Not found for account`.

Qualification 002 is therefore a recovery gate, not a repeat of 001.

## Remediation prerequisite

Live execution is forbidden until this local marker exists:

`.local/provider-remediation/OIC-NVIDIA-PROVIDER-QUALIFICATION-002-REMEDIATION.json`

and contains:

- `work_order = OIC-NVIDIA-PROVIDER-QUALIFICATION-002`
- `remediation_confirmed = true`

The marker is owner-recorded evidence that NVIDIA has indicated the
account/public-endpoint routing issue is repaired or enabled.

## Probe design

The provider path and three probes are semantically unchanged from Qualification 001:

1. BASIC_TEXT
2. JSON_MODE
3. PRODUCTION_TOKEN_RESERVATION

Endpoint: `https://integrate.api.nvidia.com/v1`

Model: `nvidia/nemotron-3.5-lightning-30b-a3b`

Timeout: 60 seconds

Pacing: 4 seconds

Retries: 0

Latency headroom: 45 seconds

## Decision

Only `QUALIFIED` authorizes the already-preregistered
`OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002`.

`DEGRADED` and `NOT_QUALIFIED` keep semantic execution closed.

No semantic hypothesis is tested by this work order.
