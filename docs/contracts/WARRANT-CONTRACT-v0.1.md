# Warrant and failure-semantics contract, v0.1

**Status: PROPOSED. Not admitted, not implemented, not called.**

Governing decision: [ADR-013](../../adr/ADR-013.md).
Mapping table: [ZTL-OCE-MAPPING-v0.1.md](ZTL-OCE-MAPPING-v0.1.md).
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
| Is the warrant current and usable? | `warrant_state` | OIC, from epoch, hashes, expiry, revocation |
| What did the runtime do? | `execution_disposition` | OIC envelope policy |
| Why did it do that? | `decision_basis` | OIC, derived from the first three |

Four questions, four fields. `schemas/draft/runtime-evaluation.schema.json` answers all
four with one `verdict` enum, which is the defect this contract corrects.

## 2. Failure semantics

**Default posture is fail-closed.** A missing kernel, a missing ground, an unusable
artifact, or an unsupported input never yields a permissive result. This matches the ZTL
side's own posture: a missing kernel blocks warrant-dependent publication rather than
fabricating a warrant.

**Fail-closed is not a finding.** Every entry below that blocks does so with
`decision_basis` of `PRECAUTIONARY` or `PROCEDURAL`. Only two rows are `SUBSTANTIVE`, and
those are the only two that say anything about the world.

