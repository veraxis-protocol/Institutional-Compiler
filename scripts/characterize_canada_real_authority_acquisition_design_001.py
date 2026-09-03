#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-real-authority-acquisition-design-001"
)
CONTRACT = BENCH / "REAL-AUTHORITY-ACQUISITION-DESIGN-CONTRACT-v0.1.json"
SOURCE_RESULT = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-synthetic-authority-act-sufficiency-001/"
    "EXECUTION-RESULT-v0.1.json"
)

CONTRACT_SHA256 = "ae39d1be9b3907ce345f5b47de65297cb018e09313e61d1bbb2fb15a1568eabf"
SOURCE_RESULT_SHA256 = "0335208b2fae5d4ad7be72d258ff31132f8debf6d8806f343c0042d212546721"

EXPECTED_FIELDS = frozenset({
    "source_kind",
    "source_locator",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
})

EXPECTED_FAMILIES = frozenset({
    "EXPLICIT_SOURCE_ORIGIN_DECLARATION",
    "PUBLISHER_CANONICAL_LOCATOR_DECLARATION",
    "EXTERNAL_RIGHTS_AUTHORITY_DECLARATION",
    "INSTITUTIONAL_RIGHTS_ADJUDICATION_DECLARATION",
    "INSTITUTIONAL_PROVENANCE_ADMISSION_DECLARATION",
    "INSTITUTIONAL_ADMISSION_DECLARATION",
})

