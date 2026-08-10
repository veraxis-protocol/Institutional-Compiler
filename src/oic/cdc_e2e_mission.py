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


# ---------------------------------------------------------------------------
# Seam closure: the executable projection is derived from verified frozen bytes.
#
# The defect this closes: ``prepare_mission`` accepts any mapping that carries
# the correct ``mission_package_sha256`` *label*. A label is a claim about bytes,
# not the bytes. Everything below refuses a caller-supplied mapping and consumes
# only what ``verify_frozen_mission_input`` actually read and hashed.
# ---------------------------------------------------------------------------

PREEXECUTION_CLARIFICATION_SHA256: Final = (
    "d6ce20b43f7707b82e14fb47eaae2481abbe5076a0513af0961cffa9a028e719"
)
HUMAN_ACTION_PLAN_SHA256: Final = "229a0c15d2bd2ee1db807904ff4d640f8fe39931372a002fbc3abf9e3244731e"

EXPECTED_CHAIN_COUNT: Final = 9
PROCEDURE_IDS: Final = ("P001", "P002", "P003")
CONTROL_IDS: Final = ("C-TENDER-01", "C-EVAL-01", "C-AWARD-01")

# Precomputed forms carried by the frozen package for reference. None of these
# may reach result-bearing evaluation or warrant construction; feeding a frozen
# answer back into the computation that is supposed to produce it would make the
# result unfalsifiable.
REFERENCE_ONLY_CHAIN_FIELDS: Final = (
    "deterministic_evaluation",
    "warrant_artifact",
    "candidate",
    "adjudicated_result",
)

# Fields the computational projection may consume.
EXECUTION_INPUT_CHAIN_FIELDS: Final = (
    "source_anchors",
    "admission_record",
    "admitted_control",
    "evidence_bundle",
    "prior_institutional_state",
)

MEMBER_ROLES: Final[dict[str, str]] = {
    "01-MISSION-MANIFEST.json": "REFERENCE_ONLY",
    "02-POPULATION/P001.json": "EXECUTION_INPUT",
    "02-POPULATION/P002.json": "EXECUTION_INPUT",
    "02-POPULATION/P003.json": "EXECUTION_INPUT",
    "03-AUTHORITY/test-reviewer.json": "EXECUTION_INPUT",
    "04-OUTPUTS/01-orientation-note.json": "POST_EXECUTION_RENDER_INPUT",
    "04-OUTPUTS/02-provisional-report.json": "POST_EXECUTION_RENDER_INPUT",
    "04-OUTPUTS/03-final-report.json": "POST_EXECUTION_RENDER_INPUT",
    "04-OUTPUTS/04-findings-summary.json": "POST_EXECUTION_RENDER_INPUT",
    "04-OUTPUTS/05-transmittal-letter.json": "POST_EXECUTION_RENDER_INPUT",
    "05-FRENCH/french-packet.json": "POST_EXECUTION_RENDER_INPUT",
    "06-GOVERNANCE/binding.json": "GOVERNANCE_BINDING",
    "07-CLAIM-EVIDENCE-MAP/"
    "CDC-END-TO-END-MISSION-001-CLAIM-EVIDENCE-MAP-v0.1.json": "EVALUATION_AID",
    "SHA256SUMS": "MANIFEST_INTEGRITY",
}
SELF_EXCLUDED_MEMBER: Final = "PACKAGE-MANIFEST.json"

OBSERVATION_IDS: Final = (
    "M01_SOURCE_BINDING",
    "M02_OIC_ADMITTED_MEANING_BINDING",
    "M03_FROZEN_MISSION_POPULATION",
    "M04_EVIDENCE_TO_CONTROL_TRACEABILITY",
    "M05_DETERMINISTIC_EVALUATION_SEPARATION",
    "M06_ZTL_WARRANT_VS_FALLBACK_SEPARATION",
    "M07_CANDIDATE_FINDING_NON_OFFICIALITY",
    "M08_REVIEWER_STANDING_AND_AUTHORITY_SCOPE",
    "M09_HUMAN_DISPOSITION_BOUNDARY",
    "M10_VEIP_TRANSITION_AFTER_VALID_DISPOSITION",
    "M11_DELIVERABLE_STATE_FIDELITY",
    "M12_CORRECTION_AND_PREDECESSOR_PRESERVATION",
)

