#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[4]
BENCH = ROOT / "benchmarks/preflight/corpus-rights-provenance-001/canada-manifest-declaration-authority-discrimination-001"
CONTRACT = BENCH / "AUTHORITY-DISCRIMINATION-CONTRACT-v0.1.json"
INVENTORY = BENCH / "AUTHORITY-SOURCE-INVENTORY-v0.2.json"

CONTRACT_SHA256 = "41c150bb1587d55355e28435ce0352a885309068cffc5155c90af506a34e04ef"

PASS_DECL = "AUTHORIZED_DECLARATION_CHANNEL_ESTABLISHED"
PASS_RULE = "AUTHORIZED_EXISTING_RULE_CHANNEL_ESTABLISHED"
FAIL = "CHANNEL_NOT_ESTABLISHED"

TARGET_FIELDS = (
    "source_kind", "source_locator", "rights_basis",
    "rights_status", "provenance_status", "redistribution_status",
)

DIMS = (
    "authority_identity_explicit",
    "authority_basis_explicit",
    "authority_scope_covers_ca3",
    "authority_scope_covers_target_field",
    "authority_act_or_rule_explicit",
    "evidence_binding_explicit_where_required",
    "temporal_or_version_scope_explicit_where_required",
    "manifest_contract_accepts_result_shape",
    "no_evaluator_self_issuance",
    "no_promotion_from_workflow_or_observation_metadata",
    "deterministic_replay_possible_if_rule_based",
)

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def static_controls():
    if sha(CONTRACT) != CONTRACT_SHA256:
        raise SystemExit("FAIL: authority contract digest mismatch")
    contract = load(CONTRACT)
    inventory = load(INVENTORY)
    assert contract["status"] == "FROZEN_HYPOTHESES_NOT_EVALUATED"
    assert contract["channel_count"] == 16
    assert contract["target_field_count"] == 6
    assert inventory["status"] == "FROZEN_INPUT_INVENTORY_NOT_EVALUATED"
    assert inventory["input_count"] == 6
    assert inventory["authority_channels_evaluated"] is False
    return contract, inventory

@dataclass(frozen=True)
class Facts:
    source_origin_decl: bool = False
    source_origin_identity: bool = False
    source_origin_basis: bool = False
    publisher_locator_decl: bool = False
    publisher_identity: bool = False
    institutional_admission: bool = False
    institutional_identity: bool = False
    institutional_basis: bool = False
    institutional_fields: frozenset[str] = frozenset()
    rights_adjudication: bool = False
    rights_identity: bool = False
    rights_basis: bool = False
    counsel_disposition: bool = False
    counsel_identity: bool = False
    counsel_basis: bool = False
    counsel_fields: frozenset[str] = frozenset()
    provenance_admission: bool = False
    provenance_identity: bool = False
    provenance_basis: bool = False
    existing_rules: frozenset[str] = frozenset()
    rights_evidence_binding: bool = True
    provenance_evidence_binding: bool = True
    temporal_scope: bool = True
    manifest_fields: frozenset[str] = frozenset(TARGET_FIELDS)

def base_dims(field: str, f: Facts) -> dict[str, bool]:
    return {
        "authority_identity_explicit": False,
        "authority_basis_explicit": False,
        "authority_scope_covers_ca3": False,
        "authority_scope_covers_target_field": False,
        "authority_act_or_rule_explicit": False,
        "evidence_binding_explicit_where_required":
            f.rights_evidence_binding if field in {"rights_basis","rights_status","redistribution_status"}
            else f.provenance_evidence_binding if field == "provenance_status"
            else True,
        "temporal_or_version_scope_explicit_where_required": f.temporal_scope,
        "manifest_contract_accepts_result_shape": field in f.manifest_fields,
        "no_evaluator_self_issuance": True,
        "no_promotion_from_workflow_or_observation_metadata": True,
        "deterministic_replay_possible_if_rule_based": True,
    }

