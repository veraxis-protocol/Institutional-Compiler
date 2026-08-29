#!/usr/bin/env python3
"""Run bounded falsification checks over implemented infrastructure only."""

from __future__ import annotations

import re
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
        "candidate authority boundary remains fail-closed",
        "tests/contract/test_claims_discipline.py::test_operator_guide_states_the_candidate_authority_boundary",
    ),
)

SUMMARY_LINE = re.compile(r"^(?P<outcomes>.+?) in \d+(?:\.\d+)?s$")
SUMMARY_ITEM = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|xfailed|xpassed|errors?|deselected|warnings?)"
)


def parse_pytest_summary(output: str) -> dict[str, int]:
    """Parse one unambiguous pytest terminal-summary line or fail closed."""
    candidates: list[dict[str, int]] = []
    for line in output.splitlines():
        match = SUMMARY_LINE.fullmatch(line.strip())
        if match is None:
            continue
        outcomes = match.group("outcomes")
        items = list(SUMMARY_ITEM.finditer(outcomes))
        if not items:
            continue
        remainder = SUMMARY_ITEM.sub("", outcomes).replace(",", "").strip()
        if remainder:
            continue
        parsed: dict[str, int] = {}
        for item in items:
            kind = item.group("kind")
            if kind in {"error", "errors"}:
                kind = "errors"
            elif kind in {"warning", "warnings"}:
                kind = "warnings"
            if kind in parsed:
                raise ValueError(f"duplicate pytest summary outcome: {kind}")
            parsed[kind] = int(item.group("count"))
        candidates.append(parsed)
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one parseable pytest summary, found {len(candidates)}")
    return candidates[0]


def actual_single_pass(returncode: int, output: str) -> tuple[bool, str]:
    """Accept only an exit-zero run proving exactly one selected test passed."""
    if returncode != 0:
        return False, f"pytest exit {returncode}"
    try:
        summary = parse_pytest_summary(output)
    except ValueError as error:
        return False, f"unusable pytest summary: {error}"
    disallowed = {
        key: value for key, value in summary.items() if key not in {"passed", "warnings"} and value
    }
    if summary.get("passed") != 1 or disallowed:
        return False, f"expected exactly 1 passed and no other outcomes; observed {summary}"
    return True, "expected selected=1 observed passed=1"


def success_message(observed: int) -> str:
    return (
        f"PASS bounded infrastructure falsification: "
        f"{observed}/{len(CASES)} expected checks observed"
    )


def main() -> int:
    observed = 0
    for name, selector in CASES:
        result = subprocess.run(  # noqa: S603 - selectors are fixed above
            [sys.executable, "-m", "pytest", "-q", selector],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = result.stdout + result.stderr
        accepted, detail = actual_single_pass(result.returncode, combined)
        if not accepted:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(f"FAIL {name}: {detail}")
        observed += 1
        print(f"PASS {name}: {selector}; {detail}")
    print(success_message(observed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
