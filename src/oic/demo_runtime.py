"""OAM composition and the bounded demonstration action gate.

What this module composes
-------------------------
Four separate questions, kept apart on purpose, each answered by the layer that
owns it and none allowed to overwrite another:

===========================  ==========================================
``epistemic_status``         what the *logic kernel* concluded
``institutional_authorization_status``  whether the institution authorizes it
``execution_disposition``    what the runtime does about it
``decision_basis``           *why* it did that
===========================  ==========================================

The separations that matter
---------------------------
- **Evaluation establishes the property; issuance creates the reliance.** A
  currentness resolution or an authority decision establishes something. Only the
  reliance issuance creates something a downstream party may rely on.
- **Authority refusal never rewrites an epistemic result.** A revoked delegation
  makes an action unauthorized; it does not make the proposition false. The
  decision record therefore carries the ZTL-derived ``epistemic_status``
  unchanged next to a REFUSED authorization.
- **Currentness refusal likewise.** A superseded control blocks the operation and
  says nothing about whether the claim was true.
- **UNKNOWN fails closed operationally without becoming substantive false.** It
  produces BLOCK with a PRECAUTIONARY or PROCEDURAL basis, never a REFUTED
  epistemic status.
- **Currentness does not imply authority; authority does not rewrite
  currentness.** They are evaluated by two unmodified L0 modules and composed
  here, never folded into one another.

What the action gate is
-----------------------
``BOUNDED_DEMO_EXECUTION_GATE``. It emits ACTION_PERMITTED / ACTION_BLOCKED /
ACTION_ESCALATED and performs no payment, no disbursement, no external API call,
no government operation and no legal act. It is emphatically **not**
``NON_BYPASSABLE_PRODUCTION_ENFORCEMENT`` and must never be described as such.

Execution context
-----------------
Every automated test runs under ``DEVELOPMENT_TEST_ONLY``. No development-test
result may be labelled a measured demonstration. The public
``oic demo run`` path refuses with ``RESULT_BEARING_EXECUTION_NOT_AUTHORIZED``
unless a separate owner-issued result-bearing authorization artifact is supplied.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from oic.cdc_authority import (
    ADMISSIBILITY_BASIS_CLASS,
    AUTHORITY_BASIS_CLASS,
    CONSUMER_PRINCIPAL,
    CONSUMER_PROFILE_CLASS,
    PRODUCER_PRINCIPAL,
    PRODUCER_PROFILE_CLASS,
    AuthorityDecisionRecord,
    AuthorityRequest,
    authority_basis_record_digest,
    currentness_epoch_digest,
    evaluate_synthetic_authority,
    parse_basis_record,
    parse_profile,
    synthetic_profile_digest,
)
from oic.cdc_currentness import (
    CONTROLLING_RECORD_CLASSES,
    HISTORICAL_ARTIFACT_IDENTITY_RECORD,
    SUPERSESSION_RECORD,
    BasisCompletenessAttestation,
    CurrentnessIndex,
    IndexEntry,
    UseGateDecision,
    UseGateProfile,
    UseGateRequest,
    basis_record_digest,
    currentness_index_digest,
    evaluate_present_use,
    historical_artifact_digest,
    parse_basis_completeness_attestation,
    resolve_currentness,
)
from oic.cdc_propagation import (
    ProducerIdentity,
    build_envelope,
    materialize_envelope,
    read_materialized_envelope,
)
from oic.cdc_reliance import (
    ConsumerContext,
    ReResolvedCurrentness,
    claim_issuance_attempt,
    issue_reliance,
    persisted_file_sha256,
    run_consumer_validation,
)
from oic.demo_compiler import (
    GROUND_ATOMS,
    CompiledPolicy,
    EvidenceState,
    canonical_json_digest,
    compile_policy,
    digest_bytes,
    ground_marking,
    load_policy_source,
)
from oic.demo_ztl import (
    CANONICALIZATION_PROFILE_ID,
    KERNEL_COMMIT,
    KERNEL_PROFILE_ID,
    BindingFinding,
    KernelResult,
    build_warrant,
    epistemic_status_for,
    expected_formula_hash,
    invoke_kernel,
    resolve_ztl_path,
    validate_warrant_binding,
)
from oic.errors import OICError

__all__ = [
    "ACTION_BLOCKED",
    "ACTION_ESCALATED",
    "ACTION_GATE_CLASS",
    "ACTION_PERMITTED",
    "CASE_IDS",
    "OAM_DECISION_SCHEMA_VERSION",
    "RESULT_BEARING_EXECUTION_NOT_AUTHORIZED",
    "SCENARIO_ID",
    "CaseOutcome",
    "DemoRuntimeError",
    "ExecutionContext",
    "Scenario",
    "build_currentness_index",
    "compile_scenario",
    "decision_semantic_projection",
    "load_result_bearing_authorization",
    "load_scenario",
    "run_all_cases",
    "run_case",
    "validate_scenario",
    "write_evidence_graph",
]

SCENARIO_ID: Final = "synthetic-grant-authority"
DEMO_ROOT: Final = "demo/oic-ztl-oam-slice-001/scenarios"

OAM_DECISION_SCHEMA_VERSION: Final = "OIC-DEMO-OAM-DECISION-v0.1"
EXECUTION_AUTHORIZATION_SCHEMA_VERSION: Final = "OIC-DEMO-EXECUTION-AUTHORIZATION-v0.1"

#: The claim this gate is permitted to make. Nothing stronger.
ACTION_GATE_CLASS: Final = "BOUNDED_DEMO_EXECUTION_GATE"

ACTION_PERMITTED: Final = "ACTION_PERMITTED"
ACTION_BLOCKED: Final = "ACTION_BLOCKED"
ACTION_ESCALATED: Final = "ACTION_ESCALATED"

AUTHORIZED: Final = "AUTHORIZED"
REFUSED: Final = "REFUSED"
UNRESOLVED: Final = "UNRESOLVED"

ALLOW: Final = "ALLOW"
BLOCK: Final = "BLOCK"
ESCALATE: Final = "ESCALATE"

SUBSTANTIVE: Final = "SUBSTANTIVE"
PRECAUTIONARY: Final = "PRECAUTIONARY"
PROCEDURAL: Final = "PROCEDURAL"
CONTROL_REQUIREMENT: Final = "CONTROL_REQUIREMENT"

RESULT_BEARING_EXECUTION_NOT_AUTHORIZED: Final = "RESULT_BEARING_EXECUTION_NOT_AUTHORIZED"

#: Recorded when the currentness gate did not PROCEED, so authority was never
#: reached. Distinct from every authority reason code, because "not asked" is not
#: an answer.
AUTHORITY_NOT_EVALUATED: Final = "NOT_EVALUATED"
CURRENTNESS_GATE_DID_NOT_PROCEED: Final = "CURRENTNESS_GATE_DID_NOT_PROCEED"

#: The only ceiling a validated owner authorization may carry. Nothing in this
#: work order issues one, and nothing here asserts this claim.
MEASURED_INTERNAL_CEILING: Final = "MEASURED_INTERNAL_END_TO_END_TECHNICAL_DEMONSTRATION"
DEVELOPMENT_CLAIM_CEILING: Final = "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"

DEMO_SUBJECT_PRINCIPAL: Final = "SYNTH-DISBURSING-OFFICER-001"
REQUESTED_USE: Final = "SYNTHETIC_GRANT_DISBURSEMENT_DECISION"
ARTIFACT_CLASS: Final = "SYNTHETIC_COMPILED_CONTROL_ENVELOPE"

CASE_IDS: Final[tuple[str, ...]] = ("case-1", "case-2", "case-3", "case-4", "case-5")

#: The evidence graph this lane is able to emit once a result-bearing execution
#: is separately authorized.
EVIDENCE_DIRECTORIES: Final[tuple[str, ...]] = (
    "00-source",
    "01-oic",
    "02-ztl",
    "03-runtime",
    "04-reliance",
    "05-evidence",
)


class DemoRuntimeError(OICError):
    """The demonstration lane refused to proceed rather than guess."""


class ExecutionContext(StrEnum):
    """Which kind of execution this is. The distinction is not cosmetic.

    A development test proves the implementation runs. Only an owner-authorized
    result-bearing execution may carry a measured claim, and this lane has no
    such authorization.
    """

    DEVELOPMENT_TEST_ONLY = "DEVELOPMENT_TEST_ONLY"
    OWNER_AUTHORIZED_RESULT_BEARING = "OWNER_AUTHORIZED_RESULT_BEARING"


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Scenario:
    """The frozen scenario declaration plus the directory it was read from."""

    root: Path
    document: dict[str, Any]

    @property
    def scope_ref(self) -> str:
        """The institutional scope every record in this lane is bound to."""
        return str(self.document["scope_ref"])

    @property
    def policy_family(self) -> str:
        """The policy family name, used to build stable identifiers."""
        return str(self.document["policy_family"])

    @property
    def test_amount(self) -> int:
        """The amount the bounded action proposal carries."""
        return int(self.document["test_amount"])

    def time(self, name: str) -> str:
        """One declared logical instant, by name."""
        return str(self.document["declared_logical_times"][name])

    def output_ref(self, version: str) -> str:
        """The currentness-governed identity of one compiled control version.

        The scope is a prefix of the reference on purpose: the L0 resolver
        requires an attestation's scope to cover the output it claims.
        """
        return f"{self.scope_ref}#OCE/{self.policy_family}/{version}"


def load_scenario(repo_root: Path, scenario_id: str = SCENARIO_ID) -> Scenario:
    """Read one scenario declaration, refusing an unknown identifier."""
    root = repo_root / DEMO_ROOT / scenario_id
    manifest = root / "SCENARIO.json"
    if not manifest.is_file():
        raise DemoRuntimeError(f"no scenario declaration at {manifest}")
    document: dict[str, Any] = json.loads(manifest.read_text(encoding="utf-8"))
    return Scenario(root=root, document=document)


def compile_scenario(scenario: Scenario) -> dict[str, CompiledPolicy]:
    """Compile every declared policy version through the full chain.

    The bound formula hash is computed from the kernel's rendering of the
    positive formula, which is a constant of the scenario rather than of any one
    invocation, so the binding exists before the kernel is ever called.
    """
    rendered = _rendered_positive_formula(scenario)
    compiled: dict[str, CompiledPolicy] = {}
    for version, declaration in sorted(scenario.document["versions"].items()):
        source = load_policy_source(
            scenario.root / str(declaration["source_path"]),
            source_id=f"src:{scenario.policy_family}/{version}",
        )
        admission_document = json.loads(
            (scenario.root / str(declaration["admission_path"])).read_text(encoding="utf-8")
        )
        compiled[version] = compile_policy(
            source,
            admission_records=list(admission_document["admission_records"]),
            ingested_at=str(declaration["effective_from"]),
            kernel_profile_id=KERNEL_PROFILE_ID,
            canonicalization_profile_id=CANONICALIZATION_PROFILE_ID,
            bound_formula_hash=expected_formula_hash(rendered),
        )
    return compiled


def _rendered_positive_formula(scenario: Scenario) -> str:
    """The kernel's rendering of the scenario formula, stated once.

    The kernel inserts parentheses and rewrites ASCII operators; the caller's
    string and the kernel's rendering are different bytes for the same
    proposition, and only the rendering is ever hashed.
    """
    atoms = [GROUND_ATOMS[ground] for ground in scenario.document["ztl"]["ground_ids"]]
    return "(" + " ∧ ".join(atoms) + ")"


_WARRANT_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def _warrant_schema(repo_root: Path) -> dict[str, Any]:
    """The proposed warrant contract, read from the repository, cached per root.

    Read rather than embedded: a copy of the schema inside runtime code would
    drift from the contract it claims to enforce and nobody would notice.
    """
    key = str(repo_root)
    if key not in _WARRANT_SCHEMA_CACHE:
        path = repo_root / "schemas" / "proposed" / "warrant-artifact.schema.json"
        document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        _WARRANT_SCHEMA_CACHE[key] = document
    return _WARRANT_SCHEMA_CACHE[key]


# ---------------------------------------------------------------------------
# Scenario bundle identity and the evidence observation
# ---------------------------------------------------------------------------


def scenario_bundle_digest(scenario: Scenario) -> str:
    """A deterministic identity over the exact scenario input bytes.

    The projection is unambiguous on purpose: sorted relative path, SHA-256 of
    the exact file bytes, canonically serialized, then digested. An owner issues
    a result-bearing authorization against this value, so "the same scenario"
    must mean the same bytes and nothing looser.
    """
    entries = []
    for relative in sorted(str(item) for item in scenario.document["scenario_bundle_paths"]):
        path = scenario.root / relative
        if not path.is_file():
            raise DemoRuntimeError(f"scenario bundle path is missing: {relative}")
        entries.append({"path": relative, "sha256": digest_bytes(path.read_bytes())})
    return canonical_json_digest({"scenario_id": SCENARIO_ID, "files": entries})


def scenario_bundle_manifest(scenario: Scenario) -> list[dict[str, str]]:
    """The per-file identities the bundle digest is taken over."""
    return [
        {
            "path": relative,
            "sha256": digest_bytes((scenario.root / relative).read_bytes()),
        }
        for relative in sorted(str(item) for item in scenario.document["scenario_bundle_paths"])
    ]


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    """One observed piece of evidence, with the bytes it was read from.

    A requirement and its satisfaction are different objects. The policy source
    says the evidence is required; this says an observation exists, what state it
    is in, and which exact bytes carry it. Nothing may conclude satisfaction from
    the requirement alone.
    """

    evidence_id: str
    evidence_class: str
    signature_state: str
    state: EvidenceState
    path: Path
    relative_path: str
    sha256: str
    document: Mapping[str, Any]
    satisfies_requirement: bool
    findings: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        """The observation as it appears in the decision and evidence records."""
        return {
            "required_evidence_id": self.evidence_id,
            "observed_evidence_id": str(self.document.get("evidence_id", "")),
            "observed_evidence_class": self.evidence_class,
            "observed_digest": self.sha256,
            "observed_path": self.relative_path,
            "signature_state": self.signature_state,
            "evidence_state": self.state.value,
            "satisfaction": self.satisfies_requirement,
            "findings": list(self.findings),
        }


def load_evidence_observation(scenario: Scenario) -> EvidenceObservation:
    """Open the declared observation, verify its identity, and read its state.

    Every failure path lands on ``NOT_OBSERVED`` or ``UNKNOWN`` rather than on a
    negative finding. Not having looked is not the same as having looked and
    found nothing, and only the second may falsify a ground.
    """
    declaration = scenario.document["evidence"]
    required_id = str(declaration["required_evidence_id"])
    relative = str(declaration["observation_path"])
    path = scenario.root / relative
    findings: list[str] = []

    if not path.is_file():
        return EvidenceObservation(
            evidence_id=required_id,
            evidence_class="",
            signature_state="",
            state=EvidenceState.NOT_OBSERVED,
            path=path,
            relative_path=relative,
            sha256="",
            document={},
            satisfies_requirement=False,
            findings=("the declared evidence observation is absent",),
        )

    payload = path.read_bytes()
    digest = digest_bytes(payload)
    document: Mapping[str, Any] = json.loads(payload.decode("utf-8"))

    observed_id = str(document.get("evidence_id", ""))
    observed_class = str(document.get("evidence_class", ""))
    signature_state = str(document.get("signature_state", ""))

    if observed_id != required_id:
        findings.append(f"observed evidence_id {observed_id!r} is not the required {required_id!r}")
    if observed_class != str(declaration["expected_evidence_class"]):
        findings.append(f"observed evidence_class {observed_class!r} is not the expected class")

    try:
        state = EvidenceState(signature_state)
    except ValueError:
        state = EvidenceState.UNKNOWN
        findings.append(f"signature_state {signature_state!r} is outside the known states")

    if findings:
        # The observation does not answer the question that was asked, so it is
        # unknown rather than negative.
        state = EvidenceState.UNKNOWN

    satisfies = not findings and signature_state == str(declaration["required_signature_state"])
    return EvidenceObservation(
        evidence_id=required_id,
        evidence_class=observed_class,
        signature_state=signature_state,
        state=state,
        path=path,
        relative_path=relative,
        sha256=digest,
        document=document,
        satisfies_requirement=satisfies,
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Currentness — synthetic state built from the adjudicated L0 types
# ---------------------------------------------------------------------------


def _identity_entry(scenario: Scenario, version: str, compiled: CompiledPolicy) -> IndexEntry:
    output_ref = scenario.output_ref(version)
    record = {
        "output_ref": output_ref,
        "historical_artifact_digest": historical_artifact_digest(compiled.control_envelope),
        "historical_state": "COMPILED_CONTROL_ENVELOPE",
        "source": "SYNTHETIC_DEMO_COMPILATION",
    }
    return IndexEntry(
        output_ref=output_ref,
        record_ref=f"ARTIFACT-IDENTITY#{output_ref}",
        record_class=HISTORICAL_ARTIFACT_IDENTITY_RECORD,
        record_digest=basis_record_digest(record),
        effective_at=None,
        admitted_at=scenario.time("supersession_admitted_at"),
        record=record,
    )


def _supersession_entry(scenario: Scenario, compiled: dict[str, CompiledPolicy]) -> IndexEntry:
    output_ref = scenario.output_ref("v1")
    record = {
        "output_ref": output_ref,
        "record_class": SUPERSESSION_RECORD,
        "successor_id": compiled["v2"].control_envelope["envelope_id"],
        "correction_event_id": f"{scenario.policy_family}-SUPERSESSION-v1-TO-v2",
        "predecessor_candidate_id": None,
        "superseded_at_utc": str(scenario.document["versions"]["v2"]["effective_from"]),
    }
    return IndexEntry(
        output_ref=output_ref,
        record_ref=f"SUPERSESSION#{output_ref}",
        record_class=SUPERSESSION_RECORD,
        record_digest=basis_record_digest(record),
        effective_at=str(scenario.document["versions"]["v2"]["effective_from"]),
        admitted_at=scenario.time("supersession_admitted_at"),
        record=record,
    )


def _attestation(
    scenario: Scenario, version: str, entries: list[IndexEntry]
) -> BasisCompletenessAttestation:
    output_ref = scenario.output_ref(version)
    covered = sorted(
        {
            entry.record_class
            for entry in entries
            if entry.output_ref == output_ref and entry.record_class in CONTROLLING_RECORD_CLASSES
        }
        | set(CONTROLLING_RECORD_CLASSES)
    )
    refs = [entry.record_ref for entry in entries if entry.output_ref == output_ref]
    source = {
        "scope_ref": scenario.scope_ref,
        "covered_output_ref": output_ref,
        "record_kinds_covered": covered,
        "basis_snapshot_refs": refs,
        "basis_snapshot_digests": [
            entry.record_digest for entry in entries if entry.output_ref == output_ref
        ],
        "completeness_as_of": scenario.time("basis_attested_at"),
        "admitted_at": scenario.time("basis_attested_at"),
        "fixture_class": None,
        "semantics": (
            "Synthetic demonstration basis. Affirmative evidence that the governing basis for "
            "this compiled control version was attested complete at the stated instant."
        ),
    }
    return parse_basis_completeness_attestation(
        source, admission_path="OIC-ZTL-OAM-DEMO-SLICE-001-SYNTHETIC-BASIS-PATH"
    )


def build_currentness_index(
    scenario: Scenario, compiled: dict[str, CompiledPolicy]
) -> CurrentnessIndex:
    """Assemble the synthetic governed state, using the L0 types unchanged.

    Nothing here is fabricated CDC mission evidence and nothing is fed through
    ``build_currentness_index()``'s frozen-artifact path: the synthetic grant
    material is declared synthetic and is admitted as its own state, so it can
    never be mistaken for, or hashed alongside, the real Mission-001 record.
    """
    entries = [
        _identity_entry(scenario, version, compiled[version]) for version in sorted(compiled)
    ]
    entries.append(_supersession_entry(scenario, compiled))
    attestations = [_attestation(scenario, version, entries) for version in sorted(compiled)]
    admitted_at = scenario.time("basis_attested_at")
    return CurrentnessIndex(
        scope_ref=scenario.scope_ref,
        entries=tuple(entries),
        attestations=tuple(attestations),
        observed_at=admitted_at,
        admitted_at=admitted_at,
        index_digest=currentness_index_digest(
            scope_ref=scenario.scope_ref,
            entries=[entry.reduced() for entry in entries],
            attestations=[attestation.as_record() for attestation in attestations],
            admitted_at=admitted_at,
        ),
        basis_source_identities={
            "synthetic_scenario": canonical_json_digest(scenario.document),
        },
    )


def _governing_records(index: CurrentnessIndex, output_ref: str) -> list[dict[str, Any]]:
    return [
        entry.reduced()
        for entry in index.entries_for(output_ref)
        if entry.record_class in CONTROLLING_RECORD_CLASSES
    ]


def _epoch_for(index: CurrentnessIndex, output_ref: str, as_of: str) -> str:
    attestation = index.attestation_for(output_ref)
    return currentness_epoch_digest(
        output_ref=output_ref,
        as_of=as_of,
        governing_records=_governing_records(index, output_ref),
        completeness_attestation_digest=(
            None if attestation is None else attestation.completeness_digest
        ),
    )


# ---------------------------------------------------------------------------
# Authority — synthetic bases, evaluated by the unmodified L0 procedure
# ---------------------------------------------------------------------------


def _stored(body: dict[str, Any], digest_field: str) -> dict[str, Any]:
    computed = (
        authority_basis_record_digest(body)
        if digest_field == "record_digest"
        else synthetic_profile_digest(body)
    )
    return {**body, digest_field: computed}


def _authority_basis(scenario: Scenario, **overrides: object) -> dict[str, Any]:
    body: dict[str, Any] = {
        "record_class": AUTHORITY_BASIS_CLASS,
        "basis_id": f"AUTH-BASIS-{scenario.document['delegation_id']}",
        "principal_id": DEMO_SUBJECT_PRINCIPAL,
        "scope": scenario.scope_ref,
        "permitted_requested_use": [REQUESTED_USE],
        "validity_from": "2027-01-01T00:00:00Z",
        "validity_until": "2028-01-01T00:00:00Z",
        "revocation_state": "NOT_REVOKED",
        "supersedes": None,
        "superseded_by": None,
        "admitted_at": "2027-01-01T00:00:00Z",
        "effective_at": "2027-01-01T00:00:00Z",
    }
    return _stored({**body, **overrides}, "record_digest")


def _admissibility_basis(scenario: Scenario, **overrides: object) -> dict[str, Any]:
    body: dict[str, Any] = {
        "record_class": ADMISSIBILITY_BASIS_CLASS,
        "basis_id": f"ADM-BASIS-{scenario.policy_family}",
        "artifact_class_admitted": [ARTIFACT_CLASS],
        "requested_use_admitted": [REQUESTED_USE],
        "validity_from": "2027-01-01T00:00:00Z",
        "validity_until": "2028-01-01T00:00:00Z",
        "revocation_state": "NOT_REVOKED",
        "admitted_at": "2027-01-01T00:00:00Z",
        "effective_at": "2027-01-01T00:00:00Z",
    }
    return _stored({**body, **overrides}, "record_digest")


def _profile(scenario: Scenario, *, consumer: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "record_class": CONSUMER_PROFILE_CLASS if consumer else PRODUCER_PROFILE_CLASS,
        "profile_id": f"DEMO-{'CONSUMER' if consumer else 'PRODUCER'}-PROFILE-001",
        "principal_id": CONSUMER_PRINCIPAL if consumer else PRODUCER_PRINCIPAL,
        "role": "RELIANCE_CONSUMER" if consumer else "PRODUCER",
        "scope": scenario.scope_ref,
        "permitted_requested_use": [REQUESTED_USE],
        "validity_from": "2027-01-01T00:00:00Z",
        "validity_until": "2028-01-01T00:00:00Z",
        "revocation_state": "NOT_REVOKED",
        "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
    }
    return _stored(body, "profile_digest")


def _authority_bases_for(scenario: Scenario, case_id: str) -> list[dict[str, Any]]:
    """The authority state each case is evaluated against.

    Case 3 revokes the delegation. Case 4 admits two operative bases for the same
    (principal, scope) with no frozen precedence between them, which is exactly
    the A6 condition — competing, not absent.
    """
    if case_id == "case-3":
        return [_authority_basis(scenario, revocation_state="REVOKED")]
    if case_id == "case-4":
        return [
            _authority_basis(scenario),
            _authority_basis(
                scenario,
                basis_id=f"AUTH-BASIS-{scenario.document['delegation_id']}-COMPETING",
            ),
        ]
    return [_authority_basis(scenario)]


# ---------------------------------------------------------------------------
# OAM composition
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Component:
    """One named precondition of ALLOW, with the observation behind it."""

    name: str
    satisfied: bool
    observed: Any
    basis_if_missing: str


def _components(
    *,
    epistemic_status: str,
    warranty_grade: str,
    unverified_ground_ids: list[str],
    gate_decision: UseGateDecision | None,
    authority: AuthorityDecisionRecord | None,
    compiled: CompiledPolicy,
    binding_ok: bool,
    evidence: EvidenceObservation,
    warrant_findings: list[BindingFinding],
    proposal_id: str,
) -> list[_Component]:
    requirement = compiled.runtime_binding["warrant_requirement"]
    grade_rank = {"until-verification": 0, "sound": 1, "hereditary": 2}
    required_rank = grade_rank[str(requirement["minimum_warranty_grade"])]
    return [
        _Component(
            "usable_logical_warrant",
            grade_rank.get(warranty_grade, -1) >= required_rank
            and not (unverified_ground_ids and requirement["unverified_ground_policy"] == "forbid"),
            {"grade": warranty_grade, "unverified": unverified_ground_ids},
            CONTROL_REQUIREMENT,
        ),
        _Component(
            # Constructing a warrant and being entitled to rely on one are two
            # acts. This component is the second.
            "warrant_binding_validated",
            not warrant_findings,
            [str(finding) for finding in warrant_findings],
            CONTROL_REQUIREMENT,
        ),
        _Component(
            "appropriate_epistemic_route",
            epistemic_status == "ESTABLISHED",
            epistemic_status,
            SUBSTANTIVE if epistemic_status == "REFUTED" else PRECAUTIONARY,
        ),
        _Component(
            "currentness_g1",
            gate_decision is not None and gate_decision.reason_code_id == "G1",
            None if gate_decision is None else gate_decision.reason_code_id,
            PROCEDURAL,
        ),
        _Component(
            # An unevaluated authority is not a satisfied one. When currentness
            # refused, this component is unmet and says so as NOT_EVALUATED,
            # rather than borrowing an A1 that was never computed.
            "authority_a1",
            authority is not None and authority.reason_code_id == "A1",
            AUTHORITY_NOT_EVALUATED if authority is None else authority.reason_code_id,
            PRECAUTIONARY
            if authority is not None and authority.reason_code_id == "A6"
            else PROCEDURAL,
        ),
        _Component(
            "valid_admission_binding",
            bool(compiled.control_envelope["admission_ids"]) and binding_ok,
            compiled.control_envelope["admission_ids"],
            PROCEDURAL,
        ),
        _Component(
            "valid_source_version_binding",
            binding_ok,
            compiled.runtime_binding["source_version_set_hash"],
            PROCEDURAL,
        ),
        _Component(
            # Derived from an observation that was opened and verified, never
            # from the presence of a requirement.
            "required_evidence",
            evidence.satisfies_requirement,
            evidence.as_record(),
            CONTROL_REQUIREMENT,
        ),
        _Component(
            "automatic_decision_mode",
            compiled.control_envelope["decision_mode"] == "automatic",
            compiled.control_envelope["decision_mode"],
            PROCEDURAL,
        ),
        _Component("bounded_action_proposal_identity", bool(proposal_id), proposal_id, PROCEDURAL),
    ]


def _compose(
    components: list[_Component],
    *,
    authority: AuthorityDecisionRecord | None,
) -> tuple[str, str, str, list[str]]:
    """Decide authorization, disposition and basis without collapsing them.

    Fails closed: any missing required component blocks. The first missing
    component in the frozen order supplies the basis, so the reason a decision
    went the way it did is a fact about the evaluation rather than a
    reconstruction after it.

    ``epistemic_status`` is deliberately not a parameter. This function returns
    the other three fields and never the epistemic one, so an authority or
    currentness refusal has no route by which it could rewrite what the kernel
    concluded — the separation is structural rather than a rule to remember.
    """
    missing = [component for component in components if not component.satisfied]
    if not missing:
        return AUTHORIZED, ALLOW, SUBSTANTIVE, []

    reasons = [component.name for component in missing]
    first = missing[0]
    if authority is None:
        # Currentness refused, so authority was never evaluated. The refusal is
        # procedural and must not be dressed up as an authority finding.
        return REFUSED, BLOCK, first.basis_if_missing, reasons
    if authority.reason_code_id == "A6":
        # Competing operative authority bases: the institution has not resolved
        # which basis governs. That is not a finding that the claim is false.
        return UNRESOLVED, ESCALATE, PRECAUTIONARY, reasons
    if authority.reason_code_id == "A7":
        return UNRESOLVED, ESCALATE, PROCEDURAL, reasons
    return REFUSED, BLOCK, first.basis_if_missing, reasons


def _action_state(execution_disposition: str) -> str:
    if execution_disposition == ALLOW:
        return ACTION_PERMITTED
    if execution_disposition == ESCALATE:
        return ACTION_ESCALATED
    return ACTION_BLOCKED


# ---------------------------------------------------------------------------
# Case execution
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CaseOutcome:
    """Everything one case produced, in evidence-graph order."""

    case_id: str
    version: str
    execution_context: ExecutionContext
    evaluated_at: str
    compiled: CompiledPolicy
    kernel_result: KernelResult
    warrant: dict[str, Any]
    gate_decision: UseGateDecision
    authority_decision: AuthorityDecisionRecord | None
    oam_decision: dict[str, Any]
    action_state: str
    evidence: EvidenceObservation | None = None
    warrant_findings: tuple[str, ...] = ()
    reliance: dict[str, Any] | None = None
    consumer_validation: dict[str, Any] | None = None
    absent_artifacts: list[dict[str, str]] = field(default_factory=list)


def decision_semantic_projection(outcome: CaseOutcome) -> dict[str, Any]:
    """The decision-affecting projection, with operational noise excluded.

    Process ids, paths and durations are declared operational observations. They
    may vary between runs and must not move any of these fields; a determinism
    test compares exactly this projection.
    """
    return {
        "case_id": outcome.case_id,
        "version": outcome.version,
        "epistemic_status": outcome.oam_decision["epistemic_status"],
        "institutional_authorization_status": outcome.oam_decision[
            "institutional_authorization_status"
        ],
        "execution_disposition": outcome.oam_decision["execution_disposition"],
        "decision_basis": outcome.oam_decision["decision_basis"],
        "currentness_state": outcome.gate_decision.currentness_state,
        "currentness_reason_code_id": outcome.gate_decision.reason_code_id,
        "authority_decision": (
            AUTHORITY_NOT_EVALUATED
            if outcome.authority_decision is None
            else outcome.authority_decision.decision
        ),
        "authority_reason_code_id": (
            AUTHORITY_NOT_EVALUATED
            if outcome.authority_decision is None
            else outcome.authority_decision.reason_code_id
        ),
        "ztl_disposition": outcome.kernel_result.disposition,
        "ztl_warranty_grade": outcome.kernel_result.warranty_grade,
        "ztl_raw_verdict": outcome.kernel_result.raw_verdict,
        "action_state": outcome.action_state,
        "reliance_disposition": (
            None if outcome.reliance is None else outcome.reliance["reliance_disposition"]
        ),
        "reliance_reason_code_id": (
            None if outcome.reliance is None else outcome.reliance["reason_code_id"]
        ),
    }


def _case_plan(scenario: Scenario, case_id: str) -> tuple[str, str]:
    """Which policy version each case exercises, and at which declared instant."""
    plan = {
        "case-1": ("v1", "before_v2_effective"),
        "case-2": ("v1", "after_v2_effective"),
        "case-3": ("v1", "before_v2_effective"),
        "case-4": ("v1", "before_v2_effective"),
        "case-5": ("v2", "after_v2_effective"),
    }
    if case_id not in plan:
        raise DemoRuntimeError(f"unknown case: {case_id}")
    version, time_name = plan[case_id]
    return version, scenario.time(time_name)


def run_case(
    case_id: str,
    *,
    scenario: Scenario,
    compiled: dict[str, CompiledPolicy],
    index: CurrentnessIndex,
    repo_root: Path,
    ztl_path: Path,
    execution_context: ExecutionContext,
    work_dir: Path | None = None,
    authorization: ValidatedExecutionAuthorization | None = None,
) -> CaseOutcome:
    """Run one semantic case end to end, in the bounded demonstration lane.

    ``execution_context`` is carried into every record this produces. A
    development-test run is labelled as one, everywhere, so no artifact it emits
    can later be read as a measured result.
    """
    version, evaluated_at = _case_plan(scenario, case_id)
    policy = compiled[version]
    output_ref = scenario.output_ref(version)

    # --- 00-source: the evidence observation, opened and verified before anything
    # is concluded from it. The requirement lives in the policy; the state lives
    # here; satisfaction is established by comparing them, never by either alone.
    evidence = load_evidence_observation(scenario)

    # --- 02-ztl: the logical layer, called live and read without interpretation.
    marking = ground_marking(policy, amount=scenario.test_amount, evidence_state=evidence.state)
    kernel_result = invoke_kernel(
        formula=str(scenario.document["ztl"]["positive_formula"]),
        marking=marking,
        repo_root=repo_root,
        ztl_path=ztl_path,
    )
    epistemic_status = epistemic_status_for(kernel_result.disposition)
    warrant = build_warrant(
        kernel_result,
        warrant_artifact_id=f"warrant:{case_id}/{version}",
        claim_id=f"claim:{scenario.policy_family}/{version}",
        ground_epoch={
            "scope_id": scenario.scope_ref,
            "sequence": 1 if version == "v1" else 2,
            "authority_id": policy.authority_record["authority_id"],
        },
        ground_set_hash=canonical_json_digest(sorted(marking)),
        source_anchor_ids=[
            str(anchor["anchor_id"]) for anchor in policy.control_envelope["source_anchors"]
        ],
        admission_ids=[str(item) for item in policy.control_envelope["admission_ids"]],
        generated_at=evaluated_at,
        valid_from=evaluated_at,
        valid_until=None,
        revocation_references=[str(item) for item in policy.control_envelope["revocation_sources"]],
    )

    # --- 01-oic: currentness, evaluated by the unmodified L0 gate.
    historical_artifact = {
        "body": policy.control_envelope,
        "historical_state": "COMPILED_CONTROL_ENVELOPE",
    }
    gate_decision = evaluate_present_use(
        request=UseGateRequest(
            output_ref=output_ref,
            requested_use=REQUESTED_USE,
            requested_operation_class="SYNTHETIC_BOUNDED_DEMONSTRATION",
            consequential=True,
            requesting_scope_ref=scenario.scope_ref,
            requested_at=evaluated_at,
        ),
        historical_artifact=historical_artifact,
        currentness_index=index,
        profile=UseGateProfile(next_gate_on_current="AUTHORITY_AND_ADMISSIBILITY_GATE"),
        run_metadata={
            "run_id": f"OIC-ZTL-OAM-DEMO-SLICE-001-{execution_context.value}",
            "trace_id": f"OIC-ZTL-OAM-DEMO-SLICE-001-{case_id}-TRACE",
            "producer": "oic.demo_runtime",
            "producer_version": "0.1.0",
            "occurred_at": evaluated_at,
            "recorded_at": evaluated_at,
        },
    )
    resolution = resolve_currentness(
        output_ref=output_ref,
        historical_artifact=historical_artifact,
        index=index,
        evaluated_at=evaluated_at,
    )

    # --- 01-oic: authority, which currentness never implies — and which is not
    # even reached when currentness refused. Evaluating it anyway would produce an
    # A1 for an operation the gate had already stopped, and an A1 on the record is
    # indistinguishable from one that meant something.
    artifact_digest = historical_artifact_digest(policy.control_envelope)
    authority_decision: AuthorityDecisionRecord | None = None
    authority_not_evaluated_reason: str | None = None
    if gate_decision.reason_code_id != "G1" or gate_decision.decision != "PROCEED":
        authority_not_evaluated_reason = CURRENTNESS_GATE_DID_NOT_PROCEED
    else:
        authority_decision = evaluate_synthetic_authority(
            request=AuthorityRequest(
                artifact_ref=output_ref,
                artifact_digest=artifact_digest,
                recomputed_artifact_digest=artifact_digest,
                requested_use=REQUESTED_USE,
                scope=scenario.scope_ref,
                requesting_principal=DEMO_SUBJECT_PRINCIPAL,
                currentness_resolution_digest=resolution.resolution_digest,
                currentness_epoch_digest=_epoch_for(index, output_ref, evaluated_at),
                evaluation_time=evaluated_at,
                valid_until="2027-12-31T23:59:59Z",
                decision_id=f"decision:{case_id}/{version}",
            ),
            authority_bases=[
                parse_basis_record(record) for record in _authority_bases_for(scenario, case_id)
            ],
            admissibility_bases=[parse_basis_record(_admissibility_basis(scenario))],
            artifact_class=ARTIFACT_CLASS,
        )

    # --- 03-runtime: re-derive every binding the warrant claims, from state this
    # function recomputes rather than from what it just wrote.
    warrant_findings = validate_warrant_binding(
        warrant,
        runtime_binding=policy.runtime_binding,
        control_envelope=policy.control_envelope,
        envelope_digest=policy.envelope_digest,
        source_version_set_hash=canonical_json_digest([policy.source.content_hash]),
        admission_version=canonical_json_digest(
            [record["admission_id"] for record in policy.admission_records]
        ),
        ground_set_hash=canonical_json_digest(sorted(marking)),
        evaluated_at=evaluated_at,
        schema=_warrant_schema(repo_root),
    )

    # --- 03-runtime: composition. Four fields, none overwriting another.
    proposal_id = f"proposal:{case_id}/{scenario.document['action']}/{scenario.test_amount}"
    components = _components(
        epistemic_status=epistemic_status,
        warranty_grade=kernel_result.warranty_grade,
        unverified_ground_ids=list(kernel_result.unverified),
        gate_decision=gate_decision,
        authority=authority_decision,
        compiled=policy,
        binding_ok=policy.runtime_binding["envelope_hash"] == policy.envelope_digest,
        evidence=evidence,
        warrant_findings=warrant_findings,
        proposal_id=proposal_id,
    )
    authorization_status, disposition, basis, unmet = _compose(
        components, authority=authority_decision
    )
    action_state = _action_state(disposition)

    oam_decision = {
        "record_class": "OIC_DEMO_OAM_DECISION",
        "schema_version": OAM_DECISION_SCHEMA_VERSION,
        "decision_id": f"oam:{case_id}/{version}",
        "case_id": case_id,
        "scenario_id": SCENARIO_ID,
        "execution_context": execution_context.value,
        "evaluated_at": evaluated_at,
        # The four separated fields.
        "epistemic_status": epistemic_status,
        "institutional_authorization_status": authorization_status,
        "execution_disposition": disposition,
        "decision_basis": basis,
        # Typed upstream observations, preserved rather than summarised away.
        "ztl_observation": {
            "disposition": kernel_result.disposition,
            "warranty_grade": kernel_result.warranty_grade,
            "raw_verdict": kernel_result.raw_verdict,
            "raw_verdict_is_operationally_inert": True,
            "unverified_ground_ids": list(kernel_result.unverified),
            "kernel_profile_id": KERNEL_PROFILE_ID,
            "warrant_artifact_id": warrant["warrant_artifact_id"],
        },
        "currentness_observation": {
            "state": gate_decision.currentness_state,
            "reason_code_id": gate_decision.reason_code_id,
            "reason_code": gate_decision.reason_code,
            "decision": gate_decision.decision,
            "resolution_digest": gate_decision.resolution_digest,
        },
        "authority_observation": (
            {
                "authority_evaluated": True,
                "decision": authority_decision.decision,
                "reason_code_id": authority_decision.reason_code_id,
                "reason_code": authority_decision.reason_code,
                "authority_decision_digest": authority_decision.authority_decision_digest,
            }
            if authority_decision is not None
            else {
                "authority_evaluated": False,
                "authority_not_evaluated_reason": authority_not_evaluated_reason,
                "decision": AUTHORITY_NOT_EVALUATED,
                "reason_code_id": AUTHORITY_NOT_EVALUATED,
            }
        ),
        "evidence_observation": evidence.as_record(),
        "warrant_binding_validation": {
            "validated": not warrant_findings,
            "findings": [str(finding) for finding in warrant_findings],
        },
        "unmet_components": unmet,
        "bounded_action": {
            "proposal_id": proposal_id,
            "action_state": action_state,
            "gate_class": ACTION_GATE_CLASS,
            "performs_real_world_effect": False,
        },
        "runtime_binding_id": policy.runtime_binding["binding_id"],
        "claim_ceiling": "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED",
        "measured_end_to_end_claim": False,
    }

    outcome = CaseOutcome(
        case_id=case_id,
        version=version,
        execution_context=execution_context,
        evaluated_at=evaluated_at,
        compiled=policy,
        kernel_result=kernel_result,
        warrant=warrant,
        gate_decision=gate_decision,
        authority_decision=authority_decision,
        oam_decision=oam_decision,
        action_state=action_state,
        evidence=evidence,
        warrant_findings=tuple(str(finding) for finding in warrant_findings),
    )

    # --- 04-reliance: only reachable when the runtime allowed the action.
    reliance_permitted = authorization is None or authorization.permits_reliance(case_id)
    if disposition == ALLOW and work_dir is not None and reliance_permitted:
        _issue_reliance(
            outcome,
            scenario=scenario,
            index=index,
            compiled=compiled,
            work_dir=work_dir,
            evaluated_at=evaluated_at,
            authorization=authorization,
        )
    elif disposition == ALLOW and work_dir is not None and not reliance_permitted:
        outcome.absent_artifacts.append(
            {
                "artifact": "reliance_record",
                "reason": (
                    "the runtime permitted the action, but this case is not named in the "
                    "authorization's authorized_reliance_case_ids"
                ),
                "execution_disposition": disposition,
                "decision_basis": basis,
            }
        )
    else:
        outcome.absent_artifacts.append(
            {
                "artifact": "reliance_record",
                "reason": (
                    "no reliance was issued because the runtime did not permit the action"
                    if work_dir is not None
                    else "no working directory was supplied, so the propagation leg did not run"
                ),
                "execution_disposition": disposition,
                "decision_basis": basis,
            }
        )
    return outcome


# ---------------------------------------------------------------------------
# Propagation and reliance
# ---------------------------------------------------------------------------


def _consumer_job(
    outcome: CaseOutcome,
    *,
    scenario: Scenario,
    work_dir: Path,
    envelope_path: Path,
    decision_path: Path,
    evaluated_at: str,
) -> dict[str, Any]:
    return {
        "case_id": outcome.case_id,
        "version": outcome.version,
        "scenario_root": str(scenario.root),
        "envelope_path": str(envelope_path),
        "decision_path": str(decision_path),
        "output_path": str(work_dir / f"{outcome.case_id}-consumer-result.json"),
        "authorization_path": str(work_dir / f"{outcome.case_id}-issuance-authorization.json"),
        "attempt_path": str(work_dir / f"{outcome.case_id}-issuance-attempt.json"),
        "now": evaluated_at,
        "reliance_id": f"reliance:{outcome.case_id}/{outcome.version}",
        "execution_context": outcome.execution_context.value,
    }


def _issue_reliance(
    outcome: CaseOutcome,
    *,
    scenario: Scenario,
    index: CurrentnessIndex,
    compiled: dict[str, CompiledPolicy],
    work_dir: Path,
    evaluated_at: str,
    authorization: ValidatedExecutionAuthorization | None = None,
) -> None:
    """Produce an envelope, then run the consumer as a separate OS process.

    The producer and the consumer are different principals and different
    processes. The consumer receives paths, not objects: it opens the governed
    bytes itself, re-resolves currentness and re-evaluates authority before it
    will consider issuing anything.
    """
    del compiled
    if outcome.authority_decision is None:
        raise DemoRuntimeError(
            "propagation reached without an authority decision; the runtime must not "
            "propagate an operation whose authority was never evaluated"
        )
    output_ref = scenario.output_ref(outcome.version)

    # Materialize the warrant and the evidence observation as governed bytes
    # BEFORE building the envelope, so the envelope can bind digests a consumer
    # can independently recompute. An evidence_ref that only carries an id tells a
    # consumer nothing it can check.
    warrant_path = work_dir / f"{outcome.case_id}-warrant.json"
    warrant_bytes = (
        json.dumps(outcome.warrant, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    warrant_path.write_bytes(warrant_bytes)

    evidence_refs: list[dict[str, Any]] = [
        {
            "evidence_id": str(outcome.warrant["warrant_artifact_id"]),
            "evidence_class": "DEMO_WARRANT_ARTIFACT",
            "path": str(warrant_path),
            "sha256": persisted_file_sha256(warrant_bytes),
        }
    ]
    if outcome.evidence is not None and outcome.evidence.sha256:
        evidence_bytes = outcome.evidence.path.read_bytes()
        evidence_path = work_dir / f"{outcome.case_id}-evidence-observation.json"
        evidence_path.write_bytes(evidence_bytes)
        evidence_refs.append(
            {
                "evidence_id": outcome.evidence.evidence_id,
                "evidence_class": outcome.evidence.evidence_class,
                "path": str(evidence_path),
                "sha256": persisted_file_sha256(evidence_bytes),
            }
        )
    envelope = build_envelope(
        envelope_id=f"envelope:{outcome.case_id}/{outcome.version}",
        artifact_ref=output_ref,
        artifact_digest=historical_artifact_digest(outcome.compiled.control_envelope),
        requested_use=REQUESTED_USE,
        scope=scenario.scope_ref,
        requesting_subject_principal=DEMO_SUBJECT_PRINCIPAL,
        producer_identity=ProducerIdentity(
            producer_principal=PRODUCER_PRINCIPAL,
            process_id=os.getpid(),
            run_id=f"OIC-ZTL-OAM-DEMO-SLICE-001-{outcome.execution_context.value}",
            trace_id=f"OIC-ZTL-OAM-DEMO-SLICE-001-{outcome.case_id}-TRACE",
        ),
        intended_consumer_principal=CONSUMER_PRINCIPAL,
        currentness_resolution_digest=outcome.gate_decision.resolution_digest,
        currentness_index_digest=index.index_digest,
        currentness_epoch_digest=_epoch_for(index, output_ref, evaluated_at),
        authority_decision_digest=outcome.authority_decision.authority_decision_digest,
        authority_basis_refs=list(outcome.authority_decision.authority_basis_refs),
        admissibility_basis_refs=list(outcome.authority_decision.admissibility_basis_refs),
        evidence_refs=evidence_refs,
        produced_at=evaluated_at,
        valid_until="2027-12-31T23:59:59Z",
    )
    envelope_path = work_dir / f"{outcome.case_id}-envelope.json"
    materialize_envelope(envelope.as_record(), envelope_path)

    decision_path = work_dir / f"{outcome.case_id}-authority-decision.json"
    decision_path.write_bytes(
        (
            json.dumps(outcome.authority_decision.as_record(), sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
    )

    authorization_path = work_dir / f"{outcome.case_id}-issuance-authorization.json"
    authorization_path.write_bytes(
        (
            json.dumps(
                {
                    "record_class": "DEMO_RELIANCE_ISSUANCE_AUTHORIZATION",
                    "case_id": outcome.case_id,
                    "execution_context": outcome.execution_context.value,
                    "single_use": True,
                    # Under DEVELOPMENT_TEST_ONLY this is genuinely not result
                    # bearing. Under a validated owner authorization it binds that
                    # instrument by identity and digest, so the reliance record can
                    # be traced to the act that permitted it.
                    "result_bearing": authorization is not None,
                    "owner_authorization_id": (
                        None if authorization is None else authorization.authorization_id
                    ),
                    "owner_authorization_sha256": (
                        None if authorization is None else authorization.file_sha256
                    ),
                    "authorized_reliance_case": (
                        None
                        if authorization is None
                        else authorization.permits_reliance(outcome.case_id)
                    ),
                },
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
    )

    job = _consumer_job(
        outcome,
        scenario=scenario,
        work_dir=work_dir,
        envelope_path=envelope_path,
        decision_path=decision_path,
        evaluated_at=evaluated_at,
    )
    job_path = work_dir / f"{outcome.case_id}-consumer-job.json"
    job_path.write_bytes((json.dumps(job, sort_keys=True, indent=2) + "\n").encode("utf-8"))

    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, this module as consumer
        [sys.executable, "-m", "oic.demo_runtime", "--consumer-job", str(job_path)],
        capture_output=True,
        check=False,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise DemoRuntimeError(f"the reliance consumer process failed: {completed.stderr.strip()}")
    result = json.loads(Path(job["output_path"]).read_text(encoding="utf-8"))
    outcome.reliance = result["reliance_record"]
    outcome.consumer_validation = result["validation"]


def _run_consumer(job_path: Path) -> int:
    """The reliance consumer, in its own process.

    It is handed paths and instants, never producer objects. Everything it
    concludes it concludes from bytes it opened itself.
    """
    job = json.loads(job_path.read_text(encoding="utf-8"))
    repo_root = Path(__file__).resolve().parents[2]
    scenario = load_scenario(repo_root)
    compiled = compile_scenario(scenario)
    index = build_currentness_index(scenario, compiled)
    now = str(job["now"])

    envelope_bytes = read_materialized_envelope(Path(str(job["envelope_path"])))
    propagated_decision = json.loads(Path(str(job["decision_path"])).read_text(encoding="utf-8"))
    version = str(job["version"])
    policy = compiled[version]
    output_ref = scenario.output_ref(version)

    def recompute_artifact_digest(artifact_ref: str) -> str | None:
        if artifact_ref != output_ref:
            return None
        return historical_artifact_digest(policy.control_envelope)

    def resolve_evidence_ref(ref: Mapping[str, Any]) -> bool:
        """Open the referenced bytes, recompute the digest, and compare.

        Returning true because the reference carried an identifier would make
        this check unfalsifiable: a substituted, corrupted or absent artifact
        would resolve exactly as well as the real one.
        """
        location = ref.get("path")
        bound = ref.get("sha256")
        if not isinstance(location, str) or not isinstance(bound, str) or not bound:
            return False
        path = Path(location)
        if not path.is_file():
            return False
        if persisted_file_sha256(path.read_bytes()) != bound:
            return False
        return bool(ref.get("evidence_id")) and bool(ref.get("evidence_class"))

    def re_resolve(artifact_ref: str, at: str) -> ReResolvedCurrentness:
        historical_artifact = {
            "body": policy.control_envelope,
            "historical_state": "COMPILED_CONTROL_ENVELOPE",
        }
        resolution = resolve_currentness(
            output_ref=artifact_ref,
            historical_artifact=historical_artifact,
            index=index,
            evaluated_at=at,
        )
        return ReResolvedCurrentness(
            currentness_state=resolution.currentness_state,
            resolution_digest=resolution.resolution_digest,
            epoch_digest=_epoch_for(index, artifact_ref, at),
            basis_reachable=index.covers(artifact_ref),
        )

    def re_evaluate(
        artifact_ref: str, at: str, re_resolved: ReResolvedCurrentness
    ) -> AuthorityDecisionRecord:
        digest = historical_artifact_digest(policy.control_envelope)
        return evaluate_synthetic_authority(
            request=AuthorityRequest(
                artifact_ref=artifact_ref,
                artifact_digest=digest,
                recomputed_artifact_digest=digest,
                requested_use=REQUESTED_USE,
                scope=scenario.scope_ref,
                requesting_principal=DEMO_SUBJECT_PRINCIPAL,
                currentness_resolution_digest=re_resolved.resolution_digest,
                currentness_epoch_digest=re_resolved.epoch_digest,
                evaluation_time=at,
                valid_until="2027-12-31T23:59:59Z",
                decision_id=f"reliance-time-decision:{job['case_id']}",
            ),
            authority_bases=[
                parse_basis_record(record)
                for record in _authority_bases_for(scenario, str(job["case_id"]))
            ],
            admissibility_bases=[parse_basis_record(_admissibility_basis(scenario))],
            artifact_class=ARTIFACT_CLASS,
        )

    context = ConsumerContext(
        consumer_profile=parse_profile(_profile(scenario, consumer=True)),
        producer_profile=parse_profile(_profile(scenario, consumer=False)),
        consumer_identity={
            "consumer_principal": CONSUMER_PRINCIPAL,
            "process_id": os.getpid(),
            "execution_context": str(job["execution_context"]),
        },
        now=now,
        expected_scope=scenario.scope_ref,
        expected_requested_use=REQUESTED_USE,
        expected_subject_principal=DEMO_SUBJECT_PRINCIPAL,
        recompute_artifact_digest=recompute_artifact_digest,
        resolve_evidence_ref=resolve_evidence_ref,
        re_resolve_currentness=re_resolve,
        re_evaluate_authority=re_evaluate,
    )

    validation_outcome = run_consumer_validation(
        envelope_bytes=envelope_bytes,
        propagated_decision=propagated_decision,
        context=context,
    )
    attempt = claim_issuance_attempt(
        authorization_path=Path(str(job["authorization_path"])),
        attempt_path=Path(str(job["attempt_path"])),
        run_id=f"OIC-ZTL-OAM-DEMO-SLICE-001-{job['execution_context']}",
        trace_id=f"OIC-ZTL-OAM-DEMO-SLICE-001-{job['case_id']}-TRACE",
        claimed_at=now,
    )
    reliance = issue_reliance(
        reliance_id=str(job["reliance_id"]),
        validation_outcome=validation_outcome,
        propagated_decision=propagated_decision,
        context=context,
        issuance_authorization_digest=str(attempt["issuance_authorization_digest"]),
        attempt_record_digest=str(attempt["attempt_record_digest"]),
        evidence_refs=[
            {
                "evidence_id": "consumer_validation",
                "digest": validation_outcome["validation"]["consumer_validation_digest"],
            }
        ],
        issued_at=now,
    )
    payload = {
        "validation": validation_outcome["validation"],
        "reliance_record": reliance,
        "consumer_process_id": os.getpid(),
    }
    output_path = Path(str(job["output_path"]))
    output_path.write_bytes(
        (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    sys.stdout.write(f"{output_path}\n")
    return 0


# ---------------------------------------------------------------------------
# Orchestration, validation and the result-bearing gate
# ---------------------------------------------------------------------------


def run_all_cases(
    *,
    repo_root: Path,
    ztl_path: Path,
    execution_context: ExecutionContext,
    work_dir: Path | None = None,
    scenario_id: str = SCENARIO_ID,
    authorization: ValidatedExecutionAuthorization | None = None,
) -> dict[str, CaseOutcome]:
    """Run the five semantic cases against one compiled scenario.

    Supplying ``ExecutionContext.OWNER_AUTHORIZED_RESULT_BEARING`` is not itself
    authorization. The enum is a label a caller can type; the interlock below
    requires the object that only the full binding validator returns, and it
    refuses before the kernel is called or any byte is written.
    """
    if execution_context is ExecutionContext.OWNER_AUTHORIZED_RESULT_BEARING:
        if authorization is None:
            raise _refuse(
                "a result-bearing execution context was requested without a validated owner "
                "authorization; the execution context alone authorizes nothing"
            )
        if authorization.implementation_commit != _git_head(repo_root):
            raise _refuse("the validated authorization is not bound to the current HEAD")
    elif authorization is not None:
        raise DemoRuntimeError(
            "a result-bearing authorization was supplied for a DEVELOPMENT_TEST_ONLY run; "
            "development and result-bearing execution must not be mixed"
        )
    scenario = load_scenario(repo_root, scenario_id)
    compiled = compile_scenario(scenario)
    index = build_currentness_index(scenario, compiled)
    outcomes: dict[str, CaseOutcome] = {}
    for case_id in CASE_IDS:
        case_dir = None if work_dir is None else work_dir / case_id
        if case_dir is not None:
            case_dir.mkdir(parents=True, exist_ok=True)
        outcomes[case_id] = run_case(
            case_id,
            scenario=scenario,
            compiled=compiled,
            index=index,
            repo_root=repo_root,
            ztl_path=ztl_path,
            execution_context=execution_context,
            work_dir=case_dir,
            authorization=authorization,
        )
    return outcomes


def validate_scenario(repo_root: Path, scenario_id: str = SCENARIO_ID) -> dict[str, Any]:
    """Compile the scenario and report what it produced, without calling ZTL.

    This is the ``oic demo validate`` path: it exercises the compiler chain and
    the currentness state, and deliberately performs no logical evaluation and
    no execution.
    """
    scenario = load_scenario(repo_root, scenario_id)
    compiled = compile_scenario(scenario)
    index = build_currentness_index(scenario, compiled)
    versions: dict[str, Any] = {}
    for version, policy in sorted(compiled.items()):
        versions[version] = {
            "source_content_hash": policy.source.content_hash,
            "candidates": len(policy.candidates),
            "admitted_units": list(policy.admitted_unit_ids),
            "executable_conditions": [
                str(condition["condition_id"])
                for condition in policy.control_envelope["conditions"]
            ],
            "envelope_id": str(policy.control_envelope["envelope_id"]),
            "envelope_digest": policy.envelope_digest,
            "runtime_binding_id": str(policy.runtime_binding["binding_id"]),
            "output_ref": scenario.output_ref(version),
        }
    evidence = load_evidence_observation(scenario)
    return {
        "scenario_id": scenario_id,
        "scope_ref": scenario.scope_ref,
        "currentness_index_digest": index.index_digest,
        # The three identities an owner needs in order to issue a result-bearing
        # authorization that cannot be re-aimed at a different tree, a different
        # scenario or a different kernel.
        "implementation_commit": _git_head(repo_root),
        "scenario_bundle_digest": scenario_bundle_digest(scenario),
        "scenario_bundle": scenario_bundle_manifest(scenario),
        "expected_ztl_commit": KERNEL_COMMIT,
        "evidence_observation": evidence.as_record(),
        "versions": versions,
        "execution_performed": False,
        "result_bearing_execution": False,
        "ztl_invoked": False,
        "claim_ceiling": str(scenario.document["claim_ceiling"]),
    }


@dataclass(frozen=True, slots=True)
class ValidatedExecutionAuthorization:
    """Proof that an owner authorization was validated against observed state.

    Only this object opens the result-bearing path. It cannot be constructed by
    passing an enum, a flag or a dict: it is returned solely by the validator
    below, so "authorized" means "checked", not "asserted".
    """

    document: Mapping[str, Any]
    path: Path
    file_sha256: str
    implementation_commit: str
    scenario_bundle_digest: str
    ztl_commit: str
    allowed_output_directory: Path

    @property
    def authorization_id(self) -> str:
        """The owner's identifier for this authorization."""
        return str(self.document["authorization_id"])

    def permits_reliance(self, case_id: str) -> bool:
        """Whether this authorization allows reliance issuance for one case."""
        return case_id in set(self.document["authorized_reliance_case_ids"])


