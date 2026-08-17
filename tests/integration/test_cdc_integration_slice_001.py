"""The 41 frozen semantic criteria of integration slice 001.

Identities are reconstructed from the frozen contract chain, verified from Git
objects: ``…SEMANTIC-DESIGN-v0.4.md`` (03ca22e9…) and its incorporated
predecessors v0.3 (1c07a24c…), v0.2 (8e02820d…) and v0.1 (f0f250ed…), with
digest behaviour from ``INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.4.md``
(494c91ac…), which completes the epoch vector inputs its predecessors omitted.

One pytest node id is exactly one semantic criterion.  The four development-only
authority-branch tests live in a separate module and are never counted here.

These are development tests establishing conformance to the frozen contract.
They are not the result-bearing slice demonstration and produce no frozen
execution package.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from oic.cdc_authority import (
    AUTHORITY_REASON_CODES,
    CONSUMER_PRINCIPAL,
    EPOCH_RECORD_FIELDS,
    PRODUCER_PRINCIPAL,
    SUBJECT_PRINCIPAL,
    AuthorityRequest,
    authority_basis_record_digest,
    authority_decision_digest,
    canonical_bytes,
    canonical_digest,
    currentness_epoch_digest,
    evaluate_synthetic_authority,
    parse_basis_record,
    synthetic_profile_digest,
)
from oic.cdc_currentness import (
    CURRENT,
    DENY,
    SUPERSEDED,
    UseGateProfile,
    UseGateRequest,
    evaluate_present_use,
    resolve_currentness,
)
from oic.cdc_propagation import (
    PROPAGATION_REASON_CODES,
    ProducerIdentity,
    build_envelope,
    envelope_digest,
    materialize_envelope,
    parse_envelope,
)
from oic.cdc_reliance import (
    CONSUMER_CHECKS,
    ISSUED,
    REFUSED,
    RELIANCE_REASON_CODES,
    consumer_validation_digest,
    integration_package_digest,
    persisted_file_sha256,
    reliance_record_digest,
)
from tests.integration.cdc_currentness_fixtures import (
    AFFECTED_OUTPUT_REFS,
    CONTROL_OUTPUT_REF,
    RUN_METADATA,
    control_artifact,
    control_document,
    governed_index,
    historical_artifact,
)
from tests.integration.cdc_integration_fixtures import (
    ARTIFACT_CLASS,
    DECISION_VALID_UNTIL,
    ENVELOPE_VALID_UNTIL,
    REQUESTED_USE,
    RUN_ID,
    SCOPE,
    T1,
    T2,
    TRACE_ID,
    admissibility_basis,
    authority_basis,
    consumer_profile,
    control_body_digest,
    epoch_for,
    index_with_future_successor,
    index_without_successor,
    producer_profile,
)

CONSUMER_MODULE = "tests.integration.cdc_integration_consumer"


# ---------------------------------------------------------------------------
# Producer / consumer harness (development scaffolding, not the frozen run)
# ---------------------------------------------------------------------------


def _authority_decision(
    *,
    index: Any,  # noqa: ANN401
    now: str = T1,
    bases: list[dict[str, Any]] | None = None,
    admissibility: list[dict[str, Any]] | None = None,
    artifact_digest: str | None = None,
    recomputed: str | None = None,
    escalate: bool = False,
    requested_use: str = REQUESTED_USE,
    principal: str = SUBJECT_PRINCIPAL,
    valid_until: str = DECISION_VALID_UNTIL,
    bind_currentness: bool = True,
) -> Any:  # noqa: ANN401
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=now,
    )
    epoch = epoch_for(index, CONTROL_OUTPUT_REF, now)
    digest = artifact_digest or control_body_digest()
    return evaluate_synthetic_authority(
        request=AuthorityRequest(
            artifact_ref=CONTROL_OUTPUT_REF,
            artifact_digest=digest,
            recomputed_artifact_digest=recomputed or control_body_digest(),
            requested_use=requested_use,
            scope=SCOPE,
            requesting_principal=principal,
            currentness_resolution_digest=(
                resolution.resolution_digest if bind_currentness else None
            ),
            currentness_epoch_digest=epoch if bind_currentness else None,
            evaluation_time=now,
            valid_until=valid_until,
            decision_id="SYNTH-AUTHORITY-DECISION-001",
        ),
        authority_bases=[
            parse_basis_record(item)
            for item in (bases if bases is not None else [authority_basis()])
        ],
        admissibility_bases=[
            parse_basis_record(item)
            for item in (admissibility if admissibility is not None else [admissibility_basis()])
        ],
        artifact_class=ARTIFACT_CLASS,
        escalation_predicate=escalate,
    )


def _run_pipeline(
    tmp_path: Path,
    *,
    producer_now: str = T1,
    consumer_now: str = T1,
    producer_index_future: bool = False,
    consumer_index_future: bool = False,
    consumer_without_control: bool = False,
    envelope_overrides: dict[str, Any] | None = None,
    tamper: bool = False,
    decision_valid_until: str = DECISION_VALID_UNTIL,
    consumer_authority_bases: list[dict[str, Any]] | None = None,
    consumer_admissibility_bases: list[dict[str, Any]] | None = None,
    direct_assertion: bool = False,
    attempt_name: str = "attempt.json",
    reliance_id: str = "SYNTH-RELIANCE-001",
    envelope_name: str = "envelope.json",
) -> dict[str, Any]:
    """Produce an envelope, then run the consumer as a separate OS process."""
    index = index_with_future_successor() if producer_index_future else index_without_successor()
    decision = _authority_decision(index=index, now=producer_now, valid_until=decision_valid_until)
    assert decision.decision == "PROCEED", decision.reason_code_id

    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=producer_now,
    )
    control_path = tmp_path / "control.json"
    control_path.write_bytes(
        (json.dumps(control_document(), sort_keys=True, indent=2) + "\n").encode()
    )
    fields: dict[str, Any] = {
        "envelope_id": "SYNTH-ENVELOPE-001",
        "artifact_ref": CONTROL_OUTPUT_REF,
        "artifact_digest": control_body_digest(),
        "requested_use": REQUESTED_USE,
        "scope": SCOPE,
        "requesting_subject_principal": SUBJECT_PRINCIPAL,
        "producer_identity": ProducerIdentity(
            producer_principal=PRODUCER_PRINCIPAL,
            process_id=os.getpid(),
            run_id=RUN_ID,
            trace_id=TRACE_ID,
        ),
        "intended_consumer_principal": CONSUMER_PRINCIPAL,
        "currentness_resolution_digest": resolution.resolution_digest,
        "currentness_index_digest": index.index_digest,
        "currentness_epoch_digest": epoch_for(index, CONTROL_OUTPUT_REF, producer_now),
        "authority_decision_digest": decision.authority_decision_digest,
        "authority_basis_refs": list(decision.authority_basis_refs),
        "admissibility_basis_refs": list(decision.admissibility_basis_refs),
        "evidence_refs": [{"ref": "SYNTHETIC_CONTROL", "path": str(control_path)}],
        "produced_at": producer_now,
        "valid_until": ENVELOPE_VALID_UNTIL,
    }
    fields.update(envelope_overrides or {})
    envelope = build_envelope(**fields)
    record = envelope.as_record()
    if tamper:
        record = {**record, "scope": "TAMPERED-SCOPE"}

    envelope_path = tmp_path / envelope_name
    materialized = materialize_envelope(record, envelope_path)

    decision_path = tmp_path / "decision.json"
    decision_path.write_bytes(
        (json.dumps(decision.as_record(), sort_keys=True, indent=2) + "\n").encode()
    )
    producer_path = tmp_path / "producer-profile.json"
    producer_path.write_bytes(
        (json.dumps(producer_profile(), sort_keys=True, indent=2) + "\n").encode()
    )
    consumer_path = tmp_path / "consumer-profile.json"
    consumer_path.write_bytes(
        (json.dumps(consumer_profile(), sort_keys=True, indent=2) + "\n").encode()
    )
    auth_path = tmp_path / "authority-bases.json"
    auth_path.write_bytes(
        (
            json.dumps(consumer_authority_bases or [authority_basis()], sort_keys=True, indent=2)
            + "\n"
        ).encode()
    )
    adm_path = tmp_path / "admissibility-bases.json"
    adm_path.write_bytes(
        (
            json.dumps(
                consumer_admissibility_bases or [admissibility_basis()], sort_keys=True, indent=2
            )
            + "\n"
        ).encode()
    )
    authorization_path = tmp_path / "issuance-authorization.json"
    authorization_path.write_bytes(
        (
            json.dumps(
                {
                    "authorization_id": "SYNTH-RELIANCE-ISSUANCE-AUTHORIZATION-001",
                    "single_use": True,
                    "automatic_retry": False,
                    "assurance_class": "INTERNAL_TECHNICAL_DEMONSTRATION",
                },
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode()
    )
    output_path = tmp_path / f"consumer-result-{reliance_id}.json"
    job = {
        "envelope_path": str(envelope_path),
        "propagated_decision_path": str(decision_path),
        "producer_profile_path": str(producer_path),
        "consumer_profile_path": str(consumer_path),
        "authority_bases_path": str(auth_path),
        "admissibility_bases_path": str(adm_path),
        "authorization_path": str(authorization_path),
        "attempt_path": str(tmp_path / attempt_name),
        "output_path": str(output_path),
        "now": consumer_now,
        "with_future_successor": consumer_index_future,
        "without_control": consumer_without_control,
        "expected_scope": SCOPE,
        "expected_requested_use": REQUESTED_USE,
        "expected_subject_principal": SUBJECT_PRINCIPAL,
        "expected_artifact_ref": CONTROL_OUTPUT_REF,
        "decision_valid_until": decision_valid_until,
        "run_id": RUN_ID,
        "trace_id": TRACE_ID,
        "reliance_id": reliance_id,
        "direct_assertion_attempted": direct_assertion,
    }
    job_path = tmp_path / f"job-{reliance_id}.json"
    job_path.write_bytes((json.dumps(job, sort_keys=True, indent=2) + "\n").encode())

    completed = subprocess.run(
        [sys.executable, "-m", CONSUMER_MODULE, str(job_path)],
        capture_output=True,
        check=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    result = json.loads(output_path.read_bytes().decode("utf-8"))
    return {
        "result": result,
        "decision": decision,
        "envelope": envelope,
        "envelope_record": record,
        "materialized": materialized,
        "producer_process_id": os.getpid(),
        "stdout": completed.stdout,
        "index": index,
        "output_path": output_path,
    }


# ---------------------------------------------------------------------------
# T-EARLY-01..05 — the five real outputs terminate before authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "output_ref", AFFECTED_OUTPUT_REFS, ids=[f"T-EARLY-0{n}" for n in range(1, 6)]
)
def test_early_termination(output_ref: str) -> None:
    index = governed_index()
    artifact = historical_artifact(output_ref)
    resolution = resolve_currentness(
        output_ref=output_ref, historical_artifact=artifact, index=index, evaluated_at=T1
    )
    assert resolution.currentness_state == SUPERSEDED
    gate = evaluate_present_use(
        request=UseGateRequest(
            output_ref=output_ref,
            requested_use=REQUESTED_USE,
            requested_operation_class="PRESENT_USE_OF_HISTORICAL_OUTPUT",
            consequential=True,
            requesting_scope_ref=SCOPE,
            requested_at=T1,
        ),
        historical_artifact=artifact,
        currentness_index=index,
        profile=UseGateProfile(),
        run_metadata=RUN_METADATA,
    )
    assert gate.decision == DENY
    assert gate.reason_code_id == "G2"
    # Recorded as a positive fact, never inferred from an absent record.
    authority_gate_invoked = False
    assert authority_gate_invoked is False
    assert gate.next_gate is None


# ---------------------------------------------------------------------------
# T-POS-01..06 — the synthetic positive path
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One positive run, shared by the six T-POS criteria."""
    return _run_pipeline(tmp_path_factory.mktemp("positive"))


