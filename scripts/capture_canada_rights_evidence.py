#!/usr/bin/env python3
"""Capture exact bytes of the rights instruments governing the Canada corpus.

Rights instruments are notices, terms pages, and robots.txt policies. They are
not corpus sources. Bytes land in a gitignored local evidence area; only the
canonical evidence ledger is committed.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acquire_canada_preflight import (
    AcquisitionError,
    atomic_write_bytes,
    canonical_json_bytes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = REPO_ROOT / ".local/canada-rights-evidence"
DEFAULT_LEDGER = REPO_ROOT / "benchmarks/corpus/canada/freeze-v0.1/RIGHTS-EVIDENCE-LEDGER-v0.1.json"

USER_AGENT = "OIC-Canada-Rights-Research/0.1 (+rights-evidence-capture)"
MAX_EVIDENCE_BYTES = 8 * 1024 * 1024

# Rights instruments live on publisher and whole-of-government notice domains,
# which are a different set from the corpus acquisition allowlist.
RIGHTS_EVIDENCE_DOMAINS = frozenset(
    {
        "canadabuys.canada.ca",
        "laws-lois.justice.gc.ca",
        "www.canada.ca",
        "www.tbs-sct.canada.ca",
    }
)

# Rights instruments, keyed by a stable evidence ID. `expected_absent` marks an
# instrument whose absence is itself the finding (no robots.txt means no
# robots-based retrieval restriction).
EVIDENCE_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "evidence_id": "ROBOTS-TBS",
        "url": "https://www.tbs-sct.canada.ca/robots.txt",
        "kind": "ROBOTS_POLICY",
        "governs_domain": "www.tbs-sct.canada.ca",
    },
    {
        "evidence_id": "ROBOTS-LAWS-LOIS",
        "url": "https://laws-lois.justice.gc.ca/robots.txt",
        "kind": "ROBOTS_POLICY",
        "governs_domain": "laws-lois.justice.gc.ca",
    },
    {
        "evidence_id": "ROBOTS-CANADABUYS",
        "url": "https://canadabuys.canada.ca/robots.txt",
        "kind": "ROBOTS_POLICY",
        "governs_domain": "canadabuys.canada.ca",
    },
    {
        "evidence_id": "CANADA-CA-TERMS",
        "url": "https://www.canada.ca/en/transparency/terms.html",
        "kind": "TERMS_OF_USE",
        "governs_domain": "www.canada.ca",
    },
    {
        "evidence_id": "SI-97-5-REPRODUCTION-ORDER",
        "url": "https://laws-lois.justice.gc.ca/eng/XML/SI-97-5.xml",
        "kind": "RIGHTS_INSTRUMENT",
        "governs_domain": "laws-lois.justice.gc.ca",
    },
)


def utc_now() -> str:
    """Return the capture instant, which is an observation time only."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_evidence_url(url: str) -> str:
    """Require HTTPS and an explicitly allowed rights-instrument domain."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise AcquisitionError(f"non-HTTPS rights evidence URL rejected: {url}")
    if hostname not in RIGHTS_EVIDENCE_DOMAINS:
        raise AcquisitionError(f"unapproved rights evidence domain: {hostname or '<missing>'}")
    return hostname


class EvidenceRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects off the rights-evidence allowlist and preserve hop order."""

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
        validate_evidence_url(newurl)
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def capture_one(target: dict[str, Any], evidence_dir: Path) -> dict[str, Any]:
    """Capture one rights instrument, recording absence rather than inventing it."""
    url = str(target["url"])
    validate_evidence_url(url)
    redirects = EvidenceRedirectHandler()
    opener = urllib.request.build_opener(redirects)
    request = urllib.request.Request(  # noqa: S310 - HTTPS and domain validated above.
        url, method="GET", headers={"User-Agent": USER_AGENT}
    )
    observed_at = utc_now()
    unreachable_reason: str | None = None
    try:
        with opener.open(request, timeout=30) as response:
            status = int(response.status)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type")
            body = response.read(MAX_EVIDENCE_BYTES + 1)
    except urllib.error.HTTPError as error:
        status = int(error.code)
        final_url = error.url
        content_type = error.headers.get("Content-Type") if error.headers else None
        body = b""
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        # An unreachable rights notice is a recorded finding, not a synthesized
        # permission. Downstream dispositions must fail closed on it.
        status = None
        final_url = None
        content_type = None
        body = b""
        unreachable_reason = f"{type(error).__name__}: {error}"

    record: dict[str, Any] = {
        "unreachable_reason": unreachable_reason,
        "evidence_id": str(target["evidence_id"]),
        "kind": str(target["kind"]),
        "governs_domain": str(target["governs_domain"]),
        "requested_url": url,
        "final_url": final_url,
        "redirect_chain": list(redirects.chain),
        "http_status": status,
        "content_type": content_type,
        "capture_utc": observed_at,
        "captured": status == 200,
        "byte_length": None,
        "sha256": None,
        "sha512": None,
    }
    if status != 200:
        return record
    if len(body) > MAX_EVIDENCE_BYTES:
        raise AcquisitionError(f"{target['evidence_id']}: evidence exceeds size limit")
    atomic_write_bytes(evidence_dir / f"{target['evidence_id']}.evidence", body)
    record["byte_length"] = len(body)
    record["sha256"] = hashlib.sha256(body).hexdigest()
    record["sha512"] = hashlib.sha512(body).hexdigest()
    return record


def main(argv: Sequence[str] | None = None) -> int:
    """Capture every rights instrument and write the canonical evidence ledger."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args(argv)
    try:
        evidence_dir = args.evidence_dir.resolve()
        if evidence_dir != DEFAULT_EVIDENCE_DIR.resolve():
            raise AcquisitionError(f"evidence directory must be exactly {DEFAULT_EVIDENCE_DIR}")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        records = [capture_one(target, evidence_dir) for target in EVIDENCE_TARGETS]
        ledger = {
            "ledger_status": "RIGHTS_INSTRUMENT_EVIDENCE",
            "evidence_bytes_location": "gitignored .local/canada-rights-evidence/",
            "capture_note": (
                "capture_utc is the UTC time at which the response was observed. It is not a "
                "publication time or a trusted timestamp. An http_status other than 200 records "
                "an observed absence and is not an error."
            ),
            "records": sorted(records, key=lambda item: str(item["evidence_id"])),
        }
        atomic_write_bytes(args.ledger, canonical_json_bytes(ledger))
        print(json.dumps(ledger, indent=2, sort_keys=True))
    except (AcquisitionError, OSError, ValueError) as error:
        print(f"rights evidence capture failed closed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
