from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/evaluate_canada_synthetic_authority_act_sufficiency_001.py"

spec = importlib.util.spec_from_file_location("suff001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["suff001"] = m
spec.loader.exec_module(m)
d = m.load_discriminator()


def baseline(**changes):
    base = d.Facts(
        manifest_fields=frozenset(d.TARGET_FIELDS),
        rights_evidence_binding=True,
        provenance_evidence_binding=True,
        temporal_scope=True,
    )
    return replace(base, **changes)


def specimen(field, cid, ctype, levers):
    return {
        "specimen_id": f"SYN-{cid}",
        "target_field": field,
        "channel_id": cid,
        "channel_type": ctype,
        "observed_gap_cardinality": 5,
        "observed_gap_signature": "synthetic",
        "synthetic_fact_levers": levers,
    }


def test_bound_bytes_verify_without_real_execution():
    m.verify_bound_bytes_only()


def test_provenance_full_completion_and_all_ablations():
    s = specimen(
        "provenance_status",
        "PS-INSTITUTIONAL-PROVENANCE",
        "INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION",
        ["provenance_admission", "provenance_identity", "provenance_basis"],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["structural_sufficiency_supported"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True
    assert r["ablation_count"] == 3


def test_external_rights_full_completion_and_field_scope_ablation():
    s = specimen(
        "rights_basis",
        "RB-EXTERNAL-RIGHTS-AUTHORITY",
        "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION",
        [
            "counsel_disposition",
            "counsel_identity",
            "counsel_basis",
            "counsel_fields[target_field]",
        ],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["structural_sufficiency_supported"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True
    assert {x["ablated_lever"] for x in r["ablations"]} == set(
        s["synthetic_fact_levers"]
    )


def test_institutional_rights_adjudication_completion():
    s = specimen(
        "rights_status",
        "RS-INSTITUTIONAL-ADJUDICATION",
        "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",
        ["rights_adjudication", "rights_identity", "rights_basis"],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["full_completion_standing_established"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True


def test_institutional_admission_completion_and_scope_membership():
    s = specimen(
        "source_kind",
        "SK-INSTITUTIONAL-ADMISSION",
        "INSTITUTIONAL_ADMISSION_DECLARATION",
        [
            "institutional_admission",
            "institutional_identity",
            "institutional_basis",
            "institutional_fields[target_field]",
        ],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["structural_sufficiency_supported"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True


def test_source_origin_completion():
    s = specimen(
        "source_kind",
        "SK-SOURCE-ORIGIN",
        "EXPLICIT_SOURCE_ORIGIN_DECLARATION",
        ["source_origin_decl", "source_origin_identity", "source_origin_basis"],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["structural_sufficiency_supported"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True


def test_publisher_identity_preexisting_is_not_counted_as_intervention():
    s = specimen(
        "source_locator",
        "SL-PUBLISHER-CANONICAL",
        "PUBLISHER_CANONICAL_LOCATOR_DECLARATION",
        ["publisher_locator_decl", "publisher_identity"],
    )
    r = m.evaluate_specimen(
        s, baseline(publisher_identity=True), d
    )
    assert r["structural_sufficiency_supported"] is True
    assert r["changed_levers"] == ["publisher_locator_decl"]
    assert r["preexisting_levers"] == ["publisher_identity"]
    assert r["ablation_count"] == 1
    assert r["bounded_fact_lever_minimality_supported"] is True


def test_existing_rule_channel_supported_generically():
    s = specimen(
        "source_kind",
        "SK-EXISTING-RULE",
        "EXISTING_CONTRACT_DEFINED_DERIVATION",
        ["existing_rules[target_field]"],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["structural_sufficiency_supported"] is True
    assert r["bounded_fact_lever_minimality_supported"] is True
    assert r["ablation_count"] == 1


def test_preexisting_true_boolean_is_not_ablated_as_added_lever():
    s = specimen(
        "source_locator",
        "SL-PUBLISHER-CANONICAL",
        "PUBLISHER_CANONICAL_LOCATOR_DECLARATION",
        ["publisher_locator_decl", "publisher_identity"],
    )
    r = m.evaluate_specimen(
        s,
        baseline(publisher_identity=True, publisher_locator_decl=True),
        d,
    )
    assert r["changed_lever_count"] == 0
    assert r["structural_sufficiency_supported"] is False
    assert r["bounded_fact_lever_minimality_supported"] is False


def test_unknown_lever_fails_closed():
    s = specimen(
        "source_kind",
        "SK-SOURCE-ORIGIN",
        "EXPLICIT_SOURCE_ORIGIN_DECLARATION",
        ["not_a_real_lever"],
    )
    try:
        m.evaluate_specimen(s, baseline(), d)
    except ValueError as exc:
        assert "unsupported levers" in str(exc)
    else:
        raise AssertionError("unsupported lever should fail")


def test_duplicate_lever_fails_closed():
    s = specimen(
        "source_kind",
        "SK-SOURCE-ORIGIN",
        "EXPLICIT_SOURCE_ORIGIN_DECLARATION",
        ["source_origin_decl", "source_origin_decl"],
    )
    try:
        m.evaluate_specimen(s, baseline(), d)
    except ValueError as exc:
        assert "duplicate synthetic fact lever" in str(exc)
    else:
        raise AssertionError("duplicate lever should fail")


def test_snapshot_shape_must_match_facts_exactly():
    snap = {
        f.name: (
            [] if f.name in m.SET_FIELDS else getattr(baseline(), f.name)
        )
        for f in __import__("dataclasses").fields(d.Facts)
    }
    snap.pop("source_origin_decl")
    try:
        m.facts_from_snapshot(snap, d)
    except ValueError as exc:
        assert "facts snapshot shape drift" in str(exc)
    else:
        raise AssertionError("shape drift should fail")


def test_no_real_authority_or_value_promotion_in_specimen_result():
    s = specimen(
        "rights_status",
        "RS-INSTITUTIONAL-ADJUDICATION",
        "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",
        ["rights_adjudication", "rights_identity", "rights_basis"],
    )
    r = m.evaluate_specimen(s, baseline(), d)
    assert r["real_authority_act_created"] is False
    assert r["real_authority_established"] is False
    assert r["declaration_value_created"] is False
    assert r["authority_channel_selected"] is False
    assert r["new_real_derivation_rule_created"] is False
