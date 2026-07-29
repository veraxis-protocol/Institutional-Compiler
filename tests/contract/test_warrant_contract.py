"""Contract tests for the proposed warrant and failure-semantics contract (OIC-WO-002).

What these prove, and what they do not
--------------------------------------
No adapter exists, so these cannot prove an implementation is correct. They prove the
fixtures are schema-valid, internally consistent, and consistent with the published
mapping table in ``docs/contracts/ZTL-OCE-MAPPING-v0.1.md`` — which is parsed here rather
than duplicated, so the document is the single source of truth.

That makes the contract executable instead of prose: a fixture that quietly records
``REFUTED`` for an ``OPEN`` disposition fails the build. When an adapter is eventually
authorised, the same fixtures become its acceptance suite.

Nothing here imports, calls, or simulates ZTL or VEIP.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator

pytestmark = pytest.mark.contract

FIXTURE_DIR = "tests/fixtures/warrant-contract"
MAPPING_DOC = "docs/contracts/ZTL-OCE-MAPPING-v0.1.md"
CONTRACT_DOC = "docs/contracts/WARRANT-CONTRACT-v0.1.md"
PROPOSED_SCHEMA_DIR = "schemas/proposed"

EXPECTED_CASES = (
    "01-earned-hereditary-current",
    "02-earned-sound-permitted-grade",
    "03-earned-sound-insufficient-grade",
    "04-earned-until-verification",
    "05-refuted",
    "06-open-raw-f",
    "07-open-raw-t",
    "08-open-raw-z",
    "09-unverified-ground",
    "10-kernel-unavailable",
    "11-warrant-stale",
    "12-ground-expired",
    "13-ground-revoked",
    "14-epoch-mismatch",
    "15-contradiction",
    "16-source-version-mismatch",
    "17-admission-version-mismatch",
)

#: Only these two reason codes may ever carry a SUBSTANTIVE basis.
SUBSTANTIVE_CODES = {"OIC-W-0013", "OIC-W-0014"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


_FIXTURE_CACHE: dict[str, Any] = {}


def _fixture(repo_root: Path, case: str) -> Any:  # noqa: ANN401 - JSON is dynamic
    """Load one fixture.

    A helper rather than a pytest fixture argument so that parametrised tests keep an
    ``Any``-free signature; mypy's ``disallow_any_decorated`` rejects a decorated function
    whose signature contains ``Any``, and JSON fixture documents are legitimately dynamic
    once inside.
    """
    if case not in _FIXTURE_CACHE:
        path = repo_root / FIXTURE_DIR / f"{case}.json"
        _FIXTURE_CACHE[case] = json.loads(path.read_text(encoding="utf-8"))
    return _FIXTURE_CACHE[case]


def _validator_for(repo_root: Path, name: str) -> Draft202012Validator:
    schema = json.loads(
        (repo_root / PROPOSED_SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def fixtures(repo_root: Path) -> dict[str, dict[str, Any]]:
    directory = repo_root / FIXTURE_DIR
    loaded = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }
    assert loaded, "no fixtures found"
    return loaded


@pytest.fixture(scope="module")
def mapping_rows(repo_root: Path) -> dict[int, dict[str, str]]:
    """Parse the published mapping table. The document is the source of truth."""
    text = (repo_root / MAPPING_DOC).read_text(encoding="utf-8")
    body = text.split("<!-- MAPPING-TABLE-START -->")[1].split("<!-- MAPPING-TABLE-END -->")[0]
    rows: dict[int, dict[str, str]] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or not cells[0].isdigit():
            continue
        rows[int(cells[0])] = {
            "disposition": cells[1],
            "grade": cells[2],
            "unverified": cells[3],
            "condition": cells[4],
            "epistemic": cells[5],
            "execution": cells[6],
            "basis": cells[7],
            "primary_reason": cells[8],
            "reachable": cells[9],
        }
    assert rows, "mapping table did not parse"
    return rows


# ---------------------------------------------------------------------------
# Schemas validate offline
# ---------------------------------------------------------------------------


def test_proposed_schemas_validate_as_draft_2020_12(repo_root: Path) -> None:
    from oic.schemas import SchemaStatus, validate_schema_directory

    report = validate_schema_directory(repo_root / PROPOSED_SCHEMA_DIR, root=repo_root)
    failures = [issue.render() for issue in report.issues]
    assert failures == []
    assert report.status is SchemaStatus.PASS
    assert len(report.results) == 2


def test_proposed_schemas_need_no_remote_resolution(repo_root: Path) -> None:
    """The suite runs with sockets disabled, so passing also proves no fetch occurred."""
    from oic.schemas import SchemaStatus, validate_schema_directory

    report = validate_schema_directory(
        repo_root / PROPOSED_SCHEMA_DIR, root=repo_root, allow_external_refs=False
    )
    assert report.status is SchemaStatus.PASS


# ---------------------------------------------------------------------------
# Fixtures are present and valid
# ---------------------------------------------------------------------------


def test_every_expected_case_is_present(fixtures: dict[str, dict[str, Any]]) -> None:
    assert tuple(sorted(fixtures)) == EXPECTED_CASES


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_warrant_artifact_validates(repo_root: Path, case: str) -> None:
    warrant = _fixture(repo_root, case)["input"]["warrant_artifact"]
    if warrant is None:
        return
    validator = _validator_for(repo_root, "warrant-artifact")
    errors = sorted(validator.iter_errors(warrant), key=str)
    assert errors == [], [error.message for error in errors]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_runtime_decision_validates(repo_root: Path, case: str) -> None:
    decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
    validator = _validator_for(repo_root, "runtime-decision")
    errors = sorted(validator.iter_errors(decision), key=str)
    assert errors == [], [error.message for error in errors]


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_expected_block_agrees_with_its_runtime_decision(repo_root: Path, case: str) -> None:
    """The summary fields and the full decision instance must not drift apart."""
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
# Consistency with the published mapping table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_matches_its_mapping_row(
    repo_root: Path, mapping_rows: dict[int, dict[str, str]], case: str
) -> None:
    fixture = _fixture(repo_root, case)
    row = mapping_rows[fixture["mapping_row"]]
    expected = fixture["expected"]

    assert expected["epistemic_status"] == row["epistemic"], case
    assert expected["decision_basis"] == row["basis"], case
    allowed = {value.strip() for value in row["execution"].split("/")}
    assert expected["execution_disposition"] in allowed, case
    assert row["primary_reason"] in expected["reason_codes"], case


def test_every_mapping_row_is_reachable_in_the_table(
    mapping_rows: dict[int, dict[str, str]],
) -> None:
    assert set(mapping_rows) == set(range(1, 26))


def test_rows_needing_ztl_confirmation_are_marked(
    mapping_rows: dict[int, dict[str, str]],
) -> None:
    """Rows we inferred rather than measured must be flagged, not presented as fact."""
    unconfirmed = {number for number, row in mapping_rows.items() if row["reachable"] == "?"}
    assert unconfirmed == {2, 5, 7}


# ---------------------------------------------------------------------------
# The load-bearing invariants
# ---------------------------------------------------------------------------


def test_open_never_becomes_refuted(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-1. Derived from the INPUT, so a wrong expectation cannot hide."""
    checked = 0
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "OPEN":
            continue
        checked += 1
        status = fixture["expected"]["epistemic_status"]
        assert status == "UNRESOLVED", f"{case}: OPEN mapped to {status}"
        assert status != "REFUTED", case
    assert checked >= 3, "expected OPEN fixtures for raw T, F and Z"


