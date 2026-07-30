"""Semantic conformance: the rules JSON Schema cannot express.

Structural validation and semantic conformance are two layers. Every positive fixture must
pass **both**; a record that satisfies the schema and violates a semantic rule is invalid.

The mutation tests below are the point of the file. Each takes a conforming fixture, breaks
exactly one rule, and asserts the validator rejects it — so a validator that silently
returned no findings would fail rather than look healthy.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# The validator is a test-only helper that deliberately does not live in src/oic, and
# tests/ is not a package, so it is loaded from its path rather than imported by name.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from semantic_conformance import (
        CANONICAL_TRIGGERS,
        check_runtime_decision,
        check_warrant_artifact,
    )
finally:
    sys.path.pop(0)

pytestmark = pytest.mark.contract

FIXTURE_DIR = "tests/fixtures/warrant-contract"
MAPPING_JSON = "docs/contracts/ZTL-OCE-MAPPING-v0.1.json"
CONDITIONAL_ALLOW = "08-on-credit-sound-allow-with-disclosure"

_CACHE: dict[str, Any] = {}


def _fixture(repo_root: Path, case: str) -> Any:  # noqa: ANN401 - JSON is dynamic
    if case not in _CACHE:
        _CACHE[case] = json.loads(
            (repo_root / FIXTURE_DIR / f"{case}.json").read_text(encoding="utf-8")
        )
    return copy.deepcopy(_CACHE[case])


@pytest.fixture(scope="module")
def fixtures(repo_root: Path) -> dict[str, dict[str, Any]]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / FIXTURE_DIR).glob("*.json"))
    }


@pytest.fixture(scope="module")
def rules(repo_root: Path) -> dict[str, dict[str, Any]]:
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return {rule["rule_id"]: rule for rule in document["semantic_conformance_rules"]["rules"]}


# ---------------------------------------------------------------------------
# The rules are declared, and the two layers are named
# ---------------------------------------------------------------------------


def test_all_six_rules_are_declared(rules: dict[str, dict[str, Any]]) -> None:
    assert set(rules) == {
        "SC-RD-001",
        "SC-RD-002",
        "SC-RD-003",
        "SC-RD-004",
        "SC-WA-001",
        "SC-WA-002",
    }
    for rule_id, rule in rules.items():
        assert rule["name"], rule_id
        assert rule["requirement"], rule_id
        assert rule["why"], rule_id
        assert rule["not_expressible_in_json_schema"], rule_id


def test_canonical_trigger_order_agrees_with_the_mapping(repo_root: Path) -> None:
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    declared = document["semantic_conformance_rules"]["canonical_trigger_order"]
    assert tuple(declared) == CANONICAL_TRIGGERS


def test_validation_layers_are_declared(repo_root: Path) -> None:
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    layers = document["validation_layers"]
    assert "JSON Schema" in layers["structural"]
    assert "canonical ordering" in layers["semantic"]
    assert "must pass BOTH" in layers["verdict"]


def test_schema_disclaims_full_enforcement(repo_root: Path) -> None:
    text = (repo_root / "schemas/proposed/runtime-decision.schema.json").read_text("utf-8")
    assert "VALIDATION IS TWO-LAYER" in text
    assert "It does NOT and cannot enforce equality between sibling arrays" in text
    assert "Passing structural validation alone is not conformance" in text


def test_the_validator_is_not_runtime_implementation(repo_root: Path) -> None:
    """It lives in tests/ and nothing in src imports it."""
    assert (repo_root / "tests/contract/semantic_conformance.py").is_file()
    assert not (repo_root / "src/oic/semantic_conformance.py").exists()
    for module in sorted((repo_root / "src" / "oic").glob("*.py")):
        assert "semantic_conformance" not in module.read_text(encoding="utf-8"), module.name


# ---------------------------------------------------------------------------
# Every positive fixture conforms
# ---------------------------------------------------------------------------


def _expected_codes(repo_root: Path, fixture: dict[str, Any]) -> frozenset[str]:
    """Codes the mapping says this fixture's matched stages must contribute."""
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    rows = {int(row["row_id"]): row for row in document["classification_rows"]}
    stages = {rule["rule_id"]: rule for rule in document["warrant_policy_rules"]}
    stages |= {overlay["overlay_id"]: overlay for overlay in document["decision_mode_overlays"]}
    applied = fixture["applied_control_overlay_ids"]
    codes = {
        stages[identifier]["policy_reason_code"]
        for identifier in applied
        if stages[identifier].get("policy_reason_code")
    }
    if not applied:
        codes.add(rows[fixture["classification_row"]]["primary_reason_code"])
    return frozenset(codes)


