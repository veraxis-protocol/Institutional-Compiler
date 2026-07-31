"""Semantic conformance: the rules JSON Schema cannot express.

Structural validation and semantic conformance are two layers. Every positive fixture must
pass **both**; a record that satisfies the schema and violates a semantic rule is invalid.

The mutation tests below are the point of the file. Each takes a conforming fixture, breaks
exactly one rule, and asserts the validator rejects it — so a validator that silently
returned no findings would fail rather than look healthy.
"""

from __future__ import annotations

import copy
import hashlib
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
        expected_formula_hash,
        expected_output_hash,
    )
finally:
    sys.path.pop(0)

ROW_28_CASE = "08-on-credit-sound-allow-with-disclosure"
ROW_29_CASE = "12-on-credit-until-verification"
ROW_29_DECLARED_MINIMUM_CASE = "38-on-credit-until-verification-declared-minimum"

pytestmark = pytest.mark.contract

FIXTURE_DIR = "tests/fixtures/warrant-contract"
MAPPING_JSON = "docs/contracts/ZTL-OCE-MAPPING-v0.1.json"
CONDITIONAL_ALLOW = "08-on-credit-sound-allow-with-disclosure"

#: The kernel renders logical OR as U+2228. Escaped so this source stays ASCII.
LOGICAL_OR = "\u2228"
#: Fixture 33's kernel-rendered formula, for caller input `p | q`.
RENDERED = f"(p {LOGICAL_OR} q)"

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


def test_all_rules_are_declared(rules: dict[str, dict[str, Any]]) -> None:
    assert set(rules) == {
        "SC-RD-001",
        "SC-RD-002",
        "SC-RD-003",
        "SC-RD-004",
        "SC-RD-005",
        "SC-RD-006",
        "SC-WA-001",
        "SC-WA-002",
    }
    assert len(rules) == 8
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


