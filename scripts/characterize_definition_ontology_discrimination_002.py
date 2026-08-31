#!/usr/bin/env python3
"""Definition Ontology Discrimination 002.

Successor to 001 with one methodological change only: a provider-qualification
prerequisite and hard scientific adjudicability gate precede semantic adjudication.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

WORK_ORDER: Final[str] = "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002"
BASE_SHA: Final[str] = "c4a87eb8483c3bd965612b601399463e005bd73e"
SOURCE_001 = ROOT / "scripts/characterize_definition_ontology_discrimination.py"
PLAN_PATH = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-002/PLAN-v0.1.json"
)
FREEZE_PATH = (
    ROOT
    / "benchmarks/characterization/definition-ontology-discrimination-002/PLAN-FREEZE-v0.3.json"
)
QUALIFICATION_RECEIPT = (
    ROOT / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-002.json"
)
RECEIPT_PATH = (
    ROOT / ".local/interpretation-proposal-receipts/OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-002.json"
)
PLANNED_REQUESTS: Final[int] = 36
PACING_SECONDS: Final[float] = 4.0
ARMS: Final[tuple[str, str]] = ("A_FROZEN_SPAN_ONLY", "B_ONTOLOGY_CLARIFIED_FORCE_LABEL")
PRIMARY: Final[tuple[str, ...]] = ("IIR-005", "IIR-023", "IIR-024")
CONTROLS: Final[tuple[str, ...]] = ("IIR-006", "IIR-027", "IIR-028")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_oic_definition_ontology_001_source", SOURCE_001)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL cannot load frozen 001 source: {SOURCE_001}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def provider_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RECEIPT.exists():
        raise SystemExit(
            "STOP provider qualification 002 receipt absent; semantic execution unauthorized"
        )
    data: dict[str, Any] = json.loads(QUALIFICATION_RECEIPT.read_text(encoding="utf-8"))
    if data.get("work_order") != "OIC-NVIDIA-PROVIDER-QUALIFICATION-002":
        raise SystemExit("STOP wrong provider qualification receipt")
    if data.get("disposition") != "QUALIFIED":
        raise SystemExit("STOP provider qualification 002 is not QUALIFIED")
    if data.get("semantic_successor_authorized") is not True:
        raise SystemExit("STOP provider qualification 002 does not authorize semantic successor")
    return data


def pair_counts(attempts: Sequence[Any]) -> dict[str, int | bool]:
    accepted = [a for a in attempts if a.outcome == "ACCEPTED"]
    accepted_keys = {(a.specimen_id, a.run_index, a.arm) for a in accepted}
    all_pairs = {(a.specimen_id, a.run_index) for a in attempts}
    complete = sum(
        (sid, run, ARMS[0]) in accepted_keys and (sid, run, ARMS[1]) in accepted_keys
        for sid, run in all_pairs
    )
    primary_pairs = sum(
        (sid, run, ARMS[0]) in accepted_keys and (sid, run, ARMS[1]) in accepted_keys
        for sid in PRIMARY
        for run in range(1, 4)
    )
    control_pairs = sum(
        (sid, run, ARMS[0]) in accepted_keys and (sid, run, ARMS[1]) in accepted_keys
        for sid in CONTROLS
        for run in range(1, 4)
    )
    gate = (
        len(attempts) == PLANNED_REQUESTS
        and len(accepted) == PLANNED_REQUESTS
        and complete == 18
        and primary_pairs == 9
        and control_pairs == 9
    )
    return {
        "planned_observations": PLANNED_REQUESTS,
        "observed_attempts": len(attempts),
        "accepted_observations": len(accepted),
        "complete_ab_pairs": complete,
        "primary_complete_pairs": primary_pairs,
        "control_complete_pairs": control_pairs,
        "adjudicable": gate,
    }


def preflight(source: ModuleType) -> dict[str, Any]:
    if not SOURCE_001.exists():
        raise SystemExit("FAIL source 001 instrument missing")
    plan: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit("FAIL 002 plan digest mismatch")
    if plan["planned_requests"] != PLANNED_REQUESTS:
        raise SystemExit("FAIL planned request count drift")
    if plan["semantic_design_change_from_001"] is not False:
        raise SystemExit("FAIL 002 semantic design must remain unchanged from 001")
    v2 = source.load_v2()
    v1 = v2.load_v1()
    source.preflight(v2, v1)
    return plan


def execute_with_pacing(
    source: ModuleType,
    corpus: dict[str, Any],
    request_plan: Sequence[Any],
    provider: object,
    v2: ModuleType,
    v1: ModuleType,
) -> list[Any]:
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    attempts: list[Any] = []
    for index, item in enumerate(request_plan):
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
                binding=source._binding(v1, specimen),
                user_prompt=source.user_prompt_for(v2, v1, specimen, item.arm),
                provider=provider,
                proposer_id="oic-definition-ontology-discrimination-002",
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
        if index < len(request_plan) - 1:
            time.sleep(PACING_SECONDS)
    return attempts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    source = load_source()
    plan = preflight(source)
    print(f"PASS frozen 002 plan verified; {plan['planned_requests']} requests")
    print("semantic design versus 001: UNCHANGED")
    print("adjudicability gate: 36/36 ACCEPTED + all 18 A/B pairs complete")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    qualification = provider_prerequisite()
    if RECEIPT_PATH.exists():
        raise SystemExit(f"STOP receipt already exists: {RECEIPT_PATH}")

    from oic.nvidia_nim import NvidiaNimProvider

    v2 = source.load_v2()
    v1 = v2.load_v1()
    corpus = json.loads(source.SOURCE_CORPUS.read_text(encoding="utf-8"))
    request_plan = source.build_plan(corpus)
    source.validate_plan(corpus, request_plan)
    attempts = execute_with_pacing(source, corpus, request_plan, NvidiaNimProvider(), v2, v1)

    adjudicability = pair_counts(attempts)
    if adjudicability["adjudicable"]:
        analysis = source.analyze_attempts(corpus, attempts, v1)
        scientific_disposition = analysis["disposition"]
        semantic_analysis = analysis
    else:
        scientific_disposition = "NOT_ADJUDICABLE_PROVIDER_FAILURE"
        semantic_analysis = None

    receipt = {
        "work_order": WORK_ORDER,
        "starting_sha": BASE_SHA,
        "plan_sha256": sha256(PLAN_PATH),
        "provider_qualification_002_receipt_sha256": sha256(QUALIFICATION_RECEIPT),
        "provider_qualification_002_disposition": qualification["disposition"],
        "attempts": [item.to_json() for item in attempts],
        "adjudicability": adjudicability,
        "scientific_disposition": scientific_disposition,
        "semantic_analysis": semantic_analysis,
        "live_run_executed": True,
        "semantic_decision_rule_evaluated": bool(adjudicability["adjudicable"]),
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
    print(f"scientific disposition: {scientific_disposition}")
    print(f"semantic decision evaluated: {bool(adjudicability['adjudicable'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
