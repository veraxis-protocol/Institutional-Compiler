#!/usr/bin/env python3
"""Definition Ontology Discrimination 003A.

Preregistered successor to Ontology 002.

This experiment discriminates one bounded explanation of the 002 result:
force classification and multi-slot extraction may interfere when required in
one generative proposal operation.

Arm A reproduces the exact ontology-clarified combined proposal condition used
as Arm B in Ontology 002.

Arm B receives the same candidate span and same six-label ontology
clarification, but returns only one provisional normative-force label.

Offline is the default. No provider is constructed without --live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import (  # noqa: E402
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
)

WORK_ORDER: Final[str] = "OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A"
PLAN_STARTING_SHA: Final[str] = "1d3833b9be6caef7906aef75016967dc709c3931"
INSTRUMENT_BASE_SHA: Final[str] = "b3635549321d7ab8cc2bf835ea051db8b9ad32d2"

BENCH = ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a"
PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
FREEZE_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE_001 = ROOT / "scripts/characterize_definition_ontology_discrimination.py"
SOURCE_CORPUS = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"
PRODUCTION_PATH = ROOT / "src/oic/interpretation_proposal.py"
PRIOR_ADJUDICATION = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-002/"
    "POST-RUN-ADJUDICATION.md"
)

QUALIFICATION_RECEIPT = (
    ROOT / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-003A.json"
)
RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-003A.json"
)

PLAN_SHA256: Final[str] = "e0d90bf41adf76402bd03cd1183feaffdbc8528c2a897874a266fe183d11cae1"
PREREG_SHA256: Final[str] = "49b40628b5e9e44af3944ff5954847ef358d55c85385f8dfd941ad0e1bce7348"
FREEZE_V1_SHA256: Final[str] = "93f406bf1d186c2a7a67649022c1ac93c82a3273ab24f4585b86f07feb327ac4"
CORPUS_SHA256: Final[str] = "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
PRODUCTION_SHA256: Final[str] = "921a569952ff8d1f3c3acd2f3b3a27be6f3c41ae4a1cc78d8f809317166a7ce0"
PRIOR_ADJUDICATION_SHA256: Final[str] = (
    "7db5217bc11eb70216cbf47e1c70fe129ae75060659ec02ce9e7fceb2f146c9d"
)

SOURCE_003_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003/PLAN-v0.1.json"
)
SOURCE_003_PLAN_SHA256: Final[str] = (
    "1643851ed0afddeafaba5731abd9308695c4f374b0be567fb8fae9ce6168b570"
)

MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"

CANDIDATE_PLACEHOLDER: Final[str] = "{candidate_span}"
FORCE_ONLY_LITERAL_JSON: Final[str] = '{"normative_force":"<ONE_ALLOWED_LABEL>"}'

ARM_A: Final[str] = "A_COMBINED_ONTOLOGY_CLARIFIED"
ARM_B: Final[str] = "B_FORCE_ONLY_ONTOLOGY_CLARIFIED"
ARMS: Final[tuple[str, str]] = (ARM_A, ARM_B)

PRIMARY: Final[tuple[str, ...]] = ("IIR-005", "IIR-023", "IIR-024")
CONTROLS: Final[tuple[str, ...]] = ("IIR-006", "IIR-027", "IIR-028")

FORCE_VALUES: Final[tuple[str, ...]] = (
    "OBLIGATION",
    "PROHIBITION",
    "PERMISSION",
    "CONSTITUTIVE_DEFINITION",
    "DELEGATION",
    "ADVISORY",
)

RUNS_PER_SPECIMEN: Final[int] = 3
PLANNED_REQUESTS: Final[int] = 36
PACING_SECONDS: Final[float] = 4.0


class ForceOnlyBoundaryError(ValueError):
    """Force-only provider output violated the frozen experimental contract."""


@dataclass(slots=True)
class Attempt:
    ordinal: int
    specimen_id: str
    run_index: int
    arm: str
    outcome: str
    proposed_force: str | None = None
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
            "proposed_force": self.proposed_force,
            "proposal": self.proposal,
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "raw_content_sha256": self.raw_content_sha256,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL cannot load frozen source instrument: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


def load_source() -> ModuleType:
    return _load_module("_oic_definition_ontology_001_for_003", SOURCE_001)


def load_plan() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    return data


def selected_corpus(
    source: ModuleType,
    corpus: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    scoped: dict[str, Any] = source.selected_corpus(corpus)

    expected = [item["specimen_id"] for item in plan["selected_specimens"]]
    actual = [item["specimen_id"] for item in scoped["specimens"]]

    if actual != expected:
        raise SystemExit("FAIL frozen selected-specimen identity/order drift")

    return scoped


def validate_request_plan(plan: dict[str, Any]) -> None:
    requests = plan["request_plan"]

    if len(requests) != PLANNED_REQUESTS:
        raise SystemExit("FAIL 003A must contain exactly 36 requests")

    if [item["ordinal"] for item in requests] != list(range(1, PLANNED_REQUESTS + 1)):
        raise SystemExit("FAIL request ordinals are not contiguous")

    counts = Counter(item["arm"] for item in requests)

    if counts != Counter({ARM_A: 18, ARM_B: 18}):
        raise SystemExit("FAIL 003A arm allocation drift")

    specimen_ids = [item["specimen_id"] for item in plan["selected_specimens"]]

    for specimen_id in specimen_ids:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            pair = [
                item["arm"]
                for item in requests
                if item["specimen_id"] == specimen_id and item["run_index"] == run_index
            ]

            expected = [ARM_A, ARM_B] if run_index % 2 else [ARM_B, ARM_A]

            if pair != expected:
                raise SystemExit(
                    f"FAIL deterministic interleaving drift for {specimen_id} run {run_index}"
                )


def parse_force_only(content: str) -> str:
    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ForceOnlyBoundaryError("force-only output is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ForceOnlyBoundaryError("force-only output root must be an object")

    if set(parsed) != {"normative_force"}:
        raise ForceOnlyBoundaryError("force-only output must contain exactly normative_force")

    force = parsed["normative_force"]

    if not isinstance(force, str) or force not in FORCE_VALUES:
        raise ForceOnlyBoundaryError("force-only output contains an invalid normative_force")

    return force


def proposal_force(proposal: dict[str, Any] | None) -> str | None:
    if proposal is None:
        return None

    values = [
        assertion.get("proposed_value")
        for assertion in proposal.get("proposed_assertions", [])
        if assertion.get("slot") == "normative_force"
    ]

    value = values[0] if values else None
    return value if isinstance(value, str) else None


class RequestMaterializationMismatchError(RuntimeError):
    """Live request differed from the offline-frozen request."""


@dataclass(slots=True)
class ExactRequestProvider:
    """Fail closed before network access if a live Arm-A request drifts."""

    delegate: ModelProvider
    expected: ModelRequest

    def complete(self, request: ModelRequest) -> ModelResponse:
        if request != self.expected:
            raise RequestMaterializationMismatchError(
                "live Arm A request differs from frozen offline materialization"
            )

        return self.delegate.complete(request)


def render_force_only_user_prompt(
    template: str,
    candidate_span: str,
) -> str:
    """Replace only the exact candidate token.

    Literal JSON braces remain literal bytes and never enter Python's
    formatting grammar.
    """
    if template.count(CANDIDATE_PLACEHOLDER) != 1:
        raise ValueError("force-only template must contain exactly one {candidate_span} token")

    rendered = template.replace(
        CANDIDATE_PLACEHOLDER,
        candidate_span,
        1,
    )

    if CANDIDATE_PLACEHOLDER in rendered:
        raise ValueError("unresolved candidate token remains")

    if FORCE_ONLY_LITERAL_JSON not in rendered:
        raise ValueError("force-only literal JSON example was not preserved")

    return rendered


def combined_request(
    *,
    specimen: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> ModelRequest:
    """Construct the exact request used by frozen propose_with_prompt."""
    return ModelRequest(
        system_prompt=v2._SYSTEM_PROMPT,
        user_prompt=source.arm_b_user_prompt(v2, v1, specimen),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=4096,
    )


def force_only_request(
    *,
    specimen: dict[str, Any],
    plan: dict[str, Any],
) -> ModelRequest:
    arm = plan["arms"][ARM_B]

    return ModelRequest(
        system_prompt=arm["system_prompt"],
        user_prompt=render_force_only_user_prompt(
            arm["user_prompt_template"],
            specimen["candidate"]["candidate_span"],
        ),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=int(arm["max_tokens"]),
    )


def request_projection(request: ModelRequest) -> dict[str, Any]:
    return {
        "system_prompt": request.system_prompt,
        "user_prompt": request.user_prompt,
        "response_format": request.response_format,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }


def request_projection_sha256(request: ModelRequest) -> str:
    payload = json.dumps(
        request_projection(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def validate_semantic_design_preservation(
    plan: dict[str, Any],
) -> None:
    source_003: dict[str, Any] = json.loads(SOURCE_003_PLAN.read_text(encoding="utf-8"))

    semantic_keys = (
        "purpose",
        "semantic_hypothesis",
        "competing_explanations",
        "arms",
        "force_values",
        "selected_specimens",
        "runs_per_specimen",
        "planned_requests",
        "planned_pairs",
        "primary_pairs",
        "control_pairs",
        "interleaving",
        "retry_policy",
        "pacing_seconds",
        "adjudicability_gate",
        "primary_endpoint",
        "control_endpoint",
        "semantic_decision_rule",
        "secondary_descriptive_endpoints",
        "claim_ceiling",
        "request_plan",
        "source_bindings",
    )

    for key in semantic_keys:
        if plan[key] != source_003[key]:
            raise SystemExit(f"FAIL semantic design drift from Ontology 003: {key}")


def materialize_requests(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> list[dict[str, Any]]:
    """Construct all 36 requests without constructing a live provider."""
    validate_semantic_design_preservation(plan)

    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}

    materialized: list[dict[str, Any]] = []

    for item in plan["request_plan"]:
        specimen = by_id[item["specimen_id"]]
        candidate_span = specimen["candidate"]["candidate_span"]

        if item["arm"] == ARM_A:
            request = combined_request(
                specimen=specimen,
                source=source,
                v2=v2,
                v1=v1,
            )
        elif item["arm"] == ARM_B:
            request = force_only_request(
                specimen=specimen,
                plan=plan,
            )
        else:
            raise ValueError(f"unknown frozen arm: {item['arm']}")

        if CANDIDATE_PLACEHOLDER in request.user_prompt:
            raise ValueError(f"unresolved candidate token at ordinal {item['ordinal']}")

        if candidate_span not in request.user_prompt:
            raise ValueError(f"candidate span absent at ordinal {item['ordinal']}")

        if item["arm"] == ARM_B and request.user_prompt.count(FORCE_ONLY_LITERAL_JSON) != 1:
            raise ValueError(
                "force-only literal JSON example must appear exactly "
                f"once at ordinal {item['ordinal']}"
            )

        materialized.append(
            {
                "ordinal": item["ordinal"],
                "specimen_id": item["specimen_id"],
                "run_index": item["run_index"],
                "arm": item["arm"],
                "candidate_span": candidate_span,
                "request": request_projection(request),
                "request_sha256": request_projection_sha256(request),
                "gold_label_exposed": False,
                "authority_metadata_exposed": False,
            }
        )

    if len(materialized) != PLANNED_REQUESTS:
        raise ValueError("offline materialization did not produce exactly 36 requests")

    identities = [
        {
            "ordinal": item["ordinal"],
            "specimen_id": item["specimen_id"],
            "run_index": item["run_index"],
            "arm": item["arm"],
        }
        for item in materialized
    ]

    if identities != plan["request_plan"]:
        raise ValueError("materialized request identities differ from frozen request_plan")

    counts = Counter(item["arm"] for item in materialized)

    if counts != Counter({ARM_A: 18, ARM_B: 18}):
        raise ValueError("materialized Arm A/B counts differ from frozen design")

    return materialized


def verify_materialization_manifest(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> None:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL frozen 003A request-materialization manifest absent")

    manifest: dict[str, Any] = json.loads(MATERIALIZATION_PATH.read_text(encoding="utf-8"))

    if manifest.get("work_order") != WORK_ORDER:
        raise SystemExit("FAIL request-materialization work-order mismatch")

    if manifest.get("plan_sha256") != PLAN_SHA256:
        raise SystemExit("FAIL request-materialization plan binding mismatch")

    if manifest.get("instrument_sha256") != sha256(Path(__file__)):
        raise SystemExit("FAIL request-materialization instrument binding mismatch")

    if manifest.get("provider_constructed") is not False:
        raise SystemExit("FAIL offline materialization records provider construction")

    if manifest.get("network_request_made") is not False:
        raise SystemExit("FAIL offline materialization records network activity")

    if manifest.get("request_count") != PLANNED_REQUESTS:
        raise SystemExit("FAIL request-materialization count mismatch")

    recomputed = materialize_requests(
        plan=plan,
        corpus=corpus,
        source=source,
        v2=v2,
        v1=v1,
    )

    if manifest.get("requests") != recomputed:
        raise SystemExit("FAIL frozen request materialization differs from recomputation")


def qualification_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RECEIPT.exists():
        raise SystemExit(
            "STOP Provider Qualification 003A receipt absent; "
            "Ontology 003A live execution unauthorized"
        )

    data: dict[str, Any] = json.loads(QUALIFICATION_RECEIPT.read_text(encoding="utf-8"))

    if data.get("work_order") != "OIC-NVIDIA-PROVIDER-QUALIFICATION-003A":
        raise SystemExit("STOP wrong Provider Qualification 003A receipt")

    if data.get("disposition") != "QUALIFIED":
        raise SystemExit("STOP Provider Qualification 003A is not QUALIFIED")

    if data.get("semantic_successor_authorized") is not True:
        raise SystemExit(
            "STOP Provider Qualification 003A did not authorize its semantic successor"
        )

    target = data.get("semantic_successor_target")

    if isinstance(target, dict):
        target = target.get("work_order")

    if target != WORK_ORDER:
        raise SystemExit("STOP Provider Qualification 003A targets a different semantic work order")

    return data


def preflight() -> tuple[dict[str, Any], ModuleType, ModuleType, ModuleType]:
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise SystemExit("FAIL 003A frozen plan digest mismatch")

    if sha256(PREREG_PATH) != PREREG_SHA256:
        raise SystemExit("FAIL 003A preregistration digest mismatch")

    if sha256(FREEZE_V1_PATH) != FREEZE_V1_SHA256:
        raise SystemExit("FAIL 003A preregistration freeze was modified")

    if sha256(SOURCE_CORPUS) != CORPUS_SHA256:
        raise SystemExit("FAIL source corpus digest mismatch")

    if sha256(PRODUCTION_PATH) != PRODUCTION_SHA256:
        raise SystemExit("FAIL production Interpretation Proposal seam changed")

    if sha256(PRIOR_ADJUDICATION) != PRIOR_ADJUDICATION_SHA256:
        raise SystemExit("FAIL Ontology 002 post-run adjudication changed")

    if sha256(SOURCE_003_PLAN) != SOURCE_003_PLAN_SHA256:
        raise SystemExit("FAIL source Ontology 003 plan changed")

    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL 003A instrument freeze identity mismatch")

    if freeze["base_commit"] != INSTRUMENT_BASE_SHA:
        raise SystemExit("FAIL 003A instrument freeze base mismatch")

    if freeze["plan_sha256"] != PLAN_SHA256:
        raise SystemExit("FAIL 003A freeze does not bind frozen plan")

    if freeze["preregistration_sha256"] != PREREG_SHA256:
        raise SystemExit("FAIL 003A freeze does not bind preregistration")

    if freeze["predecessor_freeze_v0_1_sha256"] != FREEZE_V1_SHA256:
        raise SystemExit("FAIL 003A freeze does not bind predecessor freeze")

    if freeze["instrument_sha256"] != sha256(Path(__file__)):
        raise SystemExit("FAIL 003A instrument bytes differ from static freeze")

    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL 003A request-materialization manifest absent")

    if freeze["request_materialization_sha256"] != sha256(MATERIALIZATION_PATH):
        raise SystemExit("FAIL 003A request-materialization digest mismatch")

    if freeze["request_materialization_completed"] is not True:
        raise SystemExit("FAIL 003A request materialization not marked complete")

    if freeze["request_materialization_count"] != PLANNED_REQUESTS:
        raise SystemExit("FAIL 003A request materialization count mismatch")

    if freeze["instrument_implemented"] is not True:
        raise SystemExit("FAIL 003A freeze does not mark instrument implemented")

    if freeze["instrument_frozen"] is not True:
        raise SystemExit("FAIL 003A freeze does not mark instrument frozen")

    if freeze["provider_call_made"] is not False:
        raise SystemExit("FAIL 003A static freeze incorrectly records provider activity")

    if freeze["model_call_made"] is not False:
        raise SystemExit("FAIL 003A static freeze incorrectly records model activity")

    if freeze["live_run_executed"] is not False:
        raise SystemExit("FAIL 003A static freeze incorrectly records live execution")

    plan = load_plan()

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL 003A plan work_order drift")

    if plan["starting_sha"] != PLAN_STARTING_SHA:
        raise SystemExit("FAIL 003A plan starting SHA drift")

    if plan["architectural_change_authorized"] is not False:
        raise SystemExit("FAIL architecture change must remain unauthorized")

    if plan["production_code_changed"] is not False:
        raise SystemExit("FAIL production code must remain unchanged")

    if plan["production_prompt_changed"] is not False:
        raise SystemExit("FAIL production prompt must remain unchanged")

    if plan["provider_prerequisite"]["work_order"] != "OIC-NVIDIA-PROVIDER-QUALIFICATION-003A":
        raise SystemExit("FAIL wrong provider prerequisite")

    if tuple(plan["force_values"]) != FORCE_VALUES:
        raise SystemExit("FAIL force vocabulary drift")

    validate_request_plan(plan)

    source = load_source()
    v2 = source.load_v2()
    v1 = v2.load_v1()

    source.preflight(v2, v1)

    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))
    scoped = selected_corpus(source, corpus, plan)

    clarification = plan["arms"][ARM_A]["ontology_clarification"].strip()

    if clarification != source.ONTOLOGY_CLARIFICATION_BLOCK.strip():
        raise SystemExit("FAIL Arm A ontology clarification drift")

    force_contract = plan["arms"][ARM_B]["output_contract"]

    if force_contract["exact_keys"] != ["normative_force"]:
        raise SystemExit("FAIL force-only output contract key drift")

    if tuple(force_contract["normative_force_allowed_values"]) != FORCE_VALUES:
        raise SystemExit("FAIL force-only allowed-force vocabulary drift")

    for specimen in scoped["specimens"]:
        combined = source.arm_b_user_prompt(v2, v1, specimen)

        if combined.count(source.ONTOLOGY_CLARIFICATION_BLOCK) != 1:
            raise SystemExit("FAIL combined Arm A must contain exactly one ontology clarification")

    validate_semantic_design_preservation(plan)

    verify_materialization_manifest(
        plan=plan,
        corpus=corpus,
        source=source,
        v2=v2,
        v1=v1,
    )

    return plan, source, v2, v1


def execute_combined(
    *,
    item: dict[str, Any],
    specimen: dict[str, Any],
    provider: ModelProvider,
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> Attempt:
    attempt = Attempt(
        ordinal=item["ordinal"],
        specimen_id=item["specimen_id"],
        run_index=item["run_index"],
        arm=ARM_A,
        outcome="PROVIDER_ERROR",
    )

    expected_request = combined_request(
        specimen=specimen,
        source=source,
        v2=v2,
        v1=v1,
    )

    guarded_provider = ExactRequestProvider(
        delegate=provider,
        expected=expected_request,
    )

    try:
        result = v2.propose_with_prompt(
            binding=source._binding(v1, specimen),
            user_prompt=source.arm_b_user_prompt(v2, v1, specimen),
            provider=guarded_provider,
            proposer_id="oic-definition-ontology-discrimination-003a-combined",
        )
    except v2.ProposalBoundaryError as exc:
        attempt.outcome = "BOUNDARY_REJECTED"
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
    except (v2.InterpretationProposalError, ModelProviderError) as exc:
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
    else:
        attempt.outcome = "ACCEPTED"
        attempt.proposal = result.proposal
        attempt.proposed_force = proposal_force(result.proposal)
        attempt.provider = result.provider
        attempt.model = result.model
        attempt.request_id = result.request_id
        attempt.raw_content_sha256 = result.raw_content_sha256

    return attempt


def execute_force_only(
    *,
    item: dict[str, Any],
    specimen: dict[str, Any],
    provider: ModelProvider,
    plan: dict[str, Any],
) -> Attempt:
    attempt = Attempt(
        ordinal=item["ordinal"],
        specimen_id=item["specimen_id"],
        run_index=item["run_index"],
        arm=ARM_B,
        outcome="PROVIDER_ERROR",
    )

    request = force_only_request(
        specimen=specimen,
        plan=plan,
    )

    try:
        response = provider.complete(request)
    except ModelProviderError as exc:
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
        return attempt

    try:
        force = parse_force_only(response.content)
    except ForceOnlyBoundaryError as exc:
        attempt.outcome = "BOUNDARY_REJECTED"
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
    else:
        attempt.outcome = "ACCEPTED"
        attempt.proposed_force = force
        attempt.provider = response.provider
        attempt.model = response.model
        attempt.request_id = response.request_id
        attempt.raw_content_sha256 = hashlib.sha256(response.content.encode("utf-8")).hexdigest()

    return attempt


def execute_plan(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    provider: ModelProvider,
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> list[Attempt]:
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}
    attempts: list[Attempt] = []

    for index, item in enumerate(plan["request_plan"]):
        specimen = by_id[item["specimen_id"]]

        if item["arm"] == ARM_A:
            attempt = execute_combined(
                item=item,
                specimen=specimen,
                provider=provider,
                source=source,
                v2=v2,
                v1=v1,
            )
        elif item["arm"] == ARM_B:
            attempt = execute_force_only(
                item=item,
                specimen=specimen,
                provider=provider,
                plan=plan,
            )
        else:
            raise SystemExit(f"FAIL unknown frozen arm: {item['arm']}")

        attempts.append(attempt)

        if index < len(plan["request_plan"]) - 1:
            time.sleep(PACING_SECONDS)

    return attempts


def adjudicability(attempts: Sequence[Attempt]) -> dict[str, int | bool]:
    accepted = [item for item in attempts if item.outcome == "ACCEPTED"]

    accepted_keys = {(item.specimen_id, item.run_index, item.arm) for item in accepted}

    pairs = {(item.specimen_id, item.run_index) for item in attempts}

    complete = sum(
        (sid, run, ARM_A) in accepted_keys and (sid, run, ARM_B) in accepted_keys
        for sid, run in pairs
    )

    primary_complete = sum(
        (sid, run, ARM_A) in accepted_keys and (sid, run, ARM_B) in accepted_keys
        for sid in PRIMARY
        for run in range(1, RUNS_PER_SPECIMEN + 1)
    )

    control_complete = sum(
        (sid, run, ARM_A) in accepted_keys and (sid, run, ARM_B) in accepted_keys
        for sid in CONTROLS
        for run in range(1, RUNS_PER_SPECIMEN + 1)
    )

    gate = (
        len(attempts) == PLANNED_REQUESTS
        and len(accepted) == PLANNED_REQUESTS
        and complete == 18
        and primary_complete == 9
        and control_complete == 9
    )

    return {
        "planned_observations": PLANNED_REQUESTS,
        "observed_attempts": len(attempts),
        "accepted_observations": len(accepted),
        "complete_ab_pairs": complete,
        "primary_complete_pairs": primary_complete,
        "control_complete_pairs": control_complete,
        "adjudicable": gate,
    }


def correct_force(attempt: Attempt, expected: str) -> bool:
    return attempt.outcome == "ACCEPTED" and attempt.proposed_force == expected


def paired_force_analysis(
    attempts: Sequence[Attempt],
    specimen_ids: Sequence[str],
    expected: dict[str, str],
) -> dict[str, Any]:
    cells: Counter[str] = Counter(
        {
            "A_ONLY_DEFECT": 0,
            "B_ONLY_DEFECT": 0,
            "BOTH_DEFECT": 0,
            "NEITHER_DEFECT": 0,
        }
    )

    b_improvements: list[dict[str, Any]] = []
    a_improvements: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    for specimen_id in specimen_ids:
        for run_index in range(1, RUNS_PER_SPECIMEN + 1):
            a = next(
                item
                for item in attempts
                if item.specimen_id == specimen_id
                and item.run_index == run_index
                and item.arm == ARM_A
            )

            b = next(
                item
                for item in attempts
                if item.specimen_id == specimen_id
                and item.run_index == run_index
                and item.arm == ARM_B
            )

            a_correct = correct_force(a, expected[specimen_id])
            b_correct = correct_force(b, expected[specimen_id])

            a_defect = not a_correct
            b_defect = not b_correct

            if a_defect and b_defect:
                cells["BOTH_DEFECT"] += 1
            elif a_defect:
                cells["A_ONLY_DEFECT"] += 1
                b_improvements.append(
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                    }
                )
            elif b_defect:
                cells["B_ONLY_DEFECT"] += 1
                a_improvements.append(
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                    }
                )
            else:
                cells["NEITHER_DEFECT"] += 1

            observations.extend(
                [
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                        "arm": ARM_A,
                        "expected_force": expected[specimen_id],
                        "proposed_force": a.proposed_force,
                        "correct": a_correct,
                    },
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                        "arm": ARM_B,
                        "expected_force": expected[specimen_id],
                        "proposed_force": b.proposed_force,
                        "correct": b_correct,
                    },
                ]
            )

    return {
        "observations": observations,
        "paired_cells": dict(cells),
        "b_improvement_count": len(b_improvements),
        "b_improvement_instances": b_improvements,
        "a_improvement_count": len(a_improvements),
        "a_improvement_instances": a_improvements,
    }


def decide(
    *,
    b_primary_correct: int,
    b_primary_improvements: int,
    a_primary_improvements: int,
    b_only_control_defects: int,
) -> str:
    if b_only_control_defects:
        return "REGRESSION"

    if a_primary_improvements >= 2:
        return "REFUTES_FORCE_ONLY_ADVANTAGE"

    if b_primary_correct >= 8 and b_primary_improvements >= 2:
        return "SUPPORTS_TASK_INTERFERENCE_HYPOTHESIS"

    return "INCONCLUSIVE"


def _to_v1_attempt(v1: ModuleType, item: Attempt) -> Any:  # noqa: ANN401 - dynamically loaded frozen Attempt type
    return v1.Attempt(
        ordinal=item.ordinal,
        specimen_id=item.specimen_id,
        run_index=item.run_index,
        arm=item.arm,
        outcome=item.outcome,
        proposal=item.proposal,
        provider=item.provider,
        model=item.model,
        request_id=item.request_id,
        raw_content_sha256=item.raw_content_sha256,
        error_type=item.error_type,
        error_message=item.error_message,
    )


def analyze(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    attempts: Sequence[Attempt],
    source: ModuleType,
    v1: ModuleType,
) -> dict[str, Any]:
    scoped = selected_corpus(source, corpus, plan)

    expected = {item["specimen_id"]: item["gold"]["expected_force"] for item in scoped["specimens"]}

    primary = paired_force_analysis(
        attempts,
        PRIMARY,
        expected,
    )

    controls = paired_force_analysis(
        attempts,
        CONTROLS,
        expected,
    )

    b_primary_correct = sum(
        correct_force(item, expected[item.specimen_id])
        for item in attempts
        if item.specimen_id in PRIMARY and item.arm == ARM_B
    )

    b_only_control_defects = controls["paired_cells"]["B_ONLY_DEFECT"]

    disposition = decide(
        b_primary_correct=b_primary_correct,
        b_primary_improvements=primary["b_improvement_count"],
        a_primary_improvements=primary["a_improvement_count"],
        b_only_control_defects=b_only_control_defects,
    )

    combined = [item for item in attempts if item.arm == ARM_A]

    historical = [_to_v1_attempt(v1, item) for item in combined]

    established = source._established(v1, scoped, historical)
    grounding = source._grounding(v1, scoped, historical)

    per_specimen_stability: dict[str, Any] = {}

    for specimen_id in [item["specimen_id"] for item in plan["selected_specimens"]]:
        per_specimen_stability[specimen_id] = {}

        for arm in ARMS:
            relevant = sorted(
                (item for item in attempts if item.specimen_id == specimen_id and item.arm == arm),
                key=lambda item: item.run_index,
            )

            per_specimen_stability[specimen_id][arm] = [
                {
                    "run_index": item.run_index,
                    "outcome": item.outcome,
                    "proposed_force": item.proposed_force,
                }
                for item in relevant
            ]

    return {
        "disposition": disposition,
        "primary_force": {
            **primary,
            "b_correct_planned_denominator": {
                "correct": b_primary_correct,
                "planned": 9,
            },
        },
        "control_force": {
            **controls,
            "b_only_force_defect_count": b_only_control_defects,
            "b_only_force_defect_instances": controls["a_improvement_instances"],
        },
        "combined_arm_secondary": {
            "definiendum": established["per_slot"]["definiendum"],
            "definiens": established["per_slot"]["definiens"],
            "source_quote_grounding": grounding,
            "provider_errors": sum(item.outcome == "PROVIDER_ERROR" for item in combined),
            "boundary_rejections": sum(item.outcome == "BOUNDARY_REJECTED" for item in combined),
        },
        "force_only_secondary": {
            "provider_errors": sum(
                item.outcome == "PROVIDER_ERROR" for item in attempts if item.arm == ARM_B
            ),
            "boundary_rejections": sum(
                item.outcome == "BOUNDARY_REJECTED" for item in attempts if item.arm == ARM_B
            ),
        },
        "per_specimen_force_stability": per_specimen_stability,
        "descriptive_only": True,
        "architectural_change_authorized": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="execute the frozen 36-request paired experiment exactly once",
    )
    args = parser.parse_args(argv)

    plan, source, v2, v1 = preflight()

    print(f"PASS frozen Ontology 003A instrument verified; {plan['planned_requests']} requests")
    print("Arm A: exact Ontology 002 ontology-clarified combined condition")
    print("Arm B: ontology-clarified force-only classification")
    print("adjudicability gate: 36/36 ACCEPTED + all 18 pairs complete")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    qualification = qualification_prerequisite()

    if RECEIPT_PATH.exists():
        raise SystemExit(f"STOP Ontology 003A receipt already exists: {RECEIPT_PATH}")

    from oic.nvidia_nim import NvidiaNimProvider

    corpus = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))

    attempts = execute_plan(
        plan=plan,
        corpus=corpus,
        provider=NvidiaNimProvider(),
        source=source,
        v2=v2,
        v1=v1,
    )

    gate = adjudicability(attempts)

    if gate["adjudicable"]:
        semantic_analysis = analyze(
            plan=plan,
            corpus=corpus,
            attempts=attempts,
            source=source,
            v1=v1,
        )
        scientific_disposition = semantic_analysis["disposition"]
        decision_evaluated = True
    else:
        semantic_analysis = None
        scientific_disposition = "NOT_ADJUDICABLE_PROVIDER_FAILURE"
        decision_evaluated = False

    receipt = {
        "work_order": WORK_ORDER,
        "starting_sha": PLAN_STARTING_SHA,
        "plan_sha256": sha256(PLAN_PATH),
        "instrument_freeze_sha256": sha256(FREEZE_PATH),
        "provider_qualification_003a_receipt_sha256": sha256(QUALIFICATION_RECEIPT),
        "provider_qualification_003a_disposition": qualification["disposition"],
        "attempts": [item.to_json() for item in attempts],
        "adjudicability": gate,
        "scientific_disposition": scientific_disposition,
        "semantic_analysis": semantic_analysis,
        "live_run_executed": True,
        "semantic_decision_rule_evaluated": decision_evaluated,
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "architectural_change_authorized": False,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)

    RECEIPT_PATH.write_text(
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"receipt written: {RECEIPT_PATH}")
    print(f"scientific disposition: {scientific_disposition}")
    print(f"semantic decision evaluated: {decision_evaluated}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
