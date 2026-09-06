"""Behavioral tests for the admission reference evaluator.

Two things are under test and they are kept apart on purpose:

* the **byte boundary** — inputs that are not admissible executable inputs at all, which
  must raise :class:`AdmissionInputBoundaryError` and must never become an admission
  state; and
* the **state machine** — admissible inputs, each of which must produce exactly one
  frozen terminal state.

Fixtures are built by changing one fact at a time in a frozen vector, so each test names
the single observable difference that moves the outcome.
"""

from __future__ import annotations

import ast
import copy
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from oic.admission import (
    EVALUATOR_ID,
    EVALUATOR_VERSION,
    RULESET_DIGEST,
    RULESET_ID,
    AdmissionCanonicalFormError,
    AdmissionEncodingError,
    AdmissionError,
    AdmissionEvidenceIntegrityError,
    AdmissionEvidenceOrderError,
    AdmissionInputBoundaryError,
    AdmissionJSONError,
    AdmissionReceipt,
    AdmissionRulesetError,
    AdmissionSchemaError,
    AdmissionState,
    AdmissionTimestampError,
    canonical_json,
    digest_of,
    evaluate_admission_bytes,
)

VECTORS_RELPATH = Path("design/admission-boundary-001/TEST-VECTORS-v0.2.json")
_ROOT = Path(__file__).resolve().parents[2]
_CORPUS: dict[str, Any] = json.loads((_ROOT / VECTORS_RELPATH).read_text(encoding="utf-8"))
_INPUTS: dict[str, dict[str, Any]] = {
    str(vector["vector_id"]): vector["executable_input"] for vector in _CORPUS["vectors"]
}

#: An input whose frozen expectation is ADMITTED, used as the base for single-fact edits.
ADMITTED_VECTOR = "ADM-001"
OTHER_DIGEST = "sha256:" + "0" * 64


def _base(vector_id: str = ADMITTED_VECTOR) -> dict[str, Any]:
    return copy.deepcopy(_INPUTS[vector_id])


def _seal(document: dict[str, Any]) -> bytes:
    """Recompute evidence digests and canonical evidence order, then serialize.

    This is what an institution's evidence custodian does before an input is frozen. The
    evaluator itself never does it: it verifies and refuses.
    """
    for item in document["authority_evidence"]:
        item.pop("evidence_digest", None)
        item["evidence_digest"] = digest_of(canonical_json(item))
    document["authority_evidence"].sort(
        key=lambda item: (item["evidence_id"], item["evidence_digest"])
    )
    return canonical_json(document)


def _state(document: dict[str, Any]) -> AdmissionState:
    return evaluate_admission_bytes(_seal(document)).admission_state


# ---------------------------------------------------------------------------
# The byte boundary. None of these is an admission outcome.
# ---------------------------------------------------------------------------


def test_a_valid_frozen_input_is_accepted_so_the_rejections_below_mean_something() -> None:
    receipt = evaluate_admission_bytes(canonical_json(_base()))
    assert isinstance(receipt, AdmissionReceipt)
    assert receipt.admission_state is AdmissionState.ADMITTED


def test_bytes_that_are_not_utf8_are_refused() -> None:
    with pytest.raises(AdmissionEncodingError):
        evaluate_admission_bytes(b'{"a"\xff:1}')


def test_a_utf8_byte_order_mark_is_refused() -> None:
    with pytest.raises(AdmissionEncodingError):
        evaluate_admission_bytes(b"\xef\xbb\xbf" + canonical_json(_base()))


def test_a_str_is_refused_rather_than_encoded() -> None:
    with pytest.raises(AdmissionInputBoundaryError):
        evaluate_admission_bytes(canonical_json(_base()).decode("utf-8"))  # type: ignore[arg-type]


def test_empty_bytes_are_refused() -> None:
    with pytest.raises(AdmissionJSONError):
        evaluate_admission_bytes(b"")


def test_a_trailing_newline_is_refused_rather_than_stripped() -> None:
    with pytest.raises(AdmissionCanonicalFormError):
        evaluate_admission_bytes(canonical_json(_base()) + b"\n")


