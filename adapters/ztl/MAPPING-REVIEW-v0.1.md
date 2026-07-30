# Mapping review — v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable E; completed under the ZTL-OIC cross-review order
for PR #18.
**Status: COMPLETE** — 29 classification rows and 7 control overlays reviewed, one by one.

**Reviewed against:**

| | |
|---|---|
| PR #16 head | `9623cd43363eaa3d105f263d6c3dc8999755db9d` |
| Canonical mapping `docs/contracts/ZTL-OCE-MAPPING-v0.1.json` | sha256 `296788601b1a6d12f258da245641be64fc65434f7e7c8946e8193b2233bb3c5e` |
| Kernel profile `docs/contracts/kernel-profiles/ztl-v0.1.json` | sha256 `d8e515e76635cace04f2538f537addf0fd14de27ae4b883ae3ec57c3e5ced34a` |
| Kernel | `ztljudge.judge`; original WO-002 header cited commit `e819dec7…` — corrected: that commit predates the entrypoint (measured, WO-003); the operative pin is `veraxis-ztl-input-v0.2-signed` = `56e1ff0510c62b04dbd85bbe08b7a6deacbf276b` |
| Measurement backing this review | [`evidence/KERNEL-CENSUS-v0.1.md`](evidence/KERNEL-CENSUS-v0.1.md), 294 cases |

**Result: 26 ACCEPT, 2 ACCEPT WITH QUALIFICATION, 1 REJECT, 0 CANNOT DETERMINE.**

This mapping is a substantial piece of work and most of it is right for reasons that are hard
to get right. The precedence design — *the good news must not win* — is correct and is the
part that would have been easiest to get wrong. Two objections follow, both measured, both
with counterexamples and corrected rows.

---

## 1. Row-by-row

### Rows 1–19 — OIC-side conditions

| Rows | Verdict |
|---|---|
| 1–4 (kernel unavailable, warrant absent / malformed / hash unverifiable) | **ACCEPT** |
| 5–7 (stale, expired, not yet valid) | **ACCEPT** |
| 8–9 (ground expired, ground revoked) | **ACCEPT** |
| 10–16 (epoch, source-version, admission-version, formula, profile, anchors, admission IDs) | **ACCEPT** |
| 17–18 (grade outside the ladder; combination outside the profile) | **ACCEPT** |
| 19 (`warrant_requirement` mode `not_required` / `not_applicable`) | **ACCEPT** |

None of these is a ZTL conclusion and none is presented as one: every one carries
`authority: OIC-DEFENSIVE`. That labelling is the thing we were asked to check, and it is
correct throughout.

Three observations, none an objection:

- **Rows 5–9 outrank the disposition (precedence 2 over 4–5), and that is right in both
  directions.** A `REFUTED` warrant that is stale becomes `UNRESOLVED`, not `REFUTED`. It is
  tempting to keep a refutation across an epoch boundary on the grounds that bad news is safe.
  It is not safe: `hereditary` is invariant under monotone refinement *within one epoch and
  formula*, which is exactly what our own
  [`proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md`](proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md)
  states. A refutation evaluated against grounds that have since been withdrawn is a claim
  about a world that no longer exists. Downgrading it to `UNRESOLVED` is correct.
- **Row 19 escalates rather than allowing.** A control that requires no warrant gets
  `ESCALATE` pending specification. Conservative, deliberate, explained in the fixture, and
  fails in the safe direction. Not ours to object to.
- **Rows 15–16 (anchors and admission IDs missing) are `MISBOUND`, not a ZTL condition.**
  Correct: the kernel never sees a source or an admission, so their absence cannot be a
  logical result. Assigning them to the artifact-binding tier is the right home.

### Row 20 — contradictory grounds — **ACCEPT WITH QUALIFICATION**

The behaviour is right: `BLOCK`, `SUBSTANTIVE`, precedence 3 above the disposition tiers.

**The qualification is the `authority` label.** Row 20 is marked `MEASURED`, and
`epistemic_status_mapping` lists

```json
"contradictory grounds": "CONTRADICTED"
```

alongside the four kernel dispositions. That reads as though `CONTRADICTED` is something the
kernel emits. It is not. Measured:

```
p & ~p   {p:T}   ->  REFUTED / hereditary / F
p & ~p   {p:F}   ->  REFUTED / hereditary / F
p & ~p   {p:Z}   ->  REFUTED / hereditary / F
```

A contradictory *formula* is simply `REFUTED`. And a contradictory *ground set* — two admitted
sources asserting opposite things about the same atom — cannot even be expressed to the
kernel: a marking maps each atom to exactly one of `T`/`F`/`Z`. There is no input that makes
the kernel say "these grounds conflict".

`CONTRADICTED` is therefore a genuine and useful OIC-plane distinction — it separates "the
institution holds two incompatible admitted grounds" from "the logic refutes the claim", and
those deserve different handling. It is just not a ZTL output.

