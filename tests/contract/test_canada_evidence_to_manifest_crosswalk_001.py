from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/crosswalk_canada_evidence_to_manifest_001.py"

spec = importlib.util.spec_from_file_location("crosswalk001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["crosswalk001"] = mod
spec.loader.exec_module(mod)


def controls():
    return mod.load_controls()


def rec(
    key,
    value,
    *,
    pointer="/record/value",
    artifact="synthetic.json",
    blob="a" * 40,
    value_type=None,
):
    if value_type is None:
        if value is None:
            value_type = "null"
        elif isinstance(value, bool):
            value_type = "boolean"
        elif isinstance(value, (int, float)):
            value_type = "number"
        else:
            value_type = "string"

    return {
        "artifact_path": artifact,
        "artifact_git_blob_sha": blob,
        "json_pointer": pointer,
        "key": key,
        "value_type": value_type,
        "array_length": None,
        "scalar_mode": "EXACT",
        "scalar_value": value,
        "scalar_sha256": None,
        "scalar_utf8_byte_length": None,
    }


def scoped(*extra):
    return [
        rec(
            "source_id",
            "CA-3",
            pointer="/record/source_id",
        ),
        *extra,
    ]


def evaluate(records):
    contract, _freeze, manifest = controls()
    return mod.evaluate_records(
        records,
        contract=contract,
        manifest_contract=manifest,
    )


def field(result, name):
    return next(
        item
        for item in result["field_results"]
        if item["target_field"] == name
    )


def test_source_id_establishes_only_in_explicit_ca3_scope():
    result = evaluate(scoped())
    item = field(result, "source_id")
    assert item["state"] == mod.ESTABLISHED_DIRECT
    assert item["value"] == "CA-3"


def test_candidate_outside_ca3_scope_does_not_establish():
    records = [
        rec("source_id", "OTHER", pointer="/record/source_id"),
        rec("official_url", "https://example.invalid/x", pointer="/record/official_url"),
    ]
    result = evaluate(records)
    item = field(result, "source_locator")
    assert item["state"] == mod.OUT_OF_SCOPE
    assert item["value"] is None


def test_unlisted_similar_key_is_ignored():
    records = scoped(
        rec(
            "canonical_url",
            "https://example.invalid/ca3",
            pointer="/record/canonical_url",
        )
    )
    result = evaluate(records)
    item = field(result, "source_locator")
    assert item["state"] == mod.MISSING


def test_source_kind_requires_exact_contract_enum():
    good = evaluate(
        scoped(
            rec("kind", "public", pointer="/record/kind")
        )
    )
    assert field(good, "source_kind")["state"] == mod.ESTABLISHED_DIRECT
    assert field(good, "source_kind")["value"] == "public"

    bad = evaluate(
        scoped(
            rec("kind", "government-document", pointer="/record/kind")
        )
    )
    assert field(bad, "source_kind")["value"] is None


def test_source_locator_accepts_exact_http_uri_only():
    result = evaluate(
        scoped(
            rec(
                "official_url",
                "https://example.invalid/ca3",
                pointer="/record/official_url",
            )
        )
    )
    item = field(result, "source_locator")
    assert item["state"] == mod.ESTABLISHED_DIRECT
    assert item["value"] == "https://example.invalid/ca3"


def test_multiple_distinct_source_locators_are_contradictory():
    result = evaluate(
        scoped(
            rec(
                "official_url",
                "https://example.invalid/a",
                pointer="/record/official_url",
            ),
            rec(
                "final_url",
                "https://example.invalid/b",
                pointer="/record/final_url",
            ),
        )
    )
    item = field(result, "source_locator")
    assert item["state"] == mod.CONTRADICTORY
    assert item["value"] is None


def test_local_path_does_not_promote_receipt_path():
    result = evaluate(
        scoped(
            rec(
                "receipt_path",
                "receipts/CA-3.json",
                pointer="/record/receipt_path",
            )
        )
    )
    item = field(result, "local_path")
    assert item["value"] is None


def test_local_path_accepts_frozen_bytes_path():
    result = evaluate(
        scoped(
            rec(
                "frozen_bytes_path",
                "benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml",
                pointer="/record/frozen_bytes_path",
            )
        )
    )
    item = field(result, "local_path")
    assert item["state"] == mod.ESTABLISHED_DIRECT


def test_content_hash_requires_sha256_same_context_with_frozen_bytes_path():
    result = evaluate(
        scoped(
            rec(
                "frozen_bytes_path",
                "benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml",
                pointer="/record/frozen_bytes_path",
            ),
            rec(
                "sha256",
                "b" * 64,
                pointer="/record/sha256",
            ),
        )
    )
    item = field(result, "content_hash")
    assert item["state"] == mod.ESTABLISHED_DERIVED
    assert item["value"] == "sha256:" + ("b" * 64)


def test_evidence_sha256_is_not_promoted_to_content_hash():
    result = evaluate(
        scoped(
            rec(
                "evidence_sha256",
                "b" * 64,
                pointer="/record/evidence_sha256",
            )
        )
    )
    assert field(result, "content_hash")["value"] is None


def test_rights_basis_requires_exact_manifest_enum_no_translation():
    result = evaluate(
        scoped(
            rec(
                "internal_research_use_basis",
                "government source publicly available",
                pointer="/record/internal_research_use_basis",
            )
        )
    )
    assert field(result, "rights_basis")["value"] is None

    direct = evaluate(
        scoped(
            rec(
                "disposition_basis",
                "open_license",
                pointer="/record/disposition_basis",
            )
        )
    )
    assert field(direct, "rights_basis")["value"] == "open_license"


def test_rights_status_pending_does_not_promote_to_verified():
    result = evaluate(
        scoped(
            rec(
                "rights_disposition",
                "PUBLISHER_PERMISSION_REQUIRED",
                pointer="/record/rights_disposition",
            )
        )
    )
    assert field(result, "rights_status")["value"] is None


def test_rights_status_exact_verified_may_establish():
    result = evaluate(
        scoped(
            rec(
                "rights_disposition",
                "verified",
                pointer="/record/rights_disposition",
            )
        )
    )
    assert field(result, "rights_status")["value"] == "verified"


def test_provenance_status_captured_true_does_not_promote_to_verified():
    result = evaluate(
        scoped(
            rec(
                "captured",
                True,
                pointer="/record/captured",
            )
        )
    )
    assert field(result, "provenance_status")["value"] is None


def test_public_repository_permission_boolean_maps_deterministically():
    yes = evaluate(
        scoped(
            rec(
                "public_repository_redistribution_permission",
                True,
                pointer="/record/public_repository_redistribution_permission",
            )
        )
    )
    item = field(yes, "redistribution_status")
    assert item["state"] == mod.ESTABLISHED_DERIVED
    assert item["value"] == "permitted"

    no = evaluate(
        scoped(
            rec(
                "public_repository_redistribution_permission",
                False,
                pointer="/record/public_repository_redistribution_permission",
            )
        )
    )
    assert field(no, "redistribution_status")["value"] == "not_permitted"


def test_internal_research_use_does_not_map_to_redistribution():
    result = evaluate(
        scoped(
            rec(
                "internal_research_use",
                True,
                pointer="/record/internal_research_use",
            )
        )
    )
    assert field(result, "redistribution_status")["state"] == mod.MISSING


def test_capture_timestamp_is_not_promoted_to_acquisition_timestamp():
    result = evaluate(
        scoped(
            rec(
                "capture_utc",
                "2026-09-02T12:00:00+00:00",
                pointer="/record/capture_utc",
            )
        )
    )
    assert field(result, "acquired_or_generated_at")["value"] is None


def test_retrieval_timestamp_requires_explicit_acquisition_context():
    no_context = evaluate(
        scoped(
            rec(
                "retrieval_utc",
                "2026-09-02T12:00:00+00:00",
                pointer="/record/retrieval_utc",
            )
        )
    )
    assert field(no_context, "acquired_or_generated_at")["value"] is None

    with_context = evaluate(
        scoped(
            rec(
                "acquisition_tool",
                "curl",
                pointer="/record/acquisition_tool",
            ),
            rec(
                "retrieval_utc",
                "2026-09-02T12:00:00+00:00",
                pointer="/record/retrieval_utc",
            ),
        )
    )
    item = field(with_context, "acquired_or_generated_at")
    assert item["state"] == mod.ESTABLISHED_DIRECT
    assert item["value"] == "2026-09-02T12:00:00+00:00"


def test_same_target_value_from_multiple_support_records_can_establish():
    result = evaluate(
        scoped(
            rec(
                "official_url",
                "https://example.invalid/ca3",
                pointer="/record/official_url",
            ),
            rec(
                "final_url",
                "https://example.invalid/ca3",
                pointer="/record/final_url",
            ),
        )
    )
    item = field(result, "source_locator")
    assert item["state"] == mod.ESTABLISHED_DIRECT
    assert item["admissible_value_count"] == 1


def test_incomplete_crosswalk_fails_closed():
    result = evaluate(scoped())
    assert result["disposition"] == mod.DISPOSITION_INCOMPLETE
    assert result["established_field_count"] < 12
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False


def test_output_never_claims_rights_provenance_or_downstream_authority():
    result = evaluate(scoped())
    assert result["rights_established"] is False
    assert result["provenance_established"] is False
    assert result["legal_clearance_established"] is False
    assert result["provider_model_network_calls"] == 0
    assert result["ontology_007r1_execution_authorized"] is False
    assert result["q011_creation_authorized"] is False
    assert result["canonicalization_authorized"] is False
    assert result["institutional_ir_authorized"] is False
    assert result["control_envelope_authorized"] is False
    assert result["rego_compilation_authorized"] is False
    assert result["runtime_evaluation_authorized"] is False


def test_static_controls_keep_real_receipt_and_manifest_closed():
    contract, freeze, _manifest = controls()

    assert contract["record_level_inspection_scope"]["source"] == (
        "PRESERVED_ONE_SHOT_INVENTORY_RECEIPT_ONLY"
    )
    assert contract["real_evidence_reread_authorized"] is False
    assert contract["source_xml_inspection_authorized"] is False
    assert contract["source_manifest_creation_authorized"] is False
    assert contract["source_manifest_population_authorized"] is False

    assert freeze["record_level_inventory_receipt_inspected_by_this_work_order"] is False
    assert freeze["crosswalk_execution_authorized_now"] is False
    assert freeze["source_manifest_creation_authorized"] is False
    assert freeze["source_manifest_population_authorized"] is False


def test_real_source_manifest_remains_absent():
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
