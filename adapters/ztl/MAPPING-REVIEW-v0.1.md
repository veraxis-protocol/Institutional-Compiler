# Mapping review — v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable E.
**Status: AWAITING INPUT.** `docs/contracts/ZTL-OCE-MAPPING-v0.1.md` does not exist in the repository.

---

## 1. Why this deliverable is not complete

The work order asks us to review **every row** of `docs/contracts/ZTL-OCE-MAPPING-v0.1.md` and answer ACCEPT / ACCEPT WITH QUALIFICATION / REJECT / CANNOT DETERMINE per row.

That file is not in `main` at `141ec2b`, nor in any open PR (#13, #14, #15). There are no rows to review. We will not review a mapping we wrote ourselves and call the result an independent check — the dossier's §6.3 table is **our proposal**, not OIC's contract, and marking our own proposal ACCEPT would be circular.

**When the mapping document lands, this file will be completed row by row.** For every non-accept we will supply, as required: the exact semantic objection, a counterexample, the expected ZTL result, and a proposed corrected mapping.

## 2. The required invariant — confirmed in advance

> *"OPEN remains unresolved regardless of the raw verdict field."*

**Confirmed, and it is measurable.** Two fixtures make the point concrete:

| Fixture | Input | Raw `verdict` | `disposition` |
|---|---|---|---|
| `open-with-raw-f` | `p & q`, `{p:T, q:Z}` | **F** | **OPEN** |
| `open-with-raw-z` | `p`, `{p:Z}` | Z | OPEN |

A mapping that keys on `verdict` classifies the first row as established falsity. That is wrong, it breaks OIC invariant I-04, and it will not surface in ordinary testing until a genuinely undetermined case reaches production. **Key on `disposition`.**

The corresponding NOT_REACHABLE fixture completes the picture: `open-with-raw-t` **does not exist** — OPEN never carries a raw T. No mapping row should be written against that state.

## 3. Correction that must land in the mapping before it is reviewed

Our own dossier v0.1 gave OIC an **incomplete list of dispositions**. It named EARNED / REFUTED / OPEN. The kernel has **four**:

| disposition | grade | verdict | meaning |
|---|---|---|---|
| `EARNED` | hereditary | T | grounded outright; unverified atoms are irrelevant |
| `REFUTED` | hereditary | F | false regardless of the marks |
| **`ON CREDIT`** | sound **or** until-verification | T | **true only while an unverified atom holds** — it can die when that atom resolves |
| `OPEN` | until-verification | F or Z | not established; a mark actually matters |

`ON CREDIT` was missing, and it is the one that matters most for an enforcement contract. Mapped as EARNED it would authorise action on an unverified link — precisely what a zero-trust warrant exists to prevent. Mapped as OPEN it would over-block: the verdict *is* T, and under `sound` it never lies about the present marking.

**Our proposed handling, offered as a starting row rather than a conclusion:**

| ZTL disposition + grade | Proposed OIC behavior | Reason |
|---|---|---|
| `EARNED` + hereditary | supports ALLOW (authority and evidence still OIC's to check) | cannot move under further verification |
| `ON CREDIT` + sound | ALLOW **only** where the envelope explicitly tolerates a non-monotone warrant; otherwise ESCALATE, carrying `unverified` | never lies about the present marking, but may stall |
| `ON CREDIT` + until-verification | **ESCALATE**, not ALLOW | rides an unverified atom that can flip |
| `REFUTED` | supports DENY | grounds establish falsity |
| `OPEN` (any raw verdict) | `on_unknown` → ESCALATE / CANNOT, **never** DENY | absence of verification is not falsity |
| `unverified` non-empty | populate `missing_inputs` | names the exact blocking grounds |

Fixtures for every row above are in `fixtures/interface-freeze-v0.1/`.

## 4. What we will need in the mapping document to review it properly

1. The **OIC-side semantics** of `on_missing`, `on_unknown`, `on_conflict`, `on_error` — precisely enough that a row can be judged wrong, not merely unfamiliar.
2. Whether the envelope distinguishes **ESCALATE** from **CANNOT**. Our `OPEN` collapses into whichever OIC chooses; if both exist, we need the rule for choosing.
3. Whether a row may depend on `grade`. If the envelope cannot carry the warranty grade, several rows above are not expressible and we would rather narrow them than pretend.

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the OIC semantic implementation gate remains BLOCKED.*
