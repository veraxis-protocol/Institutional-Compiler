from __future__ import annotations

import json

import pytest

from oic.candidate_extraction import CandidateExtractionResult, propose_candidate_units
from oic.model_provider import ModelRequest, ModelResponse
from oic.review_docket import AgreementState, build_review_docket


class FakeProvider:
    def __init__(self, provider: str, content: str) -> None:
        self.provider = provider
        self.content = content

    def complete(self, request: ModelRequest) -> ModelResponse:
        del request
        return ModelResponse(
            provider=self.provider,
            model=f"{self.provider}-model",
            content=self.content,
            request_id=f"{self.provider}-request",
            raw={},
        )


SOURCE = "Payments require Treasurer approval."


def anchor(identifier: str = "A-1") -> dict[str, object]:
    return {
        "anchor_id": identifier,
        "source_id": "DOC-1",
        "node_id": "N-7",
        "content_hash": "sha256:" + ("a" * 64),
    }


def extract(
    provider: str, unit_type: str = "obligation", *, empty: bool = False
) -> CandidateExtractionResult:
    body = {"candidates": [] if empty else [{"candidate_span": SOURCE, "unit_type": unit_type}]}
    return propose_candidate_units(
        source_text=SOURCE,
        source_anchor=anchor(),
        provider=FakeProvider(provider, json.dumps(body)),
    )


def test_docket_exposes_minimal_candidate_without_admission_or_role_placeholders() -> None:
    docket = build_review_docket([extract("p1"), extract("p2")])
    rendered = docket.to_json()
    assert docket.agreement_state is AgreementState.IDENTICAL
    assert rendered["institutional_admission"] is False
    assert rendered["candidate_contract"] == "source-grounded-candidate-003"
    assert "not admitted or canonical meaning" in rendered["candidate_status"]
    item = next(iter(docket.candidates_by_id.values()))
    assert item["candidate_span"] == SOURCE
    assert item["unit_type"] == "obligation"
    assert item["epistemic_state"] == "uncertain"
    assert item["interpretation_state"] == "extracted"
    assert item["source_anchors"] == [anchor()]
    for removed in (
        "actor",
        "action",
        "object",
        "target",
        "conditions",
        "exceptions",
        "evidence_requirements",
    ):
        assert removed not in item


def test_divergent_provisional_types_are_preserved_not_voted() -> None:
    docket = build_review_docket([extract("p1"), extract("p2", "mandate")])
    assert docket.agreement_state is AgreementState.DIVERGENT
    assert len(docket.candidates_by_id) == 2


def test_all_empty_proposal_sets_are_explicit() -> None:
    docket = build_review_docket([extract("p1", empty=True), extract("p2", empty=True)])
    assert docket.agreement_state is AgreementState.NO_CANDIDATES
    assert docket.candidates_by_id == {}


def test_docket_rejects_mixed_source_anchors() -> None:
    other = propose_candidate_units(
        source_text="Text.",
        source_anchor=anchor("A-2"),
        provider=FakeProvider("p2", '{"candidates":[]}'),
    )
    with pytest.raises(ValueError, match="source_anchor"):
        build_review_docket([extract("p1", empty=True), other])
