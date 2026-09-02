#!/usr/bin/env python3
"""Deterministic evidence-bundle materializer for Canada CA-3.

Static mode validates tracked frozen controls only and never opens the preserved
Crosswalk 001 receipt.

Execution mode is one-shot and must be separately authorized by an external
STARTED lock. It reads only the preserved Crosswalk 001 receipt, extracts exact
non-null mapped_value strings for rights_evidence and provenance_evidence,
deduplicates by exact string identity, sorts only for deterministic
serialization, and writes candidate bundle bytes only under .local/.

It never reads underlying evidence, dereferences evidence references, infers
semantic values, assigns precedence, establishes legal sufficiency, touches the
six declaration fields, changes the manifest contract, or writes
SOURCE_MANIFEST.csv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-bundle-materialization-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "BUNDLE-MATERIALIZATION-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

CANDIDATE_RESULT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-manifest-resolution-candidate-002/EXECUTION-RESULT-v0.1.json"
)

CANDIDATE_ADJ = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-manifest-resolution-candidate-002/POST-RUN-ADJUDICATION.md"
)

PRESERVED_RECEIPT = (
    ROOT
    / ".local/evidence-to-manifest-crosswalk-receipts/"
      "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001.json"
)

PLAN_SHA256 = "bf5984554eee59f700fb44fe1e3167ee54ad19680f0c66b4bc2127f5eabc1f72"
CONTRACT_SHA256 = "72c387ba7d46d235432ce5fb8e41debd303c952064d808ae66c7521715a2aa07"
PREREG_FREEZE_SHA256 = "8d714e990d03aea74be6cb975465e4cc2f30b49c7768901915774f30f485a7cf"
CANDIDATE_RESULT_SHA256 = "64c4e39f74e10072dcf6bb360bb8c6edc568a723d2b7d2041dd4208206161a0c"
CANDIDATE_ADJ_SHA256 = "39e75832402bd14cfcb4976a9ee10aab9ff24632517ba333062c2ff916bd167a"
PRESERVED_RECEIPT_SHA256 = "77d8a67a71e7eb073fa3f43825a1113a53effd948f69e7abee952e06767dbb92"

WORK_ORDER = "OIC-CANADA-EVIDENCE-BUNDLE-MATERIALIZATION-001"
SOURCE_WORK_ORDER = "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001"

PASS = "EVIDENCE_BUNDLES_MATERIALIZED_CA3"
FAIL = "EVIDENCE_BUNDLE_MATERIALIZATION_INCOMPLETE_FAIL_CLOSED"

TARGETS = {
    "rights_evidence": 4,
    "provenance_evidence": 3,
}

BUNDLE_VERSION = "oic-evidence-bundle-0.1"
ORDERING = "LEXICOGRAPHIC_SERIALIZATION_ONLY_NO_AUTHORITY"

TRACKED_PATHS = {
    "rights_evidence": (
        "benchmarks/preflight/corpus-rights-provenance-001/"
        "evidence-bundles/CA-3/rights_evidence-bundle-v0.1.json"
    ),
    "provenance_evidence": (
        "benchmarks/preflight/corpus-rights-provenance-001/"
        "evidence-bundles/CA-3/provenance_evidence-bundle-v0.1.json"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def load_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load tracked controls only. Never touches PRESERVED_RECEIPT."""
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (CANDIDATE_RESULT, CANDIDATE_RESULT_SHA256),
        (CANDIDATE_ADJ, CANDIDATE_ADJ_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_RESULT.read_text(encoding="utf-8"))

    if contract["status"] != "FROZEN_NOT_EXECUTED":
        raise SystemExit("FAIL materialization contract status drift")
    if freeze["status"] != "PREREGISTERED_NOT_EXECUTED":
        raise SystemExit("FAIL preregistration freeze status drift")
    if candidate["status"] != (
        "CLOSED_EXECUTED_CANDIDATE_STRUCTURALLY_FEASIBLE_CA3"
    ):
        raise SystemExit("FAIL Candidate 002 closure status drift")

    if contract["declaration_fields_in_scope"] != []:
        raise SystemExit("FAIL declaration-field scope drift")
    if contract["candidate_002_adoption_authorized"] is not False:
        raise SystemExit("FAIL candidate adoption boundary drift")
    if contract["source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest creation boundary drift")
    if contract["source_manifest_population_authorized"] is not False:
        raise SystemExit("FAIL manifest population boundary drift")

    return contract, freeze, candidate


