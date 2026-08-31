from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from oic.model_provider import ModelRequest, ModelResponse

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts/characterize_definition_ontology_discrimination_003a.py"


def load_instrument() -> ModuleType:
    name = "_test_oic_definition_ontology_003a"

    spec = importlib.util.spec_from_file_location(name, SCRIPT)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def raw_materialization(
    module: ModuleType,
) -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
]:
    plan = module.load_plan()
    source = module.load_source()
    v2 = source.load_v2()
    v1 = v2.load_v1()

    corpus = json.loads(module.SOURCE_CORPUS.read_text(encoding="utf-8"))

    requests = module.materialize_requests(
        plan=plan,
        corpus=corpus,
        source=source,
        v2=v2,
        v1=v1,
    )

    return plan, corpus, requests


class CaptureProvider:
    def __init__(self) -> None:
        self.request: ModelRequest | None = None

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.request = request

        return ModelResponse(
            provider="offline-capture",
            model="offline-capture",
            content=('{"proposed_assertions":[],"proposed_unresolved_references":[]}'),
            request_id="offline-capture",
            raw={},
        )


def test_force_only_renderer_preserves_literal_json() -> None:
    module = load_instrument()
    plan = module.load_plan()

    template = plan["arms"][module.ARM_B]["user_prompt_template"]

    rendered = module.render_force_only_user_prompt(
        template,
        "Synthetic admitted proposition.",
    )

    assert module.CANDIDATE_PLACEHOLDER not in rendered
    assert rendered.count(module.FORCE_ONLY_LITERAL_JSON) == 1

    assert '{"normative_force":"<ONE_ALLOWED_LABEL>"}' in rendered


def test_all_36_exact_requests_materialize_offline() -> None:
    module = load_instrument()
    plan, _, requests = raw_materialization(module)

    assert len(requests) == 36

    assert sum(item["arm"] == module.ARM_A for item in requests) == 18

    assert sum(item["arm"] == module.ARM_B for item in requests) == 18

    identities = [
        {
            "ordinal": item["ordinal"],
            "specimen_id": item["specimen_id"],
            "run_index": item["run_index"],
            "arm": item["arm"],
        }
        for item in requests
    ]

    assert identities == plan["request_plan"]

    for item in requests:
        request = item["request"]

        assert module.CANDIDATE_PLACEHOLDER not in request["user_prompt"]

        assert item["candidate_span"] in request["user_prompt"]

        if item["arm"] == module.ARM_B:
            assert request["user_prompt"].count(module.FORCE_ONLY_LITERAL_JSON) == 1


def test_candidate_specific_admission_metadata_is_absent() -> None:
    module = load_instrument()
    _, corpus, requests = raw_materialization(module)

    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}

    forbidden_gold_schema_tokens = (
        "expected_force",
        "expected_slots",
        "exception_closure",
        "expected_unresolved_references",
        "gold_is_evaluator_only",
    )

    for item in requests:
        specimen = by_id[item["specimen_id"]]

        prompt = item["request"]["system_prompt"] + "\n" + item["request"]["user_prompt"]

        lowered = prompt.lower()

        for token in forbidden_gold_schema_tokens:
            assert token not in lowered

        admission = specimen["admission"]

        for key in (
            "admission_receipt_id",
            "candidate_projection_digest",
            "candidate_unit_id",
            "evaluation_time",
            "reason_code",
            "source_digest",
            "source_id",
            "source_version",
        ):
            value = admission.get(key)

            if isinstance(value, str) and len(value) >= 8:
                assert value not in prompt


def test_live_arm_a_request_matches_offline_materialization() -> None:
    module = load_instrument()

    plan = module.load_plan()
    source = module.load_source()
    v2 = source.load_v2()
    v1 = v2.load_v1()

    corpus = json.loads(module.SOURCE_CORPUS.read_text(encoding="utf-8"))

    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}

    for planned in plan["request_plan"]:
        if planned["arm"] != module.ARM_A:
            continue

        specimen = by_id[planned["specimen_id"]]

        expected = module.combined_request(
            specimen=specimen,
            source=source,
            v2=v2,
            v1=v1,
        )

        capture = CaptureProvider()

        guarded = module.ExactRequestProvider(
            delegate=capture,
            expected=expected,
        )

        v2.propose_with_prompt(
            binding=source._binding(v1, specimen),
            user_prompt=source.arm_b_user_prompt(
                v2,
                v1,
                specimen,
            ),
            provider=guarded,
            proposer_id=("oic-definition-ontology-discrimination-003a-combined"),
        )

        assert capture.request == expected


def test_frozen_manifest_recomputes_exactly() -> None:
    module = load_instrument()

    plan, source, v2, v1 = module.preflight()

    corpus = json.loads(module.SOURCE_CORPUS.read_text(encoding="utf-8"))

    recomputed = module.materialize_requests(
        plan=plan,
        corpus=corpus,
        source=source,
        v2=v2,
        v1=v1,
    )

    manifest = json.loads(module.MATERIALIZATION_PATH.read_text(encoding="utf-8"))

    assert manifest["request_count"] == 36
    assert manifest["arm_a_count"] == 18
    assert manifest["arm_b_count"] == 18

    assert manifest["provider_constructed"] is False
    assert manifest["network_request_made"] is False
    assert manifest["model_call_made"] is False

    assert manifest["requests"] == recomputed


def test_offline_main_constructs_no_provider() -> None:
    module = load_instrument()

    assert module.main([]) == 0