REQUIRED_EVIDENCE = (
    "actor_identity_evidence",
    "authority_basis_evidence_external_to_oic_evaluator",
    "completed_act_evidence",
    "ca3_scope_evidence",
    "target_field_scope_evidence",
    "act_integrity_or_digest_binding",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bound_bytes_only() -> None:
    if sha256(CONTRACT) != CONTRACT_SHA256:
        raise SystemExit("FAIL: real-authority design contract digest mismatch")
    if sha256(SOURCE_RESULT) != SOURCE_RESULT_SHA256:
        raise SystemExit("FAIL: synthetic-sufficiency result digest mismatch")


def validate_source_result(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    if doc.get("status") != "EXECUTED_DETERMINISTIC_SYNTHETIC_ANALYSIS":
        raise ValueError("unexpected synthetic source status")
    if doc.get("disposition") != (
        "SYNTHETIC_AUTHORITY_ACT_STRUCTURAL_SUFFICIENCY_SUPPORTED_CA3"
    ):
        raise ValueError("unexpected synthetic source disposition")

    population = doc.get("population")
    if population != {
        "source_count": 1,
        "source_ids": ["CA-3"],
        "synthetic_specimen_count": 9,
        "target_field_count": 6,
    }:
        raise ValueError("synthetic source population drift")

    if doc.get("specimen_count_evaluated") != 9:
        raise ValueError("specimen count drift")
    if doc.get("structural_sufficiency_pass_count") != 9:
        raise ValueError("structural sufficiency count drift")
    if doc.get("bounded_fact_lever_minimality_pass_count") != 9:
        raise ValueError("minimality count drift")
    if doc.get("finding_count") != 0:
        raise ValueError("synthetic source findings not zero")
    if doc.get("real_authority_established") is not False:
        raise ValueError("source claims real authority")
    if doc.get("real_authority_act_created") is not False:
        raise ValueError("source claims real authority act")
    if doc.get("declaration_values_created") is not False:
        raise ValueError("source claims declaration values")

    rows = doc.get("specimen_results")
    if not isinstance(rows, list) or len(rows) != 9:
        raise ValueError("expected exactly nine specimen results")

    seen_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("specimen row must be object")
        specimen_id = row.get("specimen_id")
        if not isinstance(specimen_id, str) or not specimen_id:
            raise ValueError("invalid specimen_id")
        if specimen_id in seen_ids:
            raise ValueError(f"duplicate specimen_id: {specimen_id}")
        seen_ids.add(specimen_id)

        if row.get("channel_type") not in EXPECTED_FAMILIES:
            raise ValueError(f"unexpected family for {specimen_id}")
        if row.get("target_field") not in EXPECTED_FIELDS:
            raise ValueError(f"unexpected field for {specimen_id}")
        if row.get("structural_sufficiency_supported") is not True:
            raise ValueError(f"structural sufficiency missing for {specimen_id}")
        if row.get("bounded_fact_lever_minimality_supported") is not True:
            raise ValueError(f"minimality missing for {specimen_id}")
        if row.get("real_authority_established") is not False:
            raise ValueError(f"real authority promotion in {specimen_id}")
        if row.get("real_authority_act_created") is not False:
            raise ValueError(f"real act promotion in {specimen_id}")
        if row.get("declaration_value_created") is not False:
            raise ValueError(f"declaration promotion in {specimen_id}")

    return [dict(row) for row in rows]


def derive_family_fields(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    families: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        families[row["channel_type"]].add(row["target_field"])

    if set(families) != EXPECTED_FAMILIES:
        raise ValueError(
            f"family population drift: {sorted(families)}"
        )

    covered = set().union(*families.values())
    if covered != EXPECTED_FIELDS:
        raise ValueError(f"field coverage drift: {sorted(covered)}")

    return {
        family: sorted(fields)
        for family, fields in sorted(families.items())
    }


def minimum_cover_sets(
    family_fields: Mapping[str, Sequence[str]],
) -> tuple[int, list[list[str]]]:
    family_names = sorted(family_fields)
    for size in range(1, len(family_names) + 1):
        covers: list[list[str]] = []
        for combo in itertools.combinations(family_names, size):
            fields: set[str] = set()
            for family in combo:
                fields.update(family_fields[family])
            if fields == EXPECTED_FIELDS:
                covers.append(list(combo))
        if covers:
            return size, covers
    raise ValueError("no complete family cover exists")


def validate_contract_design(
    contract: Mapping[str, Any],
    family_fields: Mapping[str, Sequence[str]],
) -> tuple[int, list[list[str]], list[str]]:
    findings: list[str] = []

    if contract.get("status") != "FROZEN_DESIGN_NOT_EXECUTED":
        raise ValueError("unexpected design contract status")

    requirements = contract.get("channel_family_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("channel_family_requirements must be object")
    if set(requirements) != EXPECTED_FAMILIES:
        raise ValueError("contract family population drift")

    for family, fields in family_fields.items():
        req = requirements[family]

        if req.get("structurally_supported_target_fields") != list(fields):
            findings.append(f"{family}: target-field coverage mismatch")

        actor_origin = req.get("actor_origin")
        if actor_origin not in {"EXTERNAL", "INTERNAL_INSTITUTIONAL"}:
            findings.append(f"{family}: invalid actor origin")

        evidence = req.get("real_authority_evidence_required")
        if evidence != list(REQUIRED_EVIDENCE):
            findings.append(f"{family}: real-authority evidence vector mismatch")

        if req.get("oic_self_issuance_permitted") is not False:
            findings.append(f"{family}: OIC self-issuance not forbidden")
        if req.get("synthetic_result_promotable_to_real_authority") is not False:
            findings.append(f"{family}: synthetic promotion not forbidden")
        if req.get("currently_real_authority_established") is not False:
            findings.append(f"{family}: real authority prematurely established")

        if not isinstance(req.get("required_actor_class"), str) or not req[
            "required_actor_class"
        ]:
            findings.append(f"{family}: required actor class missing")
        if not isinstance(req.get("authority_basis_requirement"), str) or not req[
            "authority_basis_requirement"
        ]:
            findings.append(f"{family}: authority basis requirement missing")
        if not isinstance(req.get("completed_act_requirement"), str) or not req[
            "completed_act_requirement"
        ]:
            findings.append(f"{family}: completed act requirement missing")
        if not isinstance(req.get("scope_requirement"), str) or not req[
            "scope_requirement"
        ]:
            findings.append(f"{family}: scope requirement missing")

        preexisting = req.get("preexisting_internal_delegation_required")
        if actor_origin == "EXTERNAL" and preexisting is not False:
            findings.append(f"{family}: external family requires internal delegation")
        if actor_origin == "INTERNAL_INSTITUTIONAL" and preexisting is not True:
            findings.append(f"{family}: internal family lacks delegation requirement")

    external = sorted(
        family for family, req in requirements.items()
        if req["actor_origin"] == "EXTERNAL"
    )
    internal = sorted(
        family for family, req in requirements.items()
        if req["actor_origin"] == "INTERNAL_INSTITUTIONAL"
    )

    if len(external) != 3:
        findings.append("external family partition count != 3")
    if len(internal) != 3:
        findings.append("internal family partition count != 3")
    if set(external) | set(internal) != EXPECTED_FAMILIES:
        findings.append("path partition does not cover all families")
    if set(external) & set(internal):
        findings.append("path partitions overlap")

    path_classes = contract.get("path_classes", {})
    if path_classes.get("EXTERNAL_ACTOR_PATH", {}).get("families") != external:
        findings.append("external path-class family list mismatch")
    if path_classes.get("INTERNAL_GOVERNANCE_PATH", {}).get("families") != internal:
        findings.append("internal path-class family list mismatch")

    minimum, covers = minimum_cover_sets(family_fields)
    frozen_cover = contract.get("minimum_channel_family_cover", {})

    if frozen_cover.get("minimum_family_count") != minimum:
        findings.append("minimum family cover count mismatch")
    if frozen_cover.get("cover_set_count") != len(covers):
        findings.append("minimum cover-set count mismatch")
    if frozen_cover.get("cover_sets") != covers:
        findings.append("minimum cover-set membership mismatch")

    return minimum, covers, findings


def characterize(
    source: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    rows = validate_source_result(source)
    family_fields = derive_family_fields(rows)
    minimum, covers, findings = validate_contract_design(contract, family_fields)

    requirements = contract["channel_family_requirements"]
    external = contract["path_classes"]["EXTERNAL_ACTOR_PATH"]["families"]
    internal = contract["path_classes"]["INTERNAL_GOVERNANCE_PATH"]["families"]

    complete = (
        len(family_fields) == 6
        and minimum == 4
        and len(covers) == 2
        and len(external) == 3
        and len(internal) == 3
        and not findings
    )

    return {
        "work_order":
            "OIC-CANADA-REAL-AUTHORITY-ACQUISITION-DESIGN-001",
        "status":
            "EXECUTED_DETERMINISTIC_CLOSED_RESULT_DESIGN",
        "disposition": (
            "REAL_AUTHORITY_ACQUISITION_SURFACE_DESIGNED_CA3"
            if complete
            else "REAL_AUTHORITY_ACQUISITION_DESIGN_INCOMPLETE_FAIL_CLOSED"
        ),
        "population": {
            "source_count": 1,
            "source_ids": ["CA-3"],
            "target_field_count": 6,
            "successful_synthetic_specimen_count": 9,
            "successful_channel_family_count": 6,
        },
        "family_field_coverage": family_fields,
        "channel_family_requirements": requirements,
        "path_classes": contract["path_classes"],
        "minimum_channel_family_cover": {
            "minimum_family_count": minimum,
            "cover_set_count": len(covers),
            "cover_sets": covers,
            "descriptive_only": True,
            "legal_preference_implied": False,
            "authority_implied": False,
        },
        "real_authority_admissibility_requirements":
            contract["real_authority_admissibility_requirements"],
        "finding_count": len(findings),
        "findings": findings,
        "design_executed": True,
        "real_authority_evidence_acquired": False,
        "real_authority_established": False,
        "real_authority_act_created": False,
        "external_actor_contacted": False,
        "internal_delegation_created": False,
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
        print("contract/source bytes: HASH-VERIFIED ONLY")
        print("real acquisition-design semantics analyzed: FALSE")
        return 0

    if not args.execute:
        print("real-authority acquisition-design characterizer static preflight: PASS")
        print("real source-result semantics analyzed: FALSE")
        print("real authority evidence acquired: ZERO")
        print("real authority act created: FALSE")
        return 0

    if not args.output:
        raise SystemExit("FAIL: --output required with --execute")

    source = load_json(SOURCE_RESULT)
    contract = load_json(CONTRACT)
    result = characterize(source, contract)

    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("disposition:", result["disposition"])
    print("channel families:", result["population"]["successful_channel_family_count"])
    print(
        "minimum family cover:",
        result["minimum_channel_family_cover"]["minimum_family_count"],
    )
    print(
        "minimum cover sets:",
        result["minimum_channel_family_cover"]["cover_set_count"],
    )
    print("findings:", result["finding_count"])
    print("real authority evidence acquired: FALSE")
    print("real authority established: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
