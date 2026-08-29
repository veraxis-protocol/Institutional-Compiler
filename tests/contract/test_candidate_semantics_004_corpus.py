"""Contract tests over the frozen OIC-CANDIDATE-SEMANTICS-004 framing corpus.

Three obligations. The corpus must be frozen and internally consistent; every carried
specimen must be byte-identical to its OIC-CANDIDATE-SEMANTICS-003 original so before and
after are comparable; and every predecessor corpus must remain untouched, because each is
the evidence its own receipt refers to and rewriting one would falsify a receipt that was
true when it was issued.

Preregistrations describe the SOURCE, never a required answer. A registered span that the
source does not contain would produce a confident and meaningless metric, so each one is
checked against its own specimen here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

BENCH = "benchmarks/characterization"
DIR_004 = f"{BENCH}/candidate-semantics-004"
CORPUS_RELPATH = f"{DIR_004}/CORPUS-v0.4.json"
FREEZE_RELPATH = f"{DIR_004}/CORPUS-FREEZE-v0.4.json"
README_RELPATH = f"{DIR_004}/README.md"

FROZEN_SPECIMEN_COUNT = 14
FROZEN_CORPUS_SHA256 = "594cbee619f467ef949690cd56014eb4f8b3c5ba9527596c6e4bef3f242d5386"

#: Every predecessor stays exactly as its own work order froze it.
FROZEN_PREDECESSORS = {
    f"{BENCH}/candidate-semantics-001/CORPUS-v0.1.json": (
        "21053e4a8688dd80583975a551ea13652650552044faf2b3e38572ae59f3e4a0"
    ),
    f"{BENCH}/candidate-semantics-002/CORPUS-v0.2.json": (
        "f97b1a80d86f821495674dacccb8bc130f8bf78e559bab22f7aa0b5a32dd3b7c"
    ),
    f"{BENCH}/candidate-semantics-003/CORPUS-v0.3.json": (
        "8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a"
    ),
}

CARRIED_IDS = (
    "CSEM-017",
    "CSEM-018",
    "CSEM-021",
    "CSEM-022",
    "CSEM-023",
    "CSEM-024",
    "CSEM-025",
    "CSEM-027",
    "CSEM-031",
)
NEW_IDS = ("CSEM-041", "CSEM-042", "CSEM-043", "CSEM-044", "CSEM-045")

#: The framing structures OIC-CANDIDATE-SEMANTICS-004 requires the corpus to exercise.
REQUIRED_FRAMING_STRUCTURES = (
    "draft_prefix",
    "hypothetical_wrapper",
    "illustrative_wrapper",
    "non_authoritative_prefix",
    "unverified_prefix",
    "source_attribution",
    "draft_word_inside_proposition",
    "draft_prefix_over_advisory",
    "shared_framing_prefix_two_propositions",
    "no_framing_present",
    "negative_control",
)

FRAMING_FIELDS = (
    "separable_framing_spans",
    "framing_expected_excluded",
    "framing_structure",
    "carried_from_corpus",
)

ACCEPTED_UNIT_TYPES = frozenset(
    {
        "definition",
        "mandate",
        "delegation",
        "obligation",
        "prohibition",
        "permission",
        "power",
        "condition",
        "exception",
        "evidence_duty",
        "review_duty",
        "escalation",
        "remedy",
        "temporal_trigger",
        "discretion",
        "advisory",
    }
)


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
    path = repo_root / BENCH / "candidate-semantics-003/CORPUS-v0.3.json"
    return cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------
# Historical evidence stays frozen
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("relpath", "digest"), sorted(FROZEN_PREDECESSORS.items()))
def test_every_predecessor_corpus_is_byte_identical(
    repo_root: Path, relpath: str, digest: str
) -> None:
    body = (repo_root / relpath).read_bytes()
    assert hashlib.sha256(body).hexdigest() == digest, relpath


def test_004_records_which_corpus_it_succeeds(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    expected = FROZEN_PREDECESSORS[f"{BENCH}/candidate-semantics-003/CORPUS-v0.3.json"]
    assert corpus["predecessor_corpus_id"] == "OIC-CANDIDATE-SEMANTICS-003"
    assert corpus["predecessor_corpus_sha256"] == expected
    assert freeze["predecessor_corpus_sha256"] == expected


def test_carried_specimens_are_verbatim_copies_of_their_003_originals(
    specimens: list[dict[str, Any]], predecessor: dict[str, Any]
) -> None:
    """Only the four 004 preregistration fields were added; nothing else moved."""
    original_by_id = {item["specimen_id"]: item for item in predecessor["specimens"]}
    carried = {item["specimen_id"]: item for item in specimens if item["carried_from_corpus"]}
    assert set(carried) == set(CARRIED_IDS)
    for specimen_id, successor in carried.items():
        original = original_by_id[specimen_id]
        for key, value in original.items():
            assert successor[key] == value, (specimen_id, key)
        assert set(successor) - set(original) == set(FRAMING_FIELDS)
        assert successor["carried_from_corpus"] == "OIC-CANDIDATE-SEMANTICS-003"


def test_no_predecessor_source_text_was_altered_to_improve_performance(
    specimens: list[dict[str, Any]], predecessor: dict[str, Any]
) -> None:
    original_by_id = {item["specimen_id"]: item["source_text"] for item in predecessor["specimens"]}
    for specimen in specimens:
        if specimen["specimen_id"] in original_by_id:
            assert specimen["source_text"] == original_by_id[specimen["specimen_id"]]


# --------------------------------------------------------------------------
# Freeze integrity and drift detection
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
        assert recorded[specimen["specimen_id"]] == expected, specimen["specimen_id"]


def test_the_freeze_record_detects_a_mutated_corpus(
    repo_root: Path, corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    """Drift detection is real: a single edited character changes the digest."""
    mutated = json.loads(json.dumps(corpus))
    mutated["specimens"][0]["source_text"] += " "
    body = (
        json.dumps(mutated, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()
    assert hashlib.sha256(body).hexdigest() != freeze["corpus_sha256"]
    original = hashlib.sha256(mutated["specimens"][0]["source_text"].encode("utf-8")).hexdigest()
    assert freeze["specimen_source_sha256"][mutated["specimens"][0]["specimen_id"]] != original
    del repo_root


def test_specimen_count_and_ids_are_frozen(
    specimens: list[dict[str, Any]], corpus: dict[str, Any]
) -> None:
    identifiers = [item["specimen_id"] for item in specimens]
    assert len(specimens) == FROZEN_SPECIMEN_COUNT
    assert corpus["specimen_count"] == FROZEN_SPECIMEN_COUNT
    assert len(set(identifiers)) == len(identifiers)
    assert identifiers == sorted(identifiers)
    assert set(identifiers) == set(CARRIED_IDS) | set(NEW_IDS)


def test_new_specimen_ids_start_after_the_existing_range(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["carried_from_corpus"] is None:
            assert specimen["specimen_id"] in NEW_IDS
            assert int(specimen["specimen_id"].removeprefix("CSEM-")) > 40


# --------------------------------------------------------------------------
# Framing pre-registration
# --------------------------------------------------------------------------


def test_every_specimen_carries_the_004_framing_fields(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for field in FRAMING_FIELDS:
            assert field in specimen, (specimen["specimen_id"], field)
        assert specimen["framing_expected_excluded"] in (True, False, None)
        assert specimen["framing_structure"] in REQUIRED_FRAMING_STRUCTURES


def test_every_declared_framing_span_occurs_in_its_own_source(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        for span in specimen["separable_framing_spans"] or []:
            assert span in specimen["source_text"], (specimen["specimen_id"], span)


def test_every_declared_bound_and_material_span_occurs_in_its_own_source(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        for bound in specimen["candidate_span_bounds"] or []:
            assert bound in specimen["source_text"], (specimen["specimen_id"], bound)
        for group in specimen["material_span_groups"] or []:
            assert group
            assert any(variant in specimen["source_text"] for variant in group), (
                specimen["specimen_id"],
                group,
            )


def test_a_span_expected_to_be_excluded_comes_with_the_framing_and_a_bound(
    specimens: list[dict[str, Any]],
) -> None:
    excluding = [item for item in specimens if item["framing_expected_excluded"] is True]
    assert len(excluding) >= 6
    for specimen in excluding:
        assert specimen["separable_framing_spans"], specimen["specimen_id"]
        assert specimen["candidate_span_bounds"], specimen["specimen_id"]
        # The framing must genuinely sit outside every acceptable proposition bound.
        for bound in specimen["candidate_span_bounds"]:
            for framing in specimen["separable_framing_spans"]:
                assert framing not in bound, (specimen["specimen_id"], framing)


def test_a_specimen_registering_no_framing_declares_none(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["framing_expected_excluded"] is not True:
            assert specimen["separable_framing_spans"] is None, specimen["specimen_id"]


def test_negative_controls_preregister_no_framing_expectation(
    specimens: list[dict[str, Any]],
) -> None:
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert len(negatives) >= 2
    for specimen in negatives:
        assert specimen["framing_expected_excluded"] is None
        assert specimen["framing_structure"] == "negative_control"
        assert specimen["expected_candidate_count_min"] == 0
        assert specimen["expected_candidate_count_max"] == 0


def test_the_corpus_documents_what_a_framing_span_registration_means(
    corpus: dict[str, Any],
) -> None:
    semantics = corpus["separable_framing_span_semantics"]
    assert "describes the SOURCE, not a required answer" in semantics
    assert "null means no separable framing is present" in semantics


# --------------------------------------------------------------------------
# Required diagnostic coverage
# --------------------------------------------------------------------------


def test_every_required_framing_structure_is_covered(specimens: list[dict[str, Any]]) -> None:
    observed = {item["framing_structure"] for item in specimens}
    missing = sorted(set(REQUIRED_FRAMING_STRUCTURES) - observed)
    assert missing == [], f"uncovered framing structures: {missing}"


def test_the_control_against_over_stripping_exists_and_keeps_its_language(
    specimens: list[dict[str, Any]],
) -> None:
    """CSEM-043: 'still in draft' describes the contract, not this source's standing."""
    control = next(
        item for item in specimens if item["framing_structure"] == "draft_word_inside_proposition"
    )
    assert control["specimen_id"] == "CSEM-043"
    assert control["framing_expected_excluded"] is False
    assert control["separable_framing_spans"] is None
    assert "draft" in control["source_text"]
    assert any(
        "still in draft" in variant
        for group in control["material_span_groups"]
        for variant in group
    )
    assert "must_not_strip" in control["diagnostic_tags"]


