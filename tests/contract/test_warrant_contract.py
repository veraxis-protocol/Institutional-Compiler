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
    "02-earned-sound-not-reachable",
    "03-earned-until-verification-not-reachable",
    "04-refuted",
    "05-open-raw-f",
    "06-open-raw-t-not-reachable",
    "07-open-raw-z",
    "08-on-credit-sound-allow-with-disclosure",
    "09-on-credit-sound-forbid",
    "10-on-credit-sound-escalate",
    "11-on-credit-sound-insufficient-grade",
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
    "23-warrant-not-required",
    "24-overlay-established-human-judgment",
    "25-overlay-established-advisory",
    "26-overlay-refuted-human-judgment",
    "27-overlay-unresolved-advisory",
    "28-overlay-conditional-support-advisory",
    "29-overlay-contradicted-human-judgment",
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
    return {row["overlay_id"]: row for row in document["control_overlays"]}


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
    return {row["overlay_id"]: row for row in mapping["control_overlays"]}


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
    assert mapping["classification_rows"]
    assert mapping["control_overlays"]
    composition = mapping["composition"]
    assert "MUST NOT rewrite epistemic_status" in composition["control_overlays"]


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


def test_markdown_contains_both_tables(repo_root: Path) -> None:
    text = (repo_root / MAPPING_MD).read_text(encoding="utf-8")
    assert "### Classification rows" in text
    assert "### Control overlays" in text
    assert "PRESERVE" in text


def test_every_classification_row_is_well_formed(rows: dict[int, dict[str, Any]]) -> None:
    assert set(rows) == set(range(1, 30))
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
    assert len(overlays) == 7
    for identifier, overlay in overlays.items():
        assert overlay["epistemic_effect"] == "PRESERVE", identifier
        assert "epistemic_status" not in overlay, identifier
        assert overlay["decision_basis"] == "CONTROL_REQUIREMENT", identifier
        assert overlay["policy_reason_code"] in CONTROL_POLICY_CODES, identifier
        assert overlay["execution_disposition"] in {"ALLOW", "BLOCK", "ESCALATE", "ADVISORY"}


def test_only_one_overlay_can_allow(overlays: dict[str, dict[str, Any]]) -> None:
    allowing = [k for k, v in overlays.items() if v["execution_disposition"] == "ALLOW"]
    assert allowing == ["O-5"]
    assert overlays["O-5"]["policy_reason_code"] == "OIC-D-0005"
    assert "allow_with_disclosure" in overlays["O-5"]["trigger"]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_matches_its_classification_row(repo_root: Path, case: str) -> None:
    fixture = _fixture(repo_root, case)
    row = _rows(repo_root)[fixture["classification_row"]]
    expected = fixture["expected"]

    # The classification always fixes the epistemic status and the warrant state.
    assert expected["epistemic_status"] == row["epistemic_status"], case
    assert expected["warrant_state"] == row["warrant_state"], case
    assert fixture["reachability"] == row["reachability"], case

    overlay_id = fixture["control_overlay"]
    if overlay_id is None:
        # No overlay: the row's own basis, execution, and reason apply.
        assert expected["decision_basis"] == row["decision_basis"], case
        assert expected["execution_disposition"] in row["base_execution_choices"], case
        assert row["primary_reason_code"] in expected["reason_codes"], case
    else:
        overlay = _overlays(repo_root)[overlay_id]
        assert expected["execution_disposition"] == overlay["execution_disposition"], case
        assert expected["decision_basis"] == overlay["decision_basis"], case
        assert overlay["policy_reason_code"] in expected["reason_codes"], case


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_overlay_never_changes_the_row_epistemic_status(repo_root: Path, case: str) -> None:
    """Applying an overlay must leave the classification's epistemic status untouched."""
    fixture = _fixture(repo_root, case)
    if fixture["control_overlay"] is None:
        return
    row = _rows(repo_root)[fixture["classification_row"]]
    assert fixture["expected"]["epistemic_status"] == row["epistemic_status"], case