def test_open_never_becomes_a_substantive_refusal(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """An OPEN disposition may block, but never as a finding about the grounds."""
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None or ztl.get("disposition") != "OPEN":
            continue
        assert fixture["expected"]["decision_basis"] != "SUBSTANTIVE", case


def test_raw_verdict_never_drives_the_outcome(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-2. The measured trap: raw F under OPEN must not become REFUTED.

    Also checks the converse: a raw T under OPEN must not become ESTABLISHED.
    """
    raw_f_open = [
        case
        for case, fixture in fixtures.items()
        if (ztl := fixture["input"]["ztl_result"])
        and ztl.get("disposition") == "OPEN"
        and ztl.get("raw_verdict") == "F"
    ]
    assert raw_f_open, "the measured case is not covered by any fixture"
    for case in raw_f_open:
        assert fixtures[case]["expected"]["epistemic_status"] == "UNRESOLVED", case

    raw_t_open = [
        case
        for case, fixture in fixtures.items()
        if (ztl := fixture["input"]["ztl_result"])
        and ztl.get("disposition") == "OPEN"
        and ztl.get("raw_verdict") == "T"
    ]
    for case in raw_t_open:
        assert fixtures[case]["expected"]["epistemic_status"] != "ESTABLISHED", case


def test_precautionary_block_stays_distinguishable_from_substantive_refusal(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """W-3. Two BLOCKs, two different meanings, two different records."""
    precautionary = fixtures["06-open-raw-f"]["expected"]
    substantive = fixtures["05-refuted"]["expected"]

    assert precautionary["execution_disposition"] == substantive["execution_disposition"]
    # Same execution, and yet no consumer can confuse them:
    assert precautionary["epistemic_status"] != substantive["epistemic_status"]
    assert precautionary["decision_basis"] != substantive["decision_basis"]
    assert precautionary["decision_basis"] == "PRECAUTIONARY"
    assert substantive["decision_basis"] == "SUBSTANTIVE"


def test_only_refutation_and_contradiction_are_substantive(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    for case, fixture in fixtures.items():
        expected = fixture["expected"]
        if expected["decision_basis"] != "SUBSTANTIVE":
            continue
        if expected["execution_disposition"] == "ALLOW":
            continue
        assert set(expected["reason_codes"]) & SUBSTANTIVE_CODES, (
            f"{case}: SUBSTANTIVE block without a substantive reason code"
        )
        assert expected["epistemic_status"] in {"REFUTED", "CONTRADICTED"}, case


def test_on_unknown_deny_is_never_substantive(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-6. `deny` is an operational fail-closed block, not a finding."""
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision.get("on_unknown_applied") != "deny":
            continue
        checked += 1
        assert decision["decision_basis"] in {"PRECAUTIONARY", "PROCEDURAL"}, case
        assert decision["epistemic_status"] != "REFUTED", case
    assert checked >= 1


def test_contradiction_is_never_refutation(fixtures: dict[str, dict[str, Any]]) -> None:
    contradiction = fixtures["15-contradiction"]
    assert contradiction["input"]["runtime_context"]["contradiction_detected"] is True
    assert contradiction["expected"]["epistemic_status"] == "CONTRADICTED"
    # The kernel disposition was REFUTED; the contradiction takes precedence and is a
    # statement about the grounds, not about the claim.
    assert contradiction["input"]["ztl_result"]["disposition"] == "REFUTED"


def test_missing_grounds_are_never_dropped(fixtures: dict[str, dict[str, Any]]) -> None:
    """W-5. Including on ALLOW."""
    checked = 0
    for case, fixture in fixtures.items():
        ztl = fixture["input"]["ztl_result"]
        if ztl is None:
            continue
        unverified = ztl.get("unverified") or []
        if not unverified:
            continue
        checked += 1
        assert fixture["expected"]["missing_ground_ids"] == list(unverified), case
    assert checked >= 4


def test_missing_grounds_survive_an_allow(fixtures: dict[str, dict[str, Any]]) -> None:
    allow_with_missing = fixtures["09-unverified-ground"]
    assert allow_with_missing["expected"]["execution_disposition"] == "ALLOW"
    assert allow_with_missing["expected"]["missing_ground_ids"] != []
    assert "OIC-W-0015" in allow_with_missing["expected"]["reason_codes"]


def test_missing_ground_anchors_are_the_enrichment_level(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    """Level 2 anchors carry source and admission context the kernel never produces."""
    enriched = [
        fixture for fixture in fixtures.values() if fixture["expected"]["missing_ground_anchors"]
    ]
    assert enriched, "no fixture demonstrates level-2 enrichment"
    for fixture in enriched:
        for anchor in fixture["expected"]["missing_ground_anchors"]:
            assert anchor["ground_id"]
            assert anchor["source_id"], "an enriched anchor must reach the source"
            assert anchor["admitted_unit_id"], "and the admitted unit"
        recorded = {a["ground_id"] for a in fixture["expected"]["missing_ground_anchors"]}
        assert recorded <= set(fixture["expected"]["missing_ground_ids"])


# ---------------------------------------------------------------------------
# Nothing unusable may reach ALLOW
# ---------------------------------------------------------------------------


def test_only_established_may_allow(fixtures: dict[str, dict[str, Any]]) -> None:
    for case, fixture in fixtures.items():
        expected = fixture["expected"]
        if expected["execution_disposition"] == "ALLOW":
            assert expected["epistemic_status"] == "ESTABLISHED", case


def test_stale_expired_or_revoked_can_never_allow(
    fixtures: dict[str, dict[str, Any]],
) -> None:
    blocked_states = {"STALE", "EXPIRED", "NOT_YET_VALID", "REVOKED", "MISBOUND"}
    checked = 0
    for case, fixture in fixtures.items():
        expected = fixture["expected"]
        if expected["warrant_state"] not in blocked_states:
            continue
        checked += 1
        assert expected["execution_disposition"] != "ALLOW", case
        assert expected["epistemic_status"] == "UNRESOLVED", case
    assert checked >= 6


def test_insufficient_grade_can_never_allow(fixtures: dict[str, dict[str, Any]]) -> None:
    order = {"until-verification": 0, "sound": 1, "hereditary": 2}
    checked = 0
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        observed, required = (
            decision.get("warranty_grade_observed"),
            decision.get("warranty_grade_required"),
        )
        if observed is None or required is None:
            continue
        if order[observed] >= order[required]:
            continue
        checked += 1
        assert decision["execution_disposition"] != "ALLOW", case
    assert checked >= 1


def test_kernel_failure_can_never_allow(fixtures: dict[str, dict[str, Any]]) -> None:
    checked = 0
    for case, fixture in fixtures.items():
        if fixture["input"]["runtime_context"].get("kernel_available") is not False:
            continue
        checked += 1
        expected = fixture["expected"]
        assert expected["execution_disposition"] != "ALLOW", case
        assert expected["decision_basis"] == "PROCEDURAL", case
        assert expected["runtime_decision"]["warrant_artifact_id"] is None, case
        assert "OIC-W-0002" in expected["reason_codes"], case
    assert checked == 1


def test_allow_always_carries_a_warrant(fixtures: dict[str, dict[str, Any]]) -> None:
    for case, fixture in fixtures.items():
        decision = fixture["expected"]["runtime_decision"]
        if decision["execution_disposition"] != "ALLOW":
            continue
        assert decision["warrant_artifact_id"] is not None, case
        assert decision["warrant_state"] == "USABLE", case


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_fixture_files_are_canonically_serialised(repo_root: Path, case: str) -> None:
    """Byte-for-byte stable: sorted keys, two-space indent, trailing newline."""
    path = repo_root / FIXTURE_DIR / f"{case}.json"
    raw = path.read_text(encoding="utf-8")
    canonical = json.dumps(json.loads(raw), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw == canonical, f"{case}.json is not canonically serialised"


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_reason_codes_are_sorted_and_wellformed(repo_root: Path, case: str) -> None:
    codes = _fixture(repo_root, case)["expected"]["reason_codes"]
    assert codes, case
    assert codes == sorted(codes), case
    assert len(codes) == len(set(codes)), case
    for code in codes:
        assert re.fullmatch(r"OIC-[WD]-[0-9]{4}", code), code


@pytest.mark.parametrize("case", EXPECTED_CASES)
def test_digests_are_wellformed(repo_root: Path, case: str) -> None:
    sha256 = re.compile(r"^sha256:[0-9a-f]{64}$")
    sha384 = re.compile(r"^sha384:[0-9a-f]{96}$")
    warrant = _fixture(repo_root, case)["input"]["warrant_artifact"]
    if warrant is not None:
        for field in ("ground_set_hash", "input_hash", "output_hash"):
            assert sha256.fullmatch(warrant[field]), f"{case}.{field}"
        assert sha384.fullmatch(warrant["formula_hash"]), f"{case}.formula_hash"
        assert re.fullmatch(r"[0-9a-f]{40}", warrant["kernel_commit"])
    decision = _fixture(repo_root, case)["expected"]["runtime_decision"]
    for field in ("source_version_set_hash", "input_hash"):
        assert sha256.fullmatch(decision[field]), f"{case}.{field}"


def test_every_reason_code_used_is_in_the_registry(
    repo_root: Path, fixtures: dict[str, dict[str, Any]]
) -> None:
    registry = set(
        re.findall(r"`(OIC-[WD]-[0-9]{4})`", (repo_root / CONTRACT_DOC).read_text("utf-8"))
    )
    used = {code for f in fixtures.values() for code in f["expected"]["reason_codes"]}
    assert used <= registry, f"codes not in the registry: {sorted(used - registry)}"


# ---------------------------------------------------------------------------
# Boundary discipline
# ---------------------------------------------------------------------------


def test_no_ztl_or_veip_code_exists_or_is_imported(repo_root: Path) -> None:
    """No adapter, no client, no import. The gate is BLOCKED."""
    for module in sorted((repo_root / "src" / "oic").glob("*.py")):
        text = module.read_text(encoding="utf-8").lower()
        for forbidden in ("import ztl", "from ztl", "import veip", "from veip"):
            assert forbidden not in text, f"{module.name}: {forbidden}"
    adapters = repo_root / "adapters"
    for directory in ("ztl", "veip"):
        python_files = list((adapters / directory).glob("**/*.py"))
        assert python_files == [], f"adapters/{directory} contains executable code"


def test_this_work_order_added_no_source_module(repo_root: Path) -> None:
    """OIC-WO-002 is architecture, schemas and fixtures only."""
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
    """schemas/draft is Class B and out of scope for this work order."""
    import subprocess

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
    import subprocess

    from oic.baseline import BOOTSTRAP_COMMIT

    committed = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "blob", f"{BOOTSTRAP_COMMIT}:STATUS.md"],
        capture_output=True,
        check=True,
    ).stdout
    assert (repo_root / "STATUS.md").read_bytes() == committed


def test_proposed_schemas_are_not_in_the_draft_directory(repo_root: Path) -> None:
    draft = {path.name for path in (repo_root / "schemas" / "draft").glob("*.json")}
    proposed = {path.name for path in (repo_root / PROPOSED_SCHEMA_DIR).glob("*.json")}
    assert draft.isdisjoint(proposed)
    assert len(draft) == 9


def test_documents_state_the_gate_is_blocked(repo_root: Path) -> None:
    for relpath in (CONTRACT_DOC, MAPPING_DOC, "adr/ADR-013.md"):
        text = " ".join((repo_root / relpath).read_text("utf-8").replace("*", "").split())
        assert "semantic implementation gate remains BLOCKED" in text, relpath


def test_documents_label_themselves_proposed(repo_root: Path) -> None:
    for relpath in (CONTRACT_DOC, MAPPING_DOC):
        head = (repo_root / relpath).read_text("utf-8")[:400].replace("*", "")
        assert "PROPOSED" in head, relpath
        assert "Not admitted" in head, relpath