def test_advisory_material_appears_under_framing(specimens: list[dict[str, Any]]) -> None:
    advisory = [item for item in specimens if item["acceptable_unit_types"] == ["advisory"]]
    assert len(advisory) >= 2
    assert any(item["framing_expected_excluded"] is True for item in advisory)


def test_a_shared_framing_prefix_covers_two_propositions(
    specimens: list[dict[str, Any]],
) -> None:
    shared = next(
        item
        for item in specimens
        if item["framing_structure"] == "shared_framing_prefix_two_propositions"
    )
    assert shared["expected_candidate_count_min"] == 2
    assert len(shared["candidate_span_bounds"]) == 2
    assert len(shared["material_span_groups"]) == 2


def test_the_source_standing_family_survived_the_carry_over(
    specimens: list[dict[str, Any]],
) -> None:
    roles = {
        family["role"]
        for item in specimens
        for family in item["families"]
        if family["family_id"] == "CFO-10K-STANDING"
    }
    assert {"draft", "hypothetical", "unverified", "non_authoritative", "baseline"} <= roles


# --------------------------------------------------------------------------
# Shape and claim discipline
# --------------------------------------------------------------------------


def test_no_preregistered_type_is_one_the_boundary_would_refuse(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        declared = specimen["acceptable_unit_types"]
        if declared is None:
            continue
        assert declared
        assert set(declared) <= ACCEPTED_UNIT_TYPES, specimen["specimen_id"]


def test_the_corpus_states_its_own_claim_ceiling(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"]
    assert corpus["independent_validation_claim"] is False
    for denied in (
        "semantic correctness",
        "institutional admission",
        "authority",
        "enforceability",
        "legal interpretation",
        "production readiness",
        "runtime readiness",
        "cross-model generalization",
        "independent validation",
    ):
        assert denied in ceiling, denied


def test_the_corpus_records_that_framing_is_never_stripped_after_generation(
    corpus: dict[str, Any],
) -> None:
    note = corpus["framing_separation_note"]
    assert "asked of the provider" in note
    assert "never imposed afterwards" in note
    assert "No phrase list, regex, or post-generation trimming" in note


def test_the_corpus_contains_no_credential_shaped_material(corpus_bytes: bytes) -> None:
    body = corpus_bytes.decode("utf-8")
    for marker in ("NVIDIA_API_KEY", "nvapi-", "Bearer ", "api_key", "-----BEGIN"):
        assert marker not in body, marker


def test_the_reproduction_document_states_the_004_contract_and_ceiling(
    repo_root: Path,
) -> None:
    text = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-SEMANTICS-004" in text
    assert "independent_validation_claim" in text
    assert "NOT SELF-ADJUDICATED" in text
    assert "NVIDIA_API_KEY" in text
    assert "candidate_span" in text
    assert "underreach" in text.lower()