def test_overlays_cover_every_epistemic_status(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """An overlay must be demonstrated over each status, not only the convenient one."""
    covered = {
        f["expected"]["epistemic_status"]
        for f in fixtures.values()
        if f["control_overlay"] in {"O-1", "O-2"}
    }
    assert covered == EPISTEMIC, sorted(EPISTEMIC - covered)


def test_measured_rows_reflect_the_ztl_evidence(rows: dict[int, dict[str, Any]]) -> None:
    for number in (24, 28, 29):
        assert rows[number]["reachability"] == "NOT_REACHABLE", number
        assert rows[number]["authority"] == "ZTL-CONFIRMED", number
    assert not [n for n, r in rows.items() if r["authority"] == "PENDING-ZTL"]


def test_on_credit_rows_are_conditionally_supported(rows: dict[int, dict[str, Any]]) -> None:
    on_credit = {n: r for n, r in rows.items() if r["disposition"] == "ON CREDIT"}
    assert set(on_credit) == {26, 27}
    for number, row in on_credit.items():
        assert row["authority"] == "MEASURED", number
        assert row["epistemic_status"] == "CONDITIONALLY_SUPPORTED", number
        assert row["unverified"] == "non-empty", number
    # Only the `sound` row may ever reach ALLOW, and only via an overlay.
    assert "ALLOW" in rows[26]["base_execution_choices"]
    assert "ALLOW" not in rows[27]["base_execution_choices"]
    assert rows[27]["primary_reason_code"] == "OIC-W-0025"
    assert rows[27]["decision_basis"] == "PRECAUTIONARY"


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
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        observed, required = (
            decision["warranty_grade_observed"],
            decision["warranty_grade_required"],
        )
        if observed is None or required is None:
            continue
        if GRADE_ORDER[observed] >= GRADE_ORDER[required]:
            continue
        # An insufficient grade can never permit the action, whatever else is true.
        assert decision["execution_disposition"] != "ALLOW", case
        # The grade gate only decides the outcome once the claim is ESTABLISHED and the
        # warrant is usable. An UNRESOLVED result is already blocked for its own reason.
        if decision["epistemic_status"] not in {"ESTABLISHED", "CONDITIONALLY_SUPPORTED"}:
            continue
        if decision["warrant_state"] != "USABLE":
            continue
        # A classification whose own basis already decides -- ON CREDIT +
        # until-verification is PRECAUTIONARY because the result is unstable, not because
        # the grade fell short -- is not the grade gate's case.
        if fixture["control_overlay"] not in {"O-3", "O-4"}:
            continue
        checked += 1
        assert decision["decision_basis"] == "CONTROL_REQUIREMENT", case
        assert "OIC-W-0016" in decision["reason_codes"], case
    assert checked >= 1


def test_human_judgment_escalates_a_perfect_warrant(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    fixture = fixtures["24-overlay-established-human-judgment"]
    assert fixture["input"]["envelope"]["decision_mode"] == "human_judgment"
    decision = fixture["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["execution_disposition"] == "ESCALATE"
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert "OIC-D-0002" in decision["reason_codes"]
    assert decision["warranty_grade_observed"] == "hereditary"


def test_advisory_records_without_gating(fixtures: dict[str, dict[str, Any]]) -> None:
    decision = fixtures["25-overlay-established-advisory"]["expected"]["runtime_decision"]
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
    fixture = _fixture(repo_root, "23-warrant-not-required")
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
    assert rows[7]["primary_reason_code"] == "OIC-W-0021"


def test_unsupported_result_combination_code_is_used(
    fixtures: dict[str, dict[str, Any]], rows: dict[int, dict[str, Any]]
) -> None:
    """Row 31 must NOT be labelled DISPOSITION_OPEN: its disposition is not OPEN."""
    assert rows[29]["disposition"] == "EARNED"
    assert rows[29]["primary_reason_code"] == "OIC-W-0022"
    assert rows[29]["decision_basis"] == "PROCEDURAL"
    fixture = fixtures["03-earned-until-verification-not-reachable"]
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
        declared = registry[overlay["policy_reason_code"]]
        assert declared == "CONTROL_REQUIREMENT", f"overlay {identifier}: registry says {declared}"

    for case, fixture in fixtures.items():
        if fixture["control_overlay"] is not None:
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


def test_no_ztl_or_veip_code_exists_or_is_imported(repo_root: Path) -> None:
    for module in sorted((repo_root / "src" / "oic").glob("*.py")):
        text = module.read_text(encoding="utf-8").lower()
        for forbidden in ("import ztl", "from ztl", "import veip", "from veip"):
            assert forbidden not in text, f"{module.name}: {forbidden}"
    for directory in ("ztl", "veip"):
        assert list((repo_root / "adapters" / directory).glob("**/*.py")) == []


def test_this_work_order_added_no_source_module(repo_root: Path) -> None:
    modules = {path.name for path in (repo_root / "src" / "oic").glob("*.py")}
    assert modules == {
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
    assert profile["commit"] == "e819dec7e89d2dc67d6371e1eedb8e7aae854602"
    assert profile["formula_digest_algorithm"] == "sha384"
    assert profile["canonicalization_profile_id"] == "ztl-jcs-float-free-sha384-v0.1"


def test_profile_prohibits_zverify_grade(profile: dict[str, Any]) -> None:
    """The hazard that silently upgrades a conditional result to hereditary."""
    prohibited = {entry["entrypoint"] for entry in profile["prohibited_entrypoints"]}
    assert "zverify.grade" in prohibited
    hazards = {h["hazard_id"]: h for h in profile["known_interface_hazards"]}
    hazard = hazards["ZTL-H-001"]
    assert "expects 'M' for a mark" in hazard["summary"]
    assert "SILENTLY" in hazard["summary"]
    assert hazard["severity"] == "critical"
    assert "judge()" in hazard["mitigation"]


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
    assert earned["unverified"] == "empty"
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
