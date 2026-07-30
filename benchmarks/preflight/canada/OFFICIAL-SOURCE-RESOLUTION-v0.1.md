# Canada Official-Source Resolution v0.1

Status: **PROPOSED METADATA EVIDENCE — NO ARTIFACT ACQUISITION**

Observed: 2026-07-30 UTC.

This document separates an owner/architecture decision from observed HTTP
metadata, preliminary rights evidence, and unresolved matters. It records no
source bytes, provision meaning, modality, clause, control, or semantic
admission.

## Owner/architecture decision: CA-3 representation

The official current consolidated XML is the one canonical machine-readable
artifact for a later authorized acquisition. The official PDF is a secondary
human-review rendering. The English and French XML renderings and the
bilingual PDF are language/rendering expressions of the same regulation, not
separate independent authorities.

| Role | Language | Official URL | Observed status | Content type | Relationship |
|---|---|---|---:|---|---|
| canonical artifact | English | https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml | 200 | text/xml | Canonical future hash input |
| canonical artifact language rendering | French | https://laws-lois.justice.gc.ca/fra/XML/DORS-87-402.xml | 200 | text/xml | Same authority; not an additional canonical artifact |
| secondary official rendering | bilingual | https://laws-lois.justice.gc.ca/PDF/SOR-87-402.pdf | 200 | application/pdf | Human-review rendering only |
| current-consolidation index | English | https://laws-lois.justice.gc.ca/eng/regulations/sor-87-402/ | 200 | text/html | Artifact discovery and current/amended metadata |
| current-consolidation index | French | https://laws-lois.justice.gc.ca/fra/reglements/DORS-87-402/ | 200 | text/html | French index for the same authority |
| version metadata | English | https://laws-lois.justice.gc.ca/eng/regulations/sor-87-402/PITIndex.html | 200 | text/html | Official previous-version ranges |

The official index exposed the XML, PDF, and Previous Versions links. HEAD
observations at 2026-07-30T16:38:23Z through 2026-07-30T16:38:24Z showed no
redirect for these artifact and version-metadata URLs. No XML or PDF body was
retrieved by the acquisition utility or committed.

## Observed official-source metadata

The acquisition utility ran in metadata-only mode for all 11 selected English
source IDs. Each returned HTTP 200 and the expected `text/html` content type.
All redirect chains were empty. Eleven canonical receipts were written only
under `.local/canada-preflight-receipts/`, which is gitignored.

The six formerly unresolved French URLs were obtained from the official
English pages’ `fr (Français)` language-selection links. The four CA-5
requested URLs on `canadabuys.canada.ca` redirected once, in observed order,
to the corresponding final URLs on `achatscanada.canada.ca`. The CA-6 French
URLs were directly requested on `achatscanada.canada.ca` and did not redirect.
Exact URLs and observations are recorded in
`FRENCH-COUNTERPARTS-v0.1.json`.

This evidence confirms a published language relationship only. It does not
test or attest bilingual semantic equivalence.

## CA-6 enumeration

Seven proposed nodes are enumerated in `WORKING-SET-SCOPE-v0.1.md`: the
archive notice plus sections 6.1, 6.5, 6.5.5.5, 6.5.5.10, 6.5.20, and 6.20.
The rendered official metadata did not expose durable fragment identifiers,
so the visible section numbers are recorded as node identifiers.

No selected node supplied evidence of a direct glossary link. Therefore zero
glossary entries remain in the working set. The revised total is 55
print-equivalent pages. CA-7 remains excluded.

## Preliminary rights evidence

The official Government of Canada terms page provides a conditional
non-commercial reproduction basis, restricts commercial redistribution
without prior written permission, warns that third-party copyright may apply,
and restricts reproduction of official symbols. These findings support only
the preliminary classifications in `RIGHTS-PREFLIGHT-v0.1.md`.

The CA-3 official consolidation includes a notice about the evidentiary status
of Minister-published consolidations and the priority of the original
regulation or registered amendment in case of inconsistency. That is recorded
as official legal-text provenance evidence, not a legal conclusion about
redistribution.

## Unresolved matters

- Source-level exceptions and third-party ownership must still be screened
  against exact later-acquired bytes.
- Commercial redistribution permission remains restricted and unresolved.
- Official symbols and page chrome must be excluded or separately authorized
  before any proposed byte publication.
- Contact details and individual-role references on CA-5/CA-6 require a later
  exact-byte personal-information screen.
- No bilingual semantic-equivalence review has occurred.
- No acquisition freeze, manifest population, source-byte publication, or
  semantic admission has occurred.
