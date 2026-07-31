#!/usr/bin/env python3
"""Exact-byte acquisition and freeze for rights-cleared Canada corpus sources.

Every request targets the explicit acquisition target. There is no fallback to a
provenance URL, and a source whose rights disposition is BLOCKED_PENDING_CLEARANCE
is never requested. Bytes are preserved exactly as received.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acquire_canada_preflight import (
    AcquisitionError,
    AllowlistRedirectHandler,
    OpenerLike,
    atomic_write_bytes,
    canonical_json_bytes,
    validate_content_type,
    validate_url,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = REPO_ROOT / "benchmarks/corpus/canada/freeze-v0.1"
RIGHTS_PATH = FREEZE_DIR / "RIGHTS-CLEARANCE-v0.1.json"
RECEIPT_DIR = FREEZE_DIR / "receipts"
REPOSITORY_BYTES_DIR = FREEZE_DIR / "sources"
INTERNAL_BYTES_DIR = REPO_ROOT / ".local/canada-freeze-internal"

TOOL_NAME = "freeze_canada_corpus"
TOOL_VERSION = "0.1.0"
USER_AGENT = f"OIC-Canada-Freeze/{TOOL_VERSION} (+rights-cleared-exact-byte-freeze)"
MAX_BYTES = 64 * 1024 * 1024

BLOCKED = "BLOCKED_PENDING_CLEARANCE"
REPOSITORY_FREEZE = "CLEAR_REPOSITORY_FREEZE"
INTERNAL_FREEZE = "CLEAR_INTERNAL_FREEZE_ONLY"

SUFFIX_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/xml": ".xml",
    "text/html": ".html",
    "text/xml": ".xml",
}

# Leading bytes that prove a response is a rendered HTML page rather than the
# XML or PDF artifact that was requested.
HTML_SIGNATURES = (b"<!doctype html", b"<html", b"<!--", b"<head", b"<body")


def utc_now() -> str:
    """Return the acquisition observation time in UTC."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _leading(data: bytes) -> bytes:
    return data[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()


def validate_magic(content_type: str, data: bytes, source_id: str) -> None:
    """Reject a body whose file signature contradicts its declared media type."""
    leading = _leading(data)
    if content_type == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise AcquisitionError(f"{source_id}: PDF target did not return a PDF signature")
        return
    if content_type in {"application/xml", "text/xml"}:
        if any(leading.startswith(signature) for signature in HTML_SIGNATURES):
            raise AcquisitionError(f"{source_id}: XML target returned an HTML page")
        if not leading.startswith((b"<?xml", b"<")):
            raise AcquisitionError(f"{source_id}: XML target did not return XML")
        try:
            ElementTree.fromstring(data)  # noqa: S314 - structural well-formedness only.
        except ElementTree.ParseError as error:
            raise AcquisitionError(f"{source_id}: XML target is not well formed: {error}") from (
                error
            )
        return
    if content_type == "text/html" and not leading.startswith(HTML_SIGNATURES):
        raise AcquisitionError(f"{source_id}: HTML target did not return HTML")


def screen_bytes(data: bytes) -> dict[str, Any]:
    """Record mechanical presence flags. This inspects markers, never meaning."""
    lowered = data.lower()
    symbol_markers = (b"wordmark", b"coat of arms", b"arms of canada", b"flag symbol")
    contact_markers = (b"mailto:", b"@canada.ca", b"telephone", b"t\xc3\xa9l\xc3\xa9phone")
    return {
        "logo_insignia_trademark_markers_present": any(m in lowered for m in symbol_markers),
        "embedded_binary_image_present": any(
            marker in data for marker in (b"\x89PNG\r\n", b"\xff\xd8\xff", b"GIF8")
        ),
        "contact_or_personal_information_markers_present": any(
            m in lowered for m in contact_markers
        ),
        "external_reference_markers_present": b"http://" in lowered or b"https://" in lowered,
        "screening_note": (
            "Mechanical marker presence only. It is not a legal finding about third-party "
            "material, personal information, or trademark use."
        ),
    }


def acquire(
    record: Mapping[str, Any], *, opener: OpenerLike | None = None
) -> tuple[dict[str, Any], bytes]:
    """Request exactly one acquisition target and return its receipt and raw bytes."""
    source_id = str(record["source_id"])
    disposition = str(record["reviewer_disposition"])
    if disposition == BLOCKED:
        raise AcquisitionError(f"{source_id}: blocked sources must never be requested")
    if not record.get("acquisition_permitted"):
        raise AcquisitionError(f"{source_id}: acquisition is not permitted by the rights record")
    if record["automated_retrieval_permission"] != "SUPPORTED":
        raise AcquisitionError(f"{source_id}: automated retrieval is not supported")
    if record["internal_research_use"] != "SUPPORTED":
        raise AcquisitionError(f"{source_id}: internal research use is not supported")

    target_url = str(record["acquisition_target_url"])
    if target_url == str(record["provenance_url"]) and source_id == "CA-3":
        raise AcquisitionError("CA-3: canonical target must not be the provenance index")
    validate_url(target_url)
    expected_type = str(record["acquisition_target_expected_content_type"])

    redirects = AllowlistRedirectHandler()
    selected = opener or urllib.request.build_opener(redirects)
    request = urllib.request.Request(  # noqa: S310 - HTTPS and domain validated above.
        target_url, method="GET", headers={"User-Agent": USER_AGENT}
    )
    try:
        with selected.open(request, timeout=60) as response:
            status = int(response.status)
            if status != 200:
                raise AcquisitionError(f"{source_id}: HTTP {status}")
            final_url = response.geturl()
            validate_url(final_url)
            headers = dict(response.headers.items())
            content_type = validate_content_type(
                response.headers.get("Content-Type"), expected_type
            )
            observed_at = utc_now()
            body = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as error:
        raise AcquisitionError(f"{source_id}: retrieval failed: {error}") from error

    if len(body) > MAX_BYTES:
        raise AcquisitionError(f"{source_id}: response exceeds {MAX_BYTES} bytes")
    validate_magic(content_type, body, source_id)

    receipt = {
        "receipt_id": f"OIC-CA-FREEZE-{source_id}-v0.1",
        "acquisition_target_url": target_url,
        "acquisition_target_role": str(record["acquisition_target_role"]),
        "acquisition_tool": TOOL_NAME,
        "acquisition_tool_version": TOOL_VERSION,
        "byte_length": len(body),
        "content_disposition": headers.get("Content-Disposition"),
        "content_type": content_type,
        "etag": headers.get("ETag"),
        "final_url": final_url,
        "http_status": status,
        "language": "en",
        "last_modified": headers.get("Last-Modified"),
        "provenance_url": str(record["provenance_url"]),
        "redirect_chain": list(redirects.chain),
        "rendering_role": str(record["acquisition_target_role"]),
        "retrieval_utc": observed_at,
        "rights_disposition": disposition,
        "sha256": hashlib.sha256(body).hexdigest(),
        "sha512": hashlib.sha512(body).hexdigest(),
        "source_id": source_id,
        "storage_classification": str(record["storage_classification"]),
        "byte_screening": screen_bytes(body),
    }
    return receipt, body


def freeze(rights: Mapping[str, Any], *, opener: OpenerLike | None = None) -> dict[str, Any]:
    """Acquire every permitted source and assemble the freeze package in memory."""
    eligible = [
        record
        for record in rights["records"]
        if record["reviewer_disposition"] in {REPOSITORY_FREEZE, INTERNAL_FREEZE}
    ]
    entries: list[dict[str, Any]] = []
    for record in sorted(eligible, key=lambda item: str(item["source_id"])):
        receipt, body = acquire(record, opener=opener)
        source_id = receipt["source_id"]
        suffix = SUFFIX_BY_CONTENT_TYPE[str(receipt["content_type"])]
        if receipt["storage_classification"] == "REPOSITORY_FROZEN":
            path = REPOSITORY_BYTES_DIR / f"{source_id}{suffix}"
            relative = str(path.relative_to(FREEZE_DIR))
        else:
            path = INTERNAL_BYTES_DIR / f"{source_id}{suffix}"
            relative = None
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, body)
        atomic_write_bytes(RECEIPT_DIR / f"{source_id}.receipt.json", canonical_json_bytes(receipt))
        entries.append(
            {
                "acquisition_target_url": receipt["acquisition_target_url"],
                "byte_length": receipt["byte_length"],
                "content_type": receipt["content_type"],
                "final_url": receipt["final_url"],
                "frozen_bytes_path": relative,
                "receipt_id": receipt["receipt_id"],
                "receipt_path": f"receipts/{source_id}.receipt.json",
                "retrieval_utc": receipt["retrieval_utc"],
                "rights_disposition": receipt["rights_disposition"],
                "sha256": receipt["sha256"],
                "sha512": receipt["sha512"],
                "source_id": source_id,
                "storage_classification": receipt["storage_classification"],
            }
        )

    blocked = sorted(
        str(record["source_id"])
        for record in rights["records"]
        if record["reviewer_disposition"] == BLOCKED
    )
    disposition = "COMPLETE" if not blocked else ("PARTIAL" if entries else "BLOCKED")
    return {
        "acquired_source_count": len(entries),
        "blocked_source_ids": blocked,
        "blocked_source_count": len(blocked),
        "entries": entries,
        "freeze_disposition": disposition,
        "freeze_id": "CANADA-ACQUISITION-FREEZE-v0.1",
        "source_unit_count": len(rights["records"]),
    }


