# ZTL conformance procedure — v0.1

**Work order:** ZTL-OIC-WO-002, Deliverable C.
**Purpose:** let a stranger verify, from a clean clone and without trusting us, that the fixtures in `fixtures/interface-freeze-v0.1/` are what the pinned kernel actually returns.

---

## 1. Clean-clone command

```bash
git clone https://github.com/inventor1975/ZTL.git ztl-conformance
cd ztl-conformance
git checkout veraxis-ztl-input-v0.1.1-signed
git tag -v veraxis-ztl-input-v0.1.1-signed      # optional: verify provenance
```

## 2. Pinned reference

| Item | Value |
|---|---|
| Signed tag | `veraxis-ztl-input-v0.1.1-signed` |
| Annotated tag (original, unchanged) | `veraxis-ztl-input-v0.1` |
| Commit both point at | `e819dec7e89d2dc67d6371e1eedb8e7aae854602` |
| Signing key | `F170414DDBB78F231929121175B13F5AEC28313A` |

## 3. Toolchain

| Component | Version | Needed for |
|---|---|---|
| Python | 3.11 or later | the kernel and the checker |
| Lean | `leanprover/lean4:v4.29.1` | only to rebuild the machine-checked corpus; **not** needed for fixture conformance |
| GnuPG | 2.x | only to verify the tag signature |

**No third-party Python packages are required** for the conformance run. The kernel is pure standard library.

## 4. Command

From the OIC repository:

```bash
python3 adapters/ztl/fixtures/interface-freeze-v0.1/verify_fixtures.py \
        --ztl /path/to/ztl-conformance
```

The checker does two independent things: it verifies every fixture file against `SHA256SUMS`, and it re-runs each REACHABLE fixture through `ztljudge.judge` and compares `verdict`, `grade`, `disposition`, `unverified` and `formula` field by field.

## 5. Expected output

```
fixtures reproduced : 12
not-reachable (skip): 3
mismatches          : 0
hash problems       : 0

CONFORMANCE: PASS — this kernel reproduces every reachable fixture.
```

Exit code `0`. Any other exit code means the kernel under test is **not** conformant with this fixture set, and the differing fields are printed in full.

## 6. Failure behavior

| Condition | Checker behavior |
|---|---|
| kernel cannot be imported | exit 2, names the path it tried; no partial "pass" |
| a fixture file was edited | hash mismatch reported with both digests; run fails |
| `SHA256SUMS` absent | explicit warning that integrity was **not** checked; semantics still verified |
| a field differs | prints case, input, expected and actual for every differing field; run fails |
| fixture marked `NOT_REACHABLE` | skipped and counted separately — never silently treated as a pass |

The checker has no "close enough" path. It reports either reproduction or difference.

## 7. No-network assumptions

The conformance run performs **no** network access: no package installation, no remote fetch, no telemetry. Everything needed is in the clone and the standard library. It is safe to run on an air-gapped machine after the clone.

The only network steps are optional and outside the check itself: cloning the repository, and fetching the public key if the signature is to be verified (the key is also committed in-repo as `ZTL-signing-key.pub.asc`).

## 8. Fixture inventory

| Case | Status | disposition / grade / verdict |
|---|---|---|
| `earned-hereditary` | REACHABLE | EARNED / hereditary / T |
| `refuted` | REACHABLE | REFUTED / hereditary / F |
| `refuted-despite-marks` | REACHABLE | REFUTED / hereditary / F |
| `on-credit-sound` | REACHABLE | **ON CREDIT** / sound / T |
| `on-credit-until-verification` | REACHABLE | **ON CREDIT** / until-verification / T |
| `open-with-raw-f` | REACHABLE | OPEN / until-verification / **F** |
| `open-with-raw-z` | REACHABLE | OPEN / until-verification / Z |
| `open-negated-mark` | REACHABLE | OPEN / until-verification / F |
| `nonempty-unverified` | REACHABLE | OPEN / until-verification / F |
| `monotone-refinement` | REACHABLE | EARNED / hereditary / T |
| `contradiction` | REACHABLE | REFUTED / hereditary / F |
| `greedy-collapse` | REACHABLE | OPEN / until-verification / F |
| `earned-sound` | **NOT_REACHABLE** | — |
| `earned-until-verification` | **NOT_REACHABLE** | — |
| `open-with-raw-t` | **NOT_REACHABLE** | — |

### 8.1 The three states the work order asked for that do not exist

Reported rather than fabricated. Searched by exhaustive enumeration over a formula pool with all T/F/Z markings.

- **`earned-sound` and `earned-until-verification`.** `EARNED` is defined as verdict T **with grade `hereditary`**. A T verdict that is only `sound` or `until-verification` is classified **`ON CREDIT`** — "true only while an unverified link holds; if it flips, the claim can die." The requested pairs therefore cannot occur; the corresponding real states are `on-credit-sound` and `on-credit-until-verification`.
- **`open-with-raw-t`.** `OPEN` never carries raw verdict T. A T verdict is either EARNED or ON CREDIT. No envelope rule should be written against this state.

**This matters for the mapping.** The ZTL dossier v0.1 listed three dispositions (EARNED / REFUTED / OPEN) and omitted **ON CREDIT**. That omission is corrected here: an ON CREDIT verdict must **not** be routed as EARNED. It is a T that rides an unverified atom, and mapping it to ALLOW without qualification would authorise action on credit — the precise failure ZTL exists to expose.

## 9. Known limitations

1. **The fixture set is small and hand-selected** (12 reachable cases). It demonstrates the interface contract and the trap cases; it is not a statistical characterisation of the kernel.
2. **Expiry, revocation and epoch transitions are documented but not fixtured.** They are transitions between epochs (see `proposals/EPOCH-EXPIRY-REVOCATION-v0.1.md`), and a single `judge()` call cannot express them. `monotone-refinement` fixtures the within-epoch tick only. Multi-epoch fixtures require an agreed epoch-carrying envelope format and are deferred until OIC confirms one.
3. **`kernel-unavailable` behavior is specified, not fixtured.** It is the absence of a call, not a call with a result: the required behavior is that OIC blocks warrant-dependent publication and never fabricates a warrant. That is an OIC-side assertion; we can state it, not test it from here.
4. **`malformed-input` is bounded, not exhaustive.** The connector enforces `MAX_CLAIM_LEN=1024`, `MAX_ATOMS=64`, `MAX_DISTINCT_ATOMS=12`, `MAX_NAME_LEN=128`, `MAX_PROVENANCE_LEN=4096` and converts parser recursion overflow to `WarrantError`. These bounds were derived from measured DoS behavior (grading is `O(3^distinct_atoms)`), not chosen for elegance.
5. **A mark-dialect hazard exists in a second entry point.** `zverify.grade()` expects `'M'` for a mark, while `judge()` accepts `'Z'`. Passing `'Z'` to `zverify.grade()` returns `hereditary` **silently and wrongly**. Every fixture records both readings so a consumer can see the difference. **Use `judge()`.**
6. **Conformance is not independence.** This procedure was written by the ZTL side and run by the ZTL side. It is Tier-3 evidence. **Independent Tier-1 reproduction remains OPEN.**

---

*This is provisional dependency evidence. Independent Tier-1 reproduction remains OPEN, and the OIC semantic implementation gate remains BLOCKED.*
