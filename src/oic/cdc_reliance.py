"""Consumer revalidation and bounded synthetic reliance issuance, slice 001.

Implements the sixteen frozen consumer checks of
``…SEMANTIC-DESIGN-v0.4.md`` §2 (03ca22e9…) and digest Classes 5, 6 and 7 of
``INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.4.md`` (494c91ac…).

The rule the whole module exists to hold:

    EVALUATION ESTABLISHES THE PROPERTY · ISSUANCE CREATES THE RELIANCE

An authority PROCEED is not reliance.  A materialized envelope is not reliance.
A consumer validation that passes every check is not reliance.  Reliance exists
only once an issuance record is written under a single-use authorization whose
attempt was already claimed and frozen — and a refusal is recorded with the same
care as an issuance.

Two ordering facts are load-bearing and are not incidental:

* check 12 (is the propagated decision still within its own life) runs BEFORE
  checks 13-15, and its failure is terminal for the envelope.  A fresh positive
  re-evaluation at check 15 never revives an expired propagated decision — an
  expiry that any later success annuls is not an expiry.
* the reliance record binds the RE-RESOLVED currentness, never the value that
  travelled in the envelope.  The propagated value is input to validation; it is
  never the value of record.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from oic.cdc_authority import (
    ASSURANCE_CLASS,
    PROCEED,
    AuthorityDecisionRecord,
    SyntheticProfile,
    canonical_digest,
    digests_equal,
)
from oic.cdc_propagation import parse_envelope
from oic.errors import OICError

RELIANCE_RECORD_CLASS: Final = "RELIANCE_ISSUANCE"
CONSUMER_VALIDATION_RECORD_CLASS: Final = "CONSUMER_VALIDATION"
RELIANCE_CLASS: Final = "SYNTHETIC_BOUNDED_DEMONSTRATION_RELIANCE"

ISSUED: Final = "ISSUED"
REFUSED: Final = "REFUSED"

RELIANCE_REASON_CODES: Final[dict[str, str]] = {
    "I1": "RELIANCE_ISSUED",
    "I2": "RELIANCE_REFUSED_CURRENTNESS_NOT_CURRENT",
    "I3": "RELIANCE_REFUSED_CURRENTNESS_EPOCH_MOVED",
    "I4": "RELIANCE_REFUSED_AUTHORITY_DECISION_EXPIRED",
    "I5": "RELIANCE_REFUSED_AUTHORITY_DECISION_NOT_POSITIVE",
    "I6": "RELIANCE_REFUSED_ENVELOPE_INVALID",
    "I7": "RELIANCE_REFUSED_DIRECT_ASSERTION_REJECTED",
    "I8": "RELIANCE_REFUSED_ISSUANCE_AUTHORIZATION_ALREADY_CONSUMED",
    "I9": "RELIANCE_REFUSED_CURRENTNESS_BASIS_UNREACHABLE",
    "I10": "RELIANCE_REFUSED_AUTHORITY_BASIS_COMPETING_UNRESOLVED",
    "I11": "RELIANCE_REFUSED_AUTHORITY_NOT_CURRENT_AT_RELIANCE",
}
RELIANCE_REASON_CODE_COUNT: Final = len(RELIANCE_REASON_CODES)

# Frozen order 1..16 — derivation v0.4 §6, unchanged from v0.3.  Never re-sorted, never shortened.
CONSUMER_CHECKS: Final[tuple[tuple[int, str], ...]] = (
    (1, "envelope_integrity"),
    (2, "schema_closure"),
    (3, "envelope_freshness"),
    (4, "artifact_identity"),
    (5, "scope_binding"),
    (6, "subject_principal_binding"),
    (7, "requested_use_binding"),
    (8, "intended_consumer_binding"),
    (9, "evidence_resolvability"),
    (10, "producer_identity"),
    (11, "propagated_authority_decision_identity"),
    (12, "propagated_authority_decision_freshness"),
    (13, "currentness_re_resolution"),
    (14, "epoch_applicability"),
    (15, "authority_admissibility_re_evaluation"),
    (16, "issuance_gate"),
)
CONSUMER_CHECK_COUNT: Final = len(CONSUMER_CHECKS)

NOT_EVALUATED: Final = "NOT_EVALUATED_TERMINAL_REFUSAL_EARLIER_IN_FROZEN_ORDER"


class RelianceContractError(OICError):
    """The reliance layer refused to act rather than exceed its authority."""


def consumer_validation_digest(record: Mapping[str, Any]) -> str:
    """Class 5 — the validation record minus its own digest; checks[] in order."""
    return canonical_digest(
        {key: value for key, value in record.items() if key != "consumer_validation_digest"}
    )


def reliance_record_digest(record: Mapping[str, Any]) -> str:
    """Class 6 — both authority moments and the re-resolved currentness participate."""
    return canonical_digest(
        {key: value for key, value in record.items() if key != "reliance_record_digest"}
    )


def integration_package_digest(record: Mapping[str, Any]) -> str:
    """Class 7 — package minus its own digest; members as identities only."""
    return canonical_digest(
        {key: value for key, value in record.items() if key != "package_digest"}
    )


def persisted_file_sha256(payload: bytes) -> str:
    """The persisted-file rule used for both file-identity digests."""
    import hashlib

    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class ReResolvedCurrentness:
    """What the consumer established for itself, at reliance time."""

    currentness_state: str
    resolution_digest: str
    epoch_digest: str
    basis_reachable: bool


@dataclass(frozen=True, slots=True, eq=False)
class ConsumerContext:
    """Everything the consumer needs, with re-derivation supplied as callables.

    The callables exist so that checks 13 and 15 cannot be satisfied by anything
    the envelope carried: the consumer must recompute from governed bytes it
    reads itself.
    """

    consumer_profile: SyntheticProfile
    producer_profile: SyntheticProfile
    consumer_identity: Mapping[str, Any]
    now: str
    expected_scope: str
    expected_requested_use: str
    expected_subject_principal: str
    recompute_artifact_digest: Callable[[str], str | None]
    resolve_evidence_ref: Callable[[Mapping[str, Any]], bool]
    re_resolve_currentness: Callable[[str, str], ReResolvedCurrentness]
    re_evaluate_authority: Callable[[str, str, ReResolvedCurrentness], AuthorityDecisionRecord]


def _check(check_id: int, name: str, expected: Any, observed: Any, passed: bool) -> dict[str, Any]:  # noqa: ANN401
    return {
        "check_id": check_id,
        "check_name": name,
        "expected": expected,
        "observed": observed,
        "passed": passed,
    }


def run_consumer_validation(
    *,
    envelope_bytes: bytes,
    propagated_decision: Mapping[str, Any],
    context: ConsumerContext,
) -> dict[str, Any]:
    """Run the sixteen frozen checks in order and stop at the first failure.

    Every one of the sixteen appears in ``checks[]`` in ascending order whatever
    happens, so the digest domain is well defined; those never reached are
    recorded as not evaluated rather than quietly omitted or marked passed.
    """
    checks: list[dict[str, Any]] = []
    failure: tuple[str, str] | None = None
    re_resolved: ReResolvedCurrentness | None = None
    reliance_time_decision: AuthorityDecisionRecord | None = None

    parsed = parse_envelope(envelope_bytes)
    record: Mapping[str, Any] = parsed.record or {}

    # 1 envelope integrity, 2 schema closure — both come out of the same parse,
    # attributed to their own check.
    integrity_ok = parsed.accepted or parsed.reason_code_id not in {"P2", "P11"}
    checks.append(
        _check(
            1,
            "envelope_integrity",
            "envelope_digest reproduces",
            parsed.reason_code_id if not integrity_ok else "P1",
            integrity_ok,
        )
    )
    if not integrity_ok:
        failure = ("I6", parsed.reason_code_id)
    closure_ok = failure is None and parsed.reason_code_id not in {"P8", "P9"}
    checks.append(
        _check(
            2,
            "schema_closure",
            "no unknown or missing fields",
            NOT_EVALUATED
            if failure is not None
            else (parsed.reason_code_id if not closure_ok else "P1"),
            bool(closure_ok),
        )
    )
    if failure is None and not closure_ok:
        failure = ("I6", parsed.reason_code_id)

    def step(
        check_id: int,
        name: str,
        expected: object,
        evaluate: Callable[[], tuple[bool, Any, str]],
    ) -> None:
        nonlocal failure
        if failure is not None:
            checks.append(_check(check_id, name, expected, NOT_EVALUATED, False))
            return
        passed, observed, code = evaluate()
        checks.append(_check(check_id, name, expected, observed, passed))
        if not passed:
            failure = (code, name)

    def freshness() -> tuple[bool, Any, str]:
        produced_at = str(record.get("produced_at"))
        valid_until = str(record.get("valid_until"))
        ok = produced_at <= context.now <= valid_until
        return (
            ok,
            {"produced_at": produced_at, "now": context.now, "valid_until": valid_until},
            "I6",
        )

    def artifact_identity() -> tuple[bool, Any, str]:
        recomputed = context.recompute_artifact_digest(str(record.get("artifact_ref")))
        bound = str(record.get("artifact_digest"))
        ok = recomputed is not None and digests_equal(recomputed, bound)
        return ok, {"recomputed": recomputed, "bound": bound}, "I6"

    def scope_binding() -> tuple[bool, Any, str]:
        observed = str(record.get("scope"))
        return observed == context.expected_scope, observed, "I6"

    def subject_binding() -> tuple[bool, Any, str]:
        observed = str(record.get("requesting_subject_principal"))
        return observed == context.expected_subject_principal, observed, "I6"

    def use_binding() -> tuple[bool, Any, str]:
        observed = str(record.get("requested_use"))
        return observed == context.expected_requested_use, observed, "I6"

    def consumer_binding() -> tuple[bool, Any, str]:
        observed = str(record.get("intended_consumer_principal"))
        return observed == context.consumer_profile.principal_id, observed, "I6"

    def evidence_resolvability() -> tuple[bool, Any, str]:
        refs = record.get("evidence_refs") or []
        unresolved = [ref for ref in refs if not context.resolve_evidence_ref(ref)]
        return not unresolved, {"count": len(refs), "unresolved": len(unresolved)}, "I6"

    def producer_identity() -> tuple[bool, Any, str]:
        identity = record.get("producer_identity") or {}
        observed = str(identity.get("producer_principal"))
        ok = (
            observed == context.producer_profile.principal_id
            and context.producer_profile.digest_reproduces
        )
        return ok, observed, "I6"

    def decision_identity() -> tuple[bool, Any, str]:
        from oic.cdc_authority import authority_decision_digest

        recomputed = authority_decision_digest(propagated_decision)
        bound = str(record.get("authority_decision_digest"))
        if not digests_equal(recomputed, bound):
            return False, {"recomputed": recomputed, "bound": bound}, "I6"
        if propagated_decision.get("decision") != PROCEED:
            return False, propagated_decision.get("decision"), "I5"
        return True, recomputed, "I1"

    def decision_freshness() -> tuple[bool, Any, str]:
        valid_until = str(propagated_decision.get("valid_until"))
        ok = context.now <= valid_until
        return ok, {"now": context.now, "decision_valid_until": valid_until}, "I4"

    def currentness_re_resolution() -> tuple[bool, Any, str]:
        nonlocal re_resolved
        re_resolved = context.re_resolve_currentness(str(record.get("artifact_ref")), context.now)
        if not re_resolved.basis_reachable:
            return False, "BASIS_UNREACHABLE", "I9"
        if re_resolved.currentness_state != "CURRENT":
            return False, re_resolved.currentness_state, "I2"
        return True, re_resolved.currentness_state, "I1"

    def epoch_applicability() -> tuple[bool, Any, str]:
        if re_resolved is None:
            raise RelianceContractError("epoch check reached without a re-resolution")
        bound = str(propagated_decision.get("currentness_epoch_digest"))
        ok = digests_equal(re_resolved.epoch_digest, bound)
        return ok, {"epoch_now": re_resolved.epoch_digest, "epoch_bound": bound}, "I3"

    def authority_re_evaluation() -> tuple[bool, Any, str]:
        nonlocal reliance_time_decision
        if re_resolved is None:
            raise RelianceContractError("authority re-evaluation reached without a re-resolution")
        reliance_time_decision = context.re_evaluate_authority(
            str(record.get("artifact_ref")), context.now, re_resolved
        )
        if reliance_time_decision.reason_code_id == "A6":
            return False, reliance_time_decision.reason_code_id, "I10"
        if reliance_time_decision.decision != PROCEED:
            return False, reliance_time_decision.reason_code_id, "I11"
        return True, reliance_time_decision.reason_code_id, "I1"

    step(3, "envelope_freshness", "produced_at <= now <= valid_until", freshness)
    step(4, "artifact_identity", "recomputed digest equals bound digest", artifact_identity)
    step(5, "scope_binding", context.expected_scope, scope_binding)
    step(6, "subject_principal_binding", context.expected_subject_principal, subject_binding)
    step(7, "requested_use_binding", context.expected_requested_use, use_binding)
    step(8, "intended_consumer_binding", context.consumer_profile.principal_id, consumer_binding)
    step(9, "evidence_resolvability", "every evidence_ref resolves", evidence_resolvability)
    step(10, "producer_identity", context.producer_profile.principal_id, producer_identity)
    step(
        11,
        "propagated_authority_decision_identity",
        "digest reproduces and PROCEED",
        decision_identity,
    )
    step(
        12,
        "propagated_authority_decision_freshness",
        "now <= decision.valid_until",
        decision_freshness,
    )
    step(13, "currentness_re_resolution", "CURRENT", currentness_re_resolution)
    step(14, "epoch_applicability", "epoch_now == epoch bound in decision", epoch_applicability)
    step(15, "authority_admissibility_re_evaluation", "PROCEED", authority_re_evaluation)

    gate_open = failure is None
    checks.append(
        _check(
            16,
            "issuance_gate",
            "all required checks passed",
            "OPEN" if gate_open else f"CLOSED_{failure[0]}",  # type: ignore[index]
            gate_open,
        )
    )

    validation = {
        "record_class": CONSUMER_VALIDATION_RECORD_CLASS,
        "envelope_digest": str(record.get("envelope_digest", "")),
        "checks": checks,
        "decision": "PROCEED_TO_ISSUANCE" if gate_open else "REFUSE",
        "reason_code": (
            RELIANCE_REASON_CODES["I1"] if gate_open else RELIANCE_REASON_CODES[failure[0]]  # type: ignore[index]
        ),
        "consumer_identity": dict(context.consumer_identity),
        "evaluated_at": context.now,
        "re_resolved_currentness_resolution_digest": (
            None if re_resolved is None else re_resolved.resolution_digest
        ),
        "observed_currentness_epoch_digest": (
            None if re_resolved is None else re_resolved.epoch_digest
        ),
        "reliance_time_authority_decision_digest": (
            None
            if reliance_time_decision is None
            else reliance_time_decision.authority_decision_digest
        ),
        "consumer_validation_digest": "",
    }
    validation["consumer_validation_digest"] = consumer_validation_digest(validation)
    return {
        "validation": validation,
        "gate_open": gate_open,
        "reason_code_id": "I1" if gate_open else failure[0],  # type: ignore[index]
        "re_resolved": re_resolved,
        "reliance_time_decision": reliance_time_decision,
        "envelope_record": record,
        "envelope_parse": parsed,
    }


def claim_issuance_attempt(
    *, authorization_path: Path, attempt_path: Path, run_id: str, trace_id: str, claimed_at: str
) -> dict[str, Any]:
    """Claim the single-use attempt, in the frozen write order.

    Step 1 is the authorization file, already persisted by the owner.  Step 2 is
    this attempt record, written by exclusive creation and frozen.  Only then may
    a reliance record be written binding both — so no object depends on a digest
    computed over itself or over a later object.
    """
    authorization_bytes = authorization_path.read_bytes()
    authorization_digest = persisted_file_sha256(authorization_bytes)
    record = {
        "record_class": "RELIANCE_ISSUANCE_ATTEMPT",
        "issuance_authorization_path": str(authorization_path),
        "issuance_authorization_digest": authorization_digest,
        "run_id": run_id,
        "trace_id": trace_id,
        "claimed_at": claimed_at,
        "attempt_state": "CONSUMED_AT_FIRST_ISSUANCE_ATTEMPT",
    }
    payload = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    try:
        descriptor = os.open(attempt_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise RelianceContractError(
            "the issuance authorization is already consumed; no automatic retry is authorized"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "attempt_record": record,
        "attempt_record_path": str(attempt_path),
        "attempt_record_bytes": len(payload),
        "attempt_record_digest": persisted_file_sha256(payload),
        "issuance_authorization_digest": authorization_digest,
        "issuance_authorization_bytes": len(authorization_bytes),
    }


def issue_reliance(
    *,
    reliance_id: str,
    validation_outcome: Mapping[str, Any],
    propagated_decision: Mapping[str, Any],
    context: ConsumerContext,
    issuance_authorization_digest: str,
    attempt_record_digest: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    issued_at: str,
    direct_assertion_attempted: bool = False,
    authorization_already_consumed: bool = False,
) -> dict[str, Any]:
    """Write the reliance record — issued or refused, with equal care.

    A refusal is a reliance record too: it names its reason code and binds the
    same evidence, so a refused path is auditable rather than an absence.
    """
    record_env: Mapping[str, Any] = validation_outcome["envelope_record"]
    re_resolved: ReResolvedCurrentness | None = validation_outcome["re_resolved"]
    reliance_time_decision: AuthorityDecisionRecord | None = validation_outcome[
        "reliance_time_decision"
    ]
    if direct_assertion_attempted:
        reason_id = "I7"
    elif authorization_already_consumed:
        reason_id = "I8"
    else:
        reason_id = str(validation_outcome["reason_code_id"])
    disposition = ISSUED if reason_id == "I1" and not direct_assertion_attempted else REFUSED
    record = {
        "record_class": RELIANCE_RECORD_CLASS,
        "reliance_id": reliance_id,
        "consumer_id": context.consumer_profile.profile_id,
        "artifact_ref": record_env.get("artifact_ref"),
        "artifact_digest": record_env.get("artifact_digest"),
        "requested_use": record_env.get("requested_use"),
        "scope": record_env.get("scope"),
        "requesting_subject_principal": record_env.get("requesting_subject_principal"),
        "consumer_principal": context.consumer_profile.principal_id,
        "propagation_envelope_digest": record_env.get("envelope_digest"),
        "currentness_resolution_digest": (
            None if re_resolved is None else re_resolved.resolution_digest
        ),
        "currentness_epoch_digest": None if re_resolved is None else re_resolved.epoch_digest,
        "propagated_authority_decision_digest": propagated_decision.get(
            "authority_decision_digest"
        ),
        "reliance_time_authority_decision_digest": (
            None
            if reliance_time_decision is None
            else reliance_time_decision.authority_decision_digest
        ),
        "consumer_validation_digest": validation_outcome["validation"][
            "consumer_validation_digest"
        ],
        "issued_at": issued_at,
        "reliance_disposition": disposition,
        "reason_code_id": reason_id,
        "reason_code": RELIANCE_REASON_CODES[reason_id],
        "issuance_authorization_digest": issuance_authorization_digest,
        "attempt_record_digest": attempt_record_digest,
        "reliance_class": RELIANCE_CLASS,
        "assurance_class": ASSURANCE_CLASS,
        "evidence_refs": [dict(ref) for ref in evidence_refs],
        "reliance_record_digest": "",
    }
    record["reliance_record_digest"] = reliance_record_digest(record)
    return record


__all__ = [
    "CONSUMER_CHECKS",
    "CONSUMER_CHECK_COUNT",
    "ISSUED",
    "REFUSED",
    "RELIANCE_CLASS",
    "RELIANCE_REASON_CODES",
    "RELIANCE_REASON_CODE_COUNT",
    "ConsumerContext",
    "ReResolvedCurrentness",
    "RelianceContractError",
    "claim_issuance_attempt",
    "consumer_validation_digest",
    "integration_package_digest",
    "issue_reliance",
    "persisted_file_sha256",
    "reliance_record_digest",
    "run_consumer_validation",
]
