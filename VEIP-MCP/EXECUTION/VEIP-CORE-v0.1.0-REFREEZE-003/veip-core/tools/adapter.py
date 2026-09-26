#!/usr/bin/env python3
"""JSON-lines-compatible one-request adapter for the supplied conformance runner."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from veip_core import EngineError, adjudicate, explain_boundary  # noqa: E402


def main() -> int:
    envelope = json.load(sys.stdin)
    try:
        if envelope.get("entry_point") == "adjudicate":
            output = adjudicate(envelope.get("input"))
        elif envelope.get("entry_point") == "explain_boundary":
            output = explain_boundary(envelope.get("input"))
        else:
            raise EngineError("SCHEMA_INVALID", "Unsupported entry point.")
    except EngineError as exc:
        output = exc.to_dict()
    json.dump(output, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
