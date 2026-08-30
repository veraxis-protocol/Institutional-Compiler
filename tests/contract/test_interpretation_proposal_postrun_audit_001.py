"""Contract and mutation probes for Post-run Audit 001."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.contract

AUDIT = Path("benchmarks/characterization/interpretation-proposal-001-postrun-audit/AUDIT.json")
SCRIPT = Path("scripts/audit_interpretation_proposal_postrun.py")
CORPUS = Path("benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json")
SOURCE_RECEIPT_SHA = "29217e29207f7a1a5e32ae28bc7ae28cd9d33cc7acc591a9fb4aa0f38d59b7f5"
HISTORICAL_METRICS_SHA = "0edf35f335d7d60bc31d6c875c613b05e8dcc6bca007c00665450550e6e1103f"


def _load_script(repo_root: Path) -> ModuleType:
    path = repo_root / SCRIPT
    spec = importlib.util.spec_from_file_location("_postrun_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def audit(repo_root: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((repo_root / AUDIT).read_text(encoding="utf-8"))
    return value


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _load_script(repo_root)


def test_source_receipt_and_instrument_are_pinned(audit: dict[str, Any]) -> None:
    assert audit["source_receipt_sha256"] == SOURCE_RECEIPT_SHA
    assert audit["source_instrument_sha"] == "213ef5988f16f13cbf0b2e691b1873a740034a82"
    assert audit["source_corpus_sha256"] == (
        "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
    )


def test_every_historical_metric_is_preserved_exactly(
    audit: dict[str, Any], harness: ModuleType
) -> None:
    digest = hashlib.sha256(harness.canonical(audit["historical_metrics"])).hexdigest()
    assert digest == audit["historical_metrics_canonical_sha256"] == HISTORICAL_METRICS_SHA
    assert audit["historical_metrics"]["F_ambiguity_overcommitment"]["counts"] == {
        "alternatives_preserved": 6
    }


def test_authoritative_raw_counts_are_reproduced(audit: dict[str, Any]) -> None:
    assert audit["authoritative_observations"] == {
        "planned_requests": 87,
        "attempted": 87,
        "accepted_proposals": 86,
        "provider_errors": 1,
        "boundary_rejections": 0,
        "source_quotes_grounded": 323,
        "source_quotes_ungrounded": 0,
    }


def test_ambiguity_conjunction_is_not_separate_surfacing(audit: dict[str, Any]) -> None:
    metric = audit["corrected_metrics"]["ambiguity"]
    assert metric["counts"] == {
        "ALTERNATIVES_SEPARATELY_SURFACED": 0,
        "SINGLE_ALTERNATIVE_SELECTED": 0,
        "ALTERNATIVES_CONJOINED_OR_COLLAPSED": 6,
        "UNSUPPORTED_ALTERNATIVE": 0,
        "AMBIGUOUS_SLOT_OMITTED": 0,
    }
    assert {(item["specimen_id"], item["run_index"]) for item in metric["instances"]} == {
        (specimen, run) for specimen in ("IIR-017", "IIR-018") for run in (1, 2, 3)
    }


def test_separate_assertions_are_required_for_separate_surfacing(harness: ModuleType) -> None:
    specimen = {
        "specimen_id": "X",
        "candidate": {"candidate_span": "alpha and beta"},
        "gold": {
            "expected_slots": {"actor": {"status": "AMBIGUOUS", "alternatives": ["alpha", "beta"]}}
        },
    }
    composite = {
        "specimen_id": "X",
        "run_index": 1,
        "proposal": {
            "proposed_assertions": [
                {
                    "slot": "actor",
                    "proposed_value": "alpha and beta",
                    "proposed_source_quote": "alpha and beta",
                }
            ]
        },
    }
    separate = {
        "specimen_id": "X",
        "run_index": 2,
        "proposal": {
            "proposed_assertions": [
                {"slot": "actor", "proposed_value": "alpha", "proposed_source_quote": "alpha"},
                {"slot": "actor", "proposed_value": "beta", "proposed_source_quote": "beta"},
            ]
        },
    }
    result = harness.rescore_ambiguity({"X": specimen}, [composite, separate])
    assert result["instances"][0]["category"] == "ALTERNATIVES_CONJOINED_OR_COLLAPSED"
    assert result["instances"][1]["category"] == "ALTERNATIVES_SEPARATELY_SURFACED"


def test_grounded_text_is_distinct_from_semantic_assignment(audit: dict[str, Any]) -> None:
    counts = audit["corrected_metrics"]["source_text_and_semantic_assignment"]["counts"]
    assert counts == {
        "UNGROUNDED_SOURCE_TEXT": 0,
        "UNSUPPORTED_SEMANTIC_ASSIGNMENT": 36,
        "WRONG_ROLE_ASSIGNMENT": 21,
        "SUPPORTED_ROLE_ASSIGNMENT": 266,
        "NO_SOURCE_QUOTE": 0,
    }
    assert sum(counts.values()) == 323


def test_comparator_loss_is_strengthening_and_role_moves_are_distinct(
    audit: dict[str, Any],
) -> None:
    counts = audit["corrected_metrics"]["semantic_strengthening"]["counts"]
    assert counts["THRESHOLD_BROADENED_BY_COMPARATOR_LOSS"] == 6
    assert counts["CONDITION_OMITTED"] == 6
    assert counts["CONDITION_MOVED_TO_WRONG_ROLE"] == 1
    assert counts["EXCEPTION_MOVED_TO_CONDITION"] == 4
    assert "EXCEPTION_OMITTED" not in counts
    assert counts["TEMPORAL_QUALIFIER_MOVED_TO_CONDITION"] == 9
    assert counts["RECIPIENT_PROMOTED_TO_BEARER"] == 3


def test_comparator_mutation_is_detected(harness: ModuleType) -> None:
    specimen = {
        "specimen_id": "X",
        "candidate": {"candidate_span": "above 5000 units"},
        "gold": {
            "expected_slots": {
                "quantum": {
                    "status": "ESTABLISHED",
                    "value": "above 5000 units",
                    "material_qualifiers": [{"qualifier_kind": "COMPARATOR", "text": "above"}],
                },
                "bearer": {"status": "NOT_ESTABLISHED"},
                "counterparty": {"status": "NOT_ESTABLISHED"},
                "condition": {"status": "NOT_ESTABLISHED"},
                "exception": {"status": "NOT_ESTABLISHED"},
                "temporal_qualifier": {"status": "NOT_ESTABLISHED"},
            }
        },
    }
    attempt = {
        "specimen_id": "X",
        "run_index": 1,
        "proposal": {
            "proposed_assertions": [
                {
                    "slot": "quantum",
                    "proposed_value": "5000 units",
                    "proposed_source_quote": "5000 units",
                }
            ]
        },
    }
    assert harness.audit_strengthening({"X": specimen}, [attempt])["counts"] == {
        "THRESHOLD_BROADENED_BY_COMPARATOR_LOSS": 1
    }


def test_headlines_are_literal_and_denominated(audit: dict[str, Any]) -> None:
    corrected = audit["corrected_metrics"]
    assert corrected["established_slots"] == {
        "expected_established": 365,
        "compatible": 260,
        "omitted": 83,
        "incompatible": 22,
    }
    assert corrected["references"] == {
        "expected": 9,
        "surfaced": 9,
        "correct_reference_kind": 4,
        "wrong_reference_kind": 5,
        "omitted": 0,
        "invented": 0,
        "semantically_resolved_instead_of_surfaced": 0,
    }
    stability = corrected["repeat_stability"]
    assert stability["specimen_denominator"] == 29
    assert stability["semantic_hash_stable_specimens"] == 6
    assert stability["force_stable_specimens"] == 27
    assert stability["slot_set_stable_specimens"] == 12
    assert stability["provider_successful_runs_by_specimen"]["IIR-032"] == 2


def test_no_architectural_overclaim(audit: dict[str, Any]) -> None:
    assert audit["owner_disposition"].startswith("AMEND —")
    assert audit["population_rate_claimed"] is False
    assert audit["new_model_call_made"] is False
    assert audit["canonicalization_performed"] is False
    assert audit["institutional_ir_runtime_implemented"] is False
    assert audit["independent_validation_claim"] is False
    assert audit["self_adjudication"] == "NOT SELF-ADJUDICATED"


def test_corpus_bytes_remain_frozen(repo_root: Path) -> None:
    assert hashlib.sha256((repo_root / CORPUS).read_bytes()).hexdigest() == (
        "462158c1f70e10838f09d02e1dc62136d30477535048852bbc110f1d6cf7f817"
    )
