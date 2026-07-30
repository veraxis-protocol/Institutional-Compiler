# Warrant and failure-semantics contract, v0.1

**Status: PROPOSED. Not admitted, not implemented, not called.**

Governing decision: [ADR-013](../../adr/ADR-013.md).
Canonical mapping: [ZTL-OCE-MAPPING-v0.1.json](ZTL-OCE-MAPPING-v0.1.json)
(rendered as [ZTL-OCE-MAPPING-v0.1.md](ZTL-OCE-MAPPING-v0.1.md)).
Schemas: [`schemas/proposed/`](../../schemas/proposed/).
Fixtures: [`tests/fixtures/warrant-contract/`](../../tests/fixtures/warrant-contract/).

The ZTL side asked that failure semantics be stated **first**, because a contract that
silently prefers a permissive default cannot be repaired later. So §2 comes before
everything else.

---

## 1. What this contract separates

| Question | Field | Owner of the answer |
|---|---|---|
| What do the admitted grounds establish? | `epistemic_status` | logic kernel, over grounds OIC supplied |
| Is the warrant current and usable? | `warrant_state` | OIC, from epoch, hashes, profiles, expiry, revocation |
| What did the runtime do? | `execution_disposition` | OIC envelope policy |
| Why did it do that? | `decision_basis` | OIC, derived from the first three |

Four questions, four fields. `schemas/draft/runtime-evaluation.schema.json` answers all
four with one `verdict` enum, which is the defect this contract corrects.

## 2. Failure semantics

**Default posture is fail-closed.** A missing kernel, a missing ground, an unusable
artifact, or an unsupported input never yields a permissive result. This matches the ZTL
side's own posture: a missing kernel blocks warrant-dependent publication rather than
fabricating a warrant.

**Fail-closed is not a finding.** Every entry below that blocks does so with a basis of
`PRECAUTIONARY`, `PROCEDURAL`, or `CONTROL_REQUIREMENT`. Only the `SUBSTANTIVE` rows say
anything about the world.

| # | Condition | `warrant_state` | Epistemic | Execution | Basis | Reason |
|---|---|---|---|---|---|---|
| 1 | Warrant absent | `ABSENT` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0001` |
| 2 | Kernel unavailable | `ABSENT` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0002` |
| 3 | Malformed warrant | `MALFORMED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0003` |
| 4 | Unverifiable warrant hash | `UNVERIFIABLE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0004` |
| 5 | `warrant_requirement` missing or invalid | `MALFORMED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0026` |
| 6 | Stale warrant | `STALE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0005` |
| 7 | Expired warrant | `EXPIRED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0006` |
| 8 | Warrant not yet valid | `NOT_YET_VALID` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0021` |
| 9 | Revoked ground | `REVOKED` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0007` |
| 10 | Expired ground | `REVOKED` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0020` |
| 11 | Epoch mismatch within scope | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0008` |
| 12 | Source-version mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0009` |
| 13 | Admission-version mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0010` |
| 14 | Formula mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0011` |
| 15 | Profile mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0023` |
| 16 | Missing source anchors | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0018` |
| 17 | Missing admission IDs | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0019` |
| 18 | Grade vocabulary unknown | `UNSUPPORTED_GRADE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0017` |
| 19 | Result combination violates the profile | `UNSUPPORTED_RESULT` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0022` |
| 20 | Explicit `not_required` / `not_applicable` | `NOT_REQUIRED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0024` |
| 21 | Contradictory grounds (OIC-plane, not a ZTL disposition) | `USABLE` | `CONTRADICTED` | BLOCK | `SUBSTANTIVE` | `OIC-W-0014` |
| 22 | `REFUTED` disposition | `USABLE` | `REFUTED` | BLOCK | `SUBSTANTIVE` | `OIC-W-0013` |
| 23 | `OPEN`, any raw verdict | `USABLE` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0012` |
| 24 | `EARNED` + `hereditary` (unverified list may be non-empty) | `USABLE` | `ESTABLISHED` | ALLOW¹ | `SUBSTANTIVE` | `OIC-D-0001` |
| 25 | `ON CREDIT` + `sound` + `allow_with_disclosure` | `USABLE` | `CONDITIONALLY_SUPPORTED` | ALLOW¹ | `CONTROL_REQUIREMENT` | `OIC-D-0005` |
| 26 | `ON CREDIT` + `sound` + `forbid` | `USABLE` | `CONDITIONALLY_SUPPORTED` | BLOCK | `CONTROL_REQUIREMENT` | `OIC-D-0006` |
| 27 | `ON CREDIT` + `sound` + `escalate` | `USABLE` | `CONDITIONALLY_SUPPORTED` | ESCALATE | `CONTROL_REQUIREMENT` | `OIC-D-0006` |
| 28 | `ON CREDIT` + `until-verification` | `USABLE` | `CONDITIONALLY_SUPPORTED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0025` |
| 29 | Grade below the control's minimum | `USABLE` | **preserved** | BLOCK / ESCALATE | `CONTROL_REQUIREMENT` | `OIC-W-0016` |
| 30 | `decision_mode` reserves the decision | `USABLE` | **preserved** | ESCALATE | `CONTROL_REQUIREMENT` | `OIC-D-0002` |
| 31 | `decision_mode` advisory / evidence-only | `USABLE` | **preserved** | ADVISORY | `CONTROL_REQUIREMENT` | `OIC-D-0003` |
| 32 | Conditional ALLOW without a complete subscription | `USABLE` | `CONDITIONALLY_SUPPORTED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0027` |
| 33 | Non-empty `unverified` list | unchanged | unchanged | unchanged | unchanged | `OIC-W-0015` added |

