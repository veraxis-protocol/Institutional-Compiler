"""Contract tests for the Morocco official-source and real-mission preflight."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

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
GATE_CRITERIA = (
    "stable_official_procurement_reference",
    "official_french_notice_or_consultation_record",
    "buyer_and_procedure_metadata",
    "verified_real_tender_document_artifact",
    "verified_award_or_result_or_explicit_open_state",
    "no_login_captcha_or_access_control_bypass",
    "no_synthetic_object",
    "all_urls_on_permitted_official_domain",
)


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((PREFLIGHT / name).read_text(encoding="utf-8")))


def official_url(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("https://"):
        return False
    host = (urlparse(value).hostname or "").removeprefix("www.")
    return host in PERMITTED


def normalized(value: object) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def portal_record_fields(value: object) -> dict[str, str] | None:
    if not official_url(value):
        return None
    parsed = urlparse(cast(str, value))
    query = parse_qs(parsed.query)
    fields = {
        "page": query.get("page", [""])[0],
        "refConsultation": query.get("refConsultation", [""])[0],
        "orgAcronyme": query.get("orgAcronyme", [""])[0],
    }
    return fields if all(fields.values()) else None


def derive_result_linkage(case: dict[str, Any], artifact: dict[str, Any]) -> str:
    linkage = case.get("cross_record_linkage")
    if not isinstance(linkage, dict):
        return "NOT_VERIFIED"
    original_url = linkage.get("original_consultation_url")
    result_url = linkage.get("result_record_url")
    original_fields = portal_record_fields(original_url)
    result_fields = portal_record_fields(result_url)
    if original_fields is None or result_fields is None:
        return "NOT_VERIFIED"
    if original_fields["page"] != "entreprise.EntrepriseDetailConsultation":
        return "NOT_VERIFIED"
    if result_fields["page"] != "entreprise.EntrepriseDetailConsultation":
        return "NOT_VERIFIED"
    if original_url != case.get("official_portal_url"):
        return "NOT_VERIFIED"
    if result_url != artifact.get("exact_official_url"):
        return "NOT_VERIFIED"
    if original_fields["refConsultation"] != linkage.get("original_refConsultation"):
        return "NOT_VERIFIED"
    if result_fields["refConsultation"] != linkage.get("result_refConsultation"):
        return "NOT_VERIFIED"
    if original_fields["refConsultation"] == result_fields["refConsultation"]:
        return "NOT_VERIFIED"

    evidence = linkage.get("evidence_references", [])
    evidence_by_id = {item.get("evidence_id"): item for item in evidence if isinstance(item, dict)}
    expected_evidence_ids = {
        f"{case['candidate_id']}-LINK-ORIGINAL",
        f"{case['candidate_id']}-LINK-RESULT",
    }
    if set(evidence_by_id) != expected_evidence_ids:
        return "NOT_VERIFIED"
    if (
        evidence_by_id[f"{case['candidate_id']}-LINK-ORIGINAL"].get("exact_official_url")
        != original_url
    ):
        return "NOT_VERIFIED"
    if (
        evidence_by_id[f"{case['candidate_id']}-LINK-RESULT"].get("exact_official_url")
        != result_url
    ):
        return "NOT_VERIFIED"

    observed_reference = linkage.get("observed_procurement_reference", {})
    observed_buyer = linkage.get("observed_buyer", {})
    observed_object = linkage.get("observed_procurement_object", {})
    original_buyer = observed_buyer.get("original_record", {})
    result_buyer = observed_buyer.get("result_record", {})
    expected_matches = {
        "procurement_reference": (
            normalized(observed_reference.get("original_record")),
            normalized(observed_reference.get("result_record")),
            normalized(case.get("reference")),
        ),
        "buyer_portal_organization_acronym": (
            normalized(original_buyer.get("portal_organization_acronym")),
            normalized(result_buyer.get("portal_organization_acronym")),
            normalized(original_fields["orgAcronyme"]),
        ),
        "procurement_object": (
            normalized(observed_object.get("original_record")),
            normalized(observed_object.get("result_record")),
            normalized(case.get("title_fr")),
        ),
    }
    matching_fields = linkage.get("normalized_matching_fields", [])
    matching_by_name = {
        item.get("field"): item for item in matching_fields if isinstance(item, dict)
    }
    if set(matching_by_name) != set(expected_matches):
        return "NOT_VERIFIED"
    for field, (original, result, expected) in expected_matches.items():
        stored = matching_by_name[field]
        if not original or original != result or original != expected:
            return "NOT_VERIFIED"
        if normalized(stored.get("original")) != original:
            return "NOT_VERIFIED"
        if normalized(stored.get("result")) != result:
            return "NOT_VERIFIED"
        if set(stored.get("evidence_refs", [])) != expected_evidence_ids:
            return "NOT_VERIFIED"
    if normalized(result_buyer.get("portal_organization_acronym")) != normalized(
        result_fields["orgAcronyme"]
    ):
        return "NOT_VERIFIED"

    mismatches = linkage.get("mismatch_fields", [])
    if len(mismatches) != 1 or mismatches[0].get("field") != "refConsultation":
        return "NOT_VERIFIED"
    mismatch = mismatches[0]
    if mismatch.get("original") != original_fields["refConsultation"]:
        return "NOT_VERIFIED"
    if mismatch.get("result") != result_fields["refConsultation"]:
        return "NOT_VERIFIED"
    if not mismatch.get("recorded_linkage_basis"):
        return "NOT_VERIFIED"
    if set(mismatch.get("evidence_refs", [])) != expected_evidence_ids:
        return "NOT_VERIFIED"
    if not linkage.get("observed_utc"):
        return "NOT_VERIFIED"
    if artifact.get("cross_record_linkage_id") != linkage.get("linkage_id"):
        return "NOT_VERIFIED"
    return "VERIFIED_MATCH"


def iter_urls(value: object, key: str = "") -> Iterator[str]:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from iter_urls(child_value, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from iter_urls(child, key)
    elif isinstance(value, str) and key.endswith("url"):
        yield value


def artifact_access_ok(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("login_required") is False
        and artifact.get("captcha_required") is False
        and artifact.get("access_control_bypass_required") is False
    )


def verified_tender_artifact(case: dict[str, Any], artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type") == "DOSSIER_DE_CONSULTATION_DCE"
        and artifact.get("source_candidate_id") == case.get("candidate_id")
        and official_url(artifact.get("exact_official_url"))
        and bool(artifact.get("public_accessibility_state"))
        and bool(artifact.get("observed_utc"))
        and artifact.get("distinct_from_structured_consultation_record") is True
        and artifact.get("bytes_acquired") is False
    )


def verified_award_artifact(case: dict[str, Any], artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type") == "DEFINITIVE_RESULT_NOTICE"
        and artifact.get("source_candidate_id") == case.get("candidate_id")
        and official_url(artifact.get("exact_official_url"))
        and bool(artifact.get("public_accessibility_state"))
        and bool(artifact.get("observed_utc"))
        and artifact.get("distinct_from_structured_consultation_record") is True
        and artifact.get("bytes_acquired") is False
        and derive_result_linkage(case, artifact) == "VERIFIED_MATCH"
        and case.get("cross_record_linkage", {}).get("linkage_result") == "VERIFIED_MATCH"
        and artifact.get("result_evidence_eligible") is True
    )


def derive_gate(case: dict[str, Any]) -> dict[str, bool]:
    notice = case.get("structured_consultation_record", {})
    tenders = case.get("verified_tender_document_artifacts", [])
    commission = case.get("verified_commission_or_evaluation_artifacts", [])
    awards = case.get("verified_award_or_result_artifacts", [])
    urls = list(iter_urls(case))
    access_objects = [*tenders, *commission, *awards]
    criteria = {
        "stable_official_procurement_reference": bool(case.get("reference"))
        and official_url(case.get("official_portal_url")),
        "official_french_notice_or_consultation_record": notice.get("language") == "fr"
        and notice.get("record_type") == "OFFICIAL_STRUCTURED_CONSULTATION_RECORD"
        and official_url(notice.get("exact_official_url")),
        "buyer_and_procedure_metadata": bool(case.get("public_buyer"))
        and bool(case.get("procedure_type")),
        "verified_real_tender_document_artifact": any(
            verified_tender_artifact(case, artifact) for artifact in tenders
        ),
        "verified_award_or_result_or_explicit_open_state": any(
            verified_award_artifact(case, artifact) for artifact in awards
        )
        or case.get("explicit_official_current_open_state") is True,
        "no_login_captcha_or_access_control_bypass": bool(access_objects)
        and all(artifact_access_ok(artifact) for artifact in access_objects),
        "no_synthetic_object": case.get("synthetic") is False,
        "all_urls_on_permitted_official_domain": bool(urls)
        and all(official_url(url) for url in urls),
    }
    assert tuple(criteria) == GATE_CRITERIA
    return criteria


def validate(
    register: dict[str, Any],
    candidates: dict[str, Any],
    scorecard: dict[str, Any],
    normative: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    sources = register["sources"]
    source_ids = [source["source_id"] for source in sources]
    assert len(source_ids) == len(set(source_ids))
    assert LEGAL_CLEARANCE not in register["engineering_dispositions"]
    for source in sources:
        assert source["language"]
        for key in ("canonical_url", "download_url"):
            if source[key] is not None:
                assert official_url(source[key])
        assert source["engineering_disposition"] in register["engineering_dispositions"]
        assert source["engineering_disposition"] != LEGAL_CLEARANCE
        if source["language"] == "en":
            assert source["translation_status"]
        if source["translation_status"] == "UNOFFICIAL_TRANSLATION_COMPANION":
            assert "NORMATIVE_TEXT" not in source["authority_rank"]

    cases = candidates["candidates"]
    candidate_ids = [case["candidate_id"] for case in cases]
    assert 3 <= len(cases) <= 7
    assert len(candidate_ids) == len(set(candidate_ids))
    assert all(case["publication_date"] for case in cases)
    assert all(case["procurement_category"] == "GOODS_SUPPLIES" for case in cases)
    assert all("mandatory_minimum" not in case for case in cases)

    observations = register["mission_evidence_observations"]
    assert [item["candidate_id"] for item in observations] == candidate_ids
    for observation in observations:
        assert observation["bytes_acquired"] is False
        assert all(official_url(url) for url in iter_urls(observation))

    derived_by_id: dict[str, dict[str, bool]] = {}
    for case in cases:
        criteria = derive_gate(case)
        derived_by_id[case["candidate_id"]] = criteria
        stored = case["mandatory_gate"]
        assert tuple(stored["criteria"]) == GATE_CRITERIA
        assert {
            criterion: result["passed"] for criterion, result in stored["criteria"].items()
        } == criteria
        assert stored["eligible"] is all(criteria.values())
        assert all(
            not artifact["bytes_acquired"]
            for artifact in case["verified_tender_document_artifacts"]
        )

    dimensions = scorecard["dimensions"]
    assert len(dimensions) == 14
    assert len(scorecard["scores"]) == len(cases)
    score_by_id = {score["candidate_id"]: score for score in scorecard["scores"]}
    assert set(score_by_id) == set(candidate_ids)
    award_index = dimensions.index("award_or_result")
    commission_index = dimensions.index("commission_minute_or_extract")
    exact_artifact_index = dimensions.index("exact_byte_downloadable_artifacts")
    suitability_index = dimensions.index("tender_evaluation_award_suitability")
    for case in cases:
        score = score_by_id[case["candidate_id"]]
        assert "mandatory_minimum" not in score
        assert len(score["values"]) == len(dimensions)
        assert all(value in {0, 1, 2} for value in score["values"])
        assert score["total"] == sum(score["values"])
        gate_passed = all(derived_by_id[case["candidate_id"]].values())
        assert score["mandatory_gate_result"] == ("PASS" if gate_passed else "FAIL")
        assert score["gate_evidence_reference"] == f"{case['candidate_id']}#mandatory_gate"
        award_artifacts = case["verified_award_or_result_artifacts"]
        commission_artifacts = case["verified_commission_or_evaluation_artifacts"]
        assert all(verified_award_artifact(case, artifact) for artifact in award_artifacts)
        assert score["values"][award_index] == (2 if award_artifacts else 0)
        assert score["values"][commission_index] == (2 if commission_artifacts else 0)
        assert score["values"][exact_artifact_index] > 0
        assert all(
            verified_tender_artifact(case, artifact)
            for artifact in case["verified_tender_document_artifacts"]
        )
        if not award_artifacts and not commission_artifacts:
            assert score["values"][suitability_index] <= 1
        if score["nomination"] != "NOT_SELECTED":
            assert gate_passed
            assert award_artifacts
            assert all(verified_award_artifact(case, artifact) for artifact in award_artifacts)

    preferred_scores = [
        score for score in scorecard["scores"] if score["nomination"] == "PREFERRED_MAR-MISSION-001"
    ]
    fallback_scores = [score for score in scorecard["scores"] if score["nomination"] == "FALLBACK"]
    if scorecard["selection_outcome"] == "NO_ADMISSIBLE_REAL_CASE":
        assert scorecard["preferred"] is None
        assert scorecard["fallback"] is None
        assert not preferred_scores
        assert not fallback_scores
    else:
        assert scorecard["selection_outcome"] == "ADMISSIBLE_CASES_FOUND"
        assert len(preferred_scores) == 1
        assert len(fallback_scores) == 1
        assert preferred_scores[0]["candidate_id"] == scorecard["preferred"]["candidate_id"]
        assert fallback_scores[0]["candidate_id"] == scorecard["fallback"]["candidate_id"]
        preferred_case = next(
            case for case in cases if case["candidate_id"] == scorecard["preferred"]["candidate_id"]
        )
        fallback_case = next(
            case for case in cases if case["candidate_id"] == scorecard["fallback"]["candidate_id"]
        )
        assert (
            scorecard["preferred"]["result_linkage_result"]
            == preferred_case["cross_record_linkage"]["linkage_result"]
        )
        assert (
            scorecard["fallback"]["result_linkage_result"]
            == fallback_case["cross_record_linkage"]["linkage_result"]
        )

    ccag = next(entry for entry in normative["entries"] if entry["source_id"] == "MAR-CCAG-001")
    assert ccag["role"] == "DISCOVERY_CANDIDATE_NOT_APPLICABLE_TO_CURRENT_MISSION"
    assert ccag["authoritative_for_semantics"] is False
    assert "MAR-CCAG-001" not in normative["proposed_normative_corpus"]
    assert any(
        entry["source_id"] == "MAR-CCAG-001"
        for entry in normative["excluded_from_proposed_normative_corpus"]
    )

    assert decision["pmp_candidate_count"] == len(cases)
    assert scorecard["mission_selection_status"] == "PROVISIONAL_UNRECONCILED"
    assert decision["mission_selection_status"] == "PROVISIONAL_UNRECONCILED"
    assert decision["mission_selection_outcome"] == scorecard["selection_outcome"]
    assert decision["proposed_mission_id"] == scorecard["proposed_mission_id"]
    assert decision["institutional_admission"] == "NONE"
    assert scorecard["institutional_admission"] == "NONE"
    assert decision["golden_mission_status"] == "NOT_ADMITTED"
    assert scorecard["golden_mission_status"] == "NOT_ADMITTED"
    assert decision["cross_repository_reconciliation_required"] is True
    assert scorecard["cross_repository_reconciliation_required"] is True
    assert decision["preferred_mission"]["candidate_id"] == scorecard["preferred"]["candidate_id"]
    assert decision["fallback_mission"]["candidate_id"] == scorecard["fallback"]["candidate_id"]
    assert (
        decision["preferred_mission"]["result_linkage_result"]
        == scorecard["preferred"]["result_linkage_result"]
    )
    assert (
        decision["fallback_mission"]["result_linkage_result"]
        == scorecard["fallback"]["result_linkage_result"]
    )
    assert decision["normative_candidates"] == normative["proposed_normative_corpus"]
    assert decision["no_source_bytes_acquired"] is True
    assert decision["no_tender_document_bytes_acquired"] is True
    assert decision["no_semantic_processing"] is True
    assert decision["semantic_implementation_gate"] == "BLOCKED"
    assert scorecard["semantic_implementation_gate"] == "BLOCKED"


@pytest.fixture
def bundle() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    return (
        load("OFFICIAL-SOURCE-REGISTER-v0.1.json"),
        load("PMP-MISSION-CANDIDATES-v0.1.json"),
        load("MISSION-SELECTION-SCORECARD-v0.1.json"),
        load("NORMATIVE-SOURCE-MAP-v0.1.json"),
        load("PREFLIGHT-DECISION-v0.1.json"),
    )


def test_bundle_contract(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
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
    assert decision["no_tender_document_bytes_acquired"] is True


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
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "third_party",
        "authoritative_translation",
        "duplicate_id",
        "missing_language",
        "legal_clearance",
    )
    for mutation in mutations:
        register, candidates, scorecard, normative, decision = copy.deepcopy(bundle)
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
            validate(register, candidates, scorecard, normative, decision)


def test_existing_mission_mutations_fail(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "missing_artifact",
        "inflated_score",
        "synthetic",
        "login_required",
        "mandatory_bypass",
    )
    for mutation in mutations:
        register, candidates, scorecard, normative, decision = copy.deepcopy(bundle)
        if mutation == "missing_artifact":
            candidates["candidates"][3]["verified_tender_document_artifacts"] = []
        elif mutation == "inflated_score":
            scorecard["scores"][3]["total"] += 1
        elif mutation == "synthetic":
            candidates["candidates"][3]["synthetic"] = True
        elif mutation == "login_required":
            candidates["candidates"][3]["verified_tender_document_artifacts"][0][
                "login_required"
            ] = True
        else:
            candidates["candidates"][3]["mandatory_gate"]["eligible"] = False
        try:
            validate(register, candidates, scorecard, normative, decision)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"mutation survived validation: {mutation}")


def test_evidence_gate_correction_mutations_fail(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "unsupported_manual_mandatory_true",
        "empty_verified_tender_artifacts",
        "structured_notice_only",
        "non_official_tender_url",
        "tender_login_required",
        "award_score_without_award",
        "open_state_as_award_evidence",
        "nomination_with_failed_criterion",
        "preferred_present_under_no_admissible",
        "works_ccag_applicable_without_binding",
        "aggregate_score_overrides_gate",
    )
    for mutation in mutations:
        register, candidates, scorecard, normative, decision = copy.deepcopy(bundle)
        if mutation == "unsupported_manual_mandatory_true":
            scorecard["scores"][3]["mandatory_minimum"] = True
            candidates["candidates"][3]["verified_tender_document_artifacts"] = []
        elif mutation == "empty_verified_tender_artifacts":
            candidates["candidates"][3]["verified_tender_document_artifacts"] = []
        elif mutation == "structured_notice_only":
            case = candidates["candidates"][3]
            case["verified_tender_document_artifacts"] = [
                {
                    "artifact_id": "NOTICE-AS-DCE",
                    "artifact_type": "OFFICIAL_STRUCTURED_CONSULTATION_RECORD",
                    "exact_official_url": case["structured_consultation_record"][
                        "exact_official_url"
                    ],
                    "source_candidate_id": case["candidate_id"],
                    "public_accessibility_state": "PUBLIC_STRUCTURED_HTML",
                    "login_required": False,
                    "captcha_required": False,
                    "access_control_bypass_required": False,
                    "observed_utc": candidates["observed_utc"],
                    "distinct_from_structured_consultation_record": False,
                    "bytes_acquired": False,
                }
            ]
        elif mutation == "non_official_tender_url":
            candidates["candidates"][3]["verified_tender_document_artifacts"][0][
                "exact_official_url"
            ] = "https://example.com/dce"
        elif mutation == "tender_login_required":
            candidates["candidates"][3]["verified_tender_document_artifacts"][0][
                "login_required"
            ] = True
        elif mutation == "award_score_without_award":
            scorecard["scores"][0]["values"][8] = 2
            scorecard["scores"][0]["total"] += 2
        elif mutation == "open_state_as_award_evidence":
            case = candidates["candidates"][0]
            case["verified_award_or_result_artifacts"] = [
                {
                    "artifact_id": "OPEN-STATE",
                    "artifact_type": "OPEN_STATE",
                    "exact_official_url": case["official_portal_url"],
                    "source_candidate_id": case["candidate_id"],
                    "public_accessibility_state": "PUBLIC_STRUCTURED_HTML",
                    "login_required": False,
                    "captcha_required": False,
                    "access_control_bypass_required": False,
                    "observed_utc": candidates["observed_utc"],
                    "distinct_from_structured_consultation_record": False,
                    "bytes_acquired": False,
                }
            ]
            scorecard["scores"][0]["values"][8] = 2
            scorecard["scores"][0]["total"] += 2
        elif mutation == "nomination_with_failed_criterion":
            candidates["candidates"][3]["public_buyer"] = ""
        elif mutation == "preferred_present_under_no_admissible":
            scorecard["selection_outcome"] = "NO_ADMISSIBLE_REAL_CASE"
        elif mutation == "works_ccag_applicable_without_binding":
            next(entry for entry in normative["entries"] if entry["source_id"] == "MAR-CCAG-001")[
                "role"
            ] = "APPLICABLE_TO_CURRENT_MISSION"
        else:
            candidates["candidates"][3]["verified_tender_document_artifacts"] = []
            scorecard["scores"][3]["values"] = [2] * 14
            scorecard["scores"][3]["total"] = 28
        try:
            validate(register, candidates, scorecard, normative, decision)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"mutation survived validation: {mutation}")


def test_result_lineage_mutations_fail(
    bundle: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    mutations = (
        "different_official_result_url",
        "different_result_reference",
        "different_result_buyer",
        "different_result_object",
        "different_ref_without_linkage_basis",
        "manual_verified_unsupported",
        "award_score_for_not_verified",
        "nomination_on_unlinked_result",
    )
    for mutation in mutations:
        register, candidates, scorecard, normative, decision = copy.deepcopy(bundle)
        case = candidates["candidates"][3]
        linkage = case["cross_record_linkage"]
        result = case["verified_award_or_result_artifacts"][0]
        if mutation == "different_official_result_url":
            substituted = (
                "https://www.marchespublics.gov.ma/index.php?"
                "page=entreprise.EntrepriseDetailConsultation&"
                "refConsultation=1029211&orgAcronyme=g0u"
            )
            result["exact_official_url"] = substituted
            linkage["result_record_url"] = substituted
        elif mutation == "different_result_reference":
            linkage["observed_procurement_reference"]["result_record"] = "13/2026"
        elif mutation == "different_result_buyer":
            linkage["observed_buyer"]["result_record"]["portal_organization_acronym"] = "different"
        elif mutation == "different_result_object":
            linkage["observed_procurement_object"]["result_record"] = (
                "Achat de toners pour le compte d'une autre institution"
            )
        elif mutation == "different_ref_without_linkage_basis":
            del linkage["mismatch_fields"][0]["recorded_linkage_basis"]
        elif mutation == "manual_verified_unsupported":
            linkage["normalized_matching_fields"][0]["result"] = "13/2026"
            linkage["linkage_result"] = "VERIFIED_MATCH"
        elif mutation == "award_score_for_not_verified":
            linkage["linkage_result"] = "NOT_VERIFIED"
            result["result_evidence_eligible"] = False
        else:
            linkage["linkage_result"] = "NOT_VERIFIED"
            result["result_evidence_eligible"] = False
            scorecard["scores"][3]["nomination"] = "PREFERRED_MAR-MISSION-001"
        try:
            validate(register, candidates, scorecard, normative, decision)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"mutation survived validation: {mutation}")
