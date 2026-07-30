"""Executable consistency checks between the governing documents and the artifacts.

Why this file exists
--------------------
Through revisions 2 and 3 the schemas and the canonical mapping advanced while ADR-013 and
WARRANT-CONTRACT kept superseded semantics. Every test passed. The prose said `ON CREDIT`
maps to `ESTABLISHED` long after the schema forbade it, because nothing compared the two.

These tests close that gap. They read the **active normative sections** of each document —
text outside the ``<!-- HISTORICAL-START -->`` / ``<!-- HISTORICAL-END -->`` markers — and
check it against the schemas, the canonical mapping, and the reason-code registry.

The markers matter. Historical correction sections deliberately quote superseded language
in order to correct it, and a naive grep over whole files would either fail on those
quotations or force the corrections to be deleted. Deleting them would destroy the record
this project keeps on purpose.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.contract

ADR = "adr/ADR-013.md"
CONTRACT = "docs/contracts/WARRANT-CONTRACT-v0.1.md"
MAPPING_MD = "docs/contracts/ZTL-OCE-MAPPING-v0.1.md"
MAPPING_JSON = "docs/contracts/ZTL-OCE-MAPPING-v0.1.json"
PROFILE = "docs/contracts/kernel-profiles/ztl-v0.1.json"
DECISION_SCHEMA = "schemas/proposed/runtime-decision.schema.json"
WARRANT_SCHEMA = "schemas/proposed/warrant-artifact.schema.json"
REQUIREMENT_SCHEMA = "schemas/proposed/warrant-requirement.schema.json"

GOVERNING = (ADR, CONTRACT, MAPPING_MD)

_HISTORICAL = re.compile(r"<!--\s*HISTORICAL-START\s*-->.*?<!--\s*HISTORICAL-END\s*-->", re.DOTALL)


def _active(repo_root: Path, relpath: str) -> str:
    """Active normative prose: historical sections removed, markup and wrapping collapsed."""
    raw = (repo_root / relpath).read_text(encoding="utf-8")
    stripped = _HISTORICAL.sub(" ", raw)
    return " ".join(stripped.replace("*", "").replace("`", "").split())


def _historical(repo_root: Path, relpath: str) -> str:
    raw = (repo_root / relpath).read_text(encoding="utf-8")
    return " ".join(
        " ".join(match.group(0) for match in _HISTORICAL.finditer(raw))
        .replace("*", "")
        .replace("`", "")
        .split()
    )


def _load(repo_root: Path, relpath: str) -> Any:  # noqa: ANN401 - JSON is dynamic
    return json.loads((repo_root / relpath).read_text(encoding="utf-8"))


def _units(repo_root: Path, relpath: str) -> list[str]:
    """Active text as assertable units.

    A markdown table row is one unit. Prose is grouped into paragraphs and collapsed, so a
    statement split across a line wrap is still matched as one statement -- the naive
    line-by-line reading produced false failures on wrapped sentences.
    """
    raw = _HISTORICAL.sub(" ", (repo_root / relpath).read_text(encoding="utf-8"))
    units: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            units.append(" ".join(" ".join(paragraph).replace("*", "").replace("`", "").split()))
            paragraph.clear()

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            flush()
            units.append(" ".join(stripped.replace("*", "").replace("`", "").split()))
        elif not stripped:
            flush()
        else:
            paragraph.append(stripped)
    flush()
    return [unit for unit in units if unit]


# ---------------------------------------------------------------------------
# The marker convention itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", GOVERNING)
def test_historical_markers_are_balanced(repo_root: Path, relpath: str) -> None:
    raw = (repo_root / relpath).read_text(encoding="utf-8")
    assert raw.count("<!-- HISTORICAL-START -->") == raw.count("<!-- HISTORICAL-END -->"), relpath


def test_the_adr_actually_has_historical_sections(repo_root: Path) -> None:
    """If the markers vanished, every test below would silently weaken."""
    assert _historical(repo_root, ADR), "ADR-013 has no marked historical section"


# ---------------------------------------------------------------------------
# Superseded phrasing must not survive in active text
# ---------------------------------------------------------------------------

#: Phrases that were true in an earlier revision and are now wrong.
SUPERSEDED = (
    "three dependent fields",
    "ON CREDIT is recorded as ESTABLISHED",
    "is the first artifact VEIP binds to",
    "the beginning of the VEIP lifecycle",
    "are the only substantive codes",
    "minimum_warranty_grade: hereditary | sound | until-verification, defaulting to",
)


@pytest.mark.parametrize("phrase", SUPERSEDED)
@pytest.mark.parametrize("relpath", GOVERNING)
def test_superseded_phrases_are_absent_from_active_text(
    repo_root: Path, relpath: str, phrase: str
) -> None:
    assert phrase not in _active(repo_root, relpath), f"{relpath}: {phrase!r}"


def test_no_active_statement_maps_on_credit_to_established(repo_root: Path) -> None:
    """The exact regression that survived two revisions of review."""
    for relpath in GOVERNING:
        text = _active(repo_root, relpath)
        for wrong in (
            "ON CREDIT → ESTABLISHED",
            "ON CREDIT -> ESTABLISHED",
            "ON CREDIT | ESTABLISHED",
            "ON CREDIT maps to ESTABLISHED",
        ):
            assert wrong not in text, f"{relpath}: {wrong!r}"


def test_every_active_on_credit_statement_uses_conditionally_supported(
    repo_root: Path,
) -> None:
    """Wherever active text gives ON CREDIT an epistemic status, it must be the right one."""
    for relpath in GOVERNING:
        for unit in _units(repo_root, relpath):
            if "ON CREDIT" not in unit:
                continue
            # Only units that ASSIGN a status. "REFUTED" also names a disposition, so a
            # sentence merely listing the four dispositions is not an assignment.
            assigns = unit.startswith("|") or any(
                marker in unit for marker in ("→", "->", "maps to", "epistemic_status")
            )
            if not assigns:
                continue
            if not any(
                status in unit
                for status in (
                    "ESTABLISHED",
                    "UNRESOLVED",
                    "CONTRADICTED",
                    "CONDITIONALLY_SUPPORTED",
                )
            ):
                continue
            assert "CONDITIONALLY_SUPPORTED" in unit or "never" in unit.lower(), (
                f"{relpath}: ON CREDIT given a status without CONDITIONALLY_SUPPORTED: {unit}"
            )


def test_historical_sections_may_still_quote_superseded_language(
    repo_root: Path,
) -> None:
    """The corrections record is meant to contain the old wording. Prove it survived."""
    historical = _historical(repo_root, ADR)
    assert "ON CREDIT to ESTABLISHED was our error" in historical
    assert "the first artifact VEIP binds to" in historical


# ---------------------------------------------------------------------------
# Active text agrees with the schemas and the mapping
# ---------------------------------------------------------------------------


def test_active_allow_sections_describe_both_routes(repo_root: Path) -> None:
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "Route A" in text, relpath
        assert "Route B" in text, relpath
        assert "allow_with_disclosure" in text, relpath
        assert "OIC-D-0005" in text, relpath
        assert "OIC-D-0001" in text, relpath


def test_active_decision_mode_text_says_status_is_preserved(repo_root: Path) -> None:
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "preserve" in text.lower(), relpath
    assert "prior status preserved" in _active(repo_root, ADR)
    assert "preserved" in _active(repo_root, CONTRACT)
    assert "PRESERVE" in _active(repo_root, MAPPING_MD)


def test_active_text_states_the_three_stages(repo_root: Path) -> None:
    adr = _active(repo_root, ADR)
    assert "three ordered stages" in adr
    assert "applied_control_overlay_ids" in adr
    mapping = _active(repo_root, MAPPING_MD)
    for stage in (
        "Stage 1 - classification",
        "Stage 2 - warrant policy",
        "Stage 3 - decision mode",
    ):
        assert stage in mapping, stage


def test_reason_code_registry_matches_schema_and_mapping(repo_root: Path) -> None:
    """Registry, canonical mapping, and both schemas must name the same codes."""
    registry = set(re.findall(r"`(OIC-[WD]-[0-9]{4})`", (repo_root / CONTRACT).read_text("utf-8")))
    mapping = _load(repo_root, MAPPING_JSON)
    used = {row["primary_reason_code"] for row in mapping["classification_rows"]}
    used |= {rule["policy_reason_code"] for rule in mapping["warrant_policy_rules"]}
    used |= {
        overlay["policy_reason_code"]
        for overlay in mapping["decision_mode_overlays"]
        if overlay["policy_reason_code"]
    }
    assert used <= registry, sorted(used - registry)

    schema_text = (repo_root / DECISION_SCHEMA).read_text(encoding="utf-8")
    for code in re.findall(r"(OIC-[WD]-[0-9]{4})", schema_text):
        assert code in registry, code


def test_control_policy_codes_agree_between_schema_and_mapping(repo_root: Path) -> None:
    schema = _load(repo_root, DECISION_SCHEMA)
    declared = set(schema["$defs"]["control_policy_reason_code"]["enum"])
    mapping = _load(repo_root, MAPPING_JSON)
    used = {rule["policy_reason_code"] for rule in mapping["warrant_policy_rules"]}
    used |= {
        overlay["policy_reason_code"]
        for overlay in mapping["decision_mode_overlays"]
        if overlay["policy_reason_code"]
    }
    assert used == declared, f"schema {sorted(declared)} vs mapping {sorted(used)}"


def test_warrant_state_values_agree_between_schema_and_mapping(repo_root: Path) -> None:
    schema = _load(repo_root, DECISION_SCHEMA)
    declared = set(schema["properties"]["warrant_state"]["enum"])
    mapping = _load(repo_root, MAPPING_JSON)
    used = {row["warrant_state"] for row in mapping["classification_rows"]}
    assert used <= declared, sorted(used - declared)
    # Both new states must actually be in use, or the split was cosmetic.
    assert "UNSUPPORTED_RESULT" in used
    assert "UNSUPPORTED_GRADE" in used


def test_epistemic_statuses_agree_between_schema_mapping_and_profile(
    repo_root: Path,
) -> None:
    schema = _load(repo_root, DECISION_SCHEMA)
    declared = set(schema["properties"]["epistemic_status"]["enum"])
    assert declared == {
        "ESTABLISHED",
        "CONDITIONALLY_SUPPORTED",
        "REFUTED",
        "UNRESOLVED",
        "CONTRADICTED",
    }
    mapping = _load(repo_root, MAPPING_JSON)
    assert set(mapping["epistemic_status_mapping"].values()) <= declared
    profile = _load(repo_root, PROFILE)
    profile_statuses = {
        entry["maps_to_epistemic_status"] for entry in profile["disposition_values"]
    }
    assert profile_statuses <= declared
    assert mapping["epistemic_status_mapping"]["ON CREDIT"] == "CONDITIONALLY_SUPPORTED"


def test_profile_vocabulary_matches_the_warrant_schema(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    schema = _load(repo_root, WARRANT_SCHEMA)
    assert {entry["value"] for entry in profile["disposition_values"]} == set(
        schema["properties"]["disposition"]["enum"]
    )
    assert {entry["value"] for entry in profile["warranty_grade_values"]} == set(
        schema["properties"]["warranty_grade"]["enum"]
    )
    assert set(profile["raw_verdict_values"]) == set(schema["properties"]["raw_verdict"]["enum"])
    assert profile["canonicalization_profile_id"].endswith(
        profile["formula_digest_algorithm"] + "-v0.1"
    )


def test_warrant_requirement_dependent_field_count(repo_root: Path) -> None:
    """The contract says four; the schema must actually have four."""
    schema = _load(repo_root, REQUIREMENT_SCHEMA)
    dependants = set(schema["required"]) - {"mode"}
    assert len(dependants) == 4, sorted(dependants)
    text = _active(repo_root, CONTRACT)
    assert "all four dependent fields" in text


def test_counts_match_the_canonical_artifact(repo_root: Path) -> None:
    mapping = _load(repo_root, MAPPING_JSON)
    assert len(mapping["classification_rows"]) == 31
    assert len(mapping["warrant_policy_rules"]) == 5
    assert len(mapping["decision_mode_overlays"]) == 3
    fixtures = list((repo_root / "tests/fixtures/warrant-contract").glob("*.json"))
    assert len(fixtures) == 32
    assert len(list((repo_root / "schemas/proposed").glob("*.schema.json"))) == 3


def test_every_fixture_row_reference_exists(repo_root: Path) -> None:
    mapping = _load(repo_root, MAPPING_JSON)
    rows = {int(row["row_id"]) for row in mapping["classification_rows"]}
    overlays = {rule["rule_id"] for rule in mapping["warrant_policy_rules"]}
    overlays |= {overlay["overlay_id"] for overlay in mapping["decision_mode_overlays"]}
    for path in sorted((repo_root / "tests/fixtures/warrant-contract").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        assert fixture["classification_row"] in rows, path.stem
        for identifier in fixture["applied_control_overlay_ids"]:
            assert identifier in overlays, f"{path.stem}: {identifier}"


def test_active_unresolved_questions_exclude_adjudicated_ones(repo_root: Path) -> None:
    """A question that has been decided must not still be listed as open."""
    raw = _HISTORICAL.sub(" ", (repo_root / CONTRACT).read_text(encoding="utf-8"))
    section = raw.split("## 12. Unresolved questions")[1].split("## 13.")[0]
    for line in section.splitlines():
        if not line.strip().startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        question, state = cells[1], cells[3]
        if "ANSWERED" in state:
            continue
        # An open question must not restate something the mapping already fixes.
        assert "epistemic status for ON CREDIT" not in question, question
        assert "ESTABLISHED the right" not in question, question


def test_veip_handoff_language_matches_the_adr_chronology(repo_root: Path) -> None:
    contract = _active(repo_root, CONTRACT)
    adr = _active(repo_root, ADR)
    assert "RuntimeDecision alone is not the complete handoff" in contract
    for field in ("ActionProposal", "authority and admission versions"):
        assert field in contract, field
    assert "evidence inside the VEIP lifecycle" in adr
    assert "not itself a VEIP lifecycle record" in adr
    assert "VEIP receives or records the consequential ActionProposal" in adr


def test_on_unknown_scope_is_stated_correctly(repo_root: Path) -> None:
    text = _active(repo_root, CONTRACT)
    assert "UNRESOLVED and failure paths only" in text
    assert "does not apply to CONDITIONALLY_SUPPORTED" in text
    schema = _load(repo_root, DECISION_SCHEMA)
    rule = next(
        block
        for block in schema["allOf"]
        if block["if"].get("properties", {}).get("on_unknown_applied", {}).get("type") == "string"
    )
    assert rule["then"]["properties"]["epistemic_status"]["const"] == "UNRESOLVED"


def test_automatic_mode_does_not_always_imply_substantive(repo_root: Path) -> None:
    text = _active(repo_root, CONTRACT)
    assert "SUBSTANTIVE (Route A) or CONTROL_REQUIREMENT (Route B)" in text
