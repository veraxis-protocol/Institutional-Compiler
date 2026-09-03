#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-synthetic-authority-act-sufficiency-001"
)
CONTRACT = BENCH / "SYNTHETIC-SUFFICIENCY-CONTRACT-v0.1.json"
DISCRIM = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-manifest-declaration-authority-discrimination-001/"
    "evaluate_authority_discrimination_v0.2.py"
)

CONTRACT_SHA256 = "01fd348956c8251483de4d713c62a754508ef8304d2a1381c84cef616c0e8d7b"
DISCRIM_SHA256 = "6d9be5309b64476fab9e0b0782a4ca67c2caf82f7c1af71c5658abbcb19275f0"

SET_FIELDS = frozenset({
    "counsel_fields",
    "institutional_fields",
    "existing_rules",
    "manifest_fields",
})

SUPPORTED_LEVERS = frozenset({
    "provenance_admission",
    "provenance_identity",
    "provenance_basis",
    "counsel_disposition",
    "counsel_identity",
    "counsel_basis",
    "counsel_fields[target_field]",
    "rights_adjudication",
    "rights_identity",
    "rights_basis",
    "institutional_admission",
    "institutional_identity",
    "institutional_basis",
    "institutional_fields[target_field]",
    "source_origin_decl",
    "source_origin_identity",
    "source_origin_basis",
    "publisher_locator_decl",
    "publisher_identity",
    "existing_rules[target_field]",
})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bound_bytes_only() -> None:
    if sha256(CONTRACT) != CONTRACT_SHA256:
        raise SystemExit("FAIL: synthetic sufficiency contract digest mismatch")
    if sha256(DISCRIM) != DISCRIM_SHA256:
        raise SystemExit("FAIL: frozen discriminator digest mismatch")


def load_discriminator():
    if sha256(DISCRIM) != DISCRIM_SHA256:
        raise SystemExit("FAIL: frozen discriminator digest mismatch")
    spec = importlib.util.spec_from_file_location("authority_discriminator_v02_suff", DISCRIM)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL: cannot load frozen discriminator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["authority_discriminator_v02_suff"] = module
    spec.loader.exec_module(module)
    return module


def facts_from_snapshot(snapshot: Mapping[str, Any], discriminator: Any):
    fields = {f.name for f in dataclasses.fields(discriminator.Facts)}
    if set(snapshot) != fields:
        missing = sorted(fields - set(snapshot))
        extra = sorted(set(snapshot) - fields)
        raise ValueError(f"facts snapshot shape drift missing={missing} extra={extra}")

    values: dict[str, Any] = {}
    for name, value in snapshot.items():
        if name in SET_FIELDS:
            if not isinstance(value, list):
                raise ValueError(f"{name} must serialize as list")
            values[name] = frozenset(value)
        else:
            values[name] = value
    return discriminator.Facts(**values)


def lever_is_active(facts: Any, lever: str, target_field: str) -> bool:
    if lever not in SUPPORTED_LEVERS:
        raise ValueError(f"unsupported lever: {lever}")

    if lever == "counsel_fields[target_field]":
        return target_field in facts.counsel_fields
    if lever == "institutional_fields[target_field]":
        return target_field in facts.institutional_fields
    if lever == "existing_rules[target_field]":
        return target_field in facts.existing_rules

    value = getattr(facts, lever)
    if not isinstance(value, bool):
        raise ValueError(f"lever {lever} is not boolean")
    return value


def set_lever(facts: Any, lever: str, target_field: str, active: bool):
    if lever not in SUPPORTED_LEVERS:
        raise ValueError(f"unsupported lever: {lever}")

    if lever == "counsel_fields[target_field]":
        values = set(facts.counsel_fields)
        (values.add if active else values.discard)(target_field)
        return dataclasses.replace(facts, counsel_fields=frozenset(values))

    if lever == "institutional_fields[target_field]":
        values = set(facts.institutional_fields)
        (values.add if active else values.discard)(target_field)
        return dataclasses.replace(facts, institutional_fields=frozenset(values))

    if lever == "existing_rules[target_field]":
        values = set(facts.existing_rules)
        (values.add if active else values.discard)(target_field)
        return dataclasses.replace(facts, existing_rules=frozenset(values))

    if not isinstance(getattr(facts, lever), bool):
        raise ValueError(f"lever {lever} is not boolean")
    return dataclasses.replace(facts, **{lever: active})