def _field_rows(receipt: dict[str, Any], target: str) -> list[dict[str, Any]]:
    rows = receipt.get("field_results")
    if not isinstance(rows, list):
        raise ValueError("field_results must be a list")

    matches: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"field_results[{index}] must be an object")
        if row.get("target_field") == target:
            matches.append(row)
    return matches


def extract_exact_mapped_references(
    receipt: dict[str, Any],
    *,
    target: str,
    expected_count: int,
) -> tuple[list[str], list[str]]:
    findings: list[str] = []

    matches = _field_rows(receipt, target)
    if len(matches) != 1:
        return [], [
            f"{target}: expected exactly one field result, observed {len(matches)}"
        ]

    row = matches[0]

    if row.get("state") != "CONTRADICTORY_NOT_ESTABLISHED":
        findings.append(
            f"{target}: state mismatch {row.get('state')!r}"
        )

    if row.get("admissible_value_count") != expected_count:
        findings.append(
            f"{target}: admissible_value_count mismatch "
            f"{row.get('admissible_value_count')!r} != {expected_count}"
        )

    support = row.get("support")
    if not isinstance(support, list):
        findings.append(f"{target}: support is not a list")
        return [], findings

    values: list[str] = []

    for index, support_row in enumerate(support):
        if not isinstance(support_row, dict):
            findings.append(
                f"{target}: support[{index}] is not an object"
            )
            continue

        if "mapped_value" not in support_row:
            continue

        mapped = support_row["mapped_value"]
        if mapped is None:
            continue

        if not isinstance(mapped, str):
            findings.append(
                f"{target}: support[{index}].mapped_value is not a string"
            )
            continue

        values.append(mapped)

    exact = sorted(set(values))

    if len(exact) != expected_count:
        findings.append(
            f"{target}: exact distinct mapped_value count "
            f"{len(exact)} != {expected_count}"
        )

    return exact, findings


def build_bundle(
    *,
    target: str,
    references: Sequence[str],
    source_receipt_sha256: str,
) -> dict[str, Any]:
    if target not in TARGETS:
        raise ValueError(f"unsupported target: {target}")

    if len(references) != TARGETS[target]:
        raise ValueError(
            f"{target}: reference count {len(references)} "
            f"!= {TARGETS[target]}"
        )

    if len(set(references)) != len(references):
        raise ValueError(f"{target}: duplicate references supplied")

    if any(not isinstance(value, str) for value in references):
        raise ValueError(f"{target}: all references must be strings")

    refs = sorted(references)

    return {
        "bundle_version":
            BUNDLE_VERSION,
        "source_id":
            "CA-3",
        "target_field":
            target,
        "source_crosswalk_receipt_sha256":
            source_receipt_sha256,
        "ordering_semantics":
            ORDERING,
        "evidence_references":
            refs,
        "reference_count":
            len(refs),
        "legal_sufficiency_established":
            False,
        "evidentiary_priority_established":
            False,
        "underlying_evidence_rewritten":
            False,
    }


def _validate_local_output_dir(output_dir: Path) -> Path:
    root_local = (ROOT / ".local").resolve()
    resolved = output_dir.resolve()

    try:
        resolved.relative_to(root_local)
    except ValueError as exc:
        raise ValueError(
            "execution output directory must be inside repository .local/"
        ) from exc

    return resolved


