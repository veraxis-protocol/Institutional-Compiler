# Kernel output census — v0.1

**Purpose.** Two claims in PR #16 are about what the kernel can and cannot emit. Reading the
mapping cannot settle them; running the kernel can. This is the run.

**Reproduce:**

```bash
python3 adapters/ztl/evidence/kernel_census.py --ztl /path/to/ZTL
```

Machine-readable output: [`KERNEL-CENSUS-v0.1.json`](KERNEL-CENSUS-v0.1.json).
Pool: 22 formulas, every marking over `{T, F, Z}` — **294 cases**. The pool is printed by the
script and listed in the JSON. It exercises conjunction, disjunction, implication, negation,
redundant grounds and tautological consequents. It is a census over a stated pool, not a proof
of coverage, and nothing below is claimed beyond it.

---

## 1. Every cell the kernel produces

| disposition | grade | raw verdict | `unverified` | cases | example |
|---|---|---|---|---:|---|
| `EARNED` | `hereditary` | T | empty | 68 | `p` `{p:T}` |
| **`EARNED`** | **`hereditary`** | **T** | **non-empty** | **61** | **`p \| q` `{p:T, q:Z}`** |
| `ON CREDIT` | `sound` | T | non-empty | 1 | `(~p) -> (q -> q)` `{p:Z, q:Z}` |
| `ON CREDIT` | `until-verification` | T | non-empty | 6 | `~(p & q)` `{p:T, q:Z}` |
| `OPEN` | `until-verification` | F | non-empty | 94 | `~p` `{p:Z}` |
| `OPEN` | `until-verification` | Z | non-empty | 1 | `p` `{p:Z}` |
| `REFUTED` | `hereditary` | F | empty | 38 | `p` `{p:F}` |
| `REFUTED` | `hereditary` | F | non-empty | 25 | `p & q` `{p:F, q:Z}` |

Eight cells. Everything else in the product space is empty over this pool.

**Confirms** the three `NOT_REACHABLE` rows: no `EARNED` + `sound`, no `EARNED` +
`until-verification`, no `OPEN` with raw `T`. Also: `OPEN` and `ON CREDIT` never carry an
empty `unverified` list, which is what makes them what they are.

**Refutes** one claim: **`EARNED` carries a non-empty `unverified` list in 61 of 294 cases** —
21% of the measured space, and the second-largest cell in the table.

## 2. Why that is not a defect in the kernel

`p | q` with `{p:T, q:Z}` returns `EARNED` / `hereditary` / `T` / `unverified = ['q']`.
`q` was never verified. The conclusion does not need it: `p` grounds the disjunction outright,
and no value of `q` can move the result. That is the whole content of `hereditary`.

Measured, not argued:

| | |
|---|---:|
| `EARNED` results carrying a non-empty `unverified` list | **61** |
| refinements tried (every unverified atom set to T and to F, every combination) | **138** |
| refinements that moved the verdict | **0** |

So the unverified atoms in an `EARNED` result are genuinely irrelevant to it.

**The consequence for the contract is a field read with two meanings.** In an `EARNED` result
`unverified_ground_ids` is *informational*: atoms nobody checked, whose value cannot matter.
In an `ON CREDIT` result the same list is *load-bearing*: the verdict rides those atoms and
dies when one of them resolves the wrong way. A single field, two roles. A contract that does
not say which is which will get one of them wrong.

## 3. What `dependency_ids` must contain

A ground is **load-bearing** if withdrawing it — the anti-tick, a verified atom returning to
`Z` — moves the disposition. Withdrawing an already-unverified atom is a no-op, so only
verified grounds can be probed. That is exactly the revocation case `dependency_ids` serves.

The question that matters: **is probing one ground at a time enough?** No.

| | |
|---|---:|
| cases with two or more verified grounds | **180** |
| cases where withdrawing a *pair* moves the disposition although neither member does alone | **38** |

Counterexample:

```
(p | q) & r     {p:T, q:T, r:T}   ->  EARNED / hereditary

  withdraw p alone   ->  EARNED     (q still carries the disjunction)
  withdraw q alone   ->  EARNED     (p still carries it)
  withdraw p and q   ->  OPEN / until-verification
```

Redundant grounds. A minimal dependency set derived by single-ground probing omits both `p`
and `q`; a revocation of both then propagates to nothing, and a warrant that says `ESTABLISHED`
outlives the grounds that established it.

**Therefore `dependency_ids` must be the over-approximation — every verified ground in the
formula — and not a minimised load-bearing set.** Minimisation here is unsound for revocation
propagation, and it fails in the direction that matters: it leaves stale warrants usable.

---

## 4. Limitations

1. **Census over a stated pool, not a theorem.** 22 formulas up to three atoms. A cell absent
   here is absent *from this pool*; that is weaker than "the kernel cannot produce it". The
   three `NOT_REACHABLE` rows have the stronger backing described in
   [`CONFORMANCE-v0.1.md §8.1`](../CONFORMANCE-v0.1.md); this census is corroboration, not
   their source.
2. **Joint dependency was probed to pairs only.** Triples and larger were not searched. Since
   pairs already refute minimisation, searching further would not change the recommendation —
   but the number 38 is a floor, not a total.
3. **Author-side evidence.** Written and run by the ZTL side against its own kernel: Tier 3.
   The script is offered so the run can be repeated by someone else, which is the only thing
   that would change the tier. **Independent Tier-1 reproduction remains OPEN.**
4. **The pinned fixture set was not modified.** `fixtures/interface-freeze-v0.1/` and its
   `index_sha256` (`b6e007bd…`, pinned in `kernel-profiles/ztl-v0.1.json`) are untouched. If
   the `EARNED` + non-empty-`unverified` case should become a pinned fixture, that requires a
   fixture-set version bump and a re-pin, which is the OIC side's call, not ours to take
   underneath a PR under review.

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the
OIC semantic implementation gate remains BLOCKED.*