def _refuse(reason: str) -> DemoRuntimeError:
    return DemoRuntimeError(f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: {reason}")


def _git_head(repo_root: Path) -> str:
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, read-only
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise _refuse(f"cannot resolve the implementation commit: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _worktree_is_clean(repo_root: Path) -> bool:
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, read-only
        ["git", "-C", str(repo_root), "status", "--porcelain"],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )
    return completed.returncode == 0 and completed.stdout.strip() == ""


def load_result_bearing_authorization(
    path: Path | None,
    *,
    repo_root: Path | None = None,
    output_directory: Path | None = None,
    ztl_path: Path | None = None,
    scenario_id: str = SCENARIO_ID,
) -> ValidatedExecutionAuthorization:
    """Validate an owner authorization against what is actually observable.

    Checking three fields would let an authorization issued for another tree,
    another scenario, another kernel or another destination open this gate. Every
    binding the artifact carries is therefore compared to recomputed state, and
    each failure names the specific mismatch rather than refusing generically.

    Called without a repository root it performs structural validation only and
    still refuses to return anything a caller could execute against, because the
    bindings cannot be checked.
    """
    if path is None:
        raise _refuse("no owner result-bearing execution authorization was supplied")
    if not path.is_file():
        raise _refuse(f"no authorization artifact at {path}")

    payload = path.read_bytes()
    document: Mapping[str, Any] = json.loads(payload.decode("utf-8"))

    if repo_root is None:
        raise _refuse(
            "no repository root was supplied, so the authorization's bindings cannot be "
            "checked; an unchecked authorization never opens this gate"
        )

    schema = json.loads(
        (repo_root / "schemas" / "demo" / "execution-authorization.schema.json").read_text(
            encoding="utf-8"
        )
    )
    from jsonschema import Draft202012Validator

    errors = sorted(
        Draft202012Validator(schema).iter_errors(dict(document)), key=lambda item: item.json_path
    )
    if errors:
        detail = "; ".join(f"{error.json_path}: {error.message}" for error in errors[:5])
        raise _refuse(f"the authorization does not satisfy its schema: {detail}")

    if document["scenario_id"] != scenario_id:
        raise _refuse(f"the artifact authorizes scenario {document['scenario_id']!r}")

    observed_commit = _git_head(repo_root)
    if document["implementation_commit"] != observed_commit:
        raise _refuse(
            f"authorization implementation_commit {document['implementation_commit']} is not the "
            f"current HEAD {observed_commit}"
        )
    scenario = load_scenario(repo_root, scenario_id)
    recomputed_bundle = scenario_bundle_digest(scenario)
    if document["scenario_bundle_digest"] != recomputed_bundle:
        raise _refuse(
            f"authorization scenario_bundle_digest {document['scenario_bundle_digest']} does not "
            f"match the recomputed bundle {recomputed_bundle}"
        )

    if document["ztl_commit"] != KERNEL_COMMIT:
        raise _refuse(
            f"authorization ztl_commit {document['ztl_commit']} is not the pinned kernel commit"
        )
    if ztl_path is not None:
        observed_kernel = _observed_ztl_commit(ztl_path)
        if observed_kernel != KERNEL_COMMIT:
            raise _refuse(
                f"the ZTL checkout at {ztl_path} is at {observed_kernel}, not the pinned commit"
            )

    allowed_output = Path(str(document["allowed_output_directory"]))
    if (
        output_directory is not None
        and Path(output_directory).resolve() != allowed_output.resolve()
    ):
        raise _refuse(
            f"requested output directory {output_directory} is not the authorized {allowed_output}"
        )

    if document["claim_ceiling"] != MEASURED_INTERNAL_CEILING:
        raise _refuse(f"authorization claim_ceiling {document['claim_ceiling']!r} is not allowed")
    if set(document["authorized_case_ids"]) != set(CASE_IDS):
        raise _refuse("authorized_case_ids are not exactly the five declared cases")

    # Checked last on purpose: a specific binding mismatch is far more useful to
    # the operator than "your tree is dirty", and this requirement is about the
    # run being reproducible rather than about the artifact being wrong.
    if not _worktree_is_clean(repo_root):
        raise _refuse(
            "the repository working tree is not clean; a result-bearing run must be "
            "reproducible from committed state alone"
        )

    return ValidatedExecutionAuthorization(
        document=document,
        path=path,
        file_sha256=persisted_file_sha256(payload),
        implementation_commit=str(document["implementation_commit"]),
        scenario_bundle_digest=str(document["scenario_bundle_digest"]),
        ztl_commit=str(document["ztl_commit"]),
        allowed_output_directory=allowed_output,
    )


def _observed_ztl_commit(ztl_path: Path) -> str:
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, read-only
        ["git", "-C", str(ztl_path), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def claim_execution_authorization(
    authorization: ValidatedExecutionAuthorization, *, consumption_path: Path, claimed_at: str
) -> dict[str, Any]:
    """Consume a single-use authorization, or refuse.

    Exclusive creation is the whole mechanism: the second claim loses the race
    against the filesystem rather than against a check that could be skipped. The
    authorization artifact itself is never mutated — consuming it is a separate
    record, so the owner's instrument stays exactly as issued.
    """
    record = {
        "record_class": "DEMO_EXECUTION_AUTHORIZATION_CONSUMPTION",
        "authorization_id": authorization.authorization_id,
        "authorization_path": str(authorization.path),
        "authorization_sha256": authorization.file_sha256,
        "implementation_commit": authorization.implementation_commit,
        "scenario_bundle_digest": authorization.scenario_bundle_digest,
        "ztl_commit": authorization.ztl_commit,
        "allowed_output_directory": str(authorization.allowed_output_directory),
        "claimed_at": claimed_at,
        "state": "CONSUMED_AT_FIRST_CLAIM",
    }
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    try:
        descriptor = os.open(consumption_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: authorization "
            f"{authorization.authorization_id} is already consumed; no automatic retry is "
            "authorized"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "consumption_record": record,
        "consumption_path": str(consumption_path),
        "consumption_digest": persisted_file_sha256(payload),
    }


def write_evidence_graph(
    outcomes: dict[str, CaseOutcome],
    out_dir: Path,
    *,
    scenario: Scenario | None = None,
    authorization: ValidatedExecutionAuthorization | None = None,
) -> dict[str, Any]:
    """Emit the six-stage evidence graph for a completed set of cases.

    Two properties make the package independently inspectable rather than merely
    present. Every reference in the causal chain resolves to bytes that were
    actually written, with the digest they were written with. And every artifact a
    case did *not* produce carries a recorded reason: an absence with no reason is
    indistinguishable from an omission, so there are none here.
    """
    for name in EVIDENCE_DIRECTORIES:
        (out_dir / name).mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {"cases": {}, "directories": list(EVIDENCE_DIRECTORIES)}
    causal_chain: dict[str, Any] = {"cases": {}}
    written_files: list[tuple[str, dict[str, Any]]] = []

    def emit(stage: str, name: str, payload: object) -> dict[str, Any]:
        record = _write(out_dir / stage / name, payload)
        written_files.append((f"{stage}/{name}", record))
        return record

    for case_id, outcome in sorted(outcomes.items()):
        policy = outcome.compiled
        written: dict[str, Any] = {}

        # 00-source — the exact bytes, the document, the nodes, the identity.
        written["00-source"] = emit(
            "00-source",
            f"{case_id}-source.json",
            {
                "source_id": policy.source.source_id,
                "source_content_hash": policy.source.content_hash,
                "source_bytes_utf8": policy.source.payload.decode("utf-8"),
                "source_document": policy.source_document,
                "source_nodes": policy.source_document["nodes"],
                "evidence_observation": (
                    None if outcome.evidence is None else outcome.evidence.as_record()
                ),
            },
        )

        # 01-oic — every compilation artifact, admitted and unadmitted alike.
        written["01-oic"] = emit(
            "01-oic",
            f"{case_id}-compilation.json",
            {
                "candidate_normative_units": list(policy.candidates),
                "admission_records": list(policy.admission_records),
                "institutional_ir": policy.institutional_ir,
                "authority_record": policy.authority_record,
                "control_envelope": policy.control_envelope,
                "runtime_binding": policy.runtime_binding,
            },
        )

        # 02-ztl — exactly what the kernel was asked and exactly what it said.
        written["02-ztl"] = emit(
            "02-ztl",
            f"{case_id}-ztl.json",
            {
                "kernel_input": {
                    "caller_formula": outcome.kernel_result.caller_formula,
                    "marking": outcome.kernel_result.marking,
                },
                "raw_kernel_result": {
                    "rendered_formula": outcome.kernel_result.rendered_formula,
                    "disposition": outcome.kernel_result.disposition,
                    "raw_verdict": outcome.kernel_result.raw_verdict,
                    "warranty_grade": outcome.kernel_result.warranty_grade,
                    "unverified": list(outcome.kernel_result.unverified),
                },
                "warrant_artifact": outcome.warrant,
                "kernel_execution_identity": {
                    "kernel_commit": outcome.kernel_result.kernel_commit,
                    "kernel_profile_id": KERNEL_PROFILE_ID,
                    "entrypoint": "ztljudge.judge",
                    "prohibited_entrypoint_called": False,
                },
                "warrant_binding_validation": {
                    "validated": not outcome.warrant_findings,
                    "findings": list(outcome.warrant_findings),
                },
            },
        )

        # 03-runtime — including an explicit not-evaluated authority record.
        written["03-runtime"] = emit(
            "03-runtime",
            f"{case_id}-runtime.json",
            {
                "currentness_use_gate_decision": outcome.gate_decision.as_record(),
                "authority": (
                    outcome.authority_decision.as_record()
                    if outcome.authority_decision is not None
                    else {
                        "authority_evaluated": False,
                        "authority_not_evaluated_reason": CURRENTNESS_GATE_DID_NOT_PROCEED,
                    }
                ),
                "evidence_observation": (
                    None if outcome.evidence is None else outcome.evidence.as_record()
                ),
                "oam_decision": outcome.oam_decision,
                "action_proposal": outcome.oam_decision["bounded_action"],
                "bounded_execution_attempt": {
                    "gate_class": ACTION_GATE_CLASS,
                    "action_state": outcome.action_state,
                    "attempted_at": outcome.evaluated_at,
                    "performs_real_world_effect": False,
                    "execution_context": outcome.execution_context.value,
                },
            },
        )

        # 04-reliance — the whole leg, or a stated reason it does not exist.
        if outcome.reliance is not None:
            written["04-reliance"] = emit(
                "04-reliance",
                f"{case_id}-reliance.json",
                {
                    "consumer_validation": outcome.consumer_validation,
                    "reliance_record": outcome.reliance,
                },
            )
        else:
            written["04-reliance"] = emit(
                "04-reliance",
                f"{case_id}-absent.json",
                {
                    "absent_artifacts": outcome.absent_artifacts,
                    "propagation_envelope": None,
                    "consumer_validation": None,
                    "issuance_authorization": None,
                    "issuance_attempt": None,
                    "reliance_record": None,
                },
            )

        manifest["cases"][case_id] = {
            "execution_context": outcome.execution_context.value,
            "semantic_projection": decision_semantic_projection(outcome),
            "written": written,
            "absent_artifacts": outcome.absent_artifacts,
        }
        causal_chain["cases"][case_id] = {
            "source_content_hash": policy.source.content_hash,
            "admission_ids": list(policy.control_envelope["admission_ids"]),
            "source_anchor_ids": [
                str(anchor["anchor_id"]) for anchor in policy.control_envelope["source_anchors"]
            ],
            "envelope_id": str(policy.control_envelope["envelope_id"]),
            "envelope_digest": policy.envelope_digest,
            "runtime_binding_id": str(policy.runtime_binding["binding_id"]),
            "bound_formula_hash": str(policy.runtime_binding["bound_formula_hash"]),
            "warrant_artifact_id": str(outcome.warrant["warrant_artifact_id"]),
            "warrant_input_hash": str(outcome.warrant["input_hash"]),
            "warrant_output_hash": str(outcome.warrant["output_hash"]),
            "currentness_resolution_digest": outcome.gate_decision.resolution_digest,
            "authority_decision_digest": (
                None
                if outcome.authority_decision is None
                else outcome.authority_decision.authority_decision_digest
            ),
            "evidence_digest": (None if outcome.evidence is None else outcome.evidence.sha256),
            "reliance_record_digest": (
                None if outcome.reliance is None else outcome.reliance["reliance_record_digest"]
            ),
            "artifacts": dict(written),
        }

    if scenario is not None:
        causal_chain["scenario_bundle_digest"] = scenario_bundle_digest(scenario)
        causal_chain["scenario_bundle"] = scenario_bundle_manifest(scenario)
    causal_chain["owner_authorization_id"] = (
        None if authorization is None else authorization.authorization_id
    )

    contexts = {outcome.execution_context for outcome in outcomes.values()}
    complete = set(outcomes) == set(CASE_IDS)
    result_bearing = authorization is not None and contexts == {
        ExecutionContext.OWNER_AUTHORIZED_RESULT_BEARING
    }
    # A measured claim needs all five cases, a package that verifies itself, and an
    # authorization permitting that ceiling. Any one of them missing and the
    # ceiling stays where it is.
    manifest["claim_ceiling"] = (
        MEASURED_INTERNAL_CEILING if (complete and result_bearing) else DEVELOPMENT_CLAIM_CEILING
    )
    manifest["measured_end_to_end_claim"] = bool(complete and result_bearing)
    manifest["all_cases_present"] = complete
    manifest["result_bearing"] = result_bearing

    emit("05-evidence", "causal-chain.json", causal_chain)
    manifest_record = _write(out_dir / "05-evidence" / "MANIFEST.json", manifest)
    written_files.append(("05-evidence/MANIFEST.json", manifest_record))

    sums = "".join(
        f"{record['sha256']}  {relative}\n" for relative, record in sorted(written_files)
    )
    (out_dir / "05-evidence" / "SHA256SUMS").write_bytes(sums.encode("utf-8"))
    return manifest


def verify_evidence_graph(out_dir: Path) -> dict[str, Any]:
    """Re-open a written package and check it against its own SHA256SUMS.

    Self-verification is what makes the package inspectable by someone who was
    not there when it was written.
    """
    sums_path = out_dir / "05-evidence" / "SHA256SUMS"
    if not sums_path.is_file():
        return {"verified": False, "reason": "SHA256SUMS is absent", "checked": 0}
    checked = 0
    failures: list[str] = []
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, _, relative = line.partition("  ")
        path = out_dir / relative
        if not path.is_file():
            failures.append(f"{relative}: absent")
            continue
        if persisted_file_sha256(path.read_bytes()) != digest:
            failures.append(f"{relative}: digest mismatch")
        checked += 1
    return {"verified": not failures, "checked": checked, "failures": failures}


def execute_result_bearing_run(
    *,
    repo_root: Path,
    authorization_path: Path,
    output_directory: Path,
    ztl_path: Path | None = None,
    scenario_id: str = SCENARIO_ID,
    claimed_at: str,
) -> dict[str, Any]:
    """The positive path behind ``oic demo run``, in order, fail-closed at each step.

    validate the authorization against observed state
      -> claim its single use
      -> resolve the pinned ZTL checkout
      -> run all five cases under OWNER_AUTHORIZED_RESULT_BEARING
      -> write the evidence graph
      -> verify the written package against its own digests
      -> emit a final status

    Implemented so the frozen L1 baseline has a complete path rather than a stub,
    and not invoked anywhere in this work order: no owner authorization exists,
    and the validator above is the only thing that could produce one.
    """
    authorization = load_result_bearing_authorization(
        authorization_path,
        repo_root=repo_root,
        output_directory=output_directory,
        ztl_path=ztl_path,
        scenario_id=scenario_id,
    )
    consumption = claim_execution_authorization(
        authorization,
        consumption_path=output_directory.parent
        / f"{authorization.authorization_id}.consumed.json",
        claimed_at=claimed_at,
    )
    resolved_ztl = resolve_ztl_path(ztl_path)
    scenario = load_scenario(repo_root, scenario_id)
    outcomes = run_all_cases(
        repo_root=repo_root,
        ztl_path=resolved_ztl,
        execution_context=ExecutionContext.OWNER_AUTHORIZED_RESULT_BEARING,
        work_dir=output_directory / "work",
        scenario_id=scenario_id,
        authorization=authorization,
    )
    manifest = write_evidence_graph(
        outcomes, output_directory, scenario=scenario, authorization=authorization
    )
    verification = verify_evidence_graph(output_directory)
    return {
        "authorization_id": authorization.authorization_id,
        "consumption": consumption,
        "cases": sorted(outcomes),
        "manifest": manifest,
        "package_verification": verification,
        "status": (
            "RESULT_BEARING_EXECUTION_COMPLETE"
            if verification["verified"] and manifest["all_cases_present"]
            else "RESULT_BEARING_EXECUTION_INCOMPLETE"
        ),
    }


def _write(path: Path, payload: object) -> dict[str, Any]:
    data = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(data)
    return {"path": path.name, "bytes": len(data), "sha256": persisted_file_sha256(data)}


def main(argv: list[str] | None = None) -> int:
    """Consumer entry point. Not a public command; ``oic demo`` is the CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Internal demo consumer process.")
    parser.add_argument("--consumer-job", required=True, type=Path)
    args = parser.parse_args(argv)
    return _run_consumer(args.consumer_job)


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
