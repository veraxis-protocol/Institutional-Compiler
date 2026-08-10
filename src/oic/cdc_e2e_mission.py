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
from pathlib import Path
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
FROZEN_MISSION_PACKAGE_SHA256: Final = (
    "414d321dad9fe70671508848a19802f35635d27de60b932417f3305b961364f1"
)
FROZEN_MISSION_PACKAGE_BYTES: Final = 64199
FROZEN_MISSION_MANIFEST_SHA256: Final = (
    "506953539bd3991bf22d2855a898ae1a32ff618bd6dfed4be0d4c396a6fd152f"
)
GOVERNANCE_COMMIT: Final = "2e2282cb1bdeef972e2cf189030f24b011be2868"
ORACLE_SHA256: Final = "72b554e6c3ac25b8785805e57f2d0b3f0167a30d7fb9d62b61977b07a364d0d9"
ADJUDICATION_PROTOCOL_SHA256: Final = (
    "0e2a9f7202b2136b1edd76148da4f1c957ff86301c42ddf6f0dc1055ce20426b"
)
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


def _file_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha512(payload: bytes) -> str:
    return hashlib.sha512(payload).hexdigest()


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
class FrozenMissionInput:
    """Verified identity and structural counts of the persisted input package."""

    root: Path
    package_sha256: str
    package_bytes: int
    manifest_sha256: str
    population_count: int
    control_count: int
    evidence_object_count: int
    output_artifact_count: int


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


def verify_frozen_mission_input(root: Path) -> FrozenMissionInput:
    """Verify all persisted bytes and the registered 14-member package digest."""
    manifest_path = root / "PACKAGE-MANIFEST.json"
    manifest_payload = manifest_path.read_bytes()
    manifest = _require_mapping(json.loads(manifest_payload), "PACKAGE-MANIFEST.json")
    members = _require_sequence(manifest.get("members"), "manifest.members")
    identities: list[dict[str, object]] = []
    declared_paths: set[str] = set()
    for raw_member in members:
        member = _require_mapping(raw_member, "manifest member")
        relative = str(member.get("path"))
        if relative in declared_paths or relative == "PACKAGE-MANIFEST.json":
            raise MissionContractError("manifest contains a duplicate or self member")
        declared_paths.add(relative)
        payload = (root / relative).read_bytes()
        observed: dict[str, object] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": _file_sha256(payload),
            "sha512": _file_sha512(payload),
        }
        expected = {name: member.get(name) for name in observed}
        if observed != expected:
            raise MissionContractError(f"mission member identity mismatch: {relative}")
        identities.append(observed)
    physical = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if physical != declared_paths | {"PACKAGE-MANIFEST.json"}:
        raise MissionContractError("mission package contains missing or undeclared files")
    identity_bytes = json.dumps(identities, sort_keys=True, ensure_ascii=False).encode()
    package_digest = _file_sha256(identity_bytes)
    package_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    mission = _require_mapping(
        json.loads((root / "01-MISSION-MANIFEST.json").read_bytes()), "mission manifest"
    )
    population_paths = sorted((root / "02-POPULATION").glob("*.json"))
    evidence_keys = {
        "admission_record",
        "admitted_control",
        "evidence_bundle",
        "deterministic_evaluation",
        "warrant_artifact",
        "candidate",
    }
    evidence_count = 0
    for population_path in population_paths:
        population = _require_mapping(
            json.loads(population_path.read_bytes()), population_path.name
        )
        for raw_control in population.values():
            control = _require_mapping(raw_control, "population control")
            evidence_count += len(evidence_keys & control.keys())
    result = FrozenMissionInput(
        root=root,
        package_sha256=package_digest,
        package_bytes=package_bytes,
        manifest_sha256=_file_sha256(manifest_payload),
        population_count=len(population_paths),
        control_count=len(_require_sequence(mission.get("control_ids"), "control_ids")),
        evidence_object_count=evidence_count,
        output_artifact_count=len(list((root / "04-OUTPUTS").glob("*.json"))),
    )
    expected_result = FrozenMissionInput(
        root=root,
        package_sha256=FROZEN_MISSION_PACKAGE_SHA256,
        package_bytes=FROZEN_MISSION_PACKAGE_BYTES,
        manifest_sha256=FROZEN_MISSION_MANIFEST_SHA256,
        population_count=3,
        control_count=3,
        evidence_object_count=54,
        output_artifact_count=5,
    )
    if result != expected_result:
        raise MissionContractError("frozen mission package identity or counts differ")
    governance = _require_mapping(
        json.loads((root / "06-GOVERNANCE/binding.json").read_bytes()), "governance binding"
    )
    if (
        governance.get("governance_commit") != GOVERNANCE_COMMIT
        or governance.get("mission_oracle_sha256") != ORACLE_SHA256
        or governance.get("mission_adjudication_protocol_sha256") != ADJUDICATION_PROTOCOL_SHA256
    ):
        raise MissionContractError("semantic governance identity mismatch")
    return result


def prepare_mission(package: Mapping[str, Any]) -> PreparedMission:
    """Validate bindings without evaluating a control or emitting a transition."""
    if package.get("mission_id") != MISSION_ID:
        raise MissionContractError("mission_id is outside the bounded mission")
    if package.get("assurance_mode") != ASSURANCE_MODE:
        raise MissionContractError("only SYNTHETIC_EVALUATION_ONLY is permitted")
    if package.get("mission_package_sha256") != FROZEN_MISSION_PACKAGE_SHA256:
        raise MissionContractError("mission package identity is not the frozen input")
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
        package_sha256=FROZEN_MISSION_PACKAGE_SHA256,
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
    if clearance.mission_package_sha256 != FROZEN_MISSION_PACKAGE_SHA256:
        mismatches.append("mission_package_sha256")
    if package.get("mission_package_sha256") != FROZEN_MISSION_PACKAGE_SHA256:
        mismatches.append("loaded_mission_package_sha256")
    if clearance.oracle_sha256 != ORACLE_SHA256:
        mismatches.append("oracle_sha256")
    if clearance.adjudication_protocol_sha256 != ADJUDICATION_PROTOCOL_SHA256:
        mismatches.append("adjudication_protocol_sha256")
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


def validate_frozen_reviewer_standing(
    standing: Mapping[str, Any], *, mission_id: str, action: str, observed_at: str
) -> None:
    """Validate the frozen nested standing object without treating login as authority."""
    identity = _require_mapping(standing.get("identity"), "standing.identity")
    role = _require_mapping(standing.get("role"), "standing.role")
    permitted = _require_mapping(standing.get("permitted_action"), "standing.permitted_action")
    validity = _require_mapping(standing.get("validity"), "standing.validity")
    revocation = _require_mapping(standing.get("revocation"), "standing.revocation")
    required_values = (
        standing.get("mission") == mission_id,
        isinstance(identity.get("reviewer_id"), str),
        isinstance(role.get("role_id"), str),
        isinstance(standing.get("authority_scope_ref"), str),
        permitted.get("action") == action,
        str(validity.get("effective_from")) <= observed_at <= str(validity.get("effective_until")),
        revocation.get("status") == "NOT_REVOKED",
    )
    if not all(required_values):
        raise MissionContractError("frozen reviewer standing is absent, expired, or unauthorized")


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
