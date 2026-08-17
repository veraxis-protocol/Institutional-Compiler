"""The bounded synthetic OIC compiler front end.

Scope
-----
This is a demonstration lane. The grammar it reads is a small, line-oriented
synthetic notation invented for one scenario; it is **not** a general
legal-language parser, and nothing here should be read as one. What the lane
demonstrates is not extraction quality but the *chain*: which artifact each
executable field came from, and what had to be admitted before it became
executable at all.

The chain
---------
    synthetic source
      -> SourceDocument / SourceNode
      -> SourceAnchor
      -> CandidateNormativeUnit
      -> owner-authored AdmissionRecord
      -> InstitutionalIR
      -> AuthorityRecord
      -> OpenControlEnvelope
      -> RuntimeBinding

Every object emitted here is shaped by the existing governing schemas under
``schemas/draft/`` (plus, for the runtime binding alone, a demo-local schema).
No parallel canonical institutional model is introduced and no governing schema
is modified: the runtime binding is a *projection* alongside the envelope, never
an extension of it.

The load-bearing rule
--------------------
Extraction does not confer executability. Every candidate the parser produces is
``interpretation_state="extracted"``. A candidate becomes executable only when an
owner-authored AdmissionRecord names it with disposition ``admit``. The scenario
deliberately contains a ``GUIDANCE`` line that extracts cleanly and is never
admitted, so the difference is observable rather than asserted.

Determinism
-----------
Identical source bytes and an identical declared logical time produce identical
output, byte for byte. Nothing here reads the wall clock, the environment, the
filesystem beyond the source it was handed, or any random source.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from oic.errors import OICError

__all__ = [
    "ADMITTED",
    "COMPILER_VERSION",
    "CONTROL_ENVELOPE_SCHEMA_VERSION",
    "GROUND_ATOMS",
    "GROUND_IDS",
    "INSTITUTIONAL_IR_SCHEMA_VERSION",
    "RUNTIME_BINDING_SCHEMA_VERSION",
    "SYNTHETIC_GRAMMAR_ID",
    "CompilationError",
    "CompiledPolicy",
    "PolicySource",
    "canonical_json_digest",
    "compile_policy",
    "digest_bytes",
    "ground_marking",
    "load_policy_source",
    "parse_source_document",
]

#: The synthetic notation this front end reads. Bounded to this demonstration.
SYNTHETIC_GRAMMAR_ID: Final = "OIC-DEMO-SYNTHETIC-POLICY-GRAMMAR-v0.1"

COMPILER_VERSION: Final = "oic-demo-compiler-0.1.0"
CONTROL_ENVELOPE_SCHEMA_VERSION: Final = "OIC-CONTROL-ENVELOPE-DRAFT-v0.1"
INSTITUTIONAL_IR_SCHEMA_VERSION: Final = "OIC-INSTITUTIONAL-IR-DRAFT-v0.1"
RUNTIME_BINDING_SCHEMA_VERSION: Final = "OIC-DEMO-RUNTIME-BINDING-v0.1"

ADMITTED: Final = "admit"

#: The two logical grounds of the bounded example, in their institutional
#: spelling. Authority and delegation are deliberately absent: they are OAM-plane
#: facts and must never become propositions handed to a logic kernel.
GROUND_IDS: Final[tuple[str, ...]] = (
    "g:amount_within_limit",
    "g:eligibility_evidence_present",
)

#: The kernel's tokenizer accepts ``[A-Za-z0-9_]`` only, so the institutional
#: ground identifiers are carried across the boundary under these atom names.
#: The mapping is declared, not incidental: a warrant records both spellings.
GROUND_ATOMS: Final[dict[str, str]] = {
    "g:amount_within_limit": "g_amount_within_limit",
    "g:eligibility_evidence_present": "g_eligibility_evidence_present",
}

#: The line keywords the bounded grammar recognises. Anything else is refused.
_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "POLICY",
        "TITLE",
        "EFFECTIVE",
        "SUPERSEDES",
        "ACTOR",
        "ACTION",
        "CONDITION",
        "DELEGATION",
        "GUIDANCE",
    }
)

#: Condition names the grammar knows how to turn into an executable condition.
#: A condition outside this set parses, extracts, and stays inexecutable.
_EXECUTABLE_CONDITIONS: Final[frozenset[str]] = frozenset(
    {"amount_within_limit", "eligibility_evidence_present"}
)


class CompilationError(OICError):
    """The front end refused to compile rather than guess at meaning."""


# ---------------------------------------------------------------------------
# Digests
# ---------------------------------------------------------------------------


def digest_bytes(payload: bytes) -> str:
    """Canonical ``sha256:<hex>`` over raw bytes."""
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def canonical_json_digest(value: object) -> str:
    """Canonical ``sha256:<hex>`` over a canonically serialized JSON value.

    Sorted keys, no ASCII escaping, compact separators — the same serialization
    discipline the adjudicated L0 modules use, so digests taken here and there
    are comparable by construction rather than by coincidence.
    """
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return digest_bytes(payload.encode("utf-8"))


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicySource:
    """One synthetic policy source, as bytes plus its declared identity."""

    source_id: str
    payload: bytes
    original_filename: str

    @property
    def content_hash(self) -> str:
        """The digest of the exact bytes, which every anchor traces back to."""
        return digest_bytes(self.payload)


def load_policy_source(path: Path, *, source_id: str) -> PolicySource:
    """Read a synthetic policy source file without interpreting it."""
    return PolicySource(source_id=source_id, payload=path.read_bytes(), original_filename=path.name)


def _parse_line(line: str) -> tuple[str, list[str]]:
    parts = line.split()
    keyword = parts[0]
    if keyword not in _KEYWORDS:
        raise CompilationError(
            f"line keyword {keyword!r} is outside the bounded grammar {SYNTHETIC_GRAMMAR_ID}"
        )
    return keyword, parts[1:]


def parse_source_document(source: PolicySource, *, ingested_at: str) -> dict[str, Any]:
    """Build a SourceDocument with one SourceNode per significant line.

    The document node comes first and every clause node names it as parent, so
    the tree is a tree rather than a flat list that happens to be ordered.
    """
    text = source.payload.decode("utf-8")
    lines = [line.rstrip() for line in text.splitlines()]
    significant = [(number, line) for number, line in enumerate(lines, start=1) if line.strip()]
    if not significant:
        raise CompilationError("synthetic source carries no significant lines")

    document_node_id = f"{source.source_id}#document"
    nodes: list[dict[str, Any]] = [
        {
            "node_id": document_node_id,
            "source_id": source.source_id,
            "parent_id": None,
            "node_type": "document",
            "text": text,
            "page": None,
            "bbox": None,
            "content_hash": source.content_hash,
            "references": [],
        }
    ]
    for number, line in significant:
        keyword, _ = _parse_line(line.strip())
        nodes.append(
            {
                "node_id": f"{source.source_id}#L{number:03d}",
                "source_id": source.source_id,
                "parent_id": document_node_id,
                "node_type": "heading" if keyword in {"POLICY", "TITLE"} else "clause",
                "text": line.strip(),
                "page": None,
                "bbox": None,
                "content_hash": digest_bytes(line.strip().encode("utf-8")),
                "references": [],
            }
        )

    return {
        "source_id": source.source_id,
        "content_hash": source.content_hash,
        "media_type": "text/plain",
        "original_filename": source.original_filename,
        "ingested_at": ingested_at,
        "declared_metadata": {
            "grammar_id": SYNTHETIC_GRAMMAR_ID,
            "synthetic": True,
            "derived_from_real_institutional_source": False,
        },
        "verification_status": "unverified",
        "nodes": nodes,
    }


def _anchor_for(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": f"anchor:{node['node_id']}",
        "source_id": node["source_id"],
        "node_id": node["node_id"],
        "quote": node["text"],
        "page": None,
        "bbox": None,
        "content_hash": node["content_hash"],
    }


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


def _candidate(
    *,
    unit_id: str,
    unit_type: str,
    anchor: dict[str, Any],
    actor: str | None = None,
    action: str | None = None,
    conditions: list[str] | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "unit_type": unit_type,
        "actor": actor,
        "action": action,
        "object": None,
        "conditions": conditions or [],
        "exceptions": [],
        "evidence_requirements": evidence or [],
        # Every candidate starts here. Only an AdmissionRecord moves it.
        "interpretation_state": "extracted",
        "epistemic_state": "uncertain",
        "lifecycle_state": "proposed",
        "confidence": None,
        "alternatives": [],
        "source_anchors": [anchor],
    }


@dataclass(frozen=True, slots=True)
class _Parsed:
    """The scalar facts the grammar carries, separated from the candidates."""

    policy_family: str
    version: str
    title: str
    effective_from: str
    supersedes: str | None
    actor: str
    action: str
    delegation_id: str
    amount_max: int
    evidence_id: str


def _extract(
    document: dict[str, Any],
) -> tuple[_Parsed, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Walk the parsed nodes once, producing scalars and candidates together."""
    scalars: dict[str, Any] = {"supersedes": None}
    candidates: list[dict[str, Any]] = []
    anchors_by_unit: dict[str, dict[str, Any]] = {}
    source_id = document["source_id"]

    for node in document["nodes"]:
        if node["node_type"] == "document":
            continue
        keyword, arguments = _parse_line(node["text"])
        anchor = _anchor_for(node)

        if keyword == "POLICY":
            scalars["policy_family"], scalars["version"] = arguments[0], arguments[1]
        elif keyword == "TITLE":
            scalars["title"] = " ".join(arguments)
        elif keyword == "EFFECTIVE":
            scalars["effective_from"] = f"{arguments[0]}T00:00:00Z"
        elif keyword == "SUPERSEDES":
            scalars["supersedes"] = arguments[0]
        elif keyword == "ACTOR":
            scalars["actor"] = arguments[0]
        elif keyword == "ACTION":
            scalars["action"] = arguments[0]
            unit_id = f"{source_id}#unit/mandate"
            candidates.append(
                _candidate(
                    unit_id=unit_id,
                    unit_type="power",
                    anchor=anchor,
                    actor=str(scalars.get("actor")),
                    action=arguments[0],
                )
            )
            anchors_by_unit[unit_id] = anchor
        elif keyword == "CONDITION":
            name = arguments[0]
            unit_id = f"{source_id}#unit/condition/{name}"
            if name == "amount_within_limit":
                scalars["amount_max"] = int(arguments[2])
                candidate = _candidate(
                    unit_id=unit_id, unit_type="condition", anchor=anchor, conditions=[name]
                )
            elif name == "eligibility_evidence_present":
                scalars["evidence_id"] = arguments[2]
                candidate = _candidate(
                    unit_id=unit_id,
                    unit_type="evidence_duty",
                    anchor=anchor,
                    conditions=[name],
                    evidence=[arguments[2]],
                )
            else:
                # Parses, extracts, and stays inexecutable: the grammar knows the
                # shape of the line but the lane has no admitted semantics for it.
                candidate = _candidate(
                    unit_id=unit_id, unit_type="condition", anchor=anchor, conditions=[name]
                )
            candidates.append(candidate)
            anchors_by_unit[unit_id] = anchor
        elif keyword == "DELEGATION":
            scalars["delegation_id"] = arguments[0]
            unit_id = f"{source_id}#unit/delegation"
            candidates.append(_candidate(unit_id=unit_id, unit_type="delegation", anchor=anchor))
            anchors_by_unit[unit_id] = anchor
        elif keyword == "GUIDANCE":
            # Extracted on purpose and never admitted. Its presence in the IR and
            # its absence from the envelope is the demonstration.
            unit_id = f"{source_id}#unit/advisory/{arguments[0]}"
            candidates.append(_candidate(unit_id=unit_id, unit_type="advisory", anchor=anchor))
            anchors_by_unit[unit_id] = anchor

    missing = sorted(
        {
            "policy_family",
            "version",
            "title",
            "effective_from",
            "actor",
            "action",
            "delegation_id",
            "amount_max",
            "evidence_id",
        }
        - set(scalars)
    )
    if missing:
        raise CompilationError(f"synthetic source is missing required declarations: {missing}")

    parsed = _Parsed(
        policy_family=str(scalars["policy_family"]),
        version=str(scalars["version"]),
        title=str(scalars["title"]),
        effective_from=str(scalars["effective_from"]),
        supersedes=(None if scalars["supersedes"] is None else str(scalars["supersedes"])),
        actor=str(scalars["actor"]),
        action=str(scalars["action"]),
        delegation_id=str(scalars["delegation_id"]),
        amount_max=int(scalars["amount_max"]),
        evidence_id=str(scalars["evidence_id"]),
    )
    return parsed, candidates, anchors_by_unit


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompiledPolicy:
    """Everything one synthetic policy version compiles to, in chain order."""

    source: PolicySource
    parsed: _Parsed
    source_document: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    admitted_unit_ids: tuple[str, ...]
    admission_records: tuple[dict[str, Any], ...]
    institutional_ir: dict[str, Any]
    authority_record: dict[str, Any]
    control_envelope: dict[str, Any]
    runtime_binding: dict[str, Any]

    @property
    def control_id(self) -> str:
        """The control this envelope carries, stable across its versions."""
        return str(self.control_envelope["control_id"])

    @property
    def envelope_digest(self) -> str:
        """Canonical digest over the whole envelope; the runtime binds this."""
        return canonical_json_digest(self.control_envelope)

    def condition_ground_ids(self) -> tuple[str, ...]:
        """The ground identifiers the executable conditions correspond to."""
        return tuple(
            str(condition["ground_id"]) for condition in self.control_envelope["conditions"]
        )


