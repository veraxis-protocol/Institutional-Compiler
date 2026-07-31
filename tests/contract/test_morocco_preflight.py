"""Contract tests for the Morocco official-source and real-mission preflight."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = ROOT / "benchmarks/corpus/morocco/preflight-v0.1"
BASE = "29daa374b7e5cdc30ca7788310fbabb85f19912b"
PERMITTED = {
    "tgr.gov.ma",
    "marchespublics.gov.ma",
    "sgg.gov.ma",
    "courdescomptes.ma",
    "govtech.trustvalley.swiss",
    "worldbank.org",
}
LEGAL_CLEARANCE = "LEGALLY_CLEARED"


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((PREFLIGHT / name).read_text(encoding="utf-8")))


def validate(
    register: dict[str, Any], candidates: dict[str, Any], scorecard: dict[str, Any]
) -> None:
    sources = register["sources"]
    ids = [source["source_id"] for source in sources]
    assert len(ids) == len(set(ids))
    assert LEGAL_CLEARANCE not in register["engineering_dispositions"]
    for source in sources:
        assert source["language"]
        for key in ("canonical_url", "download_url"):
            if source[key] is not None:
                host = (urlparse(source[key]).hostname or "").removeprefix("www.")
                assert host in PERMITTED
        assert source["engineering_disposition"] in register["engineering_dispositions"]
        assert source["engineering_disposition"] != LEGAL_CLEARANCE
        if source["language"] == "en":
            assert source["translation_status"]
        if source["translation_status"] == "UNOFFICIAL_TRANSLATION_COMPANION":
            assert "NORMATIVE_TEXT" not in source["authority_rank"]

    cases = candidates["candidates"]
    assert 3 <= len(cases) <= 7
    assert all(not case["synthetic"] for case in cases)
    assert all(case["login_requirement_for_page"] != "REQUIRED" for case in cases)
    assert all(case["associated_public_objects"] for case in cases)
    assert all(case["state"] for case in cases)
    assert all(
        case["publication_date"] and "UNRESOLVED" not in case["publication_date"] for case in cases
    )

    dimensions = scorecard["dimensions"]
    assert len(dimensions) == 14
    assert len(scorecard["scores"]) == len(cases)
    assert (
        sum(score["nomination"] == "PREFERRED_MAR-MISSION-001" for score in scorecard["scores"])
        == 1
    )
    assert sum(score["nomination"] == "FALLBACK" for score in scorecard["scores"]) == 1
    for score in scorecard["scores"]:
        assert len(score["values"]) == len(dimensions)
        assert all(value in {0, 1, 2} for value in score["values"])
        assert score["total"] == sum(score["values"])
        if score["nomination"] in {"PREFERRED_MAR-MISSION-001", "FALLBACK"}:
            assert score["mandatory_minimum"]


@pytest.fixture
def bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        load("OFFICIAL-SOURCE-REGISTER-v0.1.json"),
        load("PMP-MISSION-CANDIDATES-v0.1.json"),
        load("MISSION-SELECTION-SCORECARD-v0.1.json"),
    )


def test_bundle_contract(bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any]]) -> None:
    validate(*bundle)


def test_deterministic_renderings_are_current() -> None:
    result = subprocess.run(
        [sys.executable, "tools/render_morocco_preflight.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_source_bytes_committed() -> None:
    allowed = {".json", ".md"}
    assert all(path.suffix in allowed for path in PREFLIGHT.iterdir())
    decision = load("PREFLIGHT-DECISION-v0.1.json")
    assert decision["no_source_bytes_acquired"] is True


def test_protected_artifacts_unchanged() -> None:
    paths = ["STATUS.md", "schemas/draft", "benchmarks/corpus/canada"]
    result = subprocess.run(["git", "diff", "--quiet", BASE, "--", *paths], cwd=ROOT, check=False)
    assert result.returncode == 0


def test_no_semantic_artifact_created() -> None:
    decision = load("PREFLIGHT-DECISION-v0.1.json")
    assert decision["no_semantic_processing"] is True
    assert decision["semantic_implementation_gate"] == "BLOCKED"
    forbidden = ("institutional-ir", "control-envelope", "warrant", "veip")
    added = subprocess.run(
        ["git", "diff", "--name-only", BASE], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.lower()
    assert not any(token in added for token in forbidden)


def test_source_mutations_fail(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "third_party",
        "authoritative_translation",
        "duplicate_id",
        "missing_language",
        "legal_clearance",
    )
    for mutation in mutations:
        register, candidates, scorecard = copy.deepcopy(bundle)
        if mutation == "third_party":
            register["sources"][0]["canonical_url"] = "https://example.com/mirror.pdf"
        elif mutation == "authoritative_translation":
            register["sources"][1]["authority_rank"] = "OFFICIAL_NORMATIVE_TEXT"
        elif mutation == "duplicate_id":
            register["sources"][1]["source_id"] = register["sources"][0]["source_id"]
        elif mutation == "missing_language":
            register["sources"][0]["language"] = ""
        else:
            register["sources"][0]["engineering_disposition"] = LEGAL_CLEARANCE
        with pytest.raises(AssertionError):
            validate(register, candidates, scorecard)


def test_mission_mutations_fail(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "missing_artifact",
        "inflated_score",
        "synthetic",
        "login_required",
        "mandatory_bypass",
    )
    for mutation in mutations:
        register, candidates, scorecard = copy.deepcopy(bundle)
        if mutation == "missing_artifact":
            candidates["candidates"][0]["associated_public_objects"] = []
        elif mutation == "inflated_score":
            scorecard["scores"][0]["total"] += 1
        elif mutation == "synthetic":
            candidates["candidates"][0]["synthetic"] = True
        elif mutation == "login_required":
            candidates["candidates"][0]["login_requirement_for_page"] = "REQUIRED"
        else:
            scorecard["scores"][0]["mandatory_minimum"] = False
        with pytest.raises(AssertionError):
            validate(register, candidates, scorecard)
