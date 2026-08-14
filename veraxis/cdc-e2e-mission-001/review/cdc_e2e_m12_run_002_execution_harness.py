"""Governed execution harness for the M12 correction successor, RUN-002.

A successor to the RUN-001 harness, not an edit of it: that one remains historical
evidence for AUTH-003 and CORR-001. This is a governed execution *procedure* and
is not the core executable implementation.

The enforcement discipline is carried forward deliberately rather than copied
blindly. Source identity is established before the core is imported, because a
runtime must not load unverified source and then declare it acceptable. The owner
execution decision is bound by exact bytes first and parsed second. The single
result-bearing call re-runs every gate, so neither a stale preflight nor a source
change between review and execution can authorize it.

One thing is checked in two independent ways. The AUTH-004 issuance record states
the state captured *at issuance time*; that is history, not proof of the present.
Whether the authority is still unexercised *now* is established separately, from
the absence of a RUN-002 correction-successor attempt.

Running this file performs the shadow preflight and never executes.
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
RUN_DIR = pathlib.Path("/private/tmp/cdc-e2e-m12-correction-successor-run-002")
SOURCE_RUN_001_EVIDENCE_ROOT = pathlib.Path("/private/tmp/cdc-e2e-stage2-run-001")
STAGE = pathlib.Path("/private/tmp/cdc-e2e-stage2-rehydration")

EXECUTION_DECISION = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-M12-CORRECTION-EXECUTION-DECISION-002.json"
)
AUTHORIZATION = RUN_DIR / "CDC-END-TO-END-MISSION-001-M12-AUTH-004.json"
INSTRUCTION = RUN_DIR / "CDC-END-TO-END-MISSION-001-M12-CORRECTION-INSTRUCTION-002.json"
ENVIRONMENT = RUN_DIR / "CDC-END-TO-END-MISSION-001-M12-RUN-002-EXECUTION-ENVIRONMENT-v0.1.json"
STAGE_1_RAW = STAGE / "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json"

# Governance evidence, held at its repository archival path rather than treated as
# a runtime authority artifact.
AUTH_004_ISSUANCE_RECORD = REPO / (
    "veraxis/cdc-e2e-mission-001/authorizations/"
    "CDC-END-TO-END-MISSION-001-M12-AUTH-004-ISSUANCE-RECORD-v0.1.json"
)
AUTH_004_ISSUANCE_RECORD_BLOB = "e17ef6f2c2f5cae607d84fb0df48afc3251860b7"
AUTH_004_ISSUANCE_COMMIT = "708f4e439add13487031a508c5b308911d35247f"

ACCEPTED_IMPLEMENTATION_COMMIT = "97f814e3d4ff40db6cdd55197a48e15c57b2ad49"
ACCEPTED_IMPLEMENTATION_TREE = "ff6d864a9b8db7c4c301271b5e7c9b29b5cd0ab5"

EXECUTION_DECISION_BYTES = 1375
EXECUTION_DECISION_SHA256 = "8dabd04971466a4235803118b499122b694ed7fe9e2e0cfc139b0563dee543e0"

AUTH_004_SHA = "eb759b44a5c971ba711b7a2a335c35bb8b993fe4f319ddb0c5cc8c4c9bd90e5f"
AUTH_004_ISSUANCE_RECORD_SHA = "76d847195ec10d2556c79f6bbb945bc93cfca5f130f761f0834dcb4ea9b9940c"
INSTRUCTION_002_SHA = "e33e075c8364f96c999072f12e8dd1f396ba85ad6085c13f5c1e85923a8fd703"
INSTRUCTION_002_ID = "CDC-END-TO-END-MISSION-001-M12-CORRECTION-INSTRUCTION-002"
SUCCESSOR_ID = "EBAWU-P-001-C-TENDER-01-CORR-002"
CORRECTION_EVENT_ID = "CDC-E2E-M12-CORRECTION-EVT-002"
PREDECESSOR_EBAWU = "EBAWU-P-001-C-TENDER-01"
PREDECESSOR_DIGEST = "07db4673eed5a124ee5eec96f4d149e59654632a12ad2632db72c19cc6efc311"
ENVIRONMENT_SHA = "e34729d3c953a84a3362b11906ca7dbb7d4c8fb03b3a7f07d13938cf1e129ea4"
EVIDENCE_BRANCH = "cdc-e2e-stage2-run-001-evidence"
EVIDENCE_COMMIT = "1a80aabe0f72eac8570b9827ee7545cda370cbe8"
EVIDENCE_TREE = "a6216214ae5a49ffcb3448a97aadce1bb3f418e3"

EXECUTION_DECISION_SEMANTICS: dict[str, Any] = {
    "authority_scope": "ONE_CORRECTION_SUCCESSOR_CONSTRUCTION",
    "authorization_id": "CDC-E2E-MISSION-001-M12-AUTH-004",
    "authorization_issuance_record_sha256": AUTH_004_ISSUANCE_RECORD_SHA,
    "authorization_sha256": AUTH_004_SHA,
    "automatic_retry_authorized": False,
    "canonical_execution_decision_path": str(EXECUTION_DECISION),
    "claim_ceiling": "SYNTHETIC_EVALUATION_ONLY",
    "correction_instruction_id": INSTRUCTION_002_ID,
    "correction_instruction_sha256": INSTRUCTION_002_SHA,
    "decision": "EXECUTE_AUTHORIZED_CORRECTION_ONCE",
    "environment_manifest_sha256": ENVIRONMENT_SHA,
    "execution_decision_id": "CDC-E2E-MISSION-001-M12-EXECUTION-DECISION-002",
    "experiment_id": "CDC-END-TO-END-MISSION-001",
    "implementation_commit": ACCEPTED_IMPLEMENTATION_COMMIT,
    "implementation_tree": ACCEPTED_IMPLEMENTATION_TREE,
    "record_class": "OWNER_CORRECTION_EXECUTION_DECISION",
    "runtime_mission_id": "CDC-TEST-MISSION-001",
    "single_use": True,
    "successor_id": SUCCESSOR_ID,
}
DECISION_ALLOWED_FIELDS = frozenset(EXECUTION_DECISION_SEMANTICS)
EXECUTION_DECISION_FIELD_COUNT = len(DECISION_ALLOWED_FIELDS)

ENFORCEMENT_CLASS = "RUN_LEVEL_GOVERNED_EXECUTION_HARNESS"
PRODUCTION_HARDENING_QUESTION = "MOVE_OWNER_EXECUTION_DECISION_VERIFICATION_INTO_CORE_RUNTIME_GATE"
PRODUCTION_HARDENING_STATUS = "OUT_OF_SCOPE_FOR_FROZEN_M12_RUN_002_SCOPE"


class HarnessRefusalError(RuntimeError):
    """The harness refused to proceed."""


def _git(repo: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise HarnessRefusalError(
            "git is unavailable; runtime source identity cannot be established"
        )
    return subprocess.run(  # noqa: S603 - fixed argv, resolved executable, no shell
        [executable, "-C", str(repo), *arguments], check=False, capture_output=True, text=True
    )


def verify_runtime_source(
    repo: pathlib.Path = REPO, accepted_commit: str = ACCEPTED_IMPLEMENTATION_COMMIT
) -> dict[str, Any]:
    """Compare the src/ tree about to be imported with the accepted implementation's.

    HEAD equality is deliberately not required: governance and evidence commits
    legitimately sit on top while leaving src untouched.
    """
    tracked = _git(repo, "diff", "--quiet", accepted_commit, "--", "src/")
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "--", "src/")
    untracked_files = [line for line in untracked.stdout.splitlines() if line.strip()]
    changed = _git(repo, "diff", "--name-only", accepted_commit, "--", "src/")
    changed_files = [line for line in changed.stdout.splitlines() if line.strip()]
    return {
        "repo": str(repo),
        "accepted_implementation_commit": accepted_commit,
        "tracked_src_differences": changed_files,
        "untracked_src_files": untracked_files,
        "matches": tracked.returncode == 0 and not untracked_files,
        "property_checked": (
            "CURRENT_EXECUTABLE_SOURCE_TREE == SOURCE_TREE_OF_ACCEPTED_IMPLEMENTATION"
        ),
        "head_equality_required": False,
    }


def verify_execution_decision(payload: bytes) -> dict[str, Any]:
    """Bind the exact reviewed decision: exact bytes first, then defined meaning."""
    observed_sha = hashlib.sha256(payload).hexdigest()
    exact = len(payload) == EXECUTION_DECISION_BYTES and observed_sha == EXECUTION_DECISION_SHA256
    report: dict[str, Any] = {
        "observed_bytes": len(payload),
        "observed_sha256": observed_sha,
        "expected_bytes": EXECUTION_DECISION_BYTES,
        "expected_sha256": EXECUTION_DECISION_SHA256,
        "exact_identity": "MATCH" if exact else "MISMATCH",
        "schema": "NOT_OBSERVED",
        "missing_fields": None,
        "unknown_fields": None,
        "semantic_bindings": "NOT_OBSERVED",
        "semantic_mismatches": None,
        "accepted": False,
    }
    if not exact:
        # No partial semantic match may substitute for exact-byte identity.
        return report
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        report["schema"] = f"UNPARSEABLE: {error}"
        return report
    if not isinstance(document, dict):
        report["schema"] = "NOT_A_JSON_OBJECT"
        return report
    missing = sorted(DECISION_ALLOWED_FIELDS - document.keys())
    unknown = sorted(document.keys() - DECISION_ALLOWED_FIELDS)
    report["missing_fields"] = missing
    report["unknown_fields"] = unknown
    closed = set(document.keys()) == DECISION_ALLOWED_FIELDS
    report["schema"] = (
        f"EXACT_{EXECUTION_DECISION_FIELD_COUNT}_FIELDS"
        if closed
        else f"SCHEMA_MISMATCH missing={missing} unknown={unknown}"
    )
    mismatches = sorted(
        name
        for name, expected in EXECUTION_DECISION_SEMANTICS.items()
        if document.get(name) is not expected and document.get(name) != expected
    )
    report["semantic_mismatches"] = mismatches
    report["semantic_bindings"] = (
        f"{EXECUTION_DECISION_FIELD_COUNT - len(mismatches)}/{EXECUTION_DECISION_FIELD_COUNT}"
    )
    report["accepted"] = closed and not mismatches
    return report


# Source identity is established BEFORE the core is imported.
_SOURCE = verify_runtime_source()
if not _SOURCE["matches"]:
    raise HarnessRefusalError(
        "runtime source does not match the accepted implementation; refusing to import: "
        f"tracked={_SOURCE['tracked_src_differences']} untracked={_SOURCE['untracked_src_files']}"
    )

sys.path.insert(0, str(REPO / "src"))
from oic import cdc_e2e_mission as mission  # noqa: E402

CORE_MODULE_PATH = REPO / "src" / "oic" / "cdc_e2e_mission.py"
if pathlib.Path(mission.__file__ or "").resolve() != CORE_MODULE_PATH.resolve():
    raise HarnessRefusalError(f"imported core from an unexpected location: {mission.__file__}")


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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

    source = verify_runtime_source()
    record("SOURCE_runtime_matches_controlling_implementation", source["matches"], source)

    decision_present = EXECUTION_DECISION.exists()
    record("A_execution_decision_present", decision_present, str(EXECUTION_DECISION))

    decision: dict[str, Any] = {}
    decision_report: dict[str, Any] = {
        "exact_identity": "NOT_OBSERVABLE",
        "schema": "NOT_OBSERVABLE",
        "semantic_bindings": "NOT_OBSERVABLE",
    }
    if decision_present:
        payload = EXECUTION_DECISION.read_bytes()
        decision_report = verify_execution_decision(payload)
        record(
            "A1_decision_exact_identity",
            decision_report["exact_identity"] == "MATCH",
            decision_report["exact_identity"],
        )
        record(
            "B_decision_schema_exact_19_fields",
            decision_report["schema"] == f"EXACT_{EXECUTION_DECISION_FIELD_COUNT}_FIELDS",
            {
                "schema": decision_report["schema"],
                "missing": decision_report["missing_fields"],
                "unknown": decision_report["unknown_fields"],
            },
        )
        record(
            "B1_decision_semantics_19_of_19",
            decision_report["semantic_bindings"]
            == f"{EXECUTION_DECISION_FIELD_COUNT}/{EXECUTION_DECISION_FIELD_COUNT}",
            {
                "semantic_bindings": decision_report["semantic_bindings"],
                "mismatches": decision_report["semantic_mismatches"],
            },
        )
        if decision_report["exact_identity"] == "MATCH":
            decision = json.loads(payload)
        record(
            "C_decision_binds_auth_004",
            decision.get("authorization_sha256") == AUTH_004_SHA,
            decision.get("authorization_sha256"),
        )
    else:
        for name in (
            "A1_decision_exact_identity",
            "B_decision_schema_exact_19_fields",
            "B1_decision_semantics_19_of_19",
            "C_decision_binds_auth_004",
        ):
            record(name, False, "NOT_OBSERVABLE: decision absent")

    auth_present = AUTHORIZATION.exists() and _sha256(AUTHORIZATION) == AUTH_004_SHA
    record("D1_auth_004_present_and_exact", auth_present, AUTH_004_SHA)

    frozen_input = mission.verify_frozen_mission_input(REPO / mission.FROZEN_MISSION_INPUT_RELPATH)
    plan = mission.verify_frozen_action_plan(REPO / mission.HUMAN_ACTION_PLAN_RELPATH)
    runtime = mission.RuntimeIdentity(
        implementation_commit=ACCEPTED_IMPLEMENTATION_COMMIT,
        implementation_tree=ACCEPTED_IMPLEMENTATION_TREE,
        environment_manifest_sha256=ENVIRONMENT_SHA,
    )
    authorization = None
    clearance = None
    if auth_present:
        document = json.loads(AUTHORIZATION.read_bytes())
        bindings = document["bindings"]
        clearance = mission.CorrectionExecutionClearance(
            owner_correction_authorization=(
                f"{mission.OWNER_AUTHORIZATION_REFERENCE_PREFIX}{AUTH_004_SHA}"
            ),
            implementation_commit=ACCEPTED_IMPLEMENTATION_COMMIT,
            implementation_tree=ACCEPTED_IMPLEMENTATION_TREE,
            environment_manifest_sha256=ENVIRONMENT_SHA,
            mission_package_sha256=bindings["mission_package_sha256"],
            oracle_sha256=bindings["oracle_sha256"],
            adjudication_protocol_sha256=bindings["adjudication_protocol_sha256"],
            action_plan_sha256=bindings["action_plan_sha256"],
            owner_acceptance_sha256=bindings["owner_acceptance_sha256"],
            source_stage_2_result_digest=bindings["source_stage_2_result_digest"],
        )
        try:
            authorization = mission.verify_owner_correction_successor_authorization(
                AUTHORIZATION,
                clearance=clearance,
                runtime=runtime,
                frozen=frozen_input,
                action_plan=plan,
            )
            record("D2_auth_004_verifies_at_canonical_path", True, authorization.authorization_id)
        except mission.CorrectionSuccessorAuthorizationError as error:
            record("D2_auth_004_verifies_at_canonical_path", False, str(error))
    else:
        record("D2_auth_004_verifies_at_canonical_path", False, "authorization absent or wrong")

    issuance_ok = (
        AUTH_004_ISSUANCE_RECORD.exists()
        and _sha256(AUTH_004_ISSUANCE_RECORD) == AUTH_004_ISSUANCE_RECORD_SHA
    )
    record("E_auth_004_issuance_record_exact", issuance_ok, AUTH_004_ISSUANCE_RECORD_SHA)
    if issuance_ok:
        issuance = json.loads(AUTH_004_ISSUANCE_RECORD.read_bytes())
        record(
            "F_issuance_record_state_at_issuance_time",
            issuance.get("authority_exists") is True
            and issuance.get("authority_exercised") is False
            and issuance.get("successor_attempt_created") is False
            and issuance.get("correction_executed") is False
            and issuance.get("execution_decision_002_created") is False,
            {
                "authority_exists": issuance.get("authority_exists"),
                "authority_exercised": issuance.get("authority_exercised"),
                "successor_attempt_created": issuance.get("successor_attempt_created"),
                "correction_executed": issuance.get("correction_executed"),
                "execution_decision_002_created": issuance.get("execution_decision_002_created"),
                "note": "state captured at issuance time; not proof of the present",
            },
        )
    else:
        record("F_issuance_record_state_at_issuance_time", False, "record absent or wrong")

    instruction = None
    if authorization is not None:
        try:
            instruction = mission.verify_owner_correction_instruction(authorization, plan)
            record(
                "G_instruction_002_verifies",
                instruction.sha256_hex == INSTRUCTION_002_SHA
                and instruction.instruction_id == INSTRUCTION_002_ID,
                {"sha256": instruction.sha256_hex, "id": instruction.instruction_id},
            )
        except mission.CorrectionInstructionError as error:
            record("G_instruction_002_verifies", False, str(error))
    else:
        record("G_instruction_002_verifies", False, "authorization unavailable")

    successor_ids = {
        "decision": decision.get("successor_id") if decision else None,
        "authorization": None if authorization is None else authorization.successor_id,
        "instruction": (
            None if instruction is None else instruction.owner_authored["new_ebawu_or_successor_id"]
        ),
        "expected": SUCCESSOR_ID,
    }
    record("H_single_successor_id", set(successor_ids.values()) == {SUCCESSOR_ID}, successor_ids)

    environment = json.loads(ENVIRONMENT.read_bytes())
    record(
        "I_executable_identity",
        environment["controlling_executable_implementation_commit"]
        == ACCEPTED_IMPLEMENTATION_COMMIT
        and environment["controlling_executable_implementation_tree"]
        == ACCEPTED_IMPLEMENTATION_TREE,
        {
            "commit": environment["controlling_executable_implementation_commit"],
            "tree": environment["controlling_executable_implementation_tree"],
        },
    )
    record("J_environment_manifest", _sha256(ENVIRONMENT) == ENVIRONMENT_SHA, ENVIRONMENT_SHA)

    # Present-tense unexercised state, established independently of the issuance record.
    attempt_state = (
        mission.CORRECTION_ATTEMPT_STATE_NONE
        if authorization is None
        else mission.read_correction_successor_attempt_state(authorization)
    )
    attempt_files = sorted(str(p) for p in RUN_DIR.rglob(".cdc-e2e-correction-successor-attempt-*"))
    record(
        "K_run_002_attempt_state_now",
        attempt_state == mission.CORRECTION_ATTEMPT_STATE_NONE and not attempt_files,
        {"attempt_state": attempt_state, "attempt_files": attempt_files},
    )

    stage_2_attempt = json.loads(
        (SOURCE_RUN_001_EVIDENCE_ROOT / mission.SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME).read_bytes()
    )["attempt_state"]
    record(
        "L_frozen_stage_2_attempt_consumed",
        stage_2_attempt == "CONSUMED_AFTER_FIRST_TRANSITION_EVALUATION",
        stage_2_attempt,
    )
    frozen_evidence = {
        "raw_result": _sha256(
            SOURCE_RUN_001_EVIDENCE_ROOT / mission.SOURCE_STAGE_2_RAW_RESULT_FILENAME
        ),
        "attempt_record": _sha256(
            SOURCE_RUN_001_EVIDENCE_ROOT / mission.SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME
        ),
        "route_trace": _sha256(
            SOURCE_RUN_001_EVIDENCE_ROOT / mission.SOURCE_STAGE_2_ROUTE_TRACE_FILENAME
        ),
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

    listed = _git(REPO, "ls-remote", "--heads", "origin", f"refs/heads/{EVIDENCE_BRANCH}")
    if listed.returncode != 0:
        record("N_origin_evidence_identity", False, f"unobservable: {listed.stderr.strip()}")
    else:
        fields = listed.stdout.split()
        origin_commit = fields[0] if fields else None
        tree = _git(REPO, "rev-parse", f"{origin_commit}^{{tree}}") if origin_commit else None
        origin_tree = tree.stdout.strip() if tree is not None and tree.returncode == 0 else None
        record(
            "N_origin_evidence_identity",
            origin_commit == EVIDENCE_COMMIT and origin_tree == EVIDENCE_TREE,
            {"commit": origin_commit, "tree": origin_tree},
        )

    execution_allowed = not refusals
    decision_dependent = {
        "A_execution_decision_present",
        "A1_decision_exact_identity",
        "B_decision_schema_exact_19_fields",
        "B1_decision_semantics_19_of_19",
        "C_decision_binds_auth_004",
        "H_single_successor_id",
    }
    return {
        "harness": "RUN_002",
        "checks": checks,
        "refusals": refusals,
        "unrelated_failures": sorted(set(refusals) - decision_dependent),
        "execution_allowed": execution_allowed,
        "refusal_reason": (
            None
            if execution_allowed
            else ("EXECUTION_DECISION_NOT_ISSUED" if not decision_present else refusals[0])
        ),
        "execution_decision_canonical_path": str(EXECUTION_DECISION),
        "execution_decision_canonical_path_present": decision_present,
        "execution_decision_exact_identity": decision_report["exact_identity"],
        "execution_decision_schema": decision_report["schema"],
        "execution_decision_semantic_bindings": decision_report["semantic_bindings"],
        "runtime_source_matches_controlling_implementation": source["matches"],
        "runtime_source_verified_before_core_import": True,
        "untracked_src_files": source["untracked_src_files"],
        "tracked_src_differences": source["tracked_src_differences"],
        "core_module_file": mission.__file__,
        "auth_004_valid": checks.get("D2_auth_004_verifies_at_canonical_path", {}).get(
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

    Every gate is re-run here, including source identity, so neither a stale
    preflight nor a source change between review and execution can authorize this.
    Invoked exactly once by the caller; there is no loop, retry or fallback path.
    """
    report = preflight()
    if not report["runtime_source_matches_controlling_implementation"]:
        raise HarnessRefusalError("runtime source changed since the accepted implementation")
    if not report["execution_allowed"]:
        raise HarnessRefusalError(f"execution refused: {report['refusals']}")
    return mission.execute_authorized_correction_successor(
        stage_1=_stage_1(),
        frozen=report["_frozen"],
        action_plan=report["_plan"],
        clearance=report["_clearance"],
        runtime=report["_runtime"],
        run_metadata=run_metadata,
        owner_correction_authorization_path=AUTHORIZATION,
    )


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    """The report without the internal object handles."""
    return {key: value for key, value in report.items() if not key.startswith("_")}


if __name__ == "__main__":
    # Running this file performs the shadow preflight only. It never executes.
    print(json.dumps(public_report(preflight()), indent=2, sort_keys=True, default=str))
