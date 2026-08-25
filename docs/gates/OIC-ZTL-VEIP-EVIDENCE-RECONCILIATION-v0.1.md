# OIC ZTL and VEIP Evidence Reconciliation v0.1

Status: mechanical evidence reconciliation at OIC commit
`d06917fa6877277d7118b49e80d6a69446f50712`. Producer evidence is not treated
as independent reproduction, a proposal is not treated as an accepted
interface, and public visibility is not treated as a license grant.

## ZTL dossier field matrix

| Requirement | Current evidence | Exact artifact/blob | Status | Still missing / authority to close | Gate effect |
|---|---|---|---|---|---|
| Repository/artifact | Public repository and entrypoints identified | `ZTL-DOSSIER-v0.1.md` `72e84ec2…`; `README.md` `c8170b5c…` | ESTABLISHED | None mechanically | DOES NOT CURRENTLY BLOCK |
| Owner | Vitaly Reznik identified as owner/maintainer | dossier `72e84ec2…`; `OWNERS.md` | ESTABLISHED | None mechanically | DOES NOT CURRENTLY BLOCK |
| License | MIT asserted with upstream LICENSE reference | dossier `72e84ec2…` | PARTIAL | Independent consumer confirmation of pinned artifact/license; owner/legal if disputed | BLOCKS EXPERIMENTAL RELEASE |
| Immutable version | v0.2 signed tag, commit `56e1ff05…`, toolchain and key recorded | ZTL README `c8170b5c…`; provenance `3a5ebdee…` | ESTABLISHED | OIC owner must admit the v0.2 pin as provisional dependency reference | BLOCKS SEMANTIC CODE START |
| Interface schema | `judge` boundary and connector schemas described | dossier `72e84ec2…`; conformance v0.2 `6abcf505…` | PARTIAL | OIC acceptance/interface-freeze record | BLOCKS SEMANTIC CODE START |
| Semantics | T/F/Z, warranty grades, four dispositions and boundary documented | dossier; mapping review `0c43b0fb…` | PARTIAL | Joint OIC/Vitaliy adjudication of mapping, including rejected row 25 | BLOCKS SEMANTIC CODE START |
| Fixture hashes | v0.1/v0.2 fixture indexes and SHA256SUMS tracked | v0.2 index `21e99c40…`; sums `2b560e8e…` | ESTABLISHED | Acceptance under selected pin | BLOCKS SEMANTIC CODE START |
| Conformance tests | Executable procedures and author-side run present | v0.2 procedure `6abcf505…`; run `87b4282d…` | PARTIAL | OIC-side reproduction of provisional interface; Tier-1 independence remains separate | BLOCKS SEMANTIC CODE START |
| Failure behavior | Fail-closed behavior documented | dossier `72e84ec2…` | PARTIAL | OIC mapping acceptance and joint negative fixtures | BLOCKS SEMANTIC CODE START |
| Security notes | Bounds/hazards recorded | dossier; kernel census `770cb69e…` | ESTABLISHED | Independent security review is later evidence | BLOCKS RELEASE FREEZE |
| Known limitations | Explicit limitations and claim ceiling | dossier `72e84ec2…` | ESTABLISHED | None for audit | DOES NOT CURRENTLY BLOCK |
| Replacement strategy | Review-only fallback and migration suite described | dossier `72e84ec2…` | PARTIAL | Owner acceptance of fallback contract | BLOCKS EXPERIMENTAL RELEASE |
| Independent reproduction | Recipe exists; author-side only | dossier §13 `72e84ec2…` | OPEN | Unrelated Tier-1 reproducer; owner decides whether deferrable from code start | BLOCKS EXPERIMENTAL RELEASE |

## Nine July ZTL items reconciled

