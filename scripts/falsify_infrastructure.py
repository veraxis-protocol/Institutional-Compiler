#!/usr/bin/env python3
"""Run bounded falsification checks over implemented infrastructure only."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    (
        "schema-invalid rejection",
        "tests/unit/test_schemas.py::test_broken_schema_fails_metaschema_validation",
    ),
    (
        "manifest digest mismatch rejection",
        "tests/contract/test_baseline.py::test_hash_mismatch_inside_a_synthetic_baseline_fails",
    ),
    (
        "semantic contract mutation rejection",
        "tests/contract/test_semantic_conformance.py::test_reject_duplicated_reason_codes",
    ),
    (
        "semantic code-start remains blocked",
        "tests/contract/test_claims_discipline.py::test_operator_guide_states_the_semantic_gate_is_blocked",
    ),
)


def main() -> int:
    for name, selector in CASES:
        result = subprocess.run(  # noqa: S603 - selectors are fixed above
            [sys.executable, "-m", "pytest", "-q", selector],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(f"FAIL {name}: pytest exit {result.returncode}")
        print(f"PASS {name}: {selector}")
    print("PASS bounded infrastructure falsification: 4/4 expected checks observed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