def _mapping(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return document


def _expected_codes(repo_root: Path, fixture: dict[str, Any]) -> frozenset[str]:
    """Every code this decision's lineage must retain.

    The classification row's primary code is required **unconditionally**. An earlier
    version added it only when no overlay applied, which meant a REFUTED decision redirected
    by an advisory overlay could silently drop `OIC-W-0013` -- the substantive refutation --
    and nothing would object. A later stage may change the execution; it may not erase why
    an earlier one fired.
    """
    document = _mapping(repo_root)
    rows = {int(row["row_id"]): row for row in document["classification_rows"]}
    stages = {rule["rule_id"]: rule for rule in document["warrant_policy_rules"]}
    stages |= {overlay["overlay_id"]: overlay for overlay in document["decision_mode_overlays"]}

    codes = {rows[fixture["classification_row"]]["primary_reason_code"]}
    codes |= {
        stages[identifier]["policy_reason_code"]
        for identifier in fixture["applied_control_overlay_ids"]
        if stages[identifier].get("policy_reason_code")
    }
    return frozenset(codes)


_GRADE_RANK = {"until-verification": 0, "sound": 1, "hereditary": 2}


def _derive_overlays(repo_root: Path, fixture: dict[str, Any]) -> list[str]:
    """Derive the applicable overlays from the envelope and kernel result.

    Stage 2 runs only where the matched classification row declares `stage_2_applies`;
    rows whose stage-1 basis already determines the outcome do not delegate. Within stage
    2, grade sufficiency is evaluated before the unverified-ground policy. Stage 3 applies
    last, and the identity overlay DM-1 is never recorded.
    """
    document = _mapping(repo_root)
    rows = {int(row["row_id"]): row for row in document["classification_rows"]}
    row = rows[fixture["classification_row"]]
    envelope = fixture["input"]["envelope"]
    derived: list[str] = []

    if envelope is not None and row.get("stage_2_applies"):
        requirement = envelope["warrant_requirement"]
        observed = fixture["input"]["ztl_result"]["grade"]
        required = requirement["minimum_warranty_grade"]
        if required is not None and _GRADE_RANK[observed] < _GRADE_RANK[required]:
            derived.append("WP-1" if requirement["on_insufficient_grade"] == "escalate" else "WP-2")
        else:
            policy = requirement["unverified_ground_policy"]
            derived.append(
                {"allow_with_disclosure": "WP-3", "forbid": "WP-4", "escalate": "WP-5"}[policy]
            )

    if envelope is not None:
        mode = envelope["decision_mode"]
        if mode in {"human_judgment", "escalation_only", "non_automatable"}:
            derived.append("DM-2")
        elif mode in {"advisory", "evidence_only"}:
            derived.append("DM-3")
    return derived


def test_every_fixture_decision_conforms(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    failures: list[str] = []
    for case, fixture in fixtures.items():
        findings = check_runtime_decision(
            fixture["expected"]["runtime_decision"],
            expected_reason_codes=_expected_codes(repo_root, fixture),
            expected_applied_overlay_ids=_derive_overlays(repo_root, fixture),
            expected_classification_row=fixture["classification_row"],
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


# ---------------------------------------------------------------------------
# A: hash projections are RECOMPUTED, not merely present
# ---------------------------------------------------------------------------


def test_formula_hash_recomputes_from_the_kernel_rendering(repo_root: Path) -> None:
    """Fixture 33 recomputes from the kernel rendering, not from the caller's string."""
    warrant = _fixture(repo_root, "33-earned-hereditary-with-unverified")["input"][
        "warrant_artifact"
    ]
    assert warrant["formula"] == RENDERED
    assert warrant["formula_hash"] == expected_formula_hash(RENDERED)
    assert warrant["formula_hash"] != expected_formula_hash("p | q")


def test_every_fixture_hash_recomputes(fixtures: dict[str, dict[str, Any]]) -> None:
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        assert warrant["formula_hash"] == expected_formula_hash(warrant["formula"]), case
        assert warrant["output_hash"] == expected_output_hash(warrant), case


def test_output_hash_projection_is_exactly_five_fields(repo_root: Path) -> None:
    """Serialisation is pinned so two conforming implementations agree byte for byte."""
    warrant = _fixture(repo_root, "33-earned-hereditary-with-unverified")["input"][
        "warrant_artifact"
    ]
    projection = {
        "kernel_rendered_formula": warrant["formula"],
        "disposition": warrant["disposition"],
        "raw_verdict": warrant["raw_verdict"],
        "warranty_grade": warrant["warranty_grade"],
        "unverified_ground_ids": warrant["unverified_ground_ids"],
    }
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert " " not in payload.replace(RENDERED, "")
    assert LOGICAL_OR in payload, "Unicode must not be ASCII-escaped"
    assert warrant["output_hash"] == "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


@pytest.mark.parametrize(
    "excluded",
    ["why", "marking", "dependency_ids", "generated_at", "source_anchor_ids", "admission_ids"],
)
def test_excluded_fields_do_not_enter_the_output_hash(repo_root: Path, excluded: str) -> None:
    """Adding an excluded field to the projection must change the digest, proving exclusion."""
    warrant = _fixture(repo_root, "33-earned-hereditary-with-unverified")["input"][
        "warrant_artifact"
    ]
    projection = {
        "kernel_rendered_formula": warrant["formula"],
        "disposition": warrant["disposition"],
        "raw_verdict": warrant["raw_verdict"],
        "warranty_grade": warrant["warranty_grade"],
        "unverified_ground_ids": warrant["unverified_ground_ids"],
        excluded: warrant.get(excluded, "some value"),
    }
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    contaminated = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    assert warrant["output_hash"] != contaminated
    assert warrant["output_hash"] == expected_output_hash(warrant)


def test_why_and_marking_do_not_affect_the_output_hash(repo_root: Path) -> None:
    """The positive half: changing a presentational or input field changes nothing."""
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    baseline = expected_output_hash(warrant)

    warrant["why"] = "a completely different human-readable justification"
    assert expected_output_hash(warrant) == baseline

    fixture["input"]["ztl_result"]["marking"] = {"p": "T", "q": "T", "r": "F"}
    assert expected_output_hash(warrant) == baseline

    warrant["generated_at"] = "2099-01-01T00:00:00Z"
    warrant["dependency_ids"] = ["something", "else"]
    assert expected_output_hash(warrant) == baseline


HASH_MUTATIONS = (
    ("arbitrary_formula_hash", "formula_hash", "sha384:" + "0" * 96),
    ("formula_hash_from_callers_string", "formula_hash", expected_formula_hash("p | q")),
    ("arbitrary_output_hash", "output_hash", "sha256:" + "0" * 64),
)


@pytest.mark.parametrize(
    ("label", "field", "value"), HASH_MUTATIONS, ids=[m[0] for m in HASH_MUTATIONS]
)
def test_reject_wrong_digest(repo_root: Path, label: str, field: str, value: str) -> None:
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    assert check_warrant_artifact(warrant) == []
    warrant[field] = value
    findings = check_warrant_artifact(warrant)
    assert any(finding.rule_id == "SC-WA-002" for finding in findings), label


@pytest.mark.parametrize("contaminant", ["why", "marking"])
def test_reject_output_hash_computed_with_an_excluded_field(
    repo_root: Path, contaminant: str
) -> None:
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    projection = {
        "kernel_rendered_formula": warrant["formula"],
        "disposition": warrant["disposition"],
        "raw_verdict": warrant["raw_verdict"],
        "warranty_grade": warrant["warranty_grade"],
        "unverified_ground_ids": warrant["unverified_ground_ids"],
        contaminant: "contaminating value",
    }
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    warrant["output_hash"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    assert any(f.rule_id == "SC-WA-002" for f in check_warrant_artifact(warrant))


@pytest.mark.parametrize(
    "omitted",
    [
        "kernel_rendered_formula",
        "disposition",
        "raw_verdict",
        "warranty_grade",
        "unverified_ground_ids",
    ],
)
def test_reject_output_hash_missing_an_included_field(repo_root: Path, omitted: str) -> None:
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    projection = {
        "kernel_rendered_formula": warrant["formula"],
        "disposition": warrant["disposition"],
        "raw_verdict": warrant["raw_verdict"],
        "warranty_grade": warrant["warranty_grade"],
        "unverified_ground_ids": warrant["unverified_ground_ids"],
    }
    del projection[omitted]
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    warrant["output_hash"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    assert any(f.rule_id == "SC-WA-002" for f in check_warrant_artifact(warrant))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("disposition", "ON CREDIT"),
        ("raw_verdict", "F"),
        ("warranty_grade", "sound"),
        ("formula", f"(q {LOGICAL_OR} p)"),
        ("unverified_ground_ids", ["p"]),
    ],
)
def test_reject_output_hash_after_altering_a_covered_field(
    repo_root: Path, field: str, value: object
) -> None:
    """Altering any covered field without recomputing must be caught."""
    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    warrant[field] = value
    assert any(f.rule_id == "SC-WA-002" for f in check_warrant_artifact(warrant))


def test_duplicate_identifiers_are_rejected(repo_root: Path) -> None:
    """D: the arrays are a partition, so a repeat is malformed."""
    fixture = _fixture(repo_root, "01-earned-hereditary-current")
    warrant = fixture["input"]["warrant_artifact"]
    warrant["dependency_ids"] = [*warrant["dependency_ids"], warrant["dependency_ids"][0]]
    findings = check_warrant_artifact(warrant)
    assert any(f.rule_id == "SC-WA-001" and "duplicate" in f.detail for f in findings)

    fixture = _fixture(repo_root, "33-earned-hereditary-with-unverified")
    warrant = fixture["input"]["warrant_artifact"]
    warrant["unverified_ground_ids"] = ["q", "q"]
    findings = check_warrant_artifact(warrant)
    assert any(f.rule_id == "SC-WA-001" and "duplicate" in f.detail for f in findings)


# ---------------------------------------------------------------------------
# B: reason lineage is complete
# ---------------------------------------------------------------------------

LINEAGE_MUTATIONS = (
    ("refuted_advisory_omits_the_refutation", "30-compose-refuted-advisory", "OIC-W-0013"),
    (
        "contradicted_human_judgment_omits_the_contradiction",
        "31-compose-contradicted-human-judgment",
        "OIC-W-0014",
    ),
    (
        "conditional_acceptance_then_human_judgment_omits_acceptance",
        "29-compose-conditional-accepted-then-human-judgment",
        "OIC-D-0005",
    ),
    (
        "grade_insufficiency_then_human_judgment_omits_the_grade_code",
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        "OIC-W-0016",
    ),
    ("overlay_omits_its_own_code", "25-overlay-established-human-judgment", "OIC-D-0002"),
    (
        "overlay_omits_the_classification_code",
        "25-overlay-established-human-judgment",
        "OIC-D-0001",
    ),
)


@pytest.mark.parametrize(
    ("label", "case", "dropped"), LINEAGE_MUTATIONS, ids=[m[0] for m in LINEAGE_MUTATIONS]
)
def test_reject_missing_reason_lineage(
    repo_root: Path, label: str, case: str, dropped: str
) -> None:
    fixture = _fixture(repo_root, case)
    decision = fixture["expected"]["runtime_decision"]
    expected = _expected_codes(repo_root, fixture)
    assert dropped in expected, f"{label}: the code must be required in the first place"
    assert check_runtime_decision(decision, expected_reason_codes=expected) == []

    decision["reason_codes"] = [code for code in decision["reason_codes"] if code != dropped]
    findings = check_runtime_decision(decision, expected_reason_codes=expected)
    assert any(finding.rule_id == "SC-RD-004" for finding in findings), label


def test_classification_code_is_required_even_when_an_overlay_applies(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    """The hole the earlier `if not applied` branch left open."""
    rows = {int(r["row_id"]): r for r in _mapping(repo_root)["classification_rows"]}
    checked = 0
    for case, fixture in fixtures.items():
        if not fixture["applied_control_overlay_ids"]:
            continue
        checked += 1
        expected = _expected_codes(repo_root, fixture)
        primary = rows[fixture["classification_row"]]["primary_reason_code"]
        assert primary in expected, case
        assert primary in fixture["expected"]["reason_codes"], case
    assert checked >= 8


# ---------------------------------------------------------------------------
# C: overlay lineage is complete
# ---------------------------------------------------------------------------


def test_derived_overlays_match_every_fixture(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    for case, fixture in fixtures.items():
        assert _derive_overlays(repo_root, fixture) == fixture["applied_control_overlay_ids"], case


OVERLAY_MUTATIONS = (
    ("omit_the_wp_rule", "28-compose-conditional-insufficient-grade-then-human-judgment", ["DM-2"]),
    (
        "omit_the_dm_overlay",
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        ["WP-2"],
    ),
    ("omit_the_acceptance_rule", "29-compose-conditional-accepted-then-human-judgment", ["DM-2"]),
    (
        "omit_the_escalation_overlay",
        "29-compose-conditional-accepted-then-human-judgment",
        ["WP-3"],
    ),
    (
        "extra_inapplicable_overlay",
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        ["WP-2", "WP-3", "DM-2"],
    ),
    (
        "wrong_order",
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        ["DM-2", "WP-2"],
    ),
    (
        "duplicate_overlay",
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        ["WP-2", "WP-2", "DM-2"],
    ),
    ("identity_overlay_recorded", "01-earned-hereditary-current", ["DM-1"]),
)


@pytest.mark.parametrize(
    ("label", "case", "recorded"), OVERLAY_MUTATIONS, ids=[m[0] for m in OVERLAY_MUTATIONS]
)
def test_reject_incomplete_overlay_lineage(
    repo_root: Path, label: str, case: str, recorded: list[str]
) -> None:
    fixture = _fixture(repo_root, case)
    decision = fixture["expected"]["runtime_decision"]
    derived = _derive_overlays(repo_root, fixture)
    assert check_runtime_decision(decision, expected_applied_overlay_ids=derived) == [], (
        f"{label}: baseline must conform"
    )

    decision["applied_control_overlay_ids"] = recorded
    findings = check_runtime_decision(decision, expected_applied_overlay_ids=derived)
    assert findings, label
    assert any(f.rule_id in {"SC-RD-003", "SC-RD-005"} for f in findings), label


# ---------------------------------------------------------------------------
# B (CLOSE-003): WP-3 self-containment, SC-RD-006
# ---------------------------------------------------------------------------


def test_measured_counterexample_never_allows(repo_root: Path) -> None:
    """A control declaring until-verification as its OWN minimum must still block.

    Grade sufficiency alone would call until-verification "sufficient" against that
    declared minimum. WP-3 is scoped to row 28 by construction, and row 29 never declares
    stage_2_applies, so WP-3 is unreachable regardless of what the control accepts.
    """
    fixture = _fixture(repo_root, ROW_29_DECLARED_MINIMUM_CASE)
    envelope = fixture["input"]["envelope"]
    assert envelope["warrant_requirement"]["minimum_warranty_grade"] == "until-verification"
    assert fixture["input"]["ztl_result"]["grade"] == "until-verification"

    decision = fixture["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == "CONDITIONALLY_SUPPORTED"
    assert decision["execution_disposition"] != "ALLOW"
    assert decision["decision_basis"] == "PRECAUTIONARY"
    assert "OIC-W-0025" in decision["reason_codes"]
    assert "WP-3" not in fixture["applied_control_overlay_ids"]
    assert "OIC-D-0005" not in decision["reason_codes"]

    findings = check_runtime_decision(
        decision,
        expected_reason_codes=_expected_codes(repo_root, fixture),
        expected_applied_overlay_ids=_derive_overlays(repo_root, fixture),
        expected_classification_row=fixture["classification_row"],
    )
    assert findings == []


def test_reject_conditional_allow_with_until_verification(repo_root: Path) -> None:
    """SC-RD-006: the observed grade must be sound, whatever the control's declared floor."""
    decision = dict(_fixture(repo_root, ROW_28_CASE)["expected"]["runtime_decision"])
    assert check_runtime_decision(decision, expected_classification_row=28) == []

    decision["warranty_grade_observed"] = "until-verification"
    findings = check_runtime_decision(decision, expected_classification_row=28)
    assert any(f.rule_id == "SC-RD-006" for f in findings)


def test_reject_conditional_allow_without_wp3(repo_root: Path) -> None:
    decision = dict(_fixture(repo_root, ROW_28_CASE)["expected"]["runtime_decision"])
    decision["applied_control_overlay_ids"] = []
    findings = check_runtime_decision(decision, expected_classification_row=28)
    assert any(f.rule_id == "SC-RD-006" for f in findings)


def test_reject_wp3_recorded_for_row_29(repo_root: Path) -> None:
    """Even if a decision claims WP-3, the row it was classified from must be 28."""
    fixture = _fixture(repo_root, ROW_29_CASE)
    decision = fixture["expected"]["runtime_decision"]
    # This decision is not a conditional ALLOW in the first place, so force one to isolate
    # the row check: SC-RD-006's row assertion must fire independent of the other checks.
    decision["execution_disposition"] = "ALLOW"
    decision["warranty_grade_observed"] = "sound"
    decision["applied_control_overlay_ids"] = ["WP-3"]
    decision["reason_codes"] = sorted({*decision["reason_codes"], "OIC-D-0005", "OIC-W-0015"})
    findings = check_runtime_decision(
        decision, expected_classification_row=fixture["classification_row"]
    )
    assert fixture["classification_row"] == 29
    assert any(f.rule_id == "SC-RD-006" and "row 29" in f.detail for f in findings)


def test_reject_conditional_allow_carrying_oic_w_0025(repo_root: Path) -> None:
    """OIC-W-0025 marks instability (row 29). It must never coexist with a conditional ALLOW."""
    decision = dict(_fixture(repo_root, ROW_28_CASE)["expected"]["runtime_decision"])
    assert check_runtime_decision(decision) == [], "baseline must conform"

    decision["reason_codes"] = sorted({*decision["reason_codes"], "OIC-W-0025"})
    findings = check_runtime_decision(decision)
    assert any(f.rule_id == "SC-RD-006" and "OIC-W-0025" in f.detail for f in findings)

    row_28 = next(r for r in _mapping(repo_root)["classification_rows"] if r["row_id"] == 28)
    row_29 = next(r for r in _mapping(repo_root)["classification_rows"] if r["row_id"] == 29)
    assert row_28["primary_reason_code"] != "OIC-W-0025"
    assert row_29["primary_reason_code"] == "OIC-W-0025"


def test_wp3_is_scoped_to_row_28_in_the_mapping(repo_root: Path) -> None:
    document = _mapping(repo_root)
    wp3 = next(r for r in document["warrant_policy_rules"] if r["rule_id"] == "WP-3")
    assert "row = 28" in wp3["trigger"] or "row=28" in wp3["trigger"].replace(" ", "")
    rows = {r["row_id"]: r for r in document["classification_rows"]}
    assert rows[28]["stage_2_applies"] is True
    assert rows[29]["stage_2_applies"] is False


def test_sc_rd_006_is_declared(rules: dict[str, dict[str, Any]]) -> None:
    rule = rules["SC-RD-006"]
    assert "sound" in rule["requirement"]
    assert "row" in rule["requirement"].lower()
    assert "OIC-D-0005" in rule["requirement"]
    assert "OIC-W-0015" in rule["requirement"]


# ---------------------------------------------------------------------------
# C (CLOSE-003): SC-WA-001 edge cases -- partition over the formula, not the marking
# ---------------------------------------------------------------------------


def test_atom_in_marking_but_not_formula_belongs_to_neither_array(repo_root: Path) -> None:
    """The caller told the kernel about an atom the formula never uses."""
    warrant = dict(
        _fixture(repo_root, "33-earned-hereditary-with-unverified")["input"]["warrant_artifact"]
    )
    marking = {"p": "T", "q": "Z", "r": "T"}  # r is in the marking, not in the formula
    formula_atoms = frozenset({"p", "q"})

    # Correct: r appears in neither array.
    assert warrant["dependency_ids"] == ["p"]
    assert warrant["unverified_ground_ids"] == ["q"]
    findings = check_warrant_artifact(warrant, marking=marking, formula_atoms=formula_atoms)
    assert findings == []

    # Incorrect: r leaks into dependency_ids.
    warrant["dependency_ids"] = ["p", "r"]
    findings = check_warrant_artifact(warrant, marking=marking, formula_atoms=formula_atoms)
    assert any(
        f.rule_id == "SC-WA-001" and "not in the evaluated formula" in f.detail for f in findings
    )


def test_atom_in_formula_but_absent_from_marking_defaults_to_unverified(
    repo_root: Path,
) -> None:
    """A formula atom nobody supplied a value for is treated exactly like a Z mark."""
    warrant = dict(
        _fixture(repo_root, "33-earned-hereditary-with-unverified")["input"]["warrant_artifact"]
    )
    marking = {"p": "T"}  # q never appears in the marking at all
    formula_atoms = frozenset({"p", "q"})

    # Correct: q defaults to unverified even though it is absent from marking.
    assert warrant["dependency_ids"] == ["p"]
    assert warrant["unverified_ground_ids"] == ["q"]
    findings = check_warrant_artifact(warrant, marking=marking, formula_atoms=formula_atoms)
    assert findings == []

    # Incorrect: treating the absent atom as covered by neither array.
    warrant["unverified_ground_ids"] = []
    findings = check_warrant_artifact(warrant, marking=marking, formula_atoms=formula_atoms)
    assert any(f.rule_id == "SC-WA-001" and "neither array" in f.detail for f in findings)


def test_sc_wa_001_wording_covers_both_edge_cases(rules: dict[str, dict[str, Any]]) -> None:
    requirement = rules["SC-WA-001"]["requirement"]
    assert "absent from the formula belongs to neither array" in requirement
    assert "absent from the marking defaults to Z" in requirement
