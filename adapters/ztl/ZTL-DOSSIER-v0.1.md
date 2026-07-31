# ZTL Dependency Verification Dossier — v0.1

**Prepared for:** Open Institutional Compiler (TDD-OIC-001 v1.1), module **M6 — Dependency and Warrant Engine**, and `adapters/ztl/`.
**Prepared by:** Vitaly Reznik (ZTL semantic boundary and adapter owner, per OIC `OWNERS.md`).
**Date:** 2026-07-29.
**Status of this document:** upstream-side record. It supplies the fields required by OIC `DEPENDENCIES.md` and TDD §3.5. It does **not** assert that ZTL has been independently reviewed or reproduced; see §13.

---

## 1. Repository / artifact location

| Item | Value |
|---|---|
| Source repository | `https://github.com/inventor1975/ZTL` (public) |
| Kernel entry points | `ztljudge.py` (`judge`, `check`, `join`, `formalize`), `zverify.py` (`grade`) |
| Lean corpus | `lean/` — 21 modules |
| Connector (drop-in boundary) | `connector/` — `canon.py`, `signer.py`, `warrant.py`, `verdict.py`, `schema/`, `fixtures/`, `harness.py` |
| Published preprint | ZTL v1.3, DOI **10.5281/zenodo.21472971** (concept DOI 10.5281/zenodo.21318981) |

## 2. Owner and maintenance authority

Vitaly Reznik, sole owner and maintainer. Contact via the repository.
Arkadiy Miteiko / Veraxis / VRG are **not** inventors or co-owners of ZTL (stated in writing by Arkadiy Miteiko, 2026-07-20).

## 3. License and permitted use

**MIT** (see `LICENSE`). Open and hosted use both permitted, including commercial use, with attribution as required by MIT.
Preprint text: separate, cite by DOI.

## 4. Immutable version (what OIC must pin)

| Pin | Value |
|---|---|
| Annotated tag | `veraxis-ztl-input-v0.1` |
| Tag target commit | `e819dec7e89d2dc67d6371e1eedb8e7aae854602` (2026-07-21) |
| Lean toolchain | `leanprover/lean4:v4.29.1` |
| Standalone dependency-closure commit | `82a0f6ac61e0ddf9a927a70e04a0018989ef316d` |

The tag is **annotated, not GPG-signed** (the maintainer has no GPG key configured). Signature is an open hardening item, not a claim.

## 5. Interface schema (the pinned boundary)

Stable public surface OIC may call. Any change to these signatures requires a new version, not an edit.

```
judge(text: str, marking: dict[str, "T"|"F"|"Z"] | None) -> dict
    -> { formula, verdict: "T"|"F"|"Z", grade: "hereditary"|"sound"|"until-verification",
         disposition, unverified: [atom, ...], why }

check(text, marking)                     # single claim
join(text_a, text_b, operator, marking)  # two claims under an operator
grade(phi, marking)                      # warranty grade only -- SEE HAZARD BELOW
formalize(text)                          # parse to AST; no evaluation
```

Connector-level JSON contracts (for artifact exchange rather than in-process calls):
`connector/schema/warrant-form.schema.json`, `connector/schema/verdict-artifact.schema.json`.
Canonicalisation: RFC 8785 (JCS) subset, float-free. Digest: SHA-384 over `{claim, rule, atoms}`.

**Mark-dialect hazard.** `zverify.grade()` expects `'M'` for a mark; `judge()` accepts `'Z'` and converts internally. Passing `'Z'` to `zverify.grade()` returns `hereditary` **silently and wrongly** for every input. Consume `judge()`; if `grade()` is called directly, translate the dialect first. Every conformance fixture records both readings.

## 6. Semantics and semantic boundary statement

### 6.1 What the kernel computes

Three truth states — **T** (earned true), **F** (earned false), **Z** (a **mark**: not verified). Z is not a third truth value in the Suszko sense; it marks the *status of verification*. Compound formulas never take Z as a value (greedy collapse): Z survives only on a bare atom.

Verdict is accompanied by a **warranty grade**:

| Grade | Meaning |
|---|---|
| `hereditary` | invariant under **every** admissible monotone refinement Z→T/F of the *same* φ and marking |
| `sound` | true under supervaluation of the current marking — never lies, may stall |
| `until-verification` | holds only in the present marking; not yet settled |

