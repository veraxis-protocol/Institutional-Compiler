"""The compiler front end: the chain, and what may not travel down it.

The interesting assertions here are the negative ones. A parser that extracts
cleanly is not the achievement; a parser whose output stays inexecutable until
something else admits it is.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from oic.demo_compiler import (
    COMPILER_VERSION,
    GROUND_ATOMS,
    GROUND_IDS,
    SYNTHETIC_GRAMMAR_ID,
    CompilationError,
    canonical_json_digest,
    compile_policy,
    ground_marking,
    load_policy_source,
    parse_source_document,
)
from oic.demo_runtime import compile_scenario, load_scenario

ADVISORY_SUFFIX = "#unit/advisory/prefer_electronic_submission"


@pytest.fixture(scope="module")
def compiled(repo_root: Path) -> dict[str, Any]:
    scenario = load_scenario(repo_root)
    return dict(compile_scenario(scenario))


def _registry(repo_root: Path) -> Registry:
    """Resolve the draft set's cross-references locally, by file name.

    The governing schemas reference each other by bare file name. Without a
    registry the reference is unresolvable and the validator raises rather than
    reporting a validation result, which would read like a passing test that
    never ran.
    """
    resources = []
    for path in sorted((repo_root / "schemas" / "draft").glob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        resources.append((path.name, Resource.from_contents(document)))
    return Registry().with_resources(resources)


def _schema(repo_root: Path, name: str) -> Draft202012Validator:
    document = json.loads((repo_root / "schemas" / "draft" / name).read_text(encoding="utf-8"))
    return Draft202012Validator(document, registry=_registry(repo_root))


def test_the_grammar_is_declared_and_bounded() -> None:
    assert SYNTHETIC_GRAMMAR_ID.endswith("v0.1")
    assert "SYNTHETIC" in SYNTHETIC_GRAMMAR_ID


def test_every_ground_id_has_a_declared_kernel_atom() -> None:
    """The two spellings are mapped explicitly, not coincidentally.

    The kernel tokenizer accepts ``[A-Za-z0-9_]`` only, so ``g:x`` cannot cross
    the boundary as written. A silent rename would make the warrant's ground
    identifiers untraceable back to the institution's.
    """
    assert set(GROUND_ATOMS) == set(GROUND_IDS)
    for ground_id, atom in GROUND_ATOMS.items():
        assert ":" not in atom
        assert atom.replace("_", "").isalnum()
        assert ground_id.split(":", 1)[1] == atom[len("g_") :]


def test_authority_and_delegation_are_not_grounds() -> None:
    """Neither may become a proposition the kernel is asked to evaluate."""
    joined = " ".join(GROUND_IDS).lower()
    assert "authority" not in joined
    assert "deleg" not in joined


def test_source_document_validates_against_the_governing_schema(
    repo_root: Path, compiled: dict[str, Any]
) -> None:
    validator = _schema(repo_root, "source-document.schema.json")
    for policy in compiled.values():
        validator.validate(policy.source_document)


def test_source_nodes_and_anchors_validate(repo_root: Path, compiled: dict[str, Any]) -> None:
    node_validator = _schema(repo_root, "source-node.schema.json")
    anchor_validator = _schema(repo_root, "source-anchor.schema.json")
    for policy in compiled.values():
        for node in policy.source_document["nodes"]:
            node_validator.validate(node)
        for anchor in policy.control_envelope["source_anchors"]:
            anchor_validator.validate(anchor)


def test_candidates_validate_against_the_governing_schema(
    repo_root: Path, compiled: dict[str, Any]
) -> None:
    validator = _schema(repo_root, "candidate-normative-unit.schema.json")
    for policy in compiled.values():
        for candidate in policy.candidates:
            validator.validate(candidate)


def test_admission_records_validate(repo_root: Path, compiled: dict[str, Any]) -> None:
    validator = _schema(repo_root, "admission-record.schema.json")
    for policy in compiled.values():
        for record in policy.admission_records:
            validator.validate(record)


def test_ir_authority_and_envelope_validate(repo_root: Path, compiled: dict[str, Any]) -> None:
    ir = _schema(repo_root, "institutional-ir.schema.json")
    authority = _schema(repo_root, "authority-record.schema.json")
    envelope = _schema(repo_root, "control-envelope.schema.json")
    for policy in compiled.values():
        ir.validate(policy.institutional_ir)
        authority.validate(policy.authority_record)
        envelope.validate(policy.control_envelope)


def test_runtime_binding_validates_against_the_demo_schema(
    repo_root: Path, compiled: dict[str, Any]
) -> None:
    document = json.loads(
        (repo_root / "schemas" / "demo" / "runtime-binding.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(document)
    for policy in compiled.values():
        validator.validate(policy.runtime_binding)


def test_the_advisory_candidate_is_extracted(compiled: dict[str, Any]) -> None:
    for policy in compiled.values():
        advisory = [c for c in policy.candidates if c["unit_id"].endswith(ADVISORY_SUFFIX)]
        assert len(advisory) == 1
        assert advisory[0]["unit_type"] == "advisory"


def test_the_advisory_candidate_never_becomes_executable(compiled: dict[str, Any]) -> None:
    """Extraction succeeded and executability did not follow. That is the point."""
    for policy in compiled.values():
        advisory = next(c for c in policy.candidates if c["unit_id"].endswith(ADVISORY_SUFFIX))
        assert advisory["interpretation_state"] == "extracted"
        assert advisory["unit_id"] not in policy.admitted_unit_ids
        executable_units = {str(c["unit_id"]) for c in policy.control_envelope["conditions"]}
        assert advisory["unit_id"] not in executable_units


def test_every_executable_field_traces_to_a_source_anchor(compiled: dict[str, Any]) -> None:
    for policy in compiled.values():
        anchor_ids = {str(a["anchor_id"]) for a in policy.control_envelope["source_anchors"]}
        assert anchor_ids
        for condition in policy.control_envelope["conditions"]:
            assert condition["source_anchor_ids"]
            assert set(condition["source_anchor_ids"]) <= anchor_ids


def test_every_admitted_unit_is_named_by_an_admission_record(compiled: dict[str, Any]) -> None:
    for policy in compiled.values():
        named = {
            str(r["subject_id"]) for r in policy.admission_records if r["disposition"] == "admit"
        }
        assert set(policy.admitted_unit_ids) == named


def test_admission_must_name_the_exact_source_bytes(repo_root: Path) -> None:
    """An admission that does not name these bytes cannot admit them."""
    scenario = load_scenario(repo_root)
    source = load_policy_source(scenario.root / "policy-v1.src.txt", source_id="src:X/v1")
    document = json.loads((scenario.root / "admission-v1.json").read_text(encoding="utf-8"))
    records = [
        {**r, "source_hashes": ["sha256:" + "0" * 64]} for r in document["admission_records"]
    ]
    with pytest.raises(CompilationError, match="does not name this source"):
        compile_policy(
            source,
            admission_records=records,
            ingested_at="2027-01-01T00:00:00Z",
            kernel_profile_id="ztl-v0.1",
            canonicalization_profile_id="ztl-jcs-float-free-sha384-v0.1",
            bound_formula_hash="sha384:" + "0" * 96,
        )


def test_admission_cannot_name_a_unit_the_source_did_not_produce(repo_root: Path) -> None:
    scenario = load_scenario(repo_root)
    source = load_policy_source(
        scenario.root / "policy-v1.src.txt", source_id="src:SYNTH-GRANT-POLICY/v1"
    )
    document = json.loads((scenario.root / "admission-v1.json").read_text(encoding="utf-8"))
    records = [
        *document["admission_records"],
        {
            **document["admission_records"][0],
            "admission_id": "adm:invented",
            "subject_id": "src:SYNTH-GRANT-POLICY/v1#unit/invented",
        },
    ]
    with pytest.raises(CompilationError, match="names units this source did not produce"):
        compile_policy(
            source,
            admission_records=records,
            ingested_at="2027-01-01T00:00:00Z",
            kernel_profile_id="ztl-v0.1",
            canonicalization_profile_id="ztl-jcs-float-free-sha384-v0.1",
            bound_formula_hash="sha384:" + "0" * 96,
        )


def test_a_line_outside_the_grammar_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.src.txt"
    path.write_text("POLICY X v1\nENACT_WHATEVER_I_LIKE now\n", encoding="utf-8")
    source = load_policy_source(path, source_id="src:X/v1")
    with pytest.raises(CompilationError, match="outside the bounded grammar"):
        parse_source_document(source, ingested_at="2027-01-01T00:00:00Z")


def test_compilation_is_deterministic(repo_root: Path) -> None:
    """Same bytes, same declared logical time, same output — byte for byte."""
    first = compile_scenario(load_scenario(repo_root))
    second = compile_scenario(load_scenario(repo_root))
    for version in first:
        assert canonical_json_digest(first[version].control_envelope) == canonical_json_digest(
            second[version].control_envelope
        )
        assert first[version].runtime_binding == second[version].runtime_binding


def test_the_envelope_records_its_compiler_and_fails_closed_on_unknown(
    compiled: dict[str, Any],
) -> None:
    for policy in compiled.values():
        assert policy.control_envelope["compiler_version"] == COMPILER_VERSION
        # UNKNOWN denies the operation. It does not assert that anything is false.
        assert policy.control_envelope["on_unknown"] == "deny"


def test_the_amount_limit_differs_between_the_two_versions(compiled: dict[str, Any]) -> None:
    limits = {
        version: next(
            c["value"] for c in policy.control_envelope["conditions"] if c["field"] == "amount"
        )
        for version, policy in compiled.items()
    }
    assert limits == {"v1": 50000, "v2": 25000}


def test_ground_marking_reflects_the_admitted_limit(compiled: dict[str, Any]) -> None:
    assert ground_marking(compiled["v1"], amount=40000, evidence_signed=True) == {
        "g_amount_within_limit": "T",
        "g_eligibility_evidence_present": "T",
    }
    assert ground_marking(compiled["v2"], amount=40000, evidence_signed=True) == {
        "g_amount_within_limit": "F",
        "g_eligibility_evidence_present": "T",
    }
