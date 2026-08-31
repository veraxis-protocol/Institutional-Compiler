from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/characterize_definition_ontology_discrimination_003.py"


def load_instrument() -> ModuleType:
    name = "_test_definition_ontology_003"

    spec = importlib.util.spec_from_file_location(name, SCRIPT)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def test_force_only_contract_accepts_exact_allowed_label() -> None:
    module = load_instrument()

    assert (
        module.parse_force_only('{"normative_force":"CONSTITUTIVE_DEFINITION"}')
        == "CONSTITUTIVE_DEFINITION"
    )


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"normative_force":"CONSTITUTIVE_DEFINITION","extra":1}',
        '{"normative_force":"UNKNOWN"}',
        '{"normative_force":null}',
    ],
)
def test_force_only_contract_rejects_drift(content: str) -> None:
    module = load_instrument()

    with pytest.raises(module.ForceOnlyBoundaryError):
        module.parse_force_only(content)


def test_preregistered_decision_rule() -> None:
    module = load_instrument()

    assert (
        module.decide(
            b_primary_correct=9,
            b_primary_improvements=2,
            a_primary_improvements=0,
            b_only_control_defects=0,
        )
        == "SUPPORTS_TASK_INTERFERENCE_HYPOTHESIS"
    )

    assert (
        module.decide(
            b_primary_correct=9,
            b_primary_improvements=2,
            a_primary_improvements=0,
            b_only_control_defects=1,
        )
        == "REGRESSION"
    )

    assert (
        module.decide(
            b_primary_correct=7,
            b_primary_improvements=0,
            a_primary_improvements=2,
            b_only_control_defects=0,
        )
        == "REFUTES_FORCE_ONLY_ADVANTAGE"
    )

    assert (
        module.decide(
            b_primary_correct=7,
            b_primary_improvements=1,
            a_primary_improvements=0,
            b_only_control_defects=0,
        )
        == "INCONCLUSIVE"
    )


def test_frozen_request_plan_and_static_preflight() -> None:
    module = load_instrument()

    plan, _source, _v2, _v1 = module.preflight()

    assert plan["planned_requests"] == 36
    assert plan["planned_pairs"] == 18

    arms = [item["arm"] for item in plan["request_plan"]]

    assert arms.count(module.ARM_A) == 18
    assert arms.count(module.ARM_B) == 18


def test_offline_main_makes_no_live_execution() -> None:
    module = load_instrument()

    assert module.main([]) == 0
