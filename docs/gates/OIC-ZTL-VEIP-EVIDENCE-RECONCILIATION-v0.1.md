# OIC ZTL and VEIP Evidence Reconciliation v0.1

Status: owner-review correction. Historical July TODO states are not carried
forward when merged successor evidence closes them. Technical evidence is not
owner admission.

## ZTL live-status matrix

PR #18 merged at approved head `2f79d4812dbba298a5986e4b40b55c0f296363e5`.
PR #16 merged at approved head `4277838743ec5169bf5045e3e8196330f5e2317f`.
The proposed profile pins signed tag `veraxis-ztl-input-v0.2-signed`, kernel
commit `56e1ff0510c62b04dbd85bbe08b7a6deacbf276b`, and fixture-index SHA-256
`ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145`.

| Requirement | Evidence | Exact artifact/blob | Live status | Remaining action |
|---|---|---|---|---|
| Signed provenance/pin | Signed v0.2 tag and commit | release provenance `3a5ebdee…`; profile `2f8520b2…` | CLOSED BY MERGED ACCEPTED EVIDENCE | Owner admission only |
| Conformance | 13 reachable, 3 NOT_REACHABLE, 0 mismatches/hash problems | conformance `6abcf505…`; run `87b4282d…`; index `21e99c40…` | CLOSED BY MERGED ACCEPTED EVIDENCE | Owner admission only |
| Mapping review | Completed row review and successor cross-review | mapping review `0c43b0fb…`; JSON `a60b41ab…` | CLOSED BY MERGED ACCEPTED EVIDENCE | Owner admission only |
| Historical row 25 | Current `EARNED/hereditary/unverified=any` correction present | profile; mapping review §§1/A | CLOSED BY MERGED ACCEPTED EVIDENCE | None technical |
| Warrant fields | All 28 classified; none unsupported or requiring ZTL change | warrant response `02e72a31…`; mapping review §F | CLOSED BY MERGED ACCEPTED EVIDENCE | Owner admission only |
| WP-3 | Successor trigger binds row 28, observed `sound`, subscription and reasons; SC-RD-006 added | mapping review §A; mapping JSON | CLOSED BY MERGED ACCEPTED EVIDENCE | None technical |
| SC-WA-001/002 | Partition and digest projections accepted | mapping review §A; mapping JSON | CLOSED BY MERGED ACCEPTED EVIDENCE | None technical |
| Trigger set | Five triggers confirmed complete for present anti-tick model | mapping review §G; warrant contract `b9ae57b3…` | CLOSED BY MERGED ACCEPTED EVIDENCE | VEIP carrier deferred |
| Profile metadata | Notice still says PR #18 is draft/not on main | profile `2f8520b2…`, `evidence_dependency_notice` | CURRENTNESS METADATA CORRECTION REQUIRED | Correct in admission package; not a semantic defect |
| Profile admission | Status remains `PROPOSED - ... not admitted` | profile `2f8520b2…` | TECHNICALLY ESTABLISHED / OWNER ADMISSION PENDING | Owner accepts/rejects exact profile |
| Tier-1 reproduction | Producer/Tier-3 evidence only | dossier `72e84ec2…`; profile provenance | LATER INDEPENDENT-EVIDENCE GATE | Owner decides timing; Tier-1 reviewer acts |

The stale `evidence_dependency_notice` is a **CURRENTNESS / PROVENANCE
METADATA DEFECT**, not a semantic mapping defect. Both referenced PRs are
merged. The profile is not edited here; its admission package should replace
the obsolete draft/merge-order statements while retaining `PROPOSED / NOT
ADMITTED` until the owner decides.

## Nine July ZTL items reconciled

| # | Item | Current disposition | Evidence/boundary |
|---:|---|---|---|
| 1 | Independent Tier-1 reproduction | LATER INDEPENDENT-EVIDENCE GATE | Dossier §13; owner decides code-start timing |
| 2 | Signed release provenance | CLOSED BY MERGED ACCEPTED EVIDENCE | Signed v0.2 record |
| 3 | Disposition/grade/unverified mapping | CLOSED BY MERGED ACCEPTED EVIDENCE | Completed mapping and successor review |
| 4 | Warrant fields | CLOSED BY MERGED ACCEPTED EVIDENCE | 28/28 classified and reconfirmed |
| 5 | MissingGround granularity | CLOSED BY MERGED ACCEPTED EVIDENCE | Contracts distinguish informational/load-bearing/blocking grounds and bind subscriptions to missing grounds |
| 6 | Epoch/expiry/revocation | CLOSED BY MERGED ACCEPTED EVIDENCE FOR CURRENT BOUNDED MODEL | Five-trigger set complete for present anti-tick model |
| 7 | VEIP boundary | EXTERNAL / VEIP DEPENDENCY | ZTL end bounded; carrier requires owner VEIP decision |
| 8 | Preflight provenance | STILL OPEN | Separate provenance gap report |
| 9 | VEIP dossier | EXTERNAL / VEIP DEPENDENCY | Minimum record requires owner decision; full lifecycle is later |

## VEIP current evidence

| Public repository | Verified `main` head | OIC status |
|---|---|---|
| `veip-spec` | `b7bae309cd39b6be2f1669aff75c4feb9cf18668` | NEWER EXTERNAL EVIDENCE EXISTS - NOT YET ADMITTED INTO OIC |
| `veip-sdk` | `40bcb5708c8e3aadcb0e31d3190824ddc33f8fce` | NEWER EXTERNAL EVIDENCE EXISTS - NOT YET ADMITTED INTO OIC |
| `veip-verifier-core` | `e8b985920b60ba74f2e0e014ee107a5c4937b1fc` | NEWER EXTERNAL EVIDENCE EXISTS - NOT YET ADMITTED INTO OIC |
| `veip-registry` | `a0b70452d14c0b29da500d53714ae215b09bc43e` | NEWER EXTERNAL EVIDENCE EXISTS - NOT YET ADMITTED INTO OIC |

Newer private/reconstructed material is likewise not admitted without formal
binding into the OIC evidence chain.

| Horizon | Minimum evidence | State |
|---|---|---|
| Semantic code start | Owner-approved non-executable handoff: ActionProposal precedes OIC; OIC consumes exact context and emits RuntimeDecision evidence; neither side creates/reinterprets the other's authority; missing lifecycle integration is fail-closed | TECHNICAL OPTION / OWNER ADMISSION PENDING |
| Result-bearing preflight | Accepted execution carrier plus replay, expiry, revocation, correction and failure behavior for the tested path | OPEN |
| Experimental release/maturity | Canonical repos/pins/licenses, fixtures, conformance, security, reliance, replacement and independent review | OPEN / EXTERNAL WORK REQUIRED |

The twenty-item July inventory remains a gap register, but it is not one
code-start blocker. Items 001–006 and 013 reduce to the minimum handoff
admission question; 007–012 govern result-bearing execution; 014–019 govern
preflight/release evidence; 020 is hygiene. External heads alone close none.