Rows 29 to 31 say **preserved** rather than naming a status, and that is the point. Grade
insufficiency and decision-mode overlays are stages 2 and 3 of evaluation; they change what
the runtime did, never what the grounds establish. `REFUTED` + `human_judgment` is
`REFUTED` / `ESCALATE`; `CONDITIONALLY_SUPPORTED` + `advisory` stays conditionally
supported.

¹ `ALLOW` additionally requires **W-4** conditions 4–8 (authority, admission, evidence,
versions). Rows 23–24 mean *the logic does not stand in the way*.

Row 28 is deliberately not a failure. A non-empty `unverified` list is **recorded on every
outcome including `ALLOW`**, and never downgrades an otherwise sound result on its own.
What it must never do is disappear.

## 3. Epistemic status

Five values. The distinction the fifth one carries is the reason this section exists.

| Value | Meaning |
|---|---|
| `ESTABLISHED` | The grounds establish the claim **independently of any unresolved ground**, under the profile's hereditary contract. |
| `CONDITIONALLY_SUPPORTED` | The current admitted marking supports the claim, but the positive result **depends on one or more unverified grounds** and is not invariant under admissible refinement. |
| `REFUTED` | The grounds establish its negation. |
| `UNRESOLVED` | The grounds do not settle it, or it was never validly evaluated. |
| `CONTRADICTED` | The admitted ground set is inconsistent — a finding about the grounds, not a refutation of the proposition. |

Mapping from the `ztl-v0.1` profile:

| Disposition | Epistemic status |
|---|---|
| `EARNED` | `ESTABLISHED` |
| `ON CREDIT` | `CONDITIONALLY_SUPPORTED` |
| `OPEN` | `UNRESOLVED` |
| `REFUTED` | `REFUTED` |
| contradictory grounds | `CONTRADICTED` |

**`ESTABLISHED` is reserved** for positive results independent of unresolved grounds under
the profile's hereditary contract. **`CONDITIONALLY_SUPPORTED` preserves a current positive
result that depends on unverified grounds.**

`ON CREDIT` must never serialise as `ESTABLISHED` — that authorises action on an unverified
link, which is the precise failure a zero-trust warrant exists to expose. Nor may it
collapse to `UNRESOLVED` merely because grounds are unverified: the verdict genuinely *is*
`T`, and under `sound` it never lies about the present marking. Discarding that would
over-block.

