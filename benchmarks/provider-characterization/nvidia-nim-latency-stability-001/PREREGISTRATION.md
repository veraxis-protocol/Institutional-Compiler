# NVIDIA Provider Latency Stability 001 — Preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED**

## Motivation

Provider Qualification 006 is closed `DEGRADED`.

All three provider probes were accepted and marker-valid. `JSON_MODE` required
55.795 seconds against the frozen 45-second latency headroom.

Qualification 006 must not be rerun. Ontology 006 remains unexecuted and
unauthorized.

This work order is not another provider qualification. It is a bounded
provider-latency characterization.

## Scientific question

Using unchanged Qualification 006 provider and probe semantics, is the
45-second headroom violation absent, intermittent, recurrent, or accompanied
by provider-path instability across a predetermined fresh observation window?

## Frozen observation population

- 12 cycles
- 3 probes per cycle
- 36 total fresh observations
- 12 observations per probe
- zero retries
- no replacement requests

The three probe orders rotate so each probe occupies each within-cycle
position exactly four times.

## Provider envelope

- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- reference headroom: 45 seconds
- request pacing: 4 seconds
- inter-cycle pacing: 10 seconds

## Historical Qualification 006 evidence

Qualification 006 observations are historical context only.

They are excluded from the Latency Stability 001 primary analysis population
and are not reused as fresh observations.

## Classification

Precedence:

1. `PROVIDER_PATH_UNSTABLE`
2. `FREQUENT_HEADROOM_VIOLATION`
3. `INTERMITTENT_HEADROOM_VIOLATION`
4. `STABLE_WITHIN_FROZEN_HEADROOM`

Any provider error, timeout, response mismatch, or invalid marker yields
`PROVIDER_PATH_UNSTABLE`.

If all 36 observations are accepted and marker-valid:

- 4 or more above 45 seconds → `FREQUENT_HEADROOM_VIOLATION`
- 1–3 above 45 seconds → `INTERMITTENT_HEADROOM_VIOLATION`
- zero above 45 seconds → `STABLE_WITHIN_FROZEN_HEADROOM`

## Non-authorization boundary

This characterization cannot:

- retroactively change Qualification 006;
- authorize Ontology 006;
- revise the 45-second threshold;
- automatically authorize Qualification 007 or another qualification.

Any future qualification requires a separate preregistered work order after
this characterization closes.

## Claim ceiling

This work order can establish only bounded descriptive latency evidence for
one endpoint/model under the frozen 36-observation window.

It establishes no semantic result, Ontology 006 result, canonical
institutional meaning, institutional authority, production readiness,
architecture change, cross-provider generalization, or independent
validation.
