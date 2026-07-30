"""Offline controls for the proposed Canada procurement acquisition preflight."""

from __future__ import annotations

import argparse
import ast
import hashlib
import http.client
import importlib.util
import io
import json
import subprocess
import urllib.request
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast
from urllib.parse import urlparse

import jsonschema
import pytest

pytestmark = pytest.mark.contract

REGISTRY_RELPATH = "benchmarks/preflight/canada/SOURCE-REGISTRY-PROPOSED-v0.1.json"
FRENCH_RELPATH = "benchmarks/preflight/canada/FRENCH-COUNTERPARTS-v0.1.json"
RECEIPT_SCHEMA_RELPATH = "benchmarks/preflight/canada/RECEIPT-SCHEMA-v0.1.json"
SCRIPT_RELPATH = "scripts/acquire_canada_preflight.py"

EXPECTED_STATUS_SHA256 = "4a6894ca72ae8d2efcf48b3d25f8aca3bc1e2e86b6aa6aa5b38af31a52c7fde8"
EXPECTED_SOURCE_MANIFEST_SHA256 = "c3ea6162cbeb9a5814f543ec23a02fecacad72053d90258162687ad3f48a2db2"
EXPECTED_SCHEMA_SHA256 = {
    "admission-record.schema.json": (
        "d040c4c86794268e26d9dd833ecd3a40347b724fbd73fb3accb3df355065f748"
    ),
    "authority-record.schema.json": (
        "f981ef4203d58c8c117566998cec03ecce669edf87b5967fa5bebd654af74d41"
    ),
    "candidate-normative-unit.schema.json": (
        "cc45ea691919f79dd29a86c3ab440ca78170add0055ef69a5e6d1de99c3b30c4"
    ),
    "control-envelope.schema.json": (
        "6e9c3ac495da0775cf9453c57ebabf7f7e4b47a44d3a667adca40543cc6f1c28"
    ),
    "institutional-ir.schema.json": (
        "d080e614212a1f8b285b558578ee0ee5927b33b534c16ee6dddae4598c7e986c"
    ),
    "runtime-evaluation.schema.json": (
        "93ef95709370866fcb1d634a36c0f9c0f048f6584d991471d255adb408827767"
    ),
    "source-anchor.schema.json": (
        "44e9a9892bb6f60534e98272d44e97f23028d9efbdca8c4ed038beb2dc1b5a36"
    ),
    "source-document.schema.json": (
        "865f128e687e9bbd46ae8fbcc807ed5610a2064703ac5961bf738cba03fa9a50"
    ),
    "source-node.schema.json": ("bc79f3e1f1449ef2f0570f6458371f621c0e6930ff71892738f5c765a35e80f2"),
}

REQUIRED_REGISTRY_FIELDS = {
    "source_id",
    "source_family_id",
    "title",
    "issuer",
    "official_english_url",
    "official_french_url",
    "french_url_absence_reason",
    "official_domain",
    "source_format",
    "expected_content_type",
    "publication_date",
    "modification_date",
    "effective_from",
    "effective_until",
    "archive_status",
    "supersedes",
    "superseded_by",
    "amendment_relationships",
    "licence_notice_url",
    "preliminary_reuse_basis",
    "third_party_material_status",
    "insignia_and_logo_status",
    "personal_information_status",
    "redistribution_status",
    "retrieval_status",
    "retrieval_timestamp",
    "HTTP_status",
    "final_URL",
    "ETag",
    "Last_Modified",
    "byte_length",
    "sha256",
    "proposed_working_set_sections",
    "estimated_print_equivalent_pages",
    "unresolved_questions",
}
UNOBSERVED_RETRIEVAL_FIELDS = {
    "retrieval_timestamp",
    "HTTP_status",
    "final_URL",
    "ETag",
    "Last_Modified",
    "byte_length",
    "sha256",
}


class AcquisitionModule(Protocol):
    ALLOWED_DOMAINS: frozenset[str]
    DEFAULT_QUARANTINE_DIR: Path
    DEFAULT_RECEIPT_DIR: Path
    AcquisitionError: type[RuntimeError]
    AllowlistRedirectHandler: type[urllib.request.HTTPRedirectHandler]

    def build_parser(self) -> argparse.ArgumentParser: ...

    def canonical_json_bytes(self, value: object) -> bytes: ...

    def source_by_id(self, source_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]: ...

    def validate_content_type(self, actual: str | None, expected: str) -> str: ...


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((repo_root / REGISTRY_RELPATH).read_text(encoding="utf-8")),
    )


