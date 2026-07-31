# Epoch, expiry and revocation — ZTL side definitions and transition table

**Work order:** ZTL-OIC-WO-002, Deliverable B.
**Prepared by:** Vitaly Reznik (ZTL semantic boundary owner).
**Standing:** definitions and measured facts are from the pinned corpus and reproducible by command. The OIC-facing transition classifications are a **proposed interpretation** until a joint conformance test exists.

---

## 1. Definitions

### 1.1 Logical epoch

An **epoch** is a triple

```
E = ( φ , M , S )
```

where `φ` is the formula under judgement, `M` is the marking (which atoms are grounded, and to what), and `S` is the kernel semantics (kernel version + operator tables). A verdict and its grade are statements **about one epoch**. Any change to `φ`, to the *identity* of the ground set, or to `S` starts a **new epoch**; results do not carry across.

Within a single epoch, `M` may change only by **monotone refinement** (§1.3). Any non-monotone change to `M` also ends the epoch.

### 1.2 Ground-set identity

The **ground set** `G(E)` is the set of atom identifiers appearing in `φ`, together with their meaning as fixed at the start of the epoch. Two markings belong to the same epoch only if they range over the *same* `G(E)` with the *same* intended referents.

Consequences, stated because they are easy to violate silently:

- **Renaming an atom is a new epoch**, even if the value is unchanged.
- **Re-pointing an atom** (same name, different source clause) is a new epoch. The name is not the identity; the referent is.
- **Adding an atom to `φ`** is a new epoch (φ changed).
- ZTL cannot detect any of these. Atom identity is supplied by the caller and must be maintained by OIC. This is a boundary, not an oversight: the kernel judges logic over supplied grounds and has no access to sources.

### 1.3 Monotone refinement (the tick)

A **tick** is one act of verification:

```
verify(M, a, v) : a ∈ G, M(a) = Z ⟼ M'(a) = v, v ∈ {T, F}
```

Only Z → T and Z → F are admissible. T → F, F → T and anything → Z are **not** refinements. Refinement is the only within-epoch motion of `M`.

### 1.4 Scoped expiry (the anti-tick)

An **anti-tick** is

```
expire(M, a) : M(a) ∈ {T, F} ⟼ M'(a) = Z
```

ground withdrawn. Expiry is **scoped** when the epoch declares an explicit set `E_exp ⊆ G` of atoms that carry a clock, together with the authority entitled to run that clock. Expiry outside `E_exp` is inadmissible and must be treated as an error, not as an event.

**Unscoped expiry is not a weaker version of scoped expiry — it destroys the apparatus.** See §3.

### 1.5 Revocation

Revocation is expiry with an **authority** attached: a named actor withdraws a ground that they had standing to establish. Logically it is the same anti-tick; institutionally it differs in who may perform it and what record it leaves. ZTL computes the consequence; it does not adjudicate the standing. Standing is OIC's admission plane.

### 1.6 Re-verification

Re-verification is a tick applied after an anti-tick: `Z → T/F` for an atom that was previously grounded. It is admissible within the epoch, but the epoch's history is **not** restored: a verdict that survived an expiry-and-reverification cycle is not the same evidential object as one that never lost its ground, and any reliance recorded in between must be re-examined by OIC.

### 1.7 Formula change

Any change to `φ` — including a change that is classically equivalent — starts a new epoch. ZTL makes no equivalence-based reuse of results across formulas. If OIC needs to know whether two formulas behave identically, that is an explicit cross-formula check, not an assumption.

### 1.8 Source invalidation

A source document being superseded, corrected or found unauthentic is, from the kernel's side, an **anti-tick on every atom whose ground came from that source**, plus (usually) a change of ground-set identity if the referents moved. ZTL cannot detect source invalidation: it never sees sources. OIC must translate it into the atom-level events above.

### 1.9 Admission invalidation

Withdrawal of an institutional admission is likewise invisible to the kernel. If the admission was what made an atom grounded, its withdrawal is an anti-tick on that atom. If the admission fixed the *meaning* of an atom, its withdrawal is a **new epoch** (ground-set identity changed), and prior verdicts do not carry across.

---

## 2. The required rule, stated exactly

> **`hereditary` is stable only under the admissible monotone refinement model, for the same formula and the same epoch. It does not mean valid forever.**

Expiry, revocation, correction, formula change, source change, admission change and epoch change each require **explicit re-evaluation**. A `hereditary` result is a statement about *what more ground can do*, and about nothing else.

Measured support: exhaustive over all depth-≤2 formulas on two atoms — **2,906 formulas, 29,812 ticks, 0 violations** of hereditary-absorption under refinement. And measured on the other side: a full-ground `T/hereditary` verdict becomes `F/until-verification` after a single `expire` of one supporting ground (worked example: a vehicle purchase whose pledge registry is re-checked). Both are reproducible from the pinned corpus.

---

