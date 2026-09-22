"""Frozen role-aware dimension derivation."""

from __future__ import annotations

from typing import TypedDict


class EvaluationRecord(TypedDict):
    code: str
    evidence_id: str | None
    evidence_role: str


def _has(records: list[EvaluationRecord], codes: set[str], roles: set[str]) -> bool:
    return any(record["code"] in codes and record["evidence_role"] in roles for record in records)


def derive(records: list[EvaluationRecord]) -> dict[str, str]:
    dimensions: dict[str, str] = {}
    dimensions["claim_support"] = (
        "NOT_ESTABLISHED"
        if _has(
            records,
            {
                "MISSING_OBSERVATION_SUBJECT_OR_EXTENT",
                "EVIDENCE_DIGEST_MISMATCH",
                "RECEIPT_WRONG_SUBJECT_OR_EXTENT",
                "EXTENT_MATCHES_NOTHING",
            },
            {"GLOBAL"},
        )
        else "UNAVAILABLE"
    )
    dimensions["execution"] = (
        "NOT_ESTABLISHED"
        if _has(
            records,
            {
                "EVIDENCE_DIGEST_MISMATCH",
                "RECEIPT_REPLAYED",
                "EVIDENCE_REF_UNRESOLVED",
                "RECEIPT_WRONG_SUBJECT_OR_EXTENT",
            },
            {"EXECUTION", "BOTH", "GLOBAL"},
        )
        else "UNAVAILABLE"
    )
    dimensions["outcome"] = (
        "NOT_ESTABLISHED"
        if _has(
            records,
            {
                "MISSING_OBSERVATION_SUBJECT_OR_EXTENT",
                "EVIDENCE_DIGEST_MISMATCH",
                "RECEIPT_REPLAYED",
                "EVIDENCE_REF_UNRESOLVED",
                "RECEIPT_WRONG_SUBJECT_OR_EXTENT",
                "EXTENT_MATCHES_NOTHING",
            },
            {"OUTCOME", "BOTH", "GLOBAL"},
        )
        else "UNAVAILABLE"
    )
    dimensions["currentness"] = (
        "NOT_ESTABLISHED"
        if _has(records, {"EVIDENCE_STALE"}, {"EXECUTION", "OUTCOME", "BOTH", "GLOBAL"})
        else "UNAVAILABLE"
    )
    dimensions["provenance_binding"] = (
        "NOT_ESTABLISHED"
        if _has(
            records,
            {
                "EVIDENCE_DIGEST_MISMATCH",
                "CHANNEL_NOT_LISTED_IN_WARRANT",
                "CHANNEL_BINDING_NOT_ESTABLISHED",
            },
            {"EXECUTION", "OUTCOME", "BOTH", "GLOBAL"},
        )
        else "UNAVAILABLE"
    )
    dimensions["channel_independence"] = (
        "NOT_ESTABLISHED"
        if _has(records, {"CHANNEL_INDEPENDENCE_NOT_ESTABLISHED"}, {"GLOBAL"})
        else "UNAVAILABLE"
    )
    dependencies = ("execution", "outcome", "currentness", "provenance_binding")
    dimensions["task_completion"] = (
        "NOT_ESTABLISHED"
        if any(dimensions[name] == "NOT_ESTABLISHED" for name in dependencies)
        else "UNAVAILABLE"
    )
    return dimensions