def _authority_record(
    parsed: _Parsed, source: PolicySource, anchors: list[dict[str, Any]]
) -> dict[str, Any]:
    """The institutional authority for this policy version.

    Delegation lives here, in the OAM plane, and not in the logical formula. A
    delegation encoded as a ZTL proposition would let a logical result stand in
    for an institutional fact, which is exactly the collapse this lane exists to
    keep visible.
    """
    return {
        "authority_id": f"authority:{parsed.policy_family}/{parsed.version}",
        "source_id": source.source_id,
        "issuer": "SYNTHETIC-GRANT-AUTHORITY-ISSUER",
        "issuer_role": "SYNTHETIC_POLICY_OWNER",
        "source_type": "enterprise_policy",
        "authority_basis": f"delegation {parsed.delegation_id}",
        "jurisdiction": None,
        "organizational_scope": ["SYNTHETIC-GRANT-PROGRAM"],
        "subject_scope": [parsed.action],
        "effective_from": parsed.effective_from,
        "effective_until": None,
        "binding_strength": "binding",
        "status": "active",
        "review_owner": "SYNTHETIC-GRANT-AUTHORITY-ISSUER",
        "source_anchors": anchors,
    }


def _control_envelope(
    parsed: _Parsed,
    source: PolicySource,
    *,
    admitted: list[dict[str, Any]],
    admission_ids: list[str],
    anchors: list[dict[str, Any]],
) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []
    evidence_requirements: list[dict[str, Any]] = []
    for candidate in admitted:
        names = [name for name in candidate["conditions"] if name in _EXECUTABLE_CONDITIONS]
        for name in names:
            condition: dict[str, Any] = {
                "condition_id": f"cond:{name}",
                "ground_id": f"g:{name}",
                "unit_id": candidate["unit_id"],
                "source_anchor_ids": [
                    anchor["anchor_id"] for anchor in candidate["source_anchors"]
                ],
            }
            if name == "amount_within_limit":
                condition["operator"] = "less_than_or_equal"
                condition["field"] = "amount"
                condition["value"] = parsed.amount_max
            else:
                condition["operator"] = "evidence_present"
                condition["field"] = "eligibility_evidence"
                condition["value"] = parsed.evidence_id
                evidence_requirements.append(
                    {
                        "evidence_id": parsed.evidence_id,
                        "unit_id": candidate["unit_id"],
                        "signature_required": True,
                    }
                )
            conditions.append(condition)
    conditions.sort(key=lambda item: str(item["condition_id"]))

    return {
        "envelope_id": f"env:{parsed.policy_family}/{parsed.version}",
        "schema_version": CONTROL_ENVELOPE_SCHEMA_VERSION,
        "semantic_version": f"1.{0 if parsed.version == 'v1' else 1}.0",
        "control_id": f"ctl:{parsed.policy_family.lower()}",
        "actor": {"actor_id": parsed.actor, "unit_id": f"{source.source_id}#unit/mandate"},
        "action": {"action_id": parsed.action, "unit_id": f"{source.source_id}#unit/mandate"},
        "resource": {"resource_class": "SYNTHETIC_GRANT_DISBURSEMENT"},
        # The authority chain is a reference to the institutional plane, not a
        # logical condition the kernel will ever see.
        "authority_chain": [
            f"authority:{parsed.policy_family}/{parsed.version}",
            f"delegation:{parsed.delegation_id}",
        ],
        "conditions": conditions,
        "exceptions": [],
        "evidence_requirements": evidence_requirements,
        "decision_mode": "automatic",
        # UNKNOWN must fail closed operationally without becoming substantive
        # false: `deny` refuses the operation, and says nothing about the truth
        # of the proposition.
        "on_unknown": "deny",
        "effective_from": parsed.effective_from,
        "effective_until": None,
        "revocation_sources": [f"revocation:{parsed.policy_family}"],
        "source_anchors": anchors,
        "admission_ids": admission_ids,
        "compiler_version": COMPILER_VERSION,
        "test_suite_hash": None,
    }


