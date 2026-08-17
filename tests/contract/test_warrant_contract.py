"""Contract tests for the proposed warrant and failure-semantics contract (OIC-WO-002).

What these prove, and what they do not
--------------------------------------
No adapter exists, so these cannot prove an implementation is correct. They prove the
fixtures are schema-valid, internally consistent, and consistent with the **canonical JSON
mapping** — which is the source of truth; the Markdown table is generated from it and
verified against it here.

That makes the contract executable instead of prose: a fixture that quietly records
``REFUTED`` for an ``OPEN`` disposition fails the build. When an adapter is eventually
authorised, the same fixtures become its acceptance suite.

Invariants are asserted from the **input** side wherever possible, so writing a wrong
answer into a fixture cannot make its own test pass.

Nothing here imports, calls, or simulates ZTL or VEIP.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator

pytestmark = pytest.mark.contract

FIXTURE_DIR = "tests/fixtures/warrant-contract"
MAPPING_JSON = "docs/contracts/ZTL-OCE-MAPPING-v0.1.json"
MAPPING_MD = "docs/contracts/ZTL-OCE-MAPPING-v0.1.md"
CONTRACT_DOC = "docs/contracts/WARRANT-CONTRACT-v0.1.md"
ADR = "adr/ADR-013.md"
PROPOSED = "schemas/proposed"

EXPECTED_CASES = (
    "01-earned-hereditary-current",
    "02-earned-sound-unsupported-result",
    "03-earned-until-verification-unsupported-result",
    "04-refuted",
    "05-open-raw-f",
    "06-open-raw-t-unsupported-result",
    "07-open-raw-z",
    "08-on-credit-sound-allow-with-disclosure",
    "09-on-credit-sound-forbid",
    "10-on-credit-sound-escalate",
    "11-on-credit-insufficient-grade-escalate",
    "12-on-credit-until-verification",
    "13-kernel-unavailable",
    "14-warrant-stale",
    "15-ground-expired",
    "16-ground-revoked",
    "17-epoch-mismatch",
    "18-contradiction",
    "19-source-version-mismatch",
    "20-admission-version-mismatch",
    "21-warrant-not-yet-valid",
    "22-profile-mismatch",
    "23-warrant-explicitly-not-applicable",
    "24-warrant-requirement-missing",
    "25-overlay-established-human-judgment",
    "26-overlay-established-advisory",
    "27-overlay-unresolved-advisory",
    "28-compose-conditional-insufficient-grade-then-human-judgment",
    "29-compose-conditional-accepted-then-human-judgment",
    "30-compose-refuted-advisory",
    "31-compose-contradicted-human-judgment",
    "32-compose-conditional-advisory",
    "33-earned-hereditary-with-unverified",
    "34-subscription-missing-reference",
    "35-subscription-missing-ground-coverage",
    "36-subscription-missing-trigger",
    "37-subscription-ground-set-mismatch",
    "38-on-credit-until-verification-declared-minimum",
)

#: The only reason codes that may accompany a SUBSTANTIVE *block*.
SUBSTANTIVE_BLOCK_CODES = {"OIC-W-0013", "OIC-W-0014"}
#: The substantive positive-decision code.
SUBSTANTIVE_ALLOW_CODE = "OIC-D-0001"
#: A CONTROL_REQUIREMENT decision must carry one of these.
CONTROL_POLICY_CODES = {
    "OIC-W-0016",
    "OIC-D-0002",
    "OIC-D-0003",
    "OIC-D-0005",
    "OIC-D-0006",
}
#: The five epistemic statuses.
EPISTEMIC = {"ESTABLISHED", "CONDITIONALLY_SUPPORTED", "REFUTED", "UNRESOLVED", "CONTRADICTED"}
BASES = {"SUBSTANTIVE", "PRECAUTIONARY", "PROCEDURAL", "CONTROL_REQUIREMENT"}
PROFILE = "docs/contracts/kernel-profiles/ztl-v0.1.json"

GRADE_ORDER = {"until-verification": 0, "sound": 1, "hereditary": 2}

_CACHE: dict[str, Any] = {}


def _plain(path: Path) -> str:
    """Read a document as flat prose.

    Strips markdown emphasis and code spans and collapses hard-wrapped lines, so an
    assertion about what a document *says* is not defeated by how it is marked up.
    """
    raw = path.read_text(encoding="utf-8")
    return " ".join(raw.replace("*", "").replace("`", "").split())


def _fixture(repo_root: Path, case: str) -> Any:  # noqa: ANN401 - JSON is dynamic
    """Load one fixture, keeping parametrised signatures free of ``Any``."""
    if case not in _CACHE:
        _CACHE[case] = json.loads(
            (repo_root / FIXTURE_DIR / f"{case}.json").read_text(encoding="utf-8")
        )
    return _CACHE[case]


def _rows(repo_root: Path) -> Any:  # noqa: ANN401 - JSON is dynamic
    """Classification rows by id, for parametrised tests with Any-free signatures."""
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return {int(row["row_id"]): row for row in document["classification_rows"]}


def _overlays(repo_root: Path) -> Any:  # noqa: ANN401 - JSON is dynamic
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return {
        **{r["rule_id"]: r for r in document["warrant_policy_rules"]},
        **{o["overlay_id"]: o for o in document["decision_mode_overlays"]},
    }


def _validator(repo_root: Path, name: str) -> Draft202012Validator:
    schema = json.loads((repo_root / PROPOSED / f"{name}.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def fixtures(repo_root: Path) -> dict[str, dict[str, Any]]:
    loaded = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((repo_root / FIXTURE_DIR).glob("*.json"))
    }
    assert loaded, "no fixtures found"
    return loaded


@pytest.fixture(scope="module")
def mapping(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return document


@pytest.fixture(scope="module")
def rows(mapping: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(row["row_id"]): row for row in mapping["classification_rows"]}


@pytest.fixture(scope="module")
def overlays(mapping: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        **{r["rule_id"]: r for r in mapping["warrant_policy_rules"]},
        **{o["overlay_id"]: o for o in mapping["decision_mode_overlays"]},
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def test_proposed_schemas_validate_offline(repo_root: Path) -> None:
    from oic.schemas import SchemaStatus, validate_schema_directory

    report = validate_schema_directory(repo_root / PROPOSED, root=repo_root)
    assert [issue.render() for issue in report.issues] == []
    assert report.status is SchemaStatus.PASS
    assert len(report.results) == 3


def test_proposed_schemas_need_no_remote_resolution(repo_root: Path) -> None:
    """The suite runs with sockets disabled, so passing proves no fetch occurred."""
    from oic.schemas import SchemaStatus, validate_schema_directory

    report = validate_schema_directory(
        repo_root / PROPOSED, root=repo_root, allow_external_refs=False
    )
    assert report.status is SchemaStatus.PASS


# ---------------------------------------------------------------------------
# Fixture validity
# ---------------------------------------------------------------------------


def test_every_expected_case_is_present(fixtures: dict[str, dict[str, Any]]) -> None:
    assert tuple(sorted(fixtures)) == EXPECTED_CASES


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_runtime_decision_validates(repo_root: Path, case: str) -> None:
    decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
    errors = sorted(_validator(repo_root, "runtime-decision").iter_errors(decision), key=str)
    assert errors == [], [error.message for error in errors]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_warrant_validity_matches_declared_reachability(repo_root: Path, case: str) -> None:
    """The schema's profile constraints ARE the measured reachability.

    A REACHABLE fixture's warrant must validate. A NOT_REACHABLE one must NOT: its
    disposition/grade/verdict combination is one the pinned kernel cannot produce, and the
    schema encodes exactly that.
    """
    fixture = _fixture(repo_root, case)
    warrant = fixture["input"]["warrant_artifact"]
    if warrant is None:
        return
    errors = sorted(_validator(repo_root, "warrant-artifact").iter_errors(warrant), key=str)
    if fixture["reachability"] == "REACHABLE":
        assert errors == [], [error.message for error in errors]
    else:
        assert errors, f"{case} is declared NOT_REACHABLE but satisfies the profile schema"


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_warrant_requirement_validates(repo_root: Path, case: str) -> None:
    envelope = _fixture(repo_root, case)["input"]["envelope"]
    if envelope is None:
        return
    requirement = envelope["warrant_requirement"]
    if requirement is None:
        # A deliberately missing control contract: OIC-W-0026, mode recorded as null.
        decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
        assert decision["warrant_requirement_mode"] is None, case
        assert "OIC-W-0026" in decision["reason_codes"], case
        return
    errors = sorted(_validator(repo_root, "warrant-requirement").iter_errors(requirement), key=str)
    assert errors == [], [error.message for error in errors]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_expected_block_agrees_with_its_runtime_decision(repo_root: Path, case: str) -> None:
    expected = _fixture(repo_root, case)["expected"]
    decision = expected["runtime_decision"]
    for field in (
        "epistemic_status",
        "execution_disposition",
        "decision_basis",
        "reason_codes",
        "missing_ground_ids",
        "missing_ground_anchors",
        "warrant_state",
    ):
        assert expected[field] == decision[field], f"{case}: {field} disagrees"


# ---------------------------------------------------------------------------
# Canonical mapping
# ---------------------------------------------------------------------------


def test_json_mapping_is_declared_canonical(mapping: dict[str, Any]) -> None:
    assert mapping["canonical"] is True
    assert mapping["kernel_profile_id"] == "ztl-v0.1"
    assert mapping["kernel_profile_ref"] == PROFILE
    assert set(mapping["authority_values"]) == {
        "MEASURED",
        "ZTL-CONFIRMED",
        "OIC-DEFENSIVE",
        "PENDING-ZTL",
    }


def test_mapping_is_compositional(mapping: dict[str, Any]) -> None:
    """Two tables, not one. A flat table let an overlay assert an epistemic status."""
    assert "rows" not in mapping, "the flat rows array must be gone"
    assert "control_overlays" not in mapping, "overlays are now split into two stages"
    assert mapping["classification_rows"]
    assert mapping["warrant_policy_rules"]
    assert mapping["decision_mode_overlays"]
    stages = mapping["evaluation_stages"]
    assert set(stages) >= {"1_classification", "2_warrant_policy", "3_decision_mode"}
    assert any("preserves the epistemic status" in i for i in stages["invariants"])


def test_disposition_to_epistemic_mapping_is_declared(mapping: dict[str, Any]) -> None:
    assert mapping["epistemic_status_mapping"] == {
        "EARNED": "ESTABLISHED",
        "ON CREDIT": "CONDITIONALLY_SUPPORTED",
        "OPEN": "UNRESOLVED",
        "REFUTED": "REFUTED",
        "contradictory grounds": "CONTRADICTED",
    }


def test_markdown_table_is_generated_from_the_json(repo_root: Path) -> None:
    """Re-render in memory and compare. The Markdown may not be hand-edited."""
    sys.path.insert(0, str(repo_root))
    try:
        from tools.render_mapping import rendered_markdown
    finally:
        sys.path.pop(0)
    assert (repo_root / MAPPING_MD).read_text(encoding="utf-8") == rendered_markdown(repo_root)


def test_markdown_contains_all_three_stage_tables(repo_root: Path) -> None:
    text = (repo_root / MAPPING_MD).read_text(encoding="utf-8")
    assert "### Stage 1 - classification" in text
    assert "### Stage 2 - warrant policy" in text
    assert "### Stage 3 - decision mode" in text
    assert "PRESERVE" in text


def test_every_classification_row_is_well_formed(rows: dict[int, dict[str, Any]]) -> None:
    assert set(rows) == set(range(1, 33))
    for number, row in rows.items():
        assert row["epistemic_status"] in EPISTEMIC, number
        assert row["decision_basis"] in BASES, number
        assert row["reachability"] in {"REACHABLE", "NOT_REACHABLE"}, number
        assert row["authority"] in {
            "MEASURED",
            "ZTL-CONFIRMED",
            "OIC-DEFENSIVE",
            "PENDING-ZTL",
        }, number
        assert set(row["base_execution_choices"]) <= {"ALLOW", "BLOCK", "ESCALATE", "ADVISORY"}
        assert re.fullmatch(r"OIC-[WD]-[0-9]{4}", row["primary_reason_code"]), number
        assert 1 <= int(row["precedence"]) <= 5, number
        assert row["warrant_state"], number


def test_every_overlay_preserves_epistemic_status(
    overlays: dict[str, dict[str, Any]],
) -> None:
    """The structural guarantee: an overlay changes what was done, not what is true."""
    assert len(overlays) == 8
    for identifier, overlay in overlays.items():
        assert overlay["epistemic_effect"] == "PRESERVE", identifier
        assert "epistemic_status" not in overlay, identifier
        if overlay.get("identity"):
            assert overlay["execution_disposition"] == "PRESERVE", identifier
            continue
        assert overlay["decision_basis"] == "CONTROL_REQUIREMENT", identifier
        assert overlay["policy_reason_code"] in CONTROL_POLICY_CODES, identifier
        assert overlay["execution_disposition"] in {"ALLOW", "BLOCK", "ESCALATE", "ADVISORY"}


def test_only_one_overlay_can_allow(overlays: dict[str, dict[str, Any]]) -> None:
    allowing = [k for k, v in overlays.items() if v["execution_disposition"] == "ALLOW"]
    assert allowing == ["WP-3"]
    assert overlays["WP-3"]["policy_reason_code"] == "OIC-D-0005"
    assert "allow_with_disclosure" in overlays["WP-3"]["trigger"]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_matches_its_classification_row(repo_root: Path, case: str) -> None:
    """Stage 1 always fixes the epistemic status and the warrant state."""
    fixture = _fixture(repo_root, case)
    row = _rows(repo_root)[fixture["classification_row"]]
    expected = fixture["expected"]
    assert expected["epistemic_status"] == row["epistemic_status"], case
    assert expected["warrant_state"] == row["warrant_state"], case
    assert fixture["reachability"] == row["reachability"], case


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_execution_follows_the_last_applied_stage(repo_root: Path, case: str) -> None:
    """With no overlay the row decides; otherwise the last applied rule decides."""
    fixture = _fixture(repo_root, case)
    expected = fixture["expected"]
    applied = fixture["applied_control_overlay_ids"]

    if not applied:
        row = _rows(repo_root)[fixture["classification_row"]]
        assert expected["decision_basis"] == row["decision_basis"], case
        assert expected["execution_disposition"] in row["base_execution_choices"], case
        assert row["primary_reason_code"] in expected["reason_codes"], case
        return

    overlays = _overlays(repo_root)
    last = overlays[applied[-1]]
    assert expected["execution_disposition"] == last["execution_disposition"], case
    assert expected["decision_basis"] == "CONTROL_REQUIREMENT", case


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_applied_overlay_ids_are_ordered_unique_and_known(repo_root: Path, case: str) -> None:
    """Warrant-policy rules before decision-mode overlays; no duplicates; DM-1 never."""
    fixture = _fixture(repo_root, case)
    applied = fixture["applied_control_overlay_ids"]
    assert applied == fixture["expected"]["runtime_decision"]["applied_control_overlay_ids"]
    assert len(applied) == len(set(applied)), case
    assert "DM-1" not in applied, f"{case}: the identity overlay is never recorded"
    overlays = _overlays(repo_root)
    for identifier in applied:
        assert identifier in overlays, f"{case}: {identifier}"
    stages = ["WP" if identifier.startswith("WP") else "DM" for identifier in applied]
    assert stages == sorted(stages, key=lambda s: 0 if s == "WP" else 1), (
        f"{case}: stage 2 rules must precede stage 3 overlays"
    )
    assert len([s for s in stages if s == "DM"]) <= 1, f"{case}: at most one decision-mode overlay"


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_every_applied_rule_keeps_its_reason_code(repo_root: Path, case: str) -> None:
    """A later stage may change the execution; it may not erase why an earlier one fired."""
    fixture = _fixture(repo_root, case)
    overlays = _overlays(repo_root)
    codes = set(fixture["expected"]["reason_codes"])
    for identifier in fixture["applied_control_overlay_ids"]:
        expected_code = overlays[identifier]["policy_reason_code"]
        assert expected_code in codes, f"{case}: {identifier} lost {expected_code}"


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_no_stage_changes_the_epistemic_status(repo_root: Path, case: str) -> None:
    fixture = _fixture(repo_root, case)
    if not fixture["applied_control_overlay_ids"]:
        return
    row = _rows(repo_root)[fixture["classification_row"]]
    assert fixture["expected"]["epistemic_status"] == row["epistemic_status"], case


def test_warrant_policy_rules_are_ordered(mapping: dict[str, Any]) -> None:
    """Grade sufficiency (order 1) is evaluated before the unverified-ground policy (2)."""
    rules = {rule["rule_id"]: rule for rule in mapping["warrant_policy_rules"]}
    assert {r["order"] for r in rules.values()} == {1, 2}
    assert all(rules[i]["order"] == 1 for i in ("WP-1", "WP-2"))
    assert all(rules[i]["order"] == 2 for i in ("WP-3", "WP-4", "WP-5"))
    assert (
        "OIC-W-0016" == rules["WP-1"]["policy_reason_code"] == rules["WP-2"]["policy_reason_code"]
    )


def test_grade_check_precedes_the_unverified_ground_policy(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Fixture 11 declares allow_with_disclosure yet never reaches it."""
    fixture = fixtures["11-on-credit-insufficient-grade-escalate"]
    requirement = fixture["input"]["envelope"]["warrant_requirement"]
    assert requirement["unverified_ground_policy"] == "allow_with_disclosure"
    assert fixture["applied_control_overlay_ids"] == ["WP-1"]
    assert fixture["expected"]["execution_disposition"] == "ESCALATE"
    assert "OIC-W-0016" in fixture["expected"]["reason_codes"]
    assert "OIC-D-0005" not in fixture["expected"]["reason_codes"]
    assert fixture["expected"]["runtime_decision"]["unverified_ground_policy_applied"] is None