## 3. Why unrestricted expiry trivialises warranty claims

**Claim.** If any ground may expire at any time, then a property invariant under *both* refinement and expiry is constant, and therefore a test that cannot fail.

**Argument (two lines).** From any marking `M`, the operation set `{expire, verify}` reaches **every** marking `M'` over the same ground set: expire everything to Z, then verify each atom to its target value. Hence "invariant under refinement and arbitrary expiry" = "constant over all markings". A predicate that holds in every marking distinguishes nothing; it is a **frame**.

**Measured.** Over the same exhaustive pool, only constant-verdict formulas survive unrestricted expiry. Every contentful assertion loses its shelf.

**Institutional reading.** If everything can be revoked by anyone at any moment, then no warrant means anything — not because the logic is weak, but because the institution has declared its own grounds worthless. The apparatus does not degrade gracefully here; it degrades to decoration.

### 3.1 The scope information required to avoid this

For each required fact, the epoch must declare:

| Field | Meaning | Consequence if absent |
|---|---|---|
| `expirable: bool` | may this ground be withdrawn at all | expiry must be assumed possible → §3 applies |
| `expiry_authority` | who may withdraw it | revocation cannot be distinguished from error |
| `expiry_trigger` | clock, event, or discretionary | no re-check schedule can be derived |
| `insurable: bool` | may redundant checks pre-empt the loss | expiry-insurance (§3.2) cannot be computed |

This is the one field group we ask OIC to carry. Without it ZTL still computes verdicts; it cannot tell OIC **which controls survive a revocation and which unsettle**, which is the operationally valuable part.

### 3.2 Expiry-insurance — measured, and probably the most useful result here

On the worked example: a verdict settled early by a shortcut (`T/hereditary` at tick 2, "saving" two checks) **unsettles** when the clock runs out — `T/hereditary → F/until-verification`. But if those two saved checks are **paid before** the clock runs out, the same expiry leaves the verdict standing: T survives, the grade merely softens.

So the checks an optimiser "saves" are the control's **insurance against revocation**, and the kernel prices them. Operationally: *a control that was cheap to admit is often exactly the one that collapses on the first revocation.* Redundant grounding is not waste; it is the premium.

---

## 4. Transition table

| Transition | Preserves `hereditary`? | Requires recomputation? | Invalidates a previous warrant? |
|---|---|---|---|
| tick — `verify(a): Z→T/F`, `a ∈ G` | **yes** (measured: 0/29,812 violations) | yes, cheap — the verdict may improve or settle early | no |
| anti-tick — `expire(a)`, `a ∈ E_exp` | **no** | **yes** | **yes**, unless the verdict was insured (§3.2) |
| anti-tick outside `E_exp` | n/a | n/a | **inadmissible** — an error, not an event |
| revocation (expiry + authority) | **no** | **yes** | **yes** — and the reliance record must be re-examined |
| re-verification after expiry | not restored retroactively | yes | previous warrant stays invalidated; a new one is issued |
| formula change | **no** — new epoch | yes, from scratch | yes |
| ground-set identity change (rename / re-point / add atom) | **no** — new epoch | yes, from scratch | yes |
| semantics or kernel-version change | **no** — new epoch | yes, and replay must be pinned to the old version | yes |
| source invalidation | **no** (anti-tick on the derived atoms, possibly new epoch) | yes | yes |
| admission invalidation — admission supplied the *ground* | **no** (anti-tick) | yes | yes |
| admission invalidation — admission supplied the *meaning* | **no** — new epoch | yes, from scratch | yes |
| correction | **no** | yes | yes; history is preserved, not overwritten |
| effective-period lapse on a declared expirable ground | **no** | yes | yes, unless insured |
| a change touching no atom of `G(E)` | yes — nothing happened in this epoch | no | no |

**Reading rule for the first column:** "preserves `hereditary`" means only that a verdict already graded `hereditary` cannot move *because of this transition*. It never means the control needs no further review.

---

## 5. What ZTL does not do here

- It does not know when anything expires. There is no clock in the kernel; something in OIC must decide.
- It does not judge whether a revoking actor had standing.
- It does not detect source or admission changes.
- It does not reconcile institutional time (effective dates, jurisdiction, retention) with logical time. These are different clocks; both are needed and neither replaces the other.

## 6. What we ask OIC to confirm

1. That `expire` is the right model for revocation, amendment and effective-period lapse on your side — or where it is not.
2. Whether the envelope can carry the scope fields of §3.1. If it cannot, say so, and we will narrow the claim rather than assume the field exists.
3. That any reviewer-facing display of a `hereditary`-equivalent carries the qualifier of §2. A grade shown without its scope will be read as "settled forever" by the first person in a hurry — and that reading is wrong in exactly the cases that matter.

---

*Independent Tier-1 reproduction remains OPEN. Nothing in this document asserts that ZTL has been independently reviewed.*
