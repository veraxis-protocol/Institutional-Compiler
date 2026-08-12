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

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from oic.cdc_e2e_mission import (
    ADJUDICATION_PROTOCOL_SHA256,
    FROZEN_MISSION_INPUT_RELPATH,
    FROZEN_MISSION_PACKAGE_SHA256,
    HUMAN_ACTION_PLAN_RELPATH,
    HUMAN_ACTION_PLAN_SHA256,
    NOT_ADOPTED_MISSION_INPUT_RELPATH,
    ORACLE_SHA256,
    OWNER_ISSUED_MISSION_INPUT_RELPATH,
    OWNER_PREEXECUTION_INTERPRETATION_RELPATH,
    OWNER_PREEXECUTION_INTERPRETATION_SHA256,
    PREDECESSOR_MISSION_INPUT_RELPATH,
    STAGE_1_COMPONENT_PROFILE_RELPATH,
    STAGE_1_COMPONENT_PROFILE_SHA256,
    EvaluationFunction,
    ExecutionClearance,
    FrozenActionPlan,
    FrozenMissionInput,
    MissionProjection,
    RuntimeIdentity,
    Stage1Observation,
    WarrantFunction,
    _bind_disposition_with_injected_clock,
    _form_stage_1,
)

PACKAGE_RELPATH = FROZEN_MISSION_INPUT_RELPATH
PREDECESSOR_PACKAGE_RELPATH = PREDECESSOR_MISSION_INPUT_RELPATH
NOT_ADOPTED_PACKAGE_RELPATH = NOT_ADOPTED_MISSION_INPUT_RELPATH
OWNER_ISSUED_PACKAGE_RELPATH = OWNER_ISSUED_MISSION_INPUT_RELPATH

# Inside the v0.3 standing's validity window (2026-08-11T20:30:00Z .. 2026-08-18).
OBSERVED_AT = "2026-08-12T00:00:00Z"

# Inside the *expired* v0.1 window. Legitimate only as a structural timestamp in
# a test; it must never stand as the observed time of a real later disposition.
PREDECESSOR_STRUCTURAL_OBSERVED_AT = "2026-08-10T12:00:00Z"

STUB_RUNTIME = RuntimeIdentity(
    implementation_commit="STUB-IMPLEMENTATION-COMMIT",
    implementation_tree="STUB-IMPLEMENTATION-TREE",
    environment_manifest_sha256="STUB-ENVIRONMENT-MANIFEST",
)

ACTION_PLAN_RELPATH = HUMAN_ACTION_PLAN_RELPATH
COMPONENT_PROFILE_RELPATH = STAGE_1_COMPONENT_PROFILE_RELPATH
OWNER_INTERPRETATION_RELPATH = OWNER_PREEXECUTION_INTERPRETATION_RELPATH


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
        owner_preexecution_interpretation_sha256=OWNER_PREEXECUTION_INTERPRETATION_SHA256,
        stage_1_component_profile_sha256=STAGE_1_COMPONENT_PROFILE_SHA256,
    )


def disposition_for(
    stage_1: Stage1Observation,
    projection: MissionProjection,
    chain_id: str,
    plan: FrozenActionPlan,
    *,
    action: str | None = None,
) -> dict[str, Any]:
    """Build the disposition the frozen plan preregisters for this chain.

    ``action`` defaults to the preregistered class recovered from the plan bytes.
    A test that wants a non-preregistered stimulus passes one explicitly.
    """
    artifact = stage_1.artifacts()[chain_id]
    if action is None:
        action = plan.target_for(
            artifact.procedure_id, artifact.control_id
        ).preregistered_action_class
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
        "affected_output_refs": [],
    }


def form_stage_1_for_tests(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    *,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
    authorization: str = "TEST_SUPPORT_WRAPPER_NOT_RESULT_BEARING",
) -> Stage1Observation:
    """Test-support wrapper over the private candidate-forming helper.

    This lives under ``tests/`` deliberately. The production module exposes no
    public callable that can form candidates without owner clearance; a unit test
    that needs an unauthorized observation reaches the private helper from here,
    where it cannot be mistaken for a runtime entrypoint.
    """
    return _form_stage_1(
        projection,
        frozen,
        evaluator=evaluator,
        warrant_builder=warrant_builder,
        authorization=authorization,
    )