def _runtime_binding(
    envelope: dict[str, Any],
    *,
    source: PolicySource,
    admission_records: list[dict[str, Any]],
    authority_record: dict[str, Any],
    kernel_profile_id: str,
    canonicalization_profile_id: str,
    bound_formula_hash: str,
) -> dict[str, Any]:
    """A runtime projection that binds identities the envelope must not carry.

    The governing OpenControlEnvelope schema is not extended to hold ZTL fields.
    Canonical institutional meaning stays in the InstitutionalIR; this object
    exists so a runtime evaluation can prove *which* versions it ran against.
    """
    return {
        "binding_id": f"binding:{envelope['envelope_id']}",
        "schema_version": RUNTIME_BINDING_SCHEMA_VERSION,
        "envelope_id": envelope["envelope_id"],
        "envelope_hash": canonical_json_digest(envelope),
        "control_id": envelope["control_id"],
        "control_version": envelope["semantic_version"],
        "source_version_set": [source.content_hash],
        "source_version_set_hash": canonical_json_digest([source.content_hash]),
        "admission_version": canonical_json_digest(
            [record["admission_id"] for record in admission_records]
        ),
        "authority_version": authority_record["authority_id"],
        "kernel_profile_id": kernel_profile_id,
        "canonicalization_profile_id": canonicalization_profile_id,
        "bound_formula_hash": bound_formula_hash,
        "warrant_requirement": {
            "mode": "required",
            "kernel_profile_id": kernel_profile_id,
            "minimum_warranty_grade": "hereditary",
            "on_insufficient_grade": "escalate",
            "unverified_ground_policy": "forbid",
        },
        "projection_note": (
            "Runtime projection only. Canonical institutional meaning remains in the "
            "InstitutionalIR; this object binds versions so an evaluation is replayable."
        ),
    }


