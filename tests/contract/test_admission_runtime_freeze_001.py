"""Contract tests for Admission Runtime Freeze 001.

The freeze is a receipt about a past state, so almost everything here is verified against
the recorded SHAs rather than against ``HEAD``. The one thing checked against the working
tree is what the freeze actually froze: the Admission Runtime 001 artifacts, by name. The
freeze deliberately does not assert that unrelated future modules under ``src/`` may never
change, and a test asserting that would put the claim back.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from oic.admission import (
    ADMISSION_INPUT_SCHEMA_NAME,
    ADMISSION_RECEIPT_SCHEMA_NAME,
    AUTHORITY_EVIDENCE_SCHEMA_NAME,
    CANONICALIZATION_ID,
    EVALUATOR_ID,
    EVALUATOR_VERSION,
    RULESET_DIGEST,
    RULESET_ID,
    STATE_INPUT_MAPPING_NAME,
    AdmissionCanonicalFormError,
    AdmissionEncodingError,
    AdmissionError,
    AdmissionEvaluationError,
    AdmissionEvidenceIntegrityError,
    AdmissionEvidenceOrderError,
    AdmissionInputBoundaryError,
    AdmissionJSONError,
    AdmissionRulesetError,
    AdmissionSchemaError,
    AdmissionSpecificationError,
    AdmissionState,
    AdmissionTimestampError,
    evaluate_admission_bytes,
)

pytestmark = pytest.mark.contract

FREEZE_DIR = "benchmarks/characterization/admission-runtime-freeze-001"
FREEZE_JSON = f"{FREEZE_DIR}/FREEZE.json"
FREEZE_MD = f"{FREEZE_DIR}/FREEZE.md"

EVALUATOR_IMPLEMENTATION = "ddc8c7ddee72cd0b3fc2ffe5c878ab7e550630ca"
FROZEN_FINAL_STATE = "ae6021496e5f87e5aaf7a6a52514dc86538987e9"
DESIGN_STARTING_STATE = "9fa2c684841ea89632bfe0129f98177761d85d12"

FROZEN_ARTIFACTS = (
    "src/oic/admission.py",
    "src/oic/admission_specs/__init__.py",
    f"src/oic/admission_specs/{ADMISSION_INPUT_SCHEMA_NAME}",
    f"src/oic/admission_specs/{ADMISSION_RECEIPT_SCHEMA_NAME}",
    f"src/oic/admission_specs/{AUTHORITY_EVIDENCE_SCHEMA_NAME}",
    f"src/oic/admission_specs/{STATE_INPUT_MAPPING_NAME}",
)


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / FREEZE_JSON).read_text(encoding="utf-8"))
    return document


def _blob(repo_root: Path, ref: str, relpath: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{ref}:{relpath}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout


# ---------------------------------------------------------------------------
# The freeze record itself
# ---------------------------------------------------------------------------


def test_the_freeze_declares_its_authorization_and_state(freeze: dict[str, Any]) -> None:
    assert freeze["freeze_id"] == "OIC-ADMISSION-RUNTIME-FREEZE-001"
    assert (
        freeze["authorization"]
        == "OWNER-AUTHORIZED BOUNDED ADMISSION RUNTIME FREEZE — PRE-INSTITUTIONAL-IR"
    )
    assert freeze["freeze_state"] == "FROZEN FOR INSTITUTIONAL-IR SUCCESSOR WORK"
    assert freeze["frozen_final_state_sha"] == FROZEN_FINAL_STATE
    assert freeze["independent_validation_claim"] is False
    assert freeze["self_adjudication"] == "NOT SELF-ADJUDICATED"


def test_the_recorded_chronology_is_the_real_one(repo_root: Path, freeze: dict[str, Any]) -> None:
    """Each recorded commit must exist, in the recorded order, in this branch's ancestry.

    The evaluator landed first and the scope-binding test repair followed it. Recording
    that backwards would misattribute the implementation to the wrong commit.
    """
    recorded = [entry["sha"] for entry in freeze["chronology"]]
    assert recorded == [DESIGN_STARTING_STATE, EVALUATOR_IMPLEMENTATION, FROZEN_FINAL_STATE]
    for sha in recorded:
        assert (
            subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                cwd=repo_root,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        ), sha
    for ancestor, descendant in itertools.pairwise(recorded):
        assert (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=repo_root,
                check=False,
                capture_output=True,
            ).returncode
            == 0
        ), f"{ancestor} does not precede {descendant}"
    assert (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", FROZEN_FINAL_STATE, "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def test_the_evaluator_was_introduced_by_the_commit_the_freeze_names(repo_root: Path) -> None:
    """The implementation SHA is checked, not asserted: the module must be absent at the
    commit before it and present at the commit that names it."""
    absent = subprocess.run(
        ["git", "cat-file", "-e", f"{DESIGN_STARTING_STATE}:src/oic/admission.py"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    assert absent.returncode != 0, "the evaluator already existed at the design starting state"
    present = subprocess.run(
        ["git", "cat-file", "-e", f"{EVALUATOR_IMPLEMENTATION}:src/oic/admission.py"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    assert present.returncode == 0, "the named implementation commit does not carry the evaluator"


# ---------------------------------------------------------------------------
# The frozen artifacts, against the working tree
# ---------------------------------------------------------------------------


def _recorded_digest(repo_root: Path, relpath: str) -> str:
    """Read one recorded digest without pulling ``Any`` into a parametrized signature."""
    document = json.loads((repo_root / FREEZE_JSON).read_text(encoding="utf-8"))
    digest: str = document["frozen_production_artifacts"][relpath]["sha256"]
    return digest


@pytest.mark.parametrize("relpath", FROZEN_ARTIFACTS)
def test_every_frozen_artifact_still_holds_its_recorded_bytes(
    repo_root: Path, relpath: str
) -> None:
    recorded = _recorded_digest(repo_root, relpath)
    current = hashlib.sha256((repo_root / relpath).read_bytes()).hexdigest()
    assert current == recorded, relpath
    assert current == hashlib.sha256(_blob(repo_root, FROZEN_FINAL_STATE, relpath)).hexdigest()


def test_the_freeze_names_every_frozen_artifact_and_no_others(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    recorded = set(freeze["frozen_production_artifacts"])
    on_disk = {
        path.relative_to(repo_root).as_posix()
        for path in (repo_root / "src/oic/admission_specs").iterdir()
        if path.is_file() and path.suffix in {".json", ".py"}
    } | {"src/oic/admission.py"}
    assert recorded == on_disk


def test_the_packaged_specifications_are_byte_identical_to_the_design_originals(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    for design_path, digest in freeze["packaged_specifications_are_byte_identical_to"].items():
        name = Path(design_path).name
        packaged = repo_root / "src/oic/admission_specs" / name
        original = repo_root / design_path
        assert packaged.read_bytes() == original.read_bytes(), name
        assert hashlib.sha256(original.read_bytes()).hexdigest() == digest, name


def test_the_package_data_declaration_ships_the_frozen_resources(repo_root: Path) -> None:
    """Without this line the wheel would import but the evaluator could not load its rules."""
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"oic.admission_specs" = ["*.json"]' in pyproject


def test_the_freeze_scope_is_the_admission_artifacts_and_not_all_of_src(
    freeze: dict[str, Any],
) -> None:
    """The freeze must not re-create a HEAD-wide claim over unrelated future modules."""
    statement = freeze["freeze_scope_statement"]
    assert "not an assertion that unrelated future OIC modules" in statement
    assert "production_tree_objects" not in freeze
    assert set(freeze["frozen_production_tree_objects"]) == {"src/oic/admission_specs"}


# ---------------------------------------------------------------------------
# The frozen interface, identity and vocabulary
# ---------------------------------------------------------------------------


def test_the_frozen_public_api_is_the_byte_seam(freeze: dict[str, Any]) -> None:
    interface = freeze["frozen_interface"]
    assert (
        interface["public_api"]
        == "evaluate_admission_bytes(input_bytes: bytes) -> AdmissionReceipt"
    )
    assert interface["input_is_bytes_not_object"] is True
    assert interface["no_object_entry_point_is_exported"] is True
    import oic.admission as admission

    exported = set(admission.__all__)
    assert "evaluate_admission_bytes" in exported
    assert not {name for name in exported if name.startswith("evaluate_")} - {
        "evaluate_admission_bytes"
    }


def test_the_frozen_identity_matches_the_module(freeze: dict[str, Any]) -> None:
    identity = freeze["frozen_identity"]
    assert identity["evaluator_id"] == EVALUATOR_ID
    assert identity["evaluator_version"] == EVALUATOR_VERSION
    assert identity["ruleset_id"] == RULESET_ID
    assert identity["ruleset_canonical_digest"] == RULESET_DIGEST
    assert identity["canonicalization_id"] == CANONICALIZATION_ID


def test_the_freeze_records_that_the_ruleset_digest_is_not_the_file_digest(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    """The two values are easy to confuse and only one is attested."""
    raw = hashlib.sha256(
        (repo_root / "design/admission-boundary-001" / STATE_INPUT_MAPPING_NAME).read_bytes()
    ).hexdigest()
    definition = freeze["frozen_identity"]["ruleset_digest_definition"]
    assert raw in definition
    assert f"sha256:{raw}" != RULESET_DIGEST


def test_the_frozen_state_vocabulary_is_the_ruleset_vocabulary(freeze: dict[str, Any]) -> None:
    recorded = freeze["frozen_state_vocabulary"]
    assert [entry["precedence"] for entry in recorded] == list(range(1, 16))
    assert [entry["state"] for entry in recorded] == [state.value for state in AdmissionState]
    forbidden = {"ALLOW", "DENY", "PERMIT", "AUTHORIZED", "EXECUTE"}
    assert {entry["state"] for entry in recorded} & forbidden == set()


def test_the_frozen_exception_boundary_matches_the_module(freeze: dict[str, Any]) -> None:
    boundary = freeze["frozen_exception_boundary"]
    subclasses = {
        "AdmissionEncodingError": AdmissionEncodingError,
        "AdmissionJSONError": AdmissionJSONError,
        "AdmissionCanonicalFormError": AdmissionCanonicalFormError,
        "AdmissionSchemaError": AdmissionSchemaError,
        "AdmissionTimestampError": AdmissionTimestampError,
        "AdmissionEvidenceOrderError": AdmissionEvidenceOrderError,
        "AdmissionEvidenceIntegrityError": AdmissionEvidenceIntegrityError,
        "AdmissionRulesetError": AdmissionRulesetError,
    }
    assert set(boundary["input_boundary_subclasses"]) == set(subclasses)
    for error_type in subclasses.values():
        assert issubclass(error_type, AdmissionInputBoundaryError)
    assert issubclass(AdmissionInputBoundaryError, AdmissionError)
    assert not issubclass(AdmissionEvaluationError, AdmissionInputBoundaryError)
    assert not issubclass(AdmissionSpecificationError, AdmissionInputBoundaryError)


# ---------------------------------------------------------------------------
# The frozen behavior, re-established rather than restated
# ---------------------------------------------------------------------------


def test_the_recorded_corpus_is_the_corpus_on_disk(repo_root: Path, freeze: dict[str, Any]) -> None:
    corpus = freeze["governing_corpus"]
    raw = (repo_root / corpus["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == corpus["sha256"]
    assert len(raw) == corpus["bytes"]
    document = json.loads(raw.decode("utf-8"))
    assert len(document["vectors"]) == corpus["vector_count"] == 38
    assert (
        hashlib.sha256((repo_root / corpus["freeze_path"]).read_bytes()).hexdigest()
        == corpus["freeze_sha256"]
    )


def test_the_recorded_behavior_is_reproduced_now(repo_root: Path, freeze: dict[str, Any]) -> None:
    """The freeze's headline numbers are recomputed, not trusted."""
    from oic.admission import canonical_json

    behavior = freeze["frozen_behavior"]
    corpus = json.loads(
        (repo_root / freeze["governing_corpus"]["path"]).read_text(encoding="utf-8")
    )
    exact = 0
    observed: dict[str, int] = {}
    for vector in corpus["vectors"]:
        receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
        if receipt.to_json() == vector["expected_receipt"]:
            exact += 1
        observed[receipt.admission_state.value] = observed.get(receipt.admission_state.value, 0) + 1
    assert exact == behavior["exact_receipt_reproductions"] == 38
    assert observed == behavior["terminal_state_coverage"]
    assert len(observed) == behavior["terminal_states_exercised"] == len(AdmissionState)


