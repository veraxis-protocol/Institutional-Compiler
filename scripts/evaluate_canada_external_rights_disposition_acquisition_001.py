#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-external-rights-disposition-acquisition-001"
)

CONTRACT = BENCH / "ACQUISITION-CONTRACT-v0.1.json"
REQUEST_SCHEMA = BENCH / "RIGHTS-DISPOSITION-REQUEST-SCHEMA-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"
ACTOR_SCHEMA = BENCH / "ACTOR-QUALIFICATION-EVIDENCE-SCHEMA-v0.1.json"
RECEIVED_SCHEMA = BENCH / "RECEIVED-RIGHTS-DISPOSITION-SCHEMA-v0.1.json"

CONTRACT_SHA256 = "e9d3e4755a077c4b2503332098e16f0ad69557eb0704e62954939432cad60bfa"
REQUEST_SCHEMA_SHA256 = "ed605a7f812657dd8dd05b53f3b8127177e5361c9997450bc199025ca8a1c745"
PREREG_FREEZE_SHA256 = "7ee3b9bbe924d55941c4a1ce641d095a70e94f43beb27fba22ce3eef15ef565a"

RIGHTS_BASIS_ALLOWED = (
    "public_domain",
    "open_license",
    "permission",
    "synthetic_owned",
    "other_documented_basis",
)
REDISTRIBUTION_ALLOWED = (
    "permitted",
    "not_permitted",
    "unknown",
)
QUALIFICATION_CLASSES = (
    "licensed_or_authorized_counsel_with_relevant_canadian_copyright_or_public-sector-rights_competence",
    "publisher_or_crown-copyright-licensing_authority_with_direct_disposition_authority",
    "other_institutional_rights_officer_with_documented_authority_over_the_specific_material",
)
ACT_STATUS_ALLOWED = ("final", "completed")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

ESTABLISHED = "EXTERNAL_RIGHTS_DISPOSITION_AUTHORITY_EVIDENCE_ESTABLISHED_CA3"
NOT_ESTABLISHED = "EXTERNAL_RIGHTS_DISPOSITION_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3"
INCOMPLETE = "EXTERNAL_RIGHTS_DISPOSITION_ACQUISITION_INCOMPLETE_FAIL_CLOSED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_preregistered_bytes() -> None:
    expected = {
        CONTRACT: CONTRACT_SHA256,
        REQUEST_SCHEMA: REQUEST_SCHEMA_SHA256,
        PREREG_FREEZE: PREREG_FREEZE_SHA256,
    }
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise ValueError(f"frozen preregistration digest mismatch: {path}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def assess_actor_qualification_evidence(
    actor: Mapping[str, Any],
) -> dict[str, Any]:
    checks = {
        "actor_identity_evidence":
            nonempty(actor.get("actor_full_name")),
        "actor_role_or_professional_capacity_evidence":
            nonempty(actor.get("actor_role_or_professional_capacity")),
        "qualification_class_frozen":
            actor.get("qualification_class") in QUALIFICATION_CLASSES,
        "authority_basis_evidence_external_to_oic_evaluator":
            nonempty(actor.get("authority_basis")),
        "authority_basis_reference_present":
            nonempty(actor.get("authority_basis_reference")),
        "authority_reference_independently_verified":
            actor.get("authority_reference_independently_verified") is True,
        "authority_scope_covers_ca3":
            actor.get("authority_scope_covers_ca3") is True,
        "authority_scope_covers_rights_basis":
            actor.get("authority_scope_covers_rights_basis") is True,
        "authority_scope_covers_redistribution_status":
            actor.get("authority_scope_covers_redistribution_status") is True,
    }
    structurally_complete = all(checks.values())
    return {
        "assessment": (
            "ACTOR_QUALIFICATION_EVIDENCE_STRUCTURALLY_COMPLETE"
            if structurally_complete
            else "ACTOR_QUALIFICATION_EVIDENCE_INCOMPLETE"
        ),
        "checks": checks,
        "structurally_complete": structurally_complete,
        # This field is deliberately never inferred from static structure.
        "real_actor_qualification_established_by_oic": False,
    }


def generate_neutral_request_packet(
    *,
    actor_identity: Mapping[str, Any] | None = None,
    source_identity_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "request_id":
            "OIC-CANADA-EXTERNAL-RIGHTS-DISPOSITION-ACQUISITION-001-REQUEST",
        "status":
            "DRAFT_NOT_SENT",
        "recipient": dict(actor_identity or {}),
        "source": {
            "source_id": "CA-3",
            "identity_binding": dict(source_identity_binding or {}),
        },
        "questions": {
            "rights_basis": {
                "select_exactly_one_from": list(RIGHTS_BASIS_ALLOWED),
                "selected_value": None,
                "reason_required": True,
            },
            "redistribution_status": {
                "select_exactly_one_from": list(REDISTRIBUTION_ALLOWED),
                "selected_value": None,
                "reason_required": True,
            },
        },
        "required_return_evidence": {
            "actor_identity": True,
            "actor_role_or_professional_capacity": True,
            "authority_basis": True,
            "authority_basis_reference": True,
            "supporting_evidence_references": True,
            "limitations_or_conditions": True,
            "actor_attestation": True,
            "issued_at": True,
            "final_or_completed_status": True,
        },
        "scope": {
            "source_id": "CA-3",
            "rights_basis": True,
            "redistribution_status": True,
            "rights_status": False,
            "source_kind": False,
            "source_locator": False,
            "provenance": False,
        },
        "candidate_values_preselected": False,
        "request_sent": False,
        "external_actor_contacted": False,
        "source_manifest_population_authorized": False,
    }


