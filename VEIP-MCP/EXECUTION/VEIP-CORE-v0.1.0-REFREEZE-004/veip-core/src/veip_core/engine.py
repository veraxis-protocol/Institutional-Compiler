"""Frozen VEIP v0.1 adjudication pipeline."""

from __future__ import annotations

from typing import Any

from .canonical import sha256
from .dimensions import EvaluationRecord, derive
from .errors import ENGINE_VERSION, EngineError
from .manifest import verify_manifest
from .schema import ValidationFailure, matching_definition

REQUESTED_DIMENSION_MAP = {
    "CLAIM_SUPPORT": "claim_support",
    "OUTCOME": "outcome",
    "CURRENTNESS": "currentness",
    "TASK_COMPLETION": "task_completion",
}


def _record(code: str, evidence_id: str | None, role: str) -> EvaluationRecord:
    return {"code": code, "evidence_id": evidence_id, "evidence_role": role}


def _role(identifier: str, execution: set[str], outcome: set[str]) -> str:
    in_execution = identifier in execution
    in_outcome = identifier in outcome
    if in_execution and in_outcome:
        return "BOTH"
    return "EXECUTION" if in_execution else "OUTCOME"


def adjudicate(request_json: dict[str, Any]) -> dict[str, Any]:
    try:
        request_type = matching_definition(
            request_json, ("ClaimEvaluationRequest", "CompletionEvaluationRequest")
        )
    except (ValidationFailure, TypeError, ValueError) as exc:
        raise EngineError("SCHEMA_INVALID", f"Request failed frozen schema validation: {exc}") from None

    if request_json.get("expected_engine_version") not in (None, ENGINE_VERSION):
        raise EngineError(
            "ENGINE_VERSION_MISMATCH",
            f"Expected engine version must equal {ENGINE_VERSION}.",
        )

    pack = request_json["evidence_pack"]
    references = pack["references"]
    identifiers = [reference["evidence_id"] for reference in references]
    if len(identifiers) != len(set(identifiers)):
        raise EngineError("DUPLICATE_EVIDENCE_ID", "Duplicate evidence_id detected in evidence pack.")

    verify_manifest(pack)

    is_completion = request_type == "CompletionEvaluationRequest"
    if is_completion:
        target_source = request_json["requested_outcome"]
        execution_ids = set(request_json["execution_evidence_refs"])
        outcome_ids = set(request_json["outcome_evidence_refs"])
    else:
        target_source = request_json["assertion"]
        execution_ids = set()
        outcome_ids = set()
    target = {
        "subject_ref": target_source["subject_ref"],
        "extent_ref": target_source.get("extent_ref"),
    }

    relevant: dict[str, tuple[dict[str, Any], str]] = {}
    if is_completion:
        wanted = execution_ids | outcome_ids
        for reference in references:
            identifier = reference["evidence_id"]
            if identifier in wanted:
                relevant[identifier] = (
                    reference,
                    _role(identifier, execution_ids, outcome_ids),
                )

    records: list[EvaluationRecord] = []

    # Phase 10: evidence identity and payload digest.
    for identifier, (reference, role) in relevant.items():
        if (
            target["subject_ref"] is not None
            and "subject_ref" not in reference
        ) or (
            target["extent_ref"] is not None
            and "extent_ref" not in reference
        ):
            records.append(_record("MISSING_OBSERVATION_SUBJECT_OR_EXTENT", identifier, role))
        if "payload" in reference:
            if sha256(reference["payload"]) != reference["payload_sha256"]:
                records.append(_record("EVIDENCE_DIGEST_MISMATCH", identifier, role))

    # Phase 20: replay and evidence-reference resolution.
    context = request_json["evaluation_context"]
    replay = context.get("replay_snapshot")
    if replay is not None:
        seen_nonces = set(replay["observed_receipt_nonces"])
        for identifier, (reference, role) in relevant.items():
            receipt = reference.get("receipt")
            if receipt is not None and receipt["nonce"] in seen_nonces:
                records.append(_record("RECEIPT_REPLAYED", identifier, role))

    if is_completion:
        pack_ids = set(identifiers)
        unresolved = (execution_ids | outcome_ids) - pack_ids
        for identifier in unresolved:
            records.append(
                _record("EVIDENCE_REF_UNRESOLVED", identifier, _role(identifier, execution_ids, outcome_ids))
            )

    # Phase 30: exact subject/extent binding.
    for identifier, (reference, role) in relevant.items():
        if (
            "subject_ref" in reference
            and reference["subject_ref"] != target["subject_ref"]
        ) or (
            "extent_ref" in reference
            and reference["extent_ref"] != target["extent_ref"]
        ):
            records.append(_record("RECEIPT_WRONG_SUBJECT_OR_EXTENT", identifier, role))

    # Phase 40: registered scope.
    scope = context.get("scope_registry_snapshot")
    if (
        target["extent_ref"] is not None
        and scope is not None
        and target["extent_ref"] not in scope["active_extents"]
    ):
        records.append(_record("EXTENT_MATCHES_NOTHING", None, "GLOBAL"))

    # Phase 50 intentionally has no active typed currentness applicability relation.

    # Phase 60: channel provenance.
    warrant = context.get("channel_warrant_snapshot")
    for identifier, (reference, role) in relevant.items():
        channel = reference.get("channel_ref")
        if channel is None or warrant is None:
            records.append(_record("CHANNEL_BINDING_NOT_ESTABLISHED", identifier, role))
        elif channel not in warrant["bound_channels"]:
            records.append(_record("CHANNEL_NOT_LISTED_IN_WARRANT", identifier, role))

    # Phases 70 and reserved codes are intentionally inactive.
    records.append(_record("CHANNEL_INDEPENDENCE_NOT_ESTABLISHED", None, "GLOBAL"))

    dimensions = derive(records)
    requested_dimension = request_json["reliance_context"]["requested_dimension"]
    reliance_projection = {
        "requested_dimension": requested_dimension,
        "state": dimensions[REQUESTED_DIMENSION_MAP[requested_dimension]],
    }
    result: dict[str, Any] = {
        "engine_version": ENGINE_VERSION,
        "reliance_projection": reliance_projection,
        "dimensions": dimensions,
        "reason_codes": sorted({record["code"] for record in records}),
    }
    if is_completion:
        result["request_id"] = request_json["request_id"]
    else:
        result["claim_id"] = request_json["claim_id"]
    result["canonical_hash"] = sha256(result)
    return result
