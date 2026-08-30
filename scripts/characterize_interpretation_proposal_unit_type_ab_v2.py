#!/usr/bin/env python3
"""Unit-Type A/B 001A: the same experiment, with the hint made self-contained.

The v0.1 plan established all seven required hint properties across the standing system
prompt *plus* the inserted sentence. That is sound architecture and it is not what the
preregistration says. The contract requires the seven properties to be explicit in the
hint block itself, so a reader of the block alone can see that the hint is provisional,
untrusted, from an earlier stage, without authority, not canonical meaning, possibly
wrong, and subordinate to the literal admitted proposition.

This successor changes exactly one thing: the text of the Arm B hint block. Arm A stays
byte-identical to Characterization 001, the corpus, ordering, plan, metrics, provider
settings and production seam are untouched, and v0.1's plan and freeze remain exactly as
they were.

Where the hint comes from
-------------------------
``src/oic/interpretation_proposal.py`` must stay byte-identical, so the successor hint is
composed here rather than in production. Arm A is rendered by calling production's own
prompt builder, which makes its byte identity a fact of construction rather than a claim.
Arm B is that same string with one block inserted at the same point production would have
used. Everything after the prompt -- the system prompt, the structural boundary parser and
the envelope builder -- is production's, unchanged, so the proposal contract under test is
the same one Characterization 001 measured.

One reporting addition
----------------------
v0.1 computed paired defect cells for the definition diagnostic only. A regression that
appeared solely in Arm B on one of the fourteen sentinels would have been visible only
inside a per-arm aggregate. This instrument reports the paired cells per sentinel and
names every B-only instance, because a hint that buys definition recognition by breaking
role assignment somewhere else is the specific risk of feeding a prior model's guess
forward.

Nothing here canonicalizes, and no provider is constructed without ``--live``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.interpretation_proposal import (  # noqa: E402 - path prepared above
    _SYSTEM_PROMPT,
    AdmittedCandidateBinding,
    InterpretationProposalError,
    InterpretationProposalResult,
    ProposalBoundaryError,
    ProposalInputBoundaryError,
    _model_payload,
    _parse_payload,
    _user_prompt,
    build_proposal_envelope,
)
from oic.model_provider import (  # noqa: E402 - path prepared above
    ModelProvider,
    ModelProviderError,
    ModelRequest,
)

WORK_ORDER: Final[str] = "OIC-INTERPRETATION-PROPOSAL-UNIT-TYPE-AB-001A"
STARTING_SHA: Final[str] = "2f95a91f6109e858eecc840757878297706a18ea"
PLAN_VERSION: Final[str] = "v0.2"

PLAN_DIR = ROOT / "benchmarks/characterization/interpretation-proposal-unit-type-ab-001"
PLAN_V1_PATH = PLAN_DIR / "PLAN-v0.1.json"
PLAN_PATH = PLAN_DIR / "PLAN-v0.2.json"
FREEZE_PATH = PLAN_DIR / "PLAN-FREEZE-v0.2.json"
V1_INSTRUMENT_PATH = ROOT / "scripts/characterize_interpretation_proposal_unit_type_ab.py"
PRODUCTION_PATH = ROOT / "src/oic/interpretation_proposal.py"
RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts"
    / "OIC-INTERPRETATION-PROPOSAL-UNIT-TYPE-AB-001A.json"
)

#: The successor hint. Every one of the seven required properties is stated inside this
#: block, so the block is self-sufficient rather than leaning on the system prompt.
ARM_B_HINT_TEMPLATE: Final[str] = (
    "\n\nAn earlier stage proposed the provisional unit type {unit_type!r} for this "
    "proposition. This hint is untrusted, carries no authority, is not canonical "
    "institutional meaning, and may be wrong. The literal admitted proposition controls; "
    "where the hint conflicts with the source text, ignore the hint. Do not treat the "
    "hint as normative force or as a finding."
)

#: Each required property paired with the literal text that establishes it. The contract
#: test iterates this, so a future edit that drops a property fails rather than passes.
HINT_REQUIRED_PROPERTIES: Final[dict[str, str]] = {
    "provisional": "the provisional unit type",
    "untrusted": "This hint is untrusted",
    "produced_at_an_earlier_stage": "An earlier stage proposed",
    "not_authority": "carries no authority",
    "not_canonical_institutional_meaning": "is not canonical institutional meaning",
    "possibly_wrong": "and may be wrong",
    "subordinate_to_the_literal_admitted_source_text": (
        "The literal admitted proposition controls; where the hint conflicts with the "
        "source text, ignore the hint"
    ),
}

#: Production inserts its hint immediately before this marker; the successor uses the
#: same point so the only difference between arms stays the block itself.
_INSERTION_MARKER: Final[str] = "\n\nADMITTED PROPOSITION:"

#: A sentinel run counts as defective under the corrected Phase A definitions when any of
#: these appear. Preregistered so the live result cannot be scored a different way later.
SENTINEL_DEFECT_RULE: Final[tuple[str, ...]] = (
    "the attempt was not ACCEPTED",
    "any corrected strengthening instance for that run",
    "any UNGROUNDED_SOURCE_TEXT, UNSUPPORTED_SEMANTIC_ASSIGNMENT or WRONG_ROLE_ASSIGNMENT",
    "an AMBIGUOUS slot scored anything other than ALTERNATIVES_SEPARATELY_SURFACED",
)

_DEFECTIVE_ASSIGNMENTS: Final[frozenset[str]] = frozenset(
    {
        "UNGROUNDED_SOURCE_TEXT",
        "UNSUPPORTED_SEMANTIC_ASSIGNMENT",
        "WRONG_ROLE_ASSIGNMENT",
    }
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging failure
        raise SystemExit(f"FAIL cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def load_v1() -> ModuleType:
    """The frozen v0.1 instrument: plan, ordering, corrected metrics and analysis."""
    return _load_module("_oic_unit_type_ab_v1", V1_INSTRUMENT_PATH)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def arm_b_hint(unit_type: str) -> str:
    return ARM_B_HINT_TEMPLATE.format(unit_type=unit_type)


def arm_a_user_prompt(binding: AdmittedCandidateBinding) -> str:
    """Arm A, rendered by production's own builder.

    Byte identity with Characterization 001 is a fact of construction here, not an
    assertion: this calls the same function, with the hint path switched off.
    """
    if binding.provisional_unit_type is not None:
        raise ValueError("arm A must not carry a provisional unit type")
    return _user_prompt(binding)


def arm_b_user_prompt(binding: AdmittedCandidateBinding, unit_type: str) -> str:
    """Arm A's prompt with exactly one block inserted at production's insertion point."""
    base = arm_a_user_prompt(binding)
    if _INSERTION_MARKER not in base:
        raise SystemExit("FAIL production prompt no longer has the expected insertion point")
    head, _, tail = base.partition(_INSERTION_MARKER)
    return f"{head}{arm_b_hint(unit_type)}{_INSERTION_MARKER}{tail}"


def user_prompt_for(specimen: dict[str, Any], arm: str, v1: ModuleType) -> str:
    binding = v1.binding_for(specimen, v1.ARMS[0])
    if arm == v1.ARMS[0]:
        return arm_a_user_prompt(binding)
    if arm == v1.ARMS[1]:
        return arm_b_user_prompt(binding, specimen["candidate"]["unit_type"])
    raise ValueError(f"unknown arm: {arm}")


def propose_with_prompt(
    *,
    binding: AdmittedCandidateBinding,
    user_prompt: str,
    provider: ModelProvider,
    proposer_id: str,
) -> InterpretationProposalResult:
    """One proposal, with the user prompt supplied by the experiment.

    Identical to ``propose_interpretation`` in every respect except who composes the user
    prompt: the same non-ADMITTED refusal before any call, the same system prompt, the same
    provider settings, the same structural boundary parser, the same OIC-controlled
    envelope. Production is not modified, and the contract under test is unchanged.
    """
    if binding.admission_state != "ADMITTED":
        raise ProposalInputBoundaryError(
            "interpretation proposal requires an ADMITTED admission receipt; received "
            f"{binding.admission_state!r}. Nothing was proposed and no provider was called."
        )
    request = ModelRequest(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=4096,
    )
    response = provider.complete(request)
    assertions, references = _model_payload(_parse_payload(response.content))
    envelope = build_proposal_envelope(
        binding=binding,
        proposer_kind="MODEL",
        proposer_id=proposer_id,
        assertions=assertions,
        references=references,
    )
    return InterpretationProposalResult(
        proposal=envelope,
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
        raw_content_sha256=hashlib.sha256(response.content.encode()).hexdigest(),
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_plan(
    corpus: dict[str, Any],
    plan: Sequence[Any],
    provider: ModelProvider,
    v1: ModuleType,
) -> list[Any]:
    """Exactly one call per plan entry, no retry, no in-process pacing."""
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
            result = propose_with_prompt(
                binding=v1.binding_for(specimen, v1.ARMS[0]),
                user_prompt=user_prompt_for(specimen, item.arm, v1),
                provider=provider,
                proposer_id=v1.PROPOSER_ID,
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


# ---------------------------------------------------------------------------
# Sentinel paired reporting
# ---------------------------------------------------------------------------


def sentinel_run_is_defective(
    specimen: dict[str, Any],
    attempt: Any,  # noqa: ANN401 - the v0.1 Attempt type is loaded dynamically
    corrected: ModuleType,
) -> bool:
    """Apply the preregistered defect rule to one sentinel run.

    Every clause comes from the corrected Phase A definitions. Nothing is repaired and
    nothing is re-scored: the run either exhibits one of the named defects or it does not.
    """
    if attempt.outcome != "ACCEPTED" or attempt.proposal is None:
        return True
    specimens = {specimen["specimen_id"]: specimen}
    raw = [attempt.to_json()]
    if corrected.audit_strengthening(specimens, raw)["instances"]:
        return True
    assignments = corrected.audit_assignments(specimens, raw)["counts"]
    if any(assignments.get(category, 0) for category in _DEFECTIVE_ASSIGNMENTS):
        return True
    ambiguity = corrected.rescore_ambiguity(specimens, raw)["counts"]
    scored = sum(ambiguity.values())
    return bool(scored) and ambiguity.get("ALTERNATIVES_SEPARATELY_SURFACED", 0) != scored


def sentinel_paired_defects(
    corpus: dict[str, Any],
    attempts: Sequence[Any],
    v1: ModuleType,
    corrected: ModuleType,
) -> dict[str, Any]:
    """Paired cells per sentinel, plus every B-only instance by name.

    Reported per sentinel and instance by instance on purpose. A single total across the
    fourteen would let a regression the hint introduced cancel against an improvement
    elsewhere, and a per-arm aggregate would never show that the two arms disagreed on the
    same specimen and run at all.
    """
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    sentinels = [
        item
        for item in v1.REGRESSION_SENTINELS
        if item not in v1.DEFINITION_SPECIMENS and item in by_id
    ]
    per_sentinel: dict[str, Any] = {}
    b_only_instances: list[dict[str, Any]] = []
    a_only_instances: list[dict[str, Any]] = []

    for specimen_id in sentinels:
        specimen = by_id[specimen_id]
        relevant = [item for item in attempts if item.specimen_id == specimen_id]
        defect = {
            (item.specimen_id, item.run_index, item.arm): sentinel_run_is_defective(
                specimen, item, corrected
            )
            for item in relevant
        }
        per_sentinel[specimen_id] = v1.paired_outcomes(relevant, defect)
        for (_, run_index, arm), flagged in sorted(defect.items()):
            if not flagged or arm != v1.ARMS[1]:
                continue
            if not defect.get((specimen_id, run_index, v1.ARMS[0]), False):
                b_only_instances.append({"specimen_id": specimen_id, "run_index": run_index})
        for (_, run_index, arm), flagged in sorted(defect.items()):
            if not flagged or arm != v1.ARMS[0]:
                continue
            if not defect.get((specimen_id, run_index, v1.ARMS[1]), False):
                a_only_instances.append({"specimen_id": specimen_id, "run_index": run_index})

    return {
        "defect_rule": list(SENTINEL_DEFECT_RULE),
        "sentinels_reported": sentinels,
        "per_sentinel_paired_cells": per_sentinel,
        "b_only_defect_instances": b_only_instances,
        "a_only_defect_instances": a_only_instances,
        "b_only_defect_count": len(b_only_instances),
        "a_only_defect_count": len(a_only_instances),
        "reported_per_sentinel_not_only_in_total": True,
    }


def analyze_attempts(
    corpus: dict[str, Any], attempts: Sequence[Any], v1: ModuleType
) -> dict[str, Any]:
    """v0.1's analysis, plus the sentinel paired section."""
    corrected = _load_module(
        "_oic_postrun_audit_metrics_v2", ROOT / "scripts/audit_interpretation_proposal_postrun.py"
    )
    analysis = v1.analyze_attempts(corpus, attempts)
    analysis["sentinel_paired_defect_cells"] = sentinel_paired_defects(
        corpus, attempts, v1, corrected
    )
    return analysis


