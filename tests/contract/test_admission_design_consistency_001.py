"""Executable-input contract closure for Admission Boundary 001."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import FormatChecker
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource

pytestmark = pytest.mark.contract

DESIGN = Path("design/admission-boundary-001")
STARTING_SHA = "e445c25a4f657c59fbfe32617f46153ac678150c"
V01_CORPUS_SHA = "2181cada7cda18a0bde77db89a7eaf701ad044253c3e179024ac7f51d50bc8e7"
V01_FREEZE_SHA = "566b5ad56a4c24c51b4547de0aed394bf31f59f7248a1c99596e85e116deef12"
AUTHORITY_SCHEMA_SHA = "f1d91532a1a50be1f5d969ce8134bdb445f4a62fee0e62565437c2c4be196c98"
V02_CORPUS_SHA = "969ddf9a853155ce6ed27f30f1c41e76f7a1ff37a42071d2141d9966907add81"
V02_CORPUS_BYTES = 209358
V02_FREEZE_SHA = "9f250c07447be532a022c3b4bf7e712283fc5567caefa541585fbbf643f048de"
CROSSWALK_SHA = "1b5dbf0fc25ccb9bbd14fbbb8092bd1e4a61008509b29370ad25c4d07008afbd"
RULESET_DIGEST = "sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c"
STATE_TO_REASON = {
    "ADMITTED": "OIC-ADM-0000",
    "CANDIDATE_INPUT_INVALID": "OIC-ADM-1001",
    "SOURCE_NOT_REGISTERED": "OIC-ADM-1002",
    "SOURCE_VERSION_MISMATCH": "OIC-ADM-1003",
    "SOURCE_DIGEST_MISMATCH": "OIC-ADM-1004",
    "MISSING_AUTHORITY_EVIDENCE": "OIC-ADM-1005",
    "NOT_YET_EFFECTIVE": "OIC-ADM-1006",
    "EXPIRED": "OIC-ADM-1007",
    "SUPERSEDED": "OIC-ADM-1008",
    "REVOKED": "OIC-ADM-1009",
    "OUT_OF_SCOPE": "OIC-ADM-1010",
    "CONFLICTING_AUTHORITY": "OIC-ADM-1011",
    "AUTHORITY_REGISTRY_UNAVAILABLE": "OIC-ADM-1012",
    "AUTHORITY_EVIDENCE_STALE": "OIC-ADM-1013",
    "ADMISSION_NOT_ESTABLISHED": "OIC-ADM-1099",
}


def _load(repo_root: Path, name: str) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / DESIGN / name).read_text(encoding="utf-8")),
    )


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _evidence_digest(evidence: dict[str, Any]) -> str:
    projection = {key: value for key, value in evidence.items() if key != "evidence_digest"}
    return _sha(projection)


def _receipt_projection(input_value: dict[str, Any], state: str, reason: str) -> dict[str, Any]:
    evidence = cast("list[dict[str, Any]]", input_value["authority_evidence"])
    receipt: dict[str, Any] = {
        "candidate_unit_id": input_value["candidate"]["unit_id"],
        "candidate_projection_digest": _sha(input_value["candidate"]),
        "source_id": input_value["source_registration"]["source_id"],
        "source_version": input_value["source_registration"]["source_version"],
        "source_digest": input_value["source_registration"]["source_digest"],
        "authority_evidence_refs": [item["evidence_id"] for item in evidence],
        "authority_evidence_digests": [item["evidence_digest"] for item in evidence],
        "evaluation_time": input_value["evaluation_time"],
        "evaluation_scope": input_value["evaluation_scope"],
        "admission_state": state,
        "reason_code": reason,
        "evaluator_id": input_value["evaluator"]["evaluator_id"],
        "evaluator_version": input_value["evaluator"]["evaluator_version"],
        "ruleset_id": input_value["ruleset"]["ruleset_id"],
        "ruleset_digest": input_value["ruleset"]["ruleset_digest"],
        "input_digest": _sha(input_value),
        "evidence_digest": _sha(evidence),
    }
    receipt["admission_receipt_id"] = (
        f"admrec-sha256:{hashlib.sha256(_canonical(receipt)).hexdigest()}"
    )
    return receipt


def _schema_validators(
    repo_root: Path,
) -> tuple[Draft202012Validator, Draft202012Validator, Draft202012Validator]:
    input_schema = _load(repo_root, "ADMISSION-INPUT-v0.1.schema.json")
    authority_schema = _load(repo_root, "AUTHORITY-EVIDENCE-v0.1.schema.json")
    receipt_schema = _load(repo_root, "ADMISSION-RECEIPT-v0.1.schema.json")
    resource = Resource.from_contents(authority_schema)
    registry = Registry().with_resource(cast("str", authority_schema["$id"]), resource)
    return (
        Draft202012Validator(input_schema, registry=registry, format_checker=FormatChecker()),
        Draft202012Validator(authority_schema, format_checker=FormatChecker()),
        Draft202012Validator(receipt_schema, format_checker=FormatChecker()),
    )


def _timestamps(value: object, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if (
                child is not None
                and isinstance(child, str)
                and (
                    key == "evaluation_time"
                    or key == "issued_at"
                    or key == "published_at"
                    or key == "adopted_at"
                    or key.endswith("_from")
                    or key.endswith("_until")
                    or key.endswith("_at")
                )
            ):
                yield child_path, child
            yield from _timestamps(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _timestamps(child, f"{path}[{index}]")


def _assert_positive_fixture_consistency(vector: dict[str, Any]) -> None:
    assert vector["expected_admission_state"] == "ADMITTED"
    input_value = vector["executable_input"]
    registration = input_value["source_registration"]
    evidence = input_value["authority_evidence"]
    assert evidence
    for item in evidence:
        assert item["source_version"] == registration["source_version"]
        assert item["source_digest"] == registration["source_digest"]
        assert item["admission_warrant"]["source_version"] == registration["source_version"]
        assert item["admission_warrant"]["source_digest"] == registration["source_digest"]


def _assert_no_default_authority(old: dict[str, Any], new: dict[str, Any]) -> None:
    if not old["authority_evidence"]:
        assert new["executable_input"]["authority_evidence"] == []


@pytest.fixture(scope="module")
def legacy(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "TEST-VECTORS-v0.1.json")


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "TEST-VECTORS-v0.2.json")


@pytest.fixture(scope="module")
def crosswalk(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "VECTOR-CROSSWALK-v0.1.json")


def test_historical_v01_and_authority_schema_are_byte_identical(repo_root: Path) -> None:
    expected = {
        "TEST-VECTORS-v0.1.json": V01_CORPUS_SHA,
        "TEST-VECTORS-FREEZE-v0.1.json": V01_FREEZE_SHA,
        "AUTHORITY-EVIDENCE-v0.1.schema.json": AUTHORITY_SCHEMA_SHA,
    }
    for name, digest in expected.items():
        assert hashlib.sha256((repo_root / DESIGN / name).read_bytes()).hexdigest() == digest


def test_v02_corpus_crosswalk_and_freeze_are_byte_frozen(repo_root: Path) -> None:
    corpus_body = (repo_root / DESIGN / "TEST-VECTORS-v0.2.json").read_bytes()
    assert len(corpus_body) == V02_CORPUS_BYTES
    assert hashlib.sha256(corpus_body).hexdigest() == V02_CORPUS_SHA
    assert (
        hashlib.sha256(
            (repo_root / DESIGN / "TEST-VECTORS-FREEZE-v0.2.json").read_bytes()
        ).hexdigest()
        == V02_FREEZE_SHA
    )
    assert (
        hashlib.sha256((repo_root / DESIGN / "VECTOR-CROSSWALK-v0.1.json").read_bytes()).hexdigest()
        == CROSSWALK_SHA
    )


def test_v02_freeze_manifest_pins_every_executable_contract_artifact(repo_root: Path) -> None:
    freeze = _load(repo_root, "TEST-VECTORS-FREEZE-v0.2.json")
    expected = {
        "ADMISSION-INPUT-v0.1.schema.json": freeze["schemas"]["admission_input_sha256"],
        "AUTHORITY-EVIDENCE-v0.1.schema.json": freeze["schemas"]["authority_evidence_sha256"],
        "ADMISSION-RECEIPT-v0.1.schema.json": freeze["schemas"]["receipt_sha256"],
        "STATE-INPUT-MAPPING-v0.1.json": freeze["state_mapping"]["file_sha256"],
        "EXECUTABLE-INPUT-CONTRACT-v0.1.md": freeze["canonicalization_contract_sha256"],
        "VECTOR-CROSSWALK-v0.1.json": freeze["crosswalk"]["sha256"],
        "TEST-VECTORS-v0.2.json": freeze["executable_corpus"]["sha256"],
    }
    for name, expected_digest in expected.items():
        observed = hashlib.sha256((repo_root / DESIGN / name).read_bytes()).hexdigest()
        assert observed == expected_digest, name
    assert freeze["executable_corpus"]["bytes"] == V02_CORPUS_BYTES
    assert freeze["state_mapping"]["ruleset_digest"] == RULESET_DIGEST
    assert freeze["schemas"]["authority_evidence_disposition"] == (
        "PRESERVED BYTE-IDENTICAL AND DESIGNATED EXECUTABLE"
    )


def test_all_design_schemas_are_valid_json_schemas(repo_root: Path) -> None:
    for name in (
        "ADMISSION-INPUT-v0.1.schema.json",
        "AUTHORITY-EVIDENCE-v0.1.schema.json",
        "ADMISSION-RECEIPT-v0.1.schema.json",
    ):
        Draft202012Validator.check_schema(_load(repo_root, name))


def test_every_executable_input_and_authority_evidence_validates(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    input_validator, authority_validator, _receipt_validator = _schema_validators(repo_root)
    vectors = cast("list[dict[str, Any]]", corpus["vectors"])
    assert len(vectors) == corpus["vector_count"] == 38
    assert corpus["legacy_vector_count"] == 30
    assert corpus["precedence_diagnostic_count"] == 8
    for vector in vectors:
        input_value = cast("dict[str, Any]", vector["executable_input"])
        assert not list(input_validator.iter_errors(input_value)), vector["vector_id"]
        for evidence in input_value["authority_evidence"]:
            assert not list(authority_validator.iter_errors(evidence)), vector["vector_id"]


def test_every_expected_receipt_validates_and_matches_all_digest_projections(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    _input_validator, _authority_validator, receipt_validator = _schema_validators(repo_root)
    for vector in corpus["vectors"]:
        receipt = vector["expected_receipt"]
        assert not list(receipt_validator.iter_errors(receipt)), vector["vector_id"]
        expected = _receipt_projection(
            vector["executable_input"],
            vector["expected_admission_state"],
            vector["reason_code"],
        )
        assert receipt == expected, vector["vector_id"]
        for evidence in vector["executable_input"]["authority_evidence"]:
            assert evidence["evidence_digest"] == _evidence_digest(evidence)


def test_v01_metadata_outcomes_and_claims_are_preserved_exactly(
    legacy: dict[str, Any], corpus: dict[str, Any], crosswalk: dict[str, Any]
) -> None:
    old_by_id = {vector["vector_id"]: vector for vector in legacy["vectors"]}
    new_legacy = [vector for vector in corpus["vectors"] if vector["legacy_vector_id"]]
    assert len(old_by_id) == len(new_legacy) == crosswalk["entry_count"] == 30
    for new in new_legacy:
        old = old_by_id[new["legacy_vector_id"]]
        for key in (
            "vector_id",
            "title",
            "threat_tags",
            "expected_admission_state",
            "reason_code",
            "falsifier",
            "claim_ceiling",
        ):
            assert new[key] == old[key]
    entries = {item["v0_1_vector_id"]: item for item in crosswalk["entries"]}
    assert set(entries) == set(old_by_id)
    for vector_id, old in old_by_id.items():
        assert entries[vector_id]["preserved"] == {
            key: old[key]
            for key in (
                "title",
                "threat_tags",
                "expected_admission_state",
                "reason_code",
                "falsifier",
                "claim_ceiling",
            )
        }


def test_no_authority_or_warrant_is_created_for_empty_legacy_evidence(
    legacy: dict[str, Any], corpus: dict[str, Any], crosswalk: dict[str, Any]
) -> None:
    new_by_id = {
        vector["legacy_vector_id"]: vector
        for vector in corpus["vectors"]
        if vector["legacy_vector_id"]
    }
    entries = {item["v0_1_vector_id"]: item for item in crosswalk["entries"]}
    for old in legacy["vectors"]:
        new = new_by_id[old["vector_id"]]
        _assert_no_default_authority(old, new)
        if not old["authority_evidence"]:
            assert entries[old["vector_id"]]["no_default_warrant"] is True
            assert entries[old["vector_id"]]["authority_bearing_additions"] == [
                "source_registration.adopted_at/published_at/effective_from/"
                "effective_until/superseded_at/revoked_at when absent in v0.1"
            ]


def test_compact_evidence_facts_are_preserved_and_additions_are_visible(
    legacy: dict[str, Any], corpus: dict[str, Any], crosswalk: dict[str, Any]
) -> None:
    new_by_id = {
        vector["legacy_vector_id"]: vector
        for vector in corpus["vectors"]
        if vector["legacy_vector_id"]
    }
    entries = {item["v0_1_vector_id"]: item for item in crosswalk["entries"]}
    for old_vector in legacy["vectors"]:
        new_evidence = new_by_id[old_vector["vector_id"]]["executable_input"]["authority_evidence"]
        assert len(new_evidence) == len(old_vector["authority_evidence"])
        old_by_id = {item["evidence_id"]: item for item in old_vector["authority_evidence"]}
        new_by_evidence_id = {item["evidence_id"]: item for item in new_evidence}
        assert set(new_by_evidence_id) == set(old_by_id)
        for evidence_id, old in old_by_id.items():
            new = new_by_evidence_id[evidence_id]
            assert new["evidence_id"] == old["evidence_id"]
            assert new["authority_basis_ref"] == old["authority_basis_ref"]
            warrant = new["admission_warrant"]
            assert warrant["warrant_id"] == old["warrant_id"]
            assert warrant["source_version"] == old["warrant_source_version"]
            assert warrant["source_digest"] == old["warrant_source_digest"]
            assert warrant["applicability_scope"] == old["warrant_scope"]
            assert warrant["effective_from"] == old["effective_from"]
            assert warrant["effective_until"] == old["effective_until"]
            assert warrant["revoked_at"] == old["revoked_at"]
            assert warrant["status"] == old["status"]
        entry = entries[old_vector["vector_id"]]
        assert entry["overall_transformation"] == ("addition_of_previously_unspecified_design_data")
        assert entry["authority_bearing_additions"]
    assert all(item["justification"] for item in crosswalk["field_class_justifications"])


def test_model_fields_cannot_create_admission_evidence(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    authority_schema = _load(repo_root, "AUTHORITY-EVIDENCE-v0.1.schema.json")
    authority_fields = set(authority_schema["properties"])
    assert authority_fields.isdisjoint({"unit_type", "model_confidence", "candidate_span"})
    positive = next(vector for vector in corpus["vectors"] if vector["vector_id"] == "ADM-001")
    mutated = copy.deepcopy(positive)
    before = _canonical(mutated["executable_input"]["authority_evidence"])
    mutated["executable_input"]["candidate"]["unit_type"] = "advisory"
    assert _canonical(mutated["executable_input"]["authority_evidence"]) == before


def test_time_is_explicit_normalized_and_has_no_schema_default(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    schema = _load(repo_root, "ADMISSION-INPUT-v0.1.schema.json")
    assert "evaluation_time" in schema["required"]
    assert '"default"' not in json.dumps(schema)
    for vector in corpus["vectors"]:
        for path, timestamp in _timestamps(vector["executable_input"]):
            assert timestamp.endswith("Z"), (vector["vector_id"], path)
    design_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (repo_root / DESIGN).glob("*v0.1.md")
    )
    assert "datetime.now(" not in design_text
    assert "datetime.utcnow(" not in design_text


def test_canonicalization_and_evidence_order_are_deterministic(corpus: dict[str, Any]) -> None:
    vector = next(item for item in corpus["vectors"] if item["vector_id"] == "ADM-017")
    input_value = vector["executable_input"]
    assert _canonical(input_value) == _canonical(json.loads(_canonical(input_value)))
    evidence = input_value["authority_evidence"]
    assert [(item["evidence_id"], item["evidence_digest"]) for item in evidence] == sorted(
        (item["evidence_id"], item["evidence_digest"]) for item in evidence
    )
    assert len({item["evidence_id"] for item in evidence}) == len(evidence)
    reversed_evidence = list(reversed(evidence))
    normalized = sorted(
        reversed_evidence, key=lambda item: (item["evidence_id"], item["evidence_digest"])
    )
    assert normalized == evidence


def test_exact_input_byte_seam_is_explicit_and_canonical(repo_root: Path) -> None:
    contract = (repo_root / DESIGN / "EXECUTABLE-INPUT-CONTRACT-v0.1.md").read_text(
        encoding="utf-8"
    )
    for requirement in (
        "UTF-8 bytes",
        "no duplicate object keys",
        "byte-identical to the canonical JSON serialization",
        "object keys sorted lexicographically",
        "no insignificant whitespace",
        "exact JSON types preserved",
        "timestamps already normalized as RFC 3339 UTC with `Z`",
        "Canonicalization never reads a clock",
    ):
        assert requirement in contract


def test_state_mapping_is_complete_machine_readable_and_frozen(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    mapping = _load(repo_root, "STATE-INPUT-MAPPING-v0.1.json")
    entries = mapping["entries"]
    assert [entry["precedence"] for entry in entries] == list(range(1, 16))
    assert {entry["state"] for entry in entries} == set(STATE_TO_REASON)
    assert all(STATE_TO_REASON[entry["state"]] == entry["reason_code"] for entry in entries)
    assert all(entry["observable_fields"] for entry in entries)
    assert all(entry["required_observable_facts"] for entry in entries)
    assert _sha(mapping) == RULESET_DIGEST
    assert mapping["first_terminal_state_wins"] is True
    assert mapping["runtime_permission_states"] == []
    assert mapping["successor_ir_state"] == "ADMITTED"
    observed = {vector["expected_admission_state"] for vector in corpus["vectors"]}
    assert observed == set(STATE_TO_REASON)
    assert all(
        vector["reason_code"] == STATE_TO_REASON[vector["expected_admission_state"]]
        for vector in corpus["vectors"]
    )


def test_precedence_diagnostics_cover_simultaneous_failures(corpus: dict[str, Any]) -> None:
    diagnostics = [
        vector for vector in corpus["vectors"] if vector["origin"] == "v0.2_precedence_diagnostic"
    ]
    assert len(diagnostics) == 8
    assert all(len(vector["threat_tags"]) == 3 for vector in diagnostics)
    assert {vector["vector_id"] for vector in diagnostics} == {
        f"ADM-PD-{index:03d}" for index in range(1, 9)
    }
    by_id = {vector["vector_id"]: vector for vector in diagnostics}
    assert (
        by_id["ADM-PD-001"]["executable_input"]["source_registration"]["registry_observation"][
            "availability"
        ]
        == "UNAVAILABLE"
    )
    assert by_id["ADM-PD-001"]["executable_input"]["source_registration"]["registered"] is False
    assert (
        by_id["ADM-PD-002"]["executable_input"]["source_registration"]["registry_observation"][
            "freshness"
        ]
        == "STALE"
    )
    assert by_id["ADM-PD-002"]["executable_input"]["source_registration"]["registered"] is False
    version_input = by_id["ADM-PD-003"]["executable_input"]
    assert version_input["source_registration"]["registered"] is False
    assert (
        version_input["source_registration"]["source_version"]
        != version_input["authority_evidence"][0]["source_version"]
    )
    digest_input = by_id["ADM-PD-004"]["executable_input"]
    assert (
        digest_input["source_registration"]["source_version"]
        != digest_input["authority_evidence"][0]["source_version"]
    )
    assert (
        digest_input["candidate"]["source_anchors"][0]["content_hash"]
        != digest_input["source_registration"]["source_digest"]
    )
    missing_input = by_id["ADM-PD-005"]["executable_input"]
    assert (
        missing_input["candidate"]["source_anchors"][0]["content_hash"]
        != missing_input["source_registration"]["source_digest"]
    )
    assert missing_input["authority_evidence"] == []
    scope_input = by_id["ADM-PD-006"]["executable_input"]
    assert scope_input["authority_evidence"] == []
    assert (
        scope_input["evaluation_scope"]["applicability"]
        not in scope_input["source_registration"]["applicability_scope"]
    )
    revoked_input = by_id["ADM-PD-007"]["executable_input"]
    assert (
        revoked_input["evaluation_scope"]["applicability"]
        not in revoked_input["source_registration"]["applicability_scope"]
    )
    assert revoked_input["authority_evidence"][0]["admission_warrant"]["status"] == "REVOKED"
    lifecycle_input = by_id["ADM-PD-008"]["executable_input"]["source_registration"]
    assert lifecycle_input["superseded_at"] is not None
    assert lifecycle_input["revoked_at"] is not None


def test_precedence_diagnostic_expected_state_is_the_earliest_declared_failure(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    mapping = _load(repo_root, "STATE-INPUT-MAPPING-v0.1.json")
    precedence = {entry["state"]: entry["precedence"] for entry in mapping["entries"]}
    diagnostic_states = {
        "ADM-PD-001": ("AUTHORITY_REGISTRY_UNAVAILABLE", "SOURCE_NOT_REGISTERED"),
        "ADM-PD-002": ("AUTHORITY_EVIDENCE_STALE", "SOURCE_NOT_REGISTERED"),
        "ADM-PD-003": ("SOURCE_NOT_REGISTERED", "SOURCE_VERSION_MISMATCH"),
        "ADM-PD-004": ("SOURCE_VERSION_MISMATCH", "SOURCE_DIGEST_MISMATCH"),
        "ADM-PD-005": ("SOURCE_DIGEST_MISMATCH", "MISSING_AUTHORITY_EVIDENCE"),
        "ADM-PD-006": ("MISSING_AUTHORITY_EVIDENCE", "OUT_OF_SCOPE"),
        "ADM-PD-007": ("OUT_OF_SCOPE", "REVOKED"),
        "ADM-PD-008": ("SUPERSEDED", "REVOKED"),
    }
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id, states in diagnostic_states.items():
        earliest = min(states, key=precedence.__getitem__)
        assert by_id[vector_id]["expected_admission_state"] == earliest


def test_allow_deny_are_absent_and_only_admitted_crosses_ir_seam(repo_root: Path) -> None:
    mapping = _load(repo_root, "STATE-INPUT-MAPPING-v0.1.json")
    states = {entry["state"] for entry in mapping["entries"]}
    assert states.isdisjoint({"ALLOW", "DENY"})
    assert mapping["successor_ir_state"] == "ADMITTED"
    contract = (repo_root / DESIGN / "EXECUTABLE-INPUT-CONTRACT-v0.1.md").read_text()
    assert "NO ADMISSION RUNTIME WAS IMPLEMENTED" in contract
    assert "NO INSTITUTIONAL IR WAS IMPLEMENTED" in contract


def test_mutation_missing_required_authority_field_is_rejected(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    _input_validator, authority_validator, _receipt_validator = _schema_validators(repo_root)
    vector = next(item for item in corpus["vectors"] if item["vector_id"] == "ADM-001")
    evidence = copy.deepcopy(vector["executable_input"]["authority_evidence"][0])
    del evidence["issuer_id"]
    assert list(authority_validator.iter_errors(evidence))


def test_mutation_self_referential_evidence_digest_is_rejected(corpus: dict[str, Any]) -> None:
    vector = next(item for item in corpus["vectors"] if item["vector_id"] == "ADM-001")
    evidence = copy.deepcopy(vector["executable_input"]["authority_evidence"][0])
    evidence["evidence_digest"] = _sha(evidence)
    assert evidence["evidence_digest"] != _evidence_digest(evidence)


def _assert_mutated_positive_warrant_binding_is_detected(
    corpus: dict[str, Any], field: str, replacement: str
) -> None:
    vector = copy.deepcopy(
        next(item for item in corpus["vectors"] if item["vector_id"] == "ADM-001")
    )
    vector["executable_input"]["authority_evidence"][0]["admission_warrant"][field] = replacement
    with pytest.raises(AssertionError):
        _assert_positive_fixture_consistency(vector)


def test_mutation_wrong_positive_warrant_version_is_detected(corpus: dict[str, Any]) -> None:
    _assert_mutated_positive_warrant_binding_is_detected(corpus, "source_version", "wrong-version")


def test_mutation_wrong_positive_warrant_digest_is_detected(corpus: dict[str, Any]) -> None:
    _assert_mutated_positive_warrant_binding_is_detected(
        corpus, "source_digest", "sha256:" + "f" * 64
    )


def test_mutation_hidden_current_time_is_rejected(repo_root: Path, corpus: dict[str, Any]) -> None:
    input_validator, _authority_validator, _receipt_validator = _schema_validators(repo_root)
    vector = next(item for item in corpus["vectors"] if item["vector_id"] == "ADM-001")
    input_value = copy.deepcopy(vector["executable_input"])
    del input_value["evaluation_time"]
    assert list(input_validator.iter_errors(input_value))


def test_mutation_state_precedence_reordering_breaks_ruleset_binding(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    mapping = _load(repo_root, "STATE-INPUT-MAPPING-v0.1.json")
    mutated = copy.deepcopy(mapping)
    mutated["entries"][0], mutated["entries"][1] = mutated["entries"][1], mutated["entries"][0]
    assert _sha(mutated) != RULESET_DIGEST
    assert all(
        vector["executable_input"]["ruleset"]["ruleset_digest"] == RULESET_DIGEST
        for vector in corpus["vectors"]
    )


def test_mutation_silent_warrant_for_empty_legacy_evidence_is_detected(
    legacy: dict[str, Any], corpus: dict[str, Any]
) -> None:
    old = next(vector for vector in legacy["vectors"] if vector["vector_id"] == "ADM-003")
    new = copy.deepcopy(
        next(vector for vector in corpus["vectors"] if vector["vector_id"] == "ADM-003")
    )
    donor = next(vector for vector in corpus["vectors"] if vector["vector_id"] == "ADM-001")
    new["executable_input"]["authority_evidence"] = copy.deepcopy(
        donor["executable_input"]["authority_evidence"]
    )
    with pytest.raises(AssertionError):
        _assert_no_default_authority(old, new)


def test_no_receipt_only_or_model_confidence_fields_are_in_input_schema(repo_root: Path) -> None:
    schema = _load(repo_root, "ADMISSION-INPUT-v0.1.schema.json")
    properties = set(schema["properties"])
    assert properties == {
        "candidate",
        "source_registration",
        "authority_evidence",
        "evaluation_time",
        "evaluation_scope",
        "evaluator",
        "ruleset",
    }
    serialized = json.dumps(schema)
    for forbidden in (
        "model_confidence",
        "input_digest",
        "admission_receipt_id",
        "admission_state",
        "reason_code",
        "Institutional IR",
    ):
        assert forbidden not in serialized


def test_production_candidate_and_historical_freeze_remain_unchanged(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{STARTING_SHA}...HEAD", "--", "src", "schemas"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""
    protected = (
        "src/oic/candidate_extraction.py",
        "src/oic/nvidia_nim.py",
        "schemas/draft/candidate-normative-unit.schema.json",
        "benchmarks/characterization/candidate-layer-freeze-001/FREEZE.json",
        "benchmarks/characterization/candidate-layer-freeze-001/FREEZE.md",
    )
    for path in protected:
        current = (repo_root / path).read_bytes()
        original = subprocess.run(
            ["git", "show", f"{STARTING_SHA}:{path}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        assert current == original, path


def test_changes_remain_design_and_contract_tests_only(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{STARTING_SHA}...HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert all(
        path.startswith(f"{DESIGN}/")
        or path
        in {
            "tests/contract/test_admission_boundary_001_design.py",
            "tests/contract/test_admission_design_consistency_001.py",
        }
        for path in changed
    )


def test_claim_ceiling_and_role_separation_are_preserved(corpus: dict[str, Any]) -> None:
    for claim in (
        "legal validity",
        "universal authority semantics",
        "production readiness",
        "runtime safety",
        "compliance",
        "successful IR compilation",
        "execution authorization",
        "independent validation",
    ):
        assert claim in corpus["claim_ceiling"]
    assert corpus["independent_validation_claim"] is False
    assert corpus["self_adjudication"] == "NOT SELF-ADJUDICATED"
