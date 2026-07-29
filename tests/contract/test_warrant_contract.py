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
    "02-earned-sound-permitted-grade",
    "03-earned-sound-insufficient-grade",
    "04-earned-until-verification",
    "05-refuted",
    "06-open-raw-f",
    "07-open-raw-t",
    "08-open-raw-z",
    "09-on-credit-sound-permitted",
    "10-kernel-unavailable",
    "11-warrant-stale",
    "12-ground-expired",
    "13-ground-revoked",
    "14-epoch-mismatch",
    "15-contradiction",
    "16-source-version-mismatch",
    "17-admission-version-mismatch",
    "18-warrant-not-yet-valid",
    "19-on-credit-sound-insufficient-grade",
    "20-on-credit-until-verification",
    "21-decision-mode-human-judgment",
    "22-decision-mode-advisory",
    "23-profile-mismatch",
    "24-warrant-not-required",
)

#: The only reason codes that may accompany a SUBSTANTIVE *block*.
SUBSTANTIVE_BLOCK_CODES = {"OIC-W-0013", "OIC-W-0014"}
#: The substantive positive-decision code.
SUBSTANTIVE_ALLOW_CODE = "OIC-D-0001"
#: A CONTROL_REQUIREMENT decision must carry one of these.
CONTROL_POLICY_CODES = {"OIC-W-0016", "OIC-D-0002", "OIC-D-0003"}

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
    """Canonical mapping rows by id, for parametrised tests with Any-free signatures."""
    document = json.loads((repo_root / MAPPING_JSON).read_text(encoding="utf-8"))
    return {int(row["row_id"]): row for row in document["rows"]}


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
    return {int(row["row_id"]): row for row in mapping["rows"]}


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
    assert set(mapping["authority_values"]) == {
        "MEASURED",
        "ZTL-CONFIRMED",
        "OIC-DEFENSIVE",
        "PENDING-ZTL",
    }


def test_markdown_table_is_generated_from_the_json(repo_root: Path) -> None:
    """Re-render in memory and compare. The Markdown may not be hand-edited."""
    sys.path.insert(0, str(repo_root))
    try:
        from tools.render_mapping import rendered_markdown
    finally:
        sys.path.pop(0)
    expected = rendered_markdown(repo_root)
    actual = (repo_root / MAPPING_MD).read_text(encoding="utf-8")
    assert actual == expected, "run tools/render_mapping.py"


def test_every_row_is_well_formed(rows: dict[int, dict[str, Any]]) -> None:
    assert set(rows) == set(range(1, 34))
    for number, row in rows.items():
        assert row["epistemic_status"] in {
            "ESTABLISHED",
            "REFUTED",
            "UNRESOLVED",
            "CONTRADICTED",
        }, number
        assert row["decision_basis"] in {
            "SUBSTANTIVE",
            "PRECAUTIONARY",
            "PROCEDURAL",
            "CONTROL_REQUIREMENT",
        }, number
        assert row["reachability"] in {"REACHABLE", "NOT_REACHABLE"}, number
        assert row["authority"] in {
            "MEASURED",
            "ZTL-CONFIRMED",
            "OIC-DEFENSIVE",
            "PENDING-ZTL",
        }, number
        assert set(row["execution_disposition_choices"]) <= {
            "ALLOW",
            "BLOCK",
            "ESCALATE",
            "ADVISORY",
        }, number
        assert re.fullmatch(r"OIC-[WD]-[0-9]{4}", row["primary_reason_code"]), number
        assert 1 <= int(row["precedence"]) <= 6, number


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_matches_its_mapping_row(repo_root: Path, case: str) -> None:
    fixture = _fixture(repo_root, case)
    row = _rows(repo_root)[fixture["mapping_row"]]
    expected = fixture["expected"]
    assert expected["epistemic_status"] == row["epistemic_status"], case
    assert expected["decision_basis"] == row["decision_basis"], case
    assert expected["execution_disposition"] in row["execution_disposition_choices"], case
    assert row["primary_reason_code"] in expected["reason_codes"], case
    assert fixture["reachability"] == row["reachability"], case


def test_measured_rows_reflect_the_ztl_evidence(rows: dict[int, dict[str, Any]]) -> None:
    """The three previously-uncertain rows are now measured NOT_REACHABLE."""
    for number in (24, 29, 30, 31):
        assert rows[number]["reachability"] == "NOT_REACHABLE", number
        assert rows[number]["authority"] == "ZTL-CONFIRMED", number
    assert not [n for n, r in rows.items() if r["authority"] == "PENDING-ZTL"]


def test_on_credit_rows_exist_and_are_measured(rows: dict[int, dict[str, Any]]) -> None:
    """ON CREDIT was missing from the dossier's three-value list."""
    on_credit = {n: r for n, r in rows.items() if r["disposition"] == "ON CREDIT"}
    assert set(on_credit) == {26, 27, 28}
    for row in on_credit.values():
        assert row["authority"] == "MEASURED"
        assert row["grade"] in {"sound", "until-verification"}
        assert row["unverified"] == "non-empty"


