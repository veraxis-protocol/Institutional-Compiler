# OIC↔ZTL Layer Ownership 001

**Date:** 2026-09-07 · **Base:** `main` at `c4a325c5`, tree `b8e31ec4` · **Status:** architecture
description, not a decision record. It describes ownership as it stands; it creates no
authority and admits nothing.

This document answers one question for each semantic act in the pipeline: **which layer owns
it, and what artifact in this repository shows that.** Two rows have no owner. Naming them is
the point of the document.

## 1. Ownership of each semantic act

| Question | Owning layer | Where it lives here |
|---|---|---|
| What source bytes existed? | OIC | `source_id` / `source_version` / `source_digest` on every admission receipt; `schemas/draft/source-document.schema.json`, `source-node`, `source-anchor` |
| What candidate spans were proposed? | OIC extraction | `src/oic/candidate_extraction.py`; `schemas/draft/candidate-normative-unit.schema.json` |
| Are **candidate** proposals divergent? | OIC review docket | `src/oic/review_docket.py` — `AgreementState` ∈ {`NO_CANDIDATES`, `IDENTICAL`, `DIVERGENT`} |
| Is institutional authority evidence sufficient? | OIC admission | `src/oic/admission.py`; `design/admission-boundary-001/ADMISSION-CONTRACT-v0.1.md` |
| **What meaning was institutionally admitted?** | — **no owner** | assigned in prose to a *"Future Institutional IR construction stage"*; no code, no receipt, no state |
| **What formal proposition represents that admitted meaning?** | — **no owner** | ADR-002 names Institutional IR as the canonical admitted representation; `schemas/draft/institutional-ir.schema.json` types `nodes` as `{"type":"object"}` and carries no formula |
| What grounds are verified / unverified? | supplied evidence state | `docs/contracts/kernel-profiles/ztl-v0.1.json` → `unverified_ground_semantics`; ADR-013 W-5, W-12 |
| What follows without granting truth on credit? | ZTL | ADR-009; profile `entrypoint: ztljudge.judge` |
| Is the conclusion earned, refuted, on-credit, or open? | ZTL | profile `disposition_values`; ADR-013 §3.1 |
| Is the result institutionally authorized for this purpose and epoch? | OIC | ADR-013 §2.2 `decision_basis`; `docs/contracts/WARRANT-CONTRACT-v0.1.md` |
| May software execute an action? | downstream authority / runtime — **not ZTL** | ADR-013 §2.2 `execution_disposition`; ADR-009 forbids ZTL deciding ALLOW/BLOCK/ESCALATE |
| Is execution integrity established? | VEIP | ADR-010; `docs/contracts/VEIP-CODE-START-BOUNDARY-v0.1.json` (non-executable); ADR-013 §4 |
| Does historical consequence retain current standing? | OAM / Authority-VM boundary | **not found in this repository.** Reported as *not found*, which is not *absent* |

## 2. A scope distinction that is easy to miss

`review_docket.py` looks like the organ that reviews interpretations. It is not. It consumes
`CandidateExtractionResult` — candidate **spans** — and never sees an
`InterpretationProposalResult`. Its own docstring states it *"never votes, selects an
authoritative interpretation, records admission, or advances candidate state."*

The word *proposal* denotes two different objects in this tree: a proposed span and a proposed
interpretation. The docket is upstream of interpretation, not downstream of it. **Divergence
among interpretation proposals has no owner**, which is a third consequence of the two unowned
rows above: nobody is appointed to accept an interpretation, and nobody is appointed to notice
that two interpretations disagree.

## 3. Currentness ownership — the rule

> **ZTL may reason over supplied epoch, expiry, revocation and currentness facts. ZTL does not
> create institutional currentness, validity, expiry authority or revocation authority.**

This is an **ownership rule**, not a claim about the logic. It asserts no theorem, and no ZTL
result is offered in support of it. It follows the boundary already drawn in ADR-009 —
which prohibits ZTL from determining authority — and makes explicit what that boundary implies
for currentness specifically, where the implication had not been written down.

Consistent with it, and already stated in ADR-013 §3.3:

- expiry is **scoped, never global**: `valid_until` is per artifact and `revocation_references`
  are per ground; unrestricted expiry would make every warranty invariant trivially true;
- `hereditary` is absorbing **only** under monotone refinement. It waives re-checking on
  nothing else — not expiry, revocation, correction, source invalidation, schema change,
  formula change, semantic-version change, or institutional admissibility.

**No ADR text was rewritten to add this rule.** It is stated here because it is an ownership
statement, and this is the ownership document. If normative consistency later requires it to
appear in an ADR, that is a separate change with its own justification.

## 4. Complexity as a ceiling, not a citation

Minimality of a repair or recheck set is **not claimed** in this repository, deliberately and
in three places: `docs/contracts/WARRANT-CONTRACT-v0.1.md` (*"Minimality is not claimed,
deliberately"*, measured in 38 of 180 census cases), the kernel profile (*"NOT claimed. This is
a deliberate over-approximation"*), and `docs/contracts/ZTL-OCE-MAPPING-v0.1.json` (*"Neither
array claims minimality"*).

`SUFFICIENT` and `MINIMAL_IF_ESTABLISHED` must remain distinct wherever a repair certificate is
eventually emitted. **NP-completeness is not claimed anywhere**: hardness is not membership,
and no claim here rests on one standing for the other.
