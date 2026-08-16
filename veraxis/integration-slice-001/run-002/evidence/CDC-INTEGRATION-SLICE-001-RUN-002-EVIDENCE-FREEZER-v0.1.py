"""Freeze the RUN-002 evidence exactly as the execution left it.

The single authorized execution consumed its ordinal, ran the five T-EARLY
criteria and the six T-POS criteria — producing a complete positive pipeline —
and then raised at T-CASE-A, because `pipeline/case-a` was not among the declared
scenario directories.  `_scenario()` refused rather than creating it, which is the
behaviour the previous gate required; the declaration it consults was incomplete.

`persist()` inside harness v0.4 was never reached, so no observation file, ledger
or package was written by the run.  This freezer records what exists: the consumed
attempt, the pipeline artifacts actually produced, the exact traceback, and the
phase accounting.  It records only.  It does not repair, replay, re-execute,
reinterpret, adjudicate, or generate any evidence the run did not produce, and it
does not touch the consumed attempt record.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path("/private/tmp/cdc-integration-slice-001-run-002")
IMPLEMENTATION_ROOT = Path("/private/tmp/cdc-integration-slice-001-impl")
CONTROL_ROOT = Path("/private/tmp/cdc-integration-slice-001-run002")

ISSUANCE_DIGEST = "baf4cc9ee6200d2f2e236847557fa8e2160a025b377c9d155113c9dc776c7901"
ATTEMPT_PATH = RUNTIME_ROOT / f".cdc-integration-slice-001-run-002-attempt-{ISSUANCE_DIGEST}.json"

TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 3261, '
    "in <module>\n"
    "    outcome = execute_run()\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 3017, '
    "in execute_run\n"
    "    observations = _run_criteria()\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 2922, '
    "in _run_criteria\n"
    "    produced = executor(criterion_id)\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 2176, '
    "in <lambda>\n"
    '    EXECUTORS["T-CASE-A"] = lambda cid: _authority_only_case(\n'
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 2078, '
    "in _authority_only_case\n"
    '    scenario = _scenario(criterion_id.lower().replace("t-case-", "case-"))\n'
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py", line 1425, '
    "in _scenario\n"
    "    raise HarnessRefusalError(\n"
    "HarnessRefusalError: scenario directory absent: "
    "/private/tmp/cdc-integration-slice-001-run-002/pipeline/case-a; "
    "prepare_scenario_tree() must create every declared directory before any "
    "scenario writer runs"
)

FROZEN_CRITERION_ORDER = (
    "T-EARLY-01", "T-EARLY-02", "T-EARLY-03", "T-EARLY-04", "T-EARLY-05",
    "T-POS-01", "T-POS-02", "T-POS-03", "T-POS-04", "T-POS-05", "T-POS-06",
    "T-CASE-A", "T-CASE-B", "T-CASE-C", "T-CASE-D", "T-CASE-E", "T-CASE-F",
    "T-CASE-G", "T-CASE-H", "T-CASE-I", "T-CASE-J", "T-CASE-K", "T-CASE-L",
    "T-CASE-M", "T-CASE-N", "T-CASE-O", "T-CASE-P", "T-CASE-Q", "T-CASE-R",
    "T-CASE-S",
    "T-DIG-01", "T-DIG-02", "T-DIG-03", "T-DIG-04", "T-DIG-05", "T-DIG-06",
    "T-DIG-07", "T-DIG-08",
    "T-EPOCH-A", "T-EPOCH-B", "T-EPOCH-C",
)
REACHED_BEFORE_FAILURE = FROZEN_CRITERION_ORDER[:11]
FAILED_AT = "T-CASE-A"
NEVER_REACHED = FROZEN_CRITERION_ORDER[11:]

DECLARED_SCENARIOS = (
    "pipeline/positive", "pipeline/toctou-currentness", "pipeline/toctou-authority",
    "pipeline/historical", "pipeline/case-c", "pipeline/case-d", "pipeline/case-e",
    "pipeline/case-f", "pipeline/case-g", "pipeline/case-h", "pipeline/case-i",
    "pipeline/case-j", "pipeline/case-m", "pipeline/case-o", "pipeline/dig-04",
    "pipeline/dig-05", "pipeline/dig-06", "observations", "accounting",
)
REQUIRED_BUT_UNDECLARED = (
    "pipeline/case-a", "pipeline/case-b", "pipeline/case-n",
    "pipeline/case-q", "pipeline/case-r", "pipeline/case-s",
)


def sha256(payload: bytes) -> str:
    """Persisted-file identity."""
    return hashlib.sha256(payload).hexdigest()


def canonical_digest(value: object) -> str:
    """Derivation v0.6 §1 canonical form."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def artifacts() -> list[dict[str, Any]]:
    """Every file the run actually produced under the runtime root."""
    members = []
    for path in sorted(RUNTIME_ROOT.rglob("*")):
        if not path.is_file() or path.name.startswith("CDC-INTEGRATION-SLICE-001-RUN-002-EV"):
            continue
        payload = path.read_bytes()
        members.append(
            {
                "relative_path": str(path.relative_to(RUNTIME_ROOT)),
                "bytes": len(payload),
                "sha256": sha256(payload),
            }
        )
    return members


