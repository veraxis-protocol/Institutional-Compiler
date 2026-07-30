# adapters/ztl

ZTL adapter zone. **Provisional project-controlled dependency** (TDD-OIC-001 v1.1 §3.4, §3.5).

> This directory contains **evidence and proposals only**. No adapter implementation, no
> ALLOW/DENY behavior. The OIC semantic implementation gate remains **BLOCKED**, and
> independent Tier-1 reproduction remains **OPEN**.

## Contents

| File | Deliverable | Status |
|---|---|---|
| `ZTL-DOSSIER-v0.1.md` | dependency dossier (13 fields) | 12 of 13 closed |
| `evidence/RELEASE-PROVENANCE-v0.1.md` | WO-002 **A** — signed provenance | **CLOSED** |
| `proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md` | WO-002 **B** — epoch/expiry/revocation | submitted |
| `fixtures/interface-freeze-v0.1/` | WO-002 **C** — machine-readable fixtures | 12 reachable + 3 not-reachable |
| `CONFORMANCE-v0.1.md` | WO-002 **C** — conformance procedure | executable, PASS |
| `WARRANT-FIELD-RESPONSE-v0.1.md` | WO-002 **D** — warrant field feasibility | **COMPLETE** — all 28 schema fields classified |
| `MAPPING-REVIEW-v0.1.md` | WO-002 **E** — mapping review | **COMPLETE** — 29 rows + 7 overlays; 1 REJECT |
| `evidence/KERNEL-CENSUS-v0.1.md` | measured backing for D and E | 294 cases, re-runnable |
| `evidence/kernel_census.py` | the census, as a command | executable |
| `OPEN-ITEMS-2026-07-29.md` | ownership of the nine open items | current |

## Pin

| Item | Value |
|---|---|
| Repository | `github.com/inventor1975/ZTL` |
| **Current signed tag (v0.2, WO-003)** | **`veraxis-ztl-input-v0.2-signed`** |
| **Current commit (v0.2)** | **`56e1ff0510c62b04dbd85bbe08b7a6deacbf276b`** |
| Signed tag (v0.1, historical — predates `ztljudge.judge`; see CONFORMANCE-v0.2.md §1) | `veraxis-ztl-input-v0.1.1-signed` |
| Annotated tag (original, unchanged) | `veraxis-ztl-input-v0.1` |
| Commit both point at | `e819dec7e89d2dc67d6371e1eedb8e7aae854602` |
| Lean toolchain | `leanprover/lean4:v4.29.1` |
| Signing key | `F170414DDBB78F231929121175B13F5AEC28313A` |
| Conformance input (SHA-256) | `33de416110be748a647216ef97b246e925b2dcde95e95cbefdd13cf51f69bb8c` |
| Fixtures (SHA-256) | `717853cf2a84ede0cb0472192d2e4fac4303acf29775f0d41d972e15c3652f93` |
| Dependency closure (SHA-256) | `efe05b396cdb4a8731f51b5cc927a8fc998e01a789a2a6dff5657e5a2b5971a5` |

## Interface

```
judge(text, marking)  -> { verdict, grade, disposition, unverified, formula, marking, why }
check(text, marking)
join(text_a, text_b, operator, marking)
grade(phi, marking)            # different mark dialect — see hazard
formalize(text)
```

### Adapter contract

Consume **`disposition`** as the operational signal, **`grade`** as the warranty qualifier,
**`unverified`** as `missing_inputs`. The raw **`verdict`** is an internal kernel detail.

There are **four** dispositions, not three:

| disposition | grade | verdict | meaning |
|---|---|---|---|
| `EARNED` | hereditary | T | grounded outright |
| `REFUTED` | hereditary | F | false regardless of the marks |
| **`ON CREDIT`** | sound / until-verification | T | **true only while an unverified atom holds** |
| `OPEN` | until-verification | F or Z | not established; a mark matters |

### Three traps

1. **`verdict` is not the answer.** `judge("p & q", {p:T, q:Z})` returns `verdict='F'` with
   `disposition='OPEN'`. Mapping that `F` to DENY converts "not yet established" into
   "established false" and breaks invariant I-04. Fixture: `open-with-raw-f`.
2. **`zverify.grade()` uses a different mark dialect** — `'M'`, not `'Z'`. Passing `'Z'`
   returns `hereditary` **silently and wrongly**. Use `judge()`.

Also: `OPEN` never carries raw verdict `T` (fixture `open-with-raw-t`, NOT_REACHABLE), and
`EARNED` is always `hereditary` — a non-hereditary T is `ON CREDIT`, never `EARNED`
(fixtures `earned-sound`, `earned-until-verification`, both NOT_REACHABLE).

3. **`unverified` means two different things**, and this one has already caused an error in a
   downstream contract. `EARNED` **can** carry a non-empty `unverified` list:

   ```
   judge("p | q", {p:T, q:Z})  ->  EARNED / hereditary / T / unverified=['q']
   ```

   `q` was never checked; `p` grounds the disjunction outright, and no value of `q` can move
   the result. Measured in 61 of 294 cases, with 138 refinements and zero verdict moves —
   `evidence/KERNEL-CENSUS-v0.1.md`. So under `EARNED` and `REFUTED` the list is
   **informational**; under `ON CREDIT` it is **load-bearing**; under `OPEN` it is
   **blocking**. An adapter that treats a non-empty list as "incomplete" refuses the strongest
   results the kernel produces.

## Boundary

ZTL does not validate source authenticity, determine authority, interpret prose, create
institutional admission, or decide ALLOW/DENY. Those are OIC's planes.

## Verify for yourself

```bash
git clone https://github.com/inventor1975/ZTL.git ztl && cd ztl
git checkout veraxis-ztl-input-v0.1.1-signed
git tag -v veraxis-ztl-input-v0.1.1-signed
cd - && python3 adapters/ztl/fixtures/interface-freeze-v0.1/verify_fixtures.py --ztl ./ztl
```

Expected: `CONFORMANCE: PASS`, 12 reproduced, 0 mismatches. No network access required.

## Open items

| Item | State | Owner |
|---|---|---|
| Independent Tier-1 reproduction | **OPEN** | not the ZTL side, by rule |
| Signed release provenance | CLOSED 2026-07-29 | ZTL side |
| Warrant artifact fields | reviewed against PR #16 `9623cd4` | OIC to accept |
| ZTL↔OCE mapping rows | reviewed; **row 25 rejected**, correction supplied | OIC to accept |
| MissingGround granularity | awaiting OIC | OIC |
| Epoch/expiry/revocation | proposal submitted | OIC to confirm |
| VEIP boundary | awaiting OIC | OIC |

No statement in this directory asserts that ZTL has been independently reviewed or reproduced.
