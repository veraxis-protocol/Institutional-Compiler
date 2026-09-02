from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/inventory_canada_evidence_vocabulary_001.py"

spec = importlib.util.spec_from_file_location("inventory001", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules["inventory001"] = mod
spec.loader.exec_module(mod)


def records(text: str):
    return mod.inventory_document_text(
        artifact_path="synthetic.json",
        artifact_git_blob_sha="a" * 40,
        text=text,
    )


def test_records_every_object_key_depth_first_document_order():
    rs = records(
        '{"alpha":1,"beta":{"gamma":true,"delta":[{"epsilon":"x"}]},"zeta":null}'
    )

    assert [
        (r.json_pointer, r.key, r.value_type)
        for r in rs
    ] == [
        ("/alpha", "alpha", "number"),
        ("/beta", "beta", "object"),
        ("/beta/gamma", "gamma", "boolean"),
        ("/beta/delta", "delta", "array"),
        ("/beta/delta/0/epsilon", "epsilon", "string"),
        ("/zeta", "zeta", "null"),
    ]


def test_json_pointer_escaping_is_exact():
    rs = records('{"a/b":{"x~y":"v"}}')
    assert rs[0].json_pointer == "/a~1b"
    assert rs[1].json_pointer == "/a~1b/x~0y"
    assert rs[0].key == "a/b"
    assert rs[1].key == "x~y"


def test_array_length_is_recorded_and_elements_traversed():
    rs = records('{"items":[{"a":1},{"b":2}]}')
    assert rs[0].key == "items"
    assert rs[0].value_type == "array"
    assert rs[0].array_length == 2
    assert [r.json_pointer for r in rs[1:]] == [
        "/items/0/a",
        "/items/1/b",
    ]


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_value"),
    [
        ('{"v":null}', "null", None),
        ('{"v":true}', "boolean", True),
        ('{"v":12}', "number", 12),
        ('{"v":12.5}', "number", 12.5),
        ('{"v":"hello"}', "string", "hello"),
    ],
)
def test_short_scalar_capture_is_exact(
    text: str,
    expected_type: str,
    expected_value,
):
    r = records(text)[0]
    assert r.value_type == expected_type
    assert r.scalar_mode == "EXACT"
    assert r.scalar_value == expected_value
    assert r.scalar_sha256 is None
    assert r.scalar_utf8_byte_length is None


def test_string_length_exact_boundary_256_characters():
    value = "x" * 256
    r = records('{"v":"' + value + '"}')[0]
    assert r.scalar_mode == "EXACT"
    assert r.scalar_value == value


def test_long_string_is_hash_and_utf8_byte_length_only():
    value = "é" * 257
    r = records('{"v":"' + value + '"}')[0]

    assert r.scalar_mode == "SHA256_AND_UTF8_BYTE_LENGTH_ONLY"
    assert r.scalar_value is None
    assert r.scalar_sha256 is not None
    assert r.scalar_utf8_byte_length == len(value.encode("utf-8"))


def test_duplicate_exact_key_fails_closed():
    with pytest.raises(mod.DuplicateKeyError):
        records('{"a":1,"a":2}')


def test_case_distinct_keys_are_not_normalized():
    rs = records('{"Rights":1,"rights":2}')
    assert [r.key for r in rs] == ["Rights", "rights"]


def test_no_alias_or_semantic_mapping_surface():
    _contract, _freeze, _allow = mod.load_controls()
    result_keys = set(mod.execute_inventory.__annotations__)

    # Static API surface is descriptive; no mapping function exists.
    assert not hasattr(mod, "map_to_manifest")
    assert not hasattr(mod, "create_crosswalk")
    assert "return" in result_keys


def test_static_controls_keep_crosswalk_and_source_xml_closed():
    contract, freeze, _allow = mod.load_controls()

    assert contract["crosswalk_creation_authorized"] is False
    assert contract["source_manifest_creation_authorized"] is False
    assert contract["inspection_scope"]["source_xml"] == "FORBIDDEN"
    assert contract["inspection_scope"]["corroborating_markdown"] == "FORBIDDEN"
    assert contract["inventory_algorithm"]["key_normalization_authorized"] is False
    assert contract["inventory_algorithm"]["alias_generation_authorized"] is False
    assert contract["inventory_algorithm"]["semantic_mapping_authorized"] is False
    assert contract["inventory_algorithm"]["manifest_field_mapping_authorized"] is False

    assert freeze["crosswalk_creation_authorized"] is False
    assert freeze["source_xml_inspection_authorized"] is False
    assert freeze["source_manifest_creation_authorized"] is False
    assert freeze["evidence_contents_inspected_by_this_work_order"] is False


def test_real_source_manifest_remains_absent():
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()
