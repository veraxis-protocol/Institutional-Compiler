"""Offline tests for the versioned candidate-semantics characterization harness."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from oic.model_provider import ModelProviderError, ModelRequest, ModelResponse

_ = urllib.request
MODULE_RELPATH = "scripts/characterize_candidate_semantics.py"


def _load(repo_root: Path) -> ModuleType:
    path = repo_root / MODULE_RELPATH
    spec = importlib.util.spec_from_file_location("characterize_candidate_semantics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["characterize_candidate_semantics"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _load(repo_root)


class ScriptedProvider:
    provider_name = "fake-provider"

    def __init__(self, *contents: str) -> None:
        self.contents = list(contents)
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        content = self.contents[len(self.requests) % len(self.contents)]
        self.requests.append(request)
        return ModelResponse(
            provider=self.provider_name,
            model="fake-model",
            content=content,
            request_id=f"fake-{len(self.requests)}",
            raw={},
        )


class BrokenProvider:
    provider_name = "fake-provider"

    def complete(self, request: ModelRequest) -> ModelResponse:
        del request
        raise ModelProviderError("provider transport failed")


def response(*candidates: tuple[str, str]) -> str:
    return json.dumps(
        {
            "candidates": [
                {"candidate_span": span, "unit_type": unit_type} for span, unit_type in candidates
            ]
        }
    )


def specimen(
    specimen_id: str,
    *,
    text: str = "The Treasurer must approve every payment.",
    category: str = "simple_obligation",
    normative: bool = True,
    cmin: int = 1,
    cmax: int | None = None,
    types: list[str] | None = None,
    families: list[dict[str, str]] | None = None,
    material: list[list[str]] | None = None,
    bounds: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "specimen_id": specimen_id,
        "category": category,
        "source_text": text,
        "normative_expected": normative,
        "expected_candidate_count_min": cmin,
        "expected_candidate_count_max": cmax,
        "acceptable_unit_types": types,
        "families": families or [],
        "threshold_markers": None,
        "material_span_groups": material,
        "candidate_span_bounds": bounds,
        "diagnostic_tags": tags or [],
        "characterization_notes": "synthetic test specimen",
        "claim_ceiling": "test fixture only",
    }


def document(*specimens: dict[str, Any]) -> dict[str, Any]:
    return {
        "corpus_id": "TEST-CORPUS",
        "corpus_version": "v0.3",
        "claim_ceiling": "test fixture only",
        "specimen_count": len(specimens),
        "specimens": list(specimens),
    }


def write_corpus(harness: ModuleType, tmp_path: Path, *items: dict[str, Any]) -> Path:
    path = tmp_path / "CORPUS.json"
    path.write_bytes(harness.canonical_json_bytes(document(*items)))
    return path


def write_freeze(harness: ModuleType, tmp_path: Path, corpus: Any) -> Path:  # noqa: ANN401
    path = tmp_path / "FREEZE.json"
    path.write_bytes(
        harness.canonical_json_bytes(
            {
                "corpus_sha256": corpus.sha256,
                "specimen_count": len(corpus.specimens),
                "specimen_ids": [item.specimen_id for item in corpus.specimens],
                "specimen_source_sha256": {
                    item.specimen_id: item.source_sha256 for item in corpus.specimens
                },
            }
        )
    )
    return path


def load(harness: ModuleType, tmp_path: Path, *items: dict[str, Any]) -> Any:  # noqa: ANN401
    return harness.load_corpus(write_corpus(harness, tmp_path, *items))


def test_003_corpus_shape_and_exact_bytes_digest(harness: ModuleType, tmp_path: Path) -> None:
    path = write_corpus(harness, tmp_path, specimen("T-1"))
    corpus = harness.load_corpus(path)
    assert corpus.corpus_version == "v0.3"
    assert corpus.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert corpus.specimens[0].diagnostic_tags == ()


def test_duplicate_ids_and_bad_material_groups_are_rejected(
    harness: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(harness.CharacterizationError, match="duplicate"):
        load(harness, tmp_path, specimen("T-1"), specimen("T-1"))
    with pytest.raises(harness.CharacterizationError, match="must not be empty"):
        load(harness, tmp_path, specimen("T-2", material=[[]]))


def test_freeze_rejects_corpus_and_source_drift(harness: ModuleType, tmp_path: Path) -> None:
    corpus = load(harness, tmp_path, specimen("T-1"))
    freeze = write_freeze(harness, tmp_path, corpus)
    state, findings = harness.resolve_corpus_integrity(corpus, freeze, allow_drift=False)
    assert state == harness.CORPUS_INTACT
    assert findings == []
    drifted = load(harness, tmp_path, specimen("T-1", text="Different source."))
    with pytest.raises(harness.CorpusIntegrityError, match="refusing to run"):
        harness.resolve_corpus_integrity(drifted, freeze, allow_drift=False)


def test_projection_is_only_span_and_provisional_type(harness: ModuleType) -> None:
    projection = harness.semantic_projection(
        {
            "unit_id": "cnu-1",
            "candidate_span": "Pay now.",
            "unit_type": "obligation",
            "interpretation_state": "extracted",
            "epistemic_state": "uncertain",
            "source_anchors": [],
        }
    )
    assert projection == {"candidate_span": "Pay now.", "unit_type": "obligation"}
    assert tuple(projection) == harness.SEMANTIC_FIELDS


def test_attempt_records_boundary_rejection_without_repair(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load(harness, tmp_path, specimen("T-1"))
    attempts = harness.run_corpus(
        corpus,
        provider=ScriptedProvider(
            '{"candidates":[{"candidate_span":"invented","unit_type":"obligation"}]}'
        ),
        runs_per_specimen=1,
    )
    assert attempts[0].boundary_result == harness.BOUNDARY_REJECTED
    assert attempts[0].error_type == "CandidateGroundingError"
    assert attempts[0].candidates == ()


def test_provider_errors_are_separate_metric_b(harness: ModuleType, tmp_path: Path) -> None:
    corpus = load(harness, tmp_path, specimen("T-1"))
    attempts = harness.run_corpus(corpus, provider=BrokenProvider(), runs_per_specimen=2)
    assert harness.metric_boundary_acceptance(attempts)["boundary_rejected"] == 0
    assert harness.metric_provider_errors(attempts)["provider_errors"] == 2


def test_presence_false_positive_and_count_metrics(harness: ModuleType, tmp_path: Path) -> None:
    positive = specimen("P", text="Payments must be approved.")
    negative = specimen("N", text="The office is blue.", normative=False, cmin=0, cmax=0)
    corpus = load(harness, tmp_path, positive, negative)
    provider = ScriptedProvider(
        response(("Payments must be approved.", "obligation")),
        response(("The office is blue.", "obligation")),
    )
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=1)
    grouped = harness.group_by_specimen(attempts)
    assert harness.metric_normative_presence(corpus, grouped)["presence_misses"] == 0
    assert harness.metric_negative_controls(corpus, grouped)["false_positive_runs"] == 1
    assert harness.metric_candidate_count_stability(grouped)["per_specimen"]


def test_metric_f_records_boundary_grounding(harness: ModuleType, tmp_path: Path) -> None:
    text = "Payments must be approved."
    corpus = load(harness, tmp_path, specimen("T", text=text))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(response((text, "obligation"))), runs_per_specimen=1
    )
    metric = harness.metric_candidate_span_grounding(attempts)
    assert metric["candidate_spans_examined"] == 1
    assert metric["candidate_spans_passing_boundary_grounding"] == 1


def test_metric_g_requires_every_material_group_across_candidate_spans(
    harness: ModuleType, tmp_path: Path
) -> None:
    text = "If spending exceeds $10,000, approval is required within five days."
    item = specimen("T", text=text, material=[["exceeds $10,000"], ["within five days"]])
    corpus = load(harness, tmp_path, item)
    complete = harness.run_corpus(
        corpus, provider=ScriptedProvider(response((text, "obligation"))), runs_per_specimen=1
    )
    incomplete = harness.run_corpus(
        corpus,
        provider=ScriptedProvider(response(("approval is required", "obligation"))),
        runs_per_specimen=1,
    )
    assert (
        harness.metric_material_span_completeness(corpus, harness.group_by_specimen(complete))[
            "complete_runs"
        ]
        == 1
    )
    assert (
        harness.metric_material_span_completeness(corpus, harness.group_by_specimen(incomplete))[
            "incomplete_runs"
        ]
        == 1
    )


def test_metric_h_reports_exact_span_variation_without_calling_it_failure(
    harness: ModuleType, tmp_path: Path
) -> None:
    text = "Payments must be approved before shipment."
    corpus = load(harness, tmp_path, specimen("T", text=text))
    attempts = harness.run_corpus(
        corpus,
        provider=ScriptedProvider(
            response((text, "obligation")),
            response(("Payments must be approved", "obligation")),
        ),
        runs_per_specimen=2,
    )
    metric = harness.metric_candidate_span_repeat_stability(harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["result"] == harness.REPEAT_VARIANT
    assert "not automatically semantic failure" in metric["note"]


def test_metrics_i_and_j_compare_presence_count_and_type_without_span_equivalence(
    harness: ModuleType, tmp_path: Path
) -> None:
    standing = {"family_id": "S", "family_kind": "source_standing", "role": "draft"}
    paraphrase = {"family_id": "P", "family_kind": "paraphrase", "role": "one"}
    one = specimen("A", text="DRAFT. Payments must be approved.", families=[standing, paraphrase])
    two = specimen(
        "B",
        text="Approval is required for payments.",
        families=[
            {**standing, "role": "baseline"},
            {**paraphrase, "role": "two"},
        ],
    )
    corpus = load(harness, tmp_path, one, two)
    attempts = harness.run_corpus(
        corpus,
        provider=ScriptedProvider(
            response((one["source_text"], "obligation")),
            response((two["source_text"], "obligation")),
        ),
        runs_per_specimen=1,
    )
    grouped = harness.group_by_specimen(attempts)
    assert harness.metric_source_standing_invariance(corpus, grouped)["families"][0][
        "presence_agreement"
    ]
    paraphrase_metric = harness.metric_paraphrase_families(corpus, grouped)
    assert paraphrase_metric["families"][0]["unit_type_set_agreement"]
    assert "semantic_hash_set_agreement" in paraphrase_metric["not_required_at_candidate_stage"]


def test_metrics_k_and_l_cover_advisory_and_multi_unit(harness: ModuleType, tmp_path: Path) -> None:
    advisory_text = "Units are encouraged to consolidate purchases."
    multi_text = "Orders must be approved. Receipts must be retained."
    corpus = load(
        harness,
        tmp_path,
        specimen("A", text=advisory_text, category="advisory"),
        specimen("M", text=multi_text, category="multi_unit", cmin=2),
    )
    provider = ScriptedProvider(
        response((advisory_text, "advisory")),
        response(
            ("Orders must be approved.", "obligation"),
            ("Receipts must be retained.", "evidence_duty"),
        ),
    )
    grouped = harness.group_by_specimen(
        harness.run_corpus(corpus, provider=provider, runs_per_specimen=1)
    )
    assert harness.metric_advisory_candidate_presence(corpus, grouped)["presence_misses"] == 0
    assert (
        harness.metric_multi_unit(corpus, grouped)["per_specimen"][0][
            "runs_returning_separated_units"
        ]
        == 1
    )


def test_metric_m_is_bounded_not_a_shortest_span_rule(harness: ModuleType, tmp_path: Path) -> None:
    text = "Context only. Payments must be approved. More context."
    bound = "Payments must be approved."
    corpus = load(harness, tmp_path, specimen("T", text=text, bounds=[bound]))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(response((text, "obligation"))), runs_per_specimen=1
    )
    metric = harness.metric_candidate_span_overreach(corpus, harness.group_by_specimen(attempts))
    assert metric["candidate_spans_outside_bounds"] == 1
    assert "not a universal shortest-span rule" in metric["note"]


def test_003_receipt_has_exact_versioned_a_through_m_metrics(
    harness: ModuleType, tmp_path: Path
) -> None:
    text = "Payments must be approved."
    corpus = load(harness, tmp_path, specimen("T", text=text))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(response((text, "obligation"))), runs_per_specimen=1
    )
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=1,
        provider_name="fake-provider",
        model="fake-model",
        corpus_integrity=harness.CORPUS_INTACT,
        corpus_freeze_relpath="FREEZE.json",
        integrity_findings=[],
        implementation={"commit": "abc", "worktree_clean": True},
    )
    assert receipt["metric_contract"] == "candidate-semantics-003-a-through-m"
    assert list(receipt["metrics"]) == [
        "a_boundary_acceptance",
        "b_provider_errors",
        "c_normative_candidate_presence",
        "d_false_positives_on_negative_controls",
        "e_candidate_count_stability",
        "f_candidate_span_source_grounding",
        "g_material_span_completeness",
        "h_candidate_span_repeat_stability",
        "i_source_standing_invariance",
        "j_paraphrase_family_compatibility",
        "k_advisory_presence",
        "l_multi_unit_separation",
        "m_candidate_span_overreach",
    ]
    assert receipt["independent_validation_claim"] is False
    assert "NOT SELF-ADJUDICATED" in receipt["self_adjudication"]
    serialized = json.dumps(receipt)
    for obsolete in ("k_unsupported_actor", "o_target_preservation", "q_operative_predicate"):
        assert obsolete not in serialized


def test_002_historical_metric_names_remain_readable_without_reinterpretation(
    harness: ModuleType,
) -> None:
    receipt = {
        "work_order": "OIC-CANDIDATE-SEMANTICS-002",
        "metrics": {"k_unsupported_actor": {}, "q_operative_predicate": {}},
    }
    assert harness.historical_metric_names(receipt) == (
        "k_unsupported_actor",
        "q_operative_predicate",
    )


def test_cli_defaults_point_to_004_and_no_live_call_occurs(harness: ModuleType) -> None:
    args = harness.build_parser().parse_args([])
    assert "candidate-semantics-004" in args.corpus.as_posix()
    assert "candidate-semantics-004" in args.freeze.as_posix()
    assert "OIC-CANDIDATE-SEMANTICS-004" in args.output.as_posix()


def test_every_predecessor_corpus_still_loads_from_its_own_path(
    harness: ModuleType, repo_root: Path
) -> None:
    """001, 002 and 003 stay runnable as the evidence their own receipts refer to."""
    for version, expected in (
        ("001/CORPUS-v0.1.json", "OIC-CANDIDATE-SEMANTICS-001"),
        ("002/CORPUS-v0.2.json", "OIC-CANDIDATE-SEMANTICS-002"),
        ("003/CORPUS-v0.3.json", "OIC-CANDIDATE-SEMANTICS-003"),
    ):
        path = repo_root / "benchmarks/characterization" / f"candidate-semantics-{version}"
        corpus = harness.load_corpus(path)
        assert corpus.corpus_id == expected
        assert corpus.specimens[0].separable_framing_spans is None


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-004 metrics
#
# Every metric is exercised firing and staying quiet. The one that matters most is the
# interaction: a span that sheds framing but also sheds material content must be booked as
# underreach and must NOT be counted as a framing-separation success.
# --------------------------------------------------------------------------

FRAMED = (
    "DRAFT — NOT YET ADOPTED. A payment above $10,000 requires approval by the "
    "Chief Financial Officer."
)
PROPOSITION = "A payment above $10,000 requires approval by the Chief Financial Officer."
FRAMING = "DRAFT — NOT YET ADOPTED."


def framing_specimen(
    specimen_id: str = "F-1",
    *,
    text: str = FRAMED,
    framing: list[str] | None = None,
    expected: bool | None = True,
    structure: str = "draft_prefix",
    material: list[list[str]] | None = None,
    bounds: list[str] | None = None,
    category: str = "standing_draft",
) -> dict[str, Any]:
    record = specimen(
        specimen_id,
        text=text,
        category=category,
        material=material
        if material is not None
        else [["above $10,000"], ["Chief Financial Officer"]],
        bounds=bounds if bounds is not None else [PROPOSITION],
    )
    record["separable_framing_spans"] = framing if framing is not None else [FRAMING]
    record["framing_expected_excluded"] = expected
    record["framing_structure"] = structure
    return record


def framing_document(*specimens: dict[str, Any]) -> dict[str, Any]:
    record = document(*specimens)
    record["corpus_id"] = "TEST-CORPUS-004"
    record["corpus_version"] = "v0.4"
    return record


def load_004(harness: ModuleType, tmp_path: Path, *items: dict[str, Any]) -> Any:  # noqa: ANN401
    path = tmp_path / "CORPUS-004.json"
    path.write_bytes(harness.canonical_json_bytes(framing_document(*items)))
    return harness.load_corpus(path)


def run(harness: ModuleType, corpus: Any, content: str, runs: int = 1) -> Any:  # noqa: ANN401
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(content), runs_per_specimen=runs
    )
    return attempts, harness.group_by_specimen(attempts)


def test_004_specimen_fields_load_and_stay_optional(harness: ModuleType, tmp_path: Path) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen(), specimen("T-2"))
    framed, plain = corpus.specimens
    assert framed.separable_framing_spans == (FRAMING,)
    assert framed.framing_expected_excluded is True
    assert framed.framing_structure == "draft_prefix"
    assert plain.separable_framing_spans is None
    assert plain.framing_expected_excluded is None
    assert plain.framing_structure is None


def test_j_records_a_clean_framing_separation(harness: ModuleType, tmp_path: Path) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen())
    _, grouped = run(harness, corpus, response((PROPOSITION, "obligation")), runs=3)
    metric = harness.metric_framing_separation(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["result"] == harness.FRAMING_SEPARATED
    assert record["spans_containing_separable_framing"] == 0
    assert record["spans_inside_acceptable_bounds"] == 3
    assert record["runs_dropping_material_proposition_content"] == 0
    assert metric["spans_cleanly_separated"] == 3


def test_j_records_carried_framing_without_repairing_it(
    harness: ModuleType, tmp_path: Path
) -> None:
    """The evidenced CSEM-021 defect: the whole framed fragment returned as the span."""
    corpus = load_004(harness, tmp_path, framing_specimen())
    _, grouped = run(harness, corpus, response((FRAMED, "obligation")), runs=3)
    metric = harness.metric_framing_separation(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["result"] == harness.FRAMING_CARRIED
    assert record["spans_containing_separable_framing"] == 3
    assert record["observed_framing_carrying_spans"] == [FRAMED]
    assert record["runs_dropping_material_proposition_content"] == 0
    assert metric["spans_cleanly_separated"] == 0


def test_j_refuses_to_score_underreach_as_a_separation_success(
    harness: ModuleType, tmp_path: Path
) -> None:
    """Shedding the framing AND the threshold is a worse answer, not a better one."""
    corpus = load_004(harness, tmp_path, framing_specimen())
    _, grouped = run(harness, corpus, response(("requires approval", "obligation")), runs=2)
    metric = harness.metric_framing_separation(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["spans_containing_separable_framing"] == 0
    assert record["result"] == harness.MATERIAL_UNDERREACH
    assert record["runs_dropping_material_proposition_content"] == 2
    assert metric["spans_cleanly_separated"] == 0
    assert record["runs"][0]["material_groups_lost"] == [
        ["above $10,000"],
        ["Chief Financial Officer"],
    ]


def test_j_ignores_specimens_that_register_no_separable_framing(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen(expected=False, framing=None))
    _, grouped = run(harness, corpus, response((PROPOSITION, "obligation")))
    assert harness.metric_framing_separation(corpus, grouped)["per_specimen"] == []


def test_j2_flags_a_specimen_whose_framing_words_belong_to_the_proposition(
    harness: ModuleType, tmp_path: Path
) -> None:
    """CSEM-043's role: 'still in draft' governs conduct and must not be stripped."""
    text = (
        "Where a contract is still in draft, the sponsoring unit must record the reason "
        "for the delay."
    )
    control = framing_specimen(
        "F-CTRL",
        text=text,
        framing=None,
        expected=False,
        structure="draft_word_inside_proposition",
        material=[["Where a contract is still in draft"], ["record the reason for the delay"]],
        bounds=[text],
        category="condition_is_not_framing",
    )
    corpus = load_004(harness, tmp_path, control)
    stripped = "the sponsoring unit must record the reason for the delay."
    _, grouped = run(harness, corpus, response((stripped, "obligation")), runs=2)
    metric = harness.metric_framing_must_not_be_stripped(corpus, grouped)
    assert metric["runs_dropping_material_content"] == 2
    assert metric["per_specimen"][0]["runs"][0]["result"] == harness.MATERIAL_UNDERREACH

    _, kept = run(harness, corpus, response((text, "obligation")), runs=2)
    assert (
        harness.metric_framing_must_not_be_stripped(corpus, kept)["runs_dropping_material_content"]
        == 0
    )


