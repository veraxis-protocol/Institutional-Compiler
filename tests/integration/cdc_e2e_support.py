"""Shared non-result-bearing scaffolding for CDC-END-TO-END-MISSION-001 tests.

Nothing here runs the real frozen evaluator or warrant contract, creates a real
disposition, or adjudicates against the semantic oracle. The evaluator and
warrant builder are deliberately trivial stubs so the *interlocks* can be tested
without supplying the governed components, which are not this module's to write.

The clearance built here is a structural stand-in: its runtime identities match
an equally synthetic ``RuntimeIdentity`` so the comparison is observed-against-
observed. The four externally governed digests are the real frozen values, so a
wrong one still refuses.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from oic.cdc_e2e_mission import (
    ADJUDICATION_PROTOCOL_SHA256,
    FROZEN_MISSION_PACKAGE_SHA256,
    HUMAN_ACTION_PLAN_SHA256,
    ORACLE_SHA256,
    ExecutionClearance,
    MissionProjection,
    RuntimeIdentity,
    Stage1Observation,
)

PACKAGE_RELPATH = "veraxis/cdc-e2e-mission-001/input-v0.1"

# Inside the frozen standing's validity window (2026-08-10 .. 2026-08-11).
OBSERVED_AT = "2026-08-10T12:00:00Z"

STUB_RUNTIME = RuntimeIdentity(
    implementation_commit="STUB-IMPLEMENTATION-COMMIT",
    implementation_tree="STUB-IMPLEMENTATION-TREE",
    environment_manifest_sha256="STUB-ENVIRONMENT-MANIFEST",
)

CORRECTION_STIMULUS: Mapping[str, Any] = {
    "correction_stimulus_id": "HA-CORRECTION-001",
    "target_id": "HA-P001-C-TENDER-01",
    "predecessor_ebawu_ref": "EBAWU-P-001-C-TENDER-01",
    "precondition": "issue only after an eligible completed transition on this chain",
}


def stub_evaluator(
    member: Mapping[str, Any], control: Mapping[str, Any], evidence: Mapping[str, Any]
) -> Mapping[str, Any]:
    """A deliberately trivial stand-in; it reaches no institutional conclusion."""
    del control, evidence
    return {"evaluation_id": f"STUB-EVAL-{member['control_ref']}", "verdict": "STUB_NOT_A_VERDICT"}


def stub_warrant(
    evaluation: Mapping[str, Any], control: Mapping[str, Any]
) -> tuple[str, Mapping[str, Any]]:
    """A stand-in warrant builder; produces no ZTL claim."""
    del control
    return "ZTL_WARRANT", {"warrant_id": f"STUB-W-{evaluation['evaluation_id']}"}


def exact_clearance(runtime: RuntimeIdentity = STUB_RUNTIME) -> ExecutionClearance:
    """A clearance whose runtime fields match ``runtime`` and whose digests are real."""
    return ExecutionClearance(
        owner_execution_authorization="OWNER-EXECUTION-AUTHORIZATION-STRUCTURAL-TEST",
        implementation_commit=runtime.implementation_commit,
        implementation_tree=runtime.implementation_tree,
        environment_manifest_sha256=runtime.environment_manifest_sha256,
        mission_package_sha256=FROZEN_MISSION_PACKAGE_SHA256,
        oracle_sha256=ORACLE_SHA256,
        adjudication_protocol_sha256=ADJUDICATION_PROTOCOL_SHA256,
        action_plan_sha256=HUMAN_ACTION_PLAN_SHA256,
    )


def disposition_for(
    stage_1: Stage1Observation,
    projection: MissionProjection,
    chain_id: str,
    *,
    action: str = "ACCEPT_CANDIDATE",
) -> dict[str, Any]:
    """Build a disposition that binds the artifacts Stage 1 actually formed."""
    artifact = stage_1.artifacts()[chain_id]
    authority = projection.authority
    return {
        "mission_id": stage_1.mission_id,
        "procedure_id": artifact.procedure_id,
        "control_id": artifact.control_id,
        "chain_id": chain_id,
        "ebawu_id": artifact.ebawu_id,
        "candidate_digest": artifact.candidate_digest,
        "warrant_ref": artifact.warrant_ref,
        "warrant_digest": artifact.warrant_digest,
        "reviewer_id": authority["identity"]["reviewer_id"],
        "reviewer_role": authority["role"]["role_id"],
        "authority_scope_ref": authority["authority_scope_ref"],
        "action": action,
        "observed_at": OBSERVED_AT,
        "reason": "structural test stimulus; not a real reviewer judgement",
        "action_plan_sha256": HUMAN_ACTION_PLAN_SHA256,
        "stage_1_observation_digest": stage_1.digest(),
    }


def run_metadata() -> dict[str, Any]:
    """Immutable run/event metadata for a structural Stage-2 run."""
    return {
        "run_id": "CDC-E2E-RUN-STRUCTURAL-001",
        "trace_id": "CDC-E2E-TRACE-STRUCTURAL-001",
        "producer": "oic.cdc_e2e_mission",
        "producer_version": "v0.2",
        "occurred_at": OBSERVED_AT,
        "recorded_at": OBSERVED_AT,
    }


def correction_object() -> dict[str, Any]:
    """A correction whose predecessor digest is bound at runtime, never precomputed."""
    return {
        "correction_stimulus_id": "HA-CORRECTION-001",
        "new_ebawu_or_successor_id": "EBAWU-P-001-C-TENDER-01-S2",
        "new_candidate_digest": "1" * 64,
        "correction_reason": "structural correction stimulus",
        "changed_fact_or_control_refs": ["EVB-P-001-C-TENDER-01"],
        "new_state": "QUALIFIED",
        "correction_event_id": "CORR-EVT-STRUCTURAL-001",
    }
