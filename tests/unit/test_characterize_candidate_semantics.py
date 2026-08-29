"""Offline tests for the OIC-CANDIDATE-SEMANTICS-001 characterization harness.

Every test here drives the harness with a fake provider. Nothing contacts a network, and
nothing asserts that a live model returns any particular answer: these tests are about
whether the measuring instrument measures, not about what it will read.

The instrument has two obligations that matter more than its metrics, and both are
tested from the failing side as well as the passing one: it must not repair a response the
candidate boundary refused, and it must not manufacture agreement between two answers that
differ.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from oic.model_provider import ModelProvider, ModelRequest, ModelResponse

# urllib.request is imported eagerly so the NVIDIA adapter the harness imports loads
# cleanly under the suite-wide socket prohibition. Same reason as the freeze suites.
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
    """Returns preset contents in order, cycling once exhausted. Performs no I/O."""

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


class KeyedProvider:
    """Returns content chosen by a marker in the source fragment."""

    provider_name = "fake-provider"

    def __init__(self, routes: dict[str, str], default: str) -> None:
        self.routes = routes
        self.default = default

    def complete(self, request: ModelRequest) -> ModelResponse:
        content = self.default
        for marker, body in self.routes.items():
            if marker in request.user_prompt:
                content = body
                break
        return ModelResponse(
            provider=self.provider_name,
            model="fake-model",
            content=content,
            request_id=None,
            raw={},
        )


def candidate_json(**fields: object) -> str:
    unit: dict[str, object] = {
        "unit_type": "obligation",
        "actor": None,
        "action": None,
        "object": None,
        "target": None,
        "conditions": [],
        "exceptions": [],
        "evidence_requirements": [],
    }
    unit.update(fields)
    return json.dumps({"candidates": [unit]})


EMPTY = '{"candidates":[]}'


def specimen_dict(
    specimen_id: str,
    *,
    text: str = "The Treasurer must approve every payment.",
    category: str = "simple_obligation",
    normative: bool = True,
    cmin: int = 1,
    cmax: int | None = None,
    types: list[str] | None = None,
    families: list[dict[str, str]] | None = None,
    markers: list[str] | None = None,
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
        "threshold_markers": markers,
        "characterization_notes": "synthetic test specimen",
        "claim_ceiling": "test fixture only",
    }


def corpus_document(*specimens: dict[str, Any]) -> dict[str, Any]:
    return {
        "corpus_id": "TEST-CORPUS",
        "corpus_version": "v0.0",
        "claim_ceiling": "test fixture only",
        "specimen_count": len(specimens),
        "specimens": list(specimens),
    }


def write_corpus(harness: ModuleType, tmp_path: Path, *specimens: dict[str, Any]) -> Path:
    path = tmp_path / "CORPUS.json"
    path.write_bytes(harness.canonical_json_bytes(corpus_document(*specimens)))
    return path


# The harness is loaded by path, so its Corpus dataclass is not statically importable.
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


# --------------------------------------------------------------------------
# Corpus loading
# --------------------------------------------------------------------------


def test_corpus_loads_and_validates_shape(harness: ModuleType, tmp_path: Path) -> None:
    path = write_corpus(harness, tmp_path, specimen_dict("T-1"), specimen_dict("T-2"))
    corpus = harness.load_corpus(path)
    assert [item.specimen_id for item in corpus.specimens] == ["T-1", "T-2"]
    assert corpus.corpus_id == "TEST-CORPUS"


def test_duplicate_specimen_ids_are_rejected(harness: ModuleType, tmp_path: Path) -> None:
    path = write_corpus(harness, tmp_path, specimen_dict("T-1"), specimen_dict("T-1"))
    with pytest.raises(harness.CharacterizationError, match="duplicate specimen ids"):
        harness.load_corpus(path)


def test_declared_specimen_count_must_match(harness: ModuleType, tmp_path: Path) -> None:
    document = corpus_document(specimen_dict("T-1"))
    document["specimen_count"] = 9
    path = tmp_path / "CORPUS.json"
    path.write_bytes(harness.canonical_json_bytes(document))
    with pytest.raises(harness.CharacterizationError, match="specimen_count"):
        harness.load_corpus(path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_text", "   ", "must not be empty"),
        ("normative_expected", "yes", "normative_expected"),
        ("expected_candidate_count_min", -1, "expected_candidate_count_min"),
        ("expected_candidate_count_max", "two", "expected_candidate_count_max"),
        ("acceptable_unit_types", [1, 2], "acceptable_unit_types"),
        ("category", 7, "string category"),
    ],
)
def test_malformed_specimen_fields_are_rejected(
    harness: ModuleType, tmp_path: Path, field: str, value: object, match: str
) -> None:
    specimen = specimen_dict("T-1")
    specimen[field] = value
    path = write_corpus(harness, tmp_path, specimen)
    with pytest.raises(harness.CharacterizationError, match=match):
        harness.load_corpus(path)


def test_corpus_digest_is_the_digest_of_the_exact_bytes(
    harness: ModuleType, tmp_path: Path
) -> None:
    path = write_corpus(harness, tmp_path, specimen_dict("T-1"))
    corpus = harness.load_corpus(path)
    assert corpus.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_specimen_expectations_are_immutable(harness: ModuleType, tmp_path: Path) -> None:
    """An evaluator cannot rewrite an expectation part-way through a run."""
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    with pytest.raises(AttributeError):
        corpus.specimens[0].normative_expected = False
    with pytest.raises(AttributeError):
        corpus.specimens[0].expected_candidate_count_min = 0


# --------------------------------------------------------------------------
# Corpus integrity gate
# --------------------------------------------------------------------------


def test_intact_corpus_passes_the_integrity_gate(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    freeze = write_freeze(harness, tmp_path, corpus)
    state, findings = harness.resolve_corpus_integrity(corpus, freeze, allow_drift=False)
    assert state == harness.CORPUS_INTACT
    assert findings == []


def test_corpus_hash_drift_refuses_the_run(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    freeze = write_freeze(harness, tmp_path, corpus)
    mutated = write_corpus(harness, tmp_path, specimen_dict("T-1", text="A different rule."))
    drifted = harness.load_corpus(mutated)
    with pytest.raises(harness.CorpusIntegrityError, match="refusing to run"):
        harness.resolve_corpus_integrity(drifted, freeze, allow_drift=False)


def test_corpus_drift_can_be_acknowledged_but_is_stamped(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    freeze = write_freeze(harness, tmp_path, corpus)
    drifted = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("T-1", text="A different rule."))
    )
    state, findings = harness.resolve_corpus_integrity(drifted, freeze, allow_drift=True)
    assert state == harness.CORPUS_DRIFT_ACKNOWLEDGED
    assert any("sha256 drift" in finding for finding in findings)
    assert any("source text drift for T-1" in finding for finding in findings)


def test_cli_exits_non_zero_on_corpus_drift_without_contacting_a_provider(
    harness: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    freeze = write_freeze(harness, tmp_path, corpus)
    mutated = tmp_path / "MUTATED.json"
    mutated.write_bytes(
        harness.canonical_json_bytes(
            corpus_document(specimen_dict("T-1", text="A different rule."))
        )
    )
    code = harness.main(
        ["--corpus", str(mutated), "--freeze", str(freeze), "--output", str(tmp_path / "r.json")]
    )
    assert code == 1
    assert "FAIL corpus integrity" in capsys.readouterr().out
    assert not (tmp_path / "r.json").exists()


# --------------------------------------------------------------------------
# Semantic projection
# --------------------------------------------------------------------------


def test_projection_keeps_only_model_proposed_fields(harness: ModuleType) -> None:
    candidate = {
        "unit_id": "cnu-deadbeef",
        "unit_type": "mandate",
        "actor": "CFO",
        "action": "approve",
        "object": "payment above $10,000",
        "target": "the Treasury",
        "conditions": [],
        "exceptions": [],
        "evidence_requirements": [],
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "source_anchors": [{"anchor_id": "A-1"}],
    }
    projection = harness.semantic_projection(candidate)
    assert list(projection) == list(harness.SEMANTIC_FIELDS)
    for excluded in harness.OIC_CONTROLLED_FIELDS:
        assert excluded not in projection


def test_projection_fails_loudly_on_a_missing_semantic_field(harness: ModuleType) -> None:
    with pytest.raises(harness.CharacterizationError, match="missing semantic fields"):
        harness.semantic_projection({"unit_type": "mandate"})


def _blank_projection(harness: ModuleType) -> dict[str, Any]:
    """An empty semantic projection: lists for the array fields, null for the rest."""
    listish = {"conditions", "exceptions", "evidence_requirements"}
    return {name: ([] if name in listish else None) for name in harness.SEMANTIC_FIELDS}


def test_semantic_hash_is_deterministic_and_ignores_key_order(harness: ModuleType) -> None:
    first = {**_blank_projection(harness), "unit_type": "mandate"}
    reordered = dict(reversed(list(first.items())))
    assert harness.semantic_hash([first]) == harness.semantic_hash([reordered])
    assert harness.semantic_hash([first]) == harness.semantic_hash([first])


def test_semantic_hash_separates_genuinely_different_answers(harness: ModuleType) -> None:
    """mandate and obligation must not collapse into one another."""
    base = _blank_projection(harness)
    mandate = {**base, "unit_type": "mandate"}
    obligation = {**base, "unit_type": "obligation"}
    assert harness.semantic_hash([mandate]) != harness.semantic_hash([obligation])
    threshold_in_object = {**mandate, "object": "payment above $10,000"}
    threshold_in_conditions = {**mandate, "conditions": ["payment above $10,000"]}
    assert harness.semantic_hash([threshold_in_object]) != harness.semantic_hash(
        [threshold_in_conditions]
    )


def test_semantic_hash_is_order_sensitive(harness: ModuleType) -> None:
    base = _blank_projection(harness)
    one = {**base, "unit_type": "mandate"}
    two = {**base, "unit_type": "prohibition"}
    assert harness.semantic_hash([one, two]) != harness.semantic_hash([two, one])


# --------------------------------------------------------------------------
# Execution and grouping
# --------------------------------------------------------------------------


def test_anchor_is_caller_controlled_and_derived_from_the_specimen(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    specimen = corpus.specimens[0]
    anchor = harness.specimen_anchor(specimen, corpus=corpus)
    assert anchor["node_id"] == "T-1"
    assert anchor["content_hash"] == f"sha256:{specimen.source_sha256}"
    assert anchor["quote"] == specimen.source_text


def test_repeated_runs_are_grouped_by_specimen_in_run_order(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("T-1"), specimen_dict("T-2", text="No duty."))
    )
    attempts = harness.run_corpus(corpus, provider=ScriptedProvider(EMPTY), runs_per_specimen=3)
    assert len(attempts) == 6
    grouped = harness.group_by_specimen(attempts)
    assert sorted(grouped) == ["T-1", "T-2"]
    for group in grouped.values():
        assert [item.run_index for item in group] == [1, 2, 3]


def test_runs_per_specimen_must_be_at_least_one(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    with pytest.raises(harness.CharacterizationError, match="at least 1"):
        harness.run_corpus(corpus, provider=ScriptedProvider(EMPTY), runs_per_specimen=0)


# --------------------------------------------------------------------------
# Boundary errors are preserved, never repaired
# --------------------------------------------------------------------------


def test_a_bare_root_response_is_recorded_as_a_boundary_rejection(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    bare = '{"unit_type":"mandate","actor":"CFO","action":"approve"}'
    attempts = harness.run_corpus(corpus, provider=ScriptedProvider(bare), runs_per_specimen=2)
    for attempt in attempts:
        assert attempt.boundary_result == harness.BOUNDARY_REJECTED
        assert attempt.error_type == "CandidateBoundaryError"
        assert "unexpected root keys" in (attempt.error_message or "")
        assert attempt.candidates == ()
        assert attempt.candidate_count is None


def test_a_forbidden_authority_field_is_not_stripped_to_rescue_the_response(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    claim = '{"candidates":[{"unit_type":"mandate","allow":true}]}'
    attempts = harness.run_corpus(corpus, provider=ScriptedProvider(claim), runs_per_specimen=1)
    assert attempts[0].boundary_result == harness.BOUNDARY_REJECTED
    assert "authority-controlled" in (attempts[0].error_message or "")
    assert attempts[0].candidates == ()


def test_a_provider_transport_error_is_not_counted_as_a_boundary_rejection(
    harness: ModuleType, tmp_path: Path
) -> None:
    from oic.model_provider import ModelProviderError

    class BrokenProvider:
        provider_name = "fake-provider"

        def complete(self, request: ModelRequest) -> ModelResponse:
            raise ModelProviderError("NVIDIA NIM HTTP error: 503")

    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(corpus, provider=BrokenProvider(), runs_per_specimen=2)
    metric = harness.metric_boundary_acceptance(attempts)
    assert metric["provider_errors"] == 2
    assert metric["boundary_rejected"] == 0
    assert metric["acceptance_rate_over_adjudicated"] is None


def test_boundary_errors_are_carried_into_the_metric(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider('{"candidates":"not-an-array"}'), runs_per_specimen=1
    )
    metric = harness.metric_boundary_acceptance(attempts)
    assert metric["boundary_accepted"] == 0
    assert metric["boundary_rejected"] == 1
    assert metric["boundary_errors"][0]["specimen_id"] == "T-1"
    assert metric["boundary_errors"][0]["error_message"]


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def test_presence_misses_are_counted_for_positive_specimens(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(
            harness, tmp_path, specimen_dict("T-1"), specimen_dict("T-2", text="Rule two.")
        )
    )
    provider = KeyedProvider({"Rule two.": EMPTY}, default=candidate_json())
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=2)
    metric = harness.metric_normative_presence(corpus, harness.group_by_specimen(attempts))
    assert metric["accepted_runs"] == 4
    assert metric["runs_meeting_minimum"] == 2
    assert metric["presence_misses"] == 2
    results = {item["specimen_id"]: item["result"] for item in metric["per_specimen"]}
    assert results == {
        "T-1": harness.EXPECTED_PRESENCE_OBSERVED,
        "T-2": harness.PRESENCE_MISS,
    }


def test_false_positives_are_counted_for_negative_specimens(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(
            harness,
            tmp_path,
            specimen_dict(
                "N-1", text="The office has twelve staff.", normative=False, cmin=0, cmax=0
            ),
            specimen_dict("N-2", text="The portal was upgraded.", normative=False, cmin=0, cmax=0),
        )
    )
    provider = KeyedProvider({"twelve staff": candidate_json()}, default=EMPTY)
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=2)
    metric = harness.metric_negative_controls(corpus, harness.group_by_specimen(attempts))
    assert metric["negative_control_specimens"] == 2
    assert metric["accepted_runs"] == 4
    assert metric["false_positive_runs"] == 2
    assert metric["false_positive_rate"] == 0.5
    results = {item["specimen_id"]: item["result"] for item in metric["per_specimen"]}
    assert results == {
        "N-1": harness.FALSE_POSITIVE_OBSERVED,
        "N-2": harness.EXPECTED_ABSENCE_OBSERVED,
    }


def test_candidate_count_stability_reports_variance(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    provider = ScriptedProvider(candidate_json(), EMPTY, candidate_json())
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=3)
    metric = harness.metric_candidate_count_stability(harness.group_by_specimen(attempts))
    record = metric["per_specimen"][0]
    assert record["count_distribution"] == {"0": 1, "1": 2}
    assert record["result"] == harness.REPEAT_VARIANT


def test_candidate_count_stability_reports_stability(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json()), runs_per_specimen=3
    )
    metric = harness.metric_candidate_count_stability(harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["result"] == harness.REPEAT_STABLE


def test_unit_types_outside_the_preregistered_set_are_flagged_not_remapped(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("T-1", types=["obligation"]))
    )
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json(unit_type="mandate")), runs_per_specimen=2
    )
    metric = harness.metric_unit_type_observation(corpus, harness.group_by_specimen(attempts))
    record = metric["per_specimen"][0]
    assert record["observed_unit_type_distribution"] == {"mandate": 2}
    assert record["types_outside_preregistered_set"] == ["mandate"]
    assert record["result"] == harness.TYPE_OUTSIDE_PREREGISTERED_SET


def test_unit_types_inside_the_preregistered_set_are_reported_as_such(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("T-1", types=["mandate", "obligation"]))
    )
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json(unit_type="mandate")), runs_per_specimen=1
    )
    metric = harness.metric_unit_type_observation(corpus, harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["result"] == harness.TYPE_WITHIN_PREREGISTERED_SET


def test_semantic_stability_distinguishes_two_different_decompositions(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("T-1", text=THRESHOLD_SOURCE))
    )
    provider = ScriptedProvider(
        candidate_json(unit_type="mandate", object="payment above $10,000"),
        candidate_json(unit_type="mandate", conditions=["payment above $10,000"]),
    )
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=2)
    metric = harness.metric_semantic_stability(harness.group_by_specimen(attempts))
    record = metric["per_specimen"][0]
    assert record["distinct_semantic_hashes"] == 2
    assert record["result"] == harness.REPEAT_VARIANT
    assert metric["excluded_fields"] == list(harness.OIC_CONTROLLED_FIELDS)


def test_semantic_stability_reports_identical_answers_as_stable(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json(actor="Treasurer")), runs_per_specimen=3
    )
    metric = harness.metric_semantic_stability(harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["result"] == harness.REPEAT_STABLE


THRESHOLD_SOURCE = "A payment above $10,000 requires approval, approve above $10,000."


@pytest.mark.parametrize(
    ("fields", "expected_key"),
    [
        ({"object": "payment above $10,000"}, "THRESHOLD_IN_OBJECT"),
        ({"conditions": ["above $10,000"]}, "THRESHOLD_IN_CONDITIONS"),
        (
            {"object": "payment above $10,000", "conditions": ["above $10,000"]},
            "THRESHOLD_IN_OBJECT_AND_CONDITIONS",
        ),
        ({"action": "approve above $10,000"}, "THRESHOLD_IN_OTHER_SEMANTIC_FIELD:action"),
        ({"object": "payment"}, "THRESHOLD_ABSENT_FROM_CANDIDATE"),
    ],
)
def test_threshold_placement_is_observed_wherever_it_lands(
    harness: ModuleType, tmp_path: Path, fields: dict[str, object], expected_key: str
) -> None:
    corpus = harness.load_corpus(
        write_corpus(
            harness,
            tmp_path,
            specimen_dict("T-1", text=THRESHOLD_SOURCE, markers=["$10,000"]),
        )
    )
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json(**fields)), runs_per_specimen=1
    )
    metric = harness.metric_threshold_placement(corpus, harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["placement_distribution"] == {expected_key: 1}


def test_specimens_without_threshold_markers_are_not_reported(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json()), runs_per_specimen=1
    )
    metric = harness.metric_threshold_placement(corpus, harness.group_by_specimen(attempts))
    assert metric["per_specimen"] == []


def test_source_standing_family_disagreement_is_reported_not_repaired(
    harness: ModuleType, tmp_path: Path
) -> None:
    baseline = specimen_dict(
        "S-1",
        text="A payment above $10,000 requires CFO approval.",
        families=[{"family_id": "F", "family_kind": "source_standing", "role": "baseline"}],
    )
    variant = specimen_dict(
        "S-2",
        text="DRAFT. A payment above $10,000 requires CFO approval.",
        families=[{"family_id": "F", "family_kind": "source_standing", "role": "draft"}],
    )
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, baseline, variant))
    provider = KeyedProvider({"DRAFT.": EMPTY}, default=candidate_json())
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=1)
    metric = harness.metric_source_standing_invariance(corpus, harness.group_by_specimen(attempts))
    family = metric["families"][0]
    assert family["family_id"] == "F"
    assert family["presence_agreement"] is False
    assert family["count_set_agreement"] is False
    roles = {member["role"]: member["candidate_presence_observed"] for member in family["members"]}
    assert roles == {"baseline": True, "draft": False}


def test_source_standing_family_agreement_is_reported(harness: ModuleType, tmp_path: Path) -> None:
    members = [
        specimen_dict(
            f"S-{index}",
            text=f"{prefix}A payment above $10,000 requires CFO approval.",
            families=[{"family_id": "F", "family_kind": "source_standing", "role": role}],
        )
        for index, (prefix, role) in enumerate(
            [("", "baseline"), ("DRAFT. ", "draft"), ("SYNTHETIC. ", "synthetic")], start=1
        )
    ]
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, *members))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json(actor="CFO")), runs_per_specimen=2
    )
    family = harness.metric_source_standing_invariance(corpus, harness.group_by_specimen(attempts))[
        "families"
    ][0]
    assert family["presence_agreement"] is True
    assert family["count_set_agreement"] is True
    assert family["unit_type_set_agreement"] is True
    assert family["semantic_hash_set_agreement"] is True


def test_paraphrase_family_difference_is_reported_without_claiming_equivalence(
    harness: ModuleType, tmp_path: Path
) -> None:
    members = [
        specimen_dict(
            "P-1",
            text="A payment above $10,000 requires CFO approval.",
            families=[{"family_id": "P", "family_kind": "paraphrase", "role": "baseline"}],
        ),
        specimen_dict(
            "P-2",
            text="CFO approval is required for payments over $10,000.",
            families=[{"family_id": "P", "family_kind": "paraphrase", "role": "variant_a"}],
        ),
    ]
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, *members))
    provider = KeyedProvider(
        {"required for payments": candidate_json(unit_type="obligation")},
        default=candidate_json(unit_type="mandate"),
    )
    attempts = harness.run_corpus(corpus, provider=provider, runs_per_specimen=1)
    metric = harness.metric_paraphrase_families(corpus, harness.group_by_specimen(attempts))
    family = metric["families"][0]
    assert family["unit_type_set_agreement"] is False
    assert family["semantic_hash_set_agreement"] is False
    assert "does not establish that they are" in metric["note"]


def test_families_of_the_other_kind_are_not_mixed_in(harness: ModuleType, tmp_path: Path) -> None:
    specimen = specimen_dict(
        "X-1",
        families=[{"family_id": "P", "family_kind": "paraphrase", "role": "baseline"}],
    )
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen))
    attempts = harness.run_corpus(corpus, provider=ScriptedProvider(EMPTY), runs_per_specimen=1)
    grouped = harness.group_by_specimen(attempts)
    assert harness.metric_source_standing_invariance(corpus, grouped)["families"] == []
    assert len(harness.metric_paraphrase_families(corpus, grouped)["families"]) == 1


def test_multi_unit_collapse_is_recorded_not_split(harness: ModuleType, tmp_path: Path) -> None:
    corpus = harness.load_corpus(
        write_corpus(harness, tmp_path, specimen_dict("M-1", cmin=2, category="multi_unit"))
    )
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(candidate_json()), runs_per_specimen=3
    )
    metric = harness.metric_multi_unit(corpus, harness.group_by_specimen(attempts))
    record = metric["per_specimen"][0]
    assert record["runs_returning_a_single_unit"] == 3
    assert record["runs_returning_separated_units"] == 0
    assert record["count_distribution"] == {"1": 3}


def test_single_unit_specimens_are_absent_from_the_multi_unit_metric(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    attempts = harness.run_corpus(corpus, provider=ScriptedProvider(EMPTY), runs_per_specimen=1)
    metric = harness.metric_multi_unit(corpus, harness.group_by_specimen(attempts))
    assert metric["per_specimen"] == []


# --------------------------------------------------------------------------
# Receipt
# --------------------------------------------------------------------------


def _receipt(
    harness: ModuleType,
    tmp_path: Path,
    *specimens: dict[str, Any],
    provider: ModelProvider | None = None,
    runs: int = 2,
) -> dict[str, Any]:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, *specimens))
    attempts = harness.run_corpus(
        corpus, provider=provider or ScriptedProvider(candidate_json()), runs_per_specimen=runs
    )
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=runs,
        provider_name="fake-provider",
        model="fake-model",
        corpus_integrity=harness.CORPUS_INTACT,
        corpus_freeze_relpath="FREEZE.json",
        integrity_findings=[],
        implementation={"commit": "0" * 40, "worktree_clean": True},
    )
    return cast("dict[str, Any]", receipt)


def test_receipt_carries_every_required_section(harness: ModuleType, tmp_path: Path) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    assert receipt["work_order"] == "OIC-CANDIDATE-SEMANTICS-001"
    assert receipt["independent_validation_claim"] is False
    assert receipt["implementation_git_sha"] == "0" * 40
    assert receipt["corpus"]["specimen_ids"] == ["T-1"]
    assert receipt["corpus"]["corpus_sha256"]
    assert receipt["run_conditions"]["runs_per_specimen"] == 2
    assert receipt["run_conditions"]["total_requests_attempted"] == 2
    assert set(receipt["metrics"]) == {
        "a_boundary_acceptance",
        "b_normative_presence",
        "c_negative_controls",
        "d_candidate_count_stability",
        "e_unit_type_observation",
        "f_semantic_decomposition_stability",
        "g_source_standing_invariance",
        "h_paraphrase_families",
        "i_threshold_placement",
        "j_multi_unit_behaviour",
        "k_unsupported_actor",
        "l_explicit_condition_preservation",
        "m_material_qualifier_preservation",
        "n_advisory_presence",
        "o_target_preservation",
        "p_evidence_duty_typing",
        "q_operative_predicate",
    }
    assert len(receipt["evidence"]) == 2
    assert receipt["evidence"][0]["semantic_projection_sha256"]


def test_receipt_keeps_engineering_gates_separate_from_semantic_observations(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    gates = receipt["engineering_gates"]
    assert gates["corpus_integrity"] == harness.CORPUS_INTACT
    assert gates["harness_executed_every_planned_request"] is True
    assert set(gates) & set(receipt["metrics"]) == set()


def test_receipt_never_self_adjudicates_institutional_correctness(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    for banned in (
        '"ADMITTED"',
        '"AUTHORIZED"',
        '"COMPLIANT"',
        '"LEGALLY_VALID"',
        '"CORRECT_POLICY"',
        '"ALLOW"',
        '"DENY"',
    ):
        assert banned not in serialized, banned
    assert "establishes no semantic correctness" in receipt["claim_ceiling"]


def test_receipt_records_the_run_condition_caveat(harness: ModuleType, tmp_path: Path) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"), runs=3)
    assert "not a statistically sufficient sample" in receipt["run_conditions"]["statistical_note"]


def test_receipt_contains_no_credential(
    harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = "nvapi-TEST-SENTINEL-DO-NOT-COMMIT-000000"
    monkeypatch.setenv("NVIDIA_API_KEY", sentinel)
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    assert sentinel not in serialized
    assert "NVIDIA_API_KEY" not in serialized
    assert "Authorization" not in serialized
    assert "Bearer" not in serialized


def test_receipt_preserves_boundary_rejections_in_evidence(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(
        harness,
        tmp_path,
        specimen_dict("T-1"),
        provider=ScriptedProvider('{"unit_type":"mandate"}'),
    )
    assert receipt["engineering_summary"]["boundary_rejected"] == 2
    assert receipt["engineering_summary"]["boundary_accepted"] == 0
    for record in receipt["evidence"]:
        assert record["boundary_result"] == harness.BOUNDARY_REJECTED
        assert record["error_type"] == "CandidateBoundaryError"


def test_receipt_is_canonical_json_and_round_trips(harness: ModuleType, tmp_path: Path) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    body = harness.canonical_json_bytes(receipt)
    assert body.endswith(b"\n")
    assert json.loads(body.decode("utf-8")) == receipt


# --------------------------------------------------------------------------
# Live runner: credential handling and network discipline
# --------------------------------------------------------------------------


def test_live_provider_requires_the_environment_credential_before_any_socket(
    harness: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No credential means a clean provider error, not a network attempt.

    The suite disables sockets, so a harness that tried to connect before checking the
    credential would raise NetworkAccessAttemptedError instead and fail this test.
    """
    from oic.model_provider import ModelProviderError
    from oic.nvidia_nim import NvidiaNimConfig, NvidiaNimProvider

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen_dict("T-1")))
    provider = NvidiaNimProvider(NvidiaNimConfig())

    # The adapter itself refuses before opening anything.
    with pytest.raises(ModelProviderError, match="NVIDIA_API_KEY"):
        provider.complete(ModelRequest(system_prompt="s", user_prompt="u", response_format=None))

    # Through the harness the same refusal is recorded, not raised and not retried.
    attempt = harness.run_attempt(
        corpus.specimens[0], corpus=corpus, provider=provider, run_index=1
    )
    assert attempt.boundary_result == harness.PROVIDER_ERROR
    assert attempt.error_type == "ModelProviderError"
    assert "NVIDIA_API_KEY" in (attempt.error_message or "")
    assert attempt.candidates == ()


