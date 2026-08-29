"""Tests for historical bootstrap baseline verification.

The central property, and the one whose absence caused the original defect: a file
changed in a *later* commit must not invalidate the baseline, because the baseline is a
statement about the bootstrap commit, not about the present tree (ADR-012).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from oic.baseline import (
    BOOTSTRAP_COMMIT,
    GOVERNING_TDD_SHA256,
    BaselineStatus,
    BlobStatus,
    verify_bootstrap_baseline,
)
from oic.errors import DependencyUnavailableError, ManifestError
from oic.hashing import hash_bytes

pytestmark = pytest.mark.contract

BOOTSTRAP_FILE_COUNT = 50


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-C", str(workspace), *args],
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """A miniature repository with a bootstrap-shaped manifest at its first commit."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "commit.gpgsign", "false")

    (tmp_path / "docs" / "tdd").mkdir(parents=True)
    (tmp_path / "docs" / "tdd" / "TDD-OIC-001-v1.1.pdf").write_bytes(b"pretend-pdf")
    (tmp_path / "adapters").mkdir()
    (tmp_path / "adapters" / "README.md").write_bytes(b"stub\n")

    manifest = {
        "artifact": "synthetic",
        "governing_tdd_sha256": hash_bytes(b"pretend-pdf"),
        "files": [
            {
                "path": "docs/tdd/TDD-OIC-001-v1.1.pdf",
                "sha256": hash_bytes(b"pretend-pdf"),
                "bytes": 11,
            },
            {"path": "adapters/README.md", "sha256": hash_bytes(b"stub\n"), "bytes": 5},
        ],
    }
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "bootstrap")
    return tmp_path


def _head(workspace: Path) -> str:
    return _git(workspace, "rev-parse", "HEAD").stdout.strip()


# ---------------------------------------------------------------------------
# 1 & 8. Baseline passes at the bootstrap commit, including on current main
# ---------------------------------------------------------------------------


def test_baseline_verification_passes_at_the_bootstrap_commit(repo_root: Path) -> None:
    report = verify_bootstrap_baseline(repo_root)
    failures = [entry.render() for entry in report.entries if entry.status is not BlobStatus.PASS]
    assert failures == []
    assert report.status is BaselineStatus.PASS
    assert report.resolved_commit == BOOTSTRAP_COMMIT


def test_baseline_passes_on_current_checkout_including_pr2(repo_root: Path) -> None:
    """The working tree contains PR #2's change to a Class C artifact.

    `adapters/ztl/README.md` differs from its bootstrap bytes in the working tree. The
    historical baseline must still pass, because it never consults the working tree.
    """
    current = (repo_root / "adapters" / "ztl" / "README.md").read_bytes()
    manifest = json.loads((repo_root / "BOOTSTRAP_MANIFEST.json").read_text(encoding="utf-8"))
    recorded = next(f for f in manifest["files"] if f["path"] == "adapters/ztl/README.md")
    assert hash_bytes(current) != recorded["sha256"], (
        "expected the working tree to differ from the bootstrap bytes for this file; "
        "if it no longer does, this test has stopped proving anything"
    )
    assert verify_bootstrap_baseline(repo_root).status is BaselineStatus.PASS


def test_baseline_covers_every_recorded_artifact(repo_root: Path) -> None:
    report = verify_bootstrap_baseline(repo_root)
    # 50 recorded files, plus the TDD blob re-read for the declared digest, plus the
    # literal governing-digest assertion that only the real bootstrap commit carries.
    assert len(report.entries) == BOOTSTRAP_FILE_COUNT + 2
    assert report.count(BlobStatus.PASS) == len(report.entries)
    recorded = {entry.path for entry in report.entries}
    assert "governing_tdd_sha256" in recorded
    assert "docs/tdd/TDD-OIC-001-v1.1.pdf" in recorded


