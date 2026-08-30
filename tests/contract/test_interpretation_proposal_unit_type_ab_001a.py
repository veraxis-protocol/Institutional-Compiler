"""Contract tests for Unit-Type A/B 001A.

Two things are proved. The successor closes the preregistration discrepancy — all seven
required properties are literal inside the Arm B hint block itself, and the test fails if
any one of them is dropped. And a regression appearing only in Arm B on a non-definition
sentinel is surfaced as a named B-only instance rather than vanishing into an aggregate.

Everything else must be exactly what v0.1 froze: the same Arm A bytes, the same corpus,
the same 174-request plan, the same corrected metrics, the same production seam.
"""

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

pytestmark = pytest.mark.contract

STARTING_SHA = "2f95a91f6109e858eecc840757878297706a18ea"
PHASE_A_SHA = "20399bd98b2702b077c0874d36fce7f3fbb45a7f"

PLAN_DIR = Path("benchmarks/characterization/interpretation-proposal-unit-type-ab-001")
PLAN_V1 = PLAN_DIR / "PLAN-v0.1.json"
FREEZE_V1 = PLAN_DIR / "PLAN-FREEZE-v0.1.json"
PLAN_V2 = PLAN_DIR / "PLAN-v0.2.json"
FREEZE_V2 = PLAN_DIR / "PLAN-FREEZE-v0.2.json"
V2_INSTRUMENT = Path("scripts/characterize_interpretation_proposal_unit_type_ab_v2.py")
V1_INSTRUMENT = Path("scripts/characterize_interpretation_proposal_unit_type_ab.py")
PRODUCTION = Path("src/oic/interpretation_proposal.py")
AUDIT_DIR = Path("benchmarks/characterization/interpretation-proposal-001-postrun-audit")

PRODUCTION_SHA256 = "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"
CORPUS = Path("benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json")
CORPUS_SHA256 = "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"

#: The sentinel used for the load-bearing B-only test: bearer and counterparty are
#: separate slots and the corrected taxonomy calls a swap a WRONG_ROLE_ASSIGNMENT.
SWAP_SENTINEL = "IIR-016"


def _sha256(repo_root: Path, relpath: Path) -> str:
    return hashlib.sha256((repo_root / relpath).read_bytes()).hexdigest()


def _load(name: str, path: Path, source: str | None = None) -> ModuleType:
    text = path.read_text(encoding="utf-8") if source is None else source
    spec = importlib.util.spec_from_loader(name, loader=None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(text, str(path), "exec"), module.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(name, None)
    return module


@pytest.fixture(scope="module")
def v2(repo_root: Path) -> ModuleType:
    return _load("_ab_v2", repo_root / V2_INSTRUMENT)


@pytest.fixture(scope="module")
def v1(v2: ModuleType) -> ModuleType:
    module: ModuleType = v2.load_v1()
    return module


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / CORPUS).read_text(encoding="utf-8"))
    return document


@pytest.fixture(scope="module")
def plan_v2(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / PLAN_V2).read_text(encoding="utf-8"))
    return document


# ---------------------------------------------------------------------------
# 1-2. v0.1 and Phase A are preserved
# ---------------------------------------------------------------------------


def test_the_v01_plan_and_freeze_are_byte_identical(repo_root: Path) -> None:
    changed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{STARTING_SHA}...HEAD",
            "--",
            PLAN_V1.as_posix(),
            FREEZE_V1.as_posix(),
            (PLAN_DIR / "PREREGISTRATION.md").as_posix(),
            V1_INSTRUMENT.as_posix(),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""
    freeze_v1 = json.loads((repo_root / FREEZE_V1).read_text(encoding="utf-8"))
    assert _sha256(repo_root, PLAN_V1) == freeze_v1["plan_sha256"]


def test_the_phase_a_audit_is_byte_identical(repo_root: Path) -> None:
    changed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{PHASE_A_SHA}...HEAD",
            "--",
            AUDIT_DIR.as_posix(),
            "scripts/audit_interpretation_proposal_postrun.py",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""


