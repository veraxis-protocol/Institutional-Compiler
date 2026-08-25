# OIC Semantic Code-Start Gate Closure v0.1

Audit base: `d06917fa6877277d7118b49e80d6a69446f50712`.

This is evidence collection, not authority. `STATUS.md` remains authoritative
and unchanged. Semantic implementation remains blocked.

## Unified closure matrix

| Gate ID | Requirement | Current evidence | Exact artifact/SHA | Status | Missing evidence | Required authority/actor | Smallest next action | Gate effect |
|---|---|---|---|---|---|---|---|---|
| OIC-CS-001 | Minimum preflight source roles selected | Proposed 55-page Canada set | scope blob `cf2ce8a9…` | PARTIAL | Owner confirmation of the minimum rights-clear set | Owner | Select retained/replacement sources by role | BLOCKS SEMANTIC CODE START |
| OIC-CS-002 | Every selected source has complete manifest/provenance | Only CA-3 frozen; even CA-3 lacks date/authority dispositions | manifest `718a9df6…`; gap report | OPEN | Rights, freeze, hashes, receipts, dates, authority for selected set | Owner + rights/domain reviewers | Close gap report rows without guessed metadata | BLOCKS SEMANTIC CODE START |
| OIC-CS-003 | ZTL provisional pin and interface admitted | Strong producer evidence and v0.2 fixtures exist | ZTL README `c8170b5c…`; mapping review `0c43b0fb…` | PARTIAL | Owner admission of pin; joint mapping/failure/MissingGround/time decisions | Owner + Vitaliy | Decide a bounded provisional interface profile and required negative fixtures | BLOCKS SEMANTIC CODE START |
| OIC-CS-004 | VEIP provisional identity and boundary admitted | Inventory/checklist present, incomplete | VEIP checklist `46490bc…`; inventory `26abb9ad…` | OPEN | Canonical repos/pins/license plus minimum lifecycle, input, replay, revocation, correction, failure and fallback boundary | Owner + licensing/architecture actors + VEIP repo owners | Answer bounded decisions listed below; external actors supply missing evidence | BLOCKS SEMANTIC CODE START |
| OIC-PF-001 | Semantic preflight fixtures and conformance commands | Plans and proposed metrics exist; semantic artifacts absent by design | preflight README `3e6cf7bd…`; metrics `e5547c6d…` | OPEN | Gold annotations, runtime/change/adversarial cases, baseline harness | Authorized semantic implementers after gate opening | Execute readiness plan only after gate opens | BLOCKS PREFLIGHT EXECUTION |
| OIC-ER-001 | Independent ZTL reproduction | Author-side evidence only | dossier `72e84ec2…` | OPEN | Tier-1 reproduction | Independent reviewer | Reproduce pinned ZTL package and publish report | BLOCKS EXPERIMENTAL RELEASE |
| OIC-ER-002 | VEIP clean conformance/security evidence | Fragmented/contradictory | VEIP checklist `46490bc…` | OPEN | Green pins, normative fixtures, security record | External VEIP owners + security reviewer | Produce evidence in source repositories | BLOCKS EXPERIMENTAL RELEASE |
| OIC-RF-001 | Full OIC-Bench, held-out, usability, pilot, reliability | Not run/not established | TDD; `CLAIMS.md` | OPEN | Later maturity evidence | Independent benchmark/security/practitioner actors | Defer until bounded implementation and preflight | BLOCKS RELEASE FREEZE |

## Minimum true blocker set

The first authorized bounded semantic commit remains blocked by exactly three
closure groups:

1. **Preflight provenance minimum:** an owner-selected source set covering the
   required roles, with complete, verifiable rights/provenance/freeze and
   declared benchmark authority records.
2. **ZTL provisional interface admission:** owner acceptance of a pinned profile
   and joint resolution of mapping, MissingGround, time/revocation and
   fail-closed behavior. Tier-1 reproduction is not mechanically established;
   the owner must decide whether it remains an experimental-release blocker
   rather than a code-start blocker.
3. **VEIP provisional interface admission:** canonical identity/pins/license and
   a bounded minimum lifecycle/input/replay/revocation/correction/failure/
   fallback contract. Full maturity evidence is not required for code start.

## Bucket 1 — Codex can complete now

Completed here: repository-wide evidence discovery, blob verification,
historical open-item reconciliation, provenance gap reporting, horizon
classification, bounded authority questions, and preflight readiness planning.

## Bucket 2 — bounded authority decisions

- **OWNER DECISION OIC-GATE-01:** Which rights-clear sources are the minimum
  authorized preflight set for the required source roles, and which blocked
  CanadaBuys sources are replaced or permission-cleared?
- **OWNER/DOMAIN DECISION OIC-GATE-02:** What bounded effective-date and
  benchmark-authority disposition is authorized for CA-3 without inventing a
  legal effect date or individual delegation?
- **OWNER DECISION OIC-GATE-03:** Is ZTL v0.2 commit `56e1ff05…` the authorized
  provisional pin for bounded code start?
- **OWNER + VITALIY DECISION OIC-GATE-04:** Are the corrected disposition/grade/
  unverified mapping, 28 warrant fields, MissingGround granularity, scoped
  expiry/revocation proposal, and fail-closed negative fixtures sufficient for
  a bounded provisional interface?
- **OWNER DECISION OIC-GATE-05:** May independent Tier-1 ZTL reproduction remain
  an experimental-release blocker rather than a semantic code-start blocker?
- **OWNER DECISION OIC-GATE-06:** Which exact VEIP repositories and commits are
  the provisional dependency reference?
- **OWNER + LICENSING DECISION OIC-GATE-07:** Is the selected VEIP subset legally
  usable for bounded internal implementation, under what limitations?
- **OWNER + ARCHITECTURE DECISION OIC-GATE-08:** Approve the minimum VEIP
  lifecycle/input/replay/revocation/correction/failure/fallback contract, or
  explicitly defer VEIP semantic integration and define the substitute
  review-only boundary.

## Bucket 3 — later evidence, not code-start blocking

Full OIC-Bench v0.1, private held-out evaluation, comparative outperformance,
practitioner usability, regulated-enterprise pilot evidence, independent
security review, production reliability, open-standard claims, community
governance, and three independent ZTL reproductions are later release or
maturity evidence. They must not be used as code-start prerequisites absent a
new governing decision.

## Gate answer

**SEMANTIC CODE-START GATE: BLOCKED / READY FOR OWNER ADJUDICATION**