def test_m_underreach_names_the_material_groups_that_went_missing(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen())
    _, grouped = run(
        harness,
        corpus,
        response(("A payment above $10,000 requires approval", "obligation")),
        runs=2,
    )
    metric = harness.metric_candidate_span_underreach(corpus, grouped)
    assert metric["measured_runs"] == 2
    assert metric["runs_losing_material_content"] == 2
    assert metric["per_specimen"][0]["runs"][0]["material_groups_lost"] == [
        ["Chief Financial Officer"]
    ]


def test_m_stays_quiet_when_every_material_group_survives(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen())
    _, grouped = run(harness, corpus, response((PROPOSITION, "obligation")), runs=3)
    metric = harness.metric_candidate_span_underreach(corpus, grouped)
    assert metric["measured_runs"] == 3
    assert metric["runs_losing_material_content"] == 0


def test_overreach_and_underreach_are_counted_separately(
    harness: ModuleType, tmp_path: Path
) -> None:
    """The same run can be both, and each lands where it belongs."""
    corpus = load_004(harness, tmp_path, framing_specimen())
    # Reaches beyond the registered bound (carries framing) and loses the recipient.
    span = "DRAFT — NOT YET ADOPTED. A payment above $10,000 requires approval"
    _, grouped = run(harness, corpus, response((span, "obligation")))
    over = harness.metric_candidate_span_overreach(corpus, grouped)
    under = harness.metric_candidate_span_underreach(corpus, grouped)
    assert over["candidate_spans_outside_bounds"] == 1
    assert under["runs_losing_material_content"] == 1
    framing = harness.metric_framing_separation(corpus, grouped)
    assert framing["per_specimen"][0]["result"] == harness.MATERIAL_UNDERREACH


