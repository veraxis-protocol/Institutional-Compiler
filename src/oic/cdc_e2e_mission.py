"""Bounded, fail-closed integration substrate for CDC-END-TO-END-MISSION-001.

The module consumes already-admitted OIC controls.  It contains no source-text
parser and creates no institutional meaning.  Its result-bearing entry point is
unreachable unless six externally governed bindings match the observed runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from oic.cdc_slice import (
    GateDecision,
    digest,
    emit_transition_event,
    evaluate_test_transition,
    make_successor,
)

MISSION_ID: Final = "CDC-TEST-MISSION-001"
ASSURANCE_MODE: Final = "SYNTHETIC_EVALUATION_ONLY"
OFFICIAL_CDC_RECORD_CREATION: Final = "PROHIBITED"
REQUIRED_CLEARANCE_FIELDS: Final = (
    "owner_execution_authorization",
    "implementation_commit",
    "implementation_tree",
    "environment_manifest_sha256",
    "mission_package_sha256",
    "oracle_sha256",
    "adjudication_protocol_sha256",
)
DRAFT_KINDS: Final = (
    "orientation_note",
    "provisional_report",
    "final_report",
    "findings_summary",
    "transmittal_letter",
)


class ResultBearingMissionBlockedError(RuntimeError):
    """The result-bearing boundary was reached without exact clearance."""


class MissionContractError(ValueError):
    """A supplied package violates the bounded integration contract."""


def canonical_bytes(value: object) -> bytes:
    """Serialize a JSON value deterministically for immutable binding."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(value: object) -> str:
    """Return the unprefixed SHA-256 of a canonical JSON value."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    """Observed, independently measurable execution substrate identity."""

    implementation_commit: str
    implementation_tree: str
    environment_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class ExecutionClearance:
    """Externally issued bindings; constructing this value grants no authority."""

    owner_execution_authorization: str | None
    implementation_commit: str | None
    implementation_tree: str | None
    environment_manifest_sha256: str | None
    mission_package_sha256: str | None
    oracle_sha256: str | None
    adjudication_protocol_sha256: str | None

    def as_mapping(self) -> dict[str, str | None]:
        """Expose the exact fields for deterministic validation and evidence."""
        return {name: getattr(self, name) for name in REQUIRED_CLEARANCE_FIELDS}


@dataclass(frozen=True, slots=True)
class PreparedMission:
    """Non-result-bearing validation output; no evaluation has occurred."""

    mission_id: str
    package_sha256: str
    admitted_control_ids: tuple[str, ...]
    population_ids: tuple[str, ...]
    status: str = "PREPARED_NOT_EXECUTED"


@dataclass(frozen=True, slots=True)
class MissionExecution:
    """One completed synthetic mission result; never an official CDC record."""

    mission_id: str
    evaluations: tuple[Mapping[str, Any], ...]
    candidates: tuple[Mapping[str, Any], ...]
    dispositions: tuple[Mapping[str, Any], ...]
    transition_events: tuple[Mapping[str, Any], ...]
    drafts: tuple[Mapping[str, Any], ...]
    corrections: tuple[Mapping[str, Any], ...]
    official_handoff: str = "PROHIBITED"


EvaluationFunction = Callable[
    [Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]
]
WarrantFunction = Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[str, Mapping[str, Any]]]


def _require_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MissionContractError(f"{field} must be an object")
    return value


def _require_sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, list | tuple):
        raise MissionContractError(f"{field} must be an array")
    return value


def prepare_mission(package: Mapping[str, Any]) -> PreparedMission:
    """Validate bindings without evaluating a control or emitting a transition."""
    if package.get("mission_id") != MISSION_ID:
        raise MissionContractError("mission_id is outside the bounded mission")
    if package.get("assurance_mode") != ASSURANCE_MODE:
        raise MissionContractError("only SYNTHETIC_EVALUATION_ONLY is permitted")
    if "raw_source_text" in package or "source_parser" in package:
        raise MissionContractError("raw-source interpretation is prohibited")
    controls = _require_sequence(package.get("admitted_controls"), "admitted_controls")
    population = _require_sequence(package.get("population"), "population")
    control_ids: list[str] = []
    for index, item in enumerate(controls):
        control = _require_mapping(item, f"admitted_controls[{index}]")
        required = {"control_id", "admission_record_ref", "source_ref", "control_version"}
        missing = sorted(required - control.keys())
        if missing:
            raise MissionContractError(f"admitted control missing bindings: {missing}")
        control_ids.append(str(control["control_id"]))
    population_ids: list[str] = []
    for index, item in enumerate(population):
        member = _require_mapping(item, f"population[{index}]")
        if not isinstance(member.get("procedure_id"), str):
            raise MissionContractError("population member lacks stable procedure_id")
        population_ids.append(member["procedure_id"])
    return PreparedMission(
        mission_id=MISSION_ID,
        package_sha256=sha256(package),
        admitted_control_ids=tuple(control_ids),
        population_ids=tuple(population_ids),
    )


def require_result_clearance(
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    package: Mapping[str, Any],
) -> None:
    """Refuse unless every external binding is present and matches observation."""
    values = clearance.as_mapping()
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        raise ResultBearingMissionBlockedError(f"missing result-bearing clearance: {missing}")
    mismatches: list[str] = []
    if clearance.implementation_commit != runtime.implementation_commit:
        mismatches.append("implementation_commit")
    if clearance.implementation_tree != runtime.implementation_tree:
        mismatches.append("implementation_tree")
    if clearance.environment_manifest_sha256 != runtime.environment_manifest_sha256:
        mismatches.append("environment_manifest_sha256")
    if clearance.mission_package_sha256 != sha256(package):
        mismatches.append("mission_package_sha256")
    if mismatches:
        raise ResultBearingMissionBlockedError(f"result-bearing binding mismatch: {mismatches}")


def _require_standing(standing: Mapping[str, Any], *, mission_id: str) -> None:
    required = {
        "mission_id",
        "reviewer_id",
        "reviewer_role",
        "authority_scope_ref",
        "action",
        "validity",
        "revocation_status",
    }
    missing = sorted(required - standing.keys())
    if missing:
        raise MissionContractError(f"reviewer standing missing fields: {missing}")
    if standing["mission_id"] != mission_id:
        raise MissionContractError("reviewer standing is bound to another mission")
    validity = _require_mapping(standing["validity"], "standing.validity")
    if not {"valid_from", "valid_until", "observed_at"}.issubset(validity):
        raise MissionContractError("standing validity interval is incomplete")
    observed = str(validity["observed_at"])
    if not str(validity["valid_from"]) <= observed <= str(validity["valid_until"]):
        raise MissionContractError("reviewer standing is outside its validity interval")
    if standing["revocation_status"] != "NOT_REVOKED":
        raise MissionContractError("reviewer standing is revoked or unresolved")


def _drafts(
    *, candidate: Mapping[str, Any], disposition: Mapping[str, Any], event: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    provenance = {
        "finding_id": candidate["finding_id"],
        "candidate_id": candidate["candidate_id"],
        "evidence_ref": candidate["evidence_ref"],
        "control_id": candidate["control_id"],
        "admission_record_ref": candidate["admission_record_ref"],
        "warrant_ref": candidate["warrant_ref"],
        "human_disposition_id": disposition["disposition_id"],
        "transition_event_id": event["event_id"],
    }
    return tuple(
        {
            "draft_id": f"CDC-TEST-MISSION-001/{kind}",
            "kind": kind,
            "status": "SYNTHETIC_DRAFT_NOT_OFFICIAL",
            "official_handoff": "PROHIBITED",
            "provenance": provenance,
        }
        for kind in DRAFT_KINDS
    )


def execute_result_bearing_mission(
    package: Mapping[str, Any],
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    *,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
) -> MissionExecution:
    """Execute the bounded path after the external interlock has opened.

    This work order deliberately does not call this function.  The two injected
    components must implement independently governed evaluation and warrant
    contracts; the runner only binds their outputs.
    """
    prepared = prepare_mission(package)
    require_result_clearance(clearance, runtime, package)
    controls = {
        str(item["control_id"]): _require_mapping(item, "admitted_control")
        for item in _require_sequence(package["admitted_controls"], "admitted_controls")
        if isinstance(item, Mapping)
    }
    evidence = _require_mapping(package.get("evidence"), "evidence")
    standings = _require_mapping(package.get("reviewer_standings"), "reviewer_standings")
    registry = _require_mapping(package.get("transition_registry"), "transition_registry")
    evaluations: list[Mapping[str, Any]] = []
    candidates: list[Mapping[str, Any]] = []
    dispositions: list[Mapping[str, Any]] = []
    events: list[Mapping[str, Any]] = []
    drafts: list[Mapping[str, Any]] = []
    for raw_member in _require_sequence(package["population"], "population"):
        member = _require_mapping(raw_member, "population member")
        control = controls.get(str(member.get("control_id")))
        if control is None:
            raise MissionContractError("population references an unadmitted control")
        evidence_item = _require_mapping(evidence.get(str(member.get("evidence_ref"))), "evidence")
        evaluation = evaluator(member, control, evidence_item)
        evaluations.append(evaluation)
        warrant_class, warrant = warrant_builder(evaluation, control)
        if warrant_class not in {"ZTL_WARRANT", "FALLBACK_WARRANT"}:
            raise MissionContractError("warrant artifact class is not governed")
        candidate = {
            "candidate_id": member["candidate_id"],
            "finding_id": member["finding_id"],
            "status": "CANDIDATE_NOT_OFFICIAL",
            "control_id": control["control_id"],
            "admission_record_ref": control["admission_record_ref"],
            "evidence_ref": member["evidence_ref"],
            "evaluation_ref": evaluation["evaluation_id"],
            "warrant_ref": warrant["warrant_id"],
            "warrant_class": warrant_class,
            "warrant_digest": digest(warrant),
        }
        candidates.append(candidate)
        disposition = _require_mapping(member.get("human_disposition"), "human_disposition")
        standing = _require_mapping(standings.get(str(disposition.get("reviewer_id"))), "standing")
        _require_standing(standing, mission_id=prepared.mission_id)
        if disposition.get("action") != standing.get("action"):
            raise MissionContractError("disposition exceeds reviewer standing")
        proposal = _require_mapping(member.get("transition_proposal"), "transition_proposal")
        decision: GateDecision = evaluate_test_transition(proposal, registry)
        event_metadata = _require_mapping(member.get("event_metadata"), "event_metadata")
        event = emit_transition_event(proposal, decision, event_metadata=event_metadata)
        dispositions.append({**disposition, "status": "HUMAN_TEST_DISPOSITION"})
        events.append(event)
        drafts.extend(_drafts(candidate=candidate, disposition=disposition, event=event))
    corrections = tuple(
        make_successor(
            _require_mapping(item["predecessor"], "correction.predecessor"),
            _require_mapping(item["correction"], "correction.correction"),
        )
        for item in _require_sequence(package.get("corrections", []), "corrections")
        if isinstance(item, Mapping)
    )
    return MissionExecution(
        mission_id=prepared.mission_id,
        evaluations=tuple(evaluations),
        candidates=tuple(candidates),
        dispositions=tuple(dispositions),
        transition_events=tuple(events),
        drafts=tuple(drafts),
        corrections=corrections,
    )
