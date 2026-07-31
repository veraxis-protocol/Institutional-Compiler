# Warrant contract golden fixtures

**PROPOSED conformance fixtures. Not admitted. No implementation consumes them yet.**

Seventeen deterministic cases pinning the contract in
[`docs/contracts/WARRANT-CONTRACT-v0.1.md`](../../../docs/contracts/WARRANT-CONTRACT-v0.1.md)
and the mapping in
[`ZTL-OCE-MAPPING-v0.1.md`](../../../docs/contracts/ZTL-OCE-MAPPING-v0.1.md).
Governing decision: [ADR-013](../../../adr/ADR-013.md).

## What these are, and what they are not

They are **the acceptance suite a future adapter must reproduce**. Each file states an
input triple — envelope, kernel result, runtime context — and the exact decision that must
come out.

They are **not evidence that an implementation is correct**, because no implementation
exists. Today the tests prove the fixtures are internally consistent, schema-valid, and
consistent with the published mapping table. That is worth something on its own: it makes
the contract executable rather than prose, and it means a wrong fixture fails the build
rather than sitting unnoticed until an adapter is written against it.

No fixture was produced by calling ZTL. The kernel outputs in them are constructed from
the interface described in `adapters/ztl/ZTL-DOSSIER-v0.1.md` §5–§6.

## Structure

```
case_id, mapping_row, description, status
input.envelope           control-envelope fields, plus the PROPOSED minimum_warranty_grade
input.ztl_result         disposition, grade, raw_verdict, unverified
input.warrant_artifact   validates against schemas/proposed/warrant-artifact.schema.json, or null
input.runtime_context    epoch, hashes, versions, revocations, kernel availability, clock
expected.*               warrant_state, epistemic_status, execution_disposition,
                         decision_basis, reason_codes, missing grounds
expected.runtime_decision  validates against schemas/proposed/runtime-decision.schema.json
```

## The cases

Twenty-four cases. `Reach` is measured reachability against the pinned ZTL v0.1 kernel.

| # | Case | Row | Reach | What it pins |
|---|---|---|---|---|
| 01 | `earned-hereditary-current` | 25 | ✅ | The only clean ALLOW |
| 02 | `earned-sound-permitted-grade` | 29 | ❌ | Defensive; a substitute kernel only |
| 03 | `earned-sound-insufficient-grade` | 30 | ❌ | Defensive; CONTROL_REQUIREMENT shape |
| 04 | `earned-until-verification` | 31 | ❌ | `OIC-W-0022`, not `DISPOSITION_OPEN` |
| 05 | `refuted` | 21 | ✅ | The only BLOCK that is a negative finding |
| 06 | `open-raw-f` | 22 | ✅ | **The measured trap** — see below |
| 07 | `open-raw-t` | 24 | ❌ | OPEN never carries raw `T` |
| 08 | `open-raw-z` | 23 | ✅ | Bare `Z` mark |
| 09 | `on-credit-sound-permitted` | 26 | ✅ | ALLOW while grounds are still missing |
| 10 | `kernel-unavailable` | 1 | ✅ | Never fabricate a warrant |
| 11 | `warrant-stale` | 5 | ✅ | A good disposition does not rescue a stale artifact |
| 12 | `ground-expired` | 8 | ✅ | Anti-tick, PRECAUTIONARY |
| 13 | `ground-revoked` | 9 | ✅ | I-13 |
| 14 | `epoch-mismatch` | 10 | ✅ | Compared **within one scope and authority** |
| 15 | `contradiction` | 20 | ✅ | CONTRADICTED, never REFUTED |
| 16 | `source-version-mismatch` | 11 | ✅ | I-07 |
| 17 | `admission-version-mismatch` | 12 | ✅ | I-02 |
| 18 | `warrant-not-yet-valid` | 7 | ✅ | Not-yet-in-force is as unusable as expired |
| 19 | `on-credit-sound-insufficient-grade` | 27 | ✅ | **Reachable CONTROL_REQUIREMENT** on grade |
| 20 | `on-credit-until-verification` | 28 | ✅ | Rides an atom that can flip |
| 21 | `decision-mode-human-judgment` | 32 | ✅ | Perfect warrant, escalated by policy |
| 22 | `decision-mode-advisory` | 33 | ✅ | Recorded, does not gate |
| 23 | `profile-mismatch` | 14 | ✅ | Hashes from different profiles are never compared |
| 24 | `warrant-not-required` | 19 | ✅ | No ALLOW path specified in v0.1 |

## NOT_REACHABLE fixtures are load-bearing

Four cases describe combinations the pinned kernel **cannot** produce. They are not dead
weight: `test_warrant_validity_matches_declared_reachability` asserts their warrants
**fail** `warrant-artifact.schema.json`, because that schema encodes the measured
reachability as `if`/`then` constraints. If ZTL later emits one of these, the fixture
starts passing schema validation and the test fails — which is exactly the notification
you want.

They also specify what an adapter must do if it ever meets one: fail closed with
`OIC-W-0022`, never fall through.

## The `ON CREDIT` correction

ZTL dossier v0.1 listed three dispositions. There are four. `ON CREDIT` is a `T` verdict
that holds **only while an unverified atom holds** and can die when that atom resolves.
The original fixture set had no such case and instead assumed `EARNED` could carry
unverified grounds — measurement showed it cannot. Cases 09, 19, and 20 replace that
assumption with the real thing.

## Fixture 06 is the one that matters most

The ZTL dossier reports, measured against the pinned kernel:

```
judge("p & q", {"p": "T", "q": "Z"})
  -> verdict='F', grade='until-verification', disposition='OPEN', unverified=['q']
```

Raw verdict `F`, disposition `OPEN`. An adapter reading `raw_verdict` records *"established
false"* for something merely unverified, violating **I-03**. The envelope in this fixture
also sets `on_unknown: "deny"`, which is the second half of the trap: the block is real,
but it is operational.

The fixture therefore requires `epistemic_status: UNRESOLVED`, `decision_basis:
PRECAUTIONARY`, and `on_unknown_applied: "deny"` — a block that stays visibly
distinguishable from `05-refuted`, which is the same `BLOCK` for a completely different
reason.

## Determinism

Every digest is derived from a fixed label, so regeneration is byte-identical. There are
no timestamps beyond the explicit declared ones, no absolute paths, and no hostnames.
`kernel_commit` is the real pinned ZTL tag target `e819dec7…854602`; all other digests are
synthetic and carry no cryptographic meaning.

## Reachability caveats

Rows 2, 5, and 7 (fixtures `09`, `04`, `07`) are our reading of the ZTL interface, not
measurements. They are specified so an adapter meeting them fails closed, and are routed
to Vitaliy Reznik for confirmation in
[WARRANT-CONTRACT §9](../../../docs/contracts/WARRANT-CONTRACT-v0.1.md#9-unresolved-questions-routed-to-named-authorities).
If the kernel cannot emit one of them, the row stays as a defensive specification and the
fixture should be relabelled rather than deleted.
