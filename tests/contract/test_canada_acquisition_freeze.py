"""Fail-closed contract tests for the Canada exact-byte acquisition freeze."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

# urllib.request is imported eagerly so the freeze modules load cleanly under pytest.
_ = urllib.request

pytestmark = pytest.mark.contract

FREEZE_RELDIR = "benchmarks/corpus/canada/freeze-v0.1"
INDEX_RELPATH = f"{FREEZE_RELDIR}/INDEX.json"
FREEZE_RELPATH = f"{FREEZE_RELDIR}/ACQUISITION-FREEZE-v0.1.json"
FREEZE_MD_RELPATH = f"{FREEZE_RELDIR}/ACQUISITION-FREEZE-v0.1.md"
RIGHTS_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.json"
SHA256SUMS_RELPATH = f"{FREEZE_RELDIR}/SHA256SUMS"
SHA512SUMS_RELPATH = f"{FREEZE_RELDIR}/SHA512SUMS"
MANIFEST_RELPATH = "benchmarks/preflight/SOURCE_MANIFEST.csv"

CA3_XML_URL = "https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml"
CA3_INDEX_URL = "https://laws-lois.justice.gc.ca/eng/regulations/sor-87-402/index.html"
CA3_PDF_URL = "https://laws-lois.justice.gc.ca/PDF/SOR-87-402.pdf"

MINIMAL_XML = b'<?xml version="1.0"?><Regulation/>'
HTML_ERROR_PAGE = b"<!DOCTYPE html><html><head><title>Error</title></head><body>404</body></html>"


def _load(repo_root: Path, name: str) -> ModuleType:
    path = repo_root / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def freezer(repo_root: Path) -> ModuleType:
    return _load(repo_root, "freeze_canada_corpus")


@pytest.fixture(scope="module")
def verifier(repo_root: Path) -> ModuleType:
    return _load(repo_root, "verify_canada_freeze")


@pytest.fixture(scope="module")
def index(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / INDEX_RELPATH).read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def rights(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def freeze_record(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", json.loads((repo_root / FREEZE_RELPATH).read_text(encoding="utf-8"))
    )


class FakeResponse(io.BytesIO):
    """A minimal urllib response stand-in that performs no network I/O."""

    def __init__(self, body: bytes, url: str, headers: Mapping[str, str]) -> None:
        super().__init__(body)
        self.status = 200
        self.headers = dict(headers)
        self._url = url

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakeOpener:
    """Records the single URL that was requested."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requested_url: str | None = None

    def open(self, request: urllib.request.Request, timeout: int) -> FakeResponse:
        self.requested_url = request.full_url
        return self.response


