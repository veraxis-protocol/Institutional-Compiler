# -*- coding: utf-8 -*-
"""Exhaustive census of the ZTL kernel's output space, and of what a warrant
artifact's `dependency_ids` must contain.

Written to answer two questions raised by the PR #16 mapping with measurement
rather than reading:

  1. Which (disposition, grade, raw_verdict, unverified) cells does the kernel
     actually produce?  The mapping and the ztl-v0.1 profile both assert that
     `EARNED` implies an empty `unverified` list.  That is the question this
     census settles.

  2. What does "the grounds the conclusion depends on" mean operationally?
     A ground is *load-bearing* if withdrawing it (an anti-tick: marking a
     verified atom `Z` again) moves the disposition.  This measures whether
     probing one ground at a time finds them all.

Usage:
    python3 kernel_census.py --ztl /path/to/ZTL [--json out.json]

Exit code 0 = census completed.  Non-zero = the kernel could not be loaded.
No network access is performed or required.
"""
import argparse
import itertools
import json
import os
import sys

# A pool chosen to exercise conjunction, disjunction, implication, negation,
# redundant grounds, and tautological consequents.  It is not a proof of
# coverage; it is a census over a stated pool, and the pool is printed.
POOL = (
    "p",
    "~p",
    "p & q",
    "p | q",
    "p -> q",
    "~(p & q)",
    "~(p | q)",
    "p | ~p",
    "p & ~p",
    "~p | q",
    "(p | q) & r",
    "(p & q) | r",
    "p | (q & r)",
    "p & (q | r)",
    "(p | q) | r",
    "p -> (q | r)",
    "(p -> q) & (q -> r)",
    "p & (q | ~q)",
    "(~p) -> (q -> q)",
    "p -> (q -> p)",
    "(p -> q) | (q -> p)",
    "~~p -> p",
)

MARKS = ("T", "F", "Z")


def atoms_of(formula):
    return sorted({c for c in formula if c.isalpha()})


def census(kernel):
    """Every reachable (disposition, grade, verdict, unverified-emptiness) cell."""
    cells = {}
    total = 0
    for formula in POOL:
        atoms = atoms_of(formula)
        for combo in itertools.product(MARKS, repeat=len(atoms)):
            marking = dict(zip(atoms, combo))
            result = kernel.judge(formula, marking)
            total += 1
            key = (
                result["disposition"],
                result["grade"],
                result["verdict"],
                "empty" if not result["unverified"] else "non-empty",
            )
            cell = cells.setdefault(key, {"count": 0, "example": None})
            cell["count"] += 1
            if cell["example"] is None:
                cell["example"] = {
                    "formula": formula,
                    "marking": marking,
                    "unverified": list(result["unverified"]),
                }
    return cells, total


def refinement_stability(kernel):
    """Does `hereditary` hold?  Refine every unverified atom every way and see
    whether the verdict of an EARNED result can be moved."""
    cases = 0
    refinements = 0
    moved = []
    for formula in POOL:
        atoms = atoms_of(formula)
        for combo in itertools.product(MARKS, repeat=len(atoms)):
            marking = dict(zip(atoms, combo))
            result = kernel.judge(formula, marking)
            if result["disposition"] != "EARNED" or not result["unverified"]:
                continue
            cases += 1
            unverified = list(result["unverified"])
            for values in itertools.product("TF", repeat=len(unverified)):
                refined = dict(marking)
                refined.update(dict(zip(unverified, values)))
                after = kernel.judge(formula, refined)
                refinements += 1
                if after["verdict"] != result["verdict"]:
                    moved.append(
                        {"formula": formula, "from": marking, "to": refined,
                         "verdict": after["verdict"]}
                    )
    return {"earned_with_unverified": cases, "refinements_tried": refinements,
            "verdict_moved": len(moved), "counterexamples": moved[:5]}


