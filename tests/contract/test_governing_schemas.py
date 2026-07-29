"""Contract tests over the nine governing draft schemas.

These assert facts about the repository itself, not about this package's logic. A failure
here means a governing artifact changed, which is a governance event, not a bug to fix in
passing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.schemas import (
    DEFAULT_SCHEMA_DIRECTORY,
    SchemaStatus,
    discover_schemas,
    validate_schema_directory,
)

pytestmark = pytest.mark.contract

#: The exact schema set frozen by the bootstrap. Adding or removing one is a contract
#: change and must be accompanied by an ADR.
EXPECTED_SCHEMAS: tuple[str, ...] = (
    "admission-record.schema.json",
    "authority-record.schema.json",
    "candidate-normative-unit.schema.json",
    "control-envelope.schema.json",
    "institutional-ir.schema.json",
    "runtime-evaluation.schema.json",
    "source-anchor.schema.json",
    "source-document.schema.json",
    "source-node.schema.json",
)

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


@pytest.fixture
def schema_dir(repo_root: Path) -> Path:
    return repo_root / DEFAULT_SCHEMA_DIRECTORY


def test_exactly_nine_schemas_are_present(schema_dir: Path) -> None:
    names = tuple(path.name for path in discover_schemas(schema_dir))
    assert names == EXPECTED_SCHEMAS
    assert len(names) == 9


def test_all_nine_schemas_validate_as_draft_2020_12(schema_dir: Path, repo_root: Path) -> None:
    report = validate_schema_directory(schema_dir, root=repo_root)
    failures = [
        f"{issue.schema_path}{issue.json_pointer or '#'}: [{issue.code.value}] {issue.message}"
        for issue in report.issues
    ]
    assert failures == []
    assert report.status is SchemaStatus.PASS
    assert len(report.results) == 9


def test_every_schema_declares_the_2020_12_metaschema(schema_dir: Path) -> None:
    for path in discover_schemas(schema_dir):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document.get("$schema") == DRAFT_2020_12, path.name


def test_every_schema_declares_a_unique_id(schema_dir: Path, repo_root: Path) -> None:
    report = validate_schema_directory(schema_dir, root=repo_root)
    ids = [result.schema_id for result in report.results]
    assert all(schema_id is not None for schema_id in ids)
    assert len(set(ids)) == len(ids)


def test_external_references_are_not_required_to_validate(
    schema_dir: Path, repo_root: Path
) -> None:
    """The governing set must validate with remote resolution switched off.

    The suite runs with sockets disabled, so passing here also demonstrates that no
    network call occurs during validation.
    """
    report = validate_schema_directory(schema_dir, root=repo_root, allow_external_refs=False)
    assert report.status is SchemaStatus.PASS
    assert report.external_refs_allowed is False


def test_schema_ordering_is_stable_across_runs(schema_dir: Path, repo_root: Path) -> None:
    first = validate_schema_directory(schema_dir, root=repo_root).to_json()
    second = validate_schema_directory(schema_dir, root=repo_root).to_json()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert [result["schema_path"] for result in first["results"]] == [
        f"{DEFAULT_SCHEMA_DIRECTORY}/{name}" for name in EXPECTED_SCHEMAS
    ]


def test_content_hash_fields_require_the_canonical_sha256_form(schema_dir: Path) -> None:
    """Digest fields in the governing schemas use the same canonical form this package emits."""
    from oic.hashing import CANONICAL_DIGEST_PATTERN

    checked = 0
    for path in discover_schemas(schema_dir):
        document = json.loads(path.read_text(encoding="utf-8"))
        for name, definition in document.get("properties", {}).items():
            if name in {"content_hash"} and isinstance(definition, dict):
                assert definition.get("pattern") == CANONICAL_DIGEST_PATTERN, path.name
                checked += 1
    assert checked >= 3, "expected content_hash on source-anchor, source-node, source-document"
