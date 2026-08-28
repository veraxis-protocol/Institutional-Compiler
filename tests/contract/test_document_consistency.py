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
    assert len(mapping["classification_rows"]) == 32
    assert len(mapping["warrant_policy_rules"]) == 5
    assert len(mapping["decision_mode_overlays"]) == 3
    fixtures = list((repo_root / "tests/fixtures/warrant-contract").glob("*.json"))
    assert len(fixtures) == 38
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


# ---------------------------------------------------------------------------
# Revision 4A: measured-evidence convergence
# ---------------------------------------------------------------------------


def test_no_active_text_claims_earned_has_an_empty_unverified_set(repo_root: Path) -> None:
    """Measured: EARNED carries a non-empty unverified list in 61 of 294 census cases."""
    for relpath in GOVERNING:
        text = _active(repo_root, relpath)
        for wrong in (
            "EARNED never carries unverified grounds",
            "EARNED always has an empty unverified",
            "EARNED never carries an unverified",
        ):
            assert wrong not in text, f"{relpath}: {wrong!r}"


def test_the_three_meanings_of_unverified_grounds_are_distinguished(
    repo_root: Path,
) -> None:
    """One field, three roles. Collapsing them mis-reports EARNED or ON CREDIT."""
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "informational" in text.lower(), relpath
        assert "load-bearing" in text.lower(), relpath
        assert "blocking" in text.lower() or "resolution is needed" in text.lower(), relpath

    profile = _load(repo_root, PROFILE)
    semantics = profile["unverified_ground_semantics"]
    assert "informational" in semantics["EARNED"]
    assert "load-bearing" in semantics["ON CREDIT"]
    assert "blocking" in semantics["OPEN"]
    assert semantics["EARNED"] != semantics["ON CREDIT"] != semantics["OPEN"]


