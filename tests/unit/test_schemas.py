"""Tests for offline schema discovery and Draft 2020-12 validation.

Fixture directories under ``tests/fixtures/schemas/`` each isolate one defect class so a
reviewer can see exactly what each failure mode looks like.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.errors import SchemaDiscoveryError, SchemaValidationError
from oic.schemas import (
    IssueCode,
    SchemaStatus,
    discover_schemas,
    validate_schema_directory,
)


@pytest.fixture
def schema_fixtures(fixtures_dir: Path) -> Path:
    return fixtures_dir / "schemas"


def _codes(directory: Path, **kwargs: bool) -> set[IssueCode]:
    report = validate_schema_directory(directory, root=directory, **kwargs)
    return {issue.code for issue in report.issues}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discovery_is_deterministically_ordered(schema_fixtures: Path) -> None:
    found = discover_schemas(schema_fixtures)
    relative = [path.relative_to(schema_fixtures).as_posix() for path in found]
    assert relative == sorted(relative)
    # Repeated discovery must produce the identical sequence.
    assert [p.as_posix() for p in discover_schemas(schema_fixtures)] == [
        p.as_posix() for p in found
    ]


def test_discovery_only_matches_the_schema_suffix(tmp_path: Path) -> None:
    (tmp_path / "real.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "plain.json").write_text("{}", encoding="utf-8")
    (tmp_path / "notes.md").write_text("x", encoding="utf-8")
    found = discover_schemas(tmp_path)
    assert [path.name for path in found] == ["real.schema.json"]


def test_discovery_recurses(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "deep.schema.json").write_text("{}", encoding="utf-8")
    assert [p.name for p in discover_schemas(tmp_path)] == ["deep.schema.json"]


def test_missing_directory_raises_discovery_error(tmp_path: Path) -> None:
    with pytest.raises(SchemaDiscoveryError) as excinfo:
        discover_schemas(tmp_path / "absent")
    assert excinfo.value.code == "OIC-1002"


def test_empty_directory_raises_discovery_error(tmp_path: Path) -> None:
    with pytest.raises(SchemaDiscoveryError):
        discover_schemas(tmp_path)


def test_file_instead_of_directory_raises_discovery_error(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(SchemaDiscoveryError):
        discover_schemas(target)


# ---------------------------------------------------------------------------
# Valid schemas
# ---------------------------------------------------------------------------


def test_valid_fixture_directory_passes(schema_fixtures: Path) -> None:
    report = validate_schema_directory(schema_fixtures / "valid", root=schema_fixtures / "valid")
    assert report.status is SchemaStatus.PASS
    assert report.issues == ()
    assert len(report.results) == 2


def test_relative_ref_resolves_against_absolute_id(schema_fixtures: Path) -> None:
    """`$ref: "child.schema.json"` under an absolute `$id` must resolve locally.

    This is the pattern the nine governing schemas use, so it must work with no network.
    """
    parent = json.loads(
        (schema_fixtures / "valid" / "parent.schema.json").read_text(encoding="utf-8")
    )
    assert parent["properties"]["children"]["items"]["$ref"] == "child.schema.json"
    assert parent["$id"].startswith("https://")
    report = validate_schema_directory(schema_fixtures / "valid", root=schema_fixtures / "valid")
    assert report.status is SchemaStatus.PASS


def test_report_json_is_deterministic(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "valid"
    first = json.dumps(
        validate_schema_directory(directory, root=directory).to_json(), sort_keys=True
    )
    second = json.dumps(
        validate_schema_directory(directory, root=directory).to_json(), sort_keys=True
    )
    assert first == second


# ---------------------------------------------------------------------------
# Defect classes
# ---------------------------------------------------------------------------


def test_broken_schema_fails_metaschema_validation(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "invalid-metaschema"
    report = validate_schema_directory(directory, root=directory)
    assert report.status is SchemaStatus.FAIL
    issue = report.issues[0]
    assert issue.code is IssueCode.INVALID_METASCHEMA
    assert issue.json_pointer == "/properties/broken/type"
    assert issue.schema_path == "bad-type.schema.json"


def test_unresolved_local_reference_fails(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "unresolved-local-ref"
    report = validate_schema_directory(directory, root=directory)
    assert report.status is SchemaStatus.FAIL
    issue = report.issues[0]
    assert issue.code is IssueCode.UNRESOLVED_LOCAL_REF
    assert issue.json_pointer == "/properties/missing/$ref"


def test_forbidden_remote_reference_is_blocked(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "remote-ref"
    report = validate_schema_directory(directory, root=directory)
    assert report.status is SchemaStatus.FAIL
    issue = report.issues[0]
    assert issue.code is IssueCode.EXTERNAL_REF_BLOCKED
    assert "network resolution is not permitted" in issue.message


def test_remote_reference_can_be_allowed_explicitly(schema_fixtures: Path) -> None:
    """Opting in stops the check failing; it never enables fetching.

    The suite-wide socket block in conftest guarantees the second half of that claim.
    """
    directory = schema_fixtures / "remote-ref"
    report = validate_schema_directory(directory, root=directory, allow_external_refs=True)
    assert report.status is SchemaStatus.PASS
    assert report.external_refs_allowed is True


def test_duplicate_schema_id_is_reported(schema_fixtures: Path) -> None:
    assert IssueCode.DUPLICATE_SCHEMA_ID in _codes(schema_fixtures / "duplicate-id")


def test_malformed_json_is_reported(schema_fixtures: Path) -> None:
    assert IssueCode.UNPARSEABLE_JSON in _codes(schema_fixtures / "malformed-json")


def test_non_object_document_is_reported(schema_fixtures: Path) -> None:
    assert IssueCode.NOT_AN_OBJECT in _codes(schema_fixtures / "not-an-object")


def test_failures_are_collected_not_raised_on_first(schema_fixtures: Path) -> None:
    """One bad schema must not hide the results for the others."""
    report = validate_schema_directory(schema_fixtures, root=schema_fixtures)
    assert report.status is SchemaStatus.FAIL
    passed = [r.schema_path for r in report.results if r.status is SchemaStatus.PASS]
    failed = [r.schema_path for r in report.results if r.status is SchemaStatus.FAIL]
    assert "valid/parent.schema.json" in passed
    assert "invalid-metaschema/bad-type.schema.json" in failed
    assert len(report.results) == len(discover_schemas(schema_fixtures))


def test_raise_for_status_raises_a_typed_contract_error(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "invalid-metaschema"
    report = validate_schema_directory(directory, root=directory)
    with pytest.raises(SchemaValidationError) as excinfo:
        report.raise_for_status()
    assert excinfo.value.code == "OIC-2002"
    assert excinfo.value.schema_path == "bad-type.schema.json"


def test_raise_for_status_is_silent_on_pass(schema_fixtures: Path) -> None:
    directory = schema_fixtures / "valid"
    validate_schema_directory(directory, root=directory).raise_for_status()
