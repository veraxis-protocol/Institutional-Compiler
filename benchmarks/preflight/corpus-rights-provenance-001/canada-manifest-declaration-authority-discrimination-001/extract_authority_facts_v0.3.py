#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[4]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-manifest-declaration-authority-discrimination-001"
)
INVENTORY = BENCH / "AUTHORITY-SOURCE-INVENTORY-v0.2.json"
DISCRIM = BENCH / "evaluate_authority_discrimination_v0.2.py"

INVENTORY_SHA256 = "10fa7c20d36ba541468675611bdedc5941758fa39eb1b803c4239a9e86ab1899"
DISCRIM_SHA256 = "6d9be5309b64476fab9e0b0782a4ca67c2caf82f7c1af71c5658abbcb19275f0"

TARGET_FIELDS = frozenset({
    "source_kind",
    "source_locator",
    "rights_basis",
    "rights_status",
    "provenance_status",
    "redistribution_status",
})
RIGHTS_FIELDS = frozenset({"rights_basis", "rights_status", "redistribution_status"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_discriminator():
    if sha256(DISCRIM) != DISCRIM_SHA256:
        raise SystemExit("FAIL: v0.2 discriminator digest mismatch")
    spec = importlib.util.spec_from_file_location("authority_discriminator_v02", DISCRIM)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL: cannot load v0.2 discriminator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["authority_discriminator_v02"] = module
    spec.loader.exec_module(module)
    return module


def load_inventory() -> dict[str, Any]:
    if sha256(INVENTORY) != INVENTORY_SHA256:
        raise SystemExit("FAIL: authority inventory digest mismatch")
    inventory = load_json(INVENTORY)
    assert inventory["status"] == "FROZEN_INPUT_INVENTORY_NOT_EVALUATED"
    assert inventory["input_count"] == 6
    assert inventory["authority_channels_evaluated"] is False
    assert inventory["declaration_values_created"] is False
    return inventory


def verify_inventory_bytes(inventory: Mapping[str, Any]) -> None:
    for row in inventory["inputs"]:
        path = ROOT / row["path"]
        if not path.is_file():
            raise SystemExit(f"FAIL: missing frozen authority input {row['path']}")
        if sha256(path) != row["sha256"]:
            raise SystemExit(f"FAIL: authority input digest drift {row['path']}")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ca3_record(records: Any) -> Mapping[str, Any]:
    if not isinstance(records, list):
        raise ValueError("records must be list")
    matches = [r for r in records if isinstance(r, dict) and r.get("source_id") == "CA-3"]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one CA-3 rights record; got {len(matches)}")
    return matches[0]


def _ca3_index_entry(entries: Any) -> Mapping[str, Any]:
    if not isinstance(entries, list):
        raise ValueError("entries must be list")
    matches = [r for r in entries if isinstance(r, dict) and r.get("source_id") == "CA-3"]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one CA-3 acquisition entry; got {len(matches)}")
    return matches[0]


def _explicit_complete_act(
    value: Any,
    *,
    identity_keys: Sequence[str],
    field_key: str | None = None,
    field_value: str | None = None,
    fields_key: str | None = None,
    allowed_fields: frozenset[str] | None = None,
) -> tuple[bool, bool, bool, frozenset[str]]:
    if not isinstance(value, dict):
        return False, False, False, frozenset()

    identity = any(_nonempty(value.get(k)) for k in identity_keys)
    basis = _nonempty(value.get("authority_basis"))
    complete = value.get("act_complete") is True

    scoped: set[str] = set()
    if field_key is not None and value.get(field_key) == field_value:
        scoped.add(str(field_value))
    if fields_key is not None:
        raw = value.get(fields_key)
        if isinstance(raw, list):
            scoped |= {v for v in raw if isinstance(v, str)}

    if allowed_fields is not None:
        scoped &= set(allowed_fields)

    return complete, identity, basis, frozenset(scoped)


def _existing_rules(manifest: Mapping[str, Any]) -> frozenset[str]:
    raw = manifest.get("manifest_value_derivation_rules")
    if not isinstance(raw, list):
        return frozenset()

    established: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            continue
        target = row.get("target_field")
        if target not in TARGET_FIELDS:
            continue
        if not _nonempty(row.get("rule_id")):
            continue
        if not _nonempty(row.get("authority_basis")):
            continue
        if row.get("deterministic_replay") is not True:
            continue

        scope = row.get("scope")
        covers_ca3 = False
        if isinstance(scope, dict):
            if scope.get("source_id") == "CA-3":
                covers_ca3 = True
            ids = scope.get("source_ids")
            if isinstance(ids, list) and "CA-3" in ids:
                covers_ca3 = True

        if covers_ca3:
            established.add(target)

    return frozenset(established)


def extract_facts_from_docs(
    docs: Mapping[str, Mapping[str, Any]],
    discriminator: Any,
):
    manifest = docs["MANIFEST_RESULT_SHAPE_CONTRACT"]
    rights_doc = docs["ENGINEERING_RIGHTS_REVIEW_RECORD"]
    acq_freeze = docs["ACQUISITION_CONTROL_RECORD"]
    acq_index = docs["ACQUISITION_INDEX"]
    counsel = docs["UNSUBMITTED_COUNSEL_REVIEW_REQUEST"]
    actions = docs["ACTOR_AND_PENDING_ACTION_REGISTER"]

    ca3_rights = _ca3_record(rights_doc.get("records"))
    ca3_index = _ca3_index_entry(acq_index.get("entries"))

    source_origin = _explicit_complete_act(
        ca3_rights.get("source_origin_declaration"),
        identity_keys=("declarant_identity", "actor_identity"),
        field_key="target_field",
        field_value="source_kind",
        allowed_fields=frozenset({"source_kind"}),
    )
    publisher_locator = _explicit_complete_act(
        ca3_rights.get("publisher_canonical_locator_declaration"),
        identity_keys=("declarant_identity", "actor_identity", "publisher_identity"),
        field_key="target_field",
        field_value="source_locator",
        allowed_fields=frozenset({"source_locator"}),
    )
    institutional = _explicit_complete_act(
        ca3_rights.get("institutional_manifest_admission"),
        identity_keys=("actor_identity", "declarant_identity"),
        fields_key="target_fields",
        allowed_fields=TARGET_FIELDS,
    )
    rights_adjudication = _explicit_complete_act(
        ca3_rights.get("institutional_rights_adjudication"),
        identity_keys=("actor_identity", "reviewer_identity"),
        fields_key="target_fields",
        allowed_fields=RIGHTS_FIELDS,
    )
    provenance_admission = _explicit_complete_act(
        ca3_index.get("institutional_provenance_admission"),
        identity_keys=("actor_identity", "reviewer_identity"),
        field_key="target_field",
        field_value="provenance_status",
        allowed_fields=frozenset({"provenance_status"}),
    )

    ca3_questions = []
    questions = counsel.get("questions")
    if isinstance(questions, list):
        ca3_questions = [
            q for q in questions
            if isinstance(q, dict)
            and isinstance(q.get("source_ids"), list)
            and "CA-3" in q["source_ids"]
        ]

    counsel_candidates: list[Mapping[str, Any]] = []
    for q in ca3_questions:
        value = q.get("counsel_disposition")
        if isinstance(value, dict):
            counsel_candidates.append(value)

    completed_actions = []
    raw_actions = actions.get("actions")
    if isinstance(raw_actions, list):
        for row in raw_actions:
            if not isinstance(row, dict):
                continue
            if row.get("actor") != "COUNSEL":
                continue
            blocked = row.get("blocks_source_ids")
            if not isinstance(blocked, list) or "CA-3" not in blocked:
                continue
            if row.get("act_complete") is True:
                completed_actions.append(row)

    counsel_complete = False
    counsel_identity = False
    counsel_basis = False
    counsel_fields: set[str] = set()

    for value in counsel_candidates:
        complete, identity, basis, fields = _explicit_complete_act(
            value,
            identity_keys=("actor_identity", "counsel_identity"),
            fields_key="target_manifest_fields",
            allowed_fields=RIGHTS_FIELDS,
        )
        if complete:
            counsel_complete = True
        if identity:
            counsel_identity = True
        if basis:
            counsel_basis = True
        counsel_fields |= set(fields)

    # A completed external action may provide explicit identity/basis, but it
    # still cannot create field scope unless the counsel disposition itself
    # names the target manifest fields.
    for row in completed_actions:
        if _nonempty(row.get("actor_identity")):
            counsel_identity = True
        if _nonempty(row.get("authority_basis")):
            counsel_basis = True

    rights_binding = False
    evidence_hashes = ca3_rights.get("evidence_hashes")
    if isinstance(evidence_hashes, list):
        for row in evidence_hashes:
            if not isinstance(row, dict):
                continue
            if not _nonempty(row.get("evidence_id")):
                continue
            if _nonempty(row.get("sha256")) or row.get("http_status") is not None:
                rights_binding = True
                break

    provenance_binding = (
        _nonempty(ca3_index.get("receipt_id"))
        and _nonempty(ca3_index.get("sha256"))
        and isinstance(acq_freeze.get("committed_to_repository_source_ids"), list)
        and "CA-3" in acq_freeze["committed_to_repository_source_ids"]
    )

    temporal_scope = (
        _nonempty(ca3_index.get("retrieval_utc"))
        and _nonempty(acq_freeze.get("acquisition_tool_version"))
    )

    fields_obj = manifest.get("fields")
    manifest_fields = (
        frozenset(k for k in fields_obj if k in TARGET_FIELDS)
        if isinstance(fields_obj, dict)
        else frozenset()
    )

    publisher_identity = _nonempty(ca3_rights.get("publisher"))

    return discriminator.Facts(
        source_origin_decl=source_origin[0],
        source_origin_identity=source_origin[1],
        source_origin_basis=source_origin[2],
        publisher_locator_decl=publisher_locator[0],
        publisher_identity=publisher_identity,
        institutional_admission=institutional[0],
        institutional_identity=institutional[1],
        institutional_basis=institutional[2],
        institutional_fields=institutional[3],
        rights_adjudication=rights_adjudication[0],
        rights_identity=rights_adjudication[1],
        rights_basis=rights_adjudication[2],
        counsel_disposition=counsel_complete,
        counsel_identity=counsel_identity,
        counsel_basis=counsel_basis,
        counsel_fields=frozenset(counsel_fields),
        provenance_admission=provenance_admission[0],
        provenance_identity=provenance_admission[1],
        provenance_basis=provenance_admission[2],
        existing_rules=_existing_rules(manifest),
        rights_evidence_binding=rights_binding,
        provenance_evidence_binding=provenance_binding,
        temporal_scope=temporal_scope,
        manifest_fields=manifest_fields,
    )


def load_real_docs(inventory: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    verify_inventory_bytes(inventory)
    docs: dict[str, dict[str, Any]] = {}
    for row in inventory["inputs"]:
        role = row["artifact_role"]
        docs[role] = load_json(ROOT / row["path"])
    return docs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-real-input-bytes", action="store_true")
    args = parser.parse_args(argv)

    inventory = load_inventory()
    load_discriminator()

    if args.verify_real_input_bytes:
        # Hash verification only. This deliberately does not parse/evaluate
        # the six authority documents.
        verify_inventory_bytes(inventory)
        print("real authority input bytes: HASH-VERIFIED ONLY")
        print("real authority semantics evaluated: FALSE")
    else:
        print("adapter static preflight: PASS")
        print("real authority documents parsed: FALSE")
        print("authority channels evaluated: FALSE")
        print("declaration values created: FALSE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
