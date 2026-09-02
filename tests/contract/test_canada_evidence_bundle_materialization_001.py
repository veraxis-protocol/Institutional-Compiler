from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/materialize_canada_evidence_bundles_001.py"

spec = importlib.util.spec_from_file_location("bundle001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["bundle001"] = mod
spec.loader.exec_module(mod)


def support(mapped):
    row = {
        "key": "synthetic_key",
        "artifact_path": "synthetic/artifact.json",
        "source_scope_pointer": "$.synthetic",
        "raw_value": "synthetic",
        "mapping_class": "EXACT_SYNTHETIC",
        "transformation": "NONE",
    }
    if mapped is not ...:
        row["mapped_value"] = mapped
    return row


def synthetic_receipt(
    rights_refs=None,
    provenance_refs=None,
):
    rights_refs = rights_refs or ["r4", "r1", "r3", "r2"]
    provenance_refs = provenance_refs or ["p3", "p1", "p2"]

    return {
        "work_order":
            "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001",
        "status":
            "EXECUTED_READ_ONLY",
        "disposition":
            "CROSSWALK_INCOMPLETE_FAIL_CLOSED",
        "target_field_count":
            12,
        "established_field_count":
            4,
        "field_results": [
            {
                "target_field":
                    "rights_evidence",
                "state":
                    "CONTRADICTORY_NOT_ESTABLISHED",
                "admissible_value_count":
                    4,
                "support":
                    [support(v) for v in rights_refs]
                    + [support(None), support(...)],
            },
            {
                "target_field":
                    "provenance_evidence",
                "state":
                    "CONTRADICTORY_NOT_ESTABLISHED",
                "admissible_value_count":
                    3,
                "support":
                    [support(v) for v in provenance_refs]
                    + [support(None)],
            },
        ],
    }


def test_static_controls_load_without_receipt_content_dependency():
    contract, freeze, candidate = mod.load_controls()
    assert contract["status"] == "FROZEN_NOT_EXECUTED"
    assert freeze["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert candidate["status"] == (
        "CLOSED_EXECUTED_CANDIDATE_STRUCTURALLY_FEASIBLE_CA3"
    )


def test_exact_reference_extraction_ignores_null_and_missing():
    receipt = synthetic_receipt()
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="rights_evidence",
        expected_count=4,
    )
    assert findings == []
    assert refs == ["r1", "r2", "r3", "r4"]


def test_exact_reference_extraction_deduplicates_exact_identity_only():
    receipt = synthetic_receipt(
        rights_refs=["r1", "r2", "r3", "r4", "r4"],
    )
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="rights_evidence",
        expected_count=4,
    )
    assert findings == []
    assert refs == ["r1", "r2", "r3", "r4"]


def test_case_and_whitespace_are_not_normalized():
    receipt = synthetic_receipt(
        rights_refs=["A", "a", " a", "a "],
    )
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="rights_evidence",
        expected_count=4,
    )
    assert findings == []
    assert set(refs) == {"A", "a", " a", "a "}


def test_non_string_mapped_value_fails_closed():
    receipt = synthetic_receipt(
        rights_refs=["r1", "r2", "r3", 4],
    )
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="rights_evidence",
        expected_count=4,
    )
    assert len(refs) == 3
    assert any("not a string" in item for item in findings)


def test_wrong_exact_count_fails_closed():
    receipt = synthetic_receipt(
        provenance_refs=["p1", "p2"],
    )
    # Keep the frozen prior count at 3 while only 2 exact mapped values exist.
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="provenance_evidence",
        expected_count=3,
    )
    assert refs == ["p1", "p2"]
    assert any("exact distinct mapped_value count" in item for item in findings)


def test_duplicate_target_field_fails_closed():
    receipt = synthetic_receipt()
    receipt["field_results"].append(receipt["field_results"][0].copy())
    refs, findings = mod.extract_exact_mapped_references(
        receipt,
        target="rights_evidence",
        expected_count=4,
    )
    assert refs == []
    assert findings == [
        "rights_evidence: expected exactly one field result, observed 2"
    ]


