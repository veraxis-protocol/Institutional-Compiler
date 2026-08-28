"""Bounded deterministic candidate extraction for authorized synthetic sources.

This module proposes source-anchored candidates.  It does not admit meaning,
produce institutional IR or control envelopes, or invoke any runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

AUTHORIZED_SOURCES: Final[dict[str, tuple[str, str, str]]] = {
    "SYN-NS-GOV-1": (
        "benchmarks/preflight/code-start-v0.1/sources/SYNTHETIC-NORTHSTAR-GOVERNANCE-v1.txt",
        "b882459931ddf06fb647e6885c1ced368b4a5f45b6441df618484a30473a2a24",
        "SYNTHETIC_CURRENT",
    ),
    "SYN-NS-PROC-1": (
        "benchmarks/preflight/code-start-v0.1/sources/SYNTHETIC-NORTHSTAR-PROCEDURE-v1.txt",
        "cfb578274460cc17492f4b25a4db6893ce87a527e1207fe6a52b6384125ec073",
        "SYNTHETIC_SUPERSEDED",
    ),
    "SYN-NS-AMEND-2": (
        "benchmarks/preflight/code-start-v0.1/sources/SYNTHETIC-NORTHSTAR-AMENDMENT-v2.txt",
        "8e197bc9e01554853163dfb5f84ad807893f678b26673737c8a72ddf0c8daf47",
        "SYNTHETIC_CURRENT",
    ),
}


class CandidateExtractionError(ValueError):
    """The bounded extraction input fails an integrity or scope invariant."""


@dataclass(frozen=True)
class CandidateExtractionResult:
    """Deterministic source nodes, candidate units, and non-interpretation diagnostics."""

    nodes: tuple[dict[str, Any], ...]
    units: tuple[dict[str, Any], ...]
    diagnostics: tuple[dict[str, Any], ...]


def _sha256(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _byte_offset(text: str, character_offset: int) -> int:
    return len(text[:character_offset].encode("utf-8"))


def _node(source_id: str, text: str, start: int, end: int) -> dict[str, Any]:
    quote = text[start:end]
    start_byte = _byte_offset(text, start)
    end_byte = _byte_offset(text, end)
    return {
        "node_id": f"{source_id}:span:{start_byte}:{end_byte}",
        "source_id": source_id,
        "parent_id": None,
        "node_type": "clause",
        "text": quote,
        "page": None,
        "bbox": None,
        "content_hash": _sha256(quote.encode("utf-8")),
        "references": [],
    }


def _unit(
    node: dict[str, Any],
    *,
    unit_type: str,
    actor: str | None,
    action: str | None,
    object_: str | None,
    conditions: list[str] | None = None,
    evidence_requirements: list[str] | None = None,
    lifecycle_state: str,
) -> dict[str, Any]:
    anchor_projection = {
        "source_id": node["source_id"],
        "node_id": node["node_id"],
        "content_hash": node["content_hash"],
    }
    anchor_id = _sha256(
        json.dumps(anchor_projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    anchor = {
        "anchor_id": f"anchor:{anchor_id}",
        **anchor_projection,
        "quote": node["text"],
        "page": None,
        "bbox": None,
    }
    projection = {
        "unit_type": unit_type,
        "actor": actor,
        "action": action,
        "object": object_,
        "conditions": conditions or [],
        "exceptions": [],
        "evidence_requirements": evidence_requirements or [],
        **anchor_projection,
    }
    unit_id = _sha256(json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {
        "unit_id": f"cnu:{unit_id}",
        "unit_type": unit_type,
        "actor": actor,
        "action": action,
        "object": object_,
        "conditions": conditions or [],
        "exceptions": [],
        "evidence_requirements": evidence_requirements or [],
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "lifecycle_state": lifecycle_state,
        "confidence": None,
        "alternatives": [],
        "source_anchors": [anchor],
    }


def _emit(
    source_id: str,
    text: str,
    match: re.Match[str],
    lifecycle: str,
    **meaning: Any,  # noqa: ANN401 - schema-shaped fields are heterogeneous by design
) -> tuple[dict[str, Any], dict[str, Any]]:
    node = _node(source_id, text, match.start(), match.end())
    return node, _unit(node, lifecycle_state=lifecycle, **meaning)


def _extract_text(source_id: str, text: str, lifecycle: str) -> CandidateExtractionResult:
    nodes: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    covered: list[tuple[int, int]] = []

    def add(
        pattern: str,
        **meaning: Any,  # noqa: ANN401 - passed directly to the typed schema constructor
    ) -> None:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            node, unit = _emit(source_id, text, match, lifecycle, **meaning)
            nodes.append(node)
            units.append(unit)
            covered.append(match.span())

    definition = r"(?P<actor>[A-Za-z][\w-]*) means (?P<object>[^.]+)\."
    for match in re.finditer(definition, text, flags=re.MULTILINE):
        node, unit = _emit(
            source_id,
            text,
            match,
            lifecycle,
            unit_type="definition",
            actor=match.group("actor"),
            action="means",
            object_=re.sub(r"\s+", " ", match.group("object")).strip(),
        )
        nodes.append(node)
        units.append(unit)
        covered.append(match.span())

    for match in re.finditer(
        r"TEST_PURCHASE_(?P<level>LOW|HIGH) requires (?:both |only )?"
        r"(?P<approvers>Approver-[A-Z](?:\s+and\s+Approver-[A-Z])?)(?:\.|,)",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        conditions = re.findall(r"Approver-[A-Z]", match.group("approvers"), re.IGNORECASE)
        node, unit = _emit(
            source_id,
            text,
            match,
            lifecycle,
            unit_type="condition",
            actor=None,
            action=f"TEST_PURCHASE_{match.group('level').upper()}",
            object_="approval",
            conditions=conditions,
        )
        nodes.append(node)
        units.append(unit)
        covered.append(match.span())

    add(
        r"Approver-A may delegate TEST_PURCHASE_LOW to Delegate-A\.",
        unit_type="delegation",
        actor="Approver-A",
        action="delegate",
        object_="TEST_PURCHASE_LOW to Delegate-A",
    )
    add(
        r"No other delegation\s+is recognized\.",
        unit_type="prohibition",
        actor=None,
        action="recognize",
        object_="other delegation",
    )
    add(
        r"every proposal carries its source identifier, amount,\s+requester identifier, "
        r"and approval records\.",
        unit_type="evidence_duty",
        actor=None,
        action="proposal_carries_evidence",
        object_=None,
        evidence_requirements=[
            "source identifier",
            "amount",
            "requester identifier",
            "approval records",
        ],
    )
    add(
        r"TEST_EMERGENCY may omit Approver-B only when an emergency record and\s+"
        r"Approver-A approval are present\.",
        unit_type="exception",
        actor=None,
        action="TEST_EMERGENCY",
        object_="omit Approver-B",
        conditions=["emergency record present", "Approver-A approval present"],
    )
    add(
        r"Approver-A may refer any proposal for human review\.",
        unit_type="discretion",
        actor="Approver-A",
        action="refer",
        object_="any proposal for human review",
    )
    add(
        r"Referral establishes no approval\.",
        unit_type="prohibition",
        actor=None,
        action="treat referral as approval",
        object_=None,
    )
    add(
        r"A stale procedure must be refused as\s+current evidence\.",
        unit_type="prohibition",
        actor=None,
        action="use as current evidence",
        object_="SYNTHETIC-NORTHSTAR-PROCEDURE-v1",
    )

    diagnostics: list[dict[str, Any]] = []
    for match in re.finditer(r"[^\n](?:.*(?:\n(?!\n).*)*)", text):
        paragraph = match.group(0)
        if any(match.start() < end and match.end() > start for start, end in covered):
            continue
        normalized = re.sub(r"\s+", " ", paragraph).strip()
        if not normalized:
            continue
        node = _node(source_id, text, match.start(), match.end())
        nodes.append(node)
        if re.search(r"\b(?:should|may|must|requires?|approval|authority)\b", normalized, re.I):
            code = "UNSUPPORTED_NORMATIVE_PATTERN"
        elif normalized.startswith(("SYNTHETIC", "Document:", "Version:", "Created:")):
            code = "NON_NORMATIVE_METADATA"
        else:
            code = "DOCUMENT_CONTROL_METADATA"
        diagnostics.append({"code": code, "node_id": node["node_id"], "message": normalized})

    ordered_nodes = tuple(sorted(nodes, key=lambda item: item["node_id"]))
    ordered_units = tuple(sorted(units, key=lambda item: item["unit_id"]))
    ordered_diagnostics = tuple(sorted(diagnostics, key=lambda item: item["node_id"]))
    return CandidateExtractionResult(ordered_nodes, ordered_units, ordered_diagnostics)


def extract_authorized_candidates(root: Path) -> CandidateExtractionResult:
    """Verify and extract exactly the owner-authorized synthetic source set."""
    source_set_path = root / "benchmarks/preflight/code-start-v0.1/SOURCE-SET.json"
    source_set = json.loads(source_set_path.read_text(encoding="utf-8"))
    records = {item["source_id"]: item for item in source_set.get("sources", [])}
    if source_set.get("global_manifest_status") != "INCOMPLETE":
        raise CandidateExtractionError("global manifest status must remain INCOMPLETE")

    all_nodes: list[dict[str, Any]] = []
    all_units: list[dict[str, Any]] = []
    all_diagnostics: list[dict[str, Any]] = []
    for source_id, (path, digest, effective_state) in AUTHORIZED_SOURCES.items():
        record = records.get(source_id)
        expected = {
            "path": path,
            "sha256": digest,
            "origin_classification": "SYNTHETIC_FICTIONAL",
            "benchmark_authority": "SYNTHETIC_BENCHMARK_ONLY",
            "issuer": "Veraxis synthetic fixture generator",
            "effective_state": effective_state,
        }
        if record is None or any(record.get(key) != value for key, value in expected.items()):
            raise CandidateExtractionError(f"source-set mismatch: {source_id}")
        payload = (root / path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise CandidateExtractionError(f"source digest mismatch: {source_id}")
        text = payload.decode("utf-8")
        if f"Effective state: {effective_state}" not in text:
            raise CandidateExtractionError(f"source header/currentness mismatch: {source_id}")
        lifecycle = "superseded" if effective_state == "SYNTHETIC_SUPERSEDED" else "proposed"
        result = _extract_text(source_id, text, lifecycle)
        all_nodes.extend(result.nodes)
        all_units.extend(result.units)
        all_diagnostics.extend(result.diagnostics)

    return CandidateExtractionResult(
        tuple(sorted(all_nodes, key=lambda item: item["node_id"])),
        tuple(sorted(all_units, key=lambda item: item["unit_id"])),
        tuple(sorted(all_diagnostics, key=lambda item: item["node_id"])),
    )
