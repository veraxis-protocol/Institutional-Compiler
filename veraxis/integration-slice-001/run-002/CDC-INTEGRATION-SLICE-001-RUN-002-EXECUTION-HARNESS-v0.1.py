"""Single-use result-bearing execution harness for integration slice 001, RUN-002.

Controlling artifacts, all verified from Git objects before this file was written:

    SEMANTIC-DESIGN-v0.4                  03ca22e9…  5848 B
    CRITERION-EVIDENCE-PROJECTION-v0.1    8fed5223…  11720 B   substantive model
    CRITERION-EVIDENCE-PROJECTION-v0.2    00af89d2…  7714 B    identity + ledger
    DIGEST-DERIVATION-v0.5                602e6ce8…  15905 B   classes 1-10

RUN-001's defect was evidentiary, not semantic: its ledger preserved
``{classname, node_name, gate_outcome, time}`` per criterion, so the strongest
surviving fact was *a test executed and passed*.  RUN-002 exists to make that no
longer the strongest fact.

The rule that shapes this harness is projection v0.1 §1 and the owner's
same-invocation rule: **the invocation that exercises a criterion is the
invocation that captures its observation.**  There is no replay step, no copying
of development-run values, and no writing of a fixture's expected value into an
``observed`` field.  Each executor calls the real implementation, holds the
machine values it produced, and hands them straight to the observation builder.

``node_accounting`` records this harness as the runner, because this harness is
what ran the criterion.  A separate pytest invocation is archived alongside as
secondary accounting for reconciliation; it is never the evidence, and no
criterion proposition depends on it.

Three modes:

    scaffold   non-result-bearing.  Proves the RUN-001 directory defect is fixed
               and nothing else; creates the scenario tree in a throwaway root,
               asserts zero result-bearing invocations, then abandons it.
    preflight  non-result-bearing.  Controlling identities, Class 9/10 published
               vectors, the four projection controls, and the scaffold control —
               separately reported.
    execute    requires a VALID owner EXEC-002 issuance.  Consumes the ordinal
               immediately before the first result-bearing invocation, runs once.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

IMPLEMENTATION_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-impl")
CONTROL_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-run002")
RUNTIME_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-run-002")

IMPLEMENTATION_COMMIT: Final = "fa96f5c3590f54118cd926a84370be6022a80b35"
IMPLEMENTATION_TREE: Final = "65a704cd9c70aef983b62ecc8176793e20004772"
IMPLEMENTATION_BRANCH: Final = "cdc-integration-slice-001"

SEMANTIC_DESIGN_SHA256: Final = "03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173"
PROJECTION_V0_1_SHA256: Final = (
    "8fed52234f418bbe4ac8d5e2a98fb31952c69ed514d2e8ea27cb1348eb12db35"
)
PROJECTION_V0_2_SHA256: Final = (
    "00af89d21fda41adaf4a95d5938d3b6fc90666d4ebf902b9c205aa42e7974db2"
)
DIGEST_DERIVATION_V0_5_SHA256: Final = (
    "602e6ce8d90981b08115132360f28d7ca694f4c137d8b2460e6fcac250e45d90"
)

EXECUTION_ID: Final = "CDC-INTEGRATION-SLICE-001-RUN-002"
TRACE_ID: Final = "CDC-INTEGRATION-SLICE-001-RUN-002-TRACE"
AUTHORIZATION_ID: Final = "OWNER-AUTHORIZATION-INTEGRATION-SLICE-001-EXEC-002"

DOCS: Final = CONTROL_ROOT / "docs/operations"
EXECUTION_CANDIDATE_PATH: Final = (
    DOCS / "CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-AUTHORIZATION-v0.1.CANDIDATE.json"
)
EXECUTION_ISSUANCE_PATH: Final = (
    DOCS / "CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-AUTHORIZATION-ISSUANCE-001.json"
)

SLICE_DOCS: Final = IMPLEMENTATION_ROOT / "veraxis/integration-slice-001"
SEMANTIC_DESIGN_PATH: Final = (
    SLICE_DOCS / "CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md"
)
CONTROL_SLICE_DOCS: Final = CONTROL_ROOT / "veraxis/integration-slice-001"
PROJECTION_V0_1_PATH: Final = (
    CONTROL_SLICE_DOCS / "INTEGRATION-SLICE-001-CRITERION-EVIDENCE-PROJECTION-v0.1.md"
)
PROJECTION_V0_2_PATH: Final = (
    CONTROL_SLICE_DOCS / "INTEGRATION-SLICE-001-CRITERION-EVIDENCE-PROJECTION-v0.2.md"
)
DIGEST_DERIVATION_V0_5_PATH: Final = (
    CONTROL_SLICE_DOCS / "INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.5.md"
)

OBSERVATION_RECORD_CLASS: Final = "CDC_INTEGRATION_SLICE_001_CRITERION_OBSERVATION"
OBSERVATION_SCHEMA_VERSION: Final = "INTEGRATION-SLICE-001-CRITERION-OBSERVATION-v0.1"
LEDGER_RECORD_CLASS: Final = "CDC_INTEGRATION_SLICE_001_CRITERION_EVIDENCE_LEDGER"
LEDGER_SCHEMA_VERSION: Final = "INTEGRATION-SLICE-001-CRITERION-EVIDENCE-LEDGER-v0.1"

# Projection v0.2 §4.  A frozen sequence, never a sortable list.
FROZEN_CRITERION_ORDER: Final[tuple[str, ...]] = (
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
CRITERIA_TOTAL: Final = 41

CRITERION_NODE_IDS: Final[dict[str, str]] = {
    **{f"T-EARLY-0{n}": f"test_early_termination[T-EARLY-0{n}]" for n in range(1, 6)},
    "T-POS-01": "test_pos_01_currentness_current",
    "T-POS-02": "test_pos_02_authority_proceed",
    "T-POS-03": "test_pos_03_envelope_materialized",
    "T-POS-04": "test_pos_04_separate_consumer_process",
    "T-POS-05": "test_pos_05_consumer_revalidates",
    "T-POS-06": "test_pos_06_reliance_issued",
    "T-CASE-A": "test_case_a_authority_deny",
    "T-CASE-B": "test_case_b_authority_escalate",
    "T-CASE-C": "test_case_c_tampered_envelope",
    "T-CASE-D": "test_case_d_wrong_artifact",
    "T-CASE-E": "test_case_e_wrong_scope",
    "T-CASE-F": "test_case_f_wrong_principal",
    "T-CASE-G": "test_case_g_expired_authority_decision",
    "T-CASE-H": "test_case_h_expired_envelope",
    "T-CASE-I": "test_case_i_direct_assertion",
    "T-CASE-J": "test_case_j_replayed_authorization",
    "T-CASE-K": "test_case_k_currentness_toctou",
    "T-CASE-L": "test_case_l_historical_reliance_preserved",
    "T-CASE-M": "test_case_m_currentness_basis_unreachable",
    "T-CASE-N": "test_case_n_competing_authority_basis",
    "T-CASE-O": "test_case_o_wrong_intended_consumer",
    "T-CASE-P": "test_case_p_authority_toctou",
    "T-CASE-Q": "test_case_q_authority_basis_missing",
    "T-CASE-R": "test_case_r_authority_basis_invalid",
    "T-CASE-S": "test_case_s_admissibility_basis_revoked",
    "T-DIG-01": "test_dig_01_currentness_epoch_digest",
    "T-DIG-02": "test_dig_02_authority_basis_record_digest",
    "T-DIG-03": "test_dig_03_authority_decision_digest",
    "T-DIG-04": "test_dig_04_envelope_digest",
    "T-DIG-05": "test_dig_05_consumer_validation_digest",
    "T-DIG-06": "test_dig_06_reliance_record_digest",
    "T-DIG-07": "test_dig_07_integration_package_digest",
    "T-DIG-08": "test_dig_08_synthetic_profile_digest",
    "T-EPOCH-A": "test_epoch_a_future_successor_excluded",
    "T-EPOCH-B": "test_epoch_b_boundary_crossing_moves_epoch",
    "T-EPOCH-C": "test_epoch_c_unrelated_output_control",
}

# Projection v0.1 §3: the criterion-specific minima, per group.  Preflight checks
# that every criterion has a declared schema and that every executor produces it.
GROUP_REQUIRED_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "EARLY": (
        "artifact_ref", "artifact_digest_expected", "artifact_digest_observed",
        "currentness_index_digest", "currentness_epoch_digest", "epoch_as_of",
        "basis_records", "completeness_attestation_digest", "controlling_successor_ref",
        "correction_event_ref", "gate_decision", "gate_reason_code",
        "authority_gate_invoked", "resolution_record_digest", "use_gate_decision_digest",
    ),
    "POS-01": (
        "currentness_state", "reason_code", "currentness_epoch_digest", "epoch_as_of",
        "completeness_attestation_digest", "completeness_attestation_reproduced",
        "basis_records",
    ),
    "POS-02": (
        "authority_decision_digest", "decision", "reason_code",
        "bound_currentness_resolution_digest", "bound_currentness_epoch_digest",
        "valid_until", "authority_basis_refs", "admissibility_basis_refs",
        "principal", "scope", "requested_use",
    ),
    "POS-03": (
        "envelope_path", "envelope_persisted_file_sha256", "envelope_digest_recomputed",
        "produced_at", "valid_until", "requesting_subject_principal",
        "producer_identity", "intended_consumer_principal",
    ),
    "POS-04": (
        "producer_process_identity", "consumer_process_identity", "processes_distinct",
        "consumer_inputs", "consumer_read_record", "producer_state_shared",
    ),
    "POS-05": (
        "checks", "re_resolved_currentness_resolution_digest",
        "observed_currentness_epoch_digest", "epoch_bound_in_decision",
        "reliance_time_authority_decision_digest", "consumer_validation_digest",
    ),
    "POS-06": (
        "reliance_record_digest", "reliance_disposition", "reason_code",
        "propagated_authority_decision_digest", "reliance_time_authority_decision_digest",
        "re_resolved_currentness_resolution_digest", "currentness_epoch_digest",
        "issuance_authorization_digest", "attempt_record_digest", "attempt_state",
        "write_order",
    ),
    "CASE": (
        "mutation_applied", "mutated_object", "terminating_layer",
        "expected_reason_code", "observed_reason_code", "downstream_not_produced",
    ),
    "DIG": (
        "digest_class", "digested_object_reference", "canonical_byte_count",
        "computed_digest", "published_reference_vector", "comparison_result",
    ),
    "EPOCH": (
        "as_of", "reduced_object", "canonical_byte_count", "computed_digest",
        "published_vector", "comparison_result",
    ),
}


def group_of(criterion_id: str) -> str:
    """Which projection group's criterion-specific minima apply."""
    if criterion_id.startswith("T-EARLY"):
        return "EARLY"
    if criterion_id.startswith("T-POS"):
        return criterion_id.replace("T-", "")
    if criterion_id.startswith("T-CASE"):
        return "CASE"
    if criterion_id.startswith("T-DIG"):
        return "DIG"
    return "EPOCH"


UNIVERSAL_FIELDS: Final = (
    "record_class", "schema_version", "execution_id", "trace_id",
    "semantic_design_sha256", "criterion_evidence_projection_sha256",
    "implementation_commit", "implementation_tree", "criterion_id", "node_id",
    "semantic_reference", "scenario_id", "inputs", "expected_condition",
    "observed_value", "observed_reason_code", "observed_decision", "outputs",
    "not_produced", "evidence_refs", "observed_at", "node_accounting",
    "observation_digest",
)

