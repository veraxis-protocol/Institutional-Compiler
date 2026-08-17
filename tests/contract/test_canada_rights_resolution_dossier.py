"""Fail-closed contract tests for the Canada rights-resolution dossier.

The dossier is documentation and decision support. These tests prove it changed
nothing about the frozen rights state and that its own promotion gates hold.
"""

from __future__ import annotations

import ast
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract

BASE_SHA = "2dab50aa5e84cc2995bb8561a8d1fb63741e4a3a"

FREEZE_RELDIR = "benchmarks/corpus/canada/freeze-v0.1"
DOSSIER_RELDIR = "benchmarks/corpus/canada/rights-resolution-v0.1"
RIGHTS_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.json"
EVIDENCE_RELPATH = f"{FREEZE_RELDIR}/RIGHTS-EVIDENCE-LEDGER-v0.1.json"
MANIFEST_RELPATH = "benchmarks/preflight/SOURCE_MANIFEST.csv"

TBS_SOURCES = ("CA-1", "CA-2", "CA-4")
CANADABUYS_SOURCES = (
    "CA-5-APPROVALS",
    "CA-5-DELEGATION",
    "CA-5-LIMITS",
    "CA-5-SIGNING",
    "CA-6-ARCHIVE",
    "CA-6-CH6",
    "CA-6-GLOSSARY",
)
UNRESOLVED = TBS_SOURCES + CANADABUYS_SOURCES
BLOCKED = "BLOCKED_PENDING_CLEARANCE"

ALLOWED_STATES = frozenset(
    {
        "EVIDENCE_RECAPTURE_REQUIRED",
        "PUBLISHER_PERMISSION_REQUIRED",
        "COUNSEL_REVIEW_REQUIRED",
        "READY_FOR_OWNER_DISPOSITION",
        "REMAINS_BLOCKED",
    }
)

# Every artifact whose bytes this work order must leave alone.
FROZEN_ARTIFACTS = (
    f"{FREEZE_RELDIR}/ACQUISITION-FREEZE-v0.1.json",
    f"{FREEZE_RELDIR}/ACQUISITION-FREEZE-v0.1.md",
    f"{FREEZE_RELDIR}/INDEX.json",
    f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.json",
    f"{FREEZE_RELDIR}/RIGHTS-CLEARANCE-v0.1.md",
    f"{FREEZE_RELDIR}/RIGHTS-EVIDENCE-LEDGER-v0.1.json",
    f"{FREEZE_RELDIR}/SHA256SUMS",
    f"{FREEZE_RELDIR}/SHA512SUMS",
    f"{FREEZE_RELDIR}/receipts/CA-3.receipt.json",
    f"{FREEZE_RELDIR}/sources/CA-3.xml",
    MANIFEST_RELPATH,
    "STATUS.md",
)


def _load(repo_root: Path, name: str) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / DOSSIER_RELDIR / f"{name}.json").read_text(encoding="utf-8")),
    )


#: The upper bound of this Canada work order's interval. It was HEAD, which let a
#: completed historical proposition drift forward and become a standing prohibition on
#: later lanes. Pinned to the frozen pre-L1 state, the assertion again says only what this
#: work order did not do. The forbidden path set is unchanged and nothing is exempted.
FROZEN_TERMINAL_SHA = "a59b885423b984b2eb8c20751833926b888e6b95"


