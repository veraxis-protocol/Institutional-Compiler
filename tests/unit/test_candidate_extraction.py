from __future__ import annotations

import json

import pytest

from oic.candidate_extraction import (
    _ALLOWED_UNIT_TYPES,
    _MODEL_FORBIDDEN_AUTHORITY_KEYS,
    _REMOVED_SEMANTIC_ROLE_KEYS,
    _UNIT_TYPES,
    CandidateBoundaryError,
    CandidateExtractionResult,
    CandidateGroundingError,
    check_source_grounding,
    propose_candidate_units,
)
from oic.model_provider import ModelRequest, ModelResponse


class FakeProvider:
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            provider="fake", model="fake-model", content=self.content, request_id="req-1", raw={}
        )


SOURCE = "A payment above $10,000 requires approval by the Chief Financial Officer."


def anchor(suffix: str = "1") -> dict[str, object]:
    return {
        "anchor_id": f"A-{suffix}",
        "source_id": "DOC-1",
        "node_id": "N-7",
        "content_hash": "sha256:" + ("a" * 64),
    }


def extract(
    content: str, *, source: str = SOURCE, source_anchor: dict[str, object] | None = None
) -> CandidateExtractionResult:
    return propose_candidate_units(
        source_text=source, source_anchor=source_anchor or anchor(), provider=FakeProvider(content)
    )


def candidate(span: str, unit_type: str = "obligation") -> str:
    return json.dumps({"candidates": [{"candidate_span": span, "unit_type": unit_type}]})


def outbound(source: str = SOURCE) -> ModelRequest:
    provider = FakeProvider('{"candidates":[]}')
    propose_candidate_units(source_text=source, source_anchor=anchor(), provider=provider)
    return provider.requests[0]


def test_literal_grounded_candidate_span_is_accepted() -> None:
    result = extract(candidate(SOURCE))
    item = result.candidates[0]
    assert item["candidate_span"] == SOURCE
    assert item["unit_type"] == "obligation"
    assert item["interpretation_state"] == "extracted"
    assert item["epistemic_state"] == "uncertain"
    assert item["source_anchors"] == [anchor()]
    assert set(item) == {
        "unit_id",
        "candidate_span",
        "unit_type",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    }


@pytest.mark.parametrize(
    "span",
    [
        "Payments above $10,000 need CFO approval.",
        "The Treasurer must approve this payment.",
        "   ",
    ],
)
def test_paraphrased_invented_and_blank_spans_fail_closed(span: str) -> None:
    with pytest.raises(CandidateGroundingError):
        extract(candidate(span))


def test_case_and_whitespace_collapse_is_comparison_only() -> None:
    span = "A   PAYMENT above $10,000"
    item = extract(candidate(span)).candidates[0]
    assert item["candidate_span"] == span


def test_unit_type_is_exempt_from_literal_grounding() -> None:
    assert "obligation" not in SOURCE.casefold()
    assert extract(candidate(SOURCE, "obligation")).candidates[0]["unit_type"] == "obligation"


def test_unknown_unit_type_is_rejected() -> None:
    with pytest.raises(CandidateBoundaryError, match="unit_type"):
        extract(candidate(SOURCE, "allow"))


@pytest.mark.parametrize("field", sorted(_REMOVED_SEMANTIC_ROLE_KEYS))
def test_every_removed_semantic_role_is_forbidden(field: str) -> None:
    payload = {"candidate_span": SOURCE, "unit_type": "obligation", field: None}
    with pytest.raises(CandidateBoundaryError, match="removed semantic-role"):
        extract(json.dumps({"candidates": [payload]}))


@pytest.mark.parametrize("field", ["actor", "conditions", "target"])
def test_motivating_removed_roles_fail_closed(field: str) -> None:
    payload = {"candidate_span": SOURCE, "unit_type": "obligation", field: "x"}
    with pytest.raises(CandidateBoundaryError, match=field):
        extract(json.dumps({"candidates": [payload]}))


@pytest.mark.parametrize("field", sorted(_MODEL_FORBIDDEN_AUTHORITY_KEYS))
def test_every_authority_controlled_field_remains_forbidden(field: str) -> None:
    payload = {"candidate_span": SOURCE, "unit_type": "obligation", field: "x"}
    with pytest.raises(CandidateBoundaryError, match="authority-controlled"):
        extract(json.dumps({"candidates": [payload]}))


