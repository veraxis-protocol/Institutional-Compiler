# Project Status

## Current status

**OWNER-AUTHORIZED BOUNDED SEMANTIC IMPLEMENTATION — PRE-EXTERNAL-REVIEW**

Owner Decision 004 authorizes only the provider-neutral model boundary, NVIDIA NIM
adapter, candidate-only extraction boundary, deterministic review docket, and their
engineering tests. Model output has no authority or admission rights.

It does not authorize public quality, enterprise-readiness, legal-compliance, universal-novelty, or superiority claims.

## Exploratory code-start gate

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

**Bounded semantic implementation:** OWNER-AUTHORIZED by
[`OIC-OWNER-DECISION-004.md`](docs/decisions/OIC-OWNER-DECISION-004.md).

Open Run execution, automatic institutional admission, Institutional IR, Open Control
Envelope, Rego, runtime ALLOW/DENY, ZTL execution, and VEIP execution remain **NOT
AUTHORIZED**. Global repository completeness remains **INCOMPLETE**.

Infrastructure scaffolding and schema validation may proceed before that gate.
