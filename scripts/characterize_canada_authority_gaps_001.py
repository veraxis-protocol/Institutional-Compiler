#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-authority-gap-characterization-001"
)
CONTRACT = BENCH / "GAP-CHARACTERIZATION-CONTRACT-v0.1.json"
SOURCE_RESULT = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-manifest-declaration-authority-discrimination-001/"
    "EXECUTION-RESULT-v0.1.json"
)

CONTRACT_SHA256 = "a786194125497d82c74c3aa50fb01acc26d044a6139a2963abf5ed24cb60eec6"
SOURCE_RESULT_SHA256 = "3ba392b85f937bcdfc4eb603b62448e4013bc7c91aa73bb4f5608b1c0c82c3b0"

EXPECTED_FIELDS = frozenset({
    "source_kind",
    "source_locator",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
})

EXPECTED_ASSESSMENT = "CHANNEL_NOT_ESTABLISHED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract() -> dict[str, Any]:
    if sha256(CONTRACT) != CONTRACT_SHA256:
        raise SystemExit("FAIL: gap contract digest mismatch")
    c = load_json(CONTRACT)
    assert c["status"] == "FROZEN_ANALYSIS_NOT_EXECUTED"
    assert c["population"]["target_field_count"] == 6
    assert c["population"]["failed_channel_count"] == 16
    assert len(c["dimension_to_action_class"]) == 11
    return c


def verify_real_source_bytes_only() -> None:
    if sha256(SOURCE_RESULT) != SOURCE_RESULT_SHA256:
        raise SystemExit("FAIL: closed authority result digest mismatch")