| # | Item | Current classification | Exact evidence | Horizon / next authority |
|---:|---|---|---|---|
| 1 | Independent Tier-1 reproduction | STILL OPEN | dossier §13; README open-items table | Experimental release; Tier-1 reviewer, then owner |
| 2 | Signed release provenance | CLOSED BY CURRENT ACCEPTED EVIDENCE | `RELEASE-PROVENANCE-v0.1.md` `3a5ebdee…`; v0.2 signed pin in README | Does not block; signature trust limitation remains visible |
| 3 | Disposition/grade/unverified mapping | EVIDENCE NOW PRESENT BUT NOT ADJUDICATED | `MAPPING-REVIEW-v0.1.md` `0c43b0fb…`; row 25 rejected | Code start; OIC owner + Vitaliy bounded mapping decision |
| 4 | Warrant artifact fields | EVIDENCE NOW PRESENT BUT NOT ADJUDICATED | `WARRANT-FIELD-RESPONSE-v0.1.md` `02e72a31…`; 28 fields classified | Code start; OIC owner accepts or requests bounded correction |
| 5 | MissingGround granularity | STILL OPEN | ZTL README; warrant response | Code start; OIC review-docket owner specifies required granularity, Vitaliy confirms feasibility |
| 6 | Epoch/expiry/revocation/anti-tick | EVIDENCE NOW PRESENT BUT NOT ADJUDICATED | proposal `00e858cb…`; mapping review | Code start for boundary minimum; owner/Vitaliy accept or constrain proposal |
| 7 | VEIP boundary | EVIDENCE NOW PRESENT BUT NOT ADJUDICATED | `ZTL-VEIP-BOUNDARY-PREFLIGHT-v0.1.md` `247558bd…` | Code start; owner architecture decision |
| 8 | Preflight provenance | STILL OPEN | provenance gap report; manifest `718a9df6…` | Code start; owner/rights/domain actors |
| 9 | VEIP dossier | STILL OPEN | VEIP checklist `46490bc…` | Code start; owner and external VEIP actors |

## VEIP dossier field matrix

| Requirement | Current evidence | Exact artifact/blob | Status | Still missing / authority to close | Gate effect |
|---|---|---|---|---|---|
| Repository/spec locations | Four candidates inventoried | `VEIP-INVENTORY-v0.1.md` `26abb9ad…` | EXTERNAL/OWNER ACTION REQUIRED | Owner attests canonical/excluded repositories | BLOCKS SEMANTIC CODE START |
| Owner | Interim owner recorded | checklist `46490bc…`; owner decision `66190c45…` | ESTABLISHED | None mechanically | DOES NOT CURRENTLY BLOCK |
| License | Conflicting/incomplete across four layers | checklist `46490bc…`; inventory `26abb9ad…` | OPEN | Complete texts and qualified compatibility review | BLOCKS SEMANTIC CODE START |
| Immutable versions | Candidate SHAs exist, no attested interface pins | inventory `26abb9ad…` | PARTIAL | Owner-attested pins/version relationship | BLOCKS SEMANTIC CODE START |
| Lifecycle interface | Small fragments; core lifecycle undefined | checklist `46490bc…`; boundary memo `247558bd…` | OPEN | Owner-approved minimum states/events | BLOCKS SEMANTIC CODE START |
| Evidence schema | Byte-identical Evidence Pack schema, SHA-256 `3ff025de…` | checklist/inventory | PARTIAL | Owner identifies its role and freezes provisional schema | BLOCKS SEMANTIC CODE START |
| Fixtures | Sparse, non-normative fixtures | checklist/inventory | PARTIAL | Version-bound minimum boundary fixtures | BLOCKS PREFLIGHT EXECUTION |
| Conformance tests | Per-repo commands only; no consolidated run | checklist/inventory | OPEN | External repositories publish clean pinned command/results | BLOCKS PREFLIGHT EXECUTION |
| Replay behavior | Recompute vs integrity-carrier semantics conflict | checklist/inventory | OPEN | Owner architecture decision and external tests | BLOCKS SEMANTIC CODE START |
| Revocation/correction | Absent | checklist `46490bc…` | OPEN | Owner defines minimum invalidation/correction boundary | BLOCKS SEMANTIC CODE START |
| Security notes | Layer notes exist, no consolidated model | checklist/inventory | PARTIAL | Minimum integration threats for code start; independent review later | BLOCKS EXPERIMENTAL RELEASE |
| Known limitations | Scattered and not owner-attested | checklist/inventory | PARTIAL | Consolidated limitation register | BLOCKS EXPERIMENTAL RELEASE |
| Replacement strategy | Conceptual only | checklist/inventory | PARTIAL | Owner-approved fail-closed fallback/continuity rule | BLOCKS SEMANTIC CODE START |

