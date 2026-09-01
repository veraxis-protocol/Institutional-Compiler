#!/usr/bin/env python3
"""Ontology Staged Decomposition 005.

Fresh full 54-cell replicate of frozen Ontology 004.

Semantic requests, ordering, endpoints and decision rules are preserved from
Ontology 004. The only planned methodological change is a bounded transport
recovery envelope:

- one retry maximum;
- only for exact ModelProviderError:
  "NVIDIA NIM connection timed out";
- exact same ModelRequest object;
- exact same frozen request projection SHA;
- both transport attempts preserved as evidence.

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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
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

WORK_ORDER: Final[str] = (
    "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005"
)

PREREG_COMMIT: Final[str] = (
    "067ec4bca5a802add89144c391db41a851f35cba"
)

PLAN_STARTING_SHA: Final[str] = (
    "3f7d96f1c83574e002e3a1972bcca0c6597e3c19"
)

BENCH = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-005"
)

PLAN_PATH = BENCH / "PLAN-v0.1.json"
PREREG_PATH = BENCH / "PREREGISTRATION.md"
FREEZE_V1_PATH = BENCH / "PLAN-FREEZE-v0.1.json"
TRANSPORT_PATH = BENCH / "TRANSPORT-RECOVERY-POLICY-v0.1.json"
BINDING_PATH = BENCH / "SEMANTIC-REPLICATION-BINDING-v0.1.json"

MATERIALIZATION_PATH = BENCH / "REQUEST-MATERIALIZATION-v0.1.json"
FREEZE_V2_PATH = BENCH / "PLAN-FREEZE-v0.2.json"

SOURCE004_SCRIPT = (
    ROOT / "scripts/characterize_definition_ontology_staged_decomposition_004.py"
)

SOURCE004_MANIFEST = (
    ROOT
    / "benchmarks/characterization/"
      "definition-ontology-staged-decomposition-004/"
      "REQUEST-MATERIALIZATION-v0.1.json"
)

ADAPTER_PATH = ROOT / "src/oic/nvidia_nim.py"

QUALIFICATION_RECEIPT = (
    ROOT
    / ".local/provider-qualification-receipts/"
      "OIC-NVIDIA-PROVIDER-QUALIFICATION-005.json"
)

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts/"
      "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005.json"
)

PLAN_SHA256: Final[str] = (
    "2dc022747d3eb4c9051e36d85f3a9d21fdf8330207057fdeb5c3a2883361ccfb"
)

PREREG_SHA256: Final[str] = (
    "df37d10254bd7e4b96329aaae1764494663619711a7bee2187fc447e27465b73"
)

TRANSPORT_SHA256: Final[str] = (
    "13cdf153a8394dfcb9ce64a468de2fda73cc5c705e02f4a7feb54147622d250f"
)

BINDING_SHA256: Final[str] = (
    "58204132703e9c613db68367c834c65a4008a671e3dcee92ef868029ea7bca14"
)

SOURCE004_SCRIPT_SHA256: Final[str] = (
    "d9e11c533a20e885b72307a3511a3f87ffb16c2669db15ea5717b4a6c334ba28"
)

SOURCE004_MANIFEST_SHA256: Final[str] = (
    "bb03876f765599fcf2630935195dfedf53d4ea759f13aba35f680f28bdf613e7"
)

PLANNED_SEMANTIC_REQUESTS: Final[int] = 54
TRANSPORT_CALL_CEILING: Final[int] = 108
PACING_SECONDS: Final[float] = 4.0
RETRY_DELAY_SECONDS: Final[float] = 4.0

ELIGIBLE_TIMEOUT: Final[str] = (
    "NVIDIA NIM connection timed out"
)

SEMANTIC_EQUALITY_KEYS: Final[tuple[str, ...]] = (
    "arms",
    "adjudicability_gate",
    "primary_endpoints",
    "control_endpoint",
    "primary_specimens",
    "control_specimens",
    "provider_request_plan",
    "interleaving",
    "planned_pairs",
    "planned_provider_requests",
    "planned_composite_observations",
    "pacing_seconds",
    "claim_ceiling",
)


class RequestBindingError(RuntimeError):
    """A live request differed from its preregistered semantic binding."""


@dataclass(slots=True)
class StaticContext:
    plan005: dict[str, Any]
    transport: dict[str, Any]
    binding: dict[str, Any]
    source004: ModuleType
    plan004: dict[str, Any]
    predecessor: ModuleType
    predecessor_plan: dict[str, Any]
    source: ModuleType
    v2: ModuleType
    v1: ModuleType
    corpus: dict[str, Any]


@dataclass(slots=True)
class TransportRecoveringProvider:
    """One-cell transport envelope with one exact-timeout retry maximum."""

    delegate: ModelProvider
    semantic_ordinal: int
    expected_request_sha256: str
    sleep_fn: Callable[[float], None] = time.sleep
    calls: list[dict[str, Any]] = field(default_factory=list)

    def _projection_sha(
        self,
        request: ModelRequest,
    ) -> str:
        payload = {
            "system_prompt": request.system_prompt,
            "user_prompt": request.user_prompt,
            "response_format": request.response_format,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(encoded).hexdigest()

    def _verify_binding(
        self,
        request: ModelRequest,
    ) -> str:
        actual = self._projection_sha(request)

        if actual != self.expected_request_sha256:
            raise RequestBindingError(
                "live request projection differs from frozen Ontology 005 binding"
            )

        return actual

    def _record_success(
        self,
        *,
        transport_index: int,
        request: ModelRequest,
        response: ModelResponse,
        same_object_as_first: bool,
    ) -> None:
        self.calls.append(
            {
                "semantic_ordinal": self.semantic_ordinal,
                "transport_attempt_index": transport_index,
                "outcome": "ACCEPTED",
                "request_projection_sha256":
                    self._projection_sha(request),
                "same_request_object_as_first":
                    same_object_as_first,
                "provider": response.provider,
                "model": response.model,
                "request_id": response.request_id,
                "raw_content_sha256": hashlib.sha256(
                    response.content.encode("utf-8")
                ).hexdigest(),
                "error_type": None,
                "error_message": None,
            }
        )

    def _record_error(
        self,
        *,
        transport_index: int,
        request: ModelRequest,
        exc: ModelProviderError,
        same_object_as_first: bool,
    ) -> None:
        self.calls.append(
            {
                "semantic_ordinal": self.semantic_ordinal,
                "transport_attempt_index": transport_index,
                "outcome": "PROVIDER_ERROR",
                "request_projection_sha256":
                    self._projection_sha(request),
                "same_request_object_as_first":
                    same_object_as_first,
                "provider": None,
                "model": None,
                "request_id": None,
                "raw_content_sha256": None,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        )

    def complete(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self._verify_binding(request)

        first_object_id = id(request)

        try:
            response = self.delegate.complete(request)
        except ModelProviderError as exc:
            self._record_error(
                transport_index=1,
                request=request,
                exc=exc,
                same_object_as_first=True,
            )

            eligible = (
                type(exc).__name__ == "ModelProviderError"
                and str(exc) == ELIGIBLE_TIMEOUT
            )

            if not eligible:
                raise

            self.sleep_fn(RETRY_DELAY_SECONDS)

            if id(request) != first_object_id:
                raise RequestBindingError(
                    "retry did not preserve exact ModelRequest object identity"
                )

            self._verify_binding(request)

            try:
                retry_response = self.delegate.complete(request)
            except ModelProviderError as retry_exc:
                self._record_error(
                    transport_index=2,
                    request=request,
                    exc=retry_exc,
                    same_object_as_first=(
                        id(request) == first_object_id
                    ),
                )

                raise

            self._record_success(
                transport_index=2,
                request=request,
                response=retry_response,
                same_object_as_first=(
                    id(request) == first_object_id
                ),
            )

            return retry_response

        self._record_success(
            transport_index=1,
            request=request,
            response=response,
            same_object_as_first=True,
        )

        return response


def sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    value: Any = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise SystemExit(
            f"FAIL expected JSON object: {path}"
        )

    return value


def load_module(
    name: str,
    path: Path,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise SystemExit(
            f"FAIL cannot load frozen module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)

    return module


def prereg_context() -> StaticContext:
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 plan digest mismatch"
        )

    if sha256(PREREG_PATH) != PREREG_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 preregistration digest mismatch"
        )

    if sha256(TRANSPORT_PATH) != TRANSPORT_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 transport-policy digest mismatch"
        )

    if sha256(BINDING_PATH) != BINDING_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 semantic-binding digest mismatch"
        )

    if sha256(SOURCE004_SCRIPT) != SOURCE004_SCRIPT_SHA256:
        raise SystemExit(
            "FAIL frozen Ontology 004 source instrument changed"
        )

    if sha256(SOURCE004_MANIFEST) != SOURCE004_MANIFEST_SHA256:
        raise SystemExit(
            "FAIL frozen Ontology 004 request manifest changed"
        )

    plan005 = load_json(PLAN_PATH)
    transport = load_json(TRANSPORT_PATH)
    binding = load_json(BINDING_PATH)
    freeze_v1 = load_json(FREEZE_V1_PATH)

    if plan005["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 005 work-order identity drift"
        )

    if plan005["starting_sha"] != PLAN_STARTING_SHA:
        raise SystemExit(
            "FAIL Ontology 005 starting SHA drift"
        )

    if freeze_v1["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 005 preregistration freeze identity drift"
        )

    if freeze_v1["base_commit"] != PLAN_STARTING_SHA:
        raise SystemExit(
            "FAIL Ontology 005 preregistration freeze base drift"
        )

    if freeze_v1["plan_sha256"] != PLAN_SHA256:
        raise SystemExit(
            "FAIL freeze v0.1 plan binding mismatch"
        )

    if freeze_v1["preregistration_sha256"] != PREREG_SHA256:
        raise SystemExit(
            "FAIL freeze v0.1 preregistration binding mismatch"
        )

    if (
        freeze_v1["transport_recovery_policy_sha256"]
        != TRANSPORT_SHA256
    ):
        raise SystemExit(
            "FAIL freeze v0.1 transport binding mismatch"
        )

    if (
        freeze_v1["semantic_replication_binding_sha256"]
        != BINDING_SHA256
    ):
        raise SystemExit(
            "FAIL freeze v0.1 semantic-binding mismatch"
        )

    if freeze_v1["instrument_implemented"] is not False:
        raise SystemExit(
            "FAIL preregistration freeze unexpectedly records implementation"
        )

    if freeze_v1["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL preregistration freeze unexpectedly records live execution"
        )

    if (
        plan005["provider_prerequisite"]["work_order"]
        != "OIC-NVIDIA-PROVIDER-QUALIFICATION-005"
    ):
        raise SystemExit(
            "FAIL wrong Provider Qualification 005 prerequisite"
        )

    if (
        plan005["provider_prerequisite"][
            "required_semantic_successor_target"
        ]
        != WORK_ORDER
    ):
        raise SystemExit(
            "FAIL Provider Qualification 005 targets wrong successor"
        )

    if plan005["planned_semantic_requests"] != 54:
        raise SystemExit(
            "FAIL Ontology 005 semantic request count drift"
        )

    if plan005["provider_transport_call_ceiling"] != 108:
        raise SystemExit(
            "FAIL Ontology 005 transport ceiling drift"
        )

    if (
        plan005["semantic_replication"][
            "ontology_004_outputs_reused"
        ]
        is not False
    ):
        raise SystemExit(
            "FAIL Ontology 004 semantic outputs may not be reused"
        )

    if (
        plan005["semantic_replication"][
            "analysis_population"
        ]
        != "ONTOLOGY_005_ONLY"
    ):
        raise SystemExit(
            "FAIL Ontology 005 analysis population drift"
        )

    if (
        transport["retry"]["max_retries_per_semantic_request"]
        != 1
    ):
        raise SystemExit(
            "FAIL transport retry budget drift"
        )

    if (
        transport["retry"]["eligible_exception_type"]
        != "ModelProviderError"
    ):
        raise SystemExit(
            "FAIL transport retry exception-class drift"
        )

    if (
        transport["retry"]["eligible_exact_error_message"]
        != ELIGIBLE_TIMEOUT
    ):
        raise SystemExit(
            "FAIL transport retry message drift"
        )

    if (
        transport["retry"][
            "same_model_request_object_required"
        ]
        is not True
    ):
        raise SystemExit(
            "FAIL exact request-object retry requirement absent"
        )

    if (
        transport["retry"][
            "same_request_projection_sha256_required"
        ]
        is not True
    ):
        raise SystemExit(
            "FAIL exact request-hash retry requirement absent"
        )

    for forbidden in (
        "retry_after_boundary_rejection",
        "retry_after_nonretryable_provider_error",
        "retry_after_accepted_response",
        "retry_after_semantic_parse_failure",
    ):
        if transport["retry"][forbidden] is not False:
            raise SystemExit(
                f"FAIL forbidden retry class enabled: {forbidden}"
            )

    if transport["semantic_change"] is not False:
        raise SystemExit(
            "FAIL transport policy records semantic change"
        )

    if transport["production_code_change"] is not False:
        raise SystemExit(
            "FAIL transport policy records production-code change"
        )

    if transport["production_prompt_change"] is not False:
        raise SystemExit(
            "FAIL transport policy records production-prompt change"
        )

    if sha256(ADAPTER_PATH) != transport["provider_adapter_sha256"]:
        raise SystemExit(
            "FAIL NVIDIA provider adapter differs from preregistered bytes"
        )

    source004 = load_module(
        "_ontology004_for_005",
        SOURCE004_SCRIPT,
    )

    (
        plan004,
        predecessor,
        predecessor_plan,
        source,
        v2,
        v1,
        corpus,
    ) = source004.preflight()

    for key in SEMANTIC_EQUALITY_KEYS:
        if plan005[key] != plan004[key]:
            raise SystemExit(
                f"FAIL Ontology 005 semantic design drift at {key}"
            )

    source_manifest = load_json(
        SOURCE004_MANIFEST
    )

    if source_manifest["request_count"] != 54:
        raise SystemExit(
            "FAIL source Ontology 004 manifest count drift"
        )

    if binding["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 005 binding identity drift"
        )

    if binding["semantic_request_population"] != 54:
        raise SystemExit(
            "FAIL Ontology 005 binding population drift"
        )

    if binding["ontology_004_semantic_outputs_reused"] is not False:
        raise SystemExit(
            "FAIL binding permits Ontology 004 output reuse"
        )

    if binding["partial_completion_of_004"] is not False:
        raise SystemExit(
            "FAIL Ontology 005 may not be a partial 004 completion"
        )

    if binding["source_manifest_sha256"] != SOURCE004_MANIFEST_SHA256:
        raise SystemExit(
            "FAIL Ontology 005 source-manifest binding mismatch"
        )

    return StaticContext(
        plan005=plan005,
        transport=transport,
        binding=binding,
        source004=source004,
        plan004=plan004,
        predecessor=predecessor,
        predecessor_plan=predecessor_plan,
        source=source,
        v2=v2,
        v1=v1,
        corpus=corpus,
    )


def semantic_materialization(
    ctx: StaticContext,
) -> list[dict[str, Any]]:
    materialized = ctx.source004.materialize_requests(
        plan=ctx.plan004,
        corpus=ctx.corpus,
        predecessor=ctx.predecessor,
        predecessor_plan=ctx.predecessor_plan,
        source=ctx.source,
        v2=ctx.v2,
        v1=ctx.v1,
    )

    if len(materialized) != 54:
        raise SystemExit(
            "FAIL Ontology 005 did not materialize exactly 54 requests"
        )

    source_manifest = load_json(
        SOURCE004_MANIFEST
    )

    if materialized != source_manifest["requests"]:
        raise SystemExit(
            "FAIL Ontology 005 requests differ from frozen Ontology 004"
        )

    binding_requests = ctx.binding["requests"]

    if len(binding_requests) != 54:
        raise SystemExit(
            "FAIL Ontology 005 semantic binding count drift"
        )

    for source_item, bound_item in zip(
        materialized,
        binding_requests,
        strict=True,
    ):
        expected = {
            "ordinal": source_item["ordinal"],
            "specimen_id": source_item["specimen_id"],
            "run_index": source_item["run_index"],
            "stage": source_item["stage"],
            "request_sha256": source_item["request_sha256"],
        }

        if bound_item != expected:
            raise SystemExit(
                "FAIL Ontology 005 request binding differs from materialization"
            )

    counts = Counter(
        item["stage"]
        for item in materialized
    )

    if counts != Counter(
        {
            "A_COMBINED": 18,
            "B1_FORCE": 18,
            "B2_NONFORCE_SLOTS": 18,
        }
    ):
        raise SystemExit(
            "FAIL Ontology 005 stage population drift"
        )

    return materialized


def materialization_document(
    ctx: StaticContext,
) -> dict[str, Any]:
    requests = semantic_materialization(ctx)

    return {
        "work_order": WORK_ORDER,
        "source_work_order":
            "OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-004",
        "source_request_materialization_sha256":
            SOURCE004_MANIFEST_SHA256,
        "plan_sha256": PLAN_SHA256,
        "preregistration_sha256": PREREG_SHA256,
        "transport_recovery_policy_sha256":
            TRANSPORT_SHA256,
        "semantic_replication_binding_sha256":
            BINDING_SHA256,
        "instrument_sha256": sha256(
            Path(__file__)
        ),
        "request_count": 54,
        "semantic_request_equivalence":
            "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_004",
        "request_order_equivalence":
            "IDENTICAL_TO_FROZEN_ONTOLOGY_004",
        "ontology_004_semantic_outputs_reused":
            False,
        "provider_constructed": False,
        "network_request_made": False,
        "requests": requests,
    }


def write_materialization(
    ctx: StaticContext,
) -> None:
    if MATERIALIZATION_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 005 materialization already exists: "
            f"{MATERIALIZATION_PATH}"
        )

    document = materialization_document(ctx)

    MATERIALIZATION_PATH.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"materialization written: {MATERIALIZATION_PATH}"
    )


def verify_materialization(
    ctx: StaticContext,
) -> dict[str, Any]:
    if not MATERIALIZATION_PATH.exists():
        raise SystemExit(
            "FAIL Ontology 005 request materialization absent"
        )

    actual = load_json(
        MATERIALIZATION_PATH
    )

    expected = materialization_document(
        ctx
    )

    if actual != expected:
        raise SystemExit(
            "FAIL Ontology 005 materialization differs from recomputation"
        )

    return actual


def verify_freeze_v2(
    ctx: StaticContext,
    materialization: dict[str, Any],
) -> dict[str, Any]:
    del ctx
    del materialization

    if not FREEZE_V2_PATH.exists():
        raise SystemExit(
            "FAIL Ontology 005 instrument freeze v0.2 absent"
        )

    freeze = load_json(
        FREEZE_V2_PATH
    )

    if freeze["work_order"] != WORK_ORDER:
        raise SystemExit(
            "FAIL Ontology 005 freeze identity drift"
        )

    if freeze["base_commit"] != PREREG_COMMIT:
        raise SystemExit(
            "FAIL Ontology 005 freeze base drift"
        )

    expected_hashes = {
        "plan_sha256": sha256(PLAN_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "preregistration_freeze_v0_1_sha256":
            sha256(FREEZE_V1_PATH),
        "transport_recovery_policy_sha256":
            sha256(TRANSPORT_PATH),
        "semantic_replication_binding_sha256":
            sha256(BINDING_PATH),
        "instrument_sha256":
            sha256(Path(__file__)),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
    }

    for key, value in expected_hashes.items():
        if freeze[key] != value:
            raise SystemExit(
                f"FAIL Ontology 005 freeze binding mismatch: {key}"
            )

    if freeze["request_materialization_count"] != 54:
        raise SystemExit(
            "FAIL Ontology 005 frozen request count drift"
        )

    if freeze["semantic_request_equivalence"] != (
        "BYTE_IDENTICAL_TO_FROZEN_ONTOLOGY_004"
    ):
        raise SystemExit(
            "FAIL Ontology 005 semantic equivalence drift"
        )

    if freeze["instrument_implemented"] is not True:
        raise SystemExit(
            "FAIL Ontology 005 instrument not marked implemented"
        )

    if freeze["instrument_frozen"] is not True:
        raise SystemExit(
            "FAIL Ontology 005 instrument not marked frozen"
        )

    if freeze["transport_recovery_implemented"] is not True:
        raise SystemExit(
            "FAIL transport recovery not marked implemented"
        )

    if freeze["provider_call_made"] is not False:
        raise SystemExit(
            "FAIL static freeze records provider activity"
        )

    if freeze["model_call_made"] is not False:
        raise SystemExit(
            "FAIL static freeze records model activity"
        )

    if freeze["network_request_made"] is not False:
        raise SystemExit(
            "FAIL static freeze records network activity"
        )

    if freeze["live_run_executed"] is not False:
        raise SystemExit(
            "FAIL static freeze records live execution"
        )

    if freeze["architecture_change_authorized"] is not False:
        raise SystemExit(
            "FAIL static freeze authorizes architecture change"
        )

    return freeze


def static_preflight() -> StaticContext:
    ctx = prereg_context()

    materialization = verify_materialization(
        ctx
    )

    verify_freeze_v2(
        ctx,
        materialization,
    )

    return ctx


def qualification_prerequisite() -> dict[str, Any]:
    if not QUALIFICATION_RECEIPT.exists():
        raise SystemExit(
            "STOP Provider Qualification 005 receipt absent; "
            "Ontology 005 live execution unauthorized"
        )

    data = load_json(
        QUALIFICATION_RECEIPT
    )

    if data.get("work_order") != (
        "OIC-NVIDIA-PROVIDER-QUALIFICATION-005"
    ):
        raise SystemExit(
            "STOP wrong Provider Qualification 005 receipt"
        )

    if data.get("disposition") != "QUALIFIED":
        raise SystemExit(
            "STOP Provider Qualification 005 is not QUALIFIED"
        )

    if data.get("semantic_successor_authorized") is not True:
        raise SystemExit(
            "STOP Provider Qualification 005 did not authorize successor"
        )

    target: Any = data.get(
        "semantic_successor_target"
    )

    if isinstance(target, dict):
        target = target.get(
            "work_order"
        )

    if target != WORK_ORDER:
        raise SystemExit(
            "STOP Provider Qualification 005 targets another work order"
        )

    return data


def execute_semantic_plan(
    *,
    ctx: StaticContext,
    provider: ModelProvider,
) -> tuple[
    list[Any],
    list[dict[str, Any]],
]:
    materialized = semantic_materialization(
        ctx
    )

    expected_sha = {
        item["ordinal"]:
            item["request_sha256"]
        for item in materialized
    }

    by_id = {
        item["specimen_id"]: item
        for item in ctx.corpus["specimens"]
    }

    attempts: list[Any] = []
    transport_calls: list[dict[str, Any]] = []

    provider_plan = ctx.plan004[
        "provider_request_plan"
    ]

    for index, item in enumerate(
        provider_plan
    ):
        ordinal = int(
            item["ordinal"]
        )

        print(
            f"[{ordinal:02d}/54] START "
            f"{item['specimen_id']} "
            f"run={item['run_index']} "
            f"stage={item['stage']}"
        )

        bounded = TransportRecoveringProvider(
            delegate=provider,
            semantic_ordinal=ordinal,
            expected_request_sha256=
                expected_sha[ordinal],
        )

        semantic_attempt = (
            ctx.source004.execute_request(
                item=item,
                specimen=by_id[
                    item["specimen_id"]
                ],
                plan=ctx.plan004,
                provider=bounded,
                predecessor=ctx.predecessor,
                predecessor_plan=
                    ctx.predecessor_plan,
                source=ctx.source,
                v2=ctx.v2,
                v1=ctx.v1,
            )
        )

        attempts.append(
            semantic_attempt
        )

        transport_calls.extend(
            bounded.calls
        )

        if len(transport_calls) > TRANSPORT_CALL_CEILING:
            raise SystemExit(
                "FAIL transport-call ceiling exceeded"
            )

        print(
            f"[{ordinal:02d}/54] DONE "
            f"outcome={semantic_attempt.outcome} "
            f"transport_calls={len(bounded.calls)}"
        )

        if (
            index
            < len(provider_plan) - 1
        ):
            time.sleep(
                PACING_SECONDS
            )

    return (
        attempts,
        transport_calls,
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )

    parser.add_argument(
        "--materialize",
        action="store_true",
        help=(
            "write the frozen 54-request offline materialization; "
            "no provider is constructed"
        ),
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "execute the frozen 54-cell semantic replicate "
            "after Provider Qualification 005"
        ),
    )

    args = parser.parse_args(
        argv
    )

    if args.materialize and args.live:
        raise SystemExit(
            "FAIL --materialize and --live are mutually exclusive"
        )

    if args.materialize:
        ctx = prereg_context()

        write_materialization(
            ctx
        )

        print(
            "PASS Ontology 005 materialized 54 exact requests"
        )
        print(
            "semantic requests vs 004: BYTE-IDENTICAL"
        )
        print(
            "provider constructed: FALSE"
        )
        print(
            "network request made: FALSE"
        )

        return 0

    ctx = static_preflight()

    print(
        "PASS frozen Ontology 005 instrument verified"
    )
    print(
        "semantic requests: 54 exact / byte-identical to Ontology 004"
    )
    print(
        "transport retry: one exact NIM timeout retry maximum"
    )
    print(
        "semantic output reuse from Ontology 004: FALSE"
    )

    if not args.live:
        print(
            "offline preflight only; no provider was constructed "
            "and no request was made"
        )

        return 0

    qualification = (
        qualification_prerequisite()
    )

    if RECEIPT_PATH.exists():
        raise SystemExit(
            f"STOP Ontology 005 receipt already exists: "
            f"{RECEIPT_PATH}"
        )

    from oic.nvidia_nim import (  # noqa: PLC0415
        NvidiaNimProvider,
    )

    attempts, transport_calls = (
        execute_semantic_plan(
            ctx=ctx,
            provider=NvidiaNimProvider(),
        )
    )

    gate = ctx.source004.adjudicability(
        attempts
    )

    if gate["adjudicable"]:
        semantic_analysis = (
            ctx.source004.analyze(
                corpus=ctx.corpus,
                attempts=attempts,
                source=ctx.source,
                v1=ctx.v1,
            )
        )

        scientific_disposition = (
            semantic_analysis[
                "disposition"
            ]
        )

        decision_evaluated = True

    else:
        semantic_analysis = None

        scientific_disposition = (
            "NOT_ADJUDICABLE_PROVIDER_OR_BOUNDARY_FAILURE"
        )

        decision_evaluated = False

    retry_cells = sorted(
        {
            int(item["semantic_ordinal"])
            for item in transport_calls
            if int(
                item["transport_attempt_index"]
            )
            == 2
        }
    )

    receipt = {
        "work_order": WORK_ORDER,
        "preregistration_commit":
            PREREG_COMMIT,
        "plan_sha256":
            sha256(PLAN_PATH),
        "instrument_freeze_sha256":
            sha256(FREEZE_V2_PATH),
        "request_materialization_sha256":
            sha256(MATERIALIZATION_PATH),
        "provider_qualification_005_receipt_sha256":
            sha256(QUALIFICATION_RECEIPT),
        "provider_qualification_005_disposition":
            qualification["disposition"],
        "attempts": [
            item.to_json()
            for item in attempts
        ],
        "transport_attempts":
            transport_calls,
        "transport_calls_observed":
            len(transport_calls),
        "transport_retry_cells":
            retry_cells,
        "transport_retries_used":
            len(retry_cells),
        "transport_call_ceiling":
            TRANSPORT_CALL_CEILING,
        "adjudicability":
            gate,
        "scientific_disposition":
            scientific_disposition,
        "semantic_analysis":
            semantic_analysis,
        "live_run_executed":
            True,
        "semantic_decision_rule_evaluated":
            decision_evaluated,
        "ontology_004_semantic_outputs_reused":
            False,
        "canonicalization_performed":
            False,
        "institutional_ir_constructed":
            False,
        "architectural_change_authorized":
            False,
        "independent_validation_claim":
            False,
        "self_adjudication":
            "NOT SELF-ADJUDICATED",
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

    print(
        f"receipt written: {RECEIPT_PATH}"
    )

    print(
        f"transport calls observed: "
        f"{len(transport_calls)}"
    )

    print(
        f"transport retries used: "
        f"{len(retry_cells)}"
    )

    print(
        f"scientific disposition: "
        f"{scientific_disposition}"
    )

    print(
        f"semantic decision evaluated: "
        f"{decision_evaluated}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
