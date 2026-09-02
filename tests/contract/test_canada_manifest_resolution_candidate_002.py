from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/evaluate_canada_manifest_resolution_candidate_002.py"

spec = importlib.util.spec_from_file_location("candidate002", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["candidate002"] = mod
spec.loader.exec_module(mod)


def controls():
    return mod.load_controls()


def test_repository_relative_reference_accepts_nested_path():
    assert mod.is_repository_relative_reference(
        "benchmarks/preflight/evidence/CA-3-rights.json"
    )


def test_repository_relative_reference_rejects_absolute_path():
    assert not mod.is_repository_relative_reference("/tmp/evidence.json")


def test_repository_relative_reference_rejects_parent_traversal():
    assert not mod.is_repository_relative_reference("../evidence.json")


def test_repository_relative_reference_rejects_uri():
    assert not mod.is_repository_relative_reference("https://example.invalid/evidence")


def test_bundle_builder_preserves_exact_distinct_set():
    refs = [
        "https://example.invalid/b",
        "https://example.invalid/a",
        "benchmarks/evidence/c.json",
    ]
    bundle = mod.build_synthetic_bundle(
        target_field="rights_evidence",
        references=refs,
    )

    assert bundle["reference_count"] == 3
    assert set(bundle["evidence_references"]) == set(refs)
    assert bundle["ordering_semantics"] == mod.SERIALIZATION_ORDERING
    assert bundle["legal_sufficiency_established"] is False
    assert bundle["evidentiary_priority_established"] is False
    assert bundle["underlying_evidence_rewritten"] is False


def test_bundle_builder_order_is_serialization_only_and_deterministic():
    refs_a = ["z", "a", "m"]
    refs_b = ["m", "z", "a"]

    a = mod.build_synthetic_bundle(
        target_field="provenance_evidence",
        references=refs_a,
    )
    b = mod.build_synthetic_bundle(
        target_field="provenance_evidence",
        references=refs_b,
    )

    assert mod.canonical_json_bytes(a) == mod.canonical_json_bytes(b)
    assert a["ordering_semantics"] == (
        "LEXICOGRAPHIC_SERIALIZATION_ONLY_NO_AUTHORITY"
    )


def test_bundle_builder_rejects_duplicate_references():
    try:
        mod.build_synthetic_bundle(
            target_field="rights_evidence",
            references=["x", "x"],
        )
    except ValueError as exc:
        assert "distinct" in str(exc)
    else:
        raise AssertionError("duplicate references must fail")


def test_bundle_validation_detects_reference_loss():
    refs = ["a", "b", "c"]
    bundle = mod.build_synthetic_bundle(
        target_field="rights_evidence",
        references=refs,
    )
    bundle["evidence_references"] = ["a", "b"]
    findings = mod.validate_synthetic_bundle(
        bundle=bundle,
        expected_field="rights_evidence",
        expected_references=refs,
    )
    assert "bundle does not preserve exact evidence reference set" in findings


def test_bundle_validation_detects_priority_promotion():
    refs = ["a", "b"]
    bundle = mod.build_synthetic_bundle(
        target_field="rights_evidence",
        references=refs,
    )
    bundle["evidentiary_priority_established"] = True
    findings = mod.validate_synthetic_bundle(
        bundle=bundle,
        expected_field="rights_evidence",
        expected_references=refs,
    )
    assert "evidentiary priority promotion" in findings


def test_static_candidate_contract_has_6_plus_2_architecture():
    candidate, freeze, _hyp, _surface, manifest = controls()

    architecture = candidate["candidate_architecture"]
    assert len(architecture["authority_or_canonical_fields"]) == 6
    assert architecture["authority_or_canonical_resolution"] == (
        "EXPLICIT_DECLARATION_ONLY_NO_INFERENCE"
    )
    assert architecture["evidence_reference_fields"] == [
        "rights_evidence",
        "provenance_evidence",
    ]
    assert architecture["evidence_reference_resolution"] == (
        "SCALAR_REFERENCE_TO_CANONICAL_TRACKED_BUNDLE"
    )

    assert freeze["explicit_declaration_field_count"] == 6
    assert freeze["tracked_evidence_bundle_reference_field_count"] == 2
    assert freeze["candidate_evaluated"] is False
    assert freeze["candidate_adopted"] is False

    assert "repository-relative tracked evidence reference" in (
        manifest["fields"]["rights_evidence"]["rule"]
    )
    assert "repository-relative tracked evidence reference" in (
        manifest["fields"]["provenance_evidence"]["rule"]
    )


def test_real_candidate_tracked_inputs_evaluate_structurally_feasible():
    candidate, _freeze, hyp, surface, manifest = controls()

    result = mod.evaluate_candidate(
        candidate=candidate,
        hyp_result=hyp,
        surface_result=surface,
        manifest_contract=manifest,
    )

    # This is a deterministic contract/synthetic-fixture test, not the
    # separately authorized formal evaluation run.
    assert result["disposition"] == mod.DISPOSITION_PASS
    assert result["finding_count"] == 0
    assert result["candidate_field_count"] == 8
    assert result["explicit_declaration_field_count"] == 6
    assert result["tracked_evidence_bundle_reference_field_count"] == 2
    assert all(
        row["structural_check_pass"]
        for row in result["declaration_checks"]
    )
    assert all(
        row["structural_check_pass"]
        for row in result["bundle_checks"]
    )
    assert result[
        "current_manifest_contract_represents_all_8_mechanisms"
    ] is True
    assert result["machine_inference_of_declaration_values_required"] is False
    assert result["precedence_among_evidence_references_required"] is False
    assert result["semantic_projection_required"] is False
    assert result["manifest_contract_change_required"] is False


def test_structural_pass_does_not_adopt_or_create_values_or_bundles():
    candidate, _freeze, hyp, surface, manifest = controls()
    result = mod.evaluate_candidate(
        candidate=candidate,
        hyp_result=hyp,
        surface_result=surface,
        manifest_contract=manifest,
    )

    assert result["candidate_adopted"] is False
    assert result["declaration_values_created"] is False
    assert result["real_evidence_bundles_created"] is False
    assert result["manifest_contract_changed"] is False
    assert result["schema_mutated"] is False
    assert result["evidence_rewritten"] is False
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False
    assert result["cross_source_generality_established"] is False
    assert result["held_out_validation_required_for_generalization"] is True
    assert result["causal_root_cause"] == "NOT_ESTABLISHED"
    assert result["rights_established"] is False
    assert result["provenance_established"] is False
    assert result["provider_model_network_calls"] == 0
    assert result["ontology_007r1_execution_authorized"] is False
    assert result["q011_creation_authorized"] is False


def test_source_manifest_remains_absent():
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
