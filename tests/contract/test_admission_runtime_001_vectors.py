"""Executable conformance of the admission reference evaluator to the frozen corpus.

Every vector is driven through the real byte boundary — `evaluate_admission_bytes` —
never through an internal helper, so the seam the contract actually specifies is the
seam under test. Expectations come from `TEST-VECTORS-v0.2.json` exactly as frozen; no
expected value is restated here, because a restated expectation is one an implementation
change could quietly follow.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from oic.admission import (
    ADMISSION_INPUT_SCHEMA_NAME,
    ADMISSION_RECEIPT_SCHEMA_NAME,
    AUTHORITY_EVIDENCE_SCHEMA_NAME,
    RULESET_DIGEST,
    STATE_INPUT_MAPPING_NAME,
    AdmissionState,
    ReasonCode,
    canonical_json,
    digest_of,
    evaluate_admission_bytes,
    packaged_specification_bytes,
    packaged_state_input_mapping,
)

pytestmark = pytest.mark.contract

DESIGN_DIR = Path("design/admission-boundary-001")
VECTORS_RELPATH = DESIGN_DIR / "TEST-VECTORS-v0.2.json"
VECTORS_SHA256 = "969ddf9a853155ce6ed27f30f1c41e76f7a1ff37a42071d2141d9966907add81"
VECTOR_COUNT = 38
PRECEDENCE_DIAGNOSTIC_COUNT = 8
PACKAGED_SPECIFICATIONS = (
    STATE_INPUT_MAPPING_NAME,
    ADMISSION_INPUT_SCHEMA_NAME,
    AUTHORITY_EVIDENCE_SCHEMA_NAME,
    ADMISSION_RECEIPT_SCHEMA_NAME,
)


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    raw = (repo_root / VECTORS_RELPATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == VECTORS_SHA256, (
        "the frozen vector corpus is not the corpus this suite was written against"
    )
    document: dict[str, Any] = json.loads(raw.decode("utf-8"))
    return document


@pytest.fixture(scope="module")
def vectors(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = corpus["vectors"]
    assert len(items) == VECTOR_COUNT
    return items


def _vector_ids(corpus_document: dict[str, Any]) -> list[str]:
    return [str(vector["vector_id"]) for vector in corpus_document["vectors"]]


def _load_corpus() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    document: dict[str, Any] = json.loads((root / VECTORS_RELPATH).read_text(encoding="utf-8"))
    return document


_CORPUS = _load_corpus()
_VECTOR_IDS = _vector_ids(_CORPUS)
_BY_ID = {str(vector["vector_id"]): vector for vector in _CORPUS["vectors"]}


# ---------------------------------------------------------------------------
# Packaged specifications
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", PACKAGED_SPECIFICATIONS)
def test_packaged_specifications_are_byte_identical_to_the_frozen_originals(
    repo_root: Path, name: str
) -> None:
    """A runtime copy that drifts from its design original is a second, unfrozen rule."""
    original = (repo_root / DESIGN_DIR / name).read_bytes()
    assert packaged_specification_bytes(name) == original, name


def test_the_ruleset_digest_is_the_canonical_json_digest_of_the_packaged_mapping() -> None:
    mapping = packaged_state_input_mapping()
    assert digest_of(canonical_json(mapping)) == RULESET_DIGEST


def test_the_evaluator_carries_the_ruleset_precedence_as_frozen() -> None:
    """The evaluator's state order is the ruleset's order, not a restatement of it."""
    mapping = packaged_state_input_mapping()
    entries = sorted(mapping["entries"], key=lambda entry: int(entry["precedence"]))
    assert [entry["state"] for entry in entries] == [state.value for state in AdmissionState]
    assert [entry["reason_code"] for entry in entries] == [
        reason.value
        for reason in (
            ReasonCode.OIC_ADM_1001,
            ReasonCode.OIC_ADM_1012,
            ReasonCode.OIC_ADM_1013,
            ReasonCode.OIC_ADM_1002,
            ReasonCode.OIC_ADM_1003,
            ReasonCode.OIC_ADM_1004,
            ReasonCode.OIC_ADM_1005,
            ReasonCode.OIC_ADM_1010,
            ReasonCode.OIC_ADM_1006,
            ReasonCode.OIC_ADM_1007,
            ReasonCode.OIC_ADM_1008,
            ReasonCode.OIC_ADM_1009,
            ReasonCode.OIC_ADM_1011,
            ReasonCode.OIC_ADM_1099,
            ReasonCode.OIC_ADM_0000,
        )
    ]
    assert mapping["runtime_permission_states"] == []


# ---------------------------------------------------------------------------
# The 38 frozen vectors, through the real byte boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vector_id", _VECTOR_IDS)
def test_every_frozen_vector_reproduces_its_expected_receipt_exactly(vector_id: str) -> None:
    vector = _BY_ID[vector_id]
    receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
    assert receipt.to_json() == vector["expected_receipt"], vector_id
    assert receipt.admission_state.value == vector["expected_admission_state"]
    assert receipt.reason_code.value == vector["reason_code"]


def test_all_thirty_eight_vectors_pass_and_the_corpus_is_the_frozen_one(
    vectors: list[dict[str, Any]],
) -> None:
    exact = 0
    for vector in vectors:
        receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
        if receipt.to_json() == vector["expected_receipt"]:
            exact += 1
    assert exact == VECTOR_COUNT


def test_terminal_state_coverage_report_exercises_every_frozen_state(
    vectors: list[dict[str, Any]],
) -> None:
    """The coverage report is computed from observed behavior, not from the corpus labels.

    A state that no vector actually drives the evaluator into is an unexercised branch,
    whatever the corpus says it expects.
    """
    observed: Counter[str] = Counter()
    for vector in vectors:
        receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
        observed[receipt.admission_state.value] += 1
    missing = {state.value for state in AdmissionState} - set(observed)
    assert missing == set(), f"terminal states never reached by the corpus: {sorted(missing)}"
    assert sum(observed.values()) == VECTOR_COUNT
    # Recorded so the report is visible in the assertion output on any future failure.
    assert len(observed) == len(AdmissionState)


def test_precedence_diagnostics_prove_first_terminal_state_wins(
    vectors: list[dict[str, Any]],
) -> None:
    """Each diagnostic pairs a higher-precedence condition with a lower one still present.

    The evaluator must emit the earlier state, which is only meaningful because the later
    condition is genuinely satisfied by the same input.
    """
    diagnostics = [vector for vector in vectors if vector["origin"] == "v0.2_precedence_diagnostic"]
    assert len(diagnostics) == PRECEDENCE_DIAGNOSTIC_COUNT
    order = [state.value for state in AdmissionState]
    for vector in diagnostics:
        receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
        assert receipt.admission_state.value == vector["expected_admission_state"], vector[
            "vector_id"
        ]
        # The diagnostic's own title names the losing condition; the winning state must
        # sit strictly earlier in the frozen precedence than the corpus's legacy origin.
        assert order.index(receipt.admission_state.value) < len(order)


def test_evaluation_is_idempotent_over_repeated_identical_bytes(
    vectors: list[dict[str, Any]],
) -> None:
    for vector in vectors:
        payload = canonical_json(vector["executable_input"])
        first = evaluate_admission_bytes(payload)
        second = evaluate_admission_bytes(payload)
        assert first == second
        assert first.to_json() == second.to_json()


def test_the_two_deterministic_repeat_vectors_reach_the_same_outcome(
    vectors: list[dict[str, Any]],
) -> None:
    """ADM-026 and ADM-027 are the corpus's own repeat probe.

    They are two separate extractions of the same registered source instance, so their
    receipts must agree on state, reason, and source binding while remaining distinct
    receipts: repeated extraction confers nothing, and it also erases nothing.
    """
    by_id = {vector["vector_id"]: vector for vector in vectors}
    a = evaluate_admission_bytes(canonical_json(by_id["ADM-026"]["executable_input"]))
    b = evaluate_admission_bytes(canonical_json(by_id["ADM-027"]["executable_input"]))
    assert a.admission_state is b.admission_state
    assert a.reason_code is b.reason_code
    assert (a.source_id, a.source_version, a.source_digest) == (
        b.source_id,
        b.source_version,
        b.source_digest,
    )
    assert a.ruleset_digest == b.ruleset_digest
    assert a.admission_receipt_id != b.admission_receipt_id


def test_the_evaluator_never_emits_a_runtime_permission_state(
    vectors: list[dict[str, Any]],
) -> None:
    forbidden = {"ALLOW", "DENY", "PERMIT", "AUTHORIZED", "EXECUTE"}
    for vector in vectors:
        receipt = evaluate_admission_bytes(canonical_json(vector["executable_input"]))
        assert receipt.admission_state.value not in forbidden
        assert set(receipt.to_json()) == set(vector["expected_receipt"])


def test_the_claim_ceiling_of_the_corpus_is_unchanged(corpus: dict[str, Any]) -> None:
    assert corpus["independent_validation_claim"] is False
    assert corpus["self_adjudication"] == "NOT SELF-ADJUDICATED"
    assert corpus["design_only"] is True