def dependency_probe(kernel):
    """A ground is load-bearing if withdrawing it moves the disposition.

    Withdrawal is the anti-tick: a verified atom (T or F) goes back to Z.
    Withdrawing an already-unverified atom is a no-op, so only verified atoms
    can be probed — which is exactly the revocation case `dependency_ids`
    exists to serve.

    The question that matters for the contract: is probing one ground at a
    time enough?  If a pair can move the disposition where neither member can
    alone, then a minimal dependency set derived by single probing is unsafe.
    """
    single_only = 0
    joint_found = []
    total = 0
    for formula in POOL:
        atoms = atoms_of(formula)
        for combo in itertools.product(MARKS, repeat=len(atoms)):
            marking = dict(zip(atoms, combo))
            result = kernel.judge(formula, marking)
            verified = [a for a in atoms if marking[a] != "Z"]
            if len(verified) < 2:
                continue
            total += 1
            bearing = set()
            for a in verified:
                probed = dict(marking)
                probed[a] = "Z"
                if kernel.judge(formula, probed)["disposition"] != result["disposition"]:
                    bearing.add(a)
            single_only += 1 if bearing else 0
            for a, b in itertools.combinations(verified, 2):
                if a in bearing or b in bearing:
                    continue
                probed = dict(marking)
                probed[a] = probed[b] = "Z"
                after = kernel.judge(formula, probed)
                if after["disposition"] != result["disposition"]:
                    joint_found.append(
                        {
                            "formula": formula,
                            "marking": marking,
                            "disposition": result["disposition"],
                            "withdrawn": [a, b],
                            "disposition_after": after["disposition"],
                            "neither_alone_moves_it": True,
                        }
                    )
                    break
    return {
        "cases_with_two_or_more_verified_grounds": total,
        "cases_where_a_pair_moves_it_but_neither_member_does": len(joint_found),
        "examples": joint_found[:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ztl", required=True, help="path to a ZTL checkout")
    ap.add_argument("--json", default=None, help="write the machine-readable census here")
    args = ap.parse_args()

    sys.path.insert(0, args.ztl)
    try:
        import ztljudge as kernel
    except ImportError as e:
        print(f"FAIL: cannot import the kernel from {args.ztl}: {e}")
        return 2

    cells, total = census(kernel)
    stability = refinement_stability(kernel)
    dependencies = dependency_probe(kernel)

    print(f"pool: {len(POOL)} formulas, markings over {{T,F,Z}} — {total} cases\n")
    print(f"{'disposition':11} {'grade':18} {'v':1} {'unverified':10} {'n':>5}  example")
    for key in sorted(cells):
        cell = cells[key]
        example = cell["example"]
        print(
            f"{key[0]:11} {key[1]:18} {key[2]:1} {key[3]:10} {cell['count']:5}  "
            f"{example['formula']}  {example['marking']}"
        )

    print()
    print("EARNED with a non-empty unverified list:")
    print(f"  cases                    : {stability['earned_with_unverified']}")
    print(f"  refinements tried        : {stability['refinements_tried']}")
    print(f"  verdict moved            : {stability['verdict_moved']}")

    print()
    print("dependency probing (anti-tick on verified grounds):")
    print(f"  cases with >=2 verified grounds : "
          f"{dependencies['cases_with_two_or_more_verified_grounds']}")
    print(f"  pair moves it, neither alone    : "
          f"{dependencies['cases_where_a_pair_moves_it_but_neither_member_does']}")

    if args.json:
        payload = {
            "pool": list(POOL),
            "cases": total,
            "cells": [
                {
                    "disposition": k[0],
                    "grade": k[1],
                    "raw_verdict": k[2],
                    "unverified": k[3],
                    "count": v["count"],
                    "example": v["example"],
                }
                for k, v in sorted(cells.items())
            ],
            "refinement_stability": stability,
            "dependency_probe": dependencies,
        }
        with open(args.json, "w") as fp:
            json.dump(payload, fp, indent=1, sort_keys=True)
            fp.write("\n")
        print(f"\nwritten: {os.path.relpath(args.json)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