def validate_received_disposition(
    act: Mapping[str, Any],
) -> dict[str, Any]:
    findings: list[str] = []

    if act.get("source_id") != "CA-3":
        findings.append("source_id must equal CA-3")

    for field in (
        "actor_full_name",
        "actor_role_or_professional_capacity",
        "issued_at",
        "rights_basis_reason",
        "redistribution_status_reason",
        "actor_attestation",
    ):
        if not nonempty(act.get(field)):
            findings.append(f"{field} missing or empty")

    if act.get("act_status") not in ACT_STATUS_ALLOWED:
        findings.append("act_status must be final or completed")

    if act.get("rights_basis") not in RIGHTS_BASIS_ALLOWED:
        findings.append("rights_basis outside frozen enum")

    if act.get("redistribution_status") not in REDISTRIBUTION_ALLOWED:
        findings.append("redistribution_status outside frozen enum")

    refs = act.get("supporting_evidence_references")
    if not isinstance(refs, list) or not refs or not all(nonempty(x) for x in refs):
        findings.append("supporting_evidence_references requires >=1 nonempty item")

    limitations = act.get("limitations_or_conditions")
    if not isinstance(limitations, list):
        findings.append("limitations_or_conditions must be a list")

    digest = act.get("raw_act_sha256")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        findings.append("raw_act_sha256 invalid")

    return {
        "schema_valid": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "rights_basis_value_observed": (
            act.get("rights_basis")
            if act.get("rights_basis") in RIGHTS_BASIS_ALLOWED
            else None
        ),
        "redistribution_status_value_observed": (
            act.get("redistribution_status")
            if act.get("redistribution_status") in REDISTRIBUTION_ALLOWED
            else None
        ),
        "unknown_redistribution_is_valid_external_value":
            act.get("redistribution_status") == "unknown",
        "unknown_redistribution_implies_manifest_pass":
            False,
    }


def evaluate_authority(
    *,
    actor_evidence: Mapping[str, Any] | None,
    received_act: Mapping[str, Any] | None,
    raw_act_digest_verified: bool,
) -> dict[str, Any]:
    if actor_evidence is None or received_act is None:
        return {
            "outcome": NOT_ESTABLISHED,
            "external_rights_authority_evidence_established": False,
            "rights_basis_value_observed": None,
            "redistribution_status_value_observed": None,
            "rights_basis_value_established": False,
            "redistribution_status_value_established": False,
            "rights_status_established": False,
            "declaration_values_created_by_oic": False,
            "source_manifest_population_authorized": False,
            "finding_count": 0,
            "findings": [],
        }

    actor = assess_actor_qualification_evidence(actor_evidence)
    act = validate_received_disposition(received_act)

    standing = {
        "actor_identity_evidence":
            actor["checks"]["actor_identity_evidence"],
        "authority_basis_evidence_external_to_oic_evaluator": (
            actor["checks"]["authority_basis_evidence_external_to_oic_evaluator"]
            and actor["checks"]["authority_basis_reference_present"]
            and actor["checks"]["authority_reference_independently_verified"]
        ),
        "completed_act_evidence":
            act["schema_valid"]
            and received_act.get("act_status") in ACT_STATUS_ALLOWED,
        "ca3_scope_evidence":
            actor["checks"]["authority_scope_covers_ca3"]
            and received_act.get("source_id") == "CA-3",
        "rights_basis_scope_evidence":
            actor["checks"]["authority_scope_covers_rights_basis"]
            and received_act.get("rights_basis") in RIGHTS_BASIS_ALLOWED,
        "redistribution_status_scope_evidence":
            actor["checks"]["authority_scope_covers_redistribution_status"]
            and received_act.get("redistribution_status") in REDISTRIBUTION_ALLOWED,
        "act_integrity_or_digest_binding":
            act["schema_valid"] and raw_act_digest_verified is True,
    }

    findings = list(act["findings"])
    if not actor["structurally_complete"]:
        findings.append("actor qualification evidence incomplete")
    if raw_act_digest_verified is not True:
        findings.append("raw act digest not independently verified")

    established = (
        actor["structurally_complete"]
        and act["schema_valid"]
        and raw_act_digest_verified is True
        and all(standing.values())
    )

    if established:
        outcome = ESTABLISHED
    else:
        outcome = INCOMPLETE

    return {
        "outcome": outcome,
        "external_rights_authority_evidence_established": established,
        "actor_qualification": actor,
        "received_act_validation": act,
        "standing_requirements": standing,
        "rights_basis_value_observed": act["rights_basis_value_observed"],
        "redistribution_status_value_observed":
            act["redistribution_status_value_observed"],
        "rights_basis_value_established": established,
        "redistribution_status_value_established": established,
        # External disposition cannot silently promote rights_status.
        "rights_status_established": False,
        "declaration_values_created_by_oic": False,
        "source_manifest_created": False,
        "source_manifest_population_authorized": False,
        "legal_clearance_established": False,
        "finding_count": len(findings),
        "findings": findings,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-preflight", action="store_true")
    args = parser.parse_args(argv)

    verify_preregistered_bytes()

    if args.static_preflight or True:
        print("external rights disposition static instrument: PASS")
        print("real actor selected: FALSE")
        print("real actor qualification established: FALSE")
        print("external actor contacted: FALSE")
        print("request sent: FALSE")
        print("real disposition ingested: FALSE")
        print("SOURCE_MANIFEST population authorized: FALSE")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