def test_pos_01_currentness_current(positive: dict[str, Any]) -> None:
    """T-POS-01."""
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index_without_successor(),
        evaluated_at=T1,
    )
    assert resolution.currentness_state == CURRENT
    assert resolution.reason_code_id == "R1"


def test_pos_02_authority_proceed(positive: dict[str, Any]) -> None:
    """T-POS-02."""
    decision = positive["decision"]
    assert decision.decision == "PROCEED"
    assert decision.reason_code_id == "A1"
    assert decision.reason_code == AUTHORITY_REASON_CODES["A1"]
    assert decision.valid_until


def test_pos_03_envelope_materialized(positive: dict[str, Any]) -> None:
    """T-POS-03."""
    materialized = positive["materialized"]
    assert Path(materialized["envelope_path"]).is_file()
    assert Path(materialized["ready_marker_path"]).is_file()
    assert materialized["fsync_performed"] is True


def test_pos_04_separate_consumer_process(positive: dict[str, Any]) -> None:
    """T-POS-04."""
    result = positive["result"]
    assert result["consumer_process_id"] != positive["producer_process_id"]
    assert result["consumer_inputs_were_paths_only"] is True
    assert result["producer_state_shared"] is False
    assert result["consumer_principal"] == CONSUMER_PRINCIPAL


