"""Tests for read-only manifest verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.errors import ManifestError
from oic.hashing import hash_bytes
from oic.manifests import (
    EntryStatus,
    ManifestKind,
    VerificationStatus,
    detect_manifest_kind,
    verify_bootstrap_manifest,
    verify_manifest,
    verify_sha256sums,
    verify_source_manifest,
    worst_status,
)

SOURCE_MANIFEST_HEADER = (
    "source_id,title,issuer,source_type,official_url_or_origin,license_or_public_basis,"
    "acquired_at,sha256,effective_from,effective_until,supersedes,confidentiality,notes"
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A throwaway repository root with one known file."""
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    payload = tmp_path / "payload.txt"
    payload.write_bytes(b"abc")
    return tmp_path


def _write_bootstrap(root: Path, records: list[dict[str, object]], **extra: object) -> Path:
    document: dict[str, object] = {"artifact": "test", "files": records, **extra}
    path = root / "BOOTSTRAP_MANIFEST.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


ABC_DIGEST = hash_bytes(b"abc")


# ---------------------------------------------------------------------------
# Bootstrap manifest
# ---------------------------------------------------------------------------


def test_bootstrap_manifest_passes_when_everything_matches(workspace: Path) -> None:
    manifest = _write_bootstrap(
        workspace, [{"path": "payload.txt", "sha256": ABC_DIGEST, "bytes": 3}]
    )
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.PASS
    assert report.count(EntryStatus.PASS) == 1


def test_manifest_missing_file_fails(workspace: Path) -> None:
    manifest = _write_bootstrap(workspace, [{"path": "absent.txt", "sha256": ABC_DIGEST}])
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.MISSING_FILE


def test_manifest_incorrect_hash_fails(workspace: Path) -> None:
    manifest = _write_bootstrap(workspace, [{"path": "payload.txt", "sha256": "0" * 64}])
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.HASH_MISMATCH


def test_missing_hash_is_reported_separately_from_incorrect_hash(workspace: Path) -> None:
    """A recorded-but-absent digest is INCOMPLETE, never a pass and never a mismatch."""
    manifest = _write_bootstrap(
        workspace,
        [
            {"path": "payload.txt"},
            {"path": "payload.txt", "sha256": ""},
        ],
    )
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.INCOMPLETE
    assert report.count(EntryStatus.MISSING_HASH) == 2
    assert report.count(EntryStatus.HASH_MISMATCH) == 0
    assert report.count(EntryStatus.PASS) == 0


def test_size_mismatch_is_detected(workspace: Path) -> None:
    manifest = _write_bootstrap(
        workspace, [{"path": "payload.txt", "sha256": ABC_DIGEST, "bytes": 999}]
    )
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.SIZE_MISMATCH


def test_malformed_digest_is_reported(workspace: Path) -> None:
    manifest = _write_bootstrap(workspace, [{"path": "payload.txt", "sha256": "not-a-digest"}])
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.MALFORMED_HASH


@pytest.mark.parametrize(
    "traversal",
    [
        "../escape.txt",
        "docs/../../escape.txt",
        "/etc/passwd",
        "https://example.invalid/policy.pdf",
        "file:///etc/passwd",
    ],
)
def test_manifest_path_traversal_is_refused(workspace: Path, traversal: str) -> None:
    manifest = _write_bootstrap(workspace, [{"path": traversal, "sha256": ABC_DIGEST}])
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.UNSAFE_PATH


