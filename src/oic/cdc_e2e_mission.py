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
# The controlling mission input is v0.2. Its only substantive difference from
# v0.1 is reviewer-authority currentness: the v0.1 standing expired at
# 2026-08-11T00:00:00Z, so it could not authorize a real later disposition.
# v0.1 is retained immutable and addressable as the predecessor.
FROZEN_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.2"
FROZEN_MISSION_PACKAGE_SHA256: Final = (
    "00dd820cfe43b780d5bec1a12382b16a7d6d9e45d6546c4fc10f3a83ab321510"
)
FROZEN_MISSION_PACKAGE_BYTES: Final = 65849
FROZEN_MISSION_MANIFEST_SHA256: Final = (
    "b159625c4d812f197278b91e7175551cbb2e77efb24a3952ba41c89643987a95"
)

PREDECESSOR_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.1"
PREDECESSOR_MISSION_PACKAGE_SHA256: Final = (
    "414d321dad9fe70671508848a19802f35635d27de60b932417f3305b961364f1"
)
PREDECESSOR_MISSION_PACKAGE_BYTES: Final = 64199
PREDECESSOR_AUTHORITY_SHA256: Final = (
    "a82c078427fefe23abbb2bd066e9e730cea7e1fc2a3bab553e8352fa48b3db23"
)
SUPERSESSION_REASON: Final = "PREEXECUTION_AUTHORITY_CURRENTNESS"
# Observed system UTC clock at issuance. Not backdated.
AUTHORITY_ISSUED_AT: Final = "2026-08-11T16:00:02Z"
AUTHORITY_EFFECTIVE_UNTIL: Final = "2026-08-18T00:00:00Z"
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
    "action_plan_sha256",
    "owner_preexecution_interpretation_sha256",
)
# Retained only as the historical five-kind vocabulary. It is NOT the authoritative
# output source: Stage 2 renders from the five frozen ``04-OUTPUTS/`` definitions.
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
    action_plan_sha256: str | None = None
    owner_preexecution_interpretation_sha256: str | None = None

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
    if clearance.action_plan_sha256 != HUMAN_ACTION_PLAN_SHA256:
        mismatches.append("action_plan_sha256")
    if (
        clearance.owner_preexecution_interpretation_sha256
        != OWNER_PREEXECUTION_INTERPRETATION_SHA256
    ):
        mismatches.append("owner_preexecution_interpretation_sha256")
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


LEGACY_MAPPING_ENTRYPOINT_STATE: Final = "RETIRED_FAIL_CLOSED"

LEGACY_MAPPING_ENTRYPOINT_NOTICE: Final = (
    "the caller-supplied mapping entrypoint is retired: "
    "execute_result_bearing_mission() can no longer execute anything. A mapping is a "
    "claim about bytes, not the bytes. Result-bearing execution now runs only through "
    "execute_authorized_stage_1() and execute_authorized_stage_2(), which consume a "
    "MissionProjection derived from verified frozen bytes under an exact ExecutionClearance."
)


def execute_result_bearing_mission(
    package: Mapping[str, Any],
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    *,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
) -> MissionExecution:
    """Retired. Fails closed before doing anything at all.

    The symbol is preserved for compatibility only. Independent review found this
    entrypoint reachable with an arbitrary mapping that merely carried the correct
    package-digest label, which made every downstream binding negotiable. It now
    raises before it can prepare a mission, evaluate, form a candidate, validate a
    caller-supplied standing, evaluate a transition, emit an event, create a draft
    or create a correction. The injected components are accepted and discarded
    unused so no caller can observe them being reached.
    """
    del package, clearance, runtime, evaluator, warrant_builder
    raise ResultBearingMissionBlockedError(LEGACY_MAPPING_ENTRYPOINT_NOTICE)


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

    def chain(self, chain_id: str) -> ExecutionChain:
        """Return the verified chain, or refuse. Never synthesizes one."""
        for chain in self.chains:
            if chain.chain_id == chain_id:
                return chain
        raise MissionContractError(f"no verified chain {chain_id}")


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
# Frozen human action plan.
#
# The defect this closes: the plan's SHA-256 was checked, but its bytes did not
# determine anything. A correct digest label sitting beside a caller's own choice
# of stimulus is an attestation about a file nobody read. Everything below reads
# the file, recomputes its digest, and makes the recovered contents the only
# source of the preregistered action classes and the correction target.
# ---------------------------------------------------------------------------

HUMAN_ACTION_PLAN_RELPATH: Final = (
    "veraxis/cdc-e2e-mission-001/preexecution/"
    "CDC-END-TO-END-MISSION-001-HUMAN-ACTION-PLAN-v0.1.json"
)
HUMAN_ACTION_PLAN_BYTES: Final = 11374
EXPECTED_DISPOSITION_TARGET_COUNT: Final = 9

ACTION_PLAN_TARGET_REQUIRED_FIELDS: Final = (
    "target_id",
    "procedure_id",
    "public_procedure_id",
    "control_ref",
    "preregistered_reviewer_action_class",
    "runtime_binding_requirement",
)

ACTION_PLAN_CORRECTION_REQUIRED_FIELDS: Final = (
    "correction_stimulus_id",
    "target_id",
    "procedure_id",
    "control_ref",
    "predecessor_ebawu_ref",
    "precondition",
    "predecessor_mutation_prohibited",
    "required_correction_fields",
)


class ActionPlanProvenanceError(MissionContractError):
    """An action plan was not derived from the verified frozen bytes."""


class ActionPlanBindingError(MissionContractError):
    """A submitted stimulus is not the one the frozen action plan preregistered."""


@dataclass(frozen=True, slots=True)
class ActionPlanTarget:
    """One preregistered disposition target recovered from frozen bytes."""

    target_id: str
    procedure_id: str
    public_procedure_id: str
    control_ref: str
    preregistered_action_class: str
    runtime_binding_requirement: str

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record."""
        return {
            "target_id": self.target_id,
            "procedure_id": self.procedure_id,
            "public_procedure_id": self.public_procedure_id,
            "control_ref": self.control_ref,
            "preregistered_reviewer_action_class": self.preregistered_action_class,
            "runtime_binding_requirement": self.runtime_binding_requirement,
        }


@dataclass(frozen=True, slots=True)
class ActionPlanCorrection:
    """The single correction stimulus recovered from frozen bytes."""

    correction_stimulus_id: str
    target_id: str
    procedure_id: str
    control_ref: str
    predecessor_ebawu_ref: str
    precondition: str
    predecessor_mutation_prohibited: bool
    required_correction_fields: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record; this is the controlling correction-stimulus content."""
        return {
            "correction_stimulus_id": self.correction_stimulus_id,
            "target_id": self.target_id,
            "procedure_id": self.procedure_id,
            "control_ref": self.control_ref,
            "predecessor_ebawu_ref": self.predecessor_ebawu_ref,
            "precondition": self.precondition,
            "predecessor_mutation_prohibited": self.predecessor_mutation_prohibited,
            "required_correction_fields": list(self.required_correction_fields),
        }

    def digest(self) -> str:
        """Digest of the frozen stimulus, never of a caller mapping."""
        return sha256(self.as_record())


@dataclass(frozen=True, slots=True)
class FrozenActionPlan:
    """Operational projection of the frozen human action plan.

    ``provenance_token`` is derived from the bytes actually read, so a caller
    cannot mint one by asserting the plan's digest, and cannot mutate a field of
    a constructed instance without the token ceasing to recompute.
    """

    path: Path
    sha256_hex: str
    byte_count: int
    provenance_token: str
    mission_id: str
    reviewer_id: str
    authority_scope_ref: str
    permitted_action: str
    permitted_disposition_vocabulary: tuple[str, ...]
    targets: tuple[ActionPlanTarget, ...]
    correction: ActionPlanCorrection

    def target_for(self, procedure_id: str, control_id: str) -> ActionPlanTarget:
        """Recover the preregistered target for an actual chain, or refuse."""
        for target in self.targets:
            if target.procedure_id == procedure_id and target.control_ref == control_id:
                return target
        raise ActionPlanBindingError(
            f"the frozen action plan preregisters no target for {procedure_id} x {control_id}"
        )

    def action_classes(self) -> dict[str, str]:
        """Preregistered action class per target id, recovered from bytes."""
        return {target.target_id: target.preregistered_action_class for target in self.targets}


