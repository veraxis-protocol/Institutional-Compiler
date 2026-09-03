from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-manifest-declaration-authority-discrimination-001/"
      "extract_authority_facts_v0.3.py"
)

spec = importlib.util.spec_from_file_location("authority_adapter_v03", ADAPTER_PATH)
assert spec and spec.loader
a = importlib.util.module_from_spec(spec)
sys.modules["authority_adapter_v03"] = a
spec.loader.exec_module(a)
d = a.load_discriminator()


def docs():
    return {
        "MANIFEST_RESULT_SHAPE_CONTRACT": {
            "fields": {field: {"required": True} for field in d.TARGET_FIELDS},
        },
        "ENGINEERING_RIGHTS_REVIEW_RECORD": {
            "records": [{
                "source_id": "CA-3",
                "publisher": "Department of Justice Canada",
                "acquisition_target_role": "CANONICAL_ARTIFACT",
                "reviewer_disposition": "PASS",
                "rights_disposition": "ENGINEERING_ONLY",
                "evidence_hashes": [
                    {"evidence_id": "E-1", "sha256": "a" * 64}
                ],
            }]
        },
        "ACQUISITION_CONTROL_RECORD": {
            "committed_to_repository_source_ids": ["CA-3"],
            "acquisition_tool_version": "v1",
        },
        "ACQUISITION_INDEX": {
            "entries": [{
                "source_id": "CA-3",
                "receipt_id": "R-1",
                "sha256": "b" * 64,
                "retrieval_utc": "2026-01-01T00:00:00Z",
            }]
        },
        "UNSUBMITTED_COUNSEL_REVIEW_REQUEST": {
            "status": "PREPARED_NOT_SUBMITTED",
            "submission_state": "NOT_SUBMITTED",
            "questions": [
                {"source_ids": ["CA-3"], "question_id": "Q1"}
            ],
        },
        "ACTOR_AND_PENDING_ACTION_REGISTER": {
            "status": "REGISTERED_NONE_PERFORMED",
            "actions": [{
                "actor": "COUNSEL",
                "blocks_source_ids": ["CA-3"],
                "status": "PENDING_ENGAGEMENT",
                "actor_detail": "not yet engaged",
            }],
        },
    }


def test_static_adapter_controls_are_bound():
    inventory = a.load_inventory()
    assert inventory["input_count"] == 6
    assert inventory["authority_channels_evaluated"] is False


def test_observational_metadata_never_creates_authority():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.publisher_identity is True
    assert f.source_origin_decl is False
    assert f.publisher_locator_decl is False
    assert f.institutional_admission is False
    assert f.rights_adjudication is False
    assert f.counsel_disposition is False
    assert f.provenance_admission is False
    assert f.existing_rules == frozenset()


def test_evidence_and_temporal_bindings_can_exist_without_authority():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.rights_evidence_binding is True
    assert f.provenance_evidence_binding is True
    assert f.temporal_scope is True
    assert f.rights_adjudication is False
    assert f.provenance_admission is False