def test_a_multi_unit_specimen_under_one_prefix_separates_cleanly(
    harness: ModuleType, tmp_path: Path
) -> None:
    text = (
        "NOT YET IN FORCE. A purchase requisition must be approved before an order is "
        "placed. Suppliers are paid within forty-five days of invoice."
    )
    first = "A purchase requisition must be approved before an order is placed."
    second = "Suppliers are paid within forty-five days of invoice."
    item = framing_specimen(
        "F-MULTI",
        text=text,
        framing=["NOT YET IN FORCE."],
        structure="shared_framing_prefix_two_propositions",
        material=[["before an order is placed"], ["within forty-five days of invoice"]],
        bounds=[first, second],
        category="shared_framing_multi_unit",
    )
    item["expected_candidate_count_min"] = 2
    corpus = load_004(harness, tmp_path, item)
    _, grouped = run(harness, corpus, response((first, "obligation"), (second, "temporal_trigger")))
    record = harness.metric_framing_separation(corpus, grouped)["per_specimen"][0]
    assert record["candidate_spans_examined"] == 2
    assert record["spans_inside_acceptable_bounds"] == 2
    assert record["result"] == harness.FRAMING_SEPARATED
    assert (
        harness.metric_multi_unit(corpus, grouped)["per_specimen"][0][
            "runs_returning_separated_units"
        ]
        == 1
    )


