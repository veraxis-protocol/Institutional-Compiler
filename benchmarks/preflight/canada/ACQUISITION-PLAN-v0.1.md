# Canada Procurement Acquisition Plan v0.1

Status: **PROPOSED — PRE-ACQUISITION — PR #15 BLOCKING**

Prepared from governing `main`:
`37d6fa4dd12f7f26c632169611b13c251bbec14a`.

This plan implements the mechanical boundaries of
`OIC-CORPUS-DECISION-001`, which remains in PR #15 and is therefore a
blocking dependency. This branch must be updated onto post-PR-15 `main`
before review. No acquisition freeze, source-manifest entry, source download,
semantic ingestion, interpretation, or admission is performed by this PR.

## Objectives

1. Define an explicit official-source registry for CA-1 through CA-6.
2. Record confirmed and unresolved English/French source relationships.
3. Separate availability, authority, effectiveness, reuse, and redistribution.
4. Provide a metadata-first, fail-closed acquisition utility.
5. Quarantine any later authorized downloads outside Git history.
6. Bound the proposed working set to 56 print-equivalent pages.

## Source-family bounds

- **CA-1:** Directive scope, definitions, authority, effective-date provisions,
  and context required for selected appendices.
- **CA-2:** Selected Appendix A approval tables and their conditions.
- **CA-3:** Complete current consolidation in one owner-selected XML or PDF
  representation, plus point-in-time metadata. The final artifact URL remains
  unresolved and must be fixed before acquisition.
- **CA-4:** Selected evidence, approval, record, and accountability provisions
  from Appendix F.
- **CA-5:** Four explicitly enumerated Buyer’s Guide approval/authority pages.
  No portal crawl.
- **CA-6:** Archive notice, selected Chapter 6 nodes, and directly referenced
  glossary entries.
- **CA-7:** Excluded by default.

## Deterministic acquisition sequence

1. Owner/reviewer resolves the open source-enumeration questions.
2. Update the proposed registry without populating retrieval facts.
3. Confirm each page’s licence notice and screen excluded material.
4. Run the utility in default metadata-only mode for explicitly named IDs.
5. Review canonical JSON receipts and establish the acquisition freeze in a
   later authorized PR.
6. If rights review permits and context requires complete artifacts, run with
   `--download` into `.local/canada-preflight-quarantine/`.
7. Compare any expected digest supplied by an independent record.
8. Keep source bytes and local receipts untracked. A separate decision governs
   whether any bytes may later enter public Git history.

## Failure posture

The utility fails closed for unknown IDs, non-HTTPS URLs, domains outside the
exact allowlist, external redirects, mismatched content types, missing
responses, ambiguous output directories, and digest mismatches. Server
timestamps and headers are recorded only when returned. No missing retrieval
fact is synthesized.

## Provenance records

Each receipt records the requested and final URLs, redirect chain, UTC
retrieval timestamp, response status, media type, ETag, Last-Modified,
Content-Length, actual byte length, and SHA-256 where bytes are downloaded.
Receipts use UTF-8 canonical JSON with sorted keys, compact separators, and a
deterministic source-ID execution order.

## Explicit non-goals

This work does not modify `SOURCE_MANIFEST.csv`, freeze a corpus, publish
source bytes, interpret policy, extract clauses, assign modality, create
controls or annotations, construct Institutional IR, generate an Open Control
Envelope, or call ZTL, VEIP, OPA, an LLM, or browser automation. `STATUS.md`
and the semantic implementation gate remain unchanged and blocked.