DENOMINATOR_STATES: Final = (
    "completed",
    "refused",
    "unresolved",
    "blocked",
    "non_evaluable",
)


class ProjectionProvenanceError(MissionContractError):
    """A projection was not derived from verified frozen bytes."""


@dataclass(frozen=True, slots=True)
class ExecutionChain:
    """One procedure/control chain derived from verified bytes."""

    chain_id: str
    procedure_id: str
    control_id: str
    ebawu_ref: str
    execution_input: Mapping[str, Any]
    reference_only: Mapping[str, Any]

    def input_digest(self) -> str:
        """Digest over the execution input only; reference forms are excluded."""
        return sha256(self.execution_input)


@dataclass(frozen=True, slots=True)
class MissionProjection:
    """Executable projection derived exclusively from verified frozen bytes.

    ``provenance_token`` is computed from the member digests actually read and
    hashed during verification. A caller cannot mint one by asserting a package
    label, which is what makes label substitution refusable rather than merely
    discouraged.
    """

    mission_id: str
    package_sha256: str
    provenance_token: str
    chains: tuple[ExecutionChain, ...]
    authority: Mapping[str, Any]
    output_definitions: tuple[Mapping[str, Any], ...]
    french_packet: Mapping[str, Any]
    governance_binding: Mapping[str, Any]
    member_roles: Mapping[str, str]
    historical_governance_field: Mapping[str, Any]

    def chain_ids(self) -> tuple[str, ...]:
        """Stable ordered chain identifiers."""
        return tuple(chain.chain_id for chain in self.chains)


def _provenance_token(root: Path, manifest: Mapping[str, Any]) -> str:
    """Derive a token from the bytes on disk, not from any declared label."""
    members = _require_sequence(manifest.get("members"), "manifest.members")
    observed = []
    for raw in members:
        member = _require_mapping(raw, "manifest member")
        relative = str(member.get("path"))
        observed.append([relative, _file_sha256((root / relative).read_bytes())])
    observed.sort()
    return sha256(
        {
            "package_sha256": FROZEN_MISSION_PACKAGE_SHA256,
            "manifest_sha256": FROZEN_MISSION_MANIFEST_SHA256,
            "observed_member_digests": observed,
        }
    )


def project_frozen_mission(frozen: FrozenMissionInput) -> MissionProjection:
    """Derive the nine-chain executable projection from verified frozen bytes.

    ``frozen`` must come from :func:`verify_frozen_mission_input`, which reads
    and hashes every member. Nothing here trusts a caller-supplied mapping.
    """
    root = frozen.root
    if frozen.package_sha256 != FROZEN_MISSION_PACKAGE_SHA256:
        raise ProjectionProvenanceError("projection source is not the frozen package")
    manifest = _require_mapping(
        json.loads((root / "PACKAGE-MANIFEST.json").read_bytes()), "PACKAGE-MANIFEST.json"
    )
    token = _provenance_token(root, manifest)

    chains: list[ExecutionChain] = []
    for procedure_id in PROCEDURE_IDS:
        population = _require_mapping(
            json.loads((root / f"02-POPULATION/{procedure_id}.json").read_bytes()),
            f"population {procedure_id}",
        )
        for control_id in CONTROL_IDS:
            raw = population.get(control_id)
            if raw is None:
                raise MissionContractError(f"missing chain {procedure_id}x{control_id}")
            chain = _require_mapping(raw, "population chain")
            execution_input = {
                field: chain[field] for field in EXECUTION_INPUT_CHAIN_FIELDS if field in chain
            }
            missing = sorted(set(EXECUTION_INPUT_CHAIN_FIELDS) - execution_input.keys())
            if missing:
                raise MissionContractError(
                    f"chain {procedure_id}x{control_id} lacks execution inputs: {missing}"
                )
            execution_input["procedure_id"] = chain["procedure_id"]
            execution_input["control_ref"] = chain["control_ref"]
            execution_input["ebawu"] = chain["ebawu"]
            reference_only = {
                field: chain[field] for field in REFERENCE_ONLY_CHAIN_FIELDS if field in chain
            }
            chains.append(
                ExecutionChain(
                    chain_id=f"{procedure_id}x{control_id}",
                    procedure_id=procedure_id,
                    control_id=control_id,
                    ebawu_ref=str(chain["ebawu"]["ebawu_id"]),
                    execution_input=execution_input,
                    reference_only=reference_only,
                )
            )
    if len(chains) != EXPECTED_CHAIN_COUNT:
        raise MissionContractError(f"projection produced {len(chains)} chains, expected 9")

    outputs = tuple(
        _require_mapping(json.loads(path.read_bytes()), path.name)
        for path in sorted((root / "04-OUTPUTS").glob("*.json"))
    )
    if len(outputs) != 5:
        raise MissionContractError("five frozen output definitions are required")

    mission_manifest = _require_mapping(
        json.loads((root / "01-MISSION-MANIFEST.json").read_bytes()), "mission manifest"
    )
    governance = _require_mapping(
        json.loads((root / "06-GOVERNANCE/binding.json").read_bytes()), "governance binding"
    )
    historical = {
        "source": "01-MISSION-MANIFEST.json/governance_binding",
        "observed_value": mission_manifest.get("governance_binding", {}).get("binding_state"),
        "status": "PRE_BINDING_CONSTRUCTION_SNAPSHOT",
        "controlling": False,
        "controlling_source": ["06-GOVERNANCE/binding.json", "PACKAGE-MANIFEST.json"],
        "normalized_or_rewritten": False,
    }
    return MissionProjection(
        mission_id=MISSION_ID,
        package_sha256=frozen.package_sha256,
        provenance_token=token,
        chains=tuple(chains),
        authority=_require_mapping(
            json.loads((root / "03-AUTHORITY/test-reviewer.json").read_bytes()), "authority"
        ),
        output_definitions=outputs,
        french_packet=_require_mapping(
            json.loads((root / "05-FRENCH/french-packet.json").read_bytes()), "french packet"
        ),
        governance_binding=governance,
        member_roles=dict(MEMBER_ROLES),
        historical_governance_field=historical,
    )