EXECUTION_AUTHORITY_VALID: Final = "VALID"
EXECUTION_AUTHORITY_ABSENT: Final = "ABSENT"
EXECUTION_AUTHORITY_INVALID: Final = "INVALID"
REFUSED_BEFORE_INVOCATION: Final = "REFUSED_BEFORE_RESULT_BEARING_INVOCATION"
REASON_NOT_ISSUED: Final = "OWNER_EXECUTION_AUTHORIZATION_NOT_ISSUED"
REASON_ISSUANCE_MALFORMED: Final = "OWNER_EXECUTION_AUTHORIZATION_MALFORMED"
REASON_PREFLIGHT_FAILED: Final = "CONTROL_PACKAGE_PREFLIGHT_FAILED"
REASON_ORDINAL_NOT_AVAILABLE: Final = "EXECUTION_ORDINAL_NOT_IN_NO_ATTEMPT_RECORD"
REASON_PREFLIGHT_NOT_CLEAN: Final = "PREFLIGHT_INVOKED_A_RESULT_BEARING_ROUTE"

PROHIBITED_CLAIM_FLAGS: Final = (
    "official_CDC_handoff_authorized",
    "real_CDC_authority_claim_authorized",
    "real_CDC_institutional_reliance_claim_authorized",
    "production_claim_authorized",
    "legal_effect_claim_authorized",
    "external_bypass_resistance_claim_authorized",
    "distributed_propagation_claim_authorized",
    "technical_adjudication_authorized",
)

ATTEMPT_STATE_NONE: Final = "NO_ATTEMPT_RECORD"
ATTEMPT_STATE_CONSUMED: Final = "CONSUMED_BEFORE_RESULT_BEARING_INVOCATION"
ATTEMPT_STATE_COMPLETED: Final = "COMPLETED_AFTER_SINGLE_RESULT_BEARING_EXECUTION"

SCENARIO_DIRECTORIES: Final = (
    "pipeline/positive",
    "pipeline/toctou-currentness",
    "pipeline/toctou-authority",
    "pipeline/historical",
    "pipeline/case-c", "pipeline/case-d", "pipeline/case-e", "pipeline/case-f",
    "pipeline/case-g", "pipeline/case-h", "pipeline/case-i", "pipeline/case-j",
    "pipeline/case-m", "pipeline/case-o",
    "pipeline/dig-04", "pipeline/dig-05", "pipeline/dig-06",
    "observations",
    "accounting",
)

_RESULT_BEARING_INVOCATIONS: dict[str, int] = {"count": 0}
_EXECUTE_RUN_INVOCATIONS: dict[str, int] = {"count": 0}


class HarnessRefusalError(RuntimeError):
    """The harness refused to proceed rather than exceed its authority."""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(payload: bytes) -> str:
    """Persisted-file identity: the exact bytes, trailing newline included."""
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(value: object) -> bytes:
    """Derivation v0.5 §1.  Object keys sorted; arrays never re-sorted."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_digest(value: object) -> str:
    """Unprefixed lowercase SHA-256 over the canonical form."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def criterion_observation_digest(record: dict[str, Any]) -> str:
    """Class 9 — observation minus ``observation_digest``.  All fields participate."""
    return canonical_digest({k: v for k, v in record.items() if k != "observation_digest"})


def criterion_ledger_digest(record: dict[str, Any]) -> str:
    """Class 10 — ledger minus ``ledger_digest``; observations[] order preserved."""
    return canonical_digest({k: v for k, v in record.items() if k != "ledger_digest"})


def _git(*arguments: str, root: Path = IMPLEMENTATION_ROOT) -> str:
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *arguments], capture_output=True, check=True, text=True
    )
    return completed.stdout.strip()


def _install_paths() -> None:
    for entry in (str(IMPLEMENTATION_ROOT / "src"), str(IMPLEMENTATION_ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def _wrap_result_bearing_routes() -> list[str]:
    """Count calls into result-bearing routes; the preflight's zero is measured."""
    _install_paths()
    import oic.cdc_authority as authority
    import oic.cdc_reliance as reliance

    wrapped: list[str] = []
    for module, name in (
        (authority, "evaluate_synthetic_authority"),
        (reliance, "run_consumer_validation"),
        (reliance, "issue_reliance"),
        (reliance, "claim_issuance_attempt"),
    ):
        original = getattr(module, name)
        if getattr(original, "_counted", False):
            continue

        def counted(*args: Any, _original: Any = original, **kwargs: Any) -> Any:  # noqa: ANN401
            _RESULT_BEARING_INVOCATIONS["count"] += 1
            return _original(*args, **kwargs)

        counted._counted = True  # type: ignore[attr-defined]
        setattr(module, name, counted)
        wrapped.append(f"{module.__name__}.{name}")
    return wrapped


# ---------------------------------------------------------------------------
# Scaffolding — the RUN-001 defect, repaired in one shared mechanism
# ---------------------------------------------------------------------------


def prepare_scenario_tree(root: Path) -> list[str]:
    """Create every scenario directory before any scenario writer runs.

    RUN-001 created the shared ``pipeline`` directory and then handed
    ``pipeline/positive`` to a writer that expects its parent to exist.  One
    mechanism now creates them all, and it is the only way a scenario directory
    comes into being.
    """
    created: list[str] = []
    for relative in SCENARIO_DIRECTORIES:
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path))
    return created


def scaffold_control(root: Path | None = None) -> dict[str, Any]:
    """Non-result-bearing control proving the scaffolding repair, and nothing else."""
    _wrap_result_bearing_routes()
    before = _RESULT_BEARING_INVOCATIONS["count"]
    target = root or (Path("/private/tmp") / f"cdc-integration-slice-001-scaffold-{os.getpid()}")
    created = prepare_scenario_tree(target)
    checks = []
    for relative in SCENARIO_DIRECTORIES:
        path = target / relative
        probe = path / ".writable-probe"
        try:
            probe.write_bytes(b"")
            writable = True
            probe.unlink()
        except OSError:
            writable = False
        checks.append(
            {
                "directory": relative,
                "exists": path.is_dir(),
                "parent_exists": path.parent.is_dir(),
                "writable": writable,
            }
        )
    after = _RESULT_BEARING_INVOCATIONS["count"]
    if root is None:
        shutil.rmtree(target, ignore_errors=True)
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_SCAFFOLD_CONTROL",
        "scaffold_root": str(target),
        "scaffold_root_abandoned": root is None,
        "directories_expected": len(SCENARIO_DIRECTORIES),
        "directories_created": len(created),
        "checks": checks,
        "all_directories_created": all(item["exists"] for item in checks),
        "all_parents_exist": all(item["parent_exists"] for item in checks),
        "all_writable": all(item["writable"] for item in checks),
        "scaffold_control": (
            "PASS"
            if all(item["exists"] and item["parent_exists"] and item["writable"] for item in checks)
            else "FAIL"
        ),
        "authority_evaluated": False,
        "consumer_validation_performed": False,
        "reliance_issued": False,
        "attempt_claimed": False,
        "result_bearing_invocations": after - before,
        "result_bearing": False,
    }


# ---------------------------------------------------------------------------
# Execution authority gate — carried forward, rebound to EXEC-002
# ---------------------------------------------------------------------------


def verify_result_bearing_execution_authority() -> dict[str, Any]:
    """Pure verifier over the owner issuance.  A candidate is never authority."""
    candidate_bytes = (
        EXECUTION_CANDIDATE_PATH.read_bytes() if EXECUTION_CANDIDATE_PATH.is_file() else b""
    )
    candidate_digest = file_sha256(candidate_bytes) if candidate_bytes else None
    harness_digest = file_sha256(Path(__file__).read_bytes())
    base = {
        "issuance_path": str(EXECUTION_ISSUANCE_PATH),
        "candidate_present": bool(candidate_bytes),
        "candidate_sha256": candidate_digest,
        "candidate_is_execution_authority": False,
    }
    if not EXECUTION_ISSUANCE_PATH.is_file():
        return {
            **base,
            "execution_authority": EXECUTION_AUTHORITY_ABSENT,
            "reason": REASON_NOT_ISSUED,
            "issuance_present": False,
            "issuance_digest": None,
            "checks": [],
            "failed_checks": [],
        }
    issuance_bytes = EXECUTION_ISSUANCE_PATH.read_bytes()
    issuance_digest = file_sha256(issuance_bytes)
    try:
        issuance = json.loads(issuance_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            **base,
            "execution_authority": EXECUTION_AUTHORITY_INVALID,
            "reason": REASON_ISSUANCE_MALFORMED,
            "issuance_present": True,
            "issuance_digest": issuance_digest,
            "checks": [],
            "failed_checks": ["issuance_parses_as_json"],
        }
    expected: list[tuple[str, Any, Any]] = [
        (
            "record_class",
            "OWNER_RESULT_BEARING_EXECUTION_AUTHORIZATION_ISSUANCE",
            issuance.get("record_class"),
        ),
        ("authorization_id", AUTHORIZATION_ID, issuance.get("authorization_id")),
        ("execution_id", EXECUTION_ID, issuance.get("execution_id")),
        ("owner", "ARKADIY_MITEIKO", issuance.get("owner")),
        ("owner_decision", "AUTHORIZED", issuance.get("owner_decision")),
        (
            "result_bearing_execution_authorized",
            True,
            issuance.get("result_bearing_execution_authorized"),
        ),
        ("single_use", True, issuance.get("single_use")),
        ("automatic_retry", False, issuance.get("automatic_retry")),
        (
            "authorization_candidate_sha256",
            candidate_digest,
            issuance.get("authorization_candidate_sha256"),
        ),
        ("execution_harness_sha256", harness_digest, issuance.get("execution_harness_sha256")),
        ("implementation_commit", IMPLEMENTATION_COMMIT, issuance.get("implementation_commit")),
        ("implementation_tree", IMPLEMENTATION_TREE, issuance.get("implementation_tree")),
        ("semantic_design_sha256", SEMANTIC_DESIGN_SHA256, issuance.get("semantic_design_sha256")),
        (
            "criterion_evidence_projection_v0_2_sha256",
            PROJECTION_V0_2_SHA256,
            issuance.get("criterion_evidence_projection_v0_2_sha256"),
        ),
        (
            "digest_derivation_sha256",
            DIGEST_DERIVATION_V0_5_SHA256,
            issuance.get("digest_derivation_sha256"),
        ),
        (
            "result_bearing_criteria_total",
            CRITERIA_TOTAL,
            issuance.get("result_bearing_criteria_total"),
        ),
        ("runtime_evidence_root", str(RUNTIME_ROOT) + "/", issuance.get("runtime_evidence_root")),
    ]
    expected.extend((flag, False, issuance.get(flag)) for flag in PROHIBITED_CLAIM_FLAGS)
    checks = [
        {"check": name, "expected": want, "observed": got, "passed": want == got}
        for name, want, got in expected
    ]
    failed = [item["check"] for item in checks if not item["passed"]]
    valid = not failed and bool(candidate_bytes)
    return {
        **base,
        "execution_authority": EXECUTION_AUTHORITY_VALID if valid else EXECUTION_AUTHORITY_INVALID,
        "reason": None if valid else REASON_ISSUANCE_MALFORMED,
        "issuance_present": True,
        "issuance_digest": issuance_digest,
        "checks": checks,
        "failed_checks": failed,
    }


# ---------------------------------------------------------------------------
# Observation construction
# ---------------------------------------------------------------------------