def _action_plan_provenance_token(payload: bytes, document: Mapping[str, Any]) -> str:
    """Derive a token from the bytes on disk, not from any declared label."""
    targets = _require_sequence(document.get("disposition_targets"), "disposition_targets")
    return sha256(
        {
            "action_plan_sha256": _file_sha256(payload),
            "action_plan_sha512": _file_sha512(payload),
            "byte_count": len(payload),
            "target_action_classes": sorted(
                [
                    str(_require_mapping(raw, "target").get("target_id")),
                    str(_require_mapping(raw, "target").get("preregistered_reviewer_action_class")),
                ]
                for raw in targets
            ),
            "correction_stimulus_id": _require_mapping(
                document.get("correction_stimulus"), "correction_stimulus"
            ).get("correction_stimulus_id"),
        }
    )


def verify_frozen_action_plan(path: Path) -> FrozenActionPlan:
    """Read the exact bytes, recompute the digest, and refuse any mismatch."""
    payload = path.read_bytes()
    observed_sha256 = _file_sha256(payload)
    if observed_sha256 != HUMAN_ACTION_PLAN_SHA256:
        raise ActionPlanProvenanceError(
            f"human action plan digest is {observed_sha256}, expected {HUMAN_ACTION_PLAN_SHA256}"
        )
    if len(payload) != HUMAN_ACTION_PLAN_BYTES:
        raise ActionPlanProvenanceError(
            f"human action plan is {len(payload)} bytes, expected {HUMAN_ACTION_PLAN_BYTES}"
        )
    document = _require_mapping(json.loads(payload), "human action plan")
    raw_targets = _require_sequence(document.get("disposition_targets"), "disposition_targets")
    if len(raw_targets) != EXPECTED_DISPOSITION_TARGET_COUNT:
        raise ActionPlanProvenanceError(
            f"frozen action plan declares {len(raw_targets)} disposition targets, expected 9"
        )
    targets: list[ActionPlanTarget] = []
    for raw in raw_targets:
        target = _require_mapping(raw, "disposition target")
        missing = sorted(set(ACTION_PLAN_TARGET_REQUIRED_FIELDS) - target.keys())
        if missing:
            raise ActionPlanProvenanceError(f"disposition target missing fields: {missing}")
        action_class = str(target["preregistered_reviewer_action_class"])
        if action_class not in NEW_STATE_BY_ACTION:
            raise ActionPlanProvenanceError(
                f"preregistered action class is not a permitted disposition: {action_class}"
            )
        targets.append(
            ActionPlanTarget(
                target_id=str(target["target_id"]),
                procedure_id=str(target["procedure_id"]),
                public_procedure_id=str(target["public_procedure_id"]),
                control_ref=str(target["control_ref"]),
                preregistered_action_class=action_class,
                runtime_binding_requirement=str(target["runtime_binding_requirement"]),
            )
        )
    raw_correction = _require_mapping(document.get("correction_stimulus"), "correction_stimulus")
    missing = sorted(set(ACTION_PLAN_CORRECTION_REQUIRED_FIELDS) - raw_correction.keys())
    if missing:
        raise ActionPlanProvenanceError(f"correction stimulus missing fields: {missing}")
    correction = ActionPlanCorrection(
        correction_stimulus_id=str(raw_correction["correction_stimulus_id"]),
        target_id=str(raw_correction["target_id"]),
        procedure_id=str(raw_correction["procedure_id"]),
        control_ref=str(raw_correction["control_ref"]),
        predecessor_ebawu_ref=str(raw_correction["predecessor_ebawu_ref"]),
        precondition=str(raw_correction["precondition"]),
        predecessor_mutation_prohibited=bool(raw_correction["predecessor_mutation_prohibited"]),
        required_correction_fields=tuple(
            str(name)
            for name in _require_sequence(
                raw_correction["required_correction_fields"], "required_correction_fields"
            )
        ),
    )
    if document.get("mission_id") != MISSION_ID:
        raise ActionPlanProvenanceError("frozen action plan is bound to another mission")
    plan = FrozenActionPlan(
        path=path,
        sha256_hex=observed_sha256,
        byte_count=len(payload),
        provenance_token=_action_plan_provenance_token(payload, document),
        mission_id=str(document["mission_id"]),
        reviewer_id=str(document["reviewer_id"]),
        authority_scope_ref=str(document["authority_scope_ref"]),
        permitted_action=str(document["permitted_action"]),
        permitted_disposition_vocabulary=tuple(
            str(name)
            for name in _require_sequence(
                document.get("permitted_disposition_vocabulary"), "permitted_disposition_vocabulary"
            )
        ),
        targets=tuple(targets),
        correction=correction,
    )
    if correction.target_id not in {target.target_id for target in plan.targets}:
        raise ActionPlanProvenanceError(
            "the correction stimulus names a target the plan does not preregister"
        )
    return plan


def require_verified_action_plan(plan: object) -> FrozenActionPlan:
    """Refuse anything that is not a projection of the verified plan bytes.

    A mapping carrying the correct SHA-256 label is rejected here, and so is a
    :class:`FrozenActionPlan` whose fields were edited after construction: the
    provenance token is recomputed from the file the instance names.
    """
    if not isinstance(plan, FrozenActionPlan):
        raise ActionPlanProvenanceError(
            "the action plan must be a FrozenActionPlan derived from verified bytes; "
            "a mapping carrying the plan digest label is not the plan"
        )
    # Re-derive the whole projection from the file the instance names and compare
    # every field. Checking only the token would let a caller edit a target's
    # action class or the correction target on a constructed instance while the
    # token, computed from the untouched file, still matched.
    authoritative = verify_frozen_action_plan(plan.path)
    if plan != authoritative:
        raise ActionPlanProvenanceError(
            "action plan provenance token does not recompute: the supplied projection "
            "differs from the one the frozen bytes produce"
        )
    return plan


# ---------------------------------------------------------------------------
# Owner pre-execution interpretation record.
#
# This artifact is *interpretive authority*, not computational input. It fixes,
# before any result exists, the terminology under which M09 is read and the
# conditional observability under which M12 is read, and it forbids rerunning a
# campaign merely to obtain a measurable M12. Nothing here parses its prose:
# reinterpreting the document at runtime would be exactly the coupling the record
# is meant to prevent, and would let its wording leak into a computed result. The
# verified object therefore carries identity only, never the document text.
# ---------------------------------------------------------------------------

OWNER_PREEXECUTION_INTERPRETATION_RELPATH: Final = (
    "veraxis/cdc-e2e-mission-001/preexecution/"
    "CDC-END-TO-END-MISSION-001-OWNER-PREEXECUTION-INTERPRETATION-v0.1.md"
)
OWNER_PREEXECUTION_INTERPRETATION_SHA256: Final = (
    "8242ccf9612531dc7b3b1d648625a934c4f616d8b8565c61d958a6825d7f2f84"
)
OWNER_PREEXECUTION_INTERPRETATION_BYTES: Final = 9311
OWNER_PREEXECUTION_INTERPRETATION_STATUS: Final = "OWNER_FROZEN_PREEXECUTION_INTERPRETATION"


class OwnerInterpretationProvenanceError(MissionContractError):
    """The owner interpretation record was not verified from its exact bytes."""