def test_harness_module_reads_no_credential_of_its_own(repo_root: Path) -> None:
    source = (repo_root / MODULE_RELPATH).read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "api_key" not in source


def test_cli_defaults_point_at_the_frozen_corpus_and_an_untracked_output(
    harness: ModuleType,
) -> None:
    args = harness.build_parser().parse_args([])
    assert args.corpus == harness.DEFAULT_CORPUS
    assert args.freeze == harness.DEFAULT_FREEZE
    assert args.runs_per_specimen == 3
    assert args.model == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert args.allow_corpus_drift is False
    assert str(args.output).startswith(".local/")


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-002 source-grounding metrics
#
# Each is exercised in both directions: the observation must fire when the condition it
# names is present, and must stay quiet when it is not. A metric that always reported a
# problem would be as useless as one that never did.
# --------------------------------------------------------------------------

PASSIVE = "Invoices are paid within thirty days of receipt."
TARGETED = "The Secretary shall forward the minutes to each committee member."
TRIGGERED = "If the vendor fails to deliver within five business days, the order is cancelled."


def _grounding_specimen(specimen_id: str, text: str, **overrides: object) -> dict[str, Any]:
    record = specimen_dict(specimen_id, text=text)
    record.update(overrides)
    return record


def _run(
    harness: ModuleType, tmp_path: Path, specimen: dict[str, Any], content: str, runs: int = 1
) -> tuple[Any, dict[str, list[Any]]]:
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen))
    attempts = harness.run_corpus(
        corpus, provider=ScriptedProvider(content), runs_per_specimen=runs
    )
    return corpus, harness.group_by_specimen(attempts)


