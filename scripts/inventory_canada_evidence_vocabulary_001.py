#!/usr/bin/env python3
"""Deterministic descriptive inventory for frozen Canada evidence JSON.

Static mode validates frozen controls and does not read the real evidence.

Execution mode, only when separately authorized, inventories the frozen
primary machine-readable allowlist. It does not inspect corroborating
Markdown, source XML, unlisted files, or network resources. It performs no
semantic interpretation, rights/provenance adjudication, manifest mapping,
crosswalk creation, or SOURCE_MANIFEST.csv write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-vocabulary-inventory-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "INVENTORY-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

ALLOWLIST = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-reconciliation-001/EVIDENCE-ALLOWLIST-v0.1.json"
)

PLAN_SHA256 = "0e464c532a259b19f136b76ca9d3471caeb8b0d98f9a88823bfc6f43b699b638"
CONTRACT_SHA256 = "3cc411a2ed2d48babc563dbb08ec0798a4146b35ae5c4646480ea34f3b008eaa"
PREREG_FREEZE_SHA256 = "f21b2eac893e6eea31dd03294f8c224466339b4ae090c57b10cbb62f1dd0ce90"
ALLOWLIST_SHA256 = "8dc6fac14ab38390231a7561668e39075ace9446c1d3736674f496818293ef95"

DISPOSITION_COMPLETE = "INVENTORY_COMPLETE"
DISPOSITION_INCOMPLETE = "INVENTORY_INCOMPLETE_FAIL_CLOSED"


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains a duplicate exact key."""


@dataclass(frozen=True)
class InventoryRecord:
    artifact_path: str
    artifact_git_blob_sha: str
    json_pointer: str
    key: str
    value_type: str
    array_length: int | None = None
    scalar_mode: str | None = None
    scalar_value: Any | None = None
    scalar_sha256: str | None = None
    scalar_utf8_byte_length: int | None = None


@dataclass(frozen=True)
class Finding:
    code: str
    artifact_path: str
    message: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (ALLOWLIST, ALLOWLIST_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))

    if contract["status"] != "FROZEN_NOT_EXECUTED":
        raise SystemExit("FAIL inventory contract status drift")
    if freeze["status"] != "PREREGISTERED_NOT_EXECUTED":
        raise SystemExit("FAIL preregistration status drift")
    if allow["population"]["source_ids"] != ["CA-3"]:
        raise SystemExit("FAIL population drift")

    if contract["inspection_scope"]["corroborating_markdown"] != "FORBIDDEN":
        raise SystemExit("FAIL Markdown inspection boundary drift")
    if contract["inspection_scope"]["source_xml"] != "FORBIDDEN":
        raise SystemExit("FAIL source XML boundary drift")
    if contract["inspection_scope"]["network"] != "FORBIDDEN":
        raise SystemExit("FAIL network boundary drift")

    algo = contract["inventory_algorithm"]
    if algo["key_normalization_authorized"] is not False:
        raise SystemExit("FAIL key-normalization boundary drift")
    if algo["alias_generation_authorized"] is not False:
        raise SystemExit("FAIL alias boundary drift")
    if algo["semantic_mapping_authorized"] is not False:
        raise SystemExit("FAIL semantic-mapping boundary drift")
    if algo["manifest_field_mapping_authorized"] is not False:
        raise SystemExit("FAIL manifest-mapping boundary drift")

    return contract, freeze, allow


def _git_blob(path: str, commit: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=ROOT,
        text=True,
    ).strip()


def verify_primary_git_identities(allow: dict[str, Any]) -> None:
    for item in allow["primary_machine_readable_evidence"]:
        actual = _git_blob(item["path"])
        if actual != item["git_blob_sha"]:
            raise SystemExit(f"FAIL Git blob drift: {item['path']}")


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate exact JSON key: {key!r}")
        out[key] = value
    return out


def parse_json_strict(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_pairs_hook)


def _escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _scalar_fields(value: Any) -> dict[str, Any]:
    value_type = _value_type(value)

    if value_type == "null":
        return {
            "scalar_mode": "EXACT",
            "scalar_value": None,
        }

    if value_type in {"boolean", "number"}:
        return {
            "scalar_mode": "EXACT",
            "scalar_value": value,
        }

    if value_type == "string":
        raw = value.encode("utf-8")
        if len(value) <= 256:
            return {
                "scalar_mode": "EXACT",
                "scalar_value": value,
            }
        return {
            "scalar_mode": "SHA256_AND_UTF8_BYTE_LENGTH_ONLY",
            "scalar_sha256": hashlib.sha256(raw).hexdigest(),
            "scalar_utf8_byte_length": len(raw),
        }

    return {}