@dataclass(frozen=True, slots=True)
class FrozenOwnerInterpretation:
    """Verified identity of the owner pre-execution interpretation record.

    Deliberately holds no document content. The record binds the interpretation
    under which a later result is adjudicated; it must not become an input to the
    computation that produces that result.
    """

    path: Path
    sha256_hex: str
    byte_count: int
    status: str
    role: str = "INTERPRETIVE_AUTHORITY_NOT_COMPUTATIONAL_INPUT"

    def as_record(self) -> dict[str, Any]:
        """Identity-only record; carries no prose."""
        return {
            "sha256": self.sha256_hex,
            "bytes": self.byte_count,
            "status": self.status,
            "role": self.role,
        }


def verify_owner_preexecution_interpretation(path: Path) -> FrozenOwnerInterpretation:
    """Read the exact bytes and establish identity, byte count and frozen status.

    No parser reinterprets the substantive prose. Verifying the bytes, the digest,
    the byte count and the frozen-status marker is sufficient and is deliberately
    all that happens.
    """
    payload = path.read_bytes()
    observed = _file_sha256(payload)
    if observed != OWNER_PREEXECUTION_INTERPRETATION_SHA256:
        raise OwnerInterpretationProvenanceError(
            f"owner interpretation digest is {observed}, "
            f"expected {OWNER_PREEXECUTION_INTERPRETATION_SHA256}"
        )
    if len(payload) != OWNER_PREEXECUTION_INTERPRETATION_BYTES:
        raise OwnerInterpretationProvenanceError(
            f"owner interpretation is {len(payload)} bytes, "
            f"expected {OWNER_PREEXECUTION_INTERPRETATION_BYTES}"
        )
    if OWNER_PREEXECUTION_INTERPRETATION_STATUS.encode() not in payload:
        raise OwnerInterpretationProvenanceError(
            "owner interpretation does not carry the frozen-status marker"
        )
    return FrozenOwnerInterpretation(
        path=path,
        sha256_hex=observed,
        byte_count=len(payload),
        status=OWNER_PREEXECUTION_INTERPRETATION_STATUS,
    )


def require_verified_owner_interpretation(record: object) -> FrozenOwnerInterpretation:
    """Refuse anything that is not a verification of the exact frozen bytes."""
    if not isinstance(record, FrozenOwnerInterpretation):
        raise OwnerInterpretationProvenanceError(
            "the owner interpretation must be a FrozenOwnerInterpretation verified from "
            "bytes; a mapping carrying the record digest label is not the record"
        )
    authoritative = verify_owner_preexecution_interpretation(record.path)
    if record != authoritative:
        raise OwnerInterpretationProvenanceError(
            "owner interpretation identity does not recompute from the bytes on disk"
        )
    return record


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
    "action_plan_sha256",
    "action_plan_provenance_token",
)


class HumanDispositionRequiredError(MissionContractError):
    """Continuation was attempted without a bound human disposition."""


class CandidateBindingError(MissionContractError):
    """A disposition did not bind the candidate observed at Stage 1."""


class PredecessorBindingError(MissionContractError):
    """A correction did not bind, or would mutate, its actual predecessor."""


# Stage-1 authorization tokens. Only the owner-cleared token satisfies Stage 2;
# the unit-test helper cannot mint it, because it is not a parameter of any
# public function.
STAGE_1_AUTHORIZATION_CLEARED: Final = "OWNER_CLEARED_STAGE_1"
STAGE_1_AUTHORIZATION_HELPER: Final = "UNAUTHORIZED_HELPER_NOT_RESULT_BEARING"

STAGE_2_OUTCOME_STATES: Final = (
    "transitioned",
    "refused",
    "unresolved",
    "blocked",
    "non_evaluable",
)

HUMAN_DISPOSITION_REQUIRED_FIELDS: Final = (
    "mission_id",
    "procedure_id",
    "control_id",
    "chain_id",
    "ebawu_id",
    "candidate_digest",
    "warrant_ref",
    "warrant_digest",
    "reviewer_id",
    "reviewer_role",
    "authority_scope_ref",
    "action",
    "observed_at",
    "reason",
    "action_plan_sha256",
    "stage_1_observation_digest",
)

RUN_METADATA_FIELDS: Final = (
    "run_id",
    "trace_id",
    "producer",
    "producer_version",
    "occurred_at",
    "recorded_at",
)

# The institutional state a permitted disposition requests. Derived here so no
# caller can propose an arbitrary destination state.
NEW_STATE_BY_ACTION: Final[dict[str, str]] = {
    "ACCEPT_CANDIDATE": "ACCEPTED_CANDIDATE",
    "QUALIFY": "QUALIFIED",
    "DISMISS": "DISMISSED",
    "REQUEST_EVIDENCE": "EVIDENCE_REQUESTED",
    "ESCALATE": "ESCALATED",
    "DEFER": "DEFERRED",
}

OUTPUT_DEFINITION_REQUIRED_KEYS: Final = frozenset(
    {
        "artifact_id",
        "official_status",
        "content_state",
        "eligibility_determination",
        "required_data_bindings",
        "label_en",
        "label_fr",
    }
)

NONCLAIMS: Final = (
    "not an official CDC record",
    "not CDC validation or deployment",
    "not evidence sufficiency",
    "not legal authority",
    "not a real reviewer identity",
    "not an adjudication against the semantic oracle",
)


class ReviewerStandingError(MissionContractError):
    """The frozen reviewer standing did not authorize the observed disposition."""


class AuthorityCurrentnessError(ReviewerStandingError):
    """A disposition was observed outside the frozen standing's validity interval.

    Distinguished from a general standing failure because currentness is the one
    dimension that can lapse without anything about the record changing. The
    v0.1 authority expired on 2026-08-11T00:00:00Z; a structural test timestamp
    inside that window is legitimate for a test and is not a real observation.
    """


class TransitionDerivationError(MissionContractError):
    """A transition proposal or registry was supplied instead of being derived."""