def failure_observation() -> dict[str, Any]:
    """What happened, in the order it happened."""
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_EXECUTION_FAILURE_OBSERVATION",
        "execution_id": "CDC-INTEGRATION-SLICE-001-RUN-002",
        "execution_outcome": "RAISED_AFTER_ORDINAL_CONSUMPTION",
        "ordinal_consumed": True,
        "attempt_state_observed": json.loads(ATTEMPT_PATH.read_bytes())["attempt_state"],
        "attempt_state_marked_completed": False,
        "phases": [
            {"phase": "verify_execution_authority", "reached": True, "outcome": "VALID"},
            {"phase": "preflight", "reached": True, "outcome": "PASS_50_OF_50"},
            {"phase": "preflight_zero_invocation_check", "reached": True, "outcome": "0"},
            {"phase": "attempt_state_check", "reached": True, "outcome": "NO_ATTEMPT_RECORD"},
            {"phase": "consume_ordinal", "reached": True, "outcome": "CONSUMED"},
            {"phase": "prepare_scenario_tree", "reached": True,
             "outcome": "19_DECLARED_DIRECTORIES_CREATED"},
            {"phase": "run_criteria", "reached": True,
             "outcome": "RAISED_AT_T-CASE-A_AFTER_11_CRITERIA"},
            {"phase": "runner_accounting", "reached": False, "outcome": "NOT_REACHED"},
            {"phase": "raw_views", "reached": False, "outcome": "NOT_REACHED"},
            {"phase": "supporting_artifact_inventory", "reached": False, "outcome": "NOT_REACHED"},
            {"phase": "observation_structural_conformance", "reached": False,
             "outcome": "NOT_REACHED"},
            {"phase": "complete_attempt", "reached": False, "outcome": "NOT_REACHED"},
            {"phase": "persist", "reached": False, "outcome": "NOT_REACHED"},
        ],
        "criteria_reached_before_failure": list(REACHED_BEFORE_FAILURE),
        "criteria_reached_count": len(REACHED_BEFORE_FAILURE),
        "criterion_that_raised": FAILED_AT,
        "criteria_never_reached": list(NEVER_REACHED),
        "criterion_observations_persisted": 0,
        "criterion_observations_produced_in_memory": len(REACHED_BEFORE_FAILURE),
        "criterion_observations_recoverable": False,
        "criterion_observations_recoverable_reason": (
            "the in-memory observations were lost when the process exited; persist() is "
            "reached only after all 41 execute, and nothing is reconstructed here"
        ),
        "exception_class": "HarnessRefusalError",
        "exception_message": (
            "scenario directory absent: /private/tmp/cdc-integration-slice-001-run-002/"
            "pipeline/case-a; prepare_scenario_tree() must create every declared "
            "directory before any scenario writer runs"
        ),
        "traceback": TRACEBACK,
        "defect_location": {
            "artifact": "CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.4.py",
            "symbol": "SCENARIO_DIRECTORIES",
            "description": (
                "the declared scenario tree omitted the six authority-only case "
                "directories that _authority_only_case() resolves: case-a, case-b, "
                "case-n, case-q, case-r, case-s"
            ),
            "defect_class": "INCOMPLETE_SCENARIO_DECLARATION",
            "refusal_mechanism_behaved_as_designed": True,
            "implementation_source_implicated": False,
        },
        "declared_scenario_directories": list(DECLARED_SCENARIOS),
        "required_but_undeclared_directories": list(REQUIRED_BUT_UNDECLARED),
        "rerun_performed": False,
        "second_result_bearing_execution": False,
        "automatic_retry_performed": False,
        "harness_modified_after_consumption": False,
        "attempt_record_modified_after_consumption": False,
        "development_evidence_substituted": False,
        "observations_mutated_to_satisfy_conformance": False,
        "semantic_adjudication_performed": False,
    }