def evaluate_specimen(
    specimen: Mapping[str, Any],
    baseline: Any,
    discriminator: Any,
) -> dict[str, Any]:
    target_field = specimen["target_field"]
    channel_id = specimen["channel_id"]
    channel_type = specimen["channel_type"]
    levers = specimen["synthetic_fact_levers"]

    if not isinstance(levers, list) or not levers:
        raise ValueError(f"{channel_id}: synthetic_fact_levers must be nonempty")
    if len(set(levers)) != len(levers):
        raise ValueError(f"{channel_id}: duplicate synthetic fact lever")
    unknown = sorted(set(levers) - SUPPORTED_LEVERS)
    if unknown:
        raise ValueError(f"{channel_id}: unsupported levers: {unknown}")

    baseline_eval = discriminator.evaluate(
        target_field, channel_id, channel_type, baseline
    )

    completed = baseline
    changed_levers: list[str] = []
    preexisting_levers: list[str] = []

    for lever in levers:
        if lever_is_active(baseline, lever, target_field):
            preexisting_levers.append(lever)
        else:
            changed_levers.append(lever)
            completed = set_lever(completed, lever, target_field, True)

    full_eval = discriminator.evaluate(
        target_field, channel_id, channel_type, completed
    )

    ablations: list[dict[str, Any]] = []
    for lever in changed_levers:
        ablated = set_lever(completed, lever, target_field, False)
        row = discriminator.evaluate(
            target_field, channel_id, channel_type, ablated
        )
        ablations.append({
            "ablated_lever": lever,
            "assessment": row["assessment"],
            "standing_established": row["standing_established"],
            "missing_dimensions": row["missing_dimensions"],
        })

    full_pass = full_eval["standing_established"] is True
    baseline_fail = baseline_eval["standing_established"] is False
    ablations_fail = all(
        row["standing_established"] is False
        for row in ablations
    )

    return {
        "specimen_id": specimen["specimen_id"],
        "target_field": target_field,
        "channel_id": channel_id,
        "channel_type": channel_type,
        "observed_gap_cardinality": specimen["observed_gap_cardinality"],
        "observed_gap_signature": specimen["observed_gap_signature"],
        "synthetic_fact_levers": list(levers),
        "changed_levers": changed_levers,
        "preexisting_levers": preexisting_levers,
        "changed_lever_count": len(changed_levers),
        "baseline_assessment": baseline_eval["assessment"],
        "baseline_standing_established": baseline_eval["standing_established"],
        "full_completion_assessment": full_eval["assessment"],
        "full_completion_standing_established": full_eval["standing_established"],
        "full_completion_missing_dimensions": full_eval["missing_dimensions"],
        "ablations": ablations,
        "ablation_count": len(ablations),
        "all_added_lever_ablations_fail_closed": ablations_fail,
        "structural_sufficiency_supported": (
            baseline_fail and full_pass
        ),
        "bounded_fact_lever_minimality_supported": (
            baseline_fail
            and full_pass
            and bool(changed_levers)
            and ablations_fail
        ),
        "real_authority_act_created": False,
        "real_authority_established": False,
        "declaration_value_created": False,
        "authority_channel_selected": False,
        "new_real_derivation_rule_created": False,
    }