@dataclass(frozen=True, slots=True)
class Stage1ChainArtifact:
    """The complete Stage-1 artifact set for one chain.

    Stage 2 must compare against the objects actually formed, not against digests
    of objects that no longer exist. Every object is retained here in full.
    """

    chain_id: str
    procedure_id: str
    control_id: str
    ebawu_id: str
    input_digest: str
    evaluation: Mapping[str, Any]
    evaluation_digest: str
    warrant_class: str
    warrant_ref: str
    warrant: Mapping[str, Any]
    warrant_digest: str
    candidate_id: str
    candidate: Mapping[str, Any]
    candidate_digest: str
    outcome_state: str

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record binding every object, not merely its digest."""
        return {
            "chain_id": self.chain_id,
            "procedure_id": self.procedure_id,
            "control_id": self.control_id,
            "ebawu_id": self.ebawu_id,
            "input_digest": self.input_digest,
            "evaluation": dict(self.evaluation),
            "evaluation_digest": self.evaluation_digest,
            "warrant_class": self.warrant_class,
            "warrant_ref": self.warrant_ref,
            "warrant": dict(self.warrant),
            "warrant_digest": self.warrant_digest,
            "candidate_id": self.candidate_id,
            "candidate": dict(self.candidate),
            "candidate_digest": self.candidate_digest,
            "outcome_state": self.outcome_state,
        }


@dataclass(frozen=True, slots=True)
class Stage1ChainObservation:
    """One chain's Stage-1 outcome. Non-adjudicating."""

    chain_id: str
    outcome_state: str
    candidate_digest: str | None
    input_digest: str
    detail: str
    artifact: Stage1ChainArtifact | None = None

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record."""
        return {
            "chain_id": self.chain_id,
            "outcome_state": self.outcome_state,
            "candidate_digest": self.candidate_digest,
            "input_digest": self.input_digest,
            "detail": self.detail,
            "artifact": None if self.artifact is None else self.artifact.as_record(),
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
    authorization: str = STAGE_1_AUTHORIZATION_HELPER
    owner_interpretation_sha256: str = "NOT_BOUND"
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
            "authorization": self.authorization,
            "owner_interpretation_sha256": self.owner_interpretation_sha256,
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
        """The frozen Stage-1 observation digest, binding every formed object."""
        return str(self.as_record()["stage_1_observation_digest"])

    def candidate_digests(self) -> dict[str, str]:
        """Candidate digests actually formed, by chain."""
        return {
            chain.chain_id: chain.candidate_digest
            for chain in self.chains
            if chain.candidate_digest is not None
        }

    def artifacts(self) -> dict[str, Stage1ChainArtifact]:
        """Complete Stage-1 artifacts actually formed, by chain."""
        return {
            chain.chain_id: chain.artifact for chain in self.chains if chain.artifact is not None
        }

    def is_owner_cleared(self) -> bool:
        """True only for an observation produced under an exact owner clearance."""
        return self.authorization == STAGE_1_AUTHORIZATION_CLEARED


def _form_stage_1(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    *,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
    authorization: str,
    owner_interpretation_sha256: str = "NOT_BOUND",
) -> Stage1Observation:
    """Form candidates across all nine chains, then stop.

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
            control = _require_mapping(chain.execution_input["admitted_control"], "control")
            evidence = _require_mapping(chain.execution_input["evidence_bundle"], "evidence")
            admission = _require_mapping(chain.execution_input["admission_record"], "admission")
            procedure_id = str(control["procedure_id"])
            candidate_id = f"CAND-{procedure_id}-{chain.control_id}"
            candidate = {
                "candidate_id": candidate_id,
                "chain_id": chain.chain_id,
                "status": "CANDIDATE_NOT_OFFICIAL",
                "control_id": chain.control_id,
                "admission_record_ref": str(admission["admission_id"]),
                "evidence_bundle_ref": str(evidence["evidence_bundle_id"]),
                "evaluation": evaluation,
                "warrant_class": warrant_class,
                "warrant": warrant,
                "input_digest": chain.input_digest(),
            }
            artifact = Stage1ChainArtifact(
                chain_id=chain.chain_id,
                procedure_id=procedure_id,
                control_id=chain.control_id,
                ebawu_id=chain.ebawu_ref,
                input_digest=chain.input_digest(),
                evaluation=evaluation,
                evaluation_digest=sha256(evaluation),
                warrant_class=warrant_class,
                warrant_ref=str(warrant["warrant_id"]),
                warrant=warrant,
                warrant_digest=sha256(warrant),
                candidate_id=candidate_id,
                candidate=candidate,
                candidate_digest=sha256(candidate),
                outcome_state="completed",
            )
            tally["completed"] += 1
            observations.append(
                Stage1ChainObservation(
                    chain_id=chain.chain_id,
                    outcome_state="completed",
                    candidate_digest=artifact.candidate_digest,
                    input_digest=chain.input_digest(),
                    detail="candidate formed; no transition and no draft eligibility",
                    artifact=artifact,
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
        authorization=authorization,
        owner_interpretation_sha256=owner_interpretation_sha256,
    )


def execute_authorized_stage_1(
    projection: object,
    frozen: FrozenMissionInput,
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    *,
    owner_interpretation: object,
    evaluator: EvaluationFunction,
    warrant_builder: WarrantFunction,
) -> Stage1Observation:
    """The single authorized route to Stage-1 candidate formation.

    Refuses unless the source is a :class:`MissionProjection` derived from
    verified frozen bytes *and* every external binding matches observation,
    including the human action-plan digest and the owner pre-execution
    interpretation record.

    The interpretation record is verified from its bytes here, before the
    clearance digest is compared against it, so authorization binds a verified
    object rather than a caller-supplied label. Its identity is recorded in the
    Stage-1 observation; its prose is never read into the computation.
    """
    interpretation = require_verified_owner_interpretation(owner_interpretation)
    verified = require_projected_source(projection, frozen)
    require_result_clearance(
        clearance, runtime, {"mission_package_sha256": verified.package_sha256}
    )
    if clearance.owner_preexecution_interpretation_sha256 != interpretation.sha256_hex:
        raise ResultBearingMissionBlockedError(
            "clearance and verified owner interpretation disagree"
        )
    if verified.package_sha256 != frozen.package_sha256:
        raise ResultBearingMissionBlockedError("projection and verified bytes disagree")
    return _form_stage_1(
        verified,
        frozen,
        evaluator=evaluator,
        warrant_builder=warrant_builder,
        authorization=STAGE_1_AUTHORIZATION_CLEARED,
        owner_interpretation_sha256=interpretation.sha256_hex,
    )


def validate_frozen_reviewer_standing_exact(
    authority: Mapping[str, Any],
    *,
    mission_id: str,
    reviewer_id: str,
    reviewer_role: str,
    authority_scope_ref: str,
    action_class: str,
    disposition: str,
    observed_at: str,
) -> dict[str, Any]:
    """Stricter successor to :func:`validate_frozen_reviewer_standing`.

    Requires exact correspondence of reviewer identity, reviewer role, mission,
    scope, permitted action, validity and revocation against the frozen
    ``03-AUTHORITY/test-reviewer.json`` object. There is no parameter through
    which a caller can supply a flat standing substitute.
    """
    identity = _require_mapping(authority.get("identity"), "standing.identity")
    role = _require_mapping(authority.get("role"), "standing.role")
    permitted = _require_mapping(authority.get("permitted_action"), "standing.permitted_action")
    validity = _require_mapping(authority.get("validity"), "standing.validity")
    revocation = _require_mapping(authority.get("revocation"), "standing.revocation")
    permitted_dispositions = _require_sequence(
        permitted.get("permitted_dispositions"), "standing.permitted_dispositions"
    )
    # Currentness is checked first so a lapsed interval is attributable as such
    # rather than surfacing as a generic "absent, expired, or unauthorized".
    effective_from = str(validity.get("effective_from"))
    effective_until = str(validity.get("effective_until"))
    if not effective_from <= observed_at <= effective_until:
        raise AuthorityCurrentnessError(
            f"frozen reviewer standing is not current: observed_at {observed_at!r} is outside "
            f"[{effective_from}, {effective_until}]"
        )
    if revocation.get("status") != "NOT_REVOKED":
        raise ReviewerStandingError(
            f"frozen reviewer standing is revoked or unresolved: {revocation.get('status')!r}"
        )
    validate_frozen_reviewer_standing(
        authority, mission_id=mission_id, action=action_class, observed_at=observed_at
    )
    mismatches = [
        name
        for name, matched in (
            ("reviewer_id", identity.get("reviewer_id") == reviewer_id),
            ("reviewer_role", role.get("role_id") == reviewer_role),
            ("mission", authority.get("mission") == mission_id),
            ("authority_scope_ref", authority.get("authority_scope_ref") == authority_scope_ref),
            ("scope_limited_to", permitted.get("scope_limited_to") == authority_scope_ref),
            ("permitted_action", permitted.get("action") == action_class),
            ("permitted_disposition", disposition in permitted_dispositions),
            (
                "validity",
                str(validity.get("effective_from"))
                <= observed_at
                <= str(validity.get("effective_until")),
            ),
            ("revocation", revocation.get("status") == "NOT_REVOKED"),
        )
        if not matched
    ]
    if mismatches:
        raise ReviewerStandingError(f"frozen reviewer standing does not authorize: {mismatches}")
    return {
        "standing_source": "03-AUTHORITY/test-reviewer.json",
        "standing_digest": sha256(authority),
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "authority_scope_ref": authority_scope_ref,
        "action_class": action_class,
        "disposition": disposition,
        "observed_at": observed_at,
        "revocation_status": revocation.get("status"),
        "caller_supplied_standing_accepted": False,
    }


def bind_human_disposition(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    projection: MissionProjection,
    action_plan: object,
    observed_now: str | None = None,
) -> dict[str, Any]:
    """Accept a disposition only if it is the preregistered stimulus for this chain.

    Three independent gates, deliberately ordered so a refusal is attributable:

    1. the disposition must bind the artifacts Stage 1 actually produced;
    2. the action must equal the class the frozen action plan preregistered for
       this chain, recovered from the plan's bytes;
    3. the frozen reviewer standing must permit it.

    Gate 2 sits before gate 3 because the standing is an authority *ceiling*, not
    a licence to substitute stimuli. ``QUALIFY`` on a chain whose plan says
    ``ACCEPT_CANDIDATE`` is inside the reviewer's authority and still refused —
    as an action-plan mismatch, not an authority failure.
    """
    plan = require_verified_action_plan(action_plan)
    if observed_now is not None and disposition.get("observed_at") != observed_now:
        raise AuthorityCurrentnessError(
            f"a real disposition must state the observed clock: observed_now is "
            f"{observed_now!r}, disposition claims {disposition.get('observed_at')!r}"
        )
    missing = sorted(set(HUMAN_DISPOSITION_REQUIRED_FIELDS) - disposition.keys())
    if missing:
        raise MissionContractError(f"human disposition missing required fields: {missing}")
    chain_id = str(disposition["chain_id"])
    artifact = stage_1.artifacts().get(chain_id)
    if artifact is None:
        raise HumanDispositionRequiredError(
            f"no Stage-1 candidate exists for {chain_id}; disposition cannot bind"
        )
    observed = {
        "mission_id": stage_1.mission_id,
        "procedure_id": artifact.procedure_id,
        "control_id": artifact.control_id,
        "ebawu_id": artifact.ebawu_id,
        "candidate_digest": artifact.candidate_digest,
        "warrant_ref": artifact.warrant_ref,
        "warrant_digest": artifact.warrant_digest,
        "stage_1_observation_digest": stage_1.digest(),
    }
    divergent = sorted(name for name, value in observed.items() if disposition.get(name) != value)
    if divergent:
        raise CandidateBindingError(
            f"disposition for {chain_id} does not bind the observed Stage-1 artifacts: {divergent}"
        )
    action = str(disposition["action"])
    if action not in NEW_STATE_BY_ACTION:
        raise MissionContractError(f"disposition action is not permitted: {action}")
    if disposition.get("action_plan_sha256") != plan.sha256_hex:
        raise ActionPlanBindingError("disposition does not carry the verified action-plan digest")
    target = plan.target_for(artifact.procedure_id, artifact.control_id)
    if action != target.preregistered_action_class:
        raise ActionPlanBindingError(
            f"action-plan mismatch on {target.target_id}: the frozen plan preregisters "
            f"{target.preregistered_action_class!r} for {artifact.procedure_id} x "
            f"{artifact.control_id}, submitted {action!r}. The reviewer's standing is an "
            "authority ceiling and does not license substituting another permitted "
            "disposition for the preregistered stimulus."
        )
    standing = validate_frozen_reviewer_standing_exact(
        projection.authority,
        mission_id=stage_1.mission_id,
        reviewer_id=str(disposition["reviewer_id"]),
        reviewer_role=str(disposition["reviewer_role"]),
        authority_scope_ref=str(disposition["authority_scope_ref"]),
        action_class=str(
            _require_mapping(projection.authority["permitted_action"], "permitted_action")["action"]
        ),
        disposition=action,
        observed_at=str(disposition["observed_at"]),
    )
    record = {
        **observed,
        "chain_id": chain_id,
        "action": action,
        "reviewer_id": str(disposition["reviewer_id"]),
        "reviewer_role": str(disposition["reviewer_role"]),
        "authority_scope_ref": str(disposition["authority_scope_ref"]),
        "observed_at": str(disposition["observed_at"]),
        "reason": str(disposition["reason"]),
        "action_plan_sha256": plan.sha256_hex,
        "action_plan_provenance_token": plan.provenance_token,
        "action_plan_target_id": target.target_id,
        "preregistered_action_class": target.preregistered_action_class,
        "runtime_binding_requirement": target.runtime_binding_requirement,
        "frozen_standing": standing,
        "status": "HUMAN_TEST_DISPOSITION_BOUND",
    }
    record["disposition_artifact_digest"] = sha256(record)
    return record


def require_human_disposition(stage_1: Stage1Observation, dispositions: Mapping[str, Any]) -> None:
    """Hold at Stage 1 unless a disposition exists for every formed candidate."""
    formed = set(stage_1.candidate_digests())
    supplied = set(dispositions)
    missing = sorted(formed - supplied)
    if missing:
        raise HumanDispositionRequiredError(
            f"HOLD: Stage-1 complete, human disposition not supplied for {missing}"
        )


def require_stage_2_clearance(
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    *,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    action_plan: object,
    stage_2_bindings: Mapping[str, Any],
) -> None:
    """Stage-2 continuation compares exact artifacts, never mere non-emptiness.

    The controlling correction-stimulus digest is computed from the verified plan
    object, so an arbitrary caller mapping cannot define what Stage 2 is bound to.
    """
    plan = require_verified_action_plan(action_plan)
    require_projected_source(projection, frozen)
    require_result_clearance(
        clearance, runtime, {"mission_package_sha256": projection.package_sha256}
    )
    if not stage_1.is_owner_cleared():
        raise ResultBearingMissionBlockedError(
            f"Stage-1 observation was not produced under owner clearance: {stage_1.authorization}"
        )
    missing = sorted(name for name in STAGE_2_BINDING_FIELDS if not stage_2_bindings.get(name))
    if missing:
        raise ResultBearingMissionBlockedError(f"missing stage-2 bindings: {missing}")
    observed_dispositions = sorted(sha256(dict(record)) for record in dispositions.values())
    supplied_dispositions = stage_2_bindings.get("human_disposition_artifact_digests")
    mismatches = [
        name
        for name, matched in (
            (
                "stage_1_observation_digest",
                stage_2_bindings.get("stage_1_observation_digest") == stage_1.digest(),
            ),
            (
                "human_disposition_artifact_digests",
                isinstance(supplied_dispositions, list | tuple)
                and sorted(str(value) for value in supplied_dispositions) == observed_dispositions,
            ),
            (
                "action_plan_sha256",
                stage_2_bindings.get("action_plan_sha256") == plan.sha256_hex,
            ),
            (
                "action_plan_provenance_token",
                stage_2_bindings.get("action_plan_provenance_token") == plan.provenance_token,
            ),
            (
                "correction_stimulus_digest",
                stage_2_bindings.get("correction_stimulus_digest") == plan.correction.digest(),
            ),
        )
        if not matched
    ]
    if mismatches:
        raise ResultBearingMissionBlockedError(f"stage-2 artifact binding mismatch: {mismatches}")


def derive_transition_registry(
    projection: MissionProjection, artifact: Stage1ChainArtifact
) -> dict[str, Any]:
    """Build the immutable Slice-001 registry from the actual objects.

    Nothing here is caller-supplied. The registry is a snapshot of the frozen
    chain inputs plus the artifacts Stage 1 actually formed.
    """
    chain = projection.chain(artifact.chain_id)
    control = _require_mapping(chain.execution_input["admitted_control"], "control")
    evidence = _require_mapping(chain.execution_input["evidence_bundle"], "evidence")
    admission = _require_mapping(chain.execution_input["admission_record"], "admission")
    reviewer_id = str(_require_mapping(projection.authority["identity"], "identity")["reviewer_id"])
    warrant_category = (
        "warrants" if artifact.warrant_class == "ZTL_WARRANT" else "fallback_warrants"
    )
    return {
        "candidates": {artifact.candidate_id: artifact.candidate},
        "ebawus": {
            artifact.ebawu_id: {
                "ebawu_id": artifact.ebawu_id,
                "procedure_id": artifact.procedure_id,
                "control_id": artifact.control_id,
            }
        },
        "controls": {str(control["control_id"]): control},
        "admissions": {str(admission["admission_id"]): admission},
        "evidence": {str(evidence["evidence_bundle_id"]): evidence},
        "evaluations": {str(artifact.evaluation["evaluation_id"]): artifact.evaluation},
        "reviewers": {reviewer_id: projection.authority},
        warrant_category: {artifact.warrant_ref: artifact.warrant},
        "states": {artifact.ebawu_id: chain.execution_input["prior_institutional_state"]},
        "stale_candidate_ids": (),
    }


def derive_transition_proposal(
    projection: MissionProjection,
    artifact: Stage1ChainArtifact,
    disposition: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive the Slice-001 proposal deterministically. Never accepted from a caller."""
    chain = projection.chain(artifact.chain_id)
    control = _require_mapping(chain.execution_input["admitted_control"], "control")
    evidence = _require_mapping(chain.execution_input["evidence_bundle"], "evidence")
    admission = _require_mapping(chain.execution_input["admission_record"], "admission")
    action = str(disposition["action"])
    proposal: dict[str, Any] = {
        "mission_id": projection.mission_id,
        "assurance_mode": ASSURANCE_MODE,
        "authority_scope_ref": str(projection.authority["authority_scope_ref"]),
        "requested_disposition": action,
        "candidate_id": artifact.candidate_id,
        "candidate_digest": digest(artifact.candidate),
        "ebawu_id": artifact.ebawu_id,
        "OIC_control_id": str(control["control_id"]),
        "OIC_control_digest": digest(control),
        "admission_record_ref": str(admission["admission_id"]),
        "evidence_bundle_ref": str(evidence["evidence_bundle_id"]),
        "evidence_bundle_digest": digest(evidence),
        "deterministic_execution_result_ref": str(artifact.evaluation["evaluation_id"]),
        "reviewer_id": str(disposition["reviewer_id"]),
        "reviewer_role_assertion": str(disposition["reviewer_role"]),
        "prior_institutional_state": chain.execution_input["prior_institutional_state"],
        "requested_new_institutional_state": NEW_STATE_BY_ACTION[action],
        "parent_event_id": None,
    }
    if artifact.warrant_class == "ZTL_WARRANT":
        proposal["ZTL_warrant_ref"] = artifact.warrant_ref
        proposal["ZTL_warrant_digest"] = digest(artifact.warrant)
    else:
        proposal["fallback_warrant_ref"] = artifact.warrant_ref
        proposal["fallback_warrant_digest"] = digest(artifact.warrant)
    # The frozen control declares ``on_unknown: ESCALATE``. An unknown or CANNOT
    # condition is a property of the evaluation actually produced, so it is read
    # from the evaluation object rather than accepted from a caller.
    condition_state = artifact.evaluation.get("required_condition_state")
    if condition_state is not None:
        proposal["required_condition_state"] = str(condition_state)
    if artifact.evaluation.get("cannot_condition") is True:
        proposal["cannot_condition"] = True
    return proposal


def _event_metadata(
    run_metadata: Mapping[str, Any], artifact: Stage1ChainArtifact
) -> dict[str, Any]:
    missing = sorted(set(RUN_METADATA_FIELDS) - run_metadata.keys())
    if missing:
        raise MissionContractError(f"run metadata incomplete: {missing}")
    return {
        **{name: run_metadata[name] for name in RUN_METADATA_FIELDS},
        "event_id": f"CDC-E2E-EVT-{artifact.chain_id}",
        "aggregate_version": 1,
    }


def render_drafts(
    output_definitions: Sequence[Mapping[str, Any]],
    *,
    provenance: Mapping[str, Any],
    french_packet: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Render one draft per frozen output definition.

    The authoritative output source is the five frozen ``04-OUTPUTS/`` objects.
    A hard-coded kind vocabulary cannot substitute: every definition must be a
    frozen object carrying the exact required keys, or this refuses.
    """
    if len(output_definitions) != 5:
        raise MissionContractError(
            f"five frozen output definitions are required, received {len(output_definitions)}"
        )
    french_state = str(french_packet.get("french_path_state"))
    absences = list(
        _require_sequence(
            french_packet.get("substantive_french_support_absent_at", []), "french absences"
        )
    )
    drafts: list[Mapping[str, Any]] = []
    for raw in output_definitions:
        if not isinstance(raw, Mapping):
            raise MissionContractError(
                "output definition is not a frozen object; a hard-coded draft kind "
                "cannot substitute for 04-OUTPUTS/"
            )
        missing = sorted(OUTPUT_DEFINITION_REQUIRED_KEYS - raw.keys())
        if missing:
            raise MissionContractError(f"frozen output definition missing keys: {missing}")
        if raw["official_status"] != "NOT_AUTHORIZED_AS_OFFICIAL":
            raise MissionContractError("an output definition claims official status")
        required = [str(name) for name in _require_sequence(raw["required_data_bindings"], "req")]
        satisfied = sorted(name for name in required if provenance.get(name))
        absent = sorted(name for name in required if not provenance.get(name))
        drafts.append(
            {
                "draft_id": f"{MISSION_ID}/{raw['artifact_id']}",
                "output_definition_artifact_id": str(raw["artifact_id"]),
                "label_en": raw["label_en"],
                "label_fr": raw["label_fr"],
                "official_status": raw["official_status"],
                "content_state_rule": raw["content_state"],
                "eligibility_determination": raw["eligibility_determination"],
                "eligibility_state": (
                    "ELIGIBLE_AS_SYNTHETIC_DRAFT"
                    if not absent
                    else "INELIGIBLE_PROVENANCE_INCOMPLETE"
                ),
                "provenance_requirements": required,
                "provenance_satisfied": satisfied,
                "provenance_absent": absent,
                "provenance": dict(provenance),
                "french_path_state": french_state,
                "french_render_capability": french_state,
                "french_named_absences": absences,
                "french_capability_synthesized": False,
                "status": "SYNTHETIC_DRAFT_NOT_OFFICIAL",
                "official_handoff": OFFICIAL_CDC_RECORD_CREATION,
                "nonclaims": list(NONCLAIMS),
            }
        )
    return tuple(drafts)


@dataclass(frozen=True, slots=True)
class Stage2ChainOutcome:
    """One chain's Stage-2 outcome. Non-adjudicating; a refusal is a result."""

    chain_id: str
    outcome_state: str
    decision: str | None
    reason_code: str | None
    epistemic_state: str | None
    transition_event: Mapping[str, Any] | None
    detail: str

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record."""
        return {
            "chain_id": self.chain_id,
            "outcome_state": self.outcome_state,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "epistemic_state": self.epistemic_state,
            "transition_event": (
                None if self.transition_event is None else dict(self.transition_event)
            ),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class Stage2Result:
    """Immutable Stage-2 result. Never an official CDC record."""

    mission_id: str
    package_sha256: str
    stage_1_observation_digest: str
    outcomes: tuple[Stage2ChainOutcome, ...]
    accounting: Mapping[str, int]
    drafts: tuple[Mapping[str, Any], ...]
    correction: Mapping[str, Any]
    official_handoff: str = "PROHIBITED"

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record."""
        body = {
            "mission_id": self.mission_id,
            "package_sha256": self.package_sha256,
            "stage_1_observation_digest": self.stage_1_observation_digest,
            "outcomes": [outcome.as_record() for outcome in self.outcomes],
            "accounting": dict(self.accounting),
            "drafts": [dict(draft) for draft in self.drafts],
            "correction": dict(self.correction),
            "official_handoff": self.official_handoff,
        }
        body["stage_2_result_digest"] = sha256(body)
        return body

    def transition_events(self) -> tuple[Mapping[str, Any], ...]:
        """Events actually emitted; a non-ALLOW gate result emits nothing."""
        return tuple(
            outcome.transition_event
            for outcome in self.outcomes
            if outcome.transition_event is not None
        )


def integrate_correction(
    projection: MissionProjection,
    stage_1: Stage1Observation,
    outcomes: Sequence[Stage2ChainOutcome],
    action_plan: object,
    correction: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Execute the correction only after an eligible completed predecessor exists.

    The target and its precondition come from the verified frozen action-plan
    bytes; there is no parameter through which a caller can choose a different
    correction target. Only the runtime correction *object* is supplied, and only
    after the predecessor exists, because its digest cannot be known earlier.

    If the precondition never occurred, this records an explicit absence. It does
    not manufacture a correction execution.
    """
    plan = require_verified_action_plan(action_plan)
    target_ebawu = plan.correction.predecessor_ebawu_ref
    stimulus_id = plan.correction.correction_stimulus_id
    artifact = next(
        (item for item in stage_1.artifacts().values() if item.ebawu_id == target_ebawu), None
    )
    outcome = next(
        (item for item in outcomes if artifact is not None and item.chain_id == artifact.chain_id),
        None,
    )
    eligible = (
        artifact is not None
        and outcome is not None
        and outcome.outcome_state == "transitioned"
        and outcome.transition_event is not None
    )
    if not eligible or artifact is None or outcome is None or outcome.transition_event is None:
        return {
            "correction_stimulus_id": stimulus_id,
            "correction_executed": False,
            "m12_state": "unavailable_incomplete",
            "predecessor_ebawu_ref": target_ebawu,
            "eligible_completed_predecessor": False,
            "correction_target_id": plan.correction.target_id,
            "correction_target_source": "FROZEN_ACTION_PLAN_BYTES",
            "precondition": plan.correction.precondition,
            "detail": (
                "the preregistered correction target has no eligible completed "
                "predecessor; no correction was manufactured"
            ),
        }
    if correction is None:
        return {
            "correction_stimulus_id": stimulus_id,
            "correction_executed": False,
            "m12_state": "unavailable_incomplete",
            "predecessor_ebawu_ref": target_ebawu,
            "eligible_completed_predecessor": True,
            "correction_target_id": plan.correction.target_id,
            "correction_target_source": "FROZEN_ACTION_PLAN_BYTES",
            "precondition": plan.correction.precondition,
            "detail": "an eligible predecessor exists but no correction object was supplied",
        }
    del projection
    missing = sorted(set(plan.correction.required_correction_fields) - correction.keys())
    frozen_side = {"supersedes", "superseded_by", "prior_state", "reliance_impact_refs"}
    missing = sorted(set(missing) - frozen_side)
    if missing:
        raise MissionContractError(
            f"correction object lacks fields the frozen plan requires: {missing}"
        )
    predecessor = {
        "ebawu_id": artifact.ebawu_id,
        "state": str(outcome.transition_event["new_state"]),
        "candidate_id": artifact.candidate_id,
        "candidate_digest": artifact.candidate_digest,
    }
    derived = sha256(predecessor)
    supplied = correction.get("predecessor_digest")
    if supplied is not None and supplied != derived:
        raise PredecessorBindingError(
            f"correction binds predecessor {supplied!r}, actual {derived!r}"
        )
    record = bind_correction(predecessor, {**correction, "predecessor_digest": derived})
    return {
        **record,
        "correction_stimulus_id": stimulus_id,
        "correction_executed": True,
        "m12_state": "executed",
        "predecessor_ebawu_ref": target_ebawu,
        "eligible_completed_predecessor": True,
        "correction_target_id": plan.correction.target_id,
        "correction_target_source": "FROZEN_ACTION_PLAN_BYTES",
        "precondition": plan.correction.precondition,
        "predecessor_mutation_prohibited": plan.correction.predecessor_mutation_prohibited,
        "predecessor_object_preserved": predecessor,
        "detail": "correction executed through frozen Slice-001 make_successor semantics",
    }


def execute_authorized_stage_2(
    projection: object,
    frozen: FrozenMissionInput,
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    *,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    action_plan: object,
    correction: Mapping[str, Any] | None,
    run_metadata: Mapping[str, Any],
    stage_2_bindings: Mapping[str, Any],
) -> Stage2Result:
    """The single authorized route to transition evaluation and rendering.

    No caller-supplied transition proposal, registry or correction target can
    enter here. The first two are derived from the actual Stage-1 artifacts and
    the frozen chain inputs; the third comes from the verified action-plan bytes.
    """
    plan = require_verified_action_plan(action_plan)
    verified = require_projected_source(projection, frozen)
    require_stage_2_clearance(
        clearance,
        runtime,
        verified,
        frozen,
        stage_1=stage_1,
        dispositions=dispositions,
        action_plan=plan,
        stage_2_bindings=stage_2_bindings,
    )
    forbidden = {"transition_proposal", "transition_registry", "registry", "proposal"}
    for chain_id, record in dispositions.items():
        intruding = sorted(forbidden & record.keys())
        if intruding:
            raise TransitionDerivationError(
                f"disposition {chain_id} carries a caller-supplied {intruding}; "
                "the proposal and registry are derived, never accepted"
            )
    artifacts = stage_1.artifacts()
    tally = dict.fromkeys(STAGE_2_OUTCOME_STATES, 0)
    outcomes: list[Stage2ChainOutcome] = []
    for chain in verified.chains:
        artifact = artifacts.get(chain.chain_id)
        if artifact is None:
            tally["non_evaluable"] += 1
            outcomes.append(
                Stage2ChainOutcome(
                    chain_id=chain.chain_id,
                    outcome_state="non_evaluable",
                    decision=None,
                    reason_code=None,
                    epistemic_state=None,
                    transition_event=None,
                    detail="no Stage-1 candidate was formed for this chain",
                )
            )
            continue
        disposition = dispositions.get(chain.chain_id)
        if disposition is None:
            tally["blocked"] += 1
            outcomes.append(
                Stage2ChainOutcome(
                    chain_id=chain.chain_id,
                    outcome_state="blocked",
                    decision=None,
                    reason_code=None,
                    epistemic_state=None,
                    transition_event=None,
                    detail="candidate formed but no bound human disposition exists",
                )
            )
            continue
        registry = derive_transition_registry(verified, artifact)
        proposal = derive_transition_proposal(verified, artifact, disposition)
        decision: GateDecision = evaluate_test_transition(proposal, registry)
        if decision.decision == "ALLOW":
            event = emit_transition_event(
                proposal, decision, event_metadata=_event_metadata(run_metadata, artifact)
            )
            state = "transitioned"
            detail = "transition event emitted after ALLOW"
        else:
            event = None
            state = "refused" if decision.decision == "DENY" else "unresolved"
            detail = f"gate returned {decision.decision}; no transition event was fabricated"
        tally[state] += 1
        outcomes.append(
            Stage2ChainOutcome(
                chain_id=chain.chain_id,
                outcome_state=state,
                decision=decision.decision,
                reason_code=decision.reason_code,
                epistemic_state=decision.epistemic_state,
                transition_event=event,
                detail=detail,
            )
        )
    total = sum(tally.values())
    if total != EXPECTED_CHAIN_COUNT:
        raise MissionContractError(f"denominator lost: {total} of 9 accounted")
    correction_record = integrate_correction(verified, stage_1, outcomes, plan, correction)
    provenance = _draft_provenance(verified, stage_1, outcomes, correction_record)
    drafts = render_drafts(
        verified.output_definitions, provenance=provenance, french_packet=verified.french_packet
    )
    return Stage2Result(
        mission_id=verified.mission_id,
        package_sha256=verified.package_sha256,
        stage_1_observation_digest=stage_1.digest(),
        outcomes=tuple(outcomes),
        accounting=tally,
        drafts=drafts,
        correction=correction_record,
    )


def _new_state(outcome: Stage2ChainOutcome) -> str | None:
    """The institutional state actually reached, or None when nothing transitioned."""
    if outcome.transition_event is None:
        return None
    return str(outcome.transition_event["new_state"])


def _draft_provenance(
    projection: MissionProjection,
    stage_1: Stage1Observation,
    outcomes: Sequence[Stage2ChainOutcome],
    correction_record: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = stage_1.artifacts()
    by_chain = {outcome.chain_id: outcome for outcome in outcomes}
    return {
        "mission_id": projection.mission_id,
        "mission_scope": projection.authority.get("authority_scope_ref"),
        "procedure_ids": sorted({chain.procedure_id for chain in projection.chains}),
        "control_ids": sorted({chain.control_id for chain in projection.chains}),
        "candidate_refs": sorted(item.candidate_id for item in artifacts.values()),
        "candidate_digests": sorted(item.candidate_digest for item in artifacts.values()),
        "evidence_bundle_refs": sorted(
            str(chain.execution_input["evidence_bundle"]["evidence_bundle_id"])
            for chain in projection.chains
        ),
        "evidence_bundle_digests": sorted(
            sha256(chain.execution_input["evidence_bundle"]) for chain in projection.chains
        ),
        "admission_refs": sorted(
            str(chain.execution_input["admission_record"]["admission_id"])
            for chain in projection.chains
        ),
        "source_anchor_refs": sorted(
            str(anchor["anchor_id"])
            for chain in projection.chains
            for anchor in _require_sequence(chain.execution_input["source_anchors"], "anchors")
            if isinstance(anchor, Mapping)
        ),
        "warrant_refs": sorted(item.warrant_ref for item in artifacts.values()),
        "warrant_digests": sorted(item.warrant_digest for item in artifacts.values()),
        "deterministic_evaluation_refs": sorted(
            str(item.evaluation["evaluation_id"]) for item in artifacts.values()
        ),
        "reviewer_id": _require_mapping(projection.authority["identity"], "identity").get(
            "reviewer_id"
        ),
        "reviewer_role": _require_mapping(projection.authority["role"], "role").get("role_id"),
        "authority_scope_ref": projection.authority.get("authority_scope_ref"),
        "disposition_per_candidate": {
            chain_id: by_chain[chain_id].outcome_state
            for chain_id in sorted(artifacts)
            if chain_id in by_chain
        },
        "institutional_state_per_ebawu": {
            artifacts[chain_id].ebawu_id: _new_state(by_chain[chain_id])
            for chain_id in sorted(artifacts)
            if chain_id in by_chain
        },
        "correction_refs": (
            [correction_record.get("successor_id")]
            if correction_record.get("correction_executed")
            else []
        ),
        "limitations": list(
            _require_sequence(
                projection.french_packet.get("substantive_french_support_absent_at", []),
                "french absences",
            )
        ),
        "nonclaims": list(NONCLAIMS),
    }


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


def observation_producer(
    projection: MissionProjection,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation | None = None,
    stage_2: Stage2Result | None = None,
) -> dict[str, Any]:
    """Produce M01-M12 result-aware, non-adjudicating observations.

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
            "evaluations_formed_at_runtime": (0 if stage_1 is None else len(stage_1.artifacts())),
        },
        "M06_ZTL_WARRANT_VS_FALLBACK_SEPARATION": {
            "precomputed_warrant_in_execution_input": any(
                "warrant_artifact" in c.execution_input for c in projection.chains
            ),
            "governed_warrant_classes": ["ZTL_WARRANT", "FALLBACK_WARRANT"],
            "warrant_classes_observed": (
                "NOT_YET_OBSERVED"
                if stage_1 is None
                else sorted({item.warrant_class for item in stage_1.artifacts().values()})
            ),
        },
        "M07_CANDIDATE_FINDING_NON_OFFICIALITY": {
            "output_official_status": sorted(
                {str(o.get("official_status")) for o in projection.output_definitions}
            ),
            "official_cdc_record_creation": OFFICIAL_CDC_RECORD_CREATION,
            "draft_official_status": (
                "NOT_YET_OBSERVED"
                if stage_2 is None
                else sorted({str(d["official_status"]) for d in stage_2.drafts})
            ),
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
            "standing_source": "03-AUTHORITY/test-reviewer.json",
            "caller_supplied_standing_accepted": False,
        },
        "M09_HUMAN_DISPOSITION_BOUNDARY": {
            "stage_1_terminal_state": STAGE_1_TERMINAL_STATE,
            "human_disposition": (
                stage_1.human_disposition if stage_1 is not None else "NOT_YET_SUPPLIED"
            ),
            "institutional_transition": (
                stage_1.institutional_transition if stage_1 is not None else "NONE"
            ),
            "stage_1_authorization": (
                "NOT_YET_OBSERVED" if stage_1 is None else stage_1.authorization
            ),
        },
        "M10_VEIP_TRANSITION_AFTER_VALID_DISPOSITION": _m10(stage_2),
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
            "drafts_rendered": 0 if stage_2 is None else len(stage_2.drafts),
            "drafts_traced_to_frozen_definitions": (
                "NOT_YET_OBSERVED"
                if stage_2 is None
                else sorted(str(d["output_definition_artifact_id"]) for d in stage_2.drafts)
            ),
            "french_capability_synthesized": (
                "NOT_YET_OBSERVED"
                if stage_2 is None
                else any(bool(d["french_capability_synthesized"]) for d in stage_2.drafts)
            ),
        },
        "M12_CORRECTION_AND_PREDECESSOR_PRESERVATION": _m12(stage_2),
    }
    missing = sorted(set(OBSERVATION_IDS) - observations.keys())
    if missing:
        raise MissionContractError(f"observation producer coverage incomplete: {missing}")
    return {
        "coverage": f"{len(observations)}/{len(OBSERVATION_IDS)}",
        "observations": observations,
        "member_consumption": ledger,
        "historical_governance_field": projection.historical_governance_field,
        "denominator_accounting": (
            "NOT_YET_OBSERVED" if stage_2 is None else dict(stage_2.accounting)
        ),
        "adjudication_present": False,
    }


