"""Definitions for the seven mandatory adversarial probes, A-01..A-07.

Each probe is a *definition*: a named mutation or condition applied to a
conforming baseline, the boundary it targets, the artifacts that must be
observable, the side effects that are prohibited, and the state that must be
preserved. Definitions are data. Nothing here evaluates anything, so importing
this module runs no probe and increments no denominator.

Defining seven probes is not measuring seven probes:

``ADVERSARIAL_PROBES_DEFINED = 7`` · ``ADVERSARIAL_PROBES_EXECUTED = 0``
``ADVERSARIAL_DENOMINATOR = 0``

Refusal, unresolved state and blocked transition are the expected outcomes and
are never normalised to PASS. An executed ALLOW under a probe would be a finding
against the slice, not a success.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Final

Mutation = Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class AdversarialProbe:
    """One mandatory probe definition."""

    probe_id: str
    mandatory_case: str
    s_case: str
    oracle_case: str
    mutation_or_condition: str
    target_boundary: str
    observable_artifacts: tuple[str, ...]
    prohibited_side_effects: tuple[str, ...]
    required_preservation: tuple[str, ...]
    permitted_decisions: frozenset[str]
    mutate: Mutation


def _drop_evidence(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = deepcopy(registry)
    registry["evidence"] = {}
    return proposal, registry


def _contradict_evidence(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = deepcopy(registry)
    for bundle in registry["evidence"].values():
        bundle["observations"].append({"fact": "publication_window_days", "value": 3})
    return proposal, registry


def _drop_admission(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = deepcopy(registry)
    registry["admissions"] = {}
    return proposal, registry


def _out_of_scope_reviewer(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    proposal = deepcopy(proposal)
    proposal["reviewer_id"] = "TEST-REVIEWER-OUT-OF-SCOPE-001"
    proposal["authority_scope_ref"] = "CDC-TEST-MISSION-999/TEST-REVIEWER"
    return proposal, registry


def _mutate_candidate(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = deepcopy(registry)
    for candidate in registry["candidates"].values():
        candidate["epistemic_state"] = "TAMPERED"
    return proposal, registry


def _supersede_predecessor(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = deepcopy(registry)
    registry["stale_candidate_ids"] = (proposal["candidate_id"],)
    return proposal, registry


def _remove_warrant_class(
    proposal: dict[str, Any], registry: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    proposal = deepcopy(proposal)
    registry = deepcopy(registry)
    proposal.pop("ZTL_warrant_ref", None)
    proposal.pop("ZTL_warrant_digest", None)
    registry["warrants"] = {}
    registry["fallback_warrants"] = {}
    return proposal, registry


_COMMON_PROHIBITED: Final[tuple[str, ...]] = (
    "institutional state transition executed",
    "VEIP transition event emitted",
    "candidate promoted to a relied-upon output",
    "implicit fallback substituted for the missing artifact",
    "prior institutional state overwritten or lost",
)

_COMMON_PRESERVED: Final[tuple[str, ...]] = (
    "prior institutional state",
    "input digests",
    "reason code",
    "epistemic state",
)

PROBES: Final[tuple[AdversarialProbe, ...]] = (
    AdversarialProbe(
        probe_id="A-01",
        mandatory_case="missing evidence",
        s_case="S-02",
        oracle_case="ORACLE-CASE-S-02",
        mutation_or_condition="required evidence object removed from the run snapshot",
        target_boundary="evidence binding resolution",
        observable_artifacts=("gate decision", "reason code", "epistemic state"),
        prohibited_side_effects=_COMMON_PROHIBITED,
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"ESCALATE", "DENY"}),
        mutate=_drop_evidence,
    ),
    AdversarialProbe(
        probe_id="A-02",
        mandatory_case="contradictory evidence",
        s_case="S-06",
        oracle_case="ORACLE-CASE-S-06",
        mutation_or_condition="mutually inconsistent observations added after digest binding",
        target_boundary="evidence digest binding and CANNOT handling",
        observable_artifacts=("gate decision", "reason code", "epistemic state"),
        prohibited_side_effects=_COMMON_PROHIBITED,
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"DENY", "ESCALATE"}),
        mutate=_contradict_evidence,
    ),
    AdversarialProbe(
        probe_id="A-03",
        mandatory_case="missing source/admission provenance",
        s_case="S-03",
        oracle_case="ORACLE-CASE-S-03",
        mutation_or_condition="admission record carrying source provenance removed",
        target_boundary="admission binding resolution",
        observable_artifacts=("gate decision", "reason code", "epistemic state"),
        prohibited_side_effects=_COMMON_PROHIBITED,
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"ESCALATE", "DENY"}),
        mutate=_drop_admission,
    ),
    AdversarialProbe(
        probe_id="A-04",
        mandatory_case="unauthorized reviewer",
        s_case="S-04",
        oracle_case="ORACLE-CASE-S-04",
        mutation_or_condition="reviewer asserts a scope outside the mission-scoped standing",
        target_boundary="authority scope check",
        observable_artifacts=("gate decision", "reason code", "declared scope"),
        prohibited_side_effects=_COMMON_PROHIBITED,
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"DENY"}),
        mutate=_out_of_scope_reviewer,
    ),
    AdversarialProbe(
        probe_id="A-05",
        mandatory_case="candidate/evidence mutation",
        s_case="S-05",
        oracle_case="ORACLE-CASE-S-05",
        mutation_or_condition="bound candidate altered after the proposal captured its digest",
        target_boundary="candidate digest recomputation",
        observable_artifacts=("gate decision", "reason code", "recomputed digest"),
        prohibited_side_effects=_COMMON_PROHIBITED,
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"DENY"}),
        mutate=_mutate_candidate,
    ),
    AdversarialProbe(
        probe_id="A-06",
        mandatory_case="correction/supersession",
        s_case="S-07",
        oracle_case="ORACLE-CASE-S-07",
        mutation_or_condition="candidate marked stale by a correction issued beforehand",
        target_boundary="staleness and supersession check",
        observable_artifacts=("gate decision", "reason code", "predecessor reference"),
        prohibited_side_effects=(
            *_COMMON_PROHIBITED,
            "predecessor mutated rather than superseded",
        ),
        required_preservation=(*_COMMON_PRESERVED, "predecessor byte-preserved and addressable"),
        permitted_decisions=frozenset({"DENY"}),
        mutate=_supersede_predecessor,
    ),
    AdversarialProbe(
        probe_id="A-07",
        mandatory_case="component failure / no implicit fallback",
        s_case="S-08",
        oracle_case="ORACLE-CASE-S-08",
        mutation_or_condition="warrant class removed entirely; no substitute artifact offered",
        target_boundary="warrant class resolution and fallback prohibition",
        observable_artifacts=("gate decision", "reason code", "epistemic state"),
        prohibited_side_effects=(
            *_COMMON_PROHIBITED,
            "fallback warrant synthesised in place of the absent ZTL warrant",
        ),
        required_preservation=_COMMON_PRESERVED,
        permitted_decisions=frozenset({"ESCALATE", "DENY"}),
        mutate=_remove_warrant_class,
    ),
)

PROBE_IDS: Final = tuple(probe.probe_id for probe in PROBES)
MANDATORY_CASES: Final = tuple(probe.mandatory_case for probe in PROBES)

ADVERSARIAL_PROBES_DEFINED: Final = len(PROBES)
ADVERSARIAL_PROBES_EXECUTED: Final = 0
ADVERSARIAL_DENOMINATOR: Final = 0


def probe_definitions() -> list[dict[str, Any]]:
    """JSON-safe probe definitions, for the evidence package and review."""
    return [
        {
            "probe_id": probe.probe_id,
            "mandatory_case": probe.mandatory_case,
            "s_case": probe.s_case,
            "oracle_case": probe.oracle_case,
            "mutation_or_condition": probe.mutation_or_condition,
            "target_boundary": probe.target_boundary,
            "observable_artifacts": list(probe.observable_artifacts),
            "prohibited_side_effects": list(probe.prohibited_side_effects),
            "required_preservation": list(probe.required_preservation),
            "permitted_decisions": sorted(probe.permitted_decisions),
            "executed": False,
            "observed_outcome": "NOT_YET_OBSERVED",
        }
        for probe in PROBES
    ]
