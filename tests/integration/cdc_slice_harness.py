"""End-to-end harness for the bounded CDC vertical slice.

The harness composes the owner-attested core into one inspectable pass:

``registry -> proposal -> gate decision -> (ALLOW only) transition event``

It is a driver, not a decision-maker. It never substitutes a decision, never
retries a refused transition, and never converts an ESCALATE or DENY into a
completion. When the core raises, the harness records the failure and preserves
the prior institutional state rather than fabricating an outcome.

Nothing executes at import. Every function below must be called explicitly, so
importing this module during collection performs no transition.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from oic.cdc_slice import GateDecision, digest, emit_transition_event, evaluate_test_transition


@dataclass(frozen=True, slots=True)
class MissionRunResult:
    """One synthetic procedure pass. Never an audit result."""

    procedure_id: str
    decision: str
    reason_code: str
    epistemic_state: str
    executed: bool
    prior_state: str
    resulting_state: str
    event: dict[str, Any] | None
    failure: str | None

    def as_record(self) -> dict[str, Any]:
        """A JSON-safe record of this pass, for evidence assembly."""
        return {
            "procedure_id": self.procedure_id,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "epistemic_state": self.epistemic_state,
            "executed": self.executed,
            "prior_state": self.prior_state,
            "resulting_state": self.resulting_state,
            "event_digest": digest(self.event) if self.event is not None else None,
            "failure": self.failure,
        }


@dataclass(slots=True)
class MissionLog:
    """Ordered record of one harness run across procedures."""

    run_id: str
    results: list[MissionRunResult] = field(default_factory=list)

    def as_record(self) -> dict[str, Any]:
        """A JSON-safe record of the whole run."""
        return {
            "run_id": self.run_id,
            "procedures": [result.as_record() for result in self.results],
        }


def run_procedure(
    procedure_id: str,
    proposal: Mapping[str, Any],
    registry: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> MissionRunResult:
    """Drive one procedure through the slice contract exactly once.

    The state transition is applied only on ALLOW. On DENY or ESCALATE the prior
    institutional state is returned unchanged, which is the behaviour the
    failure-preserving-availability probe is looking for.
    """
    prior_state = str(proposal.get("prior_institutional_state"))
    try:
        decision: GateDecision = evaluate_test_transition(proposal, registry)
    except Exception as error:
        return MissionRunResult(
            procedure_id=procedure_id,
            decision="COMPONENT_FAILURE",
            reason_code="GATE_RAISED",
            epistemic_state="UNRESOLVED_CANNOT",
            executed=False,
            prior_state=prior_state,
            resulting_state=prior_state,
            event=None,
            failure=f"{type(error).__name__}: {error}",
        )

    if decision.decision != "ALLOW":
        return MissionRunResult(
            procedure_id=procedure_id,
            decision=decision.decision,
            reason_code=decision.reason_code,
            epistemic_state=decision.epistemic_state,
            executed=False,
            prior_state=prior_state,
            resulting_state=prior_state,
            event=None,
            failure=None,
        )

    try:
        event = emit_transition_event(proposal, decision, event_metadata=metadata)
    except Exception as error:
        return MissionRunResult(
            procedure_id=procedure_id,
            decision=decision.decision,
            reason_code=decision.reason_code,
            epistemic_state=decision.epistemic_state,
            executed=False,
            prior_state=prior_state,
            resulting_state=prior_state,
            event=None,
            failure=f"{type(error).__name__}: {error}",
        )

    return MissionRunResult(
        procedure_id=procedure_id,
        decision=decision.decision,
        reason_code=decision.reason_code,
        epistemic_state=decision.epistemic_state,
        executed=True,
        prior_state=prior_state,
        resulting_state=str(proposal["requested_new_institutional_state"]),
        event=event,
        failure=None,
    )