COMPOSITION_EXAMPLES = (
    (
        "28-compose-conditional-insufficient-grade-then-human-judgment",
        "CONDITIONALLY_SUPPORTED",
        "ESCALATE",
        ["WP-2", "DM-2"],
        {"OIC-W-0016", "OIC-D-0002"},
    ),
    (
        "29-compose-conditional-accepted-then-human-judgment",
        "CONDITIONALLY_SUPPORTED",
        "ESCALATE",
        ["WP-3", "DM-2"],
        {"OIC-D-0005", "OIC-D-0002"},
    ),
    ("30-compose-refuted-advisory", "REFUTED", "ADVISORY", ["DM-3"], {"OIC-W-0013", "OIC-D-0003"}),
    (
        "31-compose-contradicted-human-judgment",
        "CONTRADICTED",
        "ESCALATE",
        ["DM-2"],
        {"OIC-W-0014", "OIC-D-0002"},
    ),
)


@pytest.mark.parametrize(
    ("case", "status", "execution", "applied", "codes"),
    COMPOSITION_EXAMPLES,
    ids=[example[0] for example in COMPOSITION_EXAMPLES],
)
def test_mandated_composition_examples(
    repo_root: Path,
    case: str,
    status: str,
    execution: str,
    applied: list[str],
    codes: set[str],
) -> None:
    """The four compositions the architecture review named, checked end to end."""
    decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == status
    assert decision["execution_disposition"] == execution
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert decision["applied_control_overlay_ids"] == applied
    assert codes <= set(decision["reason_codes"]), (
        f"{case}: lineage lost, expected {sorted(codes)} in {decision['reason_codes']}"
    )


