# Agent operating boundary

This repository contains infrastructure and the owner-admitted synthetic reference
path under OIC-SEMANTIC-PROMOTION-001. That work order alone permits its exact 58-path
maximum on `oic-weekly-convergence-2026-09-03`. The active capability matrix records
the bounded surface; it cannot authorize its own extension. No later work is authorized
by this file. After return, wait for a new deposited WO and explicit execution signal.
The broader production semantic gate remains **BLOCKED** by `STATUS.md`. No Open Control
Envelope generation, Rego compilation, real corpus fetch, live provider call, production
runtime decision, rights expansion, or merge to main is authorized by this promotion.

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

Implemented CLI commands are limited to `oic validate-schema`,
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
