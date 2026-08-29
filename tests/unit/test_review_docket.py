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


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-004: source context stays with the source
#
# 004 asks the provider to leave separable framing outside the candidate span. That is only
# safe if the framing survives somewhere a reviewer can see. It does: the caller-supplied
# source anchor carries the whole fragment as ``quote``, and the docket exposes the anchor
# as a top-level key structurally separate from the candidates.
#
# So no context field was added anywhere. These tests pin the property the work order asked
# to be confirmed before changing anything, and would fail if a later change dropped the
# anchor, dropped the quote, or folded framing into candidate metadata.
# --------------------------------------------------------------------------

DRAFT_SOURCE = (
    "DRAFT — NOT YET ADOPTED. A payment above $10,000 requires approval by the "
    "Chief Financial Officer."
)
DRAFT_PROPOSITION = "A payment above $10,000 requires approval by the Chief Financial Officer."
DRAFT_FRAMING = "DRAFT — NOT YET ADOPTED."


def framing_anchor() -> dict[str, object]:
    """A caller-controlled anchor carrying the whole source fragment as its quote."""
    return {
        "anchor_id": "A-DRAFT",
        "source_id": "DOC-DRAFT",
        "node_id": "N-1",
        "content_hash": "sha256:" + ("b" * 64),
        "quote": DRAFT_SOURCE,
    }


def framing_extract(provider: str = "p1") -> CandidateExtractionResult:
    body = {"candidates": [{"candidate_span": DRAFT_PROPOSITION, "unit_type": "obligation"}]}
    return propose_candidate_units(
        source_text=DRAFT_SOURCE,
        source_anchor=framing_anchor(),
        provider=FakeProvider(provider, json.dumps(body)),
    )


def test_the_docket_retains_the_original_source_context_including_its_framing() -> None:
    docket = build_review_docket([framing_extract()]).to_json()
    assert docket["source_anchor"]["quote"] == DRAFT_SOURCE
    assert DRAFT_FRAMING in str(docket["source_anchor"]["quote"])


def test_the_docket_separates_source_context_from_the_candidate_span() -> None:
    """A reviewer sees the draft marking and the proposition, in different places."""
    docket = build_review_docket([framing_extract()]).to_json()
    candidate = next(iter(docket["candidates_by_id"].values()))

    # Source context: the framing is here.
    assert DRAFT_FRAMING in str(docket["source_anchor"]["quote"])
    # Candidate span: the proposition is here, and the framing is not.
    assert candidate["candidate_span"] == DRAFT_PROPOSITION
    assert DRAFT_FRAMING not in str(candidate["candidate_span"])
    # They are different top-level keys, not one merged blob.
    assert "source_anchor" in docket
    assert "candidates_by_id" in docket
    assert docket["source_anchor"] is not docket["candidates_by_id"]


def test_the_candidate_anchor_still_points_back_at_the_framed_source() -> None:
    """Separation is presentational; the candidate never loses its provenance."""
    candidate = framing_extract().candidates[0]
    assert candidate["source_anchors"] == [framing_anchor()]
    assert DRAFT_FRAMING in str(candidate["source_anchors"][0]["quote"])


def test_framing_is_never_recorded_as_candidate_authority_metadata() -> None:
    """Draft standing is source context at this stage and confers nothing."""
    docket = build_review_docket([framing_extract()]).to_json()
    candidate = next(iter(docket["candidates_by_id"].values()))
    assert set(candidate) == {
        "unit_id",
        "candidate_span",
        "unit_type",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    }
    assert candidate["interpretation_state"] == "extracted"
    assert candidate["epistemic_state"] == "uncertain"
    assert docket["institutional_admission"] is False
    assert "not admitted" in str(docket["candidate_status"])
    for invented in ("standing", "framing", "draft", "authority", "admitted", "confidence"):
        assert invented not in candidate, invented


def test_no_source_context_field_was_added_to_the_docket() -> None:
    """The anchor already preserved the excerpt, so nothing new was introduced."""
    docket = build_review_docket([framing_extract()]).to_json()
    assert set(docket) == {
        "candidate_contract",
        "candidate_status",
        "docket_id",
        "source_anchor",
        "agreement_state",
        "proposal_sets",
        "candidates_by_id",
        "institutional_admission",
    }


def test_a_docket_over_an_overreaching_span_shows_the_overreach_rather_than_hiding_it() -> None:
    """An unseparated span is reported as returned, so review can see the defect."""
    body = {"candidates": [{"candidate_span": DRAFT_SOURCE, "unit_type": "obligation"}]}
    extraction = propose_candidate_units(
        source_text=DRAFT_SOURCE,
        source_anchor=framing_anchor(),
        provider=FakeProvider("p1", json.dumps(body)),
    )
    docket = build_review_docket([extraction]).to_json()
    candidate = next(iter(docket["candidates_by_id"].values()))
    assert candidate["candidate_span"] == DRAFT_SOURCE
    assert DRAFT_FRAMING in str(candidate["candidate_span"])


def test_the_same_proposition_under_different_anchors_stays_two_docket_entries() -> None:
    """Source-instance identity is preserved; nothing merges across anchors."""
    first = framing_extract()
    plain_anchor = dict(framing_anchor())
    plain_anchor["anchor_id"] = "A-PLAIN"
    body = {"candidates": [{"candidate_span": DRAFT_PROPOSITION, "unit_type": "obligation"}]}
    second = propose_candidate_units(
        source_text=DRAFT_SOURCE,
        source_anchor=plain_anchor,
        provider=FakeProvider("p2", json.dumps(body)),
    )
    assert first.candidates[0]["candidate_span"] == second.candidates[0]["candidate_span"]
    assert first.candidates[0]["unit_id"] != second.candidates[0]["unit_id"]
    with pytest.raises(ValueError, match="one source_anchor"):
        build_review_docket([first, second])
