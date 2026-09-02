#!/usr/bin/env python3
"""Deterministic fail-closed CA-3 evidence→manifest crosswalk instrument.

Static mode validates frozen controls only.

Execution mode is reserved for a later separately authorized one-shot run against
the preserved Inventory 001 receipt. It does not reopen real evidence files,
source XML, Markdown, network resources, or unlisted files. It never writes
SOURCE_MANIFEST.csv.

The instrument is deliberately conservative:
- candidate keys are frozen by target;
- source scope requires explicit CA-3 structural evidence;
- no post-observation key expansion;
- no silent enum/synonym translation;
- target-specific nonpromotion rules are enforced;
- exactly one admissible target value is required per manifest field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

BENCH = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "canada-evidence-to-manifest-crosswalk-001"
)

PLAN = BENCH / "PLAN-v0.1.md"
CONTRACT = BENCH / "CROSSWALK-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

MANIFEST_CONTRACT = (
    ROOT
    / "benchmarks/preflight/corpus-rights-provenance-001/"
      "SOURCE-MANIFEST-CONTRACT-v0.1.json"
)

LOCAL_INVENTORY_RECEIPT = (
    ROOT
    / ".local/evidence-vocabulary-inventory-receipts/"
      "OIC-CANADA-EVIDENCE-VOCABULARY-INVENTORY-001.json"
)

PLAN_SHA256 = "c3251d5dfec07206e0cf9af5832a872d15b746707f08b30d3e7e05e39536c9b2"
CONTRACT_SHA256 = "f4517e2a927784a6e231da788eaf128a3394cad7e399d5473bb42c54ba352df3"
PREREG_FREEZE_SHA256 = "46feaeb646df6ed4a99e3ec0e05a34b321351da88a288cb68e87afc64741cba7"
MANIFEST_CONTRACT_SHA256 = "3bf96bd6e6854a7beb048206f73465588df8f9b3182e1280ed7ec7878280559b"
LOCAL_INVENTORY_RECEIPT_SHA256 = "13032b0199bb1793bab0c246d0e687b1aa9942131fb19f321e9bf36fe408d0b9"

EXPECTED_SOURCE_ID = "CA-3"

DISPOSITION_COMPLETE = "CROSSWALK_COMPLETE"
DISPOSITION_INCOMPLETE = "CROSSWALK_INCOMPLETE_FAIL_CLOSED"

ESTABLISHED_DIRECT = "ESTABLISHED_DIRECT"
ESTABLISHED_DERIVED = "ESTABLISHED_DETERMINISTIC_DERIVATION"
MULTIPLE = "MULTIPLE_CANDIDATES_NOT_ESTABLISHED"
CONTRADICTORY = "CONTRADICTORY_NOT_ESTABLISHED"
MISSING = "MISSING_NOT_ESTABLISHED"
OUT_OF_SCOPE = "OUT_OF_SCOPE_NOT_ESTABLISHED"

HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Candidate:
    target_field: str
    artifact_path: str
    artifact_git_blob_sha: str
    json_pointer: str
    key: str
    raw_value: Any
    source_scope_pointer: str | None


@dataclass(frozen=True)
class Accepted:
    target_field: str
    value: str
    mapping_class: str
    candidate: Candidate
    transformation: str


@dataclass(frozen=True)
class FieldResult:
    target_field: str
    state: str
    value: str | None
    candidate_count: int
    admissible_value_count: int
    support: tuple[dict[str, Any], ...]
    notes: tuple[str, ...]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (CONTRACT, CONTRACT_SHA256),
        (PREREG_FREEZE, PREREG_FREEZE_SHA256),
        (MANIFEST_CONTRACT, MANIFEST_CONTRACT_SHA256),
    ):
        if sha256(path) != expected:
            raise SystemExit(
                f"FAIL frozen control digest mismatch: {path.relative_to(ROOT)}"
            )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    freeze = json.loads(PREREG_FREEZE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_CONTRACT.read_text(encoding="utf-8"))

    if contract["status"] != "FROZEN_NOT_EXECUTED":
        raise SystemExit("FAIL crosswalk contract status drift")
    if freeze["status"] != "PREREGISTERED_NOT_EXECUTED":
        raise SystemExit("FAIL preregistration status drift")
    if manifest["contract_id"] != "OIC-SOURCE-MANIFEST-CONTRACT-001":
        raise SystemExit("FAIL manifest contract identity drift")

    if contract["real_evidence_reread_authorized"] is not False:
        raise SystemExit("FAIL real evidence boundary drift")
    if contract["source_xml_inspection_authorized"] is not False:
        raise SystemExit("FAIL source XML boundary drift")
    if contract["source_manifest_creation_authorized"] is not False:
        raise SystemExit("FAIL manifest creation boundary drift")
    if contract["source_manifest_population_authorized"] is not False:
        raise SystemExit("FAIL manifest population boundary drift")

    return contract, freeze, manifest


def _parent_pointer(pointer: str) -> str:
    if not pointer or pointer == "/":
        return ""
    head, _, _tail = pointer.rpartition("/")
    return head


def _ancestor_object_pointers(pointer: str) -> list[str]:
    current = _parent_pointer(pointer)
    out: list[str] = []
    while True:
        out.append(current)
        if current == "":
            break
        current = _parent_pointer(current)
    return out


def _record_scalar(record: dict[str, Any]) -> Any | None:
    if record.get("scalar_mode") != "EXACT":
        return None
    return record.get("scalar_value")


def _records_by_artifact(records: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        out.setdefault(record["artifact_path"], []).append(record)
    return out


def _same_object_records(
    artifact_records: list[dict[str, Any]],
    pointer: str,
) -> list[dict[str, Any]]:
    parent = _parent_pointer(pointer)
    return [
        record
        for record in artifact_records
        if _parent_pointer(record["json_pointer"]) == parent
    ]


def _scope_pointer_for_record(
    record: dict[str, Any],
    artifact_records: list[dict[str, Any]],
) -> str | None:
    """Return nearest explicit enclosing object scoped to CA-3.

    The preserved inventory records scalar object-key values, but not scalar
    array members. Therefore only the exact source_id structural route is
    executable in Crosswalk 001 from this receipt shape. Other preregistered
    scope routes remain admissible in principle but are not fabricated from
    absent array-element data.
    """
    ancestors = _ancestor_object_pointers(record["json_pointer"])

    for object_pointer in ancestors:
        for candidate in artifact_records:
            if _parent_pointer(candidate["json_pointer"]) != object_pointer:
                continue
            if candidate["key"] != "source_id":
                continue
            if _record_scalar(candidate) == EXPECTED_SOURCE_ID:
                return object_pointer

    return None


def _is_http_uri(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_repo_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _valid_rfc3339(value: str) -> bool:
    if not value:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _candidate_records(
    *,
    target_field: str,
    records: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[list[Candidate], int]:
    allowed_keys = set(
        contract["candidate_key_allowlist_by_target"][target_field]
    )

    by_artifact = _records_by_artifact(records)
    candidates: list[Candidate] = []
    raw_candidate_count = 0

    for record in records:
        if record["key"] not in allowed_keys:
            continue

        raw_candidate_count += 1
        artifact_records = by_artifact[record["artifact_path"]]
        scope_pointer = _scope_pointer_for_record(record, artifact_records)

        if scope_pointer is None:
            continue

        scalar = _record_scalar(record)
        if scalar is None:
            continue

        candidates.append(
            Candidate(
                target_field=target_field,
                artifact_path=record["artifact_path"],
                artifact_git_blob_sha=record["artifact_git_blob_sha"],
                json_pointer=record["json_pointer"],
                key=record["key"],
                raw_value=scalar,
                source_scope_pointer=scope_pointer,
            )
        )

    return candidates, raw_candidate_count


def _context_has_exact_key(
    candidate: Candidate,
    records: list[dict[str, Any]],
    key: str,
) -> bool:
    artifact_records = [
        r for r in records if r["artifact_path"] == candidate.artifact_path
    ]

    candidate_parent = _parent_pointer(candidate.json_pointer)
    allowed_contexts = [candidate_parent] + _ancestor_object_pointers(
        candidate.json_pointer
    )

    for object_pointer in allowed_contexts:
        for record in artifact_records:
            if _parent_pointer(record["json_pointer"]) != object_pointer:
                continue
            if record["key"] == key:
                return True

    return False


def _transform_candidate(
    candidate: Candidate,
    *,
    target_field: str,
    records: list[dict[str, Any]],
    manifest_contract: dict[str, Any],
) -> Accepted | None:
    value = candidate.raw_value
    key = candidate.key

    if target_field == "source_id":
        if key == "source_id" and value == EXPECTED_SOURCE_ID:
            return Accepted(
                target_field,
                EXPECTED_SOURCE_ID,
                ESTABLISHED_DIRECT,
                candidate,
                "IDENTITY",
            )
        return None

    if target_field == "source_kind":
        if isinstance(value, str) and value in {"public", "synthetic"}:
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_CONTRACT_ENUM_IDENTITY",
            )
        return None

    if target_field == "source_locator":
        if isinstance(value, str) and _is_http_uri(value):
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_HTTP_URI_IDENTITY",
            )
        return None

    if target_field == "local_path":
        # Only frozen_bytes_path is semantically narrow enough for a source local
        # byte path. Receipt/evidence storage paths are not promoted.
        if key != "frozen_bytes_path":
            return None
        if isinstance(value, str) and _is_repo_relative(value):
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "FROZEN_BYTES_PATH_IDENTITY",
            )
        return None

    if target_field == "content_hash":
        # Only a scalar sha256 may qualify, and only when the same structural
        # record also contains frozen_bytes_path. Evidence hashes are not promoted.
        if key != "sha256":
            return None
        if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
            return None
        if not _context_has_exact_key(candidate, records, "frozen_bytes_path"):
            return None
        return Accepted(
            target_field,
            "sha256:" + value,
            ESTABLISHED_DERIVED,
            candidate,
            "PREFIX_SHA256_AFTER_SAME_CONTEXT_FROZEN_BYTES_BINDING",
        )

    if target_field == "rights_basis":
        allowed = set(
            manifest_contract["fields"]["rights_basis"]["allowed"]
        )
        if isinstance(value, str) and value in allowed:
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_CONTRACT_ENUM_IDENTITY",
            )
        return None

    if target_field in {"rights_evidence", "provenance_evidence"}:
        if not isinstance(value, str):
            return None
        if _is_http_uri(value) or _is_repo_relative(value):
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_EVIDENCE_REFERENCE_IDENTITY",
            )
        return None

    if target_field == "rights_status":
        if isinstance(value, str) and value == "verified":
            return Accepted(
                target_field,
                "verified",
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_MANIFEST_STATE_IDENTITY",
            )
        return None

    if target_field == "provenance_status":
        if isinstance(value, str) and value == "verified":
            return Accepted(
                target_field,
                "verified",
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_MANIFEST_STATE_IDENTITY",
            )
        return None

    if target_field == "redistribution_status":
        if key == "public_repository_redistribution_permission":
            if value is True:
                return Accepted(
                    target_field,
                    "permitted",
                    ESTABLISHED_DERIVED,
                    candidate,
                    "BOOLEAN_PUBLIC_REPOSITORY_PERMISSION_TRUE_TO_PERMITTED",
                )
            if value is False:
                return Accepted(
                    target_field,
                    "not_permitted",
                    ESTABLISHED_DERIVED,
                    candidate,
                    "BOOLEAN_PUBLIC_REPOSITORY_PERMISSION_FALSE_TO_NOT_PERMITTED",
                )

        if isinstance(value, str) and value in {"permitted", "not_permitted"}:
            return Accepted(
                target_field,
                value,
                ESTABLISHED_DIRECT,
                candidate,
                "EXACT_CONTRACT_ENUM_IDENTITY",
            )
        return None

    if target_field == "acquired_or_generated_at":
        # Only retrieval_utc may qualify, and only in explicit acquisition
        # context. capture_utc/evidence_capture_utc are not promoted.
        if key != "retrieval_utc":
            return None
        if not isinstance(value, str) or not _valid_rfc3339(value):
            return None
        if not (
            _context_has_exact_key(candidate, records, "acquisition_tool")
            or _context_has_exact_key(
                candidate,
                records,
                "acquisition_target_url",
            )
        ):
            return None

        return Accepted(
            target_field,
            value,
            ESTABLISHED_DIRECT,
            candidate,
            "RETRIEVAL_TIMESTAMP_IN_EXPLICIT_ACQUISITION_CONTEXT",
        )

    raise AssertionError(target_field)


def evaluate_field(
    *,
    target_field: str,
    records: list[dict[str, Any]],
    contract: dict[str, Any],
    manifest_contract: dict[str, Any],
) -> FieldResult:
    candidates, raw_count = _candidate_records(
        target_field=target_field,
        records=records,
        contract=contract,
    )

    accepted: list[Accepted] = []
    for candidate in candidates:
        transformed = _transform_candidate(
            candidate,
            target_field=target_field,
            records=records,
            manifest_contract=manifest_contract,
        )
        if transformed is not None:
            accepted.append(transformed)

    if not candidates:
        state = MISSING if raw_count == 0 else OUT_OF_SCOPE
        return FieldResult(
            target_field=target_field,
            state=state,
            value=None,
            candidate_count=raw_count,
            admissible_value_count=0,
            support=(),
            notes=(
                "No source-scoped scalar candidate survived the frozen candidate-key and CA-3 scope rules.",
            ),
        )

    if not accepted:
        state = MULTIPLE if len(candidates) > 1 else OUT_OF_SCOPE
        return FieldResult(
            target_field=target_field,
            state=state,
            value=None,
            candidate_count=raw_count,
            admissible_value_count=0,
            support=tuple(asdict(c) for c in candidates),
            notes=(
                "Candidate records exist but no target value survives the frozen target-specific nonpromotion/derivation rules.",
            ),
        )

    by_value: dict[str, list[Accepted]] = {}
    for item in accepted:
        by_value.setdefault(item.value, []).append(item)

    if len(by_value) > 1:
        return FieldResult(
            target_field=target_field,
            state=CONTRADICTORY,
            value=None,
            candidate_count=raw_count,
            admissible_value_count=len(by_value),
            support=tuple(
                {
                    **asdict(item.candidate),
                    "mapped_value": item.value,
                    "mapping_class": item.mapping_class,
                    "transformation": item.transformation,
                }
                for item in accepted
            ),
            notes=(
                "Multiple materially distinct admissible target values survive; no discretionary precedence is authorized.",
            ),
        )

    value = next(iter(by_value))
    support_items = by_value[value]
    mapping_classes = {item.mapping_class for item in support_items}

    mapping_class = (
        ESTABLISHED_DERIVED
        if ESTABLISHED_DERIVED in mapping_classes
        else ESTABLISHED_DIRECT
    )

    return FieldResult(
        target_field=target_field,
        state=mapping_class,
        value=value,
        candidate_count=raw_count,
        admissible_value_count=1,
        support=tuple(
            {
                **asdict(item.candidate),
                "mapped_value": item.value,
                "mapping_class": item.mapping_class,
                "transformation": item.transformation,
            }
            for item in support_items
        ),
        notes=(),
    )


def evaluate_records(
    records: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
    manifest_contract: dict[str, Any],
) -> dict[str, Any]:
    required_record_keys = {
        "artifact_path",
        "artifact_git_blob_sha",
        "json_pointer",
        "key",
        "value_type",
    }

    for index, record in enumerate(records):
        if not required_record_keys.issubset(record):
            missing = sorted(required_record_keys - set(record))
            raise ValueError(
                f"inventory record {index} missing required keys: {missing}"
            )

    field_results = [
        evaluate_field(
            target_field=field,
            records=records,
            contract=contract,
            manifest_contract=manifest_contract,
        )
        for field in contract["target_manifest_fields"]
    ]

    established_states = {ESTABLISHED_DIRECT, ESTABLISHED_DERIVED}
    established = [
        result for result in field_results if result.state in established_states
    ]

    complete = len(established) == len(contract["target_manifest_fields"])

    return {
        "work_order":
            "OIC-CANADA-EVIDENCE-TO-MANIFEST-CROSSWALK-001",
        "status":
            "EXECUTED_READ_ONLY",
        "disposition":
            DISPOSITION_COMPLETE if complete else DISPOSITION_INCOMPLETE,
        "population": {
            "source_count":
                1,
            "source_ids":
                [EXPECTED_SOURCE_ID],
        },
        "target_field_count":
            len(contract["target_manifest_fields"]),
        "established_field_count":
            len(established),
        "field_results":
            [asdict(result) for result in field_results],
        "candidate_key_expansion_performed":
            False,
        "real_evidence_reread":
            False,
        "source_xml_inspected":
            False,
        "corroborating_markdown_inspected":
            False,
        "network_used":
            False,
        "crosswalk_mapping_established":
            complete,
        "source_manifest_created":
            False,
        "source_manifest_population_authorized":
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
            "Crosswalk mapping only. A complete mapping would not itself "
            "establish legal rights, provenance truth, copyright clearance, "
            "semantic correctness, benchmark validity, production readiness, "
            "enterprise readiness, or downstream compiler/runtime authorization."
        ),
    }


def execute_read_only() -> dict[str, Any]:
    contract, _freeze, manifest_contract = load_controls()

    if sha256(LOCAL_INVENTORY_RECEIPT) != LOCAL_INVENTORY_RECEIPT_SHA256:
        raise SystemExit("FAIL preserved inventory receipt digest mismatch")

    inventory = json.loads(
        LOCAL_INVENTORY_RECEIPT.read_text(encoding="utf-8")
    )

    if inventory["work_order"] != "OIC-CANADA-EVIDENCE-VOCABULARY-INVENTORY-001":
        raise SystemExit("FAIL wrong inventory receipt")
    if inventory["status"] != "EXECUTED_READ_ONLY":
        raise SystemExit("FAIL inventory receipt status")
    if inventory["disposition"] != "INVENTORY_COMPLETE":
        raise SystemExit("FAIL inventory not complete")

    return evaluate_records(
        inventory["records"],
        contract=contract,
        manifest_contract=manifest_contract,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.execute_read_only:
        load_controls()
        print("static preflight: PASS")
        print("preserved real inventory receipt content read: ZERO")
        print("real evidence reread: ZERO")
        print("source XML read: ZERO")
        print("crosswalk executed: FALSE")
        print("SOURCE_MANIFEST.csv created: FALSE")
        return 0

    result = execute_read_only()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"disposition: {result['disposition']}")
        print(
            "established fields: "
            f"{result['established_field_count']}/"
            f"{result['target_field_count']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
