"""Contract tests over the frozen OIC-CANDIDATE-SEMANTICS-002 corpus.

Two obligations beyond the 001 contracts. First, the predecessor corpus must survive
untouched: 001 is the evidence its own receipt refers to, and rewriting it would falsify
that receipt retroactively. Second, every pre-registered source span must actually occur
in the specimen it is registered against -- a grounding metric measured against a span the
source does not contain would report a confident and meaningless number.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

DIR_001 = "benchmarks/characterization/candidate-semantics-001"
DIR_002 = "benchmarks/characterization/candidate-semantics-002"
CORPUS_RELPATH = f"{DIR_002}/CORPUS-v0.2.json"
FREEZE_RELPATH = f"{DIR_002}/CORPUS-FREEZE-v0.2.json"
README_RELPATH = f"{DIR_002}/README.md"

FROZEN_SPECIMEN_COUNT = 40
FROZEN_CORPUS_SHA256 = "f97b1a80d86f821495674dacccb8bc130f8bf78e559bab22f7aa0b5a32dd3b7c"
PREDECESSOR_SHA256 = "21053e4a8688dd80583975a551ea13652650552044faf2b3e38572ae59f3e4a0"

CARRIED_OVER_COUNT = 32
NEW_SPECIMEN_IDS = (
    "CSEM-033",
    "CSEM-034",
    "CSEM-035",
    "CSEM-036",
    "CSEM-037",
    "CSEM-038",
    "CSEM-039",
    "CSEM-040",
)

#: The diagnostic coverage OIC-CANDIDATE-SEMANTICS-002 requires the new specimens to add.
REQUIRED_DIAGNOSTIC_CATEGORIES = (
    "passive_no_actor",
    "explicit_target",
    "condition_vs_operative",
    "advisory",
    "evidence_duty",
    "numeric_threshold",
)

GROUNDING_FIELDS = (
    "actor_explicitly_named",
    "target_explicitly_named",
    "expected_target_spans",
    "required_condition_spans",
    "material_qualifier_spans",
    "non_operative_predicate_spans",
)
SPAN_FIELDS = (
    "expected_target_spans",
    "required_condition_spans",
    "material_qualifier_spans",
    "non_operative_predicate_spans",
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
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / DIR_001 / "CORPUS-v0.1.json").read_text(encoding="utf-8")),
    )


# --------------------------------------------------------------------------
# The predecessor is untouched
# --------------------------------------------------------------------------


def test_the_001_corpus_is_byte_identical_to_its_freeze(repo_root: Path) -> None:
    body = (repo_root / DIR_001 / "CORPUS-v0.1.json").read_bytes()
    assert hashlib.sha256(body).hexdigest() == PREDECESSOR_SHA256


def test_the_002_corpus_records_which_corpus_it_succeeds(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    assert corpus["predecessor_corpus_id"] == "OIC-CANDIDATE-SEMANTICS-001"
    assert corpus["predecessor_corpus_sha256"] == PREDECESSOR_SHA256
    assert freeze["predecessor_corpus_sha256"] == PREDECESSOR_SHA256


def test_every_predecessor_specimen_is_carried_over_verbatim(
    specimens: list[dict[str, Any]], predecessor: dict[str, Any]
) -> None:
    """Same id, same source text, same expectations. Only grounding fields were added."""
    carried = {item["specimen_id"]: item for item in specimens}
    assert len(predecessor["specimens"]) == CARRIED_OVER_COUNT
    for original in predecessor["specimens"]:
        successor = carried[original["specimen_id"]]
        for key, value in original.items():
            assert successor[key] == value, (original["specimen_id"], key)
        assert set(successor) - set(original) == set(GROUNDING_FIELDS)


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
        assert recorded[specimen["specimen_id"]] == expected, specimen["specimen_id"]


def test_specimen_count_and_ids_are_frozen(
    specimens: list[dict[str, Any]], corpus: dict[str, Any]
) -> None:
    identifiers = [item["specimen_id"] for item in specimens]
    assert len(specimens) == FROZEN_SPECIMEN_COUNT
    assert corpus["specimen_count"] == FROZEN_SPECIMEN_COUNT
    assert len(set(identifiers)) == len(identifiers)
    assert identifiers == sorted(identifiers)
    assert identifiers[-len(NEW_SPECIMEN_IDS) :] == list(NEW_SPECIMEN_IDS)


# --------------------------------------------------------------------------
# Source-grounding pre-registration
# --------------------------------------------------------------------------


def test_every_specimen_carries_the_grounding_fields(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for field in GROUNDING_FIELDS:
            assert field in specimen, (specimen["specimen_id"], field)


def test_every_declared_span_actually_occurs_in_its_own_source(
    specimens: list[dict[str, Any]],
) -> None:
    """A span the source does not contain would make its metric meaningless."""
    for specimen in specimens:
        for field in SPAN_FIELDS:
            for span in specimen[field] or []:
                assert span in specimen["source_text"], (specimen["specimen_id"], field, span)


def test_declared_spans_are_non_empty_lists_or_null(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for field in SPAN_FIELDS:
            value = specimen[field]
            assert value is None or (isinstance(value, list) and value), (
                specimen["specimen_id"],
                field,
            )


def test_actor_and_target_flags_are_boolean_or_null(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for field in ("actor_explicitly_named", "target_explicitly_named"):
            assert specimen[field] in (True, False, None), (specimen["specimen_id"], field)


def test_a_declared_target_comes_with_the_spans_that_express_it(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["target_explicitly_named"] is True:
            assert specimen["expected_target_spans"], specimen["specimen_id"]


def test_no_negative_control_pre_registers_grounding_expectations(
    specimens: list[dict[str, Any]],
) -> None:
    """Nothing is expected to be extracted, so nothing is expected to be preserved."""
    for specimen in specimens:
        if specimen["normative_expected"]:
            continue
        for field in GROUNDING_FIELDS:
            assert specimen[field] is None, (specimen["specimen_id"], field)


def test_the_corpus_states_what_a_span_list_means(corpus: dict[str, Any]) -> None:
    assert "DISJUNCTIVE" in corpus["span_list_semantics"]
    assert "ONE required element" in corpus["span_list_semantics"]


# --------------------------------------------------------------------------
# Diagnostic coverage for the evidenced failure classes
# --------------------------------------------------------------------------


def test_the_new_specimens_cover_every_required_diagnostic_category(
    specimens: list[dict[str, Any]],
) -> None:
    added = {
        specimen["category"]
        for specimen in specimens
        if specimen["specimen_id"] in NEW_SPECIMEN_IDS
    }
    missing = sorted(set(REQUIRED_DIAGNOSTIC_CATEGORIES) - added)
    assert missing == [], f"uncovered diagnostic categories: {missing}"


def test_a_fully_passive_specimen_preregisters_no_actor(specimens: list[dict[str, Any]]) -> None:
    passive = [item for item in specimens if item["category"] == "passive_no_actor"]
    assert passive
    for specimen in passive:
        assert specimen["actor_explicitly_named"] is False
        assert specimen["normative_expected"] is True


def test_the_corpus_has_specimens_with_an_explicit_target(
    specimens: list[dict[str, Any]],
) -> None:
    targeted = [item for item in specimens if item["target_explicitly_named"] is True]
    assert len(targeted) >= 4
    assert any(item["category"] == "explicit_target" for item in targeted)


def test_a_trigger_predicate_is_preregistered_for_the_role_separation_probe(
    specimens: list[dict[str, Any]],
) -> None:
    probes = [item for item in specimens if item["non_operative_predicate_spans"]]
    assert len(probes) >= 3
    assert any(item["category"] == "condition_vs_operative" for item in probes)
    for specimen in probes:
        assert specimen["required_condition_spans"], specimen["specimen_id"]


def test_advisory_language_is_covered_by_more_than_one_phrasing(
    specimens: list[dict[str, Any]],
) -> None:
    advisory = [item for item in specimens if item["category"] == "advisory"]
    assert len(advisory) >= 3
    assert len({item["source_text"] for item in advisory}) == len(advisory)
    for specimen in advisory:
        assert specimen["acceptable_unit_types"] == ["advisory"]


def test_evidence_duty_is_covered_by_more_than_one_specimen(
    specimens: list[dict[str, Any]],
) -> None:
    duties = [item for item in specimens if item["category"] == "evidence_duty"]
    assert len(duties) >= 2
    for specimen in duties:
        assert "evidence_duty" in (specimen["acceptable_unit_types"] or [])


def test_quantitative_qualifiers_are_preregistered_widely(
    specimens: list[dict[str, Any]],
) -> None:
    measured = [item for item in specimens if item["material_qualifier_spans"]]
    assert len(measured) >= 10


def test_conditions_are_preregistered_widely(specimens: list[dict[str, Any]]) -> None:
    measured = [item for item in specimens if item["required_condition_spans"]]
    assert len(measured) >= 10


# --------------------------------------------------------------------------
# Shape and claim discipline, carried forward from the 001 contracts
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


def test_negative_specimens_still_expect_exactly_zero(specimens: list[dict[str, Any]]) -> None:
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert len(negatives) >= 5
    for specimen in negatives:
        assert specimen["expected_candidate_count_min"] == 0
        assert specimen["expected_candidate_count_max"] == 0


def test_the_corpus_states_its_own_claim_ceiling(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"].lower()
    assert corpus["independent_validation_claim"] is False
    for denied in ("semantic correctness", "institutional admission", "authority"):
        assert denied in ceiling, denied


def test_the_corpus_contains_no_credential_shaped_material(corpus_bytes: bytes) -> None:
    body = corpus_bytes.decode("utf-8")
    for marker in ("NVIDIA_API_KEY", "nvapi-", "Bearer ", "api_key", "-----BEGIN"):
        assert marker not in body, marker


def test_the_reproduction_document_records_the_contract_revision(repo_root: Path) -> None:
    text = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-SEMANTICS-002" in text
    assert "NVIDIA_API_KEY" in text
    assert "independent_validation_claim" in text
    assert "verbatim" in text.lower()
    assert "target" in text