def test_the_004_receipt_is_version_specific_and_labels_both_defects(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load_004(
        harness, tmp_path, framing_specimen(), specimen("N-1", normative=False, cmin=0, cmax=0)
    )
    attempts, _ = run(harness, corpus, response((PROPOSITION, "obligation")), runs=2)
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=2,
        provider_name="fake-provider",
        model="fake-model",
        corpus_integrity=harness.CORPUS_INTACT,
        corpus_freeze_relpath="FREEZE.json",
        integrity_findings=[],
        implementation={"commit": "0" * 40, "worktree_clean": True},
    )
    assert receipt["work_order"] == "OIC-CANDIDATE-SEMANTICS-004"
    assert receipt["metric_contract"] == "candidate-semantics-004-a-through-m"
    assert set(receipt["metrics"]) == {
        "a_boundary_acceptance",
        "b_provider_errors",
        "c_normative_candidate_presence",
        "d_false_positives_on_negative_controls",
        "e_candidate_count_stability",
        "f_candidate_span_source_grounding",
        "g_material_span_completeness",
        "h_candidate_span_repeat_stability",
        "i_source_standing_invariance",
        "j_framing_separation",
        "j2_framing_that_must_not_be_stripped",
        "k_multi_unit_separation",
        "l_advisory_presence",
        "m_candidate_span_underreach",
        "m_prime_candidate_span_overreach",
    }
    assert "Opposite defects, counted separately" in receipt["overreach_versus_underreach"]
    assert receipt["candidate_contract"]["model_proposed_fields"] == [
        "candidate_span",
        "unit_type",
    ]
    assert receipt["candidate_contract"]["schema_changed_in_004"] is False
    assert "no post-generation" in receipt["candidate_contract"]["framing_separation_mechanism"]


