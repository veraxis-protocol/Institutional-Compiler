# Agent operating boundary

This repository is in **OWNER-AUTHORIZED BOUNDED SEMANTIC IMPLEMENTATION —
PRE-EXTERNAL-REVIEW** under `docs/decisions/OIC-OWNER-DECISION-004.md`. The only
authorized semantic scope is the provider-neutral model layer, NVIDIA NIM adapter,
candidate-only extraction boundary, deterministic review docket, and corresponding
engineering tests. Model output has no authority or admission rights.

Open Run execution, institutional admission, Institutional IR, Open Control Envelope,
Rego, runtime ALLOW/DENY, ZTL execution, and VEIP execution remain unauthorized.

## Safe commands

After installing the hash-locked environment described in
`docs/operations/CI.md`, agents may run:

```bash
make verify
make falsify
pytest
ruff check .
ruff format --check .
mypy
bash scripts/generate_sbom.sh
bash scripts/wheel_smoke_test.sh
```

Implemented CLI commands remain limited to `oic validate-schema`,
`oic verify-bootstrap`, `oic verify-manifest`, and `oic doctor`. They verify
infrastructure contracts only. Do not invent semantic commands, hosted APIs,
gateways, remote context services, or MCP servers.

## Role separation

Producer, verifier, and adjudicator must be distinct. A producer may run checks
and report literal evidence, but must state **NOT SELF-ADJUDICATED** and stop for
independent verification. CI PASS is not owner acceptance and cannot open the
semantic gate.

## Claims and licensing

Follow `CLAIMS.md`, `LIMITATIONS.md`, and `STATUS.md` literally. This repository
is licensed under the PolyForm Noncommercial License 1.0.0. Do not describe it
as open source or imply commercial-use rights; commercial use requires a
separate written license from Veraxis.

## Telemetry and provenance

Local package import, CLI, tests, and SBOM generation have no telemetry feature.
The test suite blocks outbound sockets. GitHub commits, pull requests, reviews,
and checks are observable transport events; local reads and reasoning are dark.

Optional contribution trailers:

```text
Agent-Assisted-By: <system and model>
Veraxis-Skill: <skill or workflow name>
Agent-Execution-ID: <optional attributable execution identifier>
```

Trailers are supplemental provenance, not institutional authority or
independent review.
