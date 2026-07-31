#!/usr/bin/env python3
"""Offline verification of the Canada acquisition freeze. Performs no network I/O.

Every repository-frozen artifact must agree, byte for byte, with its receipt, the
index entry, and both hash ledgers. Internal-only entries are verified when their
gitignored bytes are present and are otherwise reported as absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = REPO_ROOT / "benchmarks/corpus/canada/freeze-v0.1"
INTERNAL_BYTES_DIR = REPO_ROOT / ".local/canada-freeze-internal"

BLOCKED = "BLOCKED_PENDING_CLEARANCE"
REPOSITORY_FREEZE = "CLEAR_REPOSITORY_FREEZE"
INTERNAL_FREEZE = "CLEAR_INTERNAL_FREEZE_ONLY"


def parse_sums(path: Path) -> dict[str, str]:
    """Parse a two-space-separated hash ledger into name -> digest."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, separator, name = line.partition("  ")
        if not separator:
            raise ValueError(f"malformed ledger line in {path.name}: {line!r}")
        result[name] = digest
    return result


def verify(freeze_dir: Path = FREEZE_DIR) -> list[str]:
    """Return every verification failure. An empty list means the freeze verifies."""
    failures: list[str] = []
    index = json.loads((freeze_dir / "INDEX.json").read_text(encoding="utf-8"))
    rights = json.loads((freeze_dir / "RIGHTS-CLEARANCE-v0.1.json").read_text(encoding="utf-8"))
    sha256_sums = parse_sums(freeze_dir / "SHA256SUMS")
    sha512_sums = parse_sums(freeze_dir / "SHA512SUMS")

    by_source = {str(record["source_id"]): record for record in rights["records"]}
    entry_ids = {str(entry["source_id"]) for entry in index["entries"]}

    for source_id, record in sorted(by_source.items()):
        disposition = str(record["reviewer_disposition"])
        if disposition == BLOCKED and source_id in entry_ids:
            failures.append(f"{source_id}: blocked source has a freeze entry")
        if disposition != BLOCKED and source_id not in entry_ids:
            failures.append(f"{source_id}: cleared source has no freeze entry")

    receipt_files = {path.name for path in (freeze_dir / "receipts").glob("*.receipt.json")}
    expected_receipts = {f"{source_id}.receipt.json" for source_id in entry_ids}
    for extra in sorted(receipt_files - expected_receipts):
        failures.append(f"receipt without a freeze entry: {extra}")

    for entry in index["entries"]:
        source_id = str(entry["source_id"])
        record = by_source.get(source_id)
        if record is None:
            failures.append(f"{source_id}: freeze entry has no rights record")
            continue
        if str(record["reviewer_disposition"]) != str(entry["rights_disposition"]):
            failures.append(f"{source_id}: entry disposition disagrees with the rights record")
        if str(entry["acquisition_target_url"]) != str(record["acquisition_target_url"]):
            failures.append(f"{source_id}: entry target is not the rights-record target")
        if str(entry["acquisition_target_url"]) == str(record["provenance_url"]):
            failures.append(f"{source_id}: entry target fell back to the provenance URL")

        receipt_path = freeze_dir / str(entry["receipt_path"])
        if not receipt_path.is_file():
            failures.append(f"{source_id}: missing receipt {entry['receipt_path']}")
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for field in ("sha256", "sha512", "byte_length", "acquisition_target_url", "receipt_id"):
            if receipt[field] != entry[field]:
                failures.append(f"{source_id}: receipt {field} disagrees with the index")

        classification = str(entry["storage_classification"])
        relative = entry["frozen_bytes_path"]
        if classification == "REPOSITORY_FROZEN":
            if relative is None:
                failures.append(f"{source_id}: repository-frozen entry has no byte path")
                continue
            byte_path = freeze_dir / str(relative)
            ledger_key = str(relative)
        elif classification == "INTERNAL_ONLY":
            if relative is not None:
                failures.append(f"{source_id}: internal-only entry must not name a committed path")
            ledger_key = f"{source_id} (INTERNAL_ONLY)"
            candidates = sorted(INTERNAL_BYTES_DIR.glob(f"{source_id}.*"))
            if not candidates:
                print(f"note: {source_id}: internal-only bytes absent from this checkout")
                _check_ledgers(failures, source_id, ledger_key, entry, sha256_sums, sha512_sums)
                continue
            byte_path = candidates[0]
        else:
            failures.append(f"{source_id}: unexpected storage classification {classification}")
            continue

        if not byte_path.is_file():
            failures.append(f"{source_id}: frozen bytes missing at {byte_path}")
            continue
        data = byte_path.read_bytes()
        if len(data) != int(entry["byte_length"]):
            failures.append(f"{source_id}: byte length does not match the receipt")
        if hashlib.sha256(data).hexdigest() != str(entry["sha256"]):
            failures.append(f"{source_id}: SHA-256 mismatch")
        if hashlib.sha512(data).hexdigest() != str(entry["sha512"]):
            failures.append(f"{source_id}: SHA-512 mismatch")
        _check_ledgers(failures, source_id, ledger_key, entry, sha256_sums, sha512_sums)

    return failures


def _check_ledgers(
    failures: list[str],
    source_id: str,
    ledger_key: str,
    entry: Mapping[str, Any],
    sha256_sums: dict[str, str],
    sha512_sums: dict[str, str],
) -> None:
    if sha256_sums.get(ledger_key) != str(entry["sha256"]):
        failures.append(f"{source_id}: SHA256SUMS disagrees with the index")
    if sha512_sums.get(ledger_key) != str(entry["sha512"]):
        failures.append(f"{source_id}: SHA512SUMS disagrees with the index")


def main(argv: Sequence[str] | None = None) -> int:
    """Verify the freeze and report every failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-dir", type=Path, default=FREEZE_DIR)
    args = parser.parse_args(argv)
    try:
        failures = verify(args.freeze_dir)
    except (KeyError, OSError, ValueError) as error:
        print(f"freeze verification failed closed: {error}", file=sys.stderr)
        return 2
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("freeze verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
