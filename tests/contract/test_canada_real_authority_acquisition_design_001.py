from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/characterize_canada_real_authority_acquisition_design_001.py"

spec = importlib.util.spec_from_file_location("realdesign001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["realdesign001"] = m
spec.loader.exec_module(m)


def row(specimen_id, family, field):
    return {
        "specimen_id": specimen_id,
        "channel_type": family,
        "target_field": field,
        "structural_sufficiency_supported": True,
        "bounded_fact_lever_minimality_supported": True,
        "real_authority_established": False,
        "real_authority_act_created": False,
        "declaration_value_created": False,
    }


def synthetic_source():
    rows = [
        row("SYN-PS", "INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION", "provenance_status"),
        row("SYN-RD-EXT", "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION", "redistribution_status"),
        row("SYN-RD-INT", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", "redistribution_status"),
        row("SYN-RB-EXT", "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION", "rights_basis"),
        row("SYN-RB-INT", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", "rights_basis"),
        row("SYN-RS", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", "rights_status"),
        row("SYN-SK-INT", "INSTITUTIONAL_ADMISSION_DECLARATION", "source_kind"),
        row("SYN-SK-EXT", "EXPLICIT_SOURCE_ORIGIN_DECLARATION", "source_kind"),
        row("SYN-SL", "PUBLISHER_CANONICAL_LOCATOR_DECLARATION", "source_locator"),
    ]
    return {
        "status": "EXECUTED_DETERMINISTIC_SYNTHETIC_ANALYSIS",
        "disposition": "SYNTHETIC_AUTHORITY_ACT_STRUCTURAL_SUFFICIENCY_SUPPORTED_CA3",
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
            "synthetic_specimen_count": 9,
            "target_field_count": 6,
        },
        "specimen_count_evaluated": 9,
        "structural_sufficiency_pass_count": 9,
        "bounded_fact_lever_minimality_pass_count": 9,
        "finding_count": 0,
        "real_authority_established": False,
        "real_authority_act_created": False,
        "declaration_values_created": False,
        "specimen_results": rows,
    }


def synthetic_contract():
    c = m.load_json(m.CONTRACT)
    return copy.deepcopy(c)


def test_bound_bytes_verify_without_real_semantic_analysis():
    m.verify_bound_bytes_only()


def test_six_families_and_field_coverage_reconstruct_exactly():
    rows = m.validate_source_result(synthetic_source())
    families = m.derive_family_fields(rows)
    assert len(families) == 6
    assert families["EXTERNAL_RIGHTS_AUTHORITY_DECLARATION"] == [
        "redistribution_status",
        "rights_basis",
    ]
    assert families["INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION"] == [
        "redistribution_status",
        "rights_basis",
        "rights_status",
    ]


def test_minimum_cover_is_four_with_two_tied_sets():
    rows = m.validate_source_result(synthetic_source())
    families = m.derive_family_fields(rows)
    minimum, covers = m.minimum_cover_sets(families)
    assert minimum == 4
    assert len(covers) == 2
    assert all(len(x) == 4 for x in covers)


def test_minimum_cover_does_not_imply_preference_or_authority():
    result = m.characterize(synthetic_source(), synthetic_contract())
    cover = result["minimum_channel_family_cover"]
    assert cover["descriptive_only"] is True
    assert cover["legal_preference_implied"] is False
    assert cover["authority_implied"] is False


def test_external_internal_partition_is_three_and_three():
    result = m.characterize(synthetic_source(), synthetic_contract())
    assert len(result["path_classes"]["EXTERNAL_ACTOR_PATH"]["families"]) == 3
    assert len(result["path_classes"]["INTERNAL_GOVERNANCE_PATH"]["families"]) == 3


def test_every_family_has_exact_real_authority_evidence_vector():
    result = m.characterize(synthetic_source(), synthetic_contract())
    for req in result["channel_family_requirements"].values():
        assert req["real_authority_evidence_required"] == list(m.REQUIRED_EVIDENCE)
        assert req["oic_self_issuance_permitted"] is False
        assert req["synthetic_result_promotable_to_real_authority"] is False
        assert req["currently_real_authority_established"] is False


def test_internal_families_require_preexisting_delegation():
    result = m.characterize(synthetic_source(), synthetic_contract())
    for req in result["channel_family_requirements"].values():
        if req["actor_origin"] == "INTERNAL_INSTITUTIONAL":
            assert req["preexisting_internal_delegation_required"] is True


def test_external_families_do_not_require_internal_delegation():
    result = m.characterize(synthetic_source(), synthetic_contract())
    for req in result["channel_family_requirements"].values():
        if req["actor_origin"] == "EXTERNAL":
            assert req["preexisting_internal_delegation_required"] is False


def test_missing_evidence_vector_fails_closed():
    c = synthetic_contract()
    c["channel_family_requirements"]["EXPLICIT_SOURCE_ORIGIN_DECLARATION"][
        "real_authority_evidence_required"
    ] = ["actor_identity_evidence"]
    result = m.characterize(synthetic_source(), c)
    assert result["disposition"] == (
        "REAL_AUTHORITY_ACQUISITION_DESIGN_INCOMPLETE_FAIL_CLOSED"
    )
    assert result["finding_count"] > 0


def test_self_issuance_permission_fails_closed():
    c = synthetic_contract()
    c["channel_family_requirements"]["INSTITUTIONAL_ADMISSION_DECLARATION"][
        "oic_self_issuance_permitted"
    ] = True
    result = m.characterize(synthetic_source(), c)
    assert result["disposition"] == (
        "REAL_AUTHORITY_ACQUISITION_DESIGN_INCOMPLETE_FAIL_CLOSED"
    )
    assert result["finding_count"] > 0


def test_synthetic_promotion_permission_fails_closed():
    c = synthetic_contract()
    c["channel_family_requirements"]["EXTERNAL_RIGHTS_AUTHORITY_DECLARATION"][
        "synthetic_result_promotable_to_real_authority"
    ] = True
    result = m.characterize(synthetic_source(), c)
    assert result["finding_count"] > 0


def test_contract_field_coverage_mismatch_fails_closed():
    c = synthetic_contract()
    c["channel_family_requirements"]["PUBLISHER_CANONICAL_LOCATOR_DECLARATION"][
        "structurally_supported_target_fields"
    ] = ["source_kind"]
    result = m.characterize(synthetic_source(), c)
    assert result["finding_count"] > 0


def test_source_real_authority_promotion_is_rejected():
    s = synthetic_source()
    s["real_authority_established"] = True
    try:
        m.characterize(s, synthetic_contract())
    except ValueError as exc:
        assert "source claims real authority" in str(exc)
    else:
        raise AssertionError("real-authority promotion should fail")


def test_missing_structural_pass_is_rejected():
    s = synthetic_source()
    s["specimen_results"][0]["structural_sufficiency_supported"] = False
    try:
        m.characterize(s, synthetic_contract())
    except ValueError as exc:
        assert "structural sufficiency missing" in str(exc)
    else:
        raise AssertionError("failed synthetic specimen should fail")


def test_complete_design_passes_without_real_authority():
    result = m.characterize(synthetic_source(), synthetic_contract())
    assert result["disposition"] == "REAL_AUTHORITY_ACQUISITION_SURFACE_DESIGNED_CA3"
    assert result["finding_count"] == 0
    assert result["design_executed"] is True
    assert result["real_authority_evidence_acquired"] is False
    assert result["real_authority_established"] is False
    assert result["real_authority_act_created"] is False
    assert result["external_actor_contacted"] is False
    assert result["internal_delegation_created"] is False
    assert result["declaration_values_created"] is False
    assert result["authority_channel_selected"] is False
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False
