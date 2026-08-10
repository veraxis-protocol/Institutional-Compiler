"""Frozen pre-execution corpus for ``CDC-TEST-MISSION-001``.

Everything here is synthetic. No real tender, no real controller, no real
Moroccan procurement record and no CDC authority is represented. The corpus
exists to make source, admission, control and evidence relationships inspectable
*before* any execution.

Two rules govern this module:

* No expected observed result is written into a fixture. A case may name the
  oracle case it will later be adjudicated against, but it never carries a
  favourable outcome into runtime input. The oracle stays external.
* Nothing executes at import. Every object is produced by an explicit call, so
  importing this module during collection creates no mission, candidate or
  disposition.
"""

from __future__ import annotations

from typing import Any, Final

from oic.cdc_slice import ASSURANCE_MODE, MISSION_ID, TEST_SCOPE, digest

# --------------------------------------------------------------------------
# Controls. Admitted-control stand-ins for the three procurement phases named
# by the challenge: competitive tendering, bid evaluation, contract award.
# --------------------------------------------------------------------------
CONTROL_TENDER: Final = "C-TENDER-01"
CONTROL_EVAL: Final = "C-EVAL-01"
CONTROL_AWARD: Final = "C-AWARD-01"
CONTROLS: Final = (CONTROL_TENDER, CONTROL_EVAL, CONTROL_AWARD)

# --------------------------------------------------------------------------
# Three-procedure synthetic population.
# --------------------------------------------------------------------------
P_CLEAN: Final = "P-001"
P_DETERMINISTIC_BREACH: Final = "P-002"
P_MISSING_OR_CONFLICTING: Final = "P-003"
PROCEDURES: Final = (P_CLEAN, P_DETERMINISTIC_BREACH, P_MISSING_OR_CONFLICTING)

PROCEDURE_SHAPE: Final[dict[str, str]] = {
    P_CLEAN: "CLEAN",
    P_DETERMINISTIC_BREACH: "DETERMINISTIC_BREACH",
    P_MISSING_OR_CONFLICTING: "MISSING_OR_CONFLICTING_EVIDENCE",
}

TEST_REVIEWER_ID: Final = "TEST-REVIEWER-001"
TEST_REVIEWER_ROLE: Final = "CDC_TEST_CONTROLLER"
OUT_OF_SCOPE_REVIEWER_ID: Final = "TEST-REVIEWER-OUT-OF-SCOPE-001"
OUT_OF_SCOPE_SCOPE: Final = "CDC-TEST-MISSION-999/TEST-REVIEWER"

SEMANTIC_EPOCH: Final = "OIC-SEMANTIC-EPOCH-TEST-0001"

# --------------------------------------------------------------------------
# Execution corpus: S-01..S-08.
# `expected_oracle_case_ref` names the external oracle case. It is a reference
# only; no expected result is carried here.
# --------------------------------------------------------------------------
S_CASES: Final[tuple[str, ...]] = (
    "S-01",
    "S-02",
    "S-03",
    "S-04",
    "S-05",
    "S-06",
    "S-07",
    "S-08",
)

