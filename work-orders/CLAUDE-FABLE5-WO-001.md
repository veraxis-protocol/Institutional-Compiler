# Claude Fable 5 — Work Order 001

**Role:** Reference implementation lead  
**Objective:** Produce the non-semantic repository and CI foundation without bypassing the contract freeze.

## Execute

1. Review TDD-OIC-001 v1.1, `INVARIANTS.md`, and every draft schema.
2. Bootstrap a Python 3.12 modular monolith with:
   - `pyproject.toml`
   - Ruff
   - mypy strict mode
   - pytest
   - JSON Schema validation
   - pre-commit
   - GitHub Actions
3. Add schema validation tests for every file in `schemas/draft`.
4. Add deterministic artifact hashing utilities.
5. Add typed error taxonomy but no LLM extraction logic yet.
6. Add a CLI shell:
   - `oic validate-schema`
   - `oic verify-manifest`
   - `oic doctor`
7. Add Docker Compose shell for PostgreSQL, MinIO, and OPA, pinned by digest where feasible.
8. Produce PR evidence:
   - commands
   - environment
   - test output
   - SBOM draft
   - rollback
   - limitations impact

## Prohibited

- Do not implement direct document-to-Rego generation.
- Do not add auto-admission.
- Do not collapse unknown into false.
- Do not make ZTL or VEIP calls before their interfaces are frozen.
- Do not select a model provider as a semantic dependency.
- Do not alter the schema without an ADR.

## Acceptance

All checks run locally from a clean clone. No semantic module behavior is claimed.
