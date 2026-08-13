"""Bounded CDC vertical-slice transition contract.

This module implements only ``VEIP-CDC-SLICE-EVALUATION-CONTRACT-v0.1``.  It
does not establish CDC authority, production VEIP conformance, officiality,
reliance, or runtime currentness.  It deliberately consumes an already-created
evaluation and warrant; it does not interpret sources or create institutional
meaning.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

MISSION_ID: Final = "CDC-TEST-MISSION-001"
TEST_SCOPE: Final = "CDC-TEST-MISSION-001/TEST-REVIEWER"
ASSURANCE_MODE: Final = "SYNTHETIC_EVALUATION_ONLY"
CONTRACT_ID: Final = "VEIP-CDC-SLICE-EVALUATION-CONTRACT-v0.1"
PERMITTED_DISPOSITIONS: Final = frozenset(
    {"ACCEPT_CANDIDATE", "QUALIFY", "DISMISS", "REQUEST_EVIDENCE", "ESCALATE", "DEFER"}
)


def canonical_bytes(value: object) -> bytes:
    """Return the slice's deterministic, UTF-8 JSON representation."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: object) -> str:
    """Return a canonical SHA-256 digest for a JSON value."""
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Deterministic evaluation-profile decision; never an institutional finding."""

    decision: str
    reason_code: str
    epistemic_state: str


def _decision(decision: str, reason_code: str, proposal: Mapping[str, Any]) -> GateDecision:
    """Preserve CANNOT/unresolved independently of an operational decision."""
    if proposal.get("cannot_condition") is True:
        epistemic_state = "UNRESOLVED_CANNOT"
    elif proposal.get("requested_disposition") == "REQUEST_EVIDENCE":
        epistemic_state = "UNRESOLVED"
    else:
        epistemic_state = "NOT_ADJUDICATED"
    return GateDecision(decision, reason_code, epistemic_state)


def _exists(registry: Mapping[str, object], category: str, identifier: object) -> bool:
    values = registry.get(category)
    return isinstance(values, Mapping) and isinstance(identifier, str) and identifier in values


def refuse_stale_candidate_proposal(
    proposal: Mapping[str, Any], registry: Mapping[str, object]
) -> GateDecision | None:
    """Refuse a proposal addressing a superseded or corrected candidate.

    The rule lives here so the gate and the correction-successor observation
    share one definition. Returning ``None`` means "not stale"; the caller
    decides what happens next, and this function emits nothing.
    """
    stale_value = registry.get("stale_candidate_ids", ())
    stale = stale_value if isinstance(stale_value, list | tuple | set | frozenset) else ()
    if proposal.get("candidate_id") in stale:
        return _decision("DENY", "CANDIDATE_SUPERSEDED_OR_CORRECTED", proposal)
    return None


def evaluate_test_transition(
    proposal: Mapping[str, Any], registry: Mapping[str, object]
) -> GateDecision:
    """Evaluate the owner-attested TEST transition contract, failing closed.

    ``registry`` is the immutable run snapshot.  Its mappings contain the exact
    objects addressed by the proposal.  Unknown semantic conditions escalate;
    objective binding or authority failures deny.
    """
    if proposal.get("mission_id") != MISSION_ID:
        return _decision("DENY", "WRONG_MISSION", proposal)
    if proposal.get("assurance_mode") != ASSURANCE_MODE:
        return _decision("DENY", "INVALID_ASSURANCE_MODE", proposal)
    if proposal.get("authority_scope_ref") != TEST_SCOPE:
        return _decision("DENY", "UNAUTHORIZED_REVIEWER_SCOPE", proposal)
    if proposal.get("requested_disposition") not in PERMITTED_DISPOSITIONS:
        return _decision("DENY", "DISPOSITION_NOT_PERMITTED", proposal)

    bindings = (
        ("candidates", "candidate_id"),
        ("ebawus", "ebawu_id"),
        ("controls", "OIC_control_id"),
        ("admissions", "admission_record_ref"),
        ("evidence", "evidence_bundle_ref"),
        ("evaluations", "deterministic_execution_result_ref"),
        ("reviewers", "reviewer_id"),
    )
    for category, field in bindings:
        if not _exists(registry, category, proposal.get(field)):
            return _decision(
                "ESCALATE", f"REQUIRED_{category.upper()}_BINDING_UNRESOLVED", proposal
            )

    ztl_ref = proposal.get("ZTL_warrant_ref")
    ztl_digest = proposal.get("ZTL_warrant_digest")
    fallback_ref = proposal.get("fallback_warrant_ref")
    fallback_digest = proposal.get("fallback_warrant_digest")
    has_ztl = isinstance(ztl_ref, str) and isinstance(ztl_digest, str)
    has_fallback = isinstance(fallback_ref, str) and isinstance(fallback_digest, str)
    if has_ztl and has_fallback:
        return _decision("DENY", "WARRANT_ARTIFACT_CLASS_COLLISION", proposal)
    if not has_ztl and not has_fallback:
        return _decision("ESCALATE", "REQUIRED_WARRANT_CLASS_UNRESOLVED", proposal)
    if has_fallback and (ztl_ref is not None or ztl_digest is not None):
        return _decision("DENY", "FALLBACK_MASQUERADES_AS_ZTL", proposal)
    warrant_category = "warrants" if has_ztl else "fallback_warrants"
    warrant_ref = ztl_ref if has_ztl else fallback_ref
    warrant_digest = ztl_digest if has_ztl else fallback_digest
    if not _exists(registry, warrant_category, warrant_ref):
        return _decision("ESCALATE", "REQUIRED_WARRANT_BINDING_UNRESOLVED", proposal)

    digest_bindings = (
        ("candidates", "candidate_id", "candidate_digest"),
        ("controls", "OIC_control_id", "OIC_control_digest"),
        ("evidence", "evidence_bundle_ref", "evidence_bundle_digest"),
    )
    for category, id_field, digest_field in digest_bindings:
        objects = registry[category]
        if not isinstance(objects, Mapping):
            return _decision(
                "ESCALATE", f"REQUIRED_{category.upper()}_BINDING_UNRESOLVED", proposal
            )
        if digest(objects[proposal[id_field]]) != proposal.get(digest_field):
            return _decision("DENY", f"{digest_field.upper()}_MISMATCH", proposal)
    warrants = registry[warrant_category]
    if not isinstance(warrants, Mapping):
        return _decision("ESCALATE", "REQUIRED_WARRANT_BINDING_UNRESOLVED", proposal)
    if digest(warrants[warrant_ref]) != warrant_digest:
        reason = "ZTL_WARRANT_DIGEST_MISMATCH" if has_ztl else "FALLBACK_WARRANT_DIGEST_MISMATCH"
        return _decision("DENY", reason, proposal)

    states = registry.get("states")
    if not isinstance(states, Mapping) or states.get(proposal.get("ebawu_id")) != proposal.get(
        "prior_institutional_state"
    ):
        return _decision("DENY", "PRIOR_STATE_MISMATCH", proposal)
    stale_refusal = refuse_stale_candidate_proposal(proposal, registry)
    if stale_refusal is not None:
        return stale_refusal
    if proposal.get("required_condition_state") == "UNKNOWN":
        return GateDecision(
            "ESCALATE", "REQUIRED_TRANSITION_CONDITION_UNKNOWN", "UNRESOLVED_CANNOT"
        )
    if proposal.get("cannot_condition") is True:
        return GateDecision("ESCALATE", "CANNOT_REQUIRES_GOVERNED_RESOLUTION", "UNRESOLVED_CANNOT")
    return _decision("ALLOW", "SLICE_CONTRACT_SATISFIED", proposal)


def emit_transition_event(
    proposal: Mapping[str, Any], decision: GateDecision, *, event_metadata: Mapping[str, Any]
) -> dict[str, Any]:
    """Emit an immutable event value only after ALLOW.

    The caller persists returned bytes once.  No event shape is emitted for DENY or
    ESCALATE, preventing fabricated completion.
    """
    if decision.decision != "ALLOW":
        raise ValueError("a TEST transition event may be emitted only after ALLOW")
    required_metadata = {
        "event_id",
        "aggregate_version",
        "occurred_at",
        "recorded_at",
        "producer",
        "producer_version",
        "run_id",
        "trace_id",
    }
    missing = sorted(required_metadata - event_metadata.keys())
    if missing:
        raise ValueError(f"missing event metadata: {missing}")
    return {
        **event_metadata,
        "event_type": "APPLY_TEST_DISPOSITION",
        "schema_version": "VEIP-CDC-SLICE-EVENT-v0.1",
        "mission_id": proposal["mission_id"],
        "aggregate_id": proposal["ebawu_id"],
        "parent_event_id": proposal.get("parent_event_id"),
        "input_artifact_digests": sorted(
            [
                proposal["candidate_digest"],
                proposal["evidence_bundle_digest"],
                proposal["OIC_control_digest"],
                proposal.get("ZTL_warrant_digest") or proposal["fallback_warrant_digest"],
            ]
        ),
        "output_artifact_digests": [],
        "prior_state": proposal["prior_institutional_state"],
        "new_state": proposal["requested_new_institutional_state"],
        "reason_code": decision.reason_code,
        "epistemic_state": decision.epistemic_state,
        "declared_actor": proposal["reviewer_id"],
        "declared_role": proposal["reviewer_role_assertion"],
        "authority_scope_ref": proposal["authority_scope_ref"],
        "assurance_mode": proposal["assurance_mode"],
        "candidate_digest": proposal["candidate_digest"],
        "evidence_bundle_digest": proposal["evidence_bundle_digest"],
        "OIC_control_digest": proposal["OIC_control_digest"],
        "ZTL_warrant_digest": proposal.get("ZTL_warrant_digest"),
        "fallback_warrant_digest": proposal.get("fallback_warrant_digest"),
        "disposition": proposal["requested_disposition"],
        "correction_ref": proposal.get("correction_ref"),
        "downstream_eligibility_refs": [],
        "handoff_refs": [],
        "reliance_impact_refs": [],
    }


def make_successor(predecessor: Mapping[str, Any], correction: Mapping[str, Any]) -> dict[str, Any]:
    """Create a successor without changing the predecessor value."""
    required = {
        "new_ebawu_or_successor_id",
        "new_candidate_digest",
        "correction_reason",
        "changed_fact_or_control_refs",
        "new_state",
        "correction_event_id",
    }
    missing = sorted(required - correction.keys())
    if missing:
        raise ValueError(f"missing correction fields: {missing}")
    predecessor_id = predecessor.get("ebawu_id") or predecessor.get("successor_id")
    if not isinstance(predecessor_id, str):
        raise ValueError("predecessor has no stable identifier")
    return {
        "successor_id": correction["new_ebawu_or_successor_id"],
        "new_candidate_digest": correction["new_candidate_digest"],
        "supersedes": predecessor_id,
        "superseded_by": None,
        "correction_reason": correction["correction_reason"],
        "changed_fact_or_control_refs": correction["changed_fact_or_control_refs"],
        "prior_state": predecessor["state"],
        "new_state": correction["new_state"],
        "affected_output_refs": correction.get("affected_output_refs", []),
        "reliance_impact_refs": [],
        "correction_event_id": correction["correction_event_id"],
        "production_reliance_semantics": "OUT_OF_SCOPE",
    }


def manifest_entries(root: Path) -> list[dict[str, object]]:
    """Account for every file except the self-excluded ``MANIFEST.sha256``."""
    entries: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "MANIFEST.sha256":
            continue
        payload = path.read_bytes()
        entries.append(
            {"path": relative, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        )
    return entries
