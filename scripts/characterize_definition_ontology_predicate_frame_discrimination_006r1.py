#!/usr/bin/env python3
"""Ontology Predicate-Frame Discrimination 006R1.

Authorization-binding repair only.

All semantic request construction, transport recovery, adjudicability,
decision logic, target analysis and safety analysis delegate directly to
the hash-frozen Ontology 006 implementation.

The only changed execution surface is the provider-qualification prerequisite:
live execution requires a formally closed tracked Qualification 008 result
bound to this exact frozen O006R1 artifact set.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Sequence

from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

ROOT = Path(__file__).resolve().parents[1]

WORK_ORDER: Final[str] = (
    "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006R1"
)

PREREG_COMMIT: Final[str] = (
    "3d77d12e8a32487b44144e5a2fc6f8cd860d63eb"
)

BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006r1"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
REPAIR_PATH = BENCH / "AUTHORIZATION-BINDING-REPAIR-v0.1.json"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

ORIGINAL_DIR = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006"
)

ORIGINAL_PLAN = ORIGINAL_DIR / "PLAN-v0.1.json"
ORIGINAL_PREREG = ORIGINAL_DIR / "PREREGISTRATION.md"
ORIGINAL_BINDING = ORIGINAL_DIR / "TREATMENT-BINDING-v0.1.json"
ORIGINAL_FREEZE_V1 = ORIGINAL_DIR / "PLAN-FREEZE-v0.1.json"
ORIGINAL_MANIFEST = ORIGINAL_DIR / "REQUEST-MATERIALIZATION-v0.1.json"
ORIGINAL_FREEZE_V2 = ORIGINAL_DIR / "PLAN-FREEZE-v0.2.json"

ORIGINAL_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006.py"
)

ORIGINAL_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_predicate_frame_discrimination_006.py"
)

CONTRACT_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_predicate_frame_discrimination_006r1.py"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"

QUALIFICATION_RESULT = (
    ROOT
    / "benchmarks/provider-qualification/"
      "nvidia-nim-008/EXECUTION-RESULT-v0.1.json"
)

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/"
      "OIC-DEFINITION-ONTOLOGY-"
      "PREDICATE-FRAME-DISCRIMINATION-006R1.json"
)

PLAN_SHA256: Final[str] = (
    "6ccf2052a93f481dae0b3604b70900f71c0e6aad66fc93c4eee1bcfe3b759ec1"
)
PREREG_SHA256: Final[str] = (
    "7c1930391ae689bfd0bd54623b0a8ff1f8739df28cc28e08025483187a3f6818"
)
REPAIR_SHA256: Final[str] = (
    "0219946389a95129a2a6dbc70477664272fc548d0dcf151645e1205987a59637"
)
FREEZE_V1_SHA256: Final[str] = (
    "ead01e4f9229a0c8eaa5bd5ea0cce536558719e35ddc60c26b7175f2d95a177e"
)

ORIGINAL_PLAN_SHA256: Final[str] = (
    "4ef705e97e74e4623251975fb0e71d9cd59e5eb380ab6b63ebb1d07571992816"
)
ORIGINAL_PREREG_SHA256: Final[str] = (
    "5da9fd19c17fe24f9560438d047e2f7f201e07580f1990fba171d460176c1825"
)
ORIGINAL_BINDING_SHA256: Final[str] = (
    "f95efb0189adc9368499684e6d3262651751c39fe8a5e422da94f8ef0111920a"
)
ORIGINAL_FREEZE_V1_SHA256: Final[str] = (
    "1dba54e248f7761e5c153b18a37d86ded55bba9a92e95bd3c9db52fa3826df27"
)
ORIGINAL_MANIFEST_SHA256: Final[str] = (
    "8b45a5755dc0ccc4df8d58f84f2408ef6e06e1847bb9b4e4e11963f3255e17bd"
)
ORIGINAL_FREEZE_V2_SHA256: Final[str] = (
    "2acd8e2ebe0a6913721240008f06c28108ea01c85c4484958c1b849ef95b5719"
)
ORIGINAL_SCRIPT_SHA256: Final[str] = (
    "ddd069cf7317f86ad3c50b6e48291c4579efafb57a2a0ac3f420a5a4d7e080f8"
)
ORIGINAL_TEST_SHA256: Final[str] = (
    "07231f87fb029a5154a843c6e8fed5fe77a6d5ef23fcdf0af330a7d3dd7b7379"
)
ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

_ORIGINAL_MODULE_NAME: Final[str] = "_oic_frozen_ontology_006_for_006r1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path}")
    return value


def verify_frozen_sources() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        REPAIR_PATH: REPAIR_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        ORIGINAL_PLAN: ORIGINAL_PLAN_SHA256,
        ORIGINAL_PREREG: ORIGINAL_PREREG_SHA256,
        ORIGINAL_BINDING: ORIGINAL_BINDING_SHA256,
        ORIGINAL_FREEZE_V1: ORIGINAL_FREEZE_V1_SHA256,
        ORIGINAL_MANIFEST: ORIGINAL_MANIFEST_SHA256,
        ORIGINAL_FREEZE_V2: ORIGINAL_FREEZE_V2_SHA256,
        ORIGINAL_SCRIPT: ORIGINAL_SCRIPT_SHA256,
        ORIGINAL_TEST: ORIGINAL_TEST_SHA256,
        ADAPTER: ADAPTER_SHA256,
    }

    for path, expected_sha in expected.items():
        if sha256(path) != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}"
            )


def original() -> ModuleType:
    verify_frozen_sources()

    if _ORIGINAL_MODULE_NAME in sys.modules:
        return sys.modules[_ORIGINAL_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _ORIGINAL_MODULE_NAME,
        ORIGINAL_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("FAIL cannot load frozen Ontology 006")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_ORIGINAL_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != (
        "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006"
    ):
        raise SystemExit("FAIL original O006 identity drift")

    return module


def verify_repair_plan() -> dict[str, Any]:
    verify_frozen_sources()

    plan = load_json(PLAN_PATH)
    repair = load_json(REPAIR_PATH)

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL O006R1 identity drift")

    if plan["planned_provider_requests"] != 18:
        raise SystemExit("FAIL O006R1 request count drift")

    if plan["planned_pairs"] != 9:
        raise SystemExit("FAIL O006R1 pair count drift")

    if plan["semantic_request_equivalence"] != (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_006"
    ):
        raise SystemExit("FAIL semantic-equivalence requirement drift")

    if plan["provider_prerequisite"]["work_order"] != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-008"
    ):
        raise SystemExit("FAIL repaired provider prerequisite drift")

    if plan["q007_authorization_reused"] is not False:
        raise SystemExit("FAIL Q007 authorization inheritance")

    if plan["ontology_006r1_execution_authorized"] is not False:
        raise SystemExit("FAIL O006R1 prematurely authorized")

    if repair["repair_class"] != (
        "EXECUTION_AUTHORIZATION_BINDING_ONLY"
    ):
        raise SystemExit("FAIL repair class drift")

    return plan


def original_context() -> Any:
    source = original()

    # This is static-only verification. It does not invoke O006's obsolete
    # live qualification prerequisite.
    return source.static_preflight()


def repaired_requests() -> list[dict[str, Any]]:
    source = original()
    ctx = original_context()

    rows = source.semantic_materialization(ctx)

    if len(rows) != 18:
        raise SystemExit("FAIL original O006 recomputation count")

    original_manifest = load_json(ORIGINAL_MANIFEST)
    frozen_rows = original_manifest["requests"]

    if len(frozen_rows) != 18:
        raise SystemExit("FAIL original O006 manifest count")

    for recomputed, frozen in zip(rows, frozen_rows, strict=True):
        for key in (
            "ordinal",
            "specimen_id",
            "run_index",
            "arm",
            "request",
            "request_sha256",
        ):
            if recomputed[key] != frozen[key]:
                raise SystemExit(
                    f"FAIL O006 recomputation differs at "
                    f"ordinal {recomputed['ordinal']} field {key}"
                )

    return rows


def materialization_document() -> dict[str, Any]:
    rows = repaired_requests()

    return {
        "work_order":
            WORK_ORDER,

        "revision_of":
            "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006",

        "authorization_binding_repair_sha256":
            REPAIR_SHA256,

        "source_request_materialization_sha256":
            ORIGINAL_MANIFEST_SHA256,

        "source_semantic_instrument_sha256":
            ORIGINAL_SCRIPT_SHA256,

        "semantic_execution_delegation":
            "DIRECT_TO_HASH_FROZEN_ONTOLOGY_006_IMPLEMENTATION",

        "semantic_request_equivalence":
            "EVERY_REQUEST_PROJECTION_BYTE_IDENTICAL_TO_FROZEN_O006",

        "request_count":
            18,

        "pair_count":
            9,

        "baseline_request_count":
            9,

        "treatment_request_count":
            9,

        "analysis_population":
            "ONTOLOGY_006R1_ONLY",

        "q007_observations_reused":
            False,

        "q007_authorization_reused":
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
            f"STOP O006R1 materialization already exists: "
            f"{MATERIALIZATION_PATH}"
        )

    doc = materialization_document()

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            doc,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print("materialized 18 repaired requests")
    print("semantic request equivalence: 18/18 BYTE-IDENTICAL")
    print("provider/network calls: ZERO")


def verify_materialization() -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL O006R1 materialization absent")

    actual = load_json(MATERIALIZATION_PATH)
    expected = materialization_document()

    if actual != expected:
        raise SystemExit("FAIL O006R1 materialization drift")

    return actual


def static_target_descriptor() -> dict[str, Any]:
    if not FREEZE_V2_PATH.exists():
        raise SystemExit("FAIL O006R1 freeze v0.2 absent")

    return {
        "work_order":
            WORK_ORDER,

        "preregistration_commit":
            PREREG_COMMIT,

        "plan_sha256":
            sha256(PLAN_PATH),

        "preregistration_sha256":
            sha256(PREREG_PATH),

        "authorization_binding_repair_sha256":
            sha256(REPAIR_PATH),

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

        "provider_adapter_sha256":
            sha256(ADAPTER),

        "request_count":
            18,

        "pair_count":
            9,
    }


def verify_freeze_v2() -> dict[str, Any]:
    freeze = load_json(FREEZE_V2_PATH)

    expected = {
        "plan_sha256": sha256(PLAN_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "authorization_binding_repair_sha256": sha256(REPAIR_PATH),
        "preregistration_freeze_v0_1_sha256": sha256(FREEZE_V1_PATH),
        "instrument_sha256": sha256(Path(__file__)),
        "contract_test_sha256": sha256(CONTRACT_TEST),
        "request_materialization_sha256": sha256(MATERIALIZATION_PATH),
        "source_o006_instrument_sha256": sha256(ORIGINAL_SCRIPT),
        "source_o006_request_materialization_sha256":
            sha256(ORIGINAL_MANIFEST),
        "provider_adapter_sha256": sha256(ADAPTER),
    }

    for key, value in expected.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL O006R1 freeze v0.2 binding mismatch: {key}"
            )

    if freeze["request_count"] != 18:
        raise SystemExit("FAIL frozen request count")

    if freeze["pair_count"] != 9:
        raise SystemExit("FAIL frozen pair count")

    if freeze["qualification_008_created"] is not False:
        raise SystemExit("FAIL Q008 prematurely created")

    if freeze["live_run_executed"] is not False:
        raise SystemExit("FAIL O006R1 already marked executed")

    if freeze["ontology_006r1_execution_authorized"] is not False:
        raise SystemExit("FAIL O006R1 prematurely authorized")

    return freeze


def static_preflight() -> Any:
    verify_repair_plan()
    verify_materialization()
    verify_freeze_v2()

    source = original()

    # Strong semantic invariant: all live semantic machinery comes directly
    # from the frozen O006 module rather than a copied implementation.
    for name in (
        "request_for",
        "semantic_materialization",
        "bounded_provider",
        "execute_request",
        "execute_plan",
        "adjudicability",
        "analyze",
        "decide",
    ):
        if not callable(getattr(source, name, None)):
            raise SystemExit(
                f"FAIL required frozen O006 semantic delegate absent: {name}"
            )

    return original_context()


def qualification_prerequisite() -> dict[str, Any]:
    """Consume only the formally closed tracked Q008 result."""

    if not QUALIFICATION_RESULT.exists():
        raise SystemExit(
            "STOP Provider Qualification 008 tracked closure result absent; "
            "O006R1 live execution unauthorized"
        )

    q = load_json(QUALIFICATION_RESULT)

    if q.get("work_order") != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-008"
    ):
        raise SystemExit("STOP wrong provider qualification result")

    if q.get("status") != "CLOSED_QUALIFIED":
        raise SystemExit("STOP Qualification 008 is not CLOSED_QUALIFIED")

    if q.get("qualification_008_formally_closed") is not True:
        raise SystemExit("STOP Qualification 008 not formally closed")

    if q.get("qualification_008_qualified") is not True:
        raise SystemExit("STOP Qualification 008 not qualified")

    if q.get("provider_qualification_established") is not True:
        raise SystemExit("STOP provider qualification not established")

    if q.get("ontology_006r1_execution_authorized") is not True:
        raise SystemExit("STOP Qualification 008 did not authorize O006R1")

    if q.get("semantic_successor_target") != static_target_descriptor():
        raise SystemExit(
            "STOP Qualification 008 target does not match exact frozen O006R1"
        )

    return q


def execute_live() -> dict[str, Any]:
    ctx = static_preflight()

    # Must pass before provider construction.
    qualification = qualification_prerequisite()

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP O006R1 receipt already exists: {RECEIPT_PATH}"
        )

    source = original()

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=source.TIMEOUT_SECONDS,
        )
    )

    attempts, transport = source.execute_plan(
        ctx=ctx,
        provider=provider,
    )

    gate = source.adjudicability(attempts)

    if bool(gate["adjudicable"]):
        analysis = source.analyze(
            ctx=ctx,
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

    receipt = {
        "work_order":
            WORK_ORDER,

        "revision_of":
            source.WORK_ORDER,

        "preregistration_commit":
            PREREG_COMMIT,

        "authorization_binding_repair_sha256":
            REPAIR_SHA256,

        "instrument_freeze_sha256":
            sha256(FREEZE_V2_PATH),

        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),

        "source_o006_instrument_sha256":
            ORIGINAL_SCRIPT_SHA256,

        "source_o006_request_materialization_sha256":
            ORIGINAL_MANIFEST_SHA256,

        "provider_qualification_008_result_sha256":
            sha256(QUALIFICATION_RESULT),

        "provider_qualification_008_status":
            qualification["status"],

        "live_run_executed":
            True,

        "analysis_population":
            "ONTOLOGY_006R1_ONLY",

        "semantic_execution_delegation":
            "DIRECT_TO_HASH_FROZEN_ONTOLOGY_006_IMPLEMENTATION",

        "semantic_request_equivalence":
            "18_OF_18_BYTE_IDENTICAL_TO_FROZEN_O006",

        "q007_observations_reused":
            False,

        "q007_authorization_reused":
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

        "architectural_change_authorized":
            False,

        "independent_validation_claim":
            False,

        "self_adjudication":
            "NOT SELF-ADJUDICATED",
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

    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--materialize",
        action="store_true",
    )

    parser.add_argument(
        "--live",
        action="store_true",
    )

    args = parser.parse_args(argv)

    if args.materialize and args.live:
        raise SystemExit(
            "FAIL --materialize and --live are mutually exclusive"
        )

    if args.materialize:
        verify_repair_plan()
        write_materialization()
        return 0

    static_preflight()

    print("PASS frozen O006R1 repaired executable")
    print("semantic requests: 18/18 byte-identical to frozen O006")
    print("semantic machinery: DIRECT DELEGATION TO FROZEN O006")
    print("transport machinery: DIRECT DELEGATION TO FROZEN O006")
    print("provider prerequisite: FORMALLY CLOSED Q008 RESULT")
    print("Q007 authorization reuse: FALSE")
    print("O006R1 authorization: FALSE")

    if not args.live:
        print(
            "offline preflight only; no provider/model/network request made"
        )
        return 0

    execute_live()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
