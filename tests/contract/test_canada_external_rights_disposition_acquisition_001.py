from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/evaluate_canada_external_rights_disposition_acquisition_001.py"

spec = importlib.util.spec_from_file_location("rights001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["rights001"] = m
spec.loader.exec_module(m)


def good_actor():
    return {
        "actor_full_name": "Synthetic Qualified Actor",
        "actor_role_or_professional_capacity": "Synthetic Canadian rights counsel",
        "qualification_class":
            "licensed_or_authorized_counsel_with_relevant_canadian_copyright_or_public-sector-rights_competence",
        "authority_basis": "Synthetic fixture authority basis",
        "authority_basis_reference": "https://example.invalid/authority",
        "authority_reference_independently_verified": True,
        "authority_scope_covers_ca3": True,
        "authority_scope_covers_rights_basis": True,
        "authority_scope_covers_redistribution_status": True,
    }


def good_act(
    rights_basis="permission",
    redistribution_status="permitted",
):
    return {
        "source_id": "CA-3",
        "actor_full_name": "Synthetic Qualified Actor",
        "actor_role_or_professional_capacity": "Synthetic Canadian rights counsel",
        "act_status": "final",
        "issued_at": "2026-09-03T00:00:00Z",
        "rights_basis": rights_basis,
        "redistribution_status": redistribution_status,
        "rights_basis_reason": "Synthetic reason",
        "redistribution_status_reason": "Synthetic reason",
        "supporting_evidence_references": ["https://example.invalid/evidence"],
        "limitations_or_conditions": [],
        "actor_attestation": "Synthetic completed disposition.",
        "raw_act_sha256": "sha256:" + "a" * 64,
    }


def test_frozen_preregistration_bytes_verify():
    m.verify_preregistered_bytes()


def test_neutral_request_packet_preselects_no_answer():
    packet = m.generate_neutral_request_packet()
    assert packet["status"] == "DRAFT_NOT_SENT"
    assert packet["source"]["source_id"] == "CA-3"
    assert packet["questions"]["rights_basis"]["selected_value"] is None
    assert packet["questions"]["redistribution_status"]["selected_value"] is None
    assert packet["questions"]["rights_basis"]["select_exactly_one_from"] == list(
        m.RIGHTS_BASIS_ALLOWED
    )
    assert packet["questions"]["redistribution_status"]["select_exactly_one_from"] == list(
        m.REDISTRIBUTION_ALLOWED
    )
    assert packet["candidate_values_preselected"] is False
    assert packet["request_sent"] is False
    assert packet["external_actor_contacted"] is False


def test_request_packet_does_not_request_rights_status_or_other_domains():
    packet = m.generate_neutral_request_packet()
    assert packet["scope"]["rights_basis"] is True
    assert packet["scope"]["redistribution_status"] is True
    assert packet["scope"]["rights_status"] is False
    assert packet["scope"]["source_kind"] is False
    assert packet["scope"]["source_locator"] is False
    assert packet["scope"]["provenance"] is False


def test_synthetic_actor_structural_completeness_does_not_establish_real_actor():
    result = m.assess_actor_qualification_evidence(good_actor())
    assert result["structurally_complete"] is True
    assert result["assessment"] == (
        "ACTOR_QUALIFICATION_EVIDENCE_STRUCTURALLY_COMPLETE"
    )
    assert result["real_actor_qualification_established_by_oic"] is False


def test_actor_title_alone_is_insufficient():
    actor = good_actor()
    actor["authority_basis"] = ""
    actor["authority_basis_reference"] = ""
    actor["authority_reference_independently_verified"] = False
    result = m.assess_actor_qualification_evidence(actor)
    assert result["structurally_complete"] is False


def test_actor_authority_reference_must_be_independently_verified():
    actor = good_actor()
    actor["authority_reference_independently_verified"] = False
    result = m.assess_actor_qualification_evidence(actor)
    assert result["structurally_complete"] is False
    assert result["checks"]["authority_reference_independently_verified"] is False


def test_actor_scope_must_cover_both_target_fields_and_ca3():
    for key in (
        "authority_scope_covers_ca3",
        "authority_scope_covers_rights_basis",
        "authority_scope_covers_redistribution_status",
    ):
        actor = good_actor()
        actor[key] = False
        result = m.assess_actor_qualification_evidence(actor)
        assert result["structurally_complete"] is False


def test_valid_completed_act_schema():
    result = m.validate_received_disposition(good_act())
    assert result["schema_valid"] is True
    assert result["finding_count"] == 0
    assert result["rights_basis_value_observed"] == "permission"
    assert result["redistribution_status_value_observed"] == "permitted"


def test_pending_and_draft_are_not_completed_acts():
    for status in ("pending", "draft"):
        act = good_act()
        act["act_status"] = status
        result = m.validate_received_disposition(act)
        assert result["schema_valid"] is False
        assert "act_status must be final or completed" in result["findings"]


def test_both_target_fields_are_required():
    act = good_act()
    act["rights_basis"] = None
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False

    act = good_act()
    act["redistribution_status"] = None
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False


def test_no_enum_normalization_or_synonym_mapping():
    act = good_act(rights_basis="crown_copyright")
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False
    assert result["rights_basis_value_observed"] is None

    act = good_act(redistribution_status="allowed")
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False
    assert result["redistribution_status_value_observed"] is None


def test_unknown_redistribution_is_valid_external_value_but_not_manifest_pass():
    result = m.validate_received_disposition(
        good_act(redistribution_status="unknown")
    )
    assert result["schema_valid"] is True
    assert result["redistribution_status_value_observed"] == "unknown"
    assert result["unknown_redistribution_is_valid_external_value"] is True
    assert result["unknown_redistribution_implies_manifest_pass"] is False


def test_raw_act_digest_shape_required():
    act = good_act()
    act["raw_act_sha256"] = "abc"
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False


def test_supporting_evidence_reference_required():
    act = good_act()
    act["supporting_evidence_references"] = []
    result = m.validate_received_disposition(act)
    assert result["schema_valid"] is False


def test_no_actor_or_no_act_is_not_established_not_inferred():
    result = m.evaluate_authority(
        actor_evidence=None,
        received_act=None,
        raw_act_digest_verified=False,
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["external_rights_authority_evidence_established"] is False
    assert result["rights_basis_value_observed"] is None
    assert result["redistribution_status_value_observed"] is None


def test_structurally_complete_synthetic_fixture_can_pass_bounded_authority_logic():
    result = m.evaluate_authority(
        actor_evidence=good_actor(),
        received_act=good_act(),
        raw_act_digest_verified=True,
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["external_rights_authority_evidence_established"] is True
    assert result["rights_basis_value_observed"] == "permission"
    assert result["redistribution_status_value_observed"] == "permitted"
    assert result["rights_basis_value_established"] is True
    assert result["redistribution_status_value_established"] is True
    assert all(result["standing_requirements"].values())
    assert result["declaration_values_created_by_oic"] is False
    assert result["rights_status_established"] is False
    assert result["source_manifest_population_authorized"] is False


def test_unknown_can_be_externally_established_without_manifest_authorization():
    result = m.evaluate_authority(
        actor_evidence=good_actor(),
        received_act=good_act(redistribution_status="unknown"),
        raw_act_digest_verified=True,
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["redistribution_status_value_observed"] == "unknown"
    assert result["redistribution_status_value_established"] is True
    assert result["source_manifest_population_authorized"] is False


def test_unverified_actor_authority_fails_closed():
    actor = good_actor()
    actor["authority_reference_independently_verified"] = False
    result = m.evaluate_authority(
        actor_evidence=actor,
        received_act=good_act(),
        raw_act_digest_verified=True,
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["external_rights_authority_evidence_established"] is False
    assert result["rights_basis_value_established"] is False
    assert result["redistribution_status_value_established"] is False


def test_unverified_act_digest_fails_closed():
    result = m.evaluate_authority(
        actor_evidence=good_actor(),
        received_act=good_act(),
        raw_act_digest_verified=False,
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["standing_requirements"]["act_integrity_or_digest_binding"] is False


def test_external_disposition_never_promotes_rights_status():
    result = m.evaluate_authority(
        actor_evidence=good_actor(),
        received_act=good_act(),
        raw_act_digest_verified=True,
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["rights_status_established"] is False


def test_established_result_never_auto_populates_manifest():
    result = m.evaluate_authority(
        actor_evidence=good_actor(),
        received_act=good_act(),
        raw_act_digest_verified=True,
    )
    assert result["source_manifest_created"] is False
    assert result["source_manifest_population_authorized"] is False
