# OIC Semantic Code-Start Gate Closure v0.1

Original audit base: `d06917fa6877277d7118b49e80d6a69446f50712`.
The current comparison base is recorded in draft PR #35 after main
reconciliation. `STATUS.md` remains authoritative and unchanged.

## Corrected closure matrix

| Gate | Requirement | Current evidence/status | Smallest next action | Effect |
|---|---|---|---|---|
| OIC-CS-001 | Selected bounded source strategy and complete provenance | CA-3 frozen/rights-cleared but incomplete; other real sources proposed or blocked — OPEN | Owner selects Path A/B; complete selected records | BLOCKS SEMANTIC CODE START |
| OIC-CS-002 | Bounded ZTL profile admitted | Signed pin, 13/3 conformance, corrected mapping, 28 fields, WP-3, SC-WA and triggers — TECHNICALLY ESTABLISHED / OWNER ADMISSION PENDING | Correct stale metadata in admission package; owner accepts/rejects profile and decides Tier-1 timing | BLOCKS SEMANTIC CODE START |
| OIC-CS-003 | Minimum VEIP handoff admitted | Technical non-executable option identified; external heads unadmitted — PARTIAL | Owner accepts minimum boundary or requires full lifecycle | BLOCKS SEMANTIC CODE START |
| OIC-PF-001 | Result-bearing semantic preflight | Gold/runtime/change/adversarial cases and execution-grade lifecycle absent | Complete only after code-start authorization | BLOCKS PREFLIGHT EXECUTION |
| OIC-ER-001 | Reproducible experimental release | Tier-1 disposition and VEIP conformance/security incomplete | Independent/external evidence later | BLOCKS EXPERIMENTAL RELEASE |
| OIC-RF-001 | Full benchmark/maturity | Not run/not established | Defer | BLOCKS RELEASE FREEZE |

## Minimum true blocker set

1. **Source-set owner decision plus provenance completion.**
2. **ZTL profile owner admission**, not new ZTL semantic design; includes stale
   metadata correction and independent-reproduction timing.
3. **Minimum VEIP boundary owner admission**, not completion of the full VEIP
   lifecycle product.

No additional code-start blocker is asserted without an exact governing
requirement.

## Corpus alternatives

**Path A — real Canada clearance:** finish rights, bytes, hashes, receipts,
dates, confidentiality and benchmark authority for the selected real set.

**Path B — mixed public/synthetic code-start set:** subject to owner
authorization, retain CA-3 as the real anchor and create deterministic synthetic
companions for the remaining roles. Each must name a synthetic test institution,
declare synthetic status, carry generated provenance and fixed hashes, create no
real-world authority and support benchmark/test semantics only.

Path B may accelerate code start. It does not establish real-world corpus
completeness, enterprise generalization, superiority or legal validity. Neither
path is executed here.

## Horizon separation

| Horizon | Required state |
|---|---|
| Code start | Selected source path provenance-complete for bounded scope; exact ZTL profile admitted; minimum fail-closed/non-executable VEIP handoff admitted |
| Result-bearing preflight execution | Authorized semantic implementation, gold/metric lineage, runtime cases and execution-grade VEIP lifecycle for the tested path |
| Experimental release | Frozen reproducible preflight, raw results, Tier-1 disposition, VEIP conformance/security and bounded claims |
| Release freeze | Full OIC-Bench/held-out, independent review, usability, security, reliability and maturity gates |

## OWNER DECISIONS REQUIRED TO OPEN BOUNDED SEMANTIC CODE START

### OIC-CS-OD-001 — Source strategy

- **Question:** Continue real Canada clearance or authorize CA-3 plus bounded
  synthetic companions?
- **Option A:** Continue Path A.
- **Option B:** Authorize Path B with its strict claim ceiling.
- **Recommended conservative default:** A unless speed justifies B's limits.
- **Evidence:** provenance report; governing design permits public or synthetic.
- **Authorizes:** provenance work for the chosen path.
- **Still prohibits:** semantic execution and real-world authority/result claims.

### OIC-CS-OD-002 — ZTL profile admission

- **Question:** Accept profile `ztl-v0.1` version `0.1.0`, signed tag
  `veraxis-ztl-input-v0.2-signed`, commit `56e1ff05…`, fixture index
  `ffadd653…` for bounded code start?
- **Option A:** Accept after correcting stale provenance metadata.
- **Option B:** Keep blocked and name precise additional evidence.
- **Recommended conservative default:** A only while provisional boundaries,
  hazards and claim ceilings remain explicit.
- **Evidence:** merged PR #18/#16 and current accepted contracts/review.
- **Authorizes:** bounded semantic code targeting the admitted profile.
- **Still prohibits:** independence/maturity/authority claims and operational
  authorization by ZTL.

### OIC-CS-OD-003 — ZTL independent-reproduction timing

- **Question:** Require Tier-1 before code start or defer it?
- **Option A:** Require before code start.
- **Option B:** Defer to experimental release/release freeze.
- **Recommended conservative default:** B, while all independence claims remain
  prohibited.
- **Evidence:** dossier §13 and v0.2 producer conformance.
- **Authorizes:** timing only.
- **Still prohibits:** calling producer evidence independent.

### OIC-CS-OD-004 — Minimum VEIP boundary

- **Question:** Accept a non-executable review-only handoff for compiler code
  start, or require the full lifecycle first?
- **Option A:** Accept: ActionProposal precedes OIC; OIC consumes exact context
  and emits RuntimeDecision evidence; VEIP does not reinterpret ZTL; neither
  creates the other's authority; missing integration is fail-closed.
- **Option B:** Require the full VEIP lifecycle first.
- **Recommended conservative default:** A for bounded compiler work only, with
  result-bearing execution separately blocked.
- **Evidence:** current warrant contract and ZTL-VEIP preflight; external heads
  remain unadmitted.
- **Authorizes:** bounded compiler contracts without a VEIP execution adapter.
- **Still prohibits:** execution, reliance, lifecycle adapters, operational
  publication and VEIP maturity claims.

## Gate answer

**SEMANTIC CODE-START GATE: BLOCKED — OWNER DECISIONS NOW ISOLATED**

