"""Contract tests over this repository's own integrity artifacts.

Two different questions live here, and conflating them was the original defect:

* the **historical baseline** - does the bootstrap commit still hold the bytes its
  manifest recorded? Verified from the Git object database, never the working tree.
* the **current-tree manifests** - do `docs/tdd/SHA256SUMS` and the preflight corpus
  manifest match the files on disk now?

A failure in the first is a governance event. A failure in the second means a present
artifact drifted. See ADR-012.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.baseline import BaselineStatus, BlobStatus, verify_bootstrap_baseline
from oic.errors import ConfigurationError
from oic.hashing import hash_file
from oic.manifests import (
    EntryStatus,
    ManifestKind,
    VerificationStatus,
    verify_all,
    verify_manifest,
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


def test_bootstrap_baseline_verifies(repo_root: Path) -> None:
    """The bootstrap commit still holds exactly the recorded bytes.

    Verified against the Git object tree at the pinned commit, not the working tree.
    A later change to a Class C artifact does not affect this (ADR-012); the detailed
    properties of that model live in ``test_baseline.py``.
    """
    report = verify_bootstrap_baseline(repo_root)
    failures = [entry.render() for entry in report.entries if entry.status is not BlobStatus.PASS]
    assert failures == []
    assert report.status is BaselineStatus.PASS


def test_bootstrap_manifest_is_not_verified_against_the_working_tree(repo_root: Path) -> None:
    """Asking for a working-tree bootstrap check must be refused, not answered.

    Comparing the historical manifest to the present tree is the error that produced a
    false integrity alarm on PR #2. The CLI directs the operator to `verify-bootstrap`.
    """
    with pytest.raises(ConfigurationError) as excinfo:
        verify_manifest(repo_root / BOOTSTRAP_MANIFEST_RELPATH, repo_root)
    assert "verify-bootstrap" in str(excinfo.value)


def test_bootstrap_manifest_covers_the_expected_file_count(repo_root: Path) -> None:
    document = json.loads((repo_root / BOOTSTRAP_MANIFEST_RELPATH).read_text(encoding="utf-8"))
    assert len(document["files"]) == BOOTSTRAP_FILE_COUNT


def test_preflight_source_manifest_is_reported_incomplete(repo_root: Path) -> None:
    """The corpus manifest holds one partially frozen row today.

    STATUS.md records preflight corpus provenance as OPEN. The Canada rights freeze added
    CA-3 and left ten source units blocked. The manifest schema carries no path column, so
    the verifier cannot bind a row to its committed bytes and must never report PASS.
    Byte-level verification is scripts/verify_canada_freeze.py, not this verifier.
    """
    report = verify_source_manifest(repo_root / SOURCE_MANIFEST_RELPATH, repo_root)
    assert report.status is VerificationStatus.INCOMPLETE
    assert [entry.status.name for entry in report.entries] == ["RECORDED_NOT_VERIFIED"]
    assert not any(entry.status is EntryStatus.PASS for entry in report.entries)


def test_verify_all_covers_only_current_tree_manifests(repo_root: Path) -> None:
    """`verify_all` describes the present tree; the bootstrap baseline is separate."""
    reports = {report.kind: report for report in verify_all(repo_root)}
    assert set(reports) == {ManifestKind.SHA256SUMS, ManifestKind.SOURCE_MANIFEST}
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
