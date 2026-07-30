# ZTL → Open Control Envelope mapping, v0.1

**Status: PROPOSED. Not admitted, not implemented, not called.**

> **The canonical artifact is [`ZTL-OCE-MAPPING-v0.1.json`](ZTL-OCE-MAPPING-v0.1.json).**
> The table below is **generated** from it by `tools/render_mapping.py` and verified
> against it by `tests/contract/test_warrant_contract.py`. Edit the JSON, then re-render.
> Editing this table by hand will fail the build.

Governing decision: [ADR-013](../../adr/ADR-013.md).
Field definitions: [WARRANT-CONTRACT-v0.1.md](WARRANT-CONTRACT-v0.1.md).

## The disposition correction

ZTL dossier v0.1 listed **three** dispositions — `EARNED` / `REFUTED` / `OPEN`. The kernel
has **four**. `ON CREDIT` was omitted, and it is the one that matters most for an
enforcement contract:

| Disposition | Grade | Raw verdict | Meaning |
|---|---|---|---|
| `EARNED` | `hereditary` | `T` | Grounded outright; unverified atoms are irrelevant |
| `REFUTED` | `hereditary` | `F` | False regardless of the marks |
| **`ON CREDIT`** | `sound` or `until-verification` | `T` | **True only while an unverified atom holds** — it can die when that atom resolves |
| `OPEN` | `until-verification` | `F` or `Z` | Not established; a mark actually matters |

Mapped as `EARNED`, `ON CREDIT` would authorise action on an unverified link — the exact
failure a zero-trust warrant exists to prevent. Mapped as `OPEN` it would over-block: the
verdict *is* `T`, and under `sound` it never lies about the present marking. It therefore
gets its own rows, and the `warrant_requirement` object decides whether a control accepts
that grade.

The earlier version of this mapping was written against the three-value list and was wrong
in three places. Rows 24 and 29–31 record the corrections rather than deleting the history.

## How to read the table

**Total over the input space**, not over the outputs ZTL is known to emit. Rows marked
`NOT_REACHABLE` describe combinations the kernel cannot produce; they are specified anyway
so an adapter meeting one fails closed rather than falling through.

`Authority` records where a row's content comes from:

| Value | Meaning |
|---|---|
| `MEASURED` | Reproduced against the pinned kernel; fixture exists in `adapters/ztl/fixtures/interface-freeze-v0.1/` |
| `ZTL-CONFIRMED` | ZTL states the combination is not reachable; retained as a defensive row |
| `OIC-DEFENSIVE` | An OIC-side condition, not a kernel output — not a claim about ZTL |
| `PENDING-ZTL` | Awaiting measured evidence (none remain in v0.1) |

`Execution` shows the permitted choices. `BLOCK / ESCALATE` means the envelope chooses via
`on_unknown`: `cannot` or `deny` → `BLOCK`; `escalate` → `ESCALATE`. The choice never
changes `Epistemic` or `Basis`.

Where an OIC-side condition and a kernel disposition both apply, **the OIC-side condition
wins** — see precedence below.

<!-- MAPPING-TABLE-START -->

### Stage 1 - classification