def test_leading_whitespace_is_refused() -> None:
    with pytest.raises(AdmissionCanonicalFormError):
        evaluate_admission_bytes(b" " + canonical_json(_base()))


def test_pretty_printed_json_is_refused_rather_than_compacted() -> None:
    payload = json.dumps(_base(), sort_keys=True, indent=2).encode("utf-8")
    with pytest.raises(AdmissionCanonicalFormError):
        evaluate_admission_bytes(payload)


def test_unsorted_object_keys_are_refused_rather_than_sorted() -> None:
    payload = json.dumps(_base(), sort_keys=False, separators=(",", ":")).encode("utf-8")
    with pytest.raises(AdmissionCanonicalFormError):
        evaluate_admission_bytes(payload)


def test_ascii_escaped_strings_are_refused() -> None:
    document = _base()
    document["candidate"]["candidate_span"] = "Récords are kept."
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    with pytest.raises(AdmissionCanonicalFormError):
        evaluate_admission_bytes(payload)


def test_a_duplicate_object_key_is_refused() -> None:
    payload = canonical_json(_base())
    assert payload.startswith(b"{")
    injected = b'{"evaluation_time":"2026-06-01T00:00:00Z",' + payload[1:]
    with pytest.raises(AdmissionJSONError, match="duplicate object key"):
        evaluate_admission_bytes(injected)


@pytest.mark.parametrize("payload", [b"[]", b'"text"', b"12", b"null", b"true"])
def test_a_json_value_that_is_not_an_object_is_refused(payload: bytes) -> None:
    with pytest.raises(AdmissionJSONError):
        evaluate_admission_bytes(payload)


def test_trailing_content_after_the_object_is_refused() -> None:
    with pytest.raises(AdmissionJSONError):
        evaluate_admission_bytes(canonical_json(_base()) + b"{}")


@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity"])
def test_non_json_numeric_literals_are_refused(literal: bytes) -> None:
    payload = canonical_json(_base()).replace(b'"page":null', b'"page":' + literal, 1)
    assert payload != canonical_json(_base())
    with pytest.raises(AdmissionInputBoundaryError):
        evaluate_admission_bytes(payload)


def test_a_missing_required_top_level_field_is_refused() -> None:
    document = _base()
    del document["evaluation_scope"]
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


def test_an_unknown_top_level_field_is_refused() -> None:
    document = _base()
    document["input_digest"] = OTHER_DIGEST
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


def test_a_candidate_carrying_an_authority_claim_is_refused() -> None:
    """The candidate projection has no field in which a model could assert authority."""
    document = _base()
    document["candidate"]["authority"] = "board"
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        ("unit_id", "not-a-candidate-id"),
        ("interpretation_state", "interpreted"),
        ("epistemic_state", "established"),
        ("unit_type", "invented_type"),
    ],
)
def test_a_candidate_outside_the_frozen_projection_is_refused(pointer: str, value: str) -> None:
    document = _base()
    document["candidate"][pointer] = value
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


@pytest.mark.parametrize(
    ("field", "value"),
    [("evaluator_id", "some-other-evaluator"), ("evaluator_version", "0.2")],
)
def test_an_input_naming_a_different_evaluator_is_refused(field: str, value: str) -> None:
    document = _base()
    document["evaluator"][field] = value
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


def test_an_input_naming_a_different_ruleset_id_is_refused() -> None:
    document = _base()
    document["ruleset"]["ruleset_id"] = "SOME-OTHER-RULESET"
    with pytest.raises(AdmissionInputBoundaryError):
        evaluate_admission_bytes(canonical_json(document))


def test_caller_selected_admission_rules_are_refused() -> None:
    document = _base()
    document["ruleset"]["ruleset_digest"] = OTHER_DIGEST
    with pytest.raises(AdmissionRulesetError):
        evaluate_admission_bytes(canonical_json(document))


