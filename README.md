# Open Institutional Compiler

**Status:** OWNER-AUTHORIZED BOOTSTRAP — PRE-EXTERNAL-REVIEW  
**Bootstrap date:** 2026-07-29  
**Governing design:** TDD-OIC-001 v1.1

Open Institutional Compiler (OIC) is an open reference implementation for converting inherited institutional documents into source-anchored candidate meaning, exposing ambiguity and conflict, recording scoped institutional admission, generating portable Open Control Envelopes, compiling them to runtime targets, and preserving source-to-execution-to-correction lineage.

**What exists now:** a tested, non-semantic Python infrastructure package for
offline schema validation, historical bootstrap verification, current manifest
verification, environment/gate diagnostics, and reproducible CI/SBOM checks.
It is not a functioning institutional compiler.

**What is blocked:** semantic implementation remains blocked pending the corpus
provenance and ZTL/VEIP interface evidence listed in `STATUS.md`. This alignment
does not open that gate or upgrade maturity.

Run the safe non-semantic checks after the hash-locked installation in
`docs/operations/CI.md`:

```bash
make verify
make falsify
```

## Current phase

This repository scaffold authorizes contract-first exploratory implementation only. It does not claim enterprise readiness, autonomous legal interpretation, legal compliance, market-wide novelty, or superiority over other systems.

No semantic implementation may be merged until the code-start gate in `STATUS.md` is satisfied.

## First executable objective

A bounded procurement corpus must flow through:

`documents → source anchors → candidate normative units → review docket → admitted record → Open Control Envelope → Rego → ALLOW/DENY/CANNOT → lineage`

## Governing invariants

See `docs/requirements/INVARIANTS.md`.

## Public limitations

See `LIMITATIONS.md`.

## Claims discipline

See `CLAIMS.md`.