def compile_policy(
    source: PolicySource,
    *,
    admission_records: list[dict[str, Any]],
    ingested_at: str,
    kernel_profile_id: str,
    canonicalization_profile_id: str,
    bound_formula_hash: str,
) -> CompiledPolicy:
    """Compile one synthetic policy version through the full chain.

    ``admission_records`` are owner-authored and are read, never generated: this
    function has no route by which an extracted candidate can admit itself.
    """
    document = parse_source_document(source, ingested_at=ingested_at)
    parsed, candidates, _ = _extract(document)

    for record in admission_records:
        if source.content_hash not in record["source_hashes"]:
            raise CompilationError(
                f"admission {record['admission_id']} does not name this source's bytes"
            )

    admitted_ids = [
        str(record["subject_id"])
        for record in admission_records
        if record["disposition"] == ADMITTED
    ]
    known = {candidate["unit_id"] for candidate in candidates}
    unknown = sorted(set(admitted_ids) - known)
    if unknown:
        raise CompilationError(f"admission names units this source did not produce: {unknown}")

    admitted = [candidate for candidate in candidates if candidate["unit_id"] in set(admitted_ids)]
    resolved: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate["unit_id"] in set(admitted_ids):
            resolved.append(
                {**candidate, "interpretation_state": "admitted", "lifecycle_state": "active"}
            )
        else:
            resolved.append(candidate)

    anchors = [candidate["source_anchors"][0] for candidate in admitted]
    admission_ids = [str(record["admission_id"]) for record in admission_records]

    institutional_ir = {
        "ir_id": f"ir:{parsed.policy_family}/{parsed.version}",
        "schema_version": INSTITUTIONAL_IR_SCHEMA_VERSION,
        # Every candidate is carried, admitted or not. An IR that dropped the
        # unadmitted ones would make "extracted but not executable" invisible.
        "nodes": resolved,
        "edges": [
            {
                "edge_id": f"edge:{record['admission_id']}",
                "from": str(record["admission_id"]),
                "to": str(record["subject_id"]),
                "type": "admits",
            }
            for record in admission_records
        ],
        "admission_records": admission_records,
        "source_hashes": [source.content_hash],
    }

    authority_record = _authority_record(parsed, source, anchors)
    envelope = _control_envelope(
        parsed,
        source,
        admitted=[
            candidate for candidate in resolved if candidate["interpretation_state"] == "admitted"
        ],
        admission_ids=admission_ids,
        anchors=anchors,
    )
    binding = _runtime_binding(
        envelope,
        source=source,
        admission_records=admission_records,
        authority_record=authority_record,
        kernel_profile_id=kernel_profile_id,
        canonicalization_profile_id=canonicalization_profile_id,
        bound_formula_hash=bound_formula_hash,
    )

    return CompiledPolicy(
        source=source,
        parsed=parsed,
        source_document=document,
        candidates=tuple(resolved),
        admitted_unit_ids=tuple(sorted(admitted_ids)),
        admission_records=tuple(admission_records),
        institutional_ir=institutional_ir,
        authority_record=authority_record,
        control_envelope=envelope,
        runtime_binding=binding,
    )