def test_measured_rows_reflect_the_ztl_evidence(rows: dict[int, dict[str, Any]]) -> None:
    for number in (26, 30, 31):
        assert rows[number]["reachability"] == "NOT_REACHABLE", number
        assert rows[number]["authority"] == "ZTL-CONFIRMED", number
    assert not [n for n, r in rows.items() if r["authority"] == "PENDING-ZTL"]


def test_on_credit_rows_are_conditionally_supported(rows: dict[int, dict[str, Any]]) -> None:
    on_credit = {n: r for n, r in rows.items() if r["disposition"] == "ON CREDIT"}
    assert set(on_credit) == {28, 29, 32}
    for number, row in on_credit.items():
        assert row["epistemic_status"] == "CONDITIONALLY_SUPPORTED", number
        assert row["unverified"] == "non-empty", number
    # 28 and 29 are kernel behaviour; 32 is an OIC-side binding precondition.
    assert rows[28]["authority"] == rows[29]["authority"] == "MEASURED"
    assert rows[32]["authority"] == "OIC-DEFENSIVE"
    assert rows[32]["primary_reason_code"] == "OIC-W-0027"
    # Only the `sound` row may ever reach ALLOW, and only via an overlay.
    assert "ALLOW" in rows[28]["base_execution_choices"]
    assert "ALLOW" not in rows[29]["base_execution_choices"]
    assert rows[29]["primary_reason_code"] == "OIC-W-0025"
    assert rows[29]["decision_basis"] == "PRECAUTIONARY"


def test_earned_is_the_only_disposition_mapping_to_established(
    rows: dict[int, dict[str, Any]],
) -> None:
    for number, row in rows.items():
        if row["epistemic_status"] == "ESTABLISHED":
            assert row["disposition"] == "EARNED", number
            assert row["grade"] == "hereditary", number
        if row["disposition"] == "EARNED" and row["grade"] != "hereditary":
            assert row["reachability"] == "NOT_REACHABLE", number
            assert row["epistemic_status"] != "ESTABLISHED", number


# ---------------------------------------------------------------------------
# Load-bearing invariants
# ---------------------------------------------------------------------------