def test_bundle_serialization_is_deterministic_and_non_authoritative():
    bundle_a = mod.build_bundle(
        target="rights_evidence",
        references=["r4", "r1", "r3", "r2"],
        source_receipt_sha256="a" * 64,
    )
    bundle_b = mod.build_bundle(
        target="rights_evidence",
        references=["r2", "r3", "r1", "r4"],
        source_receipt_sha256="a" * 64,
    )

    assert mod.canonical_json_bytes(bundle_a) == mod.canonical_json_bytes(bundle_b)
    assert bundle_a["evidence_references"] == ["r1", "r2", "r3", "r4"]
    assert bundle_a["ordering_semantics"] == (
        "LEXICOGRAPHIC_SERIALIZATION_ONLY_NO_AUTHORITY"
    )
    assert bundle_a["legal_sufficiency_established"] is False
    assert bundle_a["evidentiary_priority_established"] is False
    assert bundle_a["underlying_evidence_rewritten"] is False


def test_materialization_success_preserves_4_and_3_exact_sets():
    result = mod.materialize_receipt(
        synthetic_receipt(),
        source_receipt_sha256="b" * 64,
    )
    assert result["disposition"] == mod.PASS
    assert result["finding_count"] == 0
    assert result["bundle_candidate_count"] == 2

    rights = result["bundle_candidates"]["rights_evidence"]
    provenance = result["bundle_candidates"]["provenance_evidence"]

    assert rights["evidence_references"] == ["r1", "r2", "r3", "r4"]
    assert provenance["evidence_references"] == ["p1", "p2", "p3"]
    assert rights["reference_count"] == 4
    assert provenance["reference_count"] == 3


def test_materialization_pass_does_not_promote_authority():
    result = mod.materialize_receipt(
        synthetic_receipt(),
        source_receipt_sha256="c" * 64,
    )
    assert result["disposition"] == mod.PASS
    assert result["declaration_fields_touched"] == []
    assert result["candidate_002_adopted"] is False
    assert result["precedence_assigned"] is False
    assert result["legal_sufficiency_established"] is False
    assert result["evidentiary_priority_established"] is False
    assert result["underlying_evidence_rewritten"] is False
    assert result["real_underlying_evidence_reread"] is False
    assert result["tracked_bundle_files_created"] is False
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False
    assert result["rights_established"] is False
    assert result["provenance_established"] is False
    assert result["provider_model_network_calls"] == 0


def test_wrong_source_receipt_identity_fails_closed():
    receipt = synthetic_receipt()
    receipt["work_order"] = "WRONG"
    result = mod.materialize_receipt(
        receipt,
        source_receipt_sha256="d" * 64,
    )
    assert result["disposition"] == mod.FAIL
    assert result["finding_count"] > 0


def test_local_output_dir_must_be_under_dot_local(tmp_path):
    with pytest.raises(ValueError, match="must be inside repository .local"):
        mod._validate_local_output_dir(tmp_path)


def test_local_candidate_write_is_exact_and_only_two_files(tmp_path, monkeypatch):
    # Use a temporary .local child inside the repository so path policy is real.
    local_root = ROOT / ".local" / "synthetic-bundle-materialization-test"
    if local_root.exists():
        raise AssertionError(f"synthetic local test path already exists: {local_root}")

    result = mod.materialize_receipt(
        synthetic_receipt(),
        source_receipt_sha256="e" * 64,
    )
    assert result["disposition"] == mod.PASS

    try:
        outputs = mod.write_local_bundle_candidates(
            result,
            output_dir=local_root,
        )
        assert set(outputs) == {"rights_evidence", "provenance_evidence"}

        files = sorted(p.name for p in local_root.iterdir())
        assert files == [
            "provenance_evidence-bundle-v0.1.json",
            "rights_evidence-bundle-v0.1.json",
        ]

        for target, relative in outputs.items():
            path = ROOT / relative
            expected = mod.canonical_json_bytes(
                result["bundle_candidates"][target]
            )
            assert path.read_bytes() == expected
    finally:
        if local_root.exists():
            for child in local_root.iterdir():
                child.unlink()
            local_root.rmdir()


def test_tracked_bundle_destinations_and_source_manifest_remain_absent():
    for relative in mod.TRACKED_PATHS.values():
        assert not (ROOT / relative).exists()
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