**Corrected row 20:** `authority` → `OIC-DEFENSIVE`. And in `epistemic_status_mapping`,
separate the four kernel dispositions from the OIC-side status, so no reader concludes the
kernel has five outputs:

```json
"epistemic_status_mapping": {
  "EARNED": "ESTABLISHED",
  "ON CREDIT": "CONDITIONALLY_SUPPORTED",
  "OPEN": "UNRESOLVED",
  "REFUTED": "REFUTED"
},
"oic_side_epistemic_status": {
  "contradictory grounds": "CONTRADICTED"
}
```

### Rows 21–24 — **ACCEPT**

| Row | Verdict | Measured |
|---|---|---|
| 21 `REFUTED` + `hereditary` + `unverified: any` | **ACCEPT** | `REFUTED` is always `hereditary` (63 cases), and **does** occur with a non-empty `unverified` list (25 cases). `any` is correct. |
| 22 `OPEN` + `until-verification` + non-empty, raw `F` | **ACCEPT** | 94 cases. The trap case, correctly keyed on `disposition` and not on `raw_verdict`. |
| 23 `OPEN` + `until-verification` + non-empty, raw `Z` | **ACCEPT** | 1 case (`p`, `{p:Z}`). |
| 24 `OPEN` + raw `T`, `NOT_REACHABLE` | **ACCEPT** | Confirmed: no `OPEN` result carries raw `T` in 294 cases, and none in the exhaustive search behind `CONFORMANCE-v0.1.md §8.1`. Retaining it as a defensive fail-closed row is the right call. |

Row 21 deserves a note, because it is the row that exposes the objection below: **`REFUTED` was
given `unverified: any` and it is correct.** The same reasoning applies unchanged to `EARNED`.

### Row 25 — `EARNED` + `hereditary` + `unverified: empty` — **REJECT**

This is the one substantive objection.