def test_every_fixture_decision_conforms(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    failures: list[str] = []
    for case, fixture in fixtures.items():
        findings = check_runtime_decision(
            fixture["expected"]["runtime_decision"],
            expected_reason_codes=_expected_codes(repo_root, fixture),
        )
        failures.extend(f"{case}: {finding}" for finding in findings)
    assert failures == []


def test_every_fixture_warrant_conforms(fixtures: dict[str, dict[str, Any]]) -> None:
    failures: list[str] = []
    checked = 0
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        checked += 1
        findings = check_warrant_artifact(
            warrant,
            marking=fixture["input"]["ztl_result"]["marking"],
            rendered_formula=warrant["formula"],
        )
        failures.extend(f"{case}: {finding}" for finding in findings)
    assert failures == []
    assert checked >= 30


def test_the_partition_covers_the_whole_marking(fixtures: dict[str, dict[str, Any]]) -> None:
    """SC-WA-001's union half, asserted directly on every fixture."""
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        marking = fixture["input"]["ztl_result"]["marking"]
        union = set(warrant["dependency_ids"]) | set(warrant["unverified_ground_ids"])
        assert union == set(marking), case


# ---------------------------------------------------------------------------
# Mutation tests: each breaks exactly one rule
# ---------------------------------------------------------------------------


def _conditional_allow(repo_root: Path) -> dict[str, Any]:
    decision: dict[str, Any] = _fixture(repo_root, CONDITIONAL_ALLOW)["expected"][
        "runtime_decision"
    ]
    assert check_runtime_decision(decision) == [], "the baseline must conform"
    return decision


def test_reject_subscription_ground_subset(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["missing_ground_ids"] = ["ground:registered", "ground:under_threshold"]
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-001" for finding in findings)


def test_reject_subscription_ground_superset(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["conditional_support_subscription_ground_ids"] = [
        "ground:registered",
        "ground:under_threshold",
    ]
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-001" for finding in findings)


def test_reject_subscription_grounds_in_non_canonical_order(repo_root: Path) -> None:
    """Same set, different order. The schema cannot see this at all."""
    decision = _conditional_allow(repo_root)
    decision["missing_ground_ids"] = ["ground:a", "ground:b"]
    decision["conditional_support_subscription_ground_ids"] = ["ground:b", "ground:a"]
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-001" for finding in findings)


def test_reject_all_five_triggers_in_non_canonical_order(repo_root: Path) -> None:
    """All five present, so the schema passes; the order is wrong, so conformance fails."""
    decision = _conditional_allow(repo_root)
    decision["conditional_support_subscription_triggers"] = list(reversed(CANONICAL_TRIGGERS))
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-002" for finding in findings)


def test_reject_duplicated_reason_codes(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["reason_codes"] = [*decision["reason_codes"], decision["reason_codes"][0]]
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-004" for finding in findings)


def test_reject_unsorted_reason_codes(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["reason_codes"] = sorted(decision["reason_codes"], reverse=True)
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-004" for finding in findings)


def test_reject_incomplete_reason_codes(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["reason_codes"] = ["OIC-W-0015"]
    findings = check_runtime_decision(decision, expected_reason_codes=frozenset({"OIC-D-0005"}))
    assert any(finding.rule_id == "SC-RD-004" for finding in findings)


def test_reject_dm_overlay_before_wp_overlay(repo_root: Path) -> None:
    decision: dict[str, Any] = _fixture(
        repo_root, "28-compose-conditional-insufficient-grade-then-human-judgment"
    )["expected"]["runtime_decision"]
    assert check_runtime_decision(decision) == []
    decision["applied_control_overlay_ids"] = ["DM-2", "WP-2"]
    findings = check_runtime_decision(decision)
    assert any(finding.rule_id == "SC-RD-003" for finding in findings)


def test_reject_duplicate_overlay_and_identity_overlay(repo_root: Path) -> None:
    decision = _conditional_allow(repo_root)
    decision["applied_control_overlay_ids"] = ["WP-3", "WP-3"]
    assert any(f.rule_id == "SC-RD-003" for f in check_runtime_decision(decision))
    decision["applied_control_overlay_ids"] = ["DM-1"]
    assert any(f.rule_id == "SC-RD-003" for f in check_runtime_decision(decision))


def test_reject_dependency_and_unverified_overlap(repo_root: Path) -> None:
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    marking = fixture["input"]["ztl_result"]["marking"]
    assert check_warrant_artifact(warrant, marking=marking) == []
    warrant["dependency_ids"] = ["p", "q"]
    findings = check_warrant_artifact(warrant, marking=marking)
    assert any(finding.rule_id == "SC-WA-001" for finding in findings)
    assert any("overlap" in finding.detail for finding in findings)


def test_reject_formula_atom_in_neither_array(repo_root: Path) -> None:
    """A ground nobody tracks cannot trigger recomputation and cannot be revoked."""
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    marking = dict(fixture["input"]["ztl_result"]["marking"])
    marking["r"] = "T"
    findings = check_warrant_artifact(warrant, marking=marking)
    assert any(finding.rule_id == "SC-WA-001" for finding in findings)
    assert any("neither array" in finding.detail for finding in findings)


def test_reject_hash_over_the_callers_formula(repo_root: Path) -> None:
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    rendered = warrant["formula"]
    warrant["formula"] = "p | q"  # the caller's string, not the kernel rendering
    findings = check_warrant_artifact(warrant, rendered_formula=rendered)
    assert any(finding.rule_id == "SC-WA-002" for finding in findings)