def test_traversal_target_is_never_read(
    workspace: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside")
    secret = outside / "secret.txt"
    secret.write_bytes(b"abc")  # would match ABC_DIGEST if it were ever hashed
    manifest = _write_bootstrap(
        workspace, [{"path": f"../{outside.name}/secret.txt", "sha256": ABC_DIGEST}]
    )
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.entries[0].status is EntryStatus.UNSAFE_PATH
    assert report.count(EntryStatus.PASS) == 0


def test_governing_tdd_digest_is_verified(workspace: Path) -> None:
    tdd = workspace / "docs" / "tdd"
    tdd.mkdir(parents=True)
    (tdd / "TDD-OIC-001-v1.1.pdf").write_bytes(b"abc")
    manifest = _write_bootstrap(workspace, [], governing_tdd_sha256=ABC_DIGEST)
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.PASS
    assert any("governing_tdd_sha256" in note for note in report.notes)


def test_wrong_governing_tdd_digest_fails(workspace: Path) -> None:
    tdd = workspace / "docs" / "tdd"
    tdd.mkdir(parents=True)
    (tdd / "TDD-OIC-001-v1.1.pdf").write_bytes(b"tampered")
    manifest = _write_bootstrap(workspace, [], governing_tdd_sha256=ABC_DIGEST)
    report = verify_bootstrap_manifest(manifest, workspace)
    assert report.status is VerificationStatus.FAIL


def test_manifest_is_never_mutated(workspace: Path) -> None:
    manifest = _write_bootstrap(workspace, [{"path": "payload.txt", "sha256": "0" * 64}])
    before = manifest.read_bytes()
    verify_bootstrap_manifest(manifest, workspace)
    assert manifest.read_bytes() == before


def test_manifest_without_files_array_raises(workspace: Path) -> None:
    path = workspace / "BOOTSTRAP_MANIFEST.json"
    path.write_text(json.dumps({"artifact": "test"}), encoding="utf-8")
    with pytest.raises(ManifestError):
        verify_bootstrap_manifest(path, workspace)


def test_unparseable_manifest_raises(workspace: Path) -> None:
    path = workspace / "BOOTSTRAP_MANIFEST.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as excinfo:
        verify_bootstrap_manifest(path, workspace)
    assert excinfo.value.code == "OIC-1003"


def test_entry_ordering_is_deterministic(workspace: Path) -> None:
    for name in ("c.txt", "a.txt", "b.txt"):
        (workspace / name).write_bytes(b"abc")
    records: list[dict[str, object]] = [
        {"path": name, "sha256": ABC_DIGEST} for name in ("c.txt", "a.txt", "b.txt")
    ]
    manifest = _write_bootstrap(workspace, records)
    first = verify_bootstrap_manifest(manifest, workspace)
    second = verify_bootstrap_manifest(manifest, workspace)
    assert [entry.path for entry in first.entries] == ["a.txt", "b.txt", "c.txt"]
    assert first.to_json() == second.to_json()


# ---------------------------------------------------------------------------
# SHA256SUMS
# ---------------------------------------------------------------------------


def test_sha256sums_passes(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"abc")
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ABC_DIGEST}  doc.pdf\n", encoding="utf-8")
    report = verify_sha256sums(sums)
    assert report.status is VerificationStatus.PASS
    assert report.kind is ManifestKind.SHA256SUMS


def test_sha256sums_accepts_binary_mode_marker(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"abc")
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ABC_DIGEST} *doc.pdf\n", encoding="utf-8")
    assert verify_sha256sums(sums).status is VerificationStatus.PASS


def test_sha256sums_detects_tampering(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"tampered")
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ABC_DIGEST}  doc.pdf\n", encoding="utf-8")
    report = verify_sha256sums(sums)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.HASH_MISMATCH


def test_sha256sums_rejects_traversal(tmp_path: Path) -> None:
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{ABC_DIGEST}  ../outside.pdf\n", encoding="utf-8")
    report = verify_sha256sums(sums)
    assert report.entries[0].status is EntryStatus.UNSAFE_PATH


def test_sha256sums_reports_malformed_lines(tmp_path: Path) -> None:
    sums = tmp_path / "SHA256SUMS"
    sums.write_text("garbage\n", encoding="utf-8")
    report = verify_sha256sums(sums)
    assert report.entries[0].status is EntryStatus.UNREADABLE


def test_sha256sums_ignores_blank_and_comment_lines(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"abc")
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"# header\n\n{ABC_DIGEST}  doc.pdf\n", encoding="utf-8")
    report = verify_sha256sums(sums)
    assert len(report.entries) == 1
    assert report.status is VerificationStatus.PASS


