"""Bounded, fail-closed integration substrate for CDC-END-TO-END-MISSION-001.

The module consumes already-admitted OIC controls.  It contains no source-text
parser and creates no institutional meaning.  Its result-bearing entry point is
unreachable unless six externally governed bindings match the observed runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from oic.cdc_slice import (
    GateDecision,
    digest,
    emit_transition_event,
    evaluate_test_transition,
    make_successor,
    refuse_stale_candidate_proposal,
)
from oic.paths import find_repo_root

MISSION_ID: Final = "CDC-TEST-MISSION-001"
ASSURANCE_MODE: Final = "SYNTHETIC_EVALUATION_ONLY"
OFFICIAL_CDC_RECORD_CREATION: Final = "PROHIBITED"
# The controlling mission input is v0.2. Its only substantive difference from
# v0.1 is reviewer-authority currentness: the v0.1 standing expired at
# 2026-08-11T00:00:00Z, so it could not authorize a real later disposition.
# v0.1 is retained immutable and addressable as the predecessor.
FROZEN_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.6"
# The package digest is computed over the declared member identities, and the
# manifest is self-excluded, so a manifest-only correction leaves it unchanged:
# v0.4 shares v0.3's package digest by construction. The manifest digest and the
# physical byte count are what separate them, and both are checked.
FROZEN_MISSION_PACKAGE_SHA256: Final = (
    "b62f39669cf5891e5864cf2b27debaade4e98637faad162b76e78753a5c9e80b"
)
FROZEN_MISSION_PACKAGE_BYTES: Final = 57452
FROZEN_MISSION_MANIFEST_SHA256: Final = (
    "8aad5e78635b691fa2fad0336e07d9b0738b61db7b12ded2ed22149a258bdb77"
)
# v0.6 carries three evidence objects per chain. The three result objects the
# earlier packages carried per chain were removed, so this count is 27, not 54.
FROZEN_MISSION_EVIDENCE_OBJECT_COUNT: Final = 27

# v0.3 carried the correct owner-issued authority but an unqualified top-level
# ``issued_at`` inherited from the rejected v0.2 local-clock lineage. It is
# retained unchanged as the immediate predecessor.
OWNER_ISSUED_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.3"
OWNER_ISSUED_MISSION_PACKAGE_SHA256: Final = (
    "1d4738d615bf2cbca481268910a14fadc0a4fceb4f60bb5619d1acf1a69687c3"
)
OWNER_ISSUED_MISSION_PACKAGE_BYTES: Final = 67268
OWNER_ISSUED_MISSION_MANIFEST_SHA256: Final = (
    "6a71ab4d6caeffe208f312400c3c7850e6905163c2b0fd28c87391ba4ae20261"
)
MANIFEST_CORRECTION_REASON: Final = "MANIFEST_PROVENANCE_CORRECTION"

# v0.2 chose its effective_from from a locally observed clock. The owner has since
# ruled that provenance unreliable, so v0.2 is retained and addressable but is not
# the controlling input. No result-bearing execution occurred under v0.1 or v0.2.
NOT_ADOPTED_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.2"
NOT_ADOPTED_MISSION_PACKAGE_SHA256: Final = (
    "00dd820cfe43b780d5bec1a12382b16a7d6d9e45d6546c4fc10f3a83ab321510"
)
NOT_ADOPTED_MISSION_PACKAGE_BYTES: Final = 65849
NOT_ADOPTED_CLASSIFICATION: Final = "PREEXECUTION_CURRENTNESS_SUCCESSOR_NOT_ADOPTED"
NOT_ADOPTED_REASON: Final = "ISSUANCE_CLOCK_PROVENANCE_UNRELIABLE"

PREDECESSOR_MISSION_INPUT_RELPATH: Final = "veraxis/cdc-e2e-mission-001/input-v0.1"
PREDECESSOR_MISSION_PACKAGE_SHA256: Final = (
    "414d321dad9fe70671508848a19802f35635d27de60b932417f3305b961364f1"
)
PREDECESSOR_MISSION_PACKAGE_BYTES: Final = 64199
PREDECESSOR_AUTHORITY_SHA256: Final = (
    "a82c078427fefe23abbb2bd066e9e730cea7e1fc2a3bab553e8352fa48b3db23"
)
SUPERSESSION_REASON: Final = "PREEXECUTION_AUTHORITY_CURRENTNESS"
# Owner-issued prospective time. This is the authority's *effective* time, not an
# issuance timestamp: no trustworthy independent issuance instant was captured and
# none is reconstructed. It is also a fail-closed sanity boundary: an execution
# environment whose UTC clock sits before it must refuse rather than compensate.
AUTHORITY_EFFECTIVE_FROM: Final = "2026-08-11T20:30:00Z"
AUTHORITY_EFFECTIVE_FROM_SOURCE: Final = "OWNER_EXPLICIT_PROSPECTIVE_TIME"
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
    "stage_1_component_profile_sha256",
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
    stage_1_component_profile_sha256: str | None = None

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
    # SHA256SUMS is checked in addition to the member-byte verification above.
    # Neither substitutes for the other, and neither substitutes for the
    # aggregate package digest computed below.
    declared_sums: dict[str, str] = {}
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest_text, _, listed = line.partition("  ")
        declared_sums[listed] = digest_text
    for identity in identities:
        listed_path = str(identity["path"])
        if listed_path == "SHA256SUMS":
            continue
        if declared_sums.get(listed_path) != identity["sha256"]:
            raise MissionContractError(f"SHA256SUMS disagrees with member bytes: {listed_path}")
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
        evidence_object_count=FROZEN_MISSION_EVIDENCE_OBJECT_COUNT,
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
    if clearance.stage_1_component_profile_sha256 != STAGE_1_COMPONENT_PROFILE_SHA256:
        mismatches.append("stage_1_component_profile_sha256")
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
)

# Stage 2 needs a prior institutional state. input-v0.6 deliberately carries
# none, because at Stage-1 input time no candidate exists and inventing one
# would be a pre-candidate state promotion. It is therefore optional in the
# projection and its absence makes Stage-2 derivation refuse explicitly.
OPTIONAL_STAGE_2_CHAIN_FIELDS: Final = ("prior_institutional_state",)

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
    "CDC-END-TO-END-MISSION-001-CLAIM-EVIDENCE-MAP-v0.2.json": "EVALUATION_AID",
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
            for optional in OPTIONAL_STAGE_2_CHAIN_FIELDS:
                if optional in chain:
                    execution_input[optional] = chain[optional]
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
    owner_execution_authorization: Mapping[str, Any] | None = None
    attempt_record: Mapping[str, Any] | None = None
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
            "owner_execution_authorization": (
                None
                if self.owner_execution_authorization is None
                else dict(self.owner_execution_authorization)
            ),
            "attempt_record": (None if self.attempt_record is None else dict(self.attempt_record)),
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
    mission_authorization: object = None,
    attempt_claim: Callable[[], MissionAttemptRecord] | None = None,
) -> Stage1Observation:
    """Form candidates across all nine chains, then stop.

    The denominator survives individual failures: a chain that raises is recorded
    as ``non_evaluable`` and the remaining chains still run. An early exception
    must never erase the rest of the population.
    """
    require_projected_source(projection, frozen)
    # Candidate formation over the frozen mission population is result-bearing
    # and consumes the single authorized attempt. The interlock sits here, above
    # the injected components, so it cannot be sidestepped by supplying a
    # different evaluator -- including a stub in a test.
    _require_mission_population_not_formed(projection, mission_authorization)
    tally = dict.fromkeys(DENOMINATOR_STATES, 0)
    observations: list[Stage1ChainObservation] = []
    claimed: MissionAttemptRecord | None = None
    evaluator_invoked = False
    for chain in projection.chains:
        try:
            # Three semantically distinct inputs. Passing the same object three
            # times, as this previously did, meant the interface guaranteed
            # nothing about what the component actually received.
            admitted_control = _require_mapping(
                chain.execution_input["admitted_control"], "admitted_control"
            )
            evidence_bundle = _require_mapping(
                chain.execution_input["evidence_bundle"], "evidence_bundle"
            )
            admission_record = _require_mapping(
                chain.execution_input["admission_record"], "admission_record"
            )
            if attempt_claim is not None and claimed is None:
                # The claim is taken here, after every precondition has already
                # passed and immediately before the first governed invocation, so
                # a precondition failure never consumes the authorization.
                claimed = attempt_claim()
            evaluator_invoked = True
            evaluation = evaluator(admitted_control, evidence_bundle, admission_record)
            warrant_class, warrant = warrant_builder(evaluation, admitted_control)
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
                "official_status": "NOT_AUTHORIZED_AS_OFFICIAL",
                "machine_disposition": None,
                "institutional_transition": "NONE",
            }
            artifact = Stage1ChainArtifact(
                chain_id=chain.chain_id,
                procedure_id=procedure_id,
                control_id=chain.control_id,
                ebawu_id=chain.ebawu_ref,
                input_digest=chain.input_digest(),
                evaluation=evaluation,
                evaluation_digest=str(evaluation["evaluation_digest"]),
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
    consumed = (
        mark_attempt_consumed(claimed) if claimed is not None and evaluator_invoked else claimed
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
        owner_execution_authorization=(
            None
            if not isinstance(mission_authorization, OwnerExecutionAuthorization)
            else mission_authorization.as_record()
        ),
        attempt_record=None if consumed is None else consumed.identity(),
    )


def execute_authorized_stage_1(
    projection: object,
    frozen: FrozenMissionInput,
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    *,
    owner_interpretation: object,
    component_profile: object,
    owner_execution_authorization_path: Path,
) -> Stage1Observation:
    """The single authorized route to Stage-1 candidate formation.

    The caller supplies identities and evidence locations. It supplies no
    components: the evaluator and warrant builder are constructed here from the
    verified profile, so there is no parameter through which a stub evaluator,
    a stub warrant builder or a per-chain semantic profile can be substituted
    once execution becomes authorized.

    Order matters, and every step is a precondition for the next:

    1. the component profile is verified from exact bytes;
    2. the mission projection is verified against the frozen package bytes;
    3. the clearance matches observed runtime and every governed identity;
    4. the owner interpretation is verified from exact bytes;
    5. the owner execution authorization is verified from exact external bytes
       and cross-bound to the clearance reference and the running implementation;
    6. package evidence is checked against the profile's preregistered
       assignments as a conformance constraint only;
    7. and only then are the governed components built and invoked.
    """
    profile = require_verified_component_profile(component_profile)
    interpretation = require_verified_owner_interpretation(owner_interpretation)
    verified = require_projected_source(projection, frozen)
    require_result_clearance(
        clearance, runtime, {"mission_package_sha256": verified.package_sha256}
    )
    if clearance.owner_preexecution_interpretation_sha256 != interpretation.sha256_hex:
        raise ResultBearingMissionBlockedError(
            "clearance and verified owner interpretation disagree"
        )
    if clearance.stage_1_component_profile_sha256 != profile.sha256_hex:
        raise ResultBearingMissionBlockedError("clearance and verified component profile disagree")
    if verified.package_sha256 != frozen.package_sha256:
        raise ResultBearingMissionBlockedError("projection and verified bytes disagree")

    authorization = verify_owner_execution_authorization(
        owner_execution_authorization_path,
        clearance=clearance,
        runtime=runtime,
        frozen=frozen,
    )
    # The conformance constraint is an operational precondition, not a report:
    # a mismatch stops the run before any evaluator is invoked.
    require_unclaimed_attempt(authorization)
    conformance = require_evidence_matches_preregistered_assignments(verified, profile)
    if conformance["fallback_to_profile_assignments"]:
        raise PreconditionMismatchError("profile assignments must never act as evidence")

    evaluator, warrant_builder = governed_stage_1_components(
        profile, mission_id=verified.mission_id, mission_authorization=authorization
    )
    return _form_stage_1(
        verified,
        frozen,
        evaluator=evaluator,
        warrant_builder=warrant_builder,
        authorization=STAGE_1_AUTHORIZATION_CLEARED,
        owner_interpretation_sha256=interpretation.sha256_hex,
        mission_authorization=authorization,
        attempt_claim=lambda: claim_attempt(authorization, runtime, frozen),
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


RUNTIME_CLOCK_SOURCE: Final = "RUNTIME_OBSERVED_UTC"
TEST_CLOCK_SOURCE: Final = "TEST_INJECTED_CLOCK_NOT_RESULT_BEARING"


def observe_runtime_utc() -> str:
    """The execution runtime's own UTC observation. Not a caller input."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def bind_human_disposition(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    projection: MissionProjection,
    action_plan: object,
) -> dict[str, Any]:
    """Bind a disposition against the clock the runtime observes for itself.

    There is deliberately no clock parameter. A caller cannot select the observed
    time, cannot pass a historical one, and cannot omit an argument to skip the
    currentness check, because no such argument exists on this path. A caller may
    still *state* ``observed_at``, but it must equal what the runtime observed.
    """
    return _bind_disposition(
        stage_1,
        disposition,
        projection=projection,
        action_plan=action_plan,
        observed_at=observe_runtime_utc(),
        clock_source=RUNTIME_CLOCK_SOURCE,
    )


def _bind_disposition_with_injected_clock(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    projection: MissionProjection,
    action_plan: object,
    clock: str,
) -> dict[str, Any]:
    """TEST-ONLY. Deterministic boundary testing with an injected clock.

    Private and explicitly non-result-bearing: the artifact it produces is stamped
    :data:`TEST_CLOCK_SOURCE`, so a reader can always tell that its observed time
    was supplied rather than observed.
    """
    return _bind_disposition(
        stage_1,
        disposition,
        projection=projection,
        action_plan=action_plan,
        observed_at=clock,
        clock_source=TEST_CLOCK_SOURCE,
    )


