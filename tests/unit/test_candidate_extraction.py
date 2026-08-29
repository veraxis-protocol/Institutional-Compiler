from __future__ import annotations

import json
from pathlib import Path

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


# --------------------------------------------------------------------------
# OIC-CANDIDATE-SEMANTICS-004: framing separation
#
# 004 changes the prompt contract and nothing else. These tests therefore split cleanly in
# two: what OIC *asks the provider for*, and what the boundary still *refuses* regardless
# of what comes back. Nothing here asserts that any model complies -- that is what the
# later live regression measures.
#
# The load-bearing property is negative: OIC must not remove framing itself. A phrase
# stripper would make OIC the author of a span it then reports as source-grounded, so the
# tests below pin that an overreaching span is accepted byte-for-byte and recorded.
# --------------------------------------------------------------------------

DRAFT_SOURCE = (
    "DRAFT — NOT YET ADOPTED. A payment above $10,000 requires approval by the "
    "Chief Financial Officer."
)
HYPOTHETICAL_SOURCE = (
    "For the sake of illustration, suppose a rule stated that a payment above $10,000 "
    "requires approval by the Chief Financial Officer."
)
ILLUSTRATIVE_SOURCE = (
    "The following example is not authoritative: a contractor must return unused "
    "equipment within ten days of contract end."
)
UNVERIFIED_SOURCE = (
    "UNVERIFIED EXTRACT — PROVENANCE NOT ESTABLISHED. A payment above $10,000 requires "
    "approval by the Chief Financial Officer."
)
NON_AUTHORITATIVE_SOURCE = (
    "DEVELOPMENT SYNTHETIC SOURCE — NOT AN AUTHORITATIVE POLICY. A payment above $10,000 "
    "requires approval by the Chief Financial Officer."
)
PROPOSITION = "A payment above $10,000 requires approval by the Chief Financial Officer."


def flat(text: str) -> str:
    """Collapse the prompt's hard wrapping so a prose assertion survives it."""
    return " ".join(text.split())


# ---- 1-5: the outbound contract states the framing rule -------------------


def test_contract_asks_for_the_proposition_without_its_status_framing() -> None:
    system = flat(outbound().system_prompt)
    assert "Quote the proposition, not the source's commentary about the proposition." in system
    assert "grammatically separable from the proposition, leave it outside the span" in system


@pytest.mark.parametrize(
    "structure",
    ["a draft", "a proposal", "a hypothetical", "an illustration", "an example"],
)
def test_contract_names_each_separable_framing_structure(structure: str) -> None:
    assert structure in flat(outbound().system_prompt), structure


def test_contract_names_attribution_and_unadopted_unverified_standing() -> None:
    system = flat(outbound().system_prompt)
    assert "a quotation of another party" in system
    assert "unadopted, unverified or non-authoritative" in system


def test_contract_keeps_framing_from_suppressing_discovery() -> None:
    """Rule 4: framing separation is a quoting decision, never a standing finding."""
    system = flat(outbound().system_prompt)
    assert "Source standing is not a discovery criterion." in system
    assert "must not suppress a candidate that appears in the fragment" in system
    assert (
        "it does not decide whether the proposition is authoritative, adopted, valid, "
        "admitted, enforceable, or legally operative" in system
    )
    assert "The source anchor keeps the framing." in system


@pytest.mark.parametrize(
    "source",
    [
        DRAFT_SOURCE,
        HYPOTHETICAL_SOURCE,
        ILLUSTRATIVE_SOURCE,
        UNVERIFIED_SOURCE,
        NON_AUTHORITATIVE_SOURCE,
    ],
)
def test_framing_never_suppresses_a_candidate_at_the_boundary(source: str) -> None:
    """Non-authoritative and unverified framing still yield candidate material."""
    result = extract(candidate(PROPOSITION if PROPOSITION in source else source), source=source)
    assert len(result.candidates) == 1
    assert result.candidates[0]["epistemic_state"] == "uncertain"
    assert result.candidates[0]["interpretation_state"] == "extracted"


# ---- 6-11: material content survives separation ---------------------------


def test_the_contract_forbids_buying_a_shorter_span_with_material_content() -> None:
    system = flat(outbound().system_prompt)
    assert "Never buy a shorter span with material content." in system
    assert "Dropping material content is a worse error than including framing." in system


@pytest.mark.parametrize(
    "element",
    [
        "threshold",
        "amount",
        "deadline",
        "condition",
        "exception",
        "recipient",
        "prohibition",
        "advisory wording",
        "trigger",
        "consequence",
    ],
)
def test_the_contract_enumerates_every_material_element_that_must_stay(element: str) -> None:
    assert element in flat(outbound().system_prompt), element


def test_a_threshold_survives_framing_separation() -> None:
    result = extract(candidate(PROPOSITION), source=DRAFT_SOURCE)
    span = str(result.candidates[0]["candidate_span"])
    assert "$10,000" in span
    assert "DRAFT" not in span


