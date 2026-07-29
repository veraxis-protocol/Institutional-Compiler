"""Contract tests over this repository's own integrity manifests.

A failure here means a bootstrap-controlled artifact changed. That is a governance
event requiring authorization, not a test to relax.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.hashing import hash_file
from oic.manifests import (
    EntryStatus,
    ManifestKind,
    VerificationStatus,
    verify_all,
    verify_bootstrap_manifest,
    verify_sha256sums,
    verify_source_manifest,
)
from oic.paths import (
    BOOTSTRAP_MANIFEST_RELPATH,
    SOURCE_MANIFEST_RELPATH,
    TDD_PDF_RELPATH,
    TDD_SHA256SUMS_RELPATH,
)

pytestmark = pytest.mark.contract

#: SHA-256 of TDD-OIC-001 v1.1, as recorded in docs/tdd/SHA256SUMS and
#: BOOTSTRAP_MANIFEST.json. This value is fixed by the governing design document.
GOVERNING_TDD_SHA256 = "2a4d802130d577e4fb8fee731174ae0f2172ef2d617e3b99f068545d2b9fbf77"

#: Count of bootstrap-controlled files recorded in BOOTSTRAP_MANIFEST.json.
BOOTSTRAP_FILE_COUNT = 50


def test_tdd_checksum_matches_the_governing_value(repo_root: Path) -> None:
    assert hash_file(repo_root / TDD_PDF_RELPATH) == GOVERNING_TDD_SHA256


def test_sha256sums_records_the_governing_tdd_digest(repo_root: Path) -> None:
    text = (repo_root / TDD_SHA256SUMS_RELPATH).read_text(encoding="utf-8")
    assert GOVERNING_TDD_SHA256 in text
    report = verify_sha256sums(repo_root / TDD_SHA256SUMS_RELPATH, repo_root)
    assert report.status is VerificationStatus.PASS


def test_bootstrap_manifest_declares_the_same_tdd_digest(repo_root: Path) -> None:
    document = json.loads((repo_root / BOOTSTRAP_MANIFEST_RELPATH).read_text(encoding="utf-8"))
    assert document["governing_tdd_sha256"] == GOVERNING_TDD_SHA256


def test_bootstrap_manifest_verifies(repo_root: Path) -> None:
    report = verify_bootstrap_manifest(repo_root / BOOTSTRAP_MANIFEST_RELPATH, repo_root)
    failures = [entry.render() for entry in report.entries if entry.status is not EntryStatus.PASS]
    assert failures == []
    assert report.status is VerificationStatus.PASS


def test_bootstrap_manifest_covers_the_expected_file_count(repo_root: Path) -> None:
    document = json.loads((repo_root / BOOTSTRAP_MANIFEST_RELPATH).read_text(encoding="utf-8"))
    assert len(document["files"]) == BOOTSTRAP_FILE_COUNT


def test_preflight_source_manifest_is_reported_incomplete(repo_root: Path) -> None:
    """The corpus manifest holds only its header today.

    STATUS.md records preflight corpus provenance as OPEN. This test pins the tooling to
    that reality: an empty corpus manifest must never verify as complete or corpus-ready.
    """
    report = verify_source_manifest(repo_root / SOURCE_MANIFEST_RELPATH, repo_root)
    assert report.status is VerificationStatus.INCOMPLETE
    assert report.entries == ()
    assert any("not corpus-ready" in note for note in report.notes)


def test_verify_all_reports_expected_statuses(repo_root: Path) -> None:
    reports = {report.kind: report for report in verify_all(repo_root)}
    assert reports[ManifestKind.BOOTSTRAP].status is VerificationStatus.PASS
    assert reports[ManifestKind.SHA256SUMS].status is VerificationStatus.PASS
    assert reports[ManifestKind.SOURCE_MANIFEST].status is VerificationStatus.INCOMPLETE


def test_verification_does_not_modify_any_manifest(repo_root: Path) -> None:
    targets = [
        repo_root / BOOTSTRAP_MANIFEST_RELPATH,
        repo_root / TDD_SHA256SUMS_RELPATH,
        repo_root / SOURCE_MANIFEST_RELPATH,
    ]
    before = {path: path.read_bytes() for path in targets}
    verify_all(repo_root)
    for path in targets:
        assert path.read_bytes() == before[path], f"{path.name} was modified during verification"
