# OIC↔ZTL DARPA Crosswalk 001

**Date:** 2026-09-07 · **OIC base:** `c4a325c5` · **ZTL base:** `8ab40b23`.

**No DARPA hypothesis is moved from UNTESTED by this document.** Component maturity is not
evidence about a seam. Nothing here is an independent review.

## 1. Three levels of falsifiability, kept separate

| Level | What a falsifier attacks | Available today |
|---|---|---|
| **COMPONENT** | one side's machinery in isolation — the admission runtime, or the logic kernel | **yes, both sides** |
| **SEAM** | a transition between two institutional objects | **no** — the transitions are not performed |
| **END-TO-END** | source bytes → executed authority, as one chain | **no** — requires every seam |

**Component falsifiability ≠ seam falsifiability ≠ end-to-end falsifiability.** None may be
promoted to another. This distinction is the document's organising rule, not a caveat attached
to it.

## 2. The six dependency families

| Family | OIC owner | ZTL role | Evidence grade | Falsifier available | Open gap |
|---|---|---|---|---|---|
| **evidence** | admission plane — receipts binding source digests, ordered authority evidence, ruleset digest, evaluator identity | none; ADR-009 forbids ZTL authenticating a source | **MEASURED** | **component:** mutate one evidence byte or reorder the array; the digest must change and the state must fail closed | none at component level |
| **semantics** | **unowned** | would consume a canonical formal object; none exists | **OPEN** | **none constructible** — a non-faithful formalization cannot be exhibited where no formalization is performed | the three transitions |
| **admission** | admission runtime — 15 frozen terminal states, frozen reason codes | none; ADR-009 forbids ZTL creating admission | **MEASURED**, for *candidate* admission | **component:** supply stale, out-of-scope, superseded or conflicting evidence; require the declared state in frozen precedence | admission **of meaning** is a different act and does not exist |
| **currentness** | institutional state — expiry, supersession, revocation | may reason over supplied epoch facts; may not create currentness | **ARGUED** — the rule is stated, not measured | **component:** revoke a ground after a favourable result; standing must fall | no path could carry currentness across the missing seam |
| **memory** | VEIP / OAM boundary | none | **PROPOSED** — the VEIP boundary is declared non-executable | **not constructible** while non-executable | no OAM or Authority-VM artifact in this repository (*not found*, which is not *absent*) |
| **authority** | control plane — execution disposition, decision basis, declared minimum grade, unverified-ground policy | ends at disposition, grade, formula and dependency information, verified and unverified grounds, epoch information, recomputation evidence; decides no ALLOW/BLOCK/ESCALATE | **PROPOSED**, with MEASURED sub-results | **component:** drive a fixture whose raw verdict and disposition disagree; the decision must follow the disposition | nothing consumes it at runtime |

## 3. A seventh failure surface: dependency reference continuity

Distinct from the semantic blocker and not to be listed beside it:

    dependency object survival
      ≠ dependency-reference continuity
        ≠ declared-profile reproducibility

| | Question | Observed 2026-09-07 |
|---|---|---|
| object survival | does the pinned object still exist anywhere? | **yes** throughout |
| reference continuity | does a published reference reach it, so an ordinary clone obtains it? | **no**, until a dated recovery tag was created; **yes** after |
| declared-profile reproducibility | do the references the frozen profile *declares* resolve? | **no**, still — the declared tag names remain absent |

A dependency can be perfectly preserved, byte-identical and signed, and still be unreachable by
the route its own contract names — while every party's local checkout looks green and only a
fresh reproducer sees nothing. **The defect is invisible from the owner's side by
construction.** It was detected only because a measurement was re-taken from a fresh clone
rather than from a working copy.

**Falsifier:** clone the published dependency repository from scratch and resolve every
reference the consuming contract declares. Any that fails to resolve is a continuity break,
whether or not the object survives by explicit hash.

**This changes no claim.** Reachability restored is **not** reproduction, and
`tier_1_reproduction` remains **NOT ESTABLISHED**.

## 4. Which ZTL capabilities are usable as T&E instruments now

**Usable, at component level:** the axiom census (re-runnable, and able to fail); the
reconvergence measurement, which states its denominator; the frozen interface fixtures,
including retained not-reachable defensive rows; and the disposition/grade vocabulary as a
classification instrument over supplied results.

**Not instruments — research questions:** anything requiring an admitted proposition or a
canonical formula; seam-level or end-to-end falsification of dependency continuity; minimality
of a repair set; ground identity under equal content; and the large-scale dependency-graph
representation, which is **not** designed here.

## 5. Two negative controls that remain genuinely open

| | Requirement | Status |
|---|---|---|
| **KILL-Z8** | a future component must not emit `MINIMAL` unless minimality is separately established | **OPEN / UNGUARDED** — minimality is refused by declaration in three places, but nothing prevents emission |
| **KILL-Z9** | equal-content grounds must not be deduplicated without an established identity rule | **OPEN / UNGUARDED** — no artifact here settles ground identity under equal content |

They are not testable yet: there is no component to refuse. They become executable negative
controls when a relevant component exists. **No test is fabricated against a component that
does not exist.**

## 6. The strongest result, stated as a result

> Some failure surfaces cannot yet be falsified, because the institutional object or transition
> whose failure would be tested does not yet exist.

That is a finding about the architecture, not an embarrassment and not an incomplete audit. The
value of the boundary described in `docs/architecture/OIC-ZTL-MATURATION-DELTA-001.md` is
precisely that it says **which** surfaces already have a witness and which cannot have one yet.

## 7. What must not be written from this document

- that any seam-level or end-to-end defect is measurable today;
- that component maturity constitutes seam or end-to-end evidence;
- that this constitutes independent review;
- that Tier-1 reproduction is established.