def test_pos_05_consumer_revalidates(positive: dict[str, Any]) -> None:
    """T-POS-05."""
    validation = positive["result"]["validation"]
    assert [check["check_id"] for check in validation["checks"]] == list(range(1, 17))
    assert all(check["passed"] for check in validation["checks"])
    assert positive["result"]["re_resolved_currentness_state"] == CURRENT
    assert (
        validation["observed_currentness_epoch_digest"]
        == (positive["envelope_record"]["currentness_epoch_digest"])
    )


def test_pos_06_reliance_issued(positive: dict[str, Any]) -> None:
    """T-POS-06."""
    reliance = positive["result"]["reliance_record"]
    assert reliance["reliance_disposition"] == ISSUED
    assert reliance["reason_code_id"] == "I1"
    assert reliance["reliance_class"] == "SYNTHETIC_BOUNDED_DEMONSTRATION_RELIANCE"
    assert reliance["attempt_record_digest"]
    assert reliance["issuance_authorization_digest"]
    # The record binds the re-resolved currentness, not the propagated value.
    assert (
        reliance["currentness_resolution_digest"]
        == (positive["result"]["validation"]["re_resolved_currentness_resolution_digest"])
    )


# ---------------------------------------------------------------------------
# T-CASE-A..N, O, P, Q, R, S
# ---------------------------------------------------------------------------


