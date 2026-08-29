from __future__ import annotations

import json

import pytest

from oic.candidate_extraction import (
    _ALLOWED_UNIT_TYPES,
    _UNIT_TYPES,
    CandidateBoundaryError,
    CandidateExtractionResult,
    CandidateGroundingError,
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
        '"action":"require","object":"Payments","target":null,'
        '"conditions":["above 100000"],'
        '"exceptions":[],"evidence_requirements":["Treasurer approval"]}]}'
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
        '"target":null,"conditions":[],"exceptions":[],"evidence_requirements":[]}]}' in prompt
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
    assert "Your task is source-grounded semantic identification only." in _outbound().system_prompt


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
    assert "EVERY OTHER FIELD MUST BE COPIED VERBATIM FROM THE FRAGMENT." in user
    for field in (
        "actor",
        "action",
        "object",
        "target",
        "conditions",
        "exceptions",
        "evidence_requirements",
    ):
        assert f"- {field}:" in user
    assert "Do not infer, complete, or supply anything the fragment does not say." in user


def test_guidance_never_names_a_specimen_specific_value_or_reading() -> None:
    """Categories of qualifier may be named. Particular values and answers may not.

    OIC-CANDIDATE-SEMANTICS-002 authorizes telling the worker that a quantitative or
    temporal qualifier belongs in conditions rather than replacing the operative function.
    It does not authorize teaching the worker any specimen's answer, so the guard is on
    concrete values and dictated placements rather than on the word "threshold".
    """
    instructions = _outbound().user_prompt.split("SOURCE FRAGMENT:")[0]
    instructions += _outbound().system_prompt
    for dictated in (
        "$10,000",
        "$75",
        "10,000",
        "Chief Financial Officer",
        "put the threshold in object",
        "the threshold belongs in object",
    ):
        assert dictated not in instructions, dictated


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
        '{"candidates":[{"unit_type":"mandate","actor":"CFO",'
        '"action":"requires approval","object":"A payment","target":"the CFO",'
        '"conditions":["above $10,000"],'
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
        "target",
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
    provider = FakeProvider('{"candidates":[{"unit_type":"mandate","action":"requires approval"}]}')
    result = propose_candidate_units(
        source_text="A payment above $10,000 requires approval by the CFO.",
        source_anchor=caller_anchor,
        provider=provider,
    )
    assert result.candidates[0]["source_anchors"] == [caller_anchor]
    assert "A-1" not in provider.requests[0].user_prompt
    assert "sha256:" not in provider.requests[0].user_prompt


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-002: source grounding
#
# The candidate layer reports what the fragment says. The grounding check is literal
# containment and nothing else -- no similarity model, no second model adjudicating the
# first -- which is only honest because the contract requires verbatim spans rather than
# paraphrase. These tests exercise both directions: invention must fail, and a genuine
# span must pass.
# --------------------------------------------------------------------------

PO_SOURCE = (
    "A purchase order must be approved before goods are ordered. "
    "Invoices are paid within thirty days of receipt."
)


def _propose(content: str, *, source_text: str = PO_SOURCE) -> CandidateExtractionResult:
    return propose_candidate_units(
        source_text=source_text, source_anchor=anchor(), provider=FakeProvider(content)
    )


def test_verbatim_spans_are_accepted_unchanged() -> None:
    result = _propose(
        json.dumps(
            {
                "candidates": [
                    {
                        "unit_type": "obligation",
                        "actor": None,
                        "action": "must be approved",
                        "object": "A purchase order",
                        "target": None,
                        "conditions": ["before goods are ordered"],
                        "exceptions": [],
                        "evidence_requirements": [],
                    }
                ]
            }
        )
    )
    candidate = result.candidates[0]
    assert candidate["actor"] is None
    assert candidate["action"] == "must be approved"
    assert candidate["conditions"] == ["before goods are ordered"]


@pytest.mark.parametrize(
    "invented",
    [
        {"actor": "accounts payable"},
        {"actor": "purchase order approver"},
        {"actor": "payee"},
        {"actor": "the Finance Office"},
        {"target": "the supplier"},
        {"object": "vendor invoices"},
        {"conditions": ["when the invoice is overdue"]},
        {"exceptions": ["unless waived by the Director"]},
        {"evidence_requirements": ["a signed approval record"]},
    ],
)
def test_unsupported_inference_fails_closed(invented: dict[str, object]) -> None:
    """Every evidenced invented participant from OIC-CANDIDATE-SEMANTICS-001, and more."""
    payload = {"unit_type": "obligation", "action": "are paid", **invented}
    with pytest.raises(CandidateGroundingError, match="not a verbatim span"):
        _propose(json.dumps({"candidates": [payload]}))


def test_the_failing_field_and_its_value_are_named_in_the_error() -> None:
    with pytest.raises(CandidateGroundingError) as excinfo:
        _propose('{"candidates":[{"unit_type":"obligation","actor":"accounts payable"}]}')
    message = str(excinfo.value)
    assert "field actor" in message
    assert "accounts payable" in message
    assert "candidate 0" in message


def test_the_index_of_the_offending_candidate_is_reported() -> None:
    payload = {
        "candidates": [
            {"unit_type": "obligation", "action": "must be approved"},
            {"unit_type": "obligation", "actor": "accounts payable"},
        ]
    }
    with pytest.raises(CandidateGroundingError, match="candidate 1 field actor"):
        _propose(json.dumps(payload))


def test_an_ungrounded_field_is_never_stripped_and_the_response_never_partially_kept() -> None:
    """No repair. One bad field fails the whole response, including its good siblings."""
    payload = {
        "candidates": [
            {"unit_type": "obligation", "action": "must be approved", "object": "A purchase order"},
            {"unit_type": "obligation", "actor": "accounts payable"},
        ]
    }
    with pytest.raises(CandidateGroundingError):
        _propose(json.dumps(payload))


def test_grounding_error_is_still_a_candidate_boundary_error() -> None:
    """Every existing fail-closed handler keeps catching it."""
    with pytest.raises(CandidateBoundaryError):
        _propose('{"candidates":[{"unit_type":"obligation","actor":"accounts payable"}]}')
    assert issubclass(CandidateGroundingError, CandidateBoundaryError)


def test_passive_voice_with_a_null_actor_is_accepted() -> None:
    result = _propose(
        '{"candidates":[{"unit_type":"obligation","actor":null,"action":"are paid",'
        '"object":"Invoices","conditions":["within thirty days of receipt"]}]}'
    )
    assert result.candidates[0]["actor"] is None
    assert result.candidates[0]["conditions"] == ["within thirty days of receipt"]


def test_case_and_whitespace_differences_do_not_reject_a_real_span() -> None:
    """Neither relaxation can admit a phrase the fragment does not contain."""
    result = _propose(
        '{"candidates":[{"unit_type":"obligation","action":"ARE   PAID","object":"invoices"}]}'
    )
    assert result.candidates[0]["action"] == "ARE   PAID"
    assert result.candidates[0]["object"] == "invoices"


def test_a_blank_textual_role_is_rejected_rather_than_treated_as_absent() -> None:
    with pytest.raises(CandidateGroundingError, match="is blank"):
        _propose('{"candidates":[{"unit_type":"obligation","actor":"   "}]}')


def test_unit_type_is_not_grounded_because_it_is_a_classification() -> None:
    """ "obligation" appears nowhere in the fragment, and must not have to."""
    assert "obligation" not in PO_SOURCE
    result = _propose('{"candidates":[{"unit_type":"obligation","action":"are paid"}]}')
    assert result.candidates[0]["unit_type"] == "obligation"
    assert result.candidates[0]["epistemic_state"] == "uncertain"


def test_grounding_is_checked_against_the_caller_supplied_source_text() -> None:
    """A span of some other document is not grounded in this one."""
    with pytest.raises(CandidateGroundingError, match="not a verbatim span"):
        _propose(
            '{"candidates":[{"unit_type":"obligation","action":"are paid"}]}',
            source_text="A wholly unrelated fragment about opening hours.",
        )


def test_check_source_grounding_is_callable_on_its_own() -> None:
    from oic.candidate_extraction import check_source_grounding

    check_source_grounding({"actor": None, "action": "are paid"}, source_text=PO_SOURCE)
    with pytest.raises(CandidateGroundingError):
        check_source_grounding({"actor": "accounts payable"}, source_text=PO_SOURCE)


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-002: the target role
# --------------------------------------------------------------------------

TARGET_SOURCE = "Each department must submit a quarterly expenditure report to the Finance Office."


def test_an_explicit_recipient_can_be_carried_in_target() -> None:
    result = _propose(
        '{"candidates":[{"unit_type":"obligation","actor":"Each department",'
        '"action":"must submit","object":"a quarterly expenditure report",'
        '"target":"the Finance Office"}]}',
        source_text=TARGET_SOURCE,
    )
    candidate = result.candidates[0]
    assert candidate["target"] == "the Finance Office"
    assert candidate["object"] == "a quarterly expenditure report"


def test_target_defaults_to_null_when_the_fragment_states_none() -> None:
    result = _propose('{"candidates":[{"unit_type":"obligation","action":"are paid"}]}')
    assert result.candidates[0]["target"] is None


def test_an_invented_target_fails_closed() -> None:
    with pytest.raises(CandidateGroundingError, match="field target"):
        _propose(
            '{"candidates":[{"unit_type":"obligation","action":"must submit",'
            '"target":"the Treasury Board"}]}',
            source_text=TARGET_SOURCE,
        )


def test_target_participates_in_the_deterministic_candidate_id() -> None:
    """Two candidates differing only in target are different candidates."""
    with_target = _propose(
        '{"candidates":[{"unit_type":"obligation","action":"must submit",'
        '"target":"the Finance Office"}]}',
        source_text=TARGET_SOURCE,
    )
    without_target = _propose(
        '{"candidates":[{"unit_type":"obligation","action":"must submit","target":null}]}',
        source_text=TARGET_SOURCE,
    )
    assert with_target.candidates[0]["unit_id"] != without_target.candidates[0]["unit_id"]


def test_target_is_rejected_as_an_authority_field_name_collision() -> None:
    """target is a semantic role; it grants nothing and unlocks no authority field."""
    with pytest.raises(CandidateBoundaryError, match="authority-controlled"):
        _propose(
            '{"candidates":[{"unit_type":"obligation","action":"are paid","authority":"CFO"}]}'
        )


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-002: outbound contract instructions
# --------------------------------------------------------------------------


def _flat(text: str) -> str:
    """Collapse the prompt's hard wrapping so a prose assertion is not defeated by it."""
    return " ".join(text.split())


def test_instructions_require_verbatim_source_spans() -> None:
    request = _outbound()
    system = _flat(request.system_prompt)
    assert "must be copied verbatim from the fragment" in system
    assert "an exact, contiguous run of characters that appears in it" in system
    assert "EVERY OTHER FIELD MUST BE COPIED VERBATIM FROM THE FRAGMENT." in request.user_prompt
    assert "fails the whole response" in _flat(request.user_prompt)


def test_instructions_forbid_inventing_a_participant() -> None:
    system = _flat(_outbound().system_prompt)
    assert "Never supply a participant the fragment does not name." in system
    assert "actor is null" in system
    assert "Do not infer an actor from the passive voice" in system
    for invented in ("recipient", "approver", "owner", "payee", "department", "authority"):
        assert invented in system, invented


def test_instructions_forbid_dropping_material_qualifiers() -> None:
    system = _flat(_outbound().system_prompt)
    assert "Never drop material qualifying language." in system
    for qualifier in ("if", "when", "where", "unless", "thresholds", "time limits"):
        assert qualifier in system, qualifier


def test_instructions_separate_the_operative_act_from_its_trigger() -> None:
    user = _flat(_outbound().user_prompt)
    assert (
        "the operative act is the consequence, not the trigger; the trigger belongs in "
        "conditions" in user
    )


def test_instructions_state_unit_type_is_the_primary_function_and_uncertain() -> None:
    user = _flat(_outbound().user_prompt)
    assert "unit_type is your classification of the candidate's PRIMARY normative function" in user
    assert "uncertain proposal" in user
    assert "normally evidence_duty" in user
    assert "normally advisory" in user
    assert "normally escalation" in user
    assert "does not replace the primary function it qualifies" in user


def test_instructions_refuse_to_pretend_classification_is_unambiguous() -> None:
    user = _flat(_outbound().user_prompt)
    assert "These are guides, not a precedence table" in user
    assert "genuinely ambiguous" in user


def test_instructions_keep_advisory_material_discoverable() -> None:
    user = _flat(_outbound().user_prompt)
    assert "remains candidate material even though it compels nothing" in user


def test_instructions_describe_target_as_source_supported_and_optional() -> None:
    user = _flat(_outbound().user_prompt)
    assert "- target: the span naming an explicitly stated recipient" in user
    assert "Use null unless the fragment states one." in user


def test_the_authority_boundary_survives_the_contract_revision() -> None:
    system = _outbound().system_prompt
    assert "has no institutional authority" in system
    assert (
        "Do not decide\nadmission, authority, authorization, enforceability, legal effect, "
        "runtime outcome, allow\nor deny, or any confidence standing for admission." in system
    )
