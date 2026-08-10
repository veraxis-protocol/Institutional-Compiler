"""Structural tests for the CDC vertical-slice preparation package.

Everything here is non-result-bearing. No test in this module calls
``evaluate_test_transition``, creates a mission, candidate or disposition, emits
a transition, builds an evidence pack, executes an adversarial probe, or
increments a denominator. These tests check that the *preparation* is coherent
and that the interlocks refuse.

The interlock test proves refusal by observing it, never by supplying a stub
clearance reference. Inventing one would defeat the interlock it claims to test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_slice_adversarial import (
    ADVERSARIAL_DENOMINATOR,
    ADVERSARIAL_PROBES_DEFINED,
    ADVERSARIAL_PROBES_EXECUTED,
    PROBE_IDS,
    PROBES,
    probe_definitions,
)
from cdc_slice_corpus import (
    CONTROLS,
    PROCEDURES,
    S_CASE_SPEC,
    S_CASES,
    build_proposal,
    build_registry,
    corpus,
    fixture_record,
)
from cdc_slice_interlock import (
    ExecutionNotAuthorizedError,
    observe_clearance,
    require_execution_clearance,
)
from cdc_slice_observation import (
    ADJUDICATION_FIELDS_PROHIBITED,
    assert_no_adjudication,
    unobserved,
)

from oic.cdc_slice import PERMITTED_DISPOSITIONS, digest

# --------------------------------------------------------------------------
# Execution corpus
# --------------------------------------------------------------------------


def test_eight_s_cases_are_defined() -> None:
    """The execution corpus is exactly S-01..S-08."""
    assert len(S_CASES) == 8
    assert set(S_CASES) == set(S_CASE_SPEC)


def test_every_fixture_carries_the_required_identity_fields() -> None:
    """Each fixture identifies its refs, scope, disposition and prior state."""
    required = {
        "case_id",
        "fixture_id",
        "mission_id",
        "precondition_description",
        "candidate_ref",
        "control_ref",
        "admission_ref",
        "evidence_refs",
        "warrant_ref",
        "reviewer_scope",
        "requested_disposition",
        "prior_state",
        "expected_oracle_case_ref",
    }
    for record in corpus():
        assert required <= set(record), record["case_id"]


def test_no_fixture_carries_an_expected_observed_result() -> None:
    """The oracle stays external: no favourable result is copied into runtime input.

    ``requested_disposition`` is deliberately excluded. ``ESCALATE`` is both a
    permitted OAM disposition a reviewer may request *and* a gate decision the
    slice may return. The token overlaps across the two vocabularies, so a naive
    substring rule would flag a legitimate input as a leaked expected result.
    What must not appear is a *gate decision* in a result-shaped field.
    """
    gate_decisions = {"ALLOW", "DENY", "ESCALATE"}
    input_fields = {"requested_disposition"}
    for record in corpus():
        assert record["expected_observed_result"] == "NOT_CARRIED_IN_FIXTURE"
        for key, value in record.items():
            if key in input_fields or not isinstance(value, str):
                continue
            assert value not in gate_decisions, f"{record['case_id']}:{key}"
            if any(token in key for token in ("expected", "observed", "result", "decision")):
                assert value in {"NOT_CARRIED_IN_FIXTURE"} or key.endswith("_ref"), (
                    f"{record['case_id']}:{key} carries a result-shaped value"
                )


def test_fixture_digests_are_reproducible() -> None:
    """Static fixture hashes recompute exactly."""
    for case_id in S_CASES:
        assert fixture_record(case_id)["input_digests"] == fixture_record(case_id)["input_digests"]


def test_proposal_digests_derive_from_registry_objects() -> None:
    """Digests are derived, never hand-written."""
    for case_id in S_CASES:
        spec = S_CASE_SPEC[case_id]
        registry = build_registry(str(spec["procedure_id"]), str(spec["control_ref"]))
        proposal = build_proposal(case_id, registry)
        assert proposal["candidate_digest"] == digest(
            registry["candidates"][proposal["candidate_id"]]
        )
        assert proposal["evidence_bundle_digest"] == digest(
            registry["evidence"][proposal["evidence_bundle_ref"]]
        )
        assert proposal["requested_disposition"] in PERMITTED_DISPOSITIONS


# --------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------


def test_population_is_three_procedures_over_three_controls() -> None:
    """P-001..P-003 bound to the three procurement-phase controls."""
    assert PROCEDURES == ("P-001", "P-002", "P-003")
    assert CONTROLS == ("C-TENDER-01", "C-EVAL-01", "C-AWARD-01")
    used_controls = {record["control_ref"] for record in corpus()}
    assert used_controls == set(CONTROLS)


# --------------------------------------------------------------------------
# Adversarial probe definitions
# --------------------------------------------------------------------------


def test_seven_probes_defined_and_none_executed() -> None:
    """Definition count is not a measurement denominator."""
    assert ADVERSARIAL_PROBES_DEFINED == 7
    assert ADVERSARIAL_PROBES_EXECUTED == 0
    assert ADVERSARIAL_DENOMINATOR == 0
    assert PROBE_IDS == ("A-01", "A-02", "A-03", "A-04", "A-05", "A-06", "A-07")


def test_each_probe_maps_to_an_s_case_and_records_required_fields() -> None:
    """Every probe binds a case, a boundary, prohibitions and preservations."""
    mapped = {probe.s_case for probe in PROBES}
    assert mapped <= set(S_CASES)
    assert mapped == {"S-02", "S-03", "S-04", "S-05", "S-06", "S-07", "S-08"}
    for definition in probe_definitions():
        assert definition["mutation_or_condition"]
        assert definition["target_boundary"]
        assert definition["observable_artifacts"]
        assert definition["prohibited_side_effects"]
        assert definition["required_preservation"]
        assert definition["executed"] is False
        assert definition["observed_outcome"] == "NOT_YET_OBSERVED"


def test_no_probe_permits_an_executed_allow() -> None:
    """A probe holds by refusing; ALLOW is never an acceptable probe outcome."""
    for probe in PROBES:
        assert "ALLOW" not in probe.permitted_decisions, probe.probe_id


# --------------------------------------------------------------------------
# Observation record
# --------------------------------------------------------------------------


def test_observation_keeps_three_axes_separate_and_carries_no_adjudication() -> None:
    """Epistemic, operational and institutional axes stay distinct."""
    record = unobserved("S-01")
    for axis in (
        "epistemic_state_observed",
        "operational_state_observed",
        "institutional_state_observed",
    ):
        assert record[axis] == "NOT_YET_OBSERVED"
    assert "adjudication" not in record
    assert not (ADJUDICATION_FIELDS_PROHIBITED & set(record))
    assert_no_adjudication(record)


def test_assert_no_adjudication_rejects_a_verdict_bearing_observation() -> None:
    """An observation that acquires a verdict is rejected, not tolerated."""
    record = unobserved("S-01")
    record["adjudication"] = "MATCH"
    with pytest.raises(ValueError, match="adjudication"):
        assert_no_adjudication(record)


# --------------------------------------------------------------------------
# Execution interlock
# --------------------------------------------------------------------------


def test_interlock_reports_blocked_without_clearance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no owner clearance reference the entry point is BLOCKED."""
    monkeypatch.delenv("CDC_SLICE_EXECUTION_CLEARANCE_REF", raising=False)
    monkeypatch.delenv("CDC_SLICE_RESULT_BEARING", raising=False)
    state = observe_clearance()
    assert state.execution_permitted is False
    record = state.as_record()
    assert record["execution_clearance_ref"] == "ABSENT"
    assert record["result_bearing_entrypoint"] == "BLOCKED"


def test_interlock_refuses_to_run_without_clearance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The interlock raises rather than defaulting to permit.

    No stub clearance reference is supplied here. Proving the refusal is the
    test; manufacturing a clearance would defeat it.
    """
    monkeypatch.delenv("CDC_SLICE_EXECUTION_CLEARANCE_REF", raising=False)
    monkeypatch.delenv("CDC_SLICE_RESULT_BEARING", raising=False)
    with pytest.raises(ExecutionNotAuthorizedError, match="EXECUTION_CLEARANCE_REF = ABSENT"):
        require_execution_clearance()
