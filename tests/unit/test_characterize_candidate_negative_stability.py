"""Offline tests for the OIC-CANDIDATE-NEGATIVE-STABILITY-001 A/B instrument.

No live request is made here and no credential is used. What is tested is whether the
instrument can measure: whether it plans the right requests, keeps the arms honest, counts
a false positive the way the work order defines one, and refuses to run a comparison whose
arms are not provably different code.

That last property earned its own tests. During development a mistyped `PYTHONPATH` made
both arms resolve to the source repository's editable install instead of their worktrees --
an A/B that would have compared 004 against 004 and reported a confident null for entirely
the wrong reason. The instrument now proves its binding rather than assuming it, and these
tests exercise both the proving and the refusing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

_ = urllib.request
MODULE_RELPATH = "scripts/characterize_candidate_negative_stability.py"

ARM_A = "003"
ARM_B = "004"

# The harness is loaded by path, so its Corpus and Attempt dataclasses are not statically
# importable. The `Any` annotations below carry a per-line suppression for that reason.


def _load(repo_root: Path) -> ModuleType:
    path = repo_root / MODULE_RELPATH
    spec = importlib.util.spec_from_file_location("characterize_negative_stability", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["characterize_negative_stability"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _load(repo_root)


@pytest.fixture(scope="module")
def real_corpus(harness: ModuleType, repo_root: Path) -> Any:  # noqa: ANN401
    return harness.load_corpus(repo_root / harness.DEFAULT_CORPUS)


def specimen_record(
    specimen_id: str,
    *,
    normative: bool = False,
    repetitions: int = 10,
    text: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    body = text or f"Source text for {specimen_id}."
    return {
        "specimen_id": specimen_id,
        "arm_role": role or ("positive_sentinel" if normative else "negative_control"),
        "category": "test_category",
        "source_text": body,
        "source_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "normative_expected": normative,
        "expected_candidate_count_min": 1 if normative else 0,
        "expected_candidate_count_max": None if normative else 0,
        "acceptable_unit_types": ["advisory"] if normative else None,
        "repetitions_per_arm": repetitions,
        "carried_from_corpus": "OIC-CANDIDATE-SEMANTICS-003",
        "carried_from_commit": "db95d8fdf52b5ffb546b2ebd84bb9e035629c46f",
        "characterization_notes": "synthetic test specimen",
        "claim_ceiling": "test fixture only",
    }


def write_corpus(harness: ModuleType, tmp_path: Path, *items: dict[str, Any]) -> Path:
    path = tmp_path / "CORPUS.json"
    path.write_bytes(
        harness.canonical_json_bytes(
            {
                "corpus_id": "TEST-NS",
                "corpus_version": "v0.1",
                "claim_ceiling": "test fixture only",
                "specimen_count": len(items),
                "specimens": list(items),
            }
        )
    )
    return path


def load(harness: ModuleType, tmp_path: Path, *items: dict[str, Any]) -> Any:  # noqa: ANN401
    return harness.load_corpus(write_corpus(harness, tmp_path, *items))


def attempt(
    harness: ModuleType,
    *,
    specimen_id: str = "N-1",
    run_index: int = 1,
    arm: str = ARM_A,
    normative: bool = False,
    outcome: str | None = None,
    spans: tuple[str, ...] = (),
    types: tuple[str, ...] = (),
    sequence: int = 1,
    error_type: str | None = None,
) -> Any:  # noqa: ANN401
    resolved = outcome or harness.STRUCTURAL_PASS
    return harness.Attempt(
        sequence=sequence,
        specimen_id=specimen_id,
        run_index=run_index,
        arm=arm,
        arm_commit=harness.ARM_COMMITS[arm],
        normative_expected=normative,
        outcome=resolved,
        provider="nvidia-nim" if resolved == harness.STRUCTURAL_PASS else None,
        model="fake-model" if resolved == harness.STRUCTURAL_PASS else None,
        request_id=f"req-{sequence}",
        raw_content_sha256="0" * 64,
        candidate_count=len(spans) if resolved == harness.STRUCTURAL_PASS else None,
        candidate_spans=spans,
        unit_types=types,
        error_type=error_type,
        error_message="synthetic" if error_type else None,
        observed_at="2026-08-30T00:00:00Z",
        source_sha256="a" * 64,
        candidates=tuple(
            {"candidate_span": span, "unit_type": unit}
            for span, unit in zip(spans, types or ("advisory",) * len(spans), strict=False)
        ),
    )


# --------------------------------------------------------------------------
# 1. The arms are fixed configuration
# --------------------------------------------------------------------------


def test_the_two_arm_commits_are_fixed_constants(harness: ModuleType) -> None:
    assert harness.ARM_A_COMMIT == "db95d8fdf52b5ffb546b2ebd84bb9e035629c46f"
    assert harness.ARM_B_COMMIT == "11acd84b97bbdb3910c208e63b69b4fbb10be179"
    assert harness.ARM_LABELS == (ARM_A, ARM_B)
    assert harness.ARM_COMMITS == {
        ARM_A: harness.ARM_A_COMMIT,
        ARM_B: harness.ARM_B_COMMIT,
    }
    for commit in harness.ARM_COMMITS.values():
        assert len(commit) == 40
        assert all(character in "0123456789abcdef" for character in commit)


def test_both_arm_commits_exist_in_this_repository(harness: ModuleType, repo_root: Path) -> None:
    for commit in harness.ARM_COMMITS.values():
        harness.require_commit_present(repo_root, commit)
    with pytest.raises(harness.ExperimentError, match="not present"):
        harness.require_commit_present(repo_root, "0" * 40)


# --------------------------------------------------------------------------
# 2-8. Run plan, interleaving, anchors
# --------------------------------------------------------------------------


def test_the_real_corpus_holds_five_negatives_and_two_positives(real_corpus: Any) -> None:  # noqa: ANN401
    assert len(real_corpus.specimens) == 7
    assert [item.specimen_id for item in real_corpus.negatives] == [
        "CSEM-018",
        "CSEM-019",
        "CSEM-020",
        "CSEM-031",
        "CSEM-032",
    ]
    assert [item.specimen_id for item in real_corpus.positives] == ["CSEM-017", "CSEM-027"]


def test_repetition_counts_are_ten_negative_and_three_positive(real_corpus: Any) -> None:  # noqa: ANN401
    for specimen in real_corpus.negatives:
        assert specimen.repetitions_per_arm == 10, specimen.specimen_id
    for specimen in real_corpus.positives:
        assert specimen.repetitions_per_arm == 3, specimen.specimen_id


def test_the_planned_total_is_exactly_112_live_requests(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    planned = harness.plan_requests(real_corpus)
    assert len(planned) == 112
    negatives = [item for item in planned if item.specimen_id.startswith("CSEM-0")]
    del negatives
    negative_ids = {item.specimen_id for item in real_corpus.negatives}
    assert sum(1 for item in planned if item.specimen_id in negative_ids) == 100
    assert sum(1 for item in planned if item.specimen_id not in negative_ids) == 12
    for arm in harness.ARM_LABELS:
        assert sum(1 for item in planned if item.arm == arm) == 56


def test_every_planned_request_is_sequenced_once_per_specimen_run_and_arm(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    planned = harness.plan_requests(real_corpus)
    assert [item.sequence for item in planned] == list(range(1, len(planned) + 1))
    triples = {(item.specimen_id, item.run_index, item.arm) for item in planned}
    assert len(triples) == len(planned)


def test_arm_order_alternates_by_run_index(harness: ModuleType) -> None:
    assert harness.arm_order(1) == (ARM_A, ARM_B)
    assert harness.arm_order(2) == (ARM_B, ARM_A)
    assert harness.arm_order(3) == (ARM_A, ARM_B)
    assert harness.arm_order(10) == (ARM_B, ARM_A)


def test_the_arms_are_interleaved_not_batched(harness: ModuleType, real_corpus: Any) -> None:  # noqa: ANN401
    """Running all of one arm then the other would confound the prompt with provider drift."""
    planned = harness.plan_requests(real_corpus)
    arms = [item.arm for item in planned]
    # Adjacent pairs belong to the same (specimen, run) and always cover both arms.
    for index in range(0, len(planned), 2):
        left, right = planned[index], planned[index + 1]
        assert left.specimen_id == right.specimen_id
        assert left.run_index == right.run_index
        assert {left.arm, right.arm} == {ARM_A, ARM_B}
    # Neither arm is ever batched: no arm runs more than twice in a row.
    longest = 1
    current = 1
    for previous, this in itertools.pairwise(arms):
        current = current + 1 if this == previous else 1
        longest = max(longest, current)
    assert longest <= 2


def test_the_same_specimen_and_run_receives_an_identical_anchor_in_both_arms(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    for specimen in real_corpus.specimens:
        for run_index in range(1, specimen.repetitions_per_arm + 1):
            anchor = harness.specimen_anchor(specimen, real_corpus, run_index)
            again = harness.specimen_anchor(specimen, real_corpus, run_index)
            assert anchor == again
            assert anchor["quote"] == specimen.source_text
            assert anchor["content_hash"] == f"sha256:{specimen.source_sha256}"
            assert ARM_A not in json.dumps(anchor)
            assert "arm" not in json.dumps(anchor).lower()


def test_anchors_differ_between_runs_but_never_between_arms(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    specimen = real_corpus.negatives[0]
    first = harness.specimen_anchor(specimen, real_corpus, 1)
    second = harness.specimen_anchor(specimen, real_corpus, 2)
    assert first["anchor_id"] != second["anchor_id"]
    assert first["node_id"] == second["node_id"]
    assert first["quote"] == second["quote"]


# --------------------------------------------------------------------------
# 9-13. Outcome classification
# --------------------------------------------------------------------------


def test_a_false_positive_is_an_accepted_negative_with_candidates(harness: ModuleType) -> None:
    assert attempt(harness, spans=("x",), types=("advisory",)).false_positive is True
    assert attempt(harness, spans=()).false_positive is False


def test_a_boundary_rejection_is_never_a_false_positive(harness: ModuleType) -> None:
    rejected = attempt(
        harness, outcome=harness.BOUNDARY_REJECTED, error_type="CandidateGroundingError"
    )
    assert rejected.false_positive is False
    assert rejected.accepted is False


def test_a_rejected_response_carrying_candidates_is_still_not_a_false_positive(
    harness: ModuleType,
) -> None:
    """Boundary acceptance is load-bearing, not incidental.

    The live path never builds this combination, because a rejected response yields no
    candidates to record. The invariant should hold by definition rather than by luck of
    construction: if some future change recorded spans alongside a rejection, `accepted` is
    the only thing standing between them and the false-positive count.
    """
    rejected = harness.Attempt(
        sequence=1,
        specimen_id="N-1",
        run_index=1,
        arm=ARM_A,
        arm_commit=harness.ARM_COMMITS[ARM_A],
        normative_expected=False,
        outcome=harness.BOUNDARY_REJECTED,
        candidate_count=3,
        candidate_spans=("a", "b", "c"),
        unit_types=("advisory", "advisory", "advisory"),
        error_type="CandidateGroundingError",
        error_message="synthetic",
        observed_at="2026-08-30T00:00:00Z",
        source_sha256="a" * 64,
    )
    assert rejected.accepted is False
    assert rejected.false_positive is False
    summary = harness.arm_summary([rejected], ARM_A)
    assert summary["false_positive_runs"] == 0
    assert summary["boundary_rejected"] == 1
    assert summary["provider_successful_negative_runs"] == 0
    assert harness.false_positive_records([rejected]) == []


def test_a_provider_error_is_never_a_false_positive(harness: ModuleType) -> None:
    errored = attempt(harness, outcome=harness.PROVIDER_ERROR, error_type="ModelProviderError")
    assert errored.false_positive is False
    assert errored.accepted is False


def test_a_positive_sentinel_returning_candidates_is_not_a_false_positive(
    harness: ModuleType,
) -> None:
    assert attempt(harness, normative=True, spans=("x",)).false_positive is False


def test_the_arm_summary_separates_rejections_errors_and_false_positives(
    harness: ModuleType,
) -> None:
    attempts = [
        attempt(harness, sequence=1, run_index=1, spans=("bad span",), types=("advisory",)),
        attempt(
            harness,
            sequence=2,
            run_index=2,
            outcome=harness.BOUNDARY_REJECTED,
            error_type="CandidateGroundingError",
        ),
        attempt(
            harness,
            sequence=3,
            run_index=3,
            outcome=harness.PROVIDER_ERROR,
            error_type="ModelProviderError",
        ),
        attempt(harness, sequence=4, run_index=4),
    ]
    summary = harness.arm_summary(attempts, ARM_A)
    assert summary["requests_attempted"] == 4
    assert summary["boundary_accepted"] == 2
    assert summary["boundary_rejected"] == 1
    assert summary["provider_errors"] == 1
    assert summary["provider_successful_negative_runs"] == 2
    assert summary["false_positive_runs"] == 1
    assert summary["false_positive_rate"] == 0.5
    assert summary["false_positive_rate_denominator"] == "provider-successful negative runs"
    assert summary["false_positive_candidate_spans"] == ["bad span"]
    assert summary["false_positive_provisional_types"] == ["advisory"]
    assert len(summary["boundary_rejections"]) == 1
    assert len(summary["provider_error_records"]) == 1


def test_every_false_positive_keeps_its_full_evidence(harness: ModuleType) -> None:
    """Individual failures are never summarized away."""
    records = harness.false_positive_records(
        [
            attempt(
                harness,
                specimen_id="CSEM-031",
                run_index=7,
                arm=ARM_B,
                spans=("the governance framework",),
                types=("advisory",),
            )
        ]
    )
    assert len(records) == 1
    record = records[0]
    assert record["specimen_id"] == "CSEM-031"
    assert record["run_index"] == 7
    assert record["arm"] == ARM_B
    assert record["arm_commit"] == harness.ARM_B_COMMIT
    assert record["candidate_spans"] == ["the governance framework"]
    assert record["unit_types"] == ["advisory"]
    assert record["request_id"]
    assert record["raw_content_sha256"]
    assert record["source_sha256"]


def test_positive_presence_misses_are_reported_separately(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = load(
        harness,
        tmp_path,
        specimen_record("N-1"),
        specimen_record("P-1", normative=True, repetitions=3),
    )
    attempts = [
        attempt(harness, specimen_id="P-1", normative=True, arm=arm, run_index=index, spans=())
        for arm in harness.ARM_LABELS
        for index in (1, 2, 3)
    ]
    report = harness.positive_sentinel_report(corpus, attempts)
    assert report["both_sentinels_present_in_every_provider_successful_run"] is False
    assert report["per_specimen"][0][f"arm_{ARM_A}"]["presence_misses"] == 3
    summary = harness.arm_summary(attempts, ARM_A)
    assert summary["positive_presence_misses"] == 3
    assert summary["false_positive_runs"] == 0


# --------------------------------------------------------------------------
# 14. Paired comparison
# --------------------------------------------------------------------------


def paired_corpus(harness: ModuleType, tmp_path: Path) -> Any:  # noqa: ANN401
    return load(harness, tmp_path, specimen_record("N-1", repetitions=4))


def test_paired_comparison_classifies_all_four_outcomes(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = paired_corpus(harness, tmp_path)
    attempts = [
        # run 1: both absent
        attempt(harness, run_index=1, arm=ARM_A),
        attempt(harness, run_index=1, arm=ARM_B),
        # run 2: 003 only
        attempt(harness, run_index=2, arm=ARM_A, spans=("s",), types=("advisory",)),
        attempt(harness, run_index=2, arm=ARM_B),
        # run 3: 004 only
        attempt(harness, run_index=3, arm=ARM_A),
        attempt(harness, run_index=3, arm=ARM_B, spans=("s",), types=("advisory",)),
        # run 4: both
        attempt(harness, run_index=4, arm=ARM_A, spans=("s",), types=("advisory",)),
        attempt(harness, run_index=4, arm=ARM_B, spans=("s",), types=("advisory",)),
    ]
    paired = harness.paired_comparison(corpus, attempts)
    assert paired["both_correctly_absent"] == 1
    assert paired[f"arm_{ARM_A}_false_positive_only"] == 1
    assert paired[f"arm_{ARM_B}_false_positive_only"] == 1
    assert paired["both_false_positive"] == 1
    assert paired["usable_pairs"] == 4
    assert paired["discordant_total"] == 2
    assert len(paired["discordant_pairs"]) == 2


def test_a_pair_missing_one_side_is_unusable_not_silently_counted(
    harness: ModuleType, tmp_path: Path
) -> None:
    corpus = paired_corpus(harness, tmp_path)
    attempts = [
        attempt(harness, run_index=1, arm=ARM_A),
        attempt(
            harness,
            run_index=1,
            arm=ARM_B,
            outcome=harness.PROVIDER_ERROR,
            error_type="ModelProviderError",
        ),
    ]
    paired = harness.paired_comparison(corpus, attempts)
    assert paired["usable_pairs"] == 0
    assert len(paired["unusable_pairs"]) == 4
    assert paired["unusable_pairs"][0][f"arm_{ARM_B}_outcome"] == harness.PROVIDER_ERROR


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [(0, 0, None), (0, 1, 1.0), (0, 5, 0.0625), (1, 5, 0.21875), (3, 3, 1.0)],
)
def test_exact_paired_p_value_matches_the_binomial(
    harness: ModuleType, left: int, right: int, expected: float | None
) -> None:
    observed = harness.exact_paired_p_value(left, right)
    if expected is None:
        assert observed is None
    else:
        assert observed == pytest.approx(expected)


def test_the_p_value_is_labelled_descriptive_only(harness: ModuleType, tmp_path: Path) -> None:
    corpus = paired_corpus(harness, tmp_path)
    paired = harness.paired_comparison(corpus, [])
    assert "does not adjudicate semantic correctness" in paired["p_value_note"]


# --------------------------------------------------------------------------
# 15. Preregistered interpretation bands
# --------------------------------------------------------------------------


def band_for(
    harness: ModuleType,
    tmp_path: Path,
    *,
    per_specimen: dict[str, tuple[int, int]],
    sentinels_ok: bool = True,
    repetitions: int = 10,
) -> dict[str, Any]:
    corpus = load(
        harness,
        tmp_path,
        *[specimen_record(name, repetitions=repetitions) for name in sorted(per_specimen)],
    )
    attempts: list[Any] = []
    sequence = 0
    for name, (a_count, b_count) in sorted(per_specimen.items()):
        for arm, count in ((ARM_A, a_count), (ARM_B, b_count)):
            for index in range(1, repetitions + 1):
                sequence += 1
                attempts.append(
                    attempt(
                        harness,
                        specimen_id=name,
                        run_index=index,
                        arm=arm,
                        sequence=sequence,
                        spans=("s",) if index <= count else (),
                        types=("advisory",) if index <= count else (),
                    )
                )
    sentinels = {"both_sentinels_present_in_every_provider_successful_run": sentinels_ok}
    return cast("dict[str, Any]", harness.interpretation_band(corpus, attempts, sentinels))


def test_band_no_material_regression_signal(harness: ModuleType, tmp_path: Path) -> None:
    result = band_for(harness, tmp_path, per_specimen={"N-1": (0, 1), "N-2": (1, 1)})
    assert result["band"] == harness.BAND_NO_MATERIAL
    assert result["delta_004_minus_003"] == 1
    assert result["rule_evaluations"]["no_material_delta_le_2"] is True
    assert result["rule_evaluations"]["no_material_both_sentinels_present"] is True


def test_band_regression_on_total_delta(harness: ModuleType, tmp_path: Path) -> None:
    result = band_for(harness, tmp_path, per_specimen={"N-1": (0, 5)})
    assert result["band"] == harness.BAND_REGRESSION
    assert result["rule_evaluations"]["regression_total_delta_ge_5"] is True


def test_band_regression_on_a_single_specimen(harness: ModuleType, tmp_path: Path) -> None:
    """004 >= 4/10 while 003 <= 1/10 on one specimen is a signal on its own."""
    result = band_for(harness, tmp_path, per_specimen={"N-1": (1, 4), "N-2": (2, 0)})
    assert result["band"] == harness.BAND_REGRESSION
    assert result["rule_evaluations"]["regression_any_specimen_b_ge_4_and_a_le_1"] is True
    assert result["rule_evaluations"]["regression_total_delta_ge_5"] is False


def test_band_inconclusive_between_the_thresholds(harness: ModuleType, tmp_path: Path) -> None:
    result = band_for(harness, tmp_path, per_specimen={"N-1": (0, 3)})
    assert result["band"] == harness.BAND_INCONCLUSIVE
    assert result["delta_004_minus_003"] == 3


def test_a_sentinel_presence_miss_blocks_the_no_material_band(
    harness: ModuleType, tmp_path: Path
) -> None:
    result = band_for(harness, tmp_path, per_specimen={"N-1": (0, 1)}, sentinels_ok=False)
    assert result["band"] == harness.BAND_INCONCLUSIVE
    assert result["rule_evaluations"]["no_material_both_sentinels_present"] is False


def test_an_elevated_specimen_blocks_the_no_material_band(
    harness: ModuleType, tmp_path: Path
) -> None:
    """004 at 3/10 with 003 at 1/10 is not a regression signal, but it is not "no signal"."""
    result = band_for(harness, tmp_path, per_specimen={"N-1": (1, 3), "N-2": (2, 0)})
    assert result["band"] == harness.BAND_INCONCLUSIVE
    assert result["rule_evaluations"]["no_material_delta_le_2"] is True
    assert result["rule_evaluations"]["no_material_no_specimen_b_ge_3_and_a_le_1"] is False


def test_the_band_disclaims_adjudication(harness: ModuleType, tmp_path: Path) -> None:
    result = band_for(harness, tmp_path, per_specimen={"N-1": (0, 0)})
    assert "decides no architecture" in result["note"]


# --------------------------------------------------------------------------
# 16-17. CSEM-031 reporting
# --------------------------------------------------------------------------


def test_csem_031_gets_every_attempt_listed_individually(harness: ModuleType) -> None:
    """Repeated identical outputs are not collapsed."""
    attempts = [
        attempt(
            harness,
            specimen_id="CSEM-031",
            run_index=index,
            arm=arm,
            sequence=index,
            spans=("the governance framework",) if (arm == ARM_B and index == 2) else (),
            types=("advisory",) if (arm == ARM_B and index == 2) else (),
        )
        for arm in harness.ARM_LABELS
        for index in range(1, 11)
    ]
    report = harness.csem_031_report(attempts)
    assert report["specimen_id"] == "CSEM-031"
    assert len(report["all_attempts"]) == 20
    assert report[f"arm_{ARM_A}"]["attempts"] == 10
    assert report[f"arm_{ARM_B}"]["attempts"] == 10
    assert report[f"arm_{ARM_A}"]["false_positive_runs"] == 0
    assert report[f"arm_{ARM_B}"]["false_positive_runs"] == 1
    assert report[f"arm_{ARM_B}"]["false_positive_rate"] == pytest.approx(0.1)
    flagged = [row for row in report["all_attempts"] if row["candidate_count"]]
    assert flagged[0]["candidate_spans"] == ["the governance framework"]
    assert flagged[0]["unit_types"] == ["advisory"]


def test_csem_031_report_shows_zero_rows_as_zero_not_as_absence(harness: ModuleType) -> None:
    attempts = [
        attempt(harness, specimen_id="CSEM-031", run_index=index, arm=arm, sequence=index)
        for arm in harness.ARM_LABELS
        for index in (1, 2)
    ]
    report = harness.csem_031_report(attempts)
    assert len(report["all_attempts"]) == 4
    assert all(row["candidate_count"] == 0 for row in report["all_attempts"])


# --------------------------------------------------------------------------
# 18-19. Receipt
# --------------------------------------------------------------------------


def build(harness: ModuleType, corpus: Any, attempts: list[Any]) -> dict[str, Any]:  # noqa: ANN401
    planned = harness.plan_requests(corpus)
    receipt = harness.build_receipt(
        corpus=corpus,
        attempts=attempts,
        planned=planned,
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        pacing_seconds=4.0,
        arm_fingerprints={
            ARM_A: {"src/oic/candidate_extraction.py": "a" * 64},
            ARM_B: {"src/oic/candidate_extraction.py": "b" * 64},
        },
        arm_bindings={
            ARM_A: {
                "resolved_module_path": "/synthetic/arm-003/src/oic/candidate_extraction.py",
                "module_file_sha256": "a" * 64,
                "system_prompt_sha256": "c" * 64,
            },
            ARM_B: {
                "resolved_module_path": "/synthetic/arm-004/src/oic/candidate_extraction.py",
                "module_file_sha256": "b" * 64,
                "system_prompt_sha256": "d" * 64,
            },
        },
        arm_worktrees={ARM_A: "/synthetic/arm-003", ARM_B: "/synthetic/arm-004"},
        cleanup={ARM_A: "removed", ARM_B: "removed"},
        corpus_freeze_relpath="FREEZE.json",
        orchestrator_commit={"commit": "0" * 40, "worktree_clean": True},
    )
    return cast("dict[str, Any]", receipt)


def test_the_receipt_carries_every_required_section(harness: ModuleType, real_corpus: Any) -> None:  # noqa: ANN401
    receipt = build(harness, real_corpus, [attempt(harness)])
    for key in (
        "work_order",
        "experiment_version",
        "generated_at",
        "arms",
        "corpus",
        "run_conditions",
        "actual_request_sequence",
        "attempts",
        "primary_measure",
        "per_specimen",
        "paired_comparison",
        "csem_031",
        "positive_sentinels",
        "interpretation",
        "limitations",
        "claim_ceiling",
        "independent_validation_claim",
    ):
        assert key in receipt, key
    assert receipt["work_order"] == "OIC-CANDIDATE-NEGATIVE-STABILITY-001"
    assert receipt["independent_validation_claim"] is False
    assert receipt["self_adjudication"].startswith("NOT SELF-ADJUDICATED")
    assert len(receipt["actual_request_sequence"]) == 112


def test_the_receipt_records_both_exact_implementation_shas(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    receipt = build(harness, real_corpus, [])
    assert receipt["arms"][f"arm_{ARM_A}"]["commit"] == harness.ARM_A_COMMIT
    assert receipt["arms"][f"arm_{ARM_B}"]["commit"] == harness.ARM_B_COMMIT
    assert receipt["arms"]["arms_verified_distinguishable"] is True
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    assert harness.ARM_A_COMMIT in serialized
    assert harness.ARM_B_COMMIT in serialized


def test_the_receipt_records_corpus_and_source_hashes(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    receipt = build(harness, real_corpus, [])
    assert receipt["corpus"]["corpus_sha256"] == real_corpus.sha256
    hashes = receipt["corpus"]["specimen_source_sha256"]
    assert len(hashes) == 7
    for specimen in real_corpus.specimens:
        assert hashes[specimen.specimen_id] == specimen.source_sha256


def test_the_receipt_records_pacing_and_that_no_retry_exists(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    conditions = build(harness, real_corpus, [])["run_conditions"]
    assert conditions["pacing_seconds_after_each_request"] == 4.0
    assert conditions["retries"] == 0
    assert "No retry exists" in conditions["retry_note"]
    assert "not retry logic" in conditions["pacing_note"]
    assert conditions["planned_total_requests"] == 112
    assert conditions["planned_negative_requests"] == 100
    assert conditions["planned_positive_requests"] == 12
    assert "odd run index runs 003 then 004" in conditions["interleaving_rule"]


def test_the_receipt_cannot_contain_a_credential(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "nvapi-TEST-SENTINEL-DO-NOT-COMMIT-000000"
    monkeypatch.setenv("NVIDIA_API_KEY", sentinel)
    receipt = build(harness, real_corpus, [attempt(harness, spans=("s",), types=("advisory",))])
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    for leaked in (sentinel, "NVIDIA_API_KEY", "Authorization", "Bearer", "nvapi-"):
        assert leaked not in serialized, leaked


def test_the_harness_never_reads_a_credential_itself(repo_root: Path) -> None:
    """The credential reaches each arm's own adapter and is never touched here.

    The variable NAME appears once, in CLI help, which is documentation rather than a
    read. What must not appear is any lookup: the environment is copied wholesale into
    the subprocess and never inspected.
    """
    source = (repo_root / MODULE_RELPATH).read_text(encoding="utf-8")
    for reading in ("getenv", "environ.get", 'environ["NVIDIA', "api_key", "Authorization"):
        assert reading not in source, reading
    assert source.count("os.environ") == 2
    assert source.count("environment = dict(os.environ)") == 2
    # The only mention is the help string telling the operator what to export.
    assert source.count("NVIDIA_API_KEY") == 1
    assert "Requires NVIDIA_API_KEY " in source


def test_the_harness_declares_no_retry_machinery(repo_root: Path) -> None:
    source = (repo_root / MODULE_RELPATH).read_text(encoding="utf-8")
    for forbidden in ("retry(", "retries=", "backoff", "max_attempts", "while True"):
        assert forbidden not in source, forbidden


def test_the_receipt_states_its_claim_ceiling_and_limitations(
    harness: ModuleType,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    receipt = build(harness, real_corpus, [])
    ceiling = receipt["claim_ceiling"]
    for denied in (
        "semantic correctness",
        "zero false-positive probability",
        "production readiness",
        "institutional admission",
        "authority",
        "enforceability",
        "legal interpretation",
        "cross-model generalization",
        "statistical equivalence",
        "independent validation",
    ):
        assert denied in ceiling, denied
    assert len(receipt["limitations"]) >= 6
    assert any("not evidence of equivalence" in item for item in receipt["limitations"])
    serialized = harness.canonical_json_bytes(receipt).decode("utf-8")
    for banned in ('"ADMITTED"', '"AUTHORIZED"', '"COMPLIANT"', '"ALLOW"', '"DENY"'):
        assert banned not in serialized, banned


# --------------------------------------------------------------------------
# Corpus integrity
# --------------------------------------------------------------------------


def test_the_frozen_corpus_passes_its_own_integrity_check(
    harness: ModuleType,
    repo_root: Path,
    real_corpus: Any,  # noqa: ANN401
) -> None:
    assert harness.verify_corpus_integrity(real_corpus, repo_root / harness.DEFAULT_FREEZE) == []


def test_corpus_drift_refuses_the_run_with_no_acknowledgement_flag(
    harness: ModuleType, tmp_path: Path, repo_root: Path
) -> None:
    drifted = load(harness, tmp_path, specimen_record("CSEM-018", text="mutated"))
    with pytest.raises(harness.CorpusIntegrityError, match="refusing to run"):
        harness.verify_corpus_integrity(drifted, repo_root / harness.DEFAULT_FREEZE)
    assert "--acknowledge-drift" not in (repo_root / MODULE_RELPATH).read_text(encoding="utf-8")


def test_a_specimen_whose_recorded_digest_disagrees_with_its_text_is_rejected(
    harness: ModuleType, tmp_path: Path
) -> None:
    record = specimen_record("N-1")
    record["source_sha256"] = "f" * 64
    with pytest.raises(harness.ExperimentError, match="disagrees with its own source_text"):
        load(harness, tmp_path, record)


def test_freeze_findings_detect_an_arm_commit_swap(harness: ModuleType, real_corpus: Any) -> None:  # noqa: ANN401
    findings = harness.corpus_freeze_findings(
        real_corpus,
        {
            "corpus_sha256": real_corpus.sha256,
            "specimen_count": len(real_corpus.specimens),
            "specimen_ids": [item.specimen_id for item in real_corpus.specimens],
            "specimen_source_sha256": {
                item.specimen_id: item.source_sha256 for item in real_corpus.specimens
            },
            "arm_a_commit": "0" * 40,
            "arm_b_commit": harness.ARM_B_COMMIT,
        },
    )
    assert any("arm 003 drift" in finding for finding in findings)


# --------------------------------------------------------------------------
# Arm isolation: proven, not assumed
# --------------------------------------------------------------------------


def test_the_source_repository_must_be_clean_before_the_experiment(
    harness: ModuleType, tmp_path: Path
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@x.invalid"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "one"], check=True)
    harness.require_clean_source_repository(tmp_path)
    (tmp_path / "a.txt").write_text("two", encoding="utf-8")
    with pytest.raises(harness.ExperimentError, match="not clean"):
        harness.require_clean_source_repository(tmp_path)


def test_an_existing_worktree_path_is_never_deleted_by_the_experiment(
    harness: ModuleType, tmp_path: Path, repo_root: Path
) -> None:
    occupied = tmp_path / "arm-003"
    occupied.mkdir()
    (occupied / "someone-elses-file.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(harness.ExperimentError, match="already exists"):
        harness.create_arm_worktree(repo_root, harness.ARM_A_COMMIT, occupied)
    assert (occupied / "someone-elses-file.txt").read_text(encoding="utf-8") == "keep me"


def test_each_arm_binds_to_its_own_worktree_and_the_arms_are_distinguishable(
    harness: ModuleType, repo_root: Path, tmp_path: Path
) -> None:
    """The property the whole experiment rests on, checked without any network call.

    Both arms are materialized, each is asked what it actually imported, and the answers
    must point inside their own worktrees and differ from each other.
    """
    script = repo_root / MODULE_RELPATH
    worktrees = {label: tmp_path / f"arm-{label}" for label in harness.ARM_LABELS}
    bindings: dict[str, Any] = {}
    try:
        for label, path in worktrees.items():
            harness.create_arm_worktree(repo_root, harness.ARM_COMMITS[label], path)
            bindings[label] = harness.verify_arm_binding(worktree=path, script_path=script)
        harness.require_distinguishable_arms(bindings)
        for label, path in worktrees.items():
            resolved = Path(bindings[label]["resolved_module_path"])
            assert (path / "src").resolve() in resolved.parents
            assert bindings[label]["model_allowed_keys"] == ["candidate_span", "unit_type"]
        assert bindings[ARM_A]["module_file_sha256"] != bindings[ARM_B]["module_file_sha256"]
        assert bindings[ARM_A]["system_prompt_sha256"] != bindings[ARM_B]["system_prompt_sha256"]
        # 004 added framing rules, so its prompt is the longer one.
        assert bindings[ARM_B]["system_prompt_length"] > bindings[ARM_A]["system_prompt_length"]
    finally:
        for path in worktrees.values():
            if path.exists():
                harness.remove_arm_worktree(repo_root, path)


@pytest.mark.parametrize(
    "identical",
    ["resolved_module_path", "module_file_sha256", "system_prompt_sha256"],
)
def test_indistinguishable_arms_refuse_to_run(harness: ModuleType, identical: str) -> None:
    """An A/B that cannot tell its arms apart would report a confident null for nothing."""
    left = {
        "resolved_module_path": "/synthetic/arm-003/src/oic/candidate_extraction.py",
        "module_file_sha256": "a" * 64,
        "system_prompt_sha256": "c" * 64,
    }
    right = {
        "resolved_module_path": "/synthetic/arm-004/src/oic/candidate_extraction.py",
        "module_file_sha256": "b" * 64,
        "system_prompt_sha256": "d" * 64,
    }
    harness.require_distinguishable_arms({ARM_A: left, ARM_B: right})
    right[identical] = left[identical]
    with pytest.raises(harness.ExperimentError, match="not distinguishable"):
        harness.require_distinguishable_arms({ARM_A: left, ARM_B: right})


def test_a_worker_bound_to_the_wrong_tree_fails_closed(harness: ModuleType, tmp_path: Path) -> None:
    """The regression guard: a mistyped arm path must refuse, not silently use the repo's."""
    with pytest.raises(harness.ArmBindingError, match="not inside the arm source root"):
        harness._bound_candidate_extraction(str(tmp_path / "not-the-arm"))
