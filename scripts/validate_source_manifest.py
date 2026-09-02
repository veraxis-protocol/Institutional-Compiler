#!/usr/bin/env python3
"""Fail-closed offline validator for OIC SOURCE_MANIFEST.csv contract v0.1.

This module validates a supplied manifest against the frozen structural contract
and an explicitly supplied expected bounded source-id population.

It does not fetch URLs, inspect source-document contents, infer rights,
establish provenance, populate SOURCE_MANIFEST.csv, admit sources, or perform
semantic/runtime/provider work.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "SOURCE-MANIFEST-CONTRACT-v0.1.json"
)

CONTRACT_SHA256 = (
    "3bf96bd6e6854a7beb048206f73465588df8f9b3182e1280ed7ec7878280559b"
)

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    row_number: int | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    disposition: str
    row_count: int
    expected_population_count: int
    validated_source_ids: tuple[str, ...]
    findings: tuple[Finding, ...]
    rights_established: bool = False
    provenance_established: bool = False
    legal_clearance_established: bool = False


def sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict[str, Any]:
    if sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise SystemExit("FAIL frozen manifest contract digest mismatch")

    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    if value["contract_id"] != "OIC-SOURCE-MANIFEST-CONTRACT-001":
        raise SystemExit("FAIL wrong manifest contract identity")

    if value["contract_version"] != "v0.1":
        raise SystemExit("FAIL wrong manifest contract version")

    return value


def _is_http_uri(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_repo_relative_path(value: str) -> bool:
    path = Path(value)
    return (
        bool(value)
        and not path.is_absolute()
        and ".." not in path.parts
    )


def _git_tracked(path: str) -> bool:
    if not _is_repo_relative_path(path):
        return False

    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _valid_evidence_reference(value: str) -> bool:
    if _is_http_uri(value):
        return True

    return _is_repo_relative_path(value) and _git_tracked(value)


def _valid_rfc3339(value: str) -> bool:
    if not value:
        return False

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False

    return parsed.tzinfo is not None


def validate_manifest(
    manifest_path: Path,
    *,
    expected_source_ids: Iterable[str] | None,
) -> ValidationResult:
    contract = load_contract()
    findings: list[Finding] = []

    if expected_source_ids is None:
        return ValidationResult(
            disposition="FAIL_CLOSED",
            row_count=0,
            expected_population_count=0,
            validated_source_ids=(),
            findings=(
                Finding(
                    "EXPECTED_POPULATION_REQUIRED",
                    "Expected bounded source-id population was not supplied.",
                ),
            ),
        )

    expected_list = list(expected_source_ids)

    if not expected_list or any(not x for x in expected_list):
        findings.append(
            Finding(
                "EXPECTED_POPULATION_INVALID",
                "Expected bounded source-id population must be non-empty "
                "and contain only non-empty identifiers.",
            )
        )

    if len(set(expected_list)) != len(expected_list):
        findings.append(
            Finding(
                "EXPECTED_POPULATION_DUPLICATE",
                "Expected bounded source-id population contains duplicates.",
            )
        )

    expected = set(expected_list)

    if not manifest_path.exists():
        findings.append(
            Finding("MANIFEST_ABSENT", f"Manifest does not exist: {manifest_path}")
        )
        return ValidationResult(
            disposition="FAIL_CLOSED",
            row_count=0,
            expected_population_count=len(expected),
            validated_source_ids=(),
            findings=tuple(findings),
        )

    try:
        handle = manifest_path.open("r", encoding="utf-8", newline="")
    except (OSError, UnicodeError) as exc:
        findings.append(Finding("MANIFEST_UNREADABLE", str(exc)))
        return ValidationResult(
            disposition="FAIL_CLOSED",
            row_count=0,
            expected_population_count=len(expected),
            validated_source_ids=(),
            findings=tuple(findings),
        )

    with handle:
        reader = csv.DictReader(handle)

        expected_header = contract["header_order"]

        if reader.fieldnames != expected_header:
            findings.append(
                Finding(
                    "HEADER_MISMATCH",
                    f"Expected exact header {expected_header!r}; "
                    f"observed {reader.fieldnames!r}.",
                )
            )
            return ValidationResult(
                disposition="FAIL_CLOSED",
                row_count=0,
                expected_population_count=len(expected),
                validated_source_ids=(),
                findings=tuple(findings),
            )

        rows = list(reader)

    if not rows:
        findings.append(Finding("MANIFEST_EMPTY", "Manifest contains no data rows."))

    seen: set[str] = set()
    validated: list[str] = []

    required_fields = [
        key
        for key, spec in contract["fields"].items()
        if spec.get("required") is True
    ]

    allowed_source_kind = set(contract["fields"]["source_kind"]["allowed"])
    allowed_rights_basis = set(contract["fields"]["rights_basis"]["allowed"])
    allowed_rights_status = set(contract["fields"]["rights_status"]["allowed"])
    allowed_provenance_status = set(
        contract["fields"]["provenance_status"]["allowed"]
    )
    allowed_redistribution = set(
        contract["fields"]["redistribution_status"]["allowed"]
    )

    for index, row in enumerate(rows, start=2):
        source_id = row.get("source_id", "")

        for field in required_fields:
            if not row.get(field, ""):
                findings.append(
                    Finding(
                        "REQUIRED_FIELD_EMPTY",
                        f"Required field {field!r} is empty.",
                        index,
                        source_id or None,
                    )
                )

        if source_id:
            if source_id in seen:
                findings.append(
                    Finding(
                        "DUPLICATE_SOURCE_ID",
                        f"Duplicate source_id {source_id!r}.",
                        index,
                        source_id,
                    )
                )
            else:
                seen.add(source_id)

        source_kind = row.get("source_kind", "")
        if source_kind not in allowed_source_kind:
            findings.append(
                Finding(
                    "UNSUPPORTED_SOURCE_KIND",
                    f"Unsupported source_kind {source_kind!r}.",
                    index,
                    source_id or None,
                )
            )

        content_hash = row.get("content_hash", "")
        if not HASH_RE.fullmatch(content_hash):
            findings.append(
                Finding(
                    "INVALID_CONTENT_HASH",
                    "content_hash must match sha256:<64 lowercase hex>.",
                    index,
                    source_id or None,
                )
            )

        local_path = row.get("local_path", "")
        if not _is_repo_relative_path(local_path):
            findings.append(
                Finding(
                    "INVALID_LOCAL_PATH",
                    "local_path must be repository-relative and must not "
                    "contain parent traversal.",
                    index,
                    source_id or None,
                )
            )

        rights_basis = row.get("rights_basis", "")
        if rights_basis not in allowed_rights_basis:
            findings.append(
                Finding(
                    "INVALID_RIGHTS_BASIS",
                    f"Unsupported rights_basis {rights_basis!r}.",
                    index,
                    source_id or None,
                )
            )

        rights_status = row.get("rights_status", "")
        if rights_status not in allowed_rights_status:
            findings.append(
                Finding(
                    "INVALID_RIGHTS_STATUS",
                    f"Unsupported rights_status {rights_status!r}.",
                    index,
                    source_id or None,
                )
            )
        elif rights_status != "verified":
            findings.append(
                Finding(
                    "RIGHTS_NOT_VERIFIED",
                    "rights_status must equal 'verified' for PASS.",
                    index,
                    source_id or None,
                )
            )

        provenance_status = row.get("provenance_status", "")
        if provenance_status not in allowed_provenance_status:
            findings.append(
                Finding(
                    "INVALID_PROVENANCE_STATUS",
                    f"Unsupported provenance_status {provenance_status!r}.",
                    index,
                    source_id or None,
                )
            )
        elif provenance_status != "verified":
            findings.append(
                Finding(
                    "PROVENANCE_NOT_VERIFIED",
                    "provenance_status must equal 'verified' for PASS.",
                    index,
                    source_id or None,
                )
            )

        redistribution = row.get("redistribution_status", "")
        if redistribution not in allowed_redistribution:
            findings.append(
                Finding(
                    "INVALID_REDISTRIBUTION_STATUS",
                    f"Unsupported redistribution_status {redistribution!r}.",
                    index,
                    source_id or None,
                )
            )
        elif redistribution == "unknown":
            findings.append(
                Finding(
                    "REDISTRIBUTION_UNKNOWN",
                    "redistribution_status must not be 'unknown' for PASS.",
                    index,
                    source_id or None,
                )
            )

        for field in ("rights_evidence", "provenance_evidence"):
            value = row.get(field, "")
            if value and not _valid_evidence_reference(value):
                findings.append(
                    Finding(
                        "INVALID_EVIDENCE_REFERENCE",
                        f"{field} must be an http(s) URI or a repository-relative "
                        "git-tracked evidence reference.",
                        index,
                        source_id or None,
                    )
                )

        acquired = row.get("acquired_or_generated_at", "")
        if acquired and not _valid_rfc3339(acquired):
            findings.append(
                Finding(
                    "INVALID_ACQUIRED_OR_GENERATED_AT",
                    "acquired_or_generated_at must be an RFC 3339 date-time "
                    "with timezone.",
                    index,
                    source_id or None,
                )
            )

        if source_id:
            validated.append(source_id)

    observed = set(validated)

    missing = sorted(expected - observed)
    undeclared = sorted(observed - expected)

    if missing:
        findings.append(
            Finding(
                "POPULATION_MISSING_SOURCES",
                "Manifest is missing expected source_id values: "
                + ", ".join(missing),
            )
        )

    if undeclared:
        findings.append(
            Finding(
                "POPULATION_UNDECLARED_SOURCES",
                "Manifest contains source_id values outside expected bounded "
                "population: "
                + ", ".join(undeclared),
            )
        )

    disposition = "PASS" if not findings else "FAIL_CLOSED"

    return ValidationResult(
        disposition=disposition,
        row_count=len(rows),
        expected_population_count=len(expected),
        validated_source_ids=tuple(validated),
        findings=tuple(findings),
        rights_established=False,
        provenance_established=False,
        legal_clearance_established=False,
    )


def result_document(result: ValidationResult) -> dict[str, Any]:
    return {
        "disposition": result.disposition,
        "row_count": result.row_count,
        "expected_population_count": result.expected_population_count,
        "validated_source_ids": list(result.validated_source_ids),
        "findings": [asdict(x) for x in result.findings],
        "rights_established": False,
        "provenance_established": False,
        "legal_clearance_established": False,
        "claim_ceiling": (
            "Structural preflight validation only. PASS does not itself establish "
            "legal rights, provenance truth, copyright clearance, institutional "
            "authority, semantic correctness, benchmark validity, production "
            "readiness, or enterprise readiness."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--expected-source-id",
        action="append",
        dest="expected_source_ids",
        help="Expected bounded source_id. Repeat once per expected source.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = validate_manifest(
        args.manifest,
        expected_source_ids=args.expected_source_ids,
    )

    if args.json:
        print(json.dumps(result_document(result), indent=2, sort_keys=True))
    else:
        print(f"disposition: {result.disposition}")
        print(f"rows: {result.row_count}")
        print(f"expected population: {result.expected_population_count}")
        for finding in result.findings:
            where = ""
            if finding.row_number is not None:
                where += f" row={finding.row_number}"
            if finding.source_id is not None:
                where += f" source_id={finding.source_id}"
            print(f"{finding.code}:{where} {finding.message}")

    return 0 if result.disposition == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