S_CASE_SPEC: Final[dict[str, dict[str, Any]]] = {
    "S-01": {
        "precondition_description": "valid bounded TEST disposition on a clean procedure",
        "procedure_id": P_CLEAN,
        "control_ref": CONTROL_TENDER,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "NOMINAL",
    },
    "S-02": {
        "precondition_description": "required evidence object absent from the run snapshot",
        "procedure_id": P_MISSING_OR_CONFLICTING,
        "control_ref": CONTROL_TENDER,
        "requested_disposition": "REQUEST_EVIDENCE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "EVIDENCE_ABSENT",
    },
    "S-03": {
        "precondition_description": "admission record absent, so admitted meaning is unsupported",
        "procedure_id": P_CLEAN,
        "control_ref": CONTROL_EVAL,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "ADMISSION_ABSENT",
    },
    "S-04": {
        "precondition_description": "reviewer asserts a scope outside the mission-scoped standing",
        "procedure_id": P_CLEAN,
        "control_ref": CONTROL_AWARD,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": OUT_OF_SCOPE_SCOPE,
        "condition": "REVIEWER_OUT_OF_SCOPE",
    },
    "S-05": {
        "precondition_description": "bound evidence altered after the proposal captured its digest",
        "procedure_id": P_DETERMINISTIC_BREACH,
        "control_ref": CONTROL_EVAL,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "EVIDENCE_MUTATED_AFTER_BINDING",
    },
    "S-06": {
        "precondition_description": "contradictory observations leaving the condition CANNOT",
        "procedure_id": P_MISSING_OR_CONFLICTING,
        "control_ref": CONTROL_EVAL,
        "requested_disposition": "ESCALATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "CONTRADICTORY_CANNOT",
    },
    "S-07": {
        "precondition_description": "candidate superseded by a correction issued beforehand",
        "procedure_id": P_DETERMINISTIC_BREACH,
        "control_ref": CONTROL_AWARD,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "PREDECESSOR_SUPERSEDED",
    },
    "S-08": {
        "precondition_description": "warrant class absent; no substitute artifact offered",
        "procedure_id": P_CLEAN,
        "control_ref": CONTROL_TENDER,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "reviewer_scope": TEST_SCOPE,
        "condition": "WARRANT_CLASS_ABSENT",
    },
}


def _source_anchor(procedure_id: str, control_ref: str, node: str) -> dict[str, Any]:
    """A synthetic source anchor. Not a real document locator."""
    return {
        "anchor_id": f"ANCHOR-{procedure_id}-{control_ref}-{node}",
        "source_id": f"SRC-{procedure_id}",
        "node_id": node,
        "content_hash": digest({"procedure": procedure_id, "control": control_ref, "node": node}),
    }


