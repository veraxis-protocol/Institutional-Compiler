#!/usr/bin/env python3
"""Deterministic, fail-closed acquisition helper for the Canada preflight.

The default mode records response metadata only. Source bytes are streamed to
an atomic local quarantine file only when ``--download`` is explicit. This
utility does not interpret or extract content.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Protocol, cast
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "benchmarks/preflight/canada/SOURCE-REGISTRY-PROPOSED-v0.1.json"
DEFAULT_RECEIPT_DIR = REPO_ROOT / ".local/canada-preflight-receipts"
DEFAULT_QUARANTINE_DIR = REPO_ROOT / ".local/canada-preflight-quarantine"

MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 64 * 1024
SAFE_SOURCE_ID = re.compile(r"^[A-Z0-9-]+$")

ALLOWED_DOMAINS = frozenset(
    {
        "achatscanada.canada.ca",
        "canadabuys.canada.ca",
        "laws-lois.justice.gc.ca",
        "lois-laws.justice.gc.ca",
        "www.tbs-sct.canada.ca",
    }
)
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/xml",
        "text/html",
        "text/xml",
    }
)
ALLOWED_TARGET_ROLES = frozenset(
    {
        "CANONICAL_ARTIFACT",
        "CURRENT_SOURCE_UNIT",
        "ARCHIVED_SOURCE_UNIT",
        "METADATA_ONLY_SOURCE",
    }
)


class AcquisitionError(RuntimeError):
    """Raised when an acquisition control fails closed."""


class Readable(Protocol):
    """A bounded-reader surface shared by urllib responses and tests."""

    def read(self, size: int | None = -1) -> bytes: ...


class ResponseLike(Readable, Protocol):
    """Minimum urllib response surface used by the acquisition path."""

    status: int
    headers: Mapping[str, str]

    def __enter__(self) -> ResponseLike: ...

    def __exit__(self, *args: object) -> None: ...

    def geturl(self) -> str: ...


class OpenerLike(Protocol):
    """Minimum opener surface, permitting offline test doubles."""

    def open(self, request: urllib.request.Request, timeout: int) -> ResponseLike: ...


ReceiptWriter = Callable[[Path, bytes], None]
QuarantineWriter = Callable[[Readable, Path, int | None, str | None], tuple[int, str]]
Clock = Callable[[], datetime]


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical UTF-8 JSON while preserving every array's order."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def load_registry(path: Path = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    """Load and minimally validate the proposed source registry."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise AcquisitionError("registry must contain a sources array")
    sources: list[dict[str, Any]] = []
    for value in raw["sources"]:
        if not isinstance(value, dict):
            raise AcquisitionError("every registry source must be an object")
        acquisition_target(value)
        sources.append(value)
    return sources


def acquisition_target(source: Mapping[str, Any]) -> tuple[str, str, str]:
    """Resolve one explicit acquisition target without any legacy fallback."""
    target = source.get("acquisition_target")
    required = {"url", "expected_content_type", "role"}
    if not isinstance(target, Mapping) or set(target) != required:
        raise AcquisitionError(
            "acquisition_target must contain exactly url, expected_content_type, and role"
        )
    url = target.get("url")
    expected_type = target.get("expected_content_type")
    role = target.get("role")
    if not all(isinstance(value, str) and value for value in (url, expected_type, role)):
        raise AcquisitionError("acquisition_target values must be non-empty strings")
    url = cast(str, url)
    expected_type = cast(str, expected_type)
    role = cast(str, role)
    validate_url(url)
    if expected_type not in ALLOWED_CONTENT_TYPES:
        raise AcquisitionError(f"unsupported acquisition target Content-Type: {expected_type}")
    if role not in ALLOWED_TARGET_ROLES:
        raise AcquisitionError(f"unsupported acquisition target role: {role}")
    return url, expected_type, role


