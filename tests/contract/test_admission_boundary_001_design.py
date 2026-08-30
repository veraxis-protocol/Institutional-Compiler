"""Design-contract tests for Admission Boundary 001 preregistration."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema.validators import Draft202012Validator

pytestmark = pytest.mark.contract

DESIGN_DIR = Path("design/admission-boundary-001")
STARTING_FREEZE = "6968dfc04f2108e910e1983b15262e2b26bf7fc9"
CORPUS_SHA256 = "2181cada7cda18a0bde77db89a7eaf701ad044253c3e179024ac7f51d50bc8e7"
CORPUS_BYTES = 48822
FREEZE_SHA256 = "566b5ad56a4c24c51b4547de0aed394bf31f59f7248a1c99596e85e116deef12"
EXPECTED_FILES = {
    "README.md",
    "ADMISSION-CONTRACT-v0.1.md",
    "ADMISSION-STATE-MACHINE-v0.1.md",
    "ADMISSION-RECEIPT-v0.1.schema.json",
    "AUTHORITY-EVIDENCE-v0.1.schema.json",
    "THREAT-MODEL-v0.1.md",
    "TEST-VECTORS-v0.1.json",
    "TEST-VECTORS-FREEZE-v0.1.json",
    "PREREGISTRATION-v0.1.md",
}
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
REQUIRED_THREATS = {
    "authoritative_looking_fake_memo",
    "perfect_grounding_from_draft",
    "valid_policy_forged_source_metadata",
    "valid_authority_wrong_version",
    "expired_source",
    "superseded_source",
    "revoked_source",
    "wrong_department_or_jurisdiction",
    "copied_policy_unauthoritative_website",
    "legitimate_policy_quoted_in_commentary",
    "model_labels_descriptive_as_mandate",
    "model_labels_valid_mandate_as_advisory",
    "source_digest_mismatch",
    "authority_registry_unavailable",
    "conflicting_warrants",
    "stale_cached_authority_evidence",
}


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / DESIGN_DIR / "TEST-VECTORS-v0.1.json").read_text()),
    )


@pytest.fixture(scope="module")
def vector_freeze(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / DESIGN_DIR / "TEST-VECTORS-FREEZE-v0.1.json").read_text()),
    )


def _read(repo_root: Path, name: str) -> str:
    return (repo_root / DESIGN_DIR / name).read_text(encoding="utf-8")


def _json(repo_root: Path, name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(_read(repo_root, name)))


def test_design_package_has_exact_required_artifacts(repo_root: Path) -> None:
    assert {path.name for path in (repo_root / DESIGN_DIR).iterdir()} == EXPECTED_FILES


def test_vector_corpus_and_freeze_are_byte_pinned(
    repo_root: Path, vector_freeze: dict[str, Any]
) -> None:
    corpus_body = (repo_root / DESIGN_DIR / "TEST-VECTORS-v0.1.json").read_bytes()
    freeze_body = (repo_root / DESIGN_DIR / "TEST-VECTORS-FREEZE-v0.1.json").read_bytes()
    assert len(corpus_body) == CORPUS_BYTES == vector_freeze["corpus_bytes"]
    assert hashlib.sha256(corpus_body).hexdigest() == CORPUS_SHA256
    assert vector_freeze["corpus_sha256"] == CORPUS_SHA256
    assert hashlib.sha256(freeze_body).hexdigest() == FREEZE_SHA256
    assert vector_freeze["freeze_state"] == "FROZEN BEFORE ADMISSION IMPLEMENTATION"
    assert vector_freeze["starting_candidate_freeze_sha"] == STARTING_FREEZE
    assert vector_freeze["runtime_execution"] is False
    assert vector_freeze["independent_validation_claim"] is False
    assert vector_freeze["self_adjudication"] == "NOT SELF-ADJUDICATED"


def test_draft_schemas_are_valid_and_freeze_exact_vocabulary(repo_root: Path) -> None:
    receipt = _json(repo_root, "ADMISSION-RECEIPT-v0.1.schema.json")
    authority = _json(repo_root, "AUTHORITY-EVIDENCE-v0.1.schema.json")
    Draft202012Validator.check_schema(receipt)
    Draft202012Validator.check_schema(authority)
    assert receipt["additionalProperties"] is False
    assert authority["additionalProperties"] is False
    assert set(receipt["properties"]["admission_state"]["enum"]) == set(STATE_TO_REASON)
    assert set(receipt["properties"]["reason_code"]["enum"]) == set(STATE_TO_REASON.values())
    assert "ALLOW" not in receipt["properties"]["admission_state"]["enum"]
    assert "DENY" not in receipt["properties"]["admission_state"]["enum"]


def test_authority_evidence_minimum_binds_source_scope_time_and_warrant(
    repo_root: Path,
) -> None:
    schema = _json(repo_root, "AUTHORITY-EVIDENCE-v0.1.schema.json")
    required = set(schema["required"])
    assert {
        "evidence_id",
        "evidence_digest",
        "source_id",
        "source_version",
        "source_digest",
        "issuer_id",
        "authority_basis_ref",
        "jurisdiction",
        "applicability_scope",
        "source_standing",
        "adopted_at",
        "effective_from",
        "effective_until",
        "superseded_at",
        "revoked_at",
        "admission_warrant",
    } <= required
    warrant_required = set(schema["properties"]["admission_warrant"]["required"])
    assert {
        "admission_authority_id",
        "delegation_basis_ref",
        "source_id",
        "source_version",
        "source_digest",
        "jurisdiction",
        "applicability_scope",
        "effective_from",
        "effective_until",
        "revoked_at",
        "status",
    } <= warrant_required


def test_receipt_is_sufficient_for_reconstruction_and_content_identity(repo_root: Path) -> None:
    schema = _json(repo_root, "ADMISSION-RECEIPT-v0.1.schema.json")
    assert {
        "admission_receipt_id",
        "candidate_unit_id",
        "candidate_projection_digest",
        "source_id",
        "source_version",
        "source_digest",
        "authority_evidence_refs",
        "authority_evidence_digests",
        "evaluation_time",
        "evaluation_scope",
        "admission_state",
        "reason_code",
        "evaluator_id",
        "evaluator_version",
        "ruleset_id",
        "ruleset_digest",
        "input_digest",
        "evidence_digest",
    } == set(schema["required"])
    assert schema["properties"]["admission_receipt_id"]["pattern"].startswith("^admrec-sha256:")


def test_vectors_are_complete_unique_and_match_frozen_state_reason_map(
    corpus: dict[str, Any], vector_freeze: dict[str, Any]
) -> None:
    vectors = cast("list[dict[str, Any]]", corpus["vectors"])
    assert len(vectors) == corpus["vector_count"] == vector_freeze["vector_count"] == 30
    assert len({vector["vector_id"] for vector in vectors}) == 30
    required = {
        "vector_id",
        "title",
        "threat_tags",
        "candidate_input",
        "source_metadata",
        "authority_evidence",
        "evaluation_time",
        "evaluation_scope",
        "expected_admission_state",
        "reason_code",
        "falsifier",
        "claim_ceiling",
    }
    for vector in vectors:
        assert required == set(vector), vector["vector_id"]
        state = cast("str", vector["expected_admission_state"])
        assert vector["reason_code"] == STATE_TO_REASON[state]
        assert vector["falsifier"]
        assert vector["claim_ceiling"]
        assert vector["evaluation_time"].endswith("Z")
    assert set(vector_freeze["frozen_state_vocabulary"]) == set(STATE_TO_REASON)
    assert set(vector_freeze["frozen_reason_codes"]) == set(STATE_TO_REASON.values())


def test_all_required_adversarial_cases_are_preregistered(corpus: dict[str, Any]) -> None:
    observed = {
        tag for vector in corpus["vectors"] for tag in cast("list[str]", vector["threat_tags"])
    }
    assert observed >= REQUIRED_THREATS
    states = [vector["expected_admission_state"] for vector in corpus["vectors"]]
    assert states.count("ADMITTED") >= 2
    assert len(states) - states.count("ADMITTED") >= 16


def test_candidate_type_and_provenance_do_not_confer_authority(
    corpus: dict[str, Any],
) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    assert by_id["ADM-013"]["expected_admission_state"] == "ADMITTED"
    assert by_id["ADM-014"]["expected_admission_state"] == "ADMITTED"
    assert "not approved" in by_id["ADM-013"]["claim_ceiling"]
    assert by_id["ADM-020"]["expected_admission_state"] == ("MISSING_AUTHORITY_EVIDENCE")
    assert by_id["ADM-020"]["source_metadata"]["provenance_complete"] is True


def test_idempotence_pair_has_identical_evaluation_inputs(corpus: dict[str, Any]) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    keys = (
        "candidate_input",
        "source_metadata",
        "authority_evidence",
        "evaluation_time",
        "evaluation_scope",
        "expected_admission_state",
        "reason_code",
    )
    assert {key: by_id["ADM-026"][key] for key in keys} == {
        key: by_id["ADM-027"][key] for key in keys
    }


def test_contract_separates_grounding_authority_interpretation_and_runtime(
    repo_root: Path,
) -> None:
    readme = _read(repo_root, "README.md")
    contract = _read(repo_root, "ADMISSION-CONTRACT-v0.1.md")
    assert "Source grounding" in readme
    assert "Source/authority admissibility" in readme
    assert "Semantic interpretation" in readme
    assert "Only `ADMITTED` may cross into Institutional IR construction" in contract
    assert "does not create authority" in readme
    assert "can never issue evidence" in readme
    assert "NO ADMISSION RUNTIME WAS IMPLEMENTED" in readme
    assert "NO INSTITUTIONAL IR WAS IMPLEMENTED" in readme


def test_authority_conservation_and_provenance_distinction_are_explicit(
    repo_root: Path,
) -> None:
    contract = _read(repo_root, "ADMISSION-CONTRACT-v0.1.md")
    normalized = " ".join(contract.split())
    assert "cannot acquire greater institutional standing" in normalized
    for forbidden_basis in (
        "model output",
        "candidate type",
        "semantic similarity",
        "repeated extraction",
        "source popularity",
        "provenance alone",
    ):
        assert forbidden_basis in normalized
    assert "provenance answers where this came" in normalized
    assert "authority answers why the institution is entitled" in normalized


def test_time_and_receipt_determinism_have_no_hidden_clock(repo_root: Path) -> None:
    contract = _read(repo_root, "ADMISSION-CONTRACT-v0.1.md")
    machine = _read(repo_root, "ADMISSION-STATE-MACHINE-v0.1.md")
    assert "No hidden wall clock" in contract
    assert "Identical canonical inputs" in contract
    assert "evaluation_time" in contract
    assert "No evaluator wall clock is consulted" in machine
    assert "publication alone" in machine
    assert "never mutated" in contract


def test_preregistration_answers_all_falsification_questions(repo_root: Path) -> None:
    preregistration = _read(repo_root, "PREREGISTRATION-v0.1.md")
    assert preregistration.count("Falsified if") == 8
    assert "independent_validation_claim = FALSE" in preregistration
    assert "NOT SELF-ADJUDICATED" in preregistration


def test_phase_b_does_not_change_candidate_or_production_trees(repo_root: Path) -> None:
    changed_production = subprocess.run(
        ["git", "diff", "--name-only", f"{STARTING_FREEZE}...HEAD", "--", "src", "schemas"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed_production == ""
    candidate_at_freeze = subprocess.run(
        ["git", "show", f"{STARTING_FREEZE}:src/oic/candidate_extraction.py"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout
    assert (repo_root / "src/oic/candidate_extraction.py").read_bytes() == candidate_at_freeze
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{STARTING_FREEZE}...HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert all(
        path.startswith(f"{DESIGN_DIR}/")
        or path == "tests/contract/test_admission_boundary_001_design.py"
        for path in changed
    )


def test_claim_ceiling_and_role_separation_are_frozen(corpus: dict[str, Any]) -> None:
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
