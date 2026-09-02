#!/usr/bin/env python3
"""Ontology 007 — Syntactic Predicate-Carrier Discrimination.

Arm A:
    exact frozen Ontology 006 B_ROLE_GUIDED_B2 request.

Arm B:
    exact Arm A plus only the frozen experimental source-syntactic
    predicate-carrier guidance.

No production interpretation rule is changed. Offline is the default.
No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Final, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import ModelProvider, ModelProviderError, ModelRequest
from oic.nvidia_nim import (
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

WORK_ORDER: Final[str] = (
    "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-DISCRIMINATION-007"
)

PREREG_COMMIT: Final[str] = (
    "227354320680151789409ec8722a183a4e093596"
)

BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-syntactic-predicate-carrier-discrimination-007"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
BINDING_PATH = BENCH / "TREATMENT-BINDING-v0.1.json"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE_PLAN = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006/PLAN-v0.1.json"
)

SOURCE_MANIFEST = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

SOURCE_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_predicate_frame_discrimination_006.py"
)

RULESET_PATH = (
    ROOT
    / "design/institutional-ir-001/"
      "INTERPRETATION-RULESET-v0.1.json"
)

ADAPTER = ROOT / "src/oic/nvidia_nim.py"

CONTRACT_TEST = (
    ROOT
    / "tests/"
      "test_definition_ontology_syntactic_predicate_carrier_discrimination_007.py"
)

QUALIFICATION_RESULT = (
    ROOT
    / "benchmarks/provider-qualification/"
      "nvidia-nim-009/EXECUTION-RESULT-v0.1.json"
)

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/"
      "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-"
      "PREDICATE-CARRIER-DISCRIMINATION-007.json"
)

PLAN_SHA256: Final[str] = (
    "3e57e122ed718372bbe89bca33c9103bc9f47caca83ce86436ac5bbe63cc64ad"
)
PREREG_SHA256: Final[str] = (
    "a186e0fc3e46a2d277c5960b323ae9ffad8d012b5780264c595aab2996ec626e"
)
BINDING_SHA256: Final[str] = (
    "35d4eedc13ae6d1c2e510bd0feb53e717a363f4dd71aa8c5d6954138b0bc158b"
)
FREEZE_V1_SHA256: Final[str] = (
    "b6ed2b7648e9c9c7cdfc421b73030f1004c40c94358e8638cde99a6bc27e0e9d"
)

SOURCE_PLAN_SHA256: Final[str] = (
    "4ef705e97e74e4623251975fb0e71d9cd59e5eb380ab6b63ebb1d07571992816"
)
SOURCE_MANIFEST_SHA256: Final[str] = (
    "8b45a5755dc0ccc4df8d58f84f2408ef6e06e1847bb9b4e4e11963f3255e17bd"
)
SOURCE_SCRIPT_SHA256: Final[str] = (
    "ddd069cf7317f86ad3c50b6e48291c4579efafb57a2a0ac3f420a5a4d7e080f8"
)
RULESET_SHA256: Final[str] = (
    "8ba398eb20d346d66ce49c0f638babe2167930a07c3bd2946757fa41d6ccb114"
)
ADAPTER_SHA256: Final[str] = (
    "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
)

ARM_A: Final[str] = "A_ROLE_GUIDED_B2"
ARM_B: Final[str] = "B_SYNTAX_CARRIER_GUIDED_B2"

ARMS: Final[tuple[str, str]] = (ARM_A, ARM_B)
SPECIMENS: Final[tuple[str, str, str]] = (
    "IIR-006",
    "IIR-027",
    "IIR-028",
)

TARGET_SPECIMEN: Final[str] = "IIR-027"
TARGET_SLOT: Final[str] = "action"

PLANNED_REQUESTS: Final[int] = 18
PLANNED_PAIRS: Final[int] = 9

PACING_SECONDS: Final[float] = 4.0
TIMEOUT_SECONDS: Final[float] = 60.0
TRANSPORT_CALL_CEILING: Final[int] = 36

_SOURCE_MODULE_NAME: Final[str] = "_oic_frozen_ontology_006_for_007"


@dataclass(slots=True)
class StaticContext:
    plan: dict[str, Any]
    binding: dict[str, Any]
    source006: ModuleType
    source_ctx: Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path}")

    return value


def request_projection(request: ModelRequest) -> dict[str, Any]:
    return {
        "system_prompt": request.system_prompt,
        "user_prompt": request.user_prompt,
        "response_format": request.response_format,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }


def request_projection_sha256(request: ModelRequest) -> str:
    encoded = json.dumps(
        request_projection(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def verify_frozen_sources() -> None:
    expected = {
        PLAN_PATH: PLAN_SHA256,
        PREREG_PATH: PREREG_SHA256,
        BINDING_PATH: BINDING_SHA256,
        FREEZE_V1_PATH: FREEZE_V1_SHA256,
        SOURCE_PLAN: SOURCE_PLAN_SHA256,
        SOURCE_MANIFEST: SOURCE_MANIFEST_SHA256,
        SOURCE_SCRIPT: SOURCE_SCRIPT_SHA256,
        RULESET_PATH: RULESET_SHA256,
        ADAPTER: ADAPTER_SHA256,
    }

    for path, expected_sha in expected.items():
        actual = sha256(path)

        if actual != expected_sha:
            raise SystemExit(
                f"FAIL frozen source digest mismatch: {path}: "
                f"{actual} != {expected_sha}"
            )


def source006() -> ModuleType:
    verify_frozen_sources()

    if _SOURCE_MODULE_NAME in sys.modules:
        return sys.modules[_SOURCE_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(
        _SOURCE_MODULE_NAME,
        SOURCE_SCRIPT,
    )

    if spec is None or spec.loader is None:
        raise SystemExit("FAIL cannot load frozen Ontology 006")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SOURCE_MODULE_NAME] = module
    spec.loader.exec_module(module)

    if module.WORK_ORDER != (
        "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006"
    ):
        raise SystemExit("FAIL source Ontology 006 identity drift")

    return module


def prereg_context() -> StaticContext:
    verify_frozen_sources()

    plan = load_json(PLAN_PATH)
    binding = load_json(BINDING_PATH)
    freeze = load_json(FREEZE_V1_PATH)

    assert plan["work_order"] == WORK_ORDER
    assert plan["planned_provider_requests"] == 18
    assert plan["planned_pairs"] == 9
    assert plan["analysis_population"] == "ONTOLOGY_007_ONLY"

    assert plan["provider_prerequisite"]["work_order"] == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    )
    assert plan["provider_prerequisite"]["qualification_009_created"] is False
    assert plan["ontology_007_execution_authorized"] is False

    assert binding["work_order"] == WORK_ORDER
    assert binding["experimental_guidance_only"] is True
    assert binding["registered_interpretation_rule"] is False
    assert binding["production_ruleset_modified"] is False

    guidance = binding["arm_b"]["appended_text"]

    if hashlib.sha256(
        guidance.encode("utf-8")
    ).hexdigest() != binding["arm_b"]["appended_text_sha256"]:
        raise SystemExit("FAIL treatment guidance digest drift")

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL freeze v0.1 identity drift")

    if freeze["plan_sha256"] != PLAN_SHA256:
        raise SystemExit("FAIL freeze v0.1 plan binding drift")

    if freeze["preregistration_sha256"] != PREREG_SHA256:
        raise SystemExit("FAIL freeze v0.1 preregistration binding drift")

    if freeze["treatment_binding_sha256"] != BINDING_SHA256:
        raise SystemExit("FAIL freeze v0.1 treatment binding drift")

    if freeze["planned_provider_requests"] != 18:
        raise SystemExit("FAIL freeze v0.1 request count drift")

    if freeze["planned_pairs"] != 9:
        raise SystemExit("FAIL freeze v0.1 pair count drift")

    if freeze["qualification_009_created"] is not False:
        raise SystemExit("FAIL Q009 prematurely created")

    if freeze["live_run_executed"] is not False:
        raise SystemExit("FAIL preregistration records live execution")

    if freeze["ontology_007_execution_authorized"] is not False:
        raise SystemExit("FAIL Ontology 007 prematurely authorized")

    source = source006()
    source_ctx = source.prereg_context()

    return StaticContext(
        plan=plan,
        binding=binding,
        source006=source,
        source_ctx=source_ctx,
    )


def source_role_guided_request(
    *,
    ctx: StaticContext,
    specimen_id: str,
    run_index: int,
) -> ModelRequest:
    specimen = next(
        x
        for x in ctx.source_ctx.corpus["specimens"]
        if x["specimen_id"] == specimen_id
    )

    source_item = {
        "ordinal": 1,
        "specimen_id": specimen_id,
        "run_index": run_index,
        "arm": ctx.source006.ARM_B,
    }

    return ctx.source006.request_for(
        ctx=ctx.source_ctx,
        item=source_item,
        specimen=specimen,
    )


def request_for(
    *,
    ctx: StaticContext,
    item: dict[str, Any],
) -> ModelRequest:
    base = source_role_guided_request(
        ctx=ctx,
        specimen_id=item["specimen_id"],
        run_index=int(item["run_index"]),
    )

    if item["arm"] == ARM_A:
        return base

    if item["arm"] != ARM_B:
        raise ValueError(f"unknown Ontology 007 arm: {item['arm']}")

    guidance = ctx.binding["arm_b"]["appended_text"]

    return ModelRequest(
        system_prompt=base.system_prompt + guidance,
        user_prompt=base.user_prompt,
        response_format=base.response_format,
        temperature=base.temperature,
        max_tokens=base.max_tokens,
    )


def semantic_materialization(
    ctx: StaticContext,
) -> list[dict[str, Any]]:
    source_manifest = load_json(SOURCE_MANIFEST)

    source_rows = {
        (
            x["specimen_id"],
            int(x["run_index"]),
        ): x
        for x in source_manifest["requests"]
        if x["specimen_id"] in SPECIMENS
        and x["arm"] == "B_ROLE_GUIDED_B2"
    }

    if len(source_rows) != 9:
        raise SystemExit(
            "FAIL frozen O006 role-guided source population is not 9"
        )

    rows: list[dict[str, Any]] = []

    for item in ctx.plan["provider_request_plan"]:
        request = request_for(
            ctx=ctx,
            item=item,
        )

        specimen_id = item["specimen_id"]
        run_index = int(item["run_index"])

        source_row = source_rows[
            (
                specimen_id,
                run_index,
            )
        ]

        rows.append({
            "ordinal": int(item["ordinal"]),
            "specimen_id": specimen_id,
            "run_index": run_index,
            "arm": item["arm"],
            "candidate_span": source_row["candidate_span"],
            "request": request_projection(request),
            "request_sha256": request_projection_sha256(request),
            "gold_label_exposed": False,
            "candidate_normative_force_value_exposed": False,
            "b1_output_exposed": False,
            "authority_metadata_exposed": False,
            "source_identity_exposed": False,
            "provider_constructed": False,
            "network_request_made": False,
        })

    if len(rows) != 18:
        raise SystemExit("FAIL Ontology 007 materialization count")

    guidance = ctx.binding["arm_b"]["appended_text"]

    for specimen_id in SPECIMENS:
        for run_index in range(1, 4):
            a = next(
                x for x in rows
                if x["specimen_id"] == specimen_id
                and x["run_index"] == run_index
                and x["arm"] == ARM_A
            )

            b = next(
                x for x in rows
                if x["specimen_id"] == specimen_id
                and x["run_index"] == run_index
                and x["arm"] == ARM_B
            )

            old = source_rows[(specimen_id, run_index)]

            if a["request"] != old["request"]:
                raise SystemExit(
                    f"FAIL Arm A parity: {specimen_id} run {run_index}"
                )

            if a["request_sha256"] != old["request_sha256"]:
                raise SystemExit(
                    f"FAIL Arm A hash parity: {specimen_id} run {run_index}"
                )

            for key in (
                "user_prompt",
                "response_format",
                "temperature",
                "max_tokens",
            ):
                if a["request"][key] != b["request"][key]:
                    raise SystemExit(
                        f"FAIL Arm B changed {key}: "
                        f"{specimen_id} run {run_index}"
                    )

            if b["request"]["system_prompt"] != (
                a["request"]["system_prompt"] + guidance
            ):
                raise SystemExit(
                    f"FAIL Arm B delta not exact suffix: "
                    f"{specimen_id} run {run_index}"
                )

    return rows


def materialization_document(ctx: StaticContext) -> dict[str, Any]:
    return {
        "work_order": WORK_ORDER,
        "source_work_order":
            "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006",
        "source_request_materialization_sha256":
            SOURCE_MANIFEST_SHA256,
        "source_instrument_sha256":
            SOURCE_SCRIPT_SHA256,
        "plan_sha256":
            PLAN_SHA256,
        "preregistration_sha256":
            PREREG_SHA256,
        "treatment_binding_sha256":
            BINDING_SHA256,
        "request_count":
            18,
        "pair_count":
            9,
        "arm_a_request_count":
            9,
        "arm_b_request_count":
            9,
        "arm_a_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_O006_B_ROLE_GUIDED_B2",
        "arm_b_delta":
            "SYSTEM_PROMPT_APPEND_FROZEN_SYNTACTIC_CARRIER_GUIDANCE_ONLY",
        "analysis_population":
            "ONTOLOGY_007_ONLY",
        "predecessor_live_outputs_reused":
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
            semantic_materialization(ctx),
    }


def write_materialization(ctx: StaticContext) -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 007 materialization already exists: "
            f"{MATERIALIZATION_PATH}"
        )

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            materialization_document(ctx),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def verify_materialization(ctx: StaticContext) -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL Ontology 007 materialization absent")

    actual = load_json(MATERIALIZATION_PATH)
    expected = materialization_document(ctx)

    if actual != expected:
        raise SystemExit("FAIL Ontology 007 materialization drift")

    return actual


def static_target_descriptor() -> dict[str, Any]:
    if not FREEZE_V2_PATH.exists():
        raise SystemExit("FAIL Ontology 007 freeze v0.2 absent")

    return {
        "work_order": WORK_ORDER,
        "preregistration_commit": PREREG_COMMIT,
        "plan_sha256": sha256(PLAN_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "treatment_binding_sha256": sha256(BINDING_PATH),
        "preregistration_freeze_v0_1_sha256": sha256(FREEZE_V1_PATH),
        "freeze_v0_2_sha256": sha256(FREEZE_V2_PATH),
        "instrument_sha256": sha256(Path(__file__)),
        "contract_test_sha256": sha256(CONTRACT_TEST),
        "request_materialization_sha256": sha256(MATERIALIZATION_PATH),
        "provider_adapter_sha256": sha256(ADAPTER),
        "source_o006_instrument_sha256": SOURCE_SCRIPT_SHA256,
        "source_o006_request_materialization_sha256":
            SOURCE_MANIFEST_SHA256,
        "request_count": 18,
        "pair_count": 9,
    }


def verify_freeze_v2() -> dict[str, Any]:
    freeze = load_json(FREEZE_V2_PATH)

    expected = {
        "plan_sha256": sha256(PLAN_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "treatment_binding_sha256": sha256(BINDING_PATH),
        "preregistration_freeze_v0_1_sha256": sha256(FREEZE_V1_PATH),
        "instrument_sha256": sha256(Path(__file__)),
        "contract_test_sha256": sha256(CONTRACT_TEST),
        "request_materialization_sha256": sha256(MATERIALIZATION_PATH),
        "source_o006_instrument_sha256": sha256(SOURCE_SCRIPT),
        "source_o006_request_materialization_sha256":
            sha256(SOURCE_MANIFEST),
        "provider_adapter_sha256": sha256(ADAPTER),
    }

    for key, value in expected.items():
        if freeze.get(key) != value:
            raise SystemExit(
                f"FAIL Ontology 007 freeze binding mismatch: {key}"
            )

    assert freeze["request_count"] == 18
    assert freeze["pair_count"] == 9
    assert freeze["qualification_009_created"] is False
    assert freeze["qualification_009_executed"] is False
    assert freeze["qualification_009_qualified"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["ontology_007_execution_authorized"] is False
    assert freeze["architecture_change_authorized"] is False

    return freeze


def static_preflight() -> StaticContext:
    ctx = prereg_context()
    verify_materialization(ctx)
    verify_freeze_v2()
    return ctx


def qualification_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RESULT.exists():
        raise SystemExit(
            "STOP Provider Qualification 009 tracked closure result absent; "
            "Ontology 007 live execution unauthorized"
        )

    q = load_json(QUALIFICATION_RESULT)

    assert q["work_order"] == "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"

    if q.get("status") != "CLOSED_QUALIFIED":
        raise SystemExit("STOP Qualification 009 not CLOSED_QUALIFIED")

    if q.get("qualification_009_formally_closed") is not True:
        raise SystemExit("STOP Qualification 009 not formally closed")

    if q.get("qualification_009_qualified") is not True:
        raise SystemExit("STOP Qualification 009 not qualified")

    if q.get("provider_qualification_established") is not True:
        raise SystemExit("STOP provider qualification not established")

    if q.get("ontology_007_execution_authorized") is not True:
        raise SystemExit("STOP Qualification 009 did not authorize Ontology 007")

    if q.get("semantic_successor_target") != static_target_descriptor():
        raise SystemExit(
            "STOP Qualification 009 target differs from exact frozen Ontology 007"
        )

    return q


def execute_request(
    *,
    ctx: StaticContext,
    item: dict[str, Any],
    provider: ModelProvider,
    expected_request_sha256: str,
) -> tuple[Any, list[dict[str, Any]]]:
    request = request_for(
        ctx=ctx,
        item=item,
    )

    bounded = ctx.source006.bounded_provider(
        ctx=ctx.source_ctx,
        delegate=provider,
        semantic_ordinal=int(item["ordinal"]),
        expected_request_sha256=expected_request_sha256,
    )

    attempt = ctx.source_ctx.source004.StageAttempt(
        ordinal=int(item["ordinal"]),
        specimen_id=item["specimen_id"],
        run_index=int(item["run_index"]),
        stage=item["arm"],
        outcome="PROVIDER_ERROR",
    )

    try:
        response = bounded.complete(request)

    except ModelProviderError as exc:
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
        return attempt, bounded.calls

    try:
        proposal = ctx.source_ctx.source004.parse_nonforce(
            response.content
        )

    except ctx.source_ctx.source004.NonforceBoundaryError as exc:
        attempt.outcome = "BOUNDARY_REJECTED"
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)

    else:
        attempt.outcome = "ACCEPTED"
        attempt.proposal = proposal
        attempt.provider = response.provider
        attempt.model = response.model
        attempt.request_id = response.request_id
        attempt.raw_content_sha256 = hashlib.sha256(
            response.content.encode("utf-8")
        ).hexdigest()

    return attempt, bounded.calls


def adjudicability(attempts: Sequence[Any]) -> dict[str, int | bool]:
    accepted = [
        x for x in attempts
        if x.outcome == "ACCEPTED"
    ]

    accepted_keys = {
        (
            x.specimen_id,
            int(x.run_index),
            x.stage,
        )
        for x in accepted
    }

    complete = 0

    for specimen_id in SPECIMENS:
        for run_index in range(1, 4):
            if all(
                (
                    specimen_id,
                    run_index,
                    arm,
                ) in accepted_keys
                for arm in ARMS
            ):
                complete += 1

    gate = (
        len(attempts) == 18
        and len(accepted) == 18
        and complete == 9
    )

    return {
        "planned_provider_requests": 18,
        "observed_attempts": len(attempts),
        "accepted_provider_requests": len(accepted),
        "complete_pairs": complete,
        "adjudicable": gate,
    }


def slot_value(attempt: Any, slot: str) -> str | None:
    return ctx_slot_value(attempt, slot)


def ctx_slot_value(attempt: Any, slot: str) -> str | None:
    if attempt.proposal is None:
        return None

    values = [
        item.get("proposed_value")
        for item in attempt.proposal.get("proposed_assertions", [])
        if item.get("slot") == slot
    ]

    if len(values) != 1:
        return None

    value = values[0]

    return value if isinstance(value, str) else None


def decide(
    *,
    target_treatment_compatible: int,
    paired_improvements: int,
    safety_defect_count: int,
) -> str:
    if safety_defect_count > 0:
        return "REGRESSION"

    if (
        target_treatment_compatible == 3
        and paired_improvements >= 2
    ):
        return "SUPPORTS_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"

    if (
        target_treatment_compatible <= 1
        and paired_improvements == 0
    ):
        return "REFUTES_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"

    return "INCONCLUSIVE"


def analyze(
    *,
    ctx: StaticContext,
    attempts: Sequence[Any],
) -> dict[str, Any]:
    by_id = {
        item["specimen_id"]: item
        for item in ctx.source_ctx.corpus["specimens"]
    }

    def attempt_for(
        specimen_id: str,
        run_index: int,
        arm: str,
    ) -> Any:
        return next(
            item
            for item in attempts
            if item.specimen_id == specimen_id
            and int(item.run_index) == run_index
            and item.stage == arm
        )

    target_specimen = by_id[TARGET_SPECIMEN]

    target_observations: list[dict[str, Any]] = []
    treatment_compatible = 0
    paired_improvements = 0

    for run_index in range(1, 4):
        baseline = attempt_for(
            TARGET_SPECIMEN,
            run_index,
            ARM_A,
        )

        treatment = attempt_for(
            TARGET_SPECIMEN,
            run_index,
            ARM_B,
        )

        baseline_ok = ctx.source_ctx.source004._single_slot_compatible(
            source=ctx.source_ctx.ctx005.source,
            v1=ctx.source_ctx.ctx005.v1,
            corpus=ctx.source_ctx.corpus,
            specimen=target_specimen,
            attempt=baseline,
            slot=TARGET_SLOT,
        )

        treatment_ok = ctx.source_ctx.source004._single_slot_compatible(
            source=ctx.source_ctx.ctx005.source,
            v1=ctx.source_ctx.ctx005.v1,
            corpus=ctx.source_ctx.corpus,
            specimen=target_specimen,
            attempt=treatment,
            slot=TARGET_SLOT,
        )

        if treatment_ok:
            treatment_compatible += 1

        improvement = (
            not baseline_ok
            and treatment_ok
        )

        if improvement:
            paired_improvements += 1

        target_observations.append({
            "specimen_id": TARGET_SPECIMEN,
            "run_index": run_index,
            "slot": TARGET_SLOT,
            "expected_value": "consider",
            "baseline_value": ctx_slot_value(
                baseline,
                TARGET_SLOT,
            ),
            "treatment_value": ctx_slot_value(
                treatment,
                TARGET_SLOT,
            ),
            "baseline_compatible": baseline_ok,
            "treatment_compatible": treatment_ok,
            "paired_improvement": improvement,
        })

    safety_defects: list[dict[str, Any]] = []
    safety_observations: list[dict[str, Any]] = []

    for specimen_id in SPECIMENS:
        specimen = by_id[specimen_id]

        expected_slots = [
            slot
            for slot, spec
            in specimen["gold"]["expected_slots"].items()
            if (
                slot != "normative_force"
                and spec["status"] == "ESTABLISHED"
                and not (
                    specimen_id == TARGET_SPECIMEN
                    and slot == TARGET_SLOT
                )
            )
        ]

        for run_index in range(1, 4):
            baseline = attempt_for(
                specimen_id,
                run_index,
                ARM_A,
            )

            treatment = attempt_for(
                specimen_id,
                run_index,
                ARM_B,
            )

            for slot in expected_slots:
                baseline_ok = (
                    ctx.source_ctx.source004._single_slot_compatible(
                        source=ctx.source_ctx.ctx005.source,
                        v1=ctx.source_ctx.ctx005.v1,
                        corpus=ctx.source_ctx.corpus,
                        specimen=specimen,
                        attempt=baseline,
                        slot=slot,
                    )
                )

                treatment_ok = (
                    ctx.source_ctx.source004._single_slot_compatible(
                        source=ctx.source_ctx.ctx005.source,
                        v1=ctx.source_ctx.ctx005.v1,
                        corpus=ctx.source_ctx.corpus,
                        specimen=specimen,
                        attempt=treatment,
                        slot=slot,
                    )
                )

                treatment_only_defect = (
                    baseline_ok
                    and not treatment_ok
                )

                if treatment_only_defect:
                    safety_defects.append({
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                        "slot": slot,
                    })

                safety_observations.append({
                    "specimen_id": specimen_id,
                    "run_index": run_index,
                    "slot": slot,
                    "baseline_compatible": baseline_ok,
                    "treatment_compatible": treatment_ok,
                    "treatment_only_defect": treatment_only_defect,
                })

    disposition = decide(
        target_treatment_compatible=treatment_compatible,
        paired_improvements=paired_improvements,
        safety_defect_count=len(safety_defects),
    )

    return {
        "disposition": disposition,

        "target_endpoint": {
            "specimen_id": TARGET_SPECIMEN,
            "slot": TARGET_SLOT,
            "expected_value": "consider",
            "syntax_guided_compatible": treatment_compatible,
            "syntax_guided_planned": 3,
            "paired_improvements": paired_improvements,
            "paired_planned": 3,
            "observations": target_observations,
        },

        "safety_endpoint": {
            "syntax_guided_only_defect_count": len(safety_defects),
            "syntax_guided_only_defect_instances": safety_defects,
            "observations": safety_observations,
        },

        "provider_errors": sum(
            x.outcome == "PROVIDER_ERROR"
            for x in attempts
        ),

        "boundary_rejections": sum(
            x.outcome == "BOUNDARY_REJECTED"
            for x in attempts
        ),

        "architecture_change_authorized": False,
        "descriptive_only": True,
    }


def execute_plan(
    *,
    ctx: StaticContext,
    provider: ModelProvider,
) -> tuple[list[Any], list[dict[str, Any]]]:
    materialized = semantic_materialization(ctx)

    expected_sha = {
        int(item["ordinal"]): item["request_sha256"]
        for item in materialized
    }

    attempts: list[Any] = []
    transport_attempts: list[dict[str, Any]] = []

    provider_plan = ctx.plan["provider_request_plan"]

    for index, item in enumerate(provider_plan):
        ordinal = int(item["ordinal"])

        print(
            f"[{ordinal:02d}/18] START "
            f"{item['specimen_id']} "
            f"run={item['run_index']} "
            f"arm={item['arm']}",
            flush=True,
        )

        attempt, calls = execute_request(
            ctx=ctx,
            item=item,
            provider=provider,
            expected_request_sha256=expected_sha[ordinal],
        )

        attempts.append(attempt)
        transport_attempts.extend(calls)

        if len(transport_attempts) > TRANSPORT_CALL_CEILING:
            raise SystemExit("FAIL transport call ceiling exceeded")

        print(
            f"[{ordinal:02d}/18] DONE "
            f"outcome={attempt.outcome} "
            f"transport_calls={len(calls)}",
            flush=True,
        )

        if index < len(provider_plan) - 1:
            time.sleep(PACING_SECONDS)

    return attempts, transport_attempts


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

    args = parser.parse_args(argv)

    if args.materialize:
        ctx = prereg_context()
        write_materialization(ctx)

        print("PASS Ontology 007 materialized 18 requests")
        print("Arm A parity vs frozen O006 role-guided B2: 9/9")
        print("Arm B delta: exact frozen syntactic-carrier suffix only")
        print("provider/model/network calls: ZERO")

        return 0

    ctx = static_preflight()

    print("PASS frozen Ontology 007 instrument verified")
    print("requests: 18 / pairs: 9")
    print("Arm A: exact frozen O006 role-guided B2")
    print("Arm B: Arm A + frozen syntactic carrier suffix")
    print("transport recovery: inherited frozen O006 envelope")
    print("Q009 required before live execution")

    if not args.live:
        print(
            "offline preflight only; no provider/model/network request made"
        )
        return 0

    qualification = qualification_prerequisite()

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 007 receipt already exists: {RECEIPT_PATH}"
        )

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=DEFAULT_NIM_MODEL,
            base_url=DEFAULT_NIM_BASE_URL,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )

    attempts, transport = execute_plan(
        ctx=ctx,
        provider=provider,
    )

    gate = adjudicability(attempts)

    if bool(gate["adjudicable"]):
        analysis = analyze(
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
        "work_order": WORK_ORDER,
        "preregistration_commit": PREREG_COMMIT,
        "instrument_freeze_sha256": sha256(FREEZE_V2_PATH),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "provider_qualification_009_result_sha256":
            sha256(QUALIFICATION_RESULT),
        "provider_qualification_009_status":
            qualification["status"],
        "live_run_executed": True,
        "analysis_population": "ONTOLOGY_007_ONLY",
        "predecessor_live_outputs_reused": False,
        "production_interpretation_ruleset_changed": False,
        "attempts": [
            item.to_json()
            for item in attempts
        ],
        "transport_attempts": transport,
        "transport_calls_observed": len(transport),
        "transport_call_ceiling": 36,
        "transport_retries_used": len(retry_cells),
        "transport_retry_cells": retry_cells,
        "adjudicability": gate,
        "semantic_decision_rule_evaluated":
            decision_evaluated,
        "scientific_disposition": disposition,
        "semantic_analysis": analysis,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "architecture_change_authorized": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
        "rerun_authorized": False,
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