def _bind_disposition(
    stage_1: Stage1Observation,
    disposition: Mapping[str, Any],
    *,
    projection: MissionProjection,
    action_plan: object,
    observed_at: str,
    clock_source: str,
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
    stated = disposition.get("observed_at")
    if stated is not None and stated != observed_at:
        raise AuthorityCurrentnessError(
            f"a disposition may not select its own observation clock: the runtime "
            f"observed {observed_at!r}, the disposition claims {stated!r}"
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
        observed_at=observed_at,
    )
    record = {
        **observed,
        "chain_id": chain_id,
        "action": action,
        "reviewer_id": str(disposition["reviewer_id"]),
        "reviewer_role": str(disposition["reviewer_role"]),
        "authority_scope_ref": str(disposition["authority_scope_ref"]),
        "observed_at": observed_at,
        "clock_source": clock_source,
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


DERIVED_PRIOR_INSTITUTIONAL_STATE: Final = "CANDIDATE_FORMED"
PRIOR_STATE_SOURCE: Final = "ACTUAL_STAGE_1_OBSERVATION"


class PriorStateDerivationError(MissionContractError):
    """Stage-2 prior state was requested before an actual candidate existed."""


def derive_stage_2_prior_state(stage_1: object, chain_id: str) -> str:
    """Derive the prior institutional state from the actual Stage-1 checkpoint.

    input-v0.6 deliberately carries no prior_institutional_state: writing one at
    Stage-1 input time would assert a state before any candidate existed. The
    state becomes true by actual candidate formation, so it is recovered here
    out of the completed, owner-cleared Stage-1 observation and nowhere else.

    There is no parameter through which a caller can supply or override it.
    """
    if not isinstance(stage_1, Stage1Observation):
        raise PriorStateDerivationError(
            "Stage-2 prior state must derive from a Stage1Observation; a mapping, "
            "disposition, binding set or run metadata is not one"
        )
    if stage_1.stage != STAGE_1_TERMINAL_STATE:
        raise PriorStateDerivationError(
            f"Stage-1 is {stage_1.stage!r}, not {STAGE_1_TERMINAL_STATE!r}; no prior "
            "institutional state exists yet"
        )
    if not stage_1.is_owner_cleared():
        raise PriorStateDerivationError(
            f"Stage-1 observation is {stage_1.authorization}; only an owner-cleared "
            "observation establishes a prior institutional state"
        )
    artifact = stage_1.artifacts().get(chain_id)
    if artifact is None:
        raise PriorStateDerivationError(
            f"no Stage-1 artifact exists for {chain_id}; prior state is not derivable"
        )
    if not artifact.candidate or not artifact.candidate_digest:
        raise PriorStateDerivationError(
            f"chain {chain_id} formed no candidate; prior state is not derivable"
        )
    return DERIVED_PRIOR_INSTITUTIONAL_STATE


def derive_transition_registry(
    projection: MissionProjection, artifact: Stage1ChainArtifact, stage_1: object
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
        "states": {artifact.ebawu_id: derive_stage_2_prior_state(stage_1, artifact.chain_id)},
        "stale_candidate_ids": (),
    }


def derive_transition_proposal(
    projection: MissionProjection,
    artifact: Stage1ChainArtifact,
    disposition: Mapping[str, Any],
    stage_1: object,
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
        "prior_institutional_state": derive_stage_2_prior_state(stage_1, artifact.chain_id),
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


def _event_metadata_fields(run_metadata: Mapping[str, Any]) -> None:
    """Structural run-metadata validation, run before anything is claimed."""
    missing = sorted(set(RUN_METADATA_FIELDS) - run_metadata.keys())
    if missing:
        raise MissionContractError(f"run metadata incomplete: {missing}")


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
    owner_stage_2_authorization: Mapping[str, Any] | None = None
    attempt_record: Mapping[str, Any] | None = None
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
            "owner_stage_2_authorization": (
                None
                if self.owner_stage_2_authorization is None
                else dict(self.owner_stage_2_authorization)
            ),
            "attempt_record": (None if self.attempt_record is None else dict(self.attempt_record)),
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


# ---------------------------------------------------------------------------
# Stage-2 owner issuance and attempt ledger.
#
# Stage 2 gets its own exact-byte authorization and its own attempt ledger. A
# nonempty owner_execution_authorization label satisfied the generic clearance
# but says nothing about whether Stage 2 was authorized, and reusing the Stage-1
# ledger would let one issuance cover two result-bearing phases.
# ---------------------------------------------------------------------------

STAGE_2_AUTHORIZATION_RECORD_CLASS: Final = "OWNER_STAGE_2_EXECUTION_AUTHORIZATION"
STAGE_2_AUTHORIZATION_STAGE: Final = "STAGE_2_ONLY"
STAGE_2_AUTHORIZATION_SCOPE: Final = "ONE_RESULT_BEARING_STAGE_2_EXECUTION"

STAGE_2_AUTHORIZATION_DECLARATIONS: Final[dict[str, object]] = {
    "record_class": STAGE_2_AUTHORIZATION_RECORD_CLASS,
    "mission_id": MISSION_ID,
    "owner_authorized": True,
    "authorized_stage": STAGE_2_AUTHORIZATION_STAGE,
    "authorization_scope": STAGE_2_AUTHORIZATION_SCOPE,
    "single_use": True,
    "automatic_retry_authorized": False,
    "stage_1_reexecution_authorized": False,
    "additional_human_disposition_authorized": False,
    "stage_2_transition_evaluation_authorized": True,
    "transition_event_emission_authorized": "GATE_RESULT_CONTROLLED",
    "draft_rendering_authorized": "FROZEN_OUTPUT_DEFINITION_CONTROLLED",
    "correction_handling_authorized": "FROZEN_ACTION_PLAN_PRECONDITION_CONTROLLED",
    "official_handoff_authorized": False,
    "result_bearing": True,
}

STAGE_2_AUTHORIZATION_BINDING_FIELDS: Final = (
    "implementation_commit",
    "implementation_tree",
    "environment_manifest_sha256",
    "mission_package_sha256",
    "stage_1_component_profile_sha256",
    "oracle_sha256",
    "adjudication_protocol_sha256",
    "action_plan_sha256",
    "action_plan_provenance_token",
    "owner_preexecution_interpretation_sha256",
    "stage_1_raw_result_sha256",
    "stage_1_observation_digest",
    "human_disposition_evidence_commit",
    "human_disposition_evidence_tree",
    "correction_stimulus_digest",
    "owner_m08_m09_acceptance_sha256",
)

ATTEMPT_STATE_STAGE_2_CONSUMED: Final = "CONSUMED_AFTER_FIRST_TRANSITION_EVALUATION"

# Immutable prior-phase evidence. These are frozen historical artifacts that
# cannot move because this implementation moved, so binding them here is not
# circular in the way an implementation digest would be.
STAGE_1_RAW_RESULT_SHA256: Final = (
    "aa32274f238d01bc9f6c6d1c67879acfb4765a34d0dc0b4ccf568f3c07353a70"
)
HUMAN_DISPOSITION_EVIDENCE_COMMIT: Final = "a61fae0a94eeaf54f69c42f40af67d9e43516294"
HUMAN_DISPOSITION_EVIDENCE_TREE: Final = "e1747b5bfa1a11f3f852a92ad13fdd975aceef9e"
OWNER_M08_M09_ACCEPTANCE_SHA256: Final = (
    "5f13fe1920be490429b9cc562bcaade38293de35e9898a4d5803f0744c29381a"
)


class OwnerStage2AuthorizationError(ResultBearingMissionBlockedError):
    """The Stage-2 owner authorization is absent, wrong, unbound or relocated."""


@dataclass(frozen=True, slots=True)
class OwnerStage2Authorization:
    """A Stage-2 owner authorization verified from exact external bytes."""

    path: Path
    sha256_hex: str
    byte_count: int
    reference: str
    record_class: str
    authorized_stage: str
    authorization_scope: str
    authorization_id: str
    canonical_path: str

    def as_record(self) -> dict[str, Any]:
        """Identity and declared scope only; carries no authorization prose."""
        return {
            "owner_stage_2_authorization_sha256": self.sha256_hex,
            "owner_stage_2_authorization_bytes": self.byte_count,
            "owner_stage_2_authorization_reference": self.reference,
            "owner_stage_2_authorization_record_class": self.record_class,
            "owner_stage_2_authorization_scope": self.authorization_scope,
            "owner_stage_2_authorization_id": self.authorization_id,
            "authorized_stage": self.authorized_stage,
        }


def verify_owner_stage_2_authorization(
    path: Path,
    *,
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    action_plan: object,
) -> OwnerStage2Authorization:
    """Verify a Stage-2 authorization: identity, location, semantics and bindings.

    Hashing says which artifact this is; the declarations say whether it
    authorizes Stage 2; the bindings say whether it authorizes *this* Stage 2.
    All three are required, and the artifact only verifies at the canonical path
    it declares, so a byte-identical copy elsewhere is not a second issuance.
    """
    plan = require_verified_action_plan(action_plan)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise OwnerStage2AuthorizationError(
            f"Stage-2 owner authorization is not readable at {path}: {error}"
        ) from error
    digest = _file_sha256(payload)
    reference = f"{OWNER_AUTHORIZATION_REFERENCE_PREFIX}{digest}"
    observed_path = path.resolve()
    if clearance.owner_execution_authorization != reference:
        raise OwnerStage2AuthorizationError(
            f"clearance owner_execution_authorization is "
            f"{clearance.owner_execution_authorization!r}, but the supplied artifact "
            f"hashes to {reference!r}; a label is not the artifact"
        )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise OwnerStage2AuthorizationError(
            f"Stage-2 owner authorization is not structured JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise OwnerStage2AuthorizationError("Stage-2 authorization must be a JSON object")

    declared_location = document.get("canonical_authorization_path")
    if not isinstance(declared_location, str) or not declared_location:
        raise OwnerStage2AuthorizationError(
            "Stage-2 authorization declares no canonical_authorization_path"
        )
    if Path(declared_location).resolve() != observed_path:
        raise OwnerStage2AuthorizationError(
            f"Stage-2 authorization was presented at {observed_path} but declares "
            f"{Path(declared_location).resolve()}; a relocated copy is not a second issuance"
        )
    wrong = [
        f"{name}={document.get(name)!r} (required {expected!r})"
        for name, expected in STAGE_2_AUTHORIZATION_DECLARATIONS.items()
        if document.get(name) is not expected and document.get(name) != expected
    ]
    if wrong:
        raise OwnerStage2AuthorizationError(
            f"the artifact does not declare Stage-2 authorization semantics: {wrong}"
        )

    observed_bindings = {
        "implementation_commit": runtime.implementation_commit,
        "implementation_tree": runtime.implementation_tree,
        "environment_manifest_sha256": runtime.environment_manifest_sha256,
        "mission_package_sha256": frozen.package_sha256,
        "stage_1_component_profile_sha256": STAGE_1_COMPONENT_PROFILE_SHA256,
        "oracle_sha256": ORACLE_SHA256,
        "adjudication_protocol_sha256": ADJUDICATION_PROTOCOL_SHA256,
        "action_plan_sha256": plan.sha256_hex,
        "action_plan_provenance_token": plan.provenance_token,
        "owner_preexecution_interpretation_sha256": OWNER_PREEXECUTION_INTERPRETATION_SHA256,
        "stage_1_observation_digest": stage_1.digest(),
        "correction_stimulus_digest": plan.correction.digest(),
        "stage_1_raw_result_sha256": STAGE_1_RAW_RESULT_SHA256,
        "human_disposition_evidence_commit": HUMAN_DISPOSITION_EVIDENCE_COMMIT,
        "human_disposition_evidence_tree": HUMAN_DISPOSITION_EVIDENCE_TREE,
        "owner_m08_m09_acceptance_sha256": OWNER_M08_M09_ACCEPTANCE_SHA256,
    }
    raw_bindings = document.get("bindings")
    if not isinstance(raw_bindings, Mapping):
        raise OwnerStage2AuthorizationError(
            "Stage-2 authorization carries no structured 'bindings' object"
        )
    missing = sorted(set(STAGE_2_AUTHORIZATION_BINDING_FIELDS) - raw_bindings.keys())
    if missing:
        raise OwnerStage2AuthorizationError(f"Stage-2 authorization bindings missing: {missing}")
    mismatched = sorted(
        name for name, value in observed_bindings.items() if raw_bindings.get(name) != value
    )
    if mismatched:
        raise OwnerStage2AuthorizationError(
            f"Stage-2 authorization bindings do not match the running mission: {mismatched}"
        )
    expected_set = sorted(sha256(dict(record)) for record in dispositions.values())
    declared_set = raw_bindings.get("stage_2_human_disposition_binding_digests")
    if (
        not isinstance(declared_set, list | tuple)
        or sorted(str(v) for v in declared_set) != expected_set
    ):
        raise OwnerStage2AuthorizationError(
            "Stage-2 authorization does not bind the exact human-disposition binding set"
        )
    return OwnerStage2Authorization(
        path=observed_path,
        sha256_hex=digest,
        byte_count=len(payload),
        reference=reference,
        record_class=str(document["record_class"]),
        authorized_stage=str(document["authorized_stage"]),
        authorization_scope=str(document["authorization_scope"]),
        authorization_id=str(document.get("authorization_id", "UNIDENTIFIED")),
        canonical_path=str(observed_path),
    )


def stage_2_attempt_record_path(authorization: OwnerStage2Authorization) -> Path:
    """Derived from the verified canonical location plus the Stage-2 digest."""
    canonical = Path(authorization.canonical_path or authorization.path).resolve()
    return canonical.parent / f".cdc-e2e-stage-2-attempt-{authorization.sha256_hex}.json"


def read_stage_2_attempt_state(authorization: OwnerStage2Authorization) -> str:
    """Current Stage-2 attempt state for this authorization."""
    path = stage_2_attempt_record_path(authorization)
    if not path.exists():
        return ATTEMPT_STATE_NONE
    document = _require_mapping(json.loads(path.read_bytes()), "attempt record")
    return str(document.get("attempt_state"))


def require_unclaimed_stage_2_attempt(authorization: OwnerStage2Authorization) -> None:
    """Refuse before any transition evaluation when the authorization is used."""
    state = read_stage_2_attempt_state(authorization)
    if state == ATTEMPT_STATE_NONE:
        return
    if state == ATTEMPT_STATE_CLAIMED:
        raise MissionAttemptStateError(
            f"Stage-2 authorization {authorization.reference} is {ATTEMPT_STATE_CLAIMED}: a "
            "prior attempt claimed it and no consumption was recorded. Automatic retry is "
            "prohibited; this requires a separate owner decision."
        )
    raise MissionAttemptStateError(
        f"Stage-2 authorization {authorization.reference} is {state}: it authorized one "
        "result-bearing Stage-2 execution and is permanently non-reusable."
    )


def claim_stage_2_attempt(
    authorization: OwnerStage2Authorization,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    disposition_binding_digests: Sequence[str],
) -> MissionAttemptRecord:
    """Atomically claim the single authorized Stage-2 attempt, or refuse."""
    record = MissionAttemptRecord(
        path=stage_2_attempt_record_path(authorization),
        state=ATTEMPT_STATE_CLAIMED,
        owner_execution_authorization_sha256=authorization.sha256_hex,
        implementation_commit=runtime.implementation_commit,
        implementation_tree=runtime.implementation_tree,
        mission_package_sha256=frozen.package_sha256,
    )
    body = {
        **record.as_record(),
        "stage": STAGE_2_AUTHORIZATION_STAGE,
        "stage_1_observation_digest": stage_1.digest(),
        "human_disposition_binding_digests": sorted(disposition_binding_digests),
    }
    payload = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode()
    try:
        handle = os.open(record.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise MissionAttemptStateError(
            f"Stage-2 authorization {authorization.reference} was already claimed by "
            "another attempt; automatic retry is prohibited"
        ) from error
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)
    written = record.path.read_bytes()
    return replace(record, record_sha256=_file_sha256(written), record_bytes=len(written))


def mark_stage_2_attempt_consumed(
    record: MissionAttemptRecord,
    stage_1: Stage1Observation,
    disposition_binding_digests: Sequence[str],
) -> MissionAttemptRecord:
    """Record that a governed transition evaluation was actually invoked."""
    consumed = replace(record, state=ATTEMPT_STATE_STAGE_2_CONSUMED)
    body = {
        **consumed.as_record(),
        "stage": STAGE_2_AUTHORIZATION_STAGE,
        "stage_1_observation_digest": stage_1.digest(),
        "human_disposition_binding_digests": sorted(disposition_binding_digests),
    }
    record.path.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode())
    written = record.path.read_bytes()
    return replace(consumed, record_sha256=_file_sha256(written), record_bytes=len(written))


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
    owner_stage_2_authorization_path: Path,
) -> Stage2Result:
    """The single authorized route to transition evaluation and rendering.

    No caller-supplied transition proposal, registry or correction target can
    enter here. The first two are derived from the actual Stage-1 artifacts and
    the frozen chain inputs; the third comes from the verified action-plan bytes.
    """
    plan = require_verified_action_plan(action_plan)
    verified = require_projected_source(projection, frozen)
    # Structural preconditions run first and in full: nothing below may claim the
    # attempt until every one of them has passed.
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
    forbidden = {
        "transition_proposal",
        "transition_registry",
        "registry",
        "proposal",
        "prior_institutional_state",
        "states",
    }
    for chain_id, record in dispositions.items():
        intruding = sorted(forbidden & record.keys())
        if intruding:
            raise TransitionDerivationError(
                f"disposition {chain_id} carries a caller-supplied {intruding}; "
                "the proposal and registry are derived, never accepted"
            )
    authorization = verify_owner_stage_2_authorization(
        owner_stage_2_authorization_path,
        clearance=clearance,
        runtime=runtime,
        frozen=frozen,
        stage_1=stage_1,
        dispositions=dispositions,
        action_plan=plan,
    )
    require_unclaimed_stage_2_attempt(authorization)
    artifacts = stage_1.artifacts()
    # Prior state must be derivable for every chain that will be evaluated, before
    # anything is claimed.
    for chain_id in sorted(set(artifacts) & set(dispositions)):
        derive_stage_2_prior_state(stage_1, chain_id)
    _event_metadata_fields(run_metadata)
    binding_digests = [sha256(dict(record)) for record in dispositions.values()]
    claimed: MissionAttemptRecord | None = None
    evaluation_invoked = False
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
        registry = derive_transition_registry(verified, artifact, stage_1)
        proposal = derive_transition_proposal(verified, artifact, disposition, stage_1)
        if claimed is None:
            # Every structural precondition has passed; claim immediately before
            # the first result-bearing gate evaluation.
            claimed = claim_stage_2_attempt(
                authorization, runtime, frozen, stage_1, binding_digests
            )
        evaluation_invoked = True
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
    consumed = (
        mark_stage_2_attempt_consumed(claimed, stage_1, binding_digests)
        if claimed is not None and evaluation_invoked
        else claimed
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
        owner_stage_2_authorization=authorization.as_record(),
        attempt_record=None if consumed is None else consumed.identity(),
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


# ---------------------------------------------------------------------------
# Stage-1 governed components.
#
# The gap these close: the mission had no designated evaluator or warrant
# builder, and the admitted controls encoded no rule deriving a verdict from
# evidence. The rule now lives in an owner-designated component profile that is
# separately governed configuration -- it is verified from exact bytes and is
# deliberately NOT written into any admitted control, because a synthetic
# evaluation profile must not become admitted OIC meaning.
# ---------------------------------------------------------------------------

STAGE_1_COMPONENT_PROFILE_RELPATH: Final = (
    "veraxis/cdc-e2e-mission-001/preexecution/"
    "CDC-END-TO-END-MISSION-001-STAGE-1-COMPONENT-PROFILE-v0.2.json"
)
STAGE_1_COMPONENT_PROFILE_SHA256: Final = (
    "03eb25effa77af830faafdb49db8318c2adcb20619c6f580a853255334a30a57"
)
STAGE_1_COMPONENT_PROFILE_ID: Final = "CDC-END-TO-END-MISSION-001-STAGE-1-COMPONENT-PROFILE-v0.2"

VERDICT_SATISFIED: Final = "SATISFIED"
VERDICT_BREACH: Final = "BREACH"
VERDICT_UNRESOLVED: Final = "UNRESOLVED"
VERDICTS: Final = (VERDICT_SATISFIED, VERDICT_BREACH, VERDICT_UNRESOLVED)

REASON_ALL_SATISFIED: Final = "ALL_REQUIRED_CONDITIONS_SATISFIED"
REASON_NOT_SATISFIED: Final = "REQUIRED_CONDITION_NOT_SATISFIED"
REASON_MISSING: Final = "MISSING_REQUIRED_EVIDENCE"
REASON_CONFLICTING: Final = "CONFLICTING_REQUIRED_EVIDENCE"

FALLBACK_WARRANT_CLASS: Final = "FALLBACK_WARRANT"
ZTL_WARRANT_STATE: Final = "PROHIBITED"
NO_ZTL_DERIVATION: Final = "NO_ZTL_DERIVATION"

ON_UNKNOWN_NON_APPLICATION_REASON: Final = "OUTSIDE_STAGE_1_EVALUATOR_CONTRACT"

# The frozen mission population. Evaluating it requires an owner execution
# authorization supplied at runtime as an exact external artifact.
#
# There is deliberately no module constant that switches execution on. A source
# toggle would be circular: the owner authorization must bind the accepted
# implementation commit and tree, but flipping a constant to enable execution
# produces a different commit and tree, so the authorization would bind an
# implementation that is no longer the one running. The gate is therefore
# runtime evidence cross-bound to the clearance, and this file never needs to
# change again to permit or refuse a run.
FROZEN_MISSION_PROCEDURE_IDS: Final = ("P-001", "P-002", "P-003")
MISSION_POPULATION_EXECUTION_STATE: Final = "REQUIRES_RUNTIME_OWNER_EXECUTION_AUTHORIZATION"
OWNER_AUTHORIZATION_REFERENCE_PREFIX: Final = "sha256:"


class ComponentProfileProvenanceError(MissionContractError):
    """The component profile was not verified from its exact bytes."""


class PreconditionMismatchError(MissionContractError):
    """A fail-closed precondition mismatch. Never a verdict."""


class MissionPopulationExecutionBlockedError(ResultBearingMissionBlockedError):
    """Evaluation of the frozen mission population was attempted without authorization."""


@dataclass(frozen=True, slots=True)
class OwnerExecutionAuthorization:
    """An owner execution authorization verified from exact external bytes.

    No expected digest is compiled into this module. The authorization's
    identity is whatever its bytes hash to, and it is accepted only when the
    externally issued ``ExecutionClearance.owner_execution_authorization``
    reference names that exact digest and the artifact itself names the exact
    implementation and package it authorizes.
    """

    path: Path
    sha256_hex: str
    byte_count: int
    reference: str
    authorized_stage: str
    record_class: str
    authorization_scope: str
    authorization_id: str
    canonical_path: str = ""

    def as_record(self) -> dict[str, Any]:
        """Identity and declared scope only; carries no authorization prose."""
        return {
            "owner_execution_authorization_sha256": self.sha256_hex,
            "owner_execution_authorization_bytes": self.byte_count,
            "owner_execution_authorization_reference": self.reference,
            "owner_execution_authorization_record_class": self.record_class,
            "owner_execution_authorization_scope": self.authorization_scope,
            "owner_execution_authorization_id": self.authorization_id,
            "authorized_stage": self.authorized_stage,
        }


class OwnerExecutionAuthorizationError(ResultBearingMissionBlockedError):
    """The runtime owner execution authorization is absent, wrong or unbound."""


OWNER_AUTHORIZATION_RECORD_CLASS: Final = "OWNER_STAGE_1_EXECUTION_AUTHORIZATION"
OWNER_AUTHORIZATION_SCOPE: Final = "ONE_RESULT_BEARING_STAGE_1_EXECUTION"
OWNER_AUTHORIZATION_STAGE: Final = "STAGE_1_ONLY"

# Immutable predecessor governance objects. Binding their fixed identities is
# safe: unlike the implementation commit and tree, they cannot change as a
# result of this implementation changing, so there is no circularity.
OWNER_SEMANTIC_PREIMPLEMENTATION_FREEZE_SHA256: Final = (
    "fa8f18cb1d890b41fd078b92238200e58cb0e7f1ff65628f2390df520e20ab2a"
)
OWNER_STAGE_1_SEAM_CLARIFICATION_SHA256: Final = (
    "a4a87ec5698416eaa9af970392070a25181df263537524e8b0fc8a91d86fec60"
)

# Declarations the artifact must make about itself. A digest identifies an
# artifact; it says nothing about whether the artifact authorizes anything.
OWNER_AUTHORIZATION_DECLARATIONS: Final[dict[str, object]] = {
    "record_class": OWNER_AUTHORIZATION_RECORD_CLASS,
    "mission_id": MISSION_ID,
    "owner_authorized": True,
    "authorized_stage": OWNER_AUTHORIZATION_STAGE,
    "authorization_scope": OWNER_AUTHORIZATION_SCOPE,
    "single_use": True,
    "automatic_retry_authorized": False,
    "stage_2_authorized": False,
    "result_bearing": True,
}

# Structured bindings, compared field by field against observed runtime, the
# clearance and the frozen governance identities. None of this is substring
# presence in a text blob.
OWNER_AUTHORIZATION_BINDING_FIELDS: Final = (
    "implementation_commit",
    "implementation_tree",
    "environment_manifest_sha256",
    "mission_package_sha256",
    "stage_1_component_profile_sha256",
    "oracle_sha256",
    "adjudication_protocol_sha256",
    "action_plan_sha256",
    "owner_preexecution_interpretation_sha256",
    "owner_semantic_preimplementation_freeze_sha256",
    "owner_stage_1_seam_clarification_sha256",
)


def verify_owner_execution_authorization(
    path: Path,
    *,
    clearance: ExecutionClearance,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
) -> OwnerExecutionAuthorization:
    """Verify an externally supplied authorization: identity *and* semantics.

    Hashing establishes which artifact this is. It does not establish that the
    artifact authorizes anything, so the bytes are hashed first and then parsed
    as structured data, and the artifact must declare its own authorization
    semantics and bind every governed identity as a field.

    No future authorization digest is compiled into this module. The two fixed
    digests bound here are immutable predecessor governance objects, which
    cannot change because this implementation changed.
    """
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise OwnerExecutionAuthorizationError(
            f"owner execution authorization artifact is not readable at {path}: {error}"
        ) from error
    digest = _file_sha256(payload)
    reference = f"{OWNER_AUTHORIZATION_REFERENCE_PREFIX}{digest}"
    supplied = clearance.owner_execution_authorization
    if not supplied:
        raise OwnerExecutionAuthorizationError(
            "clearance carries no owner_execution_authorization reference"
        )
    if supplied != reference:
        raise OwnerExecutionAuthorizationError(
            f"clearance owner_execution_authorization is {supplied!r}, but the supplied "
            f"artifact hashes to {reference!r}; a label is not the artifact"
        )
    observed_path = path.resolve()
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise OwnerExecutionAuthorizationError(
            f"owner execution authorization is not structured JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise OwnerExecutionAuthorizationError(
            "owner execution authorization must be a JSON object"
        )

    wrong = [
        f"{name}={document.get(name)!r} (required {expected!r})"
        for name, expected in OWNER_AUTHORIZATION_DECLARATIONS.items()
        if document.get(name) is not expected and document.get(name) != expected
    ]
    if wrong:
        raise OwnerExecutionAuthorizationError(
            f"the artifact does not declare Stage-1 authorization semantics: {wrong}"
        )

    expected_bindings = {
        "implementation_commit": runtime.implementation_commit,
        "implementation_tree": runtime.implementation_tree,
        "environment_manifest_sha256": runtime.environment_manifest_sha256,
        "mission_package_sha256": frozen.package_sha256,
        "stage_1_component_profile_sha256": STAGE_1_COMPONENT_PROFILE_SHA256,
        "oracle_sha256": ORACLE_SHA256,
        "adjudication_protocol_sha256": ADJUDICATION_PROTOCOL_SHA256,
        "action_plan_sha256": HUMAN_ACTION_PLAN_SHA256,
        "owner_preexecution_interpretation_sha256": OWNER_PREEXECUTION_INTERPRETATION_SHA256,
        "owner_semantic_preimplementation_freeze_sha256": (
            OWNER_SEMANTIC_PREIMPLEMENTATION_FREEZE_SHA256
        ),
        "owner_stage_1_seam_clarification_sha256": OWNER_STAGE_1_SEAM_CLARIFICATION_SHA256,
    }
    # A digest is location-independent, so a byte-identical copy at another path
    # would otherwise resolve to a fresh attempt namespace and buy a second run.
    # The owner declares the one canonical location at which the issuance is
    # valid, and a relocated copy refuses here, before any attempt state is read.
    declared_location = document.get("canonical_authorization_path")
    if not isinstance(declared_location, str) or not declared_location:
        raise OwnerExecutionAuthorizationError(
            "owner authorization declares no canonical_authorization_path; without it "
            "a byte-identical copy at another path would obtain a second attempt"
        )
    if Path(declared_location).resolve() != observed_path:
        raise OwnerExecutionAuthorizationError(
            f"owner authorization was presented at {observed_path}, but declares its "
            f"canonical location as {Path(declared_location).resolve()}; a relocated or "
            "copied issuance is not a second issuance"
        )
    raw_bindings = document.get("bindings")
    if not isinstance(raw_bindings, Mapping):
        raise OwnerExecutionAuthorizationError(
            "owner authorization carries no structured 'bindings' object; governed "
            "identities must be bound as fields, not present as loose text"
        )
    bindings: Mapping[str, Any] = raw_bindings
    mismatched = [
        name
        for name in OWNER_AUTHORIZATION_BINDING_FIELDS
        if bindings.get(name) != expected_bindings[name]
    ]
    if mismatched:
        raise OwnerExecutionAuthorizationError(
            f"owner authorization bindings do not match the running mission: {mismatched}"
        )
    # Cross-check the clearance itself, so an authorization cannot bind one set
    # of identities while the clearance carries another.
    clearance_conflicts = [
        name
        for name in (
            "stage_1_component_profile_sha256",
            "owner_preexecution_interpretation_sha256",
            "action_plan_sha256",
            "oracle_sha256",
            "adjudication_protocol_sha256",
            "mission_package_sha256",
        )
        if getattr(clearance, name) != bindings.get(name)
    ]
    if clearance_conflicts:
        raise OwnerExecutionAuthorizationError(
            f"clearance and owner authorization disagree on: {clearance_conflicts}"
        )
    return OwnerExecutionAuthorization(
        path=observed_path,
        sha256_hex=digest,
        byte_count=len(payload),
        reference=reference,
        authorized_stage=str(document["authorized_stage"]),
        record_class=str(document["record_class"]),
        authorization_scope=str(document["authorization_scope"]),
        authorization_id=str(document.get("authorization_id", "UNIDENTIFIED")),
        canonical_path=str(observed_path),
    )


# ---------------------------------------------------------------------------
# Single-use attempt state.
#
# "One run" has to be operational, not prose. The attempt record lives beside
# the authorization artifact at a path derived from that artifact's own digest,
# so a caller cannot pick a fresh location to get a second run. The claim is
# taken with an exclusive create immediately before the first governed
# evaluator invocation, which is also what makes two concurrent invocations
# impossible.
#
# CLAIMED and CONSUMED are deliberately different states. A crash between them
# leaves CLAIMED, which blocks automatic retry and requires an owner decision;
# it is never silently released.
# ---------------------------------------------------------------------------

ATTEMPT_STATE_NONE: Final = "NO_ATTEMPT_RECORD"
ATTEMPT_STATE_CLAIMED: Final = "CLAIMED_NOT_CONSUMED"
ATTEMPT_STATE_CONSUMED: Final = "CONSUMED_AFTER_GOVERNED_EVALUATOR_INVOCATION"


class MissionAttemptStateError(ResultBearingMissionBlockedError):
    """The authorization has already been claimed or consumed."""


@dataclass(frozen=True, slots=True)
class MissionAttemptRecord:
    """Immutable view of the attempt state for one authorization."""

    path: Path
    state: str
    owner_execution_authorization_sha256: str
    implementation_commit: str
    implementation_tree: str
    mission_package_sha256: str
    record_sha256: str = ""
    record_bytes: int = 0

    def as_record(self) -> dict[str, Any]:
        """The persisted payload. Deliberately does not contain its own digest."""
        return {
            "attempt_state": self.state,
            "owner_execution_authorization_sha256": self.owner_execution_authorization_sha256,
            "implementation_commit": self.implementation_commit,
            "implementation_tree": self.implementation_tree,
            "mission_package_sha256": self.mission_package_sha256,
        }

    def identity(self) -> dict[str, Any]:
        """Identity of the exact persisted bytes, for binding into Stage 1."""
        return {
            "attempt_state": self.state,
            "attempt_record_sha256": self.record_sha256,
            "attempt_record_bytes": self.record_bytes,
            "attempt_record_path": str(self.path),
            "owner_execution_authorization_sha256": self.owner_execution_authorization_sha256,
            "implementation_commit": self.implementation_commit,
            "implementation_tree": self.implementation_tree,
            "mission_package_sha256": self.mission_package_sha256,
        }


def attempt_record_identity_is_intact(record: Mapping[str, Any]) -> bool:
    """True when the bound identity reproduces the bytes on disk.

    Deletion or tampering of the local attempt ledger is detectable this way. It
    is not prevented: this is a filesystem, not an external immutable ledger.
    """
    path = Path(str(record.get("attempt_record_path")))
    if not path.exists():
        return False
    payload = path.read_bytes()
    if len(payload) != record.get("attempt_record_bytes"):
        return False
    if _file_sha256(payload) != record.get("attempt_record_sha256"):
        return False
    document = _require_mapping(json.loads(payload), "attempt record")
    return document.get("attempt_state") == record.get("attempt_state")


def attempt_record_path(authorization: OwnerExecutionAuthorization) -> Path:
    """Derived from the authorization's own identity; never caller-selected."""
    return authorization.path.parent / (f".cdc-e2e-stage-1-attempt-{authorization.sha256_hex}.json")


def read_attempt_state(authorization: OwnerExecutionAuthorization) -> str:
    """Current attempt state for this authorization."""
    path = attempt_record_path(authorization)
    if not path.exists():
        return ATTEMPT_STATE_NONE
    document = _require_mapping(json.loads(path.read_bytes()), "attempt record")
    return str(document.get("attempt_state"))


def require_unclaimed_attempt(authorization: OwnerExecutionAuthorization) -> None:
    """Refuse before any evaluator runs when the authorization is already used."""
    state = read_attempt_state(authorization)
    if state == ATTEMPT_STATE_NONE:
        return
    if state == ATTEMPT_STATE_CLAIMED:
        raise MissionAttemptStateError(
            f"authorization {authorization.reference} is {ATTEMPT_STATE_CLAIMED}: a prior "
            "attempt claimed it and no definitive consumption was recorded. Automatic "
            "retry is prohibited; this requires a separate owner decision."
        )
    raise MissionAttemptStateError(
        f"authorization {authorization.reference} is {state}: it authorized one "
        "result-bearing Stage-1 execution and is permanently non-reusable."
    )


def claim_attempt(
    authorization: OwnerExecutionAuthorization,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
) -> MissionAttemptRecord:
    """Atomically claim the single authorized attempt, or refuse.

    Exclusive create is the whole mechanism: if two invocations race, exactly
    one creates the file and the other fails here, before either reaches an
    evaluator.
    """
    record = MissionAttemptRecord(
        path=attempt_record_path(authorization),
        state=ATTEMPT_STATE_CLAIMED,
        owner_execution_authorization_sha256=authorization.sha256_hex,
        implementation_commit=runtime.implementation_commit,
        implementation_tree=runtime.implementation_tree,
        mission_package_sha256=frozen.package_sha256,
    )
    payload = (json.dumps(record.as_record(), indent=2, sort_keys=True) + "\n").encode()
    try:
        handle = os.open(record.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise MissionAttemptStateError(
            f"authorization {authorization.reference} was already claimed by another "
            "attempt; automatic retry is prohibited"
        ) from error
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)
    written = record.path.read_bytes()
    return replace(record, record_sha256=_file_sha256(written), record_bytes=len(written))


def mark_attempt_consumed(record: MissionAttemptRecord) -> MissionAttemptRecord:
    """Record that a governed evaluator was actually invoked.

    Called whether the evaluator returned or raised: invocation is what consumes
    the authorization, not success.
    """
    consumed = MissionAttemptRecord(
        path=record.path,
        state=ATTEMPT_STATE_CONSUMED,
        owner_execution_authorization_sha256=record.owner_execution_authorization_sha256,
        implementation_commit=record.implementation_commit,
        implementation_tree=record.implementation_tree,
        mission_package_sha256=record.mission_package_sha256,
    )
    record.path.write_bytes(
        (json.dumps(consumed.as_record(), indent=2, sort_keys=True) + "\n").encode()
    )
    written = record.path.read_bytes()
    return replace(consumed, record_sha256=_file_sha256(written), record_bytes=len(written))


def require_mission_execution_authorization(authorization: object) -> OwnerExecutionAuthorization:
    """Refuse anything that is not a verified authorization artifact."""
    if not isinstance(authorization, OwnerExecutionAuthorization):
        raise OwnerExecutionAuthorizationError(
            "mission execution requires an OwnerExecutionAuthorization verified from "
            "external bytes; a string, flag, environment value or mapping is not one"
        )
    return authorization


@dataclass(frozen=True, slots=True)
class FrozenComponentProfile:
    """Verified Stage-1 component semantics.

    Parsed only after the exact-byte identity check succeeds: a profile whose
    bytes do not match is never interpreted, so a mutated rule cannot reach
    semantic use even briefly.
    """

    path: Path
    sha256_hex: str
    byte_count: int
    profile_id: str
    required_facts: Mapping[str, tuple[str, ...]]
    preregistered_assignments: Mapping[str, Mapping[str, Mapping[str, tuple[bool, ...]]]]
    permitted_warrant_classes: tuple[str, ...]
    ztl_warrant_state: str

    def facts_for(self, control_id: str) -> tuple[str, ...]:
        """Required facts for a control, or refuse. Never guesses a vocabulary."""
        facts = self.required_facts.get(control_id)
        if facts is None:
            raise PreconditionMismatchError(
                f"the component profile designates no required facts for {control_id}"
            )
        return facts


def _profile_assignment_values(
    procedure: str, control_id: str, fact: object, values: object
) -> tuple[bool, ...]:
    """Preregistered assignment values must already be booleans. No coercion.

    Truthiness conversion would have silently turned "false", 0 or [] into a
    boolean. The frozen profile carries real booleans today, so this changes no
    current result; it removes the latent path.
    """
    admitted: list[bool] = []
    for value in _require_sequence(values, "assignment values"):
        if not isinstance(value, bool):
            raise ComponentProfileProvenanceError(
                f"PRECONDITION_MISMATCH_FAIL_CLOSED: preregistered assignment "
                f"{procedure}/{control_id}/{fact} carries {value!r} of type "
                f"{type(value).__name__}; only JSON booleans are admitted"
            )
        admitted.append(value)
    return tuple(admitted)


def verify_frozen_component_profile(path: Path) -> FrozenComponentProfile:
    """Verify exact profile bytes, then parse. Never the other way round."""
    payload = path.read_bytes()
    observed = _file_sha256(payload)
    if observed != STAGE_1_COMPONENT_PROFILE_SHA256:
        raise ComponentProfileProvenanceError(
            f"component profile digest is {observed}, expected {STAGE_1_COMPONENT_PROFILE_SHA256}"
        )
    document = _require_mapping(json.loads(payload), "component profile")
    if document.get("artifact_id") != STAGE_1_COMPONENT_PROFILE_ID:
        raise ComponentProfileProvenanceError("component profile identity mismatch")
    controls = _require_mapping(document.get("controls"), "profile.controls")
    required = {
        control_id: tuple(
            str(name)
            for name in _require_sequence(
                _require_mapping(body, "profile control").get("required_facts"), "required_facts"
            )
        )
        for control_id, body in controls.items()
    }
    raw_assignments = _require_mapping(
        document.get("preregistered_population_assignments"), "profile.assignments"
    )
    assignments: dict[str, dict[str, dict[str, tuple[bool, ...]]]] = {}
    for procedure, body in raw_assignments.items():
        if not isinstance(body, Mapping) or "controls" not in body:
            continue
        per_control: dict[str, dict[str, tuple[bool, ...]]] = {}
        for control_id, facts in _require_mapping(body["controls"], "assignment").items():
            per_control[control_id] = {
                str(fact): _profile_assignment_values(procedure, control_id, fact, values)
                for fact, values in _require_mapping(facts, "facts").items()
            }
        assignments[procedure] = per_control
    warrant = _require_mapping(document.get("warrant_builder"), "profile.warrant_builder")
    return FrozenComponentProfile(
        path=path,
        sha256_hex=observed,
        byte_count=len(payload),
        profile_id=str(document["artifact_id"]),
        required_facts=required,
        preregistered_assignments=assignments,
        permitted_warrant_classes=tuple(
            str(name)
            for name in _require_sequence(
                warrant.get("permitted_warrant_class"), "permitted_warrant_class"
            )
        ),
        ztl_warrant_state=str(warrant.get("ZTL_WARRANT")),
    )


def require_verified_component_profile(profile: object) -> FrozenComponentProfile:
    """Refuse anything that is not a verification of the exact profile bytes."""
    if not isinstance(profile, FrozenComponentProfile):
        raise ComponentProfileProvenanceError(
            "the component profile must be a FrozenComponentProfile verified from bytes; "
            "a mapping carrying the profile digest label is not the profile"
        )
    if profile != verify_frozen_component_profile(profile.path):
        raise ComponentProfileProvenanceError(
            "component profile does not recompute from the bytes on disk"
        )
    return profile


def _observed_values(evidence_bundle: Mapping[str, Any], fact: str) -> tuple[bool, ...]:
    """Admitted observation values for one fact, with no coercion whatsoever.

    A non-boolean observation is a fail-closed precondition mismatch, not a
    falsy value. ``0``, ``""``, ``null`` and ``"true"`` are all refused.
    """
    values: list[bool] = []
    for raw in _require_sequence(evidence_bundle.get("observations", []), "observations"):
        observation = _require_mapping(raw, "observation")
        if str(observation.get("fact")) != fact:
            continue
        value = observation.get("value")
        if not isinstance(value, bool):
            raise PreconditionMismatchError(
                f"PRECONDITION_MISMATCH_FAIL_CLOSED: observation for {fact!r} is "
                f"{value!r} of type {type(value).__name__}; only JSON booleans are admitted "
                "and no truthiness coercion is performed"
            )
        values.append(value)
    return tuple(values)


def evaluate_control(
    admitted_control: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
    admission_record: Mapping[str, Any],
    *,
    profile: object,
    mission_id: str,
    mission_authorization: object = None,
) -> dict[str, Any]:
    """The governed Stage-1 evaluator.

    Three semantically distinct inputs. The component profile is separately
    bound configuration supplied out of band, not a fourth mutable semantic
    input the caller may vary per chain.

    The decision order is exactly the frozen one and there is no fifth route:
    absence and conflict both resolve to UNRESOLVED and are tested *before*
    truth, so neither can fall through into BREACH. Absence is not false and
    conflict is not resolved by precedence or recency.
    """
    verified = require_verified_component_profile(profile)
    control_id = str(admitted_control["control_id"])
    procedure_id = str(admitted_control["procedure_id"])
    _require_mission_population_not_evaluated(mission_id, procedure_id, mission_authorization)
    facts = verified.facts_for(control_id)

    observations = {fact: _observed_values(evidence_bundle, fact) for fact in facts}
    absent = sorted(fact for fact, values in observations.items() if not values)
    conflicting = sorted(fact for fact, values in observations.items() if len(set(values)) > 1)

    if absent:
        verdict, reason, detail = VERDICT_UNRESOLVED, REASON_MISSING, absent
    elif conflicting:
        verdict, reason, detail = VERDICT_UNRESOLVED, REASON_CONFLICTING, conflicting
    elif all(values[0] for values in observations.values()):
        verdict, reason, detail = VERDICT_SATISFIED, REASON_ALL_SATISFIED, []
    else:
        verdict = VERDICT_BREACH
        reason = REASON_NOT_SATISFIED
        detail = sorted(fact for fact, values in observations.items() if values[0] is False)

    record: dict[str, Any] = {
        "evaluation_id": f"EVAL-{procedure_id}-{control_id}",
        "mission_id": mission_id,
        "procedure_id": procedure_id,
        "control_id": control_id,
        "admission_record_ref": str(admission_record["admission_id"]),
        "evidence_bundle_ref": str(evidence_bundle["evidence_bundle_id"]),
        "evidence_bundle_digest": sha256(evidence_bundle),
        "component_profile_id": verified.profile_id,
        "component_profile_sha256": verified.sha256_hex,
        "required_facts": list(facts),
        "observed_required_facts": {fact: list(values) for fact, values in observations.items()},
        "verdict": verdict,
        "reason_code": reason,
        "reason_detail_facts": detail,
        # on_unknown is admitted-control metadata. Stage 1 observes it and does
        # not apply it: applying it here would let the machine emit a
        # disposition, which is the human action plan's role, not the
        # evaluator's.
        "on_unknown_observed": admitted_control.get("on_unknown"),
        "on_unknown_applied": False,
        "non_application_reason": ON_UNKNOWN_NON_APPLICATION_REASON,
        "assurance_mode": ASSURANCE_MODE,
        "machine_disposition": None,
        "official_status": "NOT_AUTHORIZED_AS_OFFICIAL",
    }
    if verdict not in VERDICTS:
        raise MissionContractError(f"evaluator produced an ungoverned verdict: {verdict}")
    # One canonical identity: the digest is taken over the body that does not
    # contain it, and every downstream object reuses this exact value rather
    # than rehashing the digest-bearing record into a second identity.
    record["evaluation_digest"] = canonical_evaluation_digest(record)
    return record


def canonical_evaluation_digest(evaluation: Mapping[str, Any]) -> str:
    """The evaluation's canonical identity, excluding any claimed digest.

    Recomputable by a verifier: drop ``evaluation_digest`` and hash the rest, so
    the identity is never defined recursively over a record containing itself.
    """
    body = {key: value for key, value in evaluation.items() if key != "evaluation_digest"}
    return sha256(body)


def evaluation_digest_is_intact(evaluation: Mapping[str, Any]) -> bool:
    """True when the claimed digest matches the canonical digest of the body."""
    claimed = evaluation.get("evaluation_digest")
    return isinstance(claimed, str) and claimed == canonical_evaluation_digest(evaluation)


def build_fallback_warrant(
    evaluation: Mapping[str, Any], *, profile: object
) -> tuple[str, dict[str, Any]]:
    """The governed warrant builder. FALLBACK_WARRANT only; ZTL is not invoked.

    The artifact is provenance around a deterministic evaluation. It establishes
    no logical warrant, and it carries the evaluation's verdict through
    unchanged -- an UNRESOLVED evaluation stays UNRESOLVED.
    """
    verified = require_verified_component_profile(profile)
    if verified.ztl_warrant_state != ZTL_WARRANT_STATE:
        raise MissionContractError("the profile no longer prohibits ZTL_WARRANT")
    if tuple(verified.permitted_warrant_classes) != (FALLBACK_WARRANT_CLASS,):
        raise MissionContractError("the profile permits a warrant class this builder cannot emit")
    if not evaluation_digest_is_intact(evaluation):
        raise MissionContractError(
            "evaluation digest does not recompute from its body; the warrant would "
            "bind an identity that does not describe the evaluation it wraps"
        )
    verdict = str(evaluation["verdict"])
    if verdict not in VERDICTS:
        raise MissionContractError(f"evaluation carries an ungoverned verdict: {verdict}")
    warrant = {
        "warrant_id": f"FBW-{evaluation['procedure_id']}-{evaluation['control_id']}",
        "warrant_class": FALLBACK_WARRANT_CLASS,
        "mission_id": evaluation["mission_id"],
        "procedure_id": evaluation["procedure_id"],
        "control_id": evaluation["control_id"],
        "evaluation_id": evaluation["evaluation_id"],
        "evaluation_digest": evaluation["evaluation_digest"],
        "evaluation_verdict": verdict,
        "logical_warrant_status": "NOT_ESTABLISHED",
        "ztl_kernel_invoked": False,
        "fallback_basis": "DETERMINISTIC_EVALUATION_RECORD",
        "limitations": [NO_ZTL_DERIVATION],
    }
    return FALLBACK_WARRANT_CLASS, warrant


def _require_mission_population_not_evaluated(
    mission_id: str, procedure_id: str, authorization: object
) -> None:
    """Refuse to evaluate the frozen mission population without authorization.

    The implementation authorization permits building and testing these
    components; it does not permit producing the mission's actual nine
    outcomes. This interlock makes that structural rather than a matter of test
    discipline, so no unit, contract, integration or CI run can consume the one
    Stage-1 attempt by accident.
    """
    if mission_id != MISSION_ID or procedure_id not in FROZEN_MISSION_PROCEDURE_IDS:
        return
    if authorization is None:
        raise MissionPopulationExecutionBlockedError(
            f"result-bearing evaluation of the frozen mission population is not "
            f"authorized: {mission_id} / {procedure_id}. State is "
            f"{MISSION_POPULATION_EXECUTION_STATE}."
        )
    require_mission_execution_authorization(authorization)


def _require_mission_population_not_formed(
    projection: MissionProjection, authorization: object = None
) -> None:
    """Refuse Stage-1 candidate formation over the frozen mission population."""
    if (
        projection.mission_id != MISSION_ID
        or projection.package_sha256 != FROZEN_MISSION_PACKAGE_SHA256
    ):
        return
    if authorization is not None:
        require_mission_execution_authorization(authorization)
        return
    if True:
        raise MissionPopulationExecutionBlockedError(
            "Stage-1 candidate formation over the frozen mission population is not "
            f"authorized: package {FROZEN_MISSION_PACKAGE_SHA256}. State is "
            f"{MISSION_POPULATION_EXECUTION_STATE}. The implementation authorization "
            "covers building and testing the components, not producing the mission's "
            "actual nine outcomes."
        )


def require_evidence_matches_preregistered_assignments(
    projection: MissionProjection, profile: object
) -> dict[str, Any]:
    """Check package evidence against the frozen preregistered assignments.

    The assignments are a PREEXECUTION_CONFORMANCE_CONSTRAINT_ONLY. They are not
    runtime evidence and are never read in their place: this function compares
    and refuses, it does not supply. A mismatch is a fail-closed precondition
    mismatch, not something to reconcile.
    """
    verified = require_verified_component_profile(profile)
    checked: list[str] = []
    for chain in projection.chains:
        evidence = _require_mapping(chain.execution_input["evidence_bundle"], "evidence")
        control = _require_mapping(chain.execution_input["admitted_control"], "control")
        public_id = chain.procedure_id
        expected = verified.preregistered_assignments.get(public_id, {}).get(chain.control_id)
        if expected is None:
            raise PreconditionMismatchError(
                f"PRECONDITION_MISMATCH_FAIL_CLOSED: the profile preregisters no assignment "
                f"for {public_id} x {chain.control_id}"
            )
        observed = {
            fact: list(_observed_values(evidence, fact))
            for fact in verified.facts_for(str(control["control_id"]))
        }
        if observed != {fact: list(values) for fact, values in expected.items()}:
            raise PreconditionMismatchError(
                f"PRECONDITION_MISMATCH_FAIL_CLOSED: package evidence for {public_id} x "
                f"{chain.control_id} does not match the frozen preregistered assignment; "
                f"observed {observed}, preregistered "
                f"{ {fact: list(v) for fact, v in expected.items()} }"
            )
        checked.append(chain.chain_id)
    return {
        "constraint": "PREEXECUTION_CONFORMANCE_CONSTRAINT_ONLY",
        "assignments_are_runtime_evidence": False,
        "chains_checked": checked,
        "runtime_evidence_source": "input-v0.6 evidence_bundle",
        "fallback_to_profile_assignments": False,
    }


def governed_stage_1_components(
    profile: object, *, mission_id: str, mission_authorization: object = None
) -> tuple[EvaluationFunction, WarrantFunction]:
    """Bind the profile out of band and return the governed component pair.

    The profile is closed over here rather than passed per chain, so a caller
    driving Stage 1 has no parameter through which to vary the semantics between
    chains, and no way to supply a fourth mutable semantic input.
    """
    verified = require_verified_component_profile(profile)

    def evaluator(
        admitted_control: Mapping[str, Any],
        evidence_bundle: Mapping[str, Any],
        admission_record: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return evaluate_control(
            admitted_control,
            evidence_bundle,
            admission_record,
            profile=verified,
            mission_id=mission_id,
            mission_authorization=mission_authorization,
        )

    def warrant_builder(
        evaluation: Mapping[str, Any], admitted_control: Mapping[str, Any]
    ) -> tuple[str, Mapping[str, Any]]:
        del admitted_control
        return build_fallback_warrant(evaluation, profile=verified)

    return evaluator, warrant_builder


# ---------------------------------------------------------------------------
# M12 correction-successor boundary.
#
# The Stage-2 authorization that produced RUN-001 is permanently consumed, and
# its result is frozen evidence. Correction therefore cannot run through Stage 2
# again. This boundary executes the correction over the frozen RUN-001 result
# alone: it evaluates no transition, emits no event, renders no draft, and never
# opens a RUN-001 artifact for writing.
#
# The predecessor is preserved by construction. Its supersession is recorded on a
# separate successor-side object rather than written back, because a predecessor
# that changed to record its own supersession would no longer be the predecessor
# the adjudicator verified.
#
# The caller presents one thing: the authority instrument. Every historical fact
# that instrument binds -- where the frozen evidence lives, what it hashes to,
# which archive commit publishes it -- is resolved from the verified bindings.
# An operator who could point this route at relocated copies could satisfy the
# integrity checks against evidence of their own choosing.
# ---------------------------------------------------------------------------

EXPERIMENT_ID: Final = "CDC-END-TO-END-MISSION-001"

CORRECTION_SUCCESSOR_RECORD_CLASS: Final = "OWNER_CORRECTION_SUCCESSOR_EXECUTION_AUTHORIZATION"
CORRECTION_SUCCESSOR_STAGE: Final = "CORRECTION_SUCCESSOR_ONLY"
CORRECTION_SUCCESSOR_SCOPE: Final = "ONE_CORRECTION_SUCCESSOR_CONSTRUCTION"

# Frozen RUN-001 identities. These are historical facts about an execution that
# already happened; they cannot move because this implementation moved.
SOURCE_RUN_ID: Final = "CDC-E2E-STAGE2-RUN-001"
SOURCE_STAGE_2_RESULT_DIGEST: Final = (
    "8a12b681d1f08aa47b70830a939da9d545dccdcea33643fc6f5f6ca9450b3b40"
)
SOURCE_STAGE_2_RAW_RESULT_SHA256: Final = (
    "715a97038be184f5f0715a9e53d9ceb9150bf74b72e1ff2f4d27654c2b61d45d"
)
SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256: Final = (
    "0d11efa747647bf6764bb7562b3a8e7b02219ed2b10f527ce4b5e69df3ca72d2"
)
SOURCE_STAGE_2_ROUTE_TRACE_SHA256: Final = (
    "481957e87f73e2fc058e0e167b6d3d82fea830b2eaad16c78bdfc39f3c952920"
)
EVIDENCE_REPOSITORY: Final = "veraxis-protocol/Institutional-Compiler"
EVIDENCE_BRANCH: Final = "cdc-e2e-stage2-run-001-evidence"
STAGE_2_EVIDENCE_COMMIT: Final = "1a80aabe0f72eac8570b9827ee7545cda370cbe8"
STAGE_2_EVIDENCE_TREE: Final = "a6216214ae5a49ffcb3448a97aadce1bb3f418e3"
OWNER_ADJUDICATION_ACCEPTANCE_COMMIT: Final = "ceb8efe293776696d6633bc3994b23198030e5b0"
OWNER_ADJUDICATION_ACCEPTANCE_SHA256: Final = (
    "49435cbb6e955f4ecd6c36b3b1c0ab8b4c77c53bb564569b8708be036586f9b0"
)
STAGE_2_ADJUDICATION_COMMIT: Final = "a682abc7e68a3fc98c3a131c10d9ec05457e5d9c"
STAGE_2_ADJUDICATION_SHA256: Final = (
    "6983daf7153f3e409bcd4503d286ec116233e7b4979088c07be935dc15994eb6"
)

# Filenames inside the authorized evidence directory. Fixed here rather than
# supplied, so a bound location cannot be re-aimed at a different artifact.
SOURCE_STAGE_2_RAW_RESULT_FILENAME: Final = (
    "CDC-END-TO-END-MISSION-001-STAGE-2-RAW-RESULT-v0.1.json"
)
SOURCE_STAGE_2_ROUTE_TRACE_FILENAME: Final = (
    "CDC-END-TO-END-MISSION-001-STAGE-2-ROUTE-TRACE-v0.1.json"
)
SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME: Final = (
    ".cdc-e2e-stage-2-attempt-42b3c3d1285a0fddc36558875cc9df2e90b283ec79d96a56408b0fbc6f8c5f41.json"
)

STAGE_2_CONSUMED_ATTEMPT_STATE: Final = ATTEMPT_STATE_STAGE_2_CONSUMED

CORRECTION_SUCCESSOR_DECLARATIONS: Final[dict[str, object]] = {
    "record_class": CORRECTION_SUCCESSOR_RECORD_CLASS,
    "experiment_id": EXPERIMENT_ID,
    "runtime_mission_id": MISSION_ID,
    "owner_authorized": True,
    "authorized_stage": CORRECTION_SUCCESSOR_STAGE,
    "authorization_scope": CORRECTION_SUCCESSOR_SCOPE,
    "single_use": True,
    "automatic_retry_authorized": False,
    "stage_1_reexecution_authorized": False,
    "stage_2_reexecution_authorized": False,
    "transition_evaluation_authorized": False,
    "transition_event_emission_authorized": False,
    "draft_rendering_authorized": False,
    "run_001_modification_authorized": False,
    "m11_repair_authorized": False,
    "official_handoff_authorized": False,
    "result_bearing": True,
}

CORRECTION_INSTRUCTION_RECORD_CLASS: Final = "OWNER_CORRECTION_INSTRUCTION"

# What the owner authors, and therefore what the authorization must fix exactly.
CORRECTION_INSTRUCTION_OWNER_AUTHORED_FIELDS: Final = (
    "new_ebawu_or_successor_id",
    "new_candidate_digest",
    "correction_reason",
    "changed_fact_or_control_refs",
    "new_state",
    "correction_event_id",
    "affected_output_refs",
)

# Derived from the frozen predecessor or produced after authorization. An
# instruction that carried these would be asserting values it does not get to
# choose, so their presence is refused rather than ignored.
CORRECTION_INSTRUCTION_DERIVED_FIELDS: Final = (
    "prior_state",
    "reliance_impact_refs",
    "superseded_at_utc",
    "superseded_by",
    "supersedes",
)

CORRECTION_FIELD_AUTHORITY: Final[dict[str, str]] = {
    "new_ebawu_or_successor_id": "OWNER_AUTHORED",
    "new_candidate_digest": "OWNER_AUTHORED",
    "correction_reason": "OWNER_AUTHORED",
    "changed_fact_or_control_refs": "OWNER_AUTHORED",
    "new_state": "OWNER_AUTHORED",
    "correction_event_id": "OWNER_AUTHORED",
    "affected_output_refs": "OWNER_AUTHORED",
    "predecessor_digest": "FROZEN_PREDECESSOR_DERIVED",
    "supersedes": "FROZEN_PREDECESSOR_DERIVED",
    "prior_state": "FROZEN_PREDECESSOR_DERIVED",
    "superseded_by": "SYSTEM_DERIVED_AFTER_AUTHORIZATION",
    "reliance_impact_refs": "SYSTEM_DERIVED_AFTER_AUTHORIZATION",
    "superseded_at_utc": "SYSTEM_DERIVED_AFTER_AUTHORIZATION",
    "affected_output_eligibility": "SYSTEM_DERIVED_AFTER_AUTHORIZATION",
}

CORRECTION_SUCCESSOR_BINDING_FIELDS: Final = (
    "correction_instruction_id",
    "correction_instruction_path",
    "correction_instruction_sha256",
    "correction_instruction_bytes",
    "implementation_commit",
    "implementation_tree",
    "environment_manifest_sha256",
    "mission_package_sha256",
    "oracle_sha256",
    "adjudication_protocol_sha256",
    "action_plan_sha256",
    "action_plan_provenance_token",
    "correction_stimulus_digest",
    "source_run_id",
    "source_evidence_root",
    "source_stage_1_observation_digest",
    "source_stage_2_result_digest",
    "source_stage_2_raw_result_sha256",
    "source_stage_2_attempt_record_sha256",
    "source_stage_2_route_trace_sha256",
    "evidence_repository",
    "evidence_branch",
    "stage_2_evidence_commit",
    "stage_2_evidence_tree",
    "owner_acceptance_commit",
    "owner_acceptance_sha256",
    "adjudication_commit",
    "adjudication_sha256",
    "predecessor_ebawu_ref",
    "correction_target_id",
    "successor_id",
)

# An instrument states what is authorized. Whether it was issued is established
# by a separate issuance record, so an instrument that asserts its own issuance
# state is refused rather than read charitably.
CORRECTION_SUCCESSOR_FORBIDDEN_SELF_ASSERTIONS: Final = (
    "attempt_state",
    "consumed",
    "correction_executed",
    "is_issued",
    "issuance_observed",
    "issuance_observed_at_utc",
    "issued",
    "successor_constructed",
)

CORRECTION_ATTEMPT_STATE_NONE: Final = "NO_ATTEMPT_RECORD"
CORRECTION_ATTEMPT_STATE_CLAIMED: Final = "CLAIMED_NOT_CONSUMED"
CORRECTION_ATTEMPT_STATE_CONSUMED: Final = "CONSUMED_AFTER_FIRST_SUCCESSOR_CONSTRUCTION"

CORRECTION_INELIGIBILITY_STATE: Final = (
    "INELIGIBLE_PENDING_REGENERATION_OR_EXPLICIT_HUMAN_RESOLUTION"
)
CORRECTION_IMPACT_AFFECTED: Final = "AFFECTED_BY_SUPERSESSION"
CORRECTION_IMPACT_UNAFFECTED: Final = "NOT_AFFECTED_BY_SUPERSESSION"

RESULT_STATUS_FAILED_POST_CONSTRUCTION: Final = "FAILED_POST_CONSTRUCTION_INTEGRITY"


class CorrectionSuccessorAuthorizationError(ResultBearingMissionBlockedError):
    """The correction-successor authorization is absent, wrong, unbound or relocated."""


class CorrectionSuccessorBlockedError(ResultBearingMissionBlockedError):
    """A correction-successor precondition failed before anything was claimed."""


class CorrectionEvidenceInfrastructureError(ResultBearingMissionBlockedError):
    """The bound archive identity could not be observed at all.

    Distinct from a mismatch on purpose: an unobservable archive is an
    infrastructure failure and must never be recorded as a match.
    """


class CorrectionInstructionError(ResultBearingMissionBlockedError):
    """The authorized correction instruction is absent, wrong or relocated."""


class PredecessorMutationDetectedError(ResultBearingMissionBlockedError):
    """Frozen predecessor evidence changed across the correction."""


class PostConstructionIntegrityError(ResultBearingMissionBlockedError):
    """A successor was constructed, then an integrity observation failed.

    The authority is already exercised. This carries the frozen observation so the
    failure can be recorded without either persisting an invalid correction result
    or pretending no successor was ever constructed.
    """

    def __init__(self, message: str, observation: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.observation = dict(observation)


class CorrectionAttemptStateError(MissionAttemptStateError):
    """The correction-successor authorization was already claimed or consumed."""


@dataclass(frozen=True, slots=True)
class CorrectionExecutionClearance:
    """Runtime clearance for the correction successor.

    Deliberately separate from ExecutionClearance: a Stage-2 clearance must never
    be reusable as authority to correct.
    """

    owner_correction_authorization: str
    implementation_commit: str
    implementation_tree: str
    environment_manifest_sha256: str
    mission_package_sha256: str
    oracle_sha256: str
    adjudication_protocol_sha256: str
    action_plan_sha256: str
    owner_acceptance_sha256: str
    source_stage_2_result_digest: str


@dataclass(frozen=True, slots=True)
class OwnerCorrectionSuccessorAuthorization:
    """A correction-successor authorization verified from exact external bytes."""

    path: Path
    sha256_hex: str
    byte_count: int
    reference: str
    record_class: str
    authorized_stage: str
    authorization_scope: str
    authorization_id: str
    canonical_path: str
    successor_id: str
    evidence_root: Path
    evidence_repository: str
    evidence_branch: str
    stage_1_observation_digest: str
    correction_instruction_id: str
    correction_instruction_path: Path
    correction_instruction_sha256: str
    correction_instruction_bytes: int

    def as_record(self) -> dict[str, Any]:
        """Identity and declared scope only; carries no authorization prose."""
        return {
            "owner_correction_authorization_sha256": self.sha256_hex,
            "owner_correction_authorization_bytes": self.byte_count,
            "owner_correction_authorization_reference": self.reference,
            "owner_correction_authorization_record_class": self.record_class,
            "owner_correction_authorization_scope": self.authorization_scope,
            "owner_correction_authorization_id": self.authorization_id,
            "authorized_stage": self.authorized_stage,
            "authorized_successor_id": self.successor_id,
            "authorized_evidence_root": str(self.evidence_root),
            "authorized_evidence_repository": self.evidence_repository,
            "authorized_evidence_branch": self.evidence_branch,
            "authorized_correction_instruction_id": self.correction_instruction_id,
            "authorized_correction_instruction_sha256": self.correction_instruction_sha256,
            "authorized_correction_instruction_bytes": self.correction_instruction_bytes,
        }


@dataclass(frozen=True, slots=True)
class OwnerCorrectionInstruction:
    """The exact correction semantics one authorization permits.

    Authority to execute a correction is not authority to execute *this*
    correction, so the payload is an owner-reviewed artifact bound by digest
    rather than a mapping the operator supplies at call time.
    """

    path: Path
    sha256_hex: str
    byte_count: int
    instruction_id: str
    declared_predecessor_digest: str
    owner_authored: Mapping[str, Any]

    def as_correction(self, predecessor_digest: str) -> dict[str, Any]:
        """The correction payload, carrying only owner-authored values."""
        return {**dict(self.owner_authored), "predecessor_digest": predecessor_digest}

    def as_record(self) -> dict[str, Any]:
        """Identity and authored semantics; no derived value appears here."""
        return {
            "correction_instruction_id": self.instruction_id,
            "correction_instruction_sha256": self.sha256_hex,
            "correction_instruction_bytes": self.byte_count,
            "correction_instruction_path": str(self.path),
            "owner_authored_fields": sorted(self.owner_authored),
            "declared_predecessor_digest": self.declared_predecessor_digest,
            "field_authority": dict(CORRECTION_FIELD_AUTHORITY),
            "caller_selectable": False,
        }


@dataclass(frozen=True, slots=True)
class AuthorizedEvidenceLocations:
    """The exact evidence files resolved from the verified authorization."""

    root: Path
    raw_result: Path
    attempt_record: Path
    route_trace: Path

    def as_record(self) -> dict[str, Any]:
        """Where the frozen bytes were actually read from."""
        return {
            "evidence_root": str(self.root),
            "raw_result_path": str(self.raw_result),
            "attempt_record_path": str(self.attempt_record),
            "route_trace_path": str(self.route_trace),
            "locations_derived_from": "VERIFIED_AUTH_003_BINDINGS",
            "caller_selectable": False,
        }


@dataclass(frozen=True, slots=True)
class FrozenStage2Evidence:
    """The RUN-001 result, verified from its exact frozen bytes."""

    raw_result_sha256: str
    raw_result_bytes: int
    result_digest: str
    runtime_mission_id: str
    outcomes: tuple[Mapping[str, Any], ...]
    drafts: tuple[Mapping[str, Any], ...]
    attempt_record: Mapping[str, Any]

    def outcome_for_chain(self, chain_id: str) -> Mapping[str, Any] | None:
        """The frozen outcome for one chain, or None when the chain is absent."""
        return next((item for item in self.outcomes if item.get("chain_id") == chain_id), None)


@dataclass(frozen=True, slots=True)
class CorrectionSuccessorResult:
    """Immutable correction-successor result. Never an official CDC record."""

    experiment_id: str
    runtime_mission_id: str
    source_run_id: str
    source_stage_2_result_digest: str
    source_stage_2_raw_result_sha256: str
    evidence_locations: Mapping[str, Any]
    owner_correction_authorization: Mapping[str, Any]
    correction_instruction: Mapping[str, Any]
    correction_stimulus: Mapping[str, Any]
    predecessor: Mapping[str, Any]
    predecessor_digest: str
    successor: Mapping[str, Any]
    predecessor_supersession_record: Mapping[str, Any]
    correction_reason: str
    changed_fact_or_control_refs: Sequence[Any]
    affected_output_eligibility: Sequence[Mapping[str, Any]]
    stale_proposal_refusal_observation: Mapping[str, Any]
    predecessor_immutability: Mapping[str, Any]
    archive_identity: Mapping[str, Any]
    attempt_record: Mapping[str, Any] | None
    successor_construction_invoked: bool = True
    successor_constructed: bool = True
    correction_executed: bool = True
    stage_2_reexecuted: bool = False
    run_001_modified: bool = False
    m11_repaired: bool = False
    official_handoff: str = OFFICIAL_CDC_RECORD_CREATION
    claim_ceiling: str = ASSURANCE_MODE

    def as_record(self) -> dict[str, Any]:
        """JSON-safe record carrying its own contract digest."""
        body = {
            "experiment_id": self.experiment_id,
            "runtime_mission_id": self.runtime_mission_id,
            "source_run_id": self.source_run_id,
            "source_stage_2_result_digest": self.source_stage_2_result_digest,
            "source_stage_2_raw_result_sha256": self.source_stage_2_raw_result_sha256,
            "evidence_locations": dict(self.evidence_locations),
            "owner_correction_authorization": dict(self.owner_correction_authorization),
            "correction_instruction": dict(self.correction_instruction),
            "correction_stimulus": dict(self.correction_stimulus),
            "predecessor": dict(self.predecessor),
            "predecessor_digest": self.predecessor_digest,
            "successor": dict(self.successor),
            "predecessor_supersession_record": dict(self.predecessor_supersession_record),
            "correction_reason": self.correction_reason,
            "changed_fact_or_control_refs": list(self.changed_fact_or_control_refs),
            "affected_output_eligibility": [
                dict(item) for item in self.affected_output_eligibility
            ],
            "stale_proposal_refusal_observation": dict(self.stale_proposal_refusal_observation),
            "predecessor_immutability": dict(self.predecessor_immutability),
            "archive_identity": dict(self.archive_identity),
            "attempt_record": (None if self.attempt_record is None else dict(self.attempt_record)),
            "successor_construction_invoked": self.successor_construction_invoked,
            "successor_constructed": self.successor_constructed,
            "correction_executed": self.correction_executed,
            "stage_2_reexecuted": self.stage_2_reexecuted,
            "run_001_modified": self.run_001_modified,
            "m11_repaired": self.m11_repaired,
            "official_handoff": self.official_handoff,
            "claim_ceiling": self.claim_ceiling,
        }
        body["correction_successor_result_digest"] = sha256(body)
        return body


def verify_frozen_stage_2_evidence(payload: bytes) -> FrozenStage2Evidence:
    """Verify the frozen RUN-001 result from its exact bytes.

    Both identities are checked and kept distinct: the file SHA-256 of the
    persisted bytes, and the embedded contract digest recomputed over the body
    that excludes it.
    """
    observed_file_sha = _file_sha256(payload)
    if observed_file_sha != SOURCE_STAGE_2_RAW_RESULT_SHA256:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 raw result hashes to {observed_file_sha}, expected "
            f"{SOURCE_STAGE_2_RAW_RESULT_SHA256}"
        )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 raw result is not structured JSON: {error}"
        ) from error
    record = _require_mapping(document, "stage-2 result")
    embedded = record.get("stage_2_result_digest")
    recomputed = sha256({k: v for k, v in record.items() if k != "stage_2_result_digest"})
    if embedded != recomputed:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 result carries digest {embedded!r} but its body recomputes "
            f"to {recomputed!r}"
        )
    if recomputed != SOURCE_STAGE_2_RESULT_DIGEST:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 result digest is {recomputed}, expected {SOURCE_STAGE_2_RESULT_DIGEST}"
        )
    attempt = _require_mapping(record.get("attempt_record"), "stage-2 attempt record")
    if attempt.get("attempt_state") != STAGE_2_CONSUMED_ATTEMPT_STATE:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 attempt state is {attempt.get('attempt_state')!r}; the "
            f"correction successor requires {STAGE_2_CONSUMED_ATTEMPT_STATE}"
        )
    return FrozenStage2Evidence(
        raw_result_sha256=observed_file_sha,
        raw_result_bytes=len(payload),
        result_digest=recomputed,
        runtime_mission_id=str(record.get("mission_id")),
        outcomes=tuple(
            _require_mapping(item, "outcome")
            for item in _require_sequence(record.get("outcomes"), "outcomes")
        ),
        drafts=tuple(
            _require_mapping(item, "draft")
            for item in _require_sequence(record.get("drafts"), "drafts")
        ),
        attempt_record=attempt,
    )