def test_the_frozen_comparison_boundaries_resolve_exactly(repo_root: Path) -> None:
    """Both ends of the interval must be real commits, or the guard proves nothing."""
    for sha in (BASE_SHA, FROZEN_TERMINAL_SHA):
        resolved = subprocess.run(
            ["git", "rev-parse", sha],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert resolved == sha


def _changed_files(repo_root: Path) -> list[str]:
    return subprocess.run(
        ["git", "diff", "--name-only", f"{BASE_SHA}...{FROZEN_TERMINAL_SHA}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()


@pytest.fixture(scope="module")
def ledger(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "CANADA-RIGHTS-RESOLUTION-LEDGER-v0.1")


@pytest.fixture(scope="module")
def counsel(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "CANADA-COUNSEL-REVIEW-DOSSIER-v0.1")


@pytest.fixture(scope="module")
def permission(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "CANADABUYS-PERMISSION-REQUEST-v0.1")


@pytest.fixture(scope="module")
def recapture(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "TBS-TERMS-RECAPTURE-PROTOCOL-v0.1")


@pytest.fixture(scope="module")
def review(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "TBS-RIGHTS-EVIDENCE-REVIEW-v0.1")


@pytest.fixture(scope="module")
def register(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, "EXTERNAL-ACTION-REGISTER-v0.1")


@pytest.fixture(scope="module")
def rights(repo_root: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((repo_root / RIGHTS_RELPATH).read_text(encoding="utf-8")),
    )


# --------------------------------------------------------------------------
# Ledger scope
# --------------------------------------------------------------------------


def test_all_ten_unresolved_sources_occur_exactly_once(ledger: dict[str, Any]) -> None:
    ids = [row["source_id"] for row in ledger["rows"]]
    assert sorted(ids) == sorted(UNRESOLVED)
    assert len(ids) == len(set(ids)) == 10
    assert ledger["unresolved_source_count"] == 10


def test_ca3_is_excluded_from_the_unresolved_ledger(ledger: dict[str, Any]) -> None:
    assert "CA-3" not in {row["source_id"] for row in ledger["rows"]}
    assert ledger["excluded_source_ids"] == ["CA-3"]


def test_ledger_sources_match_the_frozen_rights_record(
    ledger: dict[str, Any], rights: dict[str, Any]
) -> None:
    blocked = {
        record["source_id"]
        for record in rights["records"]
        if record["reviewer_disposition"] == BLOCKED
    }
    assert {row["source_id"] for row in ledger["rows"]} == blocked


def test_ledger_urls_are_the_frozen_acquisition_targets(
    ledger: dict[str, Any], rights: dict[str, Any]
) -> None:
    targets = {record["source_id"]: record for record in rights["records"]}
    for row in ledger["rows"]:
        record = targets[row["source_id"]]
        assert row["official_url"] == record["acquisition_target_url"]
        # A provenance URL must never appear as the ledger's operative target.
        if row["official_url"] == record["provenance_url"]:
            assert record["acquisition_target_url"] == record["provenance_url"]


def test_initial_states_are_the_expected_ones(ledger: dict[str, Any]) -> None:
    by_id = {row["source_id"]: row["current_state"] for row in ledger["rows"]}
    for source_id in TBS_SOURCES:
        assert by_id[source_id] == "EVIDENCE_RECAPTURE_REQUIRED"
    for source_id in CANADABUYS_SOURCES:
        assert by_id[source_id] == "PUBLISHER_PERMISSION_REQUIRED"


def test_ledger_states_come_from_the_closed_vocabulary(ledger: dict[str, Any]) -> None:
    assert set(ledger["allowed_states"]) == ALLOWED_STATES
    for row in ledger["rows"]:
        assert row["current_state"] in ALLOWED_STATES
        assert set(row["allowed_next_states"]) <= ALLOWED_STATES


def test_every_ledger_row_still_reads_blocked(ledger: dict[str, Any]) -> None:
    for row in ledger["rows"]:
        assert row["current_rights_disposition"] == BLOCKED


def test_no_transition_has_been_recorded(ledger: dict[str, Any]) -> None:
    for row in ledger["rows"]:
        assert row["history"] == []


# --------------------------------------------------------------------------
# Transition gates
# --------------------------------------------------------------------------


def test_every_transition_requires_evidence_and_reviewer_identity(
    ledger: dict[str, Any],
) -> None:
    required = set(ledger["transition_rule"]["required_fields"])
    assert {"evidence_reference", "reviewer_identity", "review_utc", "rationale"} <= required
    assert {"previous_state", "proposed_next_state"} <= required


def test_evidence_hash_and_owner_reference_are_conditionally_required(
    ledger: dict[str, Any],
) -> None:
    conditional = ledger["transition_rule"]["conditionally_required_fields"]
    assert "evidence_sha256" in conditional
    assert "owner_disposition_reference" in conditional
    assert "READY_FOR_OWNER_DISPOSITION" in conditional["owner_disposition_reference"]


def test_owner_assertion_alone_cannot_clear_a_source(ledger: dict[str, Any]) -> None:
    rule = ledger["transition_rule"]
    assert rule["owner_assertion_alone_is_insufficient"] is True
    assert "does not open them" in rule["owner_assertion_rule"]


def test_the_ledger_cannot_move_a_rights_disposition(ledger: dict[str, Any]) -> None:
    assert (
        "No transition in this ledger changes a rights disposition"
        in (ledger["transition_rule"]["disposition_change_rule"])
    )


def test_every_state_has_an_explicit_gate(ledger: dict[str, Any]) -> None:
    assert set(ledger["state_gates"]) == ALLOWED_STATES
    for gate in ledger["state_gates"].values():
        assert gate.strip()


# --------------------------------------------------------------------------
# Bilingual permission package
# --------------------------------------------------------------------------


def test_english_and_french_cover_the_same_permission_categories(
    permission: dict[str, Any],
) -> None:
    for category in permission["permission_categories"]:
        assert set(category) == {"category_id", "en", "fr"}
        for language in ("en", "fr"):
            assert set(category[language]) == {"title", "text"}
            assert category[language]["title"].strip()
            assert category[language]["text"].strip()
    ids = [category["category_id"] for category in permission["permission_categories"]]
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "automated_retrieval_by_named_tool",
        "derived_artifact_publication",
        "internal_research_use",
        "internal_storage",
        "logos_branding_and_identifiers",
        "machine_processing",
        "preservation_and_attribution",
        "public_repository_redistribution",
        "retention_and_deletion",
        "retrieval_of_named_urls",
    }


def test_english_and_french_carry_the_same_commitments(permission: dict[str, Any]) -> None:
    for statement in permission["statements"]:
        assert set(statement) == {"statement_id", "en", "fr"}
        assert statement["en"].strip() and statement["fr"].strip()
    assert {statement["statement_id"] for statement in permission["statements"]} == {
        "access_controls_and_deletion_available",
        "derived_not_official_gc_interpretation",
        "not_represented_as_official_veraxis_product",
        "permission_may_be_limited_to_internal_only",
        "source_meaning_not_modified",
    }


def test_both_letters_render_every_category_and_commitment(repo_root: Path) -> None:
    permission = _load(repo_root, "CANADABUYS-PERMISSION-REQUEST-v0.1")
    for language, filename in (
        ("en", "CANADABUYS-PERMISSION-REQUEST-EN-v0.1.md"),
        ("fr", "CANADABUYS-PERMISSION-REQUEST-FR-v0.1.md"),
    ):
        text = (repo_root / DOSSIER_RELDIR / filename).read_text(encoding="utf-8")
        for category in permission["permission_categories"]:
            assert category[language]["title"] in text
        for statement in permission["statements"]:
            assert statement[language] in text
        for source in permission["requested_sources"]:
            assert source["url"] in text


def test_permission_request_names_exactly_the_seven_canadabuys_sources(
    permission: dict[str, Any],
) -> None:
    assert len(permission["requested_sources"]) == 7
    assert [source["source_id"] for source in permission["requested_sources"]] == sorted(
        CANADABUYS_SOURCES
    )
    assert set(permission["applies_to_source_ids"]) == {
        "CA-5-APPROVALS",
        "CA-5-DELEGATION",
        "CA-5-LIMITS",
        "CA-5-SIGNING",
        "CA-6-ARCHIVE",
        "CA-6-CH6",
        "CA-6-GLOSSARY",
    }
    assert permission["applies_to_source_ids"] == sorted(CANADABUYS_SOURCES)


def _retrieval_category(permission: dict[str, Any]) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        next(
            category
            for category in permission["permission_categories"]
            if category["category_id"] == "retrieval_of_named_urls"
        ),
    )


def _stated_count_failures(permission: dict[str, Any]) -> list[str]:
    """The retrieval category must state seven in both languages and never ten.

    The letter asks a publisher to authorize retrieval of a bounded set. A wrong
    count in either language would ask for a scope the request does not enumerate.
    """
    category = _retrieval_category(permission)
    expected = {"en": "seven", "fr": "sept"}
    wrong = {"en": ("ten", "eleven", "six", "eight"), "fr": ("dix", "onze", "six", "huit")}
    failures = []
    for language, word in expected.items():
        text = category[language]["text"].lower()
        if word not in text:
            failures.append(f"{language}: retrieval category does not state {word!r}")
        for bad in wrong[language]:
            # Match the count as a whole word so "sixty" or "sixième" cannot trip it.
            if re.search(rf"\b{bad}\b", text):
                failures.append(f"{language}: retrieval category states {bad!r}")
    return failures


def test_retrieval_category_states_seven_in_both_languages(permission: dict[str, Any]) -> None:
    assert _stated_count_failures(permission) == []
    category = _retrieval_category(permission)
    assert "seven source URLs" in category["en"]["text"]
    assert "sept URL sources" in category["fr"]["text"]


def test_the_stated_count_matches_the_enumerated_sources(permission: dict[str, Any]) -> None:
    words = {7: ("seven", "sept"), 10: ("ten", "dix")}
    count = len(permission["requested_sources"])
    english, french = words[count]
    category = _retrieval_category(permission)
    assert english in category["en"]["text"].lower()
    assert french in category["fr"]["text"].lower()


def test_no_rendering_of_the_request_refers_to_ten_source_urls(
    repo_root: Path, permission: dict[str, Any]
) -> None:
    assert "ten source URLs" not in json.dumps(permission, ensure_ascii=False)
    for filename in (
        "CANADABUYS-PERMISSION-REQUEST-EN-v0.1.md",
        "CANADABUYS-PERMISSION-REQUEST-FR-v0.1.md",
    ):
        text = (repo_root / DOSSIER_RELDIR / filename).read_text(encoding="utf-8")
        assert "ten source URLs" not in text
        assert "dix URL sources" not in text


def test_all_seven_urls_appear_in_both_rendered_languages(
    repo_root: Path, permission: dict[str, Any]
) -> None:
    urls = [source["url"] for source in permission["requested_sources"]]
    assert len(urls) == len(set(urls)) == 7
    for filename in (
        "CANADABUYS-PERMISSION-REQUEST-EN-v0.1.md",
        "CANADABUYS-PERMISSION-REQUEST-FR-v0.1.md",
    ):
        text = (repo_root / DOSSIER_RELDIR / filename).read_text(encoding="utf-8")
        for url in urls:
            assert url in text, f"{filename} omits {url}"


def test_mutation_wrong_source_count_in_either_language_fails(
    permission: dict[str, Any],
) -> None:
    assert _stated_count_failures(permission) == []
    for language, wrong in (
        ("en", "Retrieval of only the ten source URLs listed in this request."),
        ("fr", "Extraction des dix URL sources énumérées dans la présente demande."),
    ):
        mutated = copy.deepcopy(permission)
        _retrieval_category(mutated)[language]["text"] = wrong
        failures = _stated_count_failures(mutated)
        assert failures, f"a wrong {language} count was not detected"
        assert all(failure.startswith(f"{language}:") for failure in failures)


def test_mutation_a_dropped_source_desynchronizes_the_stated_count(
    permission: dict[str, Any],
) -> None:
    mutated = copy.deepcopy(permission)
    mutated["requested_sources"] = mutated["requested_sources"][:-1]
    assert len(mutated["requested_sources"]) == 6
    words = {7: "seven", 10: "ten"}
    assert len(mutated["requested_sources"]) not in words, (
        "a six-source request has no matching stated count, so the letter is inconsistent"
    )


def test_permission_request_was_not_sent(permission: dict[str, Any]) -> None:
    assert permission["transmission_state"] == "NOT_SENT"
    assert permission["status"] == "DRAFTED_NOT_SENT"
    assert "Sending is NOT authorized" in permission["send_authorization"]


def test_unanswered_permission_categories_are_not_granted(permission: dict[str, Any]) -> None:
    assert "Silence is never read as consent" in permission["unanswered_category_rule"]


# --------------------------------------------------------------------------
# Counsel dossier
# --------------------------------------------------------------------------


def test_every_counsel_question_binds_a_source_and_evidence(
    counsel: dict[str, Any], rights: dict[str, Any], repo_root: Path
) -> None:
    known_sources = {record["source_id"] for record in rights["records"]}
    evidence_ledger = json.loads((repo_root / EVIDENCE_RELPATH).read_text(encoding="utf-8"))
    known_evidence = {record["evidence_id"]: record for record in evidence_ledger["records"]}
    targets = {record["source_id"]: record for record in rights["records"]}

    assert counsel["questions"]
    for question in counsel["questions"]:
        assert question["source_ids"], f"{question['question_id']} binds no source"
        assert set(question["source_ids"]) <= known_sources
        assert question["official_urls"] == [
            targets[source_id]["acquisition_target_url"] for source_id in question["source_ids"]
        ]
        assert question["evidence_references"], f"{question['question_id']} cites no evidence"
        for reference in question["evidence_references"]:
            source = known_evidence[reference["evidence_id"]]
            assert reference["sha256"] == source["sha256"]
            assert reference["captured"] == source["captured"]
        for field in (
            "current_technical_disposition",
            "proposed_operational_use",
            "unresolved_legal_question",
            "consequence_of_approval",
            "consequence_of_denial",
            "required_counsel_disposition_form",
        ):
            assert str(question[field]).strip(), f"{question['question_id']} missing {field}"


def test_counsel_question_ids_are_unique_and_counted(counsel: dict[str, Any]) -> None:
    ids = [question["question_id"] for question in counsel["questions"]]
    assert len(ids) == len(set(ids))
    assert counsel["question_count"] == len(ids)
    for section in counsel["sections"]:
        assert section["question_count"] == sum(
            1 for question in counsel["questions"] if question["section"] == section["section"]
        )


def test_counsel_sections_cover_all_eleven_source_units(counsel: dict[str, Any]) -> None:
    covered: set[str] = set()
    for section in counsel["sections"]:
        covered.update(section["source_ids"])
    assert covered == set(UNRESOLVED) | {"CA-3"}
    assert {section["section"] for section in counsel["sections"]} == {"A", "B", "C"}


def test_counsel_dossier_disclaims_legal_conclusions(counsel: dict[str, Any]) -> None:
    note = counsel["engineering_not_legal_note"]
    assert "None of them is a legal conclusion" in note
    assert counsel["submission_state"] == "NOT_SUBMITTED"


# --------------------------------------------------------------------------
# Recapture protocol and worksheet
# --------------------------------------------------------------------------


def test_recapture_protocol_was_not_executed(recapture: dict[str, Any]) -> None:
    assert recapture["execution_state"] == "NOT_EXECUTED"
    assert "Execution is NOT authorized" in recapture["execution_authorization"]
    assert recapture["prior_failure_reference"]["captured"] is False
    assert recapture["prior_failure_reference"]["sha256"] is None


def test_recapture_protocol_specifies_every_required_control(recapture: dict[str, Any]) -> None:
    request = recapture["request"]
    for field in (
        "requested_url",
        "permitted_origin_domains",
        "permitted_redirect_domains",
        "maximum_redirect_count",
        "unapproved_cross_origin_redirect_handling",
        "required_http_status",
        "required_media_type",
        "required_content_signature",
    ):
        assert request[field], f"recapture protocol missing {field}"
    assert request["unapproved_cross_origin_redirect_handling"] == "REJECT_AND_RECORD_FAILURE"
    assert request["required_http_status"] == 200
    assert set(recapture["record_fields_required"]) >= {
        "acquisition_tool",
        "acquisition_tool_version",
        "byte_length",
        "capture_utc",
        "etag",
        "last_modified",
        "redirect_chain",
        "sha256",
        "sha512",
    }


def test_recapture_protocol_forbids_rendered_text_substitution(recapture: dict[str, Any]) -> None:
    prohibited = " ".join(recapture["prohibited_substitutions"]).lower()
    assert "browser-rendered page text" in prohibited
    assert "screenshot" in prohibited
    assert "transcribed" in prohibited
    assert "may cite only" in recapture["prohibited_substitution_rule"]


def test_worksheet_is_unpopulated_and_fails_closed(review: dict[str, Any]) -> None:
    assert review["status"] == "WORKSHEET_UNPOPULATED_PENDING_RECAPTURE"
    assert review["current_disposition_of_all_three_sources"] == BLOCKED
    assert set(review["allowed_findings"]) == {"SUPPORTED", "NOT_SUPPORTED", "UNRESOLVED"}
    for row in review["dimensions"]:
        assert row["finding"] == "UNRESOLVED"
    assert {row["dimension"] for row in review["dimensions"]} == {
        "attribution",
        "automated_retrieval",
        "internal_only_storage",
        "internal_research_use",
        "logos_insignia_trademarks",
        "machine_processing",
        "modification_restrictions",
        "personal_information",
        "public_repository_redistribution",
        "third_party_material",
    }


# --------------------------------------------------------------------------
# External action register
# --------------------------------------------------------------------------


def test_no_external_action_was_performed(register: dict[str, Any]) -> None:
    assert register["status"] == "REGISTERED_NONE_PERFORMED"
    assert "No message was sent" in register["no_action_performed_note"]
    assert register["action_count"] == len(register["actions"])
    for action in register["actions"]:
        assert action["authorized_by_this_work_order"] is False
        assert action["actor"] in {"OWNER", "PUBLISHER", "COUNSEL"}
        assert action["status"] != "PERFORMED"


def test_register_covers_both_unlocking_tracks(register: dict[str, Any]) -> None:
    blocked: set[str] = set()
    for action in register["actions"]:
        blocked.update(action["blocks_source_ids"])
    assert set(UNRESOLVED) <= blocked


# --------------------------------------------------------------------------
# The dossier changed nothing
# --------------------------------------------------------------------------


def test_no_source_bytes_or_receipts_were_added(repo_root: Path) -> None:
    changed = _changed_files(repo_root)
    assert not any(path.startswith(f"{FREEZE_RELDIR}/sources/") for path in changed)
    assert not any(path.startswith(f"{FREEZE_RELDIR}/receipts/") for path in changed)
    assert not any("receipt" in Path(path).name.lower() for path in changed)
    dossier_files = {path.name for path in (repo_root / DOSSIER_RELDIR).iterdir() if path.is_file()}
    assert all(name.endswith((".json", ".md")) for name in dossier_files)


def test_frozen_artifacts_are_byte_identical_to_the_base(repo_root: Path) -> None:
    changed = set(_changed_files(repo_root))
    for relpath in FROZEN_ARTIFACTS:
        assert relpath not in changed, f"{relpath} was modified"


def test_source_manifest_is_unchanged(repo_root: Path) -> None:
    assert MANIFEST_RELPATH not in _changed_files(repo_root)
    rows = (repo_root / MANIFEST_RELPATH).read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 2
    assert rows[1].startswith("CA-3,")


def test_no_disposition_changed_and_all_ten_remain_blocked(rights: dict[str, Any]) -> None:
    assert rights["disposition_counts"] == {
        "BLOCKED_PENDING_CLEARANCE": 10,
        "CLEAR_REPOSITORY_FREEZE": 1,
    }
    blocked = [
        record["source_id"]
        for record in rights["records"]
        if record["reviewer_disposition"] == BLOCKED
    ]
    assert sorted(blocked) == sorted(UNRESOLVED)


def test_status_and_draft_schemas_are_unchanged(repo_root: Path) -> None:
    changed = _changed_files(repo_root)
    assert "STATUS.md" not in changed
    assert not any(path.startswith("schemas/draft/") for path in changed)
    assert not any(path.startswith("docs/contracts/") for path in changed)
    assert not any(path.startswith("adapters/ztl/") for path in changed)


def test_no_network_retrieval_code_was_added(repo_root: Path) -> None:
    tree = ast.parse((repo_root / "tools/render_canada_dossier.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0].lower())
    assert imported.isdisjoint({"http", "requests", "socket", "ssl", "urllib"})


def test_no_semantic_artifact_was_produced(repo_root: Path) -> None:
    changed = _changed_files(repo_root)
    prohibited = (
        "candidate-normative",
        "control-envelope",
        "institutional-ir",
        "runtime-evaluation",
        "annotation",
        "rego",
    )
    assert not any(fragment in path for path in changed for fragment in prohibited)


def test_generated_markdown_matches_the_canonical_json(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "tools/render_canada_dossier.py", "--check", "--root", str(repo_root)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --------------------------------------------------------------------------
# Mutation checks
# --------------------------------------------------------------------------


def _ledger_scope_failures(document: dict[str, Any]) -> list[str]:
    """Re-implements the ledger scope invariants so a mutation can be shown to break them."""
    failures = []
    ids = [row["source_id"] for row in document["rows"]]
    if sorted(ids) != sorted(UNRESOLVED):
        failures.append("ledger does not cover exactly the ten unresolved sources")
    if len(ids) != len(set(ids)):
        failures.append("ledger repeats a source")
    if any(row["current_rights_disposition"] != BLOCKED for row in document["rows"]):
        failures.append("a ledger row no longer reads BLOCKED_PENDING_CLEARANCE")
    for row in document["rows"]:
        for transition in row["history"]:
            missing = [
                field
                for field in document["transition_rule"]["required_fields"]
                if not transition.get(field)
            ]
            if missing:
                failures.append(f"{row['source_id']}: transition missing {sorted(missing)}")
    return failures


def test_mutation_missing_unresolved_source_fails(ledger: dict[str, Any]) -> None:
    mutated = copy.deepcopy(ledger)
    mutated["rows"] = [row for row in mutated["rows"] if row["source_id"] != "CA-6-GLOSSARY"]
    assert _ledger_scope_failures(ledger) == []
    assert any("exactly the ten" in failure for failure in _ledger_scope_failures(mutated))


def test_mutation_disposition_promotion_without_evidence_fails(ledger: dict[str, Any]) -> None:
    mutated = copy.deepcopy(ledger)
    mutated["rows"][0]["history"] = [
        {
            "previous_state": "EVIDENCE_RECAPTURE_REQUIRED",
            "proposed_next_state": "READY_FOR_OWNER_DISPOSITION",
            "reviewer_identity": "reviewer",
            "review_utc": "2026-07-31T00:00:00Z",
            "rationale": "looks fine",
        }
    ]
    failures = _ledger_scope_failures(mutated)
    assert any("evidence_reference" in failure for failure in failures)


def test_mutation_owner_only_promotion_fails(ledger: dict[str, Any]) -> None:
    mutated = copy.deepcopy(ledger)
    mutated["rows"][0]["history"] = [
        {
            "previous_state": "EVIDENCE_RECAPTURE_REQUIRED",
            "proposed_next_state": "READY_FOR_OWNER_DISPOSITION",
            "evidence_reference": "",
            "evidence_sha256": "",
            "reviewer_identity": "Arkadiy Miteiko",
            "review_utc": "2026-07-31T00:00:00Z",
            "rationale": "owner says this is cleared",
            "owner_disposition_reference": "OIC-OWNER-DECISION-999",
        }
    ]
    failures = _ledger_scope_failures(mutated)
    assert any("evidence_reference" in failure for failure in failures)
    assert ledger["transition_rule"]["owner_assertion_alone_is_insufficient"] is True


def test_mutation_changed_disposition_fails(ledger: dict[str, Any]) -> None:
    mutated = copy.deepcopy(ledger)
    mutated["rows"][0]["current_rights_disposition"] = "CLEAR_REPOSITORY_FREEZE"
    assert any(
        "no longer reads BLOCKED_PENDING_CLEARANCE" in failure
        for failure in _ledger_scope_failures(mutated)
    )


def test_mutation_mismatched_english_french_scope_fails(permission: dict[str, Any]) -> None:
    mutated = copy.deepcopy(permission)
    mutated["permission_categories"][5]["fr"]["text"] = ""

    def scope_failures(document: dict[str, Any]) -> list[str]:
        return [
            category["category_id"]
            for category in document["permission_categories"]
            if not category["en"]["text"].strip() or not category["fr"]["text"].strip()
        ]

    assert scope_failures(permission) == []
    assert scope_failures(mutated) == ["public_repository_redistribution"]


def _source_byte_failures(directory: Path) -> list[str]:
    """A dossier directory may hold canonical JSON and rendered Markdown, nothing else."""
    return [
        path.name
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix.lower() not in {".json", ".md"}
    ]


def test_mutation_added_source_byte_fails(repo_root: Path, tmp_path: Path) -> None:
    assert _source_byte_failures(repo_root / DOSSIER_RELDIR) == []
    staged = tmp_path / "dossier"
    shutil.copytree(repo_root / DOSSIER_RELDIR, staged)
    (staged / "CA-6-CH6.html").write_bytes(b"<html></html>")
    assert _source_byte_failures(staged) == ["CA-6-CH6.html"]


def _manifest_failures(text: str) -> list[str]:
    """No unresolved source may hold a manifest row while it is BLOCKED_PENDING_CLEARANCE."""
    rows = text.strip().splitlines()[1:]
    return sorted(row.split(",", 1)[0] for row in rows if row.split(",", 1)[0] in set(UNRESOLVED))


def test_mutation_added_source_manifest_row_fails(repo_root: Path) -> None:
    real = (repo_root / MANIFEST_RELPATH).read_text(encoding="utf-8")
    assert _manifest_failures(real) == []
    assert _manifest_failures(real + "CA-1,planted,,,,,,,,,,,\n") == ["CA-1"]
