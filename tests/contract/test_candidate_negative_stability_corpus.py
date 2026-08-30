"""Contract tests over the frozen OIC-CANDIDATE-NEGATIVE-STABILITY-001 A/B micro-corpus.

The experiment asks whether behaviour changed against an already frozen negative-control
set. That question is only answerable if the set itself did not move, so the carried source
bytes are checked against the OIC-CANDIDATE-SEMANTICS-003 blob at its own commit rather
than against a working-tree copy.

The other obligation is the production freeze. This work order authorizes an instrument and
nothing else: if any candidate-path file differs from the branch's starting commit, the A/B
is measuring something other than the two commits it names.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

DIRECTORY = "benchmarks/characterization/candidate-negative-stability-001"
CORPUS_RELPATH = f"{DIRECTORY}/CORPUS-v0.1.json"
FREEZE_RELPATH = f"{DIRECTORY}/CORPUS-FREEZE-v0.1.json"
README_RELPATH = f"{DIRECTORY}/README.md"
HARNESS_RELPATH = "scripts/characterize_candidate_negative_stability.py"

ARM_A_COMMIT = "db95d8fdf52b5ffb546b2ebd84bb9e035629c46f"
ARM_B_COMMIT = "11acd84b97bbdb3910c208e63b69b4fbb10be179"
BRANCH_START_COMMIT = ARM_B_COMMIT

CORPUS_003_RELPATH = "benchmarks/characterization/candidate-semantics-003/CORPUS-v0.3.json"
FROZEN_CORPUS_SHA256 = "b135be84d9f0f9b1d111d24ebb3c118d5353c48316ac26658c6612323a386693"
PREDECESSOR_SHA256 = "8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a"

NEGATIVE_IDS = ("CSEM-018", "CSEM-019", "CSEM-020", "CSEM-031", "CSEM-032")
POSITIVE_IDS = ("CSEM-017", "CSEM-027")

#: Every file this work order must leave byte-identical to the branch's starting commit.
FROZEN_PRODUCTION_FILES = (
    "src/oic/candidate_extraction.py",
    "src/oic/nvidia_nim.py",
    "src/oic/model_provider.py",
    "src/oic/review_docket.py",
    "schemas/draft/candidate-normative-unit.schema.json",
)


def _blob(repo_root: Path, commit: str, relpath: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "blob", f"{commit}:{relpath}"],
        check=True,
        capture_output=True,
    ).stdout


@pytest.fixture(scope="module")
def corpus_bytes(repo_root: Path) -> bytes:
    return (repo_root / CORPUS_RELPATH).read_bytes()


@pytest.fixture(scope="module")
def corpus(corpus_bytes: bytes) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(corpus_bytes.decode("utf-8")))


@pytest.fixture(scope="module")
def specimens(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", corpus["specimens"])


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / FREEZE_RELPATH).read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def predecessor(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(_blob(repo_root, ARM_A_COMMIT, CORPUS_003_RELPATH).decode("utf-8")),
    )


# --------------------------------------------------------------------------
# Production freeze
# --------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", FROZEN_PRODUCTION_FILES)
def test_no_production_candidate_file_was_modified(repo_root: Path, relpath: str) -> None:
    """The A/B measures two named commits; changing production would measure a third."""
    committed = _blob(repo_root, BRANCH_START_COMMIT, relpath)
    assert (repo_root / relpath).read_bytes() == committed, relpath


def test_the_two_arms_differ_only_in_the_candidate_extraction_module(repo_root: Path) -> None:
    """The clean-A/B property: one variable, and it is the candidate prompt."""
    extraction = {
        commit: hashlib.sha256(
            _blob(repo_root, commit, "src/oic/candidate_extraction.py")
        ).hexdigest()
        for commit in (ARM_A_COMMIT, ARM_B_COMMIT)
    }
    assert extraction[ARM_A_COMMIT] != extraction[ARM_B_COMMIT]
    for relpath in ("src/oic/nvidia_nim.py", "src/oic/model_provider.py"):
        digests = {
            hashlib.sha256(_blob(repo_root, commit, relpath)).hexdigest()
            for commit in (ARM_A_COMMIT, ARM_B_COMMIT)
        }
        assert len(digests) == 1, relpath


def test_both_arm_commits_are_ancestors_of_this_branch(repo_root: Path) -> None:
    for commit in (ARM_A_COMMIT, ARM_B_COMMIT):
        result = subprocess.run(
            ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
        )
        assert result.returncode == 0, commit


# --------------------------------------------------------------------------
# Carried source preservation
# --------------------------------------------------------------------------


def test_every_carried_source_text_is_byte_identical_to_the_003_blob(
    specimens: list[dict[str, Any]], predecessor: dict[str, Any]
) -> None:
    original = {item["specimen_id"]: item for item in predecessor["specimens"]}
    for specimen in specimens:
        source = original[specimen["specimen_id"]]
        assert specimen["source_text"] == source["source_text"], specimen["specimen_id"]
        assert specimen["category"] == source["category"], specimen["specimen_id"]
        assert specimen["normative_expected"] == source["normative_expected"]
        assert specimen["carried_from_commit"] == ARM_A_COMMIT


def test_every_recorded_source_digest_matches_its_own_text(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        expected = hashlib.sha256(specimen["source_text"].encode("utf-8")).hexdigest()
        assert specimen["source_sha256"] == expected, specimen["specimen_id"]


def test_the_predecessor_corpus_is_untouched(
    repo_root: Path, corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    committed = _blob(repo_root, ARM_A_COMMIT, CORPUS_003_RELPATH)
    assert hashlib.sha256(committed).hexdigest() == PREDECESSOR_SHA256
    assert (repo_root / CORPUS_003_RELPATH).read_bytes() == committed
    assert corpus["predecessor_corpus_sha256"] == PREDECESSOR_SHA256
    assert freeze["predecessor_corpus_sha256"] == PREDECESSOR_SHA256


def test_no_new_negative_control_was_invented(specimens: list[dict[str, Any]]) -> None:
    """The question is about an already frozen set, so the set must not grow."""
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert tuple(sorted(item["specimen_id"] for item in negatives)) == NEGATIVE_IDS


# --------------------------------------------------------------------------
# Freeze integrity
# --------------------------------------------------------------------------


def test_corpus_bytes_match_the_digest_pinned_in_this_test(corpus_bytes: bytes) -> None:
    assert hashlib.sha256(corpus_bytes).hexdigest() == FROZEN_CORPUS_SHA256


def test_freeze_record_matches_the_corpus_on_disk(
    corpus_bytes: bytes, specimens: list[dict[str, Any]], freeze: dict[str, Any]
) -> None:
    assert freeze["corpus_sha256"] == hashlib.sha256(corpus_bytes).hexdigest()
    assert freeze["corpus_byte_length"] == len(corpus_bytes)
    assert freeze["specimen_count"] == len(specimens)
    assert freeze["specimen_ids"] == [item["specimen_id"] for item in specimens]
    assert freeze["corpus_relpath"] == CORPUS_RELPATH
    assert freeze["arm_a_commit"] == ARM_A_COMMIT
    assert freeze["arm_b_commit"] == ARM_B_COMMIT


def test_every_frozen_source_digest_matches_its_specimen(
    specimens: list[dict[str, Any]], freeze: dict[str, Any]
) -> None:
    recorded = freeze["specimen_source_sha256"]
    assert len(recorded) == len(specimens)
    for specimen in specimens:
        assert recorded[specimen["specimen_id"]] == specimen["source_sha256"]


# --------------------------------------------------------------------------
# Run plan
# --------------------------------------------------------------------------


def test_the_corpus_holds_five_negatives_and_two_positives(
    corpus: dict[str, Any], specimens: list[dict[str, Any]]
) -> None:
    assert len(specimens) == 7
    assert corpus["specimen_count"] == 7
    assert tuple(corpus["negative_control_ids"]) == NEGATIVE_IDS
    assert tuple(corpus["positive_sentinel_ids"]) == POSITIVE_IDS
    identifiers = [item["specimen_id"] for item in specimens]
    assert identifiers == sorted(identifiers)
    assert set(identifiers) == set(NEGATIVE_IDS) | set(POSITIVE_IDS)


def test_the_planned_run_counts_are_frozen(corpus: dict[str, Any]) -> None:
    assert corpus["negative_repetitions_per_arm"] == 10
    assert corpus["positive_repetitions_per_arm"] == 3
    assert corpus["planned_negative_requests"] == 100
    assert corpus["planned_positive_requests"] == 12
    assert corpus["planned_total_requests"] == 112


def test_each_specimen_declares_its_own_repetition_count(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        expected = 10 if not specimen["normative_expected"] else 3
        assert specimen["repetitions_per_arm"] == expected, specimen["specimen_id"]
        assert specimen["arm_role"] == (
            "negative_control" if not specimen["normative_expected"] else "positive_sentinel"
        )


def test_negative_controls_expect_exactly_zero_candidates(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["normative_expected"]:
            continue
        assert specimen["expected_candidate_count_min"] == 0
        assert specimen["expected_candidate_count_max"] == 0


def test_the_trigger_specimen_is_marked_as_such(specimens: list[dict[str, Any]]) -> None:
    trigger = next(item for item in specimens if item["specimen_id"] == "CSEM-031")
    assert trigger["normative_expected"] is False
    assert "THE TRIGGER" in trigger["characterization_notes"]
    assert "advisory" in trigger["characterization_notes"]


# --------------------------------------------------------------------------
# Claim discipline
# --------------------------------------------------------------------------


def test_the_corpus_records_the_false_positive_definition(corpus: dict[str, Any]) -> None:
    definition = corpus["false_positive_definition"]
    assert "normative_expected is false" in definition
    assert "survived the existing candidate boundary" in definition
    assert "candidate_count > 0" in definition
    assert "A boundary rejection is not a false positive" in definition
    assert "a provider error is not a false positive" in definition


def test_the_corpus_states_its_own_claim_ceiling(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"]
    assert corpus["independent_validation_claim"] is False
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


def test_the_corpus_names_both_arms(corpus: dict[str, Any]) -> None:
    assert corpus["arm_a_commit"] == ARM_A_COMMIT
    assert corpus["arm_b_commit"] == ARM_B_COMMIT


def test_no_artifact_contains_credential_shaped_material(
    corpus_bytes: bytes, repo_root: Path
) -> None:
    bodies = [
        corpus_bytes.decode("utf-8"),
        (repo_root / FREEZE_RELPATH).read_text(encoding="utf-8"),
        (repo_root / README_RELPATH).read_text(encoding="utf-8"),
    ]
    for body in bodies:
        for marker in ("nvapi-", "Bearer ", "api_key", "-----BEGIN"):
            assert marker not in body, marker


def test_the_reproduction_document_states_the_experiment_and_its_ceiling(
    repo_root: Path,
) -> None:
    text = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-NEGATIVE-STABILITY-001" in text
    assert ARM_A_COMMIT in text
    assert ARM_B_COMMIT in text
    assert "NVIDIA_API_KEY" in text
    assert "independent_validation_claim" in text
    assert "NOT SELF-ADJUDICATED" in text
    assert "112" in text
    assert "CSEM-031" in text


def test_the_harness_exists_and_declares_no_drift_convenience(repo_root: Path) -> None:
    source = (repo_root / HARNESS_RELPATH).read_text(encoding="utf-8")
    assert "--acknowledge-drift" not in source
    assert "--allow-corpus-drift" not in source
    assert "refusing to run" in source
