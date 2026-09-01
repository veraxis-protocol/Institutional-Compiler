#!/usr/bin/env python3
"""Ontology Staged Decomposition 004.

Preregistered successor to Ontology 003A.

Arm A reproduces the exact combined ontology-clarified request used in 003A.

Arm B is decomposed into two independent model requests:
B1 classifies provisional normative force only.
B2 extracts all ten non-force semantic slots only.

B2 never consumes B1 output. Their outputs are merged deterministically and
locally; the model does not merge, reconcile, repair or canonicalize them.

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
from typing import Any, Final, cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.model_provider import (  # noqa: E402
    ModelProvider,
    ModelProviderError,
    ModelRequest,
    ModelResponse,
)

WORK_ORDER: Final[str] = "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-004"

PLAN_STARTING_SHA: Final[str] = "f3eff10c7311783b6a7a8c97caf8cfd1c1b90473"

INSTRUMENT_BASE_SHA: Final[str] = "15a886eab80e1dec57517c9ee225f1e21e271703"

BENCH = ROOT / "benchmarks/characterization/definition-ontology-staged-decomposition-004"

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
FREEZE_PATH = BENCH / "PLAN-FREEZE-v0.2.json"
MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"

SOURCE_003A_SCRIPT = ROOT / "scripts/characterize_definition_ontology_discrimination_003a.py"

SOURCE_003A_PLAN = (
    ROOT / "benchmarks/characterization/definition-ontology-discrimination-003a/PLAN-v0.1.json"
)

SOURCE_003A_MANIFEST = (
    ROOT / "benchmarks/characterization/"
    "definition-ontology-discrimination-003a/"
    "REQUEST-MATERIALIZATION-v0.1.json"
)

SOURCE_CORPUS = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"

PREDECESSOR_RESULT = (
    ROOT / "benchmarks/characterization/"
    "definition-ontology-discrimination-003a/"
    "EXECUTION-RESULT-v0.1.json"
)

PREDECESSOR_ADJUDICATION = (
    ROOT / "benchmarks/characterization/"
    "definition-ontology-discrimination-003a/"
    "POST-RUN-ADJUDICATION.md"
)

QUALIFICATION_RECEIPT = (
    ROOT / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-004.json"
)

RECEIPT_PATH = (
    ROOT / ".local/interpretation-proposal-receipts/"
    "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-004.json"
)

PLAN_SHA256: Final[str] = "90945b2016918ea66ce94a5d972dae881bbe23cb54060e069acbbe89656e7100"

PREREG_SHA256: Final[str] = "469ecf061a82b82857cd360a3426731b4f5cf1c5c02edc2c87fd64930b453dcb"

FREEZE_V1_SHA256: Final[str] = "9ee8735e6d0f37325679907c0cdeb007aae73420ebb2c7620e9c086087cf6c17"

SOURCE_003A_SCRIPT_SHA256: Final[str] = (
    "dee47076199b104888092aaa6adbc57709003c78765f275c2b4031dc9701ddd3"
)

SOURCE_003A_PLAN_SHA256: Final[str] = (
    "e0d90bf41adf76402bd03cd1183feaffdbc8528c2a897874a266fe183d11cae1"
)

SOURCE_003A_MANIFEST_SHA256: Final[str] = (
    "15cc46b20df2ba27c354dc2d1be9b5bb8815c3dd7d5f0efa0dd03a1b2f816b51"
)

SOURCE_CORPUS_SHA256: Final[str] = (
    "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
)

PREDECESSOR_RESULT_SHA256: Final[str] = (
    "c6befe2c084b927d53bd093c4980fc95c1d3ae5fada38bfc34cdbb2f9bc71d72"
)

PREDECESSOR_ADJUDICATION_SHA256: Final[str] = (
    "e0cf414b2cdc04665357d1ad4d66456cbc2958ff1815e30bcb71326d5130eaba"
)

STAGE_A: Final[str] = "A_COMBINED"
STAGE_B1: Final[str] = "B1_FORCE"
STAGE_B2: Final[str] = "B2_NONFORCE_SLOTS"

STAGES: Final[tuple[str, ...]] = (
    STAGE_A,
    STAGE_B1,
    STAGE_B2,
)

PRIMARY: Final[tuple[str, ...]] = (
    "IIR-005",
    "IIR-023",
    "IIR-024",
)

CONTROLS: Final[tuple[str, ...]] = (
    "IIR-006",
    "IIR-027",
    "IIR-028",
)

NONFORCE_SLOTS: Final[tuple[str, ...]] = (
    "bearer",
    "action",
    "object",
    "counterparty",
    "condition",
    "exception",
    "temporal_qualifier",
    "quantum",
    "definiendum",
    "definiens",
)

REFERENCE_KINDS: Final[tuple[str, ...]] = (
    "INTERNAL_PROVISION",
    "EXTERNAL_DOCUMENT",
    "DEFINITION",
    "UNCLASSIFIED",
)

CANDIDATE_PLACEHOLDER: Final[str] = "{candidate_span}"

RUNS_PER_SPECIMEN: Final[int] = 3
PLANNED_PROVIDER_REQUESTS: Final[int] = 54
PLANNED_COMPOSITE_PAIRS: Final[int] = 18
PACING_SECONDS: Final[float] = 4.0

_ASSERTION_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "slot",
        "proposed_value",
        "proposed_source_quote",
    }
)

_ASSERTION_ALLOWED_KEYS: Final[frozenset[str]] = _ASSERTION_REQUIRED_KEYS | {
    "proposed_material_qualifiers"
}

_ROOT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "proposed_assertions",
        "proposed_unresolved_references",
    }
)

_REFERENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "reference_text",
        "reference_kind",
    }
)

_FORBIDDEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "admission_receipt_id",
        "admission_state",
        "admitted",
        "allow",
        "authority",
        "authorization",
        "canonical",
        "candidate_unit_id",
        "confidence",
        "deny",
        "enforceability",
        "epistemic_state",
        "established",
        "interpretation_basis",
        "interpretation_evidence",
        "interpretation_evidence_refs",
        "interpretation_status",
        "ir_unit_id",
        "legal_effect",
        "normative_force",
        "probability",
        "proposal_id",
        "proposal_state",
        "runtime_outcome",
        "score",
        "semantic_equivalence_key",
        "verdict",
        "warrant",
    }
)

_FORBIDDEN_VALUE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "established",
        "ambiguous",
        "not_established",
        "not_applicable",
    }
)


class NonforceBoundaryError(ValueError):
    """B2 provider output violated the frozen non-force contract."""


class RequestMaterializationMismatchError(RuntimeError):
    """A live request differed from its offline-frozen request."""


@dataclass(slots=True)
class ExactRequestProvider:
    """Fail closed before network access when a live request drifts."""

    delegate: ModelProvider
    expected: ModelRequest

    def complete(self, request: ModelRequest) -> ModelResponse:
        if request != self.expected:
            raise RequestMaterializationMismatchError(
                "live request differs from frozen offline materialization"
            )

        return self.delegate.complete(request)


@dataclass(slots=True)
class StageAttempt:
    ordinal: int
    specimen_id: str
    run_index: int
    stage: str
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
            "stage": self.stage,
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


def _load_module(
    name: str,
    path: Path,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL cannot load frozen source instrument: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


def load_source_003a() -> ModuleType:
    return _load_module(
        "_oic_definition_ontology_003a_for_004",
        SOURCE_003A_SCRIPT,
    )


def load_plan() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    return data


def load_context() -> tuple[
    ModuleType,
    dict[str, Any],
    ModuleType,
    ModuleType,
    ModuleType,
    dict[str, Any],
]:
    predecessor = load_source_003a()

    predecessor_plan = predecessor.load_plan()

    source = predecessor.load_source()
    v2 = source.load_v2()
    v1 = v2.load_v1()

    corpus: dict[str, Any] = json.loads(SOURCE_CORPUS.read_text(encoding="utf-8"))

    return (
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    )


def validate_request_plan(
    plan: dict[str, Any],
) -> None:
    requests = plan["provider_request_plan"]

    if len(requests) != PLANNED_PROVIDER_REQUESTS:
        raise SystemExit("FAIL 004 must contain exactly 54 provider requests")

    if [item["ordinal"] for item in requests] != list(range(1, PLANNED_PROVIDER_REQUESTS + 1)):
        raise SystemExit("FAIL 004 provider-request ordinals are not contiguous")

    counts = Counter(item["stage"] for item in requests)

    if counts != Counter(
        {
            STAGE_A: 18,
            STAGE_B1: 18,
            STAGE_B2: 18,
        }
    ):
        raise SystemExit("FAIL 004 stage allocation drift")

    specimen_ids = [item["specimen_id"] for item in plan["selected_specimens"]]

    for specimen_id in specimen_ids:
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            actual = [
                item["stage"]
                for item in requests
                if item["specimen_id"] == specimen_id and item["run_index"] == run_index
            ]

            expected = (
                [
                    STAGE_A,
                    STAGE_B1,
                    STAGE_B2,
                ]
                if run_index % 2
                else [
                    STAGE_B1,
                    STAGE_B2,
                    STAGE_A,
                ]
            )

            if actual != expected:
                raise SystemExit(
                    "FAIL deterministic staged interleaving drift "
                    f"for {specimen_id} run {run_index}"
                )


def render_candidate_prompt(
    template: str,
    candidate_span: str,
) -> str:
    """Replace only the exact candidate placeholder."""

    if template.count(CANDIDATE_PLACEHOLDER) != 1:
        raise ValueError("template must contain exactly one {candidate_span} placeholder")

    rendered = template.replace(
        CANDIDATE_PLACEHOLDER,
        candidate_span,
        1,
    )

    if CANDIDATE_PLACEHOLDER in rendered:
        raise ValueError("unresolved candidate placeholder remains")

    return rendered


def nonforce_request(
    *,
    specimen: dict[str, Any],
    plan: dict[str, Any],
) -> ModelRequest:
    stage = plan["arms"]["B_STAGED_DECOMPOSED"]["stage_2_nonforce_slots"]

    return ModelRequest(
        system_prompt=stage["system_prompt"],
        user_prompt=render_candidate_prompt(
            stage["user_prompt_template"],
            specimen["candidate"]["candidate_span"],
        ),
        response_format={
            "type": "json_object",
        },
        temperature=0.0,
        max_tokens=int(stage["max_tokens"]),
    )


def request_for(
    *,
    item: dict[str, Any],
    specimen: dict[str, Any],
    plan: dict[str, Any],
    predecessor: ModuleType,
    predecessor_plan: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> ModelRequest:
    stage = item["stage"]

    if stage == STAGE_A:
        request: ModelRequest = predecessor.combined_request(
            specimen=specimen,
            source=source,
            v2=v2,
            v1=v1,
        )

        return request

    if stage == STAGE_B1:
        return cast(
            ModelRequest,
            predecessor.force_only_request(
                specimen=specimen,
                plan=predecessor_plan,
            ),
        )

    if stage == STAGE_B2:
        return nonforce_request(
            specimen=specimen,
            plan=plan,
        )

    raise ValueError(f"unknown frozen stage: {stage}")


def request_projection(
    request: ModelRequest,
) -> dict[str, Any]:
    return {
        "system_prompt": request.system_prompt,
        "user_prompt": request.user_prompt,
        "response_format": request.response_format,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }


def request_projection_sha256(
    request: ModelRequest,
) -> str:
    payload = json.dumps(
        request_projection(request),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def materialize_requests(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    predecessor: ModuleType,
    predecessor_plan: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> list[dict[str, Any]]:
    """Construct every frozen request without constructing a provider."""

    validate_request_plan(plan)

    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}

    materialized: list[dict[str, Any]] = []

    for item in plan["provider_request_plan"]:
        specimen = by_id[item["specimen_id"]]

        candidate_span = specimen["candidate"]["candidate_span"]

        request = request_for(
            item=item,
            specimen=specimen,
            plan=plan,
            predecessor=predecessor,
            predecessor_plan=predecessor_plan,
            source=source,
            v2=v2,
            v1=v1,
        )

        if CANDIDATE_PLACEHOLDER in request.user_prompt:
            raise ValueError(f"unresolved candidate placeholder at ordinal {item['ordinal']}")

        if candidate_span not in request.user_prompt:
            raise ValueError(f"candidate span absent from request at ordinal {item['ordinal']}")

        if item["stage"] == STAGE_B2:
            allowed = plan["arms"]["B_STAGED_DECOMPOSED"]["stage_2_nonforce_slots"]["allowed_slots"]

            if "normative_force" in allowed:
                raise ValueError("B2 allowed-slot vocabulary contains normative_force")

        materialized.append(
            {
                "ordinal": item["ordinal"],
                "specimen_id": item["specimen_id"],
                "run_index": item["run_index"],
                "stage": item["stage"],
                "candidate_span": candidate_span,
                "request": request_projection(request),
                "request_sha256": request_projection_sha256(request),
                "gold_label_exposed": False,
                "authority_metadata_exposed": False,
                "provider_constructed": False,
                "network_request_made": False,
            }
        )

    if len(materialized) != PLANNED_PROVIDER_REQUESTS:
        raise ValueError("offline materialization did not produce 54 requests")

    identities = [
        {
            "ordinal": item["ordinal"],
            "specimen_id": item["specimen_id"],
            "run_index": item["run_index"],
            "stage": item["stage"],
        }
        for item in materialized
    ]

    if identities != plan["provider_request_plan"]:
        raise ValueError("materialized identities differ from frozen request plan")

    return materialized


def verify_predecessor_request_parity(
    materialized: Sequence[dict[str, Any]],
) -> None:
    predecessor_manifest: dict[str, Any] = json.loads(
        SOURCE_003A_MANIFEST.read_text(encoding="utf-8")
    )

    old_by_key = {
        (
            item["specimen_id"],
            item["run_index"],
            item["arm"],
        ): item
        for item in predecessor_manifest["requests"]
    }

    predecessor = load_source_003a()

    for item in materialized:
        stage = item["stage"]

        if stage == STAGE_B2:
            continue

        old_arm = predecessor.ARM_A if stage == STAGE_A else predecessor.ARM_B

        old = old_by_key[
            (
                item["specimen_id"],
                item["run_index"],
                old_arm,
            )
        ]

        if item["request"] != old["request"]:
            raise ValueError(
                "004 predecessor request parity failure: "
                f"{item['specimen_id']} "
                f"run {item['run_index']} "
                f"{stage}"
            )

        if item["request_sha256"] != old["request_sha256"]:
            raise ValueError("004 predecessor request hash parity failure")


def _forbidden_keys_in(
    node: object,
    found: set[str],
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN_KEYS:
                found.add(key)

            _forbidden_keys_in(
                value,
                found,
            )

    elif isinstance(node, list):
        for item in node:
            _forbidden_keys_in(
                item,
                found,
            )


def _forbidden_values_in(
    node: object,
    found: set[str],
) -> None:
    if isinstance(node, str):
        if node.strip().casefold() in _FORBIDDEN_VALUE_TOKENS:
            found.add(node)

    elif isinstance(node, dict):
        for value in node.values():
            _forbidden_values_in(
                value,
                found,
            )

    elif isinstance(node, list):
        for item in node:
            _forbidden_values_in(
                item,
                found,
            )


def parse_nonforce(
    content: str,
) -> dict[str, Any]:
    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise NonforceBoundaryError("B2 output is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise NonforceBoundaryError("B2 output root must be an object")

    unexpected = set(parsed) - _ROOT_KEYS

    if unexpected:
        raise NonforceBoundaryError(f"B2 output has unexpected root keys: {sorted(unexpected)}")

    forbidden: set[str] = set()

    _forbidden_keys_in(
        parsed,
        forbidden,
    )

    if forbidden:
        raise NonforceBoundaryError(f"B2 attempted to emit forbidden fields: {sorted(forbidden)}")

    forbidden_values: set[str] = set()

    _forbidden_values_in(
        parsed,
        forbidden_values,
    )

    if forbidden_values:
        raise NonforceBoundaryError(
            f"B2 emitted interpretation-status values: {sorted(forbidden_values)}"
        )

    assertions = parsed.get(
        "proposed_assertions",
        [],
    )

    references = parsed.get(
        "proposed_unresolved_references",
        [],
    )

    if not isinstance(assertions, list):
        raise NonforceBoundaryError("proposed_assertions must be an array")

    if not isinstance(references, list):
        raise NonforceBoundaryError("proposed_unresolved_references must be an array")

    for assertion in assertions:
        if not isinstance(assertion, dict):
            raise NonforceBoundaryError("every B2 assertion must be an object")

        keys = set(assertion)

        if not _ASSERTION_REQUIRED_KEYS.issubset(keys):
            raise NonforceBoundaryError("B2 assertion is missing required keys")

        if not keys.issubset(_ASSERTION_ALLOWED_KEYS):
            raise NonforceBoundaryError("B2 assertion has unexpected keys")

        slot = assertion["slot"]

        if not isinstance(slot, str) or slot not in NONFORCE_SLOTS:
            raise NonforceBoundaryError("B2 assertion has invalid non-force slot")

        value = assertion["proposed_value"]
        quote = assertion["proposed_source_quote"]

        if value is not None and not isinstance(value, str):
            raise NonforceBoundaryError("B2 proposed_value must be string or null")

        if quote is not None and not isinstance(quote, str):
            raise NonforceBoundaryError("B2 proposed_source_quote must be string or null")

        qualifiers = assertion.get(
            "proposed_material_qualifiers",
        )

        if qualifiers is not None and (
            not isinstance(qualifiers, list)
            or not all(isinstance(item, str) for item in qualifiers)
        ):
            raise NonforceBoundaryError(
                "B2 proposed_material_qualifiers must be an array of strings"
            )

    for reference in references:
        if not isinstance(reference, dict) or set(reference) != _REFERENCE_KEYS:
            raise NonforceBoundaryError("B2 unresolved reference shape is invalid")

        text = reference["reference_text"]
        kind = reference["reference_kind"]

        if not isinstance(text, str):
            raise NonforceBoundaryError("B2 reference_text must be a string")

        if not isinstance(kind, str) or kind not in REFERENCE_KINDS:
            raise NonforceBoundaryError("B2 reference_kind is invalid")

    result: dict[str, Any] = parsed

    return result


def deterministic_merge(
    *,
    force: str,
    nonforce: dict[str, Any],
) -> dict[str, Any]:
    """Merge staged proposals without a model or institutional act."""

    assertions = [
        {
            "slot": "normative_force",
            "proposed_value": force,
            "proposed_source_quote": None,
        }
    ]

    assertions.extend(
        nonforce.get(
            "proposed_assertions",
            [],
        )
    )

    return {
        "proposed_assertions": assertions,
        "proposed_unresolved_references": nonforce.get(
            "proposed_unresolved_references",
            [],
        ),
    }


def verify_manifest(
    *,
    plan: dict[str, Any],
    corpus: dict[str, Any],
    predecessor: ModuleType,
    predecessor_plan: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> None:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit("FAIL frozen 004 request-materialization manifest absent")

    manifest: dict[str, Any] = json.loads(MATERIALIZATION_PATH.read_text(encoding="utf-8"))

    if manifest.get("work_order") != WORK_ORDER:
        raise SystemExit("FAIL 004 request-materialization identity mismatch")

    if manifest.get("plan_sha256") != PLAN_SHA256:
        raise SystemExit("FAIL 004 materialization plan binding mismatch")

    if manifest.get("instrument_sha256") != sha256(Path(__file__)):
        raise SystemExit("FAIL 004 materialization instrument binding mismatch")

    if manifest.get("request_count") != PLANNED_PROVIDER_REQUESTS:
        raise SystemExit("FAIL 004 materialization request count mismatch")

    if manifest.get("provider_constructed") is not False:
        raise SystemExit("FAIL 004 offline materialization records provider activity")

    if manifest.get("network_request_made") is not False:
        raise SystemExit("FAIL 004 offline materialization records network activity")

    recomputed = materialize_requests(
        plan=plan,
        corpus=corpus,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )

    if manifest.get("requests") != recomputed:
        raise SystemExit("FAIL 004 materialization differs from recomputation")

    verify_predecessor_request_parity(recomputed)


def preflight() -> tuple[
    dict[str, Any],
    ModuleType,
    dict[str, Any],
    ModuleType,
    ModuleType,
    ModuleType,
    dict[str, Any],
]:
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise SystemExit("FAIL 004 frozen plan digest mismatch")

    if sha256(PREREG_PATH) != PREREG_SHA256:
        raise SystemExit("FAIL 004 preregistration digest mismatch")

    if sha256(FREEZE_V1_PATH) != FREEZE_V1_SHA256:
        raise SystemExit("FAIL 004 preregistration freeze digest mismatch")

    if sha256(SOURCE_003A_SCRIPT) != SOURCE_003A_SCRIPT_SHA256:
        raise SystemExit("FAIL source Ontology 003A instrument changed")

    if sha256(SOURCE_003A_PLAN) != SOURCE_003A_PLAN_SHA256:
        raise SystemExit("FAIL source Ontology 003A plan changed")

    if sha256(SOURCE_003A_MANIFEST) != SOURCE_003A_MANIFEST_SHA256:
        raise SystemExit("FAIL source Ontology 003A request manifest changed")

    if sha256(SOURCE_CORPUS) != SOURCE_CORPUS_SHA256:
        raise SystemExit("FAIL source corpus changed")

    if sha256(PREDECESSOR_RESULT) != PREDECESSOR_RESULT_SHA256:
        raise SystemExit("FAIL predecessor execution result changed")

    if sha256(PREDECESSOR_ADJUDICATION) != PREDECESSOR_ADJUDICATION_SHA256:
        raise SystemExit("FAIL predecessor adjudication changed")

    plan = load_plan()

    if plan["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL 004 work-order identity drift")

    if plan["starting_sha"] != PLAN_STARTING_SHA:
        raise SystemExit("FAIL 004 starting SHA drift")

    if plan["planned_provider_requests"] != 54:
        raise SystemExit("FAIL 004 planned-provider-request count drift")

    if plan["planned_pairs"] != 18:
        raise SystemExit("FAIL 004 planned-pair count drift")

    if plan["architectural_change_authorized"] is not False:
        raise SystemExit("FAIL architecture change must remain unauthorized")

    if plan["production_code_changed"] is not False:
        raise SystemExit("FAIL production code must remain unchanged")

    if plan["production_prompt_changed"] is not False:
        raise SystemExit("FAIL production prompt must remain unchanged")

    if plan["provider_prerequisite"]["work_order"] != "OIC-NVIDIA-PROVIDER-QUALIFICATION-004":
        raise SystemExit("FAIL wrong provider prerequisite")

    stage2 = plan["arms"]["B_STAGED_DECOMPOSED"]["stage_2_nonforce_slots"]

    if stage2["consumes_stage_1_output"] is not False:
        raise SystemExit("FAIL B2 must not consume B1 output")

    if "normative_force" in stage2["allowed_slots"]:
        raise SystemExit("FAIL B2 allowed-slot vocabulary contains normative_force")

    validate_request_plan(plan)

    (
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    ) = load_context()

    # This is the already-frozen predecessor's offline-only preflight.
    predecessor.preflight()

    freeze: dict[str, Any] = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit("FAIL 004 instrument-freeze identity mismatch")

    if freeze["base_commit"] != INSTRUMENT_BASE_SHA:
        raise SystemExit("FAIL 004 instrument-freeze base mismatch")

    if freeze["plan_sha256"] != PLAN_SHA256:
        raise SystemExit("FAIL 004 freeze does not bind plan")

    if freeze["preregistration_sha256"] != PREREG_SHA256:
        raise SystemExit("FAIL 004 freeze does not bind preregistration")

    if freeze["predecessor_freeze_v0_1_sha256"] != FREEZE_V1_SHA256:
        raise SystemExit("FAIL 004 freeze does not bind preregistration freeze")

    if freeze["instrument_sha256"] != sha256(Path(__file__)):
        raise SystemExit("FAIL 004 instrument bytes differ from static freeze")

    if freeze["request_materialization_sha256"] != sha256(MATERIALIZATION_PATH):
        raise SystemExit("FAIL 004 request-manifest digest mismatch")

    if freeze["request_materialization_completed"] is not True:
        raise SystemExit("FAIL 004 request materialization not complete")

    if freeze["request_materialization_count"] != 54:
        raise SystemExit("FAIL 004 frozen request count mismatch")

    if freeze["instrument_implemented"] is not True:
        raise SystemExit("FAIL 004 instrument not marked implemented")

    if freeze["instrument_frozen"] is not True:
        raise SystemExit("FAIL 004 instrument not marked frozen")

    if freeze["provider_call_made"] is not False:
        raise SystemExit("FAIL 004 freeze records provider activity")

    if freeze["model_call_made"] is not False:
        raise SystemExit("FAIL 004 freeze records model activity")

    if freeze["live_run_executed"] is not False:
        raise SystemExit("FAIL 004 freeze records live execution")

    verify_manifest(
        plan=plan,
        corpus=corpus,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )

    return (
        plan,
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    )


def qualification_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RECEIPT.exists():
        raise SystemExit(
            "STOP Provider Qualification 004 receipt absent; "
            "Ontology 004 live execution unauthorized"
        )

    data: dict[str, Any] = json.loads(QUALIFICATION_RECEIPT.read_text(encoding="utf-8"))

    if data.get("work_order") != ("OIC-NVIDIA-PROVIDER-QUALIFICATION-004"):
        raise SystemExit("STOP wrong Provider Qualification 004 receipt")

    if data.get("disposition") != "QUALIFIED":
        raise SystemExit("STOP Provider Qualification 004 is not QUALIFIED")

    if data.get("semantic_successor_authorized") is not True:
        raise SystemExit("STOP Provider Qualification 004 did not authorize successor")

    target = data.get("semantic_successor_target")

    if isinstance(target, dict):
        target = target.get("work_order")

    if target != WORK_ORDER:
        raise SystemExit("STOP Provider Qualification 004 targets another work order")

    return data


def execute_request(
    *,
    item: dict[str, Any],
    specimen: dict[str, Any],
    plan: dict[str, Any],
    provider: ModelProvider,
    predecessor: ModuleType,
    predecessor_plan: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> StageAttempt:
    attempt = StageAttempt(
        ordinal=item["ordinal"],
        specimen_id=item["specimen_id"],
        run_index=item["run_index"],
        stage=item["stage"],
        outcome="PROVIDER_ERROR",
    )

    expected_request = request_for(
        item=item,
        specimen=specimen,
        plan=plan,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )

    guarded = ExactRequestProvider(
        delegate=provider,
        expected=expected_request,
    )

    stage = item["stage"]

    if stage == STAGE_A:
        try:
            result = v2.propose_with_prompt(
                binding=source._binding(
                    v1,
                    specimen,
                ),
                user_prompt=source.arm_b_user_prompt(
                    v2,
                    v1,
                    specimen,
                ),
                provider=guarded,
                proposer_id=("oic-definition-ontology-staged-decomposition-004-combined"),
            )
        except v2.ProposalBoundaryError as exc:
            attempt.outcome = "BOUNDARY_REJECTED"
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)

        except (
            v2.InterpretationProposalError,
            ModelProviderError,
        ) as exc:
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)

        else:
            attempt.outcome = "ACCEPTED"
            attempt.proposal = result.proposal
            attempt.proposed_force = predecessor.proposal_force(result.proposal)
            attempt.provider = result.provider
            attempt.model = result.model
            attempt.request_id = result.request_id
            attempt.raw_content_sha256 = result.raw_content_sha256

        return attempt

    try:
        response = guarded.complete(expected_request)
    except ModelProviderError as exc:
        attempt.error_type = type(exc).__name__
        attempt.error_message = str(exc)
        return attempt

    if stage == STAGE_B1:
        try:
            force = predecessor.parse_force_only(response.content)
        except predecessor.ForceOnlyBoundaryError as exc:
            attempt.outcome = "BOUNDARY_REJECTED"
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)
        else:
            attempt.outcome = "ACCEPTED"
            attempt.proposed_force = force

    elif stage == STAGE_B2:
        try:
            proposal = parse_nonforce(response.content)
        except NonforceBoundaryError as exc:
            attempt.outcome = "BOUNDARY_REJECTED"
            attempt.error_type = type(exc).__name__
            attempt.error_message = str(exc)
        else:
            attempt.outcome = "ACCEPTED"
            attempt.proposal = proposal

    else:
        raise SystemExit(f"FAIL unknown frozen stage: {stage}")

    if attempt.outcome == "ACCEPTED":
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
    predecessor: ModuleType,
    predecessor_plan: dict[str, Any],
    source: ModuleType,
    v2: ModuleType,
    v1: ModuleType,
) -> list[StageAttempt]:
    by_id = {item["specimen_id"]: item for item in corpus["specimens"]}

    attempts: list[StageAttempt] = []

    for index, item in enumerate(plan["provider_request_plan"]):
        attempt = execute_request(
            item=item,
            specimen=by_id[item["specimen_id"]],
            plan=plan,
            provider=provider,
            predecessor=predecessor,
            predecessor_plan=predecessor_plan,
            source=source,
            v2=v2,
            v1=v1,
        )

        attempts.append(attempt)

        if index < len(plan["provider_request_plan"]) - 1:
            time.sleep(PACING_SECONDS)

    return attempts


def adjudicability(
    attempts: Sequence[StageAttempt],
) -> dict[str, int | bool]:
    accepted = [item for item in attempts if item.outcome == "ACCEPTED"]

    accepted_keys = {
        (
            item.specimen_id,
            item.run_index,
            item.stage,
        )
        for item in accepted
    }

    complete = 0

    for specimen_id in (*PRIMARY, *CONTROLS):
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            if all(
                (
                    specimen_id,
                    run_index,
                    stage,
                )
                in accepted_keys
                for stage in STAGES
            ):
                complete += 1

    primary_complete = sum(
        all(
            (
                specimen_id,
                run_index,
                stage,
            )
            in accepted_keys
            for stage in STAGES
        )
        for specimen_id in PRIMARY
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        )
    )

    control_complete = sum(
        all(
            (
                specimen_id,
                run_index,
                stage,
            )
            in accepted_keys
            for stage in STAGES
        )
        for specimen_id in CONTROLS
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        )
    )

    gate = (
        len(attempts) == 54
        and len(accepted) == 54
        and complete == 18
        and primary_complete == 9
        and control_complete == 9
    )

    return {
        "planned_provider_requests": 54,
        "observed_attempts": len(attempts),
        "accepted_provider_requests": len(accepted),
        "complete_composite_pairs": complete,
        "primary_complete_pairs": primary_complete,
        "control_complete_pairs": control_complete,
        "adjudicable": gate,
    }


def _to_v1_attempt(
    v1: ModuleType,
    item: StageAttempt,
) -> Any:  # noqa: ANN401
    return v1.Attempt(
        ordinal=item.ordinal,
        specimen_id=item.specimen_id,
        run_index=item.run_index,
        arm=item.stage,
        outcome=item.outcome,
        proposal=item.proposal,
        provider=item.provider,
        model=item.model,
        request_id=item.request_id,
        raw_content_sha256=item.raw_content_sha256,
        error_type=item.error_type,
        error_message=item.error_message,
    )


def _single_slot_compatible(
    *,
    source: ModuleType,
    v1: ModuleType,
    corpus: dict[str, Any],
    specimen: dict[str, Any],
    attempt: StageAttempt,
    slot: str,
) -> bool:
    one = {
        **corpus,
        "specimens": [
            specimen,
        ],
    }

    metric = source._established(
        v1,
        one,
        [
            _to_v1_attempt(
                v1,
                attempt,
            )
        ],
    )

    slot_metric = metric["per_slot"][slot]

    return cast(
        bool,
        (
            slot_metric["expected_established"] == 1
            and slot_metric["proposed_compatible"] == 1
            and slot_metric["incompatible"] == 0
            and slot_metric["omitted"] == 0
        ),
    )


def _aggregate_slot_metrics(
    *,
    source: ModuleType,
    v1: ModuleType,
    corpus: dict[str, Any],
    attempts: Sequence[StageAttempt],
) -> dict[str, Any]:
    scoped = source.selected_corpus(corpus)

    return cast(
        dict[str, Any],
        source._established(
            v1,
            scoped,
            [
                _to_v1_attempt(
                    v1,
                    item,
                )
                for item in attempts
            ],
        ),
    )


def analyze(
    *,
    corpus: dict[str, Any],
    attempts: Sequence[StageAttempt],
    source: ModuleType,
    v1: ModuleType,
) -> dict[str, Any]:
    scoped = source.selected_corpus(corpus)

    by_id = {item["specimen_id"]: item for item in scoped["specimens"]}

    expected_force = {
        item["specimen_id"]: item["gold"]["expected_force"] for item in scoped["specimens"]
    }

    def attempt_for(
        specimen_id: str,
        run_index: int,
        stage: str,
    ) -> StageAttempt:
        return next(
            item
            for item in attempts
            if item.specimen_id == specimen_id
            and item.run_index == run_index
            and item.stage == stage
        )

    primary_force_observations: list[dict[str, Any]] = []
    control_force_observations: list[dict[str, Any]] = []

    b_primary_correct = 0
    control_b_only_force_defects: list[dict[str, Any]] = []

    force_cells: Counter[str] = Counter(
        {
            "A_ONLY_DEFECT": 0,
            "B_ONLY_DEFECT": 0,
            "BOTH_DEFECT": 0,
            "NEITHER_DEFECT": 0,
        }
    )

    for specimen_id in PRIMARY:
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            a = attempt_for(
                specimen_id,
                run_index,
                STAGE_A,
            )

            b1 = attempt_for(
                specimen_id,
                run_index,
                STAGE_B1,
            )

            expected = expected_force[specimen_id]

            a_correct = a.outcome == "ACCEPTED" and a.proposed_force == expected

            b_correct = b1.outcome == "ACCEPTED" and b1.proposed_force == expected

            if b_correct:
                b_primary_correct += 1

            a_defect = not a_correct
            b_defect = not b_correct

            if a_defect and b_defect:
                force_cells["BOTH_DEFECT"] += 1
            elif a_defect:
                force_cells["A_ONLY_DEFECT"] += 1
            elif b_defect:
                force_cells["B_ONLY_DEFECT"] += 1
            else:
                force_cells["NEITHER_DEFECT"] += 1

            primary_force_observations.append(
                {
                    "specimen_id": specimen_id,
                    "run_index": run_index,
                    "expected_force": expected,
                    "a_force": a.proposed_force,
                    "b1_force": b1.proposed_force,
                    "a_correct": a_correct,
                    "b1_correct": b_correct,
                }
            )

    for specimen_id in CONTROLS:
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            a = attempt_for(
                specimen_id,
                run_index,
                STAGE_A,
            )

            b1 = attempt_for(
                specimen_id,
                run_index,
                STAGE_B1,
            )

            expected = expected_force[specimen_id]

            a_correct = a.outcome == "ACCEPTED" and a.proposed_force == expected

            b_correct = b1.outcome == "ACCEPTED" and b1.proposed_force == expected

            if a_correct and not b_correct:
                control_b_only_force_defects.append(
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                        "expected_force": expected,
                        "b1_force": b1.proposed_force,
                    }
                )

            control_force_observations.append(
                {
                    "specimen_id": specimen_id,
                    "run_index": run_index,
                    "expected_force": expected,
                    "a_force": a.proposed_force,
                    "b1_force": b1.proposed_force,
                    "a_correct": a_correct,
                    "b1_correct": b_correct,
                }
            )

    b2_attempts = [item for item in attempts if item.stage == STAGE_B2]

    a_attempts = [item for item in attempts if item.stage == STAGE_A]

    b2_slots = _aggregate_slot_metrics(
        source=source,
        v1=v1,
        corpus=corpus,
        attempts=b2_attempts,
    )

    a_slots = _aggregate_slot_metrics(
        source=source,
        v1=v1,
        corpus=corpus,
        attempts=a_attempts,
    )

    control_b_only_slot_defects: list[dict[str, Any]] = []

    for specimen_id in CONTROLS:
        specimen = by_id[specimen_id]

        expected_nonforce = [
            slot
            for slot, spec in specimen["gold"]["expected_slots"].items()
            if slot != "normative_force" and spec["status"] == "ESTABLISHED"
        ]

        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            a = attempt_for(
                specimen_id,
                run_index,
                STAGE_A,
            )

            b2 = attempt_for(
                specimen_id,
                run_index,
                STAGE_B2,
            )

            for slot in expected_nonforce:
                a_ok = _single_slot_compatible(
                    source=source,
                    v1=v1,
                    corpus=corpus,
                    specimen=specimen,
                    attempt=a,
                    slot=slot,
                )

                b_ok = _single_slot_compatible(
                    source=source,
                    v1=v1,
                    corpus=corpus,
                    specimen=specimen,
                    attempt=b2,
                    slot=slot,
                )

                if a_ok and not b_ok:
                    control_b_only_slot_defects.append(
                        {
                            "specimen_id": specimen_id,
                            "run_index": run_index,
                            "slot": slot,
                        }
                    )

    def_metric = b2_slots["per_slot"]["definiendum"]

    definiens_metric = b2_slots["per_slot"]["definiens"]

    definition_defects = (
        int(def_metric["omitted"])
        + int(def_metric["incompatible"])
        + int(definiens_metric["omitted"])
        + int(definiens_metric["incompatible"])
    )

    regression = bool(control_b_only_force_defects or control_b_only_slot_defects)

    strict_definition_success = (
        def_metric["expected_established"] == 9
        and def_metric["proposed_compatible"] == 9
        and def_metric["omitted"] == 0
        and def_metric["incompatible"] == 0
        and definiens_metric["expected_established"] == 6
        and definiens_metric["proposed_compatible"] == 6
        and definiens_metric["omitted"] == 0
        and definiens_metric["incompatible"] == 0
    )

    if regression:
        disposition = "REGRESSION"

    elif b_primary_correct == 9 and strict_definition_success:
        disposition = "SUPPORTS_STAGED_DECOMPOSITION_VIABILITY"

    elif b_primary_correct <= 7 or definition_defects >= 2:
        disposition = "REFUTES_STAGED_DECOMPOSITION_VIABILITY"

    else:
        disposition = "INCONCLUSIVE"

    merged_examples: list[dict[str, Any]] = []

    for specimen_id in (*PRIMARY, *CONTROLS):
        for run_index in range(
            1,
            RUNS_PER_SPECIMEN + 1,
        ):
            b1 = attempt_for(
                specimen_id,
                run_index,
                STAGE_B1,
            )

            b2 = attempt_for(
                specimen_id,
                run_index,
                STAGE_B2,
            )

            if b1.proposed_force is not None and b2.proposal is not None:
                merged_examples.append(
                    {
                        "specimen_id": specimen_id,
                        "run_index": run_index,
                        "proposal": deterministic_merge(
                            force=b1.proposed_force,
                            nonforce=b2.proposal,
                        ),
                    }
                )

    return {
        "disposition": disposition,
        "primary_force": {
            "b_correct_planned_denominator": {
                "correct": b_primary_correct,
                "planned": 9,
            },
            "paired_cells": dict(force_cells),
            "observations": primary_force_observations,
        },
        "control_force": {
            "b_only_force_defect_count": len(control_b_only_force_defects),
            "b_only_force_defect_instances": control_b_only_force_defects,
            "observations": control_force_observations,
        },
        "staged_nonforce_slots": {
            "definiendum": def_metric,
            "definiens": definiens_metric,
            "all_slot_metrics": b2_slots["per_slot"],
        },
        "combined_arm_slots": {
            "definiendum": a_slots["per_slot"]["definiendum"],
            "definiens": a_slots["per_slot"]["definiens"],
        },
        "control_nonforce": {
            "b_only_slot_defect_count": len(control_b_only_slot_defects),
            "b_only_slot_defect_instances": control_b_only_slot_defects,
        },
        "provider_errors": sum(item.outcome == "PROVIDER_ERROR" for item in attempts),
        "boundary_rejections": sum(item.outcome == "BOUNDARY_REJECTED" for item in attempts),
        "deterministic_merged_proposals": merged_examples,
        "architectural_change_authorized": False,
        "descriptive_only": True,
    }


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help=("execute the frozen 54-request staged experiment exactly once"),
    )

    args = parser.parse_args(argv)

    (
        plan,
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    ) = preflight()

    print("PASS frozen Ontology 004 instrument verified; 54 exact provider requests")

    print("Arm A: exact 003A combined ontology-clarified condition")

    print("Arm B1: exact 003A force-only condition")

    print("Arm B2: independent non-force-slot extraction")

    print("deterministic local merge: no provider/model call")

    print("adjudicability gate: 54/54 ACCEPTED + all 18 composite pairs complete")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")

        return 0

    qualification = qualification_prerequisite()

    if RECEIPT_PATH.exists():
        raise SystemExit(f"STOP Ontology 004 receipt already exists: {RECEIPT_PATH}")

    from oic.nvidia_nim import NvidiaNimProvider

    attempts = execute_plan(
        plan=plan,
        corpus=corpus,
        provider=NvidiaNimProvider(),
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
    )

    gate = adjudicability(attempts)

    if gate["adjudicable"]:
        semantic_analysis = analyze(
            corpus=corpus,
            attempts=attempts,
            source=source,
            v1=v1,
        )

        scientific_disposition = semantic_analysis["disposition"]

        decision_evaluated = True

    else:
        semantic_analysis = None

        scientific_disposition = "NOT_ADJUDICABLE_PROVIDER_OR_BOUNDARY_FAILURE"

        decision_evaluated = False

    receipt = {
        "work_order": WORK_ORDER,
        "starting_sha": PLAN_STARTING_SHA,
        "plan_sha256": sha256(PLAN_PATH),
        "instrument_freeze_sha256": sha256(FREEZE_PATH),
        "provider_qualification_004_receipt_sha256": sha256(QUALIFICATION_RECEIPT),
        "provider_qualification_004_disposition": qualification["disposition"],
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

    RECEIPT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
