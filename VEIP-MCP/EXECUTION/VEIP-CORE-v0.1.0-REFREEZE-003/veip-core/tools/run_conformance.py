#!/usr/bin/env python3
"""Run the externally supplied immutable VEIP conformance runner."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    package_root = project.parent
    runner = package_root / "runner" / "extracted" / "VEIP_CONFORMANCE_RUNNER_v0.1" / "veip_test.py"
    corpus = package_root / "inputs" / "VEIP_CANONICAL_FIXTURES_v0.3.json"
    adapter = project / "tools" / "adapter.py"
    report = package_root / "03_CONFORMANCE_REPORT.json"
    command = [
        sys.executable,
        str(runner),
        str(corpus),
        "--engine-cmd",
        f"{sys.executable} {adapter}",
        "--json-report",
        str(report),
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
