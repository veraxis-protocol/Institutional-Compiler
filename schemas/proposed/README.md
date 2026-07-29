# Proposed schemas

**PROPOSED. Not admitted. Nothing validates institutional data against these.**

`schemas/draft/` holds the nine bootstrap contract schemas. They are **Class B governed
contracts** under [ADR-012](../../adr/ADR-012.md): they change only through an explicit
pull request with owner review, a stated reason, compatibility impact, tests, and an ADR
where material.

This directory is where a schema lives *before* that happens. Placing a proposal here
means it can be written, reviewed, and tested without touching a governed contract — and
without a reader mistaking a proposal for something admitted.

| Schema | Purpose | Would supersede |
|---|---|---|
| `warrant-artifact.schema.json` | Recomputable record of what a logic kernel established over supplied grounds | nothing; new |
| `runtime-decision.schema.json` | Separates epistemic status, execution disposition, and decision basis | `schemas/draft/runtime-evaluation.schema.json` |

Governing decision: [ADR-013](../../adr/ADR-013.md).
Contract: [`docs/contracts/WARRANT-CONTRACT-v0.1.md`](../../docs/contracts/WARRANT-CONTRACT-v0.1.md).
Fixtures: [`tests/fixtures/warrant-contract/`](../../tests/fixtures/warrant-contract/).

## Promotion

A schema moves from `proposed/` to `draft/` only by explicit owner decision. Promotion is a
Class B change and needs its own pull request; it is **not** implied by merging the
proposal. Until then `schemas/draft/` is authoritative and unchanged, and the nine schemas
there remain byte-identical to the bootstrap commit — asserted by
`tests/contract/test_warrant_contract.py`.

## Validation

These are validated as JSON Schema Draft 2020-12 offline, exactly like the draft set:

```bash
oic validate-schema --schema-dir schemas/proposed
```

The `test` CI job covers them too, so a malformed proposal fails the build rather than
waiting for someone to run the command by hand.
