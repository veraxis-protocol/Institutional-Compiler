# OIC Owner Decision 004 — First bounded semantic implementation

- Decision date: 2026-08-28
- Authorized base: `914830ceec70bde17004d2ccbbb13218ca44a89b`
- Gate disposition: `OPEN` for the scope below only
- Authorized production path: `src/oic/candidate_extraction.py`
- Authorized sources: `SYN-NS-GOV-1`, `SYN-NS-PROC-1`, `SYN-NS-AMEND-2`

The owner authorizes a deterministic, source-anchored Source → Candidate
Normative Unit implementation for the three synthetic Northstar sources only.
Candidate output remains extracted, uncertain, unadmitted, and without machine
confidence. The stale procedure must remain visible as superseded.

Institutional admission, Institutional IR, Open Control Envelope generation,
Rego or other policy-target generation, runtime authorization, OPA/Cedar/
OpenFGA/Cerbos invocation, ZTL runtime integration, VEIP runtime integration,
CA-3 semantic extraction, network/model/API dependencies, production claims,
benchmark claims, and licensing or corpus-rights changes are not authorized.
Global manifest completeness remains `INCOMPLETE`.

This decision does not permit the evaluator or implementation to extend its own
scope. Further semantic paths or sources require a separate owner decision.