def inventory_value(
    value: Any,
    *,
    artifact_path: str,
    artifact_git_blob_sha: str,
    pointer: str = "",
) -> list[InventoryRecord]:
    """Depth-first, document-order inventory of every object key."""
    records: list[InventoryRecord] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_pointer = pointer + "/" + _escape_pointer_part(key)
            kind = _value_type(child)

            kwargs: dict[str, Any] = {}
            if kind == "array":
                kwargs["array_length"] = len(child)
            else:
                kwargs.update(_scalar_fields(child))

            records.append(
                InventoryRecord(
                    artifact_path=artifact_path,
                    artifact_git_blob_sha=artifact_git_blob_sha,
                    json_pointer=child_pointer,
                    key=key,
                    value_type=kind,
                    **kwargs,
                )
            )

            if isinstance(child, (dict, list)):
                records.extend(
                    inventory_value(
                        child,
                        artifact_path=artifact_path,
                        artifact_git_blob_sha=artifact_git_blob_sha,
                        pointer=child_pointer,
                    )
                )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                records.extend(
                    inventory_value(
                        child,
                        artifact_path=artifact_path,
                        artifact_git_blob_sha=artifact_git_blob_sha,
                        pointer=f"{pointer}/{index}",
                    )
                )

    return records


def inventory_document_text(
    *,
    artifact_path: str,
    artifact_git_blob_sha: str,
    text: str,
) -> list[InventoryRecord]:
    parsed = parse_json_strict(text)
    return inventory_value(
        parsed,
        artifact_path=artifact_path,
        artifact_git_blob_sha=artifact_git_blob_sha,
    )


def execute_inventory() -> dict[str, Any]:
    contract, _freeze, allow = load_controls()
    verify_primary_git_identities(allow)

    records: list[InventoryRecord] = []
    findings: list[Finding] = []
    artifact_summaries: list[dict[str, Any]] = []

    for item in allow["primary_machine_readable_evidence"]:
        path = ROOT / item["path"]

        try:
            text = path.read_text(encoding="utf-8")
            artifact_records = inventory_document_text(
                artifact_path=item["path"],
                artifact_git_blob_sha=item["git_blob_sha"],
                text=text,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
            findings.append(
                Finding(
                    code="ARTIFACT_INVENTORY_FAILED",
                    artifact_path=item["path"],
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        records.extend(artifact_records)
        artifact_summaries.append(
            {
                "artifact_path": item["path"],
                "artifact_git_blob_sha": item["git_blob_sha"],
                "object_key_record_count": len(artifact_records),
            }
        )

    expected_artifact_count = len(allow["primary_machine_readable_evidence"])
    complete = (
        not findings
        and len(artifact_summaries) == expected_artifact_count
    )

    disposition = (
        DISPOSITION_COMPLETE if complete else DISPOSITION_INCOMPLETE
    )

    return {
        "work_order":
            "OIC-CANADA-EVIDENCE-VOCABULARY-INVENTORY-001",
        "status":
            "EXECUTED_READ_ONLY",
        "disposition":
            disposition,
        "population": {
            "source_count":
                1,
            "source_ids":
                ["CA-3"],
        },
        "primary_artifact_expected_count":
            expected_artifact_count,
        "primary_artifact_inventoried_count":
            len(artifact_summaries),
        "artifact_summaries":
            artifact_summaries,
        "record_count":
            len(records),
        "records":
            [asdict(record) for record in records],
        "findings":
            [asdict(finding) for finding in findings],
        "inventory_algorithm": {
            "traversal":
                contract["inventory_algorithm"]["traversal"],
            "record_every_object_key":
                True,
            "record_json_pointer":
                True,
            "record_key_exactly":
                True,
            "record_value_type":
                True,
            "key_normalization_authorized":
                False,
            "alias_generation_authorized":
                False,
            "semantic_mapping_authorized":
                False,
            "manifest_field_mapping_authorized":
                False,
            "rights_interpretation_authorized":
                False,
            "provenance_interpretation_authorized":
                False,
        },
        "inspection_boundaries": {
            "corroborating_markdown_inspected":
                False,
            "source_xml_inspected":
                False,
            "unlisted_files_inspected":
                False,
            "network_used":
                False,
        },
        "crosswalk_created":
            False,
        "source_manifest_created":
            False,
        "rights_established":
            False,
        "provenance_established":
            False,
        "legal_clearance_established":
            False,
        "provider_model_network_calls":
            0,
        "ontology_007r1_execution_authorized":
            False,
        "q011_creation_authorized":
            False,
        "canonicalization_authorized":
            False,
        "institutional_ir_authorized":
            False,
        "control_envelope_authorized":
            False,
        "rego_compilation_authorized":
            False,
        "runtime_evaluation_authorized":
            False,
        "claim_ceiling": (
            "Descriptive vocabulary inventory only. INVENTORY_COMPLETE does "
            "not establish any mapping to SOURCE_MANIFEST.csv, rights, "
            "provenance, legal clearance, evidence sufficiency, semantic "
            "correctness, or downstream compiler/runtime authorization."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        load_controls()
        print("static preflight: PASS")
        print("real evidence content read: ZERO")
        print("source XML read: ZERO")
        print("crosswalk created: FALSE")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_inventory()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(f"records: {result['record_count']}")
        print(
            "artifacts: "
            f"{result['primary_artifact_inventoried_count']}/"
            f"{result['primary_artifact_expected_count']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