**Permission to act on conditional support is an admitted control decision, not a stronger
epistemic claim.** The control grants it through `unverified_ground_policy`; the epistemic
status does not change when it does. Downstream VEIP records **must preserve** the
conditional status, the missing grounds, the observed grade, and the applied policy — a
consumer that stores only `ALLOW` has destroyed the only evidence that the permission was
conditional.

## 4. The four dimensions of `decision_basis`

| Value | Meaning |
|---|---|
| `SUBSTANTIVE` | The admitted grounds determine a positive, negative, or contradictory epistemic result. |
| `PRECAUTIONARY` | The grounds remain unresolved and the runtime fails closed. |
| `PROCEDURAL` | The claim could not be validly evaluated: an artifact, binding, version, availability, or integrity precondition failed. |
| `CONTROL_REQUIREMENT` | The claim **was** validly evaluated, but the admitted control requires a particular assurance grade, human role, escalation path, or non-automatic decision mode. |

Accurate readings, and the ones that matter:

- **`SUBSTANTIVE` + `ESTABLISHED`** is a positive finding about the admitted grounds.
- **`SUBSTANTIVE` + `REFUTED`** is a negative finding about the admitted grounds.
- **`SUBSTANTIVE` + `CONTRADICTED`** is a finding that the admitted ground set is
  inconsistent. **It is not a refutation of the proposition.**
- **`PRECAUTIONARY`, `PROCEDURAL`, and `CONTROL_REQUIREMENT` are not findings that the
  proposition is false.**

`CONTROL_REQUIREMENT` exists because the alternative was to report an institutional policy
as either a defect or a doubt. When a control says *"a human decides this"*, the logic
worked perfectly and the institution reserved the call. Recording that as `PROCEDURAL`
would send an engineer to fix a pipeline that is not broken; recording it as
`PRECAUTIONARY` would suggest the grounds were lacking when they were not.

`CONTROL_REQUIREMENT` **never rewrites `epistemic_status`**. An escalated `ESTABLISHED`
stays `ESTABLISHED`.

## 5. The ALLOW gate

`ALLOW` has exactly **two positive routes**. Both require every common condition:

1. kernel available, pinned, version-matched → else `OIC-W-0002`
2. warrant present, well-formed, hash-verified → else `OIC-W-0001` / `0003` / `0004`
3. a valid `warrant_requirement` with `mode: required` → else `OIC-W-0026` / `OIC-W-0024`
4. warrant fresh: epoch within scope, ground-set hash, `valid_from`/`valid_until` under the
   declared `time_binding` → else `OIC-W-0005` / `0006` / `0008` / `0021`
5. no dependency ground expired or revoked → else `OIC-W-0020` / `0007`
6. profiles match, then formula hash matches byte-for-byte → else `OIC-W-0023` / `0011`
7. source and admission versions match → else `OIC-W-0009` / `0010`
8. authority, admission, evidence, and version checks **outside** the kernel pass
9. `decision_mode` permits automatic execution → else `OIC-D-0002` / `OIC-D-0003`

Then exactly one of:

**Route A — `EARNED` / `hereditary`**

| Field | Value |
|---|---|
| `epistemic_status` | `ESTABLISHED` |
| observed grade | `hereditary` |
| `missing_ground_ids` | any — informational when present, always preserved |
| `unverified_ground_policy_applied` | `null` |
| `decision_basis` | `SUBSTANTIVE` |
| reason codes | `OIC-D-0001` |

**Route B — `ON CREDIT` / `sound`**

| Field | Value |
|---|---|
| `epistemic_status` | `CONDITIONALLY_SUPPORTED` |
| observed grade | `sound` |
| required grade | permits `sound` |
| `unverified_ground_policy_applied` | `allow_with_disclosure` |
| `missing_ground_ids` | non-empty, preserved on the record |
| `decision_basis` | `CONTROL_REQUIREMENT` |
| reason codes | `OIC-D-0005` **and** `OIC-W-0015` |
| subscription | non-null reference, coverage equal to `missing_ground_ids`, all five triggers |

Step 8 is not implemented by this contract and is not implementable by the kernel. It is
named so that no reader mistakes a warrant for a permission.

