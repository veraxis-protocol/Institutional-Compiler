# OIC↔ZTL Maturation Delta 001

**Date:** 2026-09-07 · **OIC base:** `main` at `c4a325c5`, tree `b8e31ec4` · **ZTL base:**
`master` at `8ab40b23`, tree `0efbd9cb`.

This document reconciles what this repository says about ZTL, what it implements, and what ZTL
currently is. It broadens no claim. Where a statement here is measured, the measurement is
named; where something was not read, that is said rather than glossed.

## 1. The short answer

The contract between OIC and ZTL is **largely written and entirely unstarted**. The
documentation describing it is stale in specific places. And the three institutional
transitions that would let anything cross between them **do not exist**:

    InterpretationProposal
      → institutional semantic act        (no owner, no code, no receipt)
        → stable admitted proposition     (no identity object)
          → evidence-bearing formalization (no provenance discipline)
            → ZTL

This is why `ZTL RUNTIME ATTACHMENT = BLOCKED`. It is not a defect in ZTL and not a gap in the
warrant contract; it is a missing institutional middle.

## 2. Statements in this repository that had become stale

| Where | What it said | What is the case |
|---|---|---|
| `README.md`, `STATUS.md` | *"merge pending Gate G and owner authorization"* | PR #40 merged 2026-09-06. **Superseded by dated blocks in both files; historical text retained** |
| `STATUS.md` | validation figures for promotion base `9ad37fc8`, candidate `c0108a7a`, tree `1d12b17a`, 1714 passing | that is the historical Gate-F candidate, not the current head. Now labelled as such. Measured at the current head 2026-09-07: **1719 passed, 1 declared skip** |
| `adapters/ztl/` | dossier, conformance and census at **v0.1 / v0.2**, `OPEN-ITEMS-2026-07-29.md` | ZTL has moved substantially since. See `adapters/ztl/CURRENT-STATE-001.md` |
| `docs/capabilities/CAPABILITY_MATRIX.json` | **no ZTL entry at all** | corrected minimally in this change |
| `docs/contracts/kernel-profiles/ztl-v0.1.json` | names tags `veraxis-ztl-input-v0.1` and `veraxis-ztl-input-v0.2-signed` | neither exists in the ZTL repository. **Deliberately not modified** — see §5 |

**Not stale, and worth stating:** `STATUS.md`'s *"Broader production semantic gate: BLOCKED"*,
`CAPABILITY_MATRIX.json`'s `production_semantic_gate: "BLOCKED"`, and
`docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md`'s *"SEMANTIC IMPLEMENTATION HAS NOT
STARTED"* were all accurate. Three independent artifacts already stated the conclusion.

## 3. OIC-side maturity — what is actually implemented

| Capability | Implemented | Note |
|---|---|---|
| source binding | yes | digest-checked against a registered source; three distinct mismatch states |
| candidate grounding | yes | a literal supporting quote is required, or the slot is `null` |
| deterministic candidate identity | yes | `cnu-<24 hex>`; canonical JSON, no clock, no randomness |
| divergence preservation | yes, **for candidate spans** | see `OIC-ZTL-LAYER-OWNERSHIP-001.md` §2 |
| admission boundary | yes | 15 frozen terminal states in frozen precedence order |
| authority evidence | yes | ordered, per-item digests, integrity-checked; **supplied, never issued** |
| expiry / supersession / revocation | yes, **of the candidate's admission** | not of a meaning; the distinction is load-bearing |
| conflicting authority | yes | `CONFLICTING_AUTHORITY`; distinct from a contradictory formula, which ZTL simply refutes |
| admission receipt | yes | 18 fields, recomputable, `admrec-sha256:` identity |
| provisional interpretation | yes — **and the pipeline ends here** | `proposal_state: PROVISIONAL`, `epistemic_state: uncertain`; its own frozen prompt calls the output provisional and untrusted |
| Institutional IR closure | no | already declared `UNESTABLISHED` in the capability matrix |
| Open Control Envelope | not executable | `schemas/draft/control-envelope.schema.json` |

## 4. ZTL-side maturity, against what `adapters/ztl/` currently pins

Measured 2026-09-07 by ZTL's own inventory tooling: **1112 theorems across 66 modules, every
one on the empty axiom list.**

Present in current ZTL and absent from the adapter's July picture: `RelianceBridge`,
`ZReconverge`, `ZReceiptHard`, `ZWidthHard`, `LabelExact`, `LabelExactDefinite`, `ZNumPrice`
and others. Per-module detail, and the reading discipline separating what was read from what
was only counted, is in `adapters/ztl/CURRENT-STATE-001.md`.

Two ZTL results bear directly on this repository's architecture:

- **Reconvergence.** Eligibility of a fan-in equals eligibility of both branches — an
  equivalence, holding without non-emptiness hypotheses, *whatever grounds they share and
  however often*. The older shorthand *"a shared ancestor destroys eligibility"* is **refuted**
  and must not be carried forward. Shared ancestry never changes eligibility; verdict movement
  from a repeatedly-read unresolved ground occurs only where eligibility is already false.
  A caution for any future dependency-graph representation: the meet identity on the *verdict*
  does carry non-emptiness hypotheses, so **an empty bundle is not the identity element** and
  cannot be folded in as neutral.
- **Disposition count.** ADR-013 §3.1 already corrects the v0.1 dossier's three dispositions to
  four, adding `ON CREDIT`. That correction stands.

## 5. What was deliberately not changed

- **`docs/contracts/kernel-profiles/ztl-v0.1.json` is untouched.** Its tag names are historical
  evidence of what was admitted in July. A recovered public tag created in September does not
  retroactively replace them. A superseding profile — re-binding the current admitted ZTL
  surface to a published durable reference and a re-verified interface — is separate future
  work, and which ZTL surface it should pin must follow from a conformance and reproduction
  gate rather than from recency.
- **No runtime code, no schema promotion, no adapter.** There is no lawful input to write code
  against. The absence of the chain in §1 is a result to preserve, not a gap to fill with
  scaffolding.
- **`tier_1_reproduction` remains NOT ESTABLISHED** and is not moved by anything here.