# ---------------------------------------------------------------------------
# SOURCE_MANIFEST.csv
# ---------------------------------------------------------------------------


def test_header_only_source_manifest_is_incomplete_not_pass(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    path.write_text(SOURCE_MANIFEST_HEADER + "\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert report.status is VerificationStatus.INCOMPLETE
    assert report.entries == ()
    assert any("NOT complete" in note for note in report.notes)
    assert any("not corpus-ready" in note for note in report.notes)


def test_row_with_recorded_digest_is_not_treated_as_verified(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    row = f"SRC-1,Title,Issuer,law,https://example.invalid/a.pdf,public,2026-01-01,{ABC_DIGEST},,,,public,"
    path.write_text(f"{SOURCE_MANIFEST_HEADER}\n{row}\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert report.status is VerificationStatus.INCOMPLETE
    assert report.entries[0].status is EntryStatus.RECORDED_NOT_VERIFIED
    assert report.count(EntryStatus.PASS) == 0


def test_row_without_digest_is_incomplete(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    row = "SRC-1,Title,Issuer,law,https://example.invalid/a.pdf,public,2026-01-01,,,,,public,"
    path.write_text(f"{SOURCE_MANIFEST_HEADER}\n{row}\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert report.entries[0].status is EntryStatus.MISSING_HASH
    assert report.status is VerificationStatus.INCOMPLETE


def test_row_with_malformed_digest_fails(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    row = "SRC-1,Title,Issuer,law,https://example.invalid/a.pdf,public,2026-01-01,nope,,,,public,"
    path.write_text(f"{SOURCE_MANIFEST_HEADER}\n{row}\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert report.status is VerificationStatus.FAIL
    assert report.entries[0].status is EntryStatus.MALFORMED_HASH


def test_source_manifest_reports_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    path.write_text("source_id,title\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert any("missing required columns" in note for note in report.notes)


def test_source_manifest_states_that_urls_are_never_fetched(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    path.write_text(SOURCE_MANIFEST_HEADER + "\n", encoding="utf-8")
    report = verify_source_manifest(path, tmp_path)
    assert any("never fetches" in note for note in report.notes)


def test_source_manifest_without_header_raises(tmp_path: Path) -> None:
    path = tmp_path / "SOURCE_MANIFEST.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        verify_source_manifest(path, tmp_path)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("BOOTSTRAP_MANIFEST.json", ManifestKind.BOOTSTRAP),
        ("SHA256SUMS", ManifestKind.SHA256SUMS),
        ("SOURCE_MANIFEST.csv", ManifestKind.SOURCE_MANIFEST),
    ],
)
def test_kind_detection(tmp_path: Path, name: str, expected: ManifestKind) -> None:
    assert detect_manifest_kind(tmp_path / name) is expected


def test_unknown_manifest_name_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError):
        detect_manifest_kind(tmp_path / "mystery.txt")


def test_verify_manifest_reports_absent_manifest(tmp_path: Path) -> None:
    with pytest.raises(ManifestError):
        verify_manifest(tmp_path / "BOOTSTRAP_MANIFEST.json", tmp_path)


def test_worst_status_prefers_fail_over_incomplete(workspace: Path) -> None:
    good = _write_bootstrap(workspace, [{"path": "payload.txt", "sha256": ABC_DIGEST}])
    passing = verify_bootstrap_manifest(good, workspace)
    incomplete = _write_bootstrap(workspace, [{"path": "payload.txt"}])
    incomplete_report = verify_bootstrap_manifest(incomplete, workspace)
    failing = _write_bootstrap(workspace, [{"path": "payload.txt", "sha256": "0" * 64}])
    failing_report = verify_bootstrap_manifest(failing, workspace)

    assert worst_status([passing]) is VerificationStatus.PASS
    assert worst_status([passing, incomplete_report]) is VerificationStatus.INCOMPLETE
    assert worst_status([passing, incomplete_report, failing_report]) is VerificationStatus.FAIL
    assert worst_status([]) is VerificationStatus.PASS
