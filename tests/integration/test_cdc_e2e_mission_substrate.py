"""Non-result-bearing structural tests for CDC-END-TO-END-MISSION-001."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from oic.cdc_e2e_mission import (
    ADJUDICATION_PROTOCOL_SHA256,
    DRAFT_KINDS,
    FROZEN_MISSION_MANIFEST_SHA256,
    FROZEN_MISSION_PACKAGE_SHA256,
    GOVERNANCE_COMMIT,
    ORACLE_SHA256,
    ExecutionClearance,
    MissionContractError,
    ResultBearingMissionBlockedError,
    RuntimeIdentity,
    execute_result_bearing_mission,
    prepare_mission,
    require_result_clearance,
    validate_frozen_reviewer_standing,
    verify_frozen_mission_input,
)
from oic.cdc_slice import make_successor

PACKAGE_ROOT = Path(__file__).parents[2] / "veraxis/cdc-e2e-mission-001/input-v0.1"


def _package() -> dict[str, Any]:
    return {
        "mission_id": "CDC-TEST-MISSION-001",
        "assurance_mode": "SYNTHETIC_EVALUATION_ONLY",
        "mission_package_sha256": FROZEN_MISSION_PACKAGE_SHA256,
        "admitted_controls": [
            {
                "control_id": "OIC-CONTROL-001",
                "admission_record_ref": "OIC-ADMISSION-001",
                "source_ref": "SYNTHETIC-SOURCE-001",
                "control_version": "1",
            }
        ],
        "population": [{"procedure_id": "P-001"}],
    }


def _absent_clearance() -> ExecutionClearance:
    return ExecutionClearance(None, None, None, None, None, None, None)


def test_prepare_binds_admitted_control_and_population_without_execution() -> None:
    prepared = prepare_mission(_package())
    assert prepared.status == "PREPARED_NOT_EXECUTED"
    assert prepared.admitted_control_ids == ("OIC-CONTROL-001",)
    assert prepared.population_ids == ("P-001",)


def test_persisted_frozen_mission_package_and_governance_bindings() -> None:
    verified = verify_frozen_mission_input(PACKAGE_ROOT)
    assert verified.package_sha256 == FROZEN_MISSION_PACKAGE_SHA256
    assert verified.manifest_sha256 == FROZEN_MISSION_MANIFEST_SHA256
    assert verified.package_bytes == 64199
    assert verified.population_count == 3
    assert verified.control_count == 3
    assert verified.evidence_object_count == 54
    assert verified.output_artifact_count == 5
    governance = json.loads((PACKAGE_ROOT / "06-GOVERNANCE/binding.json").read_bytes())
    assert governance["governance_commit"] == GOVERNANCE_COMMIT
    assert governance["mission_oracle_sha256"] == ORACLE_SHA256
    assert governance["mission_adjudication_protocol_sha256"] == ADJUDICATION_PROTOCOL_SHA256


def test_raw_source_interpretation_is_rejected() -> None:
    package = _package()
    package["raw_source_text"] = "must not be parsed"
    with pytest.raises(MissionContractError, match="raw-source interpretation"):
        prepare_mission(package)


def test_result_interlock_refuses_all_missing_bindings() -> None:
    with pytest.raises(ResultBearingMissionBlockedError, match="missing result-bearing clearance"):
        require_result_clearance(
            _absent_clearance(), RuntimeIdentity("commit", "tree", "environment"), _package()
        )


def test_result_entrypoint_refuses_before_evaluator_is_called() -> None:
    """The legacy mapping entrypoint is retired and refuses before doing anything."""
    calls = 0

    def forbidden_evaluator(*_args: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("result-bearing evaluator was reached")

    def forbidden_warrant(*_args: object) -> tuple[str, dict[str, Any]]:
        raise AssertionError("result-bearing warrant builder was reached")

    with pytest.raises(ResultBearingMissionBlockedError):
        execute_result_bearing_mission(
            _package(),
            _absent_clearance(),
            RuntimeIdentity("commit", "tree", "environment"),
            evaluator=forbidden_evaluator,
            warrant_builder=forbidden_warrant,
        )
    assert calls == 0


def test_five_bounded_draft_kinds_are_explicit_and_not_official() -> None:
    assert DRAFT_KINDS == (
        "orientation_note",
        "provisional_report",
        "final_report",
        "findings_summary",
        "transmittal_letter",
    )
    templates = [
        json.loads(path.read_bytes())
        for path in sorted((PACKAGE_ROOT / "04-OUTPUTS").glob("*.json"))
    ]
    assert len(templates) == 5
    assert all(item["official_status"] == "NOT_AUTHORIZED_AS_OFFICIAL" for item in templates)
    assert all(item["content_state"] == "NOT_YET_OBSERVED" for item in templates)


def test_frozen_reviewer_standing_requires_scope_validity_and_revocation() -> None:
    standing = json.loads((PACKAGE_ROOT / "03-AUTHORITY/test-reviewer.json").read_bytes())
    validate_frozen_reviewer_standing(
        standing,
        mission_id="CDC-TEST-MISSION-001",
        action="APPLY_TEST_DISPOSITION",
        observed_at="2026-08-10T12:00:00Z",
    )
    revoked = deepcopy(standing)
    revoked["revocation"]["status"] = "REVOKED"
    with pytest.raises(MissionContractError, match="unauthorized"):
        validate_frozen_reviewer_standing(
            revoked,
            mission_id="CDC-TEST-MISSION-001",
            action="APPLY_TEST_DISPOSITION",
            observed_at="2026-08-10T12:00:00Z",
        )


def test_correction_preserves_predecessor_identity_and_bytes() -> None:
    predecessor = {"ebawu_id": "EBAWU-001", "state": "CANDIDATE_FORMED"}
    before = deepcopy(predecessor)
    successor = make_successor(
        predecessor,
        {
            "new_ebawu_or_successor_id": "EBAWU-002",
            "new_candidate_digest": "sha256:successor",
            "correction_reason": "SYNTHETIC_CORRECTION",
            "changed_fact_or_control_refs": ["FACT-001"],
            "new_state": "CORRECTED_CANDIDATE",
            "correction_event_id": "EVENT-002",
        },
    )
    assert predecessor == before
    assert successor["supersedes"] == "EBAWU-001"
    assert successor["successor_id"] == "EBAWU-002"


def test_mission_package_digest_mismatch_refuses() -> None:
    package = _package()
    clearance = ExecutionClearance(
        owner_execution_authorization="OWNER-AUTH-REF",
        implementation_commit="commit",
        implementation_tree="tree",
        environment_manifest_sha256="environment",
        mission_package_sha256="not-the-package",
        oracle_sha256="oracle",
        adjudication_protocol_sha256="protocol",
        action_plan_sha256="plan",
    )
    with pytest.raises(ResultBearingMissionBlockedError, match="mission_package_sha256"):
        require_result_clearance(
            clearance, RuntimeIdentity("commit", "tree", "environment"), package
        )