def test_explicit_source_origin_act_maps_only_when_complete():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "source_origin_declaration"
    ] = {
        "declarant_identity": "Publisher authority",
        "authority_basis": "explicit basis",
        "act_complete": True,
        "target_field": "source_kind",
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.source_origin_decl is True
    assert f.source_origin_identity is True
    assert f.source_origin_basis is True


def test_incomplete_source_origin_act_does_not_map():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "source_origin_declaration"
    ] = {
        "declarant_identity": "Publisher authority",
        "authority_basis": "explicit basis",
        "act_complete": False,
        "target_field": "source_kind",
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.source_origin_decl is False


def test_explicit_publisher_locator_declaration_maps():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "publisher_canonical_locator_declaration"
    ] = {
        "declarant_identity": "Publisher authority",
        "authority_basis": "canonical publication authority",
        "act_complete": True,
        "target_field": "source_locator",
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.publisher_locator_decl is True


def test_institutional_admission_scopes_only_named_fields():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "institutional_manifest_admission"
    ] = {
        "actor_identity": "Manifest admission officer",
        "authority_basis": "institutional admission charter",
        "act_complete": True,
        "target_fields": ["source_kind", "source_locator"],
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.institutional_admission is True
    assert f.institutional_fields == frozenset({"source_kind", "source_locator"})


def test_engineering_rights_disposition_is_not_rights_adjudication():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.rights_adjudication is False
    assert f.rights_identity is False
    assert f.rights_basis is False


def test_explicit_rights_adjudication_maps():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "institutional_rights_adjudication"
    ] = {
        "actor_identity": "Authorized rights reviewer",
        "authority_basis": "rights review charter",
        "act_complete": True,
        "target_fields": ["rights_basis", "rights_status", "redistribution_status"],
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.rights_adjudication is True
    assert f.rights_identity is True
    assert f.rights_basis is True


def test_pending_counsel_workflow_is_not_disposition():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.counsel_disposition is False
    assert f.counsel_identity is False
    assert f.counsel_basis is False
    assert f.counsel_fields == frozenset()


def test_explicit_completed_counsel_disposition_maps():
    x = docs()
    x["UNSUBMITTED_COUNSEL_REVIEW_REQUEST"]["questions"][0][
        "counsel_disposition"
    ] = {
        "actor_identity": "Named counsel",
        "authority_basis": "retained legal review",
        "act_complete": True,
        "target_manifest_fields": ["rights_basis", "redistribution_status"],
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.counsel_disposition is True
    assert f.counsel_identity is True
    assert f.counsel_basis is True
    assert f.counsel_fields == frozenset({"rights_basis", "redistribution_status"})


def test_acquisition_success_is_not_provenance_admission():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.provenance_admission is False
    assert f.provenance_identity is False
    assert f.provenance_basis is False


def test_explicit_provenance_admission_maps():
    x = docs()
    x["ACQUISITION_INDEX"]["entries"][0][
        "institutional_provenance_admission"
    ] = {
        "actor_identity": "Provenance admission officer",
        "authority_basis": "provenance admission charter",
        "act_complete": True,
        "target_field": "provenance_status",
    }
    f = a.extract_facts_from_docs(x, d)
    assert f.provenance_admission is True
    assert f.provenance_identity is True
    assert f.provenance_basis is True


def test_manifest_requiredness_is_not_derivation_rule():
    f = a.extract_facts_from_docs(docs(), d)
    assert f.existing_rules == frozenset()


def test_explicit_scoped_deterministic_rule_maps():
    x = docs()
    x["MANIFEST_RESULT_SHAPE_CONTRACT"]["manifest_value_derivation_rules"] = [{
        "rule_id": "RULE-1",
        "authority_basis": "frozen contract authority",
        "deterministic_replay": True,
        "target_field": "source_kind",
        "scope": {"source_ids": ["CA-3"]},
    }]
    f = a.extract_facts_from_docs(x, d)
    assert f.existing_rules == frozenset({"source_kind"})


def test_unscoped_or_nondeterministic_rule_does_not_map():
    x = docs()
    x["MANIFEST_RESULT_SHAPE_CONTRACT"]["manifest_value_derivation_rules"] = [{
        "rule_id": "RULE-1",
        "authority_basis": "frozen contract authority",
        "deterministic_replay": False,
        "target_field": "source_kind",
        "scope": {"source_ids": ["CA-3"]},
    }]
    f = a.extract_facts_from_docs(x, d)
    assert f.existing_rules == frozenset()


def test_adapter_plus_discriminator_can_recognize_positive_channel():
    x = docs()
    x["ENGINEERING_RIGHTS_REVIEW_RECORD"]["records"][0][
        "institutional_rights_adjudication"
    ] = {
        "actor_identity": "Authorized rights reviewer",
        "authority_basis": "rights review charter",
        "act_complete": True,
        "target_fields": ["rights_status"],
    }
    f = a.extract_facts_from_docs(x, d)
    row = d.evaluate(
        "rights_status",
        "RS-INSTITUTIONAL-ADJUDICATION",
        "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",
        f,
    )
    assert row["assessment"] == d.PASS_DECL
    assert row["declaration_value_created"] is False


def test_adapter_plus_discriminator_preserves_fail_closed_default():
    f = a.extract_facts_from_docs(docs(), d)
    contract, _ = d.static_controls()
    result = d.synthetic_evaluate_all(contract, f)
    assert result["channel_count_evaluated"] == 16
    assert result["finding_count"] == 0
    assert result["declaration_values_created"] is False
    assert result["authority_channel_selected"] is False
    assert result["new_derivation_rule_created"] is False
    assert result["source_manifest_created"] is False