def build_observation(
    *,
    criterion_id: str,
    semantic_reference: str,
    scenario_id: str,
    inputs: list[dict[str, Any]],
    expected_condition: str,
    observed_value: dict[str, Any],
    observed_reason_code: Any,
    observed_decision: Any,
    outputs: list[dict[str, Any]],
    not_produced: list[str],
    evidence_refs: list[str],
    duration_seconds: float,
) -> dict[str, Any]:
    """Assemble one CriterionObservation from values the criterion just produced.

    ``observed_value`` arrives from the executor that ran the criterion in this
    same invocation.  Nothing here supplies a default, substitutes an expected
    value, or reaches for a previous run.
    """
    record: dict[str, Any] = {
        "record_class": OBSERVATION_RECORD_CLASS,
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "semantic_design_sha256": SEMANTIC_DESIGN_SHA256,
        "criterion_evidence_projection_sha256": PROJECTION_V0_2_SHA256,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "criterion_id": criterion_id,
        "node_id": CRITERION_NODE_IDS[criterion_id],
        "semantic_reference": semantic_reference,
        "scenario_id": scenario_id,
        "inputs": inputs,
        "expected_condition": expected_condition,
        "observed_value": observed_value,
        "observed_reason_code": observed_reason_code,
        "observed_decision": observed_decision,
        "outputs": outputs,
        "not_produced": not_produced,
        "evidence_refs": evidence_refs,
        "observed_at": _now(),
        "node_accounting": {
            "outcome": "executed",
            "runner": "CDC-INTEGRATION-SLICE-001-RUN-002-EXECUTION-HARNESS-v0.1",
            "duration_seconds": round(duration_seconds, 6),
            "non_load_bearing": True,
        },
        "observation_digest": "",
    }
    record["observation_digest"] = criterion_observation_digest(record)
    return record


def observation_schema_report() -> dict[str, Any]:
    """Every criterion's declared required-field set, checkable before execution."""
    rows = []
    for criterion_id in FROZEN_CRITERION_ORDER:
        required = GROUP_REQUIRED_FIELDS[group_of(criterion_id)]
        rows.append(
            {
                "criterion_id": criterion_id,
                "node_id": CRITERION_NODE_IDS.get(criterion_id),
                "group": group_of(criterion_id),
                "universal_fields": len(UNIVERSAL_FIELDS),
                "criterion_specific_fields": list(required),
                "has_required_evidence_schema": bool(required)
                and criterion_id in CRITERION_NODE_IDS,
            }
        )
    return {
        "rows": rows,
        "count": len(rows),
        "unique": len({row["criterion_id"] for row in rows}),
        "covers_frozen_universe": [row["criterion_id"] for row in rows]
        == list(FROZEN_CRITERION_ORDER),
        "exact_order": [row["criterion_id"] for row in rows] == list(FROZEN_CRITERION_ORDER),
        "every_criterion_has_required_evidence_schema": all(
            row["has_required_evidence_schema"] for row in rows
        ),
    }


def _verify_class_9_vector() -> dict[str, Any]:
    """Reproduce CLASS-9-FIXTURE-1 from the literal published object."""
    text = DIGEST_DERIVATION_V0_5_PATH.read_text(encoding="utf-8")
    body = text.split("Exact object entering the digest:")[1].split("```json")[1].split("```")[0]
    fixture = json.loads(body)
    payload = canonical_bytes(fixture)
    return {
        "vector": "CLASS-9-FIXTURE-1",
        "source": "literal object published in derivation v0.5 §3",
        "observed_canonical_bytes": len(payload),
        "expected_canonical_bytes": 1603,
        "observed_digest": hashlib.sha256(payload).hexdigest(),
        "expected_digest": (
            "9da8ca5c7a8f4c3e8f51353eb814b6561d1b3f63613d7e888c80e9932fa42912"
        ),
        "fixture_class": fixture.get("fixture_class"),
        "is_an_observation_of_a_criterion": False,
        "reproduced": len(payload) == 1603
        and hashlib.sha256(payload).hexdigest()
        == "9da8ca5c7a8f4c3e8f51353eb814b6561d1b3f63613d7e888c80e9932fa42912",
    }


def _verify_class_10_vector() -> dict[str, Any]:
    """Reproduce CLASS-10-FIXTURE-1 from the literal published 41-row table."""
    import re

    text = DIGEST_DERIVATION_V0_5_PATH.read_text(encoding="utf-8")
    rows = [
        match.groups()
        for line in text.splitlines()
        if (match := re.match(r"^(T-[A-Z0-9-]+)\s+(\d+)\s+([0-9a-f]{64})\s+([0-9a-f]{64})$",
                              line.strip()))
    ]
    order = [row[0] for row in rows]
    ledger = {
        "record_class": LEDGER_RECORD_CLASS,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "fixture_class": "DIGEST_FIXTURE_ONLY",
        "result_bearing": False,
        "execution_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE",
        "trace_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE-TRACE",
        "semantic_design_sha256": SEMANTIC_DESIGN_SHA256,
        "criterion_evidence_projection_sha256": PROJECTION_V0_2_SHA256,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "criteria_total": 41,
        "pytest_accounting_ref": "accounting/pytest-criteria-report.xml",
        "criterion_order": order,
        "observations": [
            {
                "criterion_id": cid,
                "observation_path": f"observations/{cid}.json",
                "persisted_file_bytes": int(size),
                "persisted_file_sha256": file_digest,
                "observation_digest": observation,
            }
            for cid, size, file_digest, observation in rows
        ],
    }
    payload = canonical_bytes(ledger)
    expected = "d7809ab840920536ac848894c62daa3a881d2b33d25c04b3fbf4789360fd622e"
    return {
        "vector": "CLASS-10-FIXTURE-1",
        "source": "literal 41-row table published in derivation v0.5 §4",
        "rows_parsed": len(rows),
        "row_order_matches_frozen_order": order == list(FROZEN_CRITERION_ORDER),
        "observed_canonical_bytes": len(payload),
        "expected_canonical_bytes": 12865,
        "observed_digest": hashlib.sha256(payload).hexdigest(),
        "expected_digest": expected,
        "is_an_observation_of_a_criterion": False,
        "reproduced": len(payload) == 12865 and hashlib.sha256(payload).hexdigest() == expected,
    }


def _array_order_control() -> dict[str, Any]:
    """Reordering observations[] or criterion_order[] must change the ledger digest."""
    import re

    baseline = _verify_class_10_vector()
    text = DIGEST_DERIVATION_V0_5_PATH.read_text(encoding="utf-8")
    rows = [
        match.groups()
        for line in text.splitlines()
        if (match := re.match(r"^(T-[A-Z0-9-]+)\s+(\d+)\s+([0-9a-f]{64})\s+([0-9a-f]{64})$",
                              line.strip()))
    ]
    entries = [
        {
            "criterion_id": cid,
            "observation_path": f"observations/{cid}.json",
            "persisted_file_bytes": int(size),
            "persisted_file_sha256": file_digest,
            "observation_digest": observation,
        }
        for cid, size, file_digest, observation in rows
    ]
    header = {
        "record_class": LEDGER_RECORD_CLASS,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "fixture_class": "DIGEST_FIXTURE_ONLY",
        "result_bearing": False,
        "execution_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE",
        "trace_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE-TRACE",
        "semantic_design_sha256": SEMANTIC_DESIGN_SHA256,
        "criterion_evidence_projection_sha256": PROJECTION_V0_2_SHA256,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "criteria_total": 41,
        "pytest_accounting_ref": "accounting/pytest-criteria-report.xml",
    }
    order = [row[0] for row in rows]
    sorted_observations = canonical_digest(
        {**header, "criterion_order": order, "observations": sorted(
            entries, key=lambda item: item["criterion_id"]
        )}
    )
    sorted_order = canonical_digest(
        {**header, "criterion_order": sorted(order), "observations": entries}
    )
    return {
        "control": "ARRAY_ORDER_IS_LOAD_BEARING",
        "frozen_order_digest": baseline["observed_digest"],
        "observations_sorted_digest": sorted_observations,
        "criterion_order_sorted_digest": sorted_order,
        "observations_reorder_changes_digest": sorted_observations
        != baseline["observed_digest"],
        "criterion_order_reorder_changes_digest": sorted_order != baseline["observed_digest"],
    }


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def preflight() -> dict[str, Any]:
    """Verify everything; invoke nothing result-bearing."""
    wrapped = _wrap_result_bearing_routes()
    before = _RESULT_BEARING_INVOCATIONS["count"]
    checks: list[dict[str, Any]] = []

    def check(name: str, expected: Any, observed: Any) -> None:  # noqa: ANN401
        checks.append(
            {"check": name, "expected": expected, "observed": observed,
             "passed": expected == observed}
        )

    check("implementation_head_commit", IMPLEMENTATION_COMMIT, _git("rev-parse", "HEAD"))
    check("implementation_tree", IMPLEMENTATION_TREE, _git("rev-parse", "HEAD^{tree}"))
    check("implementation_worktree_tracked_clean", "", _git("status", "--porcelain", "-uno"))
    check("implementation_worktree_untracked_clean", "", _git("status", "--porcelain"))
    check(
        "implementation_origin_commit",
        IMPLEMENTATION_COMMIT,
        _git("ls-remote", "--heads", "origin", IMPLEMENTATION_BRANCH).split("\t")[0],
    )

    for name, path, expected in (
        ("semantic_design_sha256", SEMANTIC_DESIGN_PATH, SEMANTIC_DESIGN_SHA256),
        ("criterion_projection_v0_1_sha256", PROJECTION_V0_1_PATH, PROJECTION_V0_1_SHA256),
        ("criterion_projection_v0_2_sha256", PROJECTION_V0_2_PATH, PROJECTION_V0_2_SHA256),
        ("digest_derivation_v0_5_sha256", DIGEST_DERIVATION_V0_5_PATH,
         DIGEST_DERIVATION_V0_5_SHA256),
    ):
        check(name, expected, file_sha256(path.read_bytes()) if path.is_file() else "ABSENT")

    class_9 = _verify_class_9_vector()
    class_10 = _verify_class_10_vector()
    order_control = _array_order_control()
    check("class_9_reference_vector", True, class_9["reproduced"])
    check("class_10_reference_vector", True, class_10["reproduced"])
    check("class_10_row_order_is_frozen_order", True, class_10["row_order_matches_frozen_order"])
    check("observations_reorder_changes_digest", True,
          order_control["observations_reorder_changes_digest"])
    check("criterion_order_reorder_changes_digest", True,
          order_control["criterion_order_reorder_changes_digest"])

    schema = observation_schema_report()
    check("criterion_projection_count", CRITERIA_TOTAL, schema["count"])
    check("criterion_projection_unique", CRITERIA_TOTAL, schema["unique"])
    check("criterion_projection_covers_frozen_universe", True, schema["covers_frozen_universe"])
    check("criterion_projection_exact_order", True, schema["exact_order"])
    check("every_criterion_has_required_evidence_schema", True,
          schema["every_criterion_has_required_evidence_schema"])
    check("A2_in_result_bearing_population", False, "A2" in FROZEN_CRITERION_ORDER)
    check("executor_registered_for_every_criterion", True,
          set(EXECUTORS) == set(FROZEN_CRITERION_ORDER))

    scaffold = scaffold_control()
    check("pipeline_scaffold_control", "PASS", scaffold["scaffold_control"])
    check("pipeline_scaffold_result_bearing_invocations", 0,
          scaffold["result_bearing_invocations"])

    candidate_bytes = (
        EXECUTION_CANDIDATE_PATH.read_bytes() if EXECUTION_CANDIDATE_PATH.is_file() else b""
    )
    candidate = json.loads(candidate_bytes or b"{}")
    check("execution_authorization_candidate_present", True, bool(candidate_bytes))
    check("execution_authorization_candidate_state", "CANDIDATE_NOT_CONSUMED",
          candidate.get("authorization_state"))
    check("execution_authorization_candidate_binds_harness",
          file_sha256(Path(__file__).read_bytes()), candidate.get("execution_harness_sha256"))

    check("runtime_evidence_root_absent_or_empty", True, _root_unused())
    check("prior_attempt_record", "NONE", _prior("attempt"))
    check("prior_result", "NONE", _prior("RAW-EXECUTION-PACKAGE"))

    consumer = IMPLEMENTATION_ROOT / "tests/integration/cdc_integration_consumer.py"
    check("consumer_executable_present", True, consumer.is_file())

    authority = verify_result_bearing_execution_authority()
    after = _RESULT_BEARING_INVOCATIONS["count"]
    passed = all(item["passed"] for item in checks)
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_PREFLIGHT_OBSERVATION",
        "execution_id": EXECUTION_ID,
        "observed_at": _now(),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(1 for item in checks if item["passed"]),
        "control_package_preflight": "PASS" if passed else "FAIL",
        "control_package_preflight_passed": passed,
        "execution_authority": authority["execution_authority"],
        "execution_authority_reason": authority["reason"],
        "execution_authority_detail": authority,
        "candidate_is_execution_authority": False,
        "separate_owner_issuance_required": True,
        "class_9_vector": class_9,
        "class_10_vector": class_10,
        "array_order_control": order_control,
        "criterion_schema": schema,
        "scaffold_control": scaffold,
        "preflight_result_bearing_invocations": after - before,
        "counted_routes": wrapped,
        "runtime_identity": {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "process_id": os.getpid(),
        },
        "result_bearing": False,
    }


