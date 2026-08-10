from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from oic.cdc_slice import (
    ASSURANCE_MODE,
    MISSION_ID,
    TEST_SCOPE,
    digest,
    emit_transition_event,
    evaluate_test_transition,
    make_successor,
)


def _case() -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = {"candidate_id": "CAND-001", "claim": "synthetic tender condition satisfied"}
    control = {"control_id": "CTRL-TENDER-001", "version": "1.0.0"}
    evidence = {"evidence_id": "EVID-001", "observed": True}
    warrant = {"warrant_artifact_id": "WAR-001", "disposition": "EARNED"}
    proposal = {
        "proposal_id": "PROP-001",
        "mission_id": MISSION_ID,
        "ebawu_id": "EBAWU-001",
        "candidate_id": "CAND-001",
        "candidate_digest": digest(candidate),
        "reviewer_id": "REVIEWER-TEST-001",
        "reviewer_role_assertion": "TEST_REVIEWER",
        "authority_scope_ref": TEST_SCOPE,
        "assurance_mode": ASSURANCE_MODE,
        "requested_disposition": "ACCEPT_CANDIDATE",
        "OIC_control_id": "CTRL-TENDER-001",
        "OIC_semantic_epoch": "EPOCH-001",
        "OIC_control_digest": digest(control),
        "source_anchor_refs": ["ANCHOR-001"],
        "admission_record_ref": "ADM-001",
        "evidence_bundle_ref": "EVID-001",
        "evidence_bundle_digest": digest(evidence),
        "deterministic_execution_result_ref": "EVAL-001",
        "ZTL_warrant_ref": "WAR-001",
        "ZTL_warrant_digest": digest(warrant),
        "prior_institutional_state": "CANDIDATE_REVIEW_PENDING",
        "requested_new_institutional_state": "ACCEPTED_CANDIDATE",
        "proposal_time": "2026-08-10T00:00:00Z",
        "schema_version": "VEIP-CDC-SLICE-PROPOSAL-v0.1",
    }
    registry = {
        "candidates": {"CAND-001": candidate},
        "ebawus": {"EBAWU-001": {"ebawu_id": "EBAWU-001"}},
        "controls": {"CTRL-TENDER-001": control},
        "admissions": {"ADM-001": {"admission_id": "ADM-001"}},
        "evidence": {"EVID-001": evidence},
        "evaluations": {"EVAL-001": {"evaluation_id": "EVAL-001"}},
        "warrants": {"WAR-001": warrant},
        "reviewers": {"REVIEWER-TEST-001": {"role": "TEST_REVIEWER"}},
        "states": {"EBAWU-001": "CANDIDATE_REVIEW_PENDING"},
        "stale_candidate_ids": [],
    }
    return proposal, registry


def test_contract_complete_proposal_allows_test_transition() -> None:
    proposal, registry = _case()
    assert evaluate_test_transition(proposal, registry).decision == "ALLOW"


def test_missing_evidence_is_unresolved_not_pass_or_breach() -> None:
    proposal, registry = _case()
    registry["evidence"] = {}
    decision = evaluate_test_transition(proposal, registry)
    assert decision.decision == "ESCALATE"
    assert "UNRESOLVED" in decision.reason_code


def test_unsupported_proposition_cannot_enter_transition() -> None:
    proposal, registry = _case()
    registry["admissions"] = {}
    assert evaluate_test_transition(proposal, registry).decision == "ESCALATE"


def test_fallback_warrant_is_separate_and_never_populates_ztl_digest() -> None:
    proposal, registry = _case()
    fallback = {"fallback_warrant_id": "FB-001", "state": "UNRESOLVED"}
    proposal["ZTL_warrant_ref"] = None
    proposal["ZTL_warrant_digest"] = None
    proposal["fallback_warrant_ref"] = "FB-001"
    proposal["fallback_warrant_digest"] = digest(fallback)
    registry["fallback_warrants"] = {"FB-001": fallback}
    assert evaluate_test_transition(proposal, registry).decision == "ALLOW"


def test_unresolved_required_warrant_escalates_without_implicit_allow() -> None:
    proposal, registry = _case()
    proposal["ZTL_warrant_ref"] = None
    proposal["ZTL_warrant_digest"] = None
    decision = evaluate_test_transition(proposal, registry)
    assert decision.decision == "ESCALATE"
    assert decision.reason_code == "REQUIRED_WARRANT_CLASS_UNRESOLVED"


def test_cannot_survives_operational_deny_as_unresolved_epistemic_state() -> None:
    proposal, registry = _case()
    proposal["cannot_condition"] = True
    proposal["authority_scope_ref"] = "wrong"
    decision = evaluate_test_transition(proposal, registry)
    assert decision.decision == "DENY"
    assert decision.epistemic_state == "UNRESOLVED_CANNOT"
    assert decision.reason_code == "UNAUTHORIZED_REVIEWER_SCOPE"


def test_unauthorized_test_actor_is_denied() -> None:
    proposal, registry = _case()
    proposal["authority_scope_ref"] = "CDC-TEST-MISSION-001/UNAUTHORIZED"
    assert evaluate_test_transition(proposal, registry).decision == "DENY"


def test_bound_evidence_mutation_is_detected() -> None:
    proposal, registry = _case()
    registry["evidence"]["EVID-001"]["observed"] = False
    assert (
        evaluate_test_transition(proposal, registry).reason_code
        == "EVIDENCE_BUNDLE_DIGEST_MISMATCH"
    )


def test_non_allow_never_emits_completion() -> None:
    proposal, registry = _case()
    proposal["authority_scope_ref"] = "wrong"
    with pytest.raises(ValueError, match="only after ALLOW"):
        emit_transition_event(
            proposal, evaluate_test_transition(proposal, registry), event_metadata={}
        )


def test_correction_preserves_predecessor_and_lineage() -> None:
    predecessor = {"ebawu_id": "EBAWU-001", "state": "ACCEPTED_CANDIDATE", "bytes": "original"}
    frozen = deepcopy(predecessor)
    successor = make_successor(
        predecessor,
        {
            "new_ebawu_or_successor_id": "EBAWU-002",
            "new_candidate_digest": "sha256:" + "0" * 64,
            "correction_reason": "synthetic evidence corrected",
            "changed_fact_or_control_refs": ["EVID-001"],
            "new_state": "CANDIDATE_REVIEW_PENDING",
            "correction_event_id": "CORR-001",
            "affected_output_refs": ["STATEMENT-001"],
        },
    )
    assert predecessor == frozen
    assert successor["supersedes"] == "EBAWU-001"
    assert successor["production_reliance_semantics"] == "OUT_OF_SCOPE"
