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

| # | Case | Row | What it pins |
|---|---|---|---|
| 01 | `earned-hereditary-current` | 1 | The only clean ALLOW |
| 02 | `earned-sound-permitted-grade` | 3 | Envelope tolerates a non-monotone warrant |
| 03 | `earned-sound-insufficient-grade` | 4 | ESTABLISHED but escalated on policy, not doubt |
| 04 | `earned-until-verification` | 5 | Present-marking-only establishes nothing durable |
| 05 | `refuted` | 6 | The only BLOCK that is a finding |
| 06 | `open-raw-f` | 8 | **The measured case** — see below |
| 07 | `open-raw-t` | 7 | A favourable raw marking still establishes nothing |
| 08 | `open-raw-z` | 9 | Bare Z on an atom |
| 09 | `unverified-ground` | 2 | ALLOW while missing grounds are still surfaced |
| 10 | `kernel-unavailable` | 11 | Never fabricate a warrant |
| 11 | `warrant-stale` | 15 | A good disposition does not rescue a stale artifact |
| 12 | `ground-expired` | 17 | Anti-tick, PRECAUTIONARY |
| 13 | `ground-revoked` | 18 | I-13 |
| 14 | `epoch-mismatch` | 19 | Bound to an epoch that no longer exists |
| 15 | `contradiction` | 10 | CONTRADICTED, never REFUTED |
| 16 | `source-version-mismatch` | 20 | I-07 |
| 17 | `admission-version-mismatch` | 21 | I-02 |

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