def materialize_receipt(
    receipt: dict[str, Any],
    *,
    source_receipt_sha256: str,
) -> dict[str, Any]:
    findings: list[str] = []

    if receipt.get("work_order") != SOURCE_WORK_ORDER:
        findings.append(
            f"wrong source work_order: {receipt.get('work_order')!r}"
        )

    if receipt.get("status") != "EXECUTED_READ_ONLY":
        findings.append(
            f"wrong source status: {receipt.get('status')!r}"
        )

    if receipt.get("disposition") != "CROSSWALK_INCOMPLETE_FAIL_CLOSED":
        findings.append(
            f"wrong source disposition: {receipt.get('disposition')!r}"
        )

    if receipt.get("target_field_count") != 12:
        findings.append(
            f"wrong target_field_count: {receipt.get('target_field_count')!r}"
        )

    bundles: dict[str, dict[str, Any]] = {}
    field_observations: dict[str, dict[str, Any]] = {}

    for target, expected_count in TARGETS.items():
        refs, field_findings = extract_exact_mapped_references(
            receipt,
            target=target,
            expected_count=expected_count,
        )

        findings.extend(field_findings)

        if not field_findings:
            bundle = build_bundle(
                target=target,
                references=refs,
                source_receipt_sha256=source_receipt_sha256,
            )
            bundles[target] = bundle

            field_observations[target] = {
                "expected_reference_count":
                    expected_count,
                "observed_reference_count":
                    len(refs),
                "exact_reference_set_preserved":
                    True,
                "bundle_sha256":
                    hashlib.sha256(canonical_json_bytes(bundle)).hexdigest(),
                "tracked_destination_path":
                    TRACKED_PATHS[target],
                "precedence_assigned":
                    False,
                "legal_sufficiency_established":
                    False,
                "evidentiary_priority_established":
                    False,
            }
        else:
            field_observations[target] = {
                "expected_reference_count":
                    expected_count,
                "observed_reference_count":
                    len(refs),
                "exact_reference_set_preserved":
                    False,
                "bundle_sha256":
                    None,
                "tracked_destination_path":
                    TRACKED_PATHS[target],
                "precedence_assigned":
                    False,
                "legal_sufficiency_established":
                    False,
                "evidentiary_priority_established":
                    False,
            }

    complete = not findings and set(bundles) == set(TARGETS)

    return {
        "work_order":
            WORK_ORDER,
        "status":
            "EXECUTED_LOCAL_ONLY",
        "disposition":
            PASS if complete else FAIL,
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
        },
        "source_crosswalk_receipt_sha256":
            source_receipt_sha256,
        "target_field_count":
            2,
        "field_observations":
            field_observations,
        "bundle_candidates":
            bundles,
        "bundle_candidate_count":
            len(bundles),
        "finding_count":
            len(findings),
        "findings":
            findings,
        "declaration_fields_touched":
            [],
        "candidate_002_adopted":
            False,
        "precedence_assigned":
            False,
        "legal_sufficiency_established":
            False,
        "evidentiary_priority_established":
            False,
        "underlying_evidence_rewritten":
            False,
        "real_underlying_evidence_reread":
            False,
        "tracked_bundle_files_created":
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
    }


def write_local_bundle_candidates(
    result: dict[str, Any],
    *,
    output_dir: Path,
) -> dict[str, str]:
    if result["disposition"] != PASS:
        raise ValueError("cannot write bundle candidates from failed result")

    resolved = _validate_local_output_dir(output_dir)
    resolved.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, str] = {}

    for target in sorted(TARGETS):
        bundle = result["bundle_candidates"][target]
        path = resolved / f"{target}-bundle-v0.1.json"
        path.write_bytes(canonical_json_bytes(bundle))
        outputs[target] = str(path.relative_to(ROOT))

    return outputs


def execute_one_shot(*, output_dir: Path) -> dict[str, Any]:
    contract, _freeze, _candidate = load_controls()

    if contract["future_input_scope"]["preserved_crosswalk_001_receipt"] != (
        "ALLOWED_AFTER_INDEPENDENT_VERIFICATION_AND_STATIC_FREEZE"
    ):
        raise SystemExit("FAIL preserved receipt execution scope drift")

    # This is the only content read of the preserved Crosswalk receipt.
    if sha256(PRESERVED_RECEIPT) != PRESERVED_RECEIPT_SHA256:
        raise SystemExit("FAIL preserved Crosswalk receipt digest mismatch")

    receipt = json.loads(PRESERVED_RECEIPT.read_text(encoding="utf-8"))

    result = materialize_receipt(
        receipt,
        source_receipt_sha256=PRESERVED_RECEIPT_SHA256,
    )

    if result["disposition"] == PASS:
        outputs = write_local_bundle_candidates(
            result,
            output_dir=output_dir,
        )
    else:
        outputs = {}

    result["local_bundle_candidate_paths"] = outputs
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        load_controls()
        print("static preflight: PASS")
        print("preserved Crosswalk 001 receipt content read: ZERO")
        print("real underlying evidence read: ZERO")
        print("real bundle materialization: ZERO")
        print("declaration fields touched: ZERO")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    if args.output_dir is None:
        parser.error("--output-dir is required with --execute-read-only")

    result = execute_one_shot(output_dir=args.output_dir)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(f"findings: {result['finding_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
