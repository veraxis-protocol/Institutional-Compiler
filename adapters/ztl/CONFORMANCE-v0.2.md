# ZTL conformance procedure — v0.2

**Work order:** ZTL-OIC-WO-003, Phase 1.
**Purpose:** let a stranger verify, from a clean clone and without trusting us, that the fixtures in `fixtures/interface-freeze-v0.2/` are what the pinned kernel actually returns.

The v0.1 set and its index are preserved byte-for-byte; v0.2 adds exactly one measured fixture, `earned-hereditary-nonempty-unverified.json` — the witness that `EARNED`/`hereditary` may carry a non-empty informational `unverified` list (61 of 294 census cases).

---

## 1. The pin, and why it moved

**The v0.2 pin is NOT the v0.1 pin, deliberately.** The work order asked the new fixture to record the v0.1 pin `e819dec7`. Measured before writing anything: that commit **predates the kernel entrypoint** — `judge()` first appears in `25510dd` ("ztltool: add judge()") and is renamed to `ztljudge.judge` in `c858429`, both after `e819dec7`. Running the documented conformance command against a clean `e819dec7` worktree exits `2` with `No module named 'ztljudge'`. A fixture pinned there would carry a recomputation command that provably fails; the same applies retroactively to the v0.1 procedure (see §6).

| Item | Value |
|---|---|
| Signed tag | `veraxis-ztl-input-v0.2-signed` |
| Commit it points at | `56e1ff0510c62b04dbd85bbe08b7a6deacbf276b` |
| Signing key | `F170414DDBB78F231929121175B13F5AEC28313A` |
| Kernel entrypoint | `ztljudge.judge` (exists at this pin; measured) |

## 2. Clean-clone command

```bash
git clone https://github.com/inventor1975/ZTL.git ztl-conformance
cd ztl-conformance
git checkout veraxis-ztl-input-v0.2-signed
git tag -v veraxis-ztl-input-v0.2-signed      # optional: verify provenance
```

## 3. Toolchain

Python 3.11+; no third-party packages. GnuPG 2.x only for tag verification. Lean is not needed for fixture conformance.

## 4. Command

From the OIC repository:

```bash
python3 adapters/ztl/fixtures/interface-freeze-v0.2/verify_fixtures.py \
        --ztl /path/to/ztl-conformance
```

## 5. Expected output

```
fixtures reproduced : 13
not-reachable (skip): 3
mismatches          : 0
hash problems       : 0

CONFORMANCE: PASS — this kernel reproduces every reachable fixture.
```

Exit code `0`. The measured run record is `evidence/CONFORMANCE-v0.2-run.txt`.

## 6. Honest ledger

- **v0.1 lineage hole (now visible, not repaired here):** `CONFORMANCE-v0.1.md` §1–2 instructs checking out `veraxis-ztl-input-v0.1.1-signed` (= `e819dec7`) and running `verify_fixtures.py`; at that pin the import of `ztljudge` fails (exit 2, measured). The v0.1 fixtures themselves are genuine live-run records, but their documented recomputation path never worked at the documented pin. v0.1 is preserved unchanged as the record of what was published; **v0.2 is the set with a working pin.**
- The kernel-profile `ztl-v0.1.json` field `commit: e819dec7…` and its provenance line ("reproduced against the pinned commit by its author") inherit the same hole; flagged in the WO-003 Phase 2 review.
- The new fixture records both OIC hash projections computed by the SC-WA-002 definitions (`formula_hash` SHA-384 over the kernel-rendered formula; `output_hash` SHA-256 over the five-field projection), `dependency_ids = ["p"]` by the profile's over-approximation rule, the exact caller input, its hash, and the recomputation command at the v0.2 pin.

## 7. Fixture-set identity

| Item | Value |
|---|---|
| `INDEX.json` SHA-256 | `ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145` |
| Cases | 16 total — 13 REACHABLE, 3 NOT_REACHABLE |
| New in v0.2 | `earned-hereditary-nonempty-unverified.json` (`fixture_sha256` `e1941d1b2c49f0e10b59123d4fc9f76831cbc1af33b56eff0d5324f3f6606b3d`) |