def test_k_reports_an_actor_asserted_where_the_source_names_none(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen("T-1", PASSIVE, actor_explicitly_named=False)
    corpus, grouped = _run(
        harness, tmp_path, specimen, candidate_json(actor="Invoices", action="are paid"), runs=2
    )
    metric = harness.metric_unsupported_actor(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["candidates_asserting_an_actor"] == 2
    assert record["asserted_actor_values"] == ["Invoices"]
    assert record["result"] == harness.ACTOR_ASSERTED_WHERE_SOURCE_NAMES_NONE
    assert metric["candidates_asserting_an_actor"] == 2


def test_k_stays_quiet_when_the_actor_is_null_as_preregistered(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen("T-1", PASSIVE, actor_explicitly_named=False)
    corpus, grouped = _run(harness, tmp_path, specimen, candidate_json(action="are paid"), runs=2)
    metric = harness.metric_unsupported_actor(corpus, grouped)
    assert metric["per_specimen"][0]["result"] == harness.ACTOR_ABSENT_AS_PREREGISTERED
    assert metric["candidates_asserting_an_actor"] == 0


def test_k_ignores_specimens_whose_source_does_name_an_actor(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen("T-1", TARGETED, actor_explicitly_named=True)
    corpus, grouped = _run(
        harness, tmp_path, specimen, candidate_json(actor="The Secretary", action="shall forward")
    )
    assert harness.metric_unsupported_actor(corpus, grouped)["per_specimen"] == []


def test_an_entirely_invented_actor_never_reaches_metric_k(
    harness: ModuleType, tmp_path: Path
) -> None:
    """It fails the boundary first, and is counted as a grounding rejection instead."""
    specimen = _grounding_specimen("T-1", PASSIVE, actor_explicitly_named=False)
    corpus = harness.load_corpus(write_corpus(harness, tmp_path, specimen))
    attempts = harness.run_corpus(
        corpus,
        provider=ScriptedProvider(candidate_json(actor="accounts payable")),
        runs_per_specimen=2,
    )
    boundary = harness.metric_boundary_acceptance(attempts)
    assert boundary["boundary_rejected"] == 2
    assert boundary["rejection_error_types"] == {"CandidateGroundingError": 2}
    metric = harness.metric_unsupported_actor(corpus, harness.group_by_specimen(attempts))
    assert metric["per_specimen"][0]["result"] == harness.NOT_OBSERVED


def test_l_counts_an_omitted_explicit_condition(harness: ModuleType, tmp_path: Path) -> None:
    specimen = _grounding_specimen(
        "T-1", PASSIVE, required_condition_spans=["within thirty days of receipt"]
    )
    corpus, grouped = _run(harness, tmp_path, specimen, candidate_json(action="are paid"), runs=3)
    metric = harness.metric_condition_preservation(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["candidates_omitting_the_element"] == 3
    assert record["result"] == harness.ELEMENT_OMITTED


def test_l_accepts_any_declared_rendering_of_the_same_element(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1",
        PASSIVE,
        required_condition_spans=["within thirty days of receipt", "thirty days"],
    )
    corpus, grouped = _run(
        harness,
        tmp_path,
        specimen,
        candidate_json(action="are paid", conditions=["thirty days"]),
    )
    record = harness.metric_condition_preservation(corpus, grouped)["per_specimen"][0]
    assert record["result"] == harness.ELEMENT_PRESERVED
    assert record["matched_renderings"] == ["thirty days"]


def test_l_looks_only_in_conditions(harness: ModuleType, tmp_path: Path) -> None:
    """A qualifier parked in object is not a preserved condition."""
    specimen = _grounding_specimen("T-1", PASSIVE, required_condition_spans=["thirty days"])
    corpus, grouped = _run(
        harness, tmp_path, specimen, candidate_json(object="Invoices", action="thirty days")
    )
    assert (
        harness.metric_condition_preservation(corpus, grouped)["per_specimen"][0]["result"]
        == harness.ELEMENT_OMITTED
    )


def test_m_counts_a_dropped_material_qualifier(harness: ModuleType, tmp_path: Path) -> None:
    specimen = _grounding_specimen("T-1", THRESHOLD_SOURCE, material_qualifier_spans=["$10,000"])
    corpus, grouped = _run(harness, tmp_path, specimen, candidate_json(object="payment"), runs=2)
    record = harness.metric_material_qualifier_preservation(corpus, grouped)["per_specimen"][0]
    assert record["candidates_omitting_the_element"] == 2
    assert record["result"] == harness.ELEMENT_OMITTED


def test_m_accepts_the_qualifier_in_any_textual_role(harness: ModuleType, tmp_path: Path) -> None:
    """Where a threshold lands is metric I's business. M only asks whether it survived."""
    specimen = _grounding_specimen("T-1", THRESHOLD_SOURCE, material_qualifier_spans=["$10,000"])
    for fields in (
        {"object": "payment above $10,000"},
        {"conditions": ["above $10,000"]},
        {"action": "approve above $10,000"},
    ):
        corpus, grouped = _run(harness, tmp_path, specimen, candidate_json(**fields))
        record = harness.metric_material_qualifier_preservation(corpus, grouped)["per_specimen"][0]
        assert record["result"] == harness.ELEMENT_PRESERVED, fields


def test_n_isolates_advisory_presence_misses(harness: ModuleType, tmp_path: Path) -> None:
    specimen = _grounding_specimen(
        "T-1", "Units are encouraged to consolidate purchases.", category="advisory"
    )
    corpus, grouped = _run(harness, tmp_path, specimen, EMPTY, runs=3)
    metric = harness.metric_advisory_presence(corpus, grouped)
    assert metric["advisory_specimens"] == 1
    assert metric["presence_misses"] == 3
    assert metric["per_specimen"][0]["result"] == harness.PRESENCE_MISS


def test_n_reports_advisory_material_that_was_found(harness: ModuleType, tmp_path: Path) -> None:
    specimen = _grounding_specimen(
        "T-1", "Units are encouraged to consolidate purchases.", category="advisory"
    )
    corpus, grouped = _run(
        harness,
        tmp_path,
        specimen,
        candidate_json(unit_type="advisory", action="are encouraged"),
        runs=2,
    )
    metric = harness.metric_advisory_presence(corpus, grouped)
    assert metric["presence_misses"] == 0
    assert metric["per_specimen"][0]["observed_unit_types"] == ["advisory"]
    assert metric["per_specimen"][0]["result"] == harness.EXPECTED_PRESENCE_OBSERVED


def test_o_reports_an_explicit_target_carried_in_target(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1",
        TARGETED,
        target_explicitly_named=True,
        expected_target_spans=["each committee member"],
    )
    corpus, grouped = _run(
        harness,
        tmp_path,
        specimen,
        candidate_json(action="shall forward", target="each committee member"),
        runs=2,
    )
    record = harness.metric_target_preservation(corpus, grouped)["per_specimen"][0]
    assert record["candidates_carrying_it_in_target"] == 2
    assert record["candidates_dropping_it_entirely"] == 0
    assert record["result"] == harness.TARGET_PRESERVED


def test_o_separates_a_target_parked_in_another_role_from_one_that_vanished(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1",
        TARGETED,
        target_explicitly_named=True,
        expected_target_spans=["each committee member"],
    )
    corpus, grouped = _run(
        harness, tmp_path, specimen, candidate_json(object="each committee member")
    )
    parked = harness.metric_target_preservation(corpus, grouped)["per_specimen"][0]
    assert parked["candidates_carrying_it_in_another_role"] == 1
    assert parked["candidates_dropping_it_entirely"] == 0
    assert parked["result"] == harness.TARGET_OMITTED

    corpus, grouped = _run(harness, tmp_path, specimen, candidate_json(action="shall forward"))
    dropped = harness.metric_target_preservation(corpus, grouped)["per_specimen"][0]
    assert dropped["candidates_carrying_it_in_another_role"] == 0
    assert dropped["candidates_dropping_it_entirely"] == 1


def test_p_reports_evidence_duty_typing_alongside_action_and_requirements(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1",
        "The unit must retain the original receipt for seven years.",
        category="evidence_duty",
    )
    corpus, grouped = _run(
        harness,
        tmp_path,
        specimen,
        candidate_json(
            unit_type="condition", action=None, evidence_requirements=["the original receipt"]
        ),
        runs=3,
    )
    record = harness.metric_evidence_duty_typing(corpus, grouped)["per_specimen"][0]
    assert record["unit_type_distribution"] == {"condition": 3}
    assert record["candidates_typed_evidence_duty"] == 0
    assert record["candidates_populating_evidence_requirements"] == 3
    assert record["candidates_with_a_null_action"] == 3


def test_q_reports_a_trigger_recorded_as_the_operative_action(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1", TRIGGERED, non_operative_predicate_spans=["fails to deliver"]
    )
    corpus, grouped = _run(
        harness, tmp_path, specimen, candidate_json(action="fails to deliver"), runs=2
    )
    metric = harness.metric_operative_predicate(corpus, grouped)
    record = metric["per_specimen"][0]
    assert record["candidates_recording_the_trigger_as_action"] == 2
    assert record["result"] == harness.TRIGGER_RECORDED_AS_ACTION
    assert metric["candidates_recording_the_trigger_as_action"] == 2


def test_q_stays_quiet_when_the_operative_act_is_recorded(
    harness: ModuleType, tmp_path: Path
) -> None:
    specimen = _grounding_specimen(
        "T-1", TRIGGERED, non_operative_predicate_spans=["fails to deliver"]
    )
    corpus, grouped = _run(
        harness,
        tmp_path,
        specimen,
        candidate_json(action="is cancelled", conditions=["fails to deliver"]),
    )
    record = harness.metric_operative_predicate(corpus, grouped)["per_specimen"][0]
    assert record["result"] == harness.TRIGGER_NOT_RECORDED_AS_ACTION
    assert record["candidates_recording_the_trigger_as_action"] == 0


# --------------------------------------------------------------------------
# Receipt: measure classification and the demotion of exact semantic hashing
# --------------------------------------------------------------------------


def test_receipt_classifies_measures_and_demotes_exact_semantic_hashing(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    classification = receipt["measure_classification"]
    assert "f_semantic_decomposition_stability" in classification["secondary"]
    assert "f_semantic_decomposition_stability" not in classification["primary"]
    assert "f_semantic_decomposition_stability" in classification["demoted"]
    assert "k_unsupported_actor" in classification["primary"]
    assert "l_explicit_condition_preservation" in classification["primary"]
    assert "n_advisory_presence" in classification["primary"]
    assert "o_target_preservation" in classification["primary"]
    named = set(classification["primary"]) | set(classification["secondary"])
    assert named == set(receipt["metrics"])
    assert "Institutional IR" in classification["demoted"]["f_semantic_decomposition_stability"]


def test_paraphrase_metric_states_hash_agreement_is_not_required_here(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    metric = receipt["metrics"]["h_paraphrase_families"]
    assert metric["not_required_at_candidate_stage"] == ["semantic_hash_set_agreement"]
    assert metric["candidate_stage_invariants"] == [
        "presence_agreement",
        "count_set_agreement",
        "unit_type_set_agreement",
    ]
    assert "Normalizing them is Institutional IR's job" in metric["note"]


def test_receipt_summary_surfaces_every_grounding_headline(
    harness: ModuleType, tmp_path: Path
) -> None:
    receipt = _receipt(harness, tmp_path, specimen_dict("T-1"))
    summary = receipt["engineering_summary"]
    for key in (
        "candidates_asserting_an_actor_where_source_names_none",
        "candidates_omitting_an_explicit_condition",
        "candidates_omitting_a_material_qualifier",
        "advisory_presence_misses",
        "candidates_dropping_an_explicit_target",
        "candidates_recording_a_trigger_as_the_action",
    ):
        assert key in summary, key


def test_semantic_projection_now_carries_target(harness: ModuleType) -> None:
    assert "target" in harness.SEMANTIC_FIELDS
    assert "target" in harness.TEXTUAL_ROLE_FIELDS
    assert "unit_type" not in harness.TEXTUAL_ROLE_FIELDS
    assert set(harness.TEXTUAL_ROLE_FIELDS) < set(harness.SEMANTIC_FIELDS)


def test_the_predecessor_corpus_still_loads_unchanged(harness: ModuleType, repo_root: Path) -> None:
    """OIC-CANDIDATE-SEMANTICS-001 stays readable as historical evidence."""
    predecessor = repo_root / "benchmarks/characterization/candidate-semantics-001/CORPUS-v0.1.json"
    corpus = harness.load_corpus(predecessor)
    assert corpus.corpus_id == "OIC-CANDIDATE-SEMANTICS-001"
    assert len(corpus.specimens) == 32
    assert corpus.specimens[0].actor_explicitly_named is None


def test_cli_defaults_now_point_at_the_successor_corpus(harness: ModuleType) -> None:
    args = harness.build_parser().parse_args([])
    assert "candidate-semantics-002" in str(args.corpus)
    assert "CORPUS-v0.2.json" in str(args.corpus)
    assert "CORPUS-FREEZE-v0.2.json" in str(args.freeze)
    assert "OIC-CANDIDATE-SEMANTICS-002" in str(args.output)
