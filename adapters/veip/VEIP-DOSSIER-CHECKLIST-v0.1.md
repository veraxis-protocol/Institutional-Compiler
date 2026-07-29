# VEIP Dossier Checklist v0.1

**Status: PREFLIGHT — INCOMPLETE — NOT AN INTERFACE FREEZE**

Allowed field states:
`PRESENT`, `PARTIAL`, `ABSENT`, `CONFLICTING`, `REQUIRES OWNER ATTESTATION`.

| # | Required dossier field | State | Evidence and gap |
|---:|---|---|---|
| 1 | Canonical repositories | **REQUIRES OWNER ATTESTATION** | Four repository candidates are inventoried at exact SHAs. Arkadiy must attest that this is the authoritative set and identify any excluded or superseding repositories. |
| 2 | Owner | **PRESENT** | OIC-OWNER-DECISION-002 designates Arkadiy Miteiko as interim VEIP contract owner; Claude Fable 5 provides support and GPT-5.6 Thinking reviews architecture. |
| 3 | License | **CONFLICTING** | `veip-spec` is CC-BY-4.0; SDK has complete MIT text; Verifier Core uses a custom `NOASSERTION` license whose commercialization narrative needs review; Registry declares MIT but contains only a 12-byte label. Compatibility is not established. |
| 4 | Immutable versions | **PARTIAL** | Exact commit evidence pins exist, but no repository has a tag or GitHub release and the pins are not owner-attested interface versions. |
| 5 | Lifecycle interface | **REQUIRES OWNER ATTESTATION** | A small state-transition model exists. Expiry, revocation, correction, reliance, and OIC/VEIP lifecycle commitments are not defined. |
| 6 | Action-proposal input | **PARTIAL** | SDK has `ActionProposal(action_type, payload)` and the Evidence Pack has an `action` object. There is no canonical proposal-input schema or complete validation contract. |
| 7 | Runtime-decision input | **ABSENT** | A decision output object and classification enum exist; no separate runtime-decision input contract was found. |
| 8 | Evidence-pack schema | **PRESENT** | Draft 2020-12 schema is byte-identical across all located copies; SHA-256 `3ff025de2c91737e84aceae529e2da78a86622a26f7f5998b73ed880c15ebbf0`. Presence is not a freeze. |
| 9 | Execution-record schema | **PARTIAL** | The Evidence Pack contains an `execution` object, but no standalone execution-record schema, lifecycle event model, or correction/revocation chain exists. |
| 10 | Replay behavior | **CONFLICTING** | Spec/SDK replay recomputes classification; Verifier Core replay verifies an optional hash carrier and passes an unbound pack unless binding is required. |
| 11 | Reliance behavior | **ABSENT** | No consumer reliance contract, reliance record, invalidation behavior, or downstream obligation was found. |
| 12 | Expiry behavior | **ABSENT** | Validity timestamps exist, but no expiry transition, execution effect, replay effect, or downstream propagation behavior is defined. |
| 13 | Revocation propagation | **ABSENT** | No revocation event, propagation graph, affected-record query, or downstream invalidation behavior was found. |
| 14 | Correction behavior | **ABSENT** | No correction/supersession event, linkage, audit-chain, or replay rule was found. |
| 15 | Failure behavior | **CONFLICTING** | Verifier CLI exit codes are explicit. SDK largely raises exceptions. Registry threat documentation claims 409/404 behavior not implemented by the inspected storage/error paths. Cross-layer failure semantics are not unified. |
| 16 | Fixtures | **PARTIAL** | Verifier Core and Registry each track one Evidence Pack fixture; SDK uses generated test objects; `veip-spec` has no populated normative CTS vectors. |
| 17 | Conformance command | **PARTIAL** | Repositories expose `make check` or `make ci`, but there is no consolidated pinned command. Latest `veip-spec` main CI fails and its logs have expired. |
| 18 | Security notes | **PARTIAL** | Layer-specific notes exist, including substantial explicit omissions. There is no consolidated security model, independent assessment, or OIC integration threat model. |
| 19 | Known limitations | **PARTIAL** | Working-draft, cryptographic, storage, registry, security, and hardening limitations are scattered across repositories; no owner-attested consolidated limitation register exists. |
| 20 | Replacement strategy | **PARTIAL** | Registry operator replaceability is stated conceptually, and repositories cross-reference other layers. No operational migration, fallback, export, failover, or continuity procedure exists. |

## Fields needing Arkadiy Miteiko's attestation or decision

At minimum:

- authoritative repository set and immutable version pins;
- scope and authority of each layer;
- lifecycle interface;
- action-proposal and runtime-decision boundary;
- whether the Evidence Pack execution object is an execution record or only part of one;
- canonical meaning of replay;
- reliance, expiry, revocation, and correction behavior;
- unified failure semantics;
- acceptable fixture/conformance package;
- replacement/fallback strategy;
- resolution path for licensing evidence and compatibility.

Attestation must not be inferred from repository ownership, README language, package metadata, or
this inventory.

## Gate impact

The checklist is incomplete. It supplies preflight evidence to OIC-GC-004 and does not close that
issue. It does not authorize VEIP implementation or integration. The OIC semantic implementation
gate remains **BLOCKED**.
