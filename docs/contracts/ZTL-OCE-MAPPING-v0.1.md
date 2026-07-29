# ZTL → Open Control Envelope mapping, v0.1

**Status: PROPOSED. Not admitted, not implemented, not called.**

This answers open item 3 in [`adapters/ztl/OPEN-ITEMS-2026-07-29.md`](../../adapters/ztl/OPEN-ITEMS-2026-07-29.md)
("joint disposition/grade/unverified mapping — *you, then us*") and turns dossier §6.3
from a proposed interpretation into something that can be tested jointly.

Governing decision: [ADR-013](../../adr/ADR-013.md).
Field definitions: [WARRANT-CONTRACT-v0.1.md](WARRANT-CONTRACT-v0.1.md).

## How to read this table

The table is **total over the input space**, not over the outputs ZTL is known to emit.
Some rows describe combinations the kernel may never produce. They are specified anyway,
because an adapter that meets an unexpected combination must fail closed rather than fall
through. Rows whose reachability needs ZTL confirmation are marked **`?`** in the
*Reachable* column and listed in §3.

`Disposition`, `Grade`, and `Unverified` are the kernel's outputs. `Condition` is an
OIC-side check that runs before or after the kernel. Where both appear, **the OIC-side
condition wins**: a stale or misbound warrant is not rescued by a good disposition.

`BLOCK / ESCALATE` means the envelope chooses: `on_unknown: cannot` or `deny` → `BLOCK`;
`on_unknown: escalate` → `ESCALATE`. The choice never changes `Epistemic` or `Basis`.

**This table is the source of truth.** `tests/contract/test_warrant_contract.py` parses it
and asserts every golden fixture matches a row.

<!-- MAPPING-TABLE-START -->

| # | Disposition | Grade | Unverified | Condition | Epistemic | Execution | Basis | Primary reason code | Reachable |
|---|---|---|---|---|---|---|---|---|---|
| 1 | EARNED | hereditary | empty | all checks pass | ESTABLISHED | ALLOW | SUBSTANTIVE | OIC-D-0001 | yes |
| 2 | EARNED | hereditary | non-empty | all checks pass | ESTABLISHED | ALLOW | SUBSTANTIVE | OIC-W-0015 | ? |
| 3 | EARNED | sound | any | grade permitted by envelope | ESTABLISHED | ALLOW | SUBSTANTIVE | OIC-D-0001 | yes |
| 4 | EARNED | sound | any | grade below envelope minimum | ESTABLISHED | ESCALATE | PROCEDURAL | OIC-W-0016 | yes |
| 5 | EARNED | until-verification | any | any | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | ? |
| 6 | REFUTED | any | any | warrant usable | REFUTED | BLOCK | SUBSTANTIVE | OIC-W-0013 | yes |
| 7 | OPEN | any | any | raw verdict T | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | ? |
| 8 | OPEN | any | any | raw verdict F | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | yes |
| 9 | OPEN | any | any | raw verdict Z | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | yes |
| 10 | any | any | any | contradictory grounds | CONTRADICTED | BLOCK | SUBSTANTIVE | OIC-W-0014 | yes |
| 11 | any | any | any | kernel unavailable | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0002 | yes |
| 12 | any | any | any | warrant absent | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0001 | yes |
| 13 | any | any | any | warrant malformed | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0003 | yes |
| 14 | any | any | any | warrant hash unverifiable | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0004 | yes |
| 15 | any | any | any | warrant stale | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0005 | yes |
| 16 | any | any | any | warrant expired | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0006 | yes |
| 17 | any | any | any | ground expired | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0020 | yes |
| 18 | any | any | any | ground revoked | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0007 | yes |
| 19 | any | any | any | epoch mismatch | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0008 | yes |
| 20 | any | any | any | source-version mismatch | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0009 | yes |
| 21 | any | any | any | admission-version mismatch | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0010 | yes |
| 22 | any | any | any | formula mismatch | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0011 | yes |
| 23 | any | any | any | source anchors missing | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0018 | yes |
| 24 | any | any | any | admission IDs missing | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0019 | yes |
| 25 | any | unsupported | any | any | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0017 | yes |

