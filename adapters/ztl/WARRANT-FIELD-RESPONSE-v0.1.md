# Warrant field feasibility response — v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable D; completed under the ZTL-OIC cross-review order
for PR #18.
**Status: COMPLETE** for every field in the reviewed schema.

**Reviewed against:**

| | |
|---|---|
| PR #16 head | `9623cd43363eaa3d105f263d6c3dc8999755db9d` |
| `schemas/proposed/warrant-artifact.schema.json` | 28 properties, all required |
| Kernel profile `docs/contracts/kernel-profiles/ztl-v0.1.json` | sha256 `d8e515e76635cace04f2538f537addf0fd14de27ae4b883ae3ec57c3e5ced34a` |
| Kernel | `ztljudge.judge`, commit `e819dec7e89d2dc67d6371e1eedb8e7aae854602` |

---

## 1. The kernel's whole output surface

Measured, not quoted. `judge()` returns exactly seven fields:

```
disposition  formula  grade  marking  unverified  verdict  why
```

Anything not derived from those seven is not ZTL's to supply. `why` is presentational and
must not be parsed — the profile already says so, correctly.

## 2. Field-by-field

`NATIVE` = returned by `judge()`. `DERIVABLE` = computable from the seven fields plus the
pinned kernel, deterministically and without a new ZTL concept. `OIC-ENRICHED` = the kernel
never sees it. `UNSUPPORTED` = outside the boundary. `REQUIRES ZTL CHANGE` = a new emission.

| # | Field | Classification | Basis |
|---|---|---|---|
| 1 | `warrant_artifact_id` | **OIC-ENRICHED** | artifact identity; not a kernel concept |
| 2 | `schema_version` | **OIC-ENRICHED** | OIC's schema, OIC's version |
| 3 | `claim_id` | **OIC-ENRICHED** | the kernel evaluates a formula, not a registered claim |
| 4 | `kernel_profile_id` | **OIC-ENRICHED** | the kernel does not self-identify; see §4.1 |
| 5 | `canonicalization_profile_id` | **OIC-ENRICHED** | adapter constant; see §4.2 |
| 6 | `formula` | **NATIVE** | `result["formula"]`, the kernel's own rendering |
| 7 | `formula_hash` | **DERIVABLE** | `connector.canon.sha384_hex`, already shipped; see §4.2 |
| 8 | `disposition` | **NATIVE** | four values, exactly as the profile lists them |
| 9 | `raw_verdict` | **NATIVE** | `result["verdict"]`; inert, and rightly marked so |
| 10 | `warranty_grade` | **NATIVE** | three values, ladder as the profile states |
| 11 | `unverified_ground_ids` | **NATIVE** | echoed verbatim; **but see §3 — the field has two roles** |
| 12 | `dependency_ids` | **DERIVABLE with a constraint** | see §4.3 — must be the over-approximation |
| 13 | `ground_epoch` | **OIC-ENRICHED** | kernel is stateless; no clock, no epoch, no authority |
| 14 | `ground_set_hash` | **DERIVABLE** | digest over `result["marking"]`, which is echoed |
| 15 | `source_anchor_ids` | **OIC-ENRICHED** | the kernel never sees a source |
| 16 | `admission_ids` | **OIC-ENRICHED** | admission is OIC's plane |
| 17 | `kernel_name` | **OIC-ENRICHED** | adapter constant |
| 18 | `kernel_version` | **OIC-ENRICHED** | adapter constant |
| 19 | `kernel_commit` | **OIC-ENRICHED** | adapter constant, pinned `e819dec…` |
| 20 | `input_hash` | **DERIVABLE** | digest over formula + marking |
| 21 | `output_hash` | **DERIVABLE** | digest over the six non-presentational output fields; see §4.4 |
| 22 | `generated_at` | **OIC-ENRICHED** | the kernel has no clock |
| 23 | `time_binding` | **OIC-ENRICHED** | ditto; the field's own description already says this |
| 24 | `valid_from` | **OIC-ENRICHED** | ditto |
| 25 | `valid_until` | **OIC-ENRICHED** | ditto |
| 26 | `revocation_references` | **OIC-ENRICHED** | revocation is an institutional act |
| 27 | `recomputation_reference` | **DERIVABLE** | pinned kernel + `input_hash` + ground set, all available |
| 28 | `limitations` | **DERIVABLE, then OIC-extended** | see §4.5 |