def require_projected_source(projection: object, frozen: FrozenMissionInput) -> MissionProjection:
    """Refuse anything that is not a projection of these verified bytes.

    A mapping carrying the correct package digest label is rejected here. Only a
    :class:`MissionProjection` whose provenance token recomputes from the bytes
    on disk is accepted.
    """
    if not isinstance(projection, MissionProjection):
        raise ProjectionProvenanceError(
            "execution source must be a MissionProjection derived from verified bytes; "
            "a mapping carrying the package digest label is not the package"
        )
    manifest = _require_mapping(
        json.loads((frozen.root / "PACKAGE-MANIFEST.json").read_bytes()), "PACKAGE-MANIFEST.json"
    )
    if projection.provenance_token != _provenance_token(frozen.root, manifest):
        raise ProjectionProvenanceError("projection provenance token does not recompute")
    if projection.package_sha256 != FROZEN_MISSION_PACKAGE_SHA256:
        raise ProjectionProvenanceError("projection is bound to a different package")
    return projection


def member_consumption_ledger(frozen: FrozenMissionInput) -> dict[str, Any]:
    """Assign every declared member exactly one role. No silent-unused member."""
    manifest = _require_mapping(
        json.loads((frozen.root / "PACKAGE-MANIFEST.json").read_bytes()), "PACKAGE-MANIFEST.json"
    )
    declared = [
        str(_require_mapping(raw, "member").get("path"))
        for raw in _require_sequence(manifest.get("members"), "manifest.members")
    ]
    unclassified = sorted(set(declared) - MEMBER_ROLES.keys())
    if unclassified:
        raise MissionContractError(f"unclassified package members: {unclassified}")
    return {
        "declared_members": len(declared),
        "classified_members": len(declared),
        "coverage": f"{len(declared)}/{len(declared)}",
        "roles": {path: MEMBER_ROLES[path] for path in sorted(declared)},
        "self_excluded_manifest": {
            "path": SELF_EXCLUDED_MEMBER,
            "role": "MANIFEST_INTEGRITY",
            "counted_in_declared_members": False,
        },
        "silent_unused_members": 0,
    }


# ---------------------------------------------------------------------------
# Two-stage human boundary.
#
# Stage 1 stops at machine candidate formation. It emits no transition, confers
# no draft eligibility, and prohibits official handoff. Continuation requires an
# external human-disposition artifact that binds the candidate actually observed
# at Stage 1 — not a candidate the plan predicted.
# ---------------------------------------------------------------------------

