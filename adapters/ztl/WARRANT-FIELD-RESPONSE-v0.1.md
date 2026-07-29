# Warrant field feasibility response — v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable D.
**Status: AWAITING INPUT.** The requested OIC warrant-field list is not yet present in the repository.

---

## 1. Why this deliverable is not complete

The work order says: *"Review the proposed OIC warrant fields **once the Claude PR is available**."* As of `main` at `141ec2b` and the open PRs (#13, #14, #15), no document specifying warrant fields exists in the repository. Searched: `docs/`, `schemas/`, `adapters/`, and the files of every open PR.

We are not going to guess a field list and mark our own invention NATIVE. That would produce a feasibility answer to a question nobody asked, and it would be the sort of self-supplied evidence this project is built to refuse.

**When the field list lands, this document will be completed with one row per requested field**, marked `NATIVE` / `DERIVABLE` / `OIC-ENRICHED` / `UNSUPPORTED` / `REQUIRES ZTL CHANGE`.

## 2. What the kernel emits today, so the review can be quick when it starts

Every `judge()` call returns exactly these fields. This is the whole surface; anything not listed here is not available without a ZTL change.

| Field | Type | Meaning | Stability |
|---|---|---|---|
| `formula` | string | the parsed formula, normalised | stable within an epoch |
| `verdict` | `"T"` / `"F"` / `"Z"` | raw truth state — **internal detail, not the operational answer** | stable |
| `grade` | `hereditary` / `sound` / `until-verification` | warranty grade | stable |
| `disposition` | `EARNED` / `REFUTED` / `ON CREDIT` / `OPEN` | the operational signal | stable |
| `unverified` | list of atom identifiers | exactly which grounds block or carry the conclusion | stable |
| `marking` | map atom → `T`/`F`/`Z` | the input marking, echoed | stable |
| `why` | string | human-readable justification | **presentational — do not parse** |

Anticipated classifications, offered now to save a round trip (each is provisional until the real list arrives):

| Likely OIC need | Expected classification | Note |
|---|---|---|
| logical verdict / disposition | **NATIVE** | `disposition` is the field to consume |
| warranty qualifier | **NATIVE** | `grade` |
| blocking grounds / `missing_inputs` | **NATIVE** | `unverified`, as atom identifiers |
| stable atom identifiers for enrichment | **NATIVE** | atom names are supplied by the caller and echoed verbatim; the kernel neither invents nor rewrites them |
| dependency set for change impact | **DERIVABLE** | from `unverified` plus the formula's atom set |
| recomputation trigger | **DERIVABLE** | see the transition table in `proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md` |
| source-document anchor | **OIC-ENRICHED** | the kernel never sees sources — by design, per §6.2 of the dossier |
| admission reference | **OIC-ENRICHED** | admission is OIC's plane |
| authority chain | **OIC-ENRICHED** | not a ZTL concept |
| effective period / expiry clock | **OIC-ENRICHED** | ZTL has no clock; it computes consequences of expiry, it does not schedule it |
| warrant artifact digest | **REQUIRES ZTL CHANGE** *(small)* | the connector already canonicalises (RFC 8785 subset) and digests with SHA-384 for the warrant-form/verdict-artifact pair; exposing a per-`judge()` digest is a minor addition, not a semantic change |
| epoch identifier | **REQUIRES ZTL CHANGE** *(small)* | the kernel is stateless and has no epoch concept; it can echo an epoch id supplied by the caller, but it cannot originate or validate one |
| legal validity, authority sufficiency, ALLOW/DENY | **UNSUPPORTED** | outside the boundary; asking for them would widen ZTL's role, which the work order itself prohibits |

## 3. The constraint the work order states, and our confirmation

> *"The ZTL kernel is not required to emit source-document or admission anchors. It must emit stable atom or ground identifiers sufficient for OIC enrichment."*

**Confirmed, and already satisfied.** Atom identifiers are supplied by the caller, echoed unchanged in `marking` and `unverified`, and never rewritten or normalised away by the kernel. OIC can therefore key its enrichment on them.

One condition applies, and it is on OIC's side: **the caller owns atom identity**. If the same identifier is re-pointed at a different source clause, the kernel cannot detect it and will report a verdict for a different question under the old name. See `proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md` §1.2.

## 4. One correction we must flag before the field review begins

The ZTL dossier v0.1 listed three dispositions — EARNED / REFUTED / OPEN — and **omitted `ON CREDIT`**. There are four. `ON CREDIT` is a T verdict that is **not** `hereditary`: true only while an unverified atom holds, and able to die when that atom resolves.

Any warrant-field design or mapping written against the three-value list will silently misclassify these cases, most likely as EARNED, and thereby authorise action on credit — the exact failure ZTL exists to expose. Both real cases are fixtured: `on-credit-sound`, `on-credit-until-verification`.

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the OIC semantic implementation gate remains BLOCKED.*