**Nothing is `UNSUPPORTED` and nothing `REQUIRES ZTL CHANGE`.** Every field is either emitted,
computable from what is emitted, or correctly assigned to OIC. That is a better result than
Deliverable D anticipated in the previous revision, and it is because the schema was drawn on
the right side of the boundary.

**The work order's constraint is confirmed:** the kernel is not expected to originate source
anchors, admissions, epochs or institutional time authority — and it does not. Rows 13, 15,
16, 22–26 are exactly that set.

## 3. `unverified_ground_ids` is NATIVE, and it carries two different meanings

This is the one field where a correct classification is not enough.

Measured over 294 cases ([`evidence/KERNEL-CENSUS-v0.1.md`](evidence/KERNEL-CENSUS-v0.1.md)):

| disposition | what the list means |
|---|---|
| `EARNED` | **informational** — atoms nobody verified, whose value cannot move the verdict. 61 cases; 138 refinements tried; **0** moved the verdict. |
| `ON CREDIT` | **load-bearing** — the verdict rides these atoms and can die when one resolves |
| `OPEN` | **blocking** — the reason nothing is established |
| `REFUTED` | **informational** — false regardless |

The schema says the field is "always surfaced as `missing_ground_ids` on the runtime decision,
including when the outcome is ALLOW". **That is right and should stay** — but the runtime
decision should not imply the same thing in all four cases. Under `EARNED` these are grounds
that were not needed; under `ON CREDIT` they are grounds that are owed. Presenting both as
"missing" invites a reviewer to escalate an established result, or to relax a conditional one.

**Proposal, minimal:** keep one field, add one discriminator already present —
`epistemic_status`. `ESTABLISHED` + non-empty `missing_ground_ids` reads "not needed";
`CONDITIONALLY_SUPPORTED` + non-empty reads "owed". No schema change; a sentence in
WARRANT-CONTRACT §5 would do it.

## 4. Notes on the derivations

### 4.1 `kernel_profile_id` must pin a commit, not a name

The profile correctly says dispositions and grades are not portable between kernels. Then the
identifier must be bound to `kernel_commit`, not merely declared alongside it: `ztl-v0.1`
naming a *different* commit is a different semantics under the same label. The profile already
records `commit: e819dec…`; the adapter must verify the two agree rather than trust the label.

### 4.2 `formula_hash` is derivable today, and the profile must pin *what* is hashed

`connector/canon.py` ships `canonicalize()` (RFC 8785 subset — sorted keys, UTF-8,
no incidental whitespace, `allow_nan=False`) and `sha384_hex()`. Both already exist at the
pinned commit; no ZTL change is needed. Worked example:

```
canonical : {"atoms":["p","q"],"formula":"(p ∨ q)"}
sha384    : 57d0b23f476390915e5cbcd7ddfd1717ebef31606fe5927d5ccaefb3a7dde152
            4f3aaaf3d0b70f24d6e7059fe2908bbb
```

**Two things `ztl-jcs-float-free-sha384-v0.1` must state or the digest is not interoperable:**

1. **The exact object shape.** Above it is `{"atoms": [...], "formula": "..."}` with sorted
   atoms. Any other shape gives a different digest for the same logical content.
2. **Which rendering of the formula.** The caller supplied `p | q`; the kernel returned
   `(p ∨ q)` — parenthesised, and Unicode `∨` (U+2228). **The kernel's rendering is the one
   that must be hashed**, because it is the normalised form. An adapter that hashes the
   caller's input string will disagree with one that hashes the kernel's output on every
   formula. The UTF-8 requirement is load-bearing here, not decorative.

The "float-free" part of the profile name is accurate: no JSON numbers occur in this object,
which is why the RFC 8785 subset is sufficient. `canon.py` says so in its own scope note, and
also says what to do if numbers are ever introduced. That honesty should survive into the
profile: it is a subset, not full JCS.

### 4.3 `dependency_ids` — derivable, but only as the over-approximation

The field means "ground identifiers the conclusion depends on, used for revocation and expiry
propagation". "Depends on" is operationally testable: a ground is load-bearing if withdrawing
it — the anti-tick, a verified atom returning to `Z` — moves the disposition.

**Probing one ground at a time is not sound.** Measured: of 180 cases with two or more
verified grounds, **38** have a pair whose joint withdrawal moves the disposition although
neither member moves it alone.

