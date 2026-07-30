# ZTL–VEIP Boundary Preflight v0.1

> **PROPOSED — NOT YET OWNER-ATTESTED**

This memo organizes a provisional handoff for architecture review. It does not decide ZTL or VEIP
semantics, define an executable adapter, freeze an interface, or authorize integration.

## Proposed ZTL endpoint

ZTL ends with:

- logical disposition;
- warranty grade;
- formula;
- dependencies;
- missing grounds;
- caller-supplied epoch identifiers and freshness inputs, echoed or
  referenced by ZTL for OIC-side evaluation; ZTL originates no epoch,
  clock, freshness authority, or institutional time authority;
- recomputation evidence.

The ZTL result remains evidence about a logical/warranty boundary. This memo does not permit a raw
verdict to be converted directly into a consequential runtime decision.

## Proposed VEIP start

VEIP begins with:

- proposed consequential action;
- binding to an admitted control;
- runtime execution disposition;
- execution;
- evidence recording;
- reliance;
- revocation propagation;
- correction.

## Proposed handoff questions

Before owner attestation, the following must remain explicit and unresolved:

1. Which ZTL fields are mandatory for a VEIP action proposal?
2. What identifies the admitted OIC control, its version, authority, and active lifecycle state?
3. How does `OPEN` or missing ground constrain VEIP classification without becoming false or DENY?
4. Which epoch/freshness authority controls execution and later replay?
5. What recomputation evidence is embedded, referenced, or independently retrievable?
6. What is the difference between a proposed action, runtime-decision input, decision output,
   execution record, and Evidence Pack?
7. Who may record reliance, and what must happen when the relied-on basis expires, is revoked, or
   is corrected?
8. How are downstream records located and propagation completion or failure represented?
9. Which replay meaning is authoritative: logical recomputation, decision recomputation, integrity
   verification, or a composition of separately named operations?
10. Which failures escalate, prevent execution, invalidate reliance, or require owner review?

## Provisional responsibility table

| Concern | ZTL side | VEIP side | Status |
|---|---|---|---|
| Logical disposition and warranty | Produces disposition, grade, formula, dependencies, missing grounds, and recomputation evidence; may echo caller-supplied epoch identifiers but originates no epoch, clock, freshness authority, or institutional time. | Consumes only through an owner-attested contract | Proposed |
| Admitted-control binding | Does not establish OIC admission | Binds a proposed action to an already admitted control | Proposed; OIC admission contract not defined here |
| Runtime disposition | Does not execute consequential action | Classifies runtime execution under the attested VEIP contract | Proposed; no current OIC authorization |
| Execution and record | No execution ownership | Executes only after authorized disposition and records evidence | Proposed; current Evidence Pack is not attested as sufficient |
| Reliance | Warranty evidence may be an input | Records and governs consequential reliance | Proposed; behavior absent in inspected repositories |
| Revocation/correction | Supplies changed logical/warranty evidence | Propagates lifecycle effects to executions, records, and reliance | Proposed; behavior absent in inspected repositories |
| Replay | Supplies logical recomputation evidence | Must name decision replay and integrity verification separately | Proposed; current repository meanings conflict |

## Required owner attestations

Arkadiy Miteiko must attest or reject:

- the boundary itself;
- the canonical VEIP repositories and pins;
- proposal and decision input shapes;
- admitted-control binding;
- execution-record sufficiency;
- reliance, expiry, revocation, and correction semantics;
- replay terminology and required bindings;
- failure and escalation behavior;
- replacement/fallback behavior.

GPT-5.6 Thinking reviews the architecture. Claude Fable 5 may prepare supporting implementation
and dossier material but may not independently change VEIP semantics or lifecycle commitments.

## Non-authorization

This memo authorizes no Docling or LLM extraction, admission, Institutional IR construction,
Open Control Envelope generation, ZTL or VEIP adapter execution, Rego generation, or runtime
ALLOW/DENY evaluation. It does not modify OIC schemas or status. The semantic implementation gate
remains **BLOCKED**.
