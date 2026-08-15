"""Freeze the raw evidence of the RUN-001 execution exactly as it stands.

The single authorized execution consumed its ordinal and then raised, in the
pipeline-observation phase, after the 41-criterion phase had already completed.
``persist()`` inside harness v0.2 was never reached, so this freezer records the
artifacts the run actually produced plus an exact failure observation.

It records.  It does not repair, rerun, reinterpret or adjudicate, it does not
touch the consumed attempt record, and it does not modify the frozen harness —
the harness is bound by the issuance digest and altering it would destroy the
authority under which the run happened.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET  # noqa: N817
from pathlib import Path
from typing import Any

RUNTIME_ROOT = Path("/private/tmp/cdc-integration-slice-001-run-001")
IMPLEMENTATION_ROOT = Path("/private/tmp/cdc-integration-slice-001-impl")
CONTROL_ROOT = Path("/private/tmp/cdc-integration-slice-001-control")

ISSUANCE_DIGEST = "0ed920c1a1ba090c366fb1939d5d9bdb716f48150b6c8609afd6b8bdd17bfe4f"
ATTEMPT_PATH = RUNTIME_ROOT / f".cdc-integration-slice-001-attempt-{ISSUANCE_DIGEST}.json"
JUNIT_PATH = RUNTIME_ROOT / "pytest-criteria-report.xml"

TRACEBACK = (
    'Traceback (most recent call last):\n'
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-001-EXECUTION-HARNESS-v0.2.py", line 1242, '
    "in <module>\n"
    "    outcome = execute_run()\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-001-EXECUTION-HARNESS-v0.2.py", line 1068, '
    "in execute_run\n"
    "    pipeline = _pipeline_observations()\n"
    '  File ".../CDC-INTEGRATION-SLICE-001-RUN-001-EXECUTION-HARNESS-v0.2.py", line 895, '
    "in _pipeline_observations\n"
    "    positive = _run_pipeline(scratch / \"positive\")\n"
    '  File "/private/tmp/cdc-integration-slice-001-impl/tests/integration/'
    'test_cdc_integration_slice_001.py", line 189, in _run_pipeline\n'
    "    control_path.write_bytes(\n"
    "FileNotFoundError: [Errno 2] No such file or directory: "
    "'/private/tmp/cdc-integration-slice-001-run-001/pipeline/positive/control.json'"
)


def sha256(payload: bytes) -> str:
    """Persisted-file identity."""
    return hashlib.sha256(payload).hexdigest()


def canonical_digest(value: object) -> str:
    """Derivation v0.4 §1 canonical form."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def package_digest(record: dict[str, Any]) -> str:
    """Class 7 — package minus its own digest, members as identities."""
    return canonical_digest({k: v for k, v in record.items() if k != "package_digest"})


def criteria_ledger() -> dict[str, Any]:
    """The machine outcomes the criteria phase actually recorded."""
    root = ET.parse(JUNIT_PATH).getroot()  # noqa: S314
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    observations = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        outcome = (
            "FAIL"
            if failure is not None
            else "ERROR"
            if error is not None
            else "SKIPPED"
            if skipped is not None
            else "PASS"
        )
        observations.append(
            {
                "node_name": case.get("name"),
                "classname": case.get("classname"),
                "gate_outcome": outcome,
                "time": case.get("time"),
            }
        )
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_CRITERIA_LEDGER",
        "source": "pytest junit-xml emitted by harness v0.2 during the consumed run",
        "junit_reported_tests": suite.get("tests"),
        "junit_reported_failures": suite.get("failures"),
        "junit_reported_errors": suite.get("errors"),
        "junit_reported_skipped": suite.get("skipped"),
        "observations": observations,
        "observations_total": len(observations),
        "outcome_counts": {
            outcome: sum(1 for item in observations if item["gate_outcome"] == outcome)
            for outcome in sorted({item["gate_outcome"] for item in observations})
        },
    }