def test_evidence_out_of_canonical_order_is_refused_rather_than_sorted() -> None:
    document = _base("ADM-017")
    document["authority_evidence"].reverse()
    with pytest.raises(AdmissionEvidenceOrderError):
        evaluate_admission_bytes(canonical_json(document))


def test_a_duplicate_evidence_id_is_refused() -> None:
    document = _base("ADM-017")
    document["authority_evidence"][1]["evidence_id"] = document["authority_evidence"][0][
        "evidence_id"
    ]
    for item in document["authority_evidence"]:
        item.pop("evidence_digest", None)
        item["evidence_digest"] = digest_of(canonical_json(item))
    document["authority_evidence"].sort(
        key=lambda item: (item["evidence_id"], item["evidence_digest"])
    )
    with pytest.raises(AdmissionEvidenceOrderError):
        evaluate_admission_bytes(canonical_json(document))


def test_an_evidence_digest_that_does_not_recompute_is_refused() -> None:
    document = _base()
    document["authority_evidence"][0]["issuer_id"] = "a-different-issuer"
    with pytest.raises(AdmissionEvidenceIntegrityError):
        evaluate_admission_bytes(canonical_json(document))


def test_a_forged_evidence_digest_is_refused() -> None:
    document = _base()
    document["authority_evidence"][0]["evidence_digest"] = OTHER_DIGEST
    with pytest.raises(AdmissionEvidenceIntegrityError):
        evaluate_admission_bytes(canonical_json(document))


def test_a_non_normalized_timestamp_offset_is_refused() -> None:
    document = _base()
    document["evaluation_time"] = "2026-06-01T00:00:00+00:00"
    with pytest.raises(AdmissionSchemaError):
        evaluate_admission_bytes(canonical_json(document))


def test_a_fractional_second_timestamp_is_refused_rather_than_truncated() -> None:
    document = _base()
    document["evaluation_time"] = "2026-06-01T00:00:00.000Z"
    with pytest.raises(AdmissionTimestampError):
        evaluate_admission_bytes(_seal(document))


def test_an_input_boundary_failure_is_never_an_admission_state() -> None:
    """A malformed input has not been evaluated. Converting it to a terminal state would
    manufacture institutional evidence out of a parse failure."""
    with pytest.raises(AdmissionInputBoundaryError) as caught:
        evaluate_admission_bytes(b"{}")
    # A boundary failure carries no state, so it cannot name one either: an operator
    # reading the message must not be able to record it as an admission outcome.
    message = str(caught.value)
    for state in AdmissionState:
        assert state.value not in message


def test_a_boundary_error_message_does_not_echo_the_payload() -> None:
    document = _base()
    document["candidate"]["candidate_span"] = "SECRET-CANARY-VALUE"
    document["input_digest"] = OTHER_DIGEST
    with pytest.raises(AdmissionInputBoundaryError) as caught:
        evaluate_admission_bytes(canonical_json(document))
    assert "SECRET-CANARY-VALUE" not in str(caught.value)


# ---------------------------------------------------------------------------
# One frozen terminal state per admissible input
# ---------------------------------------------------------------------------


def test_candidate_input_invalid_when_the_candidate_has_no_source_anchor() -> None:
    document = _base()
    document["candidate"]["source_anchors"] = []
    assert _state(document) is AdmissionState.CANDIDATE_INPUT_INVALID


def test_candidate_input_invalid_when_an_anchor_names_a_different_source() -> None:
    document = _base()
    document["candidate"]["source_anchors"][0]["source_id"] = "some-other-source"
    assert _state(document) is AdmissionState.CANDIDATE_INPUT_INVALID


def test_authority_registry_unavailable_when_the_registry_was_not_observed() -> None:
    document = _base()
    document["source_registration"]["registry_observation"]["availability"] = "UNAVAILABLE"
    document["source_registration"]["registry_observation"]["freshness"] = "NOT_OBSERVED"
    assert _state(document) is AdmissionState.AUTHORITY_REGISTRY_UNAVAILABLE


def test_authority_evidence_stale_when_the_observation_is_beyond_its_freshness_bound() -> None:
    document = _base()
    document["source_registration"]["registry_observation"]["freshness"] = "STALE"
    assert _state(document) is AdmissionState.AUTHORITY_EVIDENCE_STALE


