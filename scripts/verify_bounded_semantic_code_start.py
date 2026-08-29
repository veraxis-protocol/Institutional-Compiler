#!/usr/bin/env python3
"""Verify the Owner Decision 004 bounded post-open implementation state."""

from __future__ import annotations

import sys
from pathlib import Path

STATUS = "OWNER-AUTHORIZED BOUNDED SEMANTIC IMPLEMENTATION — PRE-EXTERNAL-REVIEW"
AUTHORIZED_PATHS = (
    "src/oic/model_provider.py",
    "src/oic/nvidia_nim.py",
    "src/oic/candidate_extraction.py",
    "src/oic/review_docket.py",
)


def verify(root: Path) -> None:
    status = (root / "STATUS.md").read_text(encoding="utf-8")
    decision = (root / "docs/decisions/OIC-OWNER-DECISION-004.md").read_text(encoding="utf-8")
    receipt = (
        root / "docs/gates/OIC-NVIDIA-NIM-CODE-START-IMPLEMENTATION-RECEIPT-v0.1.md"
    ).read_text(encoding="utf-8")
    if STATUS not in status:
        raise ValueError("bounded owner-authorized status is absent")
    if "Open Run experimental execution:** NOT AUTHORIZED" not in decision:
        raise ValueError("Open Run boundary is absent")
    if "independent_validation_claim = FALSE" not in decision:
        raise ValueError("independent-validation boundary is absent")
    if "9ad37fc80d8f34318c6212ed702de5eab3551cf5" not in receipt:
        raise ValueError("pre-open starting HEAD receipt is absent")
    if "PASS semantic code-start prerequisite evidence; gate remains NOT OPEN" not in receipt:
        raise ValueError("literal pre-open verifier receipt is absent")
    missing = [path for path in AUTHORIZED_PATHS if not (root / path).is_file()]
    if missing:
        raise ValueError(f"authorized bounded production paths missing: {missing}")


if __name__ == "__main__":
    try:
        verify(Path(__file__).resolve().parents[1])
    except (OSError, ValueError) as exc:
        print(f"FAIL bounded semantic code-start state: {exc}")
        sys.exit(1)
    print(
        "PASS owner-authorized bounded semantic code-start state; Open Run remains NOT AUTHORIZED"
    )