def test_the_successor_freeze_records_the_superseded_plan(
    repo_root: Path, plan_v2: dict[str, Any]
) -> None:
    freeze = json.loads((repo_root / FREEZE_V2).read_text(encoding="utf-8"))
    assert freeze["plan_sha256"] == _sha256(repo_root, PLAN_V2)
    assert freeze["superseded_plan_sha256"] == _sha256(repo_root, PLAN_V1)
    assert freeze["superseded_plan_preserved_unchanged"] is True
    assert plan_v2["supersedes"]["plan_sha256"] == _sha256(repo_root, PLAN_V1)
    assert plan_v2["supersedes"]["preserved_unchanged"] is True
    assert plan_v2["plan_version"] == "v0.2"


# ---------------------------------------------------------------------------
# 3-4. Arm A unchanged; Arm B differs by exactly one block
# ---------------------------------------------------------------------------


def test_arm_a_is_rendered_by_production_and_is_byte_identical(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    """Byte identity is a fact of construction: Arm A calls production's own builder."""
    from oic.interpretation_proposal import _user_prompt

    for specimen in corpus["specimens"]:
        binding = v1.binding_for(specimen, v1.ARMS[0])
        assert binding.provisional_unit_type is None
        assert v2.user_prompt_for(specimen, v1.ARMS[0], v1) == _user_prompt(binding)


def test_arm_a_carries_no_hint_and_no_unit_type(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    for specimen in corpus["specimens"]:
        prompt = v2.user_prompt_for(specimen, v1.ARMS[0], v1)
        assert "An earlier stage proposed" not in prompt
        assert specimen["candidate"]["unit_type"] not in prompt


def test_arm_b_differs_from_arm_a_by_exactly_one_inserted_block(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    for specimen in corpus["specimens"]:
        arm_a = v2.user_prompt_for(specimen, v1.ARMS[0], v1)
        arm_b = v2.user_prompt_for(specimen, v1.ARMS[1], v1)
        hint = v2.arm_b_hint(specimen["candidate"]["unit_type"])
        assert arm_b.count(hint) == 1, specimen["specimen_id"]
        assert arm_b.replace(hint, "") == arm_a, specimen["specimen_id"]


def test_the_system_prompt_and_provider_settings_are_untouched(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    from oic.interpretation_proposal import _SYSTEM_PROMPT

    captured: list[Any] = []

    class Recorder:
        def complete(self, request: Any) -> Any:  # noqa: ANN401 - provider protocol
            from oic.model_provider import ModelResponse

            captured.append(request)
            return ModelResponse(
                provider="fake",
                model="fake",
                content='{"proposed_assertions":[]}',
                request_id=None,
                raw={},
            )

    specimen = corpus["specimens"][0]
    for arm in v1.ARMS:
        v2.propose_with_prompt(
            binding=v1.binding_for(specimen, v1.ARMS[0]),
            user_prompt=v2.user_prompt_for(specimen, arm, v1),
            provider=Recorder(),
            proposer_id=v1.PROPOSER_ID,
        )
    assert len(captured) == 2
    for request in captured:
        assert request.system_prompt == _SYSTEM_PROMPT
        assert request.temperature == 0.0
        assert request.response_format == {"type": "json_object"}
        assert request.max_tokens == 4096


# ---------------------------------------------------------------------------
# 5-8. The seven properties are literal in the block
# ---------------------------------------------------------------------------


def test_all_seven_properties_are_literal_inside_the_hint_block(v2: ModuleType) -> None:
    hint = v2.arm_b_hint("mandate")
    assert set(v2.HINT_REQUIRED_PROPERTIES) == {
        "provisional",
        "untrusted",
        "produced_at_an_earlier_stage",
        "not_authority",
        "not_canonical_institutional_meaning",
        "possibly_wrong",
        "subordinate_to_the_literal_admitted_source_text",
    }
    for prop, literal in v2.HINT_REQUIRED_PROPERTIES.items():
        assert literal in hint, prop


def test_the_properties_hold_without_the_system_prompt(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    """The discrepancy this successor closes: the block must stand on its own."""
    for specimen in corpus["specimens"]:
        hint = v2.arm_b_hint(specimen["candidate"]["unit_type"])
        for prop, literal in v2.HINT_REQUIRED_PROPERTIES.items():
            assert literal in hint, (specimen["specimen_id"], prop)


@pytest.mark.parametrize(
    "dropped",
    sorted(
        {
            "provisional",
            "untrusted",
            "produced_at_an_earlier_stage",
            "not_authority",
            "not_canonical_institutional_meaning",
            "possibly_wrong",
            "subordinate_to_the_literal_admitted_source_text",
        }
    ),
)
def test_dropping_any_required_property_fails_the_contract(
    repo_root: Path, v2: ModuleType, dropped: str
) -> None:
    """Load-bearing: a hint that loses one property must not pass."""
    literal = v2.HINT_REQUIRED_PROPERTIES[dropped]
    mutant = _load(f"_ab_v2_drop_{dropped}", repo_root / V2_INSTRUMENT)
    # The template is written as adjacent source literals, so the property text is
    # contiguous only in the assembled value. Mutate the value.
    template = str(mutant.__dict__["ARM_B_HINT_TEMPLATE"])
    assert literal in template, dropped
    mutant.__dict__["ARM_B_HINT_TEMPLATE"] = template.replace(literal, "<<REMOVED>>", 1)
    hint = mutant.arm_b_hint("mandate")
    assert literal not in hint, f"the mutation must actually remove {dropped}"
    missing = [name for name, text in v2.HINT_REQUIRED_PROPERTIES.items() if text not in hint]
    assert missing == [dropped], missing


def test_the_hint_declares_the_source_controlling_and_forbids_normative_force(
    v2: ModuleType,
) -> None:
    hint = v2.arm_b_hint("mandate")
    assert "The literal admitted proposition controls" in hint
    assert "where the hint conflicts with the source text, ignore the hint" in hint
    assert "Do not treat the hint as normative force or as a finding" in hint


def test_the_hint_adds_no_example_gold_or_slot_instruction(v2: ModuleType) -> None:
    hint = v2.arm_b_hint("mandate").casefold()
    for forbidden in (
        "for example",
        "e.g.",
        "such as",
        "obligation",
        "prohibition",
        "permission",
        "constitutive_definition",
        "delegation",
        "advisory",
        "slot",
        "bearer",
        "counterparty",
    ):
        assert forbidden not in hint, forbidden


# ---------------------------------------------------------------------------
# 9-11. Corpus, plan and metrics unchanged
# ---------------------------------------------------------------------------


def test_the_corpus_is_unchanged(repo_root: Path, plan_v2: dict[str, Any]) -> None:
    assert _sha256(repo_root, CORPUS) == CORPUS_SHA256 == plan_v2["source_corpus_sha256"]


def test_the_request_plan_is_identical_to_v01(repo_root: Path, plan_v2: dict[str, Any]) -> None:
    plan_v1 = json.loads((repo_root / PLAN_V1).read_text(encoding="utf-8"))
    assert plan_v2["request_plan"] == plan_v1["request_plan"]
    assert plan_v2["planned_requests"] == plan_v1["planned_requests"] == 174
    assert plan_v2["specimen_count"] == plan_v1["specimen_count"] == 29
    assert plan_v2["runs_per_specimen"] == plan_v1["runs_per_specimen"] == 3
    assert plan_v2["interleaving"] == plan_v1["interleaving"]
    assert plan_v2["retry_policy"] == plan_v1["retry_policy"]
    assert plan_v2["pacing"] == plan_v1["pacing"]
    assert plan_v2["regression_sentinels"] == plan_v1["regression_sentinels"]
    assert plan_v2["corrected_paired_metrics"] == plan_v1["corrected_paired_metrics"]
    assert (
        plan_v2["definition_primary_diagnostic"]["observations"]
        == plan_v1["definition_primary_diagnostic"]["observations"]
    )
    assert plan_v2["definition_primary_diagnostic"]["observation_count"] == 18


def test_only_the_expected_keys_differ_between_the_two_plans(
    repo_root: Path, plan_v2: dict[str, Any]
) -> None:
    """The successor changes plan identity and the Arm B hint. Nothing else."""
    plan_v1 = json.loads((repo_root / PLAN_V1).read_text(encoding="utf-8"))
    differing = {key for key in set(plan_v1) | set(plan_v2) if plan_v1.get(key) != plan_v2.get(key)}
    assert differing == {
        "work_order",
        "starting_sha",
        "plan_version",
        "supersedes",
        "successor_change",
        "arms",
        "arm_b_hint_template",
        "arm_b_hint_example",
        "arm_b_hint_required_properties",
        "arm_b_hint_insertion_marker",
        "hint_composed_by",
        "production_interpretation_proposal_sha256",
        "sentinel_paired_defect_reporting",
    }
    arm_a_key = next(iter(plan_v1["arms"]))
    assert plan_v2["arms"][arm_a_key] == plan_v1["arms"][arm_a_key]


def test_the_corrected_metrics_still_come_from_the_frozen_phase_a_audit(
    repo_root: Path, v2: ModuleType
) -> None:
    source = (repo_root / V2_INSTRUMENT).read_text(encoding="utf-8")
    assert "audit_interpretation_proposal_postrun.py" in source
    for name in ("def rescore_ambiguity", "def audit_assignments", "def audit_strengthening"):
        assert name not in source, name
    metrics = _load(
        "_phase_a_metrics_probe",
        repo_root / "scripts/audit_interpretation_proposal_postrun.py",
    )
    assert set(metrics.AMBIGUITY_CATEGORIES) == {
        "ALTERNATIVES_SEPARATELY_SURFACED",
        "SINGLE_ALTERNATIVE_SELECTED",
        "ALTERNATIVES_CONJOINED_OR_COLLAPSED",
        "UNSUPPORTED_ALTERNATIVE",
        "AMBIGUOUS_SLOT_OMITTED",
    }


# ---------------------------------------------------------------------------
# 12. The load-bearing B-only regression test
# ---------------------------------------------------------------------------


def _swap_proposal(specimen: dict[str, Any], *, swapped: bool) -> dict[str, Any]:
    gold = specimen["gold"]["expected_slots"]
    bearer = gold["bearer"]["value"]
    counterparty = gold["counterparty"]["value"]
    return {
        "proposal_id": "iip-fixture",
        "admission_receipt_id": specimen["admission"]["admission_receipt_id"],
        "candidate_unit_id": specimen["admission"]["candidate_unit_id"],
        "candidate_projection_digest": specimen["admission"]["candidate_projection_digest"],
        "proposed_assertions": [
            {
                "slot": "normative_force",
                "proposed_value": specimen["gold"]["expected_force"],
                "proposed_source_quote": specimen["candidate"]["candidate_span"],
            },
            {
                "slot": "bearer",
                "proposed_value": counterparty if swapped else bearer,
                "proposed_source_quote": counterparty if swapped else bearer,
            },
            {
                "slot": "counterparty",
                "proposed_value": bearer if swapped else counterparty,
                "proposed_source_quote": bearer if swapped else counterparty,
            },
        ],
    }


def _sentinel_attempts(v1: ModuleType, specimen: dict[str, Any], *, swap_in_arm: str) -> list[Any]:
    attempts: list[Any] = []
    ordinal = 0
    for run_index in (1, 2, 3):
        for arm in v1.ARMS:
            ordinal += 1
            attempts.append(
                v1.Attempt(
                    ordinal=ordinal,
                    specimen_id=specimen["specimen_id"],
                    run_index=run_index,
                    arm=arm,
                    outcome="ACCEPTED",
                    proposal=_swap_proposal(specimen, swapped=arm == swap_in_arm),
                )
            )
    return attempts


def test_a_b_only_sentinel_regression_is_surfaced_by_name(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    """The whole point of a paired design.

    Arm A assigns bearer and counterparty correctly on every run; Arm B swaps them on
    every run. The two arms have identical aggregate shapes in most respects, so the only
    place this shows as a regression *introduced by the hint* is the paired cell.
    """
    specimen = next(item for item in corpus["specimens"] if item["specimen_id"] == SWAP_SENTINEL)
    corrected = _load(
        "_phase_a_metrics_for_sentinel",
        Path(v2.ROOT) / "scripts/audit_interpretation_proposal_postrun.py",
    )
    attempts = _sentinel_attempts(v1, specimen, swap_in_arm=v1.ARMS[1])
    report = v2.sentinel_paired_defects({"specimens": [specimen]}, attempts, v1, corrected)

    cells = report["per_sentinel_paired_cells"][SWAP_SENTINEL]
    assert cells["B_ONLY_DEFECT"] == 3
    assert cells["A_ONLY_DEFECT"] == 0
    assert cells["BOTH_DEFECT"] == 0
    assert cells["NEITHER_DEFECT"] == 0
    assert report["b_only_defect_count"] == 3
    assert report["b_only_defect_instances"] == [
        {"specimen_id": SWAP_SENTINEL, "run_index": 1},
        {"specimen_id": SWAP_SENTINEL, "run_index": 2},
        {"specimen_id": SWAP_SENTINEL, "run_index": 3},
    ]
    assert SWAP_SENTINEL not in v1.DEFINITION_SPECIMENS


def test_the_mirrored_arm_a_regression_is_reported_as_a_only(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    """The cells must not be a one-way detector."""
    specimen = next(item for item in corpus["specimens"] if item["specimen_id"] == SWAP_SENTINEL)
    corrected = _load(
        "_phase_a_metrics_for_sentinel_a",
        Path(v2.ROOT) / "scripts/audit_interpretation_proposal_postrun.py",
    )
    attempts = _sentinel_attempts(v1, specimen, swap_in_arm=v1.ARMS[0])
    report = v2.sentinel_paired_defects({"specimens": [specimen]}, attempts, v1, corrected)
    cells = report["per_sentinel_paired_cells"][SWAP_SENTINEL]
    assert cells["A_ONLY_DEFECT"] == 3
    assert cells["B_ONLY_DEFECT"] == 0
    assert report["b_only_defect_instances"] == []
    assert report["a_only_defect_count"] == 3


def test_a_b_only_regression_never_reaches_the_definition_only_reporting(
    v1: ModuleType, v2: ModuleType, corpus: dict[str, Any]
) -> None:
    """v0.1 reported paired cells for the definition diagnostic alone. A sentinel
    regression is invisible there, which is why the sentinel section exists."""
    specimen = next(item for item in corpus["specimens"] if item["specimen_id"] == SWAP_SENTINEL)
    attempts = _sentinel_attempts(v1, specimen, swap_in_arm=v1.ARMS[1])
    analysis = v1.analyze_attempts({"specimens": [specimen]}, attempts)
    assert analysis["definition_primary_diagnostic"] == []
    assert analysis["definition_paired_defect_cells"] == {
        "A_ONLY_DEFECT": 0,
        "B_ONLY_DEFECT": 0,
        "BOTH_DEFECT": 0,
        "NEITHER_DEFECT": 0,
    }
    assert "sentinel_paired_defect_cells" not in analysis


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        (
            "remove_b_only_instance_reporting",
            '        "b_only_defect_instances": b_only_instances,\n',
            '        "b_only_defect_instances": [],\n',
        ),
        (
            "aggregate_sentinels_into_one_total",
            '        "per_sentinel_paired_cells": per_sentinel,\n',
            '        "per_sentinel_paired_cells": {},\n',
        ),
        (
            "misaggregate_b_only_into_neither",
            "            if not defect.get((specimen_id, run_index, v1.ARMS[0]), False):\n"
            '                b_only_instances.append({"specimen_id": specimen_id, '
            '"run_index": run_index})\n',
            "            if False:\n"
            '                b_only_instances.append({"specimen_id": specimen_id, '
            '"run_index": run_index})\n',
        ),
    ],
    ids=["remove_instances", "aggregate_away", "misaggregate"],
)
def test_removing_or_aggregating_b_only_reporting_fails(
    repo_root: Path,
    v1: ModuleType,
    v2: ModuleType,
    corpus: object,
    name: str,
    old: str,
    new: str,
) -> None:
    """The mutation each named failure mode corresponds to must actually break the report."""
    assert isinstance(corpus, dict)
    source = (repo_root / V2_INSTRUMENT).read_text(encoding="utf-8")
    assert source.count(old) == 1, name
    mutant = _load(f"_ab_v2_{name}", repo_root / V2_INSTRUMENT, source.replace(old, new, 1))
    specimen = next(item for item in corpus["specimens"] if item["specimen_id"] == SWAP_SENTINEL)
    corrected = _load(
        f"_phase_a_metrics_{name}",
        Path(v2.ROOT) / "scripts/audit_interpretation_proposal_postrun.py",
    )
    attempts = _sentinel_attempts(v1, specimen, swap_in_arm=v1.ARMS[1])
    report = mutant.sentinel_paired_defects({"specimens": [specimen]}, attempts, v1, corrected)

    surfaced = bool(report["b_only_defect_instances"]) and bool(
        report["per_sentinel_paired_cells"].get(SWAP_SENTINEL, {}).get("B_ONLY_DEFECT")
    )
    assert not surfaced, f"mutation {name} must actually stop surfacing the B-only regression"

    control = v2.sentinel_paired_defects({"specimens": [specimen]}, attempts, v1, corrected)
    assert control["b_only_defect_instances"]
    assert control["per_sentinel_paired_cells"][SWAP_SENTINEL]["B_ONLY_DEFECT"] == 3


def test_the_sentinel_defect_rule_is_preregistered_in_the_plan(
    plan_v2: dict[str, Any], v2: ModuleType
) -> None:
    section = plan_v2["sentinel_paired_defect_reporting"]
    assert section["added_by_successor"] is True
    assert section["reported_per_sentinel"] is True
    assert section["b_only_instances_named"] is True
    assert section["cells"] == [
        "A_ONLY_DEFECT",
        "B_ONLY_DEFECT",
        "BOTH_DEFECT",
        "NEITHER_DEFECT",
    ]
    assert section["defect_rule"] == list(v2.SENTINEL_DEFECT_RULE)


# ---------------------------------------------------------------------------
# 13-14. Offline, production untouched
# ---------------------------------------------------------------------------


def test_the_offline_preflight_constructs_no_provider(v2: ModuleType) -> None:
    assert v2.main([]) == 0


def test_the_production_seam_is_byte_identical(repo_root: Path, plan_v2: dict[str, Any]) -> None:
    digest = _sha256(repo_root, PRODUCTION)
    assert digest == PRODUCTION_SHA256
    assert plan_v2["production_interpretation_proposal_sha256"] == digest
    assert plan_v2["production_prompt_changed"] is False
    changed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{STARTING_SHA}...HEAD",
            "--",
            "src",
            "schemas",
            "design",
            ".gitignore",
            "benchmarks/characterization/interpretation-proposal-001",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""


def test_the_nvidia_adapter_is_byte_identical(repo_root: Path) -> None:
    assert (
        _sha256(repo_root, Path("src/oic/nvidia_nim.py"))
        == "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"
    )


def test_no_canonicalization_or_institutional_ir_runtime_exists(repo_root: Path) -> None:
    assert not (repo_root / "src/oic/institutional_ir.py").exists()
    assert not list((repo_root / "src").rglob("*.rego"))
    import ast

    tree = ast.parse((repo_root / V2_INSTRUMENT).read_text(encoding="utf-8"))
    forbidden = {
        "interpretation_status",
        "interpretation_basis",
        "interpretation_evidence_refs",
        "ir_unit_id",
        "semantic_equivalence_key",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            assert not keys & forbidden, sorted(keys & forbidden)


def test_the_successor_claims_no_live_run(repo_root: Path, plan_v2: dict[str, Any]) -> None:
    freeze = json.loads((repo_root / FREEZE_V2).read_text(encoding="utf-8"))
    for document in (plan_v2, freeze):
        assert document["live_run_executed"] is False
        assert document["model_call_made"] is False
        assert document["canonicalization_implemented"] is False
        assert document["institutional_ir_runtime_implemented"] is False
        assert document["independent_validation_claim"] is False
        assert document["self_adjudication"] == "NOT SELF-ADJUDICATED"
    tracked = subprocess.run(
        ["git", "ls-files", "--", ".local"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert tracked == ""


def test_the_plan_materializes_deterministically(v1: ModuleType, v2: ModuleType) -> None:
    first = v2.build_offline_plan(v1)
    second = v2.build_offline_plan(v1)
    assert first == second
    assert copy.deepcopy(first) == v2.preflight(v1)
