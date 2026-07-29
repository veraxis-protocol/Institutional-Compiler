"""Repository root detection and relative-path safety.

Every other infrastructure module resolves artifacts relative to a repository root, and
every manifest verifier must refuse paths that escape it. Both concerns live here so the
containment rule is written once.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from oic.errors import ConfigurationError, UnsafeManifestPathError

__all__ = [
    "BOOTSTRAP_MANIFEST_RELPATH",
    "REPO_ROOT_ENV_VAR",
    "SOURCE_MANIFEST_RELPATH",
    "TDD_PDF_RELPATH",
    "TDD_SHA256SUMS_RELPATH",
    "find_repo_root",
    "relative_to_root",
    "safe_join",
]

REPO_ROOT_ENV_VAR = "OIC_REPO_ROOT"

#: Presence of this file identifies an OIC repository root unambiguously.
_ROOT_MARKER = "BOOTSTRAP_MANIFEST.json"

BOOTSTRAP_MANIFEST_RELPATH = "BOOTSTRAP_MANIFEST.json"
TDD_SHA256SUMS_RELPATH = "docs/tdd/SHA256SUMS"
TDD_PDF_RELPATH = "docs/tdd/TDD-OIC-001-v1.1.pdf"
SOURCE_MANIFEST_RELPATH = "benchmarks/preflight/SOURCE_MANIFEST.csv"


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the repository root.

    Resolution order: the ``OIC_REPO_ROOT`` environment variable, then an upward walk
    from ``start`` (default: the current working directory) looking for the bootstrap
    manifest.

    Raises:
        ConfigurationError: if no root can be identified.
    """
    override = os.environ.get(REPO_ROOT_ENV_VAR)
    if override:
        candidate = Path(override).expanduser()
        if not (candidate / _ROOT_MARKER).is_file():
            raise ConfigurationError(
                f"{REPO_ROOT_ENV_VAR} does not point at an OIC repository root",
                detail=f"expected {_ROOT_MARKER} under {candidate}",
            )
        return candidate.resolve()

    origin = (start or Path.cwd()).resolve()
    for directory in (origin, *origin.parents):
        if (directory / _ROOT_MARKER).is_file():
            return directory

    raise ConfigurationError(
        "could not locate an OIC repository root",
        detail=f"no {_ROOT_MARKER} found at or above {origin}",
    )


def _reject(raw: str, reason: str) -> UnsafeManifestPathError:
    return UnsafeManifestPathError(
        "refusing to resolve unsafe manifest path",
        detail=f"{reason}: {raw!r}",
    )


def safe_join(root: Path, raw: str) -> Path:
    """Resolve a manifest-declared relative path underneath ``root``.

    The path is refused, never repaired. Rejected forms:

    * empty or whitespace-only;
    * anything containing ``://`` (a URI - manifests never cause a fetch);
    * absolute POSIX paths, UNC paths, and drive-qualified Windows paths;
    * any ``..`` component;
    * paths that resolve outside ``root``, including through a symlink.

    Raises:
        UnsafeManifestPathError: if the path is refused.
    """
    if not raw or not raw.strip():
        raise _reject(raw, "empty path")
    if "\x00" in raw:
        raise _reject(raw, "path contains a NUL byte")
    if "://" in raw:
        raise _reject(raw, "path looks like a URI and would imply a network fetch")

    normalised = raw.replace("\\", "/")
    if normalised.startswith("/"):
        raise _reject(raw, "absolute path")
    if len(normalised) >= 2 and normalised[1] == ":":
        raise _reject(raw, "drive-qualified path")

    pure = PurePosixPath(normalised)
    if any(part == ".." for part in pure.parts):
        raise _reject(raw, "parent-directory traversal")

    root_resolved = root.resolve()
    candidate = root_resolved.joinpath(*pure.parts)
    resolved = candidate.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise _reject(raw, "path resolves outside the repository root")
    return candidate


def relative_to_root(root: Path, path: Path) -> str:
    """Render ``path`` as a POSIX path relative to ``root``.

    Output is deterministic and machine-independent, so it is safe to place in JSON
    output that gets compared across environments. Paths outside ``root`` fall back to
    their own POSIX form rather than raising, because this is a formatting helper and
    must not mask the caller's real error.
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