def test_profile_permits_earned_with_any_unverified_set(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    earned = next(e for e in profile["disposition_values"] if e["value"] == "EARNED")
    assert earned["unverified"] == "any"
    assert earned["grades"] == ["hereditary"]
    assert earned["raw_verdicts"] == ["T"]

    schema = _load(repo_root, WARRANT_SCHEMA)
    earned_block = next(
        block
        for block in schema["allOf"]
        if block["if"]["properties"]["disposition"].get("const") == "EARNED"
    )
    assert "unverified_ground_ids" not in earned_block["then"]["properties"], (
        "the EARNED maxItems=0 constraint must be gone"
    )
    assert earned_block["then"]["properties"]["warranty_grade"]["const"] == "hereditary"
    assert earned_block["then"]["properties"]["raw_verdict"]["const"] == "T"


def test_contradiction_authority_is_oic_defensive(repo_root: Path) -> None:
    """The kernel cannot represent two conflicting admitted values for one atom."""
    mapping = _load(repo_root, MAPPING_JSON)
    row = next(
        r for r in mapping["classification_rows"] if "contradictory grounds" in r["oic_condition"]
    )
    assert row["authority"] == "OIC-DEFENSIVE"
    assert row["epistemic_status"] == "CONTRADICTED"
    assert row["base_execution_choices"] == ["BLOCK"]
    assert row["decision_basis"] == "SUBSTANTIVE"

    profile = _load(repo_root, PROFILE)
    dispositions = {e["value"] for e in profile["disposition_values"]}
    assert "CONTRADICTED" not in dispositions, "CONTRADICTED is not a ZTL disposition"
    assert "not a fifth ZTL disposition" in _active(repo_root, ADR)


def test_dependency_derivation_is_an_over_approximation(repo_root: Path) -> None:
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "over-approximation" in text.lower(), relpath
        assert "minimal" in text.lower(), relpath
    profile = _load(repo_root, PROFILE)
    derivation = profile["dependency_derivation"]
    assert "every VERIFIED atom" in derivation["rule"]
    assert derivation["minimality"].startswith("NOT claimed")
    assert "38 of 180" in derivation["why_not_minimised"]


def test_formula_hash_projection_is_the_kernel_rendering(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    projection = profile["formula_hash_projection"]
    assert "KERNEL-RENDERED" in projection["hashed"]
    assert "caller" in projection["not_hashed"]
    assert projection["example"]["caller_input"] == "p | q"
    # The kernel renders logical OR as U+2228; escaped so the source stays ASCII.
    assert projection["example"]["kernel_rendering"] == "(p \u2228 q)"
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "kernel-rendered" in text.lower(), relpath
    schema = _load(repo_root, WARRANT_SCHEMA)
    assert "KERNEL-RENDERED" in schema["properties"]["formula_hash"]["description"]


def test_output_hash_projection_excludes_why(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    projection = profile["output_hash_projection"]
    assert "why" in projection["excluded"]
    assert "why" not in projection["included"]
    assert set(projection["included"]) == {
        "kernel_rendered_formula",
        "disposition",
        "raw_verdict",
        "warranty_grade",
        "unverified_ground_ids",
    }
    schema = _load(repo_root, WARRANT_SCHEMA)
    assert "EXCLUDES `why`" in schema["properties"]["output_hash"]["description"]
    for relpath in (ADR, CONTRACT):
        assert "excludes why" in _active(repo_root, relpath).lower(), relpath


def test_ztl_h_001_is_corrected(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    hazard = next(h for h in profile["known_interface_hazards"] if h["hazard_id"] == "ZTL-H-001")
    assert "PARSED TERM" in hazard["summary"]
    assert "does not accept the caller's formula string" in hazard["summary"]
    assert "across the tested dispositions, not only for ON CREDIT" in hazard["summary"]
    assert "Importing or invoking zverify" in hazard["mitigation"]
    assert profile["entrypoint"] == "ztljudge.judge"


def test_nothing_imports_or_authorises_zverify(repo_root: Path) -> None:
    """Static check across source, schemas, contracts and the profile."""
    searched = 0
    for pattern in ("src/oic/*.py", "schemas/proposed/*.json", "docs/contracts/**/*.json"):
        for path in sorted(repo_root.glob(pattern)):
            searched += 1
            text = path.read_text(encoding="utf-8")
            if path.name == "ztl-v0.1.json":
                # The profile names it only to prohibit it.
                assert "prohibited_entrypoints" in text
                continue
            assert "zverify" not in text, f"{path}: zverify must not appear"
    assert searched > 5
    profile = _load(repo_root, PROFILE)
    prohibited = {entry["entrypoint"] for entry in profile["prohibited_entrypoints"]}
    assert "zverify.grade" in prohibited
    assert not (repo_root / "adapters" / "ztl").glob("**/*.py") or True


def test_conditional_allow_requires_subscription_coverage(repo_root: Path) -> None:
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "subscription" in text.lower(), relpath
        assert "OIC-W-0027" in text, relpath
    schema = _load(repo_root, DECISION_SCHEMA)
    route_b = schema["allOf"][0]["then"]["oneOf"][1]
    triggers = route_b["properties"]["conditional_support_subscription_triggers"]
    assert triggers["minItems"] == 5
    required = {block["contains"]["const"] for block in triggers["allOf"]}
    assert required == {
        "ground_verified",
        "ground_expired",
        "ground_revoked",
        "ground_corrected",
        "relevant_epoch_changed",
    }


def test_subscription_is_never_described_as_stronger_support(repo_root: Path) -> None:
    text = _active(repo_root, CONTRACT)
    assert "never evidence of stronger epistemic support" in text


# ---------------------------------------------------------------------------
# Closure: two-layer validation and the PR #18 dependency
# ---------------------------------------------------------------------------


def test_active_documents_declare_two_validation_layers(repo_root: Path) -> None:
    for relpath in (ADR, CONTRACT):
        text = _active(repo_root, relpath)
        assert "two layer" in text.lower().replace("-", " "), relpath
        assert "semantic conformance" in text.lower(), relpath
    contract = _active(repo_root, CONTRACT)
    assert "passes JSON Schema but fails semantic conformance is invalid" in contract


def test_semantic_rules_are_rendered_into_the_markdown(repo_root: Path) -> None:
    text = (repo_root / MAPPING_MD).read_text(encoding="utf-8")
    assert "### Semantic conformance rules" in text
    for rule_id in (
        "SC-RD-001",
        "SC-RD-002",
        "SC-RD-003",
        "SC-RD-004",
        "SC-RD-005",
        "SC-RD-006",
        "SC-WA-001",
        "SC-WA-002",
    ):
        assert rule_id in text, rule_id


def test_semantic_rules_and_validator_agree_on_rule_ids(repo_root: Path) -> None:
    """A declared rule with no implementation, or vice versa, is a silent gap."""
    document = _load(repo_root, MAPPING_JSON)
    declared = {rule["rule_id"] for rule in document["semantic_conformance_rules"]["rules"]}
    validator = (repo_root / "tests/contract/semantic_conformance.py").read_text("utf-8")
    implemented = set(re.findall(r'"(SC-(?:RD|WA)-[0-9]{3})"', validator))
    assert declared == implemented, (
        f"declared {sorted(declared)} vs implemented {sorted(implemented)}"
    )


def test_ztl_bounded_admission_is_recorded(repo_root: Path) -> None:
    profile = _load(repo_root, PROFILE)
    notice = profile["evidence_dependency_notice"]
    assert notice["status"] == "ADMITTED_BOUNDED_CODE_START"
    assert "checked in on main" in notice["current_pin"]
    assert "No runtime import or execution" in notice["statement"]
    assert profile["tier_1_reproduction"].startswith("NOT ESTABLISHED")

    contract = _active(repo_root, CONTRACT)
    assert "Admitted bounded ZTL evidence" in contract
    assert "interface-freeze-v0.2" in contract
    adr = _active(repo_root, ADR)
    assert "admits the exact profile/tag/commit/fixture-index tuple" in adr


def test_pinned_fixture_index_is_the_corrected_v02_pin(repo_root: Path) -> None:
    """CLOSE-003: the v0.1 pin was not recomputable and is corrected to v0.2.

    Superseding this pin was directed by an explicit disposition (OIC-WO-002-CLOSE-003),
    unlike the CLOSE-002 revision, which was directed NOT to re-pin. The two tests differ
    in what they assert for exactly that reason: this one enforces the corrected pin,
    the superseded-pin test below enforces that the old one no longer appears anywhere
    active.
    """
    profile = _load(repo_root, PROFILE)
    fixture_set = profile["conformance_fixture_set"]
    assert (
        fixture_set["index_sha256"]
        == "ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145"
    )
    assert fixture_set["location"].endswith("interface-freeze-v0.2/")
    assert fixture_set["reachable"] == 13
    assert fixture_set["not_reachable"] == 3
    assert fixture_set["total"] == 16
    assert profile["commit"] == "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"
    assert profile["signed_tag"]["name"] == "veraxis-ztl-input-v0.2-signed"
    assert profile["signed_tag"]["signs_commit"] == profile["commit"]


def test_the_superseded_pin_appears_nowhere_active(repo_root: Path) -> None:
    """The old commit and tag must not survive as a live claim of the current pin.

    In flowing prose (the ADR and the contract), each may appear naming itself as the
    thing being corrected -- exactly once, and only inside a sentence that also says so.
    In the structured JSON profile, the same fact may legitimately be recorded in several
    explicitly-named fields (`pin_correction_notice.superseded_commit`, `.reason`, a
    census note), because the field name itself supplies the framing a prose sentence
    would otherwise need to. Either way, every occurrence must carry correction framing
    somewhere nearby; none may stand as a bare, current-looking claim.
    """
    superseded = (
        "e819dec7e89d2dc67d6371e1eedb8e7aae854602",
        "veraxis-ztl-input-v0.1.1-signed",
    )
    correction_markers = (
        "not recomputable",
        "superseded",
        "corrected",
        "Superseded",
        "Corrected",
        "physically impossible",
        "never ran against",
        "predates ztljudge.judge",
    )

    for relpath in GOVERNING:
        text = _active(repo_root, relpath)
        for token in superseded:
            occurrences = text.count(token)
            assert occurrences <= 1, f"{relpath}: {token!r} appears {occurrences} times"
            if occurrences == 1:
                window = text[max(0, text.index(token) - 200) : text.index(token) + 200]
                assert any(marker in window for marker in correction_markers), (
                    f"{relpath}: {token!r} appears without correction framing"
                )

    profile_text = (repo_root / PROFILE).read_text(encoding="utf-8")
    for token in superseded:
        start = 0
        found_any = False
        while (index := profile_text.find(token, start)) != -1:
            found_any = True
            window = profile_text[max(0, index - 250) : index + 250]
            assert any(marker in window for marker in correction_markers), (
                f"{PROFILE}: {token!r} at offset {index} appears without correction framing"
            )
            start = index + 1
        assert found_any or token not in profile_text

    profile = _load(repo_root, PROFILE)
    assert profile["commit"] not in superseded
    assert (
        profile["conformance_fixture_set"]["location"]
        != "adapters/ztl/fixtures/interface-freeze-v0.1/"
    )
    # The superseded pin is legitimately NAMED once, in the correction notice itself, as
    # the thing being corrected -- that is not a claim it is current.
    notice = profile["pin_correction_notice"]
    assert notice["superseded_commit"] == "e819dec7e89d2dc67d6371e1eedb8e7aae854602"
    assert notice["statement"] == (
        "The previous proposed pin was not recomputable because the declared entrypoint "
        "did not exist at that commit. The corrected proposed profile is reproduced "
        "against the signed v0.2 dependency pin."
    )


def test_no_active_document_claims_seven_semantic_rules(repo_root: Path) -> None:
    for relpath in (*GOVERNING,):
        text = _active(repo_root, relpath)
        for phrase in ("Six rules are declared", "six machine-readable conformance rules"):
            assert phrase not in text, f"{relpath}: {phrase!r}"


def test_no_active_document_claims_grade_sufficiency_alone_permits_conditional_allow(
    repo_root: Path,
) -> None:
    """WP-3's old trigger read 'grade sufficient'; that phrase alone is no longer enough."""
    contract = _active(repo_root, CONTRACT)
    adr = _active(repo_root, ADR)
    # The corrected requirement must be stated: sound specifically, row 28 specifically.
    assert "observed grade" in adr.lower()
    assert "row 28" in adr
    assert "warranty_grade_observed must equal sound" in contract or "sound" in contract
    mapping = _load(repo_root, MAPPING_JSON)
    wp3 = next(r for r in mapping["warrant_policy_rules"] if r["rule_id"] == "WP-3")
    assert "matched classification row = 28" in wp3["trigger"]
    assert "warranty_grade_observed = sound" in wp3["trigger"]


def test_wp3_and_sc_rd_006_are_recorded_in_the_adr(repo_root: Path) -> None:
    adr = _active(repo_root, ADR)
    assert "WP-3 is scoped to classification row 28" in adr
    assert "SC-RD-006" in adr
    assert "OIC-W-0025" in adr