def test_a_recipient_survives_framing_separation() -> None:
    span = str(
        extract(candidate(PROPOSITION), source=UNVERIFIED_SOURCE).candidates[0]["candidate_span"]
    )
    assert "Chief Financial Officer" in span
    assert "UNVERIFIED EXTRACT" not in span


def test_a_condition_survives_framing_separation() -> None:
    source = (
        "DRAFT FOR CONSULTATION. If a supplier is on the restricted list, the contract "
        "must not be awarded."
    )
    proposition = "If a supplier is on the restricted list, the contract must not be awarded."
    span = str(
        extract(candidate(proposition, "prohibition"), source=source).candidates[0][
            "candidate_span"
        ]
    )
    assert "If a supplier is on the restricted list" in span
    assert "DRAFT FOR CONSULTATION" not in span


def test_an_exception_survives_framing_separation() -> None:
    source = (
        "NOT YET IN FORCE. Travel bookings must use the central agency, except for "
        "travel funded entirely by an external host."
    )
    proposition = (
        "Travel bookings must use the central agency, except for travel funded entirely "
        "by an external host."
    )
    span = str(extract(candidate(proposition), source=source).candidates[0]["candidate_span"])
    assert "except for travel funded entirely by an external host" in span
    assert "NOT YET IN FORCE" not in span


def test_advisory_wording_survives_framing_separation() -> None:
    source = (
        "DRAFT FOR CONSULTATION. Units are advised to review supplier performance before "
        "renewing a contract."
    )
    proposition = "Units are advised to review supplier performance before renewing a contract."
    result = extract(candidate(proposition, "advisory"), source=source)
    assert result.candidates[0]["candidate_span"] == proposition
    assert result.candidates[0]["unit_type"] == "advisory"


# ---- 12-15: separation does not weaken anything the boundary already did ---


def test_multi_unit_extraction_still_separates_two_propositions_under_one_prefix() -> None:
    source = (
        "NOT YET IN FORCE. A purchase requisition must be approved before an order is "
        "placed. Suppliers are paid within forty-five days of invoice."
    )
    first = "A purchase requisition must be approved before an order is placed."
    second = "Suppliers are paid within forty-five days of invoice."
    payload = json.dumps(
        {
            "candidates": [
                {"candidate_span": first, "unit_type": "obligation"},
                {"candidate_span": second, "unit_type": "temporal_trigger"},
            ]
        }
    )
    result = extract(payload, source=source)
    spans = [str(item["candidate_span"]) for item in result.candidates]
    assert spans == [first, second]
    assert all("NOT YET IN FORCE" not in span for span in spans)
    assert len({str(item["unit_id"]) for item in result.candidates}) == 2


def test_a_separated_span_is_still_literal_source_text() -> None:
    result = extract(candidate(PROPOSITION), source=DRAFT_SOURCE)
    assert str(result.candidates[0]["candidate_span"]) in DRAFT_SOURCE


@pytest.mark.parametrize(
    "span",
    [
        "A payment over $10,000 requires approval by the Chief Financial Officer.",
        "A payment above $10,000 requires CFO approval.",
        "Each grant over 5,000 euro must be countersigned by the Programme Director.",
    ],
)
def test_a_paraphrased_or_invented_span_still_fails_grounding_under_framing(span: str) -> None:
    with pytest.raises(CandidateGroundingError, match="literal contiguous span"):
        extract(candidate(span), source=DRAFT_SOURCE)


@pytest.mark.parametrize("field", sorted(_REMOVED_SEMANTIC_ROLE_KEYS))
def test_removed_semantic_roles_still_fail_closed_under_framing(field: str) -> None:
    payload = json.dumps(
        {"candidates": [{"candidate_span": PROPOSITION, "unit_type": "obligation", field: "x"}]}
    )
    with pytest.raises(CandidateBoundaryError, match="removed semantic-role fields"):
        extract(payload, source=DRAFT_SOURCE)


@pytest.mark.parametrize("field", sorted(_MODEL_FORBIDDEN_AUTHORITY_KEYS))
def test_authority_fields_still_fail_closed_under_framing(field: str) -> None:
    payload = json.dumps(
        {"candidates": [{"candidate_span": PROPOSITION, "unit_type": "obligation", field: "x"}]}
    )
    with pytest.raises(CandidateBoundaryError, match="authority-controlled"):
        extract(payload, source=DRAFT_SOURCE)


def test_no_field_was_added_by_004() -> None:
    from oic.candidate_extraction import _MODEL_ALLOWED_KEYS

    assert set(_MODEL_ALLOWED_KEYS) == {"candidate_span", "unit_type"}
    result = extract(candidate(PROPOSITION), source=DRAFT_SOURCE)
    assert set(result.candidates[0]) == {
        "unit_id",
        "candidate_span",
        "unit_type",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    }
    for invented in ("context", "framing", "standing", "source_context", "confidence"):
        payload = json.dumps(
            {
                "candidates": [
                    {"candidate_span": PROPOSITION, "unit_type": "obligation", invented: "x"}
                ]
            }
        )
        with pytest.raises(CandidateBoundaryError):
            extract(payload, source=DRAFT_SOURCE)


