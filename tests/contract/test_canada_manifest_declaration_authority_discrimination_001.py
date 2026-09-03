from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "benchmarks/preflight/corpus-rights-provenance-001/canada-manifest-declaration-authority-discrimination-001/evaluate_authority_discrimination_v0.2.py"

spec = importlib.util.spec_from_file_location("authority001", MOD)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["authority001"] = m
spec.loader.exec_module(m)

def base():
    return m.Facts()

def test_static_controls_are_frozen_and_not_evaluated():
    c, i = m.static_controls()
    assert c["channel_count"] == 16
    assert c["target_field_count"] == 6
    assert i["input_count"] == 6
    assert i["authority_channels_evaluated"] is False

def test_source_origin_metadata_alone_does_not_promote():
    r = m.evaluate("source_kind","SK-SOURCE-ORIGIN","EXPLICIT_SOURCE_ORIGIN_DECLARATION",base())
    assert r["assessment"] == m.FAIL

def test_explicit_source_origin_channel_can_pass():
    f = replace(base(), source_origin_decl=True, source_origin_identity=True, source_origin_basis=True)
    r = m.evaluate("source_kind","SK-SOURCE-ORIGIN","EXPLICIT_SOURCE_ORIGIN_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_publisher_presence_alone_is_not_locator_declaration():
    f = replace(base(), publisher_identity=True)
    r = m.evaluate("source_locator","SL-PUBLISHER-CANONICAL","PUBLISHER_CANONICAL_LOCATOR_DECLARATION",f)
    assert r["assessment"] == m.FAIL

def test_explicit_publisher_locator_declaration_can_pass():
    f = replace(base(), publisher_identity=True, publisher_locator_decl=True)
    r = m.evaluate("source_locator","SL-PUBLISHER-CANONICAL","PUBLISHER_CANONICAL_LOCATOR_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_institutional_admission_can_pass_for_scoped_field():
    f = replace(
        base(),
        institutional_admission=True,
        institutional_identity=True,
        institutional_basis=True,
        institutional_fields=frozenset({"source_kind"}),
    )
    r = m.evaluate("source_kind","SK-INSTITUTIONAL-ADMISSION","INSTITUTIONAL_ADMISSION_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_engineering_rights_state_alone_cannot_pass():
    r = m.evaluate("rights_status","RS-INSTITUTIONAL-ADJUDICATION","INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",base())
    assert r["assessment"] == m.FAIL

def test_authorized_rights_adjudication_can_pass():
    f = replace(base(), rights_adjudication=True, rights_identity=True, rights_basis=True)
    r = m.evaluate("rights_status","RS-INSTITUTIONAL-ADJUDICATION","INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_pending_counsel_channel_cannot_pass():
    r = m.evaluate("rights_basis","RB-EXTERNAL-RIGHTS-AUTHORITY","EXTERNAL_RIGHTS_AUTHORITY_DECLARATION",base())
    assert r["assessment"] == m.FAIL

def test_completed_counsel_disposition_can_pass():
    f = replace(
        base(),
        counsel_disposition=True,
        counsel_identity=True,
        counsel_basis=True,
        counsel_fields=frozenset({"rights_basis","rights_status","redistribution_status"}),
    )
    r = m.evaluate("rights_basis","RB-EXTERNAL-RIGHTS-AUTHORITY","EXTERNAL_RIGHTS_AUTHORITY_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_acquisition_record_alone_is_not_provenance_admission():
    r = m.evaluate("provenance_status","PS-INSTITUTIONAL-PROVENANCE","INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION",base())
    assert r["assessment"] == m.FAIL

def test_explicit_provenance_admission_can_pass():
    f = replace(base(), provenance_admission=True, provenance_identity=True, provenance_basis=True)
    r = m.evaluate("provenance_status","PS-INSTITUTIONAL-PROVENANCE","INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION",f)
    assert r["assessment"] == m.PASS_DECL

def test_contract_requiredness_is_not_derivation_rule():
    r = m.evaluate("source_kind","SK-EXISTING-RULE","EXISTING_CONTRACT_DEFINED_DERIVATION",base())
    assert r["assessment"] == m.FAIL
    assert r["dimensions"]["deterministic_replay_possible_if_rule_based"] is False

def test_explicit_existing_rule_can_pass():
    f = replace(base(), existing_rules=frozenset({"source_kind"}))
    r = m.evaluate("source_kind","SK-EXISTING-RULE","EXISTING_CONTRACT_DEFINED_DERIVATION",f)
    assert r["assessment"] == m.PASS_RULE

def test_all_16_channels_are_synthetically_exercised_without_value_creation():
    c, _ = m.static_controls()
    out = m.synthetic_evaluate_all(c, base())
    assert out["disposition"] == "AUTHORITY_SURFACE_DISCRIMINATED_CA3"
    assert out["channel_count_evaluated"] == 16
    assert out["finding_count"] == 0
    assert out["declaration_values_created"] is False
    assert out["authority_channel_selected"] is False
    assert out["new_derivation_rule_created"] is False
    assert out["source_manifest_created"] is False
