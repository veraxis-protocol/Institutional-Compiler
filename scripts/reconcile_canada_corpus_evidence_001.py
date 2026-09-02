#!/usr/bin/env python3
"""Offline fail-closed evidence reconciler for CA-3.

This instrument is intentionally narrower than a legal or semantic reviewer.

It:
- reads only the frozen machine-readable primary evidence allowlist;
- never opens corroborating Markdown for PASS-critical extraction;
- never fetches network resources;
- never parses/renders/extracts text from CA-3.xml;
- computes only the allowed byte-level SHA-256 of CA-3.xml;
- accepts only exact SOURCE_MANIFEST contract field names;
- requires those fields to occur in a source_id == "CA-3" context;
- does not invent aliases or post-observation mappings;
- fails closed on missing or conflicting values;
- never creates SOURCE_MANIFEST.csv.

The output is only a structural evidence-reconciliation result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-reconciliation-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
ALLOWLIST = BENCH / "EVIDENCE-ALLOWLIST-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

PLAN_SHA256 = "8b35004a1c6c02340bb9b55da68ad7caf406dbcf7c2f3e29f553fa5801bdb0c4"
ALLOWLIST_SHA256 = "8dc6fac14ab38390231a7561668e39075ace9446c1d3736674f496818293ef95"
PREREG_FREEZE_SHA256 = "47e92034a8eaa899c82085a4f3ec2ddcaa922f8c798750358d618807b25790bd"

CONTRACT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "SOURCE-MANIFEST-CONTRACT-v0.1.json"
)
CONTRACT_SHA256 = "3bf96bd6e6854a7beb048206f73465588df8f9b3182e1280ed7ec7878280559b"

EXPECTED_SOURCE_ID = "CA-3"
EXPECTED_SOURCE_PATH = (
    "benchmarks/corpus/canada/freeze-v0.1/sources/CA-3.xml"
)
EXPECTED_SOURCE_GIT_BLOB = "9d89e621e40854a192a41193a507a766af30214b"

DISPOSITION_READY = "READY_FOR_MANIFEST_POPULATION"
DISPOSITION_FAIL = "EVIDENCE_INSUFFICIENT_FAIL_CLOSED"

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

FIELDS = (
    "source_id",
    "source_kind",
    "source_locator",
    "local_path",
    "content_hash",
    "rights_basis",
    "rights_evidence",
    "rights_status",
    "provenance_evidence",
    "provenance_status",
    "redistribution_status",
    "acquired_or_generated_at",
)

EVIDENCE_EXTRACTED_FIELDS = tuple(x for x in FIELDS if x != "content_hash")


@dataclass(frozen=True)
class Occurrence:
    field: str
    value: str
    evidence_path: str
    json_pointer: str


@dataclass(frozen=True)
class Finding:
    code: str
    field: str | None
    message: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: str, commit: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=ROOT,
        text=True,
    ).strip()


def _git_tracked(path: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
    )
    return completed.returncode == 0


def load_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    checks = (
        (PLAN, PLAN_SHA256),
        (ALLOWLIST, ALLOWLIST_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (CONTRACT, CONTRACT_SHA256),
    )
    for path, expected in checks:
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    if allow["population"]["source_ids"] != [EXPECTED_SOURCE_ID]:
        raise SystemExit("FAIL population drift")
    if allow["population"]["source_count"] != 1:
        raise SystemExit("FAIL population count drift")
    if freeze["status"] != "PREREGISTERED_NOT_EXECUTED":
        raise SystemExit("FAIL wrong preregistration status")
    if freeze["source_parse_render_text_extraction_authorized"] is not False:
        raise SystemExit("FAIL source-content boundary drift")
    if freeze["source_byte_hashing_during_future_execution_authorized"] is not True:
        raise SystemExit("FAIL source byte hashing not authorized")
    if freeze["unlisted_evidence_inspection_authorized"] is not False:
        raise SystemExit("FAIL unlisted evidence boundary drift")
    if freeze["network_fetch_authorized"] is not False:
        raise SystemExit("FAIL network boundary drift")
    if freeze["root_source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest creation boundary drift")
    if contract["contract_id"] != "OIC-SOURCE-MANIFEST-CONTRACT-001":
        raise SystemExit("FAIL wrong manifest contract")
    if contract["contract_version"] != "v0.1":
        raise SystemExit("FAIL wrong manifest contract version")

    return allow, freeze, contract


def verify_git_identities(allow: dict[str, Any]) -> None:
    entries: list[dict[str, Any]] = []
    entries.extend(allow["primary_machine_readable_evidence"])
    entries.extend(allow["corroborating_human_readable_evidence"])
    entries.extend(allow["population"]["sources"])

    for item in entries:
        actual = _git_blob(item["path"])
        if actual != item["git_blob_sha"]:
            raise SystemExit(f"FAIL Git blob drift: {item['path']}")

    if _git_blob(EXPECTED_SOURCE_PATH) != EXPECTED_SOURCE_GIT_BLOB:
        raise SystemExit("FAIL source Git blob drift")


def _escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def collect_occurrences(
    value: Any,
    *,
    evidence_path: str,
    pointer: str = "",
    source_context: str | None = None,
) -> list[Occurrence]:
    """Collect exact contract-field keys only in CA-3 source context.

    Source context is established only by an exact key named ``source_id`` whose
    scalar value is exactly ``CA-3``. Nested dictionaries inherit the nearest
    source context; a nested exact ``source_id`` replaces it.

    No aliases, fuzzy matching, filename inference, or key translation is used.
    """
    found: list[Occurrence] = []

    if isinstance(value, dict):
        local_context = source_context

        if "source_id" in value and isinstance(value["source_id"], str):
            local_context = value["source_id"]
            if value["source_id"] == EXPECTED_SOURCE_ID:
                found.append(
                    Occurrence(
                        field="source_id",
                        value=EXPECTED_SOURCE_ID,
                        evidence_path=evidence_path,
                        json_pointer=(pointer + "/source_id") or "/source_id",
                    )
                )

        for key, child in value.items():
            child_pointer = pointer + "/" + _escape_pointer_part(str(key))

            if (
                local_context == EXPECTED_SOURCE_ID
                and key in EVIDENCE_EXTRACTED_FIELDS
                and key != "source_id"
                and isinstance(child, str)
            ):
                found.append(
                    Occurrence(
                        field=key,
                        value=child,
                        evidence_path=evidence_path,
                        json_pointer=child_pointer or "/",
                    )
                )

            if isinstance(child, (dict, list)):
                found.extend(
                    collect_occurrences(
                        child,
                        evidence_path=evidence_path,
                        pointer=child_pointer,
                        source_context=local_context,
                    )
                )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(
                    collect_occurrences(
                        child,
                        evidence_path=evidence_path,
                        pointer=f"{pointer}/{index}",
                        source_context=source_context,
                    )
                )

    return found


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


def _valid_evidence_reference(value: str) -> bool:
    return _is_http_uri(value) or (_is_repo_relative_path(value) and _git_tracked(value))


def _valid_rfc3339(value: str) -> bool:
    if not value:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def reconcile_from_documents(
    *,
    documents: Iterable[tuple[str, Any]],
    contract: dict[str, Any],
    computed_content_hash: str,
) -> dict[str, Any]:
    occurrences: list[Occurrence] = []

    for evidence_path, document in documents:
        occurrences.extend(
            collect_occurrences(
                document,
                evidence_path=evidence_path,
            )
        )

    by_field: dict[str, list[Occurrence]] = {field: [] for field in FIELDS}
    for occurrence in occurrences:
        by_field[occurrence.field].append(occurrence)

    # content_hash has exactly one authorized derivation: source byte SHA-256.
    by_field["content_hash"] = [
        Occurrence(
            field="content_hash",
            value=computed_content_hash,
            evidence_path=EXPECTED_SOURCE_PATH,
            json_pointer="BYTE_SHA256_ONLY",
        )
    ]

    findings: list[Finding] = []
    resolved: dict[str, str] = {}
    support: dict[str, list[dict[str, str]]] = {}

    for field in FIELDS:
        field_occurrences = by_field[field]
        support[field] = [asdict(item) for item in field_occurrences]

        if not field_occurrences:
            findings.append(
                Finding(
                    "MISSING_EXPLICIT_SUPPORT",
                    field,
                    f"No exact-key CA-3 evidence supports required field {field!r}.",
                )
            )
            continue

        distinct = sorted({item.value for item in field_occurrences})

        if len(distinct) != 1:
            findings.append(
                Finding(
                    "PRIMARY_EVIDENCE_CONFLICT",
                    field,
                    f"Multiple distinct explicit values observed: {distinct!r}.",
                )
            )
            continue

        resolved[field] = distinct[0]

    # Frozen identity constraints.
    if resolved.get("source_id") not in {None, EXPECTED_SOURCE_ID}:
        findings.append(
            Finding("SOURCE_ID_MISMATCH", "source_id", "source_id must equal CA-3.")
        )

    if resolved.get("local_path") not in {None, EXPECTED_SOURCE_PATH}:
        findings.append(
            Finding(
                "LOCAL_PATH_MISMATCH",
                "local_path",
                "local_path does not equal the frozen CA-3 source path.",
            )
        )

    # Frozen contract constraints.
    fields = contract["fields"]

    if "source_kind" in resolved and resolved["source_kind"] not in fields["source_kind"]["allowed"]:
        findings.append(
            Finding("UNSUPPORTED_SOURCE_KIND", "source_kind", resolved["source_kind"])
        )

    if "rights_basis" in resolved and resolved["rights_basis"] not in fields["rights_basis"]["allowed"]:
        findings.append(
            Finding("INVALID_RIGHTS_BASIS", "rights_basis", resolved["rights_basis"])
        )

    if "rights_status" in resolved and resolved["rights_status"] != "verified":
        findings.append(
            Finding(
                "RIGHTS_NOT_VERIFIED",
                "rights_status",
                "rights_status must be exactly 'verified'.",
            )
        )

    if "provenance_status" in resolved and resolved["provenance_status"] != "verified":
        findings.append(
            Finding(
                "PROVENANCE_NOT_VERIFIED",
                "provenance_status",
                "provenance_status must be exactly 'verified'.",
            )
        )

    if (
        "redistribution_status" in resolved
        and resolved["redistribution_status"] not in {"permitted", "not_permitted"}
    ):
        findings.append(
            Finding(
                "REDISTRIBUTION_NOT_RESOLVED",
                "redistribution_status",
                "redistribution_status must be permitted or not_permitted.",
            )
        )

    if "source_locator" in resolved and not resolved["source_locator"]:
        findings.append(
            Finding("SOURCE_LOCATOR_EMPTY", "source_locator", "source_locator is empty.")
        )

    for field in ("rights_evidence", "provenance_evidence"):
        if field in resolved and not _valid_evidence_reference(resolved[field]):
            findings.append(
                Finding(
                    "INVALID_EVIDENCE_REFERENCE",
                    field,
                    f"{field} is not a tracked repository-relative path or http(s) URI.",
                )
            )

    if (
        "acquired_or_generated_at" in resolved
        and not _valid_rfc3339(resolved["acquired_or_generated_at"])
    ):
        findings.append(
            Finding(
                "INVALID_ACQUIRED_OR_GENERATED_AT",
                "acquired_or_generated_at",
                "Value is not RFC 3339 with timezone.",
            )
        )

    if "content_hash" in resolved and not HASH_RE.fullmatch(resolved["content_hash"]):
        findings.append(
            Finding(
                "INVALID_CONTENT_HASH",
                "content_hash",
                "Computed content hash is not sha256:<64 lowercase hex>.",
            )
        )

    disposition = DISPOSITION_READY if not findings else DISPOSITION_FAIL

    return {
        "work_order": "OIC-CANADA-CORPUS-EVIDENCE-RECONCILIATION-001",
        "status": "EXECUTED_READ_ONLY",
        "disposition": disposition,
        "population": {
            "source_count": 1,
            "source_ids": [EXPECTED_SOURCE_ID],
            "source_path": EXPECTED_SOURCE_PATH,
        },
        "resolved_candidate_manifest_fields": resolved,
        "field_support": support,
        "findings": [asdict(item) for item in findings],
        "extraction_policy": {
            "source_context_key": "source_id",
            "required_source_context_value": EXPECTED_SOURCE_ID,
            "accepted_manifest_field_names": list(EVIDENCE_EXTRACTED_FIELDS),
            "aliases_authorized": False,
            "fuzzy_mapping_authorized": False,
            "missing_value_inference_authorized": False,
            "conflicting_value_discretionary_resolution_authorized": False,
            "corroborating_markdown_pass_critical_authorized": False,
            "content_hash_derivation": "BYTE_SHA256_ONLY",
        },
        "source_content_policy": {
            "byte_hash_computed": True,
            "parse_authorized": False,
            "render_authorized": False,
            "text_extraction_authorized": False,
            "semantic_inspection_authorized": False,
        },
        "source_manifest_created": False,
        "rights_established": False,
        "provenance_established": False,
        "legal_clearance_established": False,
        "provider_model_network_calls": 0,
        "ontology_007r1_execution_authorized": False,
        "q011_creation_authorized": False,
        "canonicalization_authorized": False,
        "institutional_ir_authorized": False,
        "control_envelope_authorized": False,
        "rego_compilation_authorized": False,
        "runtime_evaluation_authorized": False,
        "claim_ceiling": (
            "Structural evidence reconciliation only. READY would establish only "
            "that frozen evidence can explicitly populate the frozen manifest "
            "contract for CA-3. It is not legal advice and does not itself "
            "establish rights, provenance truth, legal clearance, semantic "
            "correctness, institutional authority, benchmark validity, production "
            "readiness, enterprise readiness, or authorization for blocked work."
        ),
    }


def execute_read_only() -> dict[str, Any]:
    allow, _freeze, contract = load_controls()
    verify_git_identities(allow)

    primary = allow["primary_machine_readable_evidence"]

    documents: list[tuple[str, Any]] = []
    for item in primary:
        path = ROOT / item["path"]
        documents.append(
            (
                item["path"],
                json.loads(path.read_text(encoding="utf-8")),
            )
        )

    # The only permitted access to the source object is byte-level hashing.
    source_path = ROOT / EXPECTED_SOURCE_PATH
    computed = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()

    return reconcile_from_documents(
        documents=documents,
        contract=contract,
        computed_content_hash=computed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        # Static preflight only. Critically, do not open real evidence here.
        load_controls()
        print("static preflight: PASS")
        print("real evidence content read: ZERO")
        print("source XML content read: ZERO")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_read_only()

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        for finding in result["findings"]:
            print(
                f"{finding['code']}: field={finding['field']} "
                f"{finding['message']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