def _m10(stage_2: Stage2Result | None) -> dict[str, Any]:
    """M10 reports the transition facts actually observed, never a literal false."""
    if stage_2 is None:
        return {
            "requires_bound_disposition": True,
            "stage_2_observed": False,
            "transition_events_emitted": "NOT_YET_OBSERVED",
            "outcome_states": "NOT_YET_OBSERVED",
        }
    return {
        "requires_bound_disposition": True,
        "stage_2_observed": True,
        "transition_events_emitted": len(stage_2.transition_events()),
        "outcome_states": dict(stage_2.accounting),
        "per_chain": {
            outcome.chain_id: {
                "outcome_state": outcome.outcome_state,
                "decision": outcome.decision,
                "reason_code": outcome.reason_code,
                "epistemic_state": outcome.epistemic_state,
                "event_id": (
                    None
                    if outcome.transition_event is None
                    else outcome.transition_event["event_id"]
                ),
                "new_state": (
                    None
                    if outcome.transition_event is None
                    else outcome.transition_event["new_state"]
                ),
            }
            for outcome in stage_2.outcomes
        },
        "denominator": sum(stage_2.accounting.values()),
    }


def _m12(stage_2: Stage2Result | None) -> dict[str, Any]:
    """M12 reports actual correction facts, or an explicit absence."""
    if stage_2 is None:
        return {
            "predecessor_mutation_prohibited": True,
            "stage_2_observed": False,
            "correction_executed": "NOT_YET_OBSERVED",
            "m12_state": "precondition_not_yet_reached",
        }
    correction = stage_2.correction
    return {
        "predecessor_mutation_prohibited": True,
        "stage_2_observed": True,
        "correction_stimulus_id": correction.get("correction_stimulus_id"),
        "correction_executed": bool(correction.get("correction_executed")),
        "m12_state": correction.get("m12_state"),
        "eligible_completed_predecessor": correction.get("eligible_completed_predecessor"),
        "predecessor_before_digest": correction.get("predecessor_before_digest"),
        "predecessor_after_digest": correction.get("predecessor_after_digest"),
        "predecessor_mutated": correction.get("predecessor_mutated"),
        "successor_id": correction.get("successor_id"),
        "supersedes": correction.get("supersedes"),
        "affected_output_eligibility": correction.get("affected_output_eligibility"),
        "detail": correction.get("detail"),
    }
