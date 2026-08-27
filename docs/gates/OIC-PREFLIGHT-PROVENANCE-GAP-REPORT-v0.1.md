# OIC Preflight Provenance Gap Report v0.1

Status: mechanical audit at OIC commit
`d06917fa6877277d7118b49e80d6a69446f50712`. No rights, authority, effective
date, or source meaning is inferred.

## Governing requirement

`benchmarks/preflight/README.md` requires every source used by the preflight to
appear in `SOURCE_MANIFEST.csv` with rights, provenance, immutable hash,
effective dates, and declared authority status. The proposed Canada working set
is defined by `benchmarks/preflight/canada/WORKING-SET-SCOPE-v0.1.md` and
`SOURCE-REGISTRY-PROPOSED-v0.1.json`; proposals are not frozen sources.

Evidence status vocabulary: `ESTABLISHED`, `PARTIAL`, `OPEN`,
`OWNER/DOMAIN ATTESTATION REQUIRED`, and `NOT REQUIRED FOR CURRENT PREFLIGHT`.

## Source-by-source provenance gap matrix

The “field state” column follows this order: stable ID; title; issuer; type;
official origin; reuse basis; acquisition time; SHA-256; effective-from;
effective-until; supersession/amendment; confidentiality; verification
receipt/command; benchmark authority status; frozen bytes.