## 6. Formula hash comparison

A control stores a **bound formula hash**. A warrant carries `formula_hash`. The runtime
compares them, and the comparison rule is exact:

1. The control declares `bound_kernel_profile_id` and `bound_canonicalization_profile_id`.
2. The warrant declares `kernel_profile_id` and `canonicalization_profile_id`.
3. **If either profile differs, the hashes are NOT compared.** The warrant is `MISBOUND`
   with `OIC-W-0023` and cannot `ALLOW`.
4. Only when both profiles match are the two declared hash strings compared, by **exact
   byte equality**. No normalisation, no re-hashing, no truncation, no case folding.
5. A byte difference is `MISBOUND` with `OIC-W-0011`.

OIC never recomputes a kernel digest and never compares digests produced under different
canonicalization profiles. Two kernels can hash the same formula to different values and
mean the same thing, or to the same value and mean different things; without the profile
identifiers the comparison is meaningless in both directions.

## 7. Warrant requirement

A control declares its warrant requirement as a structured object, schema
[`warrant-requirement.schema.json`](../../schemas/proposed/warrant-requirement.schema.json):

```json
{
  "mode": "required",
  "kernel_profile_id": "ztl-v0.1",
  "minimum_warranty_grade": "sound",
  "on_insufficient_grade": "escalate",
  "unverified_ground_policy": "allow_with_disclosure"
}
```

### `unverified_ground_policy`

`forbid` | `escalate` | `allow_with_disclosure`, required and non-null when
`mode: required`.

**A minimum warranty grade alone is not sufficient authorisation to act on unverified
grounds.** The grade says how durable the result is; this field says whether the
institution accepts a result that rides an unverified link. They are different questions
and a control must answer both. A control that declares `minimum_warranty_grade: sound`
has said "a non-monotone warrant is acceptable" — it has *not* said "proceed while a ground
is still unverified".

`ON CREDIT` + `sound` may produce `ALLOW` only when **all** of these hold:

1. warrant is `USABLE`;
2. `epistemic_status = CONDITIONALLY_SUPPORTED`;
3. observed grade is `sound`;
4. the required grade permits `sound`;
5. `unverified_ground_policy = allow_with_disclosure`;
6. `missing_ground_ids` is non-empty **and preserved on the record**;
7. authority, admission, evidence, version, profile, and time checks pass;
8. `decision_mode` permits automatic execution.

The result is `execution_disposition: ALLOW` with `decision_basis: CONTROL_REQUIREMENT` and
`OIC-D-0005`. It is never `SUBSTANTIVE`: the grounds did not establish the claim outright,
the control chose to accept a conditional result.

### `ON CREDIT` + `until-verification`

Never an automatic `ALLOW` in v0.1, reason-coded `OIC-W-0025`.

**v0.1 does not model sufficient risk, reversibility, compensation, or recovery controls to
permit automatic consequential `ALLOW` on `ON CREDIT` + `until-verification`.** The verdict
rides an atom that can flip, and the contract has no way to express what happens to an
action already taken when it does. Until those controls exist, the honest answer is to
block or escalate.

Rules:

- **No implicit or default mode.** A control that does not declare one is a contract
  error, not a permissive case — and a *different* condition from an explicit
  non-requirement:

  | Situation | `warrant_state` | `warrant_requirement_mode` | Reason |
  |---|---|---|---|
  | Object missing, or fails its schema | `MALFORMED` | `null` | `OIC-W-0026` |
  | Explicit `not_required` or `not_applicable` | `NOT_REQUIRED` | the declared mode | `OIC-W-0024` |

  An explicit declaration is a decision somebody made and is recorded as such. A missing
  one is a defect. Reporting them identically would hide the defect behind a legitimate
  configuration.
- `mode: required` requires all **four** dependent fields to be non-null.
- `mode: not_required` or `not_applicable` requires all **four** to be null.
- **`not_required` is not permission to ignore authority, admission, evidence, or version
  checks.** Those are independent and are never waived by this object.