@pytest.fixture(scope="module")
def acquisition(repo_root: Path) -> AcquisitionModule:
    path = repo_root / SCRIPT_RELPATH
    spec = importlib.util.spec_from_file_location("canada_acquisition_preflight", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return cast(AcquisitionModule, module)


def test_source_ids_are_unique(registry: dict[str, Any]) -> None:
    source_ids = [source["source_id"] for source in registry["sources"]]
    assert len(source_ids) == len(set(source_ids))


def test_english_urls_are_https_and_allowlisted(
    registry: dict[str, Any], acquisition: AcquisitionModule
) -> None:
    for source in registry["sources"]:
        parsed = urlparse(source["official_english_url"])
        assert parsed.scheme == "https"
        assert parsed.hostname == source["official_domain"]
        assert parsed.hostname in acquisition.ALLOWED_DOMAINS


def test_domain_allowlist_is_derived_only_from_registry(
    registry: dict[str, Any], acquisition: AcquisitionModule
) -> None:
    registry_domains = {
        urlparse(url).hostname
        for source in registry["sources"]
        for url in (source["official_english_url"], source["official_french_url"])
        if url is not None
    }
    assert registry_domains == acquisition.ALLOWED_DOMAINS


def test_every_record_has_french_counterpart_field(registry: dict[str, Any]) -> None:
    for source in registry["sources"]:
        assert "official_french_url" in source
        if source["official_french_url"] is None:
            assert source["french_url_absence_reason"]
        else:
            assert source["french_url_absence_reason"] is None
            assert urlparse(source["official_french_url"]).scheme == "https"


def test_french_counterpart_register_matches_source_ids(
    repo_root: Path, registry: dict[str, Any]
) -> None:
    counterparts = json.loads((repo_root / FRENCH_RELPATH).read_text(encoding="utf-8"))
    assert {item["source_id"] for item in counterparts["counterparts"]} == {
        source["source_id"] for source in registry["sources"]
    }


def test_ca7_is_excluded_by_default(registry: dict[str, Any]) -> None:
    assert not any(source["source_family_id"] == "CA-7" for source in registry["sources"])
    assert registry["excluded_by_default"] == [
        {
            "source_family_id": "CA-7",
            "reason": (
                "Excluded by OIC-CORPUS-DECISION-001 unless mandatory coverage remains "
                "below the 60-page ceiling"
            ),
        }
    ]


def test_proposed_working_set_is_within_ceiling(registry: dict[str, Any]) -> None:
    total = sum(source["estimated_print_equivalent_pages"] for source in registry["sources"])
    assert total == 56
    assert 30 <= total <= 60


def test_registry_fields_are_complete(registry: dict[str, Any]) -> None:
    for source in registry["sources"]:
        assert set(source) == REQUIRED_REGISTRY_FIELDS


def test_unobserved_retrieval_facts_are_null(registry: dict[str, Any]) -> None:
    for source in registry["sources"]:
        assert source["retrieval_status"] == "NOT_RETRIEVED"
        for field in UNOBSERVED_RETRIEVAL_FIELDS:
            assert source[field] is None


def test_no_fabricated_timestamp_or_digest(registry: dict[str, Any]) -> None:
    serialized = json.dumps(registry)
    assert '"retrieval_timestamp": "20' not in serialized
    assert '"sha256": "' not in serialized


def test_script_defaults_to_metadata_only(acquisition: AcquisitionModule) -> None:
    args = acquisition.build_parser().parse_args(["CA-1"])
    assert args.download is False


def test_download_requires_explicit_flag(acquisition: AcquisitionModule) -> None:
    args = acquisition.build_parser().parse_args(["CA-1"])
    assert not args.download
    args = acquisition.build_parser().parse_args(["CA-1", "--download"])
    assert args.download


def test_unknown_source_id_fails_closed(
    acquisition: AcquisitionModule, registry: dict[str, Any]
) -> None:
    with pytest.raises(acquisition.AcquisitionError, match="unknown"):
        acquisition.source_by_id("CA-UNKNOWN", registry["sources"])


def test_unexpected_content_type_fails_closed(acquisition: AcquisitionModule) -> None:
    with pytest.raises(acquisition.AcquisitionError, match="unexpected"):
        acquisition.validate_content_type("application/octet-stream", "text/html")
    with pytest.raises(acquisition.AcquisitionError, match="expected"):
        acquisition.validate_content_type("application/pdf", "text/html")


def test_unexpected_redirect_fails_closed(acquisition: AcquisitionModule) -> None:
    handler = acquisition.AllowlistRedirectHandler()
    request = urllib.request.Request("https://www.tbs-sct.canada.ca/example")
    with pytest.raises(acquisition.AcquisitionError, match="unapproved domain"):
        handler.redirect_request(
            request,
            io.BytesIO(),
            302,
            "Found",
            http.client.HTTPMessage(),
            "https://example.com/source",
        )


def test_receipts_serialize_deterministically(acquisition: AcquisitionModule) -> None:
    value_a = {"z": ["b", "a"], "a": {"d": 2, "c": 1}}
    value_b = {"a": {"c": 1, "d": 2}, "z": ["a", "b"]}
    assert acquisition.canonical_json_bytes(value_a) == acquisition.canonical_json_bytes(value_b)
    assert acquisition.canonical_json_bytes(value_a).endswith(b"\n")


def test_sample_receipt_validates_against_schema(repo_root: Path) -> None:
    schema = json.loads((repo_root / RECEIPT_SCHEMA_RELPATH).read_text(encoding="utf-8"))
    sample: dict[str, object] = {
        "actual_byte_length": None,
        "content_length_header": None,
        "content_type": "text/html",
        "downloaded": False,
        "etag": None,
        "final_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "http_status": 200,
        "last_modified": None,
        "redirect_chain": [],
        "requested_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "retrieval_utc": "2026-07-30T12:00:00Z",
        "sha256": None,
        "source_id": "CA-1",
    }
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        sample
    )


