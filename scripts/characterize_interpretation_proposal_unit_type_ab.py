#!/usr/bin/env python3
"""Preregister the span-only versus provisional-unit-type interpretation A/B.

Offline by default.  The instrument reuses the frozen 29-specimen Characterization 001
corpus and the existing optional ``provisional_unit_type`` production path.  It changes no
prompt text.  ``--live`` is reserved for the owner; this work order only freezes the plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import audit_interpretation_proposal_postrun as corrected  # noqa: E402
import characterize_interpretation_proposal as original  # noqa: E402

from oic.interpretation_proposal import (  # noqa: E402
    AdmittedCandidateBinding,
    InterpretationProposalError,
    ProposalBoundaryError,
    propose_interpretation,
)
from oic.model_provider import ModelProvider, ModelProviderError  # noqa: E402

WORK_ORDER: Final[str] = "OIC-INTERPRETATION-PROPOSAL-UNIT-TYPE-AB-001"
STARTING_SHA: Final[str] = "20399bd98b2702b077c0874d36fce7f3fbb45a7f"
SOURCE_CORPUS = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"
PLAN_DIR = ROOT / "benchmarks/characterization/interpretation-proposal-unit-type-ab-001"
PLAN_PATH = PLAN_DIR / "PLAN-v0.1.json"
FREEZE_PATH = PLAN_DIR / "PLAN-FREEZE-v0.1.json"
RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts"
    / "OIC-INTERPRETATION-PROPOSAL-UNIT-TYPE-AB-001.json"
)

SOURCE_CORPUS_SHA256: Final[str] = (
    "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
)
PRODUCTION_INTERPRETATION_SHA256: Final[str] = (
    "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"
)
RUNS_PER_SPECIMEN: Final[int] = 3
ARMS: Final[tuple[str, str]] = ("A_SPAN_ONLY", "B_SPAN_PLUS_PROVISIONAL_UNIT_TYPE")
PLANNED_REQUESTS: Final[int] = 174
PROPOSER_ID: Final[str] = "oic-interpretation-proposer-unit-type-ab-001"

DEFINITION_SPECIMENS: Final[tuple[str, ...]] = ("IIR-005", "IIR-023", "IIR-024")
REGRESSION_SENTINELS: Final[tuple[str, ...]] = (
    "IIR-004",
    "IIR-027",
    "IIR-003",
    "IIR-028",
    "IIR-006",
    "IIR-015",
    "IIR-016",
    "IIR-017",
    "IIR-018",
    "IIR-029",
    "IIR-030",
    "IIR-031",
    "IIR-032",
    "IIR-035",
)

CORRECTED_METRICS: Final[tuple[str, ...]] = (
    "force_paired_outcomes",
    "definition_force_paired_outcomes",
    "unsupported_semantic_assignments",
    "wrong_role_assignments",
    "established_slot_compatibility",
    "bearer_counterparty_swaps",
    "material_omissions",
    "material_wrong_slot_placements",
    "threshold_comparator_loss",
    "exception_preservation",
    "condition_preservation",
    "source_quote_grounding",
    "unresolved_reference_surfacing_and_kind",
    "semantic_strengthening_instances",
    "ambiguity_collapse",
    "semantic_hash_stability",
    "slot_set_stability",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


@dataclass(slots=True)
class Attempt:
    ordinal: int
    specimen_id: str
    run_index: int
    arm: str
    outcome: str
    proposal: dict[str, Any] | None = None
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None
    raw_content_sha256: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "specimen_id": self.specimen_id,
            "run_index": self.run_index,
            "arm": self.arm,
            "outcome": self.outcome,
            "proposal": self.proposal,
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "raw_content_sha256": self.raw_content_sha256,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def build_plan(corpus: dict[str, Any]) -> tuple[PlannedRequest, ...]:
    plan: list[PlannedRequest] = []
    ordinal = 1
    for specimen in corpus["specimens"]:
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
    specimen_ids = [item["specimen_id"] for item in corpus["specimens"]]
    if len(specimen_ids) != 29 or len(set(specimen_ids)) != 29:
        raise ValueError("the A/B must carry exactly the 29 distinct frozen specimens")
    if len(plan) != PLANNED_REQUESTS:
        raise ValueError("the A/B must contain exactly 174 planned requests")
    if [item.ordinal for item in plan] != list(range(1, PLANNED_REQUESTS + 1)):
        raise ValueError("request ordinals must be contiguous")
    for specimen_id in specimen_ids:
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


def binding_for(specimen: dict[str, Any], arm: str) -> AdmittedCandidateBinding:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    candidate = specimen["candidate"]
    admission = specimen["admission"]
    return AdmittedCandidateBinding(
        admission_receipt_id=admission["admission_receipt_id"],
        admission_state=admission["admission_state"],
        candidate_unit_id=admission["candidate_unit_id"],
        candidate_projection_digest=admission["candidate_projection_digest"],
        candidate_span=candidate["candidate_span"],
        provisional_unit_type=(
            candidate["unit_type"] if arm == "B_SPAN_PLUS_PROVISIONAL_UNIT_TYPE" else None
        ),
    )


def execute_plan(
    corpus: dict[str, Any], plan: Sequence[PlannedRequest], provider: ModelProvider
) -> list[Attempt]:
    """Execute exactly one call per plan entry, with no retry and no in-process pacing."""
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    attempts: list[Attempt] = []
    for item in plan:
        attempt = Attempt(
            ordinal=item.ordinal,
            specimen_id=item.specimen_id,
            run_index=item.run_index,
            arm=item.arm,
            outcome="PROVIDER_ERROR",
        )
        try:
            result = propose_interpretation(
                binding=binding_for(by_id[item.specimen_id], item.arm),
                provider=provider,
                proposer_id=PROPOSER_ID,
            )
        except ProposalBoundaryError as exc:
            attempt.outcome = "BOUNDARY_REJECTED"
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)
        except (InterpretationProposalError, ModelProviderError) as exc:
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


def paired_outcomes(
    attempts: Sequence[Attempt], defect: dict[tuple[str, int, str], bool]
) -> dict[str, int]:
    counts: Counter[str] = Counter(
        {"A_ONLY_DEFECT": 0, "B_ONLY_DEFECT": 0, "BOTH_DEFECT": 0, "NEITHER_DEFECT": 0}
    )
    pairs = {(item.specimen_id, item.run_index) for item in attempts}
    for specimen_id, run_index in pairs:
        a = defect[(specimen_id, run_index, ARMS[0])]
        b = defect[(specimen_id, run_index, ARMS[1])]
        if a and b:
            counts["BOTH_DEFECT"] += 1
        elif a:
            counts["A_ONLY_DEFECT"] += 1
        elif b:
            counts["B_ONLY_DEFECT"] += 1
        else:
            counts["NEITHER_DEFECT"] += 1
    return dict(counts)


def _original_attempt(item: Attempt) -> original.Attempt:
    return original.Attempt(
        specimen_id=item.specimen_id,
        run_index=item.run_index,
        outcome=item.outcome,
        proposal=item.proposal,
        provider=item.provider,
        model=item.model,
        request_id=item.request_id,
        raw_content_sha256=item.raw_content_sha256,
        error_type=item.error_type,
        error_message=item.error_message,
    )


def _force_value(item: Attempt) -> str | None:
    if item.proposal is None:
        return None
    force = [
        assertion.get("proposed_value")
        for assertion in item.proposal.get("proposed_assertions", [])
        if assertion.get("slot") == "normative_force"
    ]
    return force[0] if force and isinstance(force[0], str) else None


def analyze_attempts(corpus: dict[str, Any], attempts: Sequence[Attempt]) -> dict[str, Any]:
    """Apply the preregistered corrected metrics without repairing either arm."""
    specimens_by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    specimen_objects = original.load_specimens(corpus, include_unit_type=False)
    per_arm: dict[str, Any] = {}
    for arm in ARMS:
        arm_attempts = [item for item in attempts if item.arm == arm]
        historical_shape = [_original_attempt(item) for item in arm_attempts]
        raw_shape = [item.to_json() for item in arm_attempts if item.outcome == "ACCEPTED"]
        per_arm[arm] = {
            "force": original.metric_c_force(specimen_objects, historical_shape),
            "established_slots": original.metric_e_established_recall(
                specimen_objects, historical_shape
            ),
            "bearer_counterparty": original.metric_g_role_separation(
                specimen_objects, historical_shape
            ),
            "material_qualifiers": original.metric_h_material_preservation(
                specimen_objects, historical_shape
            ),
            "source_quote_grounding": original.metric_i_quote_grounding(
                specimen_objects, historical_shape
            ),
            "quote_role_support": original.metric_j_quote_support(
                specimen_objects, historical_shape
            ),
            "references": original.metric_k_reference_recall(specimen_objects, historical_shape),
            "repeat_stability": original.metric_m_repeat_stability(
                specimen_objects, historical_shape
            ),
            "corrected_ambiguity": corrected.rescore_ambiguity(specimens_by_id, raw_shape),
            "corrected_semantic_assignments": corrected.audit_assignments(
                specimens_by_id, raw_shape
            ),
            "corrected_strengthening": corrected.audit_strengthening(specimens_by_id, raw_shape),
        }

    definition_observations: list[dict[str, Any]] = []
    definition_defect: dict[tuple[str, int, str], bool] = {}
    for item in attempts:
        if item.specimen_id not in DEFINITION_SPECIMENS:
            continue
        force = _force_value(item)
        if force == "CONSTITUTIVE_DEFINITION":
            category = "CONSTITUTIVE_DEFINITION_PROPOSED"
        elif force is None:
            category = "FORCE_OMITTED"
        else:
            category = "OTHER_FORCE_PROPOSED"
        definition_observations.append(
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "arm": item.arm,
                "category": category,
                "proposed_force": force,
            }
        )
        definition_defect[(item.specimen_id, item.run_index, item.arm)] = (
            category != "CONSTITUTIVE_DEFINITION_PROPOSED"
        )

    return {
        "per_arm": per_arm,
        "definition_primary_diagnostic": definition_observations,
        "definition_paired_defect_cells": paired_outcomes(
            [item for item in attempts if item.specimen_id in DEFINITION_SPECIMENS],
            definition_defect,
        ),
        "descriptive_only": True,
        "architectural_decision_made": False,
    }


def build_offline_plan() -> dict[str, Any]:
    if sha256(SOURCE_CORPUS) != SOURCE_CORPUS_SHA256:
        raise SystemExit("FAIL frozen Characterization 001 corpus digest mismatch")
    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))
    plan = build_plan(corpus)
    validate_plan(corpus, plan)
    definition = [item.to_json() for item in plan if item.specimen_id in DEFINITION_SPECIMENS]
    return {
        "work_order": WORK_ORDER,
        "starting_sha": STARTING_SHA,
        "source_corpus_path": SOURCE_CORPUS.relative_to(ROOT).as_posix(),
        "source_corpus_sha256": SOURCE_CORPUS_SHA256,
        "specimen_count": 29,
        "runs_per_specimen": RUNS_PER_SPECIMEN,
        "arms": {
            ARMS[0]: {
                "inputs": ["candidate_span"],
                "description": "exact Characterization 001 behavior",
            },
            ARMS[1]: {
                "inputs": ["candidate_span", "provisional_unit_type"],
                "description": (
                    "same production prompt plus the existing explicitly provisional, "
                    "untrusted, non-authoritative and possibly wrong earlier-stage hint"
                ),
            },
        },
        "only_experimental_difference": "presence of provisional_unit_type",
        "planned_requests": PLANNED_REQUESTS,
        "retry_policy": "none; exactly one provider call per planned request",
        "pacing": "external client only; recommended 4 seconds after every request",
        "interleaving": "odd run A then B; even run B then A within each specimen/run pair",
        "request_plan": [item.to_json() for item in plan],
        "definition_primary_diagnostic": {
            "specimen_ids": list(DEFINITION_SPECIMENS),
            "observations": definition,
            "observation_count": len(definition),
            "report_categories": [
                "CONSTITUTIVE_DEFINITION_PROPOSED",
                "FORCE_OMITTED",
                "OTHER_FORCE_PROPOSED",
            ],
        },
        "regression_sentinels": list(REGRESSION_SENTINELS),
        "corrected_paired_metrics": list(CORRECTED_METRICS),
        "paired_defect_cells": [
            "A_ONLY_DEFECT",
            "B_ONLY_DEFECT",
            "BOTH_DEFECT",
            "NEITHER_DEFECT",
        ],
        "live_run_executed": False,
        "model_call_made": False,
        "production_prompt_changed": False,
        "canonicalization_implemented": False,
        "institutional_ir_runtime_implemented": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
        "claim_ceiling": (
            "A preregistered experiment isolating one prompt-input factor only; no semantic "
            "correctness, canonical meaning, model authority, production readiness, cross-model "
            "generalization, canonicalization, Institutional IR runtime, legal interpretation, "
            "or independent validation is established."
        ),
    }


def preflight() -> dict[str, Any]:
    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit("FAIL frozen A/B plan digest mismatch")
    plan: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if plan != build_offline_plan():
        raise SystemExit("FAIL frozen A/B plan differs from deterministic materialization")
    return plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    plan_document = preflight()
    print(f"PASS frozen paired plan verified; {plan_document['planned_requests']} requests")
    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    from oic.nvidia_nim import NvidiaNimProvider

    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))
    plan = build_plan(corpus)
    attempts = execute_plan(corpus, plan, NvidiaNimProvider())
    receipt = {
        **plan_document,
        "live_run_executed": True,
        "model_call_made": True,
        "attempts": [item.to_json() for item in attempts],
        "analysis": analyze_attempts(corpus, attempts),
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"receipt written: {RECEIPT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