- `not_applicable` means the control contains no logical-warrant requirement at all.
- `decision_mode` and `warrant_requirement` remain **separate dimensions**. A control may
  require a `hereditary` warrant *and* reserve the decision for a human; both apply, and
  the more restrictive outcome wins.

**Known limitation.** v0.1 does not specify an `ALLOW` path for `not_required` /
`not_applicable` controls. Such a decision routes to `OIC-W-0024` and escalates. That is
deliberate rather than an oversight: specifying it would mean defining how authority,
admission, and evidence alone authorise an action, which is a larger question than this
contract. Recorded as open question 10.

## 8. `on_unknown` and `decision_mode`

`on_unknown` selects BLOCK-versus-ESCALATE on the **`UNRESOLVED` and failure paths only**.
It does not apply to `CONDITIONALLY_SUPPORTED` — conditional support is resolved by
`unverified_ground_policy` and `on_insufficient_grade` — and it does not apply to `REFUTED`
or `CONTRADICTED`, which are findings rather than unknowns. The schema enforces this: a
non-null `on_unknown_applied` requires `epistemic_status = UNRESOLVED`.

| `on_unknown` | Execution | Basis | Note |
|---|---|---|---|
| `cannot` | `BLOCK` | non-`SUBSTANTIVE` | The system states it cannot decide (`OIC-D-0004`) |
| `escalate` | `ESCALATE` | non-`SUBSTANTIVE` | Routed to a human |
| `deny` | `BLOCK` | non-`SUBSTANTIVE` | **Operational fail-closed only** |

`on_unknown: deny` is the highest-risk value in the current draft envelope schema. It reads
like a finding and is not one. A conforming implementation records
`on_unknown_applied: "deny"` together with a non-`SUBSTANTIVE` basis, so the operational
nature of the block survives into every downstream consumer. The schema enforces this: a
non-null `on_unknown_applied` cannot pair with `ALLOW` or `SUBSTANTIVE`.

`decision_mode` overrides toward caution but never toward permission:

| `decision_mode` | Effect | Basis |
|---|---|---|
| `automatic` | Preserves the stage-2 result, including **either** positive ALLOW route | `SUBSTANTIVE` (Route A) or `CONTROL_REQUIREMENT` (Route B) |
| `human_judgment`, `escalation_only`, `non_automatable` | `ESCALATE` even when `ESTABLISHED` | `CONTROL_REQUIREMENT` (`OIC-D-0002`) |
| `advisory`, `evidence_only` | `ADVISORY`; recorded, does not gate | `CONTROL_REQUIREMENT` (`OIC-D-0003`) |

## 9. Missing grounds

Two levels, per ADR-013 §2.5.

```json
"missing_ground_ids": ["ground:supplier_registered"],
"missing_ground_anchors": [
  {
    "ground_id": "ground:supplier_registered",
    "source_id": "src:proc-manual-2026",
    "source_node_id": "node:cl-4.2.1",
    "span": { "start": 120, "end": 188 },
    "admitted_unit_id": "cnu:supplier-registration",
    "expected_evidence_type": "registry_extract"
  }
]
```

### The three meanings of an unverified ground

Whenever the kernel reports unverified grounds, OIC preserves them. Under `ztl-v0.1`:

| Disposition | Meaning of its unverified list |
|---|---|
| `EARNED` | **Informational** — irrelevant to this conclusion because the result is `hereditary` |
| `REFUTED` | **Informational** — the refutation holds regardless |
| `ON CREDIT` | **Load-bearing** — the current positive result depends on them |
| `OPEN` | **Blocking** — their resolution is needed |

Measured: `EARNED` carries a non-empty list in **61 of 294** census cases, and 138
refinements over those atoms moved the verdict **0** times. One field, three roles; a
contract that collapses them will either understate an `EARNED` result or overstate an
`ON CREDIT` one.

Level 1 comes from the kernel, verbatim. Level 2 is enriched by the OIC adapter when
authorised. **The kernel is never asked to interpret source documents.** An empty
`missing_ground_anchors` means enrichment has not run — it does not mean there are no
missing grounds, and a reviewer UI must not render it as "nothing missing".

