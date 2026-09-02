#!/usr/bin/env python3
"""Structural evaluator for Canada Manifest Resolution Candidate 002.

Static mode validates frozen tracked controls only.

Execution mode, when separately authorized, evaluates bounded structural
representability using only tracked frozen artifacts. It never reads the local
Crosswalk receipt or real evidence; it never chooses declaration values, creates
real evidence bundles, changes the manifest contract, or writes
SOURCE_MANIFEST.csv.

The evidence-bundle check is representational only: synthetic fixtures prove
that a scalar repository-relative manifest reference can point to a
deterministically serialized tracked bundle that preserves an evidence set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-manifest-resolution-candidate-002"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "CANDIDATE-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

HYP_RESULT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-manifest-resolution-hypotheses-001/EXECUTION-RESULT-v0.1.json"
)

SURFACE_RESULT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-crosswalk-failure-surface-characterization-001/"
      "EXECUTION-RESULT-v0.1.json"
)

MANIFEST_CONTRACT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "SOURCE-MANIFEST-CONTRACT-v0.1.json"
)

PLAN_SHA256 = "bc7e72b66517363c35788190586d4306f1369a5062856e0941acddf95d756178"
CONTRACT_SHA256 = "778f0a3501cd170f2cad222a828e4b1179667a1b6a2c86ca08876bd575cb470b"
PREREG_FREEZE_SHA256 = "39f8f01fbd13b6ce36e45ff028336d036d19739ed04eb1e03cbe1b613f54e22b"
HYP_RESULT_SHA256 = "3159feb0de49253c43a318d8d1b84f2f11d19f3e74620b73d3158e6ff29186d7"
SURFACE_RESULT_SHA256 = "b29831c5685f238492826db3f0f737a125f86001defa4adfa894054aba27062e"
MANIFEST_CONTRACT_SHA256 = "3bf96bd6e6854a7beb048206f73465588df8f9b3182e1280ed7ec7878280559b"

DISPOSITION_PASS = "CANDIDATE_STRUCTURALLY_FEASIBLE_CA3"
DISPOSITION_FAIL = "CANDIDATE_NOT_STRUCTURALLY_FEASIBLE_FAIL_CLOSED"

DECLARATION_FIELDS = (
    "source_kind",
    "source_locator",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
)

BUNDLE_FIELDS = (
    "rights_evidence",
    "provenance_evidence",
)

EXPECTED_PREDECESSORS = {
    "source_kind": "SK-DECLARATION",
    "source_locator": "SL-DECLARATION",
    "rights_basis": "RB-DECLARATION",
    "rights_status": "RS-DECLARATION",
    "provenance_status": "PS-DECLARATION",
    "redistribution_status": "RD-DECLARATION",
}

EXPECTED_DISTINCT_EVIDENCE_REFERENCES = {
    "rights_evidence": 4,
    "provenance_evidence": 3,
}

BUNDLE_VERSION = "oic-evidence-bundle-0.1"
SERIALIZATION_ORDERING = "LEXICOGRAPHIC_SERIALIZATION_ONLY_NO_AUTHORITY"


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


def load_controls() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (HYP_RESULT, HYP_RESULT_SHA256),
        (SURFACE_RESULT, SURFACE_RESULT_SHA256),
        (MANIFEST_CONTRACT, MANIFEST_CONTRACT_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    candidate = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    hyp = json.loads(HYP_RESULT.read_text(encoding="utf-8"))
    surface = json.loads(SURFACE_RESULT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_CONTRACT.read_text(encoding="utf-8"))

    if candidate["status"] != "FROZEN_CANDIDATE_NOT_EVALUATED":
        raise SystemExit("FAIL candidate contract status drift")
    if freeze["status"] != "PREREGISTERED_CANDIDATE_NOT_EVALUATED":
        raise SystemExit("FAIL candidate preregistration status drift")
    if hyp["status"] != "CLOSED_EXECUTED_HYPOTHESES_STRUCTURALLY_EVALUATED":
        raise SystemExit("FAIL Hypotheses 001 closure status drift")
    if surface["status"] != "CLOSED_EXECUTED_FAILURE_SURFACE_CHARACTERIZED":
        raise SystemExit("FAIL Failure-Surface 001 closure status drift")
    if manifest["contract_id"] != "OIC-SOURCE-MANIFEST-CONTRACT-001":
        raise SystemExit("FAIL manifest contract identity drift")

    if candidate["candidate_evaluated"] is not False:
        raise SystemExit("FAIL candidate evaluation boundary drift")
    if candidate["candidate_adopted"] is not False:
        raise SystemExit("FAIL candidate adoption boundary drift")
    if candidate["manifest_contract_change_authorized"] is not False:
        raise SystemExit("FAIL manifest-change boundary drift")
    if candidate["source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest-creation boundary drift")
    if candidate["source_manifest_population_authorized"] is not False:
        raise SystemExit("FAIL manifest-population boundary drift")

    return candidate, freeze, hyp, surface, manifest


def is_repository_relative_reference(value: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value:
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        return False
    path = PurePosixPath(value)
    if path.is_absolute():
        return False
    if ".." in path.parts:
        return False
    return len(path.parts) >= 2


def build_synthetic_bundle(
    *,
    target_field: str,
    references: Sequence[str],
) -> dict[str, Any]:
    if target_field not in BUNDLE_FIELDS:
        raise ValueError(f"unsupported bundle target field: {target_field}")

    if not references:
        raise ValueError("evidence bundle must contain references")

    normalized = []
    for reference in references:
        if not isinstance(reference, str) or not reference:
            raise ValueError("evidence reference must be a non-empty string")
        normalized.append(reference)

    if len(set(normalized)) != len(normalized):
        raise ValueError("evidence bundle references must be distinct")

    # Sorting is serialization-only, never evidentiary or institutional priority.
    refs = sorted(normalized)

    return {
        "bundle_version": BUNDLE_VERSION,
        "source_id": "CA-3",
        "target_field": target_field,
        "ordering_semantics": SERIALIZATION_ORDERING,
        "evidence_references": refs,
        "reference_count": len(refs),
        "legal_sufficiency_established": False,
        "evidentiary_priority_established": False,
        "underlying_evidence_rewritten": False,
    }


def validate_synthetic_bundle(
    *,
    bundle: dict[str, Any],
    expected_field: str,
    expected_references: Sequence[str],
) -> list[str]:
    findings: list[str] = []

    if bundle.get("bundle_version") != BUNDLE_VERSION:
        findings.append("bundle_version mismatch")
    if bundle.get("source_id") != "CA-3":
        findings.append("source_id mismatch")
    if bundle.get("target_field") != expected_field:
        findings.append("target_field mismatch")
    if bundle.get("ordering_semantics") != SERIALIZATION_ORDERING:
        findings.append("ordering semantics mismatch")

    expected_set = set(expected_references)
    observed = bundle.get("evidence_references")
    if not isinstance(observed, list):
        findings.append("evidence_references not list")
        observed = []

    if set(observed) != expected_set:
        findings.append("bundle does not preserve exact evidence reference set")

    if len(observed) != len(expected_set):
        findings.append("bundle reference multiplicity mismatch")

    if bundle.get("reference_count") != len(expected_set):
        findings.append("reference_count mismatch")

    if bundle.get("legal_sufficiency_established") is not False:
        findings.append("legal sufficiency promotion")
    if bundle.get("evidentiary_priority_established") is not False:
        findings.append("evidentiary priority promotion")
    if bundle.get("underlying_evidence_rewritten") is not False:
        findings.append("underlying evidence rewrite")

    # Deterministic serialization check.
    first = hashlib.sha256(canonical_json_bytes(bundle)).hexdigest()
    second = hashlib.sha256(canonical_json_bytes(bundle)).hexdigest()
    if first != second:
        findings.append("bundle serialization non-deterministic")

    return findings


def _hyp_eval_by_id(
    hyp_result: dict[str, Any],
    hypothesis_id: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in hyp_result["evaluations"]
        if row["hypothesis_id"] == hypothesis_id
    ]
    if len(rows) != 1:
        raise ValueError(
            f"expected one Hypotheses 001 evaluation for {hypothesis_id}, "
            f"observed {len(rows)}"
        )
    return rows[0]


def _surface_profile(
    surface_result: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in surface_result["profiles"]
        if row["target_field"] == field
    ]
    if len(rows) != 1:
        raise ValueError(
            f"expected one Failure-Surface 001 profile for {field}, "
            f"observed {len(rows)}"
        )
    return rows[0]


def evaluate_candidate(
    *,
    candidate: dict[str, Any],
    hyp_result: dict[str, Any],
    surface_result: dict[str, Any],
    manifest_contract: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    declaration_checks: list[dict[str, Any]] = []
    bundle_checks: list[dict[str, Any]] = []

    mechanisms = candidate["candidate_field_mechanisms"]

    if set(mechanisms) != set(DECLARATION_FIELDS) | set(BUNDLE_FIELDS):
        findings.append({
            "code": "CANDIDATE_FIELD_POPULATION_MISMATCH",
            "message": repr(sorted(mechanisms)),
        })

    for field in DECLARATION_FIELDS:
        entry = mechanisms[field]
        predecessor_id = EXPECTED_PREDECESSORS[field]
        predecessor = _hyp_eval_by_id(hyp_result, predecessor_id)
        dims = predecessor["dimensions"]

        field_findings: list[str] = []

        if entry["predecessor_hypothesis_id"] != predecessor_id:
            field_findings.append("predecessor hypothesis mismatch")
        if entry["semantic_value_may_be_inferred_by_instrument"] is not False:
            field_findings.append("semantic inference enabled")
        if entry["target_contract_change_required"] is not False:
            field_findings.append("candidate unexpectedly requires contract change")
        if predecessor["bounded_structural_assessment"] != (
            "REQUIRES_NEW_EXPLICIT_DECLARATION"
        ):
            field_findings.append("predecessor assessment mismatch")
        if dims["current_manifest_contract_compatible"] != "TRUE":
            field_findings.append("current manifest contract incompatible")
        if dims["requires_manifest_contract_change"] != "FALSE":
            field_findings.append("predecessor requires contract change")
        if dims[
            "requires_new_explicit_evidence_or_metadata_declaration"
        ] != "TRUE":
            field_findings.append("predecessor does not require declaration")
        if dims["deterministic_replay_possible"] != "TRUE":
            field_findings.append("declaration replayability not structurally true")

        manifest_field = manifest_contract["fields"].get(field)
        if not isinstance(manifest_field, dict):
            field_findings.append("manifest target field absent")
        elif manifest_field.get("required") is not True:
            field_findings.append("manifest target field not required")

        if field_findings:
            for item in field_findings:
                findings.append({
                    "code": "DECLARATION_FIELD_CHECK_FAILED",
                    "message": f"{field}: {item}",
                })

        declaration_checks.append({
            "target_field": field,
            "predecessor_hypothesis_id": predecessor_id,
            "current_manifest_contract_compatible":
                dims["current_manifest_contract_compatible"] == "TRUE",
            "requires_explicit_declaration":
                dims[
                    "requires_new_explicit_evidence_or_metadata_declaration"
                ] == "TRUE",
            "semantic_value_inferred":
                False,
            "declaration_value_created":
                False,
            "manifest_contract_change_required":
                False,
            "structural_check_pass":
                not field_findings,
            "findings":
                field_findings,
        })

    for field in BUNDLE_FIELDS:
        entry = mechanisms[field]
        profile = _surface_profile(surface_result, field)
        field_findings: list[str] = []

        if entry["mechanism"] != "CANONICAL_TRACKED_EVIDENCE_BUNDLE_REFERENCE":
            field_findings.append("candidate mechanism mismatch")
        if entry[
            "bundle_must_preserve_all_observed_distinct_references"
        ] is not True:
            field_findings.append("bundle preservation requirement missing")
        if entry["semantic_value_may_be_inferred_by_instrument"] is not False:
            field_findings.append("semantic inference enabled")
        if entry["target_contract_change_required"] is not False:
            field_findings.append("candidate unexpectedly requires contract change")

        expected_count = EXPECTED_DISTINCT_EVIDENCE_REFERENCES[field]
        if profile["surface_class"] != "MULTI_ADMISSIBLE_CONTRADICTION_SURFACE":
            field_findings.append("surface class mismatch")
        if profile["distinct_mapped_value_count"] != expected_count:
            field_findings.append(
                "distinct mapped evidence count mismatch: "
                f"{profile['distinct_mapped_value_count']} != {expected_count}"
            )

        manifest_rule = manifest_contract["fields"][field]["rule"]
        if "repository-relative tracked evidence reference" not in manifest_rule:
            field_findings.append(
                "manifest contract lacks tracked evidence-reference route"
            )

        synthetic_refs = [
            f"synthetic://{field}/{index:02d}"
            for index in range(1, expected_count + 1)
        ]
        bundle = build_synthetic_bundle(
            target_field=field,
            references=synthetic_refs,
        )

        bundle_findings = validate_synthetic_bundle(
            bundle=bundle,
            expected_field=field,
            expected_references=synthetic_refs,
        )
        field_findings.extend(bundle_findings)

        bundle_path = (
            "benchmarks/preflight/corpus-rights-provenance-001/"
            f"evidence-bundles/CA-3/{field}-bundle-v0.1.json"
        )
        if not is_repository_relative_reference(bundle_path):
            field_findings.append("synthetic bundle path not repository-relative")

        if field_findings:
            for item in field_findings:
                findings.append({
                    "code": "BUNDLE_FIELD_CHECK_FAILED",
                    "message": f"{field}: {item}",
                })

        bundle_checks.append({
            "target_field":
                field,
            "observed_distinct_admissible_reference_count":
                expected_count,
            "synthetic_bundle_reference_count":
                bundle["reference_count"],
            "exact_reference_set_preserved":
                set(bundle["evidence_references"]) == set(synthetic_refs),
            "deterministic_serialization":
                True,
            "ordering_semantics":
                SERIALIZATION_ORDERING,
            "manifest_accepts_repository_relative_tracked_reference":
                "repository-relative tracked evidence reference" in manifest_rule,
            "synthetic_bundle_path":
                bundle_path,
            "manifest_contract_change_required":
                False,
            "precedence_required":
                False,
            "legal_sufficiency_established":
                False,
            "evidentiary_priority_established":
                False,
            "real_bundle_created":
                False,
            "structural_check_pass":
                not field_findings,
            "findings":
                field_findings,
        })

    all_declarations_pass = (
        len(declaration_checks) == 6
        and all(row["structural_check_pass"] for row in declaration_checks)
    )
    all_bundles_pass = (
        len(bundle_checks) == 2
        and all(row["structural_check_pass"] for row in bundle_checks)
    )

    feasible = not findings and all_declarations_pass and all_bundles_pass

    return {
        "work_order":
            "OIC-CANADA-MANIFEST-RESOLUTION-CANDIDATE-002",
        "status":
            "EVALUATED_TRACKED_INPUTS_ONLY",
        "disposition":
            DISPOSITION_PASS if feasible else DISPOSITION_FAIL,
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
        },
        "candidate_field_count":
            8,
        "explicit_declaration_field_count":
            6,
        "tracked_evidence_bundle_reference_field_count":
            2,
        "declaration_checks":
            declaration_checks,
        "bundle_checks":
            bundle_checks,
        "finding_count":
            len(findings),
        "findings":
            findings,

        "current_manifest_contract_represents_all_8_mechanisms":
            feasible,
        "machine_inference_of_declaration_values_required":
            False,
        "precedence_among_evidence_references_required":
            False,
        "semantic_projection_required":
            False,
        "manifest_contract_change_required":
            False if feasible else None,

        "candidate_adopted":
            False,
        "declaration_values_created":
            False,
        "real_evidence_bundles_created":
            False,
        "manifest_contract_changed":
            False,
        "schema_mutated":
            False,
        "evidence_rewritten":
            False,
        "source_manifest_created":
            False,
        "source_manifest_population_authorized":
            False,

        "bounded_ca3_structural_feasibility_only":
            True,
        "cross_source_generality_established":
            False,
        "held_out_validation_required_for_generalization":
            True,

        "causal_root_cause":
            "NOT_ESTABLISHED",
        "rights_established":
            False,
        "provenance_established":
            False,
        "legal_clearance_established":
            False,

        "local_crosswalk_receipt_inspected":
            False,
        "real_evidence_reread":
            False,
        "inventory_001_receipt_inspected":
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
            "Bounded structural feasibility of Candidate 002 on the frozen "
            "CA-3 tracked artifacts only. A PASS does not establish any "
            "declaration value, actual evidence-bundle content, rights, "
            "provenance truth, legal clearance, manifest admissibility, "
            "candidate adoption, or cross-source generality."
        ),
    }


def execute_tracked_read_only() -> dict[str, Any]:
    candidate, _freeze, hyp, surface, manifest = load_controls()
    return evaluate_candidate(
        candidate=candidate,
        hyp_result=hyp,
        surface_result=surface,
        manifest_contract=manifest,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-tracked-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_tracked_read_only:
        load_controls()
        print("static preflight: PASS")
        print("candidate evaluated: FALSE")
        print("local Crosswalk receipt read: ZERO")
        print("real declaration values created: FALSE")
        print("real evidence bundles created: FALSE")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_tracked_read_only()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(f"findings: {result['finding_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
