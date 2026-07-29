"""Tests for deterministic artifact hashing.

Fixture digests are documented in ``tests/fixtures/hashing/README.md``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from oic.errors import (
    ConfigurationError,
    HashMismatchError,
    ManifestEntryMissingError,
    UnsupportedHashAlgorithmError,
)
from oic.hashing import (
    DEFAULT_CHUNK_SIZE,
    SUPPORTED_ALGORITHMS,
    canonical_digest,
    digests_equal,
    hash_bytes,
    hash_file,
    hash_stream,
    normalise_digest,
    verify_file,
)

# NIST FIPS 180-4 published SHA-256 vectors.
EMPTY_VECTOR = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_VECTOR = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
ALL_BYTES_DIGEST = "40aff2e9d2d8922e47afd4648e6967497158785fbd1da870e7110266bf944880"
CRLF_DIGEST = "98ab4d3aeab1e120560e942e2df6a0db1147bf94bafcf1590000ffb3c2b6fc80"
LF_DIGEST = "e49c81e2d2f84e259d40e2fb8192f3bcd198b355184845d76d8f58807d0d78ee"


@pytest.fixture
def hashing_fixtures(fixtures_dir: Path) -> Path:
    return fixtures_dir / "hashing"


# ---------------------------------------------------------------------------
# Known vectors
# ---------------------------------------------------------------------------


def test_known_standard_vectors_in_memory() -> None:
    assert hash_bytes(b"") == EMPTY_VECTOR
    assert hash_bytes(b"abc") == ABC_VECTOR


def test_empty_file(hashing_fixtures: Path) -> None:
    assert hash_file(hashing_fixtures / "empty.bin") == EMPTY_VECTOR


def test_text_file_matches_known_vector(hashing_fixtures: Path) -> None:
    assert hash_file(hashing_fixtures / "abc.txt") == ABC_VECTOR


def test_binary_file_including_nul_bytes(hashing_fixtures: Path) -> None:
    path = hashing_fixtures / "all-bytes.bin"
    assert path.read_bytes() == bytes(range(256))
    assert hash_file(path) == ALL_BYTES_DIGEST


def test_no_platform_dependent_newline_normalisation(hashing_fixtures: Path) -> None:
    """CRLF and LF content must hash differently.

    If these ever match, some part of the toolchain is rewriting line endings and the
    byte-exact guarantee no longer holds.
    """
    crlf = hash_file(hashing_fixtures / "crlf.txt")
    lf = hash_file(hashing_fixtures / "lf.txt")
    assert crlf == CRLF_DIGEST
    assert lf == LF_DIGEST
    assert crlf != lf


def test_hashing_does_not_mutate_the_file(hashing_fixtures: Path, tmp_path: Path) -> None:
    source = hashing_fixtures / "crlf.txt"
    target = tmp_path / "copy.txt"
    target.write_bytes(source.read_bytes())
    before = target.read_bytes()
    stat_before = target.stat().st_size
    hash_file(target)
    assert target.read_bytes() == before
    assert target.stat().st_size == stat_before


# ---------------------------------------------------------------------------
# Streaming behaviour
# ---------------------------------------------------------------------------


def test_output_is_stable_lowercase_hex(hashing_fixtures: Path) -> None:
    digest = hash_file(hashing_fixtures / "all-bytes.bin")
    assert digest == digest.lower()
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


@pytest.mark.parametrize("chunk_size", [1, 3, 7, 256, 4096, DEFAULT_CHUNK_SIZE])
def test_chunk_size_does_not_change_the_digest(hashing_fixtures: Path, chunk_size: int) -> None:
    path = hashing_fixtures / "all-bytes.bin"
    assert hash_file(path, chunk_size=chunk_size) == ALL_BYTES_DIGEST


def test_stream_is_read_incrementally() -> None:
    """The stream must be consumed in chunks, never slurped whole."""
    payload = bytes(range(256)) * 8
    reads: list[int] = []

    class RecordingStream(io.BytesIO):
        def read(self, size: int | None = -1, /) -> bytes:
            reads.append(-1 if size is None else size)
            return super().read(size)

    digest = hash_stream(RecordingStream(payload), chunk_size=64)
    assert digest == hash_bytes(payload)
    assert reads, "stream was never read"
    assert all(size == 64 for size in reads), reads


def test_non_positive_chunk_size_is_refused() -> None:
    with pytest.raises(ConfigurationError):
        hash_stream(io.BytesIO(b"x"), chunk_size=0)


# ---------------------------------------------------------------------------
# Algorithm restriction
# ---------------------------------------------------------------------------


def test_only_sha256_is_supported() -> None:
    assert set(SUPPORTED_ALGORITHMS) == {"sha256"}


@pytest.mark.parametrize("algorithm", ["md5", "sha1", "sha512", "SHA256", "sha-256", ""])
def test_unsupported_algorithms_are_refused(algorithm: str) -> None:
    with pytest.raises(UnsupportedHashAlgorithmError) as excinfo:
        hash_bytes(b"x", algorithm=algorithm)
    assert excinfo.value.code == "OIC-1004"


def test_unsupported_algorithm_refused_for_files_too(hashing_fixtures: Path) -> None:
    with pytest.raises(UnsupportedHashAlgorithmError):
        hash_file(hashing_fixtures / "abc.txt", algorithm="sha512")


# ---------------------------------------------------------------------------
# Canonical form
# ---------------------------------------------------------------------------


def test_canonical_digest_round_trip() -> None:
    canonical = canonical_digest(ABC_VECTOR)
    assert canonical == f"sha256:{ABC_VECTOR}"
    assert normalise_digest(canonical) == ABC_VECTOR


def test_canonical_form_matches_the_schema_pattern() -> None:
    """The draft schemas require ^sha256:[0-9a-f]{64}$ for content hashes."""
    import re

    pattern = re.compile(r"^sha256:[0-9a-f]{64}$")
    assert pattern.fullmatch(canonical_digest(EMPTY_VECTOR))


def test_bare_hex_is_accepted_by_normalise() -> None:
    assert normalise_digest(ABC_VECTOR) == ABC_VECTOR


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "abc",
        ABC_VECTOR[:-1],
        ABC_VECTOR + "0",
        ABC_VECTOR.upper(),
        f"sha256:{ABC_VECTOR.upper()}",
        f"sha256:{ABC_VECTOR[:-1]}",
        "sha256:",
        f"sha256:{ABC_VECTOR}:extra",
        "not a digest at all",
    ],
)
def test_malformed_digests_are_refused(malformed: str) -> None:
    with pytest.raises(ConfigurationError) as excinfo:
        normalise_digest(malformed)
    assert excinfo.value.code == "OIC-1001"


@pytest.mark.parametrize("value", [f"md5:{'0' * 32}", f"sha1:{'0' * 40}"])
def test_digest_with_foreign_algorithm_prefix_is_refused(value: str) -> None:
    with pytest.raises(UnsupportedHashAlgorithmError):
        normalise_digest(value)


def test_canonical_digest_refuses_malformed_input() -> None:
    with pytest.raises(ConfigurationError):
        canonical_digest("nope")


def test_digests_equal_across_forms() -> None:
    assert digests_equal(ABC_VECTOR, f"sha256:{ABC_VECTOR}")
    assert not digests_equal(ABC_VECTOR, EMPTY_VECTOR)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def test_verify_file_accepts_matching_digest(hashing_fixtures: Path) -> None:
    assert verify_file(hashing_fixtures / "abc.txt", f"sha256:{ABC_VECTOR}") == ABC_VECTOR


def test_verify_file_raises_on_mismatch(hashing_fixtures: Path) -> None:
    wrong = "0" * 64
    with pytest.raises(HashMismatchError) as excinfo:
        verify_file(hashing_fixtures / "abc.txt", wrong, subject="abc.txt")
    error = excinfo.value
    assert error.code == "OIC-2004"
    assert error.expected == wrong
    assert error.actual == ABC_VECTOR
    assert error.subject == "abc.txt"


def test_verify_file_refuses_malformed_expected_digest_before_reading(
    hashing_fixtures: Path,
) -> None:
    with pytest.raises(ConfigurationError):
        verify_file(hashing_fixtures / "abc.txt", "sha256:zzzz")


def test_missing_file_is_reported_as_missing_not_as_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ManifestEntryMissingError) as excinfo:
        hash_file(tmp_path / "absent.bin")
    assert excinfo.value.code == "OIC-2003"


def test_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        hash_file(tmp_path)


def test_error_messages_never_include_file_content(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET-PAYLOAD", encoding="utf-8")
    with pytest.raises(HashMismatchError) as excinfo:
        verify_file(secret, "0" * 64)
    assert "TOP-SECRET-PAYLOAD" not in str(excinfo.value)
    assert "TOP-SECRET-PAYLOAD" not in repr(excinfo.value)