def bindings_for(
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> dict[str, Any]:
    """Stage-2 bindings computed from the artifacts and the verified plan."""
    from oic.cdc_e2e_mission import sha256

    return {
        "stage_1_observation_digest": stage_1.digest(),
        "human_disposition_artifact_digests": sorted(
            sha256(dict(record)) for record in dispositions.values()
        ),
        "correction_stimulus_digest": plan.correction.digest(),
        "action_plan_sha256": plan.sha256_hex,
        "action_plan_provenance_token": plan.provenance_token,
    }


def bind_disposition_at(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    projection: MissionProjection,
    action_plan: FrozenActionPlan,
    clock: str = OBSERVED_AT,
) -> dict[str, Any]:
    """Test-support binder over the private injected-clock helper.

    The public path takes its clock from the runtime and has no clock parameter.
    Structural tests need a deterministic instant inside the frozen window, so
    they reach the private helper from here. Every artifact it produces is
    stamped TEST_INJECTED_CLOCK_NOT_RESULT_BEARING.
    """
    return _bind_disposition_with_injected_clock(
        stage_1, disposition, projection=projection, action_plan=action_plan, clock=clock
    )


def synthetic_authorization(
    tmp_path: Path,
    *,
    runtime: RuntimeIdentity = STUB_RUNTIME,
    package_sha256: str = FROZEN_MISSION_PACKAGE_SHA256,
    overrides: Mapping[str, Any] | None = None,
    binding_overrides: Mapping[str, Any] | None = None,
    raw: bytes | None = None,
    name: str = "SYNTHETIC-TEST-AUTHORIZATION.json",
) -> Path:
    """Write a synthetic, valid-shaped Stage-1 authorization for tests only.

    This is a test fixture. It is valid-shaped so the gate can be observed
    *opening*, which is the only way to test what happens after it opens, but it
    binds STUB_RUNTIME identities that no real run has, so it can only ever open
    a test gate. No real owner authorization exists and none is created here.
    """
    document: dict[str, Any] = {
        "record_class": "OWNER_STAGE_1_EXECUTION_AUTHORIZATION",
        "authorization_id": "SYNTHETIC-TEST-AUTHORIZATION-001",
        "synthetic_test_fixture": True,
        "mission_id": "CDC-TEST-MISSION-001",
        "owner_authorized": True,
        "authorized_stage": "STAGE_1_ONLY",
        "authorization_scope": "ONE_RESULT_BEARING_STAGE_1_EXECUTION",
        "single_use": True,
        "automatic_retry_authorized": False,
        "stage_2_authorized": False,
        "result_bearing": True,
        "bindings": {
            "implementation_commit": runtime.implementation_commit,
            "implementation_tree": runtime.implementation_tree,
            "environment_manifest_sha256": runtime.environment_manifest_sha256,
            "mission_package_sha256": package_sha256,
            "stage_1_component_profile_sha256": STAGE_1_COMPONENT_PROFILE_SHA256,
            "oracle_sha256": ORACLE_SHA256,
            "adjudication_protocol_sha256": ADJUDICATION_PROTOCOL_SHA256,
            "action_plan_sha256": HUMAN_ACTION_PLAN_SHA256,
            "owner_preexecution_interpretation_sha256": (OWNER_PREEXECUTION_INTERPRETATION_SHA256),
            "owner_semantic_preimplementation_freeze_sha256": (
                "fa8f18cb1d890b41fd078b92238200e58cb0e7f1ff65628f2390df520e20ab2a"
            ),
            "owner_stage_1_seam_clarification_sha256": (
                "a4a87ec5698416eaa9af970392070a25181df263537524e8b0fc8a91d86fec60"
            ),
        },
    }
    if overrides:
        document.update(overrides)
    if binding_overrides:
        document["bindings"] = {**document["bindings"], **binding_overrides}
    path = tmp_path / name
    if raw is not None:
        path.write_bytes(raw)
    else:
        path.write_bytes((json.dumps(document, indent=2, sort_keys=True) + "\n").encode())
    return path


def clearance_for_authorization(
    authorization_path: Path, runtime: RuntimeIdentity = STUB_RUNTIME
) -> ExecutionClearance:
    """A clearance whose owner reference names the artifact's exact digest."""
    import hashlib

    digest = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
    return ExecutionClearance(
        **{
            **exact_clearance(runtime).as_mapping(),
            "owner_execution_authorization": f"sha256:{digest}",
        }
    )