| # | Disposition | Grade | Unverified | OIC condition | Prec | Warrant state | Epistemic | Base execution | Basis | Reason | Reachability | Authority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | any | any | any | kernel unavailable | 1 | ABSENT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0002 | REACHABLE | OIC-DEFENSIVE |
| 2 | any | any | any | warrant absent | 1 | ABSENT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0001 | REACHABLE | OIC-DEFENSIVE |
| 3 | any | any | any | warrant malformed | 1 | MALFORMED | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0003 | REACHABLE | OIC-DEFENSIVE |
| 4 | any | any | any | warrant hash unverifiable | 1 | UNVERIFIABLE | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0004 | REACHABLE | OIC-DEFENSIVE |
| 5 | any | any | any | warrant_requirement missing or invalid | 1 | MALFORMED | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0026 | REACHABLE | OIC-DEFENSIVE |
| 6 | any | any | any | warrant stale | 2 | STALE | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0005 | REACHABLE | OIC-DEFENSIVE |
| 7 | any | any | any | warrant expired | 2 | EXPIRED | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0006 | REACHABLE | OIC-DEFENSIVE |
| 8 | any | any | any | warrant not yet valid | 2 | NOT_YET_VALID | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0021 | REACHABLE | OIC-DEFENSIVE |
| 9 | any | any | any | ground expired | 2 | REVOKED | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0020 | REACHABLE | OIC-DEFENSIVE |
| 10 | any | any | any | ground revoked | 2 | REVOKED | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0007 | REACHABLE | OIC-DEFENSIVE |
| 11 | any | any | any | epoch mismatch within scope | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0008 | REACHABLE | OIC-DEFENSIVE |
| 12 | any | any | any | source-version mismatch | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0009 | REACHABLE | OIC-DEFENSIVE |
| 13 | any | any | any | admission-version mismatch | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0010 | REACHABLE | OIC-DEFENSIVE |
| 14 | any | any | any | formula mismatch | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0011 | REACHABLE | OIC-DEFENSIVE |
| 15 | any | any | any | kernel or canonicalization profile mismatch | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0023 | REACHABLE | OIC-DEFENSIVE |
| 16 | any | any | any | source anchors missing | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0018 | REACHABLE | OIC-DEFENSIVE |
| 17 | any | any | any | admission IDs missing | 2 | MISBOUND | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0019 | REACHABLE | OIC-DEFENSIVE |
| 18 | any | unknown | any | warranty grade not in the profile ladder | 2 | UNSUPPORTED_GRADE | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0017 | REACHABLE | OIC-DEFENSIVE |
| 19 | any | any | any | disposition/grade/raw-verdict/unverified combination violates the frozen profile | 2 | UNSUPPORTED_RESULT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0022 | REACHABLE | OIC-DEFENSIVE |
| 20 | any | any | any | unknown disposition value | 2 | UNSUPPORTED_RESULT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0022 | REACHABLE | OIC-DEFENSIVE |
| 21 | any | any | any | warrant_requirement mode explicitly not_required or not_applicable | 2 | NOT_REQUIRED | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0024 | REACHABLE | OIC-DEFENSIVE |
| 22 | any | any | any | contradictory grounds | 3 | USABLE | CONTRADICTED | BLOCK | SUBSTANTIVE | OIC-W-0014 | REACHABLE | OIC-DEFENSIVE |
| 23 | REFUTED | hereditary | any | warrant usable | 4 | USABLE | REFUTED | BLOCK | SUBSTANTIVE | OIC-W-0013 | REACHABLE | MEASURED |
| 24 | OPEN | until-verification | non-empty | raw verdict F | 4 | USABLE | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | REACHABLE | MEASURED |
| 25 | OPEN | until-verification | non-empty | raw verdict Z | 4 | USABLE | UNRESOLVED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0012 | REACHABLE | MEASURED |
| 26 | OPEN | any | any | raw verdict T | 4 | UNSUPPORTED_RESULT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0022 | NOT_REACHABLE | ZTL-CONFIRMED |
| 27 | EARNED | hereditary | any | all checks pass | 5 | USABLE | ESTABLISHED | ALLOW | SUBSTANTIVE | OIC-D-0001 | REACHABLE | MEASURED |
| 28 | ON CREDIT | sound | non-empty | grade permits sound | 5 | USABLE | CONDITIONALLY_SUPPORTED | ALLOW / BLOCK / ESCALATE | CONTROL_REQUIREMENT | OIC-W-0015 | REACHABLE | MEASURED |
| 29 | ON CREDIT | until-verification | non-empty | any | 5 | USABLE | CONDITIONALLY_SUPPORTED | BLOCK / ESCALATE | PRECAUTIONARY | OIC-W-0025 | REACHABLE | MEASURED |
| 30 | EARNED | sound | any | any | 5 | UNSUPPORTED_RESULT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0022 | NOT_REACHABLE | ZTL-CONFIRMED |
| 31 | EARNED | until-verification | any | any | 5 | UNSUPPORTED_RESULT | UNRESOLVED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0022 | NOT_REACHABLE | ZTL-CONFIRMED |
| 32 | ON CREDIT | any | non-empty | conditional-support subscription missing or incomplete | 2 | USABLE | CONDITIONALLY_SUPPORTED | BLOCK / ESCALATE | PROCEDURAL | OIC-W-0027 | REACHABLE | OIC-DEFENSIVE |

### Stage 2 - warrant policy

Applied in `Order`: grade sufficiency first, then the unverified-ground policy.