# ---------------------------------------------------------------------------
# The successor plan
# ---------------------------------------------------------------------------


def build_offline_plan(v1: ModuleType) -> dict[str, Any]:
    """v0.1's plan with the successor identity and the successor hint. Nothing else."""
    plan = v1.build_offline_plan()
    corpus = json.loads(v1.SOURCE_CORPUS.read_text(encoding="utf-8"))
    example = corpus["specimens"][0]
    plan["work_order"] = WORK_ORDER
    plan["plan_version"] = PLAN_VERSION
    plan["supersedes"] = {
        "work_order": v1.WORK_ORDER,
        "plan_version": "v0.1",
        "plan_path": PLAN_V1_PATH.relative_to(ROOT).as_posix(),
        "plan_sha256": sha256(PLAN_V1_PATH),
        "preserved_unchanged": True,
    }
    plan["starting_sha"] = STARTING_SHA
    plan["successor_change"] = (
        "the Arm B inserted hint text only; the seven required properties are now literal "
        "inside the hint block rather than established across the system prompt and hint "
        "together"
    )
    plan["arms"][v1.ARMS[1]]["description"] = (
        "same production system prompt and Arm A user prompt, plus one inserted hint block "
        "that itself states the hint is provisional, untrusted, from an earlier stage, "
        "without authority, not canonical institutional meaning, possibly wrong, and "
        "subordinate to the literal admitted proposition"
    )
    plan["arm_b_hint_template"] = ARM_B_HINT_TEMPLATE
    plan["arm_b_hint_example"] = arm_b_hint(example["candidate"]["unit_type"])
    plan["arm_b_hint_required_properties"] = dict(HINT_REQUIRED_PROPERTIES)
    plan["arm_b_hint_insertion_marker"] = _INSERTION_MARKER
    plan["hint_composed_by"] = (
        "the successor instrument, so that src/oic/interpretation_proposal.py stays byte-identical"
    )
    plan["production_interpretation_proposal_sha256"] = sha256(PRODUCTION_PATH)
    plan["sentinel_paired_defect_reporting"] = {
        "added_by_successor": True,
        "reason": (
            "v0.1 computed paired cells for the definition diagnostic only, so a "
            "regression appearing solely in Arm B on a sentinel would have been visible "
            "only inside a per-arm aggregate"
        ),
        "defect_rule": list(SENTINEL_DEFECT_RULE),
        "cells": ["A_ONLY_DEFECT", "B_ONLY_DEFECT", "BOTH_DEFECT", "NEITHER_DEFECT"],
        "reported_per_sentinel": True,
        "b_only_instances_named": True,
    }
    return plan