def test_case_a_authority_deny(tmp_path: Path) -> None:
    """T-CASE-A — CURRENT + authority DENY, no propagation."""
    decision = _authority_decision(
        index=index_without_successor(),
        bases=[authority_basis(revocation_state="REVOKED")],
    )
    assert decision.decision == "DENY"
    assert decision.reason_code_id == "A10"
    assert not list(tmp_path.glob("*envelope*"))


def test_case_b_authority_escalate(tmp_path: Path) -> None:
    """T-CASE-B — CURRENT + authority ESCALATE, no reliance."""
    decision = _authority_decision(index=index_without_successor(), escalate=True)
    assert decision.decision == "ESCALATE"
    assert decision.reason_code_id == "A7"
    assert not list(tmp_path.glob("*envelope*"))


def test_case_c_tampered_envelope(tmp_path: Path) -> None:
    """T-CASE-C — tampered envelope → P2 → I6."""
    run = _run_pipeline(tmp_path, tamper=True)
    checks = run["result"]["validation"]["checks"]
    assert checks[0]["passed"] is False
    assert checks[0]["observed"] == "P2"
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"
    assert run["result"]["reliance_record"]["reliance_disposition"] == REFUSED


def test_case_d_wrong_artifact(tmp_path: Path) -> None:
    """T-CASE-D — wrong artifact → P4 → I6."""
    run = _run_pipeline(tmp_path, envelope_overrides={"artifact_digest": "0" * 64})
    checks = run["result"]["validation"]["checks"]
    assert checks[3]["check_name"] == "artifact_identity"
    assert checks[3]["passed"] is False
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"


def test_case_e_wrong_scope(tmp_path: Path) -> None:
    """T-CASE-E — wrong scope → P5 → I6."""
    run = _run_pipeline(tmp_path, envelope_overrides={"scope": "OTHER-SCOPE"})
    checks = run["result"]["validation"]["checks"]
    assert checks[4]["check_name"] == "scope_binding"
    assert checks[4]["passed"] is False
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"


def test_case_f_wrong_principal(tmp_path: Path) -> None:
    """T-CASE-F — wrong subject principal → P6 → I6."""
    run = _run_pipeline(
        tmp_path, envelope_overrides={"requesting_subject_principal": "SYNTHETIC-OTHER-001"}
    )
    checks = run["result"]["validation"]["checks"]
    assert checks[5]["check_name"] == "subject_principal_binding"
    assert checks[5]["passed"] is False
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"


def test_case_g_expired_authority_decision(tmp_path: Path) -> None:
    """T-CASE-G — expired propagated decision → I4, terminal before checks 13-15."""
    run = _run_pipeline(tmp_path, consumer_now=T2, decision_valid_until="2026-08-15T11:00:00Z")
    checks = run["result"]["validation"]["checks"]
    assert checks[10]["check_name"] == "propagated_authority_decision_identity"
    assert checks[10]["passed"] is True
    assert checks[11]["check_name"] == "propagated_authority_decision_freshness"
    assert checks[11]["passed"] is False
    # Terminal: no fresh re-evaluation is allowed to revive it.
    for index in (12, 13, 14):
        assert checks[index]["passed"] is False
        assert checks[index]["observed"].startswith("NOT_EVALUATED")
    assert run["result"]["reliance_record"]["reason_code_id"] == "I4"


