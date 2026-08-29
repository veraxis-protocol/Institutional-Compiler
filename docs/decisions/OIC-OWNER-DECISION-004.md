# OIC Owner Decision 004 — First bounded semantic implementation

- Decision date: 2026-08-28
- Authorized base: `914830ceec70bde17004d2ccbbb13218ca44a89b`
- Scope: `BOUNDED SEMANTIC CODE START`
- Gate disposition: `OPEN` for the scope below only
- Authorized production path: `src/oic/candidate_extraction.py`
- Authorized sources: `SYN-NS-GOV-1`, `SYN-NS-PROC-1`, `SYN-NS-AMEND-2`

## Exact owner authorization

> I authorize the OIC semantic code-start gate to OPEN on
> Institutional-Compiler main at exact commit
> 914830ceec70bde17004d2ccbbb13218ca44a89b.
>
> This authorization permits bounded semantic implementation under
> TDD-OIC-001 v1.1 and the admitted gate constraints.
>
> It does not authorize institutional admission, runtime authorization,
> OCE execution, Rego/OPA execution, ZTL runtime integration, VEIP runtime
> integration, production claims, or benchmark claims unless separately
> authorized.

## Authorization boundary

- First authorized semantic production path: `src/oic/candidate_extraction.py`
- Authorized source IDs: `SYN-NS-GOV-1`, `SYN-NS-PROC-1`, `SYN-NS-AMEND-2`
- CA-3 semantic extraction: `NOT AUTHORIZED`
- Institutional admission: `NOT AUTHORIZED`
- Institutional IR: `NOT AUTHORIZED`
- OCE generation or execution: `NOT AUTHORIZED`
- Rego/OPA: `NOT AUTHORIZED`
- ZTL runtime: `NOT AUTHORIZED`
- VEIP runtime: `NOT AUTHORIZED`
- Production claims: `NOT AUTHORIZED`
- Benchmark claims: `NOT AUTHORIZED`

Candidate output remains extracted, uncertain, unadmitted, and without machine
confidence. The stale procedure remains visible as superseded. Network/model/API
dependencies and licensing or corpus-rights changes are not authorized. Global
manifest completeness remains `INCOMPLETE`.

This decision does not permit the evaluator or implementation to extend its own
scope. Further semantic paths or sources require a separate owner decision.
