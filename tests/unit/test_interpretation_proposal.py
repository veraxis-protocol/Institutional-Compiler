"""The interpretation-proposal boundary: what it refuses, and what it deliberately does not.

The second half matters as much as the first. This layer must accept a schema-valid
proposal that is semantically wrong — an invented actor, a dropped exception, an ungrounded
quote — because a characterization instrument that repairs defects before measuring them
reports a clean run over a broken model.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from oic.interpretation_proposal import (
    FORCE_VALUES,
    PROPOSAL_SCHEMA_ID,
    SLOT_VOCABULARY,
    AdmittedCandidateBinding,
    InterpretationProposalError,
    ProposalBoundaryError,
    ProposalInputBoundaryError,
    build_proposal_envelope,
    grounding_key,
    is_quote_grounded,
    proposal_identity,
    propose_interpretation,
)
from oic.model_provider import ModelProviderError, ModelRequest, ModelResponse

SPAN = "The Records Officer must retain each closed file for seven years."
RECEIPT_ID = "admrec-sha256:" + "a" * 64
UNIT_ID = "cnu-" + "b" * 24
PROJECTION_DIGEST = "sha256:" + "c" * 64
PROPOSER = "test-proposer"


class CountingProvider:
    """A fake provider that records every call, so 'no call' is provable rather than assumed."""

    def __init__(self, content: str = '{"proposed_assertions":[]}') -> None:
        self.calls: list[ModelRequest] = []
        self.content = content

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        return ModelResponse(
            provider="fake",
            model="fake-model",
            content=self.content,
            request_id="req-1",
            raw={},
        )


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: ModelRequest) -> ModelResponse:
        del request
        self.calls += 1
        raise ModelProviderError("transport failed")


def _binding(state: str = "ADMITTED", unit_type: str | None = None) -> AdmittedCandidateBinding:
    return AdmittedCandidateBinding(
        admission_receipt_id=RECEIPT_ID,
        admission_state=state,
        candidate_unit_id=UNIT_ID,
        candidate_projection_digest=PROJECTION_DIGEST,
        candidate_span=SPAN,
        provisional_unit_type=unit_type,
    )


def _propose(content: str, *, unit_type: str | None = None) -> dict[str, Any]:
    provider = CountingProvider(content)
    result = propose_interpretation(
        binding=_binding(unit_type=unit_type), provider=provider, proposer_id=PROPOSER
    )
    return result.proposal


# ---------------------------------------------------------------------------
# The input boundary: non-ADMITTED never reaches a provider
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        "MISSING_AUTHORITY_EVIDENCE",
        "OUT_OF_SCOPE",
        "REVOKED",
        "CONFLICTING_AUTHORITY",
        "ADMISSION_NOT_ESTABLISHED",
        "SOURCE_NOT_REGISTERED",
    ],
)
def test_non_admitted_input_makes_zero_provider_calls(state: str) -> None:
    provider = CountingProvider()
    with pytest.raises(ProposalInputBoundaryError):
        propose_interpretation(binding=_binding(state), provider=provider, proposer_id=PROPOSER)
    assert provider.calls == [], "a non-ADMITTED receipt must not reach the provider"


def test_a_non_admitted_refusal_is_not_an_empty_proposal() -> None:
    provider = CountingProvider()
    with pytest.raises(ProposalInputBoundaryError) as caught:
        propose_interpretation(binding=_binding("REVOKED"), provider=provider, proposer_id=PROPOSER)
    assert "no provider was called" in str(caught.value)
    assert not isinstance(caught.value, ProposalBoundaryError)
    assert isinstance(caught.value, InterpretationProposalError)


def test_an_admitted_receipt_does_reach_the_provider_exactly_once() -> None:
    provider = CountingProvider()
    propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    assert len(provider.calls) == 1


def test_there_is_no_retry_on_provider_failure() -> None:
    provider = FailingProvider()
    with pytest.raises(ModelProviderError):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    assert provider.calls == 1


# ---------------------------------------------------------------------------
# The envelope belongs to OIC
# ---------------------------------------------------------------------------


def test_oic_supplies_every_binding_and_identity_field() -> None:
    proposal = _propose('{"proposed_assertions":[]}')
    assert proposal["proposal_schema_id"] == PROPOSAL_SCHEMA_ID
    assert proposal["admission_receipt_id"] == RECEIPT_ID
    assert proposal["candidate_unit_id"] == UNIT_ID
    assert proposal["candidate_projection_digest"] == PROJECTION_DIGEST
    assert proposal["proposal_state"] == "PROVISIONAL"
    assert proposal["epistemic_state"] == "uncertain"
    assert proposal["proposer"] == {"proposer_kind": "MODEL", "proposer_id": PROPOSER}
    assert proposal["proposal_id"].startswith("iip-")


@pytest.mark.parametrize(
    "field",
    [
        "proposal_id",
        "admission_receipt_id",
        "candidate_unit_id",
        "proposal_state",
        "epistemic_state",
    ],
)
def test_a_model_cannot_overwrite_an_oic_controlled_field(field: str) -> None:
    """The model is not asked for these, and emitting one is a boundary failure."""
    payload = json.dumps({"proposed_assertions": [], field: "model-supplied"})
    provider = CountingProvider(payload)
    with pytest.raises(ProposalBoundaryError):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)


# ---------------------------------------------------------------------------
# Deterministic identity
# ---------------------------------------------------------------------------


def test_proposal_identity_is_deterministic_for_an_identical_payload() -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "bearer",
                    "proposed_value": "The Records Officer",
                    "proposed_source_quote": "The Records Officer",
                }
            ]
        }
    )
    first = _propose(payload)
    second = _propose(payload)
    assert first["proposal_id"] == second["proposal_id"]
    assert first == second


def test_proposal_identity_changes_when_the_payload_changes() -> None:
    base = _propose('{"proposed_assertions":[]}')
    other = _propose(
        json.dumps(
            {
                "proposed_assertions": [
                    {"slot": "action", "proposed_value": "retain", "proposed_source_quote": None}
                ]
            }
        )
    )
    assert base["proposal_id"] != other["proposal_id"]


def test_proposal_identity_binds_the_admission_receipt_and_the_proposer() -> None:
    assertions: list[dict[str, Any]] = []
    same = proposal_identity(
        binding=_binding(), proposer_id=PROPOSER, assertions=assertions, references=[]
    )
    other_receipt = AdmittedCandidateBinding(
        admission_receipt_id="admrec-sha256:" + "d" * 64,
        admission_state="ADMITTED",
        candidate_unit_id=UNIT_ID,
        candidate_projection_digest=PROJECTION_DIGEST,
        candidate_span=SPAN,
    )
    assert (
        proposal_identity(
            binding=other_receipt, proposer_id=PROPOSER, assertions=assertions, references=[]
        )
        != same
    )
    assert (
        proposal_identity(
            binding=_binding(), proposer_id="someone-else", assertions=assertions, references=[]
        )
        != same
    )


def test_proposal_identity_uses_no_clock_and_no_randomness() -> None:
    """Identity is a pure function of the binding, the proposer and the payload."""
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[2] / "src/oic/interpretation_proposal.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert {"uuid", "random", "time", "datetime", "secrets", "os"} & imported == set()


def test_proposal_identity_is_not_ir_identity() -> None:
    proposal = _propose('{"proposed_assertions":[]}')
    assert not proposal["proposal_id"].startswith("iir-")
    assert "semantic_equivalence_key" not in proposal
    assert "ir_unit_id" not in proposal
    assert "interpretation_ruleset" not in proposal


# ---------------------------------------------------------------------------
# The provider-response contract: structural refusals only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        "not json at all",
        "[]",
        '"a string"',
        "null",
        '{"proposed_assertions":[],"extra_root":1}',
        '{"proposed_assertions":{}}',
        '{"proposed_unresolved_references":{}}',
        '{"proposed_assertions":["not an object"]}',
        '{"proposed_assertions":[{"slot":"bearer"}]}',
        '{"proposed_assertions":[{"slot":"invented_slot","proposed_value":null,'
        '"proposed_source_quote":null}]}',
        '{"proposed_assertions":[{"slot":"bearer","proposed_value":1,'
        '"proposed_source_quote":null}]}',
        '{"proposed_assertions":[{"slot":"bearer","proposed_value":null,'
        '"proposed_source_quote":7}]}',
        '{"proposed_assertions":[{"slot":"bearer","proposed_value":null,'
        '"proposed_source_quote":null,"extra":1}]}',
        '{"proposed_assertions":[{"slot":"bearer","proposed_value":null,'
        '"proposed_source_quote":null,"proposed_material_qualifiers":"x"}]}',
        '{"proposed_assertions":[],"proposed_unresolved_references":[{"reference_text":"x"}]}',
        '{"proposed_assertions":[],"proposed_unresolved_references":'
        '[{"reference_text":"x","reference_kind":"MADE_UP"}]}',
        '{"proposed_assertions":[],"proposed_unresolved_references":'
        '[{"reference_text":"","reference_kind":"DEFINITION"}]}',
    ],
)
def test_structural_contract_failures_are_refused(content: str) -> None:
    provider = CountingProvider(content)
    with pytest.raises(ProposalBoundaryError):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)


@pytest.mark.parametrize(
    "field",
    [
        "confidence",
        "score",
        "probability",
        "authority",
        "admitted",
        "canonical",
        "established",
        "interpretation_basis",
        "interpretation_evidence",
        "warrant",
        "legal_effect",
        "enforceability",
        "allow",
        "deny",
        "runtime_outcome",
        "verdict",
        "interpretation_status",
    ],
)
def test_no_authority_or_canonical_field_is_accepted_at_any_depth(field: str) -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "bearer",
                    "proposed_value": "x",
                    "proposed_source_quote": None,
                    **{field: True},
                }
            ]
        }
    )
    provider = CountingProvider(payload)
    with pytest.raises(ProposalBoundaryError, match="authority-controlled"):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)


@pytest.mark.parametrize(
    "status", ["ESTABLISHED", "AMBIGUOUS", "NOT_ESTABLISHED", "NOT_APPLICABLE"]
)
def test_a_model_may_not_assign_an_interpretation_status_as_a_value(status: str) -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "bearer", "proposed_value": status, "proposed_source_quote": None}
            ]
        }
    )
    provider = CountingProvider(payload)
    with pytest.raises(ProposalBoundaryError, match="interpretation-status"):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)


@pytest.mark.parametrize("force", FORCE_VALUES)
def test_every_frozen_force_is_accepted(force: str) -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "normative_force", "proposed_value": force, "proposed_source_quote": SPAN}
            ]
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_assertions"][0]["proposed_value"] == force


@pytest.mark.parametrize("force", ["MANDATE", "REQUIREMENT", "obligation", "SUGGESTION", ""])
def test_an_invented_normative_force_is_refused(force: str) -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "normative_force", "proposed_value": force, "proposed_source_quote": None}
            ]
        }
    )
    provider = CountingProvider(payload)
    with pytest.raises(ProposalBoundaryError, match="normative force"):
        propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)


@pytest.mark.parametrize("slot", SLOT_VOCABULARY)
def test_every_frozen_slot_is_accepted(slot: str) -> None:
    value = "OBLIGATION" if slot == "normative_force" else "some value"
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": slot, "proposed_value": value, "proposed_source_quote": None}
            ]
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_assertions"][0]["slot"] == slot


# ---------------------------------------------------------------------------
# What the layer must NOT do: no canonicalization before measurement
# ---------------------------------------------------------------------------


def test_a_null_source_quote_is_accepted() -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "bearer", "proposed_value": "someone", "proposed_source_quote": None}
            ]
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_assertions"][0]["proposed_source_quote"] is None


def test_an_ungrounded_quote_is_accepted_and_never_repaired() -> None:
    """The candidate layer refuses this. The proposal layer measures it instead."""
    quote = "text that is nowhere in the admitted proposition"
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "bearer", "proposed_value": "someone", "proposed_source_quote": quote}
            ]
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_assertions"][0]["proposed_source_quote"] == quote
    assert not is_quote_grounded(quote, candidate_span=SPAN)


def test_an_invented_actor_is_accepted_so_that_it_can_be_measured() -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "bearer",
                    "proposed_value": "the finance team",
                    "proposed_source_quote": None,
                }
            ]
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_assertions"][0]["proposed_value"] == "the finance team"


def test_a_semantically_wrong_force_is_accepted_so_that_it_can_be_measured() -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "normative_force",
                    "proposed_value": "OBLIGATION",
                    "proposed_source_quote": SPAN,
                }
            ]
        }
    )
    assert _propose(payload)["proposed_assertions"][0]["proposed_value"] == "OBLIGATION"


def test_duplicate_slot_proposals_are_preserved_not_deduplicated() -> None:
    """A proposer contradicting itself is evidence, so both assertions survive."""
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "bearer", "proposed_value": "A", "proposed_source_quote": None},
                {"slot": "bearer", "proposed_value": "B", "proposed_source_quote": None},
            ]
        }
    )
    proposal = _propose(payload)
    assert [item["proposed_value"] for item in proposal["proposed_assertions"]] == ["A", "B"]


def test_proposed_references_are_kept_as_proposed_and_never_resolved() -> None:
    payload = json.dumps(
        {
            "proposed_assertions": [],
            "proposed_unresolved_references": [
                {"reference_text": "Policy B", "reference_kind": "EXTERNAL_DOCUMENT"}
            ],
        }
    )
    proposal = _propose(payload)
    assert proposal["proposed_unresolved_references"] == [
        {"reference_text": "Policy B", "reference_kind": "EXTERNAL_DOCUMENT"}
    ]
    assert "resolved_target" not in json.dumps(proposal)


def test_an_empty_proposal_is_accepted() -> None:
    proposal = _propose('{"proposed_assertions":[]}')
    assert proposal["proposed_assertions"] == []
    assert "proposed_unresolved_references" not in proposal


# ---------------------------------------------------------------------------
# Grounding helpers
# ---------------------------------------------------------------------------


def test_grounding_is_whitespace_and_case_insensitive() -> None:
    assert grounding_key("  The   RECORDS  officer ") == "the records officer"
    assert is_quote_grounded("the   records officer", candidate_span=SPAN)
    assert not is_quote_grounded("the finance team", candidate_span=SPAN)


# ---------------------------------------------------------------------------
# The request body
# ---------------------------------------------------------------------------


def test_the_request_carries_the_proposition_and_the_vocabulary_only() -> None:
    provider = CountingProvider()
    propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    request = provider.calls[0]
    body = request.system_prompt + "\n" + request.user_prompt
    assert SPAN in body
    for slot in SLOT_VOCABULARY:
        assert slot in body
    for force in FORCE_VALUES:
        assert force in body
    assert request.temperature == 0.0
    assert request.response_format == {"type": "json_object"}


@pytest.mark.parametrize(
    "leak",
    [
        RECEIPT_ID,
        UNIT_ID,
        PROJECTION_DIGEST,
        "authority_evidence",
        "admission_warrant",
        "OIC-ADM-",
        "interpretation_evidence",
        "INSTITUTIONAL_INTERPRETATION_WARRANT",
        "REGISTERED_INTERPRETATION_RULE",
        "evaluation_scope",
    ],
)
def test_the_request_carries_no_authority_or_admission_metadata(leak: str) -> None:
    provider = CountingProvider()
    propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    request = provider.calls[0]
    body = request.system_prompt + "\n" + request.user_prompt
    assert leak not in body


def test_the_provisional_unit_type_is_omitted_by_default() -> None:
    """The preregistered arm is the candidate span alone: no prior classification crosses."""
    provider = CountingProvider()
    propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    prompt = provider.calls[0].user_prompt
    assert "An earlier stage proposed" not in prompt
    assert "mandate" not in prompt


def test_the_provisional_unit_type_arm_can_be_enabled_for_a_later_ab() -> None:
    provider = CountingProvider()
    propose_interpretation(
        binding=_binding(unit_type="mandate"), provider=provider, proposer_id=PROPOSER
    )
    prompt = provider.calls[0].user_prompt
    assert "'mandate'" in prompt
    assert "carries no authority" in prompt


def test_the_prompt_names_no_provider() -> None:
    provider = CountingProvider()
    propose_interpretation(binding=_binding(), provider=provider, proposer_id=PROPOSER)
    request = provider.calls[0]
    body = (request.system_prompt + request.user_prompt).casefold()
    for vendor in ("nvidia", "nim", "nemotron", "openai", "gpt", "anthropic", "claude", "llama"):
        assert vendor not in body


# ---------------------------------------------------------------------------
# Envelope construction
# ---------------------------------------------------------------------------


def test_build_proposal_envelope_rejects_an_unknown_proposer_kind() -> None:
    with pytest.raises(ValueError, match="proposer_kind"):
        build_proposal_envelope(
            binding=_binding(),
            proposer_kind="INSTITUTION",
            proposer_id=PROPOSER,
            assertions=[],
            references=[],
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("admission_receipt_id", "not-a-receipt"),
        ("candidate_unit_id", "not-a-candidate"),
        ("candidate_projection_digest", "not-a-digest"),
        ("candidate_span", "   "),
    ],
)
def test_the_binding_refuses_malformed_admission_material(field: str, value: str) -> None:
    kwargs: dict[str, Any] = {
        "admission_receipt_id": RECEIPT_ID,
        "admission_state": "ADMITTED",
        "candidate_unit_id": UNIT_ID,
        "candidate_projection_digest": PROJECTION_DIGEST,
        "candidate_span": SPAN,
        field: value,
    }
    with pytest.raises(ValueError):
        AdmittedCandidateBinding(**kwargs)


def test_no_institutional_ir_object_is_constructed_here() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "src/oic/interpretation_proposal.py").read_text(
        encoding="utf-8"
    )
    for token in ("InstitutionalIRUnit", "ir_unit_id", "semantic_equivalence_key"):
        assert source.count(token) <= 1, token
    assert "InstitutionalIRUnit" not in source