def preflight(v1: ModuleType) -> dict[str, Any]:
    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if sha256(PLAN_PATH) != freeze["plan_sha256"]:
        raise SystemExit("FAIL frozen successor plan digest mismatch")
    if sha256(PLAN_V1_PATH) != freeze["superseded_plan_sha256"]:
        raise SystemExit("FAIL the superseded v0.1 plan was modified")
    if sha256(PRODUCTION_PATH) != freeze["production_interpretation_proposal_sha256"]:
        raise SystemExit("FAIL the production proposal seam changed")
    plan: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if plan != build_offline_plan(v1):
        raise SystemExit("FAIL frozen successor plan differs from deterministic materialization")
    return plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="execute the preregistered paired run. Owner-only."
    )
    parser.add_argument(
        "--materialize", action="store_true", help="write the successor plan and its freeze"
    )
    args = parser.parse_args(argv)
    v1 = load_v1()

    if args.materialize:
        plan = build_offline_plan(v1)
        PLAN_PATH.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        freeze = {
            "freeze_id": f"{WORK_ORDER}-PLAN-FREEZE-{PLAN_VERSION}",
            "work_order": WORK_ORDER,
            "starting_sha": STARTING_SHA,
            "plan_path": PLAN_PATH.relative_to(ROOT).as_posix(),
            "plan_sha256": sha256(PLAN_PATH),
            "plan_bytes": PLAN_PATH.stat().st_size,
            "superseded_plan_path": PLAN_V1_PATH.relative_to(ROOT).as_posix(),
            "superseded_plan_sha256": sha256(PLAN_V1_PATH),
            "superseded_plan_preserved_unchanged": True,
            "source_corpus_sha256": plan["source_corpus_sha256"],
            "production_interpretation_proposal_sha256": sha256(PRODUCTION_PATH),
            "specimen_count": plan["specimen_count"],
            "runs_per_specimen": plan["runs_per_specimen"],
            "arm_count": 2,
            "paired_request_count": plan["planned_requests"],
            "definition_arm_observation_count": plan["definition_primary_diagnostic"][
                "observation_count"
            ],
            "regression_sentinel_count": len(plan["regression_sentinels"]),
            "successor_change": plan["successor_change"],
            "arm_b_hint_required_properties": sorted(HINT_REQUIRED_PROPERTIES),
            "live_run_executed": False,
            "model_call_made": False,
            "production_prompt_changed": False,
            "canonicalization_implemented": False,
            "institutional_ir_runtime_implemented": False,
            "independent_validation_claim": False,
            "self_adjudication": "NOT SELF-ADJUDICATED",
        }
        FREEZE_PATH.write_text(
            json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"materialized {PLAN_PATH.name} ({freeze['plan_bytes']} bytes)")
        print(f"plan sha256: {freeze['plan_sha256']}")
        return 0

    plan = preflight(v1)
    print(f"PASS frozen successor plan verified; {plan['planned_requests']} requests")
    print(f"arm B hint properties: {len(HINT_REQUIRED_PROPERTIES)} literal in the hint block")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    from oic.nvidia_nim import NvidiaNimProvider

    corpus = json.loads(v1.SOURCE_CORPUS.read_text(encoding="utf-8"))
    request_plan = v1.build_plan(corpus)
    v1.validate_plan(corpus, request_plan)
    attempts = execute_plan(corpus, request_plan, NvidiaNimProvider(), v1)
    analysis = analyze_attempts(corpus, attempts, v1)
    receipt = {
        "work_order": WORK_ORDER,
        "starting_sha": STARTING_SHA,
        "plan_version": PLAN_VERSION,
        "plan_sha256": sha256(PLAN_PATH),
        "production_interpretation_proposal_sha256": sha256(PRODUCTION_PATH),
        "arm_b_hint_template": ARM_B_HINT_TEMPLATE,
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
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"receipt written: {RECEIPT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
