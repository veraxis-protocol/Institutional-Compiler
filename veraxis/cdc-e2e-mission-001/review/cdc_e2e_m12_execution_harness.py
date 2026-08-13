"""One-shot governed execution harness for the M12 correction successor (v0.2).

An execution *procedure* around the accepted implementation, not a replacement
for it. Nothing in the frozen core is modified.

Ordering matters here. The source tree about to be imported is compared against
the accepted implementation *before* ``oic.cdc_e2e_mission`` is imported: a
runtime must not load unverified source and then declare that source acceptable.
The property checked is that the current src/ equals the accepted
implementation's src/, not that git HEAD equals the accepted commit, because
later governance and evidence commits legitimately leave src untouched.

The owner execution decision is then bound by exact bytes first and parsed
second. Exact identity and defined meaning are both required; neither substitutes
for the other.

The single result-bearing call is reachable only through ``execute``, which
re-runs every gate, including the source-identity check, so a source change
between preflight and execution refuses. Running this file directly performs the
shadow preflight and never executes.

The enforcement boundary is explicit: the core library does not itself require an
owner execution decision, so a direct call bypassing this harness is outside the
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
ENVIRONMENT = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-M12-EXACT-CORRECTION-EXECUTION-ENVIRONMENT-v0.4.json"
)
STAGE_1_RAW = STAGE / "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json"
CORE_MODULE_PATH = REPO / "src" / "oic" / "cdc_e2e_mission.py"

ACCEPTED_IMPLEMENTATION_COMMIT = "e01ab40c0ae63d5420248c8f950d3ca9fd8e618d"
ACCEPTED_IMPLEMENTATION_TREE = "9278028471b055e724c25f226800caeb26e205db"

EXECUTION_DECISION_BYTES = 1357
EXECUTION_DECISION_SHA256 = "7589fc6f7557e538da6eb467d0d35257ec7058e6f555f9bcebadce47bec43e03"

AUTH_003_SHA = "ee8b80921c704b165ab6482187cbbb1eab4fa315d7e89b468b98b83ac86f34ff"
ISSUANCE_RECORD_SHA = "40383b4ed2b7faceed71126854816371592fc4ad7cc90082c21b9ef980e4c7ec"
INSTRUCTION_SHA = "b8b4cfcb73df1db0f1fc057f2a445355f34d3bd02cd6b28a6136a27cadc53dfd"
SUCCESSOR_ID = "EBAWU-P-001-C-TENDER-01-CORR-001"
ENVIRONMENT_SHA = "b5912183cb351e900887eaec3b34361cce0f02c3fbc63d9bec1c009e7e85f6ad"
EVIDENCE_COMMIT = "1a80aabe0f72eac8570b9827ee7545cda370cbe8"
EVIDENCE_TREE = "a6216214ae5a49ffcb3448a97aadce1bb3f418e3"
EVIDENCE_BRANCH = "cdc-e2e-stage2-run-001-evidence"

# Every field of the reviewed decision, with its required value.
EXECUTION_DECISION_SEMANTICS: dict[str, Any] = {
    "record_class": "OWNER_CORRECTION_EXECUTION_DECISION",
    "execution_decision_id": "CDC-E2E-MISSION-001-M12-EXECUTION-DECISION-001",
    "experiment_id": "CDC-END-TO-END-MISSION-001",
    "runtime_mission_id": "CDC-TEST-MISSION-001",
    "decision": "EXECUTE_AUTHORIZED_CORRECTION_ONCE",
    "authorization_id": "CDC-E2E-MISSION-001-M12-AUTH-003",
    "authorization_sha256": AUTH_003_SHA,
    "authorization_issuance_record_sha256": ISSUANCE_RECORD_SHA,
    "correction_instruction_id": "CDC-END-TO-END-MISSION-001-M12-CORRECTION-INSTRUCTION-001",
    "correction_instruction_sha256": INSTRUCTION_SHA,
    "successor_id": SUCCESSOR_ID,
    "implementation_commit": ACCEPTED_IMPLEMENTATION_COMMIT,
    "implementation_tree": ACCEPTED_IMPLEMENTATION_TREE,
    "environment_manifest_sha256": ENVIRONMENT_SHA,
    "authority_scope": "ONE_CORRECTION_SUCCESSOR_CONSTRUCTION",
    "single_use": True,
    "automatic_retry_authorized": False,
    "claim_ceiling": "SYNTHETIC_EVALUATION_ONLY",
    "canonical_execution_decision_path": str(EXECUTION_DECISION),
}
DECISION_ALLOWED_FIELDS = frozenset(EXECUTION_DECISION_SEMANTICS)
EXECUTION_DECISION_FIELD_COUNT = len(DECISION_ALLOWED_FIELDS)

ENFORCEMENT_CLASS = "RUN_LEVEL_GOVERNED_EXECUTION_HARNESS"
PRODUCTION_HARDENING_QUESTION = "MOVE_OWNER_EXECUTION_DECISION_VERIFICATION_INTO_CORE_RUNTIME_GATE"
PRODUCTION_HARDENING_STATUS = "OUT_OF_SCOPE_FOR_FROZEN_M12_SUCCESSOR"


class HarnessRefusalError(RuntimeError):
    """The harness refused to proceed."""


def _git(repo: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise HarnessRefusalError(
            "git is unavailable; runtime source identity cannot be established"
        )
    return subprocess.run(  # noqa: S603 - fixed argv, resolved executable, no shell
        [executable, "-C", str(repo), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def verify_runtime_source(
    repo: pathlib.Path = REPO, accepted_commit: str = ACCEPTED_IMPLEMENTATION_COMMIT
) -> dict[str, Any]:
    """Compare the src/ tree about to be imported with the accepted implementation's.

    HEAD is deliberately not required to equal the accepted commit: governance and
    evidence commits legitimately sit on top while leaving src untouched. The
    property is about the source bytes, not the branch tip.
    """
    tracked = _git(repo, "diff", "--quiet", accepted_commit, "--", "src/")
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "--", "src/")
    untracked_files = [line for line in untracked.stdout.splitlines() if line.strip()]
    changed = _git(repo, "diff", "--name-only", accepted_commit, "--", "src/")
    changed_files = [line for line in changed.stdout.splitlines() if line.strip()]
    matches = tracked.returncode == 0 and not untracked_files
    return {
        "repo": str(repo),
        "accepted_implementation_commit": accepted_commit,
        "tracked_src_differences": changed_files,
        "untracked_src_files": untracked_files,
        "matches": matches,
        "property_checked": (
            "CURRENT_EXECUTABLE_SOURCE_TREE == SOURCE_TREE_OF_ACCEPTED_IMPLEMENTATION"
        ),
        "head_equality_required": False,
    }


def verify_execution_decision(payload: bytes) -> dict[str, Any]:
    """Bind the exact reviewed decision: exact bytes first, then defined meaning.

    Kept pure so adversarial fixtures can be checked without touching the runtime
    canonical path.
    """
    observed_sha = hashlib.sha256(payload).hexdigest()
    exact_identity = len(payload) == EXECUTION_DECISION_BYTES and observed_sha == (
        EXECUTION_DECISION_SHA256
    )
    report: dict[str, Any] = {
        "observed_bytes": len(payload),
        "observed_sha256": observed_sha,
        "expected_bytes": EXECUTION_DECISION_BYTES,
        "expected_sha256": EXECUTION_DECISION_SHA256,
        "exact_identity": "MATCH" if exact_identity else "MISMATCH",
        "schema": "NOT_OBSERVED",
        "missing_fields": None,
        "unknown_fields": None,
        "semantic_bindings": "NOT_OBSERVED",
        "semantic_mismatches": None,
        "accepted": False,
    }
    if not exact_identity:
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


# ---------------------------------------------------------------------------
# Source identity is established BEFORE the core is imported. A failure here is a
# refusal to load, not a finding reported after loading.
# ---------------------------------------------------------------------------
_SOURCE = verify_runtime_source()
if not _SOURCE["matches"]:
    raise HarnessRefusalError(
        "runtime source does not match the accepted implementation; refusing to import: "
        f"tracked={_SOURCE['tracked_src_differences']} untracked={_SOURCE['untracked_src_files']}"
    )

sys.path.insert(0, str(REPO / "src"))
from oic import cdc_e2e_mission as mission  # noqa: E402

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

    # Source identity, re-established rather than inherited from import time.
    source = verify_runtime_source()
    record("SOURCE_runtime_matches_controlling_implementation", source["matches"], source)

    # A. the owner execution decision exists at its declared canonical path
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
            "C_decision_binds_auth_003",
            decision.get("authorization_sha256") == AUTH_003_SHA,
            decision.get("authorization_sha256"),
        )
    else:
        for name in (
            "A1_decision_exact_identity",
            "B_decision_schema_exact_19_fields",
            "B1_decision_semantics_19_of_19",
            "C_decision_binds_auth_003",
        ):
            record(name, False, "NOT_OBSERVABLE: decision absent")

    # D. AUTH-003 exists and verifies at its canonical path
    auth_present = AUTHORIZATION.exists() and _sha256(AUTHORIZATION) == AUTH_003_SHA
    record("D1_auth_003_present_and_exact", auth_present, AUTH_003_SHA)

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
        clearance = mission.CorrectionExecutionClearance(
            owner_correction_authorization=(
                f"{mission.OWNER_AUTHORIZATION_REFERENCE_PREFIX}{AUTH_003_SHA}"
            ),
            implementation_commit=ACCEPTED_IMPLEMENTATION_COMMIT,
            implementation_tree=ACCEPTED_IMPLEMENTATION_TREE,
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

    # E/F. issuance record identity and recorded state
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
    record("H_single_successor_id", set(successor_ids.values()) == {SUCCESSOR_ID}, successor_ids)

    # I/J. executable identity and environment
    environment = json.loads(ENVIRONMENT.read_bytes())
    record(
        "I_executable_identity",
        environment["implementation_commit"] == ACCEPTED_IMPLEMENTATION_COMMIT
        and environment["implementation_tree"] == ACCEPTED_IMPLEMENTATION_TREE,
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
        "C_decision_binds_auth_003",
        "H_single_successor_id",
    }
    return {
        "harness_version": "v0.2",
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
        "execution_decision_expected_bytes": EXECUTION_DECISION_BYTES,
        "execution_decision_expected_sha256": EXECUTION_DECISION_SHA256,
        "runtime_source_matches_controlling_implementation": source["matches"],
        "runtime_source_verified_before_core_import": True,
        "untracked_src_files": source["untracked_src_files"],
        "tracked_src_differences": source["tracked_src_differences"],
        "core_module_file": mission.__file__,
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

    Every gate is re-run here, including source identity, so neither a stale
    preflight nor a source change between review and execution can authorize this.
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