def test_multiple_valid_candidate_spans_are_preserved_separately() -> None:
    source = "Orders must be approved. Invoices must be retained."
    body = json.dumps(
        {
            "candidates": [
                {"candidate_span": "Orders must be approved.", "unit_type": "obligation"},
                {"candidate_span": "Invoices must be retained.", "unit_type": "evidence_duty"},
            ]
        }
    )
    result = extract(body, source=source)
    assert [item["candidate_span"] for item in result.candidates] == [
        "Orders must be approved.",
        "Invoices must be retained.",
    ]
    assert len({item["unit_id"] for item in result.candidates}) == 2


def test_deterministic_ids_change_with_span_type_or_anchor() -> None:
    source = "Orders must be approved before shipment."
    full = extract(candidate(source), source=source).candidates[0]["unit_id"]
    shorter = extract(candidate("Orders must be approved"), source=source).candidates[0]["unit_id"]
    other_type = extract(candidate(source, "mandate"), source=source).candidates[0]["unit_id"]
    other_anchor = extract(candidate(source), source=source, source_anchor=anchor("2")).candidates[
        0
    ]["unit_id"]
    assert len({full, shorter, other_type, other_anchor}) == 4


def test_same_span_type_and_anchor_have_stable_id() -> None:
    first = extract(candidate(SOURCE)).candidates[0]["unit_id"]
    second = extract(candidate(SOURCE)).candidates[0]["unit_id"]
    assert first == second


def test_one_ungrounded_candidate_fails_the_whole_response() -> None:
    body = json.dumps(
        {
            "candidates": [
                {"candidate_span": SOURCE, "unit_type": "obligation"},
                {"candidate_span": "invented", "unit_type": "obligation"},
            ]
        }
    )
    with pytest.raises(CandidateGroundingError, match="candidate 1"):
        extract(body)


def test_check_source_grounding_is_direct_and_fail_closed() -> None:
    check_source_grounding({"candidate_span": SOURCE}, source_text=SOURCE)
    with pytest.raises(CandidateGroundingError):
        check_source_grounding({"candidate_span": "a paraphrase"}, source_text=SOURCE)


def test_prompt_contract_is_exact_minimal_and_source_standing_invariant() -> None:
    request = outbound()
    combined = " ".join((request.system_prompt + request.user_prompt).split())
    assert '{"candidates":[{"candidate_span":"...","unit_type":"..."}]}' in request.user_prompt
    assert 'For zero candidates, return exactly {"candidates":[]}.' in request.user_prompt
    assert "exactly these two keys: candidate_span and unit_type" in combined
    assert "literal, contiguous" in combined
    assert "Draft, hypothetical, synthetic, unverified, and non-authoritative" in combined
    assert "must not suppress" in combined
    assert "Passive voice does not require actor inference" in combined
    assert "Advisory language remains candidate material" in combined
    for role in _REMOVED_SEMANTIC_ROLE_KEYS:
        assert role in request.user_prompt
    assert request.temperature == 0.0
    assert request.response_format == {"type": "json_object"}


def test_unit_type_vocabulary_offered_matches_parser() -> None:
    request = outbound()
    assert frozenset(_UNIT_TYPES) == _ALLOWED_UNIT_TYPES
    for unit_type in _UNIT_TYPES:
        assert unit_type in request.system_prompt
        assert unit_type in request.user_prompt


def test_bare_candidate_root_and_extra_root_keys_are_rejected() -> None:
    with pytest.raises(CandidateBoundaryError, match="unexpected root keys"):
        extract(json.dumps({"candidate_span": SOURCE, "unit_type": "obligation"}))
    with pytest.raises(CandidateBoundaryError, match="unexpected root keys"):
        extract(json.dumps({"candidates": [], "verdict": "ok"}))


def test_empty_candidate_envelope_is_accepted() -> None:
    assert extract('{"candidates":[]}').candidates == ()


def test_candidate_requires_both_exact_model_fields() -> None:
    with pytest.raises(CandidateBoundaryError, match="missing required fields"):
        extract(json.dumps({"candidates": [{"unit_type": "obligation"}]}))


def test_source_anchor_shape_is_validated() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        propose_candidate_units(
            source_text=SOURCE,
            source_anchor={"anchor_id": "A"},
            provider=FakeProvider('{"candidates":[]}'),
        )
