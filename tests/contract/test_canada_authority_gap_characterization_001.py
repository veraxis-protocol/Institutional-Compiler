from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/characterize_canada_authority_gaps_001.py"

spec = importlib.util.spec_from_file_location("gap001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["gap001"] = m
spec.loader.exec_module(m)


def row(field, cid, ctype, missing):
    return {
        "target_field": field,
        "channel_id": cid,
        "channel_type": ctype,
        "assessment": "CHANNEL_NOT_ESTABLISHED",
        "standing_established": False,
        "missing_dimensions": list(missing),
        "declaration_value_created": False,
        "authority_act_created_by_evaluator": False,
        "new_derivation_rule_created": False,
    }


def synthetic_result():
    fields = [
        "source_kind",
        "source_locator",
        "rights_basis",
        "rights_status",
        "provenance_status",
        "redistribution_status",
    ]
    rows = []
    # 16 total, with deliberate ties and varied cardinalities.
    definitions = {
        "source_kind": [
            ("SK-A", "INSTITUTIONAL_ADMISSION_DECLARATION", ["authority_identity_explicit"]),
            ("SK-B", "EXPLICIT_SOURCE_ORIGIN_DECLARATION", ["authority_basis_explicit"]),
            ("SK-C", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_basis_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
        "source_locator": [
            ("SL-A", "PUBLISHER_CANONICAL_LOCATOR_DECLARATION", ["authority_act_or_rule_explicit"]),
            ("SL-B", "INSTITUTIONAL_ADMISSION_DECLARATION", ["authority_act_or_rule_explicit"]),
            ("SL-C", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_act_or_rule_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
        "rights_basis": [
            ("RB-A", "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION", ["authority_identity_explicit"]),
            ("RB-B", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", [
                "authority_identity_explicit",
                "authority_basis_explicit",
            ]),
            ("RB-C", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_identity_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
        "rights_status": [
            ("RS-A", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", ["authority_basis_explicit"]),
            ("RS-B", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_basis_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
        "provenance_status": [
            ("PS-A", "INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION", ["authority_act_or_rule_explicit"]),
            ("PS-B", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_act_or_rule_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
        "redistribution_status": [
            ("RD-A", "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION", ["authority_identity_explicit"]),
            ("RD-B", "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION", ["authority_identity_explicit"]),
            ("RD-C", "EXISTING_CONTRACT_DEFINED_DERIVATION", [
                "authority_identity_explicit",
                "deterministic_replay_possible_if_rule_based",
            ]),
        ],
    }
    for field in fields:
        for cid, ctype, missing in definitions[field]:
            rows.append(row(field, cid, ctype, missing))

    assert len(rows) == 16
    return {
        "status": "CLOSED_EXECUTED_AUTHORITY_NOT_ESTABLISHED_CA3",
        "disposition": "AUTHORITY_SURFACE_DISCRIMINATED_CA3",
        "substantive_outcome": "ALL_FROZEN_CHANNELS_NOT_ESTABLISHED",
        "target_field_count": 6,
        "channel_count_evaluated": 16,
        "finding_count": 0,
        "passing_channel_count": 0,
        "channel_evaluations": rows,
    }


def test_static_contract_loads_without_real_analysis():
    c = m.load_contract()
    assert c["status"] == "FROZEN_ANALYSIS_NOT_EXECUTED"
    assert len(c["dimension_to_action_class"]) == 11


def test_gap_signatures_are_exact_sorted_sets():
    out = m.characterize(synthetic_result(), m.load_contract())
    rb = next(r for r in out["channel_gaps"] if r["channel_id"] == "RB-B")
    assert rb["missing_dimensions"] == [
        "authority_basis_explicit",
        "authority_identity_explicit",
    ]
    assert rb["gap_signature"] == (
        "authority_basis_explicit|authority_identity_explicit"
    )


def test_frequency_counts_are_exact_and_descriptive_only():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["missing_dimension_frequency_overall"][
        "authority_identity_explicit"
    ] == 7
    assert out["frequency_is_priority"] is False


def test_frequency_per_field_is_exact():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["missing_dimension_frequency_per_field"]["rights_basis"][
        "authority_identity_explicit"
    ] == 3


def test_frequency_per_channel_type_is_exact():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["missing_dimension_frequency_per_channel_type"][
        "EXISTING_CONTRACT_DEFINED_DERIVATION"
    ]["deterministic_replay_possible_if_rule_based"] == 6


def test_action_classes_are_one_to_one_from_dimensions():
    out = m.characterize(synthetic_result(), m.load_contract())
    sk = next(r for r in out["channel_gaps"] if r["channel_id"] == "SK-A")
    assert sk["implied_action_classes"] == [
        "EXPLICIT_AUTHORIZED_ACTOR_IDENTITY_REQUIRED"
    ]


def test_lowest_gap_cardinality_lists_all_ties():
    out = m.characterize(synthetic_result(), m.load_contract())
    row = out["lowest_observed_gap_cardinality_per_field"]["source_locator"]
    assert row["lowest_observed_gap_cardinality"] == 1
    assert row["channel_ids_at_lowest_cardinality"] == ["SL-A", "SL-B"]
    assert row["selection_or_preference_implied"] is False


def test_lowest_gap_never_selects_channel():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["lowest_gap_implies_preference"] is False
    assert out["authority_channel_selected"] is False


def test_unknown_dimension_fails_closed():
    x = synthetic_result()
    x["channel_evaluations"][0]["missing_dimensions"] = [
        "unknown_dimension"
    ]
    out = m.characterize(x, m.load_contract())
    assert out["disposition"] == (
        "AUTHORITY_GAP_CHARACTERIZATION_INCOMPLETE_FAIL_CLOSED"
    )
    assert out["finding_count"] > 0


def test_duplicate_channel_id_rejected():
    x = synthetic_result()
    x["channel_evaluations"][1]["channel_id"] = x["channel_evaluations"][0][
        "channel_id"
    ]
    try:
        m.characterize(x, m.load_contract())
    except ValueError as exc:
        assert "duplicate channel_id" in str(exc)
    else:
        raise AssertionError("duplicate channel id should fail")


def test_passing_channel_rejected_as_population_drift():
    x = synthetic_result()
    x["channel_evaluations"][0]["standing_established"] = True
    try:
        m.characterize(x, m.load_contract())
    except ValueError as exc:
        assert "standing unexpectedly established" in str(exc)
    else:
        raise AssertionError("passing channel should fail")


def test_analysis_creates_no_authority_or_values():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["authority_established"] is False
    assert out["declaration_values_created"] is False
    assert out["authority_channel_selected"] is False
    assert out["new_derivation_rule_created"] is False
    assert out["source_manifest_created"] is False
    assert out["source_manifest_population_authorized"] is False
    assert out["causal_root_cause"] == "NOT_ESTABLISHED"


def test_complete_synthetic_analysis_passes():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["disposition"] == "AUTHORITY_GAPS_CHARACTERIZED_CA3"
    assert out["channel_gap_count"] == 16
    assert out["finding_count"] == 0
    assert len(out["lowest_observed_gap_cardinality_per_field"]) == 6


def test_deterministic_replay_is_authorized_only_for_closed_result_analysis():
    out = m.characterize(synthetic_result(), m.load_contract())
    assert out["deterministic_replay_authorized"] is True
    assert out["provider_model_network_calls"] == 0