**Atom identity is the caller's responsibility.** If the same identifier is re-pointed at a
different source clause, the kernel cannot detect it and will report a verdict for a
different question under the old name.

## 10. Reason code registry

Stable and machine-readable. Adding a code is a minor version; changing a code's meaning is
a breaking change.

### Warrant and ground conditions — `OIC-W-nnnn`

| Code | Name | Basis |
|---|---|---|
| `OIC-W-0001` | `WARRANT_ABSENT` | `PROCEDURAL` |
| `OIC-W-0002` | `KERNEL_UNAVAILABLE` | `PROCEDURAL` |
| `OIC-W-0003` | `WARRANT_MALFORMED` | `PROCEDURAL` |
| `OIC-W-0004` | `WARRANT_HASH_UNVERIFIABLE` | `PROCEDURAL` |
| `OIC-W-0005` | `WARRANT_STALE` | `PROCEDURAL` |
| `OIC-W-0006` | `WARRANT_EXPIRED` | `PROCEDURAL` |
| `OIC-W-0007` | `GROUND_REVOKED` | `PRECAUTIONARY` |
| `OIC-W-0008` | `EPOCH_MISMATCH` | `PROCEDURAL` |
| `OIC-W-0009` | `SOURCE_VERSION_MISMATCH` | `PROCEDURAL` |
| `OIC-W-0010` | `ADMISSION_VERSION_MISMATCH` | `PROCEDURAL` |
| `OIC-W-0011` | `FORMULA_MISMATCH` | `PROCEDURAL` |
| `OIC-W-0012` | `DISPOSITION_OPEN` | `PRECAUTIONARY` |
| `OIC-W-0013` | `DISPOSITION_REFUTED` | `SUBSTANTIVE` |
| `OIC-W-0014` | `GROUNDS_CONTRADICTORY` | `SUBSTANTIVE` |
| `OIC-W-0015` | `UNVERIFIED_GROUNDS_PRESENT` | informational |
| `OIC-W-0016` | `WARRANTY_GRADE_INSUFFICIENT` | `CONTROL_REQUIREMENT` |
| `OIC-W-0017` | `WARRANTY_GRADE_UNSUPPORTED` | `PROCEDURAL` |
| `OIC-W-0018` | `SOURCE_ANCHORS_MISSING` | `PROCEDURAL` |
| `OIC-W-0019` | `ADMISSION_IDS_MISSING` | `PROCEDURAL` |
| `OIC-W-0020` | `GROUND_EXPIRED` | `PRECAUTIONARY` |
| `OIC-W-0021` | `WARRANT_NOT_YET_VALID` | `PROCEDURAL` |
| `OIC-W-0022` | `UNSUPPORTED_RESULT_COMBINATION` | `PROCEDURAL` |
| `OIC-W-0023` | `PROFILE_MISMATCH` | `PROCEDURAL` |
| `OIC-W-0024` | `WARRANT_REQUIREMENT_NOT_APPLICABLE` | `PROCEDURAL` |
| `OIC-W-0025` | `CONDITIONAL_SUPPORT_UNSTABLE` | `PRECAUTIONARY` |
| `OIC-W-0026` | `WARRANT_REQUIREMENT_MISSING_OR_INVALID` | `PROCEDURAL` |
| `OIC-W-0027` | `CONDITIONAL_SUPPORT_SUBSCRIPTION_MISSING_OR_INCOMPLETE` | `PROCEDURAL` |

### Decision conditions — `OIC-D-nnnn`

| Code | Name | Basis |
|---|---|---|
| `OIC-D-0001` | `ESTABLISHED_ALL_CHECKS_PASSED` | `SUBSTANTIVE` |
| `OIC-D-0002` | `DECISION_MODE_NON_AUTOMATABLE` | `CONTROL_REQUIREMENT` |
| `OIC-D-0003` | `DECISION_MODE_ADVISORY` | `CONTROL_REQUIREMENT` |
| `OIC-D-0004` | `FAIL_CLOSED_ON_UNKNOWN` | `PRECAUTIONARY` / `PROCEDURAL` |
| `OIC-D-0005` | `CONDITIONAL_SUPPORT_ACCEPTED` | `CONTROL_REQUIREMENT` |
| `OIC-D-0006` | `CONDITIONAL_SUPPORT_NOT_ACCEPTED` | `CONTROL_REQUIREMENT` |