def require_distinct_identity_namespaces(
    evidence: FrozenStage2Evidence, stage_1: Stage1Observation
) -> None:
    """Keep the experiment and runtime identities separate and correctly sourced.

    The owner acceptance belongs to the experiment identity; the frozen runtime
    result and Stage-1 observation carry the runtime mission identity. Each is
    checked against its own source, so neither can vouch for the other.
    """
    if evidence.runtime_mission_id != MISSION_ID:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 result carries runtime mission {evidence.runtime_mission_id!r}, "
            f"expected {MISSION_ID!r}"
        )
    if stage_1.mission_id != MISSION_ID:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-1 observation carries runtime mission {stage_1.mission_id!r}, "
            f"expected {MISSION_ID!r}"
        )
    if EXPERIMENT_ID in {evidence.runtime_mission_id, stage_1.mission_id}:
        raise CorrectionSuccessorBlockedError(
            "the experiment identity was substituted for the runtime mission identity"
        )


def verify_owner_correction_successor_authorization(
    path: Path,
    *,
    clearance: CorrectionExecutionClearance,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
    action_plan: object,
) -> OwnerCorrectionSuccessorAuthorization:
    """Verify a correction-successor authorization: identity, location, semantics, bindings.

    Same three-part discipline as the Stage-2 instrument, and the same canonical
    location rule: a byte-identical copy elsewhere is not a second issuance. The
    frozen source-run identities are compared against this module's constants
    rather than against anything the caller supplied.
    """
    plan = require_verified_action_plan(action_plan)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise CorrectionSuccessorAuthorizationError(
            f"correction-successor authorization is not readable at {path}: {error}"
        ) from error
    file_digest = _file_sha256(payload)
    reference = f"{OWNER_AUTHORIZATION_REFERENCE_PREFIX}{file_digest}"
    observed_path = path.resolve()
    if clearance.owner_correction_authorization != reference:
        raise CorrectionSuccessorAuthorizationError(
            f"clearance owner_correction_authorization is "
            f"{clearance.owner_correction_authorization!r}, but the supplied artifact "
            f"hashes to {reference!r}; a label is not the artifact"
        )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise CorrectionSuccessorAuthorizationError(
            f"correction-successor authorization is not structured JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization must be a JSON object"
        )
    declared_location = document.get("canonical_authorization_path")
    if not isinstance(declared_location, str) or not declared_location:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization declares no canonical_authorization_path"
        )
    if Path(declared_location).resolve() != observed_path:
        raise CorrectionSuccessorAuthorizationError(
            f"correction-successor authorization was presented at {observed_path} but "
            f"declares {Path(declared_location).resolve()}; a relocated copy is not a "
            "second issuance"
        )
    self_asserted = sorted(
        name for name in CORRECTION_SUCCESSOR_FORBIDDEN_SELF_ASSERTIONS if name in document
    )
    if self_asserted:
        raise CorrectionSuccessorAuthorizationError(
            f"the instrument asserts its own issuance or execution state: {self_asserted}; "
            "issuance is established by the separate issuance record"
        )
    wrong = [
        f"{name}={document.get(name)!r} (required {expected!r})"
        for name, expected in CORRECTION_SUCCESSOR_DECLARATIONS.items()
        if document.get(name) is not expected and document.get(name) != expected
    ]
    if wrong:
        raise CorrectionSuccessorAuthorizationError(
            f"the artifact does not declare correction-successor semantics: {wrong}"
        )
    raw_bindings = document.get("bindings")
    if not isinstance(raw_bindings, Mapping):
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization carries no structured 'bindings' object"
        )
    missing = sorted(set(CORRECTION_SUCCESSOR_BINDING_FIELDS) - raw_bindings.keys())
    if missing:
        raise CorrectionSuccessorAuthorizationError(
            f"correction-successor authorization bindings missing: {missing}"
        )
    observed_bindings = {
        "implementation_commit": runtime.implementation_commit,
        "implementation_tree": runtime.implementation_tree,
        "environment_manifest_sha256": runtime.environment_manifest_sha256,
        "mission_package_sha256": frozen.package_sha256,
        "oracle_sha256": ORACLE_SHA256,
        "adjudication_protocol_sha256": ADJUDICATION_PROTOCOL_SHA256,
        "action_plan_sha256": plan.sha256_hex,
        "action_plan_provenance_token": plan.provenance_token,
        "correction_stimulus_digest": plan.correction.digest(),
        "source_run_id": SOURCE_RUN_ID,
        "source_stage_2_result_digest": SOURCE_STAGE_2_RESULT_DIGEST,
        "source_stage_2_raw_result_sha256": SOURCE_STAGE_2_RAW_RESULT_SHA256,
        "source_stage_2_attempt_record_sha256": SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256,
        "source_stage_2_route_trace_sha256": SOURCE_STAGE_2_ROUTE_TRACE_SHA256,
        "evidence_repository": EVIDENCE_REPOSITORY,
        "evidence_branch": EVIDENCE_BRANCH,
        "stage_2_evidence_commit": STAGE_2_EVIDENCE_COMMIT,
        "stage_2_evidence_tree": STAGE_2_EVIDENCE_TREE,
        "owner_acceptance_commit": OWNER_ADJUDICATION_ACCEPTANCE_COMMIT,
        "owner_acceptance_sha256": OWNER_ADJUDICATION_ACCEPTANCE_SHA256,
        "adjudication_commit": STAGE_2_ADJUDICATION_COMMIT,
        "adjudication_sha256": STAGE_2_ADJUDICATION_SHA256,
        "predecessor_ebawu_ref": plan.correction.predecessor_ebawu_ref,
        "correction_target_id": plan.correction.target_id,
    }
    mismatched = sorted(
        name for name, value in observed_bindings.items() if raw_bindings.get(name) != value
    )
    if mismatched:
        raise CorrectionSuccessorAuthorizationError(
            f"correction-successor bindings do not match the running observation: {mismatched}"
        )
    successor_id = raw_bindings.get("successor_id")
    if not isinstance(successor_id, str) or not successor_id:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a successor_id"
        )
    evidence_root = raw_bindings.get("source_evidence_root")
    if not isinstance(evidence_root, str) or not evidence_root:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a source_evidence_root"
        )
    stage_1_digest = raw_bindings.get("source_stage_1_observation_digest")
    if not isinstance(stage_1_digest, str) or not stage_1_digest:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a Stage-1 observation digest"
        )
    instruction_id = raw_bindings.get("correction_instruction_id")
    instruction_path = raw_bindings.get("correction_instruction_path")
    instruction_sha256 = raw_bindings.get("correction_instruction_sha256")
    instruction_bytes = raw_bindings.get("correction_instruction_bytes")
    if not isinstance(instruction_id, str) or not instruction_id:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a correction_instruction_id"
        )
    if not isinstance(instruction_path, str) or not instruction_path:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a correction_instruction_path"
        )
    if not isinstance(instruction_sha256, str) or len(instruction_sha256) != 64:
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind a correction_instruction_sha256"
        )
    if not isinstance(instruction_bytes, int) or isinstance(instruction_bytes, bool):
        raise CorrectionSuccessorAuthorizationError(
            "correction-successor authorization does not bind correction_instruction_bytes"
        )
    if clearance.source_stage_2_result_digest != SOURCE_STAGE_2_RESULT_DIGEST:
        raise CorrectionSuccessorAuthorizationError(
            f"clearance binds Stage-2 result {clearance.source_stage_2_result_digest!r}, "
            f"expected {SOURCE_STAGE_2_RESULT_DIGEST!r}"
        )
    if clearance.owner_acceptance_sha256 != OWNER_ADJUDICATION_ACCEPTANCE_SHA256:
        raise CorrectionSuccessorAuthorizationError(
            "clearance does not carry the owner adjudication acceptance digest"
        )
    return OwnerCorrectionSuccessorAuthorization(
        path=observed_path,
        sha256_hex=file_digest,
        byte_count=len(payload),
        reference=reference,
        record_class=str(document["record_class"]),
        authorized_stage=str(document["authorized_stage"]),
        authorization_scope=str(document["authorization_scope"]),
        authorization_id=str(document.get("authorization_id", "UNIDENTIFIED")),
        canonical_path=str(observed_path),
        successor_id=successor_id,
        evidence_root=Path(evidence_root),
        evidence_repository=str(raw_bindings["evidence_repository"]),
        evidence_branch=str(raw_bindings["evidence_branch"]),
        stage_1_observation_digest=stage_1_digest,
        correction_instruction_id=instruction_id,
        correction_instruction_path=Path(instruction_path),
        correction_instruction_sha256=instruction_sha256,
        correction_instruction_bytes=instruction_bytes,
    )


