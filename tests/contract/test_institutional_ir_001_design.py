"""Design-contract tests for Institutional IR 001.

Nothing here executes an IR runtime, because there is none. What is tested is that the
frozen design artifacts say what they claim to say, that every vector's admission receipt
is real — re-derived through the frozen Admission Runtime 001 byte boundary rather than
trusted — and that the invariants the package freezes are actually observable in the
corpus rather than only asserted in prose.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from oic.admission import canonical_json, digest_of, evaluate_admission_bytes

pytestmark = pytest.mark.contract

DESIGN = Path("design/institutional-ir-001")
CORPUS_RELPATH = DESIGN / "TEST-VECTORS-v0.1.json"
FREEZE_RELPATH = DESIGN / "TEST-VECTORS-FREEZE-v0.1.json"
HISTORICAL_IR_SCHEMA = Path("schemas/draft/institutional-ir.schema.json")

EXPECTED_FILES = {
    "README.md",
    "IR-CONTRACT-v0.1.md",
    "SEMANTIC-INVARIANTS-v0.1.md",
    "AMBIGUITY-AND-UNKNOWN-v0.1.md",
    "IR-LINEAGE-v0.1.md",
    "THREAT-MODEL-v0.1.md",
    "PREREGISTRATION-v0.1.md",
    "INTERPRETATION-RULESET-v0.1.json",
    "INTERPRETATION-PROPOSAL-v0.1.schema.json",
    "INTERPRETATION-EVIDENCE-v0.1.schema.json",
    "INSTITUTIONAL-IR-v0.1.schema.json",
    "TEST-VECTORS-v0.1.json",
    "TEST-VECTORS-FREEZE-v0.1.json",
}

SLOTS = (
    "normative_force",
    "bearer",
    "action",
    "object",
    "counterparty",
    "condition",
    "exception",
    "temporal_qualifier",
    "quantum",
    "definiendum",
    "definiens",
)
STATUSES = {"ESTABLISHED", "AMBIGUOUS", "NOT_ESTABLISHED", "NOT_APPLICABLE"}
WARRANT_ONLY_OPERATIONS = {
    "ROLE_ASSIGNMENT",
    "FORCE_ASSIGNMENT",
    "DEFINITION_RESOLUTION",
    "CROSS_REFERENCE_EXPANSION",
    "AGGREGATION",
    "CLOSED_WORLD_ASSUMPTION",
    "CANONICAL_EQUIVALENCE",
}
NON_ADMITTED_BOUNDARY_STATES = {
    "MISSING_AUTHORITY_EVIDENCE",
    "OUT_OF_SCOPE",
    "REVOKED",
    "CONFLICTING_AUTHORITY",
    "ADMISSION_NOT_ESTABLISHED",
}
FORBIDDEN_RUNTIME_TOKENS = ("ALLOW", "DENY", "PERMIT", "EXECUTE", "TRANSACTION_RESULT")
PROVIDER_NAMES = ("nvidia", "nim", "openai", "gpt", "gemini", "anthropic", "claude", "llama")


def _load(repo_root: Path, relpath: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / relpath).read_text(encoding="utf-8"))
    return document


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = _load(repo_root, CORPUS_RELPATH)
    return document


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = _load(repo_root, FREEZE_RELPATH)
    return document


@pytest.fixture(scope="module")
def ruleset(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = _load(repo_root, DESIGN / "INTERPRETATION-RULESET-v0.1.json")
    return document


@pytest.fixture(scope="module")
def validators(repo_root: Path) -> dict[str, Draft202012Validator]:
    documents = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / DESIGN).glob("*.schema.json"))
    }
    resources: list[tuple[str, Resource]] = []
    for filename, document in documents.items():
        resource = Resource.from_contents(document, default_specification=DRAFT202012)
        schema_id = document.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, resource))
        resources.append((filename, resource))
    registry = Registry().with_resources(resources)
    return {
        name: Draft202012Validator(document, registry=registry)
        for name, document in documents.items()
    }


def _units(corpus_document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        unit for vector in corpus_document["vectors"] for unit in vector["expected_canonical_ir"]
    ]


# ---------------------------------------------------------------------------
# The package and the historical schema
# ---------------------------------------------------------------------------


def test_the_design_package_contains_exactly_the_declared_deliverables(repo_root: Path) -> None:
    found = {path.name for path in (repo_root / DESIGN).iterdir() if path.is_file()}
    assert found == EXPECTED_FILES


def test_the_historical_generic_ir_schema_is_byte_identical(repo_root: Path) -> None:
    """It is historical architecture. This design is a successor, not a replacement."""
    import subprocess

    from oic.baseline import BOOTSTRAP_COMMIT

    historical = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "cat-file",
            "blob",
            f"{BOOTSTRAP_COMMIT}:{HISTORICAL_IR_SCHEMA.as_posix()}",
        ],
        capture_output=True,
        check=True,
    ).stdout
    assert (repo_root / HISTORICAL_IR_SCHEMA).read_bytes() == historical


def test_the_successor_schema_lives_in_the_design_namespace(repo_root: Path) -> None:
    successor = _load(repo_root, DESIGN / "INSTITUTIONAL-IR-v0.1.schema.json")
    historical = _load(repo_root, HISTORICAL_IR_SCHEMA)
    assert successor["$id"] != historical["$id"]
    assert "/design/institutional-ir-001/" in successor["$id"]
    assert successor["title"] != historical["title"]


def test_no_migration_from_the_historical_schema_is_claimed(repo_root: Path) -> None:
    for relpath in ("README.md", "IR-CONTRACT-v0.1.md"):
        text = (repo_root / DESIGN / relpath).read_text(encoding="utf-8")
        assert "No migration" in text or "no migration" in text, relpath


@pytest.mark.parametrize(
    "name",
    [
        "INSTITUTIONAL-IR-v0.1.schema.json",
        "INTERPRETATION-PROPOSAL-v0.1.schema.json",
        "INTERPRETATION-EVIDENCE-v0.1.schema.json",
    ],
)
def test_every_design_schema_is_a_valid_draft_2020_12_document(repo_root: Path, name: str) -> None:
    Draft202012Validator.check_schema(_load(repo_root, DESIGN / name))


# ---------------------------------------------------------------------------
# The corpus is frozen, and its admission receipts are real
# ---------------------------------------------------------------------------


def test_the_corpus_is_byte_frozen(repo_root: Path, freeze: dict[str, Any]) -> None:
    raw = (repo_root / CORPUS_RELPATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == freeze["corpus_sha256"]
    assert len(raw) == freeze["corpus_bytes"]
    assert freeze["design_only"] is True
    assert freeze["runtime_execution"] is False
    assert freeze["model_call"] is False


def test_the_corpus_declares_its_counts_and_they_hold(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    vectors = corpus["vectors"]
    assert len(vectors) == corpus["vector_count"] == freeze["vector_count"]
    assert 30 <= len(vectors) <= 40
    positive = [v for v in vectors if v["expected_boundary_rejection"] is None]
    boundary = [v for v in vectors if v["expected_boundary_rejection"] is not None]
    assert len(positive) == corpus["positive_vector_count"]
    assert len(boundary) == corpus["boundary_vector_count"]
    assert len({v["vector_id"] for v in vectors}) == len(vectors)


def test_every_admission_receipt_is_reproduced_by_the_frozen_evaluator(
    corpus: dict[str, Any],
) -> None:
    """The receipts are not authored. Each is re-derived through the real byte boundary."""
    checked = 0
    for vector in corpus["vectors"]:
        pairs = zip(vector["admission_inputs"], vector["admission_receipts"], strict=True)
        for admission_input, recorded in pairs:
            receipt = evaluate_admission_bytes(canonical_json(admission_input))
            assert receipt.to_json() == recorded, vector["vector_id"]
            checked += 1
    assert checked >= len(corpus["vectors"])


def test_only_admitted_receipts_appear_in_positive_vectors(corpus: dict[str, Any]) -> None:
    for vector in corpus["vectors"]:
        if vector["expected_boundary_rejection"] is not None:
            continue
        for receipt in vector["admission_receipts"]:
            assert receipt["admission_state"] == "ADMITTED", vector["vector_id"]
            assert receipt["reason_code"] == "OIC-ADM-0000"


def test_non_admitted_input_is_a_boundary_rejection_and_never_an_empty_ir(
    corpus: dict[str, Any],
) -> None:
    observed: set[str] = set()
    for vector in corpus["vectors"]:
        if vector["expected_boundary_rejection"] is None:
            continue
        assert vector["expected_boundary_rejection"] == "IR_INPUT_NOT_ADMITTED"
        assert vector["expected_canonical_ir"] == [], vector["vector_id"]
        assert vector["interpretation_proposal"] is None
        for receipt in vector["admission_receipts"]:
            assert receipt["admission_state"] != "ADMITTED"
            observed.add(receipt["admission_state"])
    assert observed == NON_ADMITTED_BOUNDARY_STATES


def test_every_canonical_unit_binds_an_admitted_receipt_present_in_its_vector(
    corpus: dict[str, Any],
) -> None:
    for vector in corpus["vectors"]:
        available = {receipt["admission_receipt_id"] for receipt in vector["admission_receipts"]}
        for unit in vector["expected_canonical_ir"]:
            assert unit["admission"]["admission_state"] == "ADMITTED"
            assert unit["admission"]["admission_receipt_id"] in available, vector["vector_id"]


def test_every_canonical_unit_validates_against_the_frozen_ir_schema(
    corpus: dict[str, Any], validators: dict[str, Draft202012Validator]
) -> None:
    validator = validators["INSTITUTIONAL-IR-v0.1.schema.json"]
    for unit in _units(corpus):
        errors = sorted(validator.iter_errors(unit), key=lambda error: list(error.absolute_path))
        assert errors == [], f"{unit['ir_unit_id']}: {errors[0].message if errors else ''}"


def test_every_proposal_and_interpretation_instrument_validates(
    corpus: dict[str, Any], validators: dict[str, Draft202012Validator]
) -> None:
    proposal_validator = validators["INTERPRETATION-PROPOSAL-v0.1.schema.json"]
    evidence_validator = validators["INTERPRETATION-EVIDENCE-v0.1.schema.json"]
    for vector in corpus["vectors"]:
        proposal = vector["interpretation_proposal"]
        if proposal is not None:
            assert list(proposal_validator.iter_errors(proposal)) == [], vector["vector_id"]
        for instrument in vector["interpretation_evidence"]:
            assert list(evidence_validator.iter_errors(instrument)) == [], vector["vector_id"]
            recomputed = digest_of(
                canonical_json({k: v for k, v in instrument.items() if k != "evidence_digest"})
            )
            assert recomputed == instrument["evidence_digest"]


# ---------------------------------------------------------------------------
# The invariants, observed in the corpus
# ---------------------------------------------------------------------------


def test_every_unit_carries_all_eleven_slots_exactly_once(corpus: dict[str, Any]) -> None:
    """A slot is never omitted, so an unexamined slot cannot look like an empty one."""
    for unit in _units(corpus):
        slots = [assertion["slot"] for assertion in unit["assertions"]]
        assert slots == list(SLOTS), unit["ir_unit_id"]


def test_no_established_assertion_exceeds_the_admitted_source(corpus: dict[str, Any]) -> None:
    """I1. Every canonical value, alternative, qualifier and normalization source is
    literally inside the admitted candidate span."""
    for vector in corpus["vectors"]:
        spans = {
            admission_input["candidate"]["candidate_span"]
            for admission_input in vector["admission_inputs"]
        }
        for unit in vector["expected_canonical_ir"]:
            for assertion in unit["assertions"]:
                support = assertion["source_support"]
                if assertion["interpretation_status"] == "ESTABLISHED":
                    assert support is not None, (vector["vector_id"], assertion["slot"])
                    assert any(support["quote"] in span for span in spans), (
                        vector["vector_id"],
                        assertion["slot"],
                    )
                for alternative in assertion["alternatives"]:
                    assert any(alternative["value"] in span for span in spans)
                for qualifier in assertion["material_qualifiers"]:
                    assert any(qualifier["text"] in span for span in spans)
                normalization = assertion["normalization"]
                if normalization is not None:
                    assert any(normalization["raw_source_text"] in span for span in spans)
            for reference in unit["unresolved_references"]:
                assert any(reference["reference_text"] in span for span in spans)


def test_established_requires_a_basis_and_ambiguous_forbids_a_value(
    corpus: dict[str, Any],
) -> None:
    """I4 and I9 as a structural property rather than a schema formality."""
    for unit in _units(corpus):
        for assertion in unit["assertions"]:
            status = assertion["interpretation_status"]
            assert status in STATUSES
            if status == "ESTABLISHED":
                assert assertion["interpretation_basis"] != "NONE"
                assert assertion["value"]
                assert assertion["alternatives"] == []
            elif status == "AMBIGUOUS":
                assert assertion["value"] is None
                assert len(assertion["alternatives"]) >= 2
            else:
                assert assertion["value"] is None
                assert assertion["interpretation_basis"] == "NONE"
                assert assertion["interpretation_evidence_refs"] == []


def test_a_non_deterministic_basis_always_names_an_instrument(corpus: dict[str, Any]) -> None:
    """I8. An ESTABLISHED value must be distinguishable from a confident guess."""
    for vector in corpus["vectors"]:
        available = {
            instrument["interpretation_evidence_id"]
            for instrument in vector["interpretation_evidence"]
        }
        for unit in vector["expected_canonical_ir"]:
            for assertion in unit["assertions"]:
                basis = assertion["interpretation_basis"]
                refs = assertion["interpretation_evidence_refs"]
                if basis in {
                    "REGISTERED_INTERPRETATION_RULE",
                    "INSTITUTIONAL_INTERPRETATION_WARRANT",
                }:
                    assert refs, (vector["vector_id"], assertion["slot"])
                    assert set(refs) <= available, (vector["vector_id"], assertion["slot"])
                elif basis == "DETERMINISTIC_NORMALIZATION":
                    assert refs == []


def test_an_interpretation_instrument_binds_the_same_source_instance(
    corpus: dict[str, Any],
) -> None:
    """A warrant for one source instance never reaches another."""
    for vector in corpus["vectors"]:
        instances = {
            (r["source_id"], r["source_version"], r["source_digest"])
            for r in vector["admission_receipts"]
        }
        for instrument in vector["interpretation_evidence"]:
            applies = instrument["applies_to"]
            assert (
                applies["source_id"],
                applies["source_version"],
                applies["source_digest"],
            ) in instances, vector["vector_id"]


def test_material_qualifiers_are_represented_wherever_the_source_carries_them(
    corpus: dict[str, Any],
) -> None:
    """I3, checked against the threat tags the corpus itself declares."""
    required = {
        "IIR-002": "NEGATION",
        "IIR-004": "HEDGE",
        "IIR-012": "COMPARATOR",
        "IIR-013": "CURRENCY",
        "IIR-019": "DISCRETION",
        "IIR-027": "HEDGE",
        "IIR-031": "COMPARATOR",
    }
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id, kind in required.items():
        kinds = {
            qualifier["qualifier_kind"]
            for unit in by_id[vector_id]["expected_canonical_ir"]
            for assertion in unit["assertions"]
            for qualifier in assertion["material_qualifiers"]
        }
        assert kind in kinds, vector_id


def test_normalization_never_leaves_its_raw_source_behind(corpus: dict[str, Any]) -> None:
    """A normalized value alone is unauditable, so both forms are always present."""
    seen = 0
    for unit in _units(corpus):
        for assertion in unit["assertions"]:
            normalization = assertion["normalization"]
            if normalization is None:
                continue
            seen += 1
            assert normalization["raw_source_text"]
            assert normalization["normalized_value"]
            assert assertion["interpretation_basis"] == "DETERMINISTIC_NORMALIZATION"
    assert seen >= 5


def test_ambiguity_and_unknown_are_first_class(corpus: dict[str, Any]) -> None:
    observed = {
        assertion["interpretation_status"]
        for unit in _units(corpus)
        for assertion in unit["assertions"]
    }
    assert observed == STATUSES


def test_a_dropped_proposal_slot_does_not_erase_canonical_content(
    corpus: dict[str, Any],
) -> None:
    """Canonicalization reads the admitted source, not only the proposal."""
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id, slot in (("IIR-030", "exception"), ("IIR-031", "quantum")):
        vector = by_id[vector_id]
        proposed = {
            item["slot"] for item in vector["interpretation_proposal"]["proposed_assertions"]
        }
        assert slot not in proposed, f"{vector_id}: the attack must actually drop {slot}"
        unit = vector["expected_canonical_ir"][0]
        assertion = next(a for a in unit["assertions"] if a["slot"] == slot)
        assert assertion["interpretation_status"] == "ESTABLISHED", vector_id


def test_an_added_proposal_slot_does_not_create_canonical_content(
    corpus: dict[str, Any],
) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id, slot in (("IIR-029", "bearer"), ("IIR-032", "condition")):
        vector = by_id[vector_id]
        proposed = {
            item["slot"] for item in vector["interpretation_proposal"]["proposed_assertions"]
        }
        assert slot in proposed, f"{vector_id}: the attack must actually propose {slot}"
        unit = vector["expected_canonical_ir"][0]
        assertion = next(a for a in unit["assertions"] if a["slot"] == slot)
        assert assertion["interpretation_status"] == "NOT_ESTABLISHED", vector_id


def test_semantic_force_is_never_strengthened_in_canonical_ir(corpus: dict[str, Any]) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id, proposed_force, canonical_force in (
        ("IIR-027", "OBLIGATION", "ADVISORY"),
        ("IIR-028", "OBLIGATION", "PERMISSION"),
    ):
        vector = by_id[vector_id]
        proposal_force = next(
            item
            for item in vector["interpretation_proposal"]["proposed_assertions"]
            if item["slot"] == "normative_force"
        )
        assert proposal_force["proposed_value"] == proposed_force
        unit = vector["expected_canonical_ir"][0]
        force = next(a for a in unit["assertions"] if a["slot"] == "normative_force")
        assert force["value"] == canonical_force, vector_id


def test_forbidden_content_never_reaches_canonical_ir(corpus: dict[str, Any]) -> None:
    checked = 0
    for vector in corpus["vectors"]:
        blob = canonical_json(vector["expected_canonical_ir"]).decode("utf-8")
        for forbidden in vector["forbidden_in_canonical_ir"]:
            assert forbidden not in blob, (vector["vector_id"], forbidden)
            checked += 1
    assert checked >= 4


def test_unresolved_references_stay_unresolved(corpus: dict[str, Any]) -> None:
    seen = 0
    for unit in _units(corpus):
        for reference in unit["unresolved_references"]:
            seen += 1
            assert reference["resolution_status"] == "UNRESOLVED"
            assert reference["resolved_target"] is None
    assert seen >= 3


def test_exception_closure_stays_open_without_a_closed_world_instrument(
    corpus: dict[str, Any],
) -> None:
    for unit in _units(corpus):
        if unit["exception_closure"] == "CLOSED_BY_WARRANT":
            assert unit["closed_world_evidence_refs"]
        else:
            assert unit["exception_closure"] == "OPEN"


# ---------------------------------------------------------------------------
# Identity, lineage and temporality
# ---------------------------------------------------------------------------


def test_ir_unit_identity_is_content_derived_and_reproduces(corpus: dict[str, Any]) -> None:
    for unit in _units(corpus):
        without_id = {key: value for key, value in unit.items() if key != "ir_unit_id"}
        assert unit["ir_unit_id"] == "iir-" + digest_of(canonical_json(without_id))
        assert re.fullmatch(r"iir-sha256:[0-9a-f]{64}", unit["ir_unit_id"])


def test_source_instance_identity_survives_semantic_equivalence(
    corpus: dict[str, Any],
) -> None:
    """I9. Same meaning, different institutional instance: two ids, one equivalence key."""
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    for vector_id in ("IIR-021", "IIR-033"):
        units = by_id[vector_id]["expected_canonical_ir"]
        assert len(units) == 2, vector_id
        assert units[0]["ir_unit_id"] != units[1]["ir_unit_id"], vector_id
        assert units[0]["semantic_equivalence_key"] == units[1]["semantic_equivalence_key"]
        instances = {
            (unit["admission"]["source_id"], unit["admission"]["source_version"]) for unit in units
        }
        assert len(instances) == 2, vector_id


def test_a_different_interpretation_instrument_changes_canonical_meaning(
    corpus: dict[str, Any],
) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    units = by_id["IIR-034"]["expected_canonical_ir"]
    assert len(units) == 2
    assert (
        units[0]["admission"]["admission_receipt_id"]
        == units[1]["admission"]["admission_receipt_id"]
    )
    assert units[0]["ir_unit_id"] != units[1]["ir_unit_id"]
    assert units[0]["semantic_equivalence_key"] != units[1]["semantic_equivalence_key"]
    statuses = {
        next(a for a in unit["assertions"] if a["slot"] == "bearer")["interpretation_status"]
        for unit in units
    }
    assert statuses == {"AMBIGUOUS", "ESTABLISHED"}
    resolved = next(
        unit
        for unit in units
        if next(a for a in unit["assertions"] if a["slot"] == "bearer")["interpretation_status"]
        == "ESTABLISHED"
    )
    bearer = next(a for a in resolved["assertions"] if a["slot"] == "bearer")
    assert bearer["interpretation_basis"] == "INSTITUTIONAL_INTERPRETATION_WARRANT"


def test_supersession_creates_a_successor_and_never_mutates_a_predecessor(
    corpus: dict[str, Any],
) -> None:
    by_id = {vector["vector_id"]: vector for vector in corpus["vectors"]}
    units = by_id["IIR-022"]["expected_canonical_ir"]
    assert len(units) == 2
    predecessor, successor = units
    assert predecessor["supersedes_ir_unit_id"] is None
    assert successor["supersedes_ir_unit_id"] == predecessor["ir_unit_id"]
    assert predecessor["admission"]["source_version"] != successor["admission"]["source_version"]


def test_every_unit_is_temporally_explicit(corpus: dict[str, Any]) -> None:
    for unit in _units(corpus):
        assert unit["interpretation_time"].endswith("Z")
        assert unit["admission"]["evaluation_time"].endswith("Z")
        assert unit["admission"]["ruleset_digest"].startswith("sha256:")
        assert unit["interpretation_ruleset"]["ruleset_digest"].startswith("sha256:")


def test_the_interpretation_ruleset_digest_is_the_canonical_digest_of_the_ruleset(
    repo_root: Path, corpus: dict[str, Any], ruleset: dict[str, Any]
) -> None:
    del repo_root
    computed = digest_of(canonical_json(ruleset))
    assert corpus["interpretation_ruleset_digest"] == computed
    for unit in _units(corpus):
        assert unit["interpretation_ruleset"]["ruleset_digest"] == computed


def test_the_minimum_lineage_projection_is_recoverable_for_every_assertion(
    corpus: dict[str, Any],
) -> None:
    """I8, as the chain the lineage document specifies."""
    for unit in _units(corpus):
        admission = unit["admission"]
        assert admission["authority_evidence_refs"]
        assert admission["authority_evidence_digests"]
        assert admission["candidate_projection_digest"].startswith("sha256:")
        for assertion in unit["assertions"]:
            if assertion["interpretation_status"] != "ESTABLISHED":
                continue
            support = assertion["source_support"]
            assert support["content_hash"] == admission["source_digest"]
            assert support["anchor_id"]


# ---------------------------------------------------------------------------
# Separation from execution, and provider neutrality
# ---------------------------------------------------------------------------


def test_no_runtime_permission_state_exists_anywhere_in_the_design(repo_root: Path) -> None:
    for path in sorted((repo_root / DESIGN).glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        blob = canonical_json(document).decode("utf-8")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            assert f'"{token}"' not in blob, (path.name, token)


def test_the_schemas_are_closed_so_a_permission_field_cannot_be_added(
    repo_root: Path,
) -> None:
    for name in (
        "INSTITUTIONAL-IR-v0.1.schema.json",
        "INTERPRETATION-PROPOSAL-v0.1.schema.json",
        "INTERPRETATION-EVIDENCE-v0.1.schema.json",
    ):
        document = _load(repo_root, DESIGN / name)
        assert document["additionalProperties"] is False, name


def test_a_proposal_has_no_field_that_could_carry_confidence_or_authority(
    repo_root: Path, validators: dict[str, Draft202012Validator]
) -> None:
    """Model confidence cannot create semantic establishment: there is nowhere to write it."""
    schema = _load(repo_root, DESIGN / "INTERPRETATION-PROPOSAL-v0.1.schema.json")
    properties = set(schema["properties"])
    for forbidden in (
        "confidence",
        "score",
        "probability",
        "authority",
        "interpretation_evidence_refs",
        "interpretation_basis",
        "interpretation_status",
        "canonical",
        "admission_state",
    ):
        assert forbidden not in properties, forbidden
    assert schema["properties"]["proposal_state"]["const"] == "PROVISIONAL"
    assert schema["properties"]["epistemic_state"]["const"] == "uncertain"

    validator = validators["INTERPRETATION-PROPOSAL-v0.1.schema.json"]
    sample = {
        "proposal_id": "iip-probe",
        "proposal_schema_id": "OIC-INTERPRETATION-PROPOSAL-v0.1",
        "admission_receipt_id": "admrec-sha256:" + "0" * 64,
        "candidate_unit_id": "cnu-" + "0" * 24,
        "candidate_projection_digest": "sha256:" + "0" * 64,
        "proposer": {"proposer_kind": "MODEL", "proposer_id": "probe"},
        "proposal_state": "PROVISIONAL",
        "epistemic_state": "uncertain",
        "proposed_assertions": [],
        "confidence": 0.99,
    }
    assert list(validator.iter_errors(sample)), "a confidence field must be refused"


def test_a_model_cannot_be_an_interpretation_authority(repo_root: Path) -> None:
    schema = _load(repo_root, DESIGN / "INTERPRETATION-EVIDENCE-v0.1.schema.json")
    assert set(schema["properties"]["basis_kind"]["enum"]) == {
        "REGISTERED_INTERPRETATION_RULE",
        "INSTITUTIONAL_INTERPRETATION_WARRANT",
    }
    operations = set(schema["properties"]["permitted_operations"]["items"]["enum"])
    assert operations == WARRANT_ONLY_OPERATIONS
    assert "model" in schema["properties"]["interpretation_authority_id"]["description"].lower()


def test_the_design_names_no_model_provider(repo_root: Path) -> None:
    for path in sorted((repo_root / DESIGN).iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for provider in PROVIDER_NAMES:
            assert not re.search(rf"\b{provider}\b", text), (path.name, provider)


def test_no_institutional_ir_runtime_or_compiler_exists(repo_root: Path) -> None:
    modules = {path.name for path in (repo_root / "src" / "oic").glob("*.py")}
    assert "institutional_ir.py" not in modules
    assert not (repo_root / "src/oic/institutional_ir.py").exists()
    assert not list((repo_root / "src").rglob("*.rego"))
    assert not list((repo_root / DESIGN).glob("*.rego"))


# ---------------------------------------------------------------------------
# Vocabulary justification, threat coverage and claim ceiling
# ---------------------------------------------------------------------------


def test_every_slot_is_justified_and_every_exclusion_is_reasoned(
    ruleset: dict[str, Any],
) -> None:
    declared = [entry["slot"] for entry in ruleset["slot_vocabulary"]]
    assert set(declared) == set(SLOTS)
    for entry in ruleset["slot_vocabulary"]:
        assert len(entry["justification"]) > 40, entry["slot"]
    for entry in ruleset["excluded_dimensions"]:
        assert entry["decision"] in {
            "EXCLUDED",
            "EXCLUDED AS A SLOT",
            "FOLDED",
            "REPRESENTED AS A RELATION",
        }
        assert len(entry["justification"]) > 40, entry["dimension"]
    excluded = {entry["dimension"] for entry in ruleset["excluded_dimensions"]}
    for dimension in ("scope", "consequence / remedy", "evidence duty", "review duty", "trigger"):
        assert dimension in excluded


def test_the_status_and_basis_vocabularies_are_derived_not_imported(
    ruleset: dict[str, Any],
) -> None:
    statuses = {entry["status"] for entry in ruleset["interpretation_status_vocabulary"]}
    assert statuses == STATUSES
    for entry in ruleset["interpretation_status_vocabulary"]:
        assert len(entry["meaning"]) > 40, entry["status"]
    bases = {entry["basis"] for entry in ruleset["interpretation_basis_vocabulary"]}
    assert bases == {
        "DETERMINISTIC_NORMALIZATION",
        "REGISTERED_INTERPRETATION_RULE",
        "INSTITUTIONAL_INTERPRETATION_WARRANT",
        "NONE",
    }
    assert ruleset["runtime_permission_states"] == []


def test_normalization_prohibitions_are_frozen(ruleset: dict[str, Any]) -> None:
    prohibitions = set(ruleset["normalization_prohibitions"])
    for required in (
        "adding an actor",
        "resolving ambiguity",
        "inferring a missing condition",
        "broadening scope",
        "changing modality",
        "inferring authority",
    ):
        assert required in prohibitions, required


def test_forbidden_force_transitions_are_frozen(ruleset: dict[str, Any]) -> None:
    transitions = {(entry["from"], entry["to"]) for entry in ruleset["forbidden_force_transitions"]}
    assert ("ADVISORY", "OBLIGATION") in transitions
    assert ("PERMISSION", "OBLIGATION") in transitions
    structural = set(ruleset["forbidden_structural_transitions"])
    for required in (
        "eligible -> entitled",
        "review -> approval",
        "recipient -> bearer",
        "default -> universal rule",
        "conditional -> unconditional",
        "exception-bearing -> exceptionless",
    ):
        assert required in structural, required


def test_every_required_threat_category_is_present(corpus: dict[str, Any]) -> None:
    tags = set(corpus["threat_tags"])
    required = {
        "invented_actor",
        "invented_condition",
        "force_strengthening",
        "exception_preservation",
        "threshold_preservation",
        "currency_preservation",
        "temporal_preservation",
        "condition_preservation",
        "qualifier_loss",
        "negation_preservation",
        "advisory_wording",
        "definition_invention",
        "definition_source_loss",
        "reference_expansion",
        "reference_loss",
        "ambiguity_guessed_away",
        "unknown_as_false",
        "recipient_becomes_actor",
        "instance_collapse",
        "version_collapse",
        "warrant_independence",
        "standing_leaks_into_meaning",
        "silent_mutation",
        "non_admitted_material",
        "slot_minimality",
    }
    assert required <= tags, sorted(required - tags)


def test_every_vector_carries_a_falsifier_and_a_claim_ceiling(corpus: dict[str, Any]) -> None:
    for vector in corpus["vectors"]:
        assert len(vector["falsifier"]) > 40, vector["vector_id"]
        assert vector["claim_ceiling"] == corpus["claim_ceiling"]


def test_the_preregistration_states_twelve_falsifiers(repo_root: Path) -> None:
    text = (repo_root / DESIGN / "PREREGISTRATION-v0.1.md").read_text(encoding="utf-8")
    numbered = re.findall(r"^\d+\. \*\*", text, flags=re.MULTILINE)
    assert len(numbered) == 12


def test_the_claim_ceiling_is_intact(repo_root: Path, corpus: dict[str, Any]) -> None:
    for claim in (
        "semantic correctness",
        "universal institutional ontology",
        "legal interpretation",
        "production interpretation authority",
        "cross-model reliability",
        "successful IR construction",
        "OCE compilation",
        "runtime authorization",
        "compliance",
        "production readiness",
        "independent validation",
    ):
        assert claim in corpus["claim_ceiling"], claim
    assert corpus["independent_validation_claim"] is False
    assert corpus["self_adjudication"] == "NOT SELF-ADJUDICATED"
    for relpath in ("PREREGISTRATION-v0.1.md", "IR-CONTRACT-v0.1.md", "README.md"):
        text = (repo_root / DESIGN / relpath).read_text(encoding="utf-8")
        assert "independent_validation_claim = FALSE" in text, relpath
        assert "NOT SELF-ADJUDICATED" in text, relpath


def test_the_package_declares_that_no_runtime_was_implemented(repo_root: Path) -> None:
    text = (repo_root / DESIGN / "PREREGISTRATION-v0.1.md").read_text(encoding="utf-8")
    for statement in (
        "NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.",
        "NO OCE OR REGO WAS IMPLEMENTED.",
        "NO EXECUTION AUTHORIZATION WAS IMPLEMENTED.",
        "NO MODEL CALL WAS MADE.",
    ):
        assert statement in text, statement
