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
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
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
RIGHTS_RELPATH = "benchmarks/preflight/canada/RIGHTS-PREFLIGHT-v0.1.md"
SCOPE_RELPATH = "benchmarks/preflight/canada/WORKING-SET-SCOPE-v0.1.md"
SCRIPT_RELPATH = "scripts/acquire_canada_preflight.py"
OBSERVATIONS_RELPATH = "benchmarks/preflight/canada/PREFLIGHT-HTTP-OBSERVATIONS-v0.1.json"
RESOLUTION_RELPATH = "benchmarks/preflight/canada/OFFICIAL-SOURCE-RESOLUTION-v0.1.md"
CLOSURE_SUMMARY_RELPATH = "benchmarks/preflight/canada/PREFLIGHT-CLOSURE-SUMMARY-v0.1.json"

EXPECTED_STATUS_SHA256 = "2cc1600a91a0966c42c42d5c9bcd37cf5a3e3638bf324a97e67f53db3c2a38e2"
# Repinned when the Canada rights freeze added the CA-3 row. The preflight PR left the
# manifest header-only at c3ea6162cbeb9a5814f543ec23a02fecacad72053d90258162687ad3f48a2db2.
EXPECTED_SOURCE_MANIFEST_SHA256 = "c175d96d3f211feb77bf9d020a17a3e2f01cb0f8d6da9946c8e8526d98c66a1b"
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
    "acquisition_target",
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
    MAX_DOWNLOAD_BYTES: int
    AcquisitionError: type[RuntimeError]
    AllowlistRedirectHandler: type[urllib.request.HTTPRedirectHandler]

    def build_parser(self) -> argparse.ArgumentParser: ...

    def acquisition_target(self, source: Mapping[str, Any]) -> tuple[str, str, str]: ...

    def acquire_one(
        self,
        source: Mapping[str, Any],
        *,
        download: bool,
        receipt_path: Path,
        quarantine_path: Path,
        expected_digest: str | None,
        opener: object | None = None,
        clock: Callable[[], datetime] = ...,
        quarantine_writer: Callable[
            [Readable, Path, int | None, str | None], tuple[int, str]
        ] = ...,
        receipt_writer: Callable[[Path, bytes], None] = ...,
    ) -> dict[str, object]: ...

    def atomic_write_bytes(self, path: Path, data: bytes) -> None: ...

    def canonical_json_bytes(self, value: object) -> bytes: ...

    def expected_digests(self, items: Sequence[str], *, download: bool) -> dict[str, str]: ...

    def make_receipt(
        self,
        *,
        source_id: str,
        acquisition_target_role: str,
        acquisition_target_url: str,
        registry_source_url: str,
        requested_url: str,
        final_url: str,
        redirects: Sequence[str],
        status: int,
        headers: Mapping[str, str],
        content_type: str,
        downloaded: bool,
        actual_byte_length: int | None,
        digest: str | None,
        retrieved_at: str,
    ) -> dict[str, object]: ...

    def source_by_id(self, source_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]: ...

    def source_paths(
        self,
        sources: Sequence[Mapping[str, Any]],
        receipt_dir: Path,
        quarantine_dir: Path,
    ) -> dict[str, tuple[Path, Path]]: ...

    def stream_to_quarantine(
        self,
        response: io.BytesIO,
        target: Path,
        content_length: int | None,
        expected_digest: str | None,
        *,
        max_bytes: int,
    ) -> tuple[int, str]: ...

    def validate_selection(
        self,
        source_ids: Sequence[str],
        sources: Sequence[Mapping[str, Any]],
        expected: Mapping[str, str],
    ) -> list[Mapping[str, Any]]: ...

    def validate_content_type(self, actual: str | None, expected: str) -> str: ...