| Source | Field state | Current evidence and exact artifact/blob | Overall status | Missing evidence | Required authority | Smallest truthful next action | Gate effect |
|---|---|---|---|---|---|---|---|
| CA-1 | E,E,E,E,E,P,O,O,O,O,P,P,O,O,O | Proposed registry and scope only: `SOURCE-REGISTRY-PROPOSED-v0.1.json` blob `35e23be5…`; `WORKING-SET-SCOPE-v0.1.md` blob `cf2ce8a9…` | PARTIAL | Rights clearance, authorized acquisition, frozen bytes/hash/receipt, effective dates, confidentiality and authority declaration | Owner plus qualified rights/domain reviewer | Resolve rights; if permitted, authorize deterministic acquisition and freeze | BLOCKS SEMANTIC CODE START |
| CA-2 | E,E,E,E,E,P,O,O,O,O,P,P,O,O,O | Same proposed registry/scope; appendix is version-related to CA-1 | PARTIAL | Same gaps as CA-1 plus final table/node anchors | Owner plus qualified rights/domain reviewer | Resolve rights and freeze selected appendix nodes | BLOCKS SEMANTIC CODE START |
| CA-3 | E,E,E,E,E,E,E,E,O,O,P,E,E,O,E | Manifest blob `718a9df6…`; frozen XML blob `9d89e621…`; receipt blob `52f8585f…`; freeze record blob `dc2a89d…`; rights clearance blob `dace02fd…`; SHA-256 `6e89ad25…` | PARTIAL | Effective-from/effective-until state and declared benchmark authority status are blank; current verifier still reports corpus evidence `INCOMPLETE` | Owner/domain authority for benchmark authority; domain reviewer for effective-date treatment | Record bounded authority/effective-date disposition without inventing dates, then make the current verifier resolve the accepted frozen receipt | BLOCKS SEMANTIC CODE START |
| CA-4 | E,E,E,E,E,P,O,O,O,O,P,P,O,O,O | Proposed registry/scope only (`35e23be5…`, `cf2ce8a9…`) | PARTIAL | Rights, freeze, effective date, authority and receipt fields | Owner plus qualified rights/domain reviewer | Resolve rights and freeze selected provisions if permitted | BLOCKS SEMANTIC CODE START |
| CA-5-APPROVALS | E,E,E,E,E,O,O,O,O,O,P,P,O,O,O | Proposed registry; rights-clearance record says publisher robots policy refuses project retrieval and reuse evidence is unresolved (`RIGHTS-CLEARANCE-v0.1.json`, blob `dace02fd…`) | OWNER/DOMAIN ATTESTATION REQUIRED | Lawful acquisition/reuse path, frozen bytes, dates, receipt, authority | Owner plus qualified licensing reviewer; publisher if permission is sought | Replace with a rights-clear source or obtain permission and record it | BLOCKS SEMANTIC CODE START |
| CA-5-DELEGATION | E,E,E,E,E,O,O,O,O,O,P,P,O,O,O | Same CanadaBuys rights evidence as CA-5-APPROVALS | OWNER/DOMAIN ATTESTATION REQUIRED | Same; public guidance also does not prove an individual delegation | Owner, licensing reviewer, domain authority | Select a lawful source and define the delegation-evidence ceiling | BLOCKS SEMANTIC CODE START |
| CA-5-SIGNING | E,E,E,E,E,O,O,O,O,O,P,P,O,O,O | Same CanadaBuys rights evidence | OWNER/DOMAIN ATTESTATION REQUIRED | Rights/acquisition/freeze/date/authority evidence | Owner, licensing reviewer, domain authority | Replace or obtain permission; then freeze | BLOCKS SEMANTIC CODE START |
| CA-5-LIMITS | E,E,E,E,E,O,O,O,O,O,P,P,O,O,O | Same CanadaBuys rights evidence | OWNER/DOMAIN ATTESTATION REQUIRED | Rights/acquisition/freeze/date/authority evidence | Owner, licensing reviewer, domain authority | Replace or obtain permission; then freeze | BLOCKS SEMANTIC CODE START |
| CA-6-ARCHIVE | E,E,E,E,E,O,O,O,P,P,E,P,O,O,O | Proposed archived-source metadata and rights refusal evidence | OWNER/DOMAIN ATTESTATION REQUIRED | Lawful frozen copy, hash/receipt, exact historical period, authority classification | Owner, licensing reviewer, domain authority | Replace with a lawfully reusable stale/superseded source or obtain permission | BLOCKS SEMANTIC CODE START |
| CA-6-CH6 | E,E,E,E,E,O,O,O,P,P,E,P,O,O,O | Seven proposed stable section numbers in scope; no acquired bytes | OWNER/DOMAIN ATTESTATION REQUIRED | Same as CA-6-ARCHIVE plus frozen node boundaries | Owner, licensing reviewer, domain authority | Resolve lawful source and freeze exact nodes | BLOCKS SEMANTIC CODE START |
| CA-6-GLOSSARY | E,E,E,E,E,O,O,O,O,O,P,P,O,O,O | Scope assigns zero entries because no direct selected-node reference was evidenced | NOT REQUIRED FOR CURRENT PREFLIGHT | None while zero-entry exclusion remains owner-accepted | Owner only if scope changes | Retain exclusion | DOES NOT CURRENTLY BLOCK |
| CA-7 | P,P,P,P,P,O,O,O,O,O,O,O,O,O,O | Explicitly excluded by current 55-page scope | NOT REQUIRED FOR CURRENT PREFLIGHT | None unless owner expands scope | Owner only if scope changes | Retain exclusion | DOES NOT CURRENTLY BLOCK |

Legend: `E` established, `P` partial, `O` open.

## Result

No source currently satisfies every preflight provenance requirement. CA-3 is
the only source with frozen bytes, a cryptographic digest, a tracked receipt,
and documented reuse basis. It remains incomplete for the gate because the
manifest lacks effective-date and declared authority dispositions and the
current manifest verifier reports `INCOMPLETE`.

The smallest truthful source blocker set is:

1. close the bounded CA-3 effective-date/authority/verification disposition;
2. owner-select a minimum source set that covers the required source roles;
3. replace or clear sources whose acquisition/reuse is blocked;
4. freeze every selected source with bytes, hashes, receipts, dates where
   supportable, confidentiality, and declared benchmark authority status.

## Owner source-strategy choice

The governing design permits a bounded public or synthetic subset. The owner
may continue real Canada clearance, or authorize CA-3 as the real anchor plus
explicitly synthetic procurement sources for remaining roles. Synthetic
companions must name a synthetic test institution, declare their synthetic
status, carry deterministic generated provenance and hashes, create no
real-world authority, and remain limited to benchmark/test semantics. This
audit does not authorize or create them.