`hereditary ⟹ sound` is a theorem. `hereditary` is the only monotone sort.

### 6.2 What the kernel MUST NOT be asked to do (boundary)

ZTL does **not**, and cannot:

- validate whether a source document is authentic;
- determine institutional authority, delegation, or jurisdiction;
- interpret prose or extract meaning from documents;
- create or represent institutional **admission**;
- decide the operational verdict ALLOW/DENY/CANNOT/ESCALATE on its own.

These are OIC's planes (compilation, admission, enforcement), not the kernel's. The kernel judges **logic over supplied grounds**; grounds and authority arrive from outside. This is not a limitation to be engineered away — it is the condition under which a warrant means anything.

### 6.3 Mapping to OIC Envelope behavior — **the place where a silent error is most likely**

This is a **proposed interpretation** and requires joint conformance tests before either side relies on it:

> **CORRECTION 2026-07-29.** This section originally listed **three** dispositions. The kernel has **four**: `ON CREDIT` was missing. It is a T verdict that is *not* `hereditary` — true only while an unverified atom holds. Routed as EARNED it would authorise action on credit, which is the precise failure ZTL exists to expose. Both real cases are fixtured (`on-credit-sound`, `on-credit-until-verification`). Corrected table below; see also `MAPPING-REVIEW-v0.1.md`.

| ZTL result (`disposition` + `grade`) | OIC Envelope behavior | Rationale |
|---|---|---|
| `EARNED` + `hereditary` | supports ALLOW (subject to authority/evidence, which ZTL does not check) | invariant under further verification |
| **`ON CREDIT` + `sound`** | ALLOW **only** where the envelope explicitly tolerates a non-monotone warrant; otherwise ESCALATE with `unverified` | never lies about the present marking, but may stall |
| **`ON CREDIT` + `until-verification`** | **ESCALATE**, not ALLOW | rides an unverified atom that can flip |
| `REFUTED` | supports DENY | grounds establish falsity |
| **`OPEN`** (raw verdict F or Z; never T) | **`on_unknown` → ESCALATE / CANNOT**, *never* `on_conflict` → DENY | absence of verification is **not** falsity |
| `unverified` list non-empty | `missing_inputs` | the unverified atoms blocking the conclusion |
| contradiction record | `on_conflict` → DENY | grounds are mutually inconsistent |

**Warning we ask OIC to test explicitly — with a measured example.** Run against the pinned kernel:

```
>>> judge("p & q", {"p": "T", "q": "Z"})
{ 'verdict': 'F', 'grade': 'until-verification', 'disposition': 'OPEN',
  'unverified': ['q'], 'formula': ..., 'why': ... }
```

The raw `verdict` is **F** (default deny), while `disposition` is **OPEN** and `grade` is **until-verification**. An adapter that reads `verdict` alone turns *"not yet established"* into *"established false"* — violating OIC invariant I-04 and the metric `Unknown-to-false conversion = 0`. This will not surface in ordinary tests until a genuinely undetermined case reaches production.

**Therefore the adapter contract we ask for:** consume **`disposition`** (`EARNED` / `REFUTED` / **`ON CREDIT`** / `OPEN`) as the primary signal, `grade` as the warranty qualifier, and `unverified` as `missing_inputs`. Treat the bare `verdict` field as an internal detail of the kernel, not as the operational answer. **The grade is not optional metadata; it is half of the result.**

### 6.4 Logical time (E24/E25) — offered for alignment

ZTL has a measured model of time in which **a tick is the arrival of ground** (an act of verification, Z→T/F), and `expire` is the **anti-tick**: ground being withdrawn (a re-checked registry, an expired document). The three warranty grades are exactly three temporal quantifiers: now / at all endings / always on all paths.

OIC's change propagation, revocation and re-admission are structurally the same anti-tick. We suggest aligning the two models explicitly rather than maintaining two independent notions of time in one system. Measured consequence from our side: **unrestricted expiry trivialises warranties** — a test invariant under both refinement *and* arbitrary expiry is constant, i.e. a frame that cannot fail. Expiry must therefore be scoped, not global.

## 7. Fixture hashes