# ---- 18-19: OIC never separates framing itself ----------------------------


@pytest.mark.parametrize(
    ("source", "overreaching_span"),
    [
        (DRAFT_SOURCE, DRAFT_SOURCE),
        (HYPOTHETICAL_SOURCE, HYPOTHETICAL_SOURCE),
        (UNVERIFIED_SOURCE, UNVERIFIED_SOURCE),
    ],
)
def test_an_overreaching_span_is_accepted_byte_for_byte_and_never_trimmed(
    source: str, overreaching_span: str
) -> None:
    """The defect 004 addresses is left visible, not silently repaired."""
    result = extract(candidate(overreaching_span), source=source)
    assert result.candidates[0]["candidate_span"] == overreaching_span
    assert str(result.candidates[0]["candidate_span"]).startswith(overreaching_span[:20])


def test_leading_and_trailing_source_whitespace_in_a_span_is_not_normalized() -> None:
    source = "  DRAFT.  Payments must be approved.  "
    span = "  DRAFT.  Payments must be approved.  "
    result = extract(candidate(span), source=source)
    assert result.candidates[0]["candidate_span"] == span


def test_no_deterministic_phrase_stripper_or_trimming_exists(repo_root: Path) -> None:
    """Source-level: nothing in the module can rewrite a provider-proposed span."""
    module = (repo_root / "src/oic/candidate_extraction.py").read_text(encoding="utf-8")
    for rewriting in (
        "re.sub",
        ".replace(",
        "removeprefix",
        "removesuffix",
        "partition(",
        "lstrip(",
        "rstrip(",
        "FRAMING_PREFIXES",
        "STRIP_",
    ):
        assert rewriting not in module, rewriting
    # The only compiled pattern is the source-anchor digest format.
    assert module.count("re.compile") == 1
    assert "_SHA256_PATTERN = re.compile" in module


def test_the_prompt_contains_no_corpus_specimen_language(repo_root: Path) -> None:
    """Examples must teach the rule, never a corpus answer."""
    import json as _json

    system = outbound().system_prompt
    user = outbound().user_prompt.split("SOURCE FRAGMENT:")[0]
    root = repo_root / "benchmarks/characterization"
    for relpath in (
        "candidate-semantics-003/CORPUS-v0.3.json",
        "candidate-semantics-004/CORPUS-v0.4.json",
    ):
        document = _json.loads((root / relpath).read_text(encoding="utf-8"))
        for specimen in document["specimens"]:
            assert specimen["source_text"] not in system, specimen["specimen_id"]
            assert specimen["source_text"] not in user, specimen["specimen_id"]
            for key in ("separable_framing_spans", "candidate_span_bounds"):
                for span in specimen.get(key) or []:
                    assert span not in system, (specimen["specimen_id"], span)
                    assert span not in user, (specimen["specimen_id"], span)


# ---- 22-24: identity is unchanged by 004 ----------------------------------


def test_candidate_id_remains_deterministic_and_schema_tagged_003() -> None:
    """004 changed the prompt, not the schema, so the identity tag does not move."""
    from oic.candidate_extraction import _candidate_id

    first = extract(candidate(PROPOSITION), source=DRAFT_SOURCE)
    second = extract(candidate(PROPOSITION), source=DRAFT_SOURCE)
    assert first.candidates[0]["unit_id"] == second.candidates[0]["unit_id"]
    assert str(first.candidates[0]["unit_id"]).startswith("cnu-")
    expected = _candidate_id(
        semantic={"candidate_span": PROPOSITION, "unit_type": "obligation"},
        source_anchor=anchor(),
    )
    assert first.candidates[0]["unit_id"] == expected


def test_the_same_proposition_at_a_different_anchor_is_a_different_identity() -> None:
    """Source-instance-aware by design. Cross-source equivalence is Institutional IR's."""
    here = extract(candidate(PROPOSITION), source=DRAFT_SOURCE, source_anchor=anchor("1"))
    there = extract(candidate(PROPOSITION), source=DRAFT_SOURCE, source_anchor=anchor("2"))
    assert here.candidates[0]["candidate_span"] == there.candidates[0]["candidate_span"]
    assert here.candidates[0]["unit_id"] != there.candidates[0]["unit_id"]


def test_equivalent_propositions_from_different_framings_are_not_forced_to_share_an_id() -> None:
    """CSEM-021 and CSEM-027 state the same rule; 004 does not merge their identities."""
    drafted = extract(candidate(PROPOSITION), source=DRAFT_SOURCE, source_anchor=anchor("draft"))
    plain = extract(candidate(PROPOSITION), source=PROPOSITION, source_anchor=anchor("plain"))
    assert drafted.candidates[0]["candidate_span"] == plain.candidates[0]["candidate_span"]
    assert drafted.candidates[0]["unit_id"] != plain.candidates[0]["unit_id"]