def validate_closed_result(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    if doc.get("status") != "CLOSED_EXECUTED_AUTHORITY_NOT_ESTABLISHED_CA3":
        raise ValueError("unexpected source status")
    if doc.get("disposition") != "AUTHORITY_SURFACE_DISCRIMINATED_CA3":
        raise ValueError("unexpected source disposition")
    if doc.get("substantive_outcome") != "ALL_FROZEN_CHANNELS_NOT_ESTABLISHED":
        raise ValueError("unexpected substantive outcome")
    if doc.get("target_field_count") != 6:
        raise ValueError("target field count drift")
    if doc.get("channel_count_evaluated") != 16:
        raise ValueError("channel count drift")
    if doc.get("finding_count") != 0:
        raise ValueError("source findings not zero")
    if doc.get("passing_channel_count") != 0:
        raise ValueError("passing channel count not zero")

    rows = doc.get("channel_evaluations")
    if not isinstance(rows, list) or len(rows) != 16:
        raise ValueError("expected exactly 16 channel evaluations")

    seen_ids: set[str] = set()
    fields: set[str] = set()

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("channel row must be object")
        channel_id = row.get("channel_id")
        channel_type = row.get("channel_type")
        field = row.get("target_field")
        missing = row.get("missing_dimensions")

        if not isinstance(channel_id, str) or not channel_id:
            raise ValueError("invalid channel_id")
        if channel_id in seen_ids:
            raise ValueError(f"duplicate channel_id: {channel_id}")
        seen_ids.add(channel_id)

        if not isinstance(channel_type, str) or not channel_type:
            raise ValueError(f"invalid channel_type for {channel_id}")
        if field not in EXPECTED_FIELDS:
            raise ValueError(f"invalid target_field for {channel_id}")
        fields.add(field)

        if row.get("assessment") != EXPECTED_ASSESSMENT:
            raise ValueError(f"unexpected assessment for {channel_id}")
        if row.get("standing_established") is not False:
            raise ValueError(f"standing unexpectedly established for {channel_id}")

        if not isinstance(missing, list) or not missing:
            raise ValueError(f"missing_dimensions absent for {channel_id}")
        if any(not isinstance(x, str) or not x for x in missing):
            raise ValueError(f"invalid missing dimension for {channel_id}")
        if len(set(missing)) != len(missing):
            raise ValueError(f"duplicate missing dimension for {channel_id}")

        if row.get("declaration_value_created") is not False:
            raise ValueError(f"declaration value created for {channel_id}")
        if row.get("authority_act_created_by_evaluator") is not False:
            raise ValueError(f"evaluator created authority act for {channel_id}")
        if row.get("new_derivation_rule_created") is not False:
            raise ValueError(f"new derivation rule created for {channel_id}")

        out.append(dict(row))

    if fields != EXPECTED_FIELDS:
        raise ValueError(f"field population drift: {sorted(fields)}")

    return out


def characterize(
    doc: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    rows = validate_closed_result(doc)

    action_map = contract["dimension_to_action_class"]
    allowed_dims = set(action_map)

    overall = collections.Counter()
    by_field: dict[str, collections.Counter[str]] = {
        field: collections.Counter() for field in EXPECTED_FIELDS
    }
    by_type: dict[str, collections.Counter[str]] = {}
    action_overall = collections.Counter()
    action_by_field: dict[str, collections.Counter[str]] = {
        field: collections.Counter() for field in EXPECTED_FIELDS
    }

    channel_gaps: list[dict[str, Any]] = []
    findings: list[str] = []

    for row in rows:
        channel_id = row["channel_id"]
        field = row["target_field"]
        channel_type = row["channel_type"]
        missing = sorted(row["missing_dimensions"])

        unknown = sorted(set(missing) - allowed_dims)
        if unknown:
            findings.append(
                f"{channel_id}: unmapped missing_dimensions: {','.join(unknown)}"
            )
            continue

        gap_actions = sorted(action_map[d] for d in missing)

        overall.update(missing)
        by_field[field].update(missing)
        by_type.setdefault(channel_type, collections.Counter()).update(missing)
        action_overall.update(gap_actions)
        action_by_field[field].update(gap_actions)

        channel_gaps.append({
            "target_field": field,
            "channel_id": channel_id,
            "channel_type": channel_type,
            "missing_dimensions": missing,
            "gap_signature": "|".join(missing),
            "gap_cardinality": len(missing),
            "implied_action_classes": gap_actions,
            "descriptive_only": True,
            "preferred_channel": False,
            "authorized_channel": False,
        })

    lowest_by_field: dict[str, Any] = {}
    for field in sorted(EXPECTED_FIELDS):
        field_rows = [r for r in channel_gaps if r["target_field"] == field]
        if not field_rows:
            findings.append(f"{field}: no channel gaps characterized")
            continue
        minimum = min(r["gap_cardinality"] for r in field_rows)
        tied = sorted(
            r["channel_id"]
            for r in field_rows
            if r["gap_cardinality"] == minimum
        )
        lowest_by_field[field] = {
            "lowest_observed_gap_cardinality": minimum,
            "channel_ids_at_lowest_cardinality": tied,
            "channel_count_at_lowest_cardinality": len(tied),
            "descriptive_only": True,
            "selection_or_preference_implied": False,
        }

    complete = (
        len(channel_gaps) == 16
        and len(lowest_by_field) == 6
        and not findings
    )

    return {
        "work_order": "OIC-CANADA-AUTHORITY-GAP-CHARACTERIZATION-001",
        "status": "EXECUTED_DETERMINISTIC_CLOSED_RESULT_ANALYSIS",
        "disposition": (
            "AUTHORITY_GAPS_CHARACTERIZED_CA3"
            if complete
            else "AUTHORITY_GAP_CHARACTERIZATION_INCOMPLETE_FAIL_CLOSED"
        ),
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
            "target_field_count": 6,
            "failed_channel_count": 16,
        },
        "source_authority_discrimination_result_sha256":
            SOURCE_RESULT_SHA256,
        "channel_gap_count": len(channel_gaps),
        "finding_count": len(findings),
        "findings": findings,
        "channel_gaps": sorted(
            channel_gaps,
            key=lambda r: (r["target_field"], r["channel_id"]),
        ),
        "missing_dimension_frequency_overall":
            dict(sorted(overall.items())),
        "missing_dimension_frequency_per_field": {
            field: dict(sorted(counter.items()))
            for field, counter in sorted(by_field.items())
        },
        "missing_dimension_frequency_per_channel_type": {
            kind: dict(sorted(counter.items()))
            for kind, counter in sorted(by_type.items())
        },
        "action_class_frequency_overall":
            dict(sorted(action_overall.items())),
        "action_class_frequency_per_field": {
            field: dict(sorted(counter.items()))
            for field, counter in sorted(action_by_field.items())
        },
        "lowest_observed_gap_cardinality_per_field":
            lowest_by_field,
        "frequency_is_priority":
            False,
        "lowest_gap_implies_preference":
            False,
        "authority_established":
            False,
        "declaration_values_created":
            False,
        "authority_channel_selected":
            False,
        "new_derivation_rule_created":
            False,
        "candidate_002_adopted":
            False,
        "source_manifest_created":
            False,
        "source_manifest_population_authorized":
            False,
        "rights_established":
            False,
        "provenance_established":
            False,
        "legal_clearance_established":
            False,
        "causal_root_cause":
            "NOT_ESTABLISHED",
        "cross_source_generality_established":
            False,
        "held_out_validation_required_for_generalization":
            True,
        "provider_model_network_calls":
            0,
        "ontology_007r1_execution_authorized":
            False,
        "q011_creation_authorized":
            False,
        "canonicalization_authorized":
            False,
        "institutional_ir_authorized":
            False,
        "control_envelope_authorized":
            False,
        "rego_compilation_authorized":
            False,
        "runtime_evaluation_authorized":
            False,
        "deterministic_replay_authorized":
            True,
        "claim_ceiling": contract["claim_ceiling"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--verify-source-bytes", action="store_true")
    args = parser.parse_args(argv)

    contract = load_contract()

    if args.verify_source_bytes:
        verify_real_source_bytes_only()
        print("closed authority result bytes: HASH-VERIFIED ONLY")
        print("real gap analysis executed: FALSE")
        return 0

    if not args.execute:
        print("gap characterizer static preflight: PASS")
        print("real closed-result semantics analyzed: FALSE")
        print("authority established: FALSE")
        print("declaration values created: FALSE")
        return 0

    if not args.output:
        raise SystemExit("FAIL: --output required with --execute")

    verify_real_source_bytes_only()
    source = load_json(SOURCE_RESULT)
    result = characterize(source, contract)

    output = Path(args.output)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("disposition:", result["disposition"])
    print("channel gaps:", result["channel_gap_count"])
    print("findings:", result["finding_count"])
    for field, row in sorted(
        result["lowest_observed_gap_cardinality_per_field"].items()
    ):
        ids = ",".join(row["channel_ids_at_lowest_cardinality"])
        print(
            f"{field}: lowest_gap={row['lowest_observed_gap_cardinality']} "
            f"channels={ids}"
        )
    print("frequency implies priority: FALSE")
    print("lowest gap implies preference: FALSE")
    print("declaration values created: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
