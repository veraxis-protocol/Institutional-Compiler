from __future__ import annotations

import pytest

from oic.candidate_extraction import CandidateExtractionResult, propose_candidate_units
from oic.model_provider import ModelRequest, ModelResponse
from oic.review_docket import AgreementState, build_review_docket


class FakeProvider:
    def __init__(self, *, provider: str, model: str, content: str) -> None:
        self.provider = provider
        self.model = model
        self.content = content

    def complete(self, request: ModelRequest) -> ModelResponse:
        del request
        return ModelResponse(
            provider=self.provider,
            model=self.model,
            content=self.content,
            request_id=f"{self.provider}-request",
            raw={},
        )


def anchor() -> dict[str, object]:
    return {
        "anchor_id": "A-1",
        "source_id": "DOC-1",
        "node_id": "N-7",
        "content_hash": "sha256:" + ("a" * 64),
    }


def extract(provider: str, content: str) -> CandidateExtractionResult:
    return propose_candidate_units(
        source_text="Payments require Treasurer approval.",
        source_anchor=anchor(),
        provider=FakeProvider(provider=provider, model=f"{provider}-model", content=content),
    )


def test_identical_candidate_sets_are_exposed_without_admission() -> None:
    content = '{"candidates":[{"unit_type":"obligation","actor":"Treasurer","action":"approve"}]}'
    docket = build_review_docket([extract("p1", content), extract("p2", content)])
    assert docket.agreement_state is AgreementState.IDENTICAL
    assert docket.to_json()["institutional_admission"] is False
    assert len(docket.candidates_by_id) == 1


def test_divergent_candidate_sets_are_preserved_not_voted() -> None:
    left = '{"candidates":[{"unit_type":"obligation","actor":"Treasurer","action":"approve"}]}'
    right = '{"candidates":[{"unit_type":"permission","actor":"Treasurer","action":"approve"}]}'
    docket = build_review_docket([extract("p1", left), extract("p2", right)])
    assert docket.agreement_state is AgreementState.DIVERGENT
    assert len(docket.candidates_by_id) == 2


def test_all_empty_proposal_sets_are_explicit() -> None:
    docket = build_review_docket(
        [extract("p1", '{"candidates":[]}'), extract("p2", '{"candidates":[]}')]
    )
    assert docket.agreement_state is AgreementState.NO_CANDIDATES
    assert docket.candidates_by_id == {}


def test_docket_rejects_mixed_source_anchors() -> None:
    result = extract("p1", '{"candidates":[]}')
    other_anchor = dict(anchor())
    other_anchor["anchor_id"] = "A-2"
    other = propose_candidate_units(
        source_text="Text.",
        source_anchor=other_anchor,
        provider=FakeProvider(provider="p2", model="p2-model", content='{"candidates":[]}'),
    )
    with pytest.raises(ValueError, match="source_anchor"):
        build_review_docket([result, other])