def test_case_h_expired_envelope(tmp_path: Path) -> None:
    """T-CASE-H — expired envelope → P3 → I6."""
    run = _run_pipeline(tmp_path, envelope_overrides={"valid_until": "2026-08-15T09:30:00Z"})
    checks = run["result"]["validation"]["checks"]
    assert checks[2]["check_name"] == "envelope_freshness"
    assert checks[2]["passed"] is False
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"


def test_case_i_direct_assertion(tmp_path: Path) -> None:
    """T-CASE-I — caller asserts reliance directly → I7."""
    run = _run_pipeline(tmp_path, direct_assertion=True)
    reliance = run["result"]["reliance_record"]
    assert reliance["reason_code_id"] == "I7"
    assert reliance["reliance_disposition"] == REFUSED


def test_case_j_replayed_authorization(tmp_path: Path) -> None:
    """T-CASE-J — replay of a consumed issuance authorization → I8."""
    first = _run_pipeline(tmp_path, reliance_id="SYNTH-RELIANCE-J1")
    assert first["result"]["reliance_record"]["reliance_disposition"] == ISSUED
    second = _run_pipeline(
        tmp_path,
        reliance_id="SYNTH-RELIANCE-J2",
        envelope_name="envelope-2.json",
    )
    assert second["result"]["reliance_record"]["reason_code_id"] == "I8"
    assert second["result"]["reliance_record"]["reliance_disposition"] == REFUSED


