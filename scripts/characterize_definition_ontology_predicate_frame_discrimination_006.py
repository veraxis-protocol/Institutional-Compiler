#!/usr/bin/env python3
"""Ontology Predicate-Frame Discrimination 006.

Preregistered successor to closed Ontology 005.

Arm A:
    exact frozen Ontology 005 B2 non-force request.

Arm B:
    exact Arm A request except that the system prompt appends only the
    already-frozen action/object role justifications from
    OIC-INTERPRETATION-RULESET-001 v0.1.

No normative-force value, B1 output, gold, authority metadata or source
identity is exposed to either arm.

Offline is the default. No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import (  # noqa: E402
    ModelProvider,
    ModelProviderError,
    ModelRequest,
)
from oic.nvidia_nim import (  # noqa: E402
    DEFAULT_NIM_BASE_URL,
    DEFAULT_NIM_MODEL,
    NvidiaNimConfig,
    NvidiaNimProvider,
)

WORK_ORDER: Final[str] = (
    "OIC-DEFINITION-ONTOLOGY-PREDICATE-FRAME-DISCRIMINATION-006"
)

PREREG_COMMIT: Final[str] = (
    "36d469b052835fc9b351bdd8c009fd8462a88628"
)

PLAN_STARTING_SHA: Final[str] = (
    "362a68074efc810d71da28a09079a5abd50e8def"
)

BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-predicate-frame-discrimination-006"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
BINDING_PATH = BENCH / "TREATMENT-BINDING-v0.1.json"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE005_SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_staged_decomposition_005.py"
)

SOURCE005_MANIFEST = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

SOURCE005_RESULT = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005/"
      "EXECUTION-RESULT-v0.1.json"
)

SOURCE005_ADJUDICATION = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005/"
      "POST-RUN-ADJUDICATION.md"
)

SOURCE005_LOCALIZATION = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005/"
      "REGRESSION-LOCALIZATION-v0.1.json"
)

RULESET_PATH = (
    ROOT
    / "design/institutional-ir-001/"
      "INTERPRETATION-RULESET-v0.1.json"
)

CORPUS_PATH = (
    ROOT
    / "benchmarks/characterization/"
      "interpretation-proposal-001/CORPUS-v0.1.json"
)

QUALIFICATION_RECEIPT = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-006.json"
)

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/"
      "OIC-DEFINITION-ONTOLOGY-"
      "PREDICATE-FRAME-DISCRIMINATION-006.json"
)

PLAN_SHA256: Final[str] = (
    "4ef705e97e74e4623251975fb0e71d9cd59e5eb380ab6b63ebb1d07571992816"
)

PREREG_SHA256: Final[str] = (
    "5da9fd19c17fe24f9560438d047e2f7f201e07580f1990fba171d460176c1825"
)

BINDING_SHA256: Final[str] = (
    "f95efb0189adc9368499684e6d3262651751c39fe8a5e422da94f8ef0111920a"
)

FREEZE_V1_SHA256: Final[str] = (
    "1dba54e248f7761e5c153b18a37d86ded55bba9a92e95bd3c9db52fa3826df27"
)

SOURCE005_SCRIPT_SHA256: Final[str] = (
    "4a638722c680f3ed400b5987cdc023d8493e146bc7600f299371808fed9cf265"
)

SOURCE005_MANIFEST_SHA256: Final[str] = (
    "3c867101c0ef4ae1e27add45a8d980bd389c0f38f3608321557c0941d371bf29"
)

SOURCE005_RESULT_SHA256: Final[str] = (
    "f8ca5b789ae2f1831f207a71bc14ae4bd9459e8a9c2be6d8b7fd2d65dbe9b882"
)

SOURCE005_ADJUDICATION_SHA256: Final[str] = (
    "b45744f9a35129001ee6de64ee3d8f15d8c909b9f1483772e13dc4708a345156"
)

SOURCE005_LOCALIZATION_SHA256: Final[str] = (
    "74259ff42e08718c82e8752a25c41214a1c1c48d3b97ff6994c28c5cfb095c63"
)

RULESET_SHA256: Final[str] = (
    "8ba398eb20d346d66ce49c0f638babe2167930a07c3bd2946757fa41d6ccb114"
)

CORPUS_SHA256: Final[str] = (
    "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
)

ARM_A: Final[str] = "A_BASELINE_B2"
ARM_B: Final[str] = "B_ROLE_GUIDED_B2"

ARMS: Final[tuple[str, str]] = (
    ARM_A,
    ARM_B,
)

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

CANDIDATE_PLACEHOLDER: Final[str] = "{candidate_span}"


@dataclass(slots=True)
class StaticContext:
    plan: dict[str, Any]
    binding: dict[str, Any]
    source005: ModuleType
    ctx005: Any
    source004: ModuleType
    corpus: dict[str, Any]


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value: Any = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(value, dict):
        raise SystemExit(
            f"FAIL expected JSON object: {path}"
        )

    return value


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise SystemExit(
            f"FAIL cannot load frozen module: {path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


def request_projection(
    request: ModelRequest,
) -> dict[str, Any]:
    return {
        "system_prompt":
            request.system_prompt,
        "user_prompt":
            request.user_prompt,
        "response_format":
            request.response_format,
        "temperature":
            request.temperature,
        "max_tokens":
            request.max_tokens,
    }


def request_projection_sha256(
    request: ModelRequest,
) -> str:
    encoded = json.dumps(
        request_projection(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def render_candidate(
    template: str,
    candidate_span: str,
) -> str:
    if template.count(
        CANDIDATE_PLACEHOLDER
    ) != 1:
        raise ValueError(
            "template must contain exactly one candidate placeholder"
        )

    rendered = template.replace(
        CANDIDATE_PLACEHOLDER,
        candidate_span,
        1,
    )

    if CANDIDATE_PLACEHOLDER in rendered:
        raise ValueError(
            "candidate placeholder remains"
        )

    return rendered


def validate_plan(
    plan: dict[str, Any],
) -> None:
    if plan["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 006 identity drift"
        )

    if plan["starting_sha"] != PLAN_STARTING_SHA:
        raise SystemExit(
            "FAIL Ontology 006 starting SHA drift"
        )

    if plan["planned_provider_requests"] != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL Ontology 006 request count drift"
        )

    if plan["planned_pairs"] != PLANNED_PAIRS:
        raise SystemExit(
            "FAIL Ontology 006 pair count drift"
        )

    requests = plan[
        "provider_request_plan"
    ]

    if len(requests) != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL Ontology 006 provider plan length drift"
        )

    if [
        int(x["ordinal"])
        for x in requests
    ] != list(
        range(1, PLANNED_REQUESTS + 1)
    ):
        raise SystemExit(
            "FAIL Ontology 006 ordinals drift"
        )

    counts = Counter(
        x["arm"]
        for x in requests
    )

    if counts != Counter({
        ARM_A: 9,
        ARM_B: 9,
    }):
        raise SystemExit(
            "FAIL Ontology 006 arm population drift"
        )

    if {
        x["specimen_id"]
        for x in requests
    } != set(SPECIMENS):
        raise SystemExit(
            "FAIL Ontology 006 specimen population drift"
        )

    for specimen_id in SPECIMENS:
        for run_index in range(1, 4):
            actual = [
                x["arm"]
                for x in requests
                if x["specimen_id"] == specimen_id
                and int(x["run_index"]) == run_index
            ]

            expected = (
                [ARM_A, ARM_B]
                if run_index % 2
                else [ARM_B, ARM_A]
            )

            if actual != expected:
                raise SystemExit(
                    "FAIL Ontology 006 paired interleaving drift: "
                    f"{specimen_id} run {run_index}"
                )

    if plan["analysis_population"] != "ONTOLOGY_006_ONLY":
        raise SystemExit(
            "FAIL Ontology 006 analysis population drift"
        )

    if plan["ontology_005_live_outputs_reused"] is not False:
        raise SystemExit(
            "FAIL Ontology 005 outputs may not be reused"
        )

    if plan["production_code_changed"] is not False:
        raise SystemExit(
            "FAIL production code must remain unchanged"
        )

    if plan["production_prompt_changed"] is not False:
        raise SystemExit(
            "FAIL production prompt must remain unchanged"
        )

    if plan["architecture_change_authorized"] is not False:
        raise SystemExit(
            "FAIL architecture change must remain unauthorized"
        )

    if (
        plan["provider_prerequisite"]["work_order"]
        != "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    ):
        raise SystemExit(
            "FAIL wrong provider qualification prerequisite"
        )

    transport = plan[
        "transport_policy"
    ]

    if (
        transport["maximum_retries_per_semantic_request"]
        != 1
    ):
        raise SystemExit(
            "FAIL retry budget drift"
        )

    if transport["retry_only_on_exact"] != {
        "error_type":
            "ModelProviderError",
        "error_message":
            "NVIDIA NIM connection timed out",
    }:
        raise SystemExit(
            "FAIL retry eligibility drift"
        )

    if (
        transport["same_model_request_object_required"]
        is not True
    ):
        raise SystemExit(
            "FAIL exact request object requirement absent"
        )

    if (
        transport["same_request_projection_sha256_required"]
        is not True
    ):
        raise SystemExit(
            "FAIL exact request hash requirement absent"
        )

    if transport["provider_call_ceiling"] != 36:
        raise SystemExit(
            "FAIL transport call ceiling drift"
        )


def prereg_context() -> StaticContext:
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise SystemExit(
            "FAIL Ontology 006 plan digest mismatch"
        )

    if sha256(PREREG_PATH) != PREREG_SHA256:
        raise SystemExit(
            "FAIL Ontology 006 preregistration digest mismatch"
        )

    if sha256(BINDING_PATH) != BINDING_SHA256:
        raise SystemExit(
            "FAIL Ontology 006 treatment binding digest mismatch"
        )

    if sha256(FREEZE_V1_PATH) != FREEZE_V1_SHA256:
        raise SystemExit(
            "FAIL Ontology 006 preregistration freeze digest mismatch"
        )

    if sha256(SOURCE005_SCRIPT) != SOURCE005_SCRIPT_SHA256:
        raise SystemExit(
            "FAIL frozen Ontology 005 instrument changed"
        )

    if sha256(SOURCE005_MANIFEST) != SOURCE005_MANIFEST_SHA256:
        raise SystemExit(
            "FAIL frozen Ontology 005 request materialization changed"
        )

    if sha256(SOURCE005_RESULT) != SOURCE005_RESULT_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 execution result changed"
        )

    if sha256(SOURCE005_ADJUDICATION) != SOURCE005_ADJUDICATION_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 adjudication changed"
        )

    if sha256(SOURCE005_LOCALIZATION) != SOURCE005_LOCALIZATION_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 regression localization changed"
        )

    if sha256(RULESET_PATH) != RULESET_SHA256:
        raise SystemExit(
            "FAIL interpretation ruleset changed"
        )

    if sha256(CORPUS_PATH) != CORPUS_SHA256:
        raise SystemExit(
            "FAIL frozen interpretation corpus changed"
        )

    plan = load_json(
        PLAN_PATH
    )

    binding = load_json(
        BINDING_PATH
    )

    freeze_v1 = load_json(
        FREEZE_V1_PATH
    )

    validate_plan(
        plan
    )

    if freeze_v1["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 006 freeze identity drift"
        )

    if freeze_v1["starting_sha"] != PLAN_STARTING_SHA:
        raise SystemExit(
            "FAIL Ontology 006 freeze starting SHA drift"
        )

    if freeze_v1["plan_sha256"] != PLAN_SHA256:
        raise SystemExit(
            "FAIL freeze v0.1 plan binding mismatch"
        )

    if (
        freeze_v1["preregistration_sha256"]
        != PREREG_SHA256
    ):
        raise SystemExit(
            "FAIL freeze v0.1 preregistration binding mismatch"
        )

    if (
        freeze_v1["treatment_binding_sha256"]
        != BINDING_SHA256
    ):
        raise SystemExit(
            "FAIL freeze v0.1 treatment binding mismatch"
        )

    if freeze_v1["planned_provider_requests"] != 18:
        raise SystemExit(
            "FAIL freeze v0.1 request population drift"
        )

    if freeze_v1["planned_pairs"] != 9:
        raise SystemExit(
            "FAIL freeze v0.1 pair population drift"
        )

    if freeze_v1["provider_call_made"] is not False:
        raise SystemExit(
            "FAIL preregistration records provider activity"
        )

    if freeze_v1["model_call_made"] is not False:
        raise SystemExit(
            "FAIL preregistration records model activity"
        )

    if freeze_v1["network_request_made"] is not False:
        raise SystemExit(
            "FAIL preregistration records network activity"
        )

    if freeze_v1["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL preregistration records live execution"
        )

    if binding["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL treatment binding identity drift"
        )

    if binding["scientific_treatment"] != (
        "RESTORE_EXISTING_ACTION_OBJECT_ROLE_SEMANTICS_ONLY"
    ):
        raise SystemExit(
            "FAIL treatment identity drift"
        )

    exclusions = binding[
        "treatment_exclusions"
    ]

    for key in (
        "candidate_normative_force_value_visible",
        "b1_output_visible",
        "gold_visible",
        "authority_metadata_visible",
        "source_identity_visible",
        "slot_applicability_by_force_visible",
        "examples_added",
        "new_ontology_rule_invented",
    ):
        if exclusions[key] is not False:
            raise SystemExit(
                f"FAIL treatment exclusion drift: {key}"
            )

    source005 = load_module(
        "_ontology005_for_006",
        SOURCE005_SCRIPT,
    )

    ctx005 = source005.prereg_context()

    source004 = ctx005.source004

    corpus = load_json(
        CORPUS_PATH
    )

    source_result = load_json(
        SOURCE005_RESULT
    )

    localization = load_json(
        SOURCE005_LOCALIZATION
    )

    if source_result["scientific_disposition"] != "REGRESSION":
        raise SystemExit(
            "FAIL predecessor is not frozen REGRESSION"
        )

    if source_result[
        "control_nonforce_b_only_slot_defect_count"
    ] != 2:
        raise SystemExit(
            "FAIL predecessor localized defect count drift"
        )

    expected_defects = [
        {
            "run_index": 1,
            "slot": "action",
            "specimen_id": "IIR-027",
        },
        {
            "run_index": 3,
            "slot": "action",
            "specimen_id": "IIR-027",
        },
    ]

    if source_result[
        "control_nonforce_b_only_slot_defect_instances"
    ] != expected_defects:
        raise SystemExit(
            "FAIL predecessor defect identity drift"
        )

    if localization["regression_class"] != (
        "STAGED_NONFORCE_CONTROL_REGRESSION"
    ):
        raise SystemExit(
            "FAIL predecessor regression class drift"
        )

    baseline = binding[
        "baseline_arm"
    ]

    treatment = binding[
        "treatment_arm"
    ]

    if hashlib.sha256(
        baseline["system_prompt"].encode("utf-8")
    ).hexdigest() != baseline["system_prompt_sha256"]:
        raise SystemExit(
            "FAIL baseline system-prompt digest drift"
        )

    if hashlib.sha256(
        treatment["system_prompt"].encode("utf-8")
    ).hexdigest() != treatment["system_prompt_sha256"]:
        raise SystemExit(
            "FAIL treatment system-prompt digest drift"
        )

    if hashlib.sha256(
        treatment["guidance_block"].encode("utf-8")
    ).hexdigest() != treatment["guidance_block_sha256"]:
        raise SystemExit(
            "FAIL guidance-block digest drift"
        )

    if (
        baseline["user_prompt_template"]
        != treatment["user_prompt_template"]
    ):
        raise SystemExit(
            "FAIL treatment changed user prompt"
        )

    if treatment["system_prompt"] != (
        baseline["system_prompt"]
        + "\n\n"
        + treatment["guidance_block"]
    ):
        raise SystemExit(
            "FAIL treatment delta is not append-only"
        )

    return StaticContext(
        plan=plan,
        binding=binding,
        source005=source005,
        ctx005=ctx005,
        source004=source004,
        corpus=corpus,
    )


def request_for(
    *,
    ctx: StaticContext,
    item: dict[str, Any],
    specimen: dict[str, Any],
) -> ModelRequest:
    arm = item[
        "arm"
    ]

    if arm == ARM_A:
        system_prompt = ctx.binding[
            "baseline_arm"
        ]["system_prompt"]

        user_template = ctx.binding[
            "baseline_arm"
        ]["user_prompt_template"]

    elif arm == ARM_B:
        system_prompt = ctx.binding[
            "treatment_arm"
        ]["system_prompt"]

        user_template = ctx.binding[
            "treatment_arm"
        ]["user_prompt_template"]

    else:
        raise ValueError(
            f"unknown Ontology 006 arm: {arm}"
        )

    source_stage = ctx.ctx005.plan004[
        "arms"
    ][
        "B_STAGED_DECOMPOSED"
    ][
        "stage_2_nonforce_slots"
    ]

    return ModelRequest(
        system_prompt=
            system_prompt,
        user_prompt=
            render_candidate(
                user_template,
                specimen["candidate"][
                    "candidate_span"
                ],
            ),
        response_format={
            "type": "json_object",
        },
        temperature=0.0,
        max_tokens=int(
            source_stage[
                "max_tokens"
            ]
        ),
    )


def semantic_materialization(
    ctx: StaticContext,
) -> list[dict[str, Any]]:
    by_id = {
        item["specimen_id"]:
            item
        for item in ctx.corpus[
            "specimens"
        ]
    }

    requests: list[dict[str, Any]] = []

    for item in ctx.plan[
        "provider_request_plan"
    ]:
        specimen = by_id[
            item["specimen_id"]
        ]

        request = request_for(
            ctx=ctx,
            item=item,
            specimen=specimen,
        )

        requests.append({
            "ordinal":
                item["ordinal"],
            "specimen_id":
                item["specimen_id"],
            "run_index":
                item["run_index"],
            "arm":
                item["arm"],
            "candidate_span":
                specimen["candidate"][
                    "candidate_span"
                ],
            "request":
                request_projection(
                    request
                ),
            "request_sha256":
                request_projection_sha256(
                    request
                ),
            "gold_label_exposed":
                False,
            "candidate_normative_force_value_exposed":
                False,
            "b1_output_exposed":
                False,
            "authority_metadata_exposed":
                False,
            "source_identity_exposed":
                False,
            "provider_constructed":
                False,
            "network_request_made":
                False,
        })

    if len(requests) != PLANNED_REQUESTS:
        raise SystemExit(
            "FAIL Ontology 006 did not materialize 18 requests"
        )

    source_manifest = load_json(
        SOURCE005_MANIFEST
    )

    source_b2 = {
        (
            item["specimen_id"],
            int(item["run_index"]),
        ): item
        for item in source_manifest[
            "requests"
        ]
        if item["stage"]
        == "B2_NONFORCE_SLOTS"
        and item["specimen_id"]
        in SPECIMENS
    }

    if len(source_b2) != 9:
        raise SystemExit(
            "FAIL source Ontology 005 control-B2 population is not 9"
        )

    baselines = [
        x
        for x in requests
        if x["arm"] == ARM_A
    ]

    if len(baselines) != 9:
        raise SystemExit(
            "FAIL Ontology 006 baseline count drift"
        )

    for current in baselines:
        old = source_b2[
            (
                current["specimen_id"],
                int(current["run_index"]),
            )
        ]

        if current["request"] != old["request"]:
            raise SystemExit(
                "FAIL Ontology 006 baseline request differs "
                "from frozen Ontology 005 B2: "
                f"{current['specimen_id']} "
                f"run {current['run_index']}"
            )

        if (
            current["request_sha256"]
            != old["request_sha256"]
        ):
            raise SystemExit(
                "FAIL Ontology 006 baseline request hash parity failure"
            )

    for specimen_id in SPECIMENS:
        for run_index in range(1, 4):
            baseline = next(
                x
                for x in requests
                if x["specimen_id"] == specimen_id
                and int(x["run_index"]) == run_index
                and x["arm"] == ARM_A
            )

            treatment = next(
                x
                for x in requests
                if x["specimen_id"] == specimen_id
                and int(x["run_index"]) == run_index
                and x["arm"] == ARM_B
            )

            a = baseline[
                "request"
            ]

            b = treatment[
                "request"
            ]

            for key in (
                "user_prompt",
                "response_format",
                "temperature",
                "max_tokens",
            ):
                if a[key] != b[key]:
                    raise SystemExit(
                        "FAIL treatment changed non-system request field: "
                        f"{specimen_id} run {run_index} {key}"
                    )

            if (
                a["system_prompt"]
                != ctx.binding[
                    "baseline_arm"
                ]["system_prompt"]
            ):
                raise SystemExit(
                    "FAIL baseline system prompt drift"
                )

            if (
                b["system_prompt"]
                != ctx.binding[
                    "treatment_arm"
                ]["system_prompt"]
            ):
                raise SystemExit(
                    "FAIL treatment system prompt drift"
                )

    return requests


def materialization_document(
    ctx: StaticContext,
) -> dict[str, Any]:
    requests = semantic_materialization(
        ctx
    )

    return {
        "work_order":
            WORK_ORDER,

        "source_work_order":
            "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005",

        "source_request_materialization_sha256":
            SOURCE005_MANIFEST_SHA256,

        "plan_sha256":
            PLAN_SHA256,

        "preregistration_sha256":
            PREREG_SHA256,

        "treatment_binding_sha256":
            BINDING_SHA256,

        "instrument_sha256":
            sha256(
                Path(__file__)
            ),

        "request_count":
            18,

        "pair_count":
            9,

        "baseline_request_count":
            9,

        "treatment_request_count":
            9,

        "baseline_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_005_B2_FOR_SELECTED_SPECIMENS",

        "treatment_delta":
            "SYSTEM_PROMPT_APPEND_FROZEN_ACTION_OBJECT_ROLE_GUIDANCE_ONLY",

        "analysis_population":
            "ONTOLOGY_006_ONLY",

        "ontology_005_live_outputs_reused":
            False,

        "provider_constructed":
            False,

        "network_request_made":
            False,

        "requests":
            requests,
    }


def write_materialization(
    ctx: StaticContext,
) -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 006 materialization already exists: "
            f"{MATERIALIZATION_PATH}"
        )

    doc = materialization_document(
        ctx
    )

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            doc,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"materialization written: {MATERIALIZATION_PATH}"
    )


def verify_materialization(
    ctx: StaticContext,
) -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit(
            "FAIL Ontology 006 request materialization absent"
        )

    actual = load_json(
        MATERIALIZATION_PATH
    )

    expected = materialization_document(
        ctx
    )

    if actual != expected:
        raise SystemExit(
            "FAIL Ontology 006 materialization differs from recomputation"
        )

    return actual


def verify_freeze_v2(
    materialization: dict[str, Any],
) -> dict[str, Any]:
    del materialization

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL Ontology 006 static freeze v0.2 absent"
        )

    freeze = load_json(
        FREEZE_V2_PATH
    )

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL freeze v0.2 identity drift"
        )

    if freeze["base_commit"] != PREREG_COMMIT:
        raise SystemExit(
            "FAIL freeze v0.2 base commit drift"
        )

    expected = {
        "plan_sha256":
            sha256(PLAN_PATH),
        "preregistration_sha256":
            sha256(PREREG_PATH),
        "treatment_binding_sha256":
            sha256(BINDING_PATH),
        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),
        "instrument_sha256":
            sha256(Path(__file__)),
        "contract_test_sha256":
            sha256(
                ROOT
                / "tests/"
                  "test_definition_ontology_"
                  "predicate_frame_discrimination_006.py"
            ),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
    }

    for key, value in expected.items():
        if freeze[key] != value:
            raise SystemExit(
                f"FAIL freeze v0.2 binding mismatch: {key}"
            )

    if freeze["request_materialization_count"] != 18:
        raise SystemExit(
            "FAIL freeze v0.2 request count drift"
        )

    if freeze["pair_count"] != 9:
        raise SystemExit(
            "FAIL freeze v0.2 pair count drift"
        )

    if freeze["instrument_implemented"] is not True:
        raise SystemExit(
            "FAIL instrument not marked implemented"
        )

    if freeze["instrument_frozen"] is not True:
        raise SystemExit(
            "FAIL instrument not marked frozen"
        )

    if freeze["transport_recovery_implemented"] is not True:
        raise SystemExit(
            "FAIL transport recovery not marked implemented"
        )

    for key in (
        "provider_call_made",
        "model_call_made",
        "network_request_made",
        "live_run_executed",
        "architecture_change_authorized",
    ):
        if freeze[key] is not False:
            raise SystemExit(
                f"FAIL static freeze state drift: {key}"
            )

    return freeze


def static_preflight() -> StaticContext:
    ctx = prereg_context()

    materialization = verify_materialization(
        ctx
    )

    verify_freeze_v2(
        materialization
    )

    return ctx


def qualification_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RECEIPT.exists():
        raise SystemExit(
            "STOP Provider Qualification 006 receipt absent; "
            "Ontology 006 live execution unauthorized"
        )

    data = load_json(
        QUALIFICATION_RECEIPT
    )

    if data.get("work_order") != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-006"
    ):
        raise SystemExit(
            "STOP wrong Provider Qualification 006 receipt"
        )

    if data.get("disposition") != "QUALIFIED":
        raise SystemExit(
            "STOP Provider Qualification 006 is not QUALIFIED"
        )

    if data.get(
        "semantic_successor_authorized"
    ) is not True:
        raise SystemExit(
            "STOP Qualification 006 did not authorize successor"
        )

    target: Any = data.get(
        "semantic_successor_target"
    )

    if isinstance(target, dict):
        target = target.get(
            "work_order"
        )

    if target != WORK_ORDER:
        raise SystemExit(
            "STOP Qualification 006 targets another work order"
        )

    return data


def bounded_provider(
    *,
    ctx: StaticContext,
    delegate: ModelProvider,
    semantic_ordinal: int,
    expected_request_sha256: str,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    return ctx.source005.TransportRecoveringProvider(
        delegate=delegate,
        semantic_ordinal=semantic_ordinal,
        expected_request_sha256=
            expected_request_sha256,
        sleep_fn=sleep_fn,
    )


def execute_request(
    *,
    ctx: StaticContext,
    item: dict[str, Any],
    specimen: dict[str, Any],
    provider: ModelProvider,
    expected_request_sha256: str,
) -> tuple[Any, list[dict[str, Any]]]:
    request = request_for(
        ctx=ctx,
        item=item,
        specimen=specimen,
    )

    bounded = bounded_provider(
        ctx=ctx,
        delegate=provider,
        semantic_ordinal=int(
            item["ordinal"]
        ),
        expected_request_sha256=
            expected_request_sha256,
    )

    attempt = ctx.source004.StageAttempt(
        ordinal=int(
            item["ordinal"]
        ),
        specimen_id=
            item["specimen_id"],
        run_index=int(
            item["run_index"]
        ),
        stage=
            item["arm"],
        outcome=
            "PROVIDER_ERROR",
    )

    try:
        response = bounded.complete(
            request
        )

    except ModelProviderError as exc:
        attempt.error_type = (
            type(exc).__name__
        )

        attempt.error_message = (
            str(exc)
        )

        return (
            attempt,
            bounded.calls,
        )

    try:
        proposal = (
            ctx.source004.parse_nonforce(
                response.content
            )
        )

    except ctx.source004.NonforceBoundaryError as exc:
        attempt.outcome = (
            "BOUNDARY_REJECTED"
        )

        attempt.error_type = (
            type(exc).__name__
        )

        attempt.error_message = (
            str(exc)
        )

    else:
        attempt.outcome = "ACCEPTED"
        attempt.proposal = proposal

        attempt.provider = (
            response.provider
        )

        attempt.model = (
            response.model
        )

        attempt.request_id = (
            response.request_id
        )

        attempt.raw_content_sha256 = (
            hashlib.sha256(
                response.content.encode(
                    "utf-8"
                )
            ).hexdigest()
        )

    return (
        attempt,
        bounded.calls,
    )


def adjudicability(
    attempts: Sequence[Any],
) -> dict[str, int | bool]:
    accepted = [
        x
        for x in attempts
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
                )
                in accepted_keys
                for arm in ARMS
            ):
                complete += 1

    gate = (
        len(attempts) == 18
        and len(accepted) == 18
        and complete == 9
    )

    return {
        "planned_provider_requests":
            18,
        "observed_attempts":
            len(attempts),
        "accepted_provider_requests":
            len(accepted),
        "complete_pairs":
            complete,
        "adjudicable":
            gate,
    }


def slot_value(
    attempt: Any,
    slot: str,
) -> str | None:
    if attempt.proposal is None:
        return None

    values = [
        item.get(
            "proposed_value"
        )
        for item in attempt.proposal.get(
            "proposed_assertions",
            [],
        )
        if item.get(
            "slot"
        ) == slot
    ]

    if len(values) != 1:
        return None

    value = values[0]

    return (
        value
        if isinstance(value, str)
        else None
    )


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
        return (
            "SUPPORTS_PREDICATE_FRAME_ROLE_GUIDANCE"
        )

    if (
        target_treatment_compatible <= 1
        and paired_improvements == 0
    ):
        return (
            "REFUTES_PREDICATE_FRAME_ROLE_GUIDANCE"
        )

    return "INCONCLUSIVE"


def analyze(
    *,
    ctx: StaticContext,
    attempts: Sequence[Any],
) -> dict[str, Any]:
    by_id = {
        item["specimen_id"]:
            item
        for item in ctx.corpus[
            "specimens"
        ]
    }

    def attempt_for(
        specimen_id: str,
        run_index: int,
        arm: str,
    ) -> Any:
        return next(
            item
            for item in attempts
            if item.specimen_id
            == specimen_id
            and int(item.run_index)
            == run_index
            and item.stage
            == arm
        )

    target_observations: list[
        dict[str, Any]
    ] = []

    treatment_compatible = 0
    paired_improvements = 0

    target_specimen = by_id[
        TARGET_SPECIMEN
    ]

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

        baseline_ok = (
            ctx.source004._single_slot_compatible(
                source=
                    ctx.ctx005.source,
                v1=
                    ctx.ctx005.v1,
                corpus=
                    ctx.corpus,
                specimen=
                    target_specimen,
                attempt=
                    baseline,
                slot=
                    TARGET_SLOT,
            )
        )

        treatment_ok = (
            ctx.source004._single_slot_compatible(
                source=
                    ctx.ctx005.source,
                v1=
                    ctx.ctx005.v1,
                corpus=
                    ctx.corpus,
                specimen=
                    target_specimen,
                attempt=
                    treatment,
                slot=
                    TARGET_SLOT,
            )
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
            "specimen_id":
                TARGET_SPECIMEN,
            "run_index":
                run_index,
            "slot":
                TARGET_SLOT,
            "expected_value":
                "consider",
            "baseline_value":
                slot_value(
                    baseline,
                    TARGET_SLOT,
                ),
            "treatment_value":
                slot_value(
                    treatment,
                    TARGET_SLOT,
                ),
            "baseline_compatible":
                baseline_ok,
            "treatment_compatible":
                treatment_ok,
            "paired_improvement":
                improvement,
        })

    safety_defects: list[
        dict[str, Any]
    ] = []

    safety_observations: list[
        dict[str, Any]
    ] = []

    for specimen_id in SPECIMENS:
        specimen = by_id[
            specimen_id
        ]

        expected_slots = [
            slot
            for slot, spec
            in specimen[
                "gold"
            ][
                "expected_slots"
            ].items()
            if (
                slot
                != "normative_force"
                and spec["status"]
                == "ESTABLISHED"
                and not (
                    specimen_id
                    == TARGET_SPECIMEN
                    and slot
                    == TARGET_SLOT
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
                    ctx.source004._single_slot_compatible(
                        source=
                            ctx.ctx005.source,
                        v1=
                            ctx.ctx005.v1,
                        corpus=
                            ctx.corpus,
                        specimen=
                            specimen,
                        attempt=
                            baseline,
                        slot=
                            slot,
                    )
                )

                treatment_ok = (
                    ctx.source004._single_slot_compatible(
                        source=
                            ctx.ctx005.source,
                        v1=
                            ctx.ctx005.v1,
                        corpus=
                            ctx.corpus,
                        specimen=
                            specimen,
                        attempt=
                            treatment,
                        slot=
                            slot,
                    )
                )

                b_only_defect = (
                    baseline_ok
                    and not treatment_ok
                )

                if b_only_defect:
                    safety_defects.append({
                        "specimen_id":
                            specimen_id,
                        "run_index":
                            run_index,
                        "slot":
                            slot,
                    })

                safety_observations.append({
                    "specimen_id":
                        specimen_id,
                    "run_index":
                        run_index,
                    "slot":
                        slot,
                    "baseline_compatible":
                        baseline_ok,
                    "treatment_compatible":
                        treatment_ok,
                    "treatment_only_defect":
                        b_only_defect,
                })

    disposition = decide(
        target_treatment_compatible=
            treatment_compatible,
        paired_improvements=
            paired_improvements,
        safety_defect_count=
            len(safety_defects),
    )

    return {
        "disposition":
            disposition,

        "target_endpoint": {
            "specimen_id":
                TARGET_SPECIMEN,
            "slot":
                TARGET_SLOT,
            "expected_value":
                "consider",
            "role_guided_compatible":
                treatment_compatible,
            "role_guided_planned":
                3,
            "paired_improvements":
                paired_improvements,
            "paired_planned":
                3,
            "observations":
                target_observations,
        },

        "safety_endpoint": {
            "role_guided_only_defect_count":
                len(
                    safety_defects
                ),
            "role_guided_only_defect_instances":
                safety_defects,
            "observations":
                safety_observations,
        },

        "provider_errors":
            sum(
                x.outcome
                == "PROVIDER_ERROR"
                for x in attempts
            ),

        "boundary_rejections":
            sum(
                x.outcome
                == "BOUNDARY_REJECTED"
                for x in attempts
            ),

        "architecture_change_authorized":
            False,

        "descriptive_only":
            True,
    }


def execute_plan(
    *,
    ctx: StaticContext,
    provider: ModelProvider,
) -> tuple[
    list[Any],
    list[dict[str, Any]],
]:
    materialized = semantic_materialization(
        ctx
    )

    expected_sha = {
        int(item["ordinal"]):
            item["request_sha256"]
        for item in materialized
    }

    by_id = {
        item["specimen_id"]:
            item
        for item in ctx.corpus[
            "specimens"
        ]
    }

    attempts: list[Any] = []
    transport_attempts: list[
        dict[str, Any]
    ] = []

    provider_plan = ctx.plan[
        "provider_request_plan"
    ]

    for index, item in enumerate(
        provider_plan
    ):
        ordinal = int(
            item["ordinal"]
        )

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
            specimen=
                by_id[
                    item[
                        "specimen_id"
                    ]
                ],
            provider=provider,
            expected_request_sha256=
                expected_sha[
                    ordinal
                ],
        )

        attempts.append(
            attempt
        )

        transport_attempts.extend(
            calls
        )

        if (
            len(transport_attempts)
            > TRANSPORT_CALL_CEILING
        ):
            raise SystemExit(
                "FAIL transport call ceiling exceeded"
            )

        print(
            f"[{ordinal:02d}/18] DONE "
            f"outcome={attempt.outcome} "
            f"transport_calls={len(calls)}",
            flush=True,
        )

        if index < len(
            provider_plan
        ) - 1:
            time.sleep(
                PACING_SECONDS
            )

    return (
        attempts,
        transport_attempts,
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
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

    args = parser.parse_args(
        argv
    )

    if (
        args.materialize
        and args.live
    ):
        raise SystemExit(
            "FAIL --materialize and --live are mutually exclusive"
        )

    if args.materialize:
        ctx = prereg_context()

        write_materialization(
            ctx
        )

        print(
            "PASS Ontology 006 materialized 18 exact requests"
        )

        print(
            "baseline requests vs Ontology 005 B2: BYTE-IDENTICAL"
        )

        print(
            "treatment delta: frozen action/object role guidance only"
        )

        print(
            "provider constructed: FALSE"
        )

        print(
            "network request made: FALSE"
        )

        return 0

    ctx = static_preflight()

    print(
        "PASS frozen Ontology 006 instrument verified"
    )

    print(
        "requests: 18 / pairs: 9"
    )

    print(
        "baseline B2 parity to Ontology 005: VERIFIED"
    )

    print(
        "treatment: frozen action/object role guidance only"
    )

    print(
        "transport recovery: inherited exact Ontology 005 envelope"
    )

    if not args.live:
        print(
            "offline preflight only; no provider was constructed "
            "and no request was made"
        )

        return 0

    qualification = (
        qualification_prerequisite()
    )

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 006 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    provider = NvidiaNimProvider(
        NvidiaNimConfig(
            model=
                DEFAULT_NIM_MODEL,
            base_url=
                DEFAULT_NIM_BASE_URL,
            timeout_seconds=
                TIMEOUT_SECONDS,
        )
    )

    attempts, transport = execute_plan(
        ctx=ctx,
        provider=provider,
    )

    gate = adjudicability(
        attempts
    )

    if bool(
        gate["adjudicable"]
    ):
        analysis = analyze(
            ctx=ctx,
            attempts=attempts,
        )

        disposition = analysis[
            "disposition"
        ]

        decision_evaluated = True

    else:
        analysis = None

        disposition = (
            "NOT_ADJUDICABLE_PROVIDER_OR_BOUNDARY_FAILURE"
        )

        decision_evaluated = False

    by_ordinal: dict[
        int,
        int
    ] = Counter(
        int(x["semantic_ordinal"])
        for x in transport
    )

    retry_cells = sorted(
        ordinal
        for ordinal, count
        in by_ordinal.items()
        if count == 2
    )

    receipt = {
        "work_order":
            WORK_ORDER,

        "preregistration_commit":
            PREREG_COMMIT,

        "plan_sha256":
            PLAN_SHA256,

        "preregistration_sha256":
            PREREG_SHA256,

        "treatment_binding_sha256":
            BINDING_SHA256,

        "instrument_freeze_sha256":
            sha256(
                FREEZE_V2_PATH
            ),

        "request_materialization_sha256":
            sha256(
                MATERIALIZATION_PATH
            ),

        "provider_qualification_006_receipt_sha256":
            sha256(
                QUALIFICATION_RECEIPT
            ),

        "provider_qualification_006_disposition":
            qualification[
                "disposition"
            ],

        "live_run_executed":
            True,

        "analysis_population":
            "ONTOLOGY_006_ONLY",

        "ontology_005_live_outputs_reused":
            False,

        "attempts": [
            item.to_json()
            for item in attempts
        ],

        "transport_attempts":
            transport,

        "transport_calls_observed":
            len(
                transport
            ),

        "transport_call_ceiling":
            36,

        "transport_retries_used":
            len(
                retry_cells
            ),

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
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"receipt written: {RECEIPT_PATH}"
    )

    print(
        f"scientific disposition: {disposition}"
    )

    print(
        "semantic decision evaluated: "
        f"{decision_evaluated}"
    )

    print(
        "architecture change authorization: FALSE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
