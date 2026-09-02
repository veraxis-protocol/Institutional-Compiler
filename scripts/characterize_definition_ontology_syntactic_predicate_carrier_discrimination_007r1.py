#!/usr/bin/env python3
"""Ontology 007R1 — authorization-binding-only successor to frozen O007.

All semantic request construction, transport behavior, parsing,
adjudicability, analysis, and decision logic are delegated to the
hash-frozen Ontology 007 implementation.

007R1 changes only qualification-artifact resolution/validation:
live execution requires an explicitly supplied, tracked, target-bound,
formally qualified provider artifact. No qualification serial number
is hard-coded.

Offline is the default. No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

WORK_ORDER: Final[str] = (
    "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-"
    "DISCRIMINATION-007R1"
)

PREREG_COMMIT: Final[str] = (
    "9505b78eb58d38795ca1075b3c0b48414470977e"
)

BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-discrimination-007r1"
)

REPAIR_PATH = BENCH / "AUTHORIZATION-REPAIR-BINDING-v0.1.json"
PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE_BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-discrimination-007"
)

SOURCE_MANIFEST = SOURCE_BENCH / "REQUEST-MATERIALIZATION-v0.1.json"

SOURCE_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007.py"
)

SOURCE_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007.py"
)

CONTRACT_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_syntactic_"
      "predicate_carrier_discrimination_007r1.py"
)

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/"
      "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
      "PREDICATE-CARRIER-DISCRIMINATION-007R1.json"
)

REPAIR_SHA256: Final[str] = (
    "a6acc0f22a7872d007f39cde8e8da662b12e6bde824869ee6fd9812858bb8b2d"
)
PLAN_SHA256: Final[str] = (
    "7558595f9f5caca541b03dd65f9bfeb2dddd8f05138ec9b47c06764904ba785d"
)
PREREG_SHA256: Final[str] = (
    "1f550475326da56fb89df660de28967c149d7be7e67146a55e2aa8019a7f354b"
)
FREEZE_V1_SHA256: Final[str] = (
    "c696e50eecd9d7416b5ab311dcfc1e41d01f75ec3b7aaa2826484f0cefd09027"
)

SOURCE_MANIFEST_SHA256: Final[str] = (
    "02567faee5aa55e830207b271023bf555a6f02417433731319ab0a869020f96a"
)
SOURCE_SCRIPT_SHA256: Final[str] = (
    "be752c975a6da03e9a0237aa7df09f38caf81a2e416b23584e3d86d998fa0834"
)
SOURCE_TEST_SHA256: Final[str] = (
    "c1ef0b1568fc16c70e6302d853a7a4a03c74dcf3ebfed18807b872c6f4887365"
)

PLANNED_REQUESTS: Final[int] = 18
PLANNED_PAIRS: Final[int] = 9

_SOURCE_MODULE_NAME: Final[str] = "_oic_frozen_ontology_007_for_007r1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path}")
    return value


def verify_frozen_sources() -> None:
    expected = {
        REPAIR_PATH: REPAIR_SHA256,
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        SOURCE_MANIFEST: SOURCE_MANIFEST_SHA256,
        SOURCE_SCRIPT: SOURCE_SCRIPT_SHA256,
        SOURCE_TEST: SOURCE_TEST_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)
        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: "
                f"{path}: {actual} != {expected_sha}"
            )


def source007() -> ModuleType:
    verify_frozen_sources()

    if _SOURCE_MODULE_NAME in sys.modules:
        return sys.modules[_SOURCE_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _SOURCE_MODULE_NAME,
        SOURCE_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("FAIL cannot load frozen Ontology 007")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
        "PREDICATE-CARRIER-DISCRIMINATION-007"
    ):
        raise SystemExit("FAIL source Ontology 007 identity drift")

    return module


def prereg_context() -> tuple[ModuleType, Any]:
    verify_frozen_sources()

    repair = load_json(REPAIR_PATH)
    plan = load_json(PLAN_PATH)
    freeze = load_json(FREEZE_V1_PATH)

    assert repair["work_order"] == WORK_ORDER
    assert repair["repair_class"] == "AUTHORIZATION_BINDING_ONLY"

    semantic = repair["semantic_preservation_contract"]

    assert semantic["request_count"] == PLANNED_REQUESTS
    assert semantic["pair_count"] == PLANNED_PAIRS
    assert semantic["semantic_request_bytes"] == (
        "MUST_BE_BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )
    assert semantic["decision_rules"] == "UNCHANGED"
    assert semantic["production_interpretation_ruleset_changed"] is False
    assert semantic["semantic_hypothesis_changed"] is False

    contract = repair["qualification_artifact_contract"]

    assert contract["selection_mode"] == "EXPLICIT_PATH_ONLY"
    assert contract["implicit_latest_selection"] is False
    assert contract["specific_qualification_number_hardcoded"] is False
    assert contract["required_status"] == "CLOSED_EXECUTED_QUALIFIED"
    assert contract["required_live_disposition"] == "QUALIFIED"

    assert plan["work_order"] == WORK_ORDER
    assert plan["semantic_request_population"] == PLANNED_REQUESTS
    assert plan["pair_count"] == PLANNED_PAIRS
    assert plan["only_authorized_delta"] == (
        "QUALIFICATION_ARTIFACT_RESOLUTION_AND_VALIDATION"
    )
    assert plan["semantic_request_equivalence_requirement"] == (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )
    assert plan["analysis_and_decision_rules"] == (
        "IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )

    assert plan["q010_created"] is False
    assert plan["q010_authorized"] is False
    assert plan["ontology_007r1_execution_authorized"] is False
    assert plan["ontology_007r1_executed"] is False
    assert plan["provider_call_made"] is False
    assert plan["model_call_made"] is False
    assert plan["nvidia_network_request_made"] is False

    assert freeze["work_order"] == WORK_ORDER
    assert freeze["repair_class"] == "AUTHORIZATION_BINDING_ONLY"
    assert freeze["semantic_request_count"] == PLANNED_REQUESTS
    assert freeze["pair_count"] == PLANNED_PAIRS
    assert freeze["semantic_request_equivalence"] == (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )
    assert freeze["semantic_decision_rules"] == (
        "UNCHANGED_FROM_FROZEN_ONTOLOGY_007"
    )
    assert freeze["specific_qualification_number_hardcoded"] is False
    assert freeze["qualification_selection_mode"] == "EXPLICIT_PATH_ONLY"
    assert freeze["q010_created"] is False
    assert freeze["q010_authorized"] is False
    assert freeze["ontology_007r1_executed"] is False
    assert freeze["provider_call_made"] is False
    assert freeze["model_call_made"] is False
    assert freeze["nvidia_network_request_made"] is False

    source = source007()
    source_ctx = source.static_preflight()

    return source, source_ctx


def semantic_materialization() -> list[dict[str, Any]]:
    source, source_ctx = prereg_context()
    rows = source.semantic_materialization(source_ctx)

    if len(rows) != PLANNED_REQUESTS:
        raise SystemExit("FAIL source O007 semantic population is not 18")

    frozen = load_json(SOURCE_MANIFEST)["requests"]

    if rows != frozen:
        raise SystemExit("FAIL regenerated semantic requests differ from frozen O007")

    return rows


def materialization_document() -> dict[str, Any]:
    rows = semantic_materialization()

    return {
        "work_order": WORK_ORDER,
        "source_work_order":
            "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
            "PREDICATE-CARRIER-DISCRIMINATION-007",
        "source_request_materialization_sha256":
            SOURCE_MANIFEST_SHA256,
        "source_instrument_sha256":
            SOURCE_SCRIPT_SHA256,
        "repair_class":
            "AUTHORIZATION_BINDING_ONLY",
        "semantic_request_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007",
        "semantic_decision_rules":
            "DELEGATED_UNCHANGED_TO_FROZEN_ONTOLOGY_007",
        "request_count":
            PLANNED_REQUESTS,
        "pair_count":
            PLANNED_PAIRS,
        "qualification_selection_mode":
            "EXPLICIT_PATH_ONLY",
        "specific_qualification_number_hardcoded":
            False,
        "production_interpretation_ruleset_changed":
            False,
        "provider_constructed":
            False,
        "network_request_made":
            False,
        "live_run_executed":
            False,
        "requests":
            rows,
    }


def write_materialization() -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP 007R1 materialization already exists: {MATERIALIZATION_PATH}"
        )

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            materialization_document(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def verify_materialization() -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL 007R1 materialization absent")

    actual = load_json(MATERIALIZATION_PATH)
    expected = materialization_document()

    if actual != expected:
        raise SystemExit("FAIL 007R1 materialization drift")

    source_rows = load_json(SOURCE_MANIFEST)["requests"]

    if actual["requests"] != source_rows:
        raise SystemExit("FAIL 007R1 semantic request byte parity")

    for r1, old in zip(actual["requests"], source_rows, strict=True):
        if r1["request"] != old["request"]:
            raise SystemExit("FAIL provider request projection drift")
        if r1["request_sha256"] != old["request_sha256"]:
            raise SystemExit("FAIL provider request SHA drift")

    return actual


def static_target_descriptor() -> dict[str, Any]:
    if not FREEZE_V2_PATH.exists():
        raise SystemExit("FAIL 007R1 freeze v0.2 absent")

    return {
        "work_order":
            WORK_ORDER,
        "preregistration_commit":
            PREREG_COMMIT,
        "authorization_repair_binding_sha256":
            sha256(REPAIR_PATH),
        "plan_sha256":
            sha256(PLAN_PATH),
        "preregistration_sha256":
            sha256(PREREG_PATH),
        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),
        "freeze_v0_2_sha256":
            sha256(FREEZE_V2_PATH),
        "instrument_sha256":
            sha256(Path(__file__)),
        "contract_test_sha256":
            sha256(CONTRACT_TEST),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "source_o007_instrument_sha256":
            SOURCE_SCRIPT_SHA256,
        "source_o007_request_materialization_sha256":
            SOURCE_MANIFEST_SHA256,
        "semantic_request_count":
            18,
        "pair_count":
            9,
        "semantic_request_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007",
        "qualification_selection_mode":
            "EXPLICIT_PATH_ONLY",
        "specific_qualification_number_hardcoded":
            False,
    }


def verify_freeze_v2() -> dict[str, Any]:
    freeze = load_json(FREEZE_V2_PATH)

    expected = {
        "authorization_repair_binding_sha256":
            sha256(REPAIR_PATH),
        "plan_sha256":
            sha256(PLAN_PATH),
        "preregistration_sha256":
            sha256(PREREG_PATH),
        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),
        "instrument_sha256":
            sha256(Path(__file__)),
        "contract_test_sha256":
            sha256(CONTRACT_TEST),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "source_o007_instrument_sha256":
            sha256(SOURCE_SCRIPT),
        "source_o007_request_materialization_sha256":
            sha256(SOURCE_MANIFEST),
        "source_o007_contract_test_sha256":
            sha256(SOURCE_TEST),
    }

    for key, value in expected.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL 007R1 freeze binding mismatch: {key}"
            )

    assert freeze["repair_class"] == "AUTHORIZATION_BINDING_ONLY"
    assert freeze["semantic_request_count"] == 18
    assert freeze["pair_count"] == 9
    assert freeze["semantic_request_equivalence"] == (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007"
    )
    assert freeze["semantic_decision_rules"] == (
        "DELEGATED_UNCHANGED_TO_FROZEN_ONTOLOGY_007"
    )

    assert freeze["qualification_selection_mode"] == "EXPLICIT_PATH_ONLY"
    assert freeze["specific_qualification_number_hardcoded"] is False

    assert freeze["q010_created"] is False
    assert freeze["q010_authorized"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["ontology_007r1_execution_authorized"] is False
    assert freeze["ontology_007r1_executed"] is False

    assert freeze["production_interpretation_ruleset_changed"] is False
    assert freeze["architecture_change_authorized"] is False

    return freeze


def static_preflight() -> tuple[ModuleType, Any]:
    source, source_ctx = prereg_context()
    verify_materialization()
    verify_freeze_v2()
    return source, source_ctx


def repository_clean_for_live() -> None:
    unstaged = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=ROOT,
        check=False,
    )
    if unstaged.returncode != 0:
        raise SystemExit("STOP repository has unstaged tracked changes")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT,
        check=False,
    )
    if staged.returncode != 0:
        raise SystemExit("STOP repository has staged changes")

    proc = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    unexpected = [
        line
        for line in proc.stdout.splitlines()
        if line and not line.startswith(".local/")
    ]

    if unexpected:
        raise SystemExit(
            "STOP unexpected untracked files outside .local: "
            + ", ".join(unexpected)
        )


def normalize_qualification_path(raw: str) -> Path:
    candidate = Path(raw)

    if not candidate.is_absolute():
        candidate = ROOT / candidate

    candidate = candidate.resolve()
    root = ROOT.resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            "STOP qualification artifact must be inside repository"
        ) from exc

    return candidate


def validate_qualification_document(
    q: dict[str, Any],
) -> None:
    if q.get("status") != "CLOSED_EXECUTED_QUALIFIED":
        raise SystemExit(
            "STOP qualification artifact not CLOSED_EXECUTED_QUALIFIED"
        )

    if q.get("provider_qualification_established") is not True:
        raise SystemExit(
            "STOP provider qualification not established"
        )

    if q.get("live_disposition") != "QUALIFIED":
        raise SystemExit(
            "STOP qualification live disposition not QUALIFIED"
        )

    if q.get("semantic_successor_target") != static_target_descriptor():
        raise SystemExit(
            "STOP qualification target differs from exact frozen 007R1"
        )

    if q.get("rerun_authorized") is not False:
        raise SystemExit(
            "STOP qualification artifact does not freeze rerun=false"
        )

    if q.get("semantic_hypothesis") is not None:
        raise SystemExit(
            "STOP qualification artifact contains semantic hypothesis"
        )

    if q.get("semantic_hypothesis_evaluated") is not False:
        raise SystemExit(
            "STOP qualification artifact evaluates semantic hypothesis"
        )

    if q.get("architecture_change_authorized") is not False:
        raise SystemExit(
            "STOP qualification artifact authorizes architecture change"
        )

    if q.get("independent_validation_claim") is not False:
        raise SystemExit(
            "STOP qualification artifact claims independent validation"
        )


def qualification_prerequisite(raw_path: str) -> tuple[Path, dict[str, Any]]:
    repository_clean_for_live()

    path = normalize_qualification_path(raw_path)

    if not path.exists():
        raise SystemExit(
            f"STOP qualification artifact absent: {path}"
        )

    rel = path.relative_to(ROOT.resolve()).as_posix()

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if tracked.returncode != 0:
        raise SystemExit(
            "STOP qualification artifact is not git-tracked"
        )

    q = load_json(path)
    validate_qualification_document(q)

    return path, q


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)

    modes = parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--materialize",
        action="store_true",
    )

    modes.add_argument(
        "--live",
        action="store_true",
    )

    parser.add_argument(
        "--qualification-result",
        type=str,
        default=None,
        help=(
            "Explicit tracked qualification result path. "
            "Required only for --live."
        ),
    )

    args = parser.parse_args(argv)

    if args.materialize:
        if args.qualification_result is not None:
            raise SystemExit(
                "STOP qualification artifact is not consumed during materialization"
            )

        prereg_context()
        write_materialization()

        print("PASS 007R1 materialized 18 semantic requests")
        print("semantic request byte parity vs frozen O007: 18/18")
        print("semantic decision logic: DELEGATED TO FROZEN O007")
        print("qualification selection: EXPLICIT PATH ONLY")
        print("provider/model/network calls: ZERO")

        return 0

    source, source_ctx = static_preflight()

    print("PASS frozen Ontology 007R1 instrument verified")
    print("requests: 18 / pairs: 9")
    print("semantic requests: BYTE IDENTICAL TO FROZEN O007")
    print("semantic execution/analyze/decision: DELEGATED TO FROZEN O007")
    print("qualification selection: EXPLICIT PATH ONLY")
    print("qualification number hard-coded: FALSE")

    if not args.live:
        if args.qualification_result is not None:
            raise SystemExit(
                "STOP qualification artifact is consumed only for --live"
            )

        print(
            "offline preflight only; no provider/model/network request made"
        )
        return 0

    if not args.qualification_result:
        raise SystemExit(
            "STOP --live requires --qualification-result EXPLICIT_PATH"
        )

    qualification_path, qualification = qualification_prerequisite(
        args.qualification_result
    )

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP 007R1 receipt already exists: {RECEIPT_PATH}"
        )

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=source.TIMEOUT_SECONDS,
        )
    )

    attempts, transport = source.execute_plan(
        ctx=source_ctx,
        provider=provider,
    )

    gate = source.adjudicability(attempts)

    if bool(gate["adjudicable"]):
        analysis = source.analyze(
            ctx=source_ctx,
            attempts=attempts,
        )
        disposition = analysis["disposition"]
        decision_evaluated = True
    else:
        analysis = None
        disposition = (
            "NOT_ADJUDICABLE_PROVIDER_OR_BOUNDARY_FAILURE"
        )
        decision_evaluated = False

    by_ordinal = Counter(
        int(x["semantic_ordinal"])
        for x in transport
    )

    retry_cells = sorted(
        ordinal
        for ordinal, count in by_ordinal.items()
        if count == 2
    )

    receipt = {
        "work_order":
            WORK_ORDER,
        "preregistration_commit":
            PREREG_COMMIT,
        "instrument_freeze_sha256":
            sha256(FREEZE_V2_PATH),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "source_o007_request_materialization_sha256":
            SOURCE_MANIFEST_SHA256,
        "semantic_request_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_007",
        "semantic_decision_logic":
            "DELEGATED_UNCHANGED_TO_FROZEN_ONTOLOGY_007",
        "qualification_artifact_path":
            qualification_path.relative_to(ROOT.resolve()).as_posix(),
        "qualification_artifact_sha256":
            sha256(qualification_path),
        "qualification_work_order":
            qualification.get("work_order"),
        "qualification_status":
            qualification["status"],
        "provider_qualification_established":
            qualification["provider_qualification_established"],
        "live_run_executed":
            True,
        "analysis_population":
            "ONTOLOGY_007R1_ONLY",
        "predecessor_live_outputs_reused":
            False,
        "production_interpretation_ruleset_changed":
            False,
        "attempts": [
            item.to_json()
            for item in attempts
        ],
        "transport_attempts":
            transport,
        "transport_calls_observed":
            len(transport),
        "transport_call_ceiling":
            source.TRANSPORT_CALL_CEILING,
        "transport_retries_used":
            len(retry_cells),
        "transport_retry_cells":
            retry_cells,
        "adjudicability":
            gate,
        "semantic_decision_rule_evaluated":
            decision_evaluated,
        "scientific_disposition":
            disposition,
        "semantic_analysis":
            analysis,
        "canonicalization_performed":
            False,
        "institutional_ir_constructed":
            False,
        "architecture_change_authorized":
            False,
        "independent_validation_claim":
            False,
        "self_adjudication":
            "NOT SELF-ADJUDICATED",
        "rerun_authorized":
            False,
    }

    RECEIPT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECEIPT_PATH.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"receipt written: {RECEIPT_PATH}")
    print(f"scientific disposition: {disposition}")
    print("self-adjudication: NOT SELF-ADJUDICATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