> **`OIC-W-0013` and `OIC-W-0014` are the only substantive BLOCK reason codes.
> `OIC-D-0001` is the substantive positive-decision code.**

`OIC-W-0016`, `OIC-D-0002`, `OIC-D-0003`, `OIC-D-0005`, and `OIC-D-0006` are the
**control-policy** codes: a decision with basis `CONTROL_REQUIREMENT` must carry at least
one of them, and the schema enforces it.

## 10a. Conditional-support subscription

`ON CREDIT` + `sound` may reach `ALLOW` only when the unresolved grounds are bound to a
deterministic recomputation subscription:

| Field | Requirement for a conditional ALLOW |
|---|---|
| `conditional_support_subscription_reference` | non-null, non-empty |
| `conditional_support_subscription_ground_ids` | equal to `missing_ground_ids` |
| `conditional_support_subscription_triggers` | all five, unique, deterministic order |

Triggers: `ground_verified`, `ground_expired`, `ground_revoked`, `ground_corrected`,
`relevant_epoch_changed`. Each can falsify the result, so omitting any one leaves a path by
which the `ALLOW` silently outlives its grounds.

On every other route the reference is null. **A subscription is plumbing and is never
evidence of stronger epistemic support** — it does not upgrade `CONDITIONALLY_SUPPORTED`
toward `ESTABLISHED`, and no consumer may read it that way. Missing or incomplete is
`OIC-W-0027` and cannot `ALLOW`.

The exact VEIP subscription carrier is **deferred**. `RuntimeDecision` preserves only the
binding and the evidence the later VEIP contract will need.

## 10b. Dependency derivation

`dependency_ids` is **every verified atom** (marked `T` or `F`) appearing in the
kernel-evaluated formula. `unverified_ground_ids` is exactly the atoms marked `Z`. The two
are disjoint by construction, and together they cover the formula's atoms under the exact
evaluated marking.

**Minimality is not claimed, deliberately.** Measured: in 38 of 180 census cases with two or
more verified grounds, withdrawing a *pair* moves the disposition although neither member
does alone.

```
(p | q) & r     {p:T, q:T, r:T}   ->  EARNED / hereditary
  withdraw p alone  ->  EARNED    (q still carries the disjunction)
  withdraw q alone  ->  EARNED    (p still carries it)
  withdraw p and q  ->  OPEN / until-verification
```

A set minimised by single-ground probing omits both `p` and `q`. A revocation of both then
propagates to nothing, and a warrant claiming `ESTABLISHED` outlives the grounds that
established it. The over-approximation fails safe; minimisation fails open.

## 10c. Hash projections

**`formula_hash`** is computed over the **kernel-rendered** formula returned by
`ztljudge.judge`, under the declared canonicalization profile. It is **not** computed over
the caller's original string.

| | |
|---|---|
| Caller input | `p \| q` |
| Kernel rendering | `(p ∨ q)` |
| Hashed | `(p ∨ q)` |

Hashing the caller's string would give two callers who wrote the same formula differently
two different hashes for the same evaluated proposition.

**`output_hash`** covers the semantic output projection: kernel-rendered formula,
disposition, raw verdict, warranty grade, unverified identifiers — serialised as a JSON
object with sorted keys and no whitespace. It **excludes `why`**, which is presentational
and may change without a profile version bump, and `marking`, which is input and already
covered by `input_hash`.

## 11. Determinism

- Field ordering in serialised JSON is by sorted key.
- `reason_codes` are sorted lexicographically. Position carries no meaning: the code that
  explains the outcome is identified by the mapping's *primary reason code*, not by being
  first. Sorting is chosen over significance-ordering so two implementations agreeing on
  the set cannot disagree on the bytes.