<!-- MAPPING-TABLE-END -->

## 1. Precedence

When several rows match, the outcome is the **most restrictive** one, and precedence runs:

1. rows 11–14 (kernel or artifact unusable) — the claim was never validly evaluated;
2. rows 15–25 (artifact misbound, stale, or grounds withdrawn) — evaluated against a
   different world;
3. row 10 (contradiction);
4. rows 6–9 (disposition);
5. rows 1–5 (disposition and grade).

Precedence is stated because a warrant can be simultaneously `EARNED`, `hereditary`, and
computed at an epoch that no longer exists. The good news must not win.

## 2. What each row does *not* say

No row asserts `ALLOW` on the strength of the kernel alone. Rows 1–3 read "supports
`ALLOW`" and are subject to ADR-013 **W-4** conditions 4–8: authority, admission,
evidence, and version checks that ZTL does not perform and does not claim to. A row
reaching `ALLOW` here means *the logic does not stand in the way*, not *the action is
permitted*.

## 3. Rows needing ZTL confirmation of reachability

Marked **`?`** above. These are our reading of the interface, not measurements, and we
would rather be corrected now than after a docket exists.

**Row 2 — `EARNED` + `hereditary` + non-empty `unverified`.** We believe this is
reachable: `judge("p | q", {"p": "T", "q": "Z"})` should be invariant under every
refinement of `q`, so `hereditary` with `unverified = ["q"]`. If so, the case matters a
great deal, because it is the one where OIC reaches `ALLOW` **while missing grounds
exist**, and W-5 requires those grounds still be surfaced. If the kernel instead returns
`OPEN` here, row 2 is unreachable and fixture `09` should be re-labelled.

**Row 5 — `EARNED` + `until-verification`.** Dossier §6.3 ties `OPEN` to grade
`until-verification`, which suggests `EARNED` + `until-verification` may be unreachable.
We specify it as `UNRESOLVED` regardless: a result holding only in the present marking has
established nothing durable. Please confirm whether the kernel can emit it.

**Row 7 — `OPEN` with raw verdict `T`.** The measured warning covers `OPEN` with raw `F`.
We assume raw `T` under `OPEN` is equally possible and equally non-establishing. If `OPEN`
can never carry raw `T`, the row stays as a defensive specification.

## 4. Reason codes

Registry in [WARRANT-CONTRACT-v0.1.md §6](WARRANT-CONTRACT-v0.1.md#6-reason-code-registry).
The *Primary reason code* column above is the code that explains the outcome; a decision
may carry additional codes, and `OIC-W-0015` is added whenever unverified grounds exist,
on any row.

## 5. Time model alignment

Adopting the ZTL vocabulary rather than maintaining two notions of time:

| ZTL | OIC | Artifact field |
|---|---|---|
| tick — arrival of ground (Z → T/F) | ground admitted | `ground_epoch` increments |
| anti-tick — ground withdrawn | expiry, revocation, correction | `revocation_references`, `valid_until` |
| `hereditary` — always on all paths | invariant under monotone refinement **only** | `warranty_grade` |
| `sound` — at all endings | never lies, may stall | `warranty_grade` |
| `until-verification` — now | present marking only | `warranty_grade` |

Expiry is **scoped**: per-artifact `valid_until` and per-ground `revocation_references`.
It is never a global sweep, because unrestricted expiry makes warranty invariants
trivially true.

## 6. Standing

Proposed by the OIC side under OIC-WO-002. Requires:

- **Vitaliy Reznik** — confirmation of §3 reachability and of the mapping generally;
- **GPT-5.6 Thinking** — architecture acceptance;
- **Arkadiy Miteiko / Veraxis** — final design authority.

No ZTL call was made to produce this document. No adapter exists. The semantic
implementation gate remains **BLOCKED**.