def test_open_never_becomes_refuted(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-1, derived from the INPUT so a wrong expectation cannot hide."""
    checked = 0
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "OPEN":
            continue
        checked += 1
        assert fixture["expected"]["epistemic_status"] == "UNRESOLVED", case
    assert checked >= 3


def test_open_never_becomes_a_substantive_refusal(fixtures: dict[str, dict[str, Any]]) -> None:
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "OPEN":
            continue
        assert fixture["expected"]["decision_basis"] != "SUBSTANTIVE", case


def test_raw_verdict_never_drives_the_outcome(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-2. The measured trap, plus its converse."""
    raw_f_open = [
        case
        for case, f in fixtures.items()
        if (z := f["input"]["ztl_result"])
        and z.get("disposition") == "OPEN"
        and z.get("raw_verdict") == "F"
    ]
    assert raw_f_open, "the measured case is not covered"
    for case in raw_f_open:
        assert fixtures[case]["expected"]["epistemic_status"] == "UNRESOLVED", case
    for case, f in fixtures.items():
        z = f["input"]["ztl_result"]
        if z and z.get("disposition") == "OPEN" and z.get("raw_verdict") == "T":
            assert f["expected"]["epistemic_status"] != "ESTABLISHED", case


def test_on_credit_is_never_treated_as_earned(fixtures: dict[str, dict[str, Any]]) -> None:
    """Mapped as EARNED, ON CREDIT authorises action on an unverified link."""
    checked = 0
    for case, f in fixtures.items():
        z = f["input"]["ztl_result"]
        if z is None or z.get("disposition") != "ON CREDIT":
            continue
        checked += 1
        decision = f["expected"]["runtime_decision"]
        assert decision["missing_ground_ids"], f"{case}: ON CREDIT must surface its grounds"
        assert "OIC-W-0015" in decision["reason_codes"], case
        assert decision["warranty_grade_observed"] in {"sound", "until-verification"}, case
        if decision["execution_disposition"] == "ALLOW":
            required = decision["warranty_grade_required"]
            assert required is not None, case
            assert GRADE_ORDER[decision["warranty_grade_observed"]] >= GRADE_ORDER[required], (
                f"{case}: ALLOW on credit below the declared minimum"
            )
    assert checked >= 3


def test_precautionary_block_stays_distinguishable_from_substantive_refusal(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """W-3. Two BLOCKs, two meanings, two records."""
    precautionary = fixtures["05-open-raw-f"]["expected"]
    substantive = fixtures["04-refuted"]["expected"]
    assert precautionary["execution_disposition"] == substantive["execution_disposition"]
    assert precautionary["epistemic_status"] != substantive["epistemic_status"]
    assert precautionary["decision_basis"] == "PRECAUTIONARY"
    assert substantive["decision_basis"] == "SUBSTANTIVE"


def test_only_refutation_and_contradiction_are_substantive_blocks(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Corrected wording: substantive BLOCK codes, not substantive codes in general."""
    for case, fixture in fixtures.items():
        expected = fixture["expected"]
        if expected["decision_basis"] != "SUBSTANTIVE":
            continue
        if expected["execution_disposition"] == "ALLOW":
            assert SUBSTANTIVE_ALLOW_CODE in expected["reason_codes"], case
            continue
        assert set(expected["reason_codes"]) & SUBSTANTIVE_BLOCK_CODES, case
        assert expected["epistemic_status"] in {"REFUTED", "CONTRADICTED"}, case


def test_on_unknown_deny_is_never_substantive(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-6."""
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision["on_unknown_applied"] != "deny":
            continue
        checked += 1
        assert decision["decision_basis"] != "SUBSTANTIVE", case
        assert decision["epistemic_status"] != "REFUTED", case
        assert decision["execution_disposition"] != "ALLOW", case
    assert checked >= 1


def test_contradiction_is_never_refutation(fixtures: dict[str, dict[str, Any]]) -> None:
    fixture = fixtures["18-contradiction"]
    assert fixture["input"]["runtime_context"]["contradiction_detected"] is True
    assert fixture["input"]["ztl_result"]["disposition"] == "REFUTED"
    assert fixture["expected"]["epistemic_status"] == "CONTRADICTED"


def test_missing_grounds_are_never_dropped(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-5, including on ALLOW."""
    checked = 0
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or not ztl.get("unverified"):
            continue
        checked += 1
        assert fixture["expected"]["missing_ground_ids"] == list(ztl["unverified"]), case
    assert checked >= 6


def test_missing_grounds_survive_an_allow(fixtures: dict[str, dict[str, Any]]) -> None:
    fixture = fixtures["08-on-credit-sound-allow-with-disclosure"]
    assert fixture["expected"]["execution_disposition"] == "ALLOW"
    assert fixture["expected"]["missing_ground_ids"] != []
    assert "OIC-W-0015" in fixture["expected"]["reason_codes"]


def test_missing_ground_anchors_are_the_enrichment_level(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    enriched = [f for f in fixtures.values() if f["expected"]["missing_ground_anchors"]]
    assert enriched
    for fixture in enriched:
        for anchor in fixture["expected"]["missing_ground_anchors"]:
            assert anchor["source_id"], "an enriched anchor must reach the source"
            assert anchor["admitted_unit_id"], "and the admitted unit"
        recorded = {a["ground_id"] for a in fixture["expected"]["missing_ground_anchors"]}
        assert recorded <= set(fixture["expected"]["missing_ground_ids"])


# ---------------------------------------------------------------------------
# CONTROL_REQUIREMENT
# ---------------------------------------------------------------------------


def test_control_requirement_is_not_a_defect_or_uncertainty(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    """A control-mandated escalation is neither PROCEDURAL nor epistemic doubt."""
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision["decision_basis"] != "CONTROL_REQUIREMENT":
            continue
        checked += 1
        # The warrant remains valid; only the control's policy intervened.
        assert decision["warrant_state"] == "USABLE", case
        assert set(decision["reason_codes"]) & CONTROL_POLICY_CODES, case
        # The status is whatever the classification said -- never rewritten, and never
        # invented by the overlay.
        row = _rows(repo_root)[fixture["classification_row"]]
        assert decision["epistemic_status"] == row["epistemic_status"], (
            f"{case}: CONTROL_REQUIREMENT must not rewrite the epistemic status"
        )
        # It is a control decision, so it is never reported as a defect or a doubt.
        assert decision["decision_basis"] not in {"PROCEDURAL", "PRECAUTIONARY"}, case
        if decision["execution_disposition"] == "ALLOW":
            assert decision["epistemic_status"] in {"CONDITIONALLY_SUPPORTED"}, case
            assert decision["unverified_ground_policy_applied"] == "allow_with_disclosure", case
    assert checked >= 8


def test_insufficient_grade_is_a_control_requirement(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """An insufficient grade never permits, and when it decides it is a control matter."""
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        observed = decision["warranty_grade_observed"]
        required = decision["warranty_grade_required"]
        if observed is None or required is None:
            continue
        if GRADE_ORDER[observed] >= GRADE_ORDER[required]:
            continue
        # Whatever else is true, an insufficient grade cannot permit the action.
        assert decision["execution_disposition"] != "ALLOW", case
        # The grade rules are WP-1 and WP-2. A classification whose own basis already
        # decides -- ON CREDIT + until-verification is PRECAUTIONARY because the result is
        # unstable, not because the grade fell short -- is not the grade gate's case.
        if not set(fixture["applied_control_overlay_ids"]) & {"WP-1", "WP-2"}:
            continue
        checked += 1
        assert decision["decision_basis"] == "CONTROL_REQUIREMENT", case
        assert "OIC-W-0016" in decision["reason_codes"], case
    assert checked >= 2


def test_human_judgment_escalates_a_perfect_warrant(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    fixture = fixtures["25-overlay-established-human-judgment"]
    assert fixture["input"]["envelope"]["decision_mode"] == "human_judgment"
    decision = fixture["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["execution_disposition"] == "ESCALATE"
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert "OIC-D-0002" in decision["reason_codes"]
    assert decision["warranty_grade_observed"] == "hereditary"


def test_advisory_records_without_gating(fixtures: dict[str, dict[str, Any]]) -> None:
    decision = fixtures["26-overlay-established-advisory"]["expected"]["runtime_decision"]
    assert decision["execution_disposition"] == "ADVISORY"
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert "OIC-D-0003" in decision["reason_codes"]


# ---------------------------------------------------------------------------
# Warrant requirement object
# ---------------------------------------------------------------------------


def test_warrant_requirement_conditional_fields(repo_root: Path) -> None:
    validator = _validator(repo_root, "warrant-requirement")

    valid_required = {
        "mode": "required",
        "kernel_profile_id": "ztl-v0.1",
        "minimum_warranty_grade": "hereditary",
        "on_insufficient_grade": "escalate",
        "unverified_ground_policy": "allow_with_disclosure",
    }
    assert list(validator.iter_errors(valid_required)) == []

    for mode in ("not_required", "not_applicable"):
        assert (
            list(
                validator.iter_errors(
                    {
                        "mode": mode,
                        "kernel_profile_id": None,
                        "minimum_warranty_grade": None,
                        "on_insufficient_grade": None,
                        "unverified_ground_policy": None,
                    }
                )
            )
            == []
        )

    for field in (
        "kernel_profile_id",
        "minimum_warranty_grade",
        "on_insufficient_grade",
        "unverified_ground_policy",
    ):
        bad = dict(valid_required, **{field: None})
        assert list(validator.iter_errors(bad)), f"required/{field}=None should be invalid"

    for field, value in (
        ("kernel_profile_id", "ztl-v0.1"),
        ("minimum_warranty_grade", "sound"),
        ("on_insufficient_grade", "block"),
        ("unverified_ground_policy", "allow_with_disclosure"),
    ):
        bad = {
            "mode": "not_required",
            "kernel_profile_id": None,
            "minimum_warranty_grade": None,
            "on_insufficient_grade": None,
            "unverified_ground_policy": None,
            field: value,
        }
        assert list(validator.iter_errors(bad)), f"not_required/{field} set should be invalid"

    assert list(validator.iter_errors({"kernel_profile_id": None})), "no default mode allowed"


def test_not_required_never_waives_other_checks(repo_root: Path) -> None:
    text = (repo_root / PROPOSED / "warrant-requirement.schema.json").read_text("utf-8")
    assert "NOT permission to skip authority, admission, evidence, or version checks" in text
    fixture = _fixture(repo_root, "23-warrant-explicitly-not-applicable")
    assert fixture["expected"]["execution_disposition"] != "ALLOW"
    assert fixture["expected"]["warrant_state"] == "NOT_REQUIRED"


# ---------------------------------------------------------------------------
# Negative schema tests: every prohibited combination
# ---------------------------------------------------------------------------


def _base_decision(repo_root: Path) -> dict[str, Any]:
    return dict(_fixture(repo_root, "01-earned-hereditary-current")["expected"]["runtime_decision"])


PROHIBITED: tuple[tuple[str, dict[str, object]], ...] = (
    ("allow_with_unresolved", {"epistemic_status": "UNRESOLVED"}),
    ("allow_with_refuted", {"epistemic_status": "REFUTED"}),
    ("allow_with_contradicted", {"epistemic_status": "CONTRADICTED"}),
    ("allow_with_precautionary", {"decision_basis": "PRECAUTIONARY"}),
    ("allow_with_procedural", {"decision_basis": "PROCEDURAL"}),
    ("allow_with_control_requirement", {"decision_basis": "CONTROL_REQUIREMENT"}),
    ("allow_with_null_warrant", {"warrant_artifact_id": None}),
    ("allow_with_absent_warrant", {"warrant_state": "ABSENT"}),
    ("allow_with_stale_warrant", {"warrant_state": "STALE"}),
    ("allow_with_misbound_warrant", {"warrant_state": "MISBOUND"}),
    ("allow_with_revoked_warrant", {"warrant_state": "REVOKED"}),
    ("allow_with_not_required_warrant", {"warrant_state": "NOT_REQUIRED"}),
    ("allow_with_on_unknown", {"on_unknown_applied": "deny"}),
    (
        "refuted_precautionary",
        {
            "epistemic_status": "REFUTED",
            "execution_disposition": "BLOCK",
            "decision_basis": "PRECAUTIONARY",
        },
    ),
    (
        "conditional_support_substantive",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "execution_disposition": "BLOCK",
            "decision_basis": "SUBSTANTIVE",
        },
    ),
    (
        "conditional_support_without_missing_grounds",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "execution_disposition": "BLOCK",
            "decision_basis": "PRECAUTIONARY",
            "missing_ground_ids": [],
        },
    ),
    (
        "conditional_support_with_on_unknown",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "execution_disposition": "BLOCK",
            "decision_basis": "PRECAUTIONARY",
            "missing_ground_ids": ["ground:x"],
            "on_unknown_applied": "deny",
        },
    ),
    (
        "conditional_support_allow_on_until_verification",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "decision_basis": "CONTROL_REQUIREMENT",
            "warranty_grade_observed": "until-verification",
            "warranty_grade_required": "until-verification",
            "unverified_ground_policy_applied": "allow_with_disclosure",
            "missing_ground_ids": ["ground:x"],
            "reason_codes": ["OIC-D-0005"],
        },
    ),
    (
        "conditional_support_allow_without_policy",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "decision_basis": "CONTROL_REQUIREMENT",
            "warranty_grade_observed": "sound",
            "missing_ground_ids": ["ground:x"],
            "reason_codes": ["OIC-D-0005"],
            "unverified_ground_policy_applied": None,
        },
    ),
    (
        "conditional_support_allow_without_missing_grounds",
        {
            "epistemic_status": "CONDITIONALLY_SUPPORTED",
            "decision_basis": "CONTROL_REQUIREMENT",
            "warranty_grade_observed": "sound",
            "unverified_ground_policy_applied": "allow_with_disclosure",
            "missing_ground_ids": [],
            "reason_codes": ["OIC-D-0005"],
        },
    ),
    (
        "established_allow_via_disclosure_policy",
        {
            "unverified_ground_policy_applied": "allow_with_disclosure",
            "missing_ground_ids": ["ground:x"],
        },
    ),
    (
        "allow_established_with_sound_grade",
        {"warranty_grade_observed": "sound"},
    ),
    (
        "unresolved_substantive",
        {
            "epistemic_status": "UNRESOLVED",
            "execution_disposition": "BLOCK",
            "decision_basis": "SUBSTANTIVE",
        },
    ),
    (
        "on_unknown_substantive",
        {
            "on_unknown_applied": "deny",
            "execution_disposition": "BLOCK",
            "decision_basis": "SUBSTANTIVE",
            "epistemic_status": "REFUTED",
        },
    ),
    (
        "control_requirement_without_policy_code",
        {
            "decision_basis": "CONTROL_REQUIREMENT",
            "execution_disposition": "ESCALATE",
            "reason_codes": ["OIC-W-0012"],
        },
    ),
    ("empty_replay_reference", {"replay_reference": ""}),
)


@pytest.mark.parametrize(("label", "override"), PROHIBITED, ids=[p[0] for p in PROHIBITED])
def test_prohibited_combinations_are_schema_invalid(
    repo_root: Path, label: str, override: dict[str, object]
) -> None:
    decision = _base_decision(repo_root)
    decision.update(override)
    errors = list(_validator(repo_root, "runtime-decision").iter_errors(decision))
    assert errors, f"{label} should be rejected by the schema"


@pytest.mark.parametrize(
    "field",
    [
        "warrant_state",
        "warranty_grade_observed",
        "warranty_grade_required",
        "on_unknown_applied",
        "unverified_ground_policy_applied",
        "replay_reference",
    ],
)
def test_newly_required_fields_are_required(repo_root: Path, field: str) -> None:
    decision = _base_decision(repo_root)
    del decision[field]
    errors = list(_validator(repo_root, "runtime-decision").iter_errors(decision))
    assert errors, f"{field} must be required"


def test_replay_reference_present_and_non_empty_on_every_decision(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Including failures: a block with no warrant must still be replayable."""
    for case, fixture in fixtures.items():
        reference = fixture["expected"]["runtime_decision"]["replay_reference"]
        assert isinstance(reference, str) and reference.strip(), case


# ---------------------------------------------------------------------------
# Warrant artifact: epoch, profiles, time
# ---------------------------------------------------------------------------


def test_epoch_carries_scope_and_authority(fixtures: dict[str, dict[str, Any]]) -> None:
    """An unscoped integer let two authorities' epochs compare equal."""
    checked = 0
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        checked += 1
        epoch = warrant["ground_epoch"]
        assert set(epoch) == {"scope_id", "sequence", "authority_id"}, case
        assert isinstance(epoch["sequence"], int), case
        assert epoch["scope_id"] and epoch["authority_id"], case
    assert checked >= 20


def test_epoch_mismatch_fixture_compares_within_one_scope(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    fixture = fixtures["17-epoch-mismatch"]
    warrant_epoch = fixture["input"]["warrant_artifact"]["ground_epoch"]
    context_epoch = fixture["input"]["runtime_context"]["current_ground_epoch"]
    assert warrant_epoch["scope_id"] == context_epoch["scope_id"]
    assert warrant_epoch["authority_id"] == context_epoch["authority_id"]
    assert warrant_epoch["sequence"] != context_epoch["sequence"]


def test_profile_bound_formula_hash_comparison(fixtures: dict[str, dict[str, Any]]) -> None:
    """Hashes are compared only after both profile identifiers match."""
    matching = fixtures["01-earned-hereditary-current"]
    warrant, envelope = matching["input"]["warrant_artifact"], matching["input"]["envelope"]
    assert warrant["kernel_profile_id"] == envelope["bound_kernel_profile_id"]
    assert warrant["canonicalization_profile_id"] == envelope["bound_canonicalization_profile_id"]
    assert warrant["formula_hash"] == envelope["bound_formula_hash"]

    mismatch = fixtures["22-profile-mismatch"]
    bad_warrant = mismatch["input"]["warrant_artifact"]
    bad_envelope = mismatch["input"]["envelope"]
    assert bad_warrant["kernel_profile_id"] != bad_envelope["bound_kernel_profile_id"]
    assert mismatch["expected"]["warrant_state"] == "MISBOUND"
    assert mismatch["expected"]["execution_disposition"] != "ALLOW"
    assert "OIC-W-0023" in mismatch["expected"]["reason_codes"]


def test_contract_documents_the_hash_comparison_rule(repo_root: Path) -> None:
    text = _plain(repo_root / CONTRACT_DOC)
    assert "If either profile differs, the hashes are NOT compared" in text
    assert "exact byte equality" in text


def test_time_binding_is_declared(fixtures: dict[str, dict[str, Any]]) -> None:
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        binding = warrant["time_binding"]
        assert binding["source"] in {
            "oic_system_clock",
            "attested_timestamp",
            "external_time_authority",
        }, case
        assert binding["reference"], case


def test_not_yet_valid_is_mapped_and_fixtured(
    fixtures: dict[str, dict[str, Any]], rows: dict[int, dict[str, Any]]
) -> None:
    fixture = fixtures["21-warrant-not-yet-valid"]
    warrant = fixture["input"]["warrant_artifact"]
    assert warrant["valid_from"] > fixture["input"]["runtime_context"]["evaluated_at"]
    assert fixture["expected"]["warrant_state"] == "NOT_YET_VALID"
    assert fixture["expected"]["decision_basis"] == "PROCEDURAL"
    assert "OIC-W-0021" in fixture["expected"]["reason_codes"]
    assert rows[8]["primary_reason_code"] == "OIC-W-0021"


def test_unsupported_result_combination_code_is_used(
    fixtures: dict[str, dict[str, Any]], rows: dict[int, dict[str, Any]]
) -> None:
    """Row 31 must NOT be labelled DISPOSITION_OPEN: its disposition is not OPEN."""
    assert rows[31]["disposition"] == "EARNED"
    assert rows[31]["primary_reason_code"] == "OIC-W-0022"
    assert rows[31]["decision_basis"] == "PROCEDURAL"
    fixture = fixtures["03-earned-until-verification-unsupported-result"]
    assert "OIC-W-0022" in fixture["expected"]["reason_codes"]
    assert "OIC-W-0012" not in fixture["expected"]["reason_codes"]


# ---------------------------------------------------------------------------
# Reason-code registry consistency
# ---------------------------------------------------------------------------


def _registry(repo_root: Path) -> dict[str, str]:
    """Parse the reason-code registry tables out of the contract document."""
    text = (repo_root / CONTRACT_DOC).read_text(encoding="utf-8")
    registry: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(
            r"^\|\s*`(OIC-[WD]-[0-9]{4})`\s*\|\s*`[A-Z_]+`\s*\|\s*(.+?)\s*\|\s*$", line
        )
        if match:
            registry[match.group(1)] = match.group(2).replace("`", "").strip()
    return registry


def test_registry_parses_and_covers_every_used_code(
    repo_root: Path, fixtures: dict[str, dict[str, Any]], rows: dict[int, dict[str, Any]]
) -> None:
    registry = _registry(repo_root)
    assert len(registry) >= 31
    used = {code for f in fixtures.values() for code in f["expected"]["reason_codes"]}
    used |= {row["primary_reason_code"] for row in rows.values()}
    assert used <= set(registry), sorted(used - set(registry))


def test_registry_mapping_and_fixtures_agree_on_basis(
    repo_root: Path, fixtures: dict[str, dict[str, Any]], rows: dict[int, dict[str, Any]]
) -> None:
    """The registry, the canonical mapping, and the fixtures must not disagree."""
    registry = _registry(repo_root)
    bases = {"SUBSTANTIVE", "PRECAUTIONARY", "PROCEDURAL", "CONTROL_REQUIREMENT"}

    for number, row in rows.items():
        declared = registry[row["primary_reason_code"]]
        if declared in bases:
            assert declared == row["decision_basis"], (
                f"row {number}: registry says {declared}, mapping says {row['decision_basis']}"
            )

    for identifier, overlay in _overlays(repo_root).items():
        code = overlay["policy_reason_code"]
        if code is None:
            assert overlay.get("identity"), (
                f"{identifier}: only the identity overlay may omit a code"
            )
            continue
        declared = registry[code]
        assert declared == "CONTROL_REQUIREMENT", f"overlay {identifier}: registry says {declared}"

    for case, fixture in fixtures.items():
        if fixture["applied_control_overlay_ids"]:
            # An overlay supplies its own basis and policy code; the row's base reason no
            # longer determines the outcome.
            continue
        row = rows[fixture["classification_row"]]
        declared = registry[row["primary_reason_code"]]
        if declared in bases:
            assert fixture["expected"]["decision_basis"] == declared, case


def test_registry_names_the_substantive_codes_correctly(repo_root: Path) -> None:
    """The corrected wording, not the old inaccurate claim."""
    text = _plain(repo_root / CONTRACT_DOC)
    assert "OIC-W-0013 and OIC-W-0014 are the only substantive BLOCK reason codes" in text
    assert "OIC-D-0001 is the substantive positive-decision code" in text
    assert "are the only substantive codes" not in text


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_files_are_canonically_serialised(repo_root: Path, case: str) -> None:
    path = repo_root / FIXTURE_DIR / f"{case}.json"
    raw = path.read_text(encoding="utf-8")
    canonical = json.dumps(json.loads(raw), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw == canonical, f"{case}.json is not canonically serialised"


def test_mapping_json_is_canonically_serialised(repo_root: Path) -> None:
    raw = (repo_root / MAPPING_JSON).read_text(encoding="utf-8")
    canonical = json.dumps(json.loads(raw), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw == canonical


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_reason_codes_are_sorted_and_wellformed(repo_root: Path, case: str) -> None:
    codes = _fixture(repo_root, case)["expected"]["reason_codes"]
    assert codes
    assert codes == sorted(codes)
    assert len(codes) == len(set(codes))
    for code in codes:
        assert re.fullmatch(r"OIC-[WD]-[0-9]{4}", code), code


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_digests_are_wellformed(repo_root: Path, case: str) -> None:
    sha256 = re.compile(r"^sha256:[0-9a-f]{64}$")
    sha384 = re.compile(r"^sha384:[0-9a-f]{96}$")
    fixture = _fixture(repo_root, case)
    warrant = fixture["input"]["warrant_artifact"]
    if warrant is not None:
        for field in ("ground_set_hash", "input_hash", "output_hash"):
            assert sha256.fullmatch(warrant[field]), f"{case}.{field}"
        assert sha384.fullmatch(warrant["formula_hash"]), f"{case}.formula_hash"
        assert re.fullmatch(r"[0-9a-f]{40}", warrant["kernel_commit"])
    decision = fixture["expected"]["runtime_decision"]
    for field in ("source_version_set_hash", "input_hash"):
        assert sha256.fullmatch(decision[field]), f"{case}.{field}"


# ---------------------------------------------------------------------------
# Owner decisions, VEIP chronology, boundary discipline
# ---------------------------------------------------------------------------


def test_legacy_deny_is_never_automatically_converted(repo_root: Path) -> None:
    text = _plain(repo_root / ADR)
    assert "LEGACY_UNDECOMPOSED" in text
    assert "must not be back-filled as REFUTED" in text
    assert "reevaluate the case under this contract" in text
    for path in sorted((repo_root / FIXTURE_DIR).glob("*.json")):
        assert "LEGACY" not in path.read_text(encoding="utf-8")


def test_expiry_authority_is_recorded(repo_root: Path) -> None:
    text = _plain(repo_root / ADR)
    assert "An admission may narrow but may not extend upstream validity" in text
    assert "earliest active applicable boundary" in text
    assert "does not create validity or revocation authority" in text


def test_veip_chronology_is_corrected(repo_root: Path) -> None:
    """RuntimeDecision is evidence inside the lifecycle, not its first artifact."""
    text = _plain(repo_root / ADR)
    assert "VEIP receives or records the consequential ActionProposal" in text
    assert "evidence inside the VEIP lifecycle" in text
    assert "not itself a VEIP lifecycle record" in text
    assert "not the first VEIP artifact" in text

    # The superseded claim may appear exactly once, inside the correction that quotes it.
    # It must never stand as an assertion of its own.
    superseded = "the first artifact VEIP binds to"
    assert text.count(superseded) <= 1
    if superseded in text:
        quoted = text[text.index(superseded) : text.index(superseded) + 400]
        assert "That was wrong" in quoted, "the superseded claim is not marked as corrected"


def test_veip_handoff_binding_set_is_stated(repo_root: Path) -> None:
    text = _plain(repo_root / ADR)
    for field in (
        "action_proposal_id",
        "envelope_id and envelope hash",
        "runtime_decision_id and decision hash",
        "warrant_artifact_id and warrant hash",
        "evaluation input hash",
        "authority and admission versions",
    ):
        assert field in text, field
    assert "deferred to OIC-GC-004" in text


#: Scripts checked in by PR #18 as the ZTL side's OWN reproduction/verification evidence.
#: They are not an OIC adapter, are not part of this work order, and are not imported or
#: called from anywhere OIC-side. Naming them explicitly means an unnamed .py file appearing
#: under adapters/ztl or adapters/veip -- an actual adapter implementation -- still fails.
_ZTL_EVIDENCE_SCRIPTS = frozenset(
    {
        "adapters/ztl/evidence/kernel_census.py",
        "adapters/ztl/fixtures/interface-freeze-v0.1/verify_fixtures.py",
        "adapters/ztl/fixtures/interface-freeze-v0.2/verify_fixtures.py",
    }
)


def test_no_ztl_or_veip_code_exists_or_is_imported(repo_root: Path) -> None:
    for module in sorted((repo_root / "src" / "oic").glob("*.py")):
        text = module.read_text(encoding="utf-8").lower()
        for forbidden in ("import ztl", "from ztl", "import veip", "from veip"):
            assert forbidden not in text, f"{module.name}: {forbidden}"

    for directory in ("ztl", "veip"):
        found = {
            path.relative_to(repo_root).as_posix()
            for path in (repo_root / "adapters" / directory).glob("**/*.py")
        }
        unexpected = found - _ZTL_EVIDENCE_SCRIPTS
        assert unexpected == set(), (
            f"unexpected .py under adapters/{directory}, not part of the named ZTL "
            f"evidence scripts: {sorted(unexpected)}"
        )

    # The evidence scripts are the ZTL side's own reproduction tooling: never imported or
    # called from OIC runtime code or from the semantic-conformance validator. (This test
    # file itself legitimately names them as data above, so it is excluded here.)
    for path in sorted((repo_root / "src" / "oic").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "kernel_census" not in text, path
        assert "verify_fixtures" not in text, path
    validator = repo_root / "tests" / "contract" / "semantic_conformance.py"
    validator_text = validator.read_text(encoding="utf-8")
    assert "kernel_census" not in validator_text
    assert "verify_fixtures" not in validator_text


L0_HISTORICAL_BASELINE = "857a21d47b76c58a511fe2955356db794ca80ab0"
L0_SOURCE_DELTA_AUTHORIZATION = (
    "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-L0-SOURCE-DELTA-AUTHORIZATION-001.json"
)
L0_BASELINE_MODULES = frozenset(
    {
        "__init__.py",
        "baseline.py",
        "cli.py",
        "doctor.py",
        "errors.py",
        "hashing.py",
        "manifests.py",
        "paths.py",
        "schemas.py",
    }
)


def _baseline_source_modules(repo_root: Path) -> set[str]:
    """The src/oic modules present at the frozen L0 baseline commit."""
    listing = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-tree",
            "-r",
            "--name-only",
            L0_HISTORICAL_BASELINE,
            "src/oic",
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    return {Path(path).name for path in listing.stdout.splitlines() if path.endswith(".py")}


def _assert_exact_source_delta(
    current_modules: set[str], baseline_modules: set[str], authorized: set[str]
) -> None:
    """Exact equality, never a subset: an undeclared module must fail."""
    assert baseline_modules <= current_modules
    assert current_modules - baseline_modules == authorized


def test_this_work_order_added_no_source_module(repo_root: Path) -> None:
    """The baseline is a historical fact and stays true regardless of later work.

    It previously compared the *working tree* to the nine original modules, which
    conflated "what the baseline contained" with "what exists now" and would fail
    for any authorized later addition. It now inspects the frozen baseline commit
    itself, so the proposition remains true forever.
    """
    assert _baseline_source_modules(repo_root) == set(L0_BASELINE_MODULES)


def test_l0_source_delta_authorization_is_exact(repo_root: Path) -> None:
    """The L0 instrument authorizes source presence only, and says so."""
    authorization = json.loads((repo_root / L0_SOURCE_DELTA_AUTHORIZATION).read_bytes())
    assert (
        authorization["authorization_id"] == "OWNER-AUTHORIZATION-OIC-ZTL-OAM-DEMO-SLICE-001-L0-001"
    )
    assert authorization["scope"] == "OIC-ZTL-OAM-DEMO-SLICE-001-L0"
    assert authorization["historical_baseline"] == L0_HISTORICAL_BASELINE
    assert (
        authorization["implementation_source_commit"] == "fa96f5c3590f54118cd926a84370be6022a80b35"
    )
    assert authorization["implementation_source_tree"] == "65a704cd9c70aef983b62ecc8176793e20004772"
    assert authorization["authorized_post_baseline_source_modules"] == [
        "src/oic/cdc_currentness.py",
        "src/oic/cdc_authority.py",
        "src/oic/cdc_propagation.py",
        "src/oic/cdc_reliance.py",
    ]
    for flag in (
        "additional_source_modules_authorized",
        "semantic_modification_authorized",
        "result_bearing_execution_authorized",
        "end_to_end_demo_claim_authorized",
        "production_claim_authorized",
        "institutional_reliance_authorized",
    ):
        assert authorization[flag] is False, flag


def test_l0_source_delta_is_exactly_authorized(repo_root: Path) -> None:
    """Everything added to src/oic since the baseline is named by the instrument."""
    authorization = json.loads((repo_root / L0_SOURCE_DELTA_AUTHORIZATION).read_bytes())
    authorized = {
        Path(path).name for path in authorization["authorized_post_baseline_source_modules"]
    }
    current_modules = {path.name for path in (repo_root / "src" / "oic").glob("*.py")}
    _assert_exact_source_delta(current_modules, _baseline_source_modules(repo_root), authorized)
    # Explicitly excluded from this lane and expected to stay absent.
    assert "cdc_slice.py" not in current_modules
    assert "cdc_e2e_mission.py" not in current_modules


def test_l0_source_delta_guard_rejects_an_undeclared_module() -> None:
    """Fail-closed: a fifth undeclared module must break the exact-delta rule."""
    authorized = {
        "cdc_currentness.py",
        "cdc_authority.py",
        "cdc_propagation.py",
        "cdc_reliance.py",
    }
    mutated = set(L0_BASELINE_MODULES) | authorized | {"unauthorized_fifth_module.py"}
    with pytest.raises(AssertionError):
        _assert_exact_source_delta(mutated, set(L0_BASELINE_MODULES), authorized)


def test_draft_schemas_are_byte_identical_to_the_bootstrap(repo_root: Path) -> None:
    from oic.baseline import BOOTSTRAP_COMMIT

    for path in sorted((repo_root / "schemas" / "draft").glob("*.schema.json")):
        relative = path.relative_to(repo_root).as_posix()
        committed = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "blob", f"{BOOTSTRAP_COMMIT}:{relative}"],
            capture_output=True,
            check=True,
        ).stdout
        assert path.read_bytes() == committed, relative


def test_status_md_is_byte_identical_to_the_bootstrap(repo_root: Path) -> None:
    from oic.baseline import BOOTSTRAP_COMMIT

    committed = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "blob", f"{BOOTSTRAP_COMMIT}:STATUS.md"],
        capture_output=True,
        check=True,
    ).stdout
    assert (repo_root / "STATUS.md").read_bytes() == committed


def test_proposed_schemas_are_not_in_the_draft_directory(repo_root: Path) -> None:
    draft = {path.name for path in (repo_root / "schemas" / "draft").glob("*.json")}
    proposed = {path.name for path in (repo_root / PROPOSED).glob("*.json")}
    assert draft.isdisjoint(proposed)
    assert len(draft) == 9
    assert len(proposed) == 3


def test_documents_state_the_gate_is_blocked(repo_root: Path) -> None:
    for relpath in (CONTRACT_DOC, MAPPING_MD, ADR):
        assert "semantic implementation gate remains BLOCKED" in _plain(repo_root / relpath), (
            relpath
        )


def test_documents_label_themselves_proposed(repo_root: Path) -> None:
    for relpath in (CONTRACT_DOC, MAPPING_MD):
        head = (repo_root / relpath).read_text("utf-8")[:400].replace("*", "")
        assert "PROPOSED" in head, relpath
        assert "Not admitted" in head, relpath


# ---------------------------------------------------------------------------
# A. CONDITIONALLY_SUPPORTED
# ---------------------------------------------------------------------------


def test_on_credit_never_maps_to_established(fixtures: dict[str, dict[str, Any]]) -> None:
    """Derived from the INPUT disposition, so a wrong expectation cannot hide.

    Mapped as ESTABLISHED, ON CREDIT authorises action on an unverified link.
    """
    checked = 0
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "ON CREDIT":
            continue
        checked += 1
        assert fixture["expected"]["epistemic_status"] == "CONDITIONALLY_SUPPORTED", case
        assert fixture["expected"]["epistemic_status"] != "ESTABLISHED", case
    assert checked >= 5


def test_on_credit_never_collapses_to_unresolved(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Unverified grounds do not erase a real positive result; that would over-block."""
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "ON CREDIT":
            continue
        assert fixture["expected"]["epistemic_status"] != "UNRESOLVED", case


def test_earned_is_the_only_input_disposition_reaching_established(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    for case, fixture in fixtures.items():
        if fixture["expected"]["epistemic_status"] != "ESTABLISHED":
            continue
        ztl = fixture["input"]["ztl_result"]
        assert ztl is not None, case
        assert ztl["disposition"] == "EARNED", case
        assert ztl["grade"] == "hereditary", case


def test_conditional_support_requires_non_empty_missing_grounds(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    checked = 0
    for case, fixture in fixtures.items():
        if fixture["expected"]["epistemic_status"] != "CONDITIONALLY_SUPPORTED":
            continue
        checked += 1
        assert fixture["expected"]["missing_ground_ids"], case
        assert "OIC-W-0015" in fixture["expected"]["reason_codes"], case
    assert checked >= 5


def test_conditional_support_is_never_substantive(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    for case, fixture in fixtures.items():
        if fixture["expected"]["epistemic_status"] != "CONDITIONALLY_SUPPORTED":
            continue
        assert fixture["expected"]["decision_basis"] != "SUBSTANTIVE", case


def test_conditional_allow_requires_the_full_gate(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Route B of the ALLOW gate, checked end to end on the one fixture that takes it."""
    allowing = [
        case
        for case, f in fixtures.items()
        if f["expected"]["epistemic_status"] == "CONDITIONALLY_SUPPORTED"
        and f["expected"]["execution_disposition"] == "ALLOW"
    ]
    assert allowing == ["08-on-credit-sound-allow-with-disclosure"]
    fixture = fixtures[allowing[0]]
    decision = fixture["expected"]["runtime_decision"]
    requirement = fixture["input"]["envelope"]["warrant_requirement"]

    assert decision["warrant_state"] == "USABLE"
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert decision["warranty_grade_observed"] == "sound"
    assert decision["warranty_grade_required"] == "sound"
    assert requirement["unverified_ground_policy"] == "allow_with_disclosure"
    assert decision["unverified_ground_policy_applied"] == "allow_with_disclosure"
    assert decision["missing_ground_ids"]
    assert "OIC-D-0005" in decision["reason_codes"]
    assert "OIC-W-0015" in decision["reason_codes"]
    assert decision["on_unknown_applied"] is None
    assert fixture["input"]["envelope"]["decision_mode"] == "automatic"


def test_conditional_support_never_allows_on_until_verification(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision["epistemic_status"] != "CONDITIONALLY_SUPPORTED":
            continue
        if decision["warranty_grade_observed"] != "until-verification":
            continue
        checked += 1
        assert decision["execution_disposition"] != "ALLOW", case
        assert "OIC-W-0025" in decision["reason_codes"], case
    assert checked >= 1


def test_v01_records_why_unstable_support_cannot_allow(repo_root: Path) -> None:
    """The limitation is stated, not merely implemented."""
    text = _plain(repo_root / CONTRACT_DOC)
    assert (
        "v0.1 does not model sufficient risk, reversibility, compensation, or recovery "
        "controls to permit automatic consequential ALLOW on ON CREDIT + until-verification" in text
    )


# ---------------------------------------------------------------------------
# B. unverified ground policy
# ---------------------------------------------------------------------------


def test_unverified_ground_policy_is_required_when_a_warrant_is(repo_root: Path) -> None:
    validator = _validator(repo_root, "warrant-requirement")
    base = {
        "mode": "required",
        "kernel_profile_id": "ztl-v0.1",
        "minimum_warranty_grade": "sound",
        "on_insufficient_grade": "escalate",
    }
    assert list(validator.iter_errors(base)), "unverified_ground_policy must be required"
    assert list(validator.iter_errors(dict(base, unverified_ground_policy=None)))
    for policy in ("forbid", "escalate", "allow_with_disclosure"):
        assert list(validator.iter_errors(dict(base, unverified_ground_policy=policy))) == []


def test_grade_alone_does_not_authorise_acting_on_unverified_grounds(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Same disposition, same grade, three policies, three different outcomes."""
    triples = {
        "08-on-credit-sound-allow-with-disclosure": ("allow_with_disclosure", "ALLOW"),
        "09-on-credit-sound-forbid": ("forbid", "BLOCK"),
        "10-on-credit-sound-escalate": ("escalate", "ESCALATE"),
    }
    grades = set()
    for case, (policy, execution) in triples.items():
        fixture = fixtures[case]
        assert fixture["input"]["ztl_result"]["disposition"] == "ON CREDIT", case
        assert (
            fixture["input"]["envelope"]["warrant_requirement"]["unverified_ground_policy"]
            == policy
        ), case
        assert fixture["expected"]["execution_disposition"] == execution, case
        assert fixture["expected"]["epistemic_status"] == "CONDITIONALLY_SUPPORTED", case
        grades.add(fixture["input"]["ztl_result"]["grade"])
        grades.add(fixture["input"]["envelope"]["warrant_requirement"]["minimum_warranty_grade"])
    assert grades == {"sound"}, "the grade must be identical across all three"


def test_policy_applied_is_recorded_when_it_decided(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    for case in (
        "08-on-credit-sound-allow-with-disclosure",
        "09-on-credit-sound-forbid",
        "10-on-credit-sound-escalate",
    ):
        decision = fixtures[case]["expected"]["runtime_decision"]
        assert decision["unverified_ground_policy_applied"] is not None, case
        assert (
            decision["unverified_ground_policy_applied"]
            == fixtures[case]["input"]["envelope"]["warrant_requirement"][
                "unverified_ground_policy"
            ]
        ), case


def test_contract_states_grade_is_not_authorisation(repo_root: Path) -> None:
    text = _plain(repo_root / CONTRACT_DOC)
    assert (
        "A minimum warranty grade alone is not sufficient authorisation to act on "
        "unverified grounds" in text
    )
    assert "Permission to act on conditional support is an admitted control decision" in text
    assert "not a stronger epistemic claim" in text


def test_documents_never_say_on_credit_establishes(repo_root: Path) -> None:
    """The forbidden phrasing, in any of the three documents."""
    for relpath in (CONTRACT_DOC, MAPPING_MD, ADR):
        text = _plain(repo_root / relpath).lower()
        for phrase in (
            "on credit establishes",
            "on credit establishes the proposition",
            "conditionally_supported establishes",
        ):
            assert phrase not in text, f"{relpath}: {phrase}"


def test_veip_must_preserve_conditional_status(repo_root: Path) -> None:
    text = _plain(repo_root / CONTRACT_DOC) + " " + _plain(repo_root / ADR)
    assert "must preserve" in text
    assert "the conditional status, the missing grounds, the observed grade" in text


# ---------------------------------------------------------------------------
# E. frozen kernel profile
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def profile(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / PROFILE).read_text(encoding="utf-8"))
    return document


def test_profile_declares_the_required_fields(profile: dict[str, Any]) -> None:
    for field in (
        "profile_id",
        "repository",
        "commit",
        "signed_tag",
        "entrypoint",
        "marking_alphabet",
        "raw_verdict_values",
        "disposition_values",
        "warranty_grade_values",
        "canonicalization_profile_id",
        "formula_digest_algorithm",
        "prohibited_entrypoints",
        "conformance_fixture_set",
        "known_interface_hazards",
    ):
        assert field in profile, field


def test_profile_pins_the_measured_interface(profile: dict[str, Any]) -> None:
    assert profile["profile_id"] == "ztl-v0.1"
    assert profile["entrypoint"] == "ztljudge.judge"
    assert profile["marking_alphabet"] == ["T", "F", "Z"]
    assert profile["raw_verdict_values"] == ["T", "F", "Z"]
    assert profile["commit"] == "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"
    assert profile["formula_digest_algorithm"] == "sha384"
    assert profile["canonicalization_profile_id"] == "ztl-jcs-float-free-sha384-v0.1"


def test_profile_prohibits_zverify_grade(profile: dict[str, Any]) -> None:
    """The hazard that silently upgrades a conditional result to hereditary."""
    prohibited = {entry["entrypoint"] for entry in profile["prohibited_entrypoints"]}
    assert "zverify.grade" in prohibited
    hazards = {h["hazard_id"]: h for h in profile["known_interface_hazards"]}
    hazard = hazards["ZTL-H-001"]
    assert "PARSED TERM" in hazard["summary"]
    assert "does not accept the caller's formula string" in hazard["summary"]
    assert hazard["severity"] == "critical"
    assert "ztljudge.judge" in hazard["mitigation"]


def test_profile_lists_all_four_dispositions_with_their_epistemic_mapping(
    profile: dict[str, Any],
) -> None:
    mapping = {
        entry["value"]: entry["maps_to_epistemic_status"] for entry in profile["disposition_values"]
    }
    assert mapping == {
        "EARNED": "ESTABLISHED",
        "REFUTED": "REFUTED",
        "ON CREDIT": "CONDITIONALLY_SUPPORTED",
        "OPEN": "UNRESOLVED",
    }
    earned = next(e for e in profile["disposition_values"] if e["value"] == "EARNED")
    assert earned["grades"] == ["hereditary"]
    assert earned["unverified"] == "any"
    on_credit = next(e for e in profile["disposition_values"] if e["value"] == "ON CREDIT")
    assert on_credit["unverified"] == "non-empty"
    assert "hereditary" not in on_credit["grades"]


def test_profile_records_the_not_reachable_combinations(profile: dict[str, Any]) -> None:
    combinations = {entry["combination"] for entry in profile["not_reachable_combinations"]}
    assert combinations == {
        "EARNED + sound",
        "EARNED + until-verification",
        "OPEN + raw verdict T",
    }
    for entry in profile["not_reachable_combinations"]:
        assert entry["evidence"].startswith("adapters/ztl/fixtures/")


def test_profile_marks_why_as_presentational(profile: dict[str, Any]) -> None:
    fields = {entry["field"]: entry["rule"] for entry in profile["presentational_fields"]}
    assert "Do not parse" in fields["why"]


def test_every_warrant_binds_a_declared_profile(
    fixtures: dict[str, dict[str, Any]], profile: dict[str, Any]
) -> None:
    """A warrant naming this profile must use its vocabulary; others are MISBOUND."""
    dispositions = {entry["value"] for entry in profile["disposition_values"]}
    grades = {entry["value"] for entry in profile["warranty_grade_values"]}
    checked = 0
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        if warrant["kernel_profile_id"] != profile["profile_id"]:
            # A foreign profile must not be treated as usable.
            assert fixture["expected"]["warrant_state"] == "MISBOUND", case
            continue
        checked += 1
        assert warrant["disposition"] in dispositions, case
        assert warrant["warranty_grade"] in grades, case
        assert warrant["canonicalization_profile_id"] == profile["canonicalization_profile_id"]
    assert checked >= 20


def test_profile_is_canonically_serialised(repo_root: Path) -> None:
    raw = (repo_root / PROFILE).read_text(encoding="utf-8")
    canonical = json.dumps(json.loads(raw), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw == canonical


def test_profile_does_not_execute_ztl(repo_root: Path) -> None:
    """A frozen description, not an integration."""
    profile_dir = repo_root / "docs" / "contracts" / "kernel-profiles"
    assert list(profile_dir.glob("**/*.py")) == []


# ---------------------------------------------------------------------------
# Revision 4A: measured convergence
# ---------------------------------------------------------------------------


def test_earned_may_carry_unverified_grounds(fixtures: dict[str, dict[str, Any]]) -> None:
    """The measured correction: p | q with {p:T, q:Z} is EARNED with unverified ['q'].

    A hereditary result cannot move under any refinement of those atoms, so the status is
    ESTABLISHED and the ALLOW stands -- while the grounds are still preserved.
    """
    fixture = fixtures["33-earned-hereditary-with-unverified"]
    ztl = fixture["input"]["ztl_result"]
    assert ztl["disposition"] == "EARNED"
    assert ztl["grade"] == "hereditary"
    assert ztl["raw_verdict"] == "T"
    assert ztl["unverified"] == ["q"]

    decision = fixture["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["execution_disposition"] == "ALLOW"
    assert decision["decision_basis"] == "SUBSTANTIVE"
    assert "OIC-D-0001" in decision["reason_codes"]
    assert decision["missing_ground_ids"] == ["q"], "the informational ground must survive"
    assert "OIC-W-0015" in decision["reason_codes"]
    assert decision["conditional_support_subscription_reference"] is None


def test_established_allow_does_not_require_empty_missing_grounds(
    repo_root: Path,
) -> None:
    """Mutation guard: reinstating maxItems=0 on Route A must break the measured case."""
    schema = json.loads((repo_root / PROPOSED / "runtime-decision.schema.json").read_text("utf-8"))
    route_a = schema["allOf"][0]["then"]["oneOf"][0]
    assert "missing_ground_ids" not in route_a["properties"], (
        "Route A must not constrain missing_ground_ids; 61 of 294 EARNED cases are non-empty"
    )


def test_dependency_ids_and_unverified_are_disjoint(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """D: disjoint by construction, and the unverified set is exactly the Z atoms."""
    checked = 0
    for case, fixture in fixtures.items():
        warrant = fixture["input"]["warrant_artifact"]
        if warrant is None:
            continue
        checked += 1
        dependencies = set(warrant["dependency_ids"])
        unverified = set(warrant["unverified_ground_ids"])
        assert not dependencies & unverified, f"{case}: overlap {sorted(dependencies & unverified)}"
        assert unverified == set(fixture["input"]["ztl_result"]["unverified"]), case
    assert checked >= 25


# ---------------------------------------------------------------------------
# E: conditional-support subscription
# ---------------------------------------------------------------------------

TRIGGERS = frozenset(
    {
        "ground_verified",
        "ground_expired",
        "ground_revoked",
        "ground_corrected",
        "relevant_epoch_changed",
    }
)


def test_conditional_allow_carries_a_complete_subscription(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    allowing = [
        case
        for case, f in fixtures.items()
        if f["expected"]["epistemic_status"] == "CONDITIONALLY_SUPPORTED"
        and f["expected"]["execution_disposition"] == "ALLOW"
    ]
    assert allowing == ["08-on-credit-sound-allow-with-disclosure"]
    decision = fixtures[allowing[0]]["expected"]["runtime_decision"]
    reference = decision["conditional_support_subscription_reference"]
    assert isinstance(reference, str) and reference.strip()
    assert decision["conditional_support_subscription_ground_ids"] == decision["missing_ground_ids"]
    assert set(decision["conditional_support_subscription_triggers"]) == TRIGGERS
    assert len(decision["conditional_support_subscription_triggers"]) == len(TRIGGERS)


SUBSCRIPTION_DEFECTS = (
    "34-subscription-missing-reference",
    "35-subscription-missing-ground-coverage",
    "36-subscription-missing-trigger",
    "37-subscription-ground-set-mismatch",
)


@pytest.mark.parametrize("case", SUBSCRIPTION_DEFECTS)
def test_incomplete_subscription_cannot_allow(repo_root: Path, case: str) -> None:
    decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
    assert decision["execution_disposition"] != "ALLOW", case
    assert decision["epistemic_status"] == "CONDITIONALLY_SUPPORTED", case
    assert decision["decision_basis"] == "PROCEDURAL", case
    assert "OIC-W-0027" in decision["reason_codes"], case


def test_each_subscription_defect_is_a_distinct_shape(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Four different ways to be incomplete, each actually different."""
    missing_ref = fixtures["34-subscription-missing-reference"]["expected"]["runtime_decision"]
    assert missing_ref["conditional_support_subscription_reference"] is None

    coverage = fixtures["35-subscription-missing-ground-coverage"]["expected"]["runtime_decision"]
    assert coverage["conditional_support_subscription_reference"]
    assert set(coverage["conditional_support_subscription_ground_ids"]) < set(
        coverage["missing_ground_ids"]
    ), "must be a strict subset"

    trigger = fixtures["36-subscription-missing-trigger"]["expected"]["runtime_decision"]
    assert set(trigger["conditional_support_subscription_triggers"]) < TRIGGERS
    assert "ground_revoked" not in trigger["conditional_support_subscription_triggers"]

    mismatch = fixtures["37-subscription-ground-set-mismatch"]["expected"]["runtime_decision"]
    covered = set(mismatch["conditional_support_subscription_ground_ids"])
    needed = set(mismatch["missing_ground_ids"])
    assert covered != needed
    assert covered - needed, "covers a ground that is not missing"


@pytest.mark.parametrize(
    ("label", "override"),
    [
        (
            "conditional_allow_without_subscription_reference",
            {"conditional_support_subscription_reference": None},
        ),
        (
            "conditional_allow_with_empty_subscription_reference",
            {"conditional_support_subscription_reference": ""},
        ),
        (
            "conditional_allow_missing_a_trigger",
            {
                "conditional_support_subscription_triggers": [
                    "ground_verified",
                    "ground_expired",
                    "ground_revoked",
                    "ground_corrected",
                ]
            },
        ),
        (
            "conditional_allow_with_duplicate_trigger",
            {
                "conditional_support_subscription_triggers": [
                    "ground_verified",
                    "ground_verified",
                    "ground_expired",
                    "ground_revoked",
                    "ground_corrected",
                    "relevant_epoch_changed",
                ]
            },
        ),
        (
            "conditional_allow_with_empty_subscription_grounds",
            {"conditional_support_subscription_ground_ids": []},
        ),
        (
            "subscription_on_an_established_decision",
            {
                "epistemic_status": "ESTABLISHED",
                "conditional_support_subscription_reference": "sub:x",
            },
        ),
    ],
)
def test_prohibited_subscription_shapes_are_schema_invalid(
    repo_root: Path, label: str, override: dict[str, object]
) -> None:
    decision = dict(
        _fixture(repo_root, "08-on-credit-sound-allow-with-disclosure")["expected"][
            "runtime_decision"
        ]
    )
    decision.update(override)
    errors = list(_validator(repo_root, "runtime-decision").iter_errors(decision))
    assert errors, f"{label} should be rejected by the schema"


def test_subscription_fields_are_required(repo_root: Path) -> None:
    for field in (
        "conditional_support_subscription_reference",
        "conditional_support_subscription_ground_ids",
        "conditional_support_subscription_triggers",
    ):
        decision = dict(
            _fixture(repo_root, "01-earned-hereditary-current")["expected"]["runtime_decision"]
        )
        del decision[field]
        assert list(_validator(repo_root, "runtime-decision").iter_errors(decision)), field