def _ca3_record(rights: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(
        next(record for record in rights["records"] if record["source_id"] == "CA-3")
    )


# --------------------------------------------------------------------------
# Freeze package integrity
# --------------------------------------------------------------------------


def test_offline_verification_passes(repo_root: Path, verifier: ModuleType) -> None:
    assert verifier.verify(repo_root / FREEZE_RELDIR) == []


def test_every_index_entry_binds_the_full_required_provenance(index: dict[str, Any]) -> None:
    required = (
        "acquisition_target_url",
        "byte_length",
        "content_type",
        "final_url",
        "receipt_id",
        "receipt_path",
        "retrieval_utc",
        "rights_disposition",
        "sha256",
        "sha512",
        "source_id",
        "storage_classification",
    )
    assert index["entries"]
    for entry in index["entries"]:
        for field in required:
            assert entry.get(field) not in (None, ""), f"{entry['source_id']} missing {field}"


def test_committed_bytes_match_every_receipt_and_both_hash_ledgers(
    repo_root: Path, index: dict[str, Any]
) -> None:
    sha256_lines = (repo_root / SHA256SUMS_RELPATH).read_text(encoding="utf-8").splitlines()
    sha512_lines = (repo_root / SHA512SUMS_RELPATH).read_text(encoding="utf-8").splitlines()
    committed = [
        entry
        for entry in index["entries"]
        if entry["storage_classification"] == "REPOSITORY_FROZEN"
    ]
    assert committed
    for entry in committed:
        data = (repo_root / FREEZE_RELDIR / entry["frozen_bytes_path"]).read_bytes()
        assert len(data) == entry["byte_length"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert hashlib.sha512(data).hexdigest() == entry["sha512"]
        receipt = json.loads(
            (repo_root / FREEZE_RELDIR / entry["receipt_path"]).read_text(encoding="utf-8")
        )
        assert receipt["sha256"] == entry["sha256"]
        assert receipt["sha512"] == entry["sha512"]
        assert f"{entry['sha256']}  {entry['frozen_bytes_path']}" in sha256_lines
        assert f"{entry['sha512']}  {entry['frozen_bytes_path']}" in sha512_lines


def test_blocked_sources_were_never_downloaded(
    repo_root: Path, rights: dict[str, Any], index: dict[str, Any]
) -> None:
    blocked = {
        record["source_id"]
        for record in rights["records"]
        if record["reviewer_disposition"] == "BLOCKED_PENDING_CLEARANCE"
    }
    assert blocked
    entry_ids = {entry["source_id"] for entry in index["entries"]}
    assert blocked.isdisjoint(entry_ids)
    assert set(index["blocked_source_ids"]) == blocked
    for source_id in blocked:
        assert not (repo_root / FREEZE_RELDIR / "receipts" / f"{source_id}.receipt.json").exists()
        assert not list((repo_root / FREEZE_RELDIR / "sources").glob(f"{source_id}.*"))


def test_internal_only_bytes_are_absent_from_git(repo_root: Path, index: dict[str, Any]) -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    assert not any(path.startswith(".local/") for path in tracked)
    for entry in index["entries"]:
        if entry["storage_classification"] != "INTERNAL_ONLY":
            continue
        assert entry["frozen_bytes_path"] is None
        assert not any(entry["source_id"] in path for path in tracked if "sources/" in path)


def test_committed_source_bytes_exist_only_for_repository_dispositions(
    repo_root: Path, rights: dict[str, Any]
) -> None:
    permitted = {
        record["source_id"]
        for record in rights["records"]
        if record["reviewer_disposition"] == "CLEAR_REPOSITORY_FREEZE"
    }
    present = {path.stem for path in (repo_root / FREEZE_RELDIR / "sources").iterdir()}
    assert present == permitted


def test_gitignore_covers_both_local_evidence_areas(repo_root: Path) -> None:
    for relpath in (
        ".local/canada-rights-evidence/ROBOTS-TBS.evidence",
        ".local/canada-freeze-internal/CA-1.html",
    ):
        result = subprocess.run(["git", "check-ignore", "-q", relpath], cwd=repo_root, check=False)
        assert result.returncode == 0


def test_freeze_disposition_is_partial_and_honest(
    freeze_record: dict[str, Any], index: dict[str, Any]
) -> None:
    assert freeze_record["freeze_disposition"] in {"COMPLETE", "PARTIAL", "BLOCKED"}
    assert freeze_record["freeze_disposition"] == index["freeze_disposition"]
    complete = index["blocked_source_count"] == 0
    assert (freeze_record["freeze_disposition"] == "COMPLETE") is complete
    if not complete:
        assert index["acquired_source_count"] + index["blocked_source_count"] == 11


def test_completion_cannot_be_claimed_while_any_source_is_blocked(
    freeze_record: dict[str, Any],
) -> None:
    if freeze_record["blocked_source_count"]:
        assert freeze_record["freeze_disposition"] != "COMPLETE"
    assert "not convertible to COMPLETE" in freeze_record["completion_note"]
    assert freeze_record["semantic_implementation_gate"] == "BLOCKED"


def test_generated_markdown_matches_the_canonical_json(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "tools/render_canada_freeze.py", "--check", "--root", str(repo_root)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_markdown_reports_the_same_disposition_as_the_json(
    repo_root: Path, freeze_record: dict[str, Any]
) -> None:
    markdown = (repo_root / FREEZE_MD_RELPATH).read_text(encoding="utf-8")
    assert f"**{freeze_record['freeze_disposition']}**" in markdown


# --------------------------------------------------------------------------
# Manifest discipline
# --------------------------------------------------------------------------


def test_manifest_schema_is_unchanged(repo_root: Path) -> None:
    header = (repo_root / MANIFEST_RELPATH).read_text(encoding="utf-8").splitlines()[0]
    assert header == (
        "source_id,title,issuer,source_type,official_url_or_origin,license_or_public_basis,"
        "acquired_at,sha256,effective_from,effective_until,supersedes,confidentiality,notes"
    )


def test_manifest_entries_require_an_exact_byte_receipt(
    repo_root: Path, index: dict[str, Any]
) -> None:
    import csv

    with (repo_root / MANIFEST_RELPATH).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_source = {entry["source_id"]: entry for entry in index["entries"]}
    for row in rows:
        entry = by_source.get(row["source_id"])
        assert entry is not None, f"{row['source_id']} is in the manifest with no freeze entry"
        assert entry["storage_classification"] == "REPOSITORY_FROZEN"
        assert row["sha256"] == entry["sha256"]
        assert row["acquired_at"] == entry["retrieval_utc"]
        assert row["official_url_or_origin"] == entry["acquisition_target_url"]
        receipt_path = repo_root / FREEZE_RELDIR / entry["receipt_path"]
        assert receipt_path.is_file()


def test_no_manifest_entry_exists_for_a_blocked_source(
    repo_root: Path, rights: dict[str, Any]
) -> None:
    import csv

    blocked = {
        record["source_id"]
        for record in rights["records"]
        if record["reviewer_disposition"] == "BLOCKED_PENDING_CLEARANCE"
    }
    with (repo_root / MANIFEST_RELPATH).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert blocked.isdisjoint({row["source_id"] for row in rows})


def test_metadata_only_preflight_observations_are_not_treated_as_frozen_evidence(
    repo_root: Path, index: dict[str, Any]
) -> None:
    observations = json.loads(
        (repo_root / "benchmarks/preflight/canada/PREFLIGHT-HTTP-OBSERVATIONS-v0.1.json").read_text(
            encoding="utf-8"
        )
    )
    assert observations["no_source_bytes_observed"] is True
    for observation in observations["observations"]:
        assert observation["downloaded"] is False
    # No index entry may inherit a preflight observation time or a preflight receipt digest.
    observed_times = {
        observation["observation_utc"] for observation in observations["observations"]
    }
    preflight_digests = {
        observation["local_receipt_sha256"] for observation in observations["observations"]
    }
    for entry in index["entries"]:
        assert entry["retrieval_utc"] not in observed_times
        assert entry["sha256"] not in preflight_digests


# --------------------------------------------------------------------------
# Mutation checks
# --------------------------------------------------------------------------


def test_mutation_provenance_url_fallback_fails_closed(
    rights: dict[str, Any], freezer: ModuleType
) -> None:
    record = _ca3_record(rights)
    record["acquisition_target_url"] = record["provenance_url"]
    with pytest.raises(freezer.AcquisitionError, match="provenance index"):
        freezer.acquire(record, opener=FakeOpener(FakeResponse(b"", CA3_INDEX_URL, {})))


def test_mutation_blocked_source_download_fails_closed(
    rights: dict[str, Any], freezer: ModuleType
) -> None:
    record = _ca3_record(rights)
    record["reviewer_disposition"] = "BLOCKED_PENDING_CLEARANCE"
    opener = FakeOpener(FakeResponse(MINIMAL_XML, CA3_XML_URL, {"Content-Type": "text/xml"}))
    with pytest.raises(freezer.AcquisitionError, match="never be requested"):
        freezer.acquire(record, opener=opener)
    assert opener.requested_url is None


def test_mutation_missing_rights_record_fails_the_freeze(
    repo_root: Path, verifier: ModuleType, tmp_path: Path
) -> None:
    staged = tmp_path / "freeze"
    shutil.copytree(repo_root / FREEZE_RELDIR, staged)
    rights = json.loads((staged / "RIGHTS-CLEARANCE-v0.1.json").read_text(encoding="utf-8"))
    rights["records"] = [r for r in rights["records"] if r["source_id"] != "CA-3"]
    (staged / "RIGHTS-CLEARANCE-v0.1.json").write_text(json.dumps(rights), encoding="utf-8")
    failures = verifier.verify(staged)
    assert any("no rights record" in failure for failure in failures)


def test_mutation_hash_mismatch_fails_verification(
    repo_root: Path, verifier: ModuleType, tmp_path: Path
) -> None:
    staged = tmp_path / "freeze"
    shutil.copytree(repo_root / FREEZE_RELDIR, staged)
    target = staged / "sources" / "CA-3.xml"
    target.write_bytes(target.read_bytes() + b" ")
    failures = verifier.verify(staged)
    assert any("SHA-256 mismatch" in failure for failure in failures)
    assert any("SHA-512 mismatch" in failure for failure in failures)


def test_mutation_ca3_html_substitution_fails_closed(
    rights: dict[str, Any], freezer: ModuleType
) -> None:
    record = _ca3_record(rights)
    opener = FakeOpener(FakeResponse(HTML_ERROR_PAGE, CA3_XML_URL, {"Content-Type": "text/xml"}))
    with pytest.raises(freezer.AcquisitionError, match="returned an HTML page"):
        freezer.acquire(record, opener=opener)


def test_mutation_ca3_pdf_substitution_fails_closed(
    rights: dict[str, Any], freezer: ModuleType
) -> None:
    record = _ca3_record(rights)
    opener = FakeOpener(
        FakeResponse(b"%PDF-1.7\n", CA3_PDF_URL, {"Content-Type": "application/pdf"})
    )
    with pytest.raises(freezer.AcquisitionError, match="expected Content-Type text/xml"):
        freezer.acquire(record, opener=opener)


def test_mutation_unapproved_redirect_fails_closed(freezer: ModuleType) -> None:
    handler = freezer.AllowlistRedirectHandler()
    with pytest.raises(freezer.AcquisitionError, match="unapproved domain"):
        handler.redirect_request(None, None, 302, "Found", None, "https://example.invalid/x.xml")
    assert handler.chain == []


def test_mutation_unexpected_magic_signature_fails_closed(freezer: ModuleType) -> None:
    with pytest.raises(freezer.AcquisitionError, match="did not return a PDF signature"):
        freezer.validate_magic("application/pdf", b"not a pdf", "CA-X")
    with pytest.raises(freezer.AcquisitionError, match="did not return XML"):
        freezer.validate_magic("text/xml", b"plain text body", "CA-X")
    with pytest.raises(freezer.AcquisitionError, match="not well formed"):
        freezer.validate_magic("text/xml", b"<Regulation><unclosed></Regulation>", "CA-X")


def test_mutation_ledger_disagreement_fails_verification(
    repo_root: Path, verifier: ModuleType, tmp_path: Path
) -> None:
    staged = tmp_path / "freeze"
    shutil.copytree(repo_root / FREEZE_RELDIR, staged)
    sums = staged / "SHA256SUMS"
    sums.write_text(sums.read_text(encoding="utf-8").replace("6e89", "0000"), encoding="utf-8")
    assert any("SHA256SUMS disagrees" in failure for failure in verifier.verify(staged))


def test_mutation_blocked_source_with_a_freeze_entry_fails_verification(
    repo_root: Path, verifier: ModuleType, tmp_path: Path
) -> None:
    staged = tmp_path / "freeze"
    shutil.copytree(repo_root / FREEZE_RELDIR, staged)
    index = json.loads((staged / "INDEX.json").read_text(encoding="utf-8"))
    planted = copy.deepcopy(index["entries"][0])
    planted["source_id"] = "CA-1"
    index["entries"].append(planted)
    (staged / "INDEX.json").write_text(json.dumps(index), encoding="utf-8")
    assert any(
        "blocked source has a freeze entry" in failure for failure in verifier.verify(staged)
    )


# --------------------------------------------------------------------------
# Boundary: nothing semantic was produced
# --------------------------------------------------------------------------


#: The interval this Canada work order actually covers. The upper bound was HEAD, which
#: made a completed historical proposition drift forward and turn into a permanent
#: prohibition on every later lane: any future commit touching one of these paths failed a
#: test that was only ever meant to say what this work order did NOT do. Pinning the upper
#: bound to the frozen pre-L1 repository state restores the original meaning. The forbidden
#: path set below is unchanged, and no path is exempted by name.
CANADA_FREEZE_BASE_SHA = "d99a38510e51a36972a414cadd0e44d49a04227c"
FROZEN_TERMINAL_SHA = "a59b885423b984b2eb8c20751833926b888e6b95"


def test_the_frozen_comparison_boundaries_resolve_exactly(repo_root: Path) -> None:
    """Both ends of the interval must be real commits, or the guard proves nothing."""
    for sha in (CANADA_FREEZE_BASE_SHA, FROZEN_TERMINAL_SHA):
        resolved = subprocess.run(
            ["git", "rev-parse", sha],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert resolved == sha


def test_status_and_draft_schemas_are_untouched(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{CANADA_FREEZE_BASE_SHA}...{FROZEN_TERMINAL_SHA}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "STATUS.md" not in changed
    assert not any(path.startswith("schemas/draft/") for path in changed)
    assert not any(path.startswith("docs/contracts/") for path in changed)
    assert not any(path.startswith("adapters/ztl/") for path in changed)


def test_no_semantic_artifact_was_produced(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{CANADA_FREEZE_BASE_SHA}...{FROZEN_TERMINAL_SHA}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    prohibited = (
        "candidate-normative",
        "control-envelope",
        "institutional-ir",
        "runtime-evaluation",
        "annotation",
        "rego",
    )
    assert not any(fragment in path for path in changed for fragment in prohibited)


def test_freeze_tooling_has_no_semantic_or_model_integrations(repo_root: Path) -> None:
    import ast

    for name in ("freeze_canada_corpus", "verify_canada_freeze", "capture_canada_rights_evidence"):
        tree = ast.parse((repo_root / "scripts" / f"{name}.py").read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0].lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0].lower())
        assert imported.isdisjoint(
            {"anthropic", "langchain", "openai", "opa", "playwright", "veip", "ztl"}
        )


def test_xml_use_is_structural_only(repo_root: Path) -> None:
    source = (repo_root / "scripts/freeze_canada_corpus.py").read_text(encoding="utf-8")
    # Well-formedness is the only permitted XML operation; nothing may read the tree.
    assert "ElementTree.fromstring" in source
    for forbidden in (".findall(", ".iter(", ".itertext(", ".xpath(", ".find("):
        assert forbidden not in source, f"freeze script traverses XML with {forbidden}"