def test_source_not_registered_when_the_registry_holds_no_entry() -> None:
    document = _base()
    document["source_registration"]["registered"] = False
    assert _state(document) is AdmissionState.SOURCE_NOT_REGISTERED


def test_source_version_mismatch_when_no_evidence_binds_the_registered_version() -> None:
    document = _base()
    evidence = document["authority_evidence"][0]
    evidence["source_version"] = "some-other-version"
    evidence["admission_warrant"]["source_version"] = "some-other-version"
    assert _state(document) is AdmissionState.SOURCE_VERSION_MISMATCH


def test_source_digest_mismatch_when_the_candidate_anchor_bytes_differ() -> None:
    document = _base()
    document["candidate"]["source_anchors"][0]["content_hash"] = OTHER_DIGEST
    assert _state(document) is AdmissionState.SOURCE_DIGEST_MISMATCH


def test_source_digest_mismatch_when_no_evidence_binds_the_registered_digest() -> None:
    document = _base()
    evidence = document["authority_evidence"][0]
    evidence["source_digest"] = OTHER_DIGEST
    evidence["admission_warrant"]["source_digest"] = OTHER_DIGEST
    assert _state(document) is AdmissionState.SOURCE_DIGEST_MISMATCH


def test_missing_authority_evidence_when_no_evidence_is_supplied() -> None:
    document = _base()
    document["authority_evidence"] = []
    assert _state(document) is AdmissionState.MISSING_AUTHORITY_EVIDENCE


def test_out_of_scope_when_the_requested_applicability_is_outside_the_warrant() -> None:
    document = _base()
    document["evaluation_scope"]["applicability"] = "something-else"
    assert _state(document) is AdmissionState.OUT_OF_SCOPE


def test_out_of_scope_when_the_requested_jurisdiction_is_outside_the_warrant() -> None:
    document = _base()
    document["evaluation_scope"]["jurisdiction"] = "another-jurisdiction"
    assert _state(document) is AdmissionState.OUT_OF_SCOPE


def test_not_yet_effective_when_evaluation_time_precedes_effectiveness() -> None:
    document = _base()
    document["evaluation_time"] = "2025-06-01T00:00:00Z"
    assert _state(document) is AdmissionState.NOT_YET_EFFECTIVE


def test_expired_when_evaluation_time_is_at_or_after_effective_until() -> None:
    document = _base()
    document["source_registration"]["effective_until"] = "2026-03-01T00:00:00Z"
    assert _state(document) is AdmissionState.EXPIRED


def test_the_effective_interval_is_half_open_at_its_end() -> None:
    document = _base()
    document["source_registration"]["effective_until"] = document["evaluation_time"]
    assert _state(document) is AdmissionState.EXPIRED


def test_superseded_when_evaluation_time_is_at_or_after_supersession() -> None:
    document = _base()
    document["source_registration"]["superseded_at"] = "2026-03-01T00:00:00Z"
    assert _state(document) is AdmissionState.SUPERSEDED


def test_revoked_when_evaluation_time_is_at_or_after_revocation() -> None:
    document = _base()
    document["source_registration"]["revoked_at"] = "2026-03-01T00:00:00Z"
    assert _state(document) is AdmissionState.REVOKED


def test_revoked_when_the_admission_warrant_itself_is_revoked() -> None:
    document = _base()
    warrant = document["authority_evidence"][0]["admission_warrant"]
    warrant["status"] = "REVOKED"
    warrant["revoked_at"] = "2026-03-01T00:00:00Z"
    assert _state(document) is AdmissionState.REVOKED


def test_conflicting_authority_when_two_operative_authority_bases_overlap() -> None:
    document = _base()
    rival = copy.deepcopy(document["authority_evidence"][0])
    rival["evidence_id"] = "AE-001-RIVAL"
    rival["authority_basis_ref"] = "charter:a-different-basis"
    rival["admission_warrant"]["warrant_id"] = "AW-001-RIVAL"
    document["authority_evidence"].append(rival)
    assert _state(document) is AdmissionState.CONFLICTING_AUTHORITY


