"""Read-only verification of the repository's integrity manifests.

Three manifests are supported:

``BOOTSTRAP_MANIFEST.json``
    Path/digest/size records for the bootstrap-controlled artifacts, plus the governing
    TDD digest.
``docs/tdd/SHA256SUMS``
    Classic ``<hex>  <name>`` lines, resolved relative to the file's own directory.
``benchmarks/preflight/SOURCE_MANIFEST.csv``
    The preflight corpus provenance record. Its rows describe *external* documents that
    are not in the working tree.

Guarantees
----------
* Nothing is written. No manifest is repaired, normalised, or re-sorted on disk.
* No URL is fetched. The source manifest's origin column is recorded and reported, never
  dereferenced.
* Paths are contained by :func:`oic.paths.safe_join`; traversal is refused, not sanitised.
* Output is ordered deterministically by manifest-relative path.
* A missing digest is reported as INCOMPLETE and is never rendered as a pass. An
  incomplete corpus manifest must never read as corpus-ready.

Scope
-----
Verification here is byte integrity only. A PASS means the recorded bytes are the bytes
on disk. It says nothing about whether a document is authentic, authoritative, or
correctly interpreted.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from stat import S_ISREG
from typing import Any, Final

from oic.errors import (
    ConfigurationError,
    ManifestEntryMissingError,
    ManifestError,
    UnsafeManifestPathError,
    UnsupportedHashAlgorithmError,
)
from oic.hashing import hash_file, normalise_digest
from oic.paths import (
    SOURCE_MANIFEST_RELPATH,
    TDD_PDF_RELPATH,
    TDD_SHA256SUMS_RELPATH,
    relative_to_root,
    safe_join,
)

__all__ = [
    "KNOWN_MANIFESTS",
    "EntryResult",
    "EntryStatus",
    "ManifestKind",
    "ManifestReport",
    "VerificationStatus",
    "detect_manifest_kind",
    "verify_all",
    "verify_bootstrap_manifest",
    "verify_manifest",
    "verify_sha256sums",
    "verify_source_manifest",
    "worst_status",
]

JsonValue = Any

_SOURCE_MANIFEST_REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "source_id",
    "title",
    "issuer",
    "source_type",
    "official_url_or_origin",
    "license_or_public_basis",
    "acquired_at",
    "sha256",
    "effective_from",
    "effective_until",
    "supersedes",
    "confidentiality",
    "notes",
)


class ManifestKind(Enum):
    """Which manifest format a file is parsed as."""

    BOOTSTRAP = "bootstrap"
    SHA256SUMS = "sha256sums"
    SOURCE_MANIFEST = "source-manifest"


class EntryStatus(Enum):
    """Per-entry outcome.

    ``RECORDED_NOT_VERIFIED`` exists so the source manifest cannot report a pass for a
    corpus document whose bytes are not present in the working tree. Recording a digest
    is not the same as verifying one, and conflating them would let an unverified corpus
    read as verified.
    """

    PASS = "PASS"  # noqa: S105 - status token, not a credential
    MISSING_FILE = "MISSING_FILE"
    HASH_MISMATCH = "HASH_MISMATCH"
    SIZE_MISMATCH = "SIZE_MISMATCH"
    UNSAFE_PATH = "UNSAFE_PATH"
    UNREADABLE = "UNREADABLE"
    MISSING_HASH = "MISSING_HASH"
    MALFORMED_HASH = "MALFORMED_HASH"
    RECORDED_NOT_VERIFIED = "RECORDED_NOT_VERIFIED"


#: Entry statuses that make the whole manifest FAIL.
_FAILING: Final[frozenset[EntryStatus]] = frozenset(
    {
        EntryStatus.MISSING_FILE,
        EntryStatus.HASH_MISMATCH,
        EntryStatus.SIZE_MISMATCH,
        EntryStatus.UNSAFE_PATH,
        EntryStatus.UNREADABLE,
        EntryStatus.MALFORMED_HASH,
    }
)

#: Entry statuses that make the whole manifest INCOMPLETE (absent any failure).
_INCOMPLETE: Final[frozenset[EntryStatus]] = frozenset(
    {EntryStatus.MISSING_HASH, EntryStatus.RECORDED_NOT_VERIFIED}
)


class VerificationStatus(Enum):
    """Aggregate outcome for a manifest."""

    PASS = "PASS"  # noqa: S105 - status token, not a credential
    INCOMPLETE = "INCOMPLETE"
    FAIL = "FAIL"


_SEVERITY: Final[dict[VerificationStatus, int]] = {
    VerificationStatus.PASS: 0,
    VerificationStatus.INCOMPLETE: 1,
    VerificationStatus.FAIL: 2,
}


@dataclass(frozen=True, slots=True)
class EntryResult:
    """Outcome for one manifest entry."""

    path: str
    status: EntryStatus
    detail: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return {"detail": self.detail, "path": self.path, "status": self.status.value}

    def render(self) -> str:
        base = f"  {self.status.value:<21} {self.path}"
        return f"{base}  ({self.detail})" if self.detail else base


@dataclass(frozen=True, slots=True)
class ManifestReport:
    """Aggregate outcome for one manifest."""

    manifest_path: str
    kind: ManifestKind
    status: VerificationStatus
    entries: tuple[EntryResult, ...]
    notes: tuple[str, ...]

    def count(self, status: EntryStatus) -> int:
        return sum(1 for entry in self.entries if entry.status is status)

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "entries": [entry.to_json() for entry in self.entries],
            "entry_count": len(self.entries),
            "kind": self.kind.value,
            "manifest_path": self.manifest_path,
            "notes": list(self.notes),
            "status": self.status.value,
            "summary": {status.value: self.count(status) for status in EntryStatus},
        }


def _aggregate(
    entries: Sequence[EntryResult], *, forced_notes: Sequence[str] = ()
) -> VerificationStatus:
    if any(entry.status in _FAILING for entry in entries):
        return VerificationStatus.FAIL
    if any(entry.status in _INCOMPLETE for entry in entries) or forced_notes:
        return VerificationStatus.INCOMPLETE
    return VerificationStatus.PASS


def _sorted(entries: Sequence[EntryResult]) -> tuple[EntryResult, ...]:
    return tuple(sorted(entries, key=lambda entry: (entry.path, entry.status.value)))


def _check_file(
    root: Path,
    raw_path: str,
    expected_digest: str | None,
    expected_bytes: int | None = None,
) -> EntryResult:
    """Verify one local file against a recorded digest. Never writes."""
    try:
        target = safe_join(root, raw_path)
    except UnsafeManifestPathError as exc:
        return EntryResult(path=raw_path, status=EntryStatus.UNSAFE_PATH, detail=exc.detail)

    if expected_digest is None or expected_digest == "":
        return EntryResult(
            path=raw_path,
            status=EntryStatus.MISSING_HASH,
            detail="no digest recorded in manifest",
        )

    try:
        expected_hex = normalise_digest(expected_digest)
    except (ConfigurationError, UnsupportedHashAlgorithmError) as exc:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.MALFORMED_HASH,
            detail=str(exc),
        )

    # One guarded stat answers existence, regular-file-ness, and size together.
    # `Path.exists()` and `Path.is_file()` swallow only "not found"-shaped errors and
    # re-raise the rest, so calling them unguarded lets a permission error escape and
    # destroy the whole report instead of marking one entry unreadable.
    try:
        stat_result = target.stat()
    except FileNotFoundError:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.MISSING_FILE,
            detail="file named by manifest is not present",
        )
    except NotADirectoryError:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.MISSING_FILE,
            detail="a parent path component is not a directory",
        )
    except OSError as exc:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.UNREADABLE,
            detail=f"could not stat file: {type(exc).__name__}",
        )

    if not S_ISREG(stat_result.st_mode):
        return EntryResult(
            path=raw_path,
            status=EntryStatus.UNREADABLE,
            detail="manifest entry is not a regular file",
        )

    if expected_bytes is not None and stat_result.st_size != expected_bytes:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.SIZE_MISMATCH,
            detail=f"expected {expected_bytes} bytes, found {stat_result.st_size}",
        )

    try:
        actual_hex = hash_file(target)
    except ManifestEntryMissingError:
        # Deleted between the existence check and the read.
        return EntryResult(
            path=raw_path,
            status=EntryStatus.MISSING_FILE,
            detail="file disappeared while the manifest was being verified",
        )
    except (ConfigurationError, OSError) as exc:
        # hash_file wraps read failures in ConfigurationError, so catching OSError alone
        # would never fire. The cause is preserved on the exception; only its type is
        # reported, because a read error must not leak file content.
        return EntryResult(
            path=raw_path,
            status=EntryStatus.UNREADABLE,
            detail=f"could not read file: {type(exc.__cause__ or exc).__name__}",
        )

    if actual_hex != expected_hex:
        return EntryResult(
            path=raw_path,
            status=EntryStatus.HASH_MISMATCH,
            detail=f"expected {expected_hex[:12]}..., computed {actual_hex[:12]}...",
        )
    return EntryResult(path=raw_path, status=EntryStatus.PASS)


# ---------------------------------------------------------------------------
# Bootstrap-shaped manifests
# ---------------------------------------------------------------------------


def verify_bootstrap_manifest(manifest_path: Path, root: Path) -> ManifestReport:
    """Verify a bootstrap-shaped manifest against a working tree.

    .. warning::

       **Do not use this on the repository's real** ``BOOTSTRAP_MANIFEST.json``.

       That manifest is immutable historical evidence about the bootstrap commit, not a
       policy freezing every path it lists (ADR-012). Comparing it against the current
       working tree makes every listed path permanently immutable and raises a false
       integrity alarm the first time a Class C artifact legitimately changes. Use
       :func:`oic.baseline.verify_bootstrap_baseline`, which reads the manifest and every
       listed blob from the pinned commit.

       This function remains for verifying *synthetic* manifests against a tree in tests,
       where the manifest and the tree are meant to describe the same moment.
    """
    display = relative_to_root(root, manifest_path)
    document = _read_json(manifest_path, display)

    files = document.get("files")
    if not isinstance(files, list):
        raise ManifestError(
            "bootstrap manifest has no 'files' array",
            detail=display,
        )

    entries: list[EntryResult] = []
    notes: list[str] = []
    seen: set[str] = set()

    for index, record in enumerate(files):
        if not isinstance(record, dict):
            entries.append(
                EntryResult(
                    path=f"<files[{index}]>",
                    status=EntryStatus.UNREADABLE,
                    detail="entry is not a JSON object",
                )
            )
            continue
        raw_path = record.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            entries.append(
                EntryResult(
                    path=f"<files[{index}]>",
                    status=EntryStatus.UNREADABLE,
                    detail="entry has no 'path' string",
                )
            )
            continue
        if raw_path in seen:
            notes.append(f"duplicate manifest entry for {raw_path}")
        seen.add(raw_path)

        digest = record.get("sha256")
        expected_bytes = record.get("bytes")
        entries.append(
            _check_file(
                root,
                raw_path,
                digest if isinstance(digest, str) else None,
                expected_bytes if isinstance(expected_bytes, int) else None,
            )
        )

    # The governing TDD digest is recorded twice: as a top-level field and as a file
    # entry. Both must agree with the bytes on disk.
    declared_tdd = document.get("governing_tdd_sha256")
    if isinstance(declared_tdd, str) and declared_tdd:
        entries.append(_check_file(root, TDD_PDF_RELPATH, declared_tdd))
        notes.append(f"governing_tdd_sha256 checked against {TDD_PDF_RELPATH}")
    else:
        notes.append("manifest declares no governing_tdd_sha256")

    return ManifestReport(
        manifest_path=display,
        kind=ManifestKind.BOOTSTRAP,
        status=_aggregate(entries),
        entries=_sorted(entries),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# SHA256SUMS
# ---------------------------------------------------------------------------


def verify_sha256sums(manifest_path: Path, root: Path | None = None) -> ManifestReport:
    """Verify a ``SHA256SUMS`` file.

    Names are resolved relative to the manifest's own directory, matching ``sha256sum -c``.
    ``root`` only affects how the manifest path is displayed.
    """
    display_root = root if root is not None else manifest_path.parent
    display = relative_to_root(display_root, manifest_path)
    base = manifest_path.parent

    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError("could not read SHA256SUMS", detail=display) from exc

    entries: list[EntryResult] = []
    notes: list[str] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        digest, separator, name = stripped.partition(" ")
        if not separator or not name.strip():
            entries.append(
                EntryResult(
                    path=f"<line {line_number}>",
                    status=EntryStatus.UNREADABLE,
                    detail="line is not '<digest>  <name>'",
                )
            )
            continue
        # `sha256sum` writes "<digest>  <name>" (text) or "<digest> *<name>" (binary).
        name = name.lstrip().removeprefix("*")
        entries.append(_check_file(base, name, digest))

    if not entries:
        notes.append("no digest lines found")

    return ManifestReport(
        manifest_path=display,
        kind=ManifestKind.SHA256SUMS,
        status=_aggregate(entries, forced_notes=() if entries else ("empty",)),
        entries=_sorted(entries),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# SOURCE_MANIFEST.csv
# ---------------------------------------------------------------------------


def verify_source_manifest(manifest_path: Path, root: Path) -> ManifestReport:
    """Verify the preflight corpus provenance manifest.

    The rows describe external documents that are not checked into this repository, so a
    row can never reach ``PASS`` here: a recorded digest yields
    ``RECORDED_NOT_VERIFIED``, which keeps the manifest INCOMPLETE. The
    ``official_url_or_origin`` column is reported, never fetched.
    """
    display = relative_to_root(root, manifest_path)

    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError("could not read source manifest", detail=display) from exc

    reader = csv.DictReader(text.splitlines())
    header = tuple(reader.fieldnames or ())
    if not header:
        raise ManifestError("source manifest has no header row", detail=display)

    notes: list[str] = []
    missing_columns = [
        column for column in _SOURCE_MANIFEST_REQUIRED_COLUMNS if column not in header
    ]
    if missing_columns:
        notes.append(f"header is missing required columns: {', '.join(missing_columns)}")

    entries: list[EntryResult] = []
    for row_number, row in enumerate(reader, start=2):
        source_id = (row.get("source_id") or "").strip() or f"<row {row_number}>"
        digest = (row.get("sha256") or "").strip()
        if not digest:
            entries.append(
                EntryResult(
                    path=source_id,
                    status=EntryStatus.MISSING_HASH,
                    detail="row records no sha256",
                )
            )
            continue
        try:
            normalise_digest(digest)
        except (ConfigurationError, UnsupportedHashAlgorithmError) as exc:
            entries.append(
                EntryResult(path=source_id, status=EntryStatus.MALFORMED_HASH, detail=str(exc))
            )
            continue
        entries.append(
            EntryResult(
                path=source_id,
                status=EntryStatus.RECORDED_NOT_VERIFIED,
                detail="corpus document is not in the working tree; digest recorded only",
            )
        )

    row_count = len(entries)
    notes.append(f"{row_count} corpus source row(s) recorded")
    notes.append("origin URLs are recorded only; this verifier never fetches them")

    forced: list[str] = []
    if row_count == 0:
        message = (
            "preflight corpus manifest contains only its header: corpus provenance is "
            "NOT complete and this repository is not corpus-ready"
        )
        notes.append(message)
        forced.append(message)

    return ManifestReport(
        manifest_path=display,
        kind=ManifestKind.SOURCE_MANIFEST,
        status=_aggregate(entries, forced_notes=forced),
        entries=_sorted(entries),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

#: Current-tree manifests verified by ``verify_all``, in report order.
#:
#: ``BOOTSTRAP_MANIFEST.json`` is deliberately absent. It describes the bootstrap commit,
#: not the present tree, so it is verified by :func:`oic.baseline.verify_bootstrap_baseline`
#: and surfaced through ``oic verify-bootstrap`` (ADR-012).
KNOWN_MANIFESTS: Final[tuple[tuple[str, ManifestKind], ...]] = (
    (TDD_SHA256SUMS_RELPATH, ManifestKind.SHA256SUMS),
    (SOURCE_MANIFEST_RELPATH, ManifestKind.SOURCE_MANIFEST),
)


def detect_manifest_kind(manifest_path: Path) -> ManifestKind:
    """Infer a manifest's format from its file name.

    Raises:
        ManifestError: the name matches no known manifest format.
    """
    name = manifest_path.name
    if name == "BOOTSTRAP_MANIFEST.json":
        return ManifestKind.BOOTSTRAP
    if name == "SHA256SUMS":
        return ManifestKind.SHA256SUMS
    if name == "SOURCE_MANIFEST.csv":
        return ManifestKind.SOURCE_MANIFEST
    raise ManifestError(
        "cannot infer manifest format from file name",
        detail=f"{name}; pass an explicit --kind",
    )


def verify_manifest(
    manifest_path: Path,
    root: Path,
    kind: ManifestKind | None = None,
) -> ManifestReport:
    """Verify a manifest, inferring its format when ``kind`` is not given."""
    if not manifest_path.exists():
        raise ManifestError(
            "manifest not found",
            detail=relative_to_root(root, manifest_path),
        )
    resolved_kind = kind if kind is not None else detect_manifest_kind(manifest_path)
    if resolved_kind is ManifestKind.BOOTSTRAP:
        raise ConfigurationError(
            "the bootstrap manifest is not verified against the working tree",
            detail=(
                "BOOTSTRAP_MANIFEST.json is historical evidence about the bootstrap "
                "commit (ADR-012); run 'oic verify-bootstrap' instead"
            ),
        )
    if resolved_kind is ManifestKind.SHA256SUMS:
        return verify_sha256sums(manifest_path, root)
    return verify_source_manifest(manifest_path, root)


def verify_all(root: Path) -> tuple[ManifestReport, ...]:
    """Verify every known manifest present in the repository."""
    reports: list[ManifestReport] = []
    for relpath, kind in KNOWN_MANIFESTS:
        path = root / relpath
        if not path.exists():
            reports.append(
                ManifestReport(
                    manifest_path=relpath,
                    kind=kind,
                    status=VerificationStatus.FAIL,
                    entries=(
                        EntryResult(
                            path=relpath,
                            status=EntryStatus.MISSING_FILE,
                            detail="expected manifest is absent from the repository",
                        ),
                    ),
                    notes=(),
                )
            )
            continue
        reports.append(verify_manifest(path, root, kind))
    return tuple(reports)


def worst_status(reports: Sequence[ManifestReport]) -> VerificationStatus:
    """Return the most severe status across ``reports``."""
    if not reports:
        return VerificationStatus.PASS
    return max((report.status for report in reports), key=lambda status: _SEVERITY[status])


def _read_json(path: Path, display: str) -> dict[str, JsonValue]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ManifestError("could not read manifest", detail=display) from exc
    try:
        document: JsonValue = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest is not valid UTF-8 JSON", detail=display) from exc
    if not isinstance(document, dict):
        raise ManifestError("manifest must be a JSON object", detail=display)
    return document