def evaluate_contract(contract: Mapping[str, Any], discriminator: Any) -> dict[str, Any]:
    if contract.get("status") != "FROZEN_HYPOTHESES_NOT_EXECUTED":
        raise ValueError("unexpected contract status")
    if contract["population"]["target_field_count"] != 6:
        raise ValueError("target field count drift")
    if contract["population"]["synthetic_specimen_count"] != 9:
        raise ValueError("synthetic specimen count drift")

    baseline = facts_from_snapshot(
        contract["observed_facts_snapshot"], discriminator
    )

    results = [
        evaluate_specimen(specimen, baseline, discriminator)
        for specimen in contract["specimens"]
    ]

    specimen_ids = [r["specimen_id"] for r in results]
    if len(set(specimen_ids)) != len(specimen_ids):
        raise ValueError("duplicate specimen_id")

    fields = {r["target_field"] for r in results}
    if fields != {
        "source_kind",
        "source_locator",
        "rights_basis",
        "rights_status",
        "provenance_status",
        "redistribution_status",
    }:
        raise ValueError(f"field coverage drift: {sorted(fields)}")

    structural_pass_count = sum(
        r["structural_sufficiency_supported"] for r in results
    )
    minimality_pass_count = sum(
        r["bounded_fact_lever_minimality_supported"] for r in results
    )

    findings: list[str] = []
    for r in results:
        if not r["baseline_standing_established"] is False:
            findings.append(
                f"{r['specimen_id']}: baseline unexpectedly establishes standing"
            )
        if not r["structural_sufficiency_supported"]:
            findings.append(
                f"{r['specimen_id']}: full synthetic completion not sufficient"
            )
        if not r["bounded_fact_lever_minimality_supported"]:
            findings.append(
                f"{r['specimen_id']}: added-lever ablation minimality not supported"
            )

    complete = (
        len(results) == 9
        and structural_pass_count == 9
        and minimality_pass_count == 9
        and not findings
    )

    return {
        "work_order":
            "OIC-CANADA-SYNTHETIC-AUTHORITY-ACT-SUFFICIENCY-001",
        "status":
            "EXECUTED_DETERMINISTIC_SYNTHETIC_ANALYSIS",
        "disposition": (
            "SYNTHETIC_AUTHORITY_ACT_STRUCTURAL_SUFFICIENCY_SUPPORTED_CA3"
            if complete
            else "SYNTHETIC_AUTHORITY_ACT_SUFFICIENCY_INCOMPLETE_FAIL_CLOSED"
        ),
        "population": contract["population"],
        "specimen_count_evaluated": len(results),
        "structural_sufficiency_pass_count": structural_pass_count,
        "bounded_fact_lever_minimality_pass_count": minimality_pass_count,
        "finding_count": len(findings),
        "findings": findings,
        "specimen_results": results,
        "preexisting_levers_not_counted_as_interventions": True,
        "coupled_dimensions_claimed_independent": False,
        "synthetic_pass_means_real_authority": False,
        "real_authority_established": False,
        "real_authority_act_created": False,
        "declaration_values_created": False,
        "authority_channel_selected": False,
        "new_real_derivation_rule_created": False,
        "candidate_002_adopted": False,
        "source_manifest_created": False,
        "source_manifest_population_authorized": False,
        "rights_established": False,
        "provenance_established": False,
        "legal_clearance_established": False,
        "causal_root_cause": "NOT_ESTABLISHED",
        "cross_source_generality_established": False,
        "provider_model_network_calls": 0,
        "deterministic_replay_authorized": True,
        "claim_ceiling": contract["claim_ceiling"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-bound-input-bytes", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    verify_bound_bytes_only()

    if args.verify_bound_input_bytes:
        print("contract/discriminator bytes: HASH-VERIFIED ONLY")
        print("real frozen specimen population executed: FALSE")
        return 0

    if not args.execute:
        print("synthetic sufficiency evaluator static preflight: PASS")
        print("real frozen specimen population executed: FALSE")
        print("real authority act created: FALSE")
        print("declaration values created: FALSE")
        return 0

    if not args.output:
        raise SystemExit("FAIL: --output required with --execute")

    contract = load_json(CONTRACT)
    discriminator = load_discriminator()
    result = evaluate_contract(contract, discriminator)

    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("disposition:", result["disposition"])
    print("specimens evaluated:", result["specimen_count_evaluated"])
    print(
        "structural sufficiency passes:",
        result["structural_sufficiency_pass_count"],
    )
    print(
        "bounded fact-lever minimality passes:",
        result["bounded_fact_lever_minimality_pass_count"],
    )
    print("findings:", result["finding_count"])
    print("real authority established: FALSE")
    print("declaration values created: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
