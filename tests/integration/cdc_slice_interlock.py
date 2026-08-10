"""Execution interlock for the CDC vertical slice.

A tooling interlock only. It creates no institutional authority and confers no
clearance. It exists so that a result-bearing entry point cannot be run by
accident from the preparation branch — a missing clearance record must produce a
refusal, never a default-permit.

Clearance is satisfied only by an owner-supplied *reference*, passed by
environment, naming an artifact this tooling does not create:

``CDC_SLICE_EXECUTION_CLEARANCE_REF=<owner clearance record reference>``

No fake reference is defined here, and none may be invented for tests. A test
proves the interlock by observing that it refuses, not by supplying a stub.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

CLEARANCE_ENV: Final = "CDC_SLICE_EXECUTION_CLEARANCE_REF"
INFRASTRUCTURE_ENV: Final = "CDC_SLICE_RESULT_BEARING"
# Not a secret: an explicit opt-in token, deliberately readable in source so that
# enabling result-bearing execution is visible rather than guessable.
INFRASTRUCTURE_TOKEN: Final = "PYTEST_INFRASTRUCTURE_RESOLVED"  # noqa: S105


class ExecutionNotAuthorizedError(RuntimeError):
    """Raised when a result-bearing entry point is invoked without clearance."""


@dataclass(frozen=True, slots=True)
class ClearanceState:
    """The observed interlock state. Reported, never assumed."""

    clearance_ref: str | None
    infrastructure_resolved: bool

    @property
    def execution_permitted(self) -> bool:
        """Both gates must be open. Neither implies the other."""
        return bool(self.clearance_ref) and self.infrastructure_resolved

    def as_record(self) -> dict[str, object]:
        """A JSON-safe record of the interlock state."""
        return {
            "execution_clearance_ref": self.clearance_ref or "ABSENT",
            "pytest_infrastructure": "RESOLVED" if self.infrastructure_resolved else "UNRESOLVED",
            "result_bearing_entrypoint": "PERMITTED" if self.execution_permitted else "BLOCKED",
        }


def observe_clearance() -> ClearanceState:
    """Read the interlock state from the environment without altering it."""
    ref = os.environ.get(CLEARANCE_ENV) or None
    resolved = os.environ.get(INFRASTRUCTURE_ENV) == INFRASTRUCTURE_TOKEN
    return ClearanceState(clearance_ref=ref, infrastructure_resolved=resolved)


def require_execution_clearance() -> ClearanceState:
    """Fail closed unless an owner clearance reference and resolved infra are both present."""
    state = observe_clearance()
    if not state.clearance_ref:
        raise ExecutionNotAuthorizedError(
            "EXECUTION_CLEARANCE_REF = ABSENT; RESULT_BEARING_ENTRYPOINT = BLOCKED. "
            "An owner execution-clearance reference is required and must not be invented."
        )
    if not state.infrastructure_resolved:
        raise ExecutionNotAuthorizedError(
            "PYTEST_INFRASTRUCTURE is not recorded as RESOLVED; "
            "RESULT_BEARING_ENTRYPOINT = BLOCKED."
        )
    return state