def test_earned_rows_never_claim_non_hereditary_reachability(
    rows: dict[int, dict[str, Any]],
) -> None:
    for number, row in rows.items():
        if row["disposition"] == "EARNED" and row["grade"] != "hereditary":
            assert row["reachability"] == "NOT_REACHABLE", number


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
    precautionary = fixtures["06-open-raw-f"]["expected"]
    substantive = fixtures["05-refuted"]["expected"]
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
    fixture = fixtures["15-contradiction"]
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
    fixture = fixtures["09-on-credit-sound-permitted"]
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
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """A control-mandated escalation is neither PROCEDURAL nor epistemic doubt."""
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision["decision_basis"] != "CONTROL_REQUIREMENT":
            continue
        checked += 1
        assert decision["epistemic_status"] == "ESTABLISHED", (
            f"{case}: CONTROL_REQUIREMENT must not rewrite the epistemic status"
        )
        assert decision["warrant_state"] == "USABLE", (
            f"{case}: the warrant remains valid; only the control declined"
        )
        assert decision["execution_disposition"] != "ALLOW", case
        assert set(decision["reason_codes"]) & CONTROL_POLICY_CODES, case
    assert checked >= 5


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
        if decision["epistemic_status"] != "ESTABLISHED":
            continue
        if decision["warrant_state"] != "USABLE":
            continue
        checked += 1
        assert decision["decision_basis"] == "CONTROL_REQUIREMENT", case
        assert "OIC-W-0016" in decision["reason_codes"], case
    assert checked >= 3


def test_human_judgment_escalates_a_perfect_warrant(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    fixture = fixtures["21-decision-mode-human-judgment"]
    assert fixture["input"]["envelope"]["decision_mode"] == "human_judgment"
    decision = fixture["expected"]["runtime_decision"]
    assert decision["epistemic_status"] == "ESTABLISHED"
    assert decision["execution_disposition"] == "ESCALATE"
    assert decision["decision_basis"] == "CONTROL_REQUIREMENT"
    assert "OIC-D-0002" in decision["reason_codes"]
    assert decision["warranty_grade_observed"] == "hereditary"


def test_advisory_records_without_gating(fixtures: dict[str, dict[str, Any]]) -> None:
    decision = fixtures["22-decision-mode-advisory"]["expected"]["runtime_decision"]
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
                    }
                )
            )
            == []
        )

    for field in ("kernel_profile_id", "minimum_warranty_grade", "on_insufficient_grade"):
        bad = dict(valid_required, **{field: None})
        assert list(validator.iter_errors(bad)), f"required/{field}=None should be invalid"

    for field, value in (
        ("kernel_profile_id", "ztl-v0.1"),
        ("minimum_warranty_grade", "sound"),
        ("on_insufficient_grade", "block"),
    ):
        bad = {
            "mode": "not_required",
            "kernel_profile_id": None,
            "minimum_warranty_grade": None,
            "on_insufficient_grade": None,
            field: value,
        }
        assert list(validator.iter_errors(bad)), f"not_required/{field} set should be invalid"

    assert list(validator.iter_errors({"kernel_profile_id": None})), "no default mode allowed"


def test_not_required_never_waives_other_checks(repo_root: Path) -> None:
    text = (repo_root / PROPOSED / "warrant-requirement.schema.json").read_text("utf-8")
    assert "NOT permission to skip authority, admission, evidence, or version checks" in text
    fixture = _fixture(repo_root, "24-warrant-not-required")
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
        "refuted_escalates",
        {
            "epistemic_status": "REFUTED",
            "execution_disposition": "ESCALATE",
            "decision_basis": "SUBSTANTIVE",
        },
    ),
    (
        "refuted_precautionary",
        {
            "epistemic_status": "REFUTED",
            "execution_disposition": "BLOCK",
            "decision_basis": "PRECAUTIONARY",
        },
    ),
    (
        "contradicted_escalates",
        {
            "epistemic_status": "CONTRADICTED",
            "execution_disposition": "ESCALATE",
            "decision_basis": "SUBSTANTIVE",
        },
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
    fixture = fixtures["14-epoch-mismatch"]
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

    mismatch = fixtures["23-profile-mismatch"]
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
    fixture = fixtures["18-warrant-not-yet-valid"]
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
    assert rows[31]["disposition"] == "EARNED"
    assert rows[31]["primary_reason_code"] == "OIC-W-0022"
    assert rows[31]["decision_basis"] == "PROCEDURAL"
    fixture = fixtures["04-earned-until-verification"]
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
    assert len(registry) >= 28
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

    for case, fixture in fixtures.items():
        row = rows[fixture["mapping_row"]]
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