def test_governing_tdd_digest_is_verified_at_the_baseline(repo_root: Path) -> None:
    report = verify_bootstrap_baseline(repo_root)
    assert (
        GOVERNING_TDD_SHA256 == "2a4d802130d577e4fb8fee731174ae0f2172ef2d617e3b99f068545d2b9fbf77"
    )
    assert any("governing_tdd_sha256" in note for note in report.notes)


# ---------------------------------------------------------------------------
# 2. A later change does not invalidate the baseline
# ---------------------------------------------------------------------------


def test_file_modified_in_a_later_commit_does_not_invalidate_the_baseline(
    synthetic_repo: Path,
) -> None:
    """This is the property whose absence produced the original false alarm."""
    baseline_ref = _head(synthetic_repo)
    assert verify_bootstrap_baseline(synthetic_repo, baseline_ref).status is BaselineStatus.PASS

    # Rewrite a listed Class C artifact, exactly as PR #2 did.
    (synthetic_repo / "adapters" / "README.md").write_bytes(b"substantially longer content\n")
    _git(synthetic_repo, "add", "-A")
    _git(synthetic_repo, "commit", "-q", "-m", "later: rewrite adapter README")

    assert _head(synthetic_repo) != baseline_ref
    report = verify_bootstrap_baseline(synthetic_repo, baseline_ref)
    assert report.status is BaselineStatus.PASS, [e.render() for e in report.entries]


def test_baseline_does_not_read_the_working_tree(synthetic_repo: Path) -> None:
    """Even an uncommitted working-tree edit must not affect the result."""
    baseline_ref = _head(synthetic_repo)
    (synthetic_repo / "adapters" / "README.md").write_bytes(b"dirty uncommitted edit\n")
    assert verify_bootstrap_baseline(synthetic_repo, baseline_ref).status is BaselineStatus.PASS


