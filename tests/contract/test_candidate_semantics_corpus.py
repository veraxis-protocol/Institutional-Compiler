"""Contract tests over the frozen OIC-CANDIDATE-SEMANTICS-001 corpus.

The corpus is the input side of a characterization work order, so what has to hold is
that it is frozen, complete, internally consistent, and honest about what it claims. It
is deliberately not asserted that any model answers any specimen in any particular way.

The required coverage list is restated here rather than read from the corpus, so a
specimen quietly dropped or recategorized fails instead of redefining the requirement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

CORPUS_DIR = "benchmarks/characterization/candidate-semantics-001"
CORPUS_RELPATH = f"{CORPUS_DIR}/CORPUS-v0.1.json"
FREEZE_RELPATH = f"{CORPUS_DIR}/CORPUS-FREEZE-v0.1.json"
README_RELPATH = f"{CORPUS_DIR}/README.md"

FROZEN_SPECIMEN_COUNT = 32
FROZEN_CORPUS_SHA256 = "21053e4a8688dd80583975a551ea13652650552044faf2b3e38572ae59f3e4a0"

#: The live probe recorded in the work order. Its exact bytes must stay in the corpus.
CFO_NORM = "A payment above $10,000 requires approval by the Chief Financial Officer."
LIVE_PROBE_TEXT = "DEVELOPMENT SYNTHETIC SOURCE — NOT AN AUTHORITATIVE POLICY. " + CFO_NORM

#: Every category the work order requires the corpus to cover.
REQUIRED_CATEGORIES = (
    "simple_obligation",
    "prohibition",
    "permission",
    "delegation",
    "mandate",
    "definition",
    "institutional_power",
    "explicit_condition",
    "numeric_threshold",
    "exception_carve_out",
    "evidence_duty",
    "review_duty",
    "escalation",
    "remedy",
    "temporal_trigger",
    "discretion",
    "advisory",
    "descriptive_non_normative",
    "operational_fact",
    "marketing_prose",
    "standing_draft",
    "standing_non_authoritative",
    "standing_hypothetical",
    "multi_unit",
    "condition_plus_exception",
    "threshold_plus_approval",
    "paraphrase_variant",
    "standing_unverified",
    "ambiguous_modal",
    "institutional_vocabulary_no_norm",
)

#: The unit-type vocabulary the parser accepts. A preregistered set may not name a type
#: the boundary would refuse.
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
        "dict[str, Any]",
        json.loads((repo_root / FREEZE_RELPATH).read_text(encoding="utf-8")),
    )


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


def test_specimen_count_is_frozen(specimens: list[dict[str, Any]], corpus: dict[str, Any]) -> None:
    assert len(specimens) == FROZEN_SPECIMEN_COUNT
    assert corpus["specimen_count"] == FROZEN_SPECIMEN_COUNT


def test_specimen_ids_are_unique_and_well_formed(specimens: list[dict[str, Any]]) -> None:
    identifiers = [specimen["specimen_id"] for specimen in specimens]
    assert len(set(identifiers)) == len(identifiers)
    assert identifiers == sorted(identifiers)
    for identifier in identifiers:
        assert identifier.startswith("CSEM-")
        assert identifier[5:].isdigit()


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------


def test_every_specimen_carries_the_required_fields(specimens: list[dict[str, Any]]) -> None:
    required = {
        "specimen_id",
        "category",
        "source_text",
        "normative_expected",
        "expected_candidate_count_min",
        "expected_candidate_count_max",
        "acceptable_unit_types",
        "families",
        "threshold_markers",
        "characterization_notes",
        "claim_ceiling",
    }
    for specimen in specimens:
        assert set(specimen) == required, specimen["specimen_id"]
        assert specimen["source_text"].strip(), specimen["specimen_id"]
        assert specimen["characterization_notes"].strip(), specimen["specimen_id"]
        assert specimen["claim_ceiling"].strip(), specimen["specimen_id"]


def test_positive_specimens_expect_at_least_one_candidate(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        if specimen["normative_expected"]:
            assert specimen["expected_candidate_count_min"] >= 1, specimen["specimen_id"]


def test_negative_specimens_expect_exactly_zero(specimens: list[dict[str, Any]]) -> None:
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert len(negatives) >= 5
    for specimen in negatives:
        assert specimen["expected_candidate_count_min"] == 0, specimen["specimen_id"]
        assert specimen["expected_candidate_count_max"] == 0, specimen["specimen_id"]
        assert specimen["acceptable_unit_types"] is None, specimen["specimen_id"]


def test_no_preregistered_type_is_one_the_boundary_would_refuse(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        declared = specimen["acceptable_unit_types"]
        if declared is None:
            continue
        assert declared, specimen["specimen_id"]
        assert set(declared) <= ACCEPTED_UNIT_TYPES, specimen["specimen_id"]


def test_declared_thresholds_actually_appear_in_their_source_text(
    specimens: list[dict[str, Any]],
) -> None:
    for specimen in specimens:
        markers = specimen["threshold_markers"]
        if markers is None:
            continue
        assert markers, specimen["specimen_id"]
        assert any(marker in specimen["source_text"] for marker in markers), specimen["specimen_id"]


# --------------------------------------------------------------------------
# Required coverage
# --------------------------------------------------------------------------


def test_every_required_category_is_covered(specimens: list[dict[str, Any]]) -> None:
    observed = {specimen["category"] for specimen in specimens}
    missing = sorted(set(REQUIRED_CATEGORIES) - observed)
    assert missing == [], f"uncovered required categories: {missing}"


def test_no_category_outside_the_required_list_appears(
    specimens: list[dict[str, Any]],
) -> None:
    observed = {specimen["category"] for specimen in specimens}
    assert sorted(observed - set(REQUIRED_CATEGORIES)) == []


def test_the_live_probe_specimen_is_frozen_byte_for_byte(
    specimens: list[dict[str, Any]],
) -> None:
    """The exact fragment the work order recorded a live result for."""
    by_text = {specimen["source_text"]: specimen for specimen in specimens}
    assert LIVE_PROBE_TEXT in by_text
    probe = by_text[LIVE_PROBE_TEXT]
    assert probe["specimen_id"] == "CSEM-022"
    assert probe["normative_expected"] is True
    assert probe["category"] == "standing_non_authoritative"


def test_the_undisclaimed_baseline_of_the_same_norm_is_frozen(
    specimens: list[dict[str, Any]],
) -> None:
    by_text = {specimen["source_text"]: specimen for specimen in specimens}
    assert CFO_NORM in by_text
    assert by_text[CFO_NORM]["specimen_id"] == "CSEM-027"


def test_a_multi_unit_specimen_expects_more_than_one_candidate(
    specimens: list[dict[str, Any]],
) -> None:
    multi = [item for item in specimens if item["category"] == "multi_unit"]
    assert multi
    for specimen in multi:
        assert specimen["expected_candidate_count_min"] >= 2


# --------------------------------------------------------------------------
# Families
# --------------------------------------------------------------------------


def _families(specimens: list[dict[str, Any]], kind: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for specimen in specimens:
        for family in specimen["families"]:
            if family["family_kind"] == kind:
                grouped.setdefault(family["family_id"], []).append(specimen)
    return grouped


def test_family_memberships_are_well_formed(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        for family in specimen["families"]:
            assert set(family) == {"family_id", "family_kind", "role"}
            assert family["family_kind"] in {"source_standing", "paraphrase"}
            assert family["family_id"].strip()
            assert family["role"].strip()


def test_a_source_standing_family_varies_only_the_standing_language(
    specimens: list[dict[str, Any]],
) -> None:
    families = _families(specimens, "source_standing")
    assert families
    for family_id, members in families.items():
        assert len(members) >= 3, family_id
        roles = [
            family["role"]
            for member in members
            for family in member["families"]
            if family["family_id"] == family_id
        ]
        assert "baseline" in roles
        assert len(set(roles)) == len(roles)
        # Every member states the same underlying norm.
        assert all("Chief Financial Officer" in member["source_text"] for member in members)
        assert all(member["normative_expected"] for member in members)


def test_a_paraphrase_family_holds_materially_different_phrasings(
    specimens: list[dict[str, Any]],
) -> None:
    families = _families(specimens, "paraphrase")
    assert families
    for family_id, members in families.items():
        assert len(members) >= 3, family_id
        texts = [member["source_text"] for member in members]
        assert len(set(texts)) == len(texts)
        assert all(member["normative_expected"] for member in members)


def test_the_standing_and_paraphrase_families_share_one_baseline(
    specimens: list[dict[str, Any]],
) -> None:
    """CSEM-027 is the undisclaimed, unparaphrased form both families vary from."""
    baseline = next(item for item in specimens if item["specimen_id"] == "CSEM-027")
    kinds = {family["family_kind"] for family in baseline["families"]}
    assert kinds == {"source_standing", "paraphrase"}
    assert all(family["role"] == "baseline" for family in baseline["families"])


# --------------------------------------------------------------------------
# Claim discipline
# --------------------------------------------------------------------------


def test_the_corpus_states_its_own_claim_ceiling(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"].lower()
    assert corpus["independent_validation_claim"] is False
    for denied in ("semantic correctness", "institutional admission", "authority"):
        assert denied in ceiling, denied


def test_no_specimen_claims_institutional_standing(specimens: list[dict[str, Any]]) -> None:
    for specimen in specimens:
        ceiling = specimen["claim_ceiling"].lower()
        assert "synthetic" in ceiling
        assert "engineering test intent" in ceiling


def test_the_corpus_contains_no_credential_shaped_material(corpus_bytes: bytes) -> None:
    body = corpus_bytes.decode("utf-8")
    for marker in ("NVIDIA_API_KEY", "nvapi-", "Bearer ", "api_key", "-----BEGIN"):
        assert marker not in body, marker


def test_the_reproduction_document_exists_and_states_the_ceiling(repo_root: Path) -> None:
    text = (repo_root / README_RELPATH).read_text(encoding="utf-8")
    assert "OIC-CANDIDATE-SEMANTICS-001" in text
    assert "characterization" in text.lower()
    assert "NVIDIA_API_KEY" in text
    assert "independent_validation_claim" in text