def test_the_recorded_evidence_tests_still_hold_their_recorded_bytes(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    for relpath, digest in freeze["evidence_test_references"].items():
        current = hashlib.sha256((repo_root / relpath).read_bytes()).hexdigest()
        assert current == digest, relpath


def test_the_freeze_records_the_boundaries_it_claims(freeze: dict[str, Any]) -> None:
    behavior = freeze["frozen_behavior"]
    for field in (
        "no_wall_clock",
        "no_model",
        "no_network_schema_resolution",
        "no_runtime_configuration_can_reorder_states_or_change_the_ruleset",
        "installed_wheel_execution_without_design_tree",
        "first_terminal_state_wins",
        "deterministic_receipt_construction",
        "idempotent_over_repeated_identical_bytes",
        "mutation_control_case_present",
    ):
        assert behavior[field] is True, field
    assert behavior["dependency_added"] is False
    assert behavior["byte_boundary_rejection_cases"] >= 22
    assert (
        behavior["named_implementation_mutations_killed"]
        == behavior["named_implementation_mutations"]
        >= 17
    )
    assert behavior["precedence_diagnostics_passing"] == behavior["precedence_diagnostics_defined"]


# ---------------------------------------------------------------------------
# Historical preservation, the SBOM note, and the claim ceiling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relpath",
    (
        "design/admission-boundary-001/TEST-VECTORS-v0.1.json",
        "design/admission-boundary-001/TEST-VECTORS-FREEZE-v0.1.json",
        "design/admission-boundary-001/TEST-VECTORS-v0.2.json",
        "design/admission-boundary-001/TEST-VECTORS-FREEZE-v0.2.json",
        "design/admission-boundary-001/STATE-INPUT-MAPPING-v0.1.json",
        "design/admission-boundary-001/EXECUTABLE-INPUT-CONTRACT-v0.1.md",
        "schemas/draft/admission-record.schema.json",
        "schemas/draft/authority-record.schema.json",
        "schemas/draft/institutional-ir.schema.json",
        "src/oic/candidate_extraction.py",
        "benchmarks/characterization/candidate-layer-freeze-001/FREEZE.json",
    ),
)
def test_historical_artifacts_are_unchanged_by_this_freeze(repo_root: Path, relpath: str) -> None:
    assert (repo_root / relpath).read_bytes() == _blob(repo_root, FROZEN_FINAL_STATE, relpath)


