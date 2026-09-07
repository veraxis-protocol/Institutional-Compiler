# Project Status

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

Pull request 41 subsequently merged candidate
`4576fea067d33c2c0f8e8fc2d49bb506c52b2f1c`, tree
`6e450750d7b6b1d1f0b493b050ed7d866d42b264`, into `main` as merge commit
`8ebac66965997748061d8cc0f1bfde73cb7b216a`, first parent
`c4a325c551ce8904dfcc5b9fe81b05109726a334`. That candidate changes claim-control
text only: it adds the subject term `implementation` to the README unscoped-claim
alternation and adds the matching case to the internal regression tuple, closing
SAK001C-F01/SAK001-F01 pending independent confirmation. It changes no runtime,
verifier, matrix, benchmark or claim content, and the merged tree is byte-identical
to the candidate tree. Independent review does not cover merge commit
`8ebac66965997748061d8cc0f1bfde73cb7b216a` or candidate
`4576fea067d33c2c0f8e8fc2d49bb506c52b2f1c`; the Gate F and Gate G results above
remain scoped to the exact earlier candidates that produced them.

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

## Bounded results established, and what they are not

Nothing in OIC-Bench has been measured. Every figure below is repository or
bounded-implementation evidence, scoped to the exact candidate that produced it.
All eight preregistered OIC-Bench rows in `README.md` remain TARGET - NOT MEASURED,
and the provisional comparative target remains PROVISIONAL TARGET - NOT MEASURED -
NOT CALIBRATED.

- Independent Gate F repository validation, candidate
  `c0108a7a80585d6f5732407d4904ba815073ecd2`, tree
  `1d12b17aad7977c939090909171183be166cfd50`: 1714 passed, 0 failed, 0 errors,
  1 declared skip, 93.5% coverage.
- Independent Gate G validation, candidate
  `a2b5053771ce510fb35ce09f3e99f545c21ac20e`, tree
  `b8e31ec4786a2fd1aca976a6ff047deeee63ef15`: 1720 passed, 0 failed, 0 errors,
  1 declared skip, 93.5% coverage, zero critical and zero major findings.
- Deterministic offline path, candidate
  `c0108a7a80585d6f5732407d4904ba815073ecd2`, tree
  `1d12b17aad7977c939090909171183be166cfd50`, and again at candidate
  `a2b5053771ce510fb35ce09f3e99f545c21ac20e`, tree
  `b8e31ec4786a2fd1aca976a6ff047deeee63ef15`: two separate-process runs emit
  byte-identical canonical JSON, SHA-256
  `0f9d01bb0dfc488505e027ac7bd8aecf869578e379b5a977cd9d642f2101a39a`. At the
  second of those candidates both runs executed with no network interfaces and no
  DNS available.
- Bounded synthetic path composition, candidate
  `a2b5053771ce510fb35ce09f3e99f545c21ac20e`, tree
  `b8e31ec4786a2fd1aca976a6ff047deeee63ef15`: one synthetic fictional sentence
  yields two divergent candidate units, eleven provisional interpretation slots,
  one preserved unresolved reference, one supplied synthetic authority record, and
  three refusal paths, with institutional admission false. These are counts from a
  single fixture, not a source-support rate, an ambiguity measurement, or any other
  benchmark quantity.
- Infrastructure verification, candidate
  `a2b5053771ce510fb35ce09f3e99f545c21ac20e`, tree
  `b8e31ec4786a2fd1aca976a6ff047deeee63ef15`: schemas 9/9, bootstrap 52/52,
  falsification harness 4/4, and manifest verification deliberately INCOMPLETE at
  exit 3.

Test counts measure the test suite. They do not measure whether compiled controls
behave correctly, and they are not benchmark results. Within the authorized OIC evidence universe examined by
OIC-NIM-EVIDENCE-CROSSWALK-001 as of 2026-09-07, no practitioner study, baseline
arm, human-time instrumentation or adjudicated behavioural-quality scale is
present, so no comparative statement is supported from that evidence. That is a
statement about that bounded evidence set on that date, not a claim about any
work outside it.

The reference path does not confer real institutional authority or runtime permission.
After this work order, another deposited authorization plus explicit execution signal is required.
