# OIC-Bench Procurement Corpus Candidates v0.1

Status: **RESEARCH PREFLIGHT — CANDIDATE SELECTION ONLY**

Date of research: 2026-07-29  
Decision owner: Arkadiy Miteiko / Veraxis  
Scope: English-language, public-source procurement materials  
Provenance status: **INCOMPLETE — acquisition, hashing, and source-manifest work have not begun**

This memo compares official-source candidates. It does not ingest or interpret
provisions, create annotations or candidate norms, construct Institutional IR,
or change the semantic implementation gate. References to possible transaction
cases describe only whether the documents appear to contain the requested types
of material; they are not conclusions about the meaning or application of any
provision.

## 1. Executive comparison

| Rank | Candidate pack | Source units | Estimated pages | Rights clarity | Authority clarity | Amendment chain | Delegation / exception material | Reproducibility | Acquisition effort |
|---:|---|---:|---:|---|---|---|---|---|---|
| 1 | Canada — federal procurement | 7 | ~305 | High: Open Government Licence — Canada, subject to stated exclusions | High for statutes, regulations, and Treasury Board instruments; mixed for operational guidance | High for regulations and directives; archived operational manual is date-marked | Strong public approval tables and exceptions; individual PSPC delegations are partly intranet-only | High for laws and policy pages; medium for evolving Buyer’s Portal | Medium |
| 2 | United Kingdom — central government procurement | 7 | ~260 | High: Open Government Licence for in-scope Crown material, subject to exclusions | High for legislation; medium-high for Cabinet Office guidance | High but transition between Procurement Act 2023 and legacy PCR 2015 is complex | Good exception and below-threshold material; approval controls are less like a single delegation matrix | High for legislation; medium-high for mutable GOV.UK guidance | Medium-high |
| 3 | United States — federal acquisition, GSA overlay | 7 | ~1,700 | High for US Government works, but third-party material must be screened | High for Federal Register/CFR; official-but-non-CFR acquisition publications require careful classification | High in principle; operational reconstruction across FACs and GSAM changes is laborious | Strong justification, approval, exception, and documentation material | High if official edition and archive captures are pinned | High |

The page totals are planning estimates, not acquisition measurements. For HTML
sources, they are print-equivalent estimates. Exact page counts, bytes, retrieval
timestamps, content hashes, and redirects must be recorded only during a later,
authorized acquisition step.

### Recommendation

**Recommend the Canada federal pack for the seven-day experimental slice.**

The recommendation follows the required order of criteria:

1. The Open Government Licence — Canada provides the clearest pack-wide reuse
   basis, while preserving an explicit obligation to screen third-party content,
   personal information, insignia, and other exclusions.
2. The hierarchy among the Financial Administration Act framework, Government
   Contracts Regulations, Treasury Board directive, and PSPC operational
   guidance is stated on official sites.
3. Justice Laws supplies point-in-time regulation versions, Treasury Board
   identifies replaced directive versions, and CanadaBuys labels the former
   Supply Manual as archived.
4. The directive’s contracting-approval appendix, mandatory procedures,
   Government Contracts Regulations exceptions, and archived approvals chapter
   provide unusually compact candidate material. A limitation is that individual
   PSPC officer delegations and some older manual versions are intranet-only.
5. Official HTML, XML, and PDF variants make immutable capture feasible, subject
   to acquisition-time hashing and preservation.
6. About 305 pages is manageable for a bounded slice if the Buyer’s Portal and
   archived manual are captured as selected, explicitly enumerated sections.
7. The pack appears capable of supporting later construction of ALLOW, DENY, and
   CANNOT transaction cases without assuming in this memo what any rule means.

## 2. Candidate pack A — Canada federal procurement (recommended)

**Jurisdiction:** Canada (federal)  
**Issuing institutions:** Treasury Board of Canada Secretariat (TBS), Department
of Justice Canada, and Public Services and Procurement Canada (PSPC)  
**Pack estimate:** 7 source units, ~305 print-equivalent pages  
**Expected acquisition effort:** Medium (approximately 1.5–2 researcher-days,
excluding legal review and later annotation)