def test_a_conflict_is_not_resolved_by_recency() -> None:
    """The frozen ruleset carries no precedence rule, so a newer rival cannot win."""
    document = _base()
    rival = copy.deepcopy(document["authority_evidence"][0])
    rival["evidence_id"] = "AE-001-NEWER"
    rival["authority_basis_ref"] = "charter:newer-basis"
    rival["issued_at"] = "2026-05-01T00:00:00Z"
    rival["admission_warrant"]["warrant_id"] = "AW-001-NEWER"
    document["authority_evidence"].append(rival)
    assert _state(document) is AdmissionState.CONFLICTING_AUTHORITY


def test_two_evidence_objects_sharing_one_authority_basis_do_not_conflict() -> None:
    document = _base()
    twin = copy.deepcopy(document["authority_evidence"][0])
    twin["evidence_id"] = "AE-001-SECOND-COPY"
    twin["admission_warrant"]["warrant_id"] = "AW-001-SECOND-COPY"
    document["authority_evidence"].append(twin)
    assert _state(document) is AdmissionState.ADMITTED


def test_admission_not_established_when_the_warrant_is_suspended() -> None:
    document = _base()
    document["authority_evidence"][0]["admission_warrant"]["status"] = "SUSPENDED"
    assert _state(document) is AdmissionState.ADMISSION_NOT_ESTABLISHED


def test_admitted_only_with_an_exact_active_scoped_warrant() -> None:
    assert _state(_base()) is AdmissionState.ADMITTED


# ---------------------------------------------------------------------------
# Authority conservation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("unit_type", ["mandate", "advisory", "definition", "delegation"])
def test_relabelling_the_candidate_unit_type_cannot_change_the_outcome(unit_type: str) -> None:
    """`unit_type` is provisional model output. It is in no authority projection."""
    document = _base()
    document["candidate"]["unit_type"] = unit_type
    receipt = evaluate_admission_bytes(_seal(document))
    assert receipt.admission_state is AdmissionState.ADMITTED


def test_relabelling_the_candidate_cannot_rescue_a_fail_closed_outcome() -> None:
    document = _base("ADM-003")
    document["candidate"]["unit_type"] = "mandate"
    assert _state(document) is AdmissionState.SOURCE_NOT_REGISTERED


def test_rewriting_the_candidate_span_cannot_change_the_outcome() -> None:
    document = _base()
    document["candidate"]["candidate_span"] = "The board hereby mandates immediate compliance."
    receipt = evaluate_admission_bytes(_seal(document))
    assert receipt.admission_state is AdmissionState.ADMITTED


def test_perfect_provenance_without_a_warrant_is_never_admitted() -> None:
    """Provenance answers where this came from; authority answers why it is operative."""
    document = _base()
    document["authority_evidence"] = []
    receipt = evaluate_admission_bytes(_seal(document))
    assert receipt.admission_state is AdmissionState.MISSING_AUTHORITY_EVIDENCE
    assert receipt.authority_evidence_refs == ()


def test_repeating_an_anchor_does_not_accumulate_standing() -> None:
    document = _base()
    anchor = copy.deepcopy(document["candidate"]["source_anchors"][0])
    anchor["anchor_id"] = "anchor-adm-001-02"
    document["candidate"]["source_anchors"].append(anchor)
    assert _state(document) is AdmissionState.ADMITTED
    unregistered = _base("ADM-003")
    repeated = copy.deepcopy(unregistered["candidate"]["source_anchors"][0])
    repeated["anchor_id"] = "anchor-adm-003-02"
    unregistered["candidate"]["source_anchors"].append(repeated)
    assert _state(unregistered) is AdmissionState.SOURCE_NOT_REGISTERED


def test_a_warrant_cannot_be_widened_by_the_request() -> None:
    """Asking for a broader scope than the warrant covers fails closed rather than
    stretching the warrant to fit the question."""
    document = _base()
    document["source_registration"]["applicability_scope"] = ["records", "everything"]
    document["evaluation_scope"]["applicability"] = "everything"
    assert _state(document) is AdmissionState.OUT_OF_SCOPE


