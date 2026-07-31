"""Fail-closed contract tests for the Canada rights-clearance matrix."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

FREEZE_RELDIR = "benchmarks/corpus/canada/freeze-v0.1"
RIGHTS_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.json"
RIGHTS_MD_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.md"
EVIDENCE_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-EVIDENCE-LEDGER-v0.1.json"
REGISTRY_RELPATH = "benchmarks/preflight/canada/SOURCE-REGISTRY-PROPOSED-v0.1.json"

ALLOWED_DISPOSITIONS = frozenset(
    {
        "BLOCKED_PENDING_CLEARANCE",
        "CLEAR_INTERNAL_FREEZE_ONLY",
        "CLEAR_REPOSITORY_FREEZE",
    }
)
ALLOWED_PERMISSION_VALUES = frozenset({"SUPPORTED", "NOT_SUPPORTED", "UNRESOLVED"})
ALLOWED_STORAGE = frozenset({"REPOSITORY_FROZEN", "INTERNAL_ONLY", "NOT_STORED"})

REQUIRED_FIELDS = (
    "acquisition_target_role",
    "acquisition_target_url",
    "attribution_requirements",
    "authoritative_source_status",
    "automated_retrieval_permission",
    "copyright_owner",
    "evidence_capture_utc",
    "evidence_hashes",
    "internal_research_use",
    "jurisdiction",
    "logo_insignia_trademark_flag",
    "machine_processing_permission",
    "modification_restrictions",
    "personal_information_flag",
    "public_repository_redistribution_permission",
    "publisher",
    "reviewer_disposition",
    "rights_notice_url",
    "source_id",
    "source_specific_limitations",
    "terms_of_use_url",
    "third_party_material_flag",
)

# Language that would assert a legal conclusion the captured evidence does not state.
PROHIBITED_CLAIMS = (
    "legally approved",
    "legally cleared",
    "public domain",
    "no restrictions apply",
    "unrestricted use",
    "royalty free",
)


@pytest.fixture(scope="module")
def rights(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def evidence(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / EVIDENCE_RELPATH).read_text(encoding="utf-8"))
    )


def test_exactly_eleven_rights_records_exist(rights: dict[str, Any]) -> None:
    assert rights["source_unit_count"] == 11
    assert len(rights["records"]) == 11


def test_rights_records_cover_the_governing_source_set(
    repo_root: Path, rights: dict[str, Any]
) -> None:
    registry = json.loads((repo_root / REGISTRY_RELPATH).read_text(encoding="utf-8"))
    assert {record["source_id"] for record in rights["records"]} == {
        source["source_id"] for source in registry["sources"]
    }


def test_every_source_has_exactly_one_disposition_from_the_fixed_vocabulary(
    rights: dict[str, Any],
) -> None:
    seen: set[str] = set()
    for record in rights["records"]:
        assert record["reviewer_disposition"] in ALLOWED_DISPOSITIONS
        assert record["source_id"] not in seen
        seen.add(record["source_id"])
    assert len(seen) == 11


def test_disposition_counts_agree_with_the_records(rights: dict[str, Any]) -> None:
    counted: dict[str, int] = {}
    for record in rights["records"]:
        disposition = str(record["reviewer_disposition"])
        counted[disposition] = counted.get(disposition, 0) + 1
    assert rights["disposition_counts"] == counted
    assert sum(counted.values()) == 11


def test_every_required_field_is_present_and_non_empty(rights: dict[str, Any]) -> None:
    for record in rights["records"]:
        for field in REQUIRED_FIELDS:
            assert field in record, f"{record['source_id']} is missing {field}"
            assert record[field] not in (None, "", []), f"{record['source_id']}.{field} is empty"


def test_permission_and_storage_vocabularies_are_closed(rights: dict[str, Any]) -> None:
    for record in rights["records"]:
        for field in (
            "automated_retrieval_permission",
            "internal_research_use",
            "machine_processing_permission",
            "public_repository_redistribution_permission",
        ):
            assert record[field] in ALLOWED_PERMISSION_VALUES
        assert record["storage_classification"] in ALLOWED_STORAGE


def test_no_record_asserts_an_unevidenced_legal_conclusion(
    repo_root: Path, rights: dict[str, Any]
) -> None:
    # The vocabulary note names the prohibited phrases in order to disclaim them, so it is
    # excluded from the scan and separately required to be present.
    note = str(rights["vocabulary_note"])
    assert "No record asserts that a source is legally approved" in note
    serialized = json.dumps(rights["records"]).lower()
    markdown = (repo_root / RIGHTS_MD_RELPATH).read_text(encoding="utf-8").replace(note, "").lower()
    for claim in PROHIBITED_CLAIMS:
        assert claim not in serialized, f"rights JSON asserts {claim!r}"
        assert claim not in markdown, f"rights Markdown asserts {claim!r}"


def test_ambiguity_fails_closed_to_blocked(rights: dict[str, Any]) -> None:
    for record in rights["records"]:
        supported = (
            record["automated_retrieval_permission"] == "SUPPORTED"
            and record["internal_research_use"] == "SUPPORTED"
        )
        if not supported:
            assert record["reviewer_disposition"] == "BLOCKED_PENDING_CLEARANCE", (
                f"{record['source_id']} is not blocked despite an unsupported gate"
            )


def test_acquisition_is_permitted_only_when_both_gates_are_supported(
    rights: dict[str, Any],
) -> None:
    for record in rights["records"]:
        expected = (
            record["automated_retrieval_permission"] == "SUPPORTED"
            and record["internal_research_use"] == "SUPPORTED"
        )
        assert bool(record["acquisition_permitted"]) is expected
        assert bool(record["acquisition_permitted"]) is (
            record["reviewer_disposition"] != "BLOCKED_PENDING_CLEARANCE"
        )


def test_storage_classification_follows_the_disposition(rights: dict[str, Any]) -> None:
    expected = {
        "CLEAR_REPOSITORY_FREEZE": "REPOSITORY_FROZEN",
        "CLEAR_INTERNAL_FREEZE_ONLY": "INTERNAL_ONLY",
        "BLOCKED_PENDING_CLEARANCE": "NOT_STORED",
    }
    for record in rights["records"]:
        assert record["storage_classification"] == expected[record["reviewer_disposition"]]


def test_public_redistribution_requires_an_explicit_repository_disposition(
    rights: dict[str, Any],
) -> None:
    for record in rights["records"]:
        if record["reviewer_disposition"] == "CLEAR_REPOSITORY_FREEZE":
            assert record["public_repository_redistribution_permission"] == "SUPPORTED"
        else:
            assert record["public_repository_redistribution_permission"] != "SUPPORTED"


def test_every_record_cites_at_least_one_captured_evidence_hash_or_a_recorded_absence(
    rights: dict[str, Any], evidence: dict[str, Any]
) -> None:
    known = {record["evidence_id"]: record for record in evidence["records"]}
    for record in rights["records"]:
        assert record["evidence_hashes"]
        for cited in record["evidence_hashes"]:
            source = known[cited["evidence_id"]]
            assert cited["sha256"] == source["sha256"]
            assert cited["sha512"] == source["sha512"]
            assert cited["http_status"] == source["http_status"]
            assert cited["captured"] == source["captured"]
            if cited["captured"]:
                assert re.fullmatch(r"[0-9a-f]{64}", str(cited["sha256"]))
                assert re.fullmatch(r"[0-9a-f]{128}", str(cited["sha512"]))
            else:
                assert cited["sha256"] is None
                assert cited["sha512"] is None


def test_a_cleared_source_never_rests_only_on_uncaptured_evidence(
    rights: dict[str, Any],
) -> None:
    for record in rights["records"]:
        if record["reviewer_disposition"] == "BLOCKED_PENDING_CLEARANCE":
            continue
        assert any(cited["captured"] for cited in record["evidence_hashes"]), (
            f"{record['source_id']} is cleared with no captured evidence"
        )


def test_ca3_rights_record_names_the_english_xml_and_never_the_provenance_index(
    rights: dict[str, Any],
) -> None:
    ca3 = next(record for record in rights["records"] if record["source_id"] == "CA-3")
    assert ca3["acquisition_target_url"] == "https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml"
    assert ca3["acquisition_target_expected_content_type"] == "text/xml"
    assert ca3["acquisition_target_role"] == "CANONICAL_ARTIFACT"
    assert ca3["acquisition_target_url"] != ca3["provenance_url"]
    assert not ca3["acquisition_target_url"].endswith(".pdf")


def test_acquisition_target_is_never_the_provenance_url(rights: dict[str, Any]) -> None:
    for record in rights["records"]:
        if record["source_id"] == "CA-3":
            assert record["acquisition_target_url"] != record["provenance_url"]


def test_rights_matrix_targets_match_the_governing_registry(
    repo_root: Path, rights: dict[str, Any]
) -> None:
    registry = json.loads((repo_root / REGISTRY_RELPATH).read_text(encoding="utf-8"))
    targets = {source["source_id"]: source["acquisition_target"] for source in registry["sources"]}
    for record in rights["records"]:
        target = targets[record["source_id"]]
        assert record["acquisition_target_url"] == target["url"]
        assert record["acquisition_target_role"] == target["role"]
        assert record["acquisition_target_expected_content_type"] == target["expected_content_type"]


def test_blocked_sources_record_why_and_claim_no_screening(rights: dict[str, Any]) -> None:
    for record in rights["records"]:
        if record["reviewer_disposition"] != "BLOCKED_PENDING_CLEARANCE":
            continue
        assert record["disposition_basis"]
        for flag in (
            "third_party_material_flag",
            "personal_information_flag",
            "logo_insignia_trademark_flag",
        ):
            assert record[flag] == "NOT_SCREENED_NO_BYTES_ACQUIRED"


def test_rights_document_states_that_no_counsel_review_occurred(rights: dict[str, Any]) -> None:
    assert "no counsel review has occurred" in rights["counsel_review_note"]
    assert "not legal advice" in rights["counsel_review_note"]