def test_the_004_receipt_states_its_claim_ceiling_and_does_not_self_adjudicate(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load_004(harness, tmp_path, framing_specimen())
    attempts, _ = run(harness, corpus, response((PROPOSITION, "obligation")))
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=1,
        provider_name="fake-provider",
        model="fake-model",
        corpus_integrity=harness.CORPUS_INTACT,
        corpus_freeze_relpath="FREEZE.json",
        integrity_findings=[],
        implementation={"commit": "0" * 40, "worktree_clean": True},
    )
    ceiling = receipt["claim_ceiling"]
    assert receipt["independent_validation_claim"] is False
    assert receipt["self_adjudication"] == "NOT SELF-ADJUDICATED; engineering observations only."
    for denied in (
        "semantic correctness",
        "institutional admission",
        "authority",
        "enforceability",
        "cross-model generalization",
        "independent validation",
    ):
        assert denied in ceiling, denied
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    for banned in ('"ADMITTED"', '"AUTHORIZED"', '"COMPLIANT"', '"ALLOW"', '"DENY"'):
        assert banned not in serialized, banned


def test_historical_metric_labels_stay_version_correct(harness: ModuleType, tmp_path: Path) -> None:
    """A v0.3 corpus still gets the 003 metric contract, not the 004 one."""
    corpus = load(harness, tmp_path, specimen("T-1", material=[["approve"]]))
    attempts, _ = run(harness, corpus, response(("The Treasurer must approve", "obligation")))
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=1,
        provider_name="fake-provider",
        model="fake-model",
        corpus_integrity=harness.CORPUS_INTACT,
        corpus_freeze_relpath="FREEZE.json",
        integrity_findings=[],
        implementation={"commit": "0" * 40, "worktree_clean": True},
    )
    assert receipt["metric_contract"] == "candidate-semantics-003-a-through-m"
    assert "j_framing_separation" not in receipt["metrics"]
    assert "m_candidate_span_overreach" in receipt["metrics"]
    assert "not current 003 requirements" in receipt["historical_metric_note"]