| Artifact | SHA-256 |
|---|---|
| `VERAXIS-ZTL-CONFORMANCE-input-v0.1.md` | `33de416110be748a647216ef97b246e925b2dcde95e95cbefdd13cf51f69bb8c` |
| `VERAXIS-ZTL-fixtures-v0.1.json` | `717853cf2a84ede0cb0472192d2e4fac4303acf29775f0d41d972e15c3652f93` |
| `VERAXIS-ZTL-deps-v0.1.json` | `efe05b396cdb4a8731f51b5cc927a8fc998e01a789a2a6dff5657e5a2b5971a5` |

## 8. Conformance tests

- **28 typed fixtures**, 8 `subject_kind`s: `formula_evaluation`, `inference_rule`, `entailment`, `tableau_closure`, `engine_equivalence`, `refinement_relation`, `warranty_relation`, `bounded_witness`. Fields `retained_atom_state` / `expected_formula_verdict` / `epistemic_status` appear **only** where semantically applicable — no generic defaults.
- Every adversarial fixture names the `prohibited_conversion` and the reason code the consumer must return on rejection.
- **28 declarations** documented in the conformance input with 13 fields each, including `PROHIBITED` use and an explicit **claim ceiling** per declaration.
- **Transitive dependency closure**: 826 edges over 169 distinct corpus objects; computed from the Lean kernel (`Expr.getUsedConstants` over `ConstantInfo` type+value), recursing only through corpus constants. **mathlib does not leak in** — by construction, not by inspection.
- **Connector fixtures**: `connector/fixtures/ZTL-CORE-JUDGE-fixtures-v0.1.json` — 8 cases, harness PASS 8/8 plus sign/verify and tamper-detection checks.
- **Regression**: 59 executable stands (`python3 run_all.py`) + full Lean build.

## 9. Corpus evidence

371 theorems across 21 Lean modules, **all on the empty axiom list** (`#print axioms` yields `[]` for every one). Evidence taxonomy over the 371: 285 `GENERAL`, 45 `BOUNDED_MODEL`, 2 `EXISTENCE_WITNESS`, 39 `CONCRETE_CELL`. A bounded scope is **not** "less proved" — it is a proof about a bounded model, and is labelled as such.

## 10. Failure behavior

| Condition | Required behavior |
|---|---|
| Kernel unavailable | OIC compilation may continue in **review-only** mode; publication requiring a warrant is **blocked**. A warrant must never be fabricated. |
| Unsupported formula | Block warrant-dependent publication or route to human judgment. Do not degrade to a guess. |
| Contradiction | Return contradiction record plus the affected dependency set. |
| Ground expired | Recompute and propagate invalidation. |
| Version mismatch | Reject replay unless a byte-identical compatible engine/profile is available. |
| Input exceeds bounds (see §11) | Raise `WarrantError`; fail closed, never partially evaluate. |

Default posture is **fail-closed**: missing ground, unsupported input or engine absence must never yield a permissive result.

## 11. Security notes

Measured, not asserted (audit 2026-07-23; fixes shipped in commit `48be9ae`):

- **No injection surface**: the formula parser is hand-written (no `eval`); no SQL, no shell.
- **Three DoS vectors found by measurement and closed**:
  1. grading is `O(3^distinct_atoms)` — 14 distinct atoms hung the process for >8 s;
  2. parser recursion depth ~1000 → `RecursionError`;
  3. root cause: no input bounds existed.
- **Bounds now enforced** in `warrant.py::validate`: `MAX_CLAIM_LEN=1024`, `MAX_ATOMS=64`, **`MAX_DISTINCT_ATOMS=12`** (3¹² ≈ 5.3e5, sub-second — the principal cap), `MAX_NAME_LEN=128`, `MAX_PROVENANCE_LEN=4096`; `RecursionError` is converted to `WarrantError`. Three regression guards added to the harness.
- **Signing**: crypto-agile. Ed25519 is live; ML-DSA-65 and hybrid are declared slots and report `unavailable` when no backend is present — **PQC is not faked**. Honest current claim: *quantum-ready, crypto-agile, hybrid supported* — **not** "we sign with ML-DSA today". Production intent: audited `liboqs`, default `ed25519+ml-dsa-65`.
- **Offline verification**: `verdict.py::verify_artifact` verifies an artifact without any server of the consuming protocol — a consumer is never locked to a vendor to check a verdict.

## 12. Known limitations and claim ceiling

