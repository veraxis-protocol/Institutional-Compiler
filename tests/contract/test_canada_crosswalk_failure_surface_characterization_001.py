from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/characterize_canada_crosswalk_failure_surface_001.py"

spec = importlib.util.spec_from_file_location("surface001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["surface001"] = mod
spec.loader.exec_module(mod)


def controls():
    return mod.load_controls()


def support(
    *,
    key="official_url",
    raw_value="https://example.invalid/a",
    artifact="synthetic.json",
    blob="a" * 40,
    pointer="/record/official_url",
    scope="/record",
    mapped_value=None,
    mapping_class=None,
    transformation=None,
):
    row = {
        "target_field": "source_locator",
        "artifact_path": artifact,
        "artifact_git_blob_sha": blob,
        "json_pointer": pointer,
        "key": key,
        "raw_value": raw_value,
        "source_scope_pointer": scope,
    }
    if mapped_value is not None:
        row["mapped_value"] = mapped_value
    if mapping_class is not None:
        row["mapping_class"] = mapping_class
    if transformation is not None:
        row["transformation"] = transformation
    return row


def field_result(
    field,
    *,
    state,
    candidate_count,
    admissible_value_count,
    rows,
):
    return {
        "target_field": field,
        "state": state,
        "value": None,
        "candidate_count": candidate_count,
        "admissible_value_count": admissible_value_count,
        "support": rows,
        "notes": [],
    }


def synthetic_receipt():
    contract, _freeze, _result = controls()

    rows = []
    for field, expected in contract["unresolved_fields"].items():
        if expected["prior_state"] == "MULTIPLE_CANDIDATES_NOT_ESTABLISHED":
            rows.append(
                field_result(
                    field,
                    state=expected["prior_state"],
                    candidate_count=expected["candidate_count"],
                    admissible_value_count=0,
                    rows=[
                        support(
                            key=f"{field}_candidate",
                            raw_value=f"{field}-raw",
                            pointer=f"/{field}/candidate",
                        )
                    ],
                )
            )
        else:
            rows.append(
                field_result(
                    field,
                    state=expected["prior_state"],
                    candidate_count=expected["candidate_count"],
                    admissible_value_count=expected["admissible_value_count"],
                    rows=[
                        support(
                            key=f"{field}_candidate",
                            raw_value=f"{field}-raw-a",
                            pointer=f"/{field}/a",
                            mapped_value=f"{field}-mapped-a",
                            mapping_class="ESTABLISHED_DIRECT",
                            transformation="SYNTHETIC_IDENTITY",
                        ),
                        support(
                            key=f"{field}_candidate",
                            raw_value=f"{field}-raw-b",
                            pointer=f"/{field}/b",
                            mapped_value=f"{field}-mapped-b",
                            mapping_class="ESTABLISHED_DIRECT",
                            transformation="SYNTHETIC_IDENTITY",
                        ),
                    ],
                )
            )

    return {
        "work_order": "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001",
        "status": "EXECUTED_READ_ONLY",
        "disposition": "CROSSWALK_INCOMPLETE_FAIL_CLOSED",
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
        },
        "target_field_count": 12,
        "established_field_count": 4,
        "field_results": rows,
    }


def test_raw_fingerprint_is_deterministic_exact_json():
    assert mod.raw_value_fingerprint({"b": 2, "a": 1}) == (
        mod.raw_value_fingerprint({"a": 1, "b": 2})
    )


def test_raw_fingerprint_preserves_string_case():
    assert mod.raw_value_fingerprint("Public") != mod.raw_value_fingerprint("public")


def test_raw_fingerprint_preserves_string_whitespace():
    assert mod.raw_value_fingerprint("x") != mod.raw_value_fingerprint(" x ")


def test_zero_admissible_surface_class():
    assert mod.classify_surface(
        prior_state="MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        admissible_value_count=0,
    ) == mod.ZERO_SURFACE