class FakeResponse(io.BytesIO):
    """Small context-managed response that records body-read attempts."""

    def __init__(
        self,
        payload: bytes,
        *,
        url: str = "https://www.tbs-sct.canada.ca/example",
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(payload)
        self.status = 200
        self.headers = dict(headers or {"Content-Type": "text/html"})
        self._url = url
        self.read_calls = 0

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return self._url

    def read(self, size: int | None = -1) -> bytes:
        self.read_calls += 1
        return super().read(size)


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requested_url: str | None = None

    def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
        del timeout
        self.requested_url = request.full_url
        return self.response


class Readable(Protocol):
    def read(self, size: int | None = -1) -> bytes: ...


def _source() -> dict[str, object]:
    return {
        "source_id": "CA-1",
        "official_english_url": "https://www.tbs-sct.canada.ca/example",
        "expected_content_type": "text/html",
        "acquisition_target": {
            "url": "https://www.tbs-sct.canada.ca/example",
            "expected_content_type": "text/html",
            "role": "CURRENT_SOURCE_UNIT",
        },
    }


def _fixed_clock() -> datetime:
    return datetime(2026, 7, 30, 16, 0, tzinfo=UTC)


def _sample_receipt(
    acquisition: AcquisitionModule,
    *,
    redirects: Sequence[str] = (),
    downloaded: bool = False,
    actual_byte_length: int | None = None,
    digest: str | None = None,
) -> dict[str, object]:
    return acquisition.make_receipt(
        source_id="CA-1",
        acquisition_target_role="CURRENT_SOURCE_UNIT",
        acquisition_target_url="https://www.tbs-sct.canada.ca/start",
        registry_source_url="https://www.tbs-sct.canada.ca/start",
        requested_url="https://www.tbs-sct.canada.ca/start",
        final_url="https://www.tbs-sct.canada.ca/final",
        redirects=redirects,
        status=200,
        headers={"Content-Type": "text/html"},
        content_type="text/html",
        downloaded=downloaded,
        actual_byte_length=actual_byte_length,
        digest=digest,
        retrieved_at="2026-07-30T16:00:00Z",
    )


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
    assert total == 55
    assert 30 <= total <= 60


def test_registry_fields_are_complete(registry: dict[str, Any]) -> None:
    for source in registry["sources"]:
        assert set(source) >= REQUIRED_REGISTRY_FIELDS


def test_all_eleven_sources_have_explicit_acquisition_targets(
    registry: dict[str, Any], acquisition: AcquisitionModule
) -> None:
    assert len(registry["sources"]) == 11
    assert {source["source_id"] for source in registry["sources"]} == {
        "CA-1",
        "CA-2",
        "CA-3",
        "CA-4",
        "CA-5-APPROVALS",
        "CA-5-DELEGATION",
        "CA-5-LIMITS",
        "CA-5-SIGNING",
        "CA-6-ARCHIVE",
        "CA-6-CH6",
        "CA-6-GLOSSARY",
    }
    for source in registry["sources"]:
        target = source["acquisition_target"]
        assert set(target) == {"url", "expected_content_type", "role"}
        assert acquisition.acquisition_target(source) == (
            target["url"],
            target["expected_content_type"],
            target["role"],
        )


def test_ca3_has_exactly_one_xml_canonical_artifact(registry: dict[str, Any]) -> None:
    ca3 = next(source for source in registry["sources"] if source["source_id"] == "CA-3")
    canonical = ca3["canonical_artifact"]
    assert canonical["format"] == "XML"
    assert canonical["hashing_role"] == "CANONICAL_IF_LATER_ACQUISITION_AUTHORIZED"
    assert canonical["english_url"].endswith("/eng/XML/SOR-87-402.xml")
    assert canonical["french_url"].endswith("/fra/XML/DORS-87-402.xml")
    assert not isinstance(canonical, list)
    assert ca3["acquisition_target"] == {
        "url": "https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
        "expected_content_type": "text/xml",
        "role": "CANONICAL_ARTIFACT",
    }


def test_ca3_pdf_is_secondary_and_language_renderings_share_authority(
    registry: dict[str, Any],
) -> None:
    ca3 = next(source for source in registry["sources"] if source["source_id"] == "CA-3")
    assert ca3["canonical_artifact"]["language_renderings_are_separate_authorities"] is False
    assert ca3["alternate_official_renderings"] == [
        {
            "format": "PDF",
            "language": "BILINGUAL",
            "role": "SECONDARY_HUMAN_REVIEW_ONLY",
            "url": "https://laws-lois.justice.gc.ca/PDF/SOR-87-402.pdf",
            "observed_content_type": "application/pdf",
        }
    ]
    assert ca3["alternate_official_renderings"][0]["url"] != ca3["acquisition_target"]["url"]
    all_target_urls = [source["acquisition_target"]["url"] for source in registry["sources"]]
    assert all_target_urls.count(ca3["acquisition_target"]["url"]) == 1


def test_resolved_french_urls_are_https_and_allowlisted(
    repo_root: Path, acquisition: AcquisitionModule
) -> None:
    counterparts = json.loads((repo_root / FRENCH_RELPATH).read_text(encoding="utf-8"))
    for item in counterparts["counterparts"]:
        url = item["official_french_url"]
        if url is not None:
            parsed = urlparse(url)
            assert parsed.scheme == "https"
            assert parsed.hostname in acquisition.ALLOWED_DOMAINS


def test_unresolved_french_urls_retain_reason(repo_root: Path) -> None:
    counterparts = json.loads((repo_root / FRENCH_RELPATH).read_text(encoding="utf-8"))
    for item in counterparts["counterparts"]:
        if item["official_french_url"] is None:
            assert item["absence_reason"]
            assert item["status"] == "UNRESOLVED"


def test_all_french_counterpart_records_are_resolved(repo_root: Path) -> None:
    counterparts = json.loads((repo_root / FRENCH_RELPATH).read_text(encoding="utf-8"))
    assert len(counterparts["counterparts"]) == 11
    resolved_statuses = {
        "CONFIRMED_OFFICIAL_URL",
        "CONFIRMED_OFFICIAL_LANGUAGE_LINK",
    }
    assert all(item["status"] in resolved_statuses for item in counterparts["counterparts"])
    assert all(item["official_french_url"] for item in counterparts["counterparts"])


def test_ca6_nodes_are_explicitly_enumerated(repo_root: Path) -> None:
    scope = (repo_root / SCOPE_RELPATH).read_text(encoding="utf-8")
    node_ids = {
        "CA-6-ARCHIVE-NOTICE",
        "CA-6-6.1",
        "CA-6-6.5",
        "CA-6-6.5.5.5",
        "CA-6-6.5.5.10",
        "CA-6-6.5.20",
        "CA-6-6.20",
    }
    assert all(f"| {node_id} |" in scope for node_id in node_ids)
    assert sum(f"| {node_id} |" in scope for node_id in node_ids) == 7


def test_selected_glossary_terms_are_directly_referenced(
    registry: dict[str, Any],
) -> None:
    glossary = next(
        source for source in registry["sources"] if source["source_id"] == "CA-6-GLOSSARY"
    )
    selected_terms = glossary["selected_glossary_entries"]
    referenced_terms: set[str] = set()
    assert set(selected_terms) <= referenced_terms
    assert selected_terms == []


def test_rights_classifications_use_only_preliminary_vocabulary(repo_root: Path) -> None:
    allowed = {
        "PRELIMINARY_CLEAR",
        "PRELIMINARY_RESTRICTED",
        "NOT_APPLICABLE",
        "NOT_FOUND",
        "UNRESOLVED",
    }
    rights = (repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8")
    classification_rows = [
        line
        for line in rights.splitlines()
        if line.startswith("| CA-") and "Source units" not in line
    ]
    assert classification_rows
    for row in classification_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert set(cells[1:]) <= allowed


def test_no_source_is_marked_legally_cleared_or_redistributable(repo_root: Path) -> None:
    rights = (repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8")
    assert "| CLEARED |" not in rights
    assert "| APPROVED |" not in rights
    assert "| LEGALLY_PERMITTED |" not in rights
    assert "| REDISTRIBUTABLE |" not in rights


def test_acquisition_freeze_fields_remain_null_despite_metadata_only_preflight_observations(
    registry: dict[str, Any],
) -> None:
    assert registry["preflight_http_observation_status"] == "OBSERVED_METADATA_ONLY"
    assert registry["acquisition_freeze_status"] == "NOT_PERFORMED"
    for source in registry["sources"]:
        assert source["retrieval_status"] == "NOT_RETRIEVED"
        for field in UNOBSERVED_RETRIEVAL_FIELDS:
            assert source[field] is None


def test_no_fabricated_timestamp_or_digest(registry: dict[str, Any]) -> None:
    serialized = json.dumps(registry)
    assert '"retrieval_timestamp": "20' not in serialized
    assert '"sha256": "' not in serialized


def test_committed_observation_ledger_matches_registry(
    repo_root: Path, registry: dict[str, Any]
) -> None:
    ledger = json.loads((repo_root / OBSERVATIONS_RELPATH).read_text(encoding="utf-8"))
    observations = ledger["observations"]
    assert ledger["observation_set_status"] == "METADATA_ONLY_PREFLIGHT_OBSERVATION"
    assert ledger["source_count"] == len(observations) == 11
    assert ledger["no_source_bytes_observed"] is True
    assert ledger["acquisition_freeze_performed"] is False
    assert ledger["source_registry_sha256"] == _sha256(repo_root / REGISTRY_RELPATH)
    assert ledger["acquisition_script_sha256"] == _sha256(repo_root / SCRIPT_RELPATH)
    assert {item["source_id"] for item in observations} == {
        source["source_id"] for source in registry["sources"]
    }
    by_id = {source["source_id"]: source for source in registry["sources"]}
    for item in observations:
        source = by_id[item["source_id"]]
        assert item["registry_source_url"] == source["official_english_url"]
        assert item["acquisition_target_url"] == source["acquisition_target"]["url"]
        assert item["downloaded"] is False
        assert set(item).isdisjoint(
            {"source_bytes", "body", "body_sha256", "sha256", "actual_byte_length"}
        )


def test_observation_ledger_can_be_regenerated_from_local_receipts_when_available(
    repo_root: Path, registry: dict[str, Any]
) -> None:
    receipt_dir = repo_root / ".local/canada-preflight-receipts"
    if not receipt_dir.exists():
        pytest.skip("gitignored local receipts are intentionally unavailable in CI")
    ledger = json.loads((repo_root / OBSERVATIONS_RELPATH).read_text(encoding="utf-8"))
    observed = {item["source_id"]: item for item in ledger["observations"]}
    by_id = {source["source_id"]: source for source in registry["sources"]}
    receipt_paths = sorted(receipt_dir.glob("*.receipt.json"))
    assert len(receipt_paths) == 11
    for path in receipt_paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        item = observed[receipt["source_id"]]
        source = by_id[receipt["source_id"]]
        expected = {
            "source_id": receipt["source_id"],
            "registry_source_url": source["official_english_url"],
            "acquisition_target_url": source["acquisition_target"]["url"],
            "requested_url": receipt["requested_url"],
            "final_url": receipt["final_url"],
            "redirect_chain": receipt["redirect_chain"],
            "http_status": receipt["http_status"],
            "content_type": receipt["content_type"],
            "etag": receipt["etag"],
            "last_modified": receipt["last_modified"],
            "observation_utc": receipt["retrieval_utc"],
            "downloaded": False,
            "local_receipt_sha256": _sha256(path),
        }
        assert item == expected


def test_closure_evidence_surfaces_are_consistent(
    repo_root: Path, registry: dict[str, Any]
) -> None:
    summary = json.loads((repo_root / CLOSURE_SUMMARY_RELPATH).read_text(encoding="utf-8"))
    ledger = json.loads((repo_root / OBSERVATIONS_RELPATH).read_text(encoding="utf-8"))
    scope = (repo_root / SCOPE_RELPATH).read_text(encoding="utf-8")
    resolution = (repo_root / RESOLUTION_RELPATH).read_text(encoding="utf-8")
    rights = (repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8")
    assert summary["working_set_print_equivalent_pages"] == 55
    assert sum(source["estimated_print_equivalent_pages"] for source in registry["sources"]) == 55
    assert "**55**" in scope
    assert "revised total is 55" in resolution
    assert summary["ca6_selected_node_count"] == 7
    assert "Seven proposed nodes" in resolution
    assert summary["retained_glossary_entry_count"] == 0
    assert "Selected glossary entries: **0**" in scope
    assert "Therefore zero" in resolution
    assert summary["metadata_only_observation_count"] == ledger["source_count"] == 11
    assert summary["source_bytes_acquired"] is False
    assert summary["acquisition_freeze_performed"] is False
    assert summary["rights_review_status"] == "PRELIMINARY_AND_INCOMPLETE"
    assert "no acquisition freeze was performed" in rights
    assert summary["blocking_pull_request"] == 15
    assert summary["semantic_implementation_gate"] == "BLOCKED"


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


def test_object_key_order_does_not_change_canonical_bytes(
    acquisition: AcquisitionModule,
) -> None:
    value_a = {"z": [1, 2], "a": {"d": 2, "c": 1}}
    value_b = {"a": {"c": 1, "d": 2}, "z": [1, 2]}
    assert acquisition.canonical_json_bytes(value_a) == acquisition.canonical_json_bytes(value_b)


def test_array_order_changes_canonical_bytes(acquisition: AcquisitionModule) -> None:
    assert acquisition.canonical_json_bytes(["b", "a"]) != acquisition.canonical_json_bytes(
        ["a", "b"]
    )


def test_redirect_handler_preserves_multiple_hops(acquisition: AcquisitionModule) -> None:
    handler = acquisition.AllowlistRedirectHandler()
    request = urllib.request.Request("https://www.tbs-sct.canada.ca/start")
    hops = [
        "https://www.tbs-sct.canada.ca/intermediate",
        "https://canadabuys.canada.ca/final",
    ]
    for hop in hops:
        handler.redirect_request(
            request,
            io.BytesIO(),
            302,
            "Found",
            http.client.HTTPMessage(),
            hop,
        )
    assert cast(Any, handler).chain == hops


def test_receipt_redirect_order_changes_canonical_bytes(
    acquisition: AcquisitionModule,
) -> None:
    first = _sample_receipt(acquisition, redirects=["https://a.invalid", "https://b.invalid"])
    second = _sample_receipt(acquisition, redirects=["https://b.invalid", "https://a.invalid"])
    assert acquisition.canonical_json_bytes(first) != acquisition.canonical_json_bytes(second)


def test_repeated_receipt_serialization_is_byte_identical(
    acquisition: AcquisitionModule,
) -> None:
    receipt = _sample_receipt(
        acquisition,
        redirects=[
            "https://www.tbs-sct.canada.ca/one",
            "https://canadabuys.canada.ca/two",
        ],
    )
    first = acquisition.canonical_json_bytes(receipt)
    assert first == acquisition.canonical_json_bytes(receipt)
    assert first.endswith(b"\n")


def test_sample_receipt_validates_against_schema(repo_root: Path) -> None:
    schema = json.loads((repo_root / RECEIPT_SCHEMA_RELPATH).read_text(encoding="utf-8"))
    sample: dict[str, object] = {
        "acquisition_target_role": "CURRENT_SOURCE_UNIT",
        "acquisition_target_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "actual_byte_length": None,
        "content_length_header": None,
        "content_type": "text/html",
        "downloaded": False,
        "etag": None,
        "final_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "http_status": 200,
        "last_modified": None,
        "redirect_chain": [],
        "registry_source_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "requested_url": "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32692",
        "retrieval_utc": "2026-07-30T12:00:00Z",
        "sha256": None,
        "source_id": "CA-1",
    }
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        sample
    )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"downloaded": False, "sha256": "a" * 64}, "not of type 'null'"),
        (
            {"downloaded": True, "actual_byte_length": 1, "sha256": None},
            "is not of type 'string'",
        ),
        ({"downloaded": True, "actual_byte_length": None, "sha256": "a" * 64}, "integer"),
        (
            {"downloaded": False, "actual_byte_length": 1, "sha256": None},
            "not of type 'null'",
        ),
    ],
)
def test_receipt_cross_field_invariants(
    repo_root: Path, updates: dict[str, object], message: str
) -> None:
    schema = json.loads((repo_root / RECEIPT_SCHEMA_RELPATH).read_text(encoding="utf-8"))
    receipt: dict[str, object] = {
        "acquisition_target_role": "CURRENT_SOURCE_UNIT",
        "acquisition_target_url": "https://www.tbs-sct.canada.ca/start",
        "actual_byte_length": None,
        "content_length_header": None,
        "content_type": "text/html",
        "downloaded": False,
        "etag": None,
        "final_url": "https://www.tbs-sct.canada.ca/final",
        "http_status": 200,
        "last_modified": None,
        "redirect_chain": [],
        "registry_source_url": "https://www.tbs-sct.canada.ca/start",
        "requested_url": "https://www.tbs-sct.canada.ca/start",
        "retrieval_utc": "2026-07-30T16:00:00Z",
        "sha256": None,
        "source_id": "CA-1",
    }
    receipt.update(updates)
    with pytest.raises(jsonschema.ValidationError, match=message):
        jsonschema.Draft202012Validator(schema).validate(receipt)


