# Agent operating boundary

This repository includes an owner-opened, bounded semantic candidate-extraction
slice defined by `docs/decisions/OIC-OWNER-DECISION-004.md`. No agent may claim
general document interpretation, institutional admission,
Open Control Envelope generation, Rego compilation, or runtime semantic
decisions under this work order.

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

The only authorized semantic production path is
`src/oic/candidate_extraction.py`, limited to the three synthetic Northstar
sources. Implemented CLI commands are limited to `oic validate-schema`,
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