def test_contradiction_surface_class():
    assert mod.classify_surface(
        prior_state="CONTRADICTORY_NOT_ESTABLISHED",
        admissible_value_count=3,
    ) == mod.CONTRADICTION_SURFACE


def test_unexpected_surface_fails_closed():
    assert mod.classify_surface(
        prior_state="MISSING_NOT_ESTABLISHED",
        admissible_value_count=0,
    ) == mod.UNEXPECTED_SURFACE


def test_characterize_zero_surface_does_not_select_winner():
    expected = {
        "prior_state": "MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        "candidate_count": 10,
        "admissible_value_count": 0,
    }
    row = field_result(
        "rights_status",
        state=expected["prior_state"],
        candidate_count=10,
        admissible_value_count=0,
        rows=[
            support(
                key="rights_disposition",
                raw_value="PENDING",
            ),
            support(
                key="rights_disposition",
                raw_value="REVIEW_REQUIRED",
            ),
        ],
    )
    out = mod.characterize_field_result(row, expected)

    assert out["surface_class"] == mod.ZERO_SURFACE
    assert out["profile_complete"] is True
    assert out["winner_selected"] is False
    assert out["precedence_assigned"] is False
    assert out["normalization_performed"] is False
    assert out["new_mapping_derived"] is False
    assert out["distinct_candidate_key_count"] == 1
    assert out["distinct_raw_value_fingerprint_count"] == 2
    assert out["distinct_mapped_value_count"] == 0


def test_characterize_contradiction_captures_only_preserved_mapped_values():
    expected = {
        "prior_state": "CONTRADICTORY_NOT_ESTABLISHED",
        "candidate_count": 144,
        "admissible_value_count": 2,
    }
    row = field_result(
        "source_locator",
        state=expected["prior_state"],
        candidate_count=144,
        admissible_value_count=2,
        rows=[
            support(
                raw_value="https://example.invalid/a",
                mapped_value="https://example.invalid/a",
                mapping_class="ESTABLISHED_DIRECT",
                transformation="EXACT_HTTP_URI_IDENTITY",
            ),
            support(
                raw_value="https://example.invalid/b",
                mapped_value="https://example.invalid/b",
                mapping_class="ESTABLISHED_DIRECT",
                transformation="EXACT_HTTP_URI_IDENTITY",
            ),
        ],
    )
    out = mod.characterize_field_result(row, expected)

    assert out["surface_class"] == mod.CONTRADICTION_SURFACE
    assert out["profile_complete"] is True
    assert out["mapped_value_frequency"] == {
        "https://example.invalid/a": 1,
        "https://example.invalid/b": 1,
    }
    assert out["winner_selected"] is False


def test_candidate_count_mismatch_fails_profile():
    expected = {
        "prior_state": "MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        "candidate_count": 10,
        "admissible_value_count": 0,
    }
    row = field_result(
        "source_kind",
        state=expected["prior_state"],
        candidate_count=9,
        admissible_value_count=0,
        rows=[support(key="kind", raw_value="public")],
    )
    out = mod.characterize_field_result(row, expected)

    assert out["profile_complete"] is False
    assert any(
        f["code"] == "CANDIDATE_COUNT_MISMATCH"
        for f in out["findings"]
    )


def test_prior_state_mismatch_fails_profile():
    expected = {
        "prior_state": "MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        "candidate_count": 10,
        "admissible_value_count": 0,
    }
    row = field_result(
        "source_kind",
        state="CONTRADICTORY_NOT_ESTABLISHED",
        candidate_count=10,
        admissible_value_count=2,
        rows=[support(key="kind", raw_value="public")],
    )
    out = mod.characterize_field_result(row, expected)

    assert out["profile_complete"] is False
    assert out["surface_class"] == mod.CONTRADICTION_SURFACE


def test_missing_support_raw_value_fails_profile():
    expected = {
        "prior_state": "MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        "candidate_count": 1,
        "admissible_value_count": 0,
    }
    broken = support()
    broken.pop("raw_value")
    row = field_result(
        "rights_basis",
        state=expected["prior_state"],
        candidate_count=1,
        admissible_value_count=0,
        rows=[broken],
    )
    out = mod.characterize_field_result(row, expected)

    assert out["profile_complete"] is False
    assert any(
        f["code"] == "SUPPORT_PROFILE_FAILURE"
        for f in out["findings"]
    )


