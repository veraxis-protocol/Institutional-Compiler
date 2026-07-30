#!/usr/bin/env python3
"""Deterministic, fail-closed acquisition helper for the Canada preflight.

The default mode records response metadata only. Source bytes are written only
when ``--download`` is explicitly supplied, and only beneath the gitignored
local quarantine directory. This utility does not interpret or extract content.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, cast
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "benchmarks/preflight/canada/SOURCE-REGISTRY-PROPOSED-v0.1.json"
DEFAULT_RECEIPT_DIR = REPO_ROOT / ".local/canada-preflight-receipts"
DEFAULT_QUARANTINE_DIR = REPO_ROOT / ".local/canada-preflight-quarantine"

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


class AcquisitionError(RuntimeError):
    """Raised when an acquisition control fails closed."""


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical UTF-8 JSON with stable key and array ordering."""
    normalized = _normalize(value)
    return (
        json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _normalize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        normalized = [_normalize(item) for item in value]
        if all(isinstance(item, str) for item in normalized):
            return sorted(cast(list[str], normalized))
        return normalized
    return value


def load_registry(path: Path = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    """Load and minimally validate the proposed source registry."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise AcquisitionError("registry must contain a sources array")
    sources: list[dict[str, Any]] = []
    for value in raw["sources"]:
        if not isinstance(value, dict):
            raise AcquisitionError("every registry source must be an object")
        sources.append(value)
    return sources


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
    """Reject redirect targets outside the exact official-domain allowlist."""

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
        help="explicitly write response bytes to the local quarantine directory",
    )
    parser.add_argument(
        "--expected-sha256",
        action="append",
        default=[],
        metavar="SOURCE_ID=DIGEST",
        help="optional expected digest; requires --download and fails on mismatch",
    )
    return parser


def _expected_digests(items: Sequence[str], *, download: bool) -> dict[str, str]:
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


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    return value if value else None


def _receipt(
    *,
    source_id: str,
    requested_url: str,
    final_url: str,
    redirects: Sequence[str],
    status: int,
    headers: Mapping[str, str],
    content_type: str,
    downloaded: bytes | None,
    retrieved_at: str,
) -> dict[str, object]:
    supplied_length = _header(headers, "Content-Length")
    return {
        "actual_byte_length": len(downloaded) if downloaded is not None else None,
        "content_length_header": int(supplied_length) if supplied_length is not None else None,
        "content_type": content_type,
        "downloaded": downloaded is not None,
        "etag": _header(headers, "ETag"),
        "final_url": final_url,
        "http_status": status,
        "last_modified": _header(headers, "Last-Modified"),
        "redirect_chain": list(redirects),
        "requested_url": requested_url,
        "retrieval_utc": retrieved_at,
        "sha256": hashlib.sha256(downloaded).hexdigest() if downloaded is not None else None,
        "source_id": source_id,
    }


def acquire_one(
    source: Mapping[str, Any],
    *,
    download: bool,
    receipt_dir: Path,
    quarantine_dir: Path,
    expected_digest: str | None,
) -> dict[str, object]:
    """Acquire metadata and optionally quarantine bytes for one explicit source."""
    source_id = str(source["source_id"])
    requested_url = str(source["official_english_url"])
    validate_url(requested_url)
    expected_type = str(source["expected_content_type"])

    redirect_handler = AllowlistRedirectHandler()
    opener = urllib.request.build_opener(redirect_handler)
    request = urllib.request.Request(
        requested_url,
        method="GET",
        headers={"User-Agent": "OIC-Canada-Preflight/0.1 (+metadata-and-rights-research)"},
    )
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        with opener.open(request, timeout=30) as response:
            final_url = response.geturl()
            validate_url(final_url)
            status = int(response.status)
            if status != 200:
                raise AcquisitionError(f"{source_id}: HTTP {status}")
            headers = dict(response.headers.items())
            content_type = validate_content_type(response.headers.get("Content-Type"), expected_type)
            payload = response.read() if download else None
    except (urllib.error.URLError, TimeoutError) as error:
        raise AcquisitionError(f"{source_id}: retrieval failed: {error}") from error

    receipt = _receipt(
        source_id=source_id,
        requested_url=requested_url,
        final_url=final_url,
        redirects=redirect_handler.chain,
        status=status,
        headers=headers,
        content_type=content_type,
        downloaded=payload,
        retrieved_at=retrieved_at,
    )
    if expected_digest is not None and receipt["sha256"] != expected_digest:
        raise AcquisitionError(f"{source_id}: SHA-256 mismatch")

    receipt_path = receipt_dir / f"{source_id}.receipt.json"
    receipt_path.write_bytes(canonical_json_bytes(receipt))
    if payload is not None:
        suffix = ".pdf" if content_type == "application/pdf" else ".source"
        (quarantine_dir / f"{source_id}{suffix}").write_bytes(payload)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit source acquisitions and write canonical local receipts."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        sources = load_registry(args.registry)
        expected = _expected_digests(args.expected_sha256, download=args.download)
        receipt_dir = validate_output_dir(args.receipt_dir, DEFAULT_RECEIPT_DIR)
        quarantine_dir = validate_output_dir(args.quarantine_dir, DEFAULT_QUARANTINE_DIR)
        selected = [source_by_id(source_id, sources) for source_id in args.source_ids]
        for source in sorted(selected, key=lambda item: str(item["source_id"])):
            source_id = str(source["source_id"])
            acquire_one(
                source,
                download=args.download,
                receipt_dir=receipt_dir,
                quarantine_dir=quarantine_dir,
                expected_digest=expected.get(source_id),
            )
    except (AcquisitionError, KeyError, ValueError) as error:
        print(f"acquisition failed closed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
