from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_syntactic_predicate_carrier_discrimination_007.py"
)

MODULE_NAME = "_test_ontology_007"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


def load(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def test_identity_and_population() -> None:
    ctx = module.prereg_context()

    assert module.WORK_ORDER == (
        "OIC-DEFINITION-ONTOLOGY-SYNTACTIC-PREDICATE-CARRIER-DISCRIMINATION-007"
    )

    assert ctx.plan["planned_provider_requests"] == 18
    assert ctx.plan["planned_pairs"] == 9

    assert module.SPECIMENS == (
        "IIR-006",
        "IIR-027",
        "IIR-028",
    )


def test_arm_a_exact_frozen_o006_role_guided_parity() -> None:
    ctx = module.prereg_context()

    rows = module.semantic_materialization(ctx)

    old = load(module.SOURCE_MANIFEST)

    source = {
        (
            x["specimen_id"],
            int(x["run_index"]),
        ): x
        for x in old["requests"]
        if x["arm"] == "B_ROLE_GUIDED_B2"
        and x["specimen_id"] in module.SPECIMENS
    }

    arm_a = [
        x for x in rows
        if x["arm"] == module.ARM_A
    ]

    assert len(arm_a) == 9

    for current in arm_a:
        frozen = source[
            (
                current["specimen_id"],
                current["run_index"],
            )
        ]

        assert current["request"] == frozen["request"]
        assert current["request_sha256"] == frozen["request_sha256"]


def test_arm_b_is_exact_single_suffix_delta() -> None:
    ctx = module.prereg_context()

    rows = module.semantic_materialization(ctx)

    guidance = ctx.binding["arm_b"]["appended_text"]

    for specimen_id in module.SPECIMENS:
        for run_index in range(1, 4):
            a = next(
                x for x in rows
                if x["specimen_id"] == specimen_id
                and x["run_index"] == run_index
                and x["arm"] == module.ARM_A
            )

            b = next(
                x for x in rows
                if x["specimen_id"] == specimen_id
                and x["run_index"] == run_index
                and x["arm"] == module.ARM_B
            )

            assert b["request"]["system_prompt"] == (
                a["request"]["system_prompt"] + guidance
            )

            for key in (
                "user_prompt",
                "response_format",
                "temperature",
                "max_tokens",
            ):
                assert a["request"][key] == b["request"][key]


def test_materialization_exact() -> None:
    ctx = module.prereg_context()

    actual = load(module.MATERIALIZATION_PATH)

    assert actual == module.materialization_document(ctx)

    assert actual["request_count"] == 18
    assert actual["pair_count"] == 9
    assert actual["arm_a_request_count"] == 9
    assert actual["arm_b_request_count"] == 9

    assert actual["arm_a_equivalence"] == (
        "BYTE_IDENTICAL_TO_FROZEN_O006_B_ROLE_GUIDED_B2"
    )

    assert actual["arm_b_delta"] == (
        "SYSTEM_PROMPT_APPEND_FROZEN_SYNTACTIC_CARRIER_GUIDANCE_ONLY"
    )


def test_frozen_guidance_is_experimental_only() -> None:
    ctx = module.prereg_context()

    binding = ctx.binding
    guidance = binding["arm_b"]["appended_text"]

    assert binding["experimental_guidance_only"] is True
    assert binding["registered_interpretation_rule"] is False
    assert binding["production_ruleset_modified"] is False

    assert "lexical verbal head" in guidance
    assert "nominalized event" in guidance
    assert "Do not infer or emit normative force." in guidance


def test_decision_support() -> None:
    assert module.decide(
        target_treatment_compatible=3,
        paired_improvements=2,
        safety_defect_count=0,
    ) == "SUPPORTS_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"


def test_decision_refutation() -> None:
    assert module.decide(
        target_treatment_compatible=1,
        paired_improvements=0,
        safety_defect_count=0,
    ) == "REFUTES_SYNTACTIC_PREDICATE_CARRIER_HYPOTHESIS"


def test_decision_regression_precedence() -> None:
    assert module.decide(
        target_treatment_compatible=3,
        paired_improvements=3,
        safety_defect_count=1,
    ) == "REGRESSION"


def test_decision_inconclusive() -> None:
    assert module.decide(
        target_treatment_compatible=2,
        paired_improvements=1,
        safety_defect_count=0,
    ) == "INCONCLUSIVE"


def test_q009_is_only_future_live_gate() -> None:
    ctx = module.prereg_context()

    assert ctx.plan["provider_prerequisite"]["work_order"] == (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-009"
    )

    assert ctx.plan["provider_prerequisite"][
        "qualification_009_created"
    ] is False

    assert ctx.plan["ontology_007_execution_authorized"] is False


def test_static_preflight_does_not_require_q009() -> None:
    assert not module.QUALIFICATION_RESULT.exists()

    ctx = module.static_preflight()

    assert ctx.plan["live_run_executed"] is False
    assert ctx.plan["ontology_007_execution_authorized"] is False


def test_live_gate_precedes_provider_construction() -> None:
    text = SCRIPT.read_text(
        encoding="utf-8"
    )

    qpos = text.index(
        "qualification = qualification_prerequisite()"
    )

    ppos = text.index(
        "provider = NvidiaNimProvider(",
        qpos,
    )

    assert qpos < ppos


def test_no_production_or_architecture_change() -> None:
    ctx = module.prereg_context()
    freeze = module.verify_freeze_v2()

    assert ctx.plan["production_interpretation_ruleset_changed"] is False
    assert ctx.plan["production_code_changed"] is False
    assert ctx.plan["architecture_change_authorized"] is False

    assert freeze["production_interpretation_ruleset_changed"] is False
    assert freeze["architecture_change_authorized"] is False
    assert freeze["live_run_executed"] is False
    assert freeze["ontology_007_execution_authorized"] is False
