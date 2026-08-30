"""Contract tests over the frozen OIC-CANDIDATE-SEMANTICS-005 normative-boundary corpus.

005 corrects one discovery defect while every property 004 established must survive
untouched. So the corpus carries the negative controls, positive sentinels, and
framing/material sentinels verbatim from the frozen 003 and 004 corpora — checked against
the blobs at their own commits, not working-tree copies — and the contracts here assert
both halves: that the motivating specimen is still a negative control, and that the
sentinels that would reveal an over-correction are present and preregistered.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

# The work-order scope helper is a test-only module that deliberately does not live in
# src/oic, and tests/ is not a package, so it is loaded from its path rather than by name.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from work_order_scope import CANDIDATE_SEMANTICS_005, changed_paths
finally:
    sys.path.pop(0)

pytestmark = pytest.mark.contract

WORK_ORDER = CANDIDATE_SEMANTICS_005

BENCH = "benchmarks/characterization"
DIR_005 = f"{BENCH}/candidate-semantics-005"
CORPUS_RELPATH = f"{DIR_005}/CORPUS-v0.5.json"
FREEZE_RELPATH = f"{DIR_005}/CORPUS-FREEZE-v0.5.json"
README_RELPATH = f"{DIR_005}/README.md"

C003 = "db95d8fdf52b5ffb546b2ebd84bb9e035629c46f"
C004 = "11acd84b97bbdb3910c208e63b69b4fbb10be179"
P003 = f"{BENCH}/candidate-semantics-003/CORPUS-v0.3.json"
P004 = f"{BENCH}/candidate-semantics-004/CORPUS-v0.4.json"

FROZEN_SPECIMEN_COUNT = 21
FROZEN_CORPUS_SHA256 = "2d8c5f3f4be2028e00179b4b8eee464b325b8d9efbaf19875b8b783a6139dbf0"

FROZEN_PREDECESSORS = {
    f"{BENCH}/candidate-semantics-001/CORPUS-v0.1.json": (
        "21053e4a8688dd80583975a551ea13652650552044faf2b3e38572ae59f3e4a0"
    ),
    f"{BENCH}/candidate-semantics-002/CORPUS-v0.2.json": (
        "f97b1a80d86f821495674dacccb8bc130f8bf78e559bab22f7aa0b5a32dd3b7c"
    ),
    P003: "8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a",
    P004: "594cbee619f467ef949690cd56014eb4f8b3c5ba9527596c6e4bef3f242d5386",
}

NEGATIVE_IDS = (
    "CSEM-018",
    "CSEM-019",
    "CSEM-020",
    "CSEM-031",
    "CSEM-032",
    "CSEM-046",
    "CSEM-047",
    "CSEM-048",
)
CARRIED_IDS = (
    "CSEM-017",
    "CSEM-018",
    "CSEM-019",
    "CSEM-020",
    "CSEM-021",
    "CSEM-023",
    "CSEM-024",
    "CSEM-025",
    "CSEM-027",
    "CSEM-031",
    "CSEM-032",
    "CSEM-043",
    "CSEM-044",
    "CSEM-045",
)
NEW_IDS = (
    "CSEM-046",
    "CSEM-047",
    "CSEM-048",
    "CSEM-049",
    "CSEM-050",
    "CSEM-051",
    "CSEM-052",
)
FRAMING_SENTINEL_IDS = ("CSEM-021", "CSEM-023", "CSEM-024", "CSEM-044", "CSEM-045")
MATERIAL_SENTINEL_IDS = ("CSEM-025", "CSEM-043")

#: Files this work order must leave byte-identical to the branch's starting commit.
FROZEN_PRODUCTION_FILES = (
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
def originals(repo_root: Path) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for commit, relpath in ((C003, P003), (C004, P004)):
        document = json.loads(_blob(repo_root, commit, relpath).decode("utf-8"))
        for specimen in document["specimens"]:
            merged.setdefault(specimen["specimen_id"], specimen)
    return merged


# --------------------------------------------------------------------------
# Production freeze
# --------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", FROZEN_PRODUCTION_FILES)
def test_no_out_of_scope_production_file_was_modified(repo_root: Path, relpath: str) -> None:
    assert (repo_root / relpath).read_bytes() == _blob(repo_root, C004, relpath), relpath


def test_only_the_candidate_prompt_changed_in_production(repo_root: Path) -> None:
    """005 is a prompt-contract correction. The rest of production is untouched.

    Evaluated over the range 005 actually produced, never against HEAD: a later,
    separately authorized commit is outside a closed work order's scope, and widening
    this assertion until it tolerated one would leave it saying nothing. That the four
    frozen production files still hold their 004 bytes *now* is a different guarantee,
    checked against the working tree in the test above.
    """
    assert WORK_ORDER.base == C004
    changed = [
        path
        for path in changed_paths(repo_root, WORK_ORDER)
        if path.startswith(("src/", "schemas/"))
    ]
    assert changed == ["src/oic/candidate_extraction.py"]


# --------------------------------------------------------------------------
# Historical evidence stays frozen
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("relpath", "digest"), sorted(FROZEN_PREDECESSORS.items()))
def test_every_predecessor_corpus_is_byte_identical(
    repo_root: Path, relpath: str, digest: str
) -> None:
    assert hashlib.sha256((repo_root / relpath).read_bytes()).hexdigest() == digest, relpath


def test_005_records_which_corpora_it_succeeds(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    assert corpus["predecessor_corpus_id"] == "OIC-CANDIDATE-SEMANTICS-004"
    assert corpus["predecessor_corpus_sha256"] == FROZEN_PREDECESSORS[P004]
    assert corpus["predecessor_003_corpus_sha256"] == FROZEN_PREDECESSORS[P003]
    assert corpus["production_base_commit"] == C004
    assert freeze["predecessor_corpus_sha256"] == FROZEN_PREDECESSORS[P004]
    assert freeze["production_base_commit"] == C004


def test_every_carried_source_text_is_byte_identical_to_its_own_commit(
    specimens: list[dict[str, Any]], originals: dict[str, dict[str, Any]]
) -> None:
    carried = {item["specimen_id"]: item for item in specimens if item["carried_from_commit"]}
    assert set(carried) == set(CARRIED_IDS)
    for specimen_id, specimen in carried.items():
        source = originals[specimen_id]
        assert specimen["source_text"] == source["source_text"], specimen_id
        assert specimen["category"] == source["category"], specimen_id
        assert specimen["normative_expected"] == source["normative_expected"], specimen_id
        assert specimen["acceptable_unit_types"] == source["acceptable_unit_types"]
        assert specimen["candidate_span_bounds"] == source["candidate_span_bounds"]
        assert specimen["material_span_groups"] == source["material_span_groups"]
        assert specimen["carried_from_commit"] in {C003, C004}


def test_the_motivating_negative_stability_experiment_is_cited_not_rewritten(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    evidence = corpus["motivating_evidence"]
    assert "INCONCLUSIVE" in evidence
    assert "No statistical-significance claim is made" in evidence
    assert C003 in evidence
    assert C004 in evidence
    readme = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-NEGATIVE-STABILITY-001" in readme
    assert "INCONCLUSIVE" in readme
    assert "No statistical-significance claim" in readme


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


def test_every_frozen_source_digest_matches_its_specimen(
    specimens: list[dict[str, Any]], freeze: dict[str, Any]
) -> None:
    recorded = freeze["specimen_source_sha256"]
    assert len(recorded) == len(specimens)
    for specimen in specimens:
        expected = hashlib.sha256(specimen["source_text"].encode("utf-8")).hexdigest()
        assert recorded[specimen["specimen_id"]] == expected == specimen["source_sha256"]


def test_the_freeze_record_detects_a_mutated_corpus(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    mutated = json.loads(json.dumps(corpus))
    mutated["specimens"][0]["source_text"] += " "
    body = (
        json.dumps(mutated, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()
    assert hashlib.sha256(body).hexdigest() != freeze["corpus_sha256"]
    changed = hashlib.sha256(mutated["specimens"][0]["source_text"].encode("utf-8")).hexdigest()
    assert freeze["specimen_source_sha256"][mutated["specimens"][0]["specimen_id"]] != changed


def test_specimen_count_and_ids_are_frozen(
    specimens: list[dict[str, Any]], corpus: dict[str, Any]
) -> None:
    identifiers = [item["specimen_id"] for item in specimens]
    assert len(specimens) == FROZEN_SPECIMEN_COUNT
    assert corpus["specimen_count"] == FROZEN_SPECIMEN_COUNT
    assert identifiers == sorted(identifiers)
    assert len(set(identifiers)) == len(identifiers)
    assert set(identifiers) == set(CARRIED_IDS) | set(NEW_IDS)


def test_new_specimen_ids_start_after_the_existing_range(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["carried_from_commit"] is None:
            assert specimen["specimen_id"] in NEW_IDS
            assert int(specimen["specimen_id"].removeprefix("CSEM-")) > 45


# --------------------------------------------------------------------------
# The normative boundary
# --------------------------------------------------------------------------


def test_the_motivating_specimen_remains_a_negative_control(
    specimens: list[dict[str, Any]],
) -> None:
    """CSEM-031 must still expect zero candidates. 005 corrects the prompt, not the label."""
    trigger = next(item for item in specimens if item["specimen_id"] == "CSEM-031")
    assert trigger["normative_expected"] is False
    assert trigger["expected_candidate_count_min"] == 0
    assert trigger["expected_candidate_count_max"] == 0
    assert trigger["acceptable_unit_types"] is None
    assert "THE MOTIVATING SPECIMEN" in trigger["characterization_notes"]
    assert "advisory" in trigger["characterization_notes"]


def test_every_negative_control_expects_exactly_zero_candidates(
    specimens: list[dict[str, Any]],
) -> None:
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert tuple(sorted(item["specimen_id"] for item in negatives)) == NEGATIVE_IDS
    for specimen in negatives:
        assert specimen["expected_candidate_count_min"] == 0, specimen["specimen_id"]
        assert specimen["expected_candidate_count_max"] == 0, specimen["specimen_id"]
        assert specimen["arm_role"] == "negative_control", specimen["specimen_id"]


def test_institutional_vocabulary_negatives_were_added(
    specimens: list[dict[str, Any]],
) -> None:
    """The correction must not be tuned to one sentence."""
    tagged = [
        item
        for item in specimens
        if "institutional_vocabulary" in item["diagnostic_tags"] and not item["normative_expected"]
    ]
    assert len(tagged) >= 3
    categories = {item["category"] for item in tagged}
    assert "institutional_description_only" in categories
    assert "institutional_description_plus_history" in categories
    assert "explanatory_section_no_norm" in categories


def test_the_over_correction_controls_are_present_and_positive(
    specimens: list[dict[str, Any]],
) -> None:
    """If 005 suppresses genuine normative material, these are where it shows."""
    controls = {
        item["category"]: item
        for item in specimens
        if "over_correction_control" in item["diagnostic_tags"]
    }
    assert set(controls) >= {
        "constitutive_definition",
        "explicit_advisory",
        "delegation_constitutive",
    }
    for specimen in controls.values():
        assert specimen["normative_expected"] is True
        assert specimen["expected_candidate_count_min"] >= 1
        assert specimen["acceptable_unit_types"]
        assert specimen["candidate_span_bounds"]
    assert controls["constitutive_definition"]["acceptable_unit_types"] == ["definition"]
    assert controls["explicit_advisory"]["acceptable_unit_types"] == ["advisory"]
    assert "delegation" in controls["delegation_constitutive"]["acceptable_unit_types"]


def test_the_mixed_fragment_expects_only_the_normative_sentence(
    specimens: list[dict[str, Any]],
) -> None:
    """Descriptive institutional prose followed by a real norm: one candidate, bounded."""
    mixed = next(item for item in specimens if item["category"] == "mixed_description_then_norm")
    assert mixed["specimen_id"] == "CSEM-052"
    assert mixed["normative_expected"] is True
    assert mixed["expected_candidate_count_min"] == 1
    assert mixed["expected_candidate_count_max"] == 1
    assert len(mixed["candidate_span_bounds"]) == 1
    bound = mixed["candidate_span_bounds"][0]
    assert bound in mixed["source_text"]
    assert "describes the escalation framework" not in bound
    assert "describes the escalation framework" in mixed["source_text"]
    assert "mixed_fragment" in mixed["diagnostic_tags"]


def test_no_specimen_preregisters_a_modal_keyword_requirement(
    specimens: list[dict[str, Any]],
) -> None:
    """Genuine normative material need not contain must/shall/may/should."""
    advisory = next(item for item in specimens if item["category"] == "explicit_advisory")
    definition = next(item for item in specimens if item["category"] == "constitutive_definition")
    for specimen in (advisory, definition):
        text = specimen["source_text"].lower()
        assert " must " not in text
        assert " shall " not in text
        assert " should " not in text


# --------------------------------------------------------------------------
# Sentinels that must not regress
# --------------------------------------------------------------------------


def test_the_framing_sentinels_survived_with_their_preregistration(
    specimens: list[dict[str, Any]],
) -> None:
    by_id = {item["specimen_id"]: item for item in specimens}
    for specimen_id in FRAMING_SENTINEL_IDS:
        specimen = by_id[specimen_id]
        assert specimen["framing_expected_excluded"] is True, specimen_id
        assert specimen["separable_framing_spans"], specimen_id
        assert specimen["candidate_span_bounds"], specimen_id
        for framing in specimen["separable_framing_spans"]:
            assert framing in specimen["source_text"]
            for bound in specimen["candidate_span_bounds"]:
                assert framing not in bound, (specimen_id, framing)


def test_the_material_sentinels_survived_with_their_span_groups(
    specimens: list[dict[str, Any]],
) -> None:
    by_id = {item["specimen_id"]: item for item in specimens}
    for specimen_id in MATERIAL_SENTINEL_IDS:
        specimen = by_id[specimen_id]
        assert specimen["material_span_groups"], specimen_id
        for group in specimen["material_span_groups"]:
            assert group
            assert any(variant in specimen["source_text"] for variant in group)


def test_multi_unit_behaviour_is_still_represented(specimens: list[dict[str, Any]]) -> None:
    multi = [item for item in specimens if item["expected_candidate_count_min"] >= 2]
    assert multi
    assert {item["specimen_id"] for item in multi} >= {"CSEM-025", "CSEM-045"}


def test_the_positive_sentinels_survived(specimens: list[dict[str, Any]]) -> None:
    by_id = {item["specimen_id"]: item for item in specimens}
    assert by_id["CSEM-017"]["normative_expected"] is True
    assert by_id["CSEM-017"]["acceptable_unit_types"] == ["advisory"]
    assert by_id["CSEM-027"]["normative_expected"] is True
    assert by_id["CSEM-027"]["threshold_markers"] == ["$10,000"]


def test_every_declared_span_occurs_in_its_own_source(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for key in ("candidate_span_bounds", "separable_framing_spans"):
            for span in specimen[key] or []:
                assert span in specimen["source_text"], (specimen["specimen_id"], key, span)
        for group in specimen["material_span_groups"] or []:
            assert any(variant in specimen["source_text"] for variant in group), (
                specimen["specimen_id"],
                group,
            )


# --------------------------------------------------------------------------
# Claim discipline
# --------------------------------------------------------------------------


def test_the_corpus_states_the_normative_discovery_rule(corpus: dict[str, Any]) -> None:
    rule = corpus["normative_discovery_rule"]
    assert "appears to perform a provisional normative or constitutive function" in rule
    assert "Institutional vocabulary and institutional subject matter are never sufficient" in rule
    assert "no particular modal verb is required" in rule


def test_the_corpus_states_its_own_claim_ceiling(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"]
    assert corpus["independent_validation_claim"] is False
    for denied in (
        "semantic correctness",
        "zero false-positive probability",
        "institutional admission",
        "authority",
        "enforceability",
        "legal interpretation",
        "production readiness",
        "cross-model generalization",
        "statistical superiority",
        "independent validation",
    ):
        assert denied in ceiling, denied


def test_no_artifact_contains_credential_shaped_material(
    corpus_bytes: bytes, repo_root: Path
) -> None:
    for body in (
        corpus_bytes.decode("utf-8"),
        (repo_root / FREEZE_RELPATH).read_text(encoding="utf-8"),
        (repo_root / README_RELPATH).read_text(encoding="utf-8"),
    ):
        for marker in ("nvapi-", "Bearer ", "api_key", "-----BEGIN"):
            assert marker not in body, marker


def test_the_reproduction_document_states_the_correction_and_its_ceiling(
    repo_root: Path,
) -> None:
    text = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-SEMANTICS-005" in text
    assert "CSEM-031" in text
    assert "independent_validation_claim" in text
    assert "NOT SELF-ADJUDICATED" in text
    assert "NVIDIA_API_KEY" in text
    assert "no keyword list" in text.lower() or "no keyword blacklist" in text.lower()
