"""Conformance check: re-run every REACHABLE fixture against a ZTL kernel and
compare field by field.

This is the executable half of adapters/ztl/CONFORMANCE-v0.1.md. It proves that
the fixtures were not hand-written: a kernel at the pinned tag reproduces them
exactly, and any kernel that does not is not conformant.

Usage:
    python3 verify_fixtures.py --ztl /path/to/ZTL [--dir .]

Exit code 0 = conformant. Non-zero = at least one mismatch, printed in full.
No network access is performed or required.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

FIELDS = ("verdict", "grade", "disposition", "unverified", "formula")


def load(path: Path) -> dict[str, Any]:
    with path.open() as fp:
        return json.load(fp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ztl", required=True, help="path to a ZTL checkout")
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent))
    a = ap.parse_args()

    here = Path(a.dir)
    sys.path.insert(0, a.ztl)
    try:
        import ztljudge as kernel
    except ImportError as e:
        print(f"FAIL: cannot import the kernel from {a.ztl}: {e}")
        return 2

    files = sorted(f.name for f in here.iterdir() if f.suffix == ".json" and f.name != "INDEX.json")
    checked = skipped = bad = 0
    hash_bad = 0

    # 1. integrity: the fixtures must match SHA256SUMS
    sums_path = here / "SHA256SUMS"
    if sums_path.exists():
        want = {}
        for line in sums_path.read_text().splitlines():
            h, _, n = line.strip().partition("  ")
            want[n] = h
        for n, h in want.items():
            p = here / n
            if not p.exists():
                print(f"HASH MISSING FILE: {n}")
                hash_bad += 1
                continue
            got_hash = hashlib.sha256(p.read_bytes()).hexdigest()
            if got_hash != h:
                print(f"HASH MISMATCH: {n}\n  recorded {h}\n  actual   {got_hash}")
                hash_bad += 1
    else:
        print("WARNING: SHA256SUMS absent — integrity not checked")

    # 2. semantics: the kernel must reproduce every reachable fixture
    for name in files:
        fx = load(here / name)
        if fx.get("status") != "REACHABLE":
            skipped += 1
            continue
        inp, exp = fx["input"], fx["raw_output"]
        got = kernel.judge(inp["formula"], inp["marking"])
        diffs = [(f, exp[f], got[f]) for f in FIELDS if exp[f] != got[f]]
        if diffs:
            bad += 1
            print(f"MISMATCH {fx['case_id']}  ({inp['formula']} | {inp['marking']})")
            for f, e, g in diffs:
                print(f"    {f}: fixture={e!r}  kernel={g!r}")
        else:
            checked += 1

    print()
    print(f"fixtures reproduced : {checked}")
    print(f"not-reachable (skip): {skipped}")
    print(f"mismatches          : {bad}")
    print(f"hash problems       : {hash_bad}")
    if bad or hash_bad:
        print("\nCONFORMANCE: FAILED")
        return 1
    print("\nCONFORMANCE: PASS — this kernel reproduces every reachable fixture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
