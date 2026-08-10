"""Raw observation records for the CDC vertical slice.

An observation is what was *seen*. It is not a judgement about whether what was
seen was correct. The three axes are kept separate on purpose, because
collapsing them is how an operational success quietly becomes an institutional
one:

* ``epistemic``     — what is known or unresolved about the claim
* ``operational``   — what the machinery did
* ``institutional`` — what state the institution is in

This module deliberately defines **no** ``adjudication`` field. Observation and
adjudication are different artifacts produced by different parties. Nothing here
compares an observation to the oracle.

Nothing executes at import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from oic.cdc_slice import digest

SCHEMA_VERSION: Final = "CDC-SLICE-OBSERVATION-v0.1"

NOT_YET_OBSERVED: Final = "NOT_YET_OBSERVED"

EPISTEMIC_STATES: Final = frozenset(
    {
        "SUPPORTED",
        "UNSUPPORTED",
        "UNRESOLVED",
        "UNRESOLVED_CANNOT",
        "NOT_ADJUDICATED",
        NOT_YET_OBSERVED,
    }
)
OPERATIONAL_STATES: Final = frozenset(
    {"COMPLETED", "REFUSED", "BLOCKED", "COMPONENT_FAILURE", NOT_YET_OBSERVED}
)
INSTITUTIONAL_STATES: Final = frozenset(
    {
        "CANDIDATE_FORMED",
        "ACCEPTED_CANDIDATE",
        "QUALIFIED",
        "DISMISSED",
        "EVIDENCE_REQUESTED",
        "ESCALATED",
        "DEFERRED",
        NOT_YET_OBSERVED,
    }
)


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    """One raw observation. Carries no verdict about its own correctness."""

    observation_id: str
    case_id: str
    run_id: str
    input_digests: dict[str, str]
    precondition_record: dict[str, Any]
    epistemic_state_observed: str
    operational_state_observed: str
    institutional_state_observed: str
    transition_executed: bool
    reason_codes: list[str] = field(default_factory=list)
    preserved_artifact_refs: list[str] = field(default_factory=list)
    failure_refs: list[str] = field(default_factory=list)
    side_effect_refs: list[str] = field(default_factory=list)
    raw_output_refs: list[str] = field(default_factory=list)

    def as_record(self) -> dict[str, Any]:
        """A JSON-safe observation, with its own digest bound last."""
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "case_id": self.case_id,
            "run_id": self.run_id,
            "input_digests": dict(sorted(self.input_digests.items())),
            "precondition_record": self.precondition_record,
            "epistemic_state_observed": self.epistemic_state_observed,
            "operational_state_observed": self.operational_state_observed,
            "institutional_state_observed": self.institutional_state_observed,
            "transition_executed": self.transition_executed,
            "reason_codes": list(self.reason_codes),
            "preserved_artifact_refs": list(self.preserved_artifact_refs),
            "failure_refs": list(self.failure_refs),
            "side_effect_refs": list(self.side_effect_refs),
            "raw_output_refs": list(self.raw_output_refs),
        }
        body["observation_digest"] = digest(body)
        return body


def unobserved(case_id: str) -> dict[str, Any]:
    """A placeholder observation for a case that has not run.

    Every runtime-result slot is explicitly ``NOT_YET_OBSERVED``. No empty string
    and no fabricated digest is used for evidence that does not exist yet.
    """
    return ObservationRecord(
        observation_id=f"OBS-{case_id}-NOT-YET-OBSERVED",
        case_id=case_id,
        run_id=NOT_YET_OBSERVED,
        input_digests={},
        precondition_record={"state": NOT_YET_OBSERVED},
        epistemic_state_observed=NOT_YET_OBSERVED,
        operational_state_observed=NOT_YET_OBSERVED,
        institutional_state_observed=NOT_YET_OBSERVED,
        transition_executed=False,
    ).as_record()


ADJUDICATION_FIELDS_PROHIBITED: Final = frozenset(
    {
        "adjudication",
        "MATCH",
        "SEMANTIC_VIOLATION",
        "FORBIDDEN_PROMOTION",
        "PASS",
        "FAIL",
        "INCOMPLETE",
    }
)


def assert_no_adjudication(record: dict[str, Any]) -> None:
    """Raise if an observation has acquired an adjudication verdict."""
    present = sorted(ADJUDICATION_FIELDS_PROHIBITED & set(record))
    if present:
        raise ValueError(f"observation carries adjudication fields: {present}")