```
(p | q) & r     {p:T, q:T, r:T}   ->  EARNED / hereditary

  withdraw p alone   ->  EARNED
  withdraw q alone   ->  EARNED
  withdraw p and q   ->  OPEN / until-verification
```

Redundant grounds — the ordinary shape of a control satisfiable several ways. A minimised
dependency set omits `p` and `q`; the revocation of both then propagates to nothing and an
`ESTABLISHED` warrant outlives its grounds.

**Recommendation: `dependency_ids` = every verified atom of the formula.** Do not minimise.
The over-approximation costs recomputations that turn out unnecessary; minimisation costs
correctness, in the direction that leaves stale warrants usable.

`dependency_ids` and `unverified_ground_ids` are then disjoint by construction: verified
grounds in the first, unverified in the second, together the formula's atoms. That is a
checkable invariant, and worth asserting in the contract test.

### 4.4 `output_hash` must exclude `why`

`why` is presentational and may change without a profile bump — the profile says so. If it is
inside `output_hash`, a wording change breaks every stored digest. Hash the six stable fields:
`disposition`, `grade`, `verdict`, `formula`, `unverified`, `marking`.

### 4.5 `limitations` — the kernel's ceiling is derivable; the institution's is not

A fixed ceiling follows from the profile alone and should be emitted by the adapter, not
hand-written per warrant:

> This warrant establishes a logical relation between a formula and a supplied marking under
> kernel profile `ztl-v0.1`. It does not establish source authenticity, authority,
> admissibility, institutional time, or permission to act.

Anything beyond that — what *this* control does not establish — is OIC's to add. Requiring the
array to be non-empty is a good rule; the derivable sentence guarantees it can never be empty
by accident.

---

## 5. Profile confirmation

Confirmed against the pinned kernel, by execution:

| Claim | Verdict |
|---|---|
| canonical entrypoint is `ztljudge.judge` | **CONFIRMED** |
| marking dialect is `T` / `F` / `Z` | **CONFIRMED** |
| `zverify.grade` must not be called directly by OIC | **CONFIRMED** — and correctly listed as a prohibited entrypoint, hazard `ZTL-H-001`, severity critical |
| the Z/M mismatch and its silent `hereditary` result are accurately described | **CONFIRMED** — see the measured runs below; the consequence the profile states (ON CREDIT read as EARNED) is exactly right |
| disposition vocabulary is `EARNED`, `REFUTED`, `ON CREDIT`, `OPEN` | **CONFIRMED** — no fifth value occurs in 294 cases |
| grade vocabulary is `hereditary`, `sound`, `until-verification` | **CONFIRMED**, and `hereditary` ⟹ `sound` as the ladder states |

### 5.1 The `ZTL-H-001` hazard, measured

```
~(p & q)          {p:T, q:Z}    judge() -> ON CREDIT / until-verification
                                zverify.grade, 'M' dialect  -> until-verification
                                zverify.grade, 'Z' passed   -> hereditary      WRONG, SILENT

(~p) -> (q -> q)  {p:Z, q:Z}    judge() -> ON CREDIT / sound
                                zverify.grade, 'M' dialect  -> sound
                                zverify.grade, 'Z' passed   -> hereditary      WRONG, SILENT

p & q             {p:T, q:Z}    judge() -> OPEN / until-verification
                                zverify.grade, 'M' dialect  -> until-verification
                                zverify.grade, 'Z' passed   -> hereditary      WRONG, SILENT
```

The wrong answer is always the strongest grade, for every disposition — the failure direction
that matters. **One addition to the profile's hazard note:** `zverify.grade` does not take a
formula string at all. Its first argument is a parsed term (`ztljudge.formalize(...)`), so an
adapter cannot reach the hazard by a plain string call — it reaches it only by deliberately
building the parse first. That makes the prohibited-entrypoint rule easy to enforce
mechanically: an OIC adapter that never imports `zverify` cannot express the mistake.

**One correction to the profile**, carried into the mapping review: `disposition_values` gives
`EARNED` the constraint `"unverified": "empty"`. Measured: `EARNED` carries a non-empty
`unverified` list in **61 of 294 cases**. The correct value is `"any"`. Detail, evidence and
consequence: [`MAPPING-REVIEW-v0.1.md §3`](MAPPING-REVIEW-v0.1.md) and
[`evidence/KERNEL-CENSUS-v0.1.md`](evidence/KERNEL-CENSUS-v0.1.md).

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the
OIC semantic implementation gate remains BLOCKED.*
