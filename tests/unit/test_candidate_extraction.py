from __future__ import annotations

import json

import pytest

from oic.candidate_extraction import (
    _ALLOWED_UNIT_TYPES,
    _UNIT_TYPES,
    CandidateBoundaryError,
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


# --------------------------------------------------------------------------
# Outbound extraction instructions: semantic identification vs. authority
#
# These assert what OIC *sends*. They deliberately make no claim about what any live
# model returns for any particular fragment; a test that pinned a specific semantic
# decomposition to a live LLM would be asserting model behaviour, not this boundary.
# --------------------------------------------------------------------------


def _outbound(source_text: str = "The Treasurer must approve.") -> ModelRequest:
    provider = FakeProvider('{"candidates":[]}')
    propose_candidate_units(source_text=source_text, source_anchor=anchor(), provider=provider)
    return provider.requests[0]


def test_instructions_define_a_candidate_normative_unit_operationally() -> None:
    system = _outbound().system_prompt
    assert "A candidate normative unit is the literal source expression of any one of" in system
    for unit_type in _UNIT_TYPES:
        assert unit_type in system, unit_type


def test_offered_unit_type_vocabulary_cannot_drift_from_the_parser() -> None:
    request = _outbound()
    assert frozenset(_UNIT_TYPES) == _ALLOWED_UNIT_TYPES
    for unit_type in _ALLOWED_UNIT_TYPES:
        assert unit_type in request.system_prompt, unit_type
        assert unit_type in request.user_prompt, unit_type


def test_instructions_state_extraction_is_semantic_identification_only() -> None:
    assert "Your task is semantic identification only." in _outbound().system_prompt


def test_instructions_state_source_standing_is_not_an_extraction_criterion() -> None:
    request = _outbound()
    assert (
        "Whether the source is authoritative, admitted, enforceable, legally effective, "
        "approved,\nor institutionally controlling is NOT a criterion for deciding whether "
        "candidate material\nexists." in request.system_prompt
    )
    assert "Those questions belong to later stages" in request.system_prompt
    assert (
        "Identifying candidate material is not a finding that the source is authoritative, "
        "admitted, enforceable, legally effective, approved, or institutionally controlling. "
        "Do not withhold a candidate on those grounds." in request.user_prompt
    )


def test_instructions_still_withhold_every_authority_decision() -> None:
    system = _outbound().system_prompt
    assert "has no institutional authority" in system
    assert (
        "Do not decide\nadmission, authority, authorization, enforceability, legal effect, "
        "runtime outcome, allow\nor deny, or any confidence standing for admission." in system
    )


def test_decomposition_guidance_stays_literal_and_names_each_field() -> None:
    user = _outbound().user_prompt
    assert "Restate only what the fragment literally says:" in user
    for field in ("actor", "action", "object", "conditions", "exceptions", "evidence_requirements"):
        assert f"- {field}:" in user
    assert "Do not infer, complete, or supply anything the fragment does not say." in user


def test_decomposition_guidance_does_not_prescribe_where_a_threshold_belongs() -> None:
    """Placement of a numeric threshold is left to the model, not dictated by OIC."""
    user = _outbound().user_prompt
    for dictated in ("threshold", "amount", "$", "numeric", "greater than", "above "):
        assert dictated not in user.split("SOURCE FRAGMENT:")[0], dictated


# --------------------------------------------------------------------------
# The fail-closed boundary is unchanged by the prompt correction
# --------------------------------------------------------------------------


def test_bare_root_rejection_is_unaffected_by_the_prompt_correction() -> None:
    provider = FakeProvider(
        '{"unit_type":"mandate","actor":"Chief Financial Officer","action":"approve",'
        '"object":"payment above $10,000","conditions":[],"exceptions":[],'
        '"evidence_requirements":[]}'
    )
    with pytest.raises(CandidateBoundaryError, match="unexpected root keys"):
        propose_candidate_units(
            source_text="A payment above $10,000 requires approval by the CFO.",
            source_anchor=anchor(),
            provider=provider,
        )


@pytest.mark.parametrize(
    "field",
    [
        "unit_id",
        "interpretation_state",
        "epistemic_state",
        "lifecycle_state",
        "confidence",
        "source_anchors",
        "admission",
        "authority",
        "verdict",
        "allow",
    ],
)
def test_every_forbidden_authority_field_still_fails_closed(field: str) -> None:
    provider = FakeProvider(
        json.dumps({"candidates": [{"unit_type": "mandate", "action": "approve", field: "x"}]})
    )
    with pytest.raises(CandidateBoundaryError, match="authority-controlled"):
        propose_candidate_units(
            source_text="The CFO must approve.", source_anchor=anchor(), provider=provider
        )


def test_no_repair_of_an_authority_claim_is_attempted() -> None:
    """A forbidden field is refused, never stripped and accepted."""
    provider = FakeProvider('{"candidates":[{"unit_type":"mandate","allow":true}]}')
    with pytest.raises(CandidateBoundaryError):
        propose_candidate_units(
            source_text="The CFO must approve.", source_anchor=anchor(), provider=provider
        )


def test_zero_candidate_output_remains_structurally_valid() -> None:
    result = propose_candidate_units(
        source_text="A payment above $10,000 requires approval by the CFO.",
        source_anchor=anchor(),
        provider=FakeProvider('{"candidates":[]}'),
    )
    assert result.candidates == ()
    assert result.source_anchor == anchor()
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert len(result.raw_content_sha256) == 64


def test_deterministic_fields_and_anchors_stay_oic_controlled() -> None:
    """The model supplies semantics only; identity, state and anchoring are OIC's."""
    provider = FakeProvider(
        '{"candidates":[{"unit_type":"mandate","actor":"Chief Financial Officer",'
        '"action":"approve","object":"payment above $10,000","conditions":[],'
        '"exceptions":[],"evidence_requirements":[]}]}'
    )
    result = propose_candidate_units(
        source_text="A payment above $10,000 requires approval by the CFO.",
        source_anchor=anchor(),
        provider=provider,
    )
    candidate = result.candidates[0]
    assert candidate["interpretation_state"] == "extracted"
    assert candidate["epistemic_state"] == "uncertain"
    assert candidate["source_anchors"] == [anchor()]
    assert str(candidate["unit_id"]).startswith("cnu-")
    assert set(candidate) == {
        "unit_id",
        "unit_type",
        "actor",
        "action",
        "object",
        "conditions",
        "exceptions",
        "evidence_requirements",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    }


def test_source_anchors_come_from_the_caller_not_the_model() -> None:
    caller_anchor = anchor()
    caller_anchor["quote"] = "A payment above $10,000 requires approval."
    provider = FakeProvider('{"candidates":[{"unit_type":"mandate","action":"approve"}]}')
    result = propose_candidate_units(
        source_text="A payment above $10,000 requires approval by the CFO.",
        source_anchor=caller_anchor,
        provider=provider,
    )
    assert result.candidates[0]["source_anchors"] == [caller_anchor]
    assert "A-1" not in provider.requests[0].user_prompt
    assert "sha256:" not in provider.requests[0].user_prompt
