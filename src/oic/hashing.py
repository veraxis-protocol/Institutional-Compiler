"""Deterministic artifact hashing.

Scope
-----
This module verifies *bytes*. It establishes nothing about a document's source
authority, institutional validity, provenance, or semantic equivalence. A matching
digest means two byte sequences are identical and nothing more. Do not cite a result
from this module as evidence that a source is authentic or that an interpretation is
correct.

Contract for v0.1
-----------------
* SHA-256 only. Other algorithms are refused, not silently accepted.
* Files are streamed, so hashing does not depend on a file fitting in memory.
* Byte-exact: opened in binary mode, with no newline, encoding, or whitespace
  normalisation, and no mutation of the file being read.
* Output is lowercase hexadecimal.
* The canonical serialised form is ``sha256:<64 lowercase hex chars>``, matching the
  ``^sha256:[0-9a-f]{64}$`` pattern already required by the draft schemas.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import IO, Final

from oic.errors import (
    ConfigurationError,
    HashMismatchError,
    ManifestEntryMissingError,
    UnsupportedHashAlgorithmError,
)

__all__ = [
    "CANONICAL_DIGEST_PATTERN",
    "DEFAULT_CHUNK_SIZE",
    "SUPPORTED_ALGORITHMS",
    "canonical_digest",
    "digests_equal",
    "hash_bytes",
    "hash_file",
    "hash_stream",
    "normalise_digest",
    "verify_file",
]

#: The only algorithm admitted in v0.1. Widening this set is a contract change.
SUPPORTED_ALGORITHMS: Final[frozenset[str]] = frozenset({"sha256"})

_HEX_DIGEST_LENGTH: Final[int] = 64
DEFAULT_CHUNK_SIZE: Final[int] = 1 << 20  # 1 MiB

CANONICAL_DIGEST_PATTERN: Final[str] = r"^sha256:[0-9a-f]{64}$"
_CANONICAL_RE: Final[re.Pattern[str]] = re.compile(CANONICAL_DIGEST_PATTERN)
_BARE_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


def _require_supported(algorithm: str) -> str:
    """Return the algorithm name, or refuse it.

    The comparison is case-sensitive on purpose: manifests record ``sha256`` and an
    entry spelled differently is a manifest defect worth surfacing, not normalising.
    """
    if algorithm not in SUPPORTED_ALGORITHMS:
        supported = ", ".join(sorted(SUPPORTED_ALGORITHMS))
        raise UnsupportedHashAlgorithmError(
            f"unsupported hash algorithm {algorithm!r}",
            detail=f"v0.1 supports only: {supported}",
        )
    return algorithm


def hash_stream(
    stream: IO[bytes],
    *,
    algorithm: str = "sha256",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Hash a binary stream incrementally and return lowercase hex."""
    _require_supported(algorithm)
    if chunk_size <= 0:
        raise ConfigurationError(
            "chunk_size must be positive",
            detail=f"received {chunk_size}",
        )
    digest = hashlib.sha256()
    while chunk := stream.read(chunk_size):
        digest.update(chunk)
    return digest.hexdigest()


def hash_bytes(data: bytes, *, algorithm: str = "sha256") -> str:
    """Hash an in-memory byte string and return lowercase hex."""
    _require_supported(algorithm)
    return hashlib.sha256(data).hexdigest()


def hash_file(
    path: Path,
    *,
    algorithm: str = "sha256",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Hash a file's bytes and return lowercase hex.

    The file is streamed, opened in binary mode, and never modified.

    Raises:
        ManifestEntryMissingError: the path does not exist or is not a regular file.
        ConfigurationError: the file exists but cannot be read.
        UnsupportedHashAlgorithmError: ``algorithm`` is not SHA-256.
    """
    _require_supported(algorithm)
    if not path.exists():
        raise ManifestEntryMissingError(
            "file not found",
            detail=path.as_posix(),
        )
    if not path.is_file():
        raise ConfigurationError(
            "path is not a regular file",
            detail=path.as_posix(),
        )
    try:
        with path.open("rb") as handle:
            return hash_stream(handle, algorithm=algorithm, chunk_size=chunk_size)
    except OSError as exc:
        raise ConfigurationError(
            "could not read file for hashing",
            detail=path.as_posix(),
        ) from exc


def canonical_digest(hex_digest: str, *, algorithm: str = "sha256") -> str:
    """Render a bare hex digest in the canonical ``sha256:<hex>`` form."""
    _require_supported(algorithm)
    if not _BARE_HEX_RE.fullmatch(hex_digest):
        raise ConfigurationError(
            "malformed digest",
            detail=(
                f"expected {_HEX_DIGEST_LENGTH} lowercase hex characters, "
                f"got {len(hex_digest)} characters"
            ),
        )
    return f"{algorithm}:{hex_digest}"


def normalise_digest(value: str) -> str:
    """Accept either canonical or bare-hex form and return the bare lowercase hex.

    Uppercase hex is refused rather than lowercased: manifests are byte-exact records,
    and quietly accepting a variant spelling would let two manifests that disagree
    textually both appear to pass.

    Raises:
        UnsupportedHashAlgorithmError: the value carries a non-SHA-256 prefix.
        ConfigurationError: the value is not a well-formed digest.
    """
    if ":" in value:
        prefix, _, remainder = value.partition(":")
        _require_supported(prefix)
        if not _CANONICAL_RE.fullmatch(value):
            raise ConfigurationError(
                "malformed canonical digest",
                detail=f"expected {CANONICAL_DIGEST_PATTERN}, got {len(remainder)} hex characters",
            )
        return remainder
    if not _BARE_HEX_RE.fullmatch(value):
        raise ConfigurationError(
            "malformed digest",
            detail=(
                f"expected {_HEX_DIGEST_LENGTH} lowercase hex characters "
                f"or the canonical sha256:<hex> form, got {len(value)} characters"
            ),
        )
    return value


def digests_equal(left: str, right: str) -> bool:
    """Compare two digests written in either accepted form."""
    return normalise_digest(left) == normalise_digest(right)


def verify_file(path: Path, expected: str, *, subject: str | None = None) -> str:
    """Verify a file against an expected digest and return the computed hex.

    ``expected`` may be canonical or bare hex.

    Raises:
        HashMismatchError: the computed digest differs from ``expected``.
    """
    expected_hex = normalise_digest(expected)
    actual_hex = hash_file(path)
    if actual_hex != expected_hex:
        raise HashMismatchError(
            subject=subject or path.as_posix(),
            expected=expected_hex,
            actual=actual_hex,
        )
    return actual_hex
