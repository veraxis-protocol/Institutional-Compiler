"""JSON request -> pinned ZTL invocation -> JSON response. Nothing else.

This file is the whole of the OIC/ZTL executable boundary for the bounded
demonstration lane. It exists so that exactly one place in the repository knows
how to reach the kernel, and so that place can be read in one sitting.

What it does
------------
1. Verifies the external ZTL checkout is exactly the pinned commit.
2. Imports ``ztljudge`` from that checkout.
3. Calls ``ztljudge.judge`` with a caller-supplied formula and marking.
4. Returns the kernel's result, unchanged, as JSON.

What it deliberately does not do
--------------------------------
- It never calls ``zverify.grade``. That entrypoint speaks a different marking
  dialect ('M' rather than 'Z') and silently returns an incorrect warranty grade
  when called with the ``judge()`` alphabet (hazard ZTL-H-001). Consuming it
  would upgrade ON CREDIT to hereditary without saying so.
- It never maps a raw verdict onto an institutional disposition. ``T`` is not
  ALLOW. The kernel result crosses this boundary uninterpreted; every
  institutional reading of it happens on the OIC side, where it can be governed.
- It carries no OAM authorization policy. Authority, delegation, currentness and
  admission are institutional facts and are not propositions for a logic kernel.

Fail-closed
-----------
Every failure path returns ``{"ok": false, "error_code": ..., "error": ...}``
rather than raising across the boundary or, worse, returning a usable-looking
result. A checkout whose HEAD is not the pinned commit is refused before the
kernel is imported, not after.

Usage
-----
    echo '{"formula": "a & b", "marking": {"a": "T", "b": "T"}}' \\
        | python3 adapters/ztl/demo_bridge.py --ztl /path/to/ZTL
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

#: The kernel commit this bridge is pinned to. A checkout at any other commit is
#: refused: dispositions and grades are not portable across kernel revisions.
PINNED_KERNEL_COMMIT = "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"

#: The only entrypoint this bridge is permitted to call.
PERMITTED_ENTRYPOINT = "ztljudge.judge"

#: Never called. Present as a value so a test can assert the prohibition rather
#: than grep for an absence.
PROHIBITED_ENTRYPOINT = "zverify.grade"

#: The kernel's marking alphabet. Anything else is refused before invocation.
MARKING_ALPHABET = ("T", "F", "Z")

#: Fields lifted from the kernel result. `why` is presentational and is carried
#: through untouched but must not be parsed.
RESULT_FIELDS = ("formula", "verdict", "grade", "disposition", "unverified", "why", "marking")


class BridgeError(Exception):
    """A boundary condition that must fail closed rather than return a result."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def resolve_checkout_commit(ztl_path: Path) -> str:
    """Read the HEAD commit of a local ZTL checkout, or refuse.

    Read-only: ``git rev-parse HEAD`` against a path the operator supplied. No
    network access, no fetch, no checkout mutation.
    """
    if not ztl_path.is_dir():
        raise BridgeError("ZTL_CHECKOUT_NOT_FOUND", f"no ZTL checkout at {ztl_path}")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, read-only
            ["git", "-C", str(ztl_path), "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BridgeError("ZTL_CHECKOUT_UNREADABLE", f"cannot read {ztl_path}: {error}") from error
    if completed.returncode != 0:
        raise BridgeError(
            "ZTL_CHECKOUT_UNREADABLE",
            f"git rev-parse failed in {ztl_path}: {completed.stderr.strip()}",
        )
    return completed.stdout.strip()


def verify_pin(ztl_path: Path) -> str:
    """Refuse any checkout that is not exactly the pinned commit."""
    observed = resolve_checkout_commit(ztl_path)
    if observed != PINNED_KERNEL_COMMIT:
        raise BridgeError(
            "ZTL_PIN_MISMATCH",
            f"checkout is at {observed}, pinned commit is {PINNED_KERNEL_COMMIT}",
        )
    return observed


def _validate_request(request: dict[str, Any]) -> tuple[str, dict[str, str]]:
    formula = request.get("formula")
    if not isinstance(formula, str) or not formula.strip():
        raise BridgeError("BAD_REQUEST", "request carries no formula string")
    raw_marking = request.get("marking", {})
    if not isinstance(raw_marking, dict):
        raise BridgeError("BAD_REQUEST", "marking must be an object")
    marking: dict[str, str] = {}
    for atom, value in raw_marking.items():
        if not isinstance(atom, str) or not isinstance(value, str):
            raise BridgeError("BAD_REQUEST", "marking keys and values must be strings")
        if value not in MARKING_ALPHABET:
            raise BridgeError(
                "BAD_REQUEST",
                f"marking {atom}={value!r} is outside the kernel alphabet {MARKING_ALPHABET}",
            )
        marking[atom] = value
    return formula, marking


def judge(request: dict[str, Any], ztl_path: Path) -> dict[str, Any]:
    """Verify the pin, invoke ``ztljudge.judge`` once, return the raw result.

    The returned ``result`` is the kernel's own vocabulary: EARNED / ON CREDIT /
    OPEN / REFUTED, a raw verdict in {T, F, Z}, and a warranty grade. It is not
    an institutional disposition and must not be read as one.
    """
    formula, marking = _validate_request(request)
    commit = verify_pin(ztl_path)

    sys.path.insert(0, str(ztl_path))
    try:
        import ztljudge
    except ImportError as error:
        raise BridgeError("ZTL_IMPORT_FAILED", f"cannot import ztljudge: {error}") from error
    finally:
        if sys.path and sys.path[0] == str(ztl_path):
            sys.path.pop(0)

    try:
        raw = ztljudge.judge(formula, marking)
    except (ValueError, KeyError, TypeError) as error:
        raise BridgeError("KERNEL_REFUSED", f"kernel refused the formula: {error}") from error

    return {
        "ok": True,
        "kernel_commit": commit,
        "entrypoint": PERMITTED_ENTRYPOINT,
        "request": {"formula": formula, "marking": marking},
        "result": {field: raw.get(field) for field in RESULT_FIELDS},
    }


def run(request: dict[str, Any], ztl_path: Path) -> dict[str, Any]:
    """Bridge entry point: always returns a JSON-serializable envelope."""
    try:
        return judge(request, ztl_path)
    except BridgeError as error:
        return {"ok": False, "error_code": error.error_code, "error": str(error)}


def main(argv: list[str] | None = None) -> int:
    """Read one JSON request on stdin, write one JSON response on stdout."""
    parser = argparse.ArgumentParser(
        description="Pinned ZTL invocation bridge. Reads one JSON request on stdin."
    )
    parser.add_argument("--ztl", required=True, type=Path, help="path to a local ZTL checkout")
    args = parser.parse_args(argv)

    try:
        request = json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        response: dict[str, Any] = {
            "ok": False,
            "error_code": "BAD_REQUEST",
            "error": f"stdin is not valid JSON: {error}",
        }
    else:
        if not isinstance(request, dict):
            response = {
                "ok": False,
                "error_code": "BAD_REQUEST",
                "error": "request must be a JSON object",
            }
        else:
            response = run(request, args.ztl)

    json.dump(response, sys.stdout, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
