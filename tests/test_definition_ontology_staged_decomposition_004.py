from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts/characterize_definition_ontology_staged_decomposition_004.py"


def load_instrument() -> ModuleType:
    name = "_test_ontology_staged_decomposition_004"

    spec = importlib.util.spec_from_file_location(
        name,
        SCRIPT,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


def materialized(module: ModuleType) -> list[dict[str, object]]:
    plan = module.load_plan()

    (
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    ) = module.load_context()

    return module.materialize_requests(
        plan=plan,
        corpus=corpus,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )


def test_all_54_requests_materialize_offline() -> None:
    module = load_instrument()

    requests = materialized(module)

    assert len(requests) == 54

    assert sum(item["stage"] == module.STAGE_A for item in requests) == 18

    assert sum(item["stage"] == module.STAGE_B1 for item in requests) == 18

    assert sum(item["stage"] == module.STAGE_B2 for item in requests) == 18

    assert all(item["provider_constructed"] is False for item in requests)

    assert all(item["network_request_made"] is False for item in requests)


def test_a_and_b1_requests_are_exact_003a_requests() -> None:
    module = load_instrument()

    requests = materialized(module)

    module.verify_predecessor_request_parity(requests)


def test_b2_renderer_survives_literal_json_braces() -> None:
    module = load_instrument()

    plan = module.load_plan()

    template = plan["arms"]["B_STAGED_DECOMPOSED"]["stage_2_nonforce_slots"]["user_prompt_template"]

    with pytest.raises(KeyError):
        template.format(candidate_span="test")

    rendered = module.render_candidate_prompt(
        template,
        "test",
    )

    assert module.CANDIDATE_PLACEHOLDER not in rendered
    assert "ADMITTED PROPOSITION:\ntest" in rendered


def test_b2_contract_rejects_normative_force() -> None:
    module = load_instrument()

    with pytest.raises(module.NonforceBoundaryError):
        module.parse_nonforce(
            json.dumps(
                {
                    "proposed_assertions": [
                        {
                            "slot": "normative_force",
                            "proposed_value": "OBLIGATION",
                            "proposed_source_quote": None,
                        }
                    ],
                    "proposed_unresolved_references": [],
                }
            )
        )


def test_b2_is_independent_of_b1_output() -> None:
    module = load_instrument()

    plan = module.load_plan()

    stage2 = plan["arms"]["B_STAGED_DECOMPOSED"]["stage_2_nonforce_slots"]

    assert stage2["consumes_stage_1_output"] is False
    assert "normative_force" not in stage2["allowed_slots"]

    merge = plan["arms"]["B_STAGED_DECOMPOSED"]["deterministic_merge"]

    assert merge["provider_call"] is False
    assert merge["model_may_merge_or_rewrite"] is False


def test_frozen_manifest_recomputes_exactly() -> None:
    module = load_instrument()

    (
        plan,
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    ) = module.preflight()

    recomputed = module.materialize_requests(
        plan=plan,
        corpus=corpus,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )

    manifest = json.loads(module.MATERIALIZATION_PATH.read_text(encoding="utf-8"))

    assert manifest["request_count"] == 54
    assert manifest["a_count"] == 18
    assert manifest["b1_count"] == 18
    assert manifest["b2_count"] == 18

    assert manifest["provider_constructed"] is False
    assert manifest["network_request_made"] is False
    assert manifest["model_call_made"] is False

    assert manifest["requests"] == recomputed


def test_offline_main_constructs_no_provider() -> None:
    module = load_instrument()

    assert module.main([]) == 0