def test_the_sbom_note_is_recorded_as_environmental_and_claims_nothing(
    freeze: dict[str, Any],
) -> None:
    note = freeze["sbom_environment_note"]
    assert note["classification"] == "ENVIRONMENTAL / NONBLOCKING / NO DEPENDENCY CHANGE"
    assert "cyclonedx-py" in note["observation"]
    assert note["sbom_generated"] is False
    assert note["dependency_change_made_to_close_it"] is False


def test_no_dependency_was_added_by_this_freeze(repo_root: Path) -> None:
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    declared = [
        line.strip()
        for line in pyproject.splitlines()
        if line.strip().startswith(('"jsonschema', '"referencing'))
    ]
    assert len(declared) == 2


def test_the_future_change_rule_requires_a_versioned_successor(freeze: dict[str, Any]) -> None:
    rule = freeze["future_change_rule"]
    assert "a demonstrated defect" in rule
    assert "explicit owner authorization" in rule
    assert "preservation of this freeze record" in rule
    assert "a versioned successor rather than silent mutation" in rule


def test_the_successor_boundary_admits_only_admitted_receipts(freeze: dict[str, Any]) -> None:
    boundary = freeze["successor_boundary"]
    assert "ADMITTED" in boundary
    assert "did not establish the interpretation" in boundary


def test_the_claim_ceiling_is_intact(repo_root: Path, freeze: dict[str, Any]) -> None:
    for claim in (
        "legal validity",
        "universal authority semantics",
        "issuer authentication",
        "semantic correctness",
        "institutional meaning",
        "Institutional IR",
        "execution authorization",
        "runtime safety",
        "compliance",
        "production readiness",
        "independent validation",
    ):
        assert claim in freeze["claim_ceiling"], claim
    markdown = (repo_root / FREEZE_MD).read_text(encoding="utf-8")
    assert "independent_validation_claim = FALSE" in markdown
    assert "NOT SELF-ADJUDICATED" in markdown
    assert "NO INSTITUTIONAL IR WAS IMPLEMENTED." in markdown


def test_no_institutional_ir_runtime_exists(repo_root: Path) -> None:
    assert not (repo_root / "src/oic/institutional_ir.py").exists()
    modules = {path.name for path in (repo_root / "src" / "oic").glob("*.py")}
    assert "institutional_ir.py" not in modules