def source_by_id(source_id: str, sources: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Resolve one allowlisted registry source or fail closed."""
    matches = [source for source in sources if source.get("source_id") == source_id]
    if len(matches) != 1:
        raise AcquisitionError(f"unknown or duplicate source ID: {source_id}")
    return matches[0]


def validate_url(url: str) -> str:
    """Require HTTPS and an explicitly allowed Government of Canada domain."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise AcquisitionError(f"non-HTTPS URL rejected: {url}")
    if hostname not in ALLOWED_DOMAINS:
        raise AcquisitionError(f"unapproved domain rejected: {hostname or '<missing>'}")
    if parsed.username or parsed.password:
        raise AcquisitionError("credentials in source URL are prohibited")
    return hostname


def validate_content_type(actual: str | None, expected: str) -> str:
    """Require the declared content type and reject unexpected responses."""
    if actual is None:
        raise AcquisitionError("missing Content-Type")
    media_type = actual.split(";", 1)[0].strip().lower()
    if media_type not in ALLOWED_CONTENT_TYPES:
        raise AcquisitionError(f"unexpected Content-Type: {media_type}")
    if media_type != expected:
        raise AcquisitionError(f"expected Content-Type {expected}, received {media_type}")
    return media_type


def validate_output_dir(path: Path, expected: Path) -> Path:
    """Reject ambiguous output destinations outside the fixed local directories."""
    resolved = path.resolve()
    if resolved != expected.resolve():
        raise AcquisitionError(f"output path must be exactly {expected}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


class AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject external redirects and preserve the exact observed redirect order."""

    def __init__(self) -> None:
        super().__init__()
        self.chain: list[str] = []

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        validate_url(newurl)
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser; metadata-only is the default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_ids", nargs="+", help="explicit source IDs from the registry")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--receipt-dir", type=Path, default=DEFAULT_RECEIPT_DIR)
    parser.add_argument("--quarantine-dir", type=Path, default=DEFAULT_QUARANTINE_DIR)
    parser.add_argument(
        "--download",
        action="store_true",
        help="explicitly stream response bytes to the local quarantine directory",
    )
    parser.add_argument(
        "--expected-sha256",
        action="append",
        default=[],
        metavar="SOURCE_ID=DIGEST",
        help="optional expected digest; requires --download and fails on mismatch",
    )
    return parser


def expected_digests(items: Sequence[str], *, download: bool) -> dict[str, str]:
    """Parse explicit digest expectations without accepting duplicates."""
    if items and not download:
        raise AcquisitionError("--expected-sha256 requires --download")
    result: dict[str, str] = {}
    for item in items:
        source_id, separator, digest = item.partition("=")
        if not separator or len(digest) != 64:
            raise AcquisitionError("expected digest must use SOURCE_ID=64_HEX format")
        try:
            int(digest, 16)
        except ValueError as error:
            raise AcquisitionError("expected digest must be hexadecimal") from error
        if source_id in result:
            raise AcquisitionError(f"duplicate expected digest for {source_id}")
        result[source_id] = digest.lower()
    return result


def validate_selection(
    source_ids: Sequence[str],
    sources: Sequence[Mapping[str, Any]],
    expected: Mapping[str, str],
) -> list[Mapping[str, Any]]:
    """Reject duplicate IDs and digest expectations outside the exact selection."""
    if len(source_ids) != len(set(source_ids)):
        raise AcquisitionError("duplicate source IDs are prohibited")
    known = {str(source["source_id"]) for source in sources}
    unknown_expectations = set(expected) - known
    if unknown_expectations:
        raise AcquisitionError(
            f"expected digest names unknown source: {sorted(unknown_expectations)[0]}"
        )
    unselected_expectations = set(expected) - set(source_ids)
    if unselected_expectations:
        raise AcquisitionError(
            f"expected digest names unselected source: {sorted(unselected_expectations)[0]}"
        )
    return [source_by_id(source_id, sources) for source_id in source_ids]


def source_paths(
    sources: Sequence[Mapping[str, Any]],
    receipt_dir: Path,
    quarantine_dir: Path,
) -> dict[str, tuple[Path, Path]]:
    """Resolve unique, traversal-safe final paths for every selected source."""
    result: dict[str, tuple[Path, Path]] = {}
    final_paths: set[Path] = set()
    for source in sources:
        source_id = str(source["source_id"])
        if not SAFE_SOURCE_ID.fullmatch(source_id):
            raise AcquisitionError(f"unsafe source ID: {source_id}")
        _, content_type, _ = acquisition_target(source)
        suffix = ".pdf" if content_type == "application/pdf" else ".source"
        receipt_path = receipt_dir / f"{source_id}.receipt.json"
        quarantine_path = quarantine_dir / f"{source_id}{suffix}"
        for path in (receipt_path, quarantine_path):
            if path in final_paths:
                raise AcquisitionError(f"multiple operations target final path: {path}")
            final_paths.add(path)
        result[source_id] = (receipt_path, quarantine_path)
    return result


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    return value if value else None


def _content_length(headers: Mapping[str, str]) -> int | None:
    value = _header(headers, "Content-Length")
    if value is None:
        return None
    try:
        length = int(value)
    except ValueError as error:
        raise AcquisitionError("invalid Content-Length") from error
    if length < 0:
        raise AcquisitionError("negative Content-Length")
    return length


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(DOWNLOAD_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Flush, close, and atomically replace one final file."""
    part_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".part",
            delete=False,
        ) as stream:
            part_path = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        part_path.replace(path)
    finally:
        if part_path is not None:
            part_path.unlink(missing_ok=True)


def stream_to_quarantine(
    response: Readable,
    target: Path,
    content_length: int | None,
    expected_digest: str | None,
    *,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> tuple[int, str]:
    """Stream bounded bytes to a temporary file and atomically commit or reuse."""
    if content_length is not None and content_length > max_bytes:
        raise AcquisitionError(
            f"Content-Length {content_length} exceeds maximum download size {max_bytes}"
        )

    part_path: Path | None = None
    actual_length = 0
    digest = hashlib.sha256()
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".part",
            delete=False,
        ) as stream:
            part_path = Path(stream.name)
            while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                actual_length += len(chunk)
                if actual_length > max_bytes:
                    raise AcquisitionError(f"download exceeds maximum size {max_bytes}")
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())

        actual_digest = digest.hexdigest()
        if expected_digest is not None and actual_digest != expected_digest:
            raise AcquisitionError("SHA-256 mismatch")
        if target.exists():
            if _sha256_file(target) != actual_digest:
                raise AcquisitionError("existing quarantine artifact differs; overwrite prohibited")
            part_path.unlink()
            part_path = None
            return actual_length, actual_digest
        part_path.replace(target)
        part_path = None
        return actual_length, actual_digest
    finally:
        if part_path is not None:
            part_path.unlink(missing_ok=True)


