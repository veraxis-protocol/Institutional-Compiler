# CDC-CORPUS-CLOSURE-001

## Owner-authorized corpus re-scope

**Decision date:** 2026-08-17  
**Baseline:** `ztl/currentness-slice-001-frozen-design` at `37a8ab15d5dadf2fd521578982792494b0bddf87`  
**Decision class:** source-scope and rights-posture decision only  
**Semantic implementation gate:** unchanged / BLOCKED

## 1. Controlling constraints

This decision does not authorize semantic interpretation, annotation, benchmark execution, CDC-S1 execution, ZTL/OAM result-bearing execution, RUN-004, relaxation of any `BLOCKED_PENDING_CLEARANCE` disposition, silent source substitution, or `STATUS.md` modification.

Historical rights and acquisition records remain immutable. A source previously recorded as `BLOCKED_PENDING_CLEARANCE` remains blocked in that historical record.

## 2. Decision

Path B is selected at the source-scope level.

The first Canada benchmark working set is explicitly re-scoped away from the CanadaBuys Buyer’s Portal / archived Supply Manual source family and onto Treasury Board of Canada Secretariat policy-instrument sources that preserve the preregistered structural coverage without requiring CanadaBuys automated acquisition.

The following legacy working-set units are **REMOVED FROM THE REBASELINED WORKING SET ONLY**; their historical rights dispositions are not changed:

- `CA-5-APPROVALS`
- `CA-5-DELEGATION`
- `CA-5-SIGNING`
- `CA-5-LIMITS`
- `CA-6-ARCHIVE`
- `CA-6-CH6`
- `CA-6-GLOSSARY`

The following existing units remain in scope:

- `CA-1` — Directive on the Management of Procurement: bounded scope, definitions, authority and effective-date context.
- `CA-2` — Appendix A: Contracting Approvals: selected public approval tables and attached conditions.
- `CA-3` — Government Contracts Regulations (SOR/87-402): canonical consolidated XML plus existing version metadata.
- `CA-4` — Appendix F: selected evidence, approval, record and accountability provisions.

The following substitute units are added to the proposed working set, subject to a successor rights-clearance record before acquisition:

- `CA-8` — Guide to the Proactive Publication of Contracts, current TBS policy guidance.  
  English: `https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32763&section=html`  
  French: `https://www.tbs-sct.canada.ca/pol/doc-fra.aspx?id=32763&section=html`
- `CA-9` — Rescinded [2023-06-23] Guidelines on the Proactive Disclosure of Contracts, archived TBS operating guidance.  
  English: `https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=14676&section=HTML`  
  French: `https://www.tbs-sct.canada.ca/pol/doc-fra.aspx?id=14676`

No substitute source is silently admitted: CA-8 and CA-9 are named here and remain pending rights clearance.

## 3. Coverage preservation

The re-scoped source family preserves the preregistered structural coverage without assigning meaning to any provision:

| Required corpus structure | Re-scoped source family |
|---|---|
| Primary procurement policy | CA-1 |
| Definitions / glossary material | CA-1 selected definitions |
| Approval / delegation matrix | CA-2 public contracting approval tables; individual-officer delegation remains outside the benchmark and must yield `UNRESOLVED` where required |
| Amendment / supersession material | CA-1 archive/version relationship; CA-8 identifies the prior guidelines it replaces |
| Conflicting or stale operating procedure | CA-9 archived/rescinded operating guidance paired with CA-8 current guidance |
| Evidence / record requirements | CA-4 and bounded CA-8 reporting/control sections |
| Exception material | CA-3 plus selected CA-2 conditions |
| Discretionary material | selected CA-1/CA-2/CA-4 material, to be identified only during later authorized annotation |
| Later ALLOW / DENY / CANNOT case feasibility | retained as a design requirement only; no case outcome is authorized here |

The working-set allocation is capped below the existing 60 print-equivalent-page ceiling. Exact page/node counts must be measured only after authorized acquisition.

## 4. Rights findings as of this decision

### 4.1 Historical CanadaBuys records

No CanadaBuys rights disposition is relaxed. The prior frozen rights record remains controlling for those legacy source IDs. Their removal from the working set is a scope decision, not a rights finding.

### 4.2 Treasury Board automated retrieval

The current TBS robots policy observed for `www.tbs-sct.canada.ca` permits the general `User-agent: *` crawler group, with a specific exclusion for `/cioscripts/calendar/`. The selected policy-instrument paths are under `/pol/`, not that excluded path. This supports automated retrieval at the transport-policy layer only; it does not itself establish copyright permission.

### 4.3 Treasury Board / Government of Canada reproduction terms

Current Government of Canada terms permit non-commercial reproduction subject to accuracy and attribution conditions, while commercial redistribution requires prior written permission. TBS-specific notices likewise direct requests for Crown copyright clearance to TBS Public Enquiries.

Because this repository is maintained by a commercial entity, this decision does not infer that public-repository redistribution is non-commercial. `CA-1`, `CA-2`, `CA-4`, `CA-8`, and `CA-9` therefore remain **PENDING SUCCESSOR RIGHTS CLEARANCE** for exact-byte acquisition/storage. No `CLEAR_REPOSITORY_FREEZE` or `CLEAR_INTERNAL_FREEZE_ONLY` disposition is created by this decision.

`CA-3` remains governed by its already-frozen rights record and is not re-adjudicated here.

## 5. Closure state

`CDC-CORPUS-CLOSURE-001 = REBASELINED_PENDING_TBS_RIGHTS_CLEARANCE`

Path B is completed at the source-scope level: the CanadaBuys dependency is removed from the benchmark working set and replaced with an explicitly identified TBS current/stale guidance pair that preserves the preregistered structural coverage.

The corpus is **not yet acquisition-complete**. The next blocking action is a successor TBS rights-clearance determination for `CA-1`, `CA-2`, `CA-4`, `CA-8`, and `CA-9`, followed by exact-byte acquisition only if that successor record permits it.

## 6. Evidence observations used for this decision

Official-source observations made on 2026-08-17:

- Government of Canada Terms and Conditions: `https://www.canada.ca/en/transparency/terms.html`
- TBS Important Notices / reproduction terms: `https://www.tbs-sct.canada.ca/cioscripts/in-ai_e.asp`
- TBS Public Enquiries / Crown copyright contact: `https://www.canada.ca/en/treasury-board-secretariat/corporate/contact.html`
- TBS robots policy: `https://www.tbs-sct.canada.ca/robots.txt`
- Current Guide to the Proactive Publication of Contracts: `https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32763&section=html`
- Current French counterpart: `https://www.tbs-sct.canada.ca/pol/doc-fra.aspx?id=32763&section=html`
- Rescinded Guidelines on the Proactive Disclosure of Contracts: `https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=14676&section=HTML`
- French counterpart catalogue evidence: `https://publications.gc.ca/site/eng/9.917981/publication.html`

No source bytes were acquired by this decision.
