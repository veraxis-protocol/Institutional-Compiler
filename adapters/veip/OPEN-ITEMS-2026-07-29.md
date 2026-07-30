# VEIP Preflight Open Items — 2026-07-29

**Status: OPEN PREFLIGHT ITEMS — NOT OWNER-ATTESTED**

## Ownership boundary

- Interim VEIP contract owner: Arkadiy Miteiko / Veraxis.
- Implementation/dossier support: Claude Fable 5.
- Architecture review: GPT-5.6 Thinking.
- Codex role: mechanical evidence collection and inventory only.

## Open items

| ID | Open item | Evidence needed | Next authority/actor | Gate effect |
|---|---|---|---|---|
| VEIP-OI-001 | Attest canonical repository set | Owner statement identifying authoritative, excluded, replaced, or additional VEIP repositories | Arkadiy | Blocks dossier identity |
| VEIP-OI-002 | Attest immutable versions | Signed or otherwise owner-controlled pins, tags/releases, schema fingerprint, and version relationship | Arkadiy | Blocks interface versioning |
| VEIP-OI-003 | Resolve license evidence | Complete Registry license text; qualified interpretation of Verifier Core terms; compatibility matrix across all four layers | Arkadiy plus qualified licensing reviewer | Blocks compatibility finding |
| VEIP-OI-004 | Define lifecycle interface | Owner-reviewed states/events for proposal, binding, decision, execution, reliance, expiry, revocation, correction, and replay | Arkadiy; GPT-5.6 Thinking review | Blocks lifecycle contract |
| VEIP-OI-005 | Define action-proposal input | Canonical schema, required identifiers, admitted-control binding, context, authority, time, and failure behavior | Arkadiy; Claude support | Blocks input contract |
| VEIP-OI-006 | Define runtime-decision input | Clarify whether VEIP consumes a proposed action, OIC envelope result, admitted-control warrant, or another artifact | Arkadiy; GPT-5.6 Thinking review | Blocks OIC/VEIP boundary |
| VEIP-OI-007 | Define execution record | Decide whether the current Evidence Pack `execution` object is sufficient; specify event identity, ordering, supersession, and linkage | Arkadiy | Blocks execution evidence contract |
| VEIP-OI-008 | Reconcile replay meanings | Resolve decision recomputation versus optional integrity-carrier verification; define required inputs and failure result | Arkadiy; architecture review | Blocks conformance mapping |
| VEIP-OI-009 | Define reliance | Consumer, reliance act, relied-on record, permitted use, invalidation, and downstream duties | Arkadiy | Blocks reliance contract |
| VEIP-OI-010 | Define expiry | Clock/epoch authority, expiry event, grace behavior, replay effect, and downstream propagation | Arkadiy | Blocks lifecycle contract |
| VEIP-OI-011 | Define revocation propagation | Revocation source, affected records/actions, ordering, fan-out, acknowledgement, and failure behavior | Arkadiy | Blocks lifecycle contract |
| VEIP-OI-012 | Define correction | Correction/supersession event, immutable linkage, affected reliance, replay, and audit treatment | Arkadiy | Blocks lifecycle contract |
| VEIP-OI-013 | Reconcile failure behavior | Align SDK exceptions, Verifier exit codes, Registry HTTP behavior, and OIC escalation semantics | Arkadiy; architecture review | Blocks conformance contract |
| VEIP-OI-014 | Repair or explain Registry mismatch | Reconcile claimed duplicate-409/missing-404 behavior with uncaught `KeyError` paths; add evidence tests in VEIP repository under separate authority | VEIP repository owner/support | Evidence gap; no OIC code change authorized |
| VEIP-OI-015 | Restore `veip-spec` CI evidence | Determine current failure cause and produce a green pinned-head run or an owner-accepted deviation record | VEIP repository owner/support | Blocks clean conformance evidence |
| VEIP-OI-016 | Publish normative fixtures | Version-bound authority, proposal, decision, transition, Evidence Pack, replay, failure, expiry, revocation, and correction vectors | VEIP owner/support | Blocks conformance package |
| VEIP-OI-017 | Define consolidated conformance command | Reproducible clean-environment command, pinned dependencies, expected exit codes, raw results, and artifact hashes | VEIP owner/support | Blocks reproduction |
| VEIP-OI-018 | Consolidate security model | Threats, trust boundaries, time, signing, key management, storage, authn/authz, abuse, availability, and recovery | Arkadiy; security reviewer | Blocks security finding |
| VEIP-OI-019 | Define replacement/fallback | Discovery, export, migration, failover, operator continuity, schema/version negotiation, and evidence preservation | Arkadiy | Blocks replacement strategy |
| VEIP-OI-020 | Remove or justify tracked generated artifacts | `.DS_Store`, bytecode, `__pycache__`, and egg metadata appear in VEIP repositories | VEIP repository owners | Hygiene/evidence reproducibility gap |

## Explicit non-actions

These open items do not authorize:

- modification of any VEIP repository;
- VEIP import or adapter execution in OIC;
- a schema or lifecycle decision by support agents;
- interface freeze;
- dossier completion;
- license publication;
- change to `STATUS.md`;
- opening the semantic implementation gate.

## Gate impact

OIC-GC-004 remains open. The semantic implementation gate remains **BLOCKED**.
