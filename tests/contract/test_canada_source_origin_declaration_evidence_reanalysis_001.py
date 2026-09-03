from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/reanalyze_canada_source_origin_declaration_evidence_001.py"

spec = importlib.util.spec_from_file_location("sourceorigin001", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules["sourceorigin001"] = m
spec.loader.exec_module(m)


def eval_fixture(headers=(), body=b""):
    declarations = m.collect_declarations(headers, body)
    return m.evaluate_declarations(
        declarations,
        publisher_response_bound_to_ca3=True,
        raw_integrity_bound=True,
    )


def test_bound_real_bytes_verify_without_semantic_read():
    m.verify_bound_input_bytes_only()


def test_frozen_allowed_values_exact():
    assert m.ALLOWED_VALUES == {"public", "synthetic"}


def test_header_source_kind_public_is_established():
    result = eval_fixture([["Source-Kind", " public "]])
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "public"
    assert result["source_kind_value_established"] is True
    assert result["declaration_value_created_by_oic"] is False


def test_header_x_source_kind_synthetic_casefold_is_established():
    result = eval_fixture([["X-Source-Kind", "SYNTHETIC"]])
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "synthetic"


def test_content_type_does_not_count():
    result = eval_fixture([["Content-Type", "application/xml"]])
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["declaration_count"] == 0


def test_xml_element_explicit_public_is_established():
    result = eval_fixture(
        body=b"<record><source_kind>public</source_kind></record>"
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "public"


def test_xml_sourceKind_element_is_established():
    result = eval_fixture(
        body=b"<record><sourceKind>synthetic</sourceKind></record>"
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "synthetic"


def test_xml_attribute_explicit_public_is_established():
    result = eval_fixture(
        body=b'<record source-kind="public">x</record>'
    )
    assert result["outcome"] == m.ESTABLISHED


def test_namespaced_xml_local_name_is_recognized():
    result = eval_fixture(
        body=(
            b'<r xmlns:x="urn:test"><x:source_kind>'
            b'public</x:source_kind></r>'
        )
    )
    assert result["outcome"] == m.ESTABLISHED


def test_html_meta_explicit_source_kind_is_established():
    result = eval_fixture(
        body=(
            b'<html><head><meta name="source_kind" '
            b'content="public"></head></html>'
        )
    )
    assert result["outcome"] == m.ESTABLISHED


def test_html_element_explicit_source_kind_is_established():
    result = eval_fixture(
        body=b"<html><body><source-kind>public</source-kind></body></html>"
    )
    assert result["outcome"] == m.ESTABLISHED


def test_html_attribute_explicit_source_kind_is_established():
    result = eval_fixture(
        body=b'<html><body><div source_kind="synthetic"></div></body></html>'
    )
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "synthetic"


def test_exact_label_colon_public_is_established():
    result = eval_fixture(body=b"source_kind: public\n")
    assert result["outcome"] == m.ESTABLISHED


def test_exact_label_equals_synthetic_is_established():
    result = eval_fixture(body=b"source-kind = synthetic;")
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_kind_value_observed"] == "synthetic"


def test_source_kind_synonym_is_not_normalized():
    result = eval_fixture(body=b"source_kind: official\n")
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_government_official_regulation_words_do_not_count():
    result = eval_fixture(
        body=(
            b"Official Government of Canada Regulation. "
            b"This material is publicly accessible."
        )
    )
    assert result["outcome"] == m.NOT_ESTABLISHED
    assert result["declaration_count"] == 0


def test_xml_regulation_root_does_not_count():
    result = eval_fixture(body=b"<Regulation><Title>Law</Title></Regulation>")
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_filename_or_url_text_does_not_count():
    result = eval_fixture(
        body=b"https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml"
    )
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_jsonld_type_and_id_do_not_count():
    result = eval_fixture(
        body=(
            b'<script type="application/ld+json">'
            b'{"@type":"GovernmentDocument","@id":"https://example.invalid/x"}'
            b"</script>"
        )
    )
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_open_graph_generic_type_does_not_count():
    result = eval_fixture(
        body=b'<meta property="og:type" content="article">'
    )
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_invalid_explicit_value_does_not_count():
    result = eval_fixture(body=b"source kind: PUBLIC_DOCUMENT\n")
    assert result["outcome"] == m.NOT_ESTABLISHED


def test_duplicate_same_value_declarations_fail_closed():
    result = eval_fixture(
        [["Source-Kind", "public"]],
        b"source_kind: public\n",
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["declaration_count"] == 2
    assert result["source_kind_value_established"] is False
    assert result["finding_count"] == 1
    assert "ambiguous" in result["findings"][0]


def test_conflicting_declarations_fail_closed():
    result = eval_fixture(
        [["Source-Kind", "public"]],
        b"source_kind: synthetic\n",
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["declaration_count"] == 2
    assert result["source_kind_value_observed"] is None
    assert result["source_kind_value_established"] is False
    assert "conflicting" in result["findings"][0]


def test_explicit_declaration_without_ca3_publisher_binding_is_incomplete():
    declarations = m.collect_declarations(
        [["Source-Kind", "public"]],
        b"",
    )
    result = m.evaluate_declarations(
        declarations,
        publisher_response_bound_to_ca3=False,
        raw_integrity_bound=True,
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["source_kind_value_observed"] == "public"
    assert result["source_kind_value_established"] is False
    assert result["standing_requirements"]["actor_identity_evidence"] is False
    assert result["standing_requirements"]["ca3_scope_evidence"] is False


def test_explicit_declaration_without_integrity_binding_is_incomplete():
    declarations = m.collect_declarations(
        [["Source-Kind", "public"]],
        b"",
    )
    result = m.evaluate_declarations(
        declarations,
        publisher_response_bound_to_ca3=True,
        raw_integrity_bound=False,
    )
    assert result["outcome"] == m.INCOMPLETE
    assert result["source_kind_value_established"] is False
    assert result["standing_requirements"][
        "act_integrity_or_digest_binding"
    ] is False


def test_zero_declaration_preserves_ca3_and_integrity_but_not_authority():
    result = eval_fixture()
    req = result["standing_requirements"]
    assert req["ca3_scope_evidence"] is True
    assert req["act_integrity_or_digest_binding"] is True
    assert req["actor_identity_evidence"] is False
    assert req["authority_basis_evidence_external_to_oic_evaluator"] is False
    assert req["completed_act_evidence"] is False
    assert req["target_field_scope_evidence"] is False


def test_non_utf8_body_fails_closed_instead_of_guessing():
    try:
        m.collect_declarations([], b"\xff\xfe\x00")
    except ValueError as exc:
        assert "UTF-8" in str(exc)
    else:
        raise AssertionError("non-UTF8 body must fail closed")


def test_source_kind_attribute_does_not_also_count_as_label_value():
    declarations = m.collect_declarations(
        [],
        b'<record source_kind="public">x</record>',
    )
    assert len(declarations) == 1
    assert declarations[0].evidence_type == (
        "MARKUP_EXPLICIT_SOURCE_KIND_ATTRIBUTE"
    )


def test_source_kind_element_does_not_also_count_as_label_value():
    declarations = m.collect_declarations(
        [],
        b"<record><source_kind>public</source_kind></record>",
    )
    assert len(declarations) == 1
    assert declarations[0].evidence_type == (
        "MARKUP_EXPLICIT_SOURCE_KIND_ELEMENT"
    )


def test_established_result_never_authorizes_manifest_population():
    result = eval_fixture([["Source-Kind", "public"]])
    assert result["outcome"] == m.ESTABLISHED
    assert result["source_manifest_population_authorized"] is False
    assert result["declaration_value_created_by_oic"] is False