| # | Condition | `warrant_state` | Epistemic | Execution | Basis | Reason |
|---|---|---|---|---|---|---|
| 1 | Warrant absent | `ABSENT` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0001` |
| 2 | Kernel unavailable | `ABSENT` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0002` |
| 3 | Malformed warrant | `MALFORMED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0003` |
| 4 | Unverifiable warrant hash | `UNVERIFIABLE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0004` |
| 5 | Stale warrant | `STALE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0005` |
| 6 | Expired warrant | `EXPIRED` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0006` |
| 7 | Warrant not yet valid | `NOT_YET_VALID` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0021` |
| 8 | Revoked ground | `REVOKED` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0007` |
| 9 | Expired ground | `REVOKED` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0020` |
| 10 | Epoch mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0008` |
| 11 | Source-version mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0009` |
| 12 | Admission-version mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0010` |
| 13 | Formula mismatch | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0011` |
| 14 | Missing source anchors | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0018` |
| 15 | Missing admission IDs | `MISBOUND` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0019` |
| 16 | Unsupported warranty grade | `UNSUPPORTED_GRADE` | `UNRESOLVED` | BLOCK / ESCALATE | `PROCEDURAL` | `OIC-W-0017` |
| 17 | `OPEN` disposition, any raw verdict | `USABLE` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0012` |
| 18 | `REFUTED` disposition | `USABLE` | `REFUTED` | BLOCK | `SUBSTANTIVE` | `OIC-W-0013` |
| 19 | Contradictory grounds | `USABLE` | `CONTRADICTED` | BLOCK | `SUBSTANTIVE` | `OIC-W-0014` |
| 20 | `EARNED` + `hereditary` | `USABLE` | `ESTABLISHED` | ALLOW¹ | `SUBSTANTIVE` | `OIC-D-0001` |
| 21 | `EARNED` + `sound`, grade permitted | `USABLE` | `ESTABLISHED` | ALLOW¹ | `SUBSTANTIVE` | `OIC-D-0001` |
| 22 | `EARNED` + `sound`, grade insufficient | `USABLE` | `ESTABLISHED` | ESCALATE | `PROCEDURAL` | `OIC-W-0016` |
| 23 | `EARNED` + `until-verification` | `USABLE` | `UNRESOLVED` | BLOCK / ESCALATE | `PRECAUTIONARY` | `OIC-W-0012` |
| 24 | Non-empty `unverified` list | unchanged | unchanged | unchanged | unchanged | `OIC-W-0015` added |

¹ `ALLOW` additionally requires **W-4** conditions 4–8 (authority, admission, evidence,
versions). Rows 20–21 mean *the logic does not stand in the way*.

Row 24 is deliberately not a failure. A non-empty `unverified` list is **recorded on every
outcome including `ALLOW`**, and never suppresses or downgrades an otherwise sound result
on its own. What it must never do is disappear.

## 3. The three dimensions

Defined in [ADR-013 §2.2](../../adr/ADR-013.md#22-the-three-dimensions). In brief:

- `epistemic_status` ∈ `ESTABLISHED` | `REFUTED` | `UNRESOLVED` | `CONTRADICTED`
- `execution_disposition` ∈ `ALLOW` | `BLOCK` | `ESCALATE` | `ADVISORY`
- `decision_basis` ∈ `SUBSTANTIVE` | `PRECAUTIONARY` | `PROCEDURAL`

The distinction that carries the most weight in practice:

> A `BLOCK` with `PRECAUTIONARY` basis says **"we do not know, so we stopped."**
> A `BLOCK` with `SUBSTANTIVE` basis says **"the grounds establish that this is not permitted."**
>
> These must never be recorded identically. The first is reversible by verifying a ground;
> the second is a finding about the institution's rules.

## 4. The ALLOW gate

`execution_disposition = ALLOW` requires **all eight** of ADR-013 W-4. Restated as a
checklist an implementation must satisfy in order:

1. kernel available, pinned, version-matched → else `OIC-W-0002`
2. warrant present, well-formed, hash-verified → else `OIC-W-0001` / `0003` / `0004`
3. warrant fresh: epoch, ground-set hash, `valid_from`/`valid_until` → else `OIC-W-0005` / `0006` / `0008` / `0021`
4. no dependency ground expired or revoked → else `OIC-W-0020` / `0007`
5. formula hash matches the control's bound formula → else `OIC-W-0011`
6. source and admission versions match → else `OIC-W-0009` / `0010`
7. `epistemic_status = ESTABLISHED` and grade ≥ envelope minimum → else `OIC-W-0012` / `0013` / `0014` / `0016`
8. authority, admission, evidence, and version checks **outside** the kernel pass

Step 8 is not implemented by this contract and is not implementable by the kernel. It is
named so that no reader mistakes a warrant for a permission.

## 5. Missing grounds

Two levels, per ADR-013 §2.5.

```json
"missing_ground_ids": ["atom:supplier_registered", "atom:threshold_met"],
"missing_ground_anchors": [
  {
    "ground_id": "atom:supplier_registered",
    "source_id": "src:proc-manual-2026",
    "source_node_id": "node:cl-4.2.1",
    "span": { "start": 120, "end": 188 },
    "admitted_unit_id": "cnu:supplier-registration",
    "expected_evidence_type": "registry_extract"
  }
]
```

Level 1 comes from the kernel. Level 2 is enriched by the OIC adapter when authorised.
**The kernel is never asked to interpret source documents.** An empty
`missing_ground_anchors` means enrichment has not run — it does not mean there are no
missing grounds, and a reviewer UI must not render it as "nothing missing".

## 6. Reason code registry

Stable and machine-readable. Adding a code is a minor version; changing a code's meaning
is a breaking change.

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
| `OIC-W-0016` | `WARRANTY_GRADE_INSUFFICIENT` | `PROCEDURAL` |
| `OIC-W-0017` | `WARRANTY_GRADE_UNSUPPORTED` | `PROCEDURAL` |
| `OIC-W-0018` | `SOURCE_ANCHORS_MISSING` | `PROCEDURAL` |
| `OIC-W-0019` | `ADMISSION_IDS_MISSING` | `PROCEDURAL` |
| `OIC-W-0020` | `GROUND_EXPIRED` | `PRECAUTIONARY` |
| `OIC-W-0021` | `WARRANT_NOT_YET_VALID` | `PROCEDURAL` |

### Decision conditions — `OIC-D-nnnn`

| Code | Name | Meaning |
|---|---|---|
| `OIC-D-0001` | `ESTABLISHED_ALL_CHECKS_PASSED` | The gate in §4 passed in full |
| `OIC-D-0002` | `DECISION_MODE_NON_AUTOMATABLE` | Envelope routes to human judgment regardless of logic |
| `OIC-D-0003` | `DECISION_MODE_ADVISORY` | Recorded, does not gate the action |
| `OIC-D-0004` | `FAIL_CLOSED_ON_UNKNOWN` | `on_unknown` applied; **operational only, never a finding** |

`OIC-W-0013` and `OIC-W-0014` are the **only** codes whose basis is `SUBSTANTIVE`. If any
other code appears with `decision_basis: SUBSTANTIVE`, the implementation is wrong.

## 7. `on_unknown` and `decision_mode`

`on_unknown` selects BLOCK-versus-ESCALATE when the epistemic status is not `ESTABLISHED`:

| `on_unknown` | Execution | Basis | Note |
|---|---|---|---|
| `cannot` | `BLOCK` | `PRECAUTIONARY` / `PROCEDURAL` | The system states it cannot decide |
| `escalate` | `ESCALATE` | `PRECAUTIONARY` / `PROCEDURAL` | Routed to a human |
| `deny` | `BLOCK` | `PRECAUTIONARY` / `PROCEDURAL` | **Operational fail-closed only** |

`on_unknown: deny` is the single highest-risk value in the current draft envelope schema.
It reads like a finding and is not one. A conforming implementation records
`on_unknown_applied: "deny"` together with a non-`SUBSTANTIVE` basis, so that the
operational nature of the block survives into every downstream consumer.

`decision_mode` can override toward caution but never toward permission:

| `decision_mode` | Effect |
|---|---|
| `automatic` | `ALLOW` permitted when the §4 gate passes |
| `human_judgment`, `escalation_only`, `non_automatable` | `ESCALATE` even when `ESTABLISHED` (`OIC-D-0002`) |
| `advisory`, `evidence_only` | `ADVISORY`; recorded, does not gate (`OIC-D-0003`) |

## 8. Determinism

- Field ordering in serialised JSON is by sorted key.
- `reason_codes` are sorted lexicographically. Position carries no meaning: the code that
  explains the outcome is identified by the mapping table's *Primary reason code* column,
  not by being first. Sorting is chosen over significance-ordering so that two
  implementations agreeing on the set cannot disagree on the bytes.
- No timestamps beyond the explicit `evaluated_at`, `generated_at`, `valid_from`,
  `valid_until` fields.
- No absolute filesystem paths, no hostnames, no locale-dependent formatting.
- Digests: OIC-side artifacts use `sha256:<64 hex>`; kernel-side `formula_hash` uses the
  kernel's own canonicalisation, which for ZTL v0.1 is an RFC 8785 (JCS) float-free subset
  digested with SHA-384. OIC records that value and does not recompute it.

## 9. Unresolved questions, routed to named authorities

| # | Question | Routed to |
|---|---|---|
| 1 | Is `EARNED` + `hereditary` + non-empty `unverified` reachable? (mapping row 2, fixture 09) | Vitaliy Reznik |
| 2 | Can the kernel emit `EARNED` + `until-verification`? (row 5) | Vitaliy Reznik |
| 3 | Can `OPEN` carry raw verdict `T`? (row 7) | Vitaliy Reznik |
| 4 | Do the two levels of missing-ground representation match what a reviewer needs? | Vitaliy Reznik + Arkadiy Miteiko |
| 5 | Should `control-envelope.schema.json` gain `minimum_warranty_grade`? | GPT-5.6 Thinking → Arkadiy Miteiko |
| 6 | Is `ESTABLISHED` + `ESCALATE` + `PROCEDURAL` the right shape for insufficient grade, or should it be `UNRESOLVED`? | GPT-5.6 Thinking |
| 7 | How are historical `verdict: DENY` records treated on migration? ADR-013 §6 proposes **indeterminate**, never back-filled | Arkadiy Miteiko |
| 8 | Which authority may scope expiry, and over which grounds? | Arkadiy Miteiko |
| 9 | Does the VEIP handoff need fields beyond `RuntimeDecision`? | Arkadiy Miteiko (interim VEIP contract owner) |

None of these is answered by this document. Each is labelled proposed and left open rather
than filled with a plausible guess.

## 10. Boundaries

**ZTL ends with** logical disposition, warranty grade, formula and dependency information,
verified and unverified grounds, epoch and freshness information, recomputation evidence.

**VEIP begins with** consequential action proposal, binding to the admitted control and
authority version, runtime execution disposition, execution occurrence, evidence
recording, reliance, revocation propagation, correction.

ZTL must not create a VEIP lifecycle record. VEIP must not reinterpret the ZTL formula.
`RuntimeDecision` is the handoff artifact between them.

## 11. Standing

Proposed under OIC-WO-002. Not admitted. No ZTL or VEIP code exists, is imported, or is
called. No policy document is parsed, no Institutional IR is constructed, no Open Control
Envelope is generated, no Rego is emitted, and OPA is not invoked.

`STATUS.md` is unchanged. `schemas/draft/` is unchanged. **No semantic implementation was
introduced. The semantic implementation gate remains BLOCKED.**