STAGE_1_TERMINAL_STATE: Final = "EVALUATION_AND_CANDIDATE_FORMATION_COMPLETE"

STAGE_2_BINDING_FIELDS: Final = (
    "stage_1_observation_digest",
    "human_disposition_artifact_digests",
    "correction_stimulus_digest",
)


class HumanDispositionRequiredError(MissionContractError):
    """Continuation was attempted without a bound human disposition."""


class CandidateBindingError(MissionContractError):
    """A disposition did not bind the candidate observed at Stage 1."""


class PredecessorBindingError(MissionContractError):
    """A correction did not bind, or would mutate, its actual predecessor."""


@dataclass(frozen=True, slots=True)
class Stage1ChainObservation:
    """One chain's Stage-1 outcome. Non-adjudicating."""

    chain_id: str
    outcome_state: str
    candidate_digest: str | None
    input_digest: str
    detail: str

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record."""
        return {
            "chain_id": self.chain_id,
            "outcome_state": self.outcome_state,
            "candidate_digest": self.candidate_digest,
            "input_digest": self.input_digest,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class Stage1Observation:
    """Immutable Stage-1 checkpoint across the whole nine-chain denominator."""

    mission_id: str
    package_sha256: str
    provenance_token: str
    stage: str
    chains: tuple[Stage1ChainObservation, ...]
    accounting: Mapping[str, int]
    institutional_transition: str = "NONE"
    draft_eligibility: str = "NONE"
    official_handoff: str = "PROHIBITED"
    human_disposition: str = "NOT_YET_SUPPLIED"

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record; the digest binds this exact content."""
        body = {
            "mission_id": self.mission_id,
            "package_sha256": self.package_sha256,
            "provenance_token": self.provenance_token,
            "stage": self.stage,
            "chains": [chain.as_record() for chain in self.chains],
            "accounting": dict(self.accounting),
            "institutional_transition": self.institutional_transition,
            "draft_eligibility": self.draft_eligibility,
            "official_handoff": self.official_handoff,
            "human_disposition": self.human_disposition,
        }
        body["stage_1_observation_digest"] = sha256(body)
        return body

    def digest(self) -> str:
        """The frozen Stage-1 observation digest."""
        return str(self.as_record()["stage_1_observation_digest"])

    def candidate_digests(self) -> dict[str, str]:
        """Candidate digests actually formed, by chain."""
        return {
            chain.chain_id: chain.candidate_digest
            for chain in self.chains
            if chain.candidate_digest is not None
        }


def run_stage_1(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    *,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
) -> Stage1Observation:
    """Evaluate and form candidates across all nine chains, then stop.

    The denominator survives individual failures: a chain that raises is recorded
    as ``non_evaluable`` and the remaining chains still run. An early exception
    must never erase the rest of the population.
    """
    require_projected_source(projection, frozen)
    tally = dict.fromkeys(DENOMINATOR_STATES, 0)
    observations: list[Stage1ChainObservation] = []
    for chain in projection.chains:
        try:
            evaluation = evaluator(
                chain.execution_input, chain.execution_input, chain.execution_input
            )
            warrant_class, warrant = warrant_builder(evaluation, chain.execution_input)
            if warrant_class not in {"ZTL_WARRANT", "FALLBACK_WARRANT"}:
                raise MissionContractError("warrant artifact class is not governed")
            candidate = {
                "chain_id": chain.chain_id,
                "status": "CANDIDATE_NOT_OFFICIAL",
                "control_id": chain.control_id,
                "evaluation": evaluation,
                "warrant_class": warrant_class,
                "warrant": warrant,
                "input_digest": chain.input_digest(),
            }
            tally["completed"] += 1
            observations.append(
                Stage1ChainObservation(
                    chain_id=chain.chain_id,
                    outcome_state="completed",
                    candidate_digest=sha256(candidate),
                    input_digest=chain.input_digest(),
                    detail="candidate formed; no transition and no draft eligibility",
                )
            )
        # A failing chain is an observation, not a reason to abandon the denominator.
        except Exception as error:
            tally["non_evaluable"] += 1
            observations.append(
                Stage1ChainObservation(
                    chain_id=chain.chain_id,
                    outcome_state="non_evaluable",
                    candidate_digest=None,
                    input_digest=chain.input_digest(),
                    detail=f"{type(error).__name__}: {error}",
                )
            )
    total = sum(tally.values())
    if total != EXPECTED_CHAIN_COUNT:
        raise MissionContractError(f"denominator lost: {total} of 9 accounted")
    return Stage1Observation(
        mission_id=projection.mission_id,
        package_sha256=projection.package_sha256,
        provenance_token=projection.provenance_token,
        stage=STAGE_1_TERMINAL_STATE,
        chains=tuple(observations),
        accounting=tally,
    )