def test_max_download_size_is_64_mib(acquisition: AcquisitionModule) -> None:
    assert acquisition.MAX_DOWNLOAD_BYTES == 64 * 1024 * 1024


def test_declared_content_length_above_limit_fails_before_read(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    response = FakeResponse(b"body")
    target = tmp_path / "source.source"
    with pytest.raises(acquisition.AcquisitionError, match="Content-Length"):
        acquisition.stream_to_quarantine(
            response,
            target,
            9,
            None,
            max_bytes=8,
        )
    assert response.read_calls == 0
    assert not target.exists()


def test_streamed_overflow_without_content_length_cleans_partial_file(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    target = tmp_path / "source.source"
    with pytest.raises(acquisition.AcquisitionError, match="maximum"):
        acquisition.stream_to_quarantine(
            io.BytesIO(b"123456789"),
            target,
            None,
            None,
            max_bytes=8,
        )
    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))
    assert not list(tmp_path.glob(".*.part"))


def test_exact_download_limit_succeeds(acquisition: AcquisitionModule, tmp_path: Path) -> None:
    payload = b"12345678"
    target = tmp_path / "source.source"
    length, digest = acquisition.stream_to_quarantine(
        io.BytesIO(payload),
        target,
        None,
        None,
        max_bytes=len(payload),
    )
    assert length == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert target.read_bytes() == payload


