#!/usr/bin/env python3
"""Structural evaluator for Canada manifest resolution hypotheses 001.

Static mode validates only tracked frozen controls.

Execution mode, only after separate authorization, may inspect the preserved
Crosswalk 001 receipt to establish bounded structural properties of the 16
already-frozen hypotheses. It cannot select a winner, invent an actual
precedence order, invent a semantic projection, mutate schema/evidence, or
write SOURCE_MANIFEST.csv.

Outputs are structural classifications, not repair decisions.
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
      "canada-manifest-resolution-hypotheses-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "HYPOTHESIS-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

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

PRESERVED_CROSSWALK_RECEIPT = (
    ROOT
    / ".local/evidence-to-manifest-crosswalk-receipts/"
      "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001.json"
)

PLAN_SHA256 = "a30c28198777e89963b5818860fec59b31e59fb83b80894bd1f2fded4849bbb8"
CONTRACT_SHA256 = "5e2c794b424a707927660350d32daf162eb33c58cebe1a7160d11a97d4f50d40"
PREREG_FREEZE_SHA256 = "3e80695413b730c8dac8a893e01053a0393d0fd30d40a22ab0a52d7091779e91"
SURFACE_RESULT_SHA256 = "b29831c5685f238492826db3f0f737a125f86001defa4adfa894054aba27062e"
MANIFEST_CONTRACT_SHA256 = "3bf96bd6e6854a7beb048206f73465588df8f9b3182e1280ed7ec7878280559b"
PRESERVED_CROSSWALK_RECEIPT_SHA256 = (
    "77d8a67a71e7eb073fa3f43825a1113a53effd948f69e7abee952e06767dbb92"
)

STATUS_TRUE = "TRUE"
STATUS_FALSE = "FALSE"
STATUS_NOT_ESTABLISHED = "NOT_ESTABLISHED"

ASSESSMENT_STRUCTURALLY_COMPATIBLE = "STRUCTURALLY_COMPATIBLE_CA3"
ASSESSMENT_REQUIRES_DECLARATION = "REQUIRES_NEW_EXPLICIT_DECLARATION"
ASSESSMENT_REQUIRES_CONTRACT_CHANGE = "REQUIRES_MANIFEST_CONTRACT_CHANGE"
ASSESSMENT_REQUIRES_FUTURE_RULE = "REQUIRES_SEPARATELY_FROZEN_RULE"
ASSESSMENT_INCOMPLETE = "STRUCTURAL_ASSESSMENT_INCOMPLETE_FAIL_CLOSED"

DISPOSITION_EVALUATED = "HYPOTHESES_STRUCTURALLY_EVALUATED"
DISPOSITION_INCOMPLETE = "HYPOTHESES_EVALUATION_INCOMPLETE_FAIL_CLOSED"

ZERO_SURFACE = "ZERO_ADMISSIBLE_VALUE_SURFACE"
CONTRADICTION_SURFACE = "MULTI_ADMISSIBLE_CONTRADICTION_SURFACE"

MECH_DECLARATION = "EXPLICIT_MANIFEST_ALIGNED_DECLARATION"
MECH_PROJECTION = "DETERMINISTIC_PROJECTION"
MECH_CANONICAL_DECLARATION = "EXPLICIT_CANONICAL_LOCATOR_DECLARATION"
MECH_CANONICAL_PRECEDENCE = "ROLE_BASED_CANONICAL_PRECEDENCE"
MECH_SINGLE_REFERENCE_PRECEDENCE = "SINGLE_REFERENCE_PRECEDENCE"
MECH_COLLECTION = "TYPED_MULTI_REFERENCE_COLLECTION"

EXPECTED_DIMENSIONS = [
    "current_manifest_contract_compatible",
    "requires_manifest_contract_change",
    "requires_new_explicit_evidence_or_metadata_declaration",
    "requires_new_semantic_projection",
    "requires_precedence_rule",
    "preserves_all_observed_distinct_values",
    "deterministic_replay_possible",
    "introduces_legal_or_institutional_semantic_promotion_risk",
    "independently_testable_on_current_CA3_only",
    "requires_held_out_source_for_generalization_claim",
]

ZERO_FIELDS = {
    "source_kind",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
}

CONTRADICTION_FIELDS = {
    "source_locator",
    "rights_evidence",
    "provenance_evidence",
}

LEGAL_OR_INSTITUTIONAL_CLASSIFICATION_FIELDS = {
    "source_kind",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
}

RIGHTS_PROVENANCE_FIELDS = {
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_controls() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (SURFACE_RESULT, SURFACE_RESULT_SHA256),
        (MANIFEST_CONTRACT, MANIFEST_CONTRACT_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    surface = json.loads(SURFACE_RESULT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_CONTRACT.read_text(encoding="utf-8"))

    if contract["status"] != "FROZEN_HYPOTHESES_NOT_EVALUATED":
        raise SystemExit("FAIL hypothesis contract status drift")
    if freeze["status"] != "PREREGISTERED_HYPOTHESES_NOT_EVALUATED":
        raise SystemExit("FAIL preregistration status drift")
    if surface["status"] != "CLOSED_EXECUTED_FAILURE_SURFACE_CHARACTERIZED":
        raise SystemExit("FAIL surface closure status drift")
    if manifest["contract_id"] != "OIC-SOURCE-MANIFEST-CONTRACT-001":
        raise SystemExit("FAIL manifest contract identity drift")

    if contract["winner_selection_rule"] != (
        "NO_WINNER_SELECTION_IN_HYPOTHESES_001"
    ):
        raise SystemExit("FAIL winner-selection boundary drift")
    if contract["manifest_contract_change_authorized"] is not False:
        raise SystemExit("FAIL contract-change boundary drift")
    if contract["schema_mutation_authorized"] is not False:
        raise SystemExit("FAIL schema-mutation boundary drift")
    if contract["evidence_rewrite_authorized"] is not False:
        raise SystemExit("FAIL evidence-rewrite boundary drift")
    if contract["source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest-creation boundary drift")
    if contract["source_manifest_population_authorized"] is not False:
        raise SystemExit("FAIL manifest-population boundary drift")

    if contract["evaluation_dimensions"] != EXPECTED_DIMENSIONS:
        raise SystemExit("FAIL evaluation dimensions drift")

    return contract, freeze, surface, manifest


def _field_profile(
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
            f"expected exactly one failure-surface profile for {field}, "
            f"observed {len(rows)}"
        )
    return rows[0]


def _receipt_field(
    receipt: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    rows = [
        row
        for row in receipt["field_results"]
        if row["target_field"] == field
    ]
    if len(rows) != 1:
        raise ValueError(
            f"expected exactly one Crosswalk 001 field_result for {field}, "
            f"observed {len(rows)}"
        )
    return rows[0]


def _support_structural_summary(
    field_result: dict[str, Any],
) -> dict[str, Any]:
    support = field_result.get("support")
    if not isinstance(support, list):
        raise ValueError("support is not a list")

    keys = []
    artifacts = []
    mapped_values = []
    mapping_classes = []
    transformations = []

    for index, row in enumerate(support):
        if not isinstance(row, dict):
            raise ValueError(f"support[{index}] is not an object")

        for required in (
            "artifact_path",
            "artifact_git_blob_sha",
            "json_pointer",
            "key",
            "source_scope_pointer",
        ):
            if required not in row:
                raise ValueError(
                    f"support[{index}] missing {required}"
                )

        keys.append(str(row["key"]))
        artifacts.append(str(row["artifact_path"]))

        if row.get("mapped_value") is not None:
            mapped_values.append(str(row["mapped_value"]))
        if row.get("mapping_class") is not None:
            mapping_classes.append(str(row["mapping_class"]))
        if row.get("transformation") is not None:
            transformations.append(str(row["transformation"]))

    return {
        "support_record_count":
            len(support),
        "distinct_candidate_key_count":
            len(set(keys)),
        "candidate_keys":
            sorted(set(keys)),
        "distinct_artifact_path_count":
            len(set(artifacts)),
        "distinct_mapped_value_count":
            len(set(mapped_values)),
        "mapping_classes":
            sorted(set(mapping_classes)),
        "transformations":
            sorted(set(transformations)),
    }


def _bool_status(value: bool) -> str:
    return STATUS_TRUE if value else STATUS_FALSE


def _structural_dimensions(
    *,
    field: str,
    mechanism: str,
    profile: dict[str, Any],
    support_summary: dict[str, Any],
) -> tuple[dict[str, str], str, tuple[str, ...]]:
    surface_class = profile["surface_class"]
    notes: list[str] = []

    if field in ZERO_FIELDS and surface_class != ZERO_SURFACE:
        return (
            {dim: STATUS_NOT_ESTABLISHED for dim in EXPECTED_DIMENSIONS},
            ASSESSMENT_INCOMPLETE,
            (
                f"field {field} expected {ZERO_SURFACE}, "
                f"observed {surface_class}",
            ),
        )

    if field in CONTRADICTION_FIELDS and surface_class != CONTRADICTION_SURFACE:
        return (
            {dim: STATUS_NOT_ESTABLISHED for dim in EXPECTED_DIMENSIONS},
            ASSESSMENT_INCOMPLETE,
            (
                f"field {field} expected {CONTRADICTION_SURFACE}, "
                f"observed {surface_class}",
            ),
        )

    # All mechanisms remain bounded to CA-3. None establishes generality.
    base = {
        "independently_testable_on_current_CA3_only":
            STATUS_TRUE,
        "requires_held_out_source_for_generalization_claim":
            STATUS_TRUE,
    }

    if mechanism == MECH_DECLARATION:
        if field not in ZERO_FIELDS:
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_TRUE,
            "requires_manifest_contract_change":
                STATUS_FALSE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_TRUE,
            "requires_new_semantic_projection":
                STATUS_FALSE,
            "requires_precedence_rule":
                STATUS_FALSE,
            "preserves_all_observed_distinct_values":
                STATUS_FALSE,
            "deterministic_replay_possible":
                STATUS_TRUE,
            "introduces_legal_or_institutional_semantic_promotion_risk":
                _bool_status(
                    field in LEGAL_OR_INSTITUTIONAL_CLASSIFICATION_FIELDS
                ),
            **base,
        }
        notes.append(
            "Structurally compatible with the current scalar/enum manifest "
            "shape, but the required declaration does not exist in the "
            "preserved Crosswalk 001 support surface."
        )
        return dims, ASSESSMENT_REQUIRES_DECLARATION, tuple(notes)

    if mechanism == MECH_PROJECTION:
        if field not in ZERO_FIELDS:
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_TRUE,
            "requires_manifest_contract_change":
                STATUS_FALSE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_FALSE,
            "requires_new_semantic_projection":
                STATUS_TRUE,
            "requires_precedence_rule":
                STATUS_FALSE,
            "preserves_all_observed_distinct_values":
                STATUS_FALSE,
            # No actual projection function is frozen in Hypotheses 001.
            "deterministic_replay_possible":
                STATUS_NOT_ESTABLISHED,
            "introduces_legal_or_institutional_semantic_promotion_risk":
                _bool_status(
                    field in LEGAL_OR_INSTITUTIONAL_CLASSIFICATION_FIELDS
                ),
            **base,
        }
        notes.append(
            "A projection mechanism is conceptually compatible with the "
            "current target field shape, but no projection function is "
            "authorized or frozen here; replayability therefore remains "
            "NOT_ESTABLISHED."
        )
        if field in RIGHTS_PROVENANCE_FIELDS:
            notes.append(
                "Projection would carry explicit legal/institutional "
                "semantic-promotion risk and requires a separate preregistered "
                "mapping study."
            )
        return dims, ASSESSMENT_REQUIRES_FUTURE_RULE, tuple(notes)

    if mechanism == MECH_CANONICAL_DECLARATION:
        if field != "source_locator":
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_TRUE,
            "requires_manifest_contract_change":
                STATUS_FALSE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_TRUE,
            "requires_new_semantic_projection":
                STATUS_FALSE,
            "requires_precedence_rule":
                STATUS_FALSE,
            "preserves_all_observed_distinct_values":
                STATUS_FALSE,
            "deterministic_replay_possible":
                STATUS_TRUE,
            "introduces_legal_or_institutional_semantic_promotion_risk":
                STATUS_TRUE,
            **base,
        }
        notes.append(
            "The manifest already expects one canonical locator. An explicit "
            "canonical declaration fits that shape but assigns institutional "
            "canonicality and must be separately admitted."
        )
        return dims, ASSESSMENT_REQUIRES_DECLARATION, tuple(notes)

    if mechanism == MECH_CANONICAL_PRECEDENCE:
        if field != "source_locator":
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        discriminator_present = (
            support_summary["distinct_candidate_key_count"] > 1
            and support_summary["distinct_mapped_value_count"] > 1
        )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_TRUE,
            "requires_manifest_contract_change":
                STATUS_FALSE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_FALSE,
            "requires_new_semantic_projection":
                STATUS_FALSE,
            "requires_precedence_rule":
                STATUS_TRUE,
            "preserves_all_observed_distinct_values":
                STATUS_FALSE,
            "deterministic_replay_possible":
                (
                    STATUS_NOT_ESTABLISHED
                    if discriminator_present
                    else STATUS_FALSE
                ),
            "introduces_legal_or_institutional_semantic_promotion_risk":
                STATUS_TRUE,
            **base,
        }
        notes.append(
            "The current support surface contains distinguishable locator roles, "
            "but Hypotheses 001 freezes no precedence ordering; deterministic "
            "replayability of an actual canonical-selection rule remains "
            "NOT_ESTABLISHED."
        )
        return dims, ASSESSMENT_REQUIRES_FUTURE_RULE, tuple(notes)

    if mechanism == MECH_SINGLE_REFERENCE_PRECEDENCE:
        if field not in {"rights_evidence", "provenance_evidence"}:
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        discriminator_present = (
            support_summary["distinct_candidate_key_count"] > 1
            and support_summary["distinct_mapped_value_count"] > 1
        )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_TRUE,
            "requires_manifest_contract_change":
                STATUS_FALSE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_FALSE,
            "requires_new_semantic_projection":
                STATUS_FALSE,
            "requires_precedence_rule":
                STATUS_TRUE,
            "preserves_all_observed_distinct_values":
                STATUS_FALSE,
            "deterministic_replay_possible":
                (
                    STATUS_NOT_ESTABLISHED
                    if discriminator_present
                    else STATUS_FALSE
                ),
            "introduces_legal_or_institutional_semantic_promotion_risk":
                STATUS_TRUE,
            **base,
        }
        notes.append(
            "A single-reference result fits the current scalar contract, but "
            "selecting sufficiency among multiple admissible evidence references "
            "requires a separately frozen institutional precedence/sufficiency "
            "rule."
        )
        return dims, ASSESSMENT_REQUIRES_FUTURE_RULE, tuple(notes)

    if mechanism == MECH_COLLECTION:
        if field not in {"rights_evidence", "provenance_evidence"}:
            raise ValueError(
                f"{mechanism} not frozen for field {field}"
            )

        dims = {
            "current_manifest_contract_compatible":
                STATUS_FALSE,
            "requires_manifest_contract_change":
                STATUS_TRUE,
            "requires_new_explicit_evidence_or_metadata_declaration":
                STATUS_FALSE,
            "requires_new_semantic_projection":
                STATUS_FALSE,
            "requires_precedence_rule":
                STATUS_FALSE,
            "preserves_all_observed_distinct_values":
                STATUS_TRUE,
            "deterministic_replay_possible":
                STATUS_TRUE,
            "introduces_legal_or_institutional_semantic_promotion_risk":
                STATUS_FALSE,
            **base,
        }
        notes.append(
            "A typed multi-reference collection preserves the observed evidence "
            "set without winner selection, but the current manifest field is "
            "scalar and therefore this mechanism requires a separately "
            "authorized contract change."
        )
        return dims, ASSESSMENT_REQUIRES_CONTRACT_CHANGE, tuple(notes)

    raise ValueError(f"unsupported frozen mechanism: {mechanism}")


def evaluate_hypothesis(
    *,
    field: str,
    hypothesis: dict[str, Any],
    profile: dict[str, Any],
    field_result: dict[str, Any],
) -> dict[str, Any]:
    summary = _support_structural_summary(field_result)

    # Cross-check the preserved receipt support shape against the independently
    # closed descriptive profile. This catches drift without rereading evidence.
    findings: list[str] = []

    expected_pairs = {
        "support_record_count":
            profile["support_record_count"],
        "distinct_candidate_key_count":
            profile["distinct_candidate_key_count"],
        "distinct_artifact_path_count":
            profile["distinct_artifact_path_count"],
        "distinct_mapped_value_count":
            profile["distinct_mapped_value_count"],
    }

    for key, expected in expected_pairs.items():
        observed = summary[key]
        if observed != expected:
            findings.append(
                f"{key}: expected {expected}, observed {observed}"
            )

    if field_result["state"] != profile["prior_state"]:
        findings.append(
            "prior state mismatch: "
            f"{field_result['state']!r} != {profile['prior_state']!r}"
        )

    if field_result["candidate_count"] != profile["candidate_count"]:
        findings.append(
            "candidate count mismatch: "
            f"{field_result['candidate_count']!r} != "
            f"{profile['candidate_count']!r}"
        )

    if (
        field_result["admissible_value_count"]
        != profile["admissible_value_count"]
    ):
        findings.append(
            "admissible value count mismatch: "
            f"{field_result['admissible_value_count']!r} != "
            f"{profile['admissible_value_count']!r}"
        )

    if findings:
        dimensions = {
            dim: STATUS_NOT_ESTABLISHED
            for dim in EXPECTED_DIMENSIONS
        }
        assessment = ASSESSMENT_INCOMPLETE
        notes = tuple(findings)
    else:
        dimensions, assessment, notes = _structural_dimensions(
            field=field,
            mechanism=hypothesis["mechanism"],
            profile=profile,
            support_summary=summary,
        )

    return {
        "target_field":
            field,
        "hypothesis_id":
            hypothesis["hypothesis_id"],
        "mechanism":
            hypothesis["mechanism"],
        "surface_class":
            profile["surface_class"],
        "bounded_structural_assessment":
            assessment,
        "dimensions":
            dimensions,
        "support_summary":
            summary,
        "profile_receipt_crosscheck_pass":
            not findings,
        "findings":
            findings,
        "notes":
            list(notes),
        "winner_selected":
            False,
        "hypothesis_adopted":
            False,
        "actual_precedence_rule_created":
            False,
        "actual_semantic_projection_created":
            False,
        "manifest_contract_mutated":
            False,
        "evidence_mutated":
            False,
    }


def evaluate_receipt(
    receipt: dict[str, Any],
    *,
    contract: dict[str, Any],
    surface_result: dict[str, Any],
) -> dict[str, Any]:
    top_findings: list[str] = []

    if receipt.get("work_order") != (
        "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001"
    ):
        top_findings.append("wrong Crosswalk 001 work_order")
    if receipt.get("status") != "EXECUTED_READ_ONLY":
        top_findings.append("wrong Crosswalk 001 receipt status")
    if receipt.get("disposition") != "CROSSWALK_INCOMPLETE_FAIL_CLOSED":
        top_findings.append("wrong Crosswalk 001 disposition")
    if receipt.get("target_field_count") != 12:
        top_findings.append("wrong Crosswalk 001 target_field_count")
    if receipt.get("established_field_count") != 4:
        top_findings.append("wrong Crosswalk 001 established_field_count")

    field_results = receipt.get("field_results")
    if not isinstance(field_results, list):
        raise ValueError("Crosswalk 001 field_results is not a list")

    evaluations: list[dict[str, Any]] = []

    for field, hypotheses in contract["field_hypotheses"].items():
        profile = _field_profile(surface_result, field)
        field_result = _receipt_field(receipt, field)

        for hypothesis in hypotheses:
            evaluations.append(
                evaluate_hypothesis(
                    field=field,
                    hypothesis=hypothesis,
                    profile=profile,
                    field_result=field_result,
                )
            )

    ids = [row["hypothesis_id"] for row in evaluations]
    if len(ids) != 16 or len(set(ids)) != 16:
        top_findings.append("hypothesis population mismatch")

    crosscheck_failures = [
        row
        for row in evaluations
        if not row["profile_receipt_crosscheck_pass"]
    ]

    if crosscheck_failures:
        top_findings.append(
            f"profile/receipt crosscheck failures: {len(crosscheck_failures)}"
        )

    expected_assessment_classes = {
        ASSESSMENT_REQUIRES_DECLARATION,
        ASSESSMENT_REQUIRES_CONTRACT_CHANGE,
        ASSESSMENT_REQUIRES_FUTURE_RULE,
        ASSESSMENT_STRUCTURALLY_COMPATIBLE,
    }

    unexpected_assessments = [
        row["bounded_structural_assessment"]
        for row in evaluations
        if row["bounded_structural_assessment"]
        not in expected_assessment_classes
    ]

    complete = (
        not top_findings
        and len(evaluations) == 16
        and not unexpected_assessments
    )

    assessment_counts = Counter(
        row["bounded_structural_assessment"]
        for row in evaluations
    )

    return {
        "work_order":
            "OIC-CANADA-MANIFEST-RESOLUTION-HYPOTHESES-001",
        "status":
            "EXECUTED_READ_ONLY",
        "disposition":
            (
                DISPOSITION_EVALUATED
                if complete
                else DISPOSITION_INCOMPLETE
            ),
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
        },
        "frozen_hypothesis_count":
            16,
        "evaluated_hypothesis_count":
            len(evaluations),
        "evaluation_dimensions":
            EXPECTED_DIMENSIONS,
        "evaluations":
            evaluations,
        "assessment_counts":
            dict(sorted(assessment_counts.items())),
        "finding_count":
            len(top_findings),
        "findings":
            top_findings,

        "winner_selected":
            False,
        "hypothesis_adopted":
            False,
        "actual_precedence_rule_created":
            False,
        "actual_semantic_projection_created":
            False,
        "manifest_contract_change_performed":
            False,
        "schema_mutation_performed":
            False,
        "evidence_rewrite_performed":
            False,
        "source_manifest_created":
            False,
        "source_manifest_population_authorized":
            False,

        "bounded_ca3_structural_evaluation_only":
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
            "Bounded structural evaluation of the 16 frozen resolution "
            "hypotheses on CA-3 only. No winner, actual precedence rule, actual "
            "semantic projection, manifest-contract change, evidence rewrite, "
            "legal conclusion, provenance conclusion, or cross-source "
            "generality is established."
        ),
    }


def execute_read_only() -> dict[str, Any]:
    contract, _freeze, surface, _manifest = load_controls()

    if (
        sha256(PRESERVED_CROSSWALK_RECEIPT)
        != PRESERVED_CROSSWALK_RECEIPT_SHA256
    ):
        raise SystemExit("FAIL preserved Crosswalk 001 receipt digest mismatch")

    receipt = json.loads(
        PRESERVED_CROSSWALK_RECEIPT.read_text(encoding="utf-8")
    )

    return evaluate_receipt(
        receipt,
        contract=contract,
        surface_result=surface,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        load_controls()
        print("static preflight: PASS")
        print("frozen hypotheses: 16")
        print("preserved Crosswalk 001 receipt content read: ZERO")
        print("winner selected: FALSE")
        print("precedence/projection rule created: FALSE")
        print("manifest contract mutated: FALSE")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_read_only()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(
            "evaluated hypotheses: "
            f"{result['evaluated_hypothesis_count']}/"
            f"{result['frozen_hypothesis_count']}"
        )
        print(f"findings: {result['finding_count']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