def freeze_record(index: Mapping[str, Any], rights: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the narrative freeze record that accompanies the binding index."""
    return {
        "freeze_id": index["freeze_id"],
        "freeze_disposition": index["freeze_disposition"],
        "acquisition_tool": TOOL_NAME,
        "acquisition_tool_version": TOOL_VERSION,
        "source_unit_count": index["source_unit_count"],
        "acquired_source_count": index["acquired_source_count"],
        "blocked_source_count": index["blocked_source_count"],
        "blocked_source_ids": index["blocked_source_ids"],
        "committed_to_repository_source_ids": sorted(
            str(entry["source_id"])
            for entry in index["entries"]
            if entry["storage_classification"] == "REPOSITORY_FROZEN"
        ),
        "internal_only_source_ids": sorted(
            str(entry["source_id"])
            for entry in index["entries"]
            if entry["storage_classification"] == "INTERNAL_ONLY"
        ),
        "disposition_counts": rights["disposition_counts"],
        "no_fallback_note": (
            "Every request in this freeze used the explicit acquisition target from the rights "
            "record. No provenance URL was requested as a fallback, and no source with a "
            "BLOCKED_PENDING_CLEARANCE disposition was requested at all."
        ),
        "completion_note": (
            "A PARTIAL freeze is not convertible to COMPLETE by substituting a source, relaxing a "
            "disposition, or falling back to a provenance URL. COMPLETE requires that all "
            f"{index['source_unit_count']} source units carry a permitted exact-byte acquisition."
        ),
        "source_manifest_note": (
            "SOURCE_MANIFEST.csv carries no path column, so `oic verify-manifest` cannot bind a "
            "recorded row to its committed bytes and reports RECORDED_NOT_VERIFIED rather than "
            "PASS. The schema was not changed and no field was invented; the frozen path is "
            "recorded in the notes column and byte-level verification is "
            "scripts/verify_canada_freeze.py. An internal-only freeze would have no faithful "
            "representation at all in this schema and would be left out pending an owner decision."
        ),
        "semantic_implementation_gate": "BLOCKED",
    }


def write_package(index: Mapping[str, Any], rights: Mapping[str, Any]) -> None:
    """Write the freeze record, INDEX.json, and the two hash ledgers deterministically."""
    atomic_write_bytes(FREEZE_DIR / "INDEX.json", canonical_json_bytes(index))
    atomic_write_bytes(
        FREEZE_DIR / "ACQUISITION-FREEZE-v0.1.json",
        canonical_json_bytes(freeze_record(index, rights)),
    )
    for algorithm, filename in (("sha256", "SHA256SUMS"), ("sha512", "SHA512SUMS")):
        lines = [
            f"{entry[algorithm]}  "
            f"{entry['frozen_bytes_path'] or entry['source_id'] + ' (INTERNAL_ONLY)'}\n"
            for entry in index["entries"]
        ]
        atomic_write_bytes(FREEZE_DIR / filename, "".join(lines).encode())


def main(argv: Sequence[str] | None = None) -> int:
    """Run the rights-gated freeze and emit the package."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rights", type=Path, default=RIGHTS_PATH)
    args = parser.parse_args(argv)
    try:
        import json

        rights = json.loads(args.rights.read_text(encoding="utf-8"))
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        REPOSITORY_BYTES_DIR.mkdir(parents=True, exist_ok=True)
        index = freeze(rights)
        write_package(index, rights)
        print(f"freeze disposition: {index['freeze_disposition']}")
        for entry in index["entries"]:
            print(
                f"  {entry['source_id']}  {entry['byte_length']} bytes  "
                f"{entry['sha256']}  {entry['storage_classification']}"
            )
        print(f"  blocked: {', '.join(index['blocked_source_ids']) or 'none'}")
    except (AcquisitionError, KeyError, OSError, ValueError) as error:
        print(f"freeze failed closed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
