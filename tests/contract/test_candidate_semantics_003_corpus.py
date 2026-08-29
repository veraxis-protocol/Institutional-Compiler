"""Frozen-contract checks for the OIC-CANDIDATE-SEMANTICS-003 corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

DIR = "benchmarks/characterization/candidate-semantics-003"
CORPUS_RELPATH = f"{DIR}/CORPUS-v0.3.json"
FREEZE_RELPATH = f"{DIR}/CORPUS-FREEZE-v0.3.json"
FROZEN_SHA256 = "8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a"
PREDECESSOR_SHA256 = "f97b1a80d86f821495674dacccb8bc130f8bf78e559bab22f7aa0b5a32dd3b7c"
FROZEN_COUNT = 26
REQUIRED_DIAGNOSTICS = {
    "passive_no_actor",
    "explicit_condition",
    "quantitative_threshold",
    "explicit_recipient",
    "trigger_consequence",
    "advisory",
    "evidence_retention",
    "multi_unit",
}


@pytest.fixture(scope="module")
def corpus_bytes(repo_root: Path) -> bytes:
    return (repo_root / CORPUS_RELPATH).read_bytes()


@pytest.fixture(scope="module")
def corpus(corpus_bytes: bytes) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(corpus_bytes))


@pytest.fixture(scope="module")
def specimens(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", corpus["specimens"])


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / FREEZE_RELPATH).read_text(encoding="utf-8"))
    )


def test_corpus_bytes_are_frozen(corpus_bytes: bytes) -> None:
    assert hashlib.sha256(corpus_bytes).hexdigest() == FROZEN_SHA256


def test_freeze_matches_exact_corpus(
    corpus_bytes: bytes, specimens: list[dict[str, Any]], freeze: dict[str, Any]
) -> None:
    assert freeze["corpus_sha256"] == hashlib.sha256(corpus_bytes).hexdigest()
    assert freeze["corpus_byte_length"] == len(corpus_bytes)
    assert freeze["specimen_count"] == len(specimens) == FROZEN_COUNT
    assert freeze["specimen_ids"] == [item["specimen_id"] for item in specimens]
    assert freeze["corpus_relpath"] == CORPUS_RELPATH


def test_predecessor_is_pinned_and_unchanged(repo_root: Path, corpus: dict[str, Any]) -> None:
    predecessor = repo_root / "benchmarks/characterization/candidate-semantics-002/CORPUS-v0.2.json"
    assert hashlib.sha256(predecessor.read_bytes()).hexdigest() == PREDECESSOR_SHA256
    assert corpus["predecessor_corpus_sha256"] == PREDECESSOR_SHA256


def test_every_003_source_is_carried_verbatim_from_002(
    repo_root: Path, specimens: list[dict[str, Any]]
) -> None:
    predecessor = json.loads(
        (
            repo_root / "benchmarks/characterization/candidate-semantics-002/CORPUS-v0.2.json"
        ).read_text(encoding="utf-8")
    )
    source_by_id = {item["specimen_id"]: item["source_text"] for item in predecessor["specimens"]}
    for item in specimens:
        assert item["source_text"] == source_by_id[item["specimen_id"]]


def test_every_frozen_source_digest_matches(
    specimens: list[dict[str, Any]], freeze: dict[str, Any]
) -> None:
    assert len(freeze["specimen_source_sha256"]) == FROZEN_COUNT
    for item in specimens:
        digest = hashlib.sha256(item["source_text"].encode()).hexdigest()
        assert freeze["specimen_source_sha256"][item["specimen_id"]] == digest


def test_003_schema_omits_obsolete_role_expectations(specimens: list[dict[str, Any]]) -> None:
    obsolete = {
        "actor_explicitly_named",
        "target_explicitly_named",
        "expected_target_spans",
        "required_condition_spans",
        "material_qualifier_spans",
        "non_operative_predicate_spans",
    }
    for item in specimens:
        assert not (set(item) & obsolete), item["specimen_id"]


def test_all_preregistered_material_and_bound_spans_are_literal(
    specimens: list[dict[str, Any]],
) -> None:
    for item in specimens:
        groups = item["material_span_groups"] or []
        for group in groups:
            assert group
            for span in group:
                assert span in item["source_text"], (item["specimen_id"], span)
        bounds = item["candidate_span_bounds"] or []
        for bound in bounds:
            assert bound in item["source_text"], (item["specimen_id"], bound)


def test_negative_controls_have_no_candidate_expectations(specimens: list[dict[str, Any]]) -> None:
    negatives = [item for item in specimens if not item["normative_expected"]]
    assert len(negatives) >= 5
    for item in negatives:
        assert item["expected_candidate_count_min"] == 0
        assert item["expected_candidate_count_max"] == 0
        assert item["acceptable_unit_types"] is None
        assert item["material_span_groups"] is None


def test_redesign_diagnostics_are_explicit(specimens: list[dict[str, Any]]) -> None:
    observed = {tag for item in specimens for tag in item["diagnostic_tags"]}
    assert observed >= REQUIRED_DIAGNOSTICS


def test_multi_unit_passive_specimen_requires_two_candidates(
    specimens: list[dict[str, Any]],
) -> None:
    item = next(entry for entry in specimens if entry["specimen_id"] == "CSEM-025")
    assert item["expected_candidate_count_min"] == 2
    assert {"multi_unit", "passive_voice"} <= set(item["diagnostic_tags"])
    assert len(item["candidate_span_bounds"]) == 2


def test_claim_ceiling_and_independence_are_explicit(corpus: dict[str, Any]) -> None:
    ceiling = corpus["claim_ceiling"]
    for phrase in (
        "semantic correctness",
        "institutional admission",
        "authority",
        "enforceability",
        "legal interpretation",
        "runtime readiness",
        "production readiness",
        "independent validation",
    ):
        assert phrase in ceiling
    assert corpus["independent_validation_claim"] is False


def test_governing_candidate_schema_matches_the_minimal_003_contract(repo_root: Path) -> None:
    schema = json.loads(
        (repo_root / "schemas/draft/candidate-normative-unit.schema.json").read_text(
            encoding="utf-8"
        )
    )
    exact_fields = {
        "unit_id",
        "candidate_span",
        "unit_type",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    }
    assert set(schema["properties"]) == exact_fields
    assert set(schema["required"]) == exact_fields
    assert schema["additionalProperties"] is False
    assert schema["properties"]["interpretation_state"] == {"const": "extracted"}
    assert schema["properties"]["epistemic_state"] == {"const": "uncertain"}