def preservation_observation() -> dict[str, Any]:
    """Source and history state after the consumed run."""

    def git(root: Path, *args: str) -> str:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args], capture_output=True, check=True, text=True
        ).stdout.strip()

    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_PRESERVATION_OBSERVATION",
        "implementation_head_after_run": git(IMPLEMENTATION_ROOT, "rev-parse", "HEAD"),
        "implementation_tree_after_run": git(IMPLEMENTATION_ROOT, "rev-parse", "HEAD^{tree}"),
        "implementation_worktree_porcelain_after_run": git(
            IMPLEMENTATION_ROOT, "status", "--porcelain"
        ),
        "control_head_after_run": git(CONTROL_ROOT, "rev-parse", "HEAD"),
        "control_worktree_porcelain_after_run": git(CONTROL_ROOT, "status", "--porcelain"),
        "source_modified": False,
        "run_001_untouched_by_this_run": True,
    }


def write(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist one evidence artifact and return its identity."""
    path = RUNTIME_ROOT / name
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(data)
    return {"relative_path": name, "bytes": len(data), "sha256": sha256(data)}


def main() -> dict[str, Any]:
    """Freeze the artifacts, then the package that identifies them."""
    common = {
        "execution_id": "CDC-INTEGRATION-SLICE-001-RUN-002",
        "trace_id": "CDC-INTEGRATION-SLICE-001-RUN-002-TRACE",
        "authorization_id": "OWNER-AUTHORIZATION-INTEGRATION-SLICE-001-EXEC-002",
        "execution_issuance_digest": ISSUANCE_DIGEST,
        "implementation_commit": "fa96f5c3590f54118cd926a84370be6022a80b35",
        "implementation_tree": "65a704cd9c70aef983b62ecc8176793e20004772",
        "semantic_design_sha256": (
            "03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173"
        ),
        "criterion_evidence_projection_v0_3_sha256": (
            "7adcc39f5656fa3fdc837bf3049a7a4a1be38947aed41b2fc0ccc23cc4781298"
        ),
        "digest_derivation_sha256": (
            "dc3613ece70ffd9c3c816750ccb41d0df7e8683a81377f3fa2f419c344f9f6a0"
        ),
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "semantic_adjudication_performed": False,
    }
    members = [
        write(
            "CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-FAILURE-OBSERVATION-v0.1.json",
            {**common, **failure_observation()},
        ),
        write(
            "CDC-INTEGRATION-SLICE-001-RUN-002-PRESERVATION-OBSERVATION-v0.1.json",
            {**common, **preservation_observation()},
        ),
    ]
    members.extend(artifacts())
    members.sort(key=lambda item: item["relative_path"])

    package = {
        **common,
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_RAW_EXECUTION_PACKAGE",
        "schema_version": "CDC-INTEGRATION-SLICE-001-RUN-002-RAW-EXECUTION-PACKAGE-v0.1",
        "package_state": "FROZEN_AFTER_EXECUTION_RAISED_POST_CONSUMPTION",
        "runtime_evidence_root": str(RUNTIME_ROOT),
        "execution_outcome": "RAISED_AFTER_ORDINAL_CONSUMPTION",
        "criteria_total": 41,
        "criteria_reached_before_failure": len(REACHED_BEFORE_FAILURE),
        "criterion_observations_persisted": 0,
        "criterion_evidence_ledger_produced": False,
        "criterion_ledger_digest": None,
        "runner_accounting_produced": False,
        "raw_views_produced": False,
        "observation_conformance_produced": False,
        "attempt_state": json.loads(ATTEMPT_PATH.read_bytes())["attempt_state"],
        "attempt_completed": False,
        "automatic_retry_performed": False,
        "second_result_bearing_execution": False,
        "official_handoff": "PROHIBITED",
        "members": members,
        "members_total": len(members),
        "package_digest": "",
    }
    package["package_digest"] = canonical_digest(
        {key: value for key, value in package.items() if key != "package_digest"}
    )
    identity = write(
        "CDC-INTEGRATION-SLICE-001-RUN-002-RAW-EXECUTION-PACKAGE-v0.1.json", package
    )
    return {"package": package, "identity": identity}


if __name__ == "__main__":
    print(json.dumps(main()["identity"], indent=2, sort_keys=True))