def make_receipt(
    *,
    source_id: str,
    acquisition_target_role: str,
    acquisition_target_url: str,
    registry_source_url: str,
    requested_url: str,
    final_url: str,
    redirects: Sequence[str],
    status: int,
    headers: Mapping[str, str],
    content_type: str,
    downloaded: bool,
    actual_byte_length: int | None,
    digest: str | None,
    retrieved_at: str,
) -> dict[str, object]:
    return {
        "acquisition_target_role": acquisition_target_role,
        "acquisition_target_url": acquisition_target_url,
        "actual_byte_length": actual_byte_length,
        "content_length_header": _content_length(headers),
        "content_type": content_type,
        "downloaded": downloaded,
        "etag": _header(headers, "ETag"),
        "final_url": final_url,
        "http_status": status,
        "last_modified": _header(headers, "Last-Modified"),
        "redirect_chain": list(redirects),
        "registry_source_url": registry_source_url,
        "requested_url": requested_url,
        "retrieval_utc": retrieved_at,
        "sha256": digest,
        "source_id": source_id,
    }


def utc_now() -> datetime:
    """Return the current UTC observation time."""
    return datetime.now(UTC)


def acquire_one(
    source: Mapping[str, Any],
    *,
    download: bool,
    receipt_path: Path,
    quarantine_path: Path,
    expected_digest: str | None,
    opener: OpenerLike | None = None,
    clock: Clock = utc_now,
    quarantine_writer: QuarantineWriter = stream_to_quarantine,
    receipt_writer: ReceiptWriter = atomic_write_bytes,
) -> dict[str, object]:
    """Acquire metadata and optionally quarantine bounded bytes for one source."""
    source_id = str(source["source_id"])
    registry_source_url = str(source["official_english_url"])
    validate_url(registry_source_url)
    requested_url, expected_type, target_role = acquisition_target(source)

    redirect_handler = AllowlistRedirectHandler()
    selected_opener = opener or cast(OpenerLike, urllib.request.build_opener(redirect_handler))
    request = urllib.request.Request(  # noqa: S310 - URL is HTTPS/domain validated above.
        requested_url,
        method="GET",
        headers={"User-Agent": "OIC-Canada-Preflight/0.1 (+metadata-and-rights-research)"},
    )
    try:
        with selected_opener.open(request, timeout=30) as response:
            final_url = response.geturl()
            validate_url(final_url)
            status = int(response.status)
            if status != 200:
                raise AcquisitionError(f"{source_id}: HTTP {status}")
            headers = dict(response.headers.items())
            content_type = validate_content_type(
                response.headers.get("Content-Type"), expected_type
            )
            supplied_length = _content_length(headers)
            if download and supplied_length is not None and supplied_length > MAX_DOWNLOAD_BYTES:
                raise AcquisitionError(
                    f"Content-Length {supplied_length} exceeds maximum download size "
                    f"{MAX_DOWNLOAD_BYTES}"
                )

            observed_at = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
            actual_length: int | None = None
            digest: str | None = None
            if download:
                actual_length, digest = quarantine_writer(
                    response,
                    quarantine_path,
                    supplied_length,
                    expected_digest,
                )
    except (urllib.error.URLError, TimeoutError) as error:
        raise AcquisitionError(f"{source_id}: retrieval failed: {error}") from error

    receipt = make_receipt(
        source_id=source_id,
        acquisition_target_role=target_role,
        acquisition_target_url=requested_url,
        registry_source_url=registry_source_url,
        requested_url=requested_url,
        final_url=final_url,
        redirects=redirect_handler.chain,
        status=status,
        headers=headers,
        content_type=content_type,
        downloaded=download,
        actual_byte_length=actual_length,
        digest=digest,
        retrieved_at=observed_at,
    )
    receipt_writer(receipt_path, canonical_json_bytes(receipt))
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit source acquisitions and write canonical local receipts."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        sources = load_registry(args.registry)
        expected = expected_digests(args.expected_sha256, download=args.download)
        receipt_dir = validate_output_dir(args.receipt_dir, DEFAULT_RECEIPT_DIR)
        quarantine_dir = validate_output_dir(args.quarantine_dir, DEFAULT_QUARANTINE_DIR)
        selected = validate_selection(args.source_ids, sources, expected)
        paths = source_paths(selected, receipt_dir, quarantine_dir)
        for source in sorted(selected, key=lambda item: str(item["source_id"])):
            source_id = str(source["source_id"])
            receipt_path, quarantine_path = paths[source_id]
            acquire_one(
                source,
                download=args.download,
                receipt_path=receipt_path,
                quarantine_path=quarantine_path,
                expected_digest=expected.get(source_id),
            )
    except (AcquisitionError, KeyError, OSError, ValueError) as error:
        print(f"acquisition failed closed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
