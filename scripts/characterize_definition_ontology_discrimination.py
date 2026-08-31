#!/usr/bin/env python3
"""Definition Ontology Discrimination 001.

A bounded paired experiment testing one explanation of the Interpretation Proposal
Characterization result: the model may recognize constitutive definitions structurally
while not treating CONSTITUTIVE_DEFINITION as a value of the field named
``normative_force``.

This instrument does not revise the Institutional IR ontology. It changes no production
code. It supplies no provisional unit type. Arm B differs from the frozen span-only Arm A
by one fixed ontology-clarification block and nothing else.

Offline is the default. ``--live`` constructs the NVIDIA provider and executes the frozen
36-request plan exactly once, with no retry and no in-process pacing.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

WORK_ORDER: Final[str] = "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-001"
STARTING_SHA: Final[str] = "f060dc60620c5ee4f72be7846915b80872afa00f"

V2_INSTRUMENT = ROOT / "scripts/characterize_interpretation_proposal_unit_type_ab_v2.py"
SOURCE_CORPUS = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"
PRODUCTION_PATH = ROOT / "src/oic/interpretation_proposal.py"
PLAN_PATH = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-001/PLAN-v0.1.json"
)
FREEZE_PATH = (
    ROOT
    / "benchmarks/characterization/definition-ontology-discrimination-001/PLAN-FREEZE-v0.2.json"
)
RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts"
    / "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-001.json"
)

SOURCE_CORPUS_SHA256: Final[str] = (
    "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
)
PRODUCTION_SHA256: Final[str] = "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"
PLAN_SHA256: Final[str] = "eda5025fbdcb2a8ef4154930ef6e5a9794d0e472696c863639ef3b5cd617a4f3"

ARMS: Final[tuple[str, str]] = (
    "A_FROZEN_SPAN_ONLY",
    "B_ONTOLOGY_CLARIFIED_FORCE_LABEL",
)
SELECTED_SPECIMENS: Final[tuple[str, ...]] = (
    "IIR-005",
    "IIR-006",
    "IIR-023",
    "IIR-024",
    "IIR-027",
    "IIR-028",
)
PRIMARY_DEFINITIONS: Final[tuple[str, ...]] = ("IIR-005", "IIR-023", "IIR-024")
CONTROL_SPECIMENS: Final[tuple[str, ...]] = ("IIR-006", "IIR-027", "IIR-028")
RUNS_PER_SPECIMEN: Final[int] = 3
PLANNED_REQUESTS: Final[int] = 36
PROPOSER_ID: Final[str] = "oic-definition-ontology-discrimination-001"

ONTOLOGY_CLARIFICATION_BLOCK: Final[str] = (
    "\n\nONTOLOGY CLARIFICATION FOR THIS OUTPUT CONTRACT:\n"
    "The field name `normative_force` is used here for all six allowed institutional "
    "relation labels, not only deontic modalities. `CONSTITUTIVE_DEFINITION` is therefore "
    "the required `normative_force` label when, and only when, the literal proposition "
    "itself constitutes what a term means. This label is provisional description only: "
    "it does not establish authority or canonical institutional meaning. Infer it only "
    "from the proposition; do not infer or resolve anything from outside text."
)
_INSERTION_MARKER: Final[str] = "\n\nADMITTED PROPOSITION:"


@dataclass(frozen=True, slots=True)
class PlannedRequest:
    ordinal: int
    specimen_id: str
    run_index: int
    arm: str

    def to_json(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "specimen_id": self.specimen_id,
            "run_index": self.run_index,
            "arm": self.arm,
        }


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def load_v2() -> ModuleType:
    return _load_module("_oic_unit_type_ab_v2_for_definition_ontology", V2_INSTRUMENT)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    if not all(specimen_id in by_id for specimen_id in SELECTED_SPECIMENS):
        raise SystemExit("FAIL selected specimen missing from frozen corpus")
    selected = [by_id[specimen_id] for specimen_id in SELECTED_SPECIMENS]
    return {**corpus, "specimens": selected}


def build_plan(corpus: dict[str, Any]) -> tuple[PlannedRequest, ...]:
    scoped = selected_corpus(corpus)
    plan: list[PlannedRequest] = []
    ordinal = 1
    for specimen in scoped["specimens"]:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            order = ARMS if run_index % 2 else tuple(reversed(ARMS))
            for arm in order:
                plan.append(
                    PlannedRequest(
                        ordinal=ordinal,
                        specimen_id=specimen["specimen_id"],
                        run_index=run_index,
                        arm=arm,
                    )
                )
                ordinal += 1
    return tuple(plan)


def validate_plan(corpus: dict[str, Any], plan: Sequence[PlannedRequest]) -> None:
    scoped = selected_corpus(corpus)
    specimen_ids = [item["specimen_id"] for item in scoped["specimens"]]
    if tuple(specimen_ids) != SELECTED_SPECIMENS:
        raise ValueError("selected specimen order changed")
    if len(plan) != PLANNED_REQUESTS:
        raise ValueError("experiment must contain exactly 36 requests")
    if [item.ordinal for item in plan] != list(range(1, PLANNED_REQUESTS + 1)):
        raise ValueError("request ordinals must be contiguous")
    for specimen_id in SELECTED_SPECIMENS:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            pair = [
                item.arm
                for item in plan
                if item.specimen_id == specimen_id and item.run_index == run_index
            ]
            expected = list(ARMS if run_index % 2 else tuple(reversed(ARMS)))
            if pair != expected:
                raise ValueError(
                    f"invalid deterministic arm order for {specimen_id} run {run_index}"
                )


# Dynamic adapter boundary: the concrete binding type belongs to the frozen loaded module.
def _binding(v1: ModuleType, specimen: dict[str, Any]) -> Any:  # noqa: ANN401
    # Always use v0.1 Arm A binding: candidate span only, provisional_unit_type=None.
    return v1.binding_for(specimen, v1.ARMS[0])


def arm_a_user_prompt(v2: ModuleType, v1: ModuleType, specimen: dict[str, Any]) -> str:
    return v2.arm_a_user_prompt(_binding(v1, specimen))


def arm_b_user_prompt(v2: ModuleType, v1: ModuleType, specimen: dict[str, Any]) -> str:
    base = arm_a_user_prompt(v2, v1, specimen)
    if _INSERTION_MARKER not in base:
        raise SystemExit("FAIL production prompt no longer has expected insertion point")
    head, _, tail = base.partition(_INSERTION_MARKER)
    return f"{head}{ONTOLOGY_CLARIFICATION_BLOCK}{_INSERTION_MARKER}{tail}"


def user_prompt_for(v2: ModuleType, v1: ModuleType, specimen: dict[str, Any], arm: str) -> str:
    if arm == ARMS[0]:
        return arm_a_user_prompt(v2, v1, specimen)
    if arm == ARMS[1]:
        return arm_b_user_prompt(v2, v1, specimen)
    raise ValueError(f"unknown arm: {arm}")


def execute_plan(
    corpus: dict[str, Any],
    plan: Sequence[PlannedRequest],
    provider: Any,  # noqa: ANN401
    v2: ModuleType,
    v1: ModuleType,
) -> list[Any]:
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    attempts: list[Any] = []
    for item in plan:
        specimen = by_id[item.specimen_id]
        attempt = v1.Attempt(
            ordinal=item.ordinal,
            specimen_id=item.specimen_id,
            run_index=item.run_index,
            arm=item.arm,
            outcome="PROVIDER_ERROR",
        )
        try:
            result = v2.propose_with_prompt(
                binding=_binding(v1, specimen),
                user_prompt=user_prompt_for(v2, v1, specimen, item.arm),
                provider=provider,
                proposer_id=PROPOSER_ID,
            )
        except v2.ProposalBoundaryError as exc:
            attempt.outcome = "BOUNDARY_REJECTED"
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)
        except (v2.InterpretationProposalError, v2.ModelProviderError) as exc:
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)
        else:
            attempt.outcome = "ACCEPTED"
            attempt.proposal = result.proposal
            attempt.provider = result.provider
            attempt.model = result.model
            attempt.request_id = result.request_id
            attempt.raw_content_sha256 = result.raw_content_sha256
        attempts.append(attempt)
    return attempts


# Attempt is defined by the dynamically loaded frozen characterization instrument.
def _force_value(attempt: Any) -> str | None:  # noqa: ANN401
    if attempt.outcome != "ACCEPTED" or attempt.proposal is None:
        return None
    values = [
        assertion.get("proposed_value")
        for assertion in attempt.proposal.get("proposed_assertions", [])
        if assertion.get("slot") == "normative_force"
    ]
    value = values[0] if values else None
    return value if isinstance(value, str) else None


def _paired_cells(
    attempts: Sequence[Any],
    defects: dict[tuple[str, int, str], bool],
) -> dict[str, int]:
    counts: Counter[str] = Counter(
        {"A_ONLY_DEFECT": 0, "B_ONLY_DEFECT": 0, "BOTH_DEFECT": 0, "NEITHER_DEFECT": 0}
    )
    pairs = sorted({(item.specimen_id, item.run_index) for item in attempts})
    for specimen_id, run_index in pairs:
        a = defects[(specimen_id, run_index, ARMS[0])]
        b = defects[(specimen_id, run_index, ARMS[1])]
        if a and b:
            counts["BOTH_DEFECT"] += 1
        elif a:
            counts["A_ONLY_DEFECT"] += 1
        elif b:
            counts["B_ONLY_DEFECT"] += 1
        else:
            counts["NEITHER_DEFECT"] += 1
    return dict(counts)


# Historical attempt types are owned by the dynamically loaded frozen instrument.
def _historical_attempt(
    v1: ModuleType,
    item: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    return v1._original_attempt(item)


def _established(v1: ModuleType, corpus: dict[str, Any], attempts: Sequence[Any]) -> dict[str, Any]:
    specimens = v1.original.load_specimens(corpus, include_unit_type=False)
    return v1.original.metric_e_established_recall(
        specimens, [_historical_attempt(v1, item) for item in attempts]
    )


def _grounding(v1: ModuleType, corpus: dict[str, Any], attempts: Sequence[Any]) -> dict[str, Any]:
    specimens = v1.original.load_specimens(corpus, include_unit_type=False)
    return v1.original.metric_i_quote_grounding(
        specimens, [_historical_attempt(v1, item) for item in attempts]
    )


def decide(
    *,
    b_definition_correct: int,
    paired_primary_improvements: int,
    b_only_control_force_defects: int,
    definition_slots_no_decline: bool,
) -> str:
    if b_only_control_force_defects:
        return "REGRESSION"
    if (
        b_definition_correct >= 8
        and paired_primary_improvements >= 6
        and definition_slots_no_decline
    ):
        return "SUPPORTS_ONTOLOGY_CLARIFICATION"
    if 4 <= b_definition_correct <= 7:
        return "PARTIAL_SUPPORT"
    if b_definition_correct >= 8:
        return "INCONCLUSIVE_EFFECT"
    return "REFUTES_SIMPLE_ONTOLOGY_CLARIFICATION"


def analyze_attempts(
    corpus: dict[str, Any], attempts: Sequence[Any], v1: ModuleType
) -> dict[str, Any]:
    scoped = selected_corpus(corpus)
    expected_force = {
        item["specimen_id"]: item["gold"]["expected_force"] for item in scoped["specimens"]
    }

    per_arm: dict[str, Any] = {}
    for arm in ARMS:
        arm_attempts = [item for item in attempts if item.arm == arm]
        per_arm[arm] = {
            "established_slots": _established(v1, scoped, arm_attempts),
            "source_quote_grounding": _grounding(v1, scoped, arm_attempts),
            "provider_errors": sum(item.outcome == "PROVIDER_ERROR" for item in arm_attempts),
            "boundary_rejections": sum(
                item.outcome == "BOUNDARY_REJECTED" for item in arm_attempts
            ),
        }

    primary_attempts = [item for item in attempts if item.specimen_id in PRIMARY_DEFINITIONS]
    primary_defects: dict[tuple[str, int, str], bool] = {}
    primary_observations: list[dict[str, Any]] = []
    b_definition_correct = 0
    paired_primary_improvements = 0

    for item in primary_attempts:
        force = _force_value(item)
        correct = item.outcome == "ACCEPTED" and force == "CONSTITUTIVE_DEFINITION"
        if item.arm == ARMS[1] and correct:
            b_definition_correct += 1
        primary_defects[(item.specimen_id, item.run_index, item.arm)] = not correct
        primary_observations.append(
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "arm": item.arm,
                "outcome": item.outcome,
                "proposed_force": force,
                "correct": correct,
            }
        )

    for specimen_id in PRIMARY_DEFINITIONS:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            a_item = next(
                item
                for item in primary_attempts
                if item.specimen_id == specimen_id
                and item.run_index == run_index
                and item.arm == ARMS[0]
            )
            b_item = next(
                item
                for item in primary_attempts
                if item.specimen_id == specimen_id
                and item.run_index == run_index
                and item.arm == ARMS[1]
            )
            if (
                a_item.outcome == "ACCEPTED"
                and b_item.outcome == "ACCEPTED"
                and primary_defects[(specimen_id, run_index, ARMS[0])]
                and not primary_defects[(specimen_id, run_index, ARMS[1])]
            ):
                paired_primary_improvements += 1

    control_attempts = [item for item in attempts if item.specimen_id in CONTROL_SPECIMENS]
    control_defects: dict[tuple[str, int, str], bool] = {}
    control_observations: list[dict[str, Any]] = []
    for item in control_attempts:
        force = _force_value(item)
        correct = item.outcome == "ACCEPTED" and force == expected_force[item.specimen_id]
        control_defects[(item.specimen_id, item.run_index, item.arm)] = not correct
        control_observations.append(
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "arm": item.arm,
                "expected_force": expected_force[item.specimen_id],
                "outcome": item.outcome,
                "proposed_force": force,
                "correct": correct,
            }
        )

    b_only_control_force_defects = 0
    b_only_control_instances: list[dict[str, Any]] = []
    for specimen_id in CONTROL_SPECIMENS:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            a = control_defects[(specimen_id, run_index, ARMS[0])]
            b = control_defects[(specimen_id, run_index, ARMS[1])]
            if b and not a:
                b_only_control_force_defects += 1
                b_only_control_instances.append(
                    {"specimen_id": specimen_id, "run_index": run_index}
                )

    a_slots = per_arm[ARMS[0]]["established_slots"]["per_slot"]
    b_slots = per_arm[ARMS[1]]["established_slots"]["per_slot"]
    definition_slots_no_decline = all(
        b_slots[slot]["proposed_compatible"] >= a_slots[slot]["proposed_compatible"]
        for slot in ("definiendum", "definiens")
    )

    disposition = decide(
        b_definition_correct=b_definition_correct,
        paired_primary_improvements=paired_primary_improvements,
        b_only_control_force_defects=b_only_control_force_defects,
        definition_slots_no_decline=definition_slots_no_decline,
    )

    return {
        "per_arm": per_arm,
        "primary_definition_force": {
            "observations": primary_observations,
            "paired_cells": _paired_cells(primary_attempts, primary_defects),
            "b_correct_planned_denominator": {
                "correct": b_definition_correct,
                "planned": 9,
            },
            "paired_primary_improvements_b_over_a": paired_primary_improvements,
        },
        "control_force": {
            "observations": control_observations,
            "paired_cells": _paired_cells(control_attempts, control_defects),
            "b_only_force_defect_count": b_only_control_force_defects,
            "b_only_force_defect_instances": b_only_control_instances,
        },
        "definition_slots_no_decline": definition_slots_no_decline,
        "disposition": disposition,
        "descriptive_only": True,
        "architectural_change_authorized": False,
    }


def preflight(v2: ModuleType, v1: ModuleType) -> dict[str, Any]:
    if sha256(SOURCE_CORPUS) != SOURCE_CORPUS_SHA256:
        raise SystemExit("FAIL frozen source corpus digest mismatch")
    if sha256(PRODUCTION_PATH) != PRODUCTION_SHA256:
        raise SystemExit("FAIL production proposal seam changed")
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise SystemExit("FAIL frozen discrimination plan digest mismatch")

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze["plan_sha256"] != PLAN_SHA256:
        raise SystemExit("FAIL plan freeze digest mismatch")

    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))
    materialized = build_plan(corpus)
    validate_plan(corpus, materialized)
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if [item.to_json() for item in materialized] != plan["request_plan"]:
        raise SystemExit("FAIL request plan differs from deterministic materialization")

    for specimen in selected_corpus(corpus)["specimens"]:
        a = arm_a_user_prompt(v2, v1, specimen)
        b = arm_b_user_prompt(v2, v1, specimen)
        if ONTOLOGY_CLARIFICATION_BLOCK in a:
            raise SystemExit("FAIL ontology clarification leaked into Arm A")
        if b.replace(ONTOLOGY_CLARIFICATION_BLOCK, "", 1) != a:
            raise SystemExit("FAIL Arm B differs from Arm A by more than one clarification block")
        if b.count(ONTOLOGY_CLARIFICATION_BLOCK) != 1:
            raise SystemExit("FAIL Arm B must contain exactly one clarification block")

    return plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="execute the preregistered 36-request paired run; owner-only",
    )
    args = parser.parse_args(argv)

    v2 = load_v2()
    v1 = v2.load_v1()
    plan = preflight(v2, v1)

    print(f"PASS frozen definition-ontology plan verified; {plan['planned_requests']} requests")
    print("Arm A: exact frozen span-only prompt")
    print("Arm B: Arm A plus one fixed ontology-clarification block; no unit_type supplied")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    from oic.nvidia_nim import NvidiaNimProvider

    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))
    request_plan = build_plan(corpus)
    validate_plan(corpus, request_plan)
    attempts = execute_plan(corpus, request_plan, NvidiaNimProvider(), v2, v1)
    analysis = analyze_attempts(corpus, attempts, v1)

    receipt = {
        "work_order": WORK_ORDER,
        "starting_sha": STARTING_SHA,
        "plan_sha256": PLAN_SHA256,
        "production_interpretation_proposal_sha256": PRODUCTION_SHA256,
        "attempts": [item.to_json() for item in attempts],
        "analysis": analysis,
        "live_run_executed": True,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"receipt written: {RECEIPT_PATH}")
    print(f"disposition: {analysis['disposition']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
