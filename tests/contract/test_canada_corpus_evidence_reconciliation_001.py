from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/reconcile_canada_corpus_evidence_001.py"

spec = importlib.util.spec_from_file_location("reconcile001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["reconcile001"] = mod
spec.loader.exec_module(mod)


def contract():
    return {
        "fields": {
            "source_kind": {"allowed": ["public", "synthetic"]},
            "rights_basis": {
                "allowed": [
                    "public_domain",
                    "open_license",
                    "permission",
                    "synthetic_owned",
                    "other_documented_basis",
                ]
            },
        }
    }


def full_ca3_document():
    return {
        "source_id": "CA-3",
        "source_kind": "public",
        "source_locator": "https://example.invalid/ca-3",
        "local_path":
            "benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml",
        "rights_basis": "open_license",
        "rights_evidence":
            "benchmarks/corpus/canada/freeze-v0.1/RIGHTS-CLEARANCE-v0.1.json",
        "rights_status": "verified",
        "provenance_evidence":
            "benchmarks/corpus/canada/freeze-v0.1/receipts/CA-3.receipt.json",
        "provenance_status": "verified",
        "redistribution_status": "permitted",
        "acquired_or_generated_at": "2026-09-01T12:00:00-04:00",
    }


def run(*documents):
    return mod.reconcile_from_documents(
        documents=[
            (f"synthetic-{i}.json", item)
            for i, item in enumerate(documents, start=1)
        ],
        contract=contract(),
        computed_content_hash="sha256:" + ("a" * 64),
    )


def test_complete_exact_key_ca3_support_is_ready(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    result = run(full_ca3_document())
    assert result["disposition"] == mod.DISPOSITION_READY
    assert result["findings"] == []
    assert result["source_manifest_created"] is False
    assert result["rights_established"] is False
    assert result["provenance_established"] is False


def test_aliases_do_not_count_as_support(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["license_basis"] = doc.pop("rights_basis")
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["code"] == "MISSING_EXPLICIT_SUPPORT"
        and x["field"] == "rights_basis"
        for x in result["findings"]
    )


def test_evidence_without_exact_ca3_source_context_does_not_count(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc.pop("source_id")
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    missing = {
        x["field"]
        for x in result["findings"]
        if x["code"] == "MISSING_EXPLICIT_SUPPORT"
    }
    assert "source_id" in missing
    assert "rights_basis" in missing


def test_nested_ca3_context_is_inherited(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = {
        "records": [
            {
                "source_id": "CA-3",
                "metadata": {
                    key: value
                    for key, value in full_ca3_document().items()
                    if key != "source_id"
                },
            }
        ]
    }
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_READY


def test_nested_other_source_context_overrides_ca3(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["child"] = {
        "source_id": "OTHER",
        "rights_status": "rejected",
    }
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_READY
    assert result["resolved_candidate_manifest_fields"]["rights_status"] == "verified"


def test_conflicting_primary_values_fail_closed(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    one = full_ca3_document()
    two = {"source_id": "CA-3", "rights_status": "rejected"}
    result = run(one, two)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["code"] == "PRIMARY_EVIDENCE_CONFLICT"
        and x["field"] == "rights_status"
        for x in result["findings"]
    )


def test_permission_request_like_fields_do_not_create_permission(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc.pop("rights_basis")
    doc["permission_request_status"] = "sent"
    doc["requested_rights_basis"] = "permission"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["field"] == "rights_basis"
        and x["code"] == "MISSING_EXPLICIT_SUPPORT"
        for x in result["findings"]
    )


def test_unknown_redistribution_fails(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["redistribution_status"] = "unknown"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["code"] == "REDISTRIBUTION_NOT_RESOLVED"
        for x in result["findings"]
    )


def test_unverified_rights_fail(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["rights_status"] = "unverified"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(x["code"] == "RIGHTS_NOT_VERIFIED" for x in result["findings"])


def test_unverified_provenance_fails(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["provenance_status"] = "unverified"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["code"] == "PROVENANCE_NOT_VERIFIED"
        for x in result["findings"]
    )


def test_bad_timestamp_fails(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["acquired_or_generated_at"] = "2026-09-01"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(
        x["code"] == "INVALID_ACQUIRED_OR_GENERATED_AT"
        for x in result["findings"]
    )


def test_wrong_local_path_fails(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["local_path"] = "somewhere/else.xml"
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_FAIL
    assert any(x["code"] == "LOCAL_PATH_MISMATCH" for x in result["findings"])


def test_content_hash_is_only_computed_derivation(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    doc = full_ca3_document()
    doc["content_hash"] = "sha256:" + ("b" * 64)
    result = run(doc)
    assert result["disposition"] == mod.DISPOSITION_READY
    assert (
        result["resolved_candidate_manifest_fields"]["content_hash"]
        == "sha256:" + ("a" * 64)
    )
    assert result["field_support"]["content_hash"][0]["json_pointer"] == "BYTE_SHA256_ONLY"


def test_output_never_claims_rights_or_provenance_established(monkeypatch):
    monkeypatch.setattr(mod, "_valid_evidence_reference", lambda _value: True)
    result = run(full_ca3_document())
    assert result["rights_established"] is False
    assert result["provenance_established"] is False
    assert result["legal_clearance_established"] is False
    assert result["ontology_007r1_execution_authorized"] is False
    assert result["q011_creation_authorized"] is False
    assert result["canonicalization_authorized"] is False
    assert result["institutional_ir_authorized"] is False
    assert result["control_envelope_authorized"] is False
    assert result["rego_compilation_authorized"] is False
    assert result["runtime_evaluation_authorized"] is False