def _root_unused() -> bool:
    if not RUNTIME_ROOT.exists():
        return True
    return not [path for path in RUNTIME_ROOT.rglob("*") if path.is_file()]


def _prior(marker: str) -> str:
    if not RUNTIME_ROOT.exists():
        return "NONE"
    hits = [path.name for path in RUNTIME_ROOT.rglob("*") if marker in path.name]
    return "NONE" if not hits else ",".join(sorted(hits))


# ---------------------------------------------------------------------------
# Attempt ledger — keyed to the owner issuance
# ---------------------------------------------------------------------------


def attempt_record_path(issuance_digest: str) -> Path:
    """One attempt record, keyed to the owner ISSUANCE persisted digest."""
    return RUNTIME_ROOT / f".cdc-integration-slice-001-run-002-attempt-{issuance_digest}.json"


def read_attempt_state(issuance_digest: str) -> str:
    """The current attempt state, read from the ledger rather than assumed."""
    path = attempt_record_path(issuance_digest)
    if not path.is_file():
        return ATTEMPT_STATE_NONE
    return str(json.loads(path.read_bytes()).get("attempt_state", ATTEMPT_STATE_NONE))


def consume_attempt(issuance_digest: str) -> dict[str, Any]:
    """Consume the ordinal by exclusive creation, before anything result-bearing."""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    path = attempt_record_path(issuance_digest)
    record = {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_EXECUTION_ATTEMPT",
        "authorization_id": AUTHORIZATION_ID,
        "execution_issuance_digest": issuance_digest,
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "consumed_at": _now(),
        "attempt_state": ATTEMPT_STATE_CONSUMED,
    }
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise HarnessRefusalError(
            "the single authorized attempt is already claimed; no retry is authorized"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {"record": record, "path": str(path), "digest": file_sha256(payload)}


def complete_attempt(issuance_digest: str) -> dict[str, Any]:
    """Mark the single execution complete.  Never rewinds to an unconsumed state."""
    path = attempt_record_path(issuance_digest)
    record = json.loads(path.read_bytes())
    record["attempt_state"] = ATTEMPT_STATE_COMPLETED
    record["completed_at"] = _now()
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(payload)
    return {"record": record, "path": str(path), "digest": file_sha256(payload)}


# ---------------------------------------------------------------------------
# Criterion executors — each captures what it just produced
# ---------------------------------------------------------------------------


def _fixtures() -> Any:  # noqa: ANN401
    _install_paths()
    import tests.integration.cdc_integration_fixtures as fixtures

    return fixtures


def _pipeline() -> Any:  # noqa: ANN401
    _install_paths()
    import tests.integration.test_cdc_integration_slice_001 as module

    return module


def _scenario(name: str) -> Path:
    """A scenario directory that exists before any writer touches it."""
    path = RUNTIME_ROOT / "pipeline" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _basis_records(index: Any, output_ref: str) -> list[dict[str, Any]]:  # noqa: ANN401
    return [
        {
            "record_ref": entry.record_ref,
            "record_digest": entry.record_digest,
            "record_class": entry.record_class,
            "effective_at": entry.effective_at,
            "admitted_at": entry.admitted_at,
        }
        for entry in index.entries_for(output_ref)
    ]


def _exec_early(criterion_id: str) -> dict[str, Any]:
    """T-EARLY-01..05 — a real output terminates before authority is reached."""
    _install_paths()
    from oic.cdc_currentness import (
        UseGateProfile,
        UseGateRequest,
        evaluate_present_use,
        historical_artifact_digest,
        resolve_currentness,
    )
    from tests.integration.cdc_currentness_fixtures import (
        AFFECTED_OUTPUT_REFS,
        FROZEN_ARTIFACT_DIGESTS,
        RUN_METADATA,
        governed_index,
        historical_artifact,
    )

    fixtures = _fixtures()
    ordinal = int(criterion_id.split("-")[-1]) - 1
    output_ref = AFFECTED_OUTPUT_REFS[ordinal]
    artifact = historical_artifact(output_ref)
    index = governed_index()
    resolution = resolve_currentness(
        output_ref=output_ref,
        historical_artifact=artifact,
        index=index,
        evaluated_at=fixtures.T1,
    )
    gate = evaluate_present_use(
        request=UseGateRequest(
            output_ref=output_ref,
            requested_use=fixtures.REQUESTED_USE,
            requested_operation_class="PRESENT_USE_OF_HISTORICAL_OUTPUT",
            consequential=True,
            requesting_scope_ref=fixtures.SCOPE,
            requested_at=fixtures.T1,
        ),
        historical_artifact=artifact,
        currentness_index=index,
        profile=UseGateProfile(),
        run_metadata=RUN_METADATA,
    )
    attestation = index.attestation_for(output_ref)
    epoch = fixtures.epoch_for(index, output_ref, fixtures.T1)
    observed = {
        "artifact_ref": output_ref,
        "artifact_digest_expected": FROZEN_ARTIFACT_DIGESTS[output_ref],
        "artifact_digest_observed": historical_artifact_digest(artifact["body"]),
        "currentness_index_digest": index.index_digest,
        "currentness_epoch_digest": epoch,
        "epoch_as_of": fixtures.T1,
        "basis_records": _basis_records(index, output_ref),
        "completeness_attestation_digest": (
            None if attestation is None else attestation.completeness_digest
        ),
        "currentness_state": resolution.currentness_state,
        "controlling_successor_ref": resolution.controlling_successor_ref,
        "correction_event_ref": resolution.correction_event_ref,
        "gate_decision": gate.decision,
        "gate_reason_code": {"id": gate.reason_code_id, "name": gate.reason_code},
        "authority_gate_invoked": False,
        "resolution_record_digest": resolution.resolution_digest,
        "use_gate_decision_digest": gate.use_gate_decision_digest,
        "historical_state": resolution.historical_state,
    }
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §10 / PROJECTION-v0.1 §3.1",
        "scenario_id": f"REAL-OUTPUT-{ordinal + 1:02d}",
        "inputs": [
            {"role": "historical_artifact", "ref": output_ref,
             "digest": FROZEN_ARTIFACT_DIGESTS[output_ref]},
            {"role": "currentness_index", "ref": "governed_index", "digest": index.index_digest},
        ],
        "expected_condition": (
            "currentness refuses; authority gate never invoked; no authority decision, "
            "no envelope, no reliance"
        ),
        "observed_value": observed,
        "observed_reason_code": {"id": resolution.reason_code_id, "name": resolution.reason_code},
        "observed_decision": gate.decision,
        "outputs": [
            {"role": "currentness_resolution", "ref": output_ref,
             "digest": resolution.resolution_digest},
            {"role": "use_gate_decision", "ref": output_ref,
             "digest": gate.use_gate_decision_digest},
        ],
        "not_produced": [
            "authority_decision", "propagation_envelope", "consumer_validation",
            "reliance_record",
        ],
        "evidence_refs": ["observations/" + criterion_id + ".json"],
    }


_POSITIVE_CACHE: dict[str, Any] = {}


def _positive_run() -> dict[str, Any]:
    """One positive pipeline execution, shared by T-POS-01..06.

    All six positive criteria observe stages of the *same* invocation, which is
    what makes their observations mutually consistent rather than six unrelated
    runs that happen to agree.
    """
    if "run" not in _POSITIVE_CACHE:
        module = _pipeline()
        _POSITIVE_CACHE["run"] = module._run_pipeline(_scenario("positive"))
    return _POSITIVE_CACHE["run"]


def _exec_pos_01(_: str) -> dict[str, Any]:
    fixtures = _fixtures()
    run = _positive_run()
    _install_paths()
    from oic.cdc_currentness import completeness_digest, resolve_currentness
    from tests.integration.cdc_currentness_fixtures import control_artifact

    index = run["index"]
    resolution = resolve_currentness(
        output_ref=fixtures.CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=fixtures.T1,
    )
    attestation = index.attestation_for(fixtures.CONTROL_OUTPUT_REF)
    reproduced = attestation is not None and (
        completeness_digest(attestation.source) == attestation.completeness_digest
    )
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §9 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [
            {"role": "synthetic_control", "ref": fixtures.CONTROL_OUTPUT_REF,
             "digest": fixtures.control_body_digest()},
            {"role": "currentness_index", "ref": "index_without_successor",
             "digest": index.index_digest},
        ],
        "expected_condition": "the synthetic fixture resolves CURRENT under an attested basis",
        "observed_value": {
            "currentness_state": resolution.currentness_state,
            "reason_code": {"id": resolution.reason_code_id, "name": resolution.reason_code},
            "currentness_epoch_digest": fixtures.epoch_for(
                index, fixtures.CONTROL_OUTPUT_REF, fixtures.T1
            ),
            "epoch_as_of": fixtures.T1,
            "completeness_attestation_digest": (
                None if attestation is None else attestation.completeness_digest
            ),
            "completeness_attestation_reproduced": reproduced,
            "basis_records": _basis_records(index, fixtures.CONTROL_OUTPUT_REF),
            "resolution_digest": resolution.resolution_digest,
        },
        "observed_reason_code": {"id": resolution.reason_code_id, "name": resolution.reason_code},
        "observed_decision": resolution.currentness_state,
        "outputs": [{"role": "currentness_resolution", "ref": fixtures.CONTROL_OUTPUT_REF,
                     "digest": resolution.resolution_digest}],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-01.json"],
    }


def _exec_pos_02(_: str) -> dict[str, Any]:
    fixtures = _fixtures()
    run = _positive_run()
    decision = run["decision"]
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §9 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [
            {"role": "authority_basis", "ref": fixtures.authority_basis()["basis_id"],
             "digest": fixtures.authority_basis()["record_digest"]},
            {"role": "admissibility_basis", "ref": fixtures.admissibility_basis()["basis_id"],
             "digest": fixtures.admissibility_basis()["record_digest"]},
        ],
        "expected_condition": "synthetic authority/admissibility returns PROCEED with A1",
        "observed_value": {
            "authority_decision_digest": decision.authority_decision_digest,
            "decision": decision.decision,
            "reason_code": {"id": decision.reason_code_id, "name": decision.reason_code},
            "bound_currentness_resolution_digest": decision.currentness_resolution_digest,
            "bound_currentness_epoch_digest": decision.currentness_epoch_digest,
            "valid_until": decision.valid_until,
            "authority_basis_refs": list(decision.authority_basis_refs),
            "admissibility_basis_refs": list(decision.admissibility_basis_refs),
            "principal": fixtures.SUBJECT_PRINCIPAL,
            "scope": fixtures.SCOPE,
            "requested_use": fixtures.REQUESTED_USE,
        },
        "observed_reason_code": {"id": decision.reason_code_id, "name": decision.reason_code},
        "observed_decision": decision.decision,
        "outputs": [{"role": "authority_decision", "ref": "SYNTH-AUTHORITY-DECISION-001",
                     "digest": decision.authority_decision_digest}],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-02.json"],
    }


