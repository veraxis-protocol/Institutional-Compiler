"""One-shot governed execution harness for the M12 correction successor.

This is an execution *procedure* around the accepted implementation, not a
replacement for it. It imports the frozen core and changes nothing in it.

Fourteen checks (A-N) run first and are observation-only. The single
result-bearing call is reachable solely through ``execute``, which re-runs every
check and refuses unless all of them pass. Running this file directly performs
the shadow preflight and never executes.

The enforcement boundary is deliberately explicit: the core library does not
require an owner execution decision, so a direct call to
``execute_authorized_correction_successor`` bypassing this harness is outside the
authorized run procedure for this experiment.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any

REPO = pathlib.Path("/private/tmp/claude-501/cleanroom")
RUN_DIR = pathlib.Path("/private/tmp/cdc-e2e-stage2-run-001")
STAGE = pathlib.Path("/private/tmp/cdc-e2e-stage2-rehydration")

EXECUTION_DECISION = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-M12-CORRECTION-EXECUTION-DECISION-001.json"
)
AUTHORIZATION = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-OWNER-CORRECTION-SUCCESSOR-EXECUTION-AUTHORIZATION-v0.1.json"
)
ISSUANCE_RECORD = RUN_DIR / "CDC-END-TO-END-MISSION-001-M12-AUTH-003-ISSUANCE-RECORD-v0.1.json"
INSTRUCTION = RUN_DIR / "CDC-END-TO-END-MISSION-001-M12-CORRECTION-INSTRUCTION-001.json"
ENVIRONMENT = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-M12-EXACT-CORRECTION-EXECUTION-ENVIRONMENT-v0.4.json"
)
STAGE_1_RAW = STAGE / "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json"

AUTH_003_SHA = "ee8b80921c704b165ab6482187cbbb1eab4fa315d7e89b468b98b83ac86f34ff"
ISSUANCE_RECORD_SHA = "40383b4ed2b7faceed71126854816371592fc4ad7cc90082c21b9ef980e4c7ec"
INSTRUCTION_SHA = "b8b4cfcb73df1db0f1fc057f2a445355f34d3bd02cd6b28a6136a27cadc53dfd"
SUCCESSOR_ID = "EBAWU-P-001-C-TENDER-01-CORR-001"
IMPLEMENTATION_COMMIT = "e01ab40c0ae63d5420248c8f950d3ca9fd8e618d"
IMPLEMENTATION_TREE = "9278028471b055e724c25f226800caeb26e205db"
ENVIRONMENT_SHA = "b5912183cb351e900887eaec3b34361cce0f02c3fbc63d9bec1c009e7e85f6ad"
EVIDENCE_COMMIT = "1a80aabe0f72eac8570b9827ee7545cda370cbe8"
EVIDENCE_TREE = "a6216214ae5a49ffcb3448a97aadce1bb3f418e3"
EVIDENCE_BRANCH = "cdc-e2e-stage2-run-001-evidence"
DECISION_VALUE = "EXECUTE_AUTHORIZED_CORRECTION_ONCE"

DECISION_ALLOWED_FIELDS = frozenset(
    {
        "record_class",
        "execution_decision_id",
        "experiment_id",
        "runtime_mission_id",
        "decision",
        "authorization_id",
        "authorization_sha256",
        "authorization_issuance_record_sha256",
        "correction_instruction_id",
        "correction_instruction_sha256",
        "successor_id",
        "implementation_commit",
        "implementation_tree",
        "environment_manifest_sha256",
        "authority_scope",
        "single_use",
        "automatic_retry_authorized",
        "claim_ceiling",
        "canonical_execution_decision_path",
    }
)

ENFORCEMENT_CLASS = "RUN_LEVEL_GOVERNED_EXECUTION_HARNESS"
PRODUCTION_HARDENING_QUESTION = "MOVE_OWNER_EXECUTION_DECISION_VERIFICATION_INTO_CORE_RUNTIME_GATE"
PRODUCTION_HARDENING_STATUS = "OUT_OF_SCOPE_FOR_FROZEN_M12_SUCCESSOR"

sys.path.insert(0, str(REPO / "src"))
from oic import cdc_e2e_mission as mission  # noqa: E402


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git unavailable")
    return subprocess.run(  # noqa: S603 - fixed argv, resolved executable, no shell
        [executable, "-C", str(REPO), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _stage_1() -> mission.Stage1Observation:
    raw = json.loads(STAGE_1_RAW.read_bytes())
    return mission.Stage1Observation(
        mission_id=raw["mission_id"],
        package_sha256=raw["package_sha256"],
        provenance_token=raw["provenance_token"],
        stage=raw["stage"],
        chains=tuple(
            mission.Stage1ChainObservation(
                chain_id=chain["chain_id"],
                outcome_state=chain["outcome_state"],
                candidate_digest=chain["candidate_digest"],
                input_digest=chain["input_digest"],
                detail=chain["detail"],
                artifact=(
                    None
                    if chain["artifact"] is None
                    else mission.Stage1ChainArtifact(**chain["artifact"])
                ),
            )
            for chain in raw["chains"]
        ),
        accounting=raw["accounting"],
        authorization=raw["authorization"],
        owner_interpretation_sha256=raw["owner_interpretation_sha256"],
        owner_execution_authorization=raw["owner_execution_authorization"],
        attempt_record=raw["attempt_record"],
        institutional_transition=raw["institutional_transition"],
        draft_eligibility=raw["draft_eligibility"],
        official_handoff=raw["official_handoff"],
        human_disposition=raw["human_disposition"],
    )


def preflight() -> dict[str, Any]:
    """Run every gate. Observation only: nothing here is result-bearing."""
    checks: dict[str, Any] = {}
    refusals: list[str] = []

    def record(name: str, passed: bool, detail: object = None) -> bool:
        checks[name] = {"passed": passed, "detail": detail}
        if not passed:
            refusals.append(name)
        return passed

    # A. the owner execution decision exists at its declared canonical path
    decision_present = EXECUTION_DECISION.exists()
    record("A_execution_decision_present", decision_present, str(EXECUTION_DECISION))

    decision: dict[str, Any] = {}
    if decision_present:
        decision = json.loads(EXECUTION_DECISION.read_bytes())
        unknown = sorted(decision.keys() - DECISION_ALLOWED_FIELDS)
        record(
            "B_decision_schema_closed_and_says_execute_once",
            not unknown
            and decision.get("record_class") == "OWNER_CORRECTION_EXECUTION_DECISION"
            and decision.get("decision") == DECISION_VALUE,
            {"unknown_fields": unknown, "decision": decision.get("decision")},
        )
        record(
            "C_decision_binds_auth_003",
            decision.get("authorization_sha256") == AUTH_003_SHA,
            decision.get("authorization_sha256"),
        )
        declared = decision.get("canonical_execution_decision_path")
        record(
            "A2_decision_at_its_declared_path",
            declared is not None
            and pathlib.Path(declared).resolve() == EXECUTION_DECISION.resolve(),
            declared,
        )
    else:
        record("B_decision_schema_closed_and_says_execute_once", False, "decision absent")
        record("C_decision_binds_auth_003", False, "decision absent")

    # D. AUTH-003 exists and verifies at its canonical path
    auth_present = AUTHORIZATION.exists() and _sha256(AUTHORIZATION) == AUTH_003_SHA
    record("D1_auth_003_present_and_exact", auth_present, AUTH_003_SHA)

    frozen_input = mission.verify_frozen_mission_input(REPO / mission.FROZEN_MISSION_INPUT_RELPATH)
    plan = mission.verify_frozen_action_plan(REPO / mission.HUMAN_ACTION_PLAN_RELPATH)
    runtime = mission.RuntimeIdentity(
        implementation_commit=IMPLEMENTATION_COMMIT,
        implementation_tree=IMPLEMENTATION_TREE,
        environment_manifest_sha256=ENVIRONMENT_SHA,
    )
    authorization = None
    clearance = None
    if auth_present:
        document = json.loads(AUTHORIZATION.read_bytes())
        clearance = mission.CorrectionExecutionClearance(
            owner_correction_authorization=(
                f"{mission.OWNER_AUTHORIZATION_REFERENCE_PREFIX}{AUTH_003_SHA}"
            ),
            implementation_commit=IMPLEMENTATION_COMMIT,
            implementation_tree=IMPLEMENTATION_TREE,
            environment_manifest_sha256=ENVIRONMENT_SHA,
            mission_package_sha256=document["bindings"]["mission_package_sha256"],
            oracle_sha256=document["bindings"]["oracle_sha256"],
            adjudication_protocol_sha256=document["bindings"]["adjudication_protocol_sha256"],
            action_plan_sha256=document["bindings"]["action_plan_sha256"],
            owner_acceptance_sha256=document["bindings"]["owner_acceptance_sha256"],
            source_stage_2_result_digest=document["bindings"]["source_stage_2_result_digest"],
        )
        try:
            authorization = mission.verify_owner_correction_successor_authorization(
                AUTHORIZATION,
                clearance=clearance,
                runtime=runtime,
                frozen=frozen_input,
                action_plan=plan,
            )
            record("D2_auth_003_verifies_at_canonical_path", True)
        except mission.CorrectionSuccessorAuthorizationError as error:
            record("D2_auth_003_verifies_at_canonical_path", False, str(error))
    else:
        record("D2_auth_003_verifies_at_canonical_path", False, "authorization absent or wrong")

    # E/F. issuance record identity and its recorded state
    issuance_ok = ISSUANCE_RECORD.exists() and _sha256(ISSUANCE_RECORD) == ISSUANCE_RECORD_SHA
    record("E_issuance_record_exact", issuance_ok, ISSUANCE_RECORD_SHA)
    if issuance_ok:
        issuance = json.loads(ISSUANCE_RECORD.read_bytes())
        record(
            "F_issuance_record_state",
            issuance.get("authority_exercised") is False
            and issuance.get("successor_attempt_created") is False
            and issuance.get("execution_eligibility")
            == "ELIGIBLE_PENDING_SEPARATE_OWNER_EXECUTION_DECISION",
            {
                "authority_exercised": issuance.get("authority_exercised"),
                "successor_attempt_created": issuance.get("successor_attempt_created"),
                "execution_eligibility": issuance.get("execution_eligibility"),
            },
        )
    else:
        record("F_issuance_record_state", False, "issuance record absent or wrong")

    # G. the authorized correction instruction verifies
    instruction = None
    if authorization is not None:
        try:
            instruction = mission.verify_owner_correction_instruction(authorization, plan)
            record(
                "G_correction_instruction_verifies",
                instruction.sha256_hex == INSTRUCTION_SHA,
                instruction.sha256_hex,
            )
        except mission.CorrectionInstructionError as error:
            record("G_correction_instruction_verifies", False, str(error))
    else:
        record("G_correction_instruction_verifies", False, "authorization unavailable")

    # H. one successor id across decision, authorization and instruction
    successor_ids = {
        "decision": decision.get("successor_id") if decision else None,
        "authorization": None if authorization is None else authorization.successor_id,
        "instruction": (
            None if instruction is None else instruction.owner_authored["new_ebawu_or_successor_id"]
        ),
    }
    record(
        "H_single_successor_id",
        set(successor_ids.values()) == {SUCCESSOR_ID},
        successor_ids,
    )

    # I/J. executable identity and environment
    environment = json.loads(ENVIRONMENT.read_bytes())
    record(
        "I_executable_identity",
        environment["implementation_commit"] == IMPLEMENTATION_COMMIT
        and environment["implementation_tree"] == IMPLEMENTATION_TREE,
        {
            "commit": environment["implementation_commit"],
            "tree": environment["implementation_tree"],
        },
    )
    record("J_environment_manifest", _sha256(ENVIRONMENT) == ENVIRONMENT_SHA, ENVIRONMENT_SHA)

    # K/L/M. attempt states and frozen RUN-001 evidence
    attempt_state = (
        mission.CORRECTION_ATTEMPT_STATE_NONE
        if authorization is None
        else mission.read_correction_successor_attempt_state(authorization)
    )
    record(
        "K_correction_attempt_state",
        attempt_state == mission.CORRECTION_ATTEMPT_STATE_NONE
        and not list(RUN_DIR.rglob(".cdc-e2e-correction-successor-attempt-*")),
        attempt_state,
    )
    stage_2_attempt = json.loads(
        (RUN_DIR / mission.SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME).read_bytes()
    )["attempt_state"]
    record(
        "L_stage_2_attempt_consumed",
        stage_2_attempt == "CONSUMED_AFTER_FIRST_TRANSITION_EVALUATION",
        stage_2_attempt,
    )
    frozen_evidence = {
        "raw_result": _sha256(RUN_DIR / mission.SOURCE_STAGE_2_RAW_RESULT_FILENAME),
        "attempt_record": _sha256(RUN_DIR / mission.SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME),
        "route_trace": _sha256(RUN_DIR / mission.SOURCE_STAGE_2_ROUTE_TRACE_FILENAME),
    }
    record(
        "M_run_001_evidence_unchanged",
        frozen_evidence
        == {
            "raw_result": mission.SOURCE_STAGE_2_RAW_RESULT_SHA256,
            "attempt_record": mission.SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256,
            "route_trace": mission.SOURCE_STAGE_2_ROUTE_TRACE_SHA256,
        },
        frozen_evidence,
    )

    # N. origin still publishes the bound evidence commit
    try:
        listed = _git("ls-remote", "--heads", "origin", f"refs/heads/{EVIDENCE_BRANCH}").split()
        origin_commit = listed[0] if listed else None
        origin_tree = _git("rev-parse", f"{origin_commit}^{{tree}}") if origin_commit else None
        record(
            "N_origin_evidence_identity",
            origin_commit == EVIDENCE_COMMIT and origin_tree == EVIDENCE_TREE,
            {"commit": origin_commit, "tree": origin_tree},
        )
    except (RuntimeError, subprocess.CalledProcessError) as error:
        record("N_origin_evidence_identity", False, f"unobservable: {error}")

    execution_allowed = not refusals
    return {
        "checks": checks,
        "refusals": refusals,
        "execution_allowed": execution_allowed,
        "refusal_reason": (
            None
            if execution_allowed
            else ("EXECUTION_DECISION_NOT_ISSUED" if not decision_present else refusals[0])
        ),
        "execution_decision_canonical_path": str(EXECUTION_DECISION),
        "execution_decision_canonical_path_present": decision_present,
        "auth_003_valid": checks.get("D2_auth_003_verifies_at_canonical_path", {}).get(
            "passed", False
        ),
        "authority_exists": auth_present,
        "authority_exercised": attempt_state != mission.CORRECTION_ATTEMPT_STATE_NONE,
        "correction_attempt_state": attempt_state,
        "result_bearing_functions_invoked": [],
        "enforcement_class": ENFORCEMENT_CLASS,
        "core_library_direct_call_requires_execution_decision": False,
        "authorized_run_procedure_requires_execution_decision": True,
        "direct_call_bypassing_harness": "OUTSIDE_AUTHORIZED_RUN_PROCEDURE",
        "production_hardening_question": PRODUCTION_HARDENING_QUESTION,
        "production_hardening_status": PRODUCTION_HARDENING_STATUS,
        "_authorization": authorization,
        "_clearance": clearance,
        "_frozen": frozen_input,
        "_plan": plan,
        "_runtime": runtime,
    }


def execute(run_metadata: dict[str, str]) -> mission.CorrectionSuccessorResult:
    """The single result-bearing operation, reachable only through a passing preflight.

    Every gate is re-run here rather than trusted from an earlier call, so a stale
    preflight cannot authorize an execution.
    """
    report = preflight()
    if not report["execution_allowed"]:
        raise RuntimeError(f"execution refused: {report['refusals']}")
    return mission.execute_authorized_correction_successor(
        stage_1=_stage_1(),
        frozen=report["_frozen"],
        action_plan=report["_plan"],
        clearance=report["_clearance"],
        runtime=report["_runtime"],
        run_metadata=run_metadata,
        owner_correction_authorization_path=AUTHORIZATION,
    )


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


if __name__ == "__main__":
    # Running this file performs the shadow preflight only. It never executes.
    print(json.dumps(_public_report(preflight()), indent=2, sort_keys=True, default=str))
