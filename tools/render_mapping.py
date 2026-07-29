#!/usr/bin/env python3
"""Render the human-readable mapping table from the canonical JSON mapping.

``docs/contracts/ZTL-OCE-MAPPING-v0.1.json`` is the canonical artifact. This script
regenerates the table inside ``docs/contracts/ZTL-OCE-MAPPING-v0.1.md`` from it, so the
two cannot drift. ``tests/contract/test_warrant_contract.py`` re-renders in memory and
fails if the checked-in Markdown differs.

Usage::

    python tools/render_mapping.py            # rewrite the Markdown table in place
    python tools/render_mapping.py --check    # exit 1 if the Markdown is out of date

Only the block between the START and END markers is touched; the surrounding prose is
hand-written and left alone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MAPPING_JSON = Path("docs/contracts/ZTL-OCE-MAPPING-v0.1.json")
MAPPING_MD = Path("docs/contracts/ZTL-OCE-MAPPING-v0.1.md")
START = "<!-- MAPPING-TABLE-START -->"
END = "<!-- MAPPING-TABLE-END -->"

COLUMNS = (
    "#",
    "Disposition",
    "Grade",
    "Unverified",
    "OIC condition",
    "Prec",
    "Epistemic",
    "Execution",
    "Basis",
    "Reason",
    "Reachability",
    "Authority",
)


def render_table(document: dict[str, object]) -> str:
    rows = document["rows"]
    if not isinstance(rows, list):
        raise TypeError("mapping document has no 'rows' array")
    lines = [
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join(["---"] * len(COLUMNS)) + "|",
    ]
    for row in sorted(rows, key=lambda item: int(item["row_id"])):
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["row_id"]),
                    str(row["disposition"]),
                    str(row["grade"]),
                    str(row["unverified"]),
                    str(row["oic_condition"]),
                    str(row["precedence"]),
                    str(row["epistemic_status"]),
                    " / ".join(row["execution_disposition_choices"]),
                    str(row["decision_basis"]),
                    str(row["primary_reason_code"]),
                    str(row["reachability"]),
                    str(row["authority"]),
                )
            )
            + " |"
        )
    return "\n".join(lines)


def rendered_markdown(root: Path) -> str:
    document = json.loads((root / MAPPING_JSON).read_text(encoding="utf-8"))
    text = (root / MAPPING_MD).read_text(encoding="utf-8")
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n\n{render_table(document)}\n\n{END}{tail}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    expected = rendered_markdown(args.root)
    target = args.root / MAPPING_MD
    if args.check:
        if target.read_text(encoding="utf-8") != expected:
            print("ZTL-OCE-MAPPING-v0.1.md is out of date; run tools/render_mapping.py")
            return 1
        print("mapping Markdown matches the canonical JSON")
        return 0
    target.write_text(expected, encoding="utf-8")
    print(f"rendered {MAPPING_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