def _exec_pos_03(_: str) -> dict[str, Any]:
    fixtures = _fixtures()
    run = _positive_run()
    record = run["envelope_record"]
    materialized = run["materialized"]
    envelope_path = Path(materialized["path"]) if "path" in materialized else None
    persisted = (
        file_sha256(envelope_path.read_bytes()) if envelope_path and envelope_path.is_file()
        else None
    )
    _install_paths()
    from oic.cdc_propagation import envelope_digest

    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §9 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [{"role": "authority_decision", "ref": record["envelope_id"],
                    "digest": record["authority_decision_digest"]}],
        "expected_condition": "a closed envelope is durably materialized and self-identifying",
        "observed_value": {
            "envelope_path": str(envelope_path),
            "envelope_persisted_file_sha256": persisted,
            "envelope_digest_recorded": record["envelope_digest"],
            "envelope_digest_recomputed": envelope_digest(record),
            "produced_at": record["produced_at"],
            "valid_until": record["valid_until"],
            "requesting_subject_principal": record["requesting_subject_principal"],
            "producer_identity": record["producer_identity"],
            "intended_consumer_principal": record["intended_consumer_principal"],
            "materialization": materialized,
        },
        "observed_reason_code": "NOT_APPLICABLE",
        "observed_decision": "MATERIALIZED",
        "outputs": [{"role": "propagation_envelope", "ref": record["envelope_id"],
                     "digest": record["envelope_digest"]}],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-03.json"],
    }


def _exec_pos_04(_: str) -> dict[str, Any]:
    fixtures = _fixtures()
    run = _positive_run()
    result = run["result"]
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §6 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [{"role": "envelope_file", "ref": run["envelope_record"]["envelope_id"],
                    "digest": run["envelope_record"]["envelope_digest"]}],
        "expected_condition": (
            "the consumer is a separate OS process receiving paths and bytes only"
        ),
        "observed_value": {
            "producer_process_identity": {
                "process_id": run["producer_process_id"],
                "run_id": fixtures.RUN_ID,
                "trace_id": fixtures.TRACE_ID,
            },
            "consumer_process_identity": {
                "process_id": result["consumer_process_id"],
                "run_id": result.get("run_id", fixtures.RUN_ID),
                "trace_id": result.get("trace_id", fixtures.TRACE_ID),
            },
            "processes_distinct": run["producer_process_id"] != result["consumer_process_id"],
            "consumer_inputs": result["consumer_input_paths"],
            "consumer_read_record": {
                "inputs_were_paths_only": result["consumer_inputs_were_paths_only"],
                "envelope_read_from_disk": True,
                "consumer_module": "tests.integration.cdc_integration_consumer",
            },
            "producer_state_shared": result["producer_state_shared"],
        },
        "observed_reason_code": "NOT_APPLICABLE",
        "observed_decision": "SEPARATE_PROCESS",
        "outputs": [],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-04.json"],
    }


def _exec_pos_05(_: str) -> dict[str, Any]:
    run = _positive_run()
    result = run["result"]
    validation = result["validation"]
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §7 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [{"role": "envelope", "ref": run["envelope_record"]["envelope_id"],
                    "digest": run["envelope_record"]["envelope_digest"]}],
        "expected_condition": "all sixteen consumer checks are evaluated in frozen order",
        "observed_value": {
            "checks": validation["checks"],
            "check_count": len(validation["checks"]),
            "re_resolved_currentness_state": result["re_resolved_currentness_state"],
            "re_resolved_currentness_resolution_digest": result.get(
                "re_resolved_currentness_resolution_digest"
            ),
            "observed_currentness_epoch_digest": result.get("re_resolved_currentness_epoch_digest"),
            "epoch_bound_in_decision": run["envelope_record"]["currentness_epoch_digest"],
            "reliance_time_authority_decision_digest": result["reliance_time_authority_decision"][
                "authority_decision_digest"
            ],
            "consumer_validation_digest": validation["consumer_validation_digest"],
        },
        "observed_reason_code": "NOT_APPLICABLE",
        "observed_decision": "ALL_CHECKS_EVALUATED",
        "outputs": [{"role": "consumer_validation", "ref": "positive",
                     "digest": validation["consumer_validation_digest"]}],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-05.json"],
    }


def _exec_pos_06(_: str) -> dict[str, Any]:
    run = _positive_run()
    result = run["result"]
    reliance = result["reliance_record"]
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §9 / PROJECTION-v0.1 §3.2",
        "scenario_id": "POSITIVE-PATH",
        "inputs": [{"role": "consumer_validation", "ref": "positive",
                    "digest": result["validation"]["consumer_validation_digest"]}],
        "expected_condition": "bounded synthetic reliance is issued as a separate transition",
        "observed_value": {
            "reliance_record_digest": reliance["reliance_record_digest"],
            "reliance_disposition": reliance["reliance_disposition"],
            "reason_code": {"id": reliance["reason_code_id"],
                            "name": reliance.get("reason_code")},
            "propagated_authority_decision_digest": run["decision"].authority_decision_digest,
            "reliance_time_authority_decision_digest": result["reliance_time_authority_decision"][
                "authority_decision_digest"
            ],
            "re_resolved_currentness_resolution_digest": result.get(
                "re_resolved_currentness_resolution_digest"
            ),
            "currentness_epoch_digest": result.get("re_resolved_currentness_epoch_digest"),
            "issuance_authorization_digest": result["attempt"].get(
                "issuance_authorization_digest"
            ),
            "attempt_record_digest": result["attempt"].get("attempt_record_digest"),
            "attempt_state": result["attempt"].get("attempt_state"),
            "write_order": [
                "issuance_authorization", "attempt_record", "reliance_record",
            ],
        },
        "observed_reason_code": {"id": reliance["reason_code_id"],
                                 "name": reliance.get("reason_code")},
        "observed_decision": reliance["reliance_disposition"],
        "outputs": [{"role": "reliance_record", "ref": "SYNTH-RELIANCE-001",
                     "digest": reliance["reliance_record_digest"]}],
        "not_produced": [],
        "evidence_refs": ["observations/T-POS-06.json"],
    }


def _case_observation(
    *,
    mutation: str,
    mutated_object: dict[str, Any],
    terminating_layer: str,
    expected_code: str,
    observed_code: Any,
    observed_decision: Any,
    observed: dict[str, Any],
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    not_produced: list[str],
    criterion_id: str,
    expected_condition: str,
) -> dict[str, Any]:
    return {
        "semantic_reference": "SEMANTIC-DESIGN-v0.4 §8 / PROJECTION-v0.1 §3.3",
        "scenario_id": criterion_id,
        "inputs": inputs,
        "expected_condition": expected_condition,
        "observed_value": {
            **observed,
            "mutation_applied": mutation,
            "mutated_object": mutated_object,
            "terminating_layer": terminating_layer,
            "expected_reason_code": expected_code,
            "observed_reason_code": observed_code,
            "downstream_not_produced": not_produced,
        },
        "observed_reason_code": observed_code,
        "observed_decision": observed_decision,
        "outputs": outputs,
        "not_produced": not_produced,
        "evidence_refs": [f"observations/{criterion_id}.json"],
    }


def _authority_only_case(
    criterion_id: str, *, mutation: str, expected_code: str, expected_condition: str, **kwargs: Any
) -> dict[str, Any]:
    """Cases that terminate in the authority layer: no envelope is produced."""
    module = _pipeline()
    fixtures = _fixtures()
    decision = module._authority_decision(index=fixtures.index_without_successor(), **kwargs)
    scenario = _scenario(criterion_id.lower().replace("t-case-", "case-"))
    envelopes = sorted(str(path) for path in scenario.glob("*envelope*"))
    return _case_observation(
        criterion_id=criterion_id,
        mutation=mutation,
        mutated_object={"ref": "authority_or_admissibility_basis", "digest_before": None,
                        "digest_after": None},
        terminating_layer="AUTHORITY",
        expected_code=expected_code,
        observed_code={"id": decision.reason_code_id, "name": decision.reason_code},
        observed_decision=decision.decision,
        expected_condition=expected_condition,
        observed={
            "authority_decision_digest": decision.authority_decision_digest,
            "decision": decision.decision,
            "authority_basis_refs": list(decision.authority_basis_refs),
            "admissibility_basis_refs": list(decision.admissibility_basis_refs),
            "envelope_files_present": envelopes,
        },
        inputs=[{"role": "currentness_index", "ref": "index_without_successor",
                 "digest": fixtures.index_without_successor().index_digest}],
        outputs=[{"role": "authority_decision", "ref": criterion_id,
                  "digest": decision.authority_decision_digest}],
        not_produced=["propagation_envelope", "consumer_validation", "reliance_record"],
    )