def test_local_output_directories_are_gitignored(repo_root: Path) -> None:
    for relpath in (
        ".local/canada-preflight-quarantine/example.pdf",
        ".local/canada-preflight-receipts/CA-1.receipt.json",
    ):
        result = subprocess.run(
            ["git", "check-ignore", "-q", relpath],
            cwd=repo_root,
            check=False,
        )
        assert result.returncode == 0


def test_no_source_bytes_are_tracked(repo_root: Path) -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    prohibited_suffixes = {".doc", ".docx", ".html", ".pdf", ".xml"}
    canada_paths = [
        Path(path) for path in tracked if path.startswith("benchmarks/preflight/canada/")
    ]
    assert not any(path.suffix.lower() in prohibited_suffixes for path in canada_paths)
    assert not any(path.startswith(".local/") for path in tracked)


def test_governing_files_are_byte_identical(repo_root: Path) -> None:
    assert _sha256(repo_root / "STATUS.md") == EXPECTED_STATUS_SHA256
    assert (
        _sha256(repo_root / "benchmarks/preflight/SOURCE_MANIFEST.csv")
        == EXPECTED_SOURCE_MANIFEST_SHA256
    )
    schema_dir = repo_root / "schemas/draft"
    assert {path.name: _sha256(path) for path in sorted(schema_dir.glob("*.json"))} == (
        EXPECTED_SCHEMA_SHA256
    )


def test_no_semantic_artifact_types_are_created(repo_root: Path) -> None:
    changed = set(
        subprocess.run(
            ["git", "diff", "--name-only", "37d6fa4dd12f7f26c632169611b13c251bbec14a...HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    prohibited_fragments = {
        "candidate-normative",
        "control-envelope",
        "institutional-ir",
        "runtime-evaluation",
    }
    assert not any(fragment in path for path in changed for fragment in prohibited_fragments)


def test_script_has_no_prohibited_integration_imports(repo_root: Path) -> None:
    tree = ast.parse((repo_root / SCRIPT_RELPATH).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0].lower())
    assert imported.isdisjoint(
        {"anthropic", "browser", "langchain", "openai", "opa", "playwright", "veip", "ztl"}
    )