def test_baseline_does_not_modify_the_working_tree(synthetic_repo: Path) -> None:
    before = {
        path: path.read_bytes()
        for path in synthetic_repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    verify_bootstrap_baseline(synthetic_repo, _head(synthetic_repo))
    after = {
        path: path.read_bytes()
        for path in synthetic_repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    assert before == after
    assert _git(synthetic_repo, "status", "--porcelain").stdout == ""


# ---------------------------------------------------------------------------
# 3, 4, 5, 6. Failure modes
# ---------------------------------------------------------------------------


def test_wrong_baseline_ref_fails(synthetic_repo: Path) -> None:
    """A ref whose tree does not match the recorded digests must FAIL, not pass."""
    (synthetic_repo / "adapters" / "README.md").write_bytes(b"changed\n")
    _git(synthetic_repo, "add", "-A")
    _git(synthetic_repo, "commit", "-q", "-m", "later")
    report = verify_bootstrap_baseline(synthetic_repo, _head(synthetic_repo))
    assert report.status is BaselineStatus.FAIL
    offending = [e for e in report.entries if e.path == "adapters/README.md"]
    assert offending and offending[0].status in {
        BlobStatus.HASH_MISMATCH,
        BlobStatus.SIZE_MISMATCH,
    }


def test_unavailable_commit_fails_clearly(synthetic_repo: Path) -> None:
    absent = "0" * 40
    with pytest.raises(ManifestError) as excinfo:
        verify_bootstrap_baseline(synthetic_repo, absent)
    assert excinfo.value.code == "OIC-1003"
    assert "could not be resolved" in str(excinfo.value)


def test_nonexistent_ref_name_fails_clearly(synthetic_repo: Path) -> None:
    with pytest.raises(ManifestError):
        verify_bootstrap_baseline(synthetic_repo, "no-such-tag")


def test_missing_blob_fails(synthetic_repo: Path) -> None:
    """A manifest entry naming a path absent from the baseline tree must FAIL."""
    manifest = json.loads((synthetic_repo / "BOOTSTRAP_MANIFEST.json").read_text("utf-8"))
    manifest["files"].append({"path": "never/existed.md", "sha256": hash_bytes(b"x"), "bytes": 1})
    (synthetic_repo / "BOOTSTRAP_MANIFEST.json").write_text(json.dumps(manifest), "utf-8")
    _git(synthetic_repo, "add", "-A")
    _git(synthetic_repo, "commit", "-q", "-m", "manifest names an absent file")

    report = verify_bootstrap_baseline(synthetic_repo, _head(synthetic_repo))
    assert report.status is BaselineStatus.FAIL
    entry = next(e for e in report.entries if e.path == "never/existed.md")
    assert entry.status is BlobStatus.MISSING_BLOB


def test_hash_mismatch_inside_a_synthetic_baseline_fails(synthetic_repo: Path) -> None:
    manifest = json.loads((synthetic_repo / "BOOTSTRAP_MANIFEST.json").read_text("utf-8"))
    for record in manifest["files"]:
        if record["path"] == "adapters/README.md":
            record["sha256"] = "0" * 64
    (synthetic_repo / "BOOTSTRAP_MANIFEST.json").write_text(json.dumps(manifest), "utf-8")
    _git(synthetic_repo, "add", "-A")
    _git(synthetic_repo, "commit", "-q", "-m", "manifest records a wrong digest")

    report = verify_bootstrap_baseline(synthetic_repo, _head(synthetic_repo))
    assert report.status is BaselineStatus.FAIL
    entry = next(e for e in report.entries if e.path == "adapters/README.md")
    assert entry.status is BlobStatus.HASH_MISMATCH


def test_absent_manifest_at_ref_fails(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "README.md").write_text("no manifest here\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "no manifest")
    with pytest.raises(ManifestError) as excinfo:
        verify_bootstrap_baseline(tmp_path, _head(tmp_path))
    assert "absent at the baseline ref" in str(excinfo.value)


def test_missing_git_fails_clearly(synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(DependencyUnavailableError) as excinfo:
        verify_bootstrap_baseline(synthetic_repo)
    assert excinfo.value.code == "OIC-1005"


# ---------------------------------------------------------------------------
# 7. No network, no mutation
# ---------------------------------------------------------------------------


def test_only_read_only_git_subcommands_are_used(
    synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No fetch, no checkout, no shell. Asserted on the actual argv."""
    ref = _head(synthetic_repo)  # resolve before patching; this helper is not under test
    seen: list[list[str]] = []
    real_run = subprocess.run

    def _record(args: object, **kwargs: object) -> object:
        assert isinstance(args, list)
        seen.append([str(a) for a in args])
        assert kwargs.get("shell") is False, "git must never be run through a shell"
        return real_run(args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(subprocess, "run", _record)
    verify_bootstrap_baseline(synthetic_repo, ref)

    assert seen, "no git call was made"
    forbidden = {"fetch", "pull", "clone", "checkout", "switch", "reset", "add", "commit"}
    for argv in seen:
        assert argv[0].endswith("git"), argv
        subcommand = argv[3] if len(argv) > 3 else ""
        assert subcommand in {"rev-parse", "cat-file"}, argv
        assert forbidden.isdisjoint(argv), argv


def test_report_json_is_deterministic(repo_root: Path) -> None:
    first = json.dumps(verify_bootstrap_baseline(repo_root).to_json(), sort_keys=True)
    second = json.dumps(verify_bootstrap_baseline(repo_root).to_json(), sort_keys=True)
    assert first == second


def test_entries_are_path_ordered(repo_root: Path) -> None:
    paths = [entry.path for entry in verify_bootstrap_baseline(repo_root).entries]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# 9. The manifest itself is untouched
# ---------------------------------------------------------------------------


def test_bootstrap_manifest_is_byte_identical_to_its_bootstrap_version(
    repo_root: Path,
) -> None:
    """`BOOTSTRAP_MANIFEST.json` is Class A evidence and must never be rewritten."""
    committed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "cat-file",
            "blob",
            f"{BOOTSTRAP_COMMIT}:BOOTSTRAP_MANIFEST.json",
        ],
        capture_output=True,
        check=True,
    ).stdout
    working = (repo_root / "BOOTSTRAP_MANIFEST.json").read_bytes()
    assert working == committed