### Source-by-source evidence

| # | Official source, title, and type | Effective/current status and supersession | Pages / format / accessibility | Rights and redistribution | Acquisition and corpus utility | Uncertainty |
|---:|---|---|---|---|---|---|
| CA-1 | [TBS — Directive on the Management of Procurement](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692), primary policy directive | Current page observed 2026-07-29; page records replaced/archived versions dated 2022-04-25, 2023-06-22, and 2026-01-08. Individual requirements have stated effective dates. | ~70 pages including appendices; accessible HTML/print view | Officially available. Government of Canada material is generally reusable under the OGL-Canada where the page is covered and no exclusion applies. Redistribution appears permitted with attribution and no implied endorsement. | Immutable capture feasible by saving rendered HTML plus response metadata and hash. Strong authority/effective-date metadata; includes requirements, records, exceptions, discretion, and links to approvals. | Confirm the licence footer and any third-party material at acquisition. A live policy page may change after capture. |
| CA-2 | [TBS Directive, Appendix A — Contracting Approvals](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692&p=A&section=procedure), approval/delegation table | Part of the current directive; must be versioned with CA-1. Tables specify basic and exceptional contracting approval limits and conditions. | ~22 pages; accessible HTML/print view | Same preliminary OGL-Canada basis as CA-1. | Public approval matrix is available. Immutable capture feasible. Candidate for approval thresholds and exception pathways. | This is not the complete individual delegation instrument for every department or contracting officer. Do not represent it as such. |
| CA-3 | [Justice Laws — Government Contracts Regulations, SOR/87-402](https://laws-lois.justice.gc.ca/eng/regulations/SOR-87-402/index.html), regulation | Consolidation current to 2026-05-26; last amended 2024-12-16 on the observed page. [Previous versions](https://laws-lois.justice.gc.ca/eng/regulations/sor-87-402/PITIndex.html) permit point-in-time reconstruction. | ~18 pages; accessible HTML, XML, and [PDF](https://laws-lois.justice.gc.ca/pdf/SOR-87-402.pdf) | Officially available. Preliminary OGL-Canada reuse basis; the consolidation includes the usual notice that it is not an official version for evidentiary purposes. | Strong amendment-chain source. Contains regulatory bidding exceptions and approval conditions suitable for later case design. PDF/XML allow deterministic capture. | Confirm source PDF page count and consolidation date at acquisition; distinguish consolidated convenience copy from authoritative enacted instruments. |
| CA-4 | [TBS Directive, Appendix F — Mandatory Procedures for Business Owners When Procuring Professional Services](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692&p=F&section=procedure), subordinate mandatory procedure | Effective 2024-09-30; current as part of CA-1 on research date. | ~12 pages; accessible HTML/print view | Same preliminary OGL-Canada basis as CA-1. | Contains candidate evidence, approval, record, and accountability requirements for professional services over stated thresholds. Immutable capture feasible. | Scope is professional services, not all procurement. Threshold/effective-date context must travel with the source. |
| CA-5 | [CanadaBuys — Buyer’s Guide](https://canadabuys.canada.ca/en/buyer-s-portal/buyer-s-guide), current PSPC operating guidance | CanadaBuys states the Buyer’s Portal became the official Acquisitions Program information source on 2026-01-30. It supersedes the maintained role of the archived Supply Manual, not the higher-order regulation/directive. | ~95 pages for an enumerated selection of Plan, Approve, Solicit, Evaluate, Award, and Manage pages; accessible HTML | Preliminary OGL-Canada basis; each page and embedded asset requires licence/exclusion screening. | Current subordinate workflow and evidence guidance. Capture must enumerate URLs rather than crawl an undefined portal. | Content is mutable; “official source of information” does not make every page a legal authority or establish effectiveness equivalent to a regulation. |
| CA-6 | [CanadaBuys — Archived Supply Manual](https://canadabuys.canada.ca/en/supply-manual), stale operating procedure, including [Chapter 6 — Approvals and authorities](https://canadabuys.canada.ca/en/supply-manual/chapter-6) | Explicitly archived and no longer maintained as of 2025-10-31. The current Buyer’s Portal is identified as the replacement. | ~80 pages for enumerated Chapters 1, 4, 6, and glossary; accessible HTML; complete HTML download is advertised | Preliminary OGL-Canada basis, subject to page-level exclusions. Redistribution appears permitted after screening and attribution. | Honest stale/current contrast is available. Chapter 6 contains prior approval processes; synopsis records dated changes. Complete HTML and explicit archive label support reproducibility. | Some pre-migration versions and referenced tools are accessible only on the Government of Canada network. Archived content may remain relevant to older transactions; no applicability conclusion is made here. |
| CA-7 | [TBS Directive, Appendix B — Limitation of Liability and Indemnification](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692&p=B&section=procedure), mandatory procedure / exception material | Current as part of CA-1 on research date; conditions and approvals must be tied to the captured directive version. | ~8 pages; accessible HTML/print view | Same preliminary OGL-Canada basis as CA-1. | Compact evidence of exceptions, approvals, risk decisions, and discretionary choices. Immutable capture feasible with CA-1. | Specialized subject matter; inclusion is for structural coverage only, not a claim that it governs any future example. |

### Coverage assessment

- Primary rule/policy: CA-1 and CA-3.
- Definitions/glossary: CA-1 definitions and the enumerated CA-6 glossary.
- Approval/delegation: CA-2 and CA-6 Chapter 6.
- Amendment/supersession: CA-1 archived versions, CA-3 point-in-time versions,
  and CA-5/CA-6 current-to-archived transition.
- Subordinate operating procedure: CA-4 and CA-5.
- Potentially stale/conflicting procedure: CA-6, explicitly archived. Any actual
  conflict must be established later, not inferred.
- Evidence requirements: CA-4, CA-5, and CA-7.
- Exception/discretion: CA-3 and CA-7.
- Transaction feasibility: High at preflight level. Thresholds, approvals,
  exceptions, missing internal delegations, and effective-date transitions appear
  capable of supporting later ALLOW, DENY, and CANNOT designs.

## 3. Candidate pack B — United Kingdom central government

**Jurisdiction:** United Kingdom (central government; England/Wales/NI coverage
must be verified per instrument, with devolved and Scottish regimes excluded)  
**Issuing institutions:** UK Parliament, Cabinet Office, and The National Archives  
**Pack estimate:** 7 source units, ~260 pages  
**Expected acquisition effort:** Medium-high (approximately 2–3 researcher-days,
excluding legal review)

### Source-by-source evidence

| # | Official source, title, and type | Effective/current status and supersession | Pages / format / accessibility | Rights and redistribution | Acquisition and corpus utility | Uncertainty |
|---:|---|---|---|---|---|---|
| UK-1 | [legislation.gov.uk — Procurement Act 2023](https://www.legislation.gov.uk/ukpga/2023/54/contents), primary legislation | Most substantive provisions commenced 2025-02-24, subject to commencement, transitional, and saving instruments. Revised and enacted views must be distinguished. | ~130 pages; accessible HTML and PDF | Crown copyright material on legislation.gov.uk is generally offered under the UK Open Government Licence unless otherwise indicated. Redistribution appears permitted with attribution and stated exceptions. | Authoritative legislative publisher, stable identifiers, enacted/revised views, and effects metadata support immutable capture and reconstruction. | Geographic extent, commencement, savings, and revised-text status must be recorded provision by provision during acquisition. |
| UK-2 | [legislation.gov.uk — Procurement Regulations 2024](https://www.legislation.gov.uk/uksi/2024/692/contents), subordinate regulation | Made under the 2023 Act; current/revised status and effects must be captured on acquisition date. | ~65 pages; accessible HTML and PDF | Preliminary OGL basis as above. | Contains operative detail, forms/notices, evidence structures, and definitions linked to the Act. | Revised text may incorporate later changes; record both “made” and current views where available. |
| UK-3 | [GOV.UK — Guidance: Below-threshold contracts](https://www.gov.uk/government/publications/procurement-act-2023-guidance-documents-define-phase/guidance-below-threshold-contracts-html), subordinate official guidance | Applies to the Procurement Act 2023 regime; page observed updated 2026-07-13. It points to Act Part 6 and current thresholds. | ~14 pages; accessible HTML, normally paired with PDF in the publication collection | Crown material on GOV.UK is generally OGL unless otherwise stated; screen embedded material. | Compact procedure with thresholds, discretion, exceptions, and publication steps. Capture publication metadata and update history. | Guidance is not legislation. Update history may not expose every prior byte version. |
| UK-4 | [GOV.UK — PPN 005: Reserving below threshold procurements](https://www.gov.uk/government/publications/ppn-005-reserving-below-threshold-procurements), policy note plus guidance | Published 2025-02-17 for the Procurement Act regime. The publication says PPN 11/20 applies to procurements under the prior regime. | 4-page PPN plus 17-page guide; accessible PDF and HTML metadata | Preliminary OGL basis; verify PDF notices and logos. | Explicit exception/discretion candidate, with applicability boundaries and a named predecessor. PDF supports deterministic capture. | Scope and mandatory status vary by contracting authority; do not generalize beyond the note. |
| UK-5 | [GOV.UK — Procurement Policy Notes collection](https://www.gov.uk/government/collections/procurement-policy-notes), amendment/supersession index | Separates Procurement Act 2023 notes for procurements from 2025-02-24 from PCR 2015 notes for earlier procurements and contracts under legacy frameworks. | ~8 pages; accessible HTML | Preliminary OGL basis. | Official transition map; useful for selecting and documenting current versus legacy sources. | Collection pages are indexes, not themselves operative policy. They are mutable and need timestamped capture. |
| UK-6 | [legislation.gov.uk — Procurement Act 2023 (Commencement No. 3 and Transitional and Saving Provisions) Regulations 2024](https://www.legislation.gov.uk/uksi/2024/716/contents/made), commencement/transitional instrument, together with its [2024 amendment](https://www.legislation.gov.uk/uksi/2024/959/contents/made) | Establishes commencement and transition, then amended before the new regime came into force. | ~16 pages combined; accessible HTML and PDF | Preliminary OGL basis as above. | Direct amendment/supersession evidence and an official basis for representing legacy procedure honestly. | Acquisition should treat the two statutory instruments as one linked source unit but hash each file separately. |
| UK-7 | [GOV.UK — PPN 019: Transparency requirements for publishing on Contracts Finder](https://www.gov.uk/government/publications/ppn-019-transparency-requirements-for-publishing-on-contracts-finder), legacy/current-boundary operating guidance | Published 2025-03; distinguishes legacy Public Contracts Regulations 2015 Contracts Finder duties from Procurement Act notice obligations. | ~10 pages; accessible PDF/HTML metadata | Preliminary OGL basis; verify asset notices. | Provides a concrete potentially stale/conflicting procedural boundary and evidence/publication requirements. | The pack must not characterize legacy guidance as simply invalid: saved procurements and framework contracts may retain relevance. |

### Coverage assessment

- Primary rule/policy: UK-1 and UK-2.
- Definitions/glossary: UK-1/UK-2 definitions.
- Approval/delegation: below-threshold authority and Cabinet Office policy
  controls are present, but no single universal contracting-officer delegation
  matrix was located. This is weaker than Canada.
- Amendment/supersession: UK-5 and UK-6.
- Subordinate procedure: UK-3 and UK-4.
- Potentially stale/conflicting procedure: UK-7 and the legacy branch of UK-5.
- Evidence requirements: UK-2, UK-3, and UK-7.
- Exception/discretion: UK-1 schedules and UK-4.
- Transaction feasibility: Medium-high, especially for threshold, transition,
  reservation, notice, and missing-authority cases. Jurisdictional and
  transitional complexity increases the risk of an accidental applicability
  assertion.

## 4. Candidate pack C — United States federal acquisition (GSA overlay)

**Jurisdiction:** United States federal; GSA-specific procedures are included
only as the agency overlay  
**Issuing institutions:** Federal Acquisition Regulatory Council, General
Services Administration, Office of the Federal Register/Government Publishing
Office  
**Pack estimate:** 7 source units, ~1,700 pages  
**Expected acquisition effort:** High (approximately 4–5 researcher-days,
excluding legal review)

### Source-by-source evidence

| # | Official source, title, and type | Effective/current status and supersession | Pages / format / accessibility | Rights and redistribution | Acquisition and corpus utility | Uncertainty |
|---:|---|---|---|---|---|---|
| US-1 | [Acquisition.gov — Federal Acquisition Regulation](https://www.acquisition.gov/browse/index/far), primary procurement regulation, FAC 2026-01 | Observed FAC 2026-01, effective 2026-03-13. Acquisition.gov provides current FAR and downloadable editions; official CFR edition/status must be separately recorded. | ~1,250 pages for full PDF estimate; HTML, DITA, PDF, Word, EPUB | US Government works are generally not subject to US copyright under 17 U.S.C. §105, but third-party material and transferred rights must be screened. Redistribution appears permitted for government-authored text. | Comprehensive primary source, definitions, procedures, evidence, exceptions, discretion. Downloaded edition can be hashed. | Acquisition.gov is the official FAR site, while the CFR published through OFR/GPO has distinct legal-status conventions. Do not equate every rendering. |
| US-2 | [Acquisition.gov — FAR Part 2, Definitions of Words and Terms](https://www.acquisition.gov/far/part-2), definitions source | Same FAC/effective date as the captured FAR edition. | ~35 pages; accessible HTML; part-level download/print | Same preliminary federal-work basis as US-1. | Compact, addressable glossary for later reference. | Duplicates content within the full FAR; preserve as a separately hashed convenience view only if approved. |
| US-3 | [Acquisition.gov — FAR Part 6, Competition Requirements](https://www.acquisition.gov/far/part-6), exception, justification, and approval source | Same FAC/effective date as captured FAR edition. | ~45 pages; accessible HTML; part-level print/download | Same preliminary federal-work basis as US-1. | Contains explicit competition exceptions, justification content, approval levels, and public-availability requirements. | Applicability exceptions and agency supplements make later case design nontrivial. |
| US-4 | [Acquisition.gov — FAR Part 7, Acquisition Planning](https://www.acquisition.gov/far/part-7), subordinate operating/evidence procedure | Same FAC/effective date as captured FAR edition. | ~55 pages; accessible HTML; part-level print/download | Same preliminary federal-work basis as US-1. | Planning, documentation, approvals, and discretionary determinations. | Duplicates the full FAR; authority and deviations must be kept with the captured edition. |
| US-5 | [Acquisition.gov — General Services Administration Acquisition Manual](https://www.acquisition.gov/gsam/general-services-administration-acquisition-manual-gsam), agency supplement/manual | Observed Change 200 Wave 2, effective 2026-06-13. Applies within GSA; it does not replace the FAR. | ~260 pages; HTML and downloadable edition/archive | Preliminary federal-work basis; screen incorporated third-party material. | Agency-level procedure and approval/delegation detail, including [GSAM 504.7104](https://www.acquisition.gov/gsam/504.7104) review and approval requirements. | GSA-only overlay. The full current change package and effective dates must be pinned. |
| US-6 | [Federal Register — FAC 2026-01 trade-agreement threshold final rule](https://www.federalregister.gov/documents/2026/03/13/2026-04912/federal-acquisition-regulation-trade-agreements-thresholds), amendment source | Final rule associated with FAC 2026-01; effective date stated as 2026-03-13. Official Federal Register PDF/XML should be acquired from OFR/GPO. | ~8 pages; HTML, PDF, XML | Federal Register government text is generally a US Government work; screen attachments and incorporated material. | Strong official amendment provenance and effective-date evidence. Stable document number supports immutable acquisition. | Confirm final published URL/document number and correction notices during acquisition; public-inspection copy is not the final published edition. |
| US-7 | [Acquisition.gov — GSAM archive](https://www.acquisition.gov/browse/index/gsam), archived/historical procedure, including Change Order 116 | Historical change packages allow comparison with current GSAM and can expose prior approval tables. | ~47 pages for selected Change Order 116 package; PDF | Preliminary federal-work basis; page-level screening still required. | Honest stale procedure candidate; archive and change order make supersession explicit. PDF can be hashed. | Select one exact archived package only after confirming its dates, affected sections, and replacement chain. Historical content may remain relevant to older acquisitions. |

### Coverage assessment

- Primary rule/policy: US-1.
- Definitions/glossary: US-2.
- Approval/delegation: US-3 and GSA-specific US-5.
- Amendment/supersession: US-6 and FAC metadata.
- Subordinate procedure: US-4 and US-5.
- Potentially stale/conflicting procedure: US-7.
- Evidence requirements: US-3 through US-5.
- Exception/discretion: US-3 and multiple FAR parts.
- Transaction feasibility: High in content breadth, but the source volume,
  agency overlay, deviation system, and edition status make a seven-day slice
  riskier and less manageable.

## 5. Rights and redistribution analysis

### Canada

The [Open Government Licence — Canada](https://open.canada.ca/en/open-government-licence-canada)
permits worldwide, royalty-free, perpetual, non-exclusive use, including
copying, modification, publication, translation, adaptation, distribution, and
commercial use, subject to attribution and other conditions. It excludes or
qualifies material such as third-party rights, personal information, official
marks, and content not made available under the licence. Accordingly:

- Official availability does not itself prove that every embedded asset is
  licensed.
- Redistribution appears permitted for the identified government-authored
  source text after page-level rights screening and attribution planning.
- The legal reuse basis is separate from whether a TBS, Justice Laws, or PSPC
  source is institutionally authoritative or currently effective.

### United Kingdom

The [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
generally permits copying, publication, distribution, adaptation, commercial
and non-commercial exploitation of covered information, subject to attribution
and exclusions. The UK Government Licensing Framework identifies the OGL as the
default licensing model for Crown bodies. Accordingly:

- Legislation.gov.uk and GOV.UK materials appear redistributable where their
  page notices place them under OGL and no exclusion applies.
- Royal arms, departmental logos, personal data, third-party rights, and other
  excluded material require screening.
- A GOV.UK publication can be officially available and reusable without having
  the institutional authority or current effectiveness of legislation.

### United States

[17 U.S.C. §105](https://www.copyright.gov/title17/92chap1.html#105) states that
copyright protection is not available for a work of the United States
Government, while permitting the Government to receive and hold transferred
copyrights. [GovInfo’s policies](https://www.govinfo.gov/about/policies) caution
that public government documents can contain protected third-party material.
Accordingly:

- Federal-authored regulatory text appears redistributable in the United States.
- Logos, photographs, standards incorporated by reference, contractor-authored
  material, and other third-party content require item-level screening.
- Public-domain status does not establish that a web rendering is authoritative,
  current, or the legally controlling edition.

No pack should be redistributed until acquisition records the exact licence or
public-domain basis for every captured file and resolves embedded third-party
content.

## 6. Authority and effective-date analysis

| Candidate | Official availability | Legal reuse basis | Institutional authority | Current effectiveness |
|---|---|---|---|---|
| Canada | All seven source units are publicly reachable, although some linked historical/delegation material is intranet-only | Preliminary OGL-Canada basis; verify every asset | Justice Laws regulations and TBS policy instruments have higher authority than PSPC operating guidance | Explicit dates are strong; archived Supply Manual is intentionally not current, and current Buyer’s Portal pages remain mutable |
| UK | Legislation and policy guidance are public | Preliminary OGL basis; verify notices/exclusions | Acts and statutory instruments are distinct from Cabinet Office guidance and PPNs | Must reconstruct commencement/savings and old/new procurement regime; publication update date is not necessarily legal effective date |
| US | FAR, GSAM, Federal Register, and archives are public | Preliminary federal-government-work basis; screen third-party content | CFR/Federal Register status, FAR Council issuance, and agency supplement/manual status must remain distinct | FAC, GSAM change, and final-rule effective dates can differ; archived rules may apply to older acquisitions |

## 7. Acquisition risks

1. **Mutable HTML:** TBS, GOV.UK, CanadaBuys, and Acquisition.gov pages may
   change without a new stable URL. A later acquisition must record timestamp,
   resolved URL, headers where available, bytes, rendering method, and SHA-256.
2. **Edition ambiguity:** Consolidations and web renderings may be official
   publication services without being the evidentiary “official version.”
3. **Incomplete histories:** Canada’s older Supply Manual versions and individual
   delegations are partly intranet-only. GOV.UK update histories may not expose
   all prior bytes. US operational changes span FACs, change orders, deviations,
   and agency supplements.
4. **Third-party content:** Open licences and US public-domain rules do not
   automatically cover incorporated standards, images, contractor material,
   logos, or linked content.
5. **Applicability boundaries:** UK transitional savings, Canadian
   department-specific delegation, and US agency overlays can make a document
   current yet inapplicable to a particular transaction.
6. **Page estimates:** HTML print pagination is renderer-dependent. Exact
   acquisition size remains unresolved.
7. **Accessibility:** The selected primary pages are generally accessible HTML
   or tagged government PDFs, but formal WCAG/PDF-UA testing has not been done.
8. **Scope creep:** Portal crawls and full regulation sets could exceed the
   seven-day slice. Every acquired URL must be explicitly enumerated.

## 8. Rejected candidates and reasons

These were considered at screening level and rejected before full pack
construction:

- **European Union institutions:** excellent EUR-Lex authority and reuse
  infrastructure, but the requested one-jurisdiction constraint is harder to
  preserve across EU rules, member-state implementation, and actual delegation
  practice.
- **Australia — Commonwealth:** strong official legislation and guidance, but
  the whole-of-government copyright/licensing position must be checked
  publication by publication; the screening result was less clear than Canada’s
  OGL.
- **New Zealand central government:** promising open-licence and rule/guidance
  sources, but a compact public delegation/approval matrix and an honest stale
  procedure pair were not established within this research window.
- **US state or municipal procurement:** could provide a smaller corpus than the
  FAR, but rights, archive quality, authority hierarchy, and local delegation
  publication vary substantially. No single jurisdiction clearly outranked the
  three completed packs under the ordered criteria.

“Rejected” means not recommended for this seven-day slice, not unsuitable for
future research.

## 9. Unresolved questions requiring Arkadiy’s decision

1. Approve Canada federal procurement as the sole acquisition target for the
   seven-day experimental slice, or request a different pack.
2. Decide whether the public TBS Appendix A approval limits are sufficient for
   the experiment despite individual PSPC delegations being partly intranet-only.
   If not, the pack should remain a candidate and acquisition should pause.
3. Approve treating separately addressable mandatory appendices as distinct
   source units while preserving their dependency on the exact parent directive
   capture.
4. Approve a bounded enumeration of Buyer’s Portal and archived Supply Manual
   sections, rather than an uncontrolled site crawl.
5. Decide whether redistribution is required for the experiment or whether the
   repository should contain only hashes, metadata, and official URLs. This memo
   does not authorize either approach.
6. Identify who will perform final rights review and determine the required
   attribution form before any source files are committed.
7. Decide whether English-only captures are acceptable where Canada’s official
   instruments are also available in French and the two language versions are
   equally authoritative.
8. Decide the authoritative acquisition timestamp/cutoff. Live pages observed on
   2026-07-29 can change before authorized acquisition.
9. Decide whether the archived Supply Manual should be limited to Chapters 1, 4,
   6, and its glossary, or include the complete advertised HTML download.

## Research limitations

- Research used public official websites and their visible metadata as of
  2026-07-29. No source document was downloaded into the repository.
- No legal opinion is offered on copyright, licensing, authority, effect, or
  applicability.
- No provision was interpreted and no transaction outcome was assigned.
- Estimated page counts and effort are planning figures requiring
  acquisition-time verification.
- No claim is made that corpus provenance is complete.
