"""Historical bootstrap baseline verification.

What this verifies
------------------
That the bootstrap commit still contains exactly the bytes ``BOOTSTRAP_MANIFEST.json``
recorded for it. Both the manifest and every artifact it lists are read **from the pinned
commit** through the local Git object database. The working tree is never consulted.

Why it is not a working-tree check
----------------------------------
``BOOTSTRAP_MANIFEST.json`` is immutable historical evidence about one commit, not a
policy freezing every path it happens to list (ADR-012). A file that changes in a later
commit cannot invalidate the baseline, because the baseline is a statement about the past.
Comparing the historical manifest against the present tree conflated the two and produced
a false integrity alarm the first time a Class C artifact legitimately changed.

Safety properties
-----------------
* No shell. Every Git invocation uses a fixed argument array with ``shell=False``.
* No network. Only ``cat-file`` and ``rev-parse`` are used; nothing fetches.
* No mutation. No checkout, no index write, no working-tree change.
* Blob bytes are hashed exactly as stored, with no newline or encoding translation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Final

from oic.errors import (
    ConfigurationError,
    DependencyUnavailableError,
    ManifestError,
    UnsupportedHashAlgorithmError,
)
from oic.hashing import hash_bytes, normalise_digest
from oic.paths import BOOTSTRAP_MANIFEST_RELPATH, TDD_PDF_RELPATH

__all__ = [
    "BOOTSTRAP_COMMIT",
    "GOVERNING_TDD_SHA256",
    "BaselineReport",
    "BaselineStatus",
    "BlobResult",
    "verify_bootstrap_baseline",
]

#: The bootstrap commit. This is Class A evidence (ADR-012) and never changes.
BOOTSTRAP_COMMIT: Final[str] = "8b06b8a7f1a319a0b5ceeea6857eefa30b9eb081"

#: SHA-256 of TDD-OIC-001 v1.1, fixed by the governing design document.
GOVERNING_TDD_SHA256: Final[str] = (
    "2a4d802130d577e4fb8fee731174ae0f2172ef2d617e3b99f068545d2b9fbf77"
)

_GIT_TIMEOUT_SECONDS: Final[float] = 60.0

JsonValue = Any


class BaselineStatus(Enum):
    """Per-entry and aggregate outcome."""

    PASS = "PASS"  # noqa: S105 - status token, not a credential
    FAIL = "FAIL"


class BlobStatus(Enum):
    """Outcome for one artifact read from the historical tree."""

    PASS = "PASS"  # noqa: S105 - status token, not a credential
    MISSING_BLOB = "MISSING_BLOB"
    HASH_MISMATCH = "HASH_MISMATCH"
    SIZE_MISMATCH = "SIZE_MISMATCH"
    MALFORMED_ENTRY = "MALFORMED_ENTRY"


@dataclass(frozen=True, slots=True)
class BlobResult:
    """Verification outcome for one artifact at the pinned commit."""

    path: str
    status: BlobStatus
    detail: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return {"detail": self.detail, "path": self.path, "status": self.status.value}

    def render(self) -> str:
        base = f"  {self.status.value:<16} {self.path}"
        return f"{base}  ({self.detail})" if self.detail else base


@dataclass(frozen=True, slots=True)
class BaselineReport:
    """Aggregate outcome of historical baseline verification."""

    ref: str
    resolved_commit: str
    status: BaselineStatus
    entries: tuple[BlobResult, ...]
    notes: tuple[str, ...]

    def count(self, status: BlobStatus) -> int:
        return sum(1 for entry in self.entries if entry.status is status)

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "entries": [entry.to_json() for entry in self.entries],
            "entry_count": len(self.entries),
            "notes": list(self.notes),
            "ref": self.ref,
            "resolved_commit": self.resolved_commit,
            "status": self.status.value,
            "summary": {status.value: self.count(status) for status in BlobStatus},
        }


# ---------------------------------------------------------------------------
# Git object access
# ---------------------------------------------------------------------------


def _git_executable() -> str:
    """Resolve git to an absolute path, or fail with a clear operator error."""
    location = shutil.which("git")
    if location is None:
        raise DependencyUnavailableError(
            "git is not available",
            detail="historical baseline verification reads the Git object database",
        )
    return location


def _run_git(args: Sequence[str], *, repo_root: Path) -> subprocess.CompletedProcess[bytes]:
    """Run a fixed git argument array. No shell, no network, no mutation.

    Only ``rev-parse`` and ``cat-file`` are ever passed, both read-only. The executable is
    resolved to an absolute path first so nothing depends on ``PATH`` ordering at call
    time.
    """
    executable = _git_executable()
    try:
        return subprocess.run(  # noqa: S603 - absolute executable, fixed read-only argv
            [executable, "-C", str(repo_root), *args],
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DependencyUnavailableError(
            "git could not be executed",
            detail=type(exc).__name__,
        ) from exc


def _resolve_commit(ref: str, repo_root: Path) -> str:
    completed = _run_git(["rev-parse", "--verify", f"{ref}^{{commit}}"], repo_root=repo_root)
    if completed.returncode != 0:
        raise ManifestError(
            "baseline ref could not be resolved to a commit",
            detail=f"{ref} (is the commit present in this clone?)",
        )
    return completed.stdout.decode("utf-8", errors="replace").strip()


def _read_blob(commit: str, relpath: str, repo_root: Path) -> bytes | None:
    """Return the exact blob bytes at ``commit:relpath``, or None if absent."""
    completed = _run_git(["cat-file", "blob", f"{commit}:{relpath}"], repo_root=repo_root)
    if completed.returncode != 0:
        return None
    return completed.stdout


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_bootstrap_baseline(
    repo_root: Path,
    ref: str = BOOTSTRAP_COMMIT,
) -> BaselineReport:
    """Verify the bootstrap manifest against the tree of ``ref``.

    Both the manifest and every artifact it lists are read from ``ref`` through the Git
    object database. The working tree is not read and not modified.

    Raises:
        DependencyUnavailableError: git is unavailable.
        ManifestError: the ref cannot be resolved, or the manifest blob is absent or
            unparseable at that ref.
    """
    commit = _resolve_commit(ref, repo_root)

    manifest_bytes = _read_blob(commit, BOOTSTRAP_MANIFEST_RELPATH, repo_root)
    if manifest_bytes is None:
        raise ManifestError(
            "bootstrap manifest is absent at the baseline ref",
            detail=f"{commit[:12]}:{BOOTSTRAP_MANIFEST_RELPATH}",
        )
    try:
        document: JsonValue = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(
            "bootstrap manifest at the baseline ref is not valid UTF-8 JSON",
            detail=f"{commit[:12]}:{BOOTSTRAP_MANIFEST_RELPATH}",
        ) from exc
    if not isinstance(document, dict):
        raise ManifestError(
            "bootstrap manifest must be a JSON object",
            detail=f"{commit[:12]}:{BOOTSTRAP_MANIFEST_RELPATH}",
        )

    files = document.get("files")
    if not isinstance(files, list):
        raise ManifestError(
            "bootstrap manifest has no 'files' array",
            detail=f"{commit[:12]}:{BOOTSTRAP_MANIFEST_RELPATH}",
        )

    entries: list[BlobResult] = []
    notes: list[str] = []

    for index, record in enumerate(files):
        entries.append(_verify_entry(index, record, commit, repo_root))

    # The governing TDD digest is recorded as a top-level field as well as a file entry.
    declared_tdd = document.get("governing_tdd_sha256")
    if isinstance(declared_tdd, str) and declared_tdd:
        try:
            declared_hex = normalise_digest(declared_tdd)
        except (ConfigurationError, UnsupportedHashAlgorithmError) as exc:
            entries.append(
                BlobResult(
                    path="governing_tdd_sha256",
                    status=BlobStatus.MALFORMED_ENTRY,
                    detail=str(exc),
                )
            )
        else:
            # Self-consistency: the declared field must match the PDF blob at this ref.
            entries.append(
                _verify_entry_bytes(TDD_PDF_RELPATH, declared_hex, None, commit, repo_root)
            )
            notes.append("governing_tdd_sha256 verified against the blob at the baseline ref")

            # Additionally, the real bootstrap commit must carry the exact digest fixed by
            # the governing design document. This literal is only meaningful for that
            # commit, so a synthetic or alternative baseline is not held to it.
            if commit == BOOTSTRAP_COMMIT:
                entries.append(
                    BlobResult(
                        path="governing_tdd_sha256",
                        status=(
                            BlobStatus.PASS
                            if declared_hex == GOVERNING_TDD_SHA256
                            else BlobStatus.HASH_MISMATCH
                        ),
                        detail=(
                            None
                            if declared_hex == GOVERNING_TDD_SHA256
                            else "does not equal the governing TDD digest for TDD-OIC-001 v1.1"
                        ),
                    )
                )
    else:
        entries.append(
            BlobResult(
                path="governing_tdd_sha256",
                status=BlobStatus.MALFORMED_ENTRY,
                detail="manifest declares no governing_tdd_sha256",
            )
        )

    entries.sort(key=lambda entry: (entry.path, entry.status.value))
    status = (
        BaselineStatus.FAIL
        if any(entry.status is not BlobStatus.PASS for entry in entries)
        else BaselineStatus.PASS
    )
    notes.append(
        "verified against the Git object tree at the baseline ref; the working tree was "
        "neither read nor modified"
    )
    return BaselineReport(
        ref=ref,
        resolved_commit=commit,
        status=status,
        entries=tuple(entries),
        notes=tuple(notes),
    )


def _verify_entry(index: int, record: JsonValue, commit: str, repo_root: Path) -> BlobResult:
    if not isinstance(record, dict):
        return BlobResult(
            path=f"<files[{index}]>",
            status=BlobStatus.MALFORMED_ENTRY,
            detail="entry is not a JSON object",
        )
    relpath = record.get("path")
    if not isinstance(relpath, str) or not relpath:
        return BlobResult(
            path=f"<files[{index}]>",
            status=BlobStatus.MALFORMED_ENTRY,
            detail="entry has no 'path' string",
        )
    digest = record.get("sha256")
    if not isinstance(digest, str) or not digest:
        return BlobResult(
            path=relpath,
            status=BlobStatus.MALFORMED_ENTRY,
            detail="entry records no sha256",
        )
    expected_bytes = record.get("bytes")
    return _verify_entry_bytes(
        relpath,
        digest,
        expected_bytes if isinstance(expected_bytes, int) else None,
        commit,
        repo_root,
    )


def _verify_entry_bytes(
    relpath: str,
    digest: str,
    expected_bytes: int | None,
    commit: str,
    repo_root: Path,
) -> BlobResult:
    try:
        expected_hex = normalise_digest(digest)
    except (ConfigurationError, UnsupportedHashAlgorithmError) as exc:
        return BlobResult(path=relpath, status=BlobStatus.MALFORMED_ENTRY, detail=str(exc))

    blob = _read_blob(commit, relpath, repo_root)
    if blob is None:
        return BlobResult(
            path=relpath,
            status=BlobStatus.MISSING_BLOB,
            detail="not present in the tree at the baseline ref",
        )
    if expected_bytes is not None and len(blob) != expected_bytes:
        return BlobResult(
            path=relpath,
            status=BlobStatus.SIZE_MISMATCH,
            detail=f"expected {expected_bytes} bytes, found {len(blob)}",
        )
    actual_hex = hash_bytes(blob)
    if actual_hex != expected_hex:
        return BlobResult(
            path=relpath,
            status=BlobStatus.HASH_MISMATCH,
            detail=f"expected {expected_hex[:12]}..., computed {actual_hex[:12]}...",
        )
    return BlobResult(path=relpath, status=BlobStatus.PASS)
