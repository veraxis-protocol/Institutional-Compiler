# Project Status

## OIC↔ZTL boundary — 2026-09-07

Gate G promotion is recorded in the section below. This block adds what it does not say:
**where the boundary with ZTL is, and why nothing crosses it yet.**

On `main` today: **bounded candidate admission** and **provisional interpretation** are
present. Separately, **ZTL reasoning and warrant semantics have materially matured** well
beyond the July dossier in `adapters/ztl/` — a statement about the dependency, not a claim
that OIC uses it.

Between those two matured sides, three institutional transitions **do not exist**:

    institutional semantic admission
      → stable admitted proposition
        → evidence-bearing formalization

Therefore: semantic implementation has not started, the broader production semantic gate
remains **BLOCKED**, and **ZTL runtime attachment remains BLOCKED** — the institutional
semantic act that would produce an admitted canonical proposition does not exist, so there is
no lawful input for a logic kernel. Neither side maturing makes that blockage smaller.

The boundary is described in `docs/architecture/OIC-ZTL-MATURATION-DELTA-001.md` and
`docs/architecture/OIC-ZTL-LAYER-OWNERSHIP-001.md`; the current dependency state in
`adapters/ztl/CURRENT-STATE-001.md`; the falsifiability hierarchy in
`docs/darpa/OIC-ZTL-DARPA-CROSSWALK-001.md`.

No semantic correctness, runtime authorization, institutional validity, or independent
reproduction is established by this block. `tier_1_reproduction` remains **NOT ESTABLISHED**.

## Current status

**BOUNDED_REFERENCE_IMPLEMENTATION — SCOPED INDEPENDENT GATE G VALIDATION PASSED AND MERGED TO MAIN**

OIC-SEMANTIC-PROMOTION-001 admits only the 58-path maximum recorded in
`docs/capabilities/CAPABILITY_MATRIX.json`, from main
`9ad37fc80d8f34318c6212ed702de5eab3551cf5`. It implements an offline synthetic
reference path, not production compilation, runtime authorization, or canonical meaning.

Independent Gate F repository validation passed for exact candidate
`c0108a7a80585d6f5732407d4904ba815073ecd2`, tree
`1d12b17aad7977c939090909171183be166cfd50`. Canonical Linux execution reported
1714 passed, 0 failed, 0 errors, 1 declared skip, 93.5% coverage, and two
byte-identical offline demo runs with SHA-256
`0f9d01bb0dfc488505e027ac7bd8aecf869578e379b5a977cd9d642f2101a39a`. The result
establishes reproducibility, boundary integrity, the specified fail-closed
properties, packaging, and named adversarial checks for that candidate only. It
is not validation of any later commit.

Independent Gate G validation passed for exact candidate
`a2b5053771ce510fb35ce09f3e99f545c21ac20e`, tree
`b8e31ec4786a2fd1aca976a6ff047deeee63ef15`. Canonical Linux execution reported
1720 passed, 0 failed, 0 errors, 1 declared skip
(`tests/contract/test_canada_acquisition_preflight.py:574`), 93.5% coverage, and
two byte-identical offline demo runs with SHA-256
`0f9d01bb0dfc488505e027ac7bd8aecf869578e379b5a977cd9d642f2101a39a`. Pull request
40 merged that exact tree into `main` as merge commit
`c4a325c551ce8904dfcc5b9fe81b05109726a334`, first parent
`9ad37fc80d8f34318c6212ed702de5eab3551cf5`, second parent
`a2b5053771ce510fb35ce09f3e99f545c21ac20e`, approved by `inventor1975` at
2026-09-06T08:12:51Z and merged at 2026-09-06T08:14:03Z. The merged tree is
byte-identical to the validated tree. Each result above is scoped to the exact
commit and tree that produced it and to nothing later.

NVIDIA: NOT_QUALIFIED and excluded from the demo. Canada redistribution: UNRESOLVED.
Ontology 007R1: unexecuted and execution-unauthorized. Institutional-IR closure:
UNESTABLISHED. Production compilation and runtime authorization: UNESTABLISHED. Negative-stability
live outcome: DEFERRED. Existing SOURCE_MANIFEST.csv remains unchanged and entry-scoped.

It does not establish semantic correctness, model accuracy, institutional validity,
legal effect, provider qualification, rights resolution, ontology execution,
production compilation, runtime authorization, institutional-IR closure, enterprise
readiness, or benchmark superiority. It also does not establish legal validity,
production readiness, public quality, universal novelty, or legal compliance.

## Historical bootstrap exploratory code-start gate

| Gate | Status | Required evidence |
|---|---|---|
| TDD-OIC-001 v1.1 checked in | PASS in bootstrap bundle | PDF + SHA-256 |
| Requirement IDs and invariants checked in | PASS in bootstrap bundle | `docs/requirements/` |
| Draft schemas explicit | PASS in bootstrap bundle | `schemas/draft/` |
| Dependency status explicit | PARTIAL | `DEPENDENCIES.md`; ZTL/VEIP dossiers open |
| Preflight corpus rights/provenance documented | OPEN | completed `SOURCE_MANIFEST.csv` |
| Claims categories and forbidden claims checked in | PASS | `CLAIMS.md` |
| Public Lab restrictions visible before upload | PASS as specification | `LIMITATIONS.md`, `docs/architecture/LAB_RESTRICTIONS.md` |
| Named owner for each implemented module | PASS for kickoff | `OWNERS.md` |

**Broader production semantic gate:** BLOCKED. Historical NOT OPEN receipts remain
unchanged; the active capability matrix supersedes only the bounded synthetic surface.

The reference path does not confer real institutional authority or runtime permission.
After this work order, another deposited authorization plus explicit execution signal is required.