def build_control(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """An admitted OIC control envelope stand-in."""
    phase = {
        CONTROL_TENDER: "competitive_tendering",
        CONTROL_EVAL: "bid_evaluation",
        CONTROL_AWARD: "contract_award",
    }[control_ref]
    return {
        "control_id": control_ref,
        "procedure_id": procedure_id,
        "phase": phase,
        "semantic_epoch": SEMANTIC_EPOCH,
        "decision_mode": "DETERMINISTIC",
        "on_unknown": "ESCALATE",
        "conditions": [f"{phase}_condition_satisfied"],
        "source_anchors": [_source_anchor(procedure_id, control_ref, "art-1")],
    }


def build_admission(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """An admission record binding a control to admitted meaning."""
    return {
        "admission_id": f"ADM-{procedure_id}-{control_ref}",
        "subject_id": control_ref,
        "disposition": "ADMITTED",
        "reviewer": TEST_REVIEWER_ID,
        "reviewer_role": TEST_REVIEWER_ROLE,
        "authority_basis": "SYNTHETIC_TEST_CHARTER",
        "scope": TEST_SCOPE,
        "source_hashes": [digest({"procedure": procedure_id, "control": control_ref})],
    }


def build_evidence(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """An evidence bundle. This function records observations; it evaluates none."""
    shape = PROCEDURE_SHAPE[procedure_id]
    observations: list[dict[str, Any]] = []
    if shape == "MISSING_OR_CONFLICTING_EVIDENCE":
        observations.append({"fact": "publication_window_days", "value": None})
        observations.append({"fact": "publication_window_days", "value": 7})
    elif shape == "DETERMINISTIC_BREACH":
        observations.append({"fact": "publication_window_days", "value": 9})
    else:
        observations.append({"fact": "publication_window_days", "value": 30})
    return {
        "evidence_bundle_id": f"EVB-{procedure_id}-{control_ref}",
        "procedure_id": procedure_id,
        "control_id": control_ref,
        "observations": observations,
        "source_anchors": [_source_anchor(procedure_id, control_ref, "dossier-1")],
    }


def build_evaluation(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """A deterministic evaluation record produced upstream of the gate."""
    shape = PROCEDURE_SHAPE[procedure_id]
    verdict = {
        "CLEAN": "SATISFIED",
        "DETERMINISTIC_BREACH": "BREACH",
        "MISSING_OR_CONFLICTING_EVIDENCE": "UNRESOLVED",
    }[shape]
    return {
        "evaluation_id": f"EVAL-{procedure_id}-{control_ref}",
        "control_id": control_ref,
        "verdict": verdict,
        "reason_codes": [f"{verdict}_SYNTHETIC"],
    }


def build_warrant(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """A ZTL warrant artifact stand-in. Not a ZTL kernel output."""
    return {
        "warrant_artifact_id": f"ZTL-{procedure_id}-{control_ref}",
        "claim_id": f"CLAIM-{procedure_id}-{control_ref}",
        "warranty_grade": "SYNTHETIC",
        "limitations": ["SYNTHETIC_EVALUATION_ONLY"],
    }


def build_candidate(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """An evidence-bound candidate value. Never an institutional finding."""
    shape = PROCEDURE_SHAPE[procedure_id]
    epistemic = "UNSUPPORTED" if shape == "MISSING_OR_CONFLICTING_EVIDENCE" else "SUPPORTED"
    return {
        "candidate_id": f"CAND-{procedure_id}-{control_ref}",
        "unit_type": "CONTROL_RESULT_CANDIDATE",
        "epistemic_state": epistemic,
        "interpretation_state": "SYNTHETIC",
        "source_anchors": [_source_anchor(procedure_id, control_ref, "art-1")],
    }


def build_registry(procedure_id: str, control_ref: str) -> dict[str, Any]:
    """The immutable run snapshot: the exact objects the gate may address."""
    ebawu = f"EBAWU-{procedure_id}-{control_ref}"
    return {
        "candidates": {
            f"CAND-{procedure_id}-{control_ref}": build_candidate(procedure_id, control_ref)
        },
        "ebawus": {ebawu: {"ebawu_id": ebawu}},
        "controls": {control_ref: build_control(procedure_id, control_ref)},
        "admissions": {
            f"ADM-{procedure_id}-{control_ref}": build_admission(procedure_id, control_ref)
        },
        "evidence": {
            f"EVB-{procedure_id}-{control_ref}": build_evidence(procedure_id, control_ref)
        },
        "evaluations": {
            f"EVAL-{procedure_id}-{control_ref}": build_evaluation(procedure_id, control_ref)
        },
        "reviewers": {
            TEST_REVIEWER_ID: {"reviewer_id": TEST_REVIEWER_ID, "role": TEST_REVIEWER_ROLE}
        },
        "warrants": {f"ZTL-{procedure_id}-{control_ref}": build_warrant(procedure_id, control_ref)},
        "fallback_warrants": {},
        "states": {ebawu: "CANDIDATE_FORMED"},
        "stale_candidate_ids": (),
    }


_NEW_STATE: Final[dict[str, str]] = {
    "ACCEPT_CANDIDATE": "ACCEPTED_CANDIDATE",
    "QUALIFY": "QUALIFIED",
    "DISMISS": "DISMISSED",
    "REQUEST_EVIDENCE": "EVIDENCE_REQUESTED",
    "ESCALATE": "ESCALATED",
    "DEFER": "DEFERRED",
}


def build_proposal(case_id: str, registry: dict[str, Any]) -> dict[str, Any]:
    """A well-formed ``APPLY_TEST_DISPOSITION`` proposal for one S-case.

    Digests are derived from the registry objects, never hand-written, so a
    conforming proposal binds exactly and an adversarial variant differs by one
    named field.
    """
    spec = S_CASE_SPEC[case_id]
    procedure_id = str(spec["procedure_id"])
    control_ref = str(spec["control_ref"])
    candidate_id = f"CAND-{procedure_id}-{control_ref}"
    evidence_ref = f"EVB-{procedure_id}-{control_ref}"
    warrant_ref = f"ZTL-{procedure_id}-{control_ref}"
    disposition = str(spec["requested_disposition"])
    return {
        "proposal_id": f"PROP-{case_id}",
        "case_id": case_id,
        "mission_id": MISSION_ID,
        "ebawu_id": f"EBAWU-{procedure_id}-{control_ref}",
        "candidate_id": candidate_id,
        "candidate_digest": digest(registry["candidates"][candidate_id]),
        "reviewer_id": TEST_REVIEWER_ID,
        "reviewer_role_assertion": TEST_REVIEWER_ROLE,
        "authority_scope_ref": str(spec["reviewer_scope"]),
        "assurance_mode": ASSURANCE_MODE,
        "requested_disposition": disposition,
        "OIC_control_id": control_ref,
        "OIC_semantic_epoch": SEMANTIC_EPOCH,
        "OIC_control_digest": digest(registry["controls"][control_ref]),
        "source_anchor_refs": [f"ANCHOR-{procedure_id}-{control_ref}-art-1"],
        "admission_record_ref": f"ADM-{procedure_id}-{control_ref}",
        "evidence_bundle_ref": evidence_ref,
        "evidence_bundle_digest": digest(registry["evidence"][evidence_ref]),
        "deterministic_execution_result_ref": f"EVAL-{procedure_id}-{control_ref}",
        "ZTL_warrant_ref": warrant_ref,
        "ZTL_warrant_digest": digest(registry["warrants"][warrant_ref]),
        "prior_institutional_state": "CANDIDATE_FORMED",
        "requested_new_institutional_state": _NEW_STATE[disposition],
        "proposal_time": "2026-08-10T00:00:00Z",
        "schema_version": "VEIP-CDC-SLICE-PROPOSAL-v0.1",
    }


def fixture_record(case_id: str) -> dict[str, Any]:
    """The inspectable pre-execution fixture record for one S-case.

    Carries identities and relationships only. It deliberately contains no
    expected observed result; ``expected_oracle_case_ref`` is a pointer to the
    external oracle, not a copy of its content.
    """
    spec = S_CASE_SPEC[case_id]
    procedure_id = str(spec["procedure_id"])
    control_ref = str(spec["control_ref"])
    registry = build_registry(procedure_id, control_ref)
    proposal = build_proposal(case_id, registry)
    return {
        "case_id": case_id,
        "fixture_id": f"FIX-{case_id}",
        "mission_id": MISSION_ID,
        "precondition_description": spec["precondition_description"],
        "precondition_condition": spec["condition"],
        "procedure_id": procedure_id,
        "procedure_shape": PROCEDURE_SHAPE[procedure_id],
        "candidate_ref": proposal["candidate_id"],
        "control_ref": control_ref,
        "admission_ref": proposal["admission_record_ref"],
        "evidence_refs": [proposal["evidence_bundle_ref"]],
        "warrant_ref": proposal["ZTL_warrant_ref"],
        "reviewer_scope": proposal["authority_scope_ref"],
        "requested_disposition": proposal["requested_disposition"],
        "prior_state": proposal["prior_institutional_state"],
        "expected_oracle_case_ref": f"ORACLE-CASE-{case_id}",
        "expected_observed_result": "NOT_CARRIED_IN_FIXTURE",
        "input_digests": {
            "candidate_digest": proposal["candidate_digest"],
            "OIC_control_digest": proposal["OIC_control_digest"],
            "evidence_bundle_digest": proposal["evidence_bundle_digest"],
            "ZTL_warrant_digest": proposal["ZTL_warrant_digest"],
        },
    }


def corpus() -> list[dict[str, Any]]:
    """The complete frozen S-01..S-08 fixture corpus."""
    return [fixture_record(case_id) for case_id in S_CASES]


def event_metadata(case_id: str, run_id: str) -> dict[str, Any]:
    """Deterministic event metadata for one synthetic case."""
    return {
        "event_id": f"EVT-{case_id}",
        "aggregate_version": 1,
        "occurred_at": "2026-08-10T00:00:00Z",
        "recorded_at": "2026-08-10T00:00:00Z",
        "producer": "cdc-slice-integration-harness",
        "producer_version": "0.1.0",
        "run_id": run_id,
        "trace_id": f"TRACE-{case_id}",
    }