def verify_owner_correction_instruction(
    authorization: OwnerCorrectionSuccessorAuthorization, action_plan: object
) -> OwnerCorrectionInstruction:
    """Read the exact correction instruction the authorization binds.

    The location, the identifier and the digest all come from the verified
    authorization, so the operator cannot present different semantics under an
    issued authority.
    """
    plan = require_verified_action_plan(action_plan)
    path = authorization.correction_instruction_path
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise CorrectionInstructionError(
            f"the authorized correction instruction is not readable at {path}: {error}"
        ) from error
    observed_sha = _file_sha256(payload)
    if observed_sha != authorization.correction_instruction_sha256:
        raise CorrectionInstructionError(
            f"the correction instruction at {path} hashes to {observed_sha}, but the "
            f"authorization binds {authorization.correction_instruction_sha256}; a "
            "substituted instruction is not the authorized correction"
        )
    if len(payload) != authorization.correction_instruction_bytes:
        raise CorrectionInstructionError(
            f"the correction instruction is {len(payload)} bytes, but the authorization "
            f"binds {authorization.correction_instruction_bytes}"
        )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise CorrectionInstructionError(
            f"the correction instruction is not structured JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise CorrectionInstructionError("the correction instruction must be a JSON object")
    declarations = {
        "record_class": CORRECTION_INSTRUCTION_RECORD_CLASS,
        "experiment_id": EXPERIMENT_ID,
        "runtime_mission_id": MISSION_ID,
        "correction_stimulus_id": plan.correction.correction_stimulus_id,
        "correction_target_id": plan.correction.target_id,
        "predecessor_ebawu_ref": plan.correction.predecessor_ebawu_ref,
        "correction_instruction_id": authorization.correction_instruction_id,
    }
    wrong = sorted(
        f"{name}={document.get(name)!r} (required {expected!r})"
        for name, expected in declarations.items()
        if document.get(name) != expected
    )
    if wrong:
        raise CorrectionInstructionError(
            f"the correction instruction does not declare the authorized correction: {wrong}"
        )
    missing = sorted(set(CORRECTION_INSTRUCTION_OWNER_AUTHORED_FIELDS) - document.keys())
    if missing:
        raise CorrectionInstructionError(
            f"the correction instruction omits owner-authored fields: {missing}"
        )
    derived_present = sorted(
        name for name in CORRECTION_INSTRUCTION_DERIVED_FIELDS if name in document
    )
    if derived_present:
        raise CorrectionInstructionError(
            f"the correction instruction asserts derived fields it does not author: "
            f"{derived_present}"
        )
    declared_predecessor = document.get("predecessor_digest")
    if not isinstance(declared_predecessor, str) or not declared_predecessor:
        raise CorrectionInstructionError(
            "the correction instruction declares no predecessor_digest"
        )
    return OwnerCorrectionInstruction(
        path=path.resolve(),
        sha256_hex=observed_sha,
        byte_count=len(payload),
        instruction_id=str(document["correction_instruction_id"]),
        declared_predecessor_digest=declared_predecessor,
        owner_authored={
            name: document[name] for name in CORRECTION_INSTRUCTION_OWNER_AUTHORED_FIELDS
        },
    )


def resolve_authorized_evidence_locations(
    authorization: OwnerCorrectionSuccessorAuthorization,
) -> AuthorizedEvidenceLocations:
    """Derive the exact evidence file locations from the verified authorization."""
    root = authorization.evidence_root
    return AuthorizedEvidenceLocations(
        root=root,
        raw_result=root / SOURCE_STAGE_2_RAW_RESULT_FILENAME,
        attempt_record=root / SOURCE_STAGE_2_ATTEMPT_RECORD_FILENAME,
        route_trace=root / SOURCE_STAGE_2_ROUTE_TRACE_FILENAME,
    )


def load_authorized_stage_2_evidence(
    locations: AuthorizedEvidenceLocations,
) -> FrozenStage2Evidence:
    """Read and verify the frozen Stage-2 result from the authorized location."""
    try:
        payload = locations.raw_result.read_bytes()
    except OSError as error:
        raise CorrectionSuccessorBlockedError(
            f"authorized Stage-2 evidence is not readable at {locations.raw_result}: {error}"
        ) from error
    return verify_frozen_stage_2_evidence(payload)


ARCHIVE_OBSERVATION_SOURCE: Final = "ORIGIN_LS_REMOTE"
_COMMIT_SHA_LENGTH: Final = 40


def _git(repo_root: Path, *arguments: str) -> str:
    """Run one git command, or report an infrastructure failure.

    The single seam through which the archive observation reaches git, so tests
    can drive it without the public route ever exposing an injection point.
    """
    executable = shutil.which("git")
    if executable is None:
        raise CorrectionEvidenceInfrastructureError(
            "git is unavailable, so the bound evidence archive identity cannot be observed"
        )
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, resolved executable, no shell
            [executable, "-C", str(repo_root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise CorrectionEvidenceInfrastructureError(
            f"git {' '.join(arguments)} failed: {error}"
        ) from error
    return completed.stdout.strip()


def _normalize_repository(remote_url: str) -> str:
    """Reduce an origin URL to its owner/name form."""
    trimmed = remote_url.removesuffix(".git")
    for prefix in ("https://github.com/", "git@github.com:", "ssh://git@github.com/"):
        trimmed = trimmed.removeprefix(prefix)
    return trimmed


def _observe_git_archive_identity(repo_root: Path, branch: str) -> dict[str, str]:
    """Observe the published archive identity from origin itself.

    The commit comes from ``git ls-remote``, never from a local branch ref: a
    local ref says only what this working copy believes, which is exactly what an
    archive observation must not rely on. The tree is derived from the commit
    object only after origin has supplied that exact SHA, because the SHA fixes
    the commit's contents.
    """
    listed = _git(repo_root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    rows = [line for line in listed.splitlines() if line.strip()]
    if not rows:
        raise CorrectionEvidenceInfrastructureError(
            f"origin publishes no branch {branch!r}; the bound archive identity cannot be observed"
        )
    if len(rows) > 1:
        raise CorrectionEvidenceInfrastructureError(
            f"origin returned {len(rows)} refs for {branch!r}; the archive identity is ambiguous"
        )
    remote_commit = rows[0].split()[0].strip()
    if len(remote_commit) != _COMMIT_SHA_LENGTH or not all(
        character in "0123456789abcdef" for character in remote_commit
    ):
        raise CorrectionEvidenceInfrastructureError(
            f"origin returned {remote_commit!r}, which is not a commit SHA"
        )
    remote_url = _git(repo_root, "remote", "get-url", "origin")
    try:
        _git(repo_root, "cat-file", "-e", f"{remote_commit}^{{commit}}")
        tree_source = "LOCAL_OBJECT_FOR_ORIGIN_SUPPLIED_SHA"
    except CorrectionEvidenceInfrastructureError:
        # Narrow, non-mutating: fetch only the object origin just named.
        _git(repo_root, "fetch", "--depth", "1", "--no-write-fetch-head", "origin", remote_commit)
        _git(repo_root, "cat-file", "-e", f"{remote_commit}^{{commit}}")
        tree_source = "FETCHED_OBJECT_FOR_ORIGIN_SUPPLIED_SHA"
    remote_commit_tree = _git(repo_root, "rev-parse", f"{remote_commit}^{{tree}}")
    return {
        "repository_remote_url": remote_url,
        "repository_normalized": _normalize_repository(remote_url),
        "branch": branch,
        "observation_source": ARCHIVE_OBSERVATION_SOURCE,
        "remote_commit": remote_commit,
        "remote_commit_tree": remote_commit_tree,
        "remote_commit_tree_source": tree_source,
    }


def verify_frozen_stage_2_archive_identity(
    authorization: OwnerCorrectionSuccessorAuthorization,
    locations: AuthorizedEvidenceLocations,
) -> dict[str, Any]:
    """Verify the published archive still carries the bound evidence commit.

    The comparison is against what origin publishes now, not against any local
    ref, and only the authorization's own bound identity is compared. An identity
    that cannot be observed raises rather than degrading into a match.
    """
    repo_root = find_repo_root(locations.root)
    observed = _observe_git_archive_identity(repo_root, authorization.evidence_branch)
    comparison = {
        "repository_normalized": authorization.evidence_repository,
        "branch": authorization.evidence_branch,
        "remote_commit": STAGE_2_EVIDENCE_COMMIT,
        "remote_commit_tree": STAGE_2_EVIDENCE_TREE,
    }
    mismatched = sorted(name for name, value in comparison.items() if observed.get(name) != value)
    return {
        **observed,
        "expected_commit": STAGE_2_EVIDENCE_COMMIT,
        "expected_tree": STAGE_2_EVIDENCE_TREE,
        "expected_repository": authorization.evidence_repository,
        "expected_branch": authorization.evidence_branch,
        "mismatched": mismatched,
        "archive_identity_verified": not mismatched,
        "observed_after_successor_construction": True,
        "local_branch_consulted": False,
        "caller_injectable": False,
    }


def correction_successor_attempt_record_path(
    authorization: OwnerCorrectionSuccessorAuthorization,
) -> Path:
    """Its own namespace: the frozen Stage-2 attempt ledger is never reopened."""
    canonical = Path(authorization.canonical_path or authorization.path).resolve()
    return (
        canonical.parent / f".cdc-e2e-correction-successor-attempt-{authorization.sha256_hex}.json"
    )


def read_correction_successor_attempt_state(
    authorization: OwnerCorrectionSuccessorAuthorization,
) -> str:
    """Current correction-successor attempt state for this authorization."""
    path = correction_successor_attempt_record_path(authorization)
    if not path.exists():
        return CORRECTION_ATTEMPT_STATE_NONE
    document = _require_mapping(json.loads(path.read_bytes()), "attempt record")
    return str(document.get("attempt_state"))


def require_unclaimed_correction_successor_attempt(
    authorization: OwnerCorrectionSuccessorAuthorization,
) -> None:
    """Refuse before any successor construction when the authorization is used."""
    state = read_correction_successor_attempt_state(authorization)
    if state == CORRECTION_ATTEMPT_STATE_NONE:
        return
    if state == CORRECTION_ATTEMPT_STATE_CLAIMED:
        raise CorrectionAttemptStateError(
            f"correction-successor authorization {authorization.reference} is "
            f"{CORRECTION_ATTEMPT_STATE_CLAIMED}: a prior attempt claimed it and no "
            "consumption was recorded. Automatic retry is prohibited; this requires a "
            "separate owner decision."
        )
    raise CorrectionAttemptStateError(
        f"correction-successor authorization {authorization.reference} is {state}: it "
        "authorized one successor construction and is permanently non-reusable."
    )


def claim_correction_successor_attempt(
    authorization: OwnerCorrectionSuccessorAuthorization,
    runtime: RuntimeIdentity,
    frozen: FrozenMissionInput,
    evidence: FrozenStage2Evidence,
    predecessor_digest: str,
) -> MissionAttemptRecord:
    """Atomically claim the single authorized successor construction, or refuse."""
    record = MissionAttemptRecord(
        path=correction_successor_attempt_record_path(authorization),
        state=CORRECTION_ATTEMPT_STATE_CLAIMED,
        owner_execution_authorization_sha256=authorization.sha256_hex,
        implementation_commit=runtime.implementation_commit,
        implementation_tree=runtime.implementation_tree,
        mission_package_sha256=frozen.package_sha256,
    )
    body = {
        **record.as_record(),
        "stage": CORRECTION_SUCCESSOR_STAGE,
        "source_run_id": SOURCE_RUN_ID,
        "source_stage_2_result_digest": evidence.result_digest,
        "predecessor_digest": predecessor_digest,
        "successor_construction_invoked": False,
        "successor_constructed": False,
    }
    payload = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode()
    try:
        handle = os.open(record.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise CorrectionAttemptStateError(
            f"correction-successor authorization {authorization.reference} was already "
            "claimed by another attempt; automatic retry is prohibited"
        ) from error
    with os.fdopen(handle, "wb") as stream:
        stream.write(payload)
    written = record.path.read_bytes()
    return replace(record, record_sha256=_file_sha256(written), record_bytes=len(written))


def mark_correction_successor_attempt_consumed(
    record: MissionAttemptRecord,
    evidence: FrozenStage2Evidence,
    predecessor_digest: str,
    successor_id: str,
) -> MissionAttemptRecord:
    """Record that a successor was actually constructed.

    Written immediately after construction, before any later observation runs, so
    a failure downstream cannot make the exercised authority look reusable.
    """
    consumed = replace(record, state=CORRECTION_ATTEMPT_STATE_CONSUMED)
    body = {
        **consumed.as_record(),
        "stage": CORRECTION_SUCCESSOR_STAGE,
        "source_run_id": SOURCE_RUN_ID,
        "source_stage_2_result_digest": evidence.result_digest,
        "predecessor_digest": predecessor_digest,
        "successor_id": successor_id,
        "successor_construction_invoked": True,
        "successor_constructed": True,
    }
    record.path.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode())
    written = record.path.read_bytes()
    return replace(consumed, record_sha256=_file_sha256(written), record_bytes=len(written))


def derive_correction_predecessor(
    stage_1: Stage1Observation, evidence: FrozenStage2Evidence, action_plan: object
) -> dict[str, Any]:
    """Rebuild the predecessor from frozen evidence; never accept one from a caller.

    The object is built in exactly the shape ``integrate_correction`` builds it,
    so the digest the successor binds is the digest Stage 2 would have bound.
    """
    plan = require_verified_action_plan(action_plan)
    target_ebawu = plan.correction.predecessor_ebawu_ref
    artifact = next(
        (item for item in stage_1.artifacts().values() if item.ebawu_id == target_ebawu), None
    )
    if artifact is None:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-1 evidence carries no artifact for {target_ebawu}"
        )
    outcome = evidence.outcome_for_chain(artifact.chain_id)
    if outcome is None:
        raise CorrectionSuccessorBlockedError(
            f"frozen Stage-2 result carries no outcome for chain {artifact.chain_id}"
        )
    if outcome.get("outcome_state") != "transitioned" or outcome.get("transition_event") is None:
        raise CorrectionSuccessorBlockedError(
            f"chain {artifact.chain_id} is {outcome.get('outcome_state')!r} with "
            f"transition_event present={outcome.get('transition_event') is not None}; "
            "no eligible completed predecessor exists"
        )
    event = _require_mapping(outcome["transition_event"], "transition event")
    return {
        "ebawu_id": artifact.ebawu_id,
        "state": str(event["new_state"]),
        "candidate_id": artifact.candidate_id,
        "candidate_digest": artifact.candidate_digest,
    }


def build_predecessor_supersession_record(
    predecessor: Mapping[str, Any],
    predecessor_digest: str,
    successor_id: str,
    correction_event_id: str,
    *,
    superseded_at_utc: str,
    predecessor_mutated: bool,
) -> dict[str, Any]:
    """State the backward relation on a new object, never on the predecessor.

    ``make_successor`` carries the forward link. The predecessor itself is frozen
    evidence, so its supersession is recorded here rather than written into it.
    """
    return {
        "record_class": "PREDECESSOR_SUPERSESSION_RECORD",
        "predecessor_id": predecessor["ebawu_id"],
        "predecessor_candidate_id": predecessor["candidate_id"],
        "predecessor_digest": predecessor_digest,
        "superseded_by": successor_id,
        "superseded_at_utc": superseded_at_utc,
        "superseded_by_correction_event_id": correction_event_id,
        "predecessor_mutated": predecessor_mutated,
        "predecessor_rewritten": False,
        "is_successor_side_evidence": True,
    }


def recompute_affected_output_eligibility(
    evidence: FrozenStage2Evidence,
    predecessor: Mapping[str, Any],
    successor_id: str,
    correction_stimulus_id: str,
) -> list[dict[str, Any]]:
    """Determine correction-induced reliance state over the exact frozen drafts.

    The frozen drafts are read, never rewritten. A draft's pre-existing
    eligibility is carried alongside the new determination rather than replaced,
    because provenance incompleteness and correction-induced staleness are
    different facts about the same deliverable.
    """
    determinations: list[dict[str, Any]] = []
    predecessor_ebawu = str(predecessor["ebawu_id"])
    predecessor_candidate = str(predecessor["candidate_id"])
    for draft in evidence.drafts:
        provenance = _require_mapping(draft.get("provenance"), "draft provenance")
        states = provenance.get("institutional_state_per_ebawu")
        dispositions = provenance.get("disposition_per_candidate")
        candidate_refs = _require_sequence(provenance.get("candidate_refs", []), "candidate refs")
        affected = (
            (isinstance(states, Mapping) and predecessor_ebawu in states)
            or (isinstance(dispositions, Mapping) and predecessor_candidate in dispositions)
            or predecessor_candidate in candidate_refs
        )
        determinations.append(
            {
                "draft_id": draft.get("draft_id"),
                "pre_correction_frozen_eligibility": draft.get("eligibility_state"),
                "pre_correction_eligibility_reason": "FROZEN_RUN_001_DETERMINATION",
                "correction_impact": (
                    CORRECTION_IMPACT_AFFECTED if affected else CORRECTION_IMPACT_UNAFFECTED
                ),
                "post_correction_reliance_state": (
                    CORRECTION_INELIGIBILITY_STATE
                    if affected
                    else str(draft.get("eligibility_state"))
                ),
                "basis": {
                    "predecessor_id": predecessor_ebawu,
                    "predecessor_candidate_id": predecessor_candidate,
                    "successor_id": successor_id,
                    "correction_stimulus_id": correction_stimulus_id,
                },
                "frozen_draft_modified": False,
                "determination_class": "CORRECTION_SUCCESSOR_SIDE_RELIANCE_STATUS",
            }
        )
    return determinations


def observe_stale_predecessor_proposal_refusal(
    evidence: FrozenStage2Evidence, predecessor: Mapping[str, Any], successor_id: str
) -> dict[str, Any]:
    """Observe that the superseded candidate is refused as stale.

    The shared gate predicate is called directly. No transition is evaluated, no
    event is emitted and no Stage-2 attempt is touched: the refusal is a returned
    decision over frozen values.
    """
    artifact_chain = next(
        (
            item
            for item in evidence.outcomes
            if isinstance(item.get("transition_event"), Mapping)
            and item["transition_event"].get("aggregate_id") == predecessor["ebawu_id"]
        ),
        None,
    )
    if artifact_chain is None:
        raise CorrectionSuccessorBlockedError(
            "frozen evidence carries no transition event for the predecessor"
        )
    event = _require_mapping(artifact_chain["transition_event"], "transition event")
    # Rebuilt from the frozen event rather than authored, so the refusal is
    # observed against the candidate that actually transitioned.
    proposal = {
        "mission_id": event["mission_id"],
        "assurance_mode": event["assurance_mode"],
        "authority_scope_ref": event["authority_scope_ref"],
        "requested_disposition": event["disposition"],
        "candidate_id": predecessor["candidate_id"],
        "candidate_digest": predecessor["candidate_digest"],
        "ebawu_id": predecessor["ebawu_id"],
    }
    stale_candidate_ids = (str(predecessor["candidate_id"]),)
    registry = {"stale_candidate_ids": stale_candidate_ids}
    decision = refuse_stale_candidate_proposal(proposal, registry)
    if decision is None:
        raise CorrectionSuccessorBlockedError(
            "the superseded candidate was not refused as stale; the correction "
            "successor cannot claim supersession it cannot demonstrate"
        )
    return {
        "observation_class": "STALE_PREDECESSOR_PROPOSAL_REFUSAL",
        "candidate_id": predecessor["candidate_id"],
        "stale_candidate_ids": list(stale_candidate_ids),
        "superseded_by": successor_id,
        "decision": decision.decision,
        "reason_code": decision.reason_code,
        "epistemic_state": decision.epistemic_state,
        "rule_source": "oic.cdc_slice.refuse_stale_candidate_proposal",
        "gate_invoked": False,
        "transition_event_emitted": False,
        "stage_2_attempt_touched": False,
    }


def observe_predecessor_immutability(
    *,
    digest_before: str,
    digest_after: str,
    locations: AuthorizedEvidenceLocations,
) -> dict[str, Any]:
    """Two local levels of predecessor preservation, observed after construction.

    Level 1 proves the correction did not mutate its own argument. Level 2 proves
    the frozen files at the authorized location are unchanged. Level 1 alone would
    not be evidence of level 2, and neither is evidence of the published archive.
    """
    level_2 = {
        "raw_result_sha256": _file_sha256(locations.raw_result.read_bytes()),
        "attempt_record_sha256": _file_sha256(locations.attempt_record.read_bytes()),
        "route_trace_sha256": _file_sha256(locations.route_trace.read_bytes()),
    }
    expected_level_2 = {
        "raw_result_sha256": SOURCE_STAGE_2_RAW_RESULT_SHA256,
        "attempt_record_sha256": SOURCE_STAGE_2_ATTEMPT_RECORD_SHA256,
        "route_trace_sha256": SOURCE_STAGE_2_ROUTE_TRACE_SHA256,
    }
    mismatched = sorted(name for name, value in level_2.items() if expected_level_2[name] != value)
    if digest_before != digest_after:
        mismatched.append("in_memory_predecessor_digest")
    return {
        "level_1_in_memory_digest_before": digest_before,
        "level_1_in_memory_digest_after": digest_after,
        "level_1_preserved": digest_before == digest_after,
        "level_2_observed": level_2,
        "level_2_expected": expected_level_2,
        "level_2_preserved": not [name for name in mismatched if name in expected_level_2],
        "mismatched": sorted(set(mismatched)),
        "predecessor_byte_identity_preserved": not mismatched,
    }


def execute_authorized_correction_successor(
    *,
    stage_1: Stage1Observation,
    frozen: FrozenMissionInput,
    action_plan: object,
    clearance: CorrectionExecutionClearance,
    runtime: RuntimeIdentity,
    run_metadata: Mapping[str, Any],
    owner_correction_authorization_path: Path,
) -> CorrectionSuccessorResult:
    """The single authorized route to correction over frozen RUN-001 evidence.

    Stage 1 and Stage 2 are not re-entered, no transition is evaluated, no event
    is emitted and no draft is rendered. The caller presents the authority
    instrument; the correction semantics, the frozen evidence location, its
    identities and the published archive identity are all resolved from that
    instrument's verified bindings. There is no parameter through which an
    operator can vary what correction an issued authorization executes.
    """
    plan = require_verified_action_plan(action_plan)
    _event_metadata_fields(run_metadata)
    authorization = verify_owner_correction_successor_authorization(
        owner_correction_authorization_path,
        clearance=clearance,
        runtime=runtime,
        frozen=frozen,
        action_plan=plan,
    )
    instruction = verify_owner_correction_instruction(authorization, plan)
    locations = resolve_authorized_evidence_locations(authorization)
    evidence = load_authorized_stage_2_evidence(locations)
    require_distinct_identity_namespaces(evidence, stage_1)
    if stage_1.digest() != authorization.stage_1_observation_digest:
        raise CorrectionSuccessorBlockedError(
            f"Stage-1 observation digests to {stage_1.digest()}, but the authorization "
            f"binds {authorization.stage_1_observation_digest}"
        )
    require_unclaimed_correction_successor_attempt(authorization)

    predecessor = derive_correction_predecessor(stage_1, evidence, plan)
    predecessor_digest = sha256(predecessor)
    if instruction.declared_predecessor_digest != predecessor_digest:
        raise PredecessorBindingError(
            f"correction binds predecessor {instruction.declared_predecessor_digest!r}, "
            f"actual {predecessor_digest!r}"
        )
    correction = instruction.as_correction(predecessor_digest)
    missing = sorted(set(plan.correction.required_correction_fields) - correction.keys())
    frozen_side = set(CORRECTION_INSTRUCTION_DERIVED_FIELDS)
    missing = sorted(set(missing) - frozen_side)
    if missing:
        raise CorrectionSuccessorBlockedError(
            f"correction object lacks fields the frozen plan requires: {missing}"
        )
    if correction["new_ebawu_or_successor_id"] != authorization.successor_id:
        raise CorrectionSuccessorBlockedError(
            f"the correction instruction constructs successor "
            f"{correction['new_ebawu_or_successor_id']!r}, but the authorization "
            f"binds {authorization.successor_id!r}"
        )

    # Every structural precondition has passed; claim immediately before the
    # first result-bearing construction.
    claimed = claim_correction_successor_attempt(
        authorization, runtime, frozen, evidence, predecessor_digest
    )

    # Construction. A failure here leaves the attempt CLAIMED_NOT_CONSUMED,
    # because no successor came into existence.
    bound = bind_correction(predecessor, {**correction, "predecessor_digest": predecessor_digest})
    successor = make_successor(predecessor, correction)

    # A successor now exists. The authority is exercised from this point on, so it
    # is marked consumed before any further observation can fail.
    consumed = mark_correction_successor_attempt_consumed(
        claimed, evidence, predecessor_digest, authorization.successor_id
    )

    superseded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    failure_context: dict[str, Any] = {
        "result_status": RESULT_STATUS_FAILED_POST_CONSTRUCTION,
        "successor_construction_invoked": True,
        "successor_constructed": True,
        "successor_id": authorization.successor_id,
        "attempt_state": CORRECTION_ATTEMPT_STATE_CONSUMED,
        "attempt_record": consumed.identity(),
        "predecessor": dict(predecessor),
        "predecessor_digest": predecessor_digest,
        "predecessor_before_digest": bound["predecessor_before_digest"],
        "predecessor_after_digest": bound["predecessor_after_digest"],
        "automatic_retry": False,
    }
    try:
        supersession = build_predecessor_supersession_record(
            predecessor,
            predecessor_digest,
            authorization.successor_id,
            str(correction["correction_event_id"]),
            superseded_at_utc=superseded_at,
            predecessor_mutated=bool(bound["predecessor_mutated"]),
        )
        eligibility = recompute_affected_output_eligibility(
            evidence,
            predecessor,
            authorization.successor_id,
            plan.correction.correction_stimulus_id,
        )
        stale_observation = observe_stale_predecessor_proposal_refusal(
            evidence, predecessor, authorization.successor_id
        )
        immutability = observe_predecessor_immutability(
            digest_before=str(bound["predecessor_before_digest"]),
            digest_after=str(bound["predecessor_after_digest"]),
            locations=locations,
        )
        if not immutability["predecessor_byte_identity_preserved"]:
            raise PredecessorMutationDetectedError(
                f"PREDECESSOR_MUTATION_DETECTED: {immutability['mismatched']}"
            )
        archive_identity = verify_frozen_stage_2_archive_identity(authorization, locations)
        if not archive_identity["archive_identity_verified"]:
            raise PredecessorMutationDetectedError(
                f"PREDECESSOR_MUTATION_DETECTED: archive identity {archive_identity['mismatched']}"
            )
    except Exception as error:
        raise PostConstructionIntegrityError(
            f"{RESULT_STATUS_FAILED_POST_CONSTRUCTION}: {error}",
            {**failure_context, "failure": f"{type(error).__name__}: {error}"},
        ) from error

    return CorrectionSuccessorResult(
        experiment_id=EXPERIMENT_ID,
        runtime_mission_id=MISSION_ID,
        source_run_id=SOURCE_RUN_ID,
        source_stage_2_result_digest=evidence.result_digest,
        source_stage_2_raw_result_sha256=evidence.raw_result_sha256,
        evidence_locations=locations.as_record(),
        owner_correction_authorization=authorization.as_record(),
        correction_instruction=instruction.as_record(),
        correction_stimulus={
            "correction_stimulus_id": plan.correction.correction_stimulus_id,
            "correction_stimulus_digest": plan.correction.digest(),
            "correction_target_id": plan.correction.target_id,
            "correction_target_source": "FROZEN_ACTION_PLAN_BYTES",
            "predecessor_ebawu_ref": plan.correction.predecessor_ebawu_ref,
            "precondition": plan.correction.precondition,
            "stimulus_is_not_the_instruction": True,
        },
        predecessor=predecessor,
        predecessor_digest=predecessor_digest,
        successor=successor,
        predecessor_supersession_record=supersession,
        correction_reason=str(bound["correction_reason"]),
        changed_fact_or_control_refs=list(bound["changed_refs"]),
        affected_output_eligibility=eligibility,
        stale_proposal_refusal_observation=stale_observation,
        predecessor_immutability=immutability,
        archive_identity=archive_identity,
        attempt_record=consumed.identity(),
    )