| ID | Order | Trigger | Epistemic effect | Execution | Basis | Policy reason |
|---|---|---|---|---|---|---|
| WP-1 | 1 | warranty_grade_observed below warrant_requirement.minimum_warranty_grade, on_insufficient_grade = escalate | PRESERVE | ESCALATE | CONTROL_REQUIREMENT | OIC-W-0016 |
| WP-2 | 1 | warranty_grade_observed below warrant_requirement.minimum_warranty_grade, on_insufficient_grade = block | PRESERVE | BLOCK | CONTROL_REQUIREMENT | OIC-W-0016 |
| WP-3 | 2 | epistemic_status = CONDITIONALLY_SUPPORTED, grade sufficient, unverified_ground_policy = allow_with_disclosure | PRESERVE | ALLOW | CONTROL_REQUIREMENT | OIC-D-0005 |
| WP-4 | 2 | epistemic_status = CONDITIONALLY_SUPPORTED, grade sufficient, unverified_ground_policy = forbid | PRESERVE | BLOCK | CONTROL_REQUIREMENT | OIC-D-0006 |
| WP-5 | 2 | epistemic_status = CONDITIONALLY_SUPPORTED, grade sufficient, unverified_ground_policy = escalate | PRESERVE | ESCALATE | CONTROL_REQUIREMENT | OIC-D-0006 |

### Stage 3 - decision mode

Applied last. `DM-1` is the identity and is never recorded in `applied_control_overlay_ids`.

| ID | Trigger | Epistemic effect | Execution | Basis | Policy reason |
|---|---|---|---|---|---|
| DM-1 | decision_mode = automatic | PRESERVE | PRESERVE | - | - |
| DM-2 | decision_mode in {human_judgment, escalation_only, non_automatable} | PRESERVE | ESCALATE | CONTROL_REQUIREMENT | OIC-D-0002 |
| DM-3 | decision_mode in {advisory, evidence_only} | PRESERVE | ADVISORY | CONTROL_REQUIREMENT | OIC-D-0003 |

### Semantic conformance rules

JSON Schema cannot express these. A record passing the schema and failing one of them is **invalid**.

| ID | Name | Applies to | Requirement | Not expressible as |
|---|---|---|---|---|
| SC-RD-001 | SUBSCRIPTION_GROUND_COVERAGE | RuntimeDecision where epistemic_status = CONDITIONALLY_SUPPORTED and execution_disposition = ALLOW | conditional_support_subscription_ground_ids must EQUAL missing_ground_ids exactly, including canonical order. Not a subset, not a superset, not a reordering. | equality between two sibling arrays |
| SC-RD-002 | SUBSCRIPTION_TRIGGER_SET | RuntimeDecision where epistemic_status = CONDITIONALLY_SUPPORTED and execution_disposition = ALLOW | conditional_support_subscription_triggers must equal exactly ['ground_corrected', 'ground_expired', 'ground_revoked', 'ground_verified', 'relevant_epoch_changed'], in that canonical order. | canonical ordering of an array |
| SC-RD-003 | OVERLAY_ORDER | every RuntimeDecision | applied_control_overlay_ids must list all applicable stage-2 WP identifiers first, then the single applicable non-identity stage-3 DM identifier last. No duplicates. DM-1 never appears. | ordering constrained by identifier prefix |
| SC-RD-004 | REASON_CODE_CANONICALIZATION | every RuntimeDecision | reason_codes must be unique, sorted lexicographically, and complete: every matched classification row and every applied policy stage contributes its code. | completeness relative to the mapping |
| SC-WA-001 | GROUND_PARTITION | WarrantArtifact produced under kernel_profile_id ztl-v0.1 | dependency_ids are exactly the formula atoms marked T or F; unverified_ground_ids are exactly the atoms marked Z; the two arrays are disjoint; their union equals the evaluated formula's atom set. Neither claims minimality. | a partition derived from the evaluated marking |
| SC-WA-002 | HASH_PROJECTIONS | WarrantArtifact produced under kernel_profile_id ztl-v0.1 | formula_hash is computed over the kernel-rendered formula, not the caller's string. output_hash is computed over the declared semantic projection, which EXCLUDES why and marking. | the provenance of a digest's input |

Stages 2 and 3 may change the execution disposition, the decision basis, and the policy reason codes. Neither may change the epistemic status fixed by stage 1, which is why every rule and overlay declares `epistemic_effect = PRESERVE`. Every matched policy reason code is **retained** even when a later stage changes the final execution disposition.

<!-- MAPPING-TABLE-END -->

## Precedence

When several rows match, the most restrictive wins, in this order:

1. **kernel or artifact unusable** — the claim was never validly evaluated;
2. **artifact misbound, stale, or grounds withdrawn** — evaluated against a different world;
3. **contradiction**;
4. **disposition**;
5. **disposition and warranty grade**;
6. **control policy override** (`decision_mode`).

Precedence is stated because a warrant can be simultaneously `EARNED`, `hereditary`, and
computed at an epoch that no longer exists. **The good news must not win.**

## What no row says

No row asserts `ALLOW` on the strength of the kernel alone. Rows 25 and 26 remain subject
to ADR-013 **W-4** conditions 4–8: authority, admission, evidence, and version checks that
ZTL does not perform and does not claim to. A row reaching `ALLOW` means *the logic does
not stand in the way*, not *the action is permitted*.

## Rows corrected after measured ZTL evidence

The first version of this mapping marked three rows `?` — our reading, awaiting
confirmation. Vitaliy Reznik supplied measured fixtures. All three are **NOT_REACHABLE**:

| Old assumption | Measured result | Now |
|---|---|---|
| `EARNED` + `hereditary` + non-empty `unverified` supports ALLOW | `EARNED` is grounded outright and never carries unverified grounds | Removed. The real non-empty-`unverified` ALLOW case is `ON CREDIT` + `sound` (row 26) |
| `EARNED` + `sound` reachable | `EARNED` requires `hereditary` by construction; a `sound` `T` is `ON CREDIT` | Rows 29–30, `NOT_REACHABLE`, retained for a substitute kernel |
| `OPEN` may carry raw `T` | Exhaustive search found no counterexample | Row 24, `NOT_REACHABLE`, defensive only |

Row 31 (`EARNED` + `until-verification`) is likewise confirmed `NOT_REACHABLE`. It is
reason-coded `OIC-W-0022` (unsupported result combination) rather than `OIC-W-0012`,
because its disposition is not `OPEN` and labelling it `DISPOSITION_OPEN` would be false.

**The prior review record is preserved, not rewritten.** The corrections are recorded here
and in ADR-013 §9 rather than by silently editing the earlier rows away.

## Time model alignment

| ZTL | OIC | Artifact field |
|---|---|---|
| tick — arrival of ground (Z → T/F) | ground admitted | `ground_epoch.sequence` increments within `scope_id` |
| anti-tick — ground withdrawn | expiry, revocation, correction | `revocation_references`, `valid_until` |
| `hereditary` — always on all paths | invariant under monotone refinement **only** | `warranty_grade` |
| `sound` — at all endings | never lies, may stall | `warranty_grade` |
| `until-verification` — now | present marking only | `warranty_grade` |

Expiry is **scoped**: per-artifact `valid_until`, per-ground `revocation_references`, and
an epoch that counts only within its own `scope_id` under a named `authority_id`. It is
never a global sweep, because unrestricted expiry makes warranty invariants trivially true.

The kernel has no clock and no epoch concept. It echoes an epoch OIC supplies and can
neither originate nor validate one, which is why `ground_epoch` carries an `authority_id`.

## Answers to the ZTL side's three questions

1. **Semantics of `on_unknown`** — see [WARRANT-CONTRACT §7](WARRANT-CONTRACT-v0.1.md#7-on_unknown-and-decision_mode).
   `on_missing`, `on_conflict`, and `on_error` do not exist in the current draft envelope;
   their absence is why rows 1–19 are keyed on OIC-side conditions rather than envelope
   policy. Whether to add them is an open question for the architecture lead.
2. **`ESCALATE` versus `CANNOT`** — both exist. `on_unknown: escalate` → `ESCALATE`
   (routed to a human); `on_unknown: cannot` → `BLOCK` with `OIC-D-0004` (the system
   states it cannot decide); `deny` → `BLOCK`, operational only, never substantive.
3. **May a row depend on `grade`?** — yes. The control carries it through the proposed
   [`warrant-requirement.schema.json`](../../schemas/proposed/warrant-requirement.schema.json),
   with no default: a control must declare `minimum_warranty_grade` explicitly.

## Standing

Proposed by the OIC side under OIC-WO-002. Requires:

- **Vitaliy Reznik** — row-by-row review now that the mapping exists, and confirmation
  that the `ON CREDIT` rows (26–28) match kernel behaviour;
- **GPT-5.6 Thinking** — architecture acceptance;
- **Arkadiy Miteiko / Veraxis** — final design authority.

No ZTL call was made to produce this document; the measured rows cite fixtures published
by the ZTL side. No adapter exists. The semantic implementation gate remains **BLOCKED**.