class EvidenceState(StrEnum):
    """What was actually observed about a required piece of evidence.

    A boolean cannot carry this. ``False`` conflates "we looked and it is not
    signed" with "we never looked", and those two must not produce the same
    kernel mark: the first is a finding, the second is an absence. The kernel
    alphabet already distinguishes them, so the compiler must not throw the
    distinction away before it gets there.
    """

    SIGNED = "SIGNED"
    UNSIGNED = "UNSIGNED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"
    NOT_OBSERVED = "NOT_OBSERVED"


#: The only mapping from an observed evidence state to a kernel mark.
#: ``None`` means *supply no mark at all*: the kernel then defaults the atom to
#: ``Z``, and the formula comes back OPEN rather than REFUTED.
EVIDENCE_STATE_TO_MARK: Final[dict[EvidenceState, str | None]] = {
    EvidenceState.SIGNED: "T",
    EvidenceState.UNSIGNED: "F",
    EvidenceState.INVALID: "F",
    EvidenceState.UNKNOWN: None,
    EvidenceState.NOT_OBSERVED: None,
}


def ground_marking(
    compiled: CompiledPolicy,
    *,
    amount: int,
    evidence_state: EvidenceState = EvidenceState.NOT_OBSERVED,
) -> dict[str, str]:
    """Evaluate the admitted conditions into a kernel marking.

    Only admitted conditions produce a mark, and only an *observed* evidence
    state produces one for the evidence ground. An unknown or unobserved
    observation contributes no mark, so the atom stays ``Z``: unverified, not
    false. Never falsify a ground because Python happened to hold ``False``.
    """
    marks: dict[str, str] = {}
    for condition in compiled.control_envelope["conditions"]:
        ground_id = str(condition["ground_id"])
        atom = GROUND_ATOMS[ground_id]
        if condition["operator"] == "less_than_or_equal":
            marks[atom] = "T" if amount <= int(condition["value"]) else "F"
        else:
            mark = EVIDENCE_STATE_TO_MARK[evidence_state]
            if mark is not None:
                marks[atom] = mark
    return marks
