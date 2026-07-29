# Project Status

## Current status

**OWNER-AUTHORIZED BOOTSTRAP — PRE-EXTERNAL-REVIEW**

This status authorizes repository creation, contract drafting, fixture preparation, dependency verification, benchmark preflight design, and non-semantic infrastructure scaffolding.

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

**Semantic implementation gate:** BLOCKED until the preflight corpus manifest and ZTL/VEIP provisional-interface records are completed.

Infrastructure scaffolding and schema validation may proceed before that gate.