def bind_human_disposition(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    action_plan_sha256: str,
) -> dict[str, Any]:
    """Accept a disposition only if it binds the observed Stage-1 candidate.

    The pre-registered stimulus class is not authority to proceed. The binding
    check is on the candidate digest that Stage 1 actually produced.
    """
    if action_plan_sha256 != HUMAN_ACTION_PLAN_SHA256:
        raise MissionContractError("human action plan identity mismatch")
    chain_id = str(disposition.get("chain_id"))
    observed = stage_1.candidate_digests().get(chain_id)
    if observed is None:
        raise HumanDispositionRequiredError(
            f"no Stage-1 candidate exists for {chain_id}; disposition cannot bind"
        )
    supplied = disposition.get("candidate_digest")
    if supplied != observed:
        raise CandidateBindingError(
            f"disposition for {chain_id} binds {supplied!r}, Stage 1 observed {observed!r}"
        )
    action = str(disposition.get("action"))
    if action not in {
        "ACCEPT_CANDIDATE",
        "QUALIFY",
        "DISMISS",
        "REQUEST_EVIDENCE",
        "ESCALATE",
        "DEFER",
    }:
        raise MissionContractError(f"disposition action is not permitted: {action}")
    return {
        "chain_id": chain_id,
        "action": action,
        "candidate_digest": observed,
        "bound_to_stage_1_observation": stage_1.digest(),
        "action_plan_sha256": action_plan_sha256,
        "status": "HUMAN_TEST_DISPOSITION_BOUND",
    }


def require_human_disposition(stage_1: Stage1Observation, dispositions: Mapping[str, Any]) -> None:
    """Hold at Stage 1 unless a disposition exists for every formed candidate."""
    formed = set(stage_1.candidate_digests())
    supplied = set(dispositions)
    missing = sorted(formed - supplied)
    if missing:
        raise HumanDispositionRequiredError(
            f"HOLD: Stage-1 complete, human disposition not supplied for {missing}"
        )


