from __future__ import annotations

import pytest

from oic.candidate_extraction import CandidateBoundaryError, propose_candidate_units
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


def anchor() -> dict[str, object]:
    return {
        "anchor_id": "A-1",
        "source_id": "DOC-1",
        "node_id": "N-7",
        "content_hash": "sha256:" + ("a" * 64),
    }


def test_provider_output_is_forced_to_candidate_only_state() -> None:
    provider = FakeProvider(
        '{"candidates":[{"unit_type":"obligation","actor":"Treasurer",'
        '"action":"approve","object":"payment","conditions":["amount > 100000"],'
        '"exceptions":[],"evidence_requirements":["approval record"]}]}'
    )
    result = propose_candidate_units(
        source_text="Payments above 100000 require Treasurer approval.",
        source_anchor=anchor(),
        provider=provider,
    )
    candidate = result.candidates[0]
    assert candidate["interpretation_state"] == "extracted"
    assert candidate["epistemic_state"] == "uncertain"
    assert candidate["source_anchors"] == [anchor()]
    assert str(candidate["unit_id"]).startswith("cnu-")
    assert provider.requests[0].temperature == 0.0
    assert provider.requests[0].response_format == {"type": "json_object"}


def test_outbound_prompt_requires_exact_candidates_root_envelope() -> None:
    provider = FakeProvider('{"candidates":[]}')
    propose_candidate_units(
        source_text="No duties here.", source_anchor=anchor(), provider=provider
    )
    prompt = provider.requests[0].user_prompt
    assert "exactly one top-level key named candidates" in prompt
    assert (
        '{"candidates":[{"unit_type":"...","actor":null,"action":null,"object":null,'
        '"conditions":[],"exceptions":[],"evidence_requirements":[]}]}' in prompt
    )
    assert 'For zero candidates, return exactly {"candidates":[]}.' in prompt
    assert "Never return a candidate directly at the JSON root." in prompt
    assert "Never add another root key." in prompt


def test_bare_candidate_object_at_root_remains_rejected() -> None:
    provider = FakeProvider('{"unit_type":"obligation","actor":"Treasurer"}')
    with pytest.raises(CandidateBoundaryError, match="unexpected root keys"):
        propose_candidate_units(
            source_text="The Treasurer must approve.", source_anchor=anchor(), provider=provider
        )


def test_empty_candidates_envelope_is_accepted() -> None:
    result = propose_candidate_units(
        source_text="No duties here.",
        source_anchor=anchor(),
        provider=FakeProvider('{"candidates":[]}'),
    )
    assert result.candidates == ()


def test_model_cannot_emit_authority_controlled_fields() -> None:
    provider = FakeProvider(
        '{"candidates":[{"unit_type":"permission","source_anchors":[],"action":"pay"}]}'
    )
    with pytest.raises(CandidateBoundaryError, match="authority-controlled"):
        propose_candidate_units(source_text="May pay.", source_anchor=anchor(), provider=provider)


def test_candidate_id_is_stable_for_same_semantics_and_anchor() -> None:
    content = '{"candidates":[{"unit_type":"prohibition","action":"pay"}]}'
    first = propose_candidate_units(
        source_text="Do not pay.", source_anchor=anchor(), provider=FakeProvider(content)
    )
    second = propose_candidate_units(
        source_text="Do not pay.", source_anchor=anchor(), provider=FakeProvider(content)
    )
    assert first.candidates[0]["unit_id"] == second.candidates[0]["unit_id"]


def test_unknown_unit_type_is_rejected() -> None:
    with pytest.raises(CandidateBoundaryError, match="unit_type"):
        propose_candidate_units(
            source_text="Pay.",
            source_anchor=anchor(),
            provider=FakeProvider('{"candidates":[{"unit_type":"allow","action":"pay"}]}'),
        )


def test_source_anchor_must_match_current_required_shape() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        propose_candidate_units(
            source_text="Text.",
            source_anchor={"anchor_id": "A-1"},
            provider=FakeProvider('{"candidates":[]}'),
        )


def test_source_anchor_rejects_malformed_content_hash() -> None:
    bad = anchor()
    bad["content_hash"] = "abc"
    with pytest.raises(ValueError, match="sha256"):
        propose_candidate_units(
            source_text="Text.", source_anchor=bad, provider=FakeProvider('{"candidates":[]}')
        )