def evaluate(field: str, channel_id: str, channel_type: str, f: Facts) -> dict[str, Any]:
    d = base_dims(field, f)
    is_rule = channel_type == "EXISTING_CONTRACT_DEFINED_DERIVATION"

    if channel_type == "EXPLICIT_SOURCE_ORIGIN_DECLARATION":
        d.update(
            authority_identity_explicit=f.source_origin_identity,
            authority_basis_explicit=f.source_origin_basis,
            authority_scope_covers_ca3=f.source_origin_decl,
            authority_scope_covers_target_field=f.source_origin_decl and field == "source_kind",
            authority_act_or_rule_explicit=f.source_origin_decl,
        )
    elif channel_type == "PUBLISHER_CANONICAL_LOCATOR_DECLARATION":
        d.update(
            authority_identity_explicit=f.publisher_identity,
            authority_basis_explicit=f.publisher_locator_decl,
            authority_scope_covers_ca3=f.publisher_locator_decl,
            authority_scope_covers_target_field=f.publisher_locator_decl and field == "source_locator",
            authority_act_or_rule_explicit=f.publisher_locator_decl,
        )
    elif channel_type == "INSTITUTIONAL_ADMISSION_DECLARATION":
        d.update(
            authority_identity_explicit=f.institutional_identity,
            authority_basis_explicit=f.institutional_basis,
            authority_scope_covers_ca3=f.institutional_admission,
            authority_scope_covers_target_field=field in f.institutional_fields,
            authority_act_or_rule_explicit=f.institutional_admission,
        )
    elif channel_type == "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION":
        d.update(
            authority_identity_explicit=f.rights_identity,
            authority_basis_explicit=f.rights_basis,
            authority_scope_covers_ca3=f.rights_adjudication,
            authority_scope_covers_target_field=f.rights_adjudication and field in {"rights_basis","rights_status","redistribution_status"},
            authority_act_or_rule_explicit=f.rights_adjudication,
        )
    elif channel_type == "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION":
        d.update(
            authority_identity_explicit=f.counsel_identity,
            authority_basis_explicit=f.counsel_basis,
            authority_scope_covers_ca3=f.counsel_disposition,
            authority_scope_covers_target_field=field in f.counsel_fields,
            authority_act_or_rule_explicit=f.counsel_disposition,
        )
    elif channel_type == "INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION":
        d.update(
            authority_identity_explicit=f.provenance_identity,
            authority_basis_explicit=f.provenance_basis,
            authority_scope_covers_ca3=f.provenance_admission,
            authority_scope_covers_target_field=f.provenance_admission and field == "provenance_status",
            authority_act_or_rule_explicit=f.provenance_admission,
        )
    elif is_rule:
        ok = field in f.existing_rules
        d.update(
            authority_identity_explicit=ok,
            authority_basis_explicit=ok,
            authority_scope_covers_ca3=ok,
            authority_scope_covers_target_field=ok,
            authority_act_or_rule_explicit=ok,
            deterministic_replay_possible_if_rule_based=ok,
        )
    else:
        raise ValueError(channel_type)

    missing = [k for k in DIMS if not d[k]]
    passed = not missing
    assessment = PASS_RULE if passed and is_rule else PASS_DECL if passed else FAIL
    return {
        "target_field": field,
        "channel_id": channel_id,
        "channel_type": channel_type,
        "assessment": assessment,
        "standing_established": passed,
        "dimensions": d,
        "missing_dimensions": missing,
        "declaration_value_created": False,
        "authority_act_created_by_evaluator": False,
        "new_derivation_rule_created": False,
    }

def synthetic_evaluate_all(contract: Mapping[str, Any], f: Facts) -> dict[str, Any]:
    rows = []
    findings = []
    for field in contract["target_fields"]:
        for channel in contract["field_authority_channel_hypotheses"][field]:
            try:
                rows.append(evaluate(field, channel["channel_id"], channel["channel_type"], f))
            except Exception as exc:
                findings.append(f"{field}/{channel.get('channel_id')}: {type(exc).__name__}: {exc}")
    outcomes = {}
    for field in contract["target_fields"]:
        passing = [r["channel_id"] for r in rows if r["target_field"] == field and r["standing_established"]]
        outcomes[field] = {
            "passing_channel_ids": passing,
            "passing_channel_count": len(passing),
            "outcome": "AUTHORITY_CHANNEL_ESTABLISHED" if passing else "AUTHORITY_NOT_ESTABLISHED",
        }
    return {
        "disposition": "AUTHORITY_SURFACE_DISCRIMINATED_CA3" if len(rows) == 16 and not findings else "AUTHORITY_DISCRIMINATION_INCOMPLETE_FAIL_CLOSED",
        "channel_count_evaluated": len(rows),
        "finding_count": len(findings),
        "findings": findings,
        "channel_evaluations": rows,
        "field_outcomes": outcomes,
        "declaration_values_created": False,
        "authority_channel_selected": False,
        "new_derivation_rule_created": False,
        "source_manifest_created": False,
        "rerun_authorized": False,
    }

def verify_inventory_bytes(inventory: Mapping[str, Any]) -> None:
    for row in inventory["inputs"]:
        p = ROOT / row["path"]
        if not p.is_file() or sha(p) != row["sha256"]:
            raise SystemExit(f"FAIL: frozen authority input drift: {row['path']}")

def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute-read-only", action="store_true")
    args = ap.parse_args(argv)
    contract, inventory = static_controls()
    if args.execute_read_only:
        raise SystemExit("STOP: REAL AUTHORITY EVALUATION NOT IMPLEMENTED/AUTHORIZED IN STATIC FREEZE")
    print("static preflight: PASS")
    print("frozen authority input count: 6")
    print("real authority channels evaluated: FALSE")
    print("declaration values created: FALSE")
    print("SOURCE_MANIFEST.csv created: FALSE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
