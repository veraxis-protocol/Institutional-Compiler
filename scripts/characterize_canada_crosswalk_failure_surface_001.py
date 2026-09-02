#!/usr/bin/env python3
"""Deterministic descriptive characterization of Crosswalk 001 failure surface.

Static mode validates frozen tracked controls only and does not read the preserved
Crosswalk 001 one-shot receipt.

Execution mode, only when separately authorized, reads that preserved receipt
and characterizes the eight already-unresolved fields. It does not reopen real
evidence, Inventory 001, source XML, Markdown, network resources, or unlisted
files. It does not select winners, invent precedence, normalize values, mutate
schemas/evidence, or write SOURCE_MANIFEST.csv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-crosswalk-failure-surface-characterization-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "CHARACTERIZATION-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

CROSSWALK_RESULT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-to-manifest-crosswalk-001/EXECUTION-RESULT-v0.1.json"
)

PRESERVED_RECEIPT = (
    ROOT
    / ".local/evidence-to-manifest-crosswalk-receipts/"
      "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001.json"
)

PLAN_SHA256 = "f149741453324f1cebb3368f9aa0ebe1e8bc10b6503dd894e7d928b6c2ad1b21"
CONTRACT_SHA256 = "b84cdc8d59e189188898903392e45b2e38d8bcb3486d01c5f567ec0e3b46e26c"
PREREG_FREEZE_SHA256 = "da1f31e7c0f89de193e358dd63f456455a514be2b4de7e211c1e47fc56b60d73"
CROSSWALK_RESULT_SHA256 = "c5373e8a0fce35a50f2559c6c0457135fe8776487de49c82c7ee11686161ea67"
PRESERVED_RECEIPT_SHA256 = "77d8a67a71e7eb073fa3f43825a1113a53effd948f69e7abee952e06767dbb92"

DISPOSITION_CHARACTERIZED = "FAILURE_SURFACE_CHARACTERIZED"
DISPOSITION_INCOMPLETE = "FAILURE_SURFACE_INCOMPLETE_FAIL_CLOSED"

ZERO_SURFACE = "ZERO_ADMISSIBLE_VALUE_SURFACE"
CONTRADICTION_SURFACE = "MULTI_ADMISSIBLE_CONTRADICTION_SURFACE"
UNEXPECTED_SURFACE = "UNEXPECTED_SURFACE_FAIL_CLOSED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def raw_value_fingerprint(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def load_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (CROSSWALK_RESULT, CROSSWALK_RESULT_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    result = json.loads(CROSSWALK_RESULT.read_text(encoding="utf-8"))

    if contract["status"] != "FROZEN_NOT_EXECUTED":
        raise SystemExit("FAIL characterization contract status drift")
    if freeze["status"] != "PREREGISTERED_NOT_EXECUTED":
        raise SystemExit("FAIL preregistration status drift")
    if result["status"] != "CLOSED_EXECUTED_CROSSWALK_INCOMPLETE_FAIL_CLOSED":
        raise SystemExit("FAIL Crosswalk 001 closure status drift")

    if contract["crosswalk_001_rerun_authorized"] is not False:
        raise SystemExit("FAIL Crosswalk 001 rerun boundary drift")
    if contract["schema_resolution_authorized"] is not False:
        raise SystemExit("FAIL schema resolution boundary drift")
    if contract["normalization_authorized"] is not False:
        raise SystemExit("FAIL normalization boundary drift")
    if contract["precedence_selection_authorized"] is not False:
        raise SystemExit("FAIL precedence boundary drift")
    if contract["source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest creation boundary drift")
    if contract["source_manifest_population_authorized"] is not False:
        raise SystemExit("FAIL manifest population boundary drift")

    return contract, freeze, result


def _frequency(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _optional_frequency(
    support: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    values: list[str] = []
    for row in support:
        if key not in row:
            continue
        value = row[key]
        if value is None:
            continue
        if not isinstance(value, str):
            value = canonical_json(value)
        values.append(value)
    return _frequency(values)


def _required_string_frequency(
    support: list[dict[str, Any]],
    key: str,
) -> dict[str, int]:
    values: list[str] = []
    for index, row in enumerate(support):
        if key not in row:
            raise ValueError(f"support[{index}] missing {key}")
        value = row[key]
        if value is None:
            value = "<NULL>"
        elif not isinstance(value, str):
            value = canonical_json(value)
        values.append(value)
    return _frequency(values)


def _raw_fingerprint_frequency(
    support: list[dict[str, Any]],
) -> dict[str, int]:
    values: list[str] = []
    for index, row in enumerate(support):
        if "raw_value" not in row:
            raise ValueError(f"support[{index}] missing raw_value")
        values.append(raw_value_fingerprint(row["raw_value"]))
    return _frequency(values)


def classify_surface(
    *,
    prior_state: str,
    admissible_value_count: int,
) -> str:
    if (
        prior_state == "MULTIPLE_CANDIDATES_NOT_ESTABLISHED"
        and admissible_value_count == 0
    ):
        return ZERO_SURFACE

    if (
        prior_state == "CONTRADICTORY_NOT_ESTABLISHED"
        and admissible_value_count > 1
    ):
        return CONTRADICTION_SURFACE

    return UNEXPECTED_SURFACE


def characterize_field_result(
    field_result: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    target = field_result.get("target_field")
    prior_state = field_result.get("state")
    candidate_count = field_result.get("candidate_count")
    admissible_value_count = field_result.get("admissible_value_count")

    findings: list[dict[str, str]] = []

    if prior_state != expected["prior_state"]:
        findings.append({
            "code": "PRIOR_STATE_MISMATCH",
            "message": (
                f"expected {expected['prior_state']!r}, "
                f"observed {prior_state!r}"
            ),
        })

    if candidate_count != expected["candidate_count"]:
        findings.append({
            "code": "CANDIDATE_COUNT_MISMATCH",
            "message": (
                f"expected {expected['candidate_count']}, "
                f"observed {candidate_count!r}"
            ),
        })

    if admissible_value_count != expected["admissible_value_count"]:
        findings.append({
            "code": "ADMISSIBLE_VALUE_COUNT_MISMATCH",
            "message": (
                f"expected {expected['admissible_value_count']}, "
                f"observed {admissible_value_count!r}"
            ),
        })

    support = field_result.get("support")
    if not isinstance(support, list):
        findings.append({
            "code": "SUPPORT_NOT_LIST",
            "message": f"observed support type {type(support).__name__}",
        })
        support = []

    surface_class = classify_surface(
        prior_state=prior_state,
        admissible_value_count=(
            admissible_value_count
            if isinstance(admissible_value_count, int)
            else -1
        ),
    )

    if surface_class == UNEXPECTED_SURFACE:
        findings.append({
            "code": "UNEXPECTED_SURFACE_CLASS",
            "message": (
                f"state={prior_state!r}, "
                f"admissible_value_count={admissible_value_count!r}"
            ),
        })

    try:
        candidate_key_frequency = _required_string_frequency(
            support, "key"
        )
        artifact_path_frequency = _required_string_frequency(
            support, "artifact_path"
        )
        source_scope_pointer_frequency = _required_string_frequency(
            support, "source_scope_pointer"
        )
        raw_fingerprint_frequency = _raw_fingerprint_frequency(support)
        mapped_value_frequency = _optional_frequency(
            support, "mapped_value"
        )
        mapping_class_frequency = _optional_frequency(
            support, "mapping_class"
        )
        transformation_frequency = _optional_frequency(
            support, "transformation"
        )
    except (TypeError, ValueError) as exc:
        findings.append({
            "code": "SUPPORT_PROFILE_FAILURE",
            "message": f"{type(exc).__name__}: {exc}",
        })
        candidate_key_frequency = {}
        artifact_path_frequency = {}
        source_scope_pointer_frequency = {}
        raw_fingerprint_frequency = {}
        mapped_value_frequency = {}
        mapping_class_frequency = {}
        transformation_frequency = {}

    profile_complete = not findings

    return {
        "target_field": target,
        "prior_state": prior_state,
        "candidate_count": candidate_count,
        "admissible_value_count": admissible_value_count,
        "surface_class": surface_class,
        "support_record_count": len(support),

        "distinct_candidate_key_count":
            len(candidate_key_frequency),
        "candidate_key_frequency":
            candidate_key_frequency,

        "distinct_artifact_path_count":
            len(artifact_path_frequency),
        "artifact_path_frequency":
            artifact_path_frequency,

        "distinct_source_scope_pointer_count":
            len(source_scope_pointer_frequency),
        "source_scope_pointer_frequency":
            source_scope_pointer_frequency,

        "distinct_raw_value_fingerprint_count":
            len(raw_fingerprint_frequency),
        "raw_value_fingerprint_frequency":
            raw_fingerprint_frequency,

        "distinct_mapped_value_count":
            len(mapped_value_frequency),
        "mapped_value_frequency":
            mapped_value_frequency,

        "mapping_class_frequency":
            mapping_class_frequency,
        "transformation_frequency":
            transformation_frequency,

        "winner_selected":
            False,
        "precedence_assigned":
            False,
        "normalization_performed":
            False,
        "new_mapping_derived":
            False,

        "profile_complete":
            profile_complete,
        "findings":
            findings,
    }


def characterize_receipt(
    receipt: dict[str, Any],
    *,
    contract: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    if receipt.get("work_order") != (
        "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001"
    ):
        findings.append({
            "code": "WRONG_WORK_ORDER",
            "message": repr(receipt.get("work_order")),
        })

    if receipt.get("status") != "EXECUTED_READ_ONLY":
        findings.append({
            "code": "WRONG_RECEIPT_STATUS",
            "message": repr(receipt.get("status")),
        })

    if receipt.get("disposition") != "CROSSWALK_INCOMPLETE_FAIL_CLOSED":
        findings.append({
            "code": "WRONG_CROSSWALK_DISPOSITION",
            "message": repr(receipt.get("disposition")),
        })

    if receipt.get("target_field_count") != 12:
        findings.append({
            "code": "TARGET_FIELD_COUNT_MISMATCH",
            "message": repr(receipt.get("target_field_count")),
        })

    if receipt.get("established_field_count") != 4:
        findings.append({
            "code": "ESTABLISHED_FIELD_COUNT_MISMATCH",
            "message": repr(receipt.get("established_field_count")),
        })

    rows = receipt.get("field_results")
    if not isinstance(rows, list):
        findings.append({
            "code": "FIELD_RESULTS_NOT_LIST",
            "message": type(rows).__name__,
        })
        rows = []

    by_field: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            findings.append({
                "code": "FIELD_RESULT_NOT_OBJECT",
                "message": type(row).__name__,
            })
            continue
        name = row.get("target_field")
        if not isinstance(name, str):
            findings.append({
                "code": "FIELD_RESULT_TARGET_INVALID",
                "message": repr(name),
            })
            continue
        if name in by_field:
            duplicates.add(name)
        by_field[name] = row

    for name in sorted(duplicates):
        findings.append({
            "code": "DUPLICATE_FIELD_RESULT",
            "message": name,
        })

    profiles: list[dict[str, Any]] = []

    for field in contract["characterization_algorithm"]["fields"]:
        expected = contract["unresolved_fields"][field]
        row = by_field.get(field)

        if row is None:
            findings.append({
                "code": "UNRESOLVED_FIELD_MISSING",
                "message": field,
            })
            continue

        profile = characterize_field_result(row, expected)
        profiles.append(profile)

        for item in profile["findings"]:
            findings.append({
                "code": item["code"],
                "message": f"{field}: {item['message']}",
            })

    expected_fields = set(contract["characterization_algorithm"]["fields"])
    observed_profile_fields = {
        profile["target_field"] for profile in profiles
    }

    complete = (
        not findings
        and len(profiles) == 8
        and observed_profile_fields == expected_fields
        and all(profile["profile_complete"] for profile in profiles)
    )

    surface_counts = Counter(
        profile["surface_class"] for profile in profiles
    )

    return {
        "work_order":
            "OIC-CANADA-CROSSWALK-FAILURE-SURFACE-CHARACTERIZATION-001",
        "status":
            "EXECUTED_READ_ONLY",
        "disposition":
            (
                DISPOSITION_CHARACTERIZED
                if complete
                else DISPOSITION_INCOMPLETE
            ),
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
        },
        "unresolved_field_expected_count":
            8,
        "unresolved_field_profile_count":
            len(profiles),
        "profiles":
            profiles,
        "surface_class_counts":
            dict(sorted(surface_counts.items())),
        "finding_count":
            len(findings),
        "findings":
            findings,

        "winner_selection_performed":
            False,
        "precedence_assignment_performed":
            False,
        "normalization_performed":
            False,
        "schema_mutation_performed":
            False,
        "evidence_rewrite_performed":
            False,
        "candidate_key_expansion_performed":
            False,
        "new_semantic_mapping_performed":
            False,

        "causal_root_cause":
            "NOT_ESTABLISHED",
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

        "real_evidence_reread":
            False,
        "inventory_receipt_inspected":
            False,
        "source_xml_inspected":
            False,
        "corroborating_markdown_inspected":
            False,
        "network_used":
            False,
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

        "claim_ceiling": (
            "Descriptive failure-surface characterization only. It does not "
            "establish causal root cause, a correct precedence rule, a correct "
            "normalization, legal rights, provenance truth, evidence "
            "sufficiency, or authority to mutate evidence/schema or populate "
            "SOURCE_MANIFEST.csv."
        ),
    }


def execute_read_only() -> dict[str, Any]:
    contract, _freeze, _result = load_controls()

    if sha256(PRESERVED_RECEIPT) != PRESERVED_RECEIPT_SHA256:
        raise SystemExit("FAIL preserved Crosswalk 001 receipt digest mismatch")

    receipt = json.loads(
        PRESERVED_RECEIPT.read_text(encoding="utf-8")
    )

    return characterize_receipt(
        receipt,
        contract=contract,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        load_controls()
        print("static preflight: PASS")
        print("preserved Crosswalk 001 receipt content read: ZERO")
        print("real evidence reread: ZERO")
        print("normalization/precedence design performed: FALSE")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_read_only()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(
            "profiles: "
            f"{result['unresolved_field_profile_count']}/"
            f"{result['unresolved_field_expected_count']}"
        )
        print(f"findings: {result['finding_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