- ZTL gives **no** mathematical material and is not a foundational logic; it is finite, decidable, tabular. Its strengths are clarity, implementability and honesty — not generative depth.
- The kernel decides **propositional** structure over supplied atoms. Arithmetic, quantities, dates, "only"/"all" quantification and world knowledge are **outside** it: such content must be folded into an atom by the party that establishes it, and that folding is not the kernel's act.
- Verdict is **not** world state; `F` is not a grounded negative fact unless grounds establish it.
- `hereditary_absorbing` is scoped: invariance under admissible monotone Z→T/F within the **same** φ, marking and semantics. It does **not** waive re-checking on expiry, revocation, correction, source invalidation, schema change, formula change, semantic-version change, or institutional admissibility.
- Novelty claim is **narrow and specific**: `¬¬p ⊨ p` separates ZTL from three-valued matrices with an **involutive** negation (K3 / LP / weak Kleene / Ł3 and the infinite class implied). External Bochvar is **not** separated by this rule (it shares the broken involution); the difference there lies in the implicative fragment and has **not** been measured. Prior art for the clone census is Finn 1974.
- No claim is made that ZTL is the first or only such system, nor that it guarantees legal or regulatory correctness.

## 13. Independent reproduction status — **OPEN**

**No independent reproduction has been performed.** This field is deliberately left open rather than filled with a weaker substitute.

- A reproduction recipe exists and is public: `REPRODUCE.md`, pinned to an immutable commit; it yields 59 stands / 371 theorems / 21 modules.
- The maintainer's own run is **Tier 3 (author-side)** and is labelled as such. It is **not** independent evidence.
- Tier policy (agreed with Arkadiy Miteiko, 2026-07-22): **Tier 1** = unrelated engineer; **Tier 2** = disclosed acquaintance outside development; **Tier 3** = author, family, co-author, developer. **The first report must be Tier 1.** A spouse, relative or co-author is excluded — this was fixed by Arkadiy himself.
- Claim ladder: only after **three** Tier-1 reports may anyone state "independent parties reproduced this without author involvement".
- Templates in place: `reproductions/INDEPENDENT-REPRODUCTION-REPORT-TEMPLATE.md`, `reproductions/README.md`.
- Lowering the cost: the Lean corpus is import-free / mathlib-free and can be pasted into `live.lean-lang.org` and checked in a stranger's browser — built before the requirement existed.

**Consequence for OIC:** any OIC statement about ZTL maturity must currently read *"project-controlled dependency, provisional, independent reproduction OPEN"*. We ask that this not be softened on our behalf.

## 14. Replacement strategy

If ZTL is unavailable, unacceptable, or replaced:

1. **The interface, not the implementation, is the contract.** §5 is a small, total surface (four functions). Any engine that (a) returns T/F/Z with a warranty grade, (b) never serialises an unverified state as false, and (c) reports the unverified atoms blocking a conclusion, can be substituted behind the same adapter.
2. **A deterministic reference evaluator** must remain available on the OIC side (TDD §4.6 already requires this), so that a ZTL outage degrades to review-only rather than to an invented warrant.
3. **What would be lost** on substitution, stated honestly: the machine-checked corpus on an empty axiom list, the warranty ladder (`hereditary`/`sound`), and the measured separation results. A substitute providing only T/F/Z without grades satisfies the interface but **not** §6.3 — envelopes relying on grade semantics must then be re-admitted, not silently re-pointed.
4. **Migration test**: the 28 fixtures in §7 are the acceptance suite for any replacement. A replacement that fails an adversarial fixture must not be swapped in.

---

## Open items on our side (not claims)

| Item | State |
|---|---|
| Independent Tier-1 reproduction | OPEN — sought by Arkadiy Miteiko; cannot be closed by us |
| GPG signature on the release tag | OPEN — no key configured |
| Joint ZTL↔Envelope mapping conformance test (§6.3) | PROPOSED — requires OIC side to define expected Envelope behavior |
| ZTL↔OIC time-model alignment (§6.4) | PROPOSED |
| `MissingGround` granularity vs OIC review docket | QUESTION — ours is a list of unverified atoms; OIC to confirm this matches what a reviewer needs |

*This dossier states what is measured, what is argued, and what is open. Nothing in it should be read as evidence of independent review.*
