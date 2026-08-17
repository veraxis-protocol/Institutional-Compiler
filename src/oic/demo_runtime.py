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
    canonical_json_digest,
    compile_policy,
    ground_marking,
    load_policy_source,
)
from oic.demo_ztl import (
    CANONICALIZATION_PROFILE_ID,
    KERNEL_PROFILE_ID,
    KernelResult,
    build_warrant,
    epistemic_status_for,
    expected_formula_hash,
    invoke_kernel,
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
    gate_decision: UseGateDecision,
    authority: AuthorityDecisionRecord,
    compiled: CompiledPolicy,
    binding_ok: bool,
    evidence_ok: bool,
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
            "appropriate_epistemic_route",
            epistemic_status == "ESTABLISHED",
            epistemic_status,
            SUBSTANTIVE if epistemic_status == "REFUTED" else PRECAUTIONARY,
        ),
        _Component(
            "currentness_g1",
            gate_decision.reason_code_id == "G1",
            gate_decision.reason_code_id,
            PROCEDURAL,
        ),
        _Component(
            "authority_a1",
            authority.reason_code_id == "A1",
            authority.reason_code_id,
            PRECAUTIONARY if authority.reason_code_id == "A6" else PROCEDURAL,
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
        _Component("required_evidence", evidence_ok, evidence_ok, CONTROL_REQUIREMENT),
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
    authority: AuthorityDecisionRecord,
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
    authority_decision: AuthorityDecisionRecord
    oam_decision: dict[str, Any]
    action_state: str
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
        "authority_decision": outcome.authority_decision.decision,
        "authority_reason_code_id": outcome.authority_decision.reason_code_id,
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
) -> CaseOutcome:
    """Run one semantic case end to end, in the bounded demonstration lane.

    ``execution_context`` is carried into every record this produces. A
    development-test run is labelled as one, everywhere, so no artifact it emits
    can later be read as a measured result.
    """
    version, evaluated_at = _case_plan(scenario, case_id)
    policy = compiled[version]
    output_ref = scenario.output_ref(version)

    # --- 02-ztl: the logical layer, called live and read without interpretation.
    marking = ground_marking(policy, amount=scenario.test_amount, evidence_signed=True)
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

    # --- 01-oic: authority, which currentness never implies.
    artifact_digest = historical_artifact_digest(policy.control_envelope)
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
        evidence_ok=bool(policy.control_envelope["evidence_requirements"]),
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
        "authority_observation": {
            "decision": authority_decision.decision,
            "reason_code_id": authority_decision.reason_code_id,
            "reason_code": authority_decision.reason_code,
            "authority_decision_digest": authority_decision.authority_decision_digest,
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
    )

    # --- 04-reliance: only reachable when the runtime allowed the action.
    if disposition == ALLOW and work_dir is not None:
        _issue_reliance(
            outcome,
            scenario=scenario,
            index=index,
            compiled=compiled,
            work_dir=work_dir,
            evaluated_at=evaluated_at,
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
) -> None:
    """Produce an envelope, then run the consumer as a separate OS process.

    The producer and the consumer are different principals and different
    processes. The consumer receives paths, not objects: it opens the governed
    bytes itself, re-resolves currentness and re-evaluates authority before it
    will consider issuing anything.
    """
    del compiled
    output_ref = scenario.output_ref(outcome.version)
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
        evidence_refs=[
            {
                "evidence_id": warrant_ref,
                "evidence_class": "DEMO_WARRANT_ARTIFACT",
            }
            for warrant_ref in [outcome.warrant["warrant_artifact_id"]]
        ],
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
                    "result_bearing": False,
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
        return bool(ref.get("evidence_id"))

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
) -> dict[str, CaseOutcome]:
    """Run the five semantic cases against one compiled scenario."""
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
    return {
        "scenario_id": scenario_id,
        "scope_ref": scenario.scope_ref,
        "currentness_index_digest": index.index_digest,
        "versions": versions,
        "execution_performed": False,
        "result_bearing_execution": False,
        "claim_ceiling": str(scenario.document["claim_ceiling"]),
    }


def load_result_bearing_authorization(path: Path | None) -> dict[str, Any]:
    """Refuse a result-bearing run unless the owner separately authorized one.

    There is no flag, environment variable or default that opens this gate. The
    only route is an owner-issued artifact naming this scenario and saying so.
    """
    if path is None:
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: no owner result-bearing execution "
            "authorization was supplied"
        )
    if not path.is_file():
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: no authorization artifact at {path}"
        )
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != EXECUTION_AUTHORIZATION_SCHEMA_VERSION:
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: authorization declares schema_version "
            f"{document.get('schema_version')!r}"
        )
    if document.get("result_bearing_execution_authorized") is not True:
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: the artifact does not authorize a "
            "result-bearing execution"
        )
    if document.get("scenario_id") != SCENARIO_ID:
        raise DemoRuntimeError(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: the artifact authorizes scenario "
            f"{document.get('scenario_id')!r}"
        )
    return document


def write_evidence_graph(outcomes: dict[str, CaseOutcome], out_dir: Path) -> dict[str, Any]:
    """Emit the six-stage evidence graph for a completed set of cases.

    Negative cases record *why* a later artifact does not exist. An absence with
    no recorded reason is indistinguishable from an omission, so there are none.
    """
    for name in EVIDENCE_DIRECTORIES:
        (out_dir / name).mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {"cases": {}, "directories": list(EVIDENCE_DIRECTORIES)}
    for case_id, outcome in sorted(outcomes.items()):
        policy = outcome.compiled
        written = {
            "00-source": _write(
                out_dir / "00-source" / f"{case_id}-source-document.json", policy.source_document
            ),
            "01-oic": _write(
                out_dir / "01-oic" / f"{case_id}-compilation.json",
                {
                    "institutional_ir": policy.institutional_ir,
                    "authority_record": policy.authority_record,
                    "control_envelope": policy.control_envelope,
                    "runtime_binding": policy.runtime_binding,
                    "currentness_use_gate_decision": outcome.gate_decision.as_record(),
                    "authority_decision": outcome.authority_decision.as_record(),
                },
            ),
            "02-ztl": _write(out_dir / "02-ztl" / f"{case_id}-warrant.json", outcome.warrant),
            "03-runtime": _write(
                out_dir / "03-runtime" / f"{case_id}-oam-decision.json", outcome.oam_decision
            ),
        }
        if outcome.reliance is not None:
            written["04-reliance"] = _write(
                out_dir / "04-reliance" / f"{case_id}-reliance.json",
                {"validation": outcome.consumer_validation, "reliance_record": outcome.reliance},
            )
        else:
            written["04-reliance"] = _write(
                out_dir / "04-reliance" / f"{case_id}-absent.json",
                {"absent_artifacts": outcome.absent_artifacts},
            )
        manifest["cases"][case_id] = {
            "execution_context": outcome.execution_context.value,
            "semantic_projection": decision_semantic_projection(outcome),
            "written": written,
            "absent_artifacts": outcome.absent_artifacts,
        }
    manifest["claim_ceiling"] = "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"
    manifest["measured_end_to_end_claim"] = False
    _write(out_dir / "05-evidence" / "MANIFEST.json", manifest)
    return manifest


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
