# ZTL current state — 001

**Date:** 2026-09-07. This file records what ZTL is **now**, beside the v0.1/v0.2 dossier and
conformance material in this directory, which describe a July state and are retained unchanged.

**Reading discipline.** A module's existence and theorem count is **not** a reading of its
statements. Below, *read* means the source was opened in the pass that produced this file;
*counted* means only the census figure is asserted. Nothing here upgrades a claim on the
strength of a file name.

## Pin

| | |
|---|---|
| repository | `https://github.com/inventor1975/ZTL` |
| branch | `master` |
| HEAD | `8ab40b23546eb9fd5a4fd8cc22e94282ce2a7a44` |
| tree | `0efbd9cb6852a214bc653477454639a5f378a1ce` |

The **frozen kernel profile pins a different, older commit** — `56e1ff05`, July — and that is
correct and deliberate: this file is not a re-pin. See
`docs/architecture/OIC-ZTL-MATURATION-DELTA-001.md` §5.

## Census — measured 2026-09-07

ZTL's own inventory tooling reports, verbatim:

    ALL CLEAN: 1112 theorems across 66 modules, every one on the empty axiom list.

**Anticipating the arithmetic.** A plain count over the sources disagrees — 67 `.lean` files and
1118 `theorem`/`lemma` line-starts. Both differences are explained and neither is an exclusion:

- **67 vs 66 modules:** one file contains zero theorem or lemma declarations; it is an
  evaluation script, contributing a file and no theorem.
- **1118 vs 1112 declarations:** the six extras are English prose **inside block comments**
  that happen to begin with the word *theorem* or *lemma*. The inventory tool skips block
  comments deliberately; its own source records that exact bug being caught earlier, with one
  of these six lines as the example.

Separately and unrelatedly, classical proofs of the `F:∀` rule **are** held outside the
theorem corpus, in a probes directory that is not part of the module set. That is a real
exclusion — but those files were never inside the counted scope, so they explain none of the
six. The two facts are both true and neither explains the other.

**The figure to use is 1112 / 66.**

## Modules the current interface work depends on

| module | theorems | this pass |
|---|---|---|
| `ZCutElim` | 103 | counted |
| `ZProv` | 35 | counted |
| `ZNaN` | 25 | counted |
| `Linear` | 22 | counted |
| `RelianceBridge` | 19 | counted |
| `LabelExactDefinite` | 19 | counted |
| `LabelExact` | 17 | counted |
| `ZHeredTaut` | 17 | counted |
| `ContextClosure` | 12 | counted |
| `ZReceiptHard` | 12 | counted |
| `ZReconverge` | 11 | **read** |
| `ZWidthHard` | 10 | counted |
| `NoGift` | 10 | counted |
| `Receipt` | 4 | counted |

Every module in the census is on the empty axiom list; that part is measured for all of them.

## The one result read in full, because this repository's architecture depends on it

`ZReconverge` — 11 theorems, empty axiom list:

    eligible m (Γ₁ ++ Γ₂) = true  ↔  eligible m Γ₁ = true ∧ eligible m Γ₂ = true

An **equivalence**, holding **without** non-emptiness hypotheses, *whatever the two branches
share and however many times they share it*. The question is settled by a theorem over every
marking and every pair of bundles — not by a failed search.

Where sharing does bite: **below eligibility, in the verdict.** One unresolved ground read once
yields `Z`; read twice it yields `F`. In that witness eligibility is `false` in **both** cases,
and more generally an unresolved ground makes every branch reading it ineligible **before** any
recombination. The one way such a ground enters an eligible branch is the over-grant `¬¬p`, and
there recombination is neutral.

Supporting measurement, 2026-09-07: 135 225 enumerated cells — verdict ≠ meet with both bundles
non-empty **0**, on the empty-bundle edge **12**, eligibility ≠ conjunction **0**, cells where
both branches are eligible **14 387** (the denominator; the check is not vacuous). A second
sweep of 3000 random pairs: 27 000 cells, edge 45, eligibility mismatches **0**.

**Consequences for this repository.** Do not write *"shared ancestor = unsafe"* or *"shared
ancestor = loss of standing"*; both are refuted. Keep **eligibility**, **verdict**, **ground
identity**, **use multiplicity** and **path multiplicity** as separate questions — ground
identity in particular is *not* settled by this module. And note that the meet identity on the
verdict does carry non-emptiness hypotheses: an empty bundle is not the identity element of
that operation. No dependency-graph representation is proposed here.

## What this file does not do

It does not re-pin the kernel profile, does not update the dossier, does not claim
conformance against the current head, and does not establish Tier-1 reproduction — which
remains **NOT ESTABLISHED**.
