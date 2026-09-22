#!/usr/bin/env python3
"""Execute every frozen input without reading or comparing expected outputs."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT.parent
sys.path.insert(0, str(PROJECT / "src"))

from veip_core import EngineError, adjudicate, explain_boundary  # noqa: E402


def main() -> int:
    corpus_path = PACKAGE_ROOT / "inputs" / "VEIP_CANONICAL_FIXTURES_v0.3.json"
    document = json.loads(corpus_path.read_text(encoding="utf-8"))
    results = []
    for fixture in document["fixtures"]:
        try:
            if fixture["entry_point"] == "adjudicate":
                output = adjudicate(deepcopy(fixture["input"]))
            else:
                output = explain_boundary(deepcopy(fixture["input"]))
        except EngineError as exc:
            output = exc.to_dict()
        results.append({"fixture_id": fixture["fixture_id"], "output": output})
    json.dump(results, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