def test_complete_synthetic_eight_field_surface_characterizes():
    contract, _freeze, _result = controls()
    result = mod.characterize_receipt(
        synthetic_receipt(),
        contract=contract,
    )

    assert result["disposition"] == mod.DISPOSITION_CHARACTERIZED
    assert result["unresolved_field_profile_count"] == 8
    assert result["finding_count"] == 0
    assert result["surface_class_counts"] == {
        mod.CONTRADICTION_SURFACE: 3,
        mod.ZERO_SURFACE: 5,
    }


def test_missing_one_unresolved_field_fails_closed():
    contract, _freeze, _result = controls()
    receipt = synthetic_receipt()
    receipt["field_results"] = receipt["field_results"][:-1]

    result = mod.characterize_receipt(
        receipt,
        contract=contract,
    )

    assert result["disposition"] == mod.DISPOSITION_INCOMPLETE
    assert result["finding_count"] > 0
    assert any(
        f["code"] == "UNRESOLVED_FIELD_MISSING"
        for f in result["findings"]
    )


def test_duplicate_field_result_fails_closed():
    contract, _freeze, _result = controls()
    receipt = synthetic_receipt()
    receipt["field_results"].append(receipt["field_results"][0])

    result = mod.characterize_receipt(
        receipt,
        contract=contract,
    )

    assert result["disposition"] == mod.DISPOSITION_INCOMPLETE
    assert any(
        f["code"] == "DUPLICATE_FIELD_RESULT"
        for f in result["findings"]
    )


def test_output_never_authorizes_resolution_manifest_or_downstream():
    contract, _freeze, _result = controls()
    result = mod.characterize_receipt(
        synthetic_receipt(),
        contract=contract,
    )

    assert result["winner_selection_performed"] is False
    assert result["precedence_assignment_performed"] is False
    assert result["normalization_performed"] is False
    assert result["schema_mutation_performed"] is False
    assert result["evidence_rewrite_performed"] is False
    assert result["candidate_key_expansion_performed"] is False
    assert result["new_semantic_mapping_performed"] is False
    assert result["causal_root_cause"] == "NOT_ESTABLISHED"
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False
    assert result["rights_established"] is False
    assert result["provenance_established"] is False
    assert result["provider_model_network_calls"] == 0
    assert result["ontology_007r1_execution_authorized"] is False
    assert result["q011_creation_authorized"] is False
    assert result["canonicalization_authorized"] is False
    assert result["institutional_ir_authorized"] is False
    assert result["control_envelope_authorized"] is False
    assert result["rego_compilation_authorized"] is False
    assert result["runtime_evaluation_authorized"] is False


def test_static_controls_keep_real_receipt_and_schema_resolution_closed():
    contract, freeze, _result = controls()

    assert contract["input_scope"]["source"] == (
        "PRESERVED_CROSSWALK_001_ONE_SHOT_RECEIPT_ONLY"
    )
    assert contract["schema_resolution_authorized"] is False
    assert contract["normalization_authorized"] is False
    assert contract["precedence_selection_authorized"] is False
    assert contract["source_manifest_creation_authorized"] is False
    assert contract["source_manifest_population_authorized"] is False

    algo = contract["characterization_algorithm"]
    assert algo["winner_selection_authorized"] is False
    assert algo["precedence_rule_design_authorized"] is False
    assert algo["normalization_rule_design_authorized"] is False
    assert algo["schema_mutation_authorized"] is False

    assert freeze["preserved_crosswalk_receipt_inspected_by_this_work_order"] is False
    assert freeze["schema_resolution_authorized"] is False
    assert freeze["normalization_authorized"] is False
    assert freeze["precedence_selection_authorized"] is False


def test_source_manifest_remains_absent():
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