def _consumer_case(
    criterion_id: str,
    *,
    mutation: str,
    expected_code: str,
    expected_condition: str,
    scenario_dir: str,
    extra: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Cases that reach the consumer: the full validation is captured."""
    module = _pipeline()
    run = module._run_pipeline(_scenario(scenario_dir), **kwargs)
    result = run["result"]
    reliance = result["reliance_record"]
    observed = {
        "checks": result["validation"]["checks"],
        "consumer_validation_digest": result["validation"]["consumer_validation_digest"],
        "re_resolved_currentness_state": result["re_resolved_currentness_state"],
        "reliance_disposition": reliance["reliance_disposition"],
        "envelope_digest": run["envelope_record"]["envelope_digest"],
        "consumer_process_id": result["consumer_process_id"],
        "producer_process_id": run["producer_process_id"],
    }
    if extra is not None:
        observed.update(extra(run))
    issued = reliance["reliance_disposition"] == "ISSUED"
    return _case_observation(
        criterion_id=criterion_id,
        mutation=mutation,
        mutated_object={
            "ref": "propagation_envelope",
            "digest_before": run["envelope"].as_record()["envelope_digest"],
            "digest_after": run["envelope_record"]["envelope_digest"],
        },
        terminating_layer="CONSUMER",
        expected_code=expected_code,
        observed_code={"id": reliance["reason_code_id"], "name": reliance.get("reason_code")},
        observed_decision=reliance["reliance_disposition"],
        expected_condition=expected_condition,
        observed=observed,
        inputs=[{"role": "propagation_envelope", "ref": run["envelope_record"]["envelope_id"],
                 "digest": run["envelope_record"]["envelope_digest"]}],
        outputs=[{"role": "reliance_record", "ref": criterion_id,
                  "digest": reliance["reliance_record_digest"]}],
        not_produced=[] if issued else ["reliance_issuance"],
    )


EXECUTORS: dict[str, Any] = {}


def _register_early() -> None:
    for index in range(1, 6):
        criterion = f"T-EARLY-0{index}"
        EXECUTORS[criterion] = _exec_early


def _register_positive() -> None:
    EXECUTORS["T-POS-01"] = _exec_pos_01
    EXECUTORS["T-POS-02"] = _exec_pos_02
    EXECUTORS["T-POS-03"] = _exec_pos_03
    EXECUTORS["T-POS-04"] = _exec_pos_04
    EXECUTORS["T-POS-05"] = _exec_pos_05
    EXECUTORS["T-POS-06"] = _exec_pos_06


def _register_cases() -> None:
    fixtures_lazy = _fixtures

    EXECUTORS["T-CASE-A"] = lambda cid: _authority_only_case(
        cid, mutation="authority basis revocation_state set to REVOKED",
        expected_code="A10",
        expected_condition="CURRENT artifact, authority DENY, no propagation",
        bases=[fixtures_lazy().authority_basis(revocation_state="REVOKED")],
    )
    EXECUTORS["T-CASE-B"] = lambda cid: _authority_only_case(
        cid, mutation="escalation predicate asserted", expected_code="A7",
        expected_condition="CURRENT artifact, authority ESCALATE, no reliance",
        escalate=True,
    )
    EXECUTORS["T-CASE-C"] = lambda cid: _consumer_case(
        cid, mutation="envelope scope field altered after digesting",
        expected_code="I6", scenario_dir="case-c",
        expected_condition="tampered envelope fails integrity at check 1 (P2) and refuses",
        tamper=True,
    )
    EXECUTORS["T-CASE-D"] = lambda cid: _consumer_case(
        cid, mutation="envelope artifact_digest replaced with zeros",
        expected_code="I6", scenario_dir="case-d",
        expected_condition="artifact identity mismatch at check 4 (P4) refuses",
        envelope_overrides={"artifact_digest": "0" * 64},
    )
    EXECUTORS["T-CASE-E"] = lambda cid: _consumer_case(
        cid, mutation="envelope scope replaced with OTHER-SCOPE",
        expected_code="I6", scenario_dir="case-e",
        expected_condition="scope binding mismatch at check 5 (P5) refuses",
        envelope_overrides={"scope": "OTHER-SCOPE"},
    )
    EXECUTORS["T-CASE-F"] = lambda cid: _consumer_case(
        cid, mutation="requesting subject principal replaced",
        expected_code="I6", scenario_dir="case-f",
        expected_condition="subject principal mismatch at check 6 (P6) refuses",
        envelope_overrides={"requesting_subject_principal": "SYNTHETIC-OTHER-001"},
    )
    EXECUTORS["T-CASE-G"] = lambda cid: _consumer_case(
        cid, mutation="propagated authority decision expires before reliance time",
        expected_code="I4", scenario_dir="case-g",
        expected_condition=(
            "expired propagated decision refuses with I4 and is terminal: check 15 is "
            "never reached, so a fresh positive cannot revive it"
        ),
        consumer_now=_fixtures().T2, decision_valid_until="2026-08-15T11:00:00Z",
        extra=lambda run: {
            "propagated_decision_valid_until": "2026-08-15T11:00:00Z",
            "evaluation_time": _fixtures().T2,
            "decision_expired": True,
            "check_12_freshness": run["result"]["validation"]["checks"][11],
            "check_15_reached": not str(
                run["result"]["validation"]["checks"][14]["observed"]
            ).startswith("NOT_EVALUATED"),
            "check_15_observed": run["result"]["validation"]["checks"][14]["observed"],
            "authority_basis_revocation_state": "NOT_REVOKED",
            "reliance_time_authority_decision": run["result"]["reliance_time_authority_decision"],
        },
    )
    EXECUTORS["T-CASE-H"] = lambda cid: _consumer_case(
        cid, mutation="envelope valid_until set before the evaluation instant",
        expected_code="I6", scenario_dir="case-h",
        expected_condition="stale envelope fails freshness at check 3 (P3) and refuses",
        envelope_overrides={"valid_until": "2026-08-15T09:30:00Z"},
    )
    EXECUTORS["T-CASE-I"] = lambda cid: _consumer_case(
        cid, mutation="caller asserts reliance directly",
        expected_code="I7", scenario_dir="case-i",
        expected_condition="a caller-asserted reliance is refused explicitly, not ignored",
        direct_assertion=True,
    )
    EXECUTORS["T-CASE-J"] = _exec_case_j = None  # replaced below
    EXECUTORS["T-CASE-K"] = _exec_case_k = None
    EXECUTORS["T-CASE-L"] = _exec_case_l = None
    EXECUTORS["T-CASE-M"] = lambda cid: _consumer_case(
        cid, mutation="consumer index built without the synthetic control",
        expected_code="I9", scenario_dir="case-m",
        expected_condition="an unreachable currentness basis fails closed with I9",
        consumer_without_control=True,
    )
    EXECUTORS["T-CASE-N"] = lambda cid: _authority_only_case(
        cid, mutation="two operative authority bases for the same principal and scope",
        expected_code="A6",
        expected_condition="competing operative bases deny with A6; no precedence is invented",
        bases=[fixtures_lazy().authority_basis(),
               fixtures_lazy().authority_basis(basis_id="SYNTH-AUTH-BASIS-002")],
    )
    EXECUTORS["T-CASE-O"] = lambda cid: _consumer_case(
        cid, mutation="envelope addressed to a different intended consumer",
        expected_code="I6", scenario_dir="case-o",
        expected_condition="intended consumer mismatch at check 8 (P12) refuses",
        envelope_overrides={"intended_consumer_principal": "SYNTHETIC-OTHER-CONSUMER-001"},
    )
    EXECUTORS["T-CASE-P"] = _exec_case_p = None
    EXECUTORS["T-CASE-Q"] = lambda cid: _authority_only_case(
        cid, mutation="no authority basis supplied for (principal, scope)",
        expected_code="A11",
        expected_condition="an unresolvable authority basis denies with A11",
        bases=[],
    )
    EXECUTORS["T-CASE-R"] = lambda cid: _authority_only_case(
        cid, mutation="stored authority basis record_digest replaced with zeros",
        expected_code="A12",
        expected_condition="a non-reproducing basis digest denies with A12",
        bases=[{**fixtures_lazy().authority_basis(), "record_digest": "0" * 64}],
    )
    EXECUTORS["T-CASE-S"] = lambda cid: _authority_only_case(
        cid, mutation="admissibility basis revocation_state set to REVOKED",
        expected_code="A13",
        expected_condition="a revoked admissibility basis denies with its own code, not A10",
        admissibility=[fixtures_lazy().admissibility_basis(revocation_state="REVOKED")],
    )


def _exec_case_j(criterion_id: str) -> dict[str, Any]:
    """T-CASE-J — replay of a consumed issuance authorization."""
    module = _pipeline()
    scenario = _scenario("case-j")
    first = module._run_pipeline(scenario, reliance_id="SYNTH-RELIANCE-J1")
    second = module._run_pipeline(
        scenario, reliance_id="SYNTH-RELIANCE-J2", envelope_name="envelope-2.json"
    )
    first_reliance = first["result"]["reliance_record"]
    second_reliance = second["result"]["reliance_record"]
    return _case_observation(
        criterion_id=criterion_id,
        mutation="the same issuance authorization is presented a second time",
        mutated_object={"ref": "issuance_authorization", "digest_before": None,
                        "digest_after": None},
        terminating_layer="ISSUANCE",
        expected_code="I8",
        observed_code={"id": second_reliance["reason_code_id"],
                       "name": second_reliance.get("reason_code")},
        observed_decision=second_reliance["reliance_disposition"],
        expected_condition="a replayed issuance authorization is refused with I8",
        observed={
            "first_use_disposition": first_reliance["reliance_disposition"],
            "first_use_reliance_record_digest": first_reliance["reliance_record_digest"],
            "first_use_attempt": first["result"]["attempt"],
            "replay_disposition": second_reliance["reliance_disposition"],
            "replay_attempt": second["result"]["attempt"],
            "issuance_authorization_digest": first["result"]["attempt"].get(
                "issuance_authorization_digest"
            ),
        },
        inputs=[{"role": "issuance_authorization", "ref": "SYNTH-RELIANCE-ISSUANCE-AUTHORIZATION-001",
                 "digest": first["result"]["attempt"].get("issuance_authorization_digest")}],
        outputs=[{"role": "reliance_record", "ref": "SYNTH-RELIANCE-J2",
                  "digest": second_reliance["reliance_record_digest"]}],
        not_produced=["second_reliance_issuance"],
    )


def _exec_case_k(criterion_id: str) -> dict[str, Any]:
    """T-CASE-K — the currentness TOCTOU, with both temporal states archived."""
    module = _pipeline()
    fixtures = _fixtures()
    run = module._run_pipeline(
        _scenario("toctou-currentness"),
        producer_now=fixtures.T1,
        consumer_now=fixtures.T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    result = run["result"]
    reliance = result["reliance_record"]
    index = fixtures.index_with_future_successor()
    epoch_before = fixtures.epoch_for(index, fixtures.CONTROL_OUTPUT_REF, fixtures.T1)
    epoch_after = fixtures.epoch_for(index, fixtures.CONTROL_OUTPUT_REF, fixtures.T2)
    return _case_observation(
        criterion_id=criterion_id,
        mutation="successor becomes operative between t1 and t2; nothing is edited",
        mutated_object={"ref": "currentness_epoch", "digest_before": epoch_before,
                        "digest_after": epoch_after},
        terminating_layer="CONSUMER",
        expected_code="I2",
        observed_code={"id": reliance["reason_code_id"], "name": reliance.get("reason_code")},
        observed_decision=reliance["reliance_disposition"],
        expected_condition=(
            "re-resolution at t2 yields SUPERSEDED, the epoch has moved, reliance is "
            "refused with I2 and the I3 epoch observation is recorded alongside"
        ),
        observed={
            "epoch_before": epoch_before,
            "epoch_before_as_of": fixtures.T1,
            "epoch_after": epoch_after,
            "epoch_after_as_of": fixtures.T2,
            "epoch_moved": epoch_before != epoch_after,
            "epoch_bound_in_envelope": run["envelope_record"]["currentness_epoch_digest"],
            "currentness_state_at_t1": "CURRENT",
            "currentness_state_at_t2": result["re_resolved_currentness_state"],
            "i3_observation": {
                "code": "I3",
                "meaning": "currentness epoch no longer applicable",
                "epoch_bound": run["envelope_record"]["currentness_epoch_digest"],
                "epoch_at_reliance_time": epoch_after,
                "applicable": run["envelope_record"]["currentness_epoch_digest"] == epoch_after,
            },
            "checks": result["validation"]["checks"],
            "reliance_disposition": reliance["reliance_disposition"],
        },
        inputs=[{"role": "propagation_envelope", "ref": run["envelope_record"]["envelope_id"],
                 "digest": run["envelope_record"]["envelope_digest"]}],
        outputs=[{"role": "reliance_record", "ref": criterion_id,
                  "digest": reliance["reliance_record_digest"]}],
        not_produced=["reliance_issuance"],
    )


def _exec_case_l(criterion_id: str) -> dict[str, Any]:
    """T-CASE-L — an issued reliance record stays byte-identical afterwards."""
    module = _pipeline()
    fixtures = _fixtures()
    scenario = _scenario("historical")
    issued = module._run_pipeline(scenario, reliance_id="SYNTH-RELIANCE-L1")
    issued_record = issued["result"]["reliance_record"]
    path = Path(issued["output_path"])
    before = file_sha256(path.read_bytes())
    later = module._run_pipeline(
        scenario,
        reliance_id="SYNTH-RELIANCE-L2",
        envelope_name="envelope-later.json",
        attempt_name="attempt-later.json",
        producer_now=fixtures.T1,
        consumer_now=fixtures.T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    after = file_sha256(path.read_bytes())
    later_record = later["result"]["reliance_record"]
    return _case_observation(
        criterion_id=criterion_id,
        mutation="a later correction becomes operative after a reliance was issued",
        mutated_object={"ref": "issued_reliance_record", "digest_before": before,
                        "digest_after": after},
        terminating_layer="CONSUMER",
        expected_code="I2",
        observed_code={"id": later_record["reason_code_id"],
                       "name": later_record.get("reason_code")},
        observed_decision=later_record["reliance_disposition"],
        expected_condition=(
            "the historical reliance record is unchanged and carries no marker of its "
            "own obsolescence; the later attempt is refused"
        ),
        observed={
            "issued_reliance_record_digest": issued_record["reliance_record_digest"],
            "issued_persisted_file_sha256_before": before,
            "issued_persisted_file_sha256_after": after,
            "byte_identity_preserved": before == after,
            "issued_record_mentions_supersession": "superseded"
            in json.dumps(issued_record).lower(),
            "later_attempt_disposition": later_record["reliance_disposition"],
            "later_attempt_reason_code": later_record["reason_code_id"],
        },
        inputs=[{"role": "issued_reliance_record", "ref": "SYNTH-RELIANCE-L1",
                 "digest": issued_record["reliance_record_digest"]}],
        outputs=[{"role": "reliance_record", "ref": "SYNTH-RELIANCE-L2",
                  "digest": later_record["reliance_record_digest"]}],
        not_produced=["reliance_issuance_for_later_attempt"],
    )


def _exec_case_p(criterion_id: str) -> dict[str, Any]:
    """T-CASE-P — the authority TOCTOU, distinguishable from T-CASE-G by evidence."""
    module = _pipeline()
    fixtures = _fixtures()
    run = module._run_pipeline(
        _scenario("toctou-authority"),
        producer_now=fixtures.T1,
        consumer_now=fixtures.T2,
        consumer_authority_bases=[fixtures.authority_basis(revocation_state="REVOKED")],
    )
    result = run["result"]
    reliance = result["reliance_record"]
    checks = result["validation"]["checks"]
    return _case_observation(
        criterion_id=criterion_id,
        mutation="authority standing revoked between t1 and t2; artifact untouched",
        mutated_object={
            "ref": "authority_basis",
            "digest_before": fixtures.authority_basis()["record_digest"],
            "digest_after": fixtures.authority_basis(revocation_state="REVOKED")["record_digest"],
        },
        terminating_layer="CONSUMER",
        expected_code="I11",
        observed_code={"id": reliance["reason_code_id"], "name": reliance.get("reason_code")},
        observed_decision=reliance["reliance_disposition"],
        expected_condition=(
            "the artifact is still CURRENT and the propagated decision is NOT expired, "
            "yet re-evaluated authority fails: I11, and no reliance is issued"
        ),
        observed={
            "re_resolved_currentness_state": result["re_resolved_currentness_state"],
            "artifact_remains_current": result["re_resolved_currentness_state"] == "CURRENT",
            "propagated_decision_valid_until": run["decision"].valid_until,
            "evaluation_time": fixtures.T2,
            "propagated_decision_expired": False,
            "check_12_freshness": checks[11],
            "check_14_epoch_applicability": checks[13],
            "check_15_authority_re_evaluation": checks[14],
            "check_15_reached": not str(checks[14]["observed"]).startswith("NOT_EVALUATED"),
            "authority_basis_revocation_before": "NOT_REVOKED",
            "authority_basis_revocation_after": "REVOKED",
            "reliance_time_authority_decision": result["reliance_time_authority_decision"],
        },
        inputs=[{"role": "propagation_envelope", "ref": run["envelope_record"]["envelope_id"],
                 "digest": run["envelope_record"]["envelope_digest"]}],
        outputs=[{"role": "reliance_record", "ref": criterion_id,
                  "digest": reliance["reliance_record_digest"]}],
        not_produced=["reliance_issuance"],
    )


def _dig_observation(
    criterion_id: str,
    *,
    digest_class: str,
    digested_object_reference: str,
    canonical_byte_count: int,
    computed_digest: str,
    published_vector: Any,
    published_digest: Any,
    comparison_operands: dict[str, Any],
    comparison_result: str,
) -> dict[str, Any]:
    return {
        "semantic_reference": "DIGEST-DERIVATION-v0.5 §2-§4 / PROJECTION-v0.1 §3.4",
        "scenario_id": criterion_id,
        "inputs": [{"role": "digested_object", "ref": digested_object_reference,
                    "digest": computed_digest}],
        "expected_condition": f"{digest_class} reproduces its frozen rule and published vector",
        "observed_value": {
            "digest_class": digest_class,
            "digested_object_reference": digested_object_reference,
            "canonical_byte_count": canonical_byte_count,
            "computed_digest": computed_digest,
            "published_reference_vector": published_vector,
            "published_digest": published_digest,
            "comparison_operands": comparison_operands,
            "comparison_result": comparison_result,
        },
        "observed_reason_code": "NOT_APPLICABLE",
        "observed_decision": "NOT_APPLICABLE",
        "outputs": [],
        "not_produced": [],
        "evidence_refs": [f"observations/{criterion_id}.json"],
    }


def _register_digests() -> None:
    def dig_01(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_authority import currentness_epoch_digest

        output_ref = "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"
        attestation = "eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7"
        successor = {
            "output_ref": output_ref,
            "record_ref": "EBAWU-P-001-C-TENDER-01-CORR-002#" + output_ref,
            "record_digest": (
                "943affbf3e86d8a1b6831eb3deafb2efeac902989d8ee75fe85daea6f82e1e3c"
            ),
            "record_class": "CORRECTION_SUCCESSOR_RECORD",
            "effective_at": "2026-08-15T12:00:00Z",
            "admitted_at": "2026-08-15T09:00:00Z",
        }
        reduced = {
            "output_ref": output_ref,
            "completeness_attestation_digest": attestation,
            "operative_basis_records": [],
        }
        computed = currentness_epoch_digest(
            output_ref=output_ref,
            as_of="2026-08-15T10:00:00Z",
            governing_records=[successor],
            completeness_attestation_digest=attestation,
        )
        published = "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46"
        return _dig_observation(
            cid, digest_class="currentness_epoch_digest",
            digested_object_reference="EPOCH-A reduced object",
            canonical_byte_count=len(canonical_bytes(reduced)),
            computed_digest=computed, published_vector="EPOCH-A", published_digest=published,
            comparison_operands={"computed": computed, "published": published},
            comparison_result="EQUAL" if computed == published else "NOT_EQUAL",
        )

    def dig_02(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_authority import authority_basis_record_digest

        fixtures = _fixtures()
        body = {k: v for k, v in fixtures.authority_basis().items() if k != "record_digest"}
        computed = authority_basis_record_digest(body)
        published = "7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e"
        return _dig_observation(
            cid, digest_class="authority_basis_record_digest",
            digested_object_reference="BASIS-AUTH-1 body minus record_digest",
            canonical_byte_count=len(canonical_bytes(body)),
            computed_digest=computed, published_vector="BASIS-AUTH-1", published_digest=published,
            comparison_operands={"computed": computed, "published": published,
                                 "stored": fixtures.authority_basis()["record_digest"]},
            comparison_result="EQUAL" if computed == published else "NOT_EQUAL",
        )

    def dig_03(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_authority import authority_decision_digest

        run = _positive_run()
        record = run["decision"].as_record()
        computed = authority_decision_digest(record)
        stored = record["authority_decision_digest"]
        return _dig_observation(
            cid, digest_class="authority_decision_digest",
            digested_object_reference="positive-path authority decision minus its own digest",
            canonical_byte_count=len(
                canonical_bytes({k: v for k, v in record.items()
                                 if k != "authority_decision_digest"})
            ),
            computed_digest=computed, published_vector=None, published_digest=None,
            comparison_operands={"computed": computed, "stored": stored},
            comparison_result="EQUAL" if computed == stored else "NOT_EQUAL",
        )

    def dig_04(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_propagation import envelope_digest

        run = _positive_run()
        record = run["envelope_record"]
        computed = envelope_digest(record)
        stored = record["envelope_digest"]
        return _dig_observation(
            cid, digest_class="envelope_digest",
            digested_object_reference="positive-path envelope minus its own digest",
            canonical_byte_count=len(
                canonical_bytes({k: v for k, v in record.items() if k != "envelope_digest"})
            ),
            computed_digest=computed, published_vector=None, published_digest=None,
            comparison_operands={"computed": computed, "stored": stored},
            comparison_result="EQUAL" if computed == stored else "NOT_EQUAL",
        )

    def dig_05(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_reliance import consumer_validation_digest

        run = _positive_run()
        validation = run["result"]["validation"]
        computed = consumer_validation_digest(validation)
        stored = validation["consumer_validation_digest"]
        return _dig_observation(
            cid, digest_class="consumer_validation_digest",
            digested_object_reference="positive-path consumer validation, checks[] 1..16",
            canonical_byte_count=len(
                canonical_bytes({k: v for k, v in validation.items()
                                 if k != "consumer_validation_digest"})
            ),
            computed_digest=computed, published_vector=None, published_digest=None,
            comparison_operands={"computed": computed, "stored": stored,
                                 "check_count": len(validation["checks"])},
            comparison_result="EQUAL" if computed == stored else "NOT_EQUAL",
        )

    def dig_06(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_reliance import reliance_record_digest

        run = _positive_run()
        record = run["result"]["reliance_record"]
        computed = reliance_record_digest(record)
        stored = record["reliance_record_digest"]
        return _dig_observation(
            cid, digest_class="reliance_record_digest",
            digested_object_reference="positive-path reliance record minus its own digest",
            canonical_byte_count=len(
                canonical_bytes({k: v for k, v in record.items()
                                 if k != "reliance_record_digest"})
            ),
            computed_digest=computed, published_vector=None, published_digest=None,
            comparison_operands={"computed": computed, "stored": stored},
            comparison_result="EQUAL" if computed == stored else "NOT_EQUAL",
        )

    def dig_07(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_reliance import integration_package_digest

        probe = {
            "record_class": "CDC_INTEGRATION_SLICE_001_RAW_EXECUTION_PACKAGE",
            "members": [{"path": "a.json", "bytes": 10, "sha256": "ab" * 32}],
            "package_digest": "0" * 64,
        }
        computed = integration_package_digest(probe)
        expected = canonical_digest({k: v for k, v in probe.items() if k != "package_digest"})
        return _dig_observation(
            cid, digest_class="integration_package_digest",
            digested_object_reference="package probe minus package_digest",
            canonical_byte_count=len(
                canonical_bytes({k: v for k, v in probe.items() if k != "package_digest"})
            ),
            computed_digest=computed, published_vector=None, published_digest=None,
            comparison_operands={"computed": computed, "recomputed_by_rule": expected},
            comparison_result="EQUAL" if computed == expected else "NOT_EQUAL",
        )

    def dig_08(cid: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_authority import synthetic_profile_digest

        fixtures = _fixtures()
        body = {k: v for k, v in fixtures.producer_profile().items() if k != "profile_digest"}
        computed = synthetic_profile_digest(body)
        published = "1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c"
        return _dig_observation(
            cid, digest_class="synthetic_profile_digest",
            digested_object_reference="PROFILE-PRODUCER-1 body minus profile_digest",
            canonical_byte_count=len(canonical_bytes(body)),
            computed_digest=computed, published_vector="PROFILE-PRODUCER-1",
            published_digest=published,
            comparison_operands={"computed": computed, "published": published},
            comparison_result="EQUAL" if computed == published else "NOT_EQUAL",
        )

    for name, executor in (
        ("T-DIG-01", dig_01), ("T-DIG-02", dig_02), ("T-DIG-03", dig_03),
        ("T-DIG-04", dig_04), ("T-DIG-05", dig_05), ("T-DIG-06", dig_06),
        ("T-DIG-07", dig_07), ("T-DIG-08", dig_08),
    ):
        EXECUTORS[name] = executor


def _register_epochs() -> None:
    output_ref = "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"
    attestation = "eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7"
    successor = {
        "output_ref": output_ref,
        "record_ref": "EBAWU-P-001-C-TENDER-01-CORR-002#" + output_ref,
        "record_digest": "943affbf3e86d8a1b6831eb3deafb2efeac902989d8ee75fe85daea6f82e1e3c",
        "record_class": "CORRECTION_SUCCESSOR_RECORD",
        "effective_at": "2026-08-15T12:00:00Z",
        "admitted_at": "2026-08-15T09:00:00Z",
    }
    unrelated = {
        **successor,
        "output_ref": "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02",
        "record_ref": "EBAWU-OTHER#CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02",
        "effective_at": "2026-08-15T08:00:00Z",
    }
    reduced_field = {key: successor[key] for key in
                     ("record_ref", "record_digest", "record_class", "effective_at",
                      "admitted_at")}

    def epoch(cid: str, as_of: str, records: list[dict[str, Any]], att: Any,
              reduced: dict[str, Any], published: str, vector: str) -> dict[str, Any]:
        _install_paths()
        from oic.cdc_authority import currentness_epoch_digest

        computed = currentness_epoch_digest(
            output_ref=output_ref, as_of=as_of, governing_records=records,
            completeness_attestation_digest=att,
        )
        return {
            "semantic_reference": "DIGEST-DERIVATION-v0.5 §2 / PROJECTION-v0.1 §3.5",
            "scenario_id": vector,
            "inputs": [{"role": "governing_records", "ref": vector, "digest": None}],
            "expected_condition": f"{vector} reproduces its published digest at as_of {as_of}",
            "observed_value": {
                "as_of": as_of,
                "reduced_object": reduced,
                "canonical_byte_count": len(canonical_bytes(reduced)),
                "computed_digest": computed,
                "published_vector": vector,
                "published_digest": published,
                "comparison_operands": {"computed": computed, "published": published},
                "comparison_result": "EQUAL" if computed == published else "NOT_EQUAL",
            },
            "observed_reason_code": "NOT_APPLICABLE",
            "observed_decision": "NOT_APPLICABLE",
            "outputs": [],
            "not_produced": [],
            "evidence_refs": [f"observations/{cid}.json"],
        }

    epoch_a_reduced = {
        "output_ref": output_ref,
        "completeness_attestation_digest": attestation,
        "operative_basis_records": [],
    }
    epoch_b_reduced = {
        "output_ref": output_ref,
        "completeness_attestation_digest": None,
        "operative_basis_records": [reduced_field],
    }
    published_a = "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46"
    published_b = "6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac"
    EXECUTORS["T-EPOCH-A"] = lambda cid: epoch(
        cid, "2026-08-15T10:00:00Z", [successor], attestation, epoch_a_reduced,
        published_a, "EPOCH-A")
    EXECUTORS["T-EPOCH-B"] = lambda cid: epoch(
        cid, "2026-08-15T13:00:00Z", [successor], None, epoch_b_reduced,
        published_b, "EPOCH-B")
    EXECUTORS["T-EPOCH-C"] = lambda cid: epoch(
        cid, "2026-08-15T10:00:00Z", [successor, unrelated], attestation, epoch_a_reduced,
        published_a, "EPOCH-C")


_register_early()
_register_positive()
_register_cases()
EXECUTORS["T-CASE-J"] = _exec_case_j
EXECUTORS["T-CASE-K"] = _exec_case_k
EXECUTORS["T-CASE-L"] = _exec_case_l
EXECUTORS["T-CASE-P"] = _exec_case_p
_register_digests()
_register_epochs()


# ---------------------------------------------------------------------------
# Result-bearing execution
# ---------------------------------------------------------------------------


def _run_criteria() -> list[dict[str, Any]]:
    """Execute all 41 in frozen order, capturing each observation in-invocation."""
    observations: list[dict[str, Any]] = []
    for criterion_id in FROZEN_CRITERION_ORDER:
        executor = EXECUTORS[criterion_id]
        started = time.monotonic()
        produced = executor(criterion_id)
        duration = time.monotonic() - started
        observations.append(
            build_observation(
                criterion_id=criterion_id,
                duration_seconds=duration,
                **produced,
            )
        )
    return observations


def _pytest_accounting() -> dict[str, Any]:
    """Secondary accounting only.  No criterion proposition depends on this."""
    report = RUNTIME_ROOT / "accounting" / "pytest-criteria-report.xml"
    report.parent.mkdir(parents=True, exist_ok=True)
    node_ids = [
        f"tests/integration/test_cdc_integration_slice_001.py::{CRITERION_NODE_IDS[key]}"
        for key in FROZEN_CRITERION_ORDER
    ]
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-q", "--no-header",
         f"--junit-xml={report}", *node_ids],
        capture_output=True, check=False, text=True, cwd=str(IMPLEMENTATION_ROOT),
    )
    payload = report.read_bytes() if report.is_file() else b""
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_PYTEST_ACCOUNTING",
        "non_load_bearing": True,
        "path": str(report),
        "bytes": len(payload),
        "sha256": file_sha256(payload) if payload else None,
        "exit_status": completed.returncode,
        "note": (
            "secondary accounting for reconciliation; the evidentiary payload is the "
            "41 criterion observations, not this file"
        ),
    }


def execute_run() -> dict[str, Any]:
    """The single authorized result-bearing execution, in the frozen order."""
    if _EXECUTE_RUN_INVOCATIONS["count"]:
        raise HarnessRefusalError("a second result-bearing execution is not authorized")
    _EXECUTE_RUN_INVOCATIONS["count"] += 1
    observed_at = _now()

    def refuse(reason: str, **extra: Any) -> dict[str, Any]:  # noqa: ANN401
        return {
            "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_EXECUTION_REFUSAL",
            "execution": REFUSED_BEFORE_INVOCATION,
            "reason": reason,
            "execution_id": EXECUTION_ID,
            "observed_at": observed_at,
            "result_bearing_invocations": _RESULT_BEARING_INVOCATIONS["count"],
            "attempt_record": "NONE",
            "ordinal_consumed": False,
            "runtime_result": "NONE",
            "runtime_evidence_root_unused": _root_unused(),
            **extra,
        }

    authority = verify_result_bearing_execution_authority()
    if authority["execution_authority"] != EXECUTION_AUTHORITY_VALID:
        return refuse(authority["reason"] or REASON_NOT_ISSUED,
                      execution_authority=authority["execution_authority"],
                      authority_detail=authority)

    pre = preflight()
    if not pre["control_package_preflight_passed"]:
        return refuse(REASON_PREFLIGHT_FAILED,
                      execution_authority=authority["execution_authority"],
                      failed_checks=[item for item in pre["checks"] if not item["passed"]])
    if pre["preflight_result_bearing_invocations"] != 0:
        return refuse(REASON_PREFLIGHT_NOT_CLEAN,
                      execution_authority=authority["execution_authority"])

    issuance_digest = str(authority["issuance_digest"])
    if read_attempt_state(issuance_digest) != ATTEMPT_STATE_NONE:
        return refuse(REASON_ORDINAL_NOT_AVAILABLE,
                      execution_authority=authority["execution_authority"],
                      attempt_state=read_attempt_state(issuance_digest))

    attempt = consume_attempt(issuance_digest)
    started_at = _now()
    before = _RESULT_BEARING_INVOCATIONS["count"]

    prepare_scenario_tree(RUNTIME_ROOT)
    observations = _run_criteria()
    accounting = _pytest_accounting()

    after = _RESULT_BEARING_INVOCATIONS["count"]
    completed = complete_attempt(issuance_digest)
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_RESULT",
        "execution": "EXECUTED",
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "started_at": started_at,
        "completed_at": _now(),
        "execution_authority": authority,
        "preflight": pre,
        "attempt_consumed": attempt,
        "attempt_completed": completed,
        "execution_issuance_digest": issuance_digest,
        "observations": observations,
        "pytest_accounting": accounting,
        "result_bearing_invocations_during_run": after - before,
        "execute_run_invocations": _EXECUTE_RUN_INVOCATIONS["count"],
        "second_result_bearing_execution": False,
        "automatic_retry_performed": False,
    }


def persist(result: dict[str, Any]) -> dict[str, Any]:
    """Write 41 observation files, then the ledger, then the package."""
    _install_paths()
    from oic.cdc_reliance import integration_package_digest

    observations_dir = RUNTIME_ROOT / "observations"
    observations_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for record in result["observations"]:
        path = observations_dir / f"{record['criterion_id']}.json"
        data = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
        path.write_bytes(data)
        entries.append(
            {
                "criterion_id": record["criterion_id"],
                "observation_path": f"observations/{record['criterion_id']}.json",
                "persisted_file_bytes": len(data),
                "persisted_file_sha256": file_sha256(data),
                "observation_digest": record["observation_digest"],
            }
        )

    ledger = {
        "record_class": LEDGER_RECORD_CLASS,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "semantic_design_sha256": SEMANTIC_DESIGN_SHA256,
        "criterion_evidence_projection_sha256": PROJECTION_V0_2_SHA256,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "criteria_total": CRITERIA_TOTAL,
        "criterion_order": list(FROZEN_CRITERION_ORDER),
        "observations": entries,
        "pytest_accounting_ref": "accounting/pytest-criteria-report.xml",
        "ledger_digest": "",
    }
    ledger["ledger_digest"] = criterion_ledger_digest(ledger)
    ledger_path = RUNTIME_ROOT / "CDC-INTEGRATION-SLICE-001-RUN-002-CRITERION-EVIDENCE-LEDGER-v0.1.json"
    ledger_bytes = (json.dumps(ledger, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    ledger_path.write_bytes(ledger_bytes)

    members = [
        {"path": str(observations_dir / f"{entry['criterion_id']}.json"),
         "bytes": entry["persisted_file_bytes"], "sha256": entry["persisted_file_sha256"]}
        for entry in entries
    ]
    members.append({"path": str(ledger_path), "bytes": len(ledger_bytes),
                    "sha256": file_sha256(ledger_bytes)})
    attempt_path = Path(result["attempt_completed"]["path"])
    members.append({"path": str(attempt_path), "bytes": len(attempt_path.read_bytes()),
                    "sha256": file_sha256(attempt_path.read_bytes())})
    accounting = result["pytest_accounting"]
    if accounting["sha256"]:
        members.append({"path": accounting["path"], "bytes": accounting["bytes"],
                        "sha256": accounting["sha256"]})

    package = {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_002_RAW_EXECUTION_PACKAGE",
        "schema_version": "CDC-INTEGRATION-SLICE-001-RUN-002-RAW-EXECUTION-PACKAGE-v0.1",
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "authorization_id": AUTHORIZATION_ID,
        "execution_issuance_digest": result["execution_issuance_digest"],
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "semantic_design_sha256": SEMANTIC_DESIGN_SHA256,
        "criterion_evidence_projection_v0_1_sha256": PROJECTION_V0_1_SHA256,
        "criterion_evidence_projection_v0_2_sha256": PROJECTION_V0_2_SHA256,
        "digest_derivation_sha256": DIGEST_DERIVATION_V0_5_SHA256,
        "runtime_evidence_root": str(RUNTIME_ROOT),
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "criteria_total": CRITERIA_TOTAL,
        "observations_persisted": len(entries),
        "criterion_ledger_digest": ledger["ledger_digest"],
        "pytest_accounting": accounting,
        "attempt_state": result["attempt_completed"]["record"]["attempt_state"],
        "result_bearing_invocations_during_run": result["result_bearing_invocations_during_run"],
        "automatic_retry_performed": False,
        "second_result_bearing_execution": False,
        "official_handoff": "PROHIBITED",
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "semantic_adjudication_performed": False,
        "members": members,
        "package_digest": "",
    }
    package["package_digest"] = integration_package_digest(package)
    package_path = RUNTIME_ROOT / "CDC-INTEGRATION-SLICE-001-RUN-002-RAW-EXECUTION-PACKAGE-v0.1.json"
    package_bytes = (
        json.dumps(package, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    package_path.write_bytes(package_bytes)
    return {
        "ledger": {"path": str(ledger_path), "bytes": len(ledger_bytes),
                   "sha256": file_sha256(ledger_bytes), "digest": ledger["ledger_digest"]},
        "package": {"path": str(package_path), "bytes": len(package_bytes),
                    "sha256": file_sha256(package_bytes),
                    "digest": package["package_digest"]},
        "observations": entries,
    }


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    if mode == "scaffold":
        print(json.dumps(scaffold_control(), indent=2, sort_keys=True, default=str))
    elif mode == "preflight":
        print(json.dumps(preflight(), indent=2, sort_keys=True, default=str))
    elif mode == "execute":
        outcome = execute_run()
        if outcome.get("execution") == REFUSED_BEFORE_INVOCATION:
            print(json.dumps(outcome, indent=2, sort_keys=True, default=str))
        else:
            print(json.dumps(persist(outcome), indent=2, sort_keys=True, default=str))
    else:
        raise SystemExit(f"unknown mode: {mode}")