def failure_observation() -> dict[str, Any]:
    """Exactly what happened, in the order it happened."""
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_001_EXECUTION_FAILURE_OBSERVATION",
        "execution_id": "CDC-INTEGRATION-SLICE-001-RUN-001",
        "execution_outcome": "RAISED_AFTER_ORDINAL_CONSUMPTION",
        "ordinal_consumed": True,
        "attempt_state_observed": json.loads(ATTEMPT_PATH.read_bytes())["attempt_state"],
        "attempt_state_marked_completed": False,
        "phases": [
            {"phase": "verify_execution_authority", "reached": True, "outcome": "VALID"},
            {"phase": "preflight", "reached": True, "outcome": "PASS_45_OF_45"},
            {
                "phase": "preflight_zero_invocation_check",
                "reached": True,
                "outcome": "0_RESULT_BEARING_INVOCATIONS",
            },
            {"phase": "attempt_state_check", "reached": True, "outcome": "NO_ATTEMPT_RECORD"},
            {"phase": "consume_ordinal", "reached": True, "outcome": "CONSUMED"},
            {"phase": "run_criteria", "reached": True, "outcome": "COMPLETED_41_OF_41"},
            {"phase": "pipeline_observations", "reached": True, "outcome": "RAISED"},
            {"phase": "complete_attempt", "reached": False, "outcome": "NOT_REACHED"},
            {"phase": "persist", "reached": False, "outcome": "NOT_REACHED"},
        ],
        "exception_class": "FileNotFoundError",
        "exception_message": (
            "[Errno 2] No such file or directory: "
            "'/private/tmp/cdc-integration-slice-001-run-001/pipeline/positive/control.json'"
        ),
        "traceback": TRACEBACK,
        "defect_location": {
            "artifact": "CDC-INTEGRATION-SLICE-001-RUN-001-EXECUTION-HARNESS-v0.2.py",
            "function": "_pipeline_observations",
            "description": (
                "the harness created the shared 'pipeline' directory but not the per-scenario "
                "subdirectories it then passed to _run_pipeline, which writes into a directory "
                "it expects to already exist"
            ),
            "defect_class": "HARNESS_SCAFFOLDING_DEFECT",
            "implementation_source_implicated": False,
        },
        "rerun_performed": False,
        "second_result_bearing_execution": False,
        "automatic_retry_performed": False,
        "harness_modified_after_consumption": False,
        "attempt_record_modified_after_consumption": False,
        "pipeline_observations_produced": False,
        "positive_path_observations_produced": False,
        "toctou_observations_produced": False,
        "historical_reliance_observation_produced": False,
        "semantic_adjudication_performed": False,
    }


def preservation_observation() -> dict[str, Any]:
    """Source and history state after the consumed run."""

    def git(root: Path, *args: str) -> str:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args], capture_output=True, check=True, text=True
        ).stdout.strip()

    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_PRESERVATION_OBSERVATION",
        "implementation_head_after_run": git(IMPLEMENTATION_ROOT, "rev-parse", "HEAD"),
        "implementation_tree_after_run": git(IMPLEMENTATION_ROOT, "rev-parse", "HEAD^{tree}"),
        "implementation_worktree_porcelain_after_run": git(
            IMPLEMENTATION_ROOT, "status", "--porcelain"
        ),
        "control_head_after_run": git(CONTROL_ROOT, "rev-parse", "HEAD"),
        "control_worktree_porcelain_after_run": git(CONTROL_ROOT, "status", "--porcelain"),
        "source_modified": False,
    }


def write(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist one evidence artifact and return its identity."""
    path = RUNTIME_ROOT / name
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(data)
    return {"path": str(path), "bytes": len(data), "sha256": sha256(data)}


def main() -> dict[str, Any]:
    """Freeze the artifacts, then the package that identifies them."""
    common = {
        "execution_id": "CDC-INTEGRATION-SLICE-001-RUN-001",
        "trace_id": "CDC-INTEGRATION-SLICE-001-RUN-001-TRACE",
        "authorization_id": "OWNER-AUTHORIZATION-INTEGRATION-SLICE-001-EXEC-001",
        "execution_issuance_digest": ISSUANCE_DIGEST,
        "implementation_commit": "fa96f5c3590f54118cd926a84370be6022a80b35",
        "implementation_tree": "65a704cd9c70aef983b62ecc8176793e20004772",
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "semantic_adjudication_performed": False,
    }
    members = [
        write(
            "CDC-INTEGRATION-SLICE-001-RUN-001-EXECUTION-FAILURE-OBSERVATION-v0.1.json",
            {**common, **failure_observation()},
        ),
        write(
            "CDC-INTEGRATION-SLICE-001-RUN-001-CRITERIA-LEDGER-v0.1.json",
            {**common, **criteria_ledger()},
        ),
        write(
            "CDC-INTEGRATION-SLICE-001-RUN-001-PRESERVATION-OBSERVATION-v0.1.json",
            {**common, **preservation_observation()},
        ),
    ]
    for path in (ATTEMPT_PATH, JUNIT_PATH):
        payload = path.read_bytes()
        members.append({"path": str(path), "bytes": len(payload), "sha256": sha256(payload)})

    package = {
        **common,
        "record_class": "CDC_INTEGRATION_SLICE_001_RAW_EXECUTION_PACKAGE",
        "schema_version": "CDC-INTEGRATION-SLICE-001-RAW-EXECUTION-PACKAGE-v0.1",
        "package_state": "FROZEN_AFTER_EXECUTION_RAISED_POST_CONSUMPTION",
        "runtime_evidence_root": str(RUNTIME_ROOT),
        "execution_outcome": "RAISED_AFTER_ORDINAL_CONSUMPTION",
        "result_bearing_criteria_total": 41,
        "criteria_phase_completed": True,
        "pipeline_phase_completed": False,
        "members": [
            {"path": item["path"], "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in members
        ],
        "attempt_state": json.loads(ATTEMPT_PATH.read_bytes())["attempt_state"],
        "automatic_retry_performed": False,
        "second_result_bearing_execution": False,
        "official_handoff": "PROHIBITED",
        "package_digest": "",
    }
    package["package_digest"] = package_digest(package)
    identity = write(
        "CDC-INTEGRATION-SLICE-001-RUN-001-RAW-EXECUTION-PACKAGE-v0.1.json", package
    )
    return {"package": package, "identity": identity}


if __name__ == "__main__":
    print(json.dumps(main()["identity"], indent=2, sort_keys=True))