def test_the_receipt_records_only_facts_present_in_the_input() -> None:
    document = _base()
    receipt = evaluate_admission_bytes(_seal(document))
    assert receipt.evaluation_time == document["evaluation_time"]
    assert receipt.source_id == document["source_registration"]["source_id"]
    assert receipt.evaluator_id == EVALUATOR_ID
    assert receipt.evaluator_version == EVALUATOR_VERSION
    assert receipt.ruleset_id == RULESET_ID
    assert receipt.ruleset_digest == RULESET_DIGEST
    assert list(receipt.authority_evidence_refs) == [
        item["evidence_id"] for item in document["authority_evidence"]
    ]


def test_the_receipt_is_immutable() -> None:
    receipt = evaluate_admission_bytes(canonical_json(_base()))
    with pytest.raises(AttributeError):
        receipt.admission_state = AdmissionState.ADMITTED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Time comes only from evaluation_time
# ---------------------------------------------------------------------------


def test_the_outcome_moves_only_when_evaluation_time_moves() -> None:
    document = _base()
    document["source_registration"]["revoked_at"] = "2026-06-15T00:00:00Z"
    document["evaluation_time"] = "2026-06-01T00:00:00Z"
    assert _state(copy.deepcopy(document)) is AdmissionState.ADMITTED
    document["evaluation_time"] = "2026-07-01T00:00:00Z"
    assert _state(document) is AdmissionState.REVOKED


def test_an_earlier_receipt_is_not_mutated_by_later_revocation_evidence() -> None:
    before = evaluate_admission_bytes(canonical_json(_base()))
    revoked = _base()
    revoked["source_registration"]["revoked_at"] = "2026-03-01T00:00:00Z"
    after = evaluate_admission_bytes(_seal(revoked))
    assert before.admission_state is AdmissionState.ADMITTED
    assert after.admission_state is AdmissionState.REVOKED
    assert before.admission_receipt_id != after.admission_receipt_id


def test_the_evaluator_reads_no_clock() -> None:
    """Structural, not textual: a wall-clock call is looked for in the parsed module."""
    source = (_ROOT / "src/oic/admission.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_attributes = {"now", "utcnow", "today", "time", "monotonic", "time_ns", "gmtime"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in forbidden_attributes, ast.dump(node.func)
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
    assert "time" not in imported
    assert "random" not in imported
    assert "uuid" not in imported
    assert "os" not in imported
    assert "socket" not in imported
    assert "urllib" not in imported


# ---------------------------------------------------------------------------
# Offline
# ---------------------------------------------------------------------------


def test_the_evaluator_runs_with_sockets_disabled() -> None:
    """The suite disables sockets; this names the guarantee rather than relying on it.

    Both governing schemas carry absolute https `$id` values and the input schema `$ref`s
    one of them by absolute URI. Resolution must still be local.
    """
    with pytest.MonkeyPatch.context() as patcher:

        def _explode(*args: object, **kwargs: object) -> None:
            del args, kwargs
            raise AssertionError("the admission evaluator attempted a network connection")

        patcher.setattr(socket, "socket", _explode)
        patcher.setattr(socket, "create_connection", _explode)
        patcher.setattr(socket, "getaddrinfo", _explode)
        receipt = evaluate_admission_bytes(canonical_json(_base()))
    assert receipt.admission_state is AdmissionState.ADMITTED


def test_every_boundary_error_is_an_admission_error() -> None:
    for error_type in (
        AdmissionEncodingError,
        AdmissionJSONError,
        AdmissionCanonicalFormError,
        AdmissionSchemaError,
        AdmissionTimestampError,
        AdmissionEvidenceOrderError,
        AdmissionEvidenceIntegrityError,
        AdmissionRulesetError,
    ):
        assert issubclass(error_type, AdmissionInputBoundaryError)
        assert issubclass(error_type, AdmissionError)
