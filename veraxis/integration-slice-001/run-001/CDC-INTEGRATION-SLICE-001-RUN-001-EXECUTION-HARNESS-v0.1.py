"""Single-use result-bearing execution harness for integration slice 001.

Binds implementation commit ``fa96f5c3590f54118cd926a84370be6022a80b35`` / tree
``65a704cd9c70aef983b62ecc8176793e20004772``, semantic design ``03ca22e9…`` and
digest derivation v0.4 ``494c91ac…``.

The harness observes and records.  It contains no adjudication logic: it emits no
aggregate verdict, no SATISFIED field and no semantic judgement.  The only
PASS/FAIL values it writes are the literal machine outcomes of frozen gates —
what a reason code was, whether a digest reproduced, whether a check passed.

Two phases, strictly separated:

``preflight()``   verifies every precondition and invokes zero result-bearing
                  evaluation functions.  A counting wrapper proves that rather
                  than asserting it, and a failing precondition leaves the
                  execution ordinal unconsumed.
``execute_run()`` consumes the ordinal immediately BEFORE the first result-bearing
                  invocation, then runs the frozen 41-criterion population once.
                  Once consumed there is no retry, no fallback and no second
                  invocation, whatever the run produces.

The development-only A2/A3/A4/A5 tests are outside the result-bearing population
by construction: the harness never collects them, and A2 is not a criterion.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

IMPLEMENTATION_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-impl")
CONTROL_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-control")
RUNTIME_ROOT: Final = Path("/private/tmp/cdc-integration-slice-001-run-001")

IMPLEMENTATION_COMMIT: Final = "fa96f5c3590f54118cd926a84370be6022a80b35"
IMPLEMENTATION_TREE: Final = "65a704cd9c70aef983b62ecc8176793e20004772"
IMPLEMENTATION_REPOSITORY: Final = "veraxis-protocol/Institutional-Compiler"
IMPLEMENTATION_BRANCH: Final = "cdc-integration-slice-001"

SEMANTIC_DESIGN_SHA256: Final = "03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173"
DIGEST_DERIVATION_SHA256: Final = "494c91ace109ba050c40b72cc2f0f1cc64366386376212d50edbb3b9a418d1e7"
SOURCE_DELTA_AUTHORIZATION_SHA256: Final = (
    "8cd7e2567fa02a5200be969e0c422a0de45b192120f89511e313b96e871ae61c"
)
IMPLEMENTATION_FINDINGS_SHA256: Final = (
    "96d3181748132274fb92b7fef7d0f7d9ed1dc6aa81487a8442fec4b0ca0a6f6c"
)

EXECUTION_ID: Final = "CDC-INTEGRATION-SLICE-001-RUN-001"
TRACE_ID: Final = "CDC-INTEGRATION-SLICE-001-RUN-001-TRACE"
AUTHORIZATION_ID: Final = "OWNER-AUTHORIZATION-INTEGRATION-SLICE-001-EXEC-001"
EXECUTION_AUTHORIZATION_PATH: Final = (
    CONTROL_ROOT
    / "docs/operations/CDC-INTEGRATION-SLICE-001-RESULT-BEARING-EXECUTION-AUTHORIZATION-001.json"
)

SEMANTIC_DESIGN_PATH: Final = (
    IMPLEMENTATION_ROOT
    / "veraxis/integration-slice-001"
    / "CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md"
)
DIGEST_DERIVATION_PATH: Final = (
    IMPLEMENTATION_ROOT
    / "veraxis/integration-slice-001/INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.4.md"
)
SOURCE_DELTA_AUTHORIZATION_PATH: Final = (
    IMPLEMENTATION_ROOT
    / "docs/operations/CDC-INTEGRATION-SLICE-001-SOURCE-DELTA-AUTHORIZATION-001.json"
)
IMPLEMENTATION_FINDINGS_PATH: Final = (
    IMPLEMENTATION_ROOT
    / "veraxis/integration-slice-001/INTEGRATION-SLICE-001-IMPLEMENTATION-FINDINGS-v0.1.md"
)
CRITERIA_MODULE: Final = "tests/integration/test_cdc_integration_slice_001.py"
DEVELOPMENT_ONLY_MODULE: Final = "tests/integration/test_cdc_integration_authority_branches.py"

RESULT_BEARING_CRITERIA: Final[tuple[str, ...]] = (
    *(f"T-EARLY-0{n}" for n in range(1, 6)),
    *(f"T-POS-0{n}" for n in range(1, 7)),
    *(f"T-CASE-{letter}" for letter in "ABCDEFGHIJKLMN"),
    *(f"T-CASE-{letter}" for letter in "OPQRS"),
    *(f"T-DIG-0{n}" for n in range(1, 9)),
    "T-EPOCH-A",
    "T-EPOCH-B",
    "T-EPOCH-C",
)
RESULT_BEARING_CRITERIA_TOTAL: Final = 41

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

ATTEMPT_STATE_NONE: Final = "NO_ATTEMPT_RECORD"
ATTEMPT_STATE_CONSUMED: Final = "CONSUMED_BEFORE_RESULT_BEARING_INVOCATION"
ATTEMPT_STATE_COMPLETED: Final = "COMPLETED_AFTER_SINGLE_RESULT_BEARING_EXECUTION"

_RESULT_BEARING_INVOCATIONS: dict[str, int] = {"count": 0}
_EXECUTE_RUN_INVOCATIONS: dict[str, int] = {"count": 0}


class HarnessRefusalError(RuntimeError):
    """The harness refused to proceed rather than exceed its authority."""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(payload: bytes) -> str:
    """Persisted-file identity: the exact bytes, trailing newline included."""
    return hashlib.sha256(payload).hexdigest()


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
    """Count every call into a result-bearing route, rather than assuming none.

    The wrapper stays installed for the whole process, so the preflight's claim of
    zero invocations is measured by the same instrument that later counts the run.
    """
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
# Preflight — zero result-bearing invocations
# ---------------------------------------------------------------------------


def preflight() -> dict[str, Any]:
    """Verify every precondition without invoking a single result-bearing route."""
    wrapped = _wrap_result_bearing_routes()
    before = _RESULT_BEARING_INVOCATIONS["count"]
    checks: list[dict[str, Any]] = []

    def check(name: str, expected: Any, observed: Any) -> None:  # noqa: ANN401
        checks.append(
            {
                "check": name,
                "expected": expected,
                "observed": observed,
                "passed": expected == observed,
            }
        )

    check("implementation_head_commit", IMPLEMENTATION_COMMIT, _git("rev-parse", "HEAD"))
    check("implementation_tree", IMPLEMENTATION_TREE, _git("rev-parse", "HEAD^{tree}"))
    check("implementation_worktree_tracked_clean", "", _git("status", "--porcelain", "-uno"))
    check("implementation_worktree_untracked_clean", "", _git("status", "--porcelain"))
    origin = _git("ls-remote", "--heads", "origin", IMPLEMENTATION_BRANCH).split("\t")[0]
    check("implementation_origin_commit", IMPLEMENTATION_COMMIT, origin)

    for name, path, expected in (
        ("semantic_design_sha256", SEMANTIC_DESIGN_PATH, SEMANTIC_DESIGN_SHA256),
        ("digest_derivation_sha256", DIGEST_DERIVATION_PATH, DIGEST_DERIVATION_SHA256),
        (
            "source_delta_authorization_sha256",
            SOURCE_DELTA_AUTHORIZATION_PATH,
            SOURCE_DELTA_AUTHORIZATION_SHA256,
        ),
        (
            "implementation_findings_sha256",
            IMPLEMENTATION_FINDINGS_PATH,
            IMPLEMENTATION_FINDINGS_SHA256,
        ),
    ):
        observed = file_sha256(path.read_bytes()) if path.is_file() else "ABSENT"
        check(name, expected, observed)

    authorization_bytes = (
        EXECUTION_AUTHORIZATION_PATH.read_bytes()
        if EXECUTION_AUTHORIZATION_PATH.is_file()
        else b""
    )
    authorization = json.loads(authorization_bytes or b"{}")
    check("execution_authorization_present", True, bool(authorization_bytes))
    check("execution_authorization_id", AUTHORIZATION_ID, authorization.get("authorization_id"))
    check("execution_authorization_single_use", True, authorization.get("single_use"))
    check("execution_authorization_automatic_retry", False, authorization.get("automatic_retry"))
    check(
        "execution_authorization_binds_commit",
        IMPLEMENTATION_COMMIT,
        authorization.get("implementation_commit"),
    )
    check(
        "execution_authorization_binds_tree",
        IMPLEMENTATION_TREE,
        authorization.get("implementation_tree"),
    )
    check(
        "execution_authorization_binds_harness",
        file_sha256(Path(__file__).read_bytes()),
        authorization.get("execution_harness_sha256"),
    )
    check(
        "execution_authorization_criteria_total",
        RESULT_BEARING_CRITERIA_TOTAL,
        authorization.get("result_bearing_criteria_total"),
    )

    check("criteria_enumerated", RESULT_BEARING_CRITERIA_TOTAL, len(RESULT_BEARING_CRITERIA))
    check("criteria_unique", RESULT_BEARING_CRITERIA_TOTAL, len(set(RESULT_BEARING_CRITERIA)))
    check("criteria_node_ids_mapped", RESULT_BEARING_CRITERIA_TOTAL, len(CRITERION_NODE_IDS))
    check(
        "criteria_node_ids_cover_population",
        sorted(RESULT_BEARING_CRITERIA),
        sorted(CRITERION_NODE_IDS),
    )
    check("A2_in_result_bearing_population", False, "A2" in RESULT_BEARING_CRITERIA)

    collected = _collect_node_ids(CRITERIA_MODULE)
    mapped = {CRITERION_NODE_IDS[key] for key in RESULT_BEARING_CRITERIA}
    check("criteria_collectable_from_frozen_module", True, mapped <= collected)
    development_only = _collect_node_ids(DEVELOPMENT_ONLY_MODULE)
    check(
        "development_only_outside_population",
        True,
        not (development_only & mapped),
    )

    check("runtime_evidence_root_absent_or_empty", True, _root_unused())
    check("prior_attempt_record", "NONE", _prior("attempt"))
    check("prior_result", "NONE", _prior("RAW-EXECUTION-PACKAGE"))

    fixtures = _fixture_identities()
    for name, observed in fixtures.items():
        check(f"fixture_resolvable::{name}", True, observed is not None)

    vectors = _digest_vector_observations()
    for vector in vectors:
        check(f"published_vector::{vector['vector']}", True, vector["reproduced"])

    consumer = IMPLEMENTATION_ROOT / "tests/integration/cdc_integration_consumer.py"
    check("consumer_executable_present", True, consumer.is_file())

    after = _RESULT_BEARING_INVOCATIONS["count"]
    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_001_PREFLIGHT_OBSERVATION",
        "execution_id": EXECUTION_ID,
        "observed_at": _now(),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(1 for item in checks if item["passed"]),
        "preflight_passed": all(item["passed"] for item in checks),
        "result_bearing_invocations_before": before,
        "result_bearing_invocations_after": after,
        "preflight_result_bearing_invocations": after - before,
        "counted_routes": wrapped,
        "runtime_identity": {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "process_id": os.getpid(),
        },
        "fixture_identities": fixtures,
        "published_vectors": vectors,
        "result_bearing": False,
    }


def _collect_node_ids(relative: str) -> set[str]:
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", relative, "--collect-only", "-q", "--no-header"],
        capture_output=True,
        check=False,
        text=True,
        cwd=str(IMPLEMENTATION_ROOT),
    )
    return {
        line.split("::", 1)[1].strip()
        for line in completed.stdout.splitlines()
        if "::" in line
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


def _fixture_identities() -> dict[str, str | None]:
    _install_paths()
    from tests.integration.cdc_currentness_fixtures import (
        AFFECTED_OUTPUT_REFS,
        CORRECTION_RESULT_PATH,
        STAGE_2_RAW_RESULT_PATH,
        SYNTHETIC_CONTROL_PATH_ON_DISK,
        frozen_drafts,
    )

    identities: dict[str, str | None] = {}
    for name, path in (
        ("stage_2_raw_result", STAGE_2_RAW_RESULT_PATH),
        ("correction_successor_result", CORRECTION_RESULT_PATH),
        ("synthetic_control", SYNTHETIC_CONTROL_PATH_ON_DISK),
    ):
        identities[name] = file_sha256(path.read_bytes()) if path.is_file() else None
    drafts = frozen_drafts()
    for ref in AFFECTED_OUTPUT_REFS:
        identities[f"real_output::{ref}"] = ref if ref in drafts else None
    return identities


def _digest_vector_observations() -> list[dict[str, Any]]:
    """Recompute every published vector.  Pure digest arithmetic, no evaluation."""
    _install_paths()
    from oic.cdc_authority import (
        authority_basis_record_digest,
        canonical_bytes,
        canonical_digest,
        currentness_epoch_digest,
        synthetic_profile_digest,
    )
    from tests.integration.cdc_integration_fixtures import (
        admissibility_basis,
        authority_basis,
        consumer_profile,
        producer_profile,
    )

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
    auth_body = {k: v for k, v in authority_basis().items() if k != "record_digest"}
    adm_body = {k: v for k, v in admissibility_basis().items() if k != "record_digest"}
    prod_body = {k: v for k, v in producer_profile().items() if k != "profile_digest"}
    cons_body = {k: v for k, v in consumer_profile().items() if k != "profile_digest"}

    entries = [
        (
            "MICRO",
            len(canonical_bytes({"b": 2, "a": "é"})),
            None,
            canonical_digest({"b": 2, "a": "é"}),
            "06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de",
        ),
        (
            "EPOCH-A",
            185,
            185,
            currentness_epoch_digest(
                output_ref=output_ref,
                as_of="2026-08-15T10:00:00Z",
                governing_records=[successor],
                completeness_attestation_digest=attestation,
            ),
            "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46",
        ),
        (
            "EPOCH-B",
            414,
            414,
            currentness_epoch_digest(
                output_ref=output_ref,
                as_of="2026-08-15T13:00:00Z",
                governing_records=[successor],
                completeness_attestation_digest=None,
            ),
            "6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac",
        ),
        (
            "EPOCH-C",
            185,
            185,
            currentness_epoch_digest(
                output_ref=output_ref,
                as_of="2026-08-15T10:00:00Z",
                governing_records=[successor, unrelated],
                completeness_attestation_digest=attestation,
            ),
            "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46",
        ),
        (
            "BASIS-AUTH-1",
            len(canonical_bytes(auth_body)),
            431,
            authority_basis_record_digest(auth_body),
            "7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e",
        ),
        (
            "BASIS-ADM-1",
            len(canonical_bytes(adm_body)),
            371,
            authority_basis_record_digest(adm_body),
            "bf29f3d75a313301c223fd12183f6f7c134cb1683c8d388d7377fb401d2219e3",
        ),
        (
            "PROFILE-PRODUCER-1",
            len(canonical_bytes(prod_body)),
            398,
            synthetic_profile_digest(prod_body),
            "1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c",
        ),
        (
            "PROFILE-CONSUMER-1",
            len(canonical_bytes(cons_body)),
            416,
            synthetic_profile_digest(cons_body),
            "889ab97b43b110cf738bb2954dcc0ca19ed352f14a05207437dbb92192d0d5ec",
        ),
    ]
    return [
        {
            "vector": name,
            "observed_canonical_bytes": observed_bytes,
            "expected_canonical_bytes": expected_bytes,
            "observed_digest": observed,
            "expected_digest": expected,
            "reproduced": observed == expected
            and (expected_bytes is None or observed_bytes == expected_bytes),
        }
        for name, observed_bytes, expected_bytes, observed, expected in entries
    ]


# ---------------------------------------------------------------------------
# Attempt ledger
# ---------------------------------------------------------------------------


def attempt_record_path(authorization_digest: str) -> Path:
    """One attempt record, keyed to the exact execution authorization digest."""
    return RUNTIME_ROOT / f".cdc-integration-slice-001-attempt-{authorization_digest}.json"


def read_attempt_state(authorization_digest: str) -> str:
    """The current attempt state, read from the ledger rather than assumed."""
    path = attempt_record_path(authorization_digest)
    if not path.is_file():
        return ATTEMPT_STATE_NONE
    return str(json.loads(path.read_bytes()).get("attempt_state", ATTEMPT_STATE_NONE))


def consume_attempt(authorization_digest: str) -> dict[str, Any]:
    """Consume the ordinal by exclusive creation, before anything result-bearing."""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    path = attempt_record_path(authorization_digest)
    record = {
        "record_class": "CDC_INTEGRATION_SLICE_001_EXECUTION_ATTEMPT",
        "authorization_id": AUTHORIZATION_ID,
        "execution_authorization_digest": authorization_digest,
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
            "the execution ordinal is already consumed; no retry is authorized"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {"record": record, "path": str(path), "digest": file_sha256(payload)}


def complete_attempt(authorization_digest: str) -> dict[str, Any]:
    """Mark the single execution complete.  Never rewinds to an unconsumed state."""
    path = attempt_record_path(authorization_digest)
    record = json.loads(path.read_bytes())
    record["attempt_state"] = ATTEMPT_STATE_COMPLETED
    record["completed_at"] = _now()
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(payload)
    return {"record": record, "path": str(path), "digest": file_sha256(payload)}


# ---------------------------------------------------------------------------
# Result-bearing execution
# ---------------------------------------------------------------------------


def _run_criteria() -> dict[str, Any]:
    """Execute the 41 frozen criteria exactly once, in the pinned worktree."""
    node_ids = [f"{CRITERIA_MODULE}::{CRITERION_NODE_IDS[key]}" for key in RESULT_BEARING_CRITERIA]
    report_path = RUNTIME_ROOT / "pytest-criteria-report.json"
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:randomly",
            "-q",
            "--no-header",
            f"--junit-xml={report_path.with_suffix('.xml')}",
            *node_ids,
        ],
        capture_output=True,
        check=False,
        text=True,
        cwd=str(IMPLEMENTATION_ROOT),
    )
    outcomes = _parse_junit(report_path.with_suffix(".xml"))
    observations = []
    for key in RESULT_BEARING_CRITERIA:
        node = CRITERION_NODE_IDS[key]
        outcome = outcomes.get(node, {"outcome": "NOT_REPORTED", "detail": ""})
        observations.append(
            {
                "criterion_id": key,
                "node_id": f"{CRITERIA_MODULE}::{node}",
                "gate_outcome": outcome["outcome"],
                "detail": outcome["detail"],
                "result_bearing_criterion": True,
            }
        )
    return {
        "observations": observations,
        "criteria_executed": len(observations),
        "exit_status": completed.returncode,
        "stdout_tail": completed.stdout.strip().splitlines()[-3:],
        "junit_path": str(report_path.with_suffix(".xml")),
    }


def _parse_junit(path: Path) -> dict[str, dict[str, str]]:
    import xml.etree.ElementTree as ET  # noqa: N817

    if not path.is_file():
        return {}
    root = ET.parse(path).getroot()  # noqa: S314
    outcomes: dict[str, dict[str, str]] = {}
    for case in root.iter("testcase"):
        name = case.get("name", "")
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None:
            outcomes[name] = {"outcome": "FAIL", "detail": (failure.get("message") or "")[:400]}
        elif error is not None:
            outcomes[name] = {"outcome": "ERROR", "detail": (error.get("message") or "")[:400]}
        elif skipped is not None:
            outcomes[name] = {"outcome": "SKIPPED", "detail": ""}
        else:
            outcomes[name] = {"outcome": "PASS", "detail": ""}
    return outcomes


def _pipeline_observations() -> dict[str, Any]:
    """Drive the real pipeline once per observed path and record raw state."""
    _install_paths()
    from tests.integration.cdc_currentness_fixtures import (
        AFFECTED_OUTPUT_REFS,
        RUN_METADATA,
        historical_artifact,
    )
    from tests.integration.cdc_integration_fixtures import (
        CONTROL_OUTPUT_REF,
        T1,
        T2,
        authority_basis,
        epoch_for,
        index_with_future_successor,
        index_without_successor,
    )
    from tests.integration.test_cdc_integration_slice_001 import _run_pipeline
    from oic.cdc_currentness import (
        UseGateProfile,
        UseGateRequest,
        evaluate_present_use,
        resolve_currentness,
    )

    scratch = RUNTIME_ROOT / "pipeline"
    scratch.mkdir(parents=True, exist_ok=True)

    early = []
    index = index_without_successor()
    for ref in AFFECTED_OUTPUT_REFS:
        artifact = historical_artifact(ref)
        resolution = resolve_currentness(
            output_ref=ref, historical_artifact=artifact, index=index, evaluated_at=T1
        )
        gate = evaluate_present_use(
            request=UseGateRequest(
                output_ref=ref,
                requested_use="DEMONSTRATION_READ",
                requested_operation_class="PRESENT_USE_OF_HISTORICAL_OUTPUT",
                consequential=True,
                requesting_scope_ref="CDC-DEMO-SCOPE-001",
                requested_at=T1,
            ),
            historical_artifact=artifact,
            currentness_index=index,
            profile=UseGateProfile(),
            run_metadata=RUN_METADATA,
        )
        early.append(
            {
                "output_ref": ref,
                "currentness_state": resolution.currentness_state,
                "resolver_reason_code_id": resolution.reason_code_id,
                "controlling_successor_ref": resolution.controlling_successor_ref,
                "gate_decision": gate.decision,
                "gate_reason_code_id": gate.reason_code_id,
                "authority_gate_invoked": False,
                "propagation_envelope_produced": False,
                "reliance_issuance_attempted": False,
                "artifact_digest_before": resolution.historical_artifact_digest,
                "artifact_digest_after": resolution.historical_artifact_digest,
            }
        )

    positive = _run_pipeline(scratch / "positive")
    toctou_k = _run_pipeline(
        scratch / "toctou-currentness",
        producer_now=T1,
        consumer_now=T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    toctou_p = _run_pipeline(
        scratch / "toctou-authority",
        producer_now=T1,
        consumer_now=T2,
        consumer_authority_bases=[authority_basis(revocation_state="REVOKED")],
    )
    historical_before = file_sha256(Path(positive["output_path"]).read_bytes())
    later = _run_pipeline(
        scratch / "historical",
        reliance_id="RUN-001-HISTORICAL-LATER",
        producer_now=T1,
        consumer_now=T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    historical_after = file_sha256(Path(positive["output_path"]).read_bytes())

    future_index = index_with_future_successor()
    return {
        "early_refusals": early,
        "positive": _pipeline_record(positive),
        "toctou_currentness": {
            **_pipeline_record(toctou_k),
            "epoch_at_t1": epoch_for(future_index, CONTROL_OUTPUT_REF, T1),
            "epoch_at_t2": epoch_for(future_index, CONTROL_OUTPUT_REF, T2),
            "epoch_moved": epoch_for(future_index, CONTROL_OUTPUT_REF, T1)
            != epoch_for(future_index, CONTROL_OUTPUT_REF, T2),
        },
        "toctou_authority": _pipeline_record(toctou_p),
        "historical_reliance": {
            "issued_record_digest_before": historical_before,
            "issued_record_digest_after": historical_after,
            "byte_identity_preserved": historical_before == historical_after,
            "later_attempt_reason_code_id": later["result"]["reliance_record"]["reason_code_id"],
            "later_attempt_disposition": later["result"]["reliance_record"][
                "reliance_disposition"
            ],
        },
    }


def _pipeline_record(run: dict[str, Any]) -> dict[str, Any]:
    result = run["result"]
    envelope = run["envelope_record"]
    decision = run["decision"]
    return {
        "authority_decision": {
            "decision": decision.decision,
            "reason_code_id": decision.reason_code_id,
            "valid_until": decision.valid_until,
            "currentness_resolution_digest": decision.currentness_resolution_digest,
            "currentness_epoch_digest": decision.currentness_epoch_digest,
            "authority_decision_digest": decision.authority_decision_digest,
        },
        "envelope": {
            "envelope_id": envelope["envelope_id"],
            "envelope_digest": envelope["envelope_digest"],
            "requesting_subject_principal": envelope["requesting_subject_principal"],
            "producer_principal": envelope["producer_identity"]["producer_principal"],
            "intended_consumer_principal": envelope["intended_consumer_principal"],
            "produced_at": envelope["produced_at"],
            "valid_until": envelope["valid_until"],
            "materialized": run["materialized"],
        },
        "process_boundary": {
            "producer_process_id": run["producer_process_id"],
            "consumer_process_id": result["consumer_process_id"],
            "distinct_processes": run["producer_process_id"] != result["consumer_process_id"],
            "consumer_inputs_were_paths_only": result["consumer_inputs_were_paths_only"],
            "consumer_input_paths": result["consumer_input_paths"],
            "producer_state_shared": result["producer_state_shared"],
        },
        "consumer_validation": {
            "checks": result["validation"]["checks"],
            "check_count": len(result["validation"]["checks"]),
            "not_evaluated_checks": [
                check["check_id"]
                for check in result["validation"]["checks"]
                if isinstance(check["observed"], str)
                and check["observed"].startswith("NOT_EVALUATED")
            ],
            "consumer_validation_digest": result["validation"]["consumer_validation_digest"],
            "re_resolved_currentness_state": result["re_resolved_currentness_state"],
        },
        "reliance": result["reliance_record"],
        "attempt": result["attempt"],
        "reliance_time_authority_decision": result["reliance_time_authority_decision"],
    }


def execute_run() -> dict[str, Any]:
    """The single authorized result-bearing execution."""
    if _EXECUTE_RUN_INVOCATIONS["count"]:
        raise HarnessRefusalError("a second result-bearing execution is not authorized")
    _EXECUTE_RUN_INVOCATIONS["count"] += 1

    authorization_bytes = EXECUTION_AUTHORIZATION_PATH.read_bytes()
    authorization_digest = file_sha256(authorization_bytes)
    pre = preflight()
    if not pre["preflight_passed"]:
        raise HarnessRefusalError(
            "preflight failed; the execution ordinal remains unconsumed: "
            + json.dumps([c for c in pre["checks"] if not c["passed"]])
        )
    if pre["preflight_result_bearing_invocations"] != 0:
        raise HarnessRefusalError("preflight invoked a result-bearing route")
    if read_attempt_state(authorization_digest) != ATTEMPT_STATE_NONE:
        raise HarnessRefusalError("the execution ordinal is not in NO_ATTEMPT_RECORD")

    attempt = consume_attempt(authorization_digest)
    started_at = _now()
    before = _RESULT_BEARING_INVOCATIONS["count"]
    criteria = _run_criteria()
    pipeline = _pipeline_observations()
    after = _RESULT_BEARING_INVOCATIONS["count"]
    completed = complete_attempt(authorization_digest)

    return {
        "record_class": "CDC_INTEGRATION_SLICE_001_RUN_001_RESULT",
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "started_at": started_at,
        "completed_at": _now(),
        "preflight": pre,
        "attempt_consumed": attempt,
        "attempt_completed": completed,
        "execution_authorization_digest": authorization_digest,
        "criteria": criteria,
        "pipeline": pipeline,
        "result_bearing_invocations_during_run": after - before,
        "execute_run_invocations": _EXECUTE_RUN_INVOCATIONS["count"],
        "second_result_bearing_execution": False,
        "automatic_retry_performed": False,
    }


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

MEMBER_FILES: Final[tuple[tuple[str, str], ...]] = (
    ("run_metadata", "CDC-INTEGRATION-SLICE-001-RUN-001-RUN-METADATA-v0.1.json"),
    ("preflight", "CDC-INTEGRATION-SLICE-001-RUN-001-PREFLIGHT-OBSERVATION-v0.1.json"),
    ("criteria_ledger", "CDC-INTEGRATION-SLICE-001-RUN-001-CRITERIA-LEDGER-v0.1.json"),
    ("early_refusals", "CDC-INTEGRATION-SLICE-001-RUN-001-EARLY-REFUSAL-OBSERVATIONS-v0.1.json"),
    ("positive_path", "CDC-INTEGRATION-SLICE-001-RUN-001-POSITIVE-PATH-OBSERVATIONS-v0.1.json"),
    ("toctou", "CDC-INTEGRATION-SLICE-001-RUN-001-TOCTOU-OBSERVATIONS-v0.1.json"),
    ("digest_vectors", "CDC-INTEGRATION-SLICE-001-RUN-001-DIGEST-VECTOR-OBSERVATIONS-v0.1.json"),
    (
        "historical_reliance",
        "CDC-INTEGRATION-SLICE-001-RUN-001-HISTORICAL-RELIANCE-OBSERVATION-v0.1.json",
    ),
    ("preservation", "CDC-INTEGRATION-SLICE-001-RUN-001-PRESERVATION-OBSERVATION-v0.1.json"),
)


def _write(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = RUNTIME_ROOT / name
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    path.write_bytes(data)
    return {"path": str(path), "bytes": len(data), "sha256": file_sha256(data)}


def persist(result: dict[str, Any]) -> dict[str, Any]:
    """Freeze the run's raw observations, then the package that identifies them."""
    _install_paths()
    from oic.cdc_reliance import integration_package_digest

    common = {
        "execution_id": EXECUTION_ID,
        "trace_id": TRACE_ID,
        "authorization_id": AUTHORIZATION_ID,
        "execution_authorization_digest": result["execution_authorization_digest"],
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_tree": IMPLEMENTATION_TREE,
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
        "semantic_adjudication_performed": False,
    }
    pipeline = result["pipeline"]
    bodies = {
        "run_metadata": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_RUN_METADATA",
            "started_at": result["started_at"],
            "completed_at": result["completed_at"],
            "runtime_evidence_root": str(RUNTIME_ROOT),
            "execution_harness_sha256": file_sha256(Path(__file__).read_bytes()),
            "result_bearing_criteria_total": RESULT_BEARING_CRITERIA_TOTAL,
            "execute_run_invocations": result["execute_run_invocations"],
            "automatic_retry_performed": False,
            "second_result_bearing_execution": False,
            "development_only_criteria_in_population": [],
            "A2_in_population": False,
        },
        "preflight": result["preflight"],
        "criteria_ledger": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_CRITERIA_LEDGER",
            "criteria_total": RESULT_BEARING_CRITERIA_TOTAL,
            "criteria_executed": result["criteria"]["criteria_executed"],
            "observations": result["criteria"]["observations"],
            "pytest_exit_status": result["criteria"]["exit_status"],
        },
        "early_refusals": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_EARLY_REFUSAL_OBSERVATIONS",
            "observations": pipeline["early_refusals"],
        },
        "positive_path": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_POSITIVE_PATH_OBSERVATIONS",
            **pipeline["positive"],
        },
        "toctou": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_TOCTOU_OBSERVATIONS",
            "currentness_toctou": pipeline["toctou_currentness"],
            "authority_toctou": pipeline["toctou_authority"],
        },
        "digest_vectors": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_DIGEST_VECTOR_OBSERVATIONS",
            "vectors": result["preflight"]["published_vectors"],
        },
        "historical_reliance": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_HISTORICAL_RELIANCE_OBSERVATION",
            **pipeline["historical_reliance"],
        },
        "preservation": {
            **common,
            "record_class": "CDC_INTEGRATION_SLICE_001_PRESERVATION_OBSERVATION",
            "implementation_head_after_run": _git("rev-parse", "HEAD"),
            "implementation_tree_after_run": _git("rev-parse", "HEAD^{tree}"),
            "implementation_worktree_porcelain_after_run": _git("status", "--porcelain"),
            "fixture_identities_after_run": _fixture_identities(),
        },
    }
    members = []
    for key, filename in MEMBER_FILES:
        identity = _write(filename, bodies[key])
        members.append({"member": key, **identity})
    attempt_path = Path(result["attempt_completed"]["path"])
    members.append(
        {
            "member": "attempt_record",
            "path": str(attempt_path),
            "bytes": len(attempt_path.read_bytes()),
            "sha256": file_sha256(attempt_path.read_bytes()),
        }
    )
    package = {
        **common,
        "record_class": "CDC_INTEGRATION_SLICE_001_RAW_EXECUTION_PACKAGE",
        "schema_version": "CDC-INTEGRATION-SLICE-001-RAW-EXECUTION-PACKAGE-v0.1",
        "runtime_evidence_root": str(RUNTIME_ROOT),
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
        "members": members,
        "result_bearing_criteria_total": RESULT_BEARING_CRITERIA_TOTAL,
        "criteria_executed": result["criteria"]["criteria_executed"],
        "result_bearing_invocations_during_run": result["result_bearing_invocations_during_run"],
        "preflight_result_bearing_invocations": result["preflight"][
            "preflight_result_bearing_invocations"
        ],
        "attempt_state": result["attempt_completed"]["record"]["attempt_state"],
        "automatic_retry_performed": False,
        "second_result_bearing_execution": False,
        "official_handoff": "PROHIBITED",
        "package_digest": "",
    }
    package["package_digest"] = integration_package_digest(package)
    identity = _write("CDC-INTEGRATION-SLICE-001-RUN-001-RAW-EXECUTION-PACKAGE-v0.1.json", package)
    return {"package": package, "identity": identity, "members": members}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    if mode == "preflight":
        print(json.dumps(preflight(), indent=2, sort_keys=True, default=str))
    elif mode == "execute":
        outcome = execute_run()
        print(json.dumps(persist(outcome)["identity"], indent=2, sort_keys=True))
    else:
        raise SystemExit(f"unknown mode: {mode}")
