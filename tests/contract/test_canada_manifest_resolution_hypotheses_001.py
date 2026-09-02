from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/evaluate_canada_manifest_resolution_hypotheses_001.py"

spec = importlib.util.spec_from_file_location("hyp001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["hyp001"] = mod
spec.loader.exec_module(mod)


def controls():
    return mod.load_controls()


def support(
    *,
    key,
    mapped_value=None,
    artifact="synthetic.json",
    pointer="/record/value",
):
    row = {
        "target_field": "synthetic",
        "artifact_path": artifact,
        "artifact_git_blob_sha": "a" * 40,
        "json_pointer": pointer,
        "key": key,
        "raw_value": "raw",
        "source_scope_pointer": "/record",
    }
    if mapped_value is not None:
        row["mapped_value"] = mapped_value
        row["mapping_class"] = "ESTABLISHED_DIRECT"
        row["transformation"] = "SYNTHETIC_IDENTITY"
    return row


def field_result(
    field,
    *,
    state,
    candidate_count,
    admissible_value_count,
    support_rows,
):
    return {
        "target_field": field,
        "state": state,
        "value": None,
        "candidate_count": candidate_count,
        "admissible_value_count": admissible_value_count,
        "support": support_rows,
        "notes": [],
    }


def synthetic_surface_profile(
    field,
    *,
    surface_class,
    prior_state,
    candidate_count,
    admissible_value_count,
    support_record_count,
    distinct_candidate_key_count,
    distinct_artifact_path_count,
    distinct_mapped_value_count,
):
    return {
        "target_field": field,
        "surface_class": surface_class,
        "prior_state": prior_state,
        "candidate_count": candidate_count,
        "admissible_value_count": admissible_value_count,
        "support_record_count": support_record_count,
        "distinct_candidate_key_count": distinct_candidate_key_count,
        "distinct_artifact_path_count": distinct_artifact_path_count,
        "distinct_mapped_value_count": distinct_mapped_value_count,
    }


def test_declaration_is_current_contract_compatible_but_requires_new_state():
    profile = synthetic_surface_profile(
        "source_kind",
        surface_class=mod.ZERO_SURFACE,
        prior_state="MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        candidate_count=1,
        admissible_value_count=0,
        support_record_count=1,
        distinct_candidate_key_count=1,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=0,
    )
    result = field_result(
        "source_kind",
        state=profile["prior_state"],
        candidate_count=1,
        admissible_value_count=0,
        support_rows=[support(key="rendering_role")],
    )

    out = mod.evaluate_hypothesis(
        field="source_kind",
        hypothesis={
            "hypothesis_id": "SK-DECLARATION",
            "mechanism": mod.MECH_DECLARATION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["bounded_structural_assessment"] == (
        mod.ASSESSMENT_REQUIRES_DECLARATION
    )
    assert out["dimensions"]["current_manifest_contract_compatible"] == mod.STATUS_TRUE
    assert out["dimensions"]["requires_manifest_contract_change"] == mod.STATUS_FALSE
    assert out["dimensions"][
        "requires_new_explicit_evidence_or_metadata_declaration"
    ] == mod.STATUS_TRUE
    assert out["winner_selected"] is False


def test_projection_never_invents_mapping_or_claims_replayability():
    profile = synthetic_surface_profile(
        "rights_basis",
        surface_class=mod.ZERO_SURFACE,
        prior_state="MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        candidate_count=1,
        admissible_value_count=0,
        support_record_count=1,
        distinct_candidate_key_count=1,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=0,
    )
    result = field_result(
        "rights_basis",
        state=profile["prior_state"],
        candidate_count=1,
        admissible_value_count=0,
        support_rows=[support(key="automated_retrieval_basis")],
    )

    out = mod.evaluate_hypothesis(
        field="rights_basis",
        hypothesis={
            "hypothesis_id": "RB-PROJECTION",
            "mechanism": mod.MECH_PROJECTION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["bounded_structural_assessment"] == (
        mod.ASSESSMENT_REQUIRES_FUTURE_RULE
    )
    assert out["dimensions"]["requires_new_semantic_projection"] == mod.STATUS_TRUE
    assert out["dimensions"]["deterministic_replay_possible"] == (
        mod.STATUS_NOT_ESTABLISHED
    )
    assert out["actual_semantic_projection_created"] is False


def test_canonical_locator_declaration_fits_scalar_contract():
    profile = synthetic_surface_profile(
        "source_locator",
        surface_class=mod.CONTRADICTION_SURFACE,
        prior_state="CONTRADICTORY_NOT_ESTABLISHED",
        candidate_count=2,
        admissible_value_count=2,
        support_record_count=2,
        distinct_candidate_key_count=2,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=2,
    )
    result = field_result(
        "source_locator",
        state=profile["prior_state"],
        candidate_count=2,
        admissible_value_count=2,
        support_rows=[
            support(key="final_url", mapped_value="https://example.invalid/a"),
            support(key="requested_url", mapped_value="https://example.invalid/b"),
        ],
    )

    out = mod.evaluate_hypothesis(
        field="source_locator",
        hypothesis={
            "hypothesis_id": "SL-DECLARATION",
            "mechanism": mod.MECH_CANONICAL_DECLARATION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["dimensions"]["current_manifest_contract_compatible"] == mod.STATUS_TRUE
    assert out["dimensions"]["requires_manifest_contract_change"] == mod.STATUS_FALSE
    assert out["dimensions"][
        "requires_new_explicit_evidence_or_metadata_declaration"
    ] == mod.STATUS_TRUE


def test_canonical_precedence_requires_future_rule_and_selects_no_winner():
    profile = synthetic_surface_profile(
        "source_locator",
        surface_class=mod.CONTRADICTION_SURFACE,
        prior_state="CONTRADICTORY_NOT_ESTABLISHED",
        candidate_count=2,
        admissible_value_count=2,
        support_record_count=2,
        distinct_candidate_key_count=2,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=2,
    )
    result = field_result(
        "source_locator",
        state=profile["prior_state"],
        candidate_count=2,
        admissible_value_count=2,
        support_rows=[
            support(key="final_url", mapped_value="https://example.invalid/a"),
            support(key="requested_url", mapped_value="https://example.invalid/b"),
        ],
    )

    out = mod.evaluate_hypothesis(
        field="source_locator",
        hypothesis={
            "hypothesis_id": "SL-PRECEDENCE",
            "mechanism": mod.MECH_CANONICAL_PRECEDENCE,
        },
        profile=profile,
        field_result=result,
    )

    assert out["bounded_structural_assessment"] == (
        mod.ASSESSMENT_REQUIRES_FUTURE_RULE
    )
    assert out["dimensions"]["requires_precedence_rule"] == mod.STATUS_TRUE
    assert out["dimensions"]["deterministic_replay_possible"] == (
        mod.STATUS_NOT_ESTABLISHED
    )
    assert out["winner_selected"] is False
    assert out["actual_precedence_rule_created"] is False


def test_single_reference_precedence_does_not_preserve_all_values():
    profile = synthetic_surface_profile(
        "rights_evidence",
        surface_class=mod.CONTRADICTION_SURFACE,
        prior_state="CONTRADICTORY_NOT_ESTABLISHED",
        candidate_count=2,
        admissible_value_count=2,
        support_record_count=2,
        distinct_candidate_key_count=2,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=2,
    )
    result = field_result(
        "rights_evidence",
        state=profile["prior_state"],
        candidate_count=2,
        admissible_value_count=2,
        support_rows=[
            support(key="rights_notice_url", mapped_value="https://example.invalid/a"),
            support(key="terms_of_use_url", mapped_value="https://example.invalid/b"),
        ],
    )

    out = mod.evaluate_hypothesis(
        field="rights_evidence",
        hypothesis={
            "hypothesis_id": "RE-PRECEDENCE",
            "mechanism": mod.MECH_SINGLE_REFERENCE_PRECEDENCE,
        },
        profile=profile,
        field_result=result,
    )

    assert out["dimensions"]["current_manifest_contract_compatible"] == mod.STATUS_TRUE
    assert out["dimensions"]["requires_precedence_rule"] == mod.STATUS_TRUE
    assert out["dimensions"]["preserves_all_observed_distinct_values"] == (
        mod.STATUS_FALSE
    )


def test_collection_preserves_values_but_requires_contract_change():
    profile = synthetic_surface_profile(
        "provenance_evidence",
        surface_class=mod.CONTRADICTION_SURFACE,
        prior_state="CONTRADICTORY_NOT_ESTABLISHED",
        candidate_count=2,
        admissible_value_count=2,
        support_record_count=2,
        distinct_candidate_key_count=2,
        distinct_artifact_path_count=2,
        distinct_mapped_value_count=2,
    )
    result = field_result(
        "provenance_evidence",
        state=profile["prior_state"],
        candidate_count=2,
        admissible_value_count=2,
        support_rows=[
            support(key="provenance_url", mapped_value="https://example.invalid/a"),
            support(
                key="receipt_path",
                mapped_value="benchmarks/example.json",
                artifact="other.json",
            ),
        ],
    )

    out = mod.evaluate_hypothesis(
        field="provenance_evidence",
        hypothesis={
            "hypothesis_id": "PE-COLLECTION",
            "mechanism": mod.MECH_COLLECTION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["bounded_structural_assessment"] == (
        mod.ASSESSMENT_REQUIRES_CONTRACT_CHANGE
    )
    assert out["dimensions"]["current_manifest_contract_compatible"] == mod.STATUS_FALSE
    assert out["dimensions"]["requires_manifest_contract_change"] == mod.STATUS_TRUE
    assert out["dimensions"]["preserves_all_observed_distinct_values"] == mod.STATUS_TRUE
    assert out["manifest_contract_mutated"] is False


def test_profile_receipt_support_count_mismatch_fails_closed():
    profile = synthetic_surface_profile(
        "rights_status",
        surface_class=mod.ZERO_SURFACE,
        prior_state="MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        candidate_count=1,
        admissible_value_count=0,
        support_record_count=2,
        distinct_candidate_key_count=1,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=0,
    )
    result = field_result(
        "rights_status",
        state=profile["prior_state"],
        candidate_count=1,
        admissible_value_count=0,
        support_rows=[support(key="rights_disposition")],
    )

    out = mod.evaluate_hypothesis(
        field="rights_status",
        hypothesis={
            "hypothesis_id": "RS-DECLARATION",
            "mechanism": mod.MECH_DECLARATION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["bounded_structural_assessment"] == mod.ASSESSMENT_INCOMPLETE
    assert out["profile_receipt_crosscheck_pass"] is False
    assert all(
        value == mod.STATUS_NOT_ESTABLISHED
        for value in out["dimensions"].values()
    )


def test_every_evaluation_requires_heldout_for_generality():
    profile = synthetic_surface_profile(
        "source_kind",
        surface_class=mod.ZERO_SURFACE,
        prior_state="MULTIPLE_CANDIDATES_NOT_ESTABLISHED",
        candidate_count=1,
        admissible_value_count=0,
        support_record_count=1,
        distinct_candidate_key_count=1,
        distinct_artifact_path_count=1,
        distinct_mapped_value_count=0,
    )
    result = field_result(
        "source_kind",
        state=profile["prior_state"],
        candidate_count=1,
        admissible_value_count=0,
        support_rows=[support(key="rendering_role")],
    )

    out = mod.evaluate_hypothesis(
        field="source_kind",
        hypothesis={
            "hypothesis_id": "SK-DECLARATION",
            "mechanism": mod.MECH_DECLARATION,
        },
        profile=profile,
        field_result=result,
    )

    assert out["dimensions"]["independently_testable_on_current_CA3_only"] == (
        mod.STATUS_TRUE
    )
    assert out["dimensions"][
        "requires_held_out_source_for_generalization_claim"
    ] == mod.STATUS_TRUE


def test_static_contract_has_exact_16_frozen_hypotheses_and_no_winner():
    contract, freeze, _surface, manifest = controls()

    assert contract["hypothesis_count"] == 16
    assert len(contract["field_hypotheses"]) == 8
    assert all(len(v) == 2 for v in contract["field_hypotheses"].values())
    assert contract["winner_selection_rule"] == (
        "NO_WINNER_SELECTION_IN_HYPOTHESES_001"
    )
    assert contract["winner_selected"] is False
    assert contract["manifest_contract_change_authorized"] is False
    assert contract["schema_mutation_authorized"] is False
    assert contract["source_manifest_creation_authorized"] is False
    assert contract["source_manifest_population_authorized"] is False

    assert freeze["frozen_hypothesis_count"] == 16
    assert freeze["preserved_crosswalk_receipt_inspected_by_this_work_order"] is False
    assert freeze["hypotheses_evaluated"] is False
    assert freeze["winner_selected"] is False

    assert manifest["normalization_policy"].startswith("NONE:")


def test_source_manifest_remains_absent():
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
