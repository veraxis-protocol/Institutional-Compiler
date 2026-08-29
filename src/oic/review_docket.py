"""Deterministic review docket for model-proposed candidate normative units.

A docket exposes agreement and divergence among proposal sets. It never votes,
selects an authoritative interpretation, records admission, or advances candidate state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from oic.candidate_extraction import CandidateExtractionResult
from oic.model_provider import JsonObject


class AgreementState(Enum):
    """Literal relationship among candidate proposal sets, not an admission verdict."""

    NO_CANDIDATES = "NO_CANDIDATES"
    IDENTICAL = "IDENTICAL"
    DIVERGENT = "DIVERGENT"


@dataclass(frozen=True, slots=True)
class ProposalSet:
    """One provider's candidate set as presented to authorized review."""

    provider: str
    model: str
    request_id: str | None
    candidate_ids: tuple[str, ...]
    candidate_set_sha256: str
    raw_content_sha256: str

    def to_json(self) -> JsonObject:
        return {
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "candidate_ids": list(self.candidate_ids),
            "candidate_set_sha256": self.candidate_set_sha256,
            "raw_content_sha256": self.raw_content_sha256,
        }


@dataclass(frozen=True, slots=True)
class ReviewDocket:
    """Review material only. No field constitutes institutional admission."""

    docket_id: str
    source_anchor: JsonObject
    agreement_state: AgreementState
    proposal_sets: tuple[ProposalSet, ...]
    candidates_by_id: JsonObject

    def to_json(self) -> JsonObject:
        return {
            "candidate_contract": "source-grounded-candidate-003",
            "candidate_status": "candidate material only; not admitted or canonical meaning",
            "docket_id": self.docket_id,
            "source_anchor": dict(self.source_anchor),
            "agreement_state": self.agreement_state.value,
            "proposal_sets": [proposal.to_json() for proposal in self.proposal_sets],
            "candidates_by_id": dict(self.candidates_by_id),
            "institutional_admission": False,
        }


def build_review_docket(extractions: Sequence[CandidateExtractionResult]) -> ReviewDocket:
    """Build a deterministic comparison docket without choosing a winning proposal."""
    if not extractions:
        raise ValueError("at least one candidate extraction result is required")
    anchor = dict(extractions[0].source_anchor)
    if any(extraction.source_anchor != anchor for extraction in extractions[1:]):
        raise ValueError("all proposal sets in one review docket must share one source_anchor")
    proposals = tuple(_proposal_set(extraction) for extraction in extractions)
    fingerprints = {proposal.candidate_set_sha256 for proposal in proposals}
    all_empty = all(not proposal.candidate_ids for proposal in proposals)
    agreement = (
        AgreementState.NO_CANDIDATES
        if all_empty
        else (AgreementState.IDENTICAL if len(fingerprints) == 1 else AgreementState.DIVERGENT)
    )
    candidates: dict[str, object] = {}
    for extraction in extractions:
        for candidate in extraction.candidates:
            candidate_id = candidate.get("unit_id")
            if not isinstance(candidate_id, str):
                raise ValueError("candidate result is missing deterministic unit_id")
            existing = candidates.get(candidate_id)
            if existing is not None and existing != candidate:
                raise ValueError("same candidate unit_id resolved to different candidate content")
            candidates[candidate_id] = candidate
    docket_payload = {
        "source_anchor": anchor,
        "proposal_sets": [proposal.to_json() for proposal in proposals],
    }
    return ReviewDocket(
        docket_id=f"docket-{_sha256_json(docket_payload)[:24]}",
        source_anchor=anchor,
        agreement_state=agreement,
        proposal_sets=proposals,
        candidates_by_id=dict(sorted(candidates.items())),
    )


def _proposal_set(extraction: CandidateExtractionResult) -> ProposalSet:
    candidate_ids: list[str] = []
    for candidate in extraction.candidates:
        candidate_id = candidate.get("unit_id")
        if not isinstance(candidate_id, str):
            raise ValueError("candidate result is missing deterministic unit_id")
        candidate_ids.append(candidate_id)
    ordered_ids = tuple(sorted(candidate_ids))
    return ProposalSet(
        provider=extraction.provider,
        model=extraction.model,
        request_id=extraction.request_id,
        candidate_ids=ordered_ids,
        candidate_set_sha256=_sha256_json(list(ordered_ids)),
        raw_content_sha256=extraction.raw_content_sha256,
    )


def _sha256_json(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()
