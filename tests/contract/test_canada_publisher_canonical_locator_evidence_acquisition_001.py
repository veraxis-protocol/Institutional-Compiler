from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/acquire_canada_publisher_canonical_locator_evidence_001.py"

spec = importlib.util.spec_from_file_location("canonical001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["canonical001"] = m
spec.loader.exec_module(m)


def response(
    url="https://laws-lois.justice.gc.ca/page",
    status=200,
    headers=(),
    body=b"",
):
    return m.ResponseRecord(
        request_url=url,
        status=status,
        reason="OK",
        headers=tuple(headers),
        body=body,
    )


def test_bound_bytes_verify_without_navigation_semantic_read():
    m.verify_bound_bytes_only()


def test_navigation_seed_reader_returns_only_allowed_fields():
    doc = {
        "other": {"source_id": "CA-2", "target_url": "https://example.ca/2"},
        "nested": [
            {
                "source_id": "CA-3",
                "target_url": "https://laws-lois.justice.gc.ca/a",
                "final_url": "https://laws-lois.justice.gc.ca/b",
                "rights_status": "MUST_NOT_ESCAPE",
                "publisher": "MUST_NOT_ESCAPE",
            }
        ],
    }
    out = m.extract_ca3_navigation_seed(doc)
    assert out == {
        "source_id": "CA-3",
        "target_url": "https://laws-lois.justice.gc.ca/a",
        "final_url": "https://laws-lois.justice.gc.ca/b",
    }


def test_duplicate_ca3_navigation_seed_fails_closed():
    doc = [
        {"source_id": "CA-3", "target_url": "https://canada.ca/a"},
        {"source_id": "CA-3", "target_url": "https://canada.ca/b"},
    ]
    try:
        m.extract_ca3_navigation_seed(doc)
    except ValueError as exc:
        assert "exactly one CA-3" in str(exc)
    else:
        raise AssertionError("duplicate CA-3 should fail")


def test_navigation_url_prefers_final_url_without_treating_it_as_authority():
    seed = {
        "source_id": "CA-3",
        "target_url": "https://justice.gc.ca/start",
        "final_url": "https://laws-lois.justice.gc.ca/final",
    }
    assert m.choose_navigation_url(seed) == (
        "https://laws-lois.justice.gc.ca/final"
    )


def test_non_https_navigation_url_fails_closed():
    try:
        m.normalize_https_url("http://canada.ca/x")
    except ValueError as exc:
        assert "https" in str(exc)
    else:
        raise AssertionError("http URL should fail")


def test_canada_registrable_domain_handles_gc_ca():
    assert m.registrable_domain("laws-lois.justice.gc.ca") == "justice.gc.ca"
    assert m.registrable_domain("justice.gc.ca") == "justice.gc.ca"
    assert m.same_registrable_domain(
        "laws-lois.justice.gc.ca",
        "www.justice.gc.ca",
    )


def test_canada_registrable_domain_handles_canada_ca():
    assert m.registrable_domain("www.canada.ca") == "canada.ca"


def test_unknown_public_suffix_fails_closed():
    try:
        m.registrable_domain("example.com")
    except ValueError as exc:
        assert "outside frozen Canada" in str(exc)
    else:
        raise AssertionError("non-Canada suffix should fail")


def test_bounded_redirect_accepts_same_registrable_domain():
    records = {
        "https://laws-lois.justice.gc.ca/a": response(
            "https://laws-lois.justice.gc.ca/a",
            302,
            headers=(("Location", "https://www.justice.gc.ca/b"),),
        ),
        "https://www.justice.gc.ca/b": response(
            "https://www.justice.gc.ca/b",
            200,
        ),
    }

    def requester(url, method):
        assert method == "GET"
        return records[url]

    out = m.acquire_with_bounded_redirects(
        "https://laws-lois.justice.gc.ca/a",
        requester=requester,
    )
    assert len(out) == 2
    assert out[-1].request_url == "https://www.justice.gc.ca/b"


def test_bounded_redirect_rejects_cross_registrable_domain():
    def requester(url, method):
        return response(
            url,
            302,
            headers=(("Location", "https://canada.ca/elsewhere"),),
        )

    try:
        m.acquire_with_bounded_redirects(
            "https://laws-lois.justice.gc.ca/a",
            requester=requester,
        )
    except m.AcquisitionError as exc:
        assert "escaped" in str(exc)
    else:
        raise AssertionError("cross-domain redirect should fail")


def test_http_link_header_canonical_is_recognized():
    r = response(
        headers=(
            ("Link", '<https://laws-lois.justice.gc.ca/canon>; rel="canonical"'),
        )
    )
    declarations = m.canonical_declarations(r)
    assert declarations == [{
        "evidence_type": "HTTP_LINK_HEADER_CANONICAL",
        "canonical_url": "https://laws-lois.justice.gc.ca/canon",
    }]


def test_html_link_rel_canonical_is_recognized():
    r = response(
        headers=(("Content-Type", "text/html; charset=utf-8"),),
        body=b'<html><head><link rel="canonical" href="/canon"></head></html>',
    )
    declarations = m.canonical_declarations(r)
    assert declarations == [{
        "evidence_type": "HTML_LINK_REL_CANONICAL",
        "canonical_url": "https://laws-lois.justice.gc.ca/canon",
    }]


def test_open_graph_and_json_ld_do_not_count():
    r = response(
        headers=(("Content-Type", "text/html"),),
        body=(
            b'<meta property="og:url" content="https://laws-lois.justice.gc.ca/c">'
            b'<script type="application/ld+json">'
            b'{"@id":"https://laws-lois.justice.gc.ca/c"}'
            b'</script>'
        ),
    )
    assert m.canonical_declarations(r) == []


def test_missing_canonical_is_not_established():
    result = m.evaluate_final_response([response()])
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["finding_count"] == 0
    assert result["declaration_count"] == 0


def test_unique_header_canonical_same_domain_is_established():
    r = response(
        headers=(
            ("Link", '<https://www.justice.gc.ca/canon>; rel="canonical"'),
        )
    )
    result = m.evaluate_final_response([r])
    assert result["outcome"] == m.ESTABLISHED
    assert result["finding_count"] == 0
    assert all(result["standing_requirements"].values())
    assert result["real_authority_act_created_by_oic"] is False
    assert result["declaration_value_created"] is False
    assert result["source_manifest_population_authorized"] is False


def test_unique_html_canonical_same_domain_is_established():
    r = response(
        headers=(("Content-Type", "text/html"),),
        body=b'<link rel="canonical" href="https://www.justice.gc.ca/canon">',
    )
    result = m.evaluate_final_response([r])
    assert result["outcome"] == m.ESTABLISHED


def test_two_canonical_declarations_even_if_same_url_fail_closed():
    r = response(
        headers=(
            ("Link", '<https://www.justice.gc.ca/c>; rel="canonical"'),
            ("Content-Type", "text/html"),
        ),
        body=b'<link rel="canonical" href="https://www.justice.gc.ca/c">',
    )
    result = m.evaluate_final_response([r])
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["finding_count"] == 1
    assert result["declaration_count"] == 2


def test_cross_domain_canonical_is_not_established():
    r = response(
        headers=(
            ("Link", '<https://canada.ca/canon>; rel="canonical"'),
        )
    )
    result = m.evaluate_final_response([r])
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["finding_count"] > 0


def test_non_https_canonical_is_not_established():
    r = response(
        headers=(
            ("Link", '<http://laws-lois.justice.gc.ca/canon>; rel="canonical"'),
        )
    )
    result = m.evaluate_final_response([r])
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["finding_count"] > 0


def test_unsuccessful_final_response_is_incomplete():
    result = m.evaluate_final_response([response(status=503)])
    assert result["outcome"] == m.INCOMPLETE


def test_publisher_identity_must_be_preexisting_for_established():
    r = response(
        headers=(
            ("Link", '<https://www.justice.gc.ca/canon>; rel="canonical"'),
        )
    )
    result = m.evaluate_final_response(
        [r],
        publisher_identity_preexisting=False,
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["standing_requirements"]["actor_identity_evidence"] is False


def test_response_receipt_hashes_headers_and_body():
    r = response(
        headers=(("Content-Type", "text/html"),),
        body=b"abc",
    )
    receipt = m.response_receipt([r])
    assert receipt["response_count"] == 1
    row = receipt["responses"][0]
    assert row["body_sha256"] == m.sha256_bytes(b"abc")
    assert row["body_bytes"] == 3


def test_started_lock_is_create_once(tmp_path):
    lock = tmp_path / "STARTED.json"
    sha = m.create_started_lock(lock, {"status": "STARTED"})
    assert sha == m.sha256(lock)
    try:
        m.create_started_lock(lock, {"status": "STARTED"})
    except FileExistsError:
        pass
    else:
        raise AssertionError("second STARTED creation must fail")


def test_raw_evidence_writes_digest_bound_files(tmp_path):
    directory = tmp_path / "evidence"
    r = response(
        headers=(("Link", '<https://www.justice.gc.ca/c>; rel="canonical"'),),
        body=b"body",
    )
    evaluation = m.evaluate_final_response([r])
    digests = m.write_raw_evidence(directory, [r], evaluation)
    assert "response-00-headers.json" in digests
    assert "response-00-body.bin" in digests
    assert "parsed-evaluation.json" in digests
    for name, digest in digests.items():
        assert digest == m.sha256(directory / name)


def test_seed_semantic_failure_after_started_returns_structured_incomplete(tmp_path):
    auth = tmp_path / "authorization.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    lock = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"

    def seed_loader(_path):
        return {"not_ca3": True}

    def must_not_acquire(_url):
        raise AssertionError("network acquirer must not run")

    result = m.execute_live(
        auth,
        evidence,
        lock,
        seed_loader=seed_loader,
        acquirer=must_not_acquire,
    )

    assert lock.exists()
    assert result["outcome"] == m.INCOMPLETE
    assert result["status"] == "LIVE_ACQUISITION_EXECUTED_FAIL_CLOSED"
    assert result["navigation_seed_semantics_read"] is True
    assert result["network_request_made"] is False
    assert result["new_real_world_evidence_acquired"] is False
    assert result["seed_metadata"] is None
    assert result["finding_count"] == 1
    assert result["declaration_values_created"] is False
    assert result["source_manifest_population_authorized"] is False


def test_domain_preflight_failure_after_started_is_incomplete_without_network(tmp_path):
    auth = tmp_path / "authorization.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    lock = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"

    def seed_loader(_path):
        return {
            "x": {
                "source_id": "CA-3",
                "target_url": "https://example.com/a",
                "final_url": None,
            }
        }

    def must_not_acquire(_url):
        raise AssertionError("network acquirer must not run")

    result = m.execute_live(
        auth,
        evidence,
        lock,
        seed_loader=seed_loader,
        acquirer=must_not_acquire,
    )

    assert lock.exists()
    assert result["outcome"] == m.INCOMPLETE
    assert result["navigation_seed_semantics_read"] is True
    assert result["network_request_made"] is False
    assert result["new_real_world_evidence_acquired"] is False
    assert result["seed_metadata"]["source_id"] == "CA-3"
    assert "outside frozen Canada" in result["findings"][0]


def test_network_failure_after_request_boundary_is_structured_incomplete(tmp_path):
    auth = tmp_path / "authorization.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    lock = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"

    def seed_loader(_path):
        return {
            "x": {
                "source_id": "CA-3",
                "target_url": "https://laws-lois.justice.gc.ca/a",
                "final_url": None,
            }
        }

    def failing_acquirer(_url):
        raise m.AcquisitionError("synthetic network failure")

    result = m.execute_live(
        auth,
        evidence,
        lock,
        seed_loader=seed_loader,
        acquirer=failing_acquirer,
    )

    assert lock.exists()
    assert result["outcome"] == m.INCOMPLETE
    assert result["navigation_seed_semantics_read"] is True
    assert result["network_request_made"] is True
    assert result["new_real_world_evidence_acquired"] is True
    assert "synthetic network failure" in result["findings"][0]


def test_started_lock_prevents_second_execution_even_after_fail_closed(tmp_path):
    auth = tmp_path / "authorization.json"
    auth.write_text('{"authorized":true}\n', encoding="utf-8")
    lock = tmp_path / "STARTED.json"
    evidence = tmp_path / "evidence"

    def bad_seed(_path):
        return {"bad": True}

    first = m.execute_live(
        auth,
        evidence,
        lock,
        seed_loader=bad_seed,
        acquirer=lambda _url: [],
    )
    assert first["outcome"] == m.INCOMPLETE

    try:
        m.execute_live(
            auth,
            evidence,
            lock,
            seed_loader=bad_seed,
            acquirer=lambda _url: [],
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("consumed STARTED lock must block rerun")
