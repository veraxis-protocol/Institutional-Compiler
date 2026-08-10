"""Non-result-bearing structural tests for CDC-END-TO-END-MISSION-001."""

from __future__ import annotations

from typing import Any

import pytest

from oic.cdc_e2e_mission import (
    DRAFT_KINDS,
    ExecutionClearance,
    MissionContractError,
    ResultBearingMissionBlockedError,
    RuntimeIdentity,
    execute_result_bearing_mission,
    prepare_mission,
    require_result_clearance,
)


def _package() -> dict[str, Any]:
    return {
        "mission_id": "CDC-TEST-MISSION-001",
        "assurance_mode": "SYNTHETIC_EVALUATION_ONLY",
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
    )
    with pytest.raises(ResultBearingMissionBlockedError, match="mission_package_sha256"):
        require_result_clearance(
            clearance, RuntimeIdentity("commit", "tree", "environment"), package
        )
