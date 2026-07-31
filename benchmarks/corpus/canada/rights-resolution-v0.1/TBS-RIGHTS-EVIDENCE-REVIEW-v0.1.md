# TBS Rights Evidence Review v0.1

Status: **WORKSHEET_UNPOPULATED_PENDING_RECAPTURE**

Applies to: CA-1, CA-2, CA-4. Depends on `TBS-TERMS-RECAPTURE-PROTOCOL-v0.1`.

**Precondition.** No cell may be completed until the recapture protocol has executed successfully and the captured notice carries a byte length, a SHA-256 and a SHA-512.

**Fail-closed rule.** A dimension whose answer is not stated unambiguously by the captured notice is recorded UNRESOLVED. UNRESOLVED never supports a CLEAR disposition.

Allowed findings: `SUPPORTED`, `NOT_SUPPORTED`, `UNRESOLVED`.

Every completed cell must carry: `dimension`, `finding`, `evidence_id`, `evidence_sha256`, `quoted_clause`, `reviewer_identity`, `review_utc`, `rationale`.

## Worksheet

| Dimension | Question | Evidence to examine | Finding |
|---|---|---|---|
| `internal_research_use` | May the exact bytes be retained and read inside Veraxis for research? | Non-commercial reproduction clause and any stated exclusion. | **UNRESOLVED** |
| `automated_retrieval` | May a named automated tool request these URLs? | The robots policy captured for the host, plus any terms clause addressing automated access. | **UNRESOLVED** |
| `machine_processing` | May the bytes be parsed, indexed, hashed and diffed by machine? | Any clause addressing format, adaptation, or permitted reproduction media. | **UNRESOLVED** |
| `internal_only_storage` | May the bytes persist in a gitignored internal evidence area? | Whether the reproduction permission is conditioned on publication or is silent on storage. | **UNRESOLVED** |
| `public_repository_redistribution` | May the exact bytes be committed to a public repository? | The commercial-redistribution clause and whether a public repository of undetermined licence can be characterized as non-commercial. | **UNRESOLVED** |
| `attribution` | What attribution must accompany a reproduction? | The enumerated conditions: accuracy, complete title and author, and a statement that the reproduction is a copy of the version available at the original URL. | **UNRESOLVED** |
| `modification_restrictions` | What changes to the reproduction are prohibited? | The accuracy due-diligence condition and any prohibition on altered reproductions. | **UNRESOLVED** |
| `third_party_material` | Does the page carry material whose copyright is not held by the Crown? | Any third-party copyright clause, plus page-level ownership notices. | **UNRESOLVED** |
| `personal_information` | Does the page carry personal information such as names or contact details? | Presence of individual names, roles, telephone numbers or e-mail addresses in the bytes. | **UNRESOLVED** |
| `logos_insignia_trademarks` | Does the page carry official symbols, and may they be reproduced? | The trademark clause covering the Canada wordmark, the Arms of Canada and the flag symbol, and whether markup references or embeds them. | **UNRESOLVED** |

Every finding is `UNRESOLVED` because: Recapture has not been executed; no notice bytes exist to review.

**Disposition gate.** CLEAR_INTERNAL_FREEZE_ONLY requires internal_research_use and automated_retrieval both SUPPORTED. CLEAR_REPOSITORY_FREEZE additionally requires public_repository_redistribution SUPPORTED. Anything short of that leaves the source BLOCKED_PENDING_CLEARANCE.

Current disposition of all three sources: **BLOCKED_PENDING_CLEARANCE**.

This worksheet records engineering findings about what captured evidence states. It is not legal advice and does not substitute for the counsel review.

