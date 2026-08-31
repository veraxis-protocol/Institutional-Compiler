"""Offline contract and mutation tests for Unit-Type A/B 001."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from oic.interpretation_proposal import propose_interpretation
from oic.model_provider import ModelRequest, ModelResponse

pytestmark = pytest.mark.contract

PLAN = Path("benchmarks/characterization/interpretation-proposal-unit-type-ab-001/PLAN-v0.1.json")
FREEZE = Path(
    "benchmarks/characterization/interpretation-proposal-unit-type-ab-001/PLAN-FREEZE-v0.1.json"
)
CORPUS = Path("benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json")
SCRIPT = Path("scripts/characterize_interpretation_proposal_unit_type_ab.py")
PHASE_A_SHA = "20399bd98b2702b077c0874d36fce7f3fbb45a7f"
UNIT_TYPE_PHASE_END_SHA = "f060dc60620c5ee4f72be7846915b80872afa00f"
PLAN_SHA = "134173f2314d66a943ebe1f35e3b00c124b731433a693de6138bfdc0b248f1d4"
CORPUS_SHA = "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
PRODUCTION_SHA = "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"


def _load_script(repo_root: Path) -> ModuleType:
    path = repo_root / SCRIPT
    spec = importlib.util.spec_from_file_location("_unit_type_ab", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _load_script(repo_root)


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((repo_root / CORPUS).read_text(encoding="utf-8"))
    return value


@pytest.fixture(scope="module")
def plan(repo_root: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((repo_root / PLAN).read_text(encoding="utf-8"))
    return value


class RecordingProvider:
    def __init__(self, content: str = '{"proposed_assertions":[]}') -> None:
        self.calls: list[ModelRequest] = []
        self.content = content

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        return ModelResponse(
            provider="fake",
            model="fake",
            content=self.content,
            request_id=None,
            raw={},
        )


def _request(harness: ModuleType, specimen: dict[str, Any], arm: str) -> ModelRequest:
    provider = RecordingProvider()
    propose_interpretation(
        binding=harness.binding_for(specimen, arm),
        provider=provider,
        proposer_id="ab-contract-test",
    )
    return provider.calls[0]


def test_phase_b_starts_at_phase_a_final(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE_A_SHA, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    assert result.returncode == 0


def test_source_corpus_and_production_are_byte_frozen(repo_root: Path) -> None:
    assert hashlib.sha256((repo_root / CORPUS).read_bytes()).hexdigest() == CORPUS_SHA
    assert (
        hashlib.sha256((repo_root / "src/oic/interpretation_proposal.py").read_bytes()).hexdigest()
        == PRODUCTION_SHA
    )


def test_plan_and_freeze_are_exact(repo_root: Path, plan: dict[str, Any]) -> None:
    freeze = json.loads((repo_root / FREEZE).read_text(encoding="utf-8"))
    assert hashlib.sha256((repo_root / PLAN).read_bytes()).hexdigest() == PLAN_SHA
    assert freeze["plan_sha256"] == PLAN_SHA
    assert freeze["plan_bytes"] == (repo_root / PLAN).stat().st_size == 27511
    assert plan["source_corpus_sha256"] == freeze["source_corpus_sha256"] == CORPUS_SHA
    assert freeze["model_call_made"] is False


def test_exact_29_by_3_by_2_plan_and_deterministic_interleaving(
    harness: ModuleType, corpus: dict[str, Any], plan: dict[str, Any]
) -> None:
    assert plan["specimen_count"] == 29
    assert plan["runs_per_specimen"] == 3
    assert plan["planned_requests"] == 174
    materialized = harness.build_plan(corpus)
    harness.validate_plan(corpus, materialized)
    assert [item.to_json() for item in materialized] == plan["request_plan"]
    assert plan["interleaving"] == (
        "odd run A then B; even run B then A within each specimen/run pair"
    )


def test_interleaving_mutation_is_caught(harness: ModuleType, corpus: dict[str, Any]) -> None:
    materialized = list(harness.build_plan(corpus))
    first, second = materialized[:2]
    materialized[0] = harness.PlannedRequest(
        first.ordinal, first.specimen_id, first.run_index, second.arm
    )
    materialized[1] = harness.PlannedRequest(
        second.ordinal, second.specimen_id, second.run_index, first.arm
    )
    with pytest.raises(ValueError, match="arm order"):
        harness.validate_plan(corpus, materialized)


def test_missing_arm_mutation_is_caught(harness: ModuleType, corpus: dict[str, Any]) -> None:
    materialized = list(harness.build_plan(corpus))[:-1]
    with pytest.raises(ValueError, match="exactly 174"):
        harness.validate_plan(corpus, materialized)


def test_only_prompt_difference_is_existing_unit_type_hint(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    specimen = corpus["specimens"][0]
    arm_a = _request(harness, specimen, harness.ARMS[0])
    arm_b = _request(harness, specimen, harness.ARMS[1])
    unit_type = specimen["candidate"]["unit_type"]
    exact_delta = (
        "\n\nAn earlier stage proposed the provisional, uncertain type "
        f"{unit_type!r} for this proposition. It is another model's guess, it carries no "
        "authority, and it may be wrong. Do not treat it as the normative force."
    )
    assert arm_a.system_prompt == arm_b.system_prompt
    assert exact_delta not in arm_a.user_prompt
    assert exact_delta in arm_b.user_prompt
    assert arm_b.user_prompt.replace(exact_delta, "") == arm_a.user_prompt
    assert arm_a.response_format == arm_b.response_format
    assert arm_a.temperature == arm_b.temperature == 0.0
    assert arm_a.max_tokens == arm_b.max_tokens


def test_hint_is_explicitly_untrusted_non_authoritative_and_subordinate(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    request = _request(harness, corpus["specimens"][0], harness.ARMS[1])
    rendered = (request.system_prompt + "\n" + request.user_prompt).casefold()
    for phrase in (
        "provisional and untrusted",
        "earlier stage",
        "another model's guess",
        "carries no authority",
        "may be wrong",
        "suggestion, not a finding",
        "inspect only the proposition supplied",
    ):
        assert phrase in rendered


def test_gold_and_authority_metadata_cannot_change_the_prompt(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    first = corpus["specimens"][0]
    mutated = copy.deepcopy(first)
    mutated["gold"] = {"SECRET_ANSWER_KEY": "ALLOW WITH WARRANT"}
    mutated["admission"]["reason_code"] = "SECRET-REASON"
    for arm in harness.ARMS:
        assert _request(harness, first, arm) == _request(harness, mutated, arm)


def test_definition_primary_diagnostic_has_all_18_observations(plan: dict[str, Any]) -> None:
    diagnostic = plan["definition_primary_diagnostic"]
    assert diagnostic["specimen_ids"] == ["IIR-005", "IIR-023", "IIR-024"]
    assert diagnostic["observation_count"] == len(diagnostic["observations"]) == 18
    assert {
        (item["specimen_id"], item["run_index"], item["arm"]) for item in diagnostic["observations"]
    } == {
        (specimen, run, arm)
        for specimen in diagnostic["specimen_ids"]
        for run in (1, 2, 3)
        for arm in plan["arms"]
    }


def test_regression_sentinels_and_corrected_metrics_are_complete(plan: dict[str, Any]) -> None:
    assert len(plan["regression_sentinels"]) == 14
    assert set(plan["corrected_paired_metrics"]) == {
        "force_paired_outcomes",
        "definition_force_paired_outcomes",
        "unsupported_semantic_assignments",
        "wrong_role_assignments",
        "established_slot_compatibility",
        "bearer_counterparty_swaps",
        "material_omissions",
        "material_wrong_slot_placements",
        "threshold_comparator_loss",
        "exception_preservation",
        "condition_preservation",
        "source_quote_grounding",
        "unresolved_reference_surfacing_and_kind",
        "semantic_strengthening_instances",
        "ambiguity_collapse",
        "semantic_hash_stability",
        "slot_set_stability",
    }


def test_paired_defect_cells_are_computed_without_aggregation_bias(
    harness: ModuleType,
) -> None:
    attempts = [
        harness.Attempt(index, "X", index, arm, "ACCEPTED")
        for index, arm in enumerate((harness.ARMS[0], harness.ARMS[1]), 1)
    ]
    defects = {("X", 1, harness.ARMS[0]): True, ("X", 1, harness.ARMS[1]): False}
    # Normalize the deliberately synthetic pair to the same run index.
    attempts[1].run_index = 1
    assert harness.paired_outcomes(attempts, defects) == {
        "A_ONLY_DEFECT": 1,
        "B_ONLY_DEFECT": 0,
        "BOTH_DEFECT": 0,
        "NEITHER_DEFECT": 0,
    }


def test_primary_definition_analysis_remains_paired(
    harness: ModuleType, corpus: dict[str, Any]
) -> None:
    specimen = next(item for item in corpus["specimens"] if item["specimen_id"] == "IIR-005")
    proposals: list[dict[str, Any]] = []
    for arm, content in (
        (harness.ARMS[0], '{"proposed_assertions":[]}'),
        (
            harness.ARMS[1],
            '{"proposed_assertions":[{"slot":"normative_force",'
            '"proposed_value":"CONSTITUTIVE_DEFINITION",'
            '"proposed_source_quote":"means"}]}',
        ),
    ):
        result = propose_interpretation(
            binding=harness.binding_for(specimen, arm),
            provider=RecordingProvider(content),
            proposer_id="analysis-test",
        )
        proposals.append(result.proposal)
    attempts = [
        harness.Attempt(1, "IIR-005", 1, harness.ARMS[0], "ACCEPTED", proposals[0]),
        harness.Attempt(2, "IIR-005", 1, harness.ARMS[1], "ACCEPTED", proposals[1]),
    ]
    result = harness.analyze_attempts(corpus, attempts)
    assert [item["category"] for item in result["definition_primary_diagnostic"]] == [
        "FORCE_OMITTED",
        "CONSTITUTIVE_DEFINITION_PROPOSED",
    ]
    assert result["definition_paired_defect_cells"] == {
        "A_ONLY_DEFECT": 1,
        "B_ONLY_DEFECT": 0,
        "BOTH_DEFECT": 0,
        "NEITHER_DEFECT": 0,
    }


def test_offline_preflight_constructs_no_provider_or_receipt(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, harness: ModuleType
) -> None:
    monkeypatch.setattr(harness, "RECEIPT_PATH", repo_root / ".local/should-not-exist.json")
    assert harness.main([]) == 0
    assert not harness.RECEIPT_PATH.exists()


def test_no_live_claim_or_architectural_overreach(plan: dict[str, Any]) -> None:
    assert plan["live_run_executed"] is False
    assert plan["model_call_made"] is False
    assert plan["production_prompt_changed"] is False
    assert plan["canonicalization_implemented"] is False
    assert plan["institutional_ir_runtime_implemented"] is False
    assert plan["independent_validation_claim"] is False
    assert plan["self_adjudication"] == "NOT SELF-ADJUDICATED"


def test_phase_b_changes_only_instrument_and_preregistration_paths(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{PHASE_A_SHA}...{UNIT_TYPE_PHASE_END_SHA}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert all(
        path.startswith("benchmarks/characterization/interpretation-proposal-unit-type-ab-001/")
        or path == "scripts/characterize_interpretation_proposal_unit_type_ab.py"
        or path == "scripts/characterize_interpretation_proposal_unit_type_ab_v2.py"
        or path == "tests/contract/test_interpretation_proposal_unit_type_ab_001.py"
        or path == "tests/contract/test_interpretation_proposal_unit_type_ab_001a.py"
        for path in changed
    )
