from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/acquire_canada_external_rights_actor_qualification_001.py"

spec = importlib.util.spec_from_file_location("actorqual001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["actorqual001"] = m
spec.loader.exec_module(m)


def rec(
    url: str,
    *,
    status: int = 200,
    body: bytes = b"",
    headers=(),
):
    return m.ResponseRecord(
        requested_url=url,
        final_url=url,
        status=status,
        headers=tuple(headers),
        body=body,
        redirect_count=0,
    )


def good_responses():
    return {
        "JUS-TERMS": rec(
            "https://www.justice.gc.ca/eng/terms-avis/index.html",
            body=(
                b"<html>Department of Justice Canada content and material. "
                b"For permission to reproduce, contact the Communications Branch "
                b"Copyright administrator.</html>"
            ),
        ),
        "JUS-CLEARANCE-FORM": rec(
            "https://www.justice.gc.ca/eng/terms-avis/copyright-droitdauteur.html",
            body=(
                b"<html>Copyright clearance for a Department of Justice Canada work. "
                b"Provide the source URL or web page. All correspondence to the "
                b"Communications Branch Copyright administrator.</html>"
            ),
        ),
        "JUSTICE-LAWS-FAQ": rec(
            "https://laws-lois.justice.gc.ca/eng/FAQ/",
            body=(
                b"<html>The Reproduction of Federal Law Order permits reproduction "
                b"of federal Acts and regulations subject to conditions.</html>"
            ),
        ),
        "FEDERAL-LAW-ORDER": rec(
            "https://laws-lois.justice.gc.ca/eng/regulations/SI-97-5/FullText.html",
            body=(
                b"<html>Reproduction of Federal Law Order. Federal law may be "
                b"reproduced without charge or request for permission provided due "
                b"diligence is exercised to ensure the accuracy of the materials "
                b"reproduced and the reproduction is not represented as an official "
                b"version.</html>"
            ),
        ),
    }


def test_frozen_bytes_verify_without_public_fetch():
    m.verify_frozen_bytes()


def test_allowed_urls_are_exact_https_domains():
    assert m.allowed_url("https://www.justice.gc.ca/eng/terms-avis/index.html")
    assert m.allowed_url("https://justice.gc.ca/x")
    assert m.allowed_url("https://laws-lois.justice.gc.ca/eng/FAQ/")
    assert not m.allowed_url("http://www.justice.gc.ca/x")
    assert not m.allowed_url("https://example.com/x")
    assert not m.allowed_url("https://justice.gc.ca.evil.example/x")
    assert not m.allowed_url("https://user@justice.gc.ca/x")


def test_get_acquirer_allows_redirect_within_frozen_domain_set():
    first = m.ResponseRecord(
        requested_url="https://justice.gc.ca/a",
        final_url="https://justice.gc.ca/a",
        status=302,
        headers=(("Location", "https://www.justice.gc.ca/b"),),
        body=b"",
        redirect_count=0,
    )
    second = rec("https://www.justice.gc.ca/b", body=b"ok")
    calls = []

    def requester(url):
        calls.append(url)
        return first if len(calls) == 1 else second

    records = m.acquire_url("https://justice.gc.ca/a", requester=requester)
    assert len(records) == 2
    assert records[-1].status == 200


def test_get_acquirer_rejects_redirect_outside_allowlist():
    first = m.ResponseRecord(
        requested_url="https://justice.gc.ca/a",
        final_url="https://justice.gc.ca/a",
        status=302,
        headers=(("Location", "https://example.com/out"),),
        body=b"",
        redirect_count=0,
    )

    try:
        m.acquire_url("https://justice.gc.ca/a", requester=lambda _url: first)
    except ValueError as exc:
        assert "outside frozen HTTPS allowlist" in str(exc)
    else:
        raise AssertionError("cross-domain redirect must fail closed")


def test_exact_four_source_population_required():
    responses = good_responses()
    responses.pop("FEDERAL-LAW-ORDER")
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.INCOMPLETE


def test_non_200_source_fails_closed():
    responses = good_responses()
    responses["JUS-TERMS"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/index.html",
        status=404,
        body=b"not found",
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.INCOMPLETE


def test_complete_synthetic_public_surface_supports_candidate_only():
    result = m.evaluate_public_evidence(
        good_responses(),
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.SUPPORTED
    assert result["candidate_actor_qualification_supported"] is True
    assert all(result["qualification_findings"].values())
    assert result["rights_basis_value_observed"] is None
    assert result["redistribution_status_value_observed"] is None
    assert result["rights_disposition_request_send_authorized"] is False
    assert result["external_actor_contact_authorized"] is False
    assert result["source_manifest_population_authorized"] is False


def test_missing_actor_identity_is_not_established():
    responses = good_responses()
    responses["JUS-TERMS"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/index.html",
        body=b"<html>Department of Justice Canada content. Permission to reproduce.</html>",
    )
    responses["JUS-CLEARANCE-FORM"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/copyright-droitdauteur.html",
        body=b"<html>Department of Justice Canada work. Provide source URL.</html>",
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"]["actor_identity_explicit"] is False


def test_missing_reproduction_role_is_not_established():
    responses = good_responses()
    responses["JUS-TERMS"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/index.html",
        body=b"<html>Communications Branch Copyright administrator.</html>",
    )
    responses["JUS-CLEARANCE-FORM"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/copyright-droitdauteur.html",
        body=(
            b"<html>Communications Branch Copyright administrator. "
            b"Department of Justice Canada work. Source URL.</html>"
        ),
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"][
        "copyright_or_reproduction_role_explicit"
    ] is False


def test_clearance_form_must_support_exact_source_url_intake():
    responses = good_responses()
    responses["JUS-CLEARANCE-FORM"] = rec(
        "https://www.justice.gc.ca/eng/terms-avis/copyright-droitdauteur.html",
        body=(
            b"<html>Copyright clearance for a Department of Justice Canada work. "
            b"Communications Branch Copyright administrator.</html>"
        ),
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"]["exact_source_url_intake_supported"] is False


def test_order_must_be_recognized_by_faq_and_authoritative_text():
    responses = good_responses()
    responses["JUSTICE-LAWS-FAQ"] = rec(
        "https://laws-lois.justice.gc.ca/eng/FAQ/",
        body=b"<html>Acts and regulations are available here.</html>",
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"][
        "federal_law_reproduction_order_recognized"
    ] is False


def test_order_requires_accuracy_and_non_official_version_condition():
    responses = good_responses()
    responses["FEDERAL-LAW-ORDER"] = rec(
        "https://laws-lois.justice.gc.ca/eng/regulations/SI-97-5/FullText.html",
        body=(
            b"<html>Reproduction of Federal Law Order. Reproduce without charge "
            b"or permission.</html>"
        ),
    )
    result = m.evaluate_public_evidence(
        responses,
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"]["authority_basis_reference_present"] is False


def test_ca3_binding_must_be_exact_frozen_justice_laws_material():
    result = m.evaluate_public_evidence(
        good_responses(),
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/OTHER.xml",
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["qualification_findings"]["ca3_is_justice_laws_material"] is False


def test_public_qualification_support_never_observes_rights_enums():
    result = m.evaluate_public_evidence(
        good_responses(),
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.SUPPORTED
    assert result["rights_basis_value_observed"] is None
    assert result["redistribution_status_value_observed"] is None


def test_public_qualification_support_never_authorizes_contact_or_manifest():
    result = m.evaluate_public_evidence(
        good_responses(),
        ca3_final_url="https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml",
    )
    assert result["outcome"] == m.SUPPORTED
    assert result["rights_disposition_request_send_authorized"] is False
    assert result["external_actor_contact_authorized"] is False
    assert result["source_manifest_population_authorized"] is False


def test_raw_evidence_writer_sha_binds_headers_and_body(tmp_path):
    records = [
        rec(
            "https://justice.gc.ca/a",
            body=b"hello",
            headers=(("Content-Type", "text/html"),),
        )
    ]
    digests = m.write_raw_evidence(tmp_path, "JUS-TERMS", records)
    assert len(digests) == 2
    for name, digest in digests.items():
        assert m.sha256(tmp_path / name) == digest


def test_started_lock_is_create_once(tmp_path):
    lock = tmp_path / "STARTED.json"
    digest = m.create_started_lock(lock, {"status": "STARTED"})
    assert m.sha256(lock) == digest
    try:
        m.create_started_lock(lock, {"status": "STARTED"})
    except FileExistsError:
        pass
    else:
        raise AssertionError("STARTED lock must be create-once")


def test_live_synthetic_run_is_get_only_and_preserves_no_contact(tmp_path, monkeypatch):
    auth = tmp_path / "AUTH.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    started = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"
    output = tmp_path / "RESULT.json"

    inventory = {
        "sources": [
            {
                "source_id": "JUS-TERMS",
                "url": "https://www.justice.gc.ca/eng/terms-avis/index.html",
            },
            {
                "source_id": "JUS-CLEARANCE-FORM",
                "url": "https://www.justice.gc.ca/eng/terms-avis/copyright-droitdauteur.html",
            },
            {
                "source_id": "JUSTICE-LAWS-FAQ",
                "url": "https://laws-lois.justice.gc.ca/eng/FAQ/",
            },
            {
                "source_id": "FEDERAL-LAW-ORDER",
                "url": "https://laws-lois.justice.gc.ca/eng/regulations/SI-97-5/FullText.html",
            },
        ]
    }
    monkeypatch.setattr(m, "load_inventory", lambda: inventory)
    monkeypatch.setattr(m, "verify_frozen_bytes", lambda: None)

    good = good_responses()

    def requester(url):
        for source_id, response in good.items():
            if response.requested_url == url:
                return response
        raise AssertionError(url)

    result = m.execute_live(
        authorization_receipt=auth,
        started_lock=started,
        evidence_dir=evidence,
        output=output,
        requester=requester,
    )
    assert started.exists()
    assert result["disposition"] == m.SUPPORTED
    assert result["external_actor_contacted"] is False
    assert result["email_sent"] is False
    assert result["form_submitted"] is False
    assert result["rights_disposition_request_sent"] is False


def test_live_failure_after_started_is_terminal_and_no_contact(tmp_path, monkeypatch):
    auth = tmp_path / "AUTH.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    started = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"
    output = tmp_path / "RESULT.json"

    inventory = {
        "sources": [
            {
                "source_id": "JUS-TERMS",
                "url": "https://www.justice.gc.ca/eng/terms-avis/index.html",
            }
        ]
    }
    monkeypatch.setattr(m, "load_inventory", lambda: inventory)
    monkeypatch.setattr(m, "verify_frozen_bytes", lambda: None)

    def requester(_url):
        raise RuntimeError("synthetic transport failure")

    result = m.execute_live(
        authorization_receipt=auth,
        started_lock=started,
        evidence_dir=evidence,
        output=output,
        requester=requester,
    )
    assert started.exists()
    assert result["disposition"] == m.INCOMPLETE
    assert result["external_actor_contacted"] is False
    assert result["email_sent"] is False
    assert result["form_submitted"] is False
    assert result["rights_disposition_request_sent"] is False


def test_started_lock_blocks_rerun(tmp_path, monkeypatch):
    auth = tmp_path / "AUTH.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    started = tmp_path / "STARTED.json"
    started.write_text('{"status":"STARTED"}\n', encoding="utf-8")
    evidence = tmp_path / "evidence"
    output = tmp_path / "RESULT.json"

    monkeypatch.setattr(m, "verify_frozen_bytes", lambda: None)

    try:
        m.execute_live(
            authorization_receipt=auth,
            started_lock=started,
            evidence_dir=evidence,
            output=output,
            requester=lambda _url: None,
        )
    except SystemExit as exc:
        assert "acquisition consumed" in str(exc)
    else:
        raise AssertionError("existing STARTED must block rerun")
