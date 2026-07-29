# -*- coding: utf-8 -*-
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
import os
import sys

FIELDS = ("verdict", "grade", "disposition", "unverified", "formula")


def load(path):
    with open(path) as fp:
        return json.load(fp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ztl", required=True, help="path to a ZTL checkout")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    sys.path.insert(0, a.ztl)
    try:
        import ztljudge as K
    except ImportError as e:
        print(f"FAIL: cannot import the kernel from {a.ztl}: {e}")
        return 2

    files = sorted(f for f in os.listdir(a.dir)
                   if f.endswith(".json") and f != "INDEX.json")
    checked = skipped = bad = 0
    hash_bad = 0

    # 1. integrity: the fixtures must match SHA256SUMS
    sums_path = os.path.join(a.dir, "SHA256SUMS")
    if os.path.exists(sums_path):
        want = {}
        for line in open(sums_path):
            h, _, n = line.strip().partition("  ")
            want[n] = h
        for n, h in want.items():
            p = os.path.join(a.dir, n)
            if not os.path.exists(p):
                print(f"HASH MISSING FILE: {n}")
                hash_bad += 1
                continue
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if got != h:
                print(f"HASH MISMATCH: {n}\n  recorded {h}\n  actual   {got}")
                hash_bad += 1
    else:
        print("WARNING: SHA256SUMS absent — integrity not checked")

    # 2. semantics: the kernel must reproduce every reachable fixture
    for name in files:
        fx = load(os.path.join(a.dir, name))
        if fx.get("status") != "REACHABLE":
            skipped += 1
            continue
        inp, exp = fx["input"], fx["raw_output"]
        got = K.judge(inp["formula"], inp["marking"])
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