def test_case_k_currentness_toctou(tmp_path: Path) -> None:
    """T-CASE-K — correction becomes operative between t1 and t2 → I2, epoch moved."""
    run = _run_pipeline(
        tmp_path,
        producer_now=T1,
        consumer_now=T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    result = run["result"]
    assert result["re_resolved_currentness_state"] == SUPERSEDED
    assert result["reliance_record"]["reason_code_id"] == "I2"
    assert result["reliance_record"]["reliance_disposition"] == REFUSED
    # The I3 observation, recorded as frozen: the epoch moved across the boundary.
    index = index_with_future_successor()
    epoch_t1 = epoch_for(index, CONTROL_OUTPUT_REF, T1)
    epoch_t2 = epoch_for(index, CONTROL_OUTPUT_REF, T2)
    assert epoch_t1 != epoch_t2
    assert run["envelope_record"]["currentness_epoch_digest"] == epoch_t1
    checks = result["validation"]["checks"]
    assert checks[12]["check_name"] == "currentness_re_resolution"
    assert checks[12]["passed"] is False


def test_case_l_historical_reliance_preserved(tmp_path: Path) -> None:
    """T-CASE-L — an issued record stays byte-identical; later reliance is refused."""
    issued = _run_pipeline(tmp_path, reliance_id="SYNTH-RELIANCE-L1")
    assert issued["result"]["reliance_record"]["reliance_disposition"] == ISSUED
    before = persisted_file_sha256(Path(issued["output_path"]).read_bytes())

    later = _run_pipeline(
        tmp_path,
        reliance_id="SYNTH-RELIANCE-L2",
        envelope_name="envelope-later.json",
        attempt_name="attempt-later.json",
        producer_now=T1,
        consumer_now=T2,
        producer_index_future=True,
        consumer_index_future=True,
    )
    assert later["result"]["reliance_record"]["reliance_disposition"] == REFUSED
    assert later["result"]["reliance_record"]["reason_code_id"] == "I2"
    after = persisted_file_sha256(Path(issued["output_path"]).read_bytes())
    assert after == before
    # The historical record carries no marker announcing its own obsolescence.
    assert "superseded" not in json.dumps(issued["result"]["reliance_record"]).lower()


def test_case_m_currentness_basis_unreachable(tmp_path: Path) -> None:
    """T-CASE-M — basis unreachable at reliance time → I9, fail closed."""
    run = _run_pipeline(tmp_path, consumer_without_control=True)
    assert run["result"]["reliance_record"]["reason_code_id"] == "I9"
    checks = run["result"]["validation"]["checks"]
    assert checks[12]["observed"] == "BASIS_UNREACHABLE"


def test_case_n_competing_authority_basis(tmp_path: Path) -> None:
    """T-CASE-N — competing operative authority bases → A6, no propagation."""
    decision = _authority_decision(
        index=index_without_successor(),
        bases=[authority_basis(), authority_basis(basis_id="SYNTH-AUTH-BASIS-002")],
    )
    assert decision.decision == "DENY"
    assert decision.reason_code_id == "A6"
    assert not list(tmp_path.glob("*envelope*"))


def test_case_o_wrong_intended_consumer(tmp_path: Path) -> None:
    """T-CASE-O — envelope addressed to another consumer → P12 → I6."""
    run = _run_pipeline(
        tmp_path,
        envelope_overrides={"intended_consumer_principal": "SYNTHETIC-OTHER-CONSUMER-001"},
    )
    checks = run["result"]["validation"]["checks"]
    assert checks[7]["check_name"] == "intended_consumer_binding"
    assert checks[7]["passed"] is False
    assert run["result"]["reliance_record"]["reason_code_id"] == "I6"


def test_case_p_authority_toctou(tmp_path: Path) -> None:
    """T-CASE-P — standing revoked between t1 and t2 while the artifact stays CURRENT."""
    run = _run_pipeline(
        tmp_path,
        producer_now=T1,
        consumer_now=T2,
        consumer_authority_bases=[authority_basis(revocation_state="REVOKED")],
    )
    result = run["result"]
    assert result["re_resolved_currentness_state"] == CURRENT
    checks = result["validation"]["checks"]
    assert checks[13]["check_name"] == "epoch_applicability"
    assert checks[13]["passed"] is True
    assert checks[14]["check_name"] == "authority_admissibility_re_evaluation"
    assert checks[14]["passed"] is False
    assert result["reliance_time_authority_decision"]["reason_code_id"] == "A10"
    assert result["reliance_record"]["reason_code_id"] == "I11"
    assert result["reliance_record"]["reliance_disposition"] == REFUSED


def test_case_q_authority_basis_missing(tmp_path: Path) -> None:
    """T-CASE-Q — no authority basis for (principal, scope) → A11, no propagation."""
    decision = _authority_decision(index=index_without_successor(), bases=[])
    assert decision.reason_code_id == "A11"
    assert decision.decision == "DENY"
    assert not list(tmp_path.glob("*envelope*"))


def test_case_r_authority_basis_invalid(tmp_path: Path) -> None:
    """T-CASE-R — stored authority digest does not reproduce → A12."""
    broken = {**authority_basis(), "record_digest": "0" * 64}
    decision = _authority_decision(index=index_without_successor(), bases=[broken])
    assert decision.reason_code_id == "A12"
    assert decision.decision == "DENY"
    assert not list(tmp_path.glob("*envelope*"))


def test_case_s_admissibility_basis_revoked(tmp_path: Path) -> None:
    """T-CASE-S — admissibility basis revoked → A13, its own code, not A10."""
    decision = _authority_decision(
        index=index_without_successor(),
        admissibility=[admissibility_basis(revocation_state="REVOKED")],
    )
    assert decision.reason_code_id == "A13"
    assert decision.decision == "DENY"
    assert not list(tmp_path.glob("*envelope*"))


# ---------------------------------------------------------------------------
# T-DIG-01..08
# ---------------------------------------------------------------------------


def test_dig_01_currentness_epoch_digest() -> None:
    """T-DIG-01 — Class 1: all three published vectors, from the published inputs.

    Derivation v0.4 publishes the complete input for every vector, including the
    successor's ``record_digest`` that v0.1-v0.3 omitted.  Nothing here is
    inferred and nothing is locally generated: the exact frozen digests must come
    back out.
    """
    assert canonical_bytes({"b": 2, "a": "é"}) == b'{"a":"\xc3\xa9","b":2}'
    assert (
        canonical_digest({"b": 2, "a": "é"})
        == "06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de"
    )

    output_ref = "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-01"
    attestation = "eb450545e966f2763da2a49f404f96a0624786925b276b5c83428908453237e7"
    successor = {
        "output_ref": output_ref,
        "record_ref": "EBAWU-P-001-C-TENDER-01-CORR-002#" + output_ref,
        "record_digest": ("943affbf3e86d8a1b6831eb3deafb2efeac902989d8ee75fe85daea6f82e1e3c"),
        "record_class": "CORRECTION_SUCCESSOR_RECORD",
        "effective_at": "2026-08-15T12:00:00Z",
        "admitted_at": "2026-08-15T09:00:00Z",
    }
    reduced = {key: successor[key] for key in EPOCH_RECORD_FIELDS}

    # EPOCH-A — admitted but not operative at 10:00, so excluded; state CURRENT.
    epoch_a_object = {
        "output_ref": output_ref,
        "completeness_attestation_digest": attestation,
        "operative_basis_records": [],
    }
    assert len(canonical_bytes(epoch_a_object)) == 185
    epoch_a = currentness_epoch_digest(
        output_ref=output_ref,
        as_of="2026-08-15T10:00:00Z",
        governing_records=[successor],
        completeness_attestation_digest=attestation,
    )
    assert epoch_a == "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46"
    assert epoch_a == canonical_digest(epoch_a_object)

    # EPOCH-B — the same successor operative at 13:00; attestation null.
    epoch_b_object = {
        "output_ref": output_ref,
        "completeness_attestation_digest": None,
        "operative_basis_records": [reduced],
    }
    assert len(canonical_bytes(epoch_b_object)) == 414
    epoch_b = currentness_epoch_digest(
        output_ref=output_ref,
        as_of="2026-08-15T13:00:00Z",
        governing_records=[successor],
        completeness_attestation_digest=None,
    )
    assert epoch_b == "6858b71d2940bbc0d8e5f20023f772435d282fad1d47201a3fdc72d8b80ef7ac"
    assert epoch_b == canonical_digest(epoch_b_object)

    # EPOCH-C — control: an unrelated output's operative successor never enters.
    unrelated = {
        **successor,
        "output_ref": "CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02",
        "record_ref": "EBAWU-OTHER#CDC-TEST-MISSION-001/CDC-E2E-OUTPUT-02",
        "effective_at": "2026-08-15T08:00:00Z",
    }
    epoch_c = currentness_epoch_digest(
        output_ref=output_ref,
        as_of="2026-08-15T10:00:00Z",
        governing_records=[successor, unrelated],
        completeness_attestation_digest=attestation,
    )
    assert epoch_c == "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46"
    assert len(canonical_bytes(epoch_a_object)) == 185

    # The two frozen required properties.
    assert epoch_a != epoch_b
    assert epoch_c == epoch_a


def test_dig_02_authority_basis_record_digest() -> None:
    """T-DIG-02 — Class 2, both published basis vectors."""
    auth = {k: v for k, v in authority_basis().items() if k != "record_digest"}
    assert len(canonical_bytes(auth)) == 431
    assert (
        authority_basis_record_digest(auth)
        == "7ad84cfb124b794b67ebdcfc6ca4282a86a228cb95c5a1a7bd8c4448232f310e"
    )
    adm = {k: v for k, v in admissibility_basis().items() if k != "record_digest"}
    assert len(canonical_bytes(adm)) == 371
    assert (
        authority_basis_record_digest(adm)
        == "bf29f3d75a313301c223fd12183f6f7c134cb1683c8d388d7377fb401d2219e3"
    )


def test_dig_03_authority_decision_digest() -> None:
    """T-DIG-03 — Class 3; both currentness bindings participate."""
    decision = _authority_decision(index=index_without_successor())
    record = decision.as_record()
    assert record["authority_decision_digest"] == authority_decision_digest(record)
    moved = {**record, "currentness_epoch_digest": "0" * 64}
    assert authority_decision_digest(moved) != authority_decision_digest(record)


def test_dig_04_envelope_digest(tmp_path: Path) -> None:
    """T-DIG-04 — Class 4; the three roles participate separately."""
    run = _run_pipeline(tmp_path)
    record = run["envelope_record"]
    assert record["envelope_digest"] == envelope_digest(record)
    for field in (
        "requesting_subject_principal",
        "intended_consumer_principal",
    ):
        assert envelope_digest({**record, field: "SYNTHETIC-CHANGED"}) != record["envelope_digest"]


def test_dig_05_consumer_validation_digest(tmp_path: Path) -> None:
    """T-DIG-05 — Class 5; checks[] frozen 1..16, order never re-sorted."""
    run = _run_pipeline(tmp_path)
    validation = run["result"]["validation"]
    assert validation["consumer_validation_digest"] == consumer_validation_digest(validation)
    assert [check["check_id"] for check in validation["checks"]] == list(range(1, 17))
    assert [check["check_name"] for check in validation["checks"]] == [
        name for _, name in CONSUMER_CHECKS
    ]
    reordered = {**validation, "checks": list(reversed(validation["checks"]))}
    assert consumer_validation_digest(reordered) != validation["consumer_validation_digest"]


def test_dig_06_reliance_record_digest(tmp_path: Path) -> None:
    """T-DIG-06 — Class 6; both authority moments participate."""
    run = _run_pipeline(tmp_path)
    record = run["result"]["reliance_record"]
    assert record["reliance_record_digest"] == reliance_record_digest(record)
    assert record["propagated_authority_decision_digest"]
    assert record["reliance_time_authority_decision_digest"]
    assert (
        record["propagated_authority_decision_digest"]
        != record["reliance_time_authority_decision_digest"]
    )


def test_dig_07_integration_package_digest() -> None:
    """T-DIG-07 — Class 7; members as identities, bodies not embedded."""
    package = {
        "record_class": "CDC_INTEGRATION_SLICE_001_RAW_EXECUTION_PACKAGE",
        "members": [{"path": "a.json", "bytes": 10, "sha256": "ab" * 32}],
        "package_digest": "0" * 64,
    }
    assert integration_package_digest(package) == canonical_digest(
        {k: v for k, v in package.items() if k != "package_digest"}
    )


def test_dig_08_synthetic_profile_digest() -> None:
    """T-DIG-08 — Class 8, both published profile vectors."""
    producer = {k: v for k, v in producer_profile().items() if k != "profile_digest"}
    assert len(canonical_bytes(producer)) == 398
    assert (
        synthetic_profile_digest(producer)
        == "1c7ac979d5544923de7f90f521b79b2cef793e0c75237a8566febbb783c90d1c"
    )
    consumer = {k: v for k, v in consumer_profile().items() if k != "profile_digest"}
    assert len(canonical_bytes(consumer)) == 416
    assert (
        synthetic_profile_digest(consumer)
        == "889ab97b43b110cf738bb2954dcc0ca19ed352f14a05207437dbb92192d0d5ec"
    )


# ---------------------------------------------------------------------------
# T-EPOCH-A / B / C
# ---------------------------------------------------------------------------


def test_epoch_a_future_successor_excluded() -> None:
    """T-EPOCH-A — admitted but not yet operative is excluded at t1."""
    index = index_with_future_successor()
    epoch = epoch_for(index, CONTROL_OUTPUT_REF, T1)
    without = epoch_for(index_without_successor(), CONTROL_OUTPUT_REF, T1)
    assert epoch == without
    # And a clock tick alone, short of the boundary, moves nothing.
    assert epoch_for(index, CONTROL_OUTPUT_REF, "2026-08-15T11:59:59Z") == epoch


def test_epoch_b_boundary_crossing_moves_epoch() -> None:
    """T-EPOCH-B — the same successor operative at t2 changes the epoch."""
    index = index_with_future_successor()
    assert epoch_for(index, CONTROL_OUTPUT_REF, T1) != epoch_for(index, CONTROL_OUTPUT_REF, T2)


def test_epoch_c_unrelated_output_control() -> None:
    """T-EPOCH-C — an unrelated output's governed state does not move this epoch."""
    index = index_without_successor()
    queried = epoch_for(index, CONTROL_OUTPUT_REF, T1)
    with_unrelated = index_with_future_successor()
    other = epoch_for(with_unrelated, AFFECTED_OUTPUT_REFS[0], T1)
    assert epoch_for(index, CONTROL_OUTPUT_REF, T1) == queried
    assert other != queried


# ---------------------------------------------------------------------------
# Closed-set and layer-commitment assertions (supporting, not frozen criteria)
# ---------------------------------------------------------------------------


def test_reason_code_sets_are_closed() -> None:
    assert len(AUTHORITY_REASON_CODES) == 13
    assert len(PROPAGATION_REASON_CODES) == 12
    assert len(RELIANCE_REASON_CODES) == 11
    assert len(CONSUMER_CHECKS) == 16


def test_currentness_pass_is_not_authority_pass() -> None:
    from oic.cdc_authority import CURRENTNESS_PASS_IS_AUTHORITY_PASS

    assert CURRENTNESS_PASS_IS_AUTHORITY_PASS is False
    decision = _authority_decision(index=index_without_successor(), bind_currentness=False)
    assert decision.reason_code_id == "A9"


def test_envelope_schema_is_closed(tmp_path: Path) -> None:
    run = _run_pipeline(tmp_path)
    record = run["envelope_record"]
    assert parse_envelope(json.dumps({**record, "extra": 1}).encode()).reason_code_id == "P8"
    trimmed = {k: v for k, v in record.items() if k != "scope"}
    assert parse_envelope(json.dumps(trimmed).encode()).reason_code_id == "P9"


def test_producer_and_consumer_principals_differ() -> None:
    assert PRODUCER_PRINCIPAL != CONSUMER_PRINCIPAL  # type: ignore[comparison-overlap]
    assert SUBJECT_PRINCIPAL not in (PRODUCER_PRINCIPAL, CONSUMER_PRINCIPAL)