def test_existing_different_quarantine_artifact_fails_closed(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    target = tmp_path / "source.source"
    target.write_bytes(b"old")
    with pytest.raises(acquisition.AcquisitionError, match="overwrite prohibited"):
        acquisition.stream_to_quarantine(
            io.BytesIO(b"new"),
            target,
            3,
            None,
            max_bytes=8,
        )
    assert target.read_bytes() == b"old"
    assert not list(tmp_path.glob(".*.part"))


def test_existing_identical_quarantine_artifact_is_reused(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    payload = b"same"
    target = tmp_path / "source.source"
    target.write_bytes(payload)
    length, digest = acquisition.stream_to_quarantine(
        io.BytesIO(payload),
        target,
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        max_bytes=8,
    )
    assert (length, digest) == (len(payload), hashlib.sha256(payload).hexdigest())
    assert target.read_bytes() == payload
    assert not list(tmp_path.glob(".*.part"))


def test_metadata_only_does_not_read_body_and_uses_injected_clock(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    response = FakeResponse(b"must-not-be-read")
    receipt_path = tmp_path / "receipt.json"
    quarantine_path = tmp_path / "source.source"
    receipt = acquisition.acquire_one(
        _source(),
        download=False,
        receipt_path=receipt_path,
        quarantine_path=quarantine_path,
        expected_digest=None,
        opener=FakeOpener(response),
        clock=_fixed_clock,
    )
    assert response.read_calls == 0
    assert receipt["retrieval_utc"] == "2026-07-30T16:00:00Z"
    assert receipt["downloaded"] is False
    assert receipt["acquisition_target_role"] == "CURRENT_SOURCE_UNIT"
    assert receipt["registry_source_url"] == _source()["official_english_url"]
    assert receipt["acquisition_target_url"] == "https://www.tbs-sct.canada.ca/example"
    assert receipt_path.exists()
    assert not quarantine_path.exists()


def test_quarantine_write_failure_leaves_no_receipt_or_part(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    receipt_path = tmp_path / "receipt.json"
    quarantine_path = tmp_path / "source.source"

    def fail_quarantine(
        response: Readable,
        target: Path,
        content_length: int | None,
        expected_digest: str | None,
    ) -> tuple[int, str]:
        del response, target, content_length, expected_digest
        raise OSError("injected quarantine failure")

    with pytest.raises(OSError, match="injected"):
        acquisition.acquire_one(
            _source(),
            download=True,
            receipt_path=receipt_path,
            quarantine_path=quarantine_path,
            expected_digest=None,
            opener=FakeOpener(FakeResponse(b"payload")),
            clock=_fixed_clock,
            quarantine_writer=fail_quarantine,
        )
    assert not receipt_path.exists()
    assert not quarantine_path.exists()
    assert not list(tmp_path.glob(".*.part"))


def test_receipt_write_failure_creates_no_false_successful_receipt(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    receipt_path = tmp_path / "receipt.json"
    quarantine_path = tmp_path / "source.source"

    def fail_receipt(path: Path, data: bytes) -> None:
        del path, data
        raise OSError("injected receipt failure")

    with pytest.raises(OSError, match="injected"):
        acquisition.acquire_one(
            _source(),
            download=True,
            receipt_path=receipt_path,
            quarantine_path=quarantine_path,
            expected_digest=None,
            opener=FakeOpener(FakeResponse(b"payload")),
            clock=_fixed_clock,
            receipt_writer=fail_receipt,
        )
    assert quarantine_path.read_bytes() == b"payload"
    assert not receipt_path.exists()
    assert not list(tmp_path.glob(".*.part"))


def test_atomic_receipt_failure_cleans_part_file(
    acquisition: AcquisitionModule, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "receipt.json"

    def fail_replace(source: Path, destination: Path) -> Path:
        del source, destination
        raise OSError("injected replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        acquisition.atomic_write_bytes(target, b"{}")
    assert not target.exists()
    assert not list(tmp_path.glob(".*.part"))


def test_duplicate_source_ids_fail_closed(
    acquisition: AcquisitionModule, registry: dict[str, Any]
) -> None:
    with pytest.raises(acquisition.AcquisitionError, match="duplicate source IDs"):
        acquisition.validate_selection(["CA-1", "CA-1"], registry["sources"], {})


def test_digest_for_unselected_source_fails_closed(
    acquisition: AcquisitionModule, registry: dict[str, Any]
) -> None:
    with pytest.raises(acquisition.AcquisitionError, match="unselected"):
        acquisition.validate_selection(["CA-1"], registry["sources"], {"CA-2": "a" * 64})


def test_digest_for_unknown_source_fails_closed(
    acquisition: AcquisitionModule, registry: dict[str, Any]
) -> None:
    with pytest.raises(acquisition.AcquisitionError, match="unknown source"):
        acquisition.validate_selection(["CA-1"], registry["sources"], {"CA-UNKNOWN": "a" * 64})


def test_multiple_operations_targeting_same_final_path_fail_closed(
    acquisition: AcquisitionModule, tmp_path: Path
) -> None:
    duplicate_sources = [
        {"source_id": "CA-1", "acquisition_target": _source()["acquisition_target"]},
        {"source_id": "CA-1", "acquisition_target": _source()["acquisition_target"]},
    ]
    with pytest.raises(acquisition.AcquisitionError, match="multiple operations"):
        acquisition.source_paths(
            duplicate_sources,
            tmp_path / "receipts",
            tmp_path / "quarantine",
        )


@pytest.mark.parametrize(
    "target",
    [
        None,
        {},
        {"url": "https://www.tbs-sct.canada.ca/example"},
        {
            "url": "https://www.tbs-sct.canada.ca/example",
            "expected_content_type": "text/html",
            "role": "UNKNOWN",
        },
        {
            "url": "https://example.com/source",
            "expected_content_type": "text/html",
            "role": "CURRENT_SOURCE_UNIT",
        },
    ],
)
def test_missing_or_malformed_acquisition_target_fails_closed(
    acquisition: AcquisitionModule, target: object
) -> None:
    source = _source()
    if target is None:
        source.pop("acquisition_target")
    else:
        source["acquisition_target"] = target
    with pytest.raises(acquisition.AcquisitionError):
        acquisition.acquisition_target(source)


def test_ca3_requests_xml_target_not_html_index(
    acquisition: AcquisitionModule, registry: dict[str, Any], tmp_path: Path
) -> None:
    ca3 = next(source for source in registry["sources"] if source["source_id"] == "CA-3")
    xml_url = "https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml"
    opener = FakeOpener(
        FakeResponse(b"not-read", url=xml_url, headers={"Content-Type": "text/xml"})
    )
    receipt = acquisition.acquire_one(
        ca3,
        download=False,
        receipt_path=tmp_path / "CA-3.receipt.json",
        quarantine_path=tmp_path / "CA-3.source",
        expected_digest=None,
        opener=opener,
        clock=_fixed_clock,
    )
    assert opener.requested_url == xml_url
    assert opener.requested_url != ca3["official_english_url"]
    assert receipt["content_type"] == "text/xml"


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