## Twenty July VEIP items reconciled

| ID | Classification | Code-start horizon | Current evidence / smallest next action |
|---|---|---|---|
| VEIP-OI-001 | OWNER DECISION REQUIRED | Blocks code start | Inventory present; owner attests canonical repository set. |
| VEIP-OI-002 | OWNER DECISION REQUIRED | Blocks code start | Candidate SHAs present; owner selects provisional immutable versions. |
| VEIP-OI-003 | OWNER DECISION REQUIRED | Blocks code start | Conflicting licenses; obtain complete texts and qualified compatibility finding. |
| VEIP-OI-004 | OWNER DECISION REQUIRED | Blocks code start | Define minimum lifecycle states/events. |
| VEIP-OI-005 | OWNER DECISION REQUIRED | Blocks code start | Select canonical action-proposal input and required identifiers. |
| VEIP-OI-006 | OWNER DECISION REQUIRED | Blocks code start | Decide the exact OIC-to-VEIP runtime-decision boundary. |
| VEIP-OI-007 | EVIDENCE NOW PRESENT BUT NOT ADJUDICATED | Blocks preflight execution | Evidence Pack execution object exists; owner decides whether it is sufficient for bounded preflight. |
| VEIP-OI-008 | OWNER DECISION REQUIRED | Blocks code start | Reconcile recomputation and integrity-carrier replay meanings. |
| VEIP-OI-009 | STILL OPEN | Blocks experimental release | Define reliance record and invalidation duties before reliance claims. |
| VEIP-OI-010 | OWNER DECISION REQUIRED | Blocks code start | Define minimum expiry/time-authority boundary. |
| VEIP-OI-011 | OWNER DECISION REQUIRED | Blocks code start | Define fail-closed revocation propagation boundary. |
| VEIP-OI-012 | OWNER DECISION REQUIRED | Blocks code start | Define correction/supersession linkage minimum. |
| VEIP-OI-013 | OWNER DECISION REQUIRED | Blocks code start | Select unified fail-closed behavior across layers. |
| VEIP-OI-014 | EXTERNAL REPOSITORY WORK REQUIRED | Blocks preflight execution | VEIP Registry owner repairs/explains mismatch and adds tests. |
| VEIP-OI-015 | EXTERNAL REPOSITORY WORK REQUIRED | Blocks experimental release | VEIP spec owner produces green pinned-head CI or accepted deviation. |
| VEIP-OI-016 | EXTERNAL REPOSITORY WORK REQUIRED | Blocks preflight execution | Publish minimum normative boundary fixtures. |
| VEIP-OI-017 | EXTERNAL REPOSITORY WORK REQUIRED | Blocks preflight execution | Publish consolidated pinned conformance command/results. |
| VEIP-OI-018 | OWNER DECISION REQUIRED | Blocks experimental release | Consolidate security model; independent assessment is release-freeze evidence. |
| VEIP-OI-019 | OWNER DECISION REQUIRED | Blocks code start | Define fail-closed replacement/fallback and evidence continuity. |
| VEIP-OI-020 | EXTERNAL REPOSITORY WORK REQUIRED | Does not currently block | Remove or justify tracked generated artifacts before maturity claims. |