- No timestamps beyond the explicit declared fields.
- No absolute filesystem paths, hostnames, or locale-dependent formatting.
- Digests: OIC-side artifacts use `sha256:<64 hex>`. Kernel-side `formula_hash` uses the
  kernel's own canonicalisation — for ZTL v0.1 an RFC 8785 (JCS) float-free subset digested
  with SHA-384. OIC records that value and never recomputes it.
- `replay_reference` is required and non-empty on **every** decision, including failures.
  An evaluation that blocked because no warrant existed must still be replayable, or the
  failure cannot be audited.

## 12. Unresolved questions, routed to named authorities

| # | Question | Routed to | State |
|---|---|---|---|
| 1 | Is `EARNED` + non-empty `unverified` reachable? | Vitaliy Reznik | **ANSWERED — yes.** Measured in 61 of 294 census cases. An earlier answer of "no" was wrong and is corrected here |
| 2 | Can the kernel emit `EARNED` + `until-verification`? | Vitaliy Reznik | **ANSWERED** — no; `NOT_REACHABLE` |
| 3 | Can `OPEN` carry raw verdict `T`? | Vitaliy Reznik | **ANSWERED** — no; exhaustive search found no counterexample |
| 4 | Do the two levels of missing-ground representation match reviewer needs? | Vitaliy Reznik + Arkadiy Miteiko | open |
| 5 | Do the `ON CREDIT` classification rows (28, 29) and the policy rules `WP-3`–`WP-5` match kernel behaviour? | Vitaliy Reznik | open |
| 6 | What epistemic status does `ON CREDIT` carry? | GPT-5.6 Thinking | **ANSWERED** — `CONDITIONALLY_SUPPORTED`; never `ESTABLISHED`, never collapsed to `UNRESOLVED` |
| 7 | Should `control-envelope.schema.json` carry `warrant_requirement`? | GPT-5.6 Thinking → Arkadiy Miteiko | open |
| 8 | Should the envelope gain `on_missing`, `on_conflict`, `on_error`? | GPT-5.6 Thinking | open |
| 9 | Which authority may scope expiry, and over which grounds? | Arkadiy Miteiko | **ANSWERED** — see ADR-013 §9.2 |
| 10 | What is the `ALLOW` path for `not_required` / `not_applicable` controls? | GPT-5.6 Thinking → Arkadiy Miteiko | open |
| 11 | Does the VEIP handoff need fields beyond `RuntimeDecision`? | Arkadiy Miteiko | **ANSWERED** — yes. `RuntimeDecision` alone is **not** the complete handoff: it must be bound to the pre-existing `ActionProposal`, the envelope, the warrant where applicable, the evaluation input, and the authority and admission versions. See ADR-013 §9.3 |
| 12 | Who carries the conditional-support subscription, and with what delivery guarantee? | Arkadiy Miteiko (interim VEIP owner) | **new**, open — `RuntimeDecision` preserves the binding only |
| 13 | Is the census pool adequate, given it is 22 formulas over three atoms and joint dependency was probed to pairs only? | Vitaliy Reznik | **new**, open |

## 13. Boundaries

**ZTL ends with** logical disposition, warranty grade, formula and dependency information,
verified and unverified grounds, epoch and freshness information, recomputation evidence.

**VEIP begins with** the consequential `ActionProposal`, before OIC evaluates anything. See
ADR-013 §7 for the chronology. `RuntimeDecision` is OIC's evaluation output and becomes
**evidence inside** the VEIP lifecycle; it is **not** a VEIP lifecycle record and **not**
the first VEIP artifact.

ZTL must not create a VEIP lifecycle record. VEIP must not reinterpret the ZTL formula.

## 14. Standing

Proposed under OIC-WO-002. Not admitted. No ZTL or VEIP code exists, is imported, or is
called. No policy document is parsed, no Institutional IR is constructed, no Open Control
Envelope is generated, no Rego is emitted, and OPA is not invoked.

`STATUS.md` is unchanged. `schemas/draft/` is unchanged. **No semantic implementation was
introduced. The semantic implementation gate remains BLOCKED.**
