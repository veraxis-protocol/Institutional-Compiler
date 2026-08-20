#!/usr/bin/env python3
"""RESULT-002 exact semantic comparator.

Reads only persisted evidence output and a frozen oracle. It performs no
institutional interpretation and has no tolerance rules. Any mismatch fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:  # noqa: ANN401 - the candidate's signature is
    # pinned; a noqa keeps the module AST-identical to the authoritative bytes,
    # where a changed annotation would not.
    return json.loads(path.read_text(encoding="utf-8"))


def compare(manifest: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    fields = list(oracle["comparison_fields"])
    expected_cases = dict(oracle["cases"])
    observed_cases = dict(manifest.get("cases", {}))
    mismatches: list[dict[str, Any]] = []

    expected_ids = set(expected_cases)
    observed_ids = set(observed_cases)
    for missing in sorted(expected_ids - observed_ids):
        mismatches.append({"case_id": missing, "kind": "MISSING_CASE"})
    for extra in sorted(observed_ids - expected_ids):
        mismatches.append({"case_id": extra, "kind": "EXTRA_CASE"})

    for case_id in sorted(expected_ids & observed_ids):
        expected = expected_cases[case_id]
        projection = observed_cases[case_id].get("semantic_projection")
        if not isinstance(projection, dict):
            mismatches.append({"case_id": case_id, "kind": "MISSING_SEMANTIC_PROJECTION"})
            continue
        for field in fields:
            if field not in projection:
                mismatches.append({"case_id": case_id, "field": field, "kind": "MISSING_FIELD"})
                continue
            observed = projection[field]
            wanted = expected[field]
            if observed != wanted:
                mismatches.append(
                    {
                        "case_id": case_id,
                        "field": field,
                        "kind": "VALUE_MISMATCH",
                        "expected": wanted,
                        "observed": observed,
                    }
                )

    observed_projection = {
        case_id: {
            field: observed_cases[case_id].get("semantic_projection", {}).get(field, "__MISSING__")
            for field in fields
        }
        for case_id in sorted(expected_ids & observed_ids)
    }
    expected_projection = {
        case_id: {field: expected_cases[case_id][field] for field in fields}
        for case_id in sorted(expected_cases)
    }
    return {
        "record_class": "RESULT_002_SEMANTIC_COMPARISON",
        "result_id": oracle.get("result_id", "RESULT-002"),
        "oracle_id": oracle["oracle_id"],
        "comparison_fields": fields,
        "expected_case_ids": sorted(expected_ids),
        "observed_case_ids": sorted(observed_ids),
        "expected_projection_sha256": sha256_bytes(canonical_bytes(expected_projection)),
        "observed_projection_sha256": sha256_bytes(canonical_bytes(observed_projection)),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "decision": "PASS" if not mismatches else "FAIL",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence-root", required=True, type=Path)
    p.add_argument("--oracle", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    manifest_path = args.evidence_root / "05-evidence" / "MANIFEST.json"
    try:
        manifest = load_json(manifest_path)
        oracle = load_json(args.oracle)
        report = compare(manifest, oracle)
    except Exception as exc:  # fail closed; emit a machine-readable refusal
        report = {
            "record_class": "RESULT_002_SEMANTIC_COMPARISON",
            "result_id": "RESULT-002",
            "decision": "FAIL",
            "mismatch_count": 1,
            "mismatches": [{"kind": "COMPARATOR_ERROR", "detail": f"{type(exc).__name__}: {exc}"}],
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0 if report.get("decision") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
