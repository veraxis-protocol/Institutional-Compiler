from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

from oic.model_provider import (
    ModelProviderError,
    ModelResponse,
)

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts/"
      "characterize_definition_ontology_"
      "predicate_frame_discrimination_006.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "_ontology006_contract",
        SCRIPT,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        "_ontology006_contract"
    ] = module

    try:
        spec.loader.exec_module(
            module
        )
    finally:
        sys.modules.pop(
            "_ontology006_contract",
            None,
        )

    return module


# Import the experimental module once during pytest collection.
# This keeps stdlib/network-module import timing outside test-time
# socket isolation while making no provider or network call.
_ONTOLOGY006 = load_module()


def test_materializes_exact_18_request_population() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    items = mod.semantic_materialization(
        ctx
    )

    assert len(items) == 18

    assert Counter(
        x["arm"]
        for x in items
    ) == Counter({
        mod.ARM_A: 9,
        mod.ARM_B: 9,
    })

    assert {
        x["specimen_id"]
        for x in items
    } == {
        "IIR-006",
        "IIR-027",
        "IIR-028",
    }

    assert [
        int(x["ordinal"])
        for x in items
    ] == list(
        range(1, 19)
    )


def test_baseline_is_byte_identical_to_frozen_005_b2() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    current = mod.semantic_materialization(
        ctx
    )

    source = json.loads(
        mod.SOURCE005_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    old = {
        (
            x["specimen_id"],
            int(x["run_index"]),
        ): x
        for x in source["requests"]
        if (
            x["stage"]
            == "B2_NONFORCE_SLOTS"
            and x["specimen_id"]
            in mod.SPECIMENS
        )
    }

    assert len(old) == 9

    for item in current:
        if item["arm"] != mod.ARM_A:
            continue

        previous = old[
            (
                item["specimen_id"],
                int(
                    item["run_index"]
                ),
            )
        ]

        assert item[
            "request"
        ] == previous[
            "request"
        ]

        assert item[
            "request_sha256"
        ] == previous[
            "request_sha256"
        ]


def test_treatment_delta_is_system_prompt_only() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    items = mod.semantic_materialization(
        ctx
    )

    for specimen_id in mod.SPECIMENS:
        for run_index in range(1, 4):
            baseline = next(
                x
                for x in items
                if x["specimen_id"]
                == specimen_id
                and int(
                    x["run_index"]
                ) == run_index
                and x["arm"]
                == mod.ARM_A
            )

            treatment = next(
                x
                for x in items
                if x["specimen_id"]
                == specimen_id
                and int(
                    x["run_index"]
                ) == run_index
                and x["arm"]
                == mod.ARM_B
            )

            a = baseline["request"]
            b = treatment["request"]

            assert (
                b["system_prompt"]
                == (
                    a["system_prompt"]
                    + "\n\n"
                    + ctx.binding[
                        "treatment_arm"
                    ][
                        "guidance_block"
                    ]
                )
            )

            for key in (
                "user_prompt",
                "response_format",
                "temperature",
                "max_tokens",
            ):
                assert (
                    a[key]
                    == b[key]
                )


def test_treatment_exposes_no_gold_force_or_b1_output() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    exclusions = ctx.binding[
        "treatment_exclusions"
    ]

    assert exclusions[
        "candidate_normative_force_value_visible"
    ] is False

    assert exclusions[
        "b1_output_visible"
    ] is False

    assert exclusions[
        "gold_visible"
    ] is False

    assert exclusions[
        "examples_added"
    ] is False

    assert exclusions[
        "new_ontology_rule_invented"
    ] is False

    treatment = ctx.binding[
        "treatment_arm"
    ]["system_prompt"]

    assert "ADVISORY" not in treatment
    assert "IIR-027" not in treatment
    assert "consider" not in treatment


def test_nonforce_boundary_still_rejects_normative_force() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    with pytest.raises(
        ctx.source004.NonforceBoundaryError
    ):
        ctx.source004.parse_nonforce(
            json.dumps({
                "proposed_assertions": [
                    {
                        "slot":
                            "normative_force",
                        "proposed_value":
                            "ADVISORY",
                        "proposed_source_quote":
                            None,
                    }
                ],
                "proposed_unresolved_references":
                    [],
            })
        )


def test_exact_timeout_transport_retry_is_inherited() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    materialized = (
        mod.semantic_materialization(
            ctx
        )
    )

    item = materialized[0]

    plan_item = ctx.plan[
        "provider_request_plan"
    ][0]

    specimen = next(
        x
        for x in ctx.corpus["specimens"]
        if x["specimen_id"]
        == plan_item["specimen_id"]
    )

    request = mod.request_for(
        ctx=ctx,
        item=plan_item,
        specimen=specimen,
    )

    class Delegate:
        def __init__(self):
            self.calls = 0
            self.ids = []

        def complete(self, req):
            self.calls += 1
            self.ids.append(
                id(req)
            )

            if self.calls == 1:
                raise ModelProviderError(
                    "NVIDIA NIM connection timed out"
                )

            return ModelResponse(
                provider="test",
                model="test",
                content=(
                    '{"proposed_assertions":[],'
                    '"proposed_unresolved_references":[]}'
                ),
                request_id="req-2",
                raw={},
            )

    delegate = Delegate()

    bounded = mod.bounded_provider(
        ctx=ctx,
        delegate=delegate,
        semantic_ordinal=1,
        expected_request_sha256=
            item["request_sha256"],
        sleep_fn=lambda _: None,
    )

    response = bounded.complete(
        request
    )

    assert response.request_id == "req-2"
    assert delegate.calls == 2
    assert len(set(delegate.ids)) == 1
    assert len(bounded.calls) == 2

    assert bounded.calls[0][
        "outcome"
    ] == "PROVIDER_ERROR"

    assert bounded.calls[0][
        "error_type"
    ] == "ModelProviderError"

    assert bounded.calls[0][
        "error_message"
    ] == "NVIDIA NIM connection timed out"

    assert bounded.calls[1][
        "outcome"
    ] == "ACCEPTED"

    assert (
        bounded.calls[0][
            "request_projection_sha256"
        ]
        == bounded.calls[1][
            "request_projection_sha256"
        ]
        == item[
            "request_sha256"
        ]
    )


def test_noneligible_provider_error_is_not_retried() -> None:
    mod = _ONTOLOGY006
    ctx = mod.prereg_context()

    materialized = (
        mod.semantic_materialization(
            ctx
        )
    )

    item = materialized[0]

    plan_item = ctx.plan[
        "provider_request_plan"
    ][0]

    specimen = next(
        x
        for x in ctx.corpus["specimens"]
        if x["specimen_id"]
        == plan_item["specimen_id"]
    )

    request = mod.request_for(
        ctx=ctx,
        item=plan_item,
        specimen=specimen,
    )

    class Delegate:
        def __init__(self):
            self.calls = 0

        def complete(self, req):
            del req
            self.calls += 1

            raise ModelProviderError(
                "different provider error"
            )

    delegate = Delegate()

    bounded = mod.bounded_provider(
        ctx=ctx,
        delegate=delegate,
        semantic_ordinal=1,
        expected_request_sha256=
            item["request_sha256"],
        sleep_fn=lambda _: None,
    )

    with pytest.raises(
        ModelProviderError,
        match="different provider error",
    ):
        bounded.complete(
            request
        )

    assert delegate.calls == 1
    assert len(bounded.calls) == 1


def test_decision_rule_precedence() -> None:
    mod = _ONTOLOGY006

    assert mod.decide(
        target_treatment_compatible=3,
        paired_improvements=3,
        safety_defect_count=1,
    ) == "REGRESSION"

    assert mod.decide(
        target_treatment_compatible=3,
        paired_improvements=2,
        safety_defect_count=0,
    ) == (
        "SUPPORTS_PREDICATE_FRAME_ROLE_GUIDANCE"
    )

    assert mod.decide(
        target_treatment_compatible=1,
        paired_improvements=0,
        safety_defect_count=0,
    ) == (
        "REFUTES_PREDICATE_FRAME_ROLE_GUIDANCE"
    )

    assert mod.decide(
        target_treatment_compatible=2,
        paired_improvements=1,
        safety_defect_count=0,
    ) == "INCONCLUSIVE"