**The claim.** Row 25 requires `unverified = empty`. The kernel profile says the same
(`disposition_values` → `EARNED` → `"unverified": "empty"`), the schema's `disposition`
description says the same ("EARNED = grounded outright, always grade hereditary, unverified
empty"), and `test_warrant_contract.py:1477` asserts it.

**The counterexample.**

```
judge("p | q", {p: "T", q: "Z"})

  disposition : EARNED
  grade       : hereditary
  verdict     : T
  unverified  : ['q']
  why         : "grounded; the unverified ['q'] do not matter"
```

`q` was never verified. The conclusion does not need it — `p` grounds the disjunction outright.
The kernel's own explanation says so in as many words.

**How often.** 61 of 294 measured cases — 21% of the space, and the second-largest cell in the
census. It is not an edge case: it is the ordinary shape of a control satisfiable by any one of
several alternative grounds, where the alternatives were never checked because they did not
need to be.

**That the result is genuinely established, measured:** over those 61 cases, every unverified
atom was refined to `T` and to `F` in every combination — **138 refinements, 0 moved the
verdict.** That is what `hereditary` asserts, and it holds.

**What breaks today.** `unverified` is part of every row's match key. An `EARNED` result with a
non-empty list matches no disposition row: row 25 demands `empty`, rows 28–29 demand a grade
`EARNED` never has. It falls to row 18 — *combination not in the profile* — at precedence 2,
which outranks the disposition tiers anyway. Outcome: `UNSUPPORTED_GRADE` → `UNRESOLVED` →
`BLOCK / ESCALATE`.

So a fully grounded, hereditarily warranted claim is refused as an unsupported result.

**Why it matters even though it fails closed.** It is the mirror of invariant I-04. I-04
forbids turning unknown into grounded false; this turns **established into unknown**. The
metric "unknown-to-false conversion = 0" would read clean while the envelope quietly refuses
the strongest results the kernel can produce. And it fails *silently* in the sense that
matters: the reason code says the combination is unsupported, which points an operator at the
kernel rather than at the mapping.

**Root cause, stated plainly so it does not recur.** `unverified_ground_ids` carries two
different meanings depending on the disposition — informational under `EARNED` and `REFUTED`,
load-bearing under `ON CREDIT`, blocking under `OPEN`. The `empty` constraint on row 25 reads
the field with the `ON CREDIT` meaning. Row 21 already reads it correctly for `REFUTED`; the
inconsistency between rows 21 and 25 is itself the evidence that this was a slip rather than a
position.

**We should say where this came from.** The ZTL side answered a question about this row in the
previous round and the answer was recorded as the opposite of what was meant. Our answer was
not written down as a fixture at the time, which is precisely why it could be inverted without
anyone noticing. That is our process failure, and the census script now in
`adapters/ztl/evidence/` exists so this class of question is settled by a re-runnable command
instead of by correspondence.

**Corrected row 25:**

| field | from | to |
|---|---|---|
| `unverified` | `"empty"` | **`"any"`** |

Nothing else in the row changes: `EARNED` + `hereditary` remains `USABLE` / `ESTABLISHED` /
`ALLOW` / `SUBSTANTIVE` / `OIC-D-0001`. Every W-4 check outside the kernel still applies —
`ALLOW` here means the logic does not stand in the way, which is exactly how the mapping
already words it.

**Five places carry the same correction:**

1. `docs/contracts/ZTL-OCE-MAPPING-v0.1.json` — row 25, `"unverified": "any"`;
2. `docs/contracts/kernel-profiles/ztl-v0.1.json` — `disposition_values` → `EARNED` →
   `"unverified": "any"`;
3. `schemas/proposed/warrant-artifact.schema.json` — the `disposition` description, drop
   "unverified empty" and say instead: *unverified atoms may be present and are irrelevant to
   the conclusion*;
4. `tests/contract/test_warrant_contract.py:1477` — `assert earned["unverified"] == "any"`;
5. `ZTL-OCE-MAPPING-v0.1.md` — re-render via `tools/render_mapping.py`.

**And one fixture is missing from the contract suite.** Fixture `01-earned-hereditary-current`
has `missing_ground_ids: []`, so it cannot catch this. A sibling is needed —
`EARNED` / `hereditary` / non-empty `missing_ground_ids` / `ALLOW`, from
`judge("p | q", {p:T, q:Z})` — asserting that the disclosure list survives onto an `ALLOW`
decision. That is the case the schema already promises to surface ("always surfaced as
`missing_ground_ids` … including when the outcome is ALLOW") and that no current fixture
exercises.

**On the pinned fixture set.** We did not add this case to
`fixtures/interface-freeze-v0.1/`. Its `index_sha256` is pinned inside `ztl-v0.1.json` in the
PR under review, and changing it underneath you would invalidate your own pin. The evidence
sits in `adapters/ztl/evidence/` instead. Promoting it to a pinned fixture means a fixture-set
version bump and a re-pin — your call, and we will produce it on request.

### Rows 26–29 — **ACCEPT**

| Row | Verdict | Measured |
|---|---|---|
| 26 `ON CREDIT` + `sound` → `CONDITIONALLY_SUPPORTED`, `ALLOW`/`BLOCK`/`ESCALATE`, `CONTROL_REQUIREMENT` | **ACCEPT** | Reachable but rare: 1 case in the 294-case census, plus the pinned fixture `on-credit-sound` (`(~p) -> (q -> q)`, `{p:Z, q:Z}`), reproduced live. Rarity is not a reason to drop the row — it is the row that carries the only conditional `ALLOW`. |
| 27 `ON CREDIT` + `until-verification` → `BLOCK`/`ESCALATE`, `PRECAUTIONARY`, no `ALLOW` | **ACCEPT** | 6 cases. Correct — see §2.2. |
| 28 `EARNED` + `sound`, `NOT_REACHABLE` | **ACCEPT** | Confirmed. `EARNED` is `hereditary` by construction; a non-hereditary `T` is `ON CREDIT`. |
| 29 `EARNED` + `until-verification`, `NOT_REACHABLE` | **ACCEPT** | Confirmed. Reason-coding it `OIC-W-0022` rather than `OIC-W-0012` is right: its disposition is not `OPEN`, and labelling it `DISPOSITION_OPEN` would be false. |

---

## 2. The four questions put to the ZTL side

### 2.1 May `ON CREDIT` + `sound` support action where the institution explicitly accepts unverified conditional support?

**Yes — with one thing named precisely, because the word "conditional" hides it.**

`sound` means the verdict **never lies about the present marking**. At the moment of
evaluation the claim is true. What `sound` does *not* buy is survival: under refinement the
result may stall — cease to be established — without ever having been false.

So the institution accepting `ON CREDIT` + `sound` is not accepting a risk of *falsity*. It is
accepting a risk of *expiry*: that the basis stops supporting the action later. That is a
coherent thing for an institution to accept, and it is why the row is right to exist.

**Two conditions must ride with the acceptance**, and O-5 already carries the first:

1. **The unverified grounds are disclosed on the record** — O-5's note requires exactly this.
2. **The unverified grounds are subscribed for revocation and refinement.** An `ALLOW` on
   `sound` is a promise to recompute when those atoms resolve. Without that, "conditional
   support" degrades into unconditional support that nobody ever revisits — which is the
   failure ZTL exists to expose, arriving through the front door with paperwork.

Condition 2 is not currently stated anywhere we can find. Recommend adding it to O-5's note or
to WARRANT-CONTRACT §7.

### 2.2 Should `ON CREDIT` + `until-verification` remain non-automatic in OIC v0.1?

**Yes. Confirmed, and it is the right conservatism.**

`until-verification` holds **only in the present marking** — not at all endings, not under
refinement. It is the weakest rung: the result is true as things stand and carries no promise
whatever about what happens when the unverified atom resolves. Row 27's `PRECAUTIONARY` basis
and the absence of `ALLOW` from its base choices are both correct.

Row 27 also correctly refuses the tempting symmetry with row 26. The gap between `sound` and
`until-verification` is not one of degree — `sound` is a statement about every ending, and
`until-verification` is a statement about one moment.

### 2.3 Are missing unverified atoms always preserved?

**They must be, and the schema already requires it** — `unverified_ground_ids` is "always
surfaced as `missing_ground_ids` on the runtime decision, including when the outcome is ALLOW".
That is right and should not be weakened.

Two qualifications:

1. **Preservation must survive the row-25 correction.** With `unverified: empty` on row 25, the
   "including when the outcome is ALLOW" clause was very nearly vacuous: the only unconditional
   `ALLOW` row could not carry a non-empty list at all. Correcting row 25 gives that clause the
   61-case cell it was written for, and the missing fixture named in §1 is what would hold it.
2. **Preserved with the right meaning.** Under `EARNED` these are grounds that were *not
   needed*; under `ON CREDIT` they are grounds that are *owed*. Presenting both as "missing"
   invites an operator to escalate an established result or relax a conditional one. The
   discriminator already exists — `epistemic_status` — and one sentence in WARRANT-CONTRACT §5
   would fix it without a schema change. Detail in
   [`WARRANT-FIELD-RESPONSE-v0.1.md §3`](WARRANT-FIELD-RESPONSE-v0.1.md).

### 2.4 Does `CONTROL_REQUIREMENT` correctly represent an OIC policy decision rather than a ZTL conclusion?

**Yes. Confirmed, and the vocabulary is used consistently across the whole table.**

Checked every row and overlay for where each basis appears:

| Basis | Where it appears | Correct? |
|---|---|---|
| `SUBSTANTIVE` | rows 20, 21, 25 — outcome derived from the grounds | yes |
| `PRECAUTIONARY` | rows 8, 9, 22, 23, 27 — outcome from absence of ground, not from ground | yes |
| `PROCEDURAL` | rows 1–7, 10–19, 24, 28, 29 — outcome from the artifact or the process | yes |
| `CONTROL_REQUIREMENT` | row 26 and every overlay O-1…O-7 — outcome chosen by policy | yes |

`CONTROL_REQUIREMENT` appears in exactly one classification row — 26 — and that is the one row
whose execution genuinely is not determined by the logic: `ON CREDIT` + `sound` can go to
`ALLOW`, `BLOCK` or `ESCALATE` depending on `unverified_ground_policy`. Marking it
`CONTROL_REQUIREMENT` says openly that the institution, not ZTL, decides. That is exactly
right, and it is the distinction we would have asked for had it been absent.

---

## 3. The four disposition mappings

Confirmed, all four:

| ZTL disposition | OIC epistemic status | Verdict |
|---|---|---|
| `EARNED` | `ESTABLISHED` | **CONFIRM** — subject to the row-25 correction; the mapping itself is right |
| `ON CREDIT` | `CONDITIONALLY_SUPPORTED` | **CONFIRM** — and the new status was the right response to our correction. Neither `ESTABLISHED` (would authorise action on an unverified link) nor `UNRESOLVED` (would over-block a `T` that never lies) could have carried it. |
| `OPEN` | `UNRESOLVED` | **CONFIRM** — and it must remain independent of `raw_verdict`, which rows 22 and 23 get right |
| `REFUTED` | `REFUTED` | **CONFIRM** |

---

## 4. Control overlays

Reviewed only for the question asked: **do they preserve ZTL's result, or do they claim ZTL
owns the policy?**

| Overlay | Verdict |
|---|---|
| O-1 `human_judgment` / `escalation_only` / `non_automatable` → `ESCALATE` | **ACCEPT** — `PRESERVE`; the note that `REFUTED` + human judgment stays `REFUTED` is the exact right example to have chosen |
| O-2 `advisory` / `evidence_only` → `ADVISORY` | **ACCEPT** — `PRESERVE` |
| O-3 grade below minimum, `on_insufficient_grade = escalate` | **ACCEPT** — `PRESERVE`; the note "the grounds did support the claim; the control declined to act on that grade" draws the line in the right place |
| O-4 same, `= block` | **ACCEPT** — `PRESERVE` |
| O-5 `CONDITIONALLY_SUPPORTED` + sufficient grade + `allow_with_disclosure` → `ALLOW` | **ACCEPT WITH QUALIFICATION** — see §2.1: add the revocation-subscription condition |
| O-6 `CONDITIONALLY_SUPPORTED` + `forbid` → `BLOCK` | **ACCEPT** — `PRESERVE` |
| O-7 `CONDITIONALLY_SUPPORTED` + `escalate` → `ESCALATE` | **ACCEPT** — `PRESERVE` |

**The separation itself is the right architecture, and we want to say so specifically.** Every
overlay declares `epistemic_effect = PRESERVE`, and the `composition` block explains why: a
flat table let a `decision_mode` row assert an epistemic status of its own, so "a human decides
this" could silently claim the grounds were established. Splitting classification from overlay
makes that unsayable rather than merely discouraged. Structurally enforced, not documented —
which is the difference between a rule and a hope.

No overlay claims ZTL owns a policy. `decision_basis: CONTROL_REQUIREMENT` on all seven says
the opposite, in the schema.

---

## 5. Warranty ladder — no objection

Checked, because O-3 and O-4 depend on "below minimum" being well defined. The profile's
ranking (`hereditary` 2, `sound` 1, `until-verification` 0) and its stated implication
`hereditary ⟹ sound` match the kernel's own definitions in `zverify.py`, which computes
`hereditary` first, `sound` second and `until-verification` as the fallback, and which records
`hereditary ⟹ sound` as measured and `sound ⇏ hereditary` as separated. The ordering is a
genuine total order of strength, so `minimum_warranty_grade` is meaningful.

---

## 6. What this review is not

It is a review of the mapping against the kernel. It is **not** an architecture acceptance, not
an approval of ADR-013, not an approval of PR #16, and not a statement that the mapping is
implementable — we have no view on the OIC-side halves of rows 1–19 beyond confirming they
claim nothing about ZTL.

The census in `adapters/ztl/evidence/` is author-side evidence, Tier 3, run by us against our
own kernel. The script is offered so that the run can be repeated by someone who is not us,
which is the only thing that would raise its tier.

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the
OIC semantic implementation gate remains BLOCKED.*

---

# WO-003 Phase 2 — final cross-review of the accepted PR #16 head

**Reviewed head:** `d9eba5fd89d2745341f0b4007672ef9124be073f` (exactly; nothing later).
**Mapping reviewed:** `docs/contracts/ZTL-OCE-MAPPING-v0.1.json`,
SHA-256 `795818df958fa73aa4bf1edf1fa2951fb77d996e81b55110f57fc556d5ad29bf` (verified byte-level).
**Kernel profile reviewed:** `docs/contracts/kernel-profiles/ztl-v0.1.json`,
SHA-256 `66438af3b742d4bd5f5a676d27d016f51a221f58c1b3c5d6ea1866e4d7744288` (verified byte-level).
**Semantic-conformance rule set reviewed:** SC-RD-001…005, SC-WA-001, SC-WA-002 (the seven
rules embedded in the mapping JSON and executable via `tests/contract/semantic_conformance.py`).
**Kernel measured against:** `ztljudge.judge` at `56e1ff0` (`veraxis-ztl-input-v0.2-signed`);
census re-run for this review: EARNED non-empty 61/294 (138 refinements, 0 moved),
REFUTED non-empty 25/294, pair-withdrawal 38/180 — all three match the profile's claims.

## Verdict totals

| Artifact | ACCEPT | ACCEPT WITH QUALIFICATION | REJECT | CANNOT DETERMINE |
|---|---|---|---|---|
| 32 classification rows | 30 | 2 (rows 9, 10) | 0 | 0 |
| 5 warrant-policy rules | 4 | 0 | **1 (WP-3)** | 0 |
| 3 decision-mode overlays | 3 | 0 | 0 | 0 |
| 7 semantic-conformance rules | 6 | 1 (SC-WA-001) | 0 | 0 |
| kernel profile (out of the ordered lists, reviewed by its SHA) | — | — | **1 (commit + provenance fields)** | — |

## The one mapping objection — WP-3 (REJECT)

- **Rule:** `warrant_policy_rules`, `rule_id: WP-3` — the only ALLOW route for conditional
  support. Its machine trigger reads `grade sufficient`; its own `note` and the contract
  (§7 condition 3, and the §4 table row "ON CREDIT + until-verification → BLOCK / ESCALATE,
  PRECAUTIONARY, OIC-W-0025") require **observed grade = sound**.
- **Counterexample (measured-reachable input):** fixture `on-credit-until-verification`
  (`(b -> a) -> (b = c)`, `{a:F, b:Z, c:T}` → `ON CREDIT / until-verification / T`), against
  an envelope `{mode: required, minimum_warranty_grade: "until-verification",
  unverified_ground_policy: "allow_with_disclosure"}` — legal per
  `warrant-requirement.schema.json`, whose `minimum_warranty_grade` enum includes
  `"until-verification"`. The observed grade meets the declared minimum, so the trigger's
  `grade sufficient` conjunct is satisfied and WP-3 yields **ALLOW** for a T that can die on
  the next resolving tick. No SC rule catches it: SC-RD-001/002 check subscription coverage
  and triggers, not the grade.
- **Expected behavior (per the contract's own text):** that input never reaches ALLOW —
  PRECAUTIONARY BLOCK/ESCALATE with `OIC-W-0025`.
- **Proposed correction (either closes it; both is belt-and-braces):**
  1. WP-3 trigger: `epistemic_status = CONDITIONALLY_SUPPORTED, observed grade = sound,
     grade sufficient, unverified_ground_policy = allow_with_disclosure`; and/or
  2. remove `"until-verification"` from the `minimum_warranty_grade` enum (a control that
     "accepts until-verification" accepts an unfalsified guess — no institutional meaning we
     can see), or add an explicit WP-6: `ON CREDIT + until-verification → BLOCK/ESCALATE,
     PRECAUTIONARY, OIC-W-0025`, so the prose row has a machine twin.

## The kernel-profile objection (REJECT on two fields)

`commit: e819dec7…` with provenance "reproduced against the pinned commit by its author".
**Measured:** `ztljudge.judge` does not exist at `e819dec7` — `judge()` first appears in
`25510dd` and is renamed in `c858429`, both later; `verify_fixtures.py` against a clean
`e819dec7` worktree exits 2 (`No module named 'ztljudge'`). The v0.1 fixtures are genuine
live-run records, but no judge-based fixture is recomputable at that pin, so the provenance
line cannot be true as written. **Proposed correction:** pin
`veraxis-ztl-input-v0.2-signed` = `56e1ff0510c62b04dbd85bbe08b7a6deacbf276b` (entrypoint
exists; measured PASS 13/3/0/0) and point `conformance_fixture_set` at
`interface-freeze-v0.2/` (index SHA-256
`ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145`). Same hole, same fix,
in `CONFORMANCE-v0.1.md` §1–2 (v0.1 is preserved unchanged; the correction lives in v0.2).

## Qualifications (ACCEPT WITH QUALIFICATION)

- **Rows 9, 10:** both map a ground event to `warrant_state: REVOKED`; expiry and revocation
  stay distinguishable only through the reason codes (`OIC-W-0020` vs `OIC-W-0007`). Our
  epoch model treats them as different events (expire = the world changed; revoke =
  authoritative composite), and the trigger vocabulary keeps them apart — suggest either a
  `GROUND_EXPIRED` state or a one-line note that the state label deliberately compresses
  what the codes preserve.
- **SC-WA-001:** the rule's wording ("the evaluated formula's atom set") is exactly right —
  two measured edges for adapter authors: an atom present in the caller's marking but absent
  from the formula appears in **neither** array (`p`, `{p:T, x:Z}` → both arrays exclude
  `x`); an atom in the formula but absent from the marking **defaults to Z** and appears in
  `unverified_ground_ids` (`p | q`, `{p:T}` → `unverified ['q']`, disposition still EARNED).

## The seventeen ordered confirmations

1. EARNED → ESTABLISHED incl. informational unverified — **CONFIRM** (row 27 `unverified:
   any`; 61/294; the v0.2 witness fixture `earned-hereditary-nonempty-unverified.json`).
2. REFUTED → REFUTED incl. informational unverified — **CONFIRM** (row 23; 25/294).
3. ON CREDIT → CONDITIONALLY_SUPPORTED — **CONFIRM** (rows 28/29; the disposition our
   dossier omitted, correctly restored by the profile).
4. OPEN → UNRESOLVED — **CONFIRM** (rows 24/25; OPEN+T NOT_REACHABLE, row 26, matches our
   exhaustive search).
5. CONTRADICTED is OIC-plane — **CONFIRM**; measured: kernel `DISPOSITIONS = (EARNED,
   ON CREDIT, OPEN, REFUTED)`; a contradictory formula is REFUTED, conflicting admitted
   values are unrepresentable in a marking.
6. dependency_ids = every T/F atom, no minimality — **CONFIRM** (the 38/180 pair-withdrawal
   measurement is ours and the profile quotes it correctly).
7. unverified_ground_ids = every Z atom — **CONFIRM with the SC-WA-001 precision**: every Z
   atom *of the evaluated formula*, including unmarked atoms defaulting to Z.
8. Disjoint, unique, covering — **CONFIRM** for the formula's atom set (the exact SC-WA-001
   wording; "the evaluated marking" in the order should be read the same way).
9. Conditional ALLOW quadruple requirement — **CONFIRM as intended, REJECT as encoded** —
   see the WP-3 objection; the sound-grade conjunct is in the prose and missing from the
   machine trigger.
10. Five-trigger completeness — **CONFIRM** for the present anti-tick model: verify tick =
    `ground_verified`, anti-tick = `ground_expired`, the authoritative composite =
    `ground_revoked` + `ground_corrected`, epoch boundary = `relevant_epoch_changed`.
    A formula change is a different warrant, not a trigger — correctly excluded.
11. formula_hash = SHA-384 over UTF-8 kernel-rendered formula — **CONFIRM** (recomputed
    independently for the v0.2 fixture: `sha384:b77102bb…`).
12. output_hash = SHA-256 over the five-field projection, sorted keys, compact, no ASCII
    escaping — **CONFIRM** (recomputed independently: `sha256:20657bd3…`).
13. `why` and `marking` excluded from output_hash — **CONFIRM**; `why` is presentational
    (its text varies with the unverified list), `marking` is input and covered by the input
    hash and the two ground arrays.
14. Classification codes survive overlays — **CONFIRM** (SC-RD-004 completeness + DM-2/DM-3
    "codes retained").
15. Applied overlay IDs complete, exact, ordered — **CONFIRM** (SC-RD-003 + SC-RD-005;
    DM-1 never recorded).
16. zverify prohibited — **CONFIRM**; ZTL-H-001 wording is accurate to our measured trap
    (the 'M'-dialect: `Z` passed by mistake yields `hereditary` for everything, silently).
17. No ZTL output as authority / admission / time authority / execution / reliance /
    correction — **CONFIRM** (§ W-4 step 8 outside the kernel; time under the envelope's
    `time_binding`; "ZTL must not create a VEIP lifecycle record"; "no reader mistakes a
    warrant for a permission").

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and
the OIC semantic implementation gate remains BLOCKED.*

---

# WO-004C Track C — final exact-head cross-review of Revision 4B

**Reviewed head:** `cdca530ce11374bb9a37423ba076afc133dc1b70` (verified unmoved at review time; PR #16 DRAFT, unmerged).
**Mapping SHA-256, independently recomputed:** `84b336191457707c19f11a08288e7b0570de21dd8b66d9a04456c507c0d96078` — **matches the supplied value.**
**Kernel-profile SHA-256, independently recomputed:** `3fdd19970fcacaa53bdfb22b016b75865dd3b71e8c5f82d88a698b77818e07ce` — **matches the supplied value.**
**Fixture-set index SHA-256:** `ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145` (unchanged; verified on disk at PR #18 head).

## Verdict totals

| Artifact | ACCEPT | QUALIFY | REJECT | CANNOT DETERMINE |
|---|---|---|---|---|
| 32 classification rows | **32** | 0 | 0 | 0 |
| 5 warrant-policy rules | **5** | 0 | 0 | 0 |
| 8 semantic-conformance rules | **8** | 0 | 0 | 0 |
| Kernel profile | — | **1 (two minor items, below)** | 0 | 0 |
| 28 warrant-artifact fields (re-review, §F) | **28** (5 NATIVE, 7 DERIVABLE, 16 OIC-ENRICHED; 0 UNSUPPORTED, 0 REQUIRES ZTL CHANGE) | — | — | — |

## B. Profile and provenance — confirmed, with two minor qualifications

Confirmed exactly: repository `https://github.com/inventor1975/ZTL`; signed tag `veraxis-ztl-input-v0.2-signed` (with an honest limitations note on the key); commit `56e1ff0510c62b04dbd85bbe08b7a6deacbf276b`; entrypoint `ztljudge.judge`; fixture set `interface-freeze-v0.2/`; index SHA `ffadd653…`; counts 13/3/16; `profile_id: ztl-v0.1` retained for a proposed, unadmitted profile; every remaining `e819dec7` mention is historical/corrective ("superseded", "predates ztljudge.judge") — **no active claim states the entrypoint existed at `e819dec7`**; interface-freeze-v0.1 remains byte-preserved (INDEX sha `b6e007bd…` verified on disk); PR #16 body states "PR #16 must not merge before PR #18."

**Qualification B-1 (minor).** The profile's census note reads "Run against the superseded commit `e819dec7…`". The census artifact (`KERNEL-CENSUS-v0.1.json`) declares **no kernel commit at all**, and the claim is impossible as stated: `kernel_census.py` imports `ztljudge`, which does not exist at `e819dec7` (measured — exit 2). The truthful statement: the census was run against the author's working tree (kernel content identical to the v0.2 pin), and was **re-run against the v0.2 pin on 2026-07-30 with identical numbers** (61/294 EARNED non-empty; 138 refinements, 0 moved; 25/294 REFUTED non-empty; 38/180 pair-withdrawal). Required correction: replace "Run against the superseded commit e819dec7…" with "Re-verified against the v0.2 pin `56e1ff0…`; originally run against the author's working tree, whose census-relevant kernel content is identical." Severity: minor (provenance wording; the numbers themselves are confirmed).

**Qualification B-2 (minor).** The order asks to confirm "version remains 0.1.0"; the profile has **no `version` key** (only `profile_id: ztl-v0.1`). Either add `"version": "0.1.0"` or treat `profile_id` as the sole version carrier. Severity: editorial.

## C/D/E. The two prior objections are closed, and verified closed

- **WP-3 (prior REJECT → ACCEPT).** The trigger now carries every ordered conjunct verbatim: matched row = 28, `epistemic_status = CONDITIONALLY_SUPPORTED`, `warranty_grade_observed = sound`, grade sufficient, `unverified_ground_policy = allow_with_disclosure`. Row 29 (`ON CREDIT`/`until-verification`) is PRECAUTIONARY, `OIC-W-0025`, `stage_2_applies = false`, execution BLOCK/ESCALATE only — it cannot reach WP-3, so a declared minimum of `until-verification` no longer authorizes a conditional ALLOW on an observed `until-verification` grade. WP-1/2 (order 1) precede the unverified-ground policy (order 2); WP-4/5 scopes unchanged.
- **SC-RD-006 (new) — ACCEPT.** Requires observed sound + row 28 + WP-3 in `applied_control_overlay_ids` + `OIC-D-0005` and `OIC-W-0015` retained + SC-RD-001/002 independently passing + absence of `OIC-W-0025` on any decision reaching ALLOW. The runtime-decision schema adds the structural proxy (`applied_control_overlay_ids` contains `WP-3`; grade const `sound`) with an honest comment that row-binding itself is beyond JSON Schema.
- **SC-WA-001 — ACCEPT.** Now states, verbatim to our measured edges: partition over the evaluated formula's atom set, not the caller's marking; marking-only atoms in neither array; unmarked formula atoms default to Z and land in `unverified_ground_ids`; uniqueness, disjointness, union equality; no minimality claim.
- **SC-WA-002 — ACCEPT.** Both projections match the kernel and our independent recomputation (`sha384:` over the kernel-rendered formula; `sha256:` over the five-field projection, sorted keys, compact separators, no ASCII escaping; `why` and `marking` excluded).
- **Rows 9/10 (prior qualification → ACCEPT).** The notes now state the coarse-state design explicitly: `REVOKED` is the coarse unusability state; `OIC-W-0020` (expiry) vs `OIC-W-0007` (revocation) plus the trigger vocabulary remain authoritative for the distinction.
- **Rows 30/31 — ACCEPT.** `EARNED`+`sound` and `EARNED`+`until-verification` remain NOT_REACHABLE; supported by the v0.2 NOT_REACHABLE fixtures (exhaustive-search reasons recorded).
- **Authority labels.** Every MEASURED row maps to a reachable v0.2 fixture; every ZTL-CONFIRMED row maps to a NOT_REACHABLE fixture or the measured disposition vocabulary (`DISPOSITIONS = (EARNED, ON CREDIT, OPEN, REFUTED)` — no CONTRADICTED). Confirmed.

## F. Warrant-field feasibility, re-reviewed against the corrected pin

All 28 classifications of Deliverable D stand under the v0.2 pin (the kernel bytes at `56e1ff0` are the same kernel the fields were measured against; the pin correction changes provenance, not behavior). Specifically re-confirmed: `formula_hash` DERIVABLE (recomputed today, SC-WA-002 definition); `dependency_ids` DERIVABLE with the over-approximation constraint (38/180 measured); `ground_set_hash` DERIVABLE (digest over the echoed marking); `input_hash` DERIVABLE; `output_hash` DERIVABLE (recomputed); `recomputation_reference` DERIVABLE — and now actually executable, since the v0.2 pin contains the entrypoint (the v0.1 pin did not); `ground_epoch`, `source_anchor_ids`, `admission_ids`, `generated_at`, `time_binding`, `valid_from`, `valid_until`, `revocation_references` OIC-ENRICHED (the kernel originates no epoch, clock, source, admission, or institutional time — consistent with the corrected PR #14 boundary memo). Nothing UNSUPPORTED; nothing REQUIRES ZTL CHANGE.

## G. Subscription and trigger completeness — CONFIRMED from the ZTL boundary

A conditional ALLOW rides exactly its `missing_ground_ids`. From the kernel boundary, the ground state of a subscribed atom can change only by: verification (`ground_verified`, the tick), expiry (`ground_expired`, the anti-tick), authoritative correction (`ground_corrected` — the expire+verify composite), authoritative revocation (`ground_revoked`), or a change of the epoch scope the grounds live in (`relevant_epoch_changed`). These are the only state transitions the logical-time model (E24/E25) admits; a formula change is a different warrant, not a trigger, and stipulation events concern the solver's self-referential systems, which the warrant path does not evaluate. We searched for a transition by which a conditional ALLOW could outlive its support without firing one of the five triggers and found none. The canonical set and its fixed order are **complete for the present anti-tick model**.

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the OIC semantic implementation gate remains BLOCKED.*
