"""Contract for the bounded pre-admission candidate-layer freeze."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

FREEZE_DIR = "benchmarks/characterization/candidate-layer-freeze-001"
FREEZE_JSON = f"{FREEZE_DIR}/FREEZE.json"
FREEZE_MD = f"{FREEZE_DIR}/FREEZE.md"
FROZEN_IMPLEMENTATION = "59c6b34a4972c7758ea1ef4c09fd26be5ddb507e"
#: The artifacts Candidate Layer Freeze 001 actually froze. Separately authorized work
#: elsewhere in `src` is outside the freeze; changing one of these is not.
FROZEN_CANDIDATE_LAYER_FILES = (
    "src/oic/candidate_extraction.py",
    "src/oic/model_provider.py",
    "src/oic/nvidia_nim.py",
    "src/oic/review_docket.py",
    "schemas/draft/candidate-normative-unit.schema.json",
)
FROZEN_JSON_SHA256 = "19501da4e34187a745a55bee6cabb10e6361d2b77905a2f668d4a73a086db8df"
EXPECTED_CORPORA = {
    "OIC-CANDIDATE-SEMANTICS-003": (
        "8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a"
    ),
    "OIC-CANDIDATE-SEMANTICS-004": (
        "594cbee619f467ef949690cd56014eb4f8b3c5ba9527596c6e4bef3f242d5386"
    ),
    "OIC-CANDIDATE-SEMANTICS-005": (
        "2d8c5f3f4be2028e00179b4b8eee464b325b8d9efbaf19875b8b783a6139dbf0"
    ),
}
EXPECTED_RECEIPTS = {
    "OIC-CANDIDATE-SEMANTICS-005": (
        "a44b14b81dbd300d8a6d86e1e882ae0dc7eab152ea4f0823f227c71fce64f8bd"
    ),
    "OIC-CANDIDATE-NEGATIVE-STABILITY-001": (
        "3a1dfbb8d43e69800af4f38cf856907fdcdf82108e925723ee745df92ced1408"
    ),
}


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((repo_root / FREEZE_JSON).read_text(encoding="utf-8")))


def _tree(repo_root: Path, revision: str, path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}:{path}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_freeze_json_is_byte_frozen(repo_root: Path) -> None:
    body = (repo_root / FREEZE_JSON).read_bytes()
    assert hashlib.sha256(body).hexdigest() == FROZEN_JSON_SHA256


def test_freeze_pins_the_authorized_implementation_and_state(freeze: dict[str, Any]) -> None:
    assert freeze["freeze_id"] == "OIC-CANDIDATE-LAYER-FREEZE-001"
    assert freeze["frozen_implementation_sha"] == FROZEN_IMPLEMENTATION
    assert freeze["freeze_state"] == "FROZEN FOR SUCCESSOR ARCHITECTURE WORK"
    assert freeze["independent_validation_claim"] is False
    assert freeze["self_adjudication"] == "NOT SELF-ADJUDICATED"


def test_the_freeze_records_the_tree_objects_of_the_implementation_it_froze(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    """The freeze is evidence about one commit, so it is verified against that commit.

    Reading the recorded tree objects against ``HEAD`` instead would make the freeze a
    claim that ``src`` and ``schemas`` never change again — which the freeze does not
    say and could not be authorized to say. What the freeze actually froze is the
    candidate layer, and that is checked, at HEAD, in the test below.
    """
    for path in ("src", "schemas"):
        assert (
            _tree(repo_root, FROZEN_IMPLEMENTATION, path) == freeze["production_tree_objects"][path]
        )


def test_the_frozen_candidate_layer_still_holds_its_frozen_bytes(repo_root: Path) -> None:
    """The standing guarantee, against the working tree: these exact artifacts are frozen."""
    for relpath in FROZEN_CANDIDATE_LAYER_FILES:
        frozen = subprocess.run(
            ["git", "show", f"{FROZEN_IMPLEMENTATION}:{relpath}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        assert (repo_root / relpath).read_bytes() == frozen, relpath


def test_referenced_corpora_match_their_pinned_digests(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    assert set(freeze["corpus_references"]) == set(EXPECTED_CORPORA)
    for identifier, digest in EXPECTED_CORPORA.items():
        reference = freeze["corpus_references"][identifier]
        assert reference["sha256"] == digest
        assert hashlib.sha256((repo_root / reference["path"]).read_bytes()).hexdigest() == digest


def test_receipts_are_references_not_committed_copies(
    repo_root: Path, freeze: dict[str, Any]
) -> None:
    assert set(freeze["receipt_references"]) == set(EXPECTED_RECEIPTS)
    for identifier, digest in EXPECTED_RECEIPTS.items():
        reference = freeze["receipt_references"][identifier]
        assert reference["sha256"] == digest
        assert reference["committed"] is False
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", reference["local_conventional_path"]],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        assert tracked.returncode != 0
    assert (
        freeze["receipt_references"]["OIC-CANDIDATE-NEGATIVE-STABILITY-001"]["historical_result"]
        == "INCONCLUSIVE"
    )


def test_live_observations_are_recorded_exactly(freeze: dict[str, Any]) -> None:
    live = freeze["live_characterization"]
    assert live["requests_attempted"] == live["boundary_accepted"] == 63
    for key in (
        "boundary_rejected",
        "provider_errors",
        "presence_misses",
        "negative_control_false_positive_runs",
        "positive_boundary_presence_misses",
        "candidate_spans_outside_registered_bounds",
        "runs_losing_material_content",
        "spans_containing_separable_framing",
    ):
        assert live[key] == 0, key
    assert live["source_grounded_candidate_spans"] == {"passing": 45, "examined": 45}
    assert live["material_completeness_runs"] == {"complete": 36, "measured": 36}
    assert live["negative_controls"] == {"accepted_runs": 24, "false_positive_runs": 0}
    assert live["positive_controls"] == {"accepted_runs": 39, "presence_misses": 0}


def test_named_negative_positive_and_multi_unit_observations_are_complete(
    freeze: dict[str, Any],
) -> None:
    observed = freeze["live_characterization"]["explicit_specimen_observations"]
    for specimen in ("CSEM-031", "CSEM-046", "CSEM-047", "CSEM-048"):
        assert observed[specimen] == "3/3 zero-candidate runs"
    for specimen in ("CSEM-049", "CSEM-050", "CSEM-051", "CSEM-052"):
        assert observed[specimen] == "3/3 candidate-present runs"
    for specimen in ("CSEM-025", "CSEM-045"):
        assert observed[specimen] == "exactly 2 candidates in 3/3 runs"
    assert freeze["live_characterization"]["framing_sentinel_observation"] == (
        "zero separable framing retained"
    )


def test_boundary_has_exact_model_and_oic_fields(freeze: dict[str, Any]) -> None:
    boundary = freeze["boundary"]
    assert boundary["model_proposed_fields"] == ["candidate_span", "unit_type"]
    assert boundary["oic_controlled_fields"] == [
        "unit_id",
        "interpretation_state",
        "epistemic_state",
        "source_anchors",
    ]
    for withheld in ("authority", "admission", "Institutional IR", "ALLOW", "DENY"):
        assert withheld in boundary["does_not_establish"]


def test_freeze_preserves_revision_path_and_claim_ceiling(freeze: dict[str, Any]) -> None:
    assert len(freeze["frozen_invariants"]) == 12
    assert freeze["future_revision_requirements"] == [
        "a new demonstrated defect",
        "a new bounded work order",
        "explicit owner authorization",
        "preservation of this freeze record",
        "a new successor version rather than silent modification",
    ]
    ceiling = freeze["claim_ceiling"]
    for claim in (
        "universal semantic correctness",
        "institutional admission",
        "authority",
        "Institutional IR",
        "runtime authorization",
        "independent validation",
    ):
        assert claim in ceiling


def test_markdown_states_the_same_bounded_freeze(repo_root: Path) -> None:
    text = (repo_root / FREEZE_MD).read_text(encoding="utf-8")
    assert "FROZEN FOR SUCCESSOR ARCHITECTURE WORK" in text
    assert "future candidate-layer revision" in text
    assert "does not state that revision is impossible" in text
    assert "independent_validation_claim = false" in text
    assert "NOT SELF-ADJUDICATED" in text