def bind_correction(
    predecessor: Mapping[str, Any], correction: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind a correction to its actual predecessor without mutating it."""
    before = sha256(predecessor)
    supplied = correction.get("predecessor_digest")
    if supplied != before:
        raise PredecessorBindingError(
            f"correction binds predecessor {supplied!r}, actual {before!r}"
        )
    successor = make_successor(predecessor, correction)
    after = sha256(predecessor)
    if before != after:
        raise PredecessorBindingError("predecessor mutated during correction")
    return {
        "correction_stimulus_id": correction.get("correction_stimulus_id", "HA-CORRECTION-001"),
        "predecessor_before_digest": before,
        "predecessor_after_digest": after,
        "successor_id": successor["successor_id"],
        "supersedes": successor["supersedes"],
        "correction_reason": successor["correction_reason"],
        "changed_refs": successor["changed_fact_or_control_refs"],
        "affected_output_eligibility": "INELIGIBLE_UNTIL_REGENERATED_OR_HUMAN_RESOLVED",
        "predecessor_mutated": before != after,
    }


def require_stage_2_clearance(
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    *,
    stage_2_bindings: Mapping[str, Any],
) -> None:
    """Stage-2 continuation binds Stage-1 and human artifacts in addition."""
    require_projected_source(projection, frozen)
    require_result_clearance(
        clearance, runtime, {"mission_package_sha256": projection.package_sha256}
    )
    missing = sorted(name for name in STAGE_2_BINDING_FIELDS if not stage_2_bindings.get(name))
    if missing:
        raise ResultBearingMissionBlockedError(f"missing stage-2 bindings: {missing}")


def observation_producer(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation | None = None,
) -> dict[str, Any]:
    """Produce M01-M12 non-adjudicating observations.

    These record what was observed. They contain no adjudication vocabulary: no
    MATCH, PASS, FAIL, VIOLATION or COMPLIANT. Comparing an observation to the
    oracle is the adjudication layer's work, not this function's.
    """
    require_projected_source(projection, frozen)
    ledger = member_consumption_ledger(frozen)
    french = projection.french_packet
    observations: dict[str, Any] = {
        "M01_SOURCE_BINDING": {
            "chains_with_source_anchors": sum(
                1 for c in projection.chains if c.execution_input.get("source_anchors")
            ),
            "chain_count": len(projection.chains),
        },
        "M02_OIC_ADMITTED_MEANING_BINDING": {
            "chains_with_admission_record": sum(
                1 for c in projection.chains if c.execution_input.get("admission_record")
            ),
            "admitted_control_ids": sorted({c.control_id for c in projection.chains}),
        },
        "M03_FROZEN_MISSION_POPULATION": {
            "package_sha256": projection.package_sha256,
            "chain_ids": list(projection.chain_ids()),
            "chain_count": len(projection.chains),
        },
        "M04_EVIDENCE_TO_CONTROL_TRACEABILITY": {
            "chains_with_evidence_bundle": sum(
                1 for c in projection.chains if c.execution_input.get("evidence_bundle")
            ),
            "evidence_bound_to_control": [
                {"chain_id": c.chain_id, "control_id": c.control_id} for c in projection.chains
            ],
        },
        "M05_DETERMINISTIC_EVALUATION_SEPARATION": {
            "precomputed_evaluation_in_execution_input": any(
                "deterministic_evaluation" in c.execution_input for c in projection.chains
            ),
            "precomputed_evaluation_classified_reference_only": all(
                "deterministic_evaluation" in c.reference_only for c in projection.chains
            ),
        },
        "M06_ZTL_WARRANT_VS_FALLBACK_SEPARATION": {
            "precomputed_warrant_in_execution_input": any(
                "warrant_artifact" in c.execution_input for c in projection.chains
            ),
            "governed_warrant_classes": ["ZTL_WARRANT", "FALLBACK_WARRANT"],
        },
        "M07_CANDIDATE_FINDING_NON_OFFICIALITY": {
            "output_official_status": sorted(
                {str(o.get("official_status")) for o in projection.output_definitions}
            ),
            "official_cdc_record_creation": OFFICIAL_CDC_RECORD_CREATION,
        },
        "M08_REVIEWER_STANDING_AND_AUTHORITY_SCOPE": {
            "standing_dimensions_present": sorted(
                d
                for d in (
                    "identity",
                    "role",
                    "mission",
                    "authority_scope_ref",
                    "permitted_action",
                    "validity",
                    "revocation",
                )
                if d in projection.authority
            ),
            "authority_scope_ref": projection.authority.get("authority_scope_ref"),
        },
        "M09_HUMAN_DISPOSITION_BOUNDARY": {
            "stage_1_terminal_state": STAGE_1_TERMINAL_STATE,
            "human_disposition": (
                stage_1.human_disposition if stage_1 is not None else "NOT_YET_SUPPLIED"
            ),
            "institutional_transition": (
                stage_1.institutional_transition if stage_1 is not None else "NONE"
            ),
        },
        "M10_VEIP_TRANSITION_AFTER_VALID_DISPOSITION": {
            "transition_emitted": False,
            "requires_bound_disposition": True,
        },
        "M11_DELIVERABLE_STATE_FIDELITY": {
            "output_definition_ids": [
                str(o.get("artifact_id")) for o in projection.output_definitions
            ],
            "french_path": french.get("french_path_state"),
            "french_named_absences": len(
                _require_sequence(
                    french.get("substantive_french_support_absent_at", []), "french absences"
                )
            ),
        },
        "M12_CORRECTION_AND_PREDECESSOR_PRESERVATION": {
            "correction_stimulus_id": "HA-CORRECTION-001",
            "predecessor_mutation_prohibited": True,
            "correction_executed": False,
        },
    }
    missing = sorted(set(OBSERVATION_IDS) - observations.keys())
    if missing:
        raise MissionContractError(f"observation producer coverage incomplete: {missing}")
    return {
        "coverage": f"{len(observations)}/{len(OBSERVATION_IDS)}",
        "observations": observations,
        "member_consumption": ledger,
        "historical_governance_field": projection.historical_governance_field,
        "adjudication_present": False,
    }
