from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_source_manifest.py"

MODULE_NAME = "_test_corpus_rights_provenance_preflight_001"
spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)

HEADER = module.load_contract()["header_order"]


def write_manifest(path: Path, rows: Iterable[dict[str, str]], header=None) -> None:
    fields = HEADER if header is None else header
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def valid_row(source_id: str = "SRC-001") -> dict[str, str]:
    return {
        "source_id": source_id,
        "source_kind": "synthetic",
        "source_locator": f"synthetic:oic:{source_id.lower()}",
        "local_path": f"tests/fixtures/{source_id.lower()}.txt",
        "content_hash": "sha256:" + ("a" * 64),
        "rights_basis": "synthetic_owned",
        "rights_evidence": "https://example.invalid/evidence/rights",
        "rights_status": "verified",
        "provenance_evidence": "https://example.invalid/evidence/provenance",
        "provenance_status": "verified",
        "redistribution_status": "permitted",
        "acquired_or_generated_at": "2026-09-02T12:00:00-04:00",
        "notes": "",
    }


def codes(result) -> set[str]:
    return {x.code for x in result.findings}


def test_contract_identity_and_boundaries() -> None:
    c = module.load_contract()

    assert c["contract_id"] == "OIC-SOURCE-MANIFEST-CONTRACT-001"
    assert c["contract_version"] == "v0.1"
    assert c["manifest_path"] == "SOURCE_MANIFEST.csv"
    assert c["provider_call_authorized"] is False
    assert c["model_call_authorized"] is False
    assert c["network_access_authorized"] is False
    assert c["canonicalization_authorized"] is False
    assert c["institutional_ir_authorized"] is False
    assert c["control_envelope_authorized"] is False
    assert c["runtime_authorized"] is False


def test_missing_real_manifest_fails_closed(tmp_path: Path) -> None:
    result = module.validate_manifest(
        tmp_path / "SOURCE_MANIFEST.csv",
        expected_source_ids=["SRC-001"],
    )
    assert result.disposition == "FAIL_CLOSED"
    assert "MANIFEST_ABSENT" in codes(result)


def test_expected_population_is_mandatory(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row()])

    result = module.validate_manifest(path, expected_source_ids=None)

    assert result.disposition == "FAIL_CLOSED"
    assert "EXPECTED_POPULATION_REQUIRED" in codes(result)


def test_empty_expected_population_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row()])

    result = module.validate_manifest(path, expected_source_ids=[])

    assert result.disposition == "FAIL_CLOSED"
    assert "EXPECTED_POPULATION_INVALID" in codes(result)


def test_duplicate_expected_population_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row()])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001", "SRC-001"],
    )

    assert result.disposition == "FAIL_CLOSED"
    assert "EXPECTED_POPULATION_DUPLICATE" in codes(result)


def test_exact_valid_synthetic_manifest_passes_shape_only(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row()])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "PASS"
    assert result.findings == ()
    assert result.rights_established is False
    assert result.provenance_established is False
    assert result.legal_clearance_established is False


def test_header_order_mismatch_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    header = list(HEADER)
    header[0], header[1] = header[1], header[0]
    write_manifest(path, [valid_row()], header=header)

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "FAIL_CLOSED"
    assert "HEADER_MISMATCH" in codes(result)


def test_no_data_rows_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "FAIL_CLOSED"
    assert "MANIFEST_EMPTY" in codes(result)


def test_duplicate_source_id_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row(), valid_row()])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "FAIL_CLOSED"
    assert "DUPLICATE_SOURCE_ID" in codes(result)


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("source_id", "REQUIRED_FIELD_EMPTY"),
        ("source_locator", "REQUIRED_FIELD_EMPTY"),
        ("rights_evidence", "REQUIRED_FIELD_EMPTY"),
        ("provenance_evidence", "REQUIRED_FIELD_EMPTY"),
    ],
)
def test_required_field_empty_fails_closed(
    tmp_path: Path,
    field: str,
    code: str,
) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row[field] = ""
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "FAIL_CLOSED"
    assert code in codes(result)


def test_unsupported_source_kind_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["source_kind"] = "private"
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "UNSUPPORTED_SOURCE_KIND" in codes(result)


@pytest.mark.parametrize(
    "bad_hash",
    [
        "sha256:" + ("A" * 64),
        "sha256:" + ("a" * 63),
        "md5:" + ("a" * 64),
        "a" * 64,
    ],
)
def test_invalid_content_hash_fails_closed(
    tmp_path: Path,
    bad_hash: str,
) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["content_hash"] = bad_hash
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "INVALID_CONTENT_HASH" in codes(result)


@pytest.mark.parametrize("bad_path", ["/tmp/source.pdf", "../source.pdf", "x/../../y"])
def test_invalid_local_path_fails_closed(tmp_path: Path, bad_path: str) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["local_path"] = bad_path
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "INVALID_LOCAL_PATH" in codes(result)


@pytest.mark.parametrize("status", ["unverified", "rejected"])
def test_rights_must_be_verified(tmp_path: Path, status: str) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["rights_status"] = status
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "RIGHTS_NOT_VERIFIED" in codes(result)


@pytest.mark.parametrize("status", ["unverified", "rejected"])
def test_provenance_must_be_verified(tmp_path: Path, status: str) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["provenance_status"] = status
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "PROVENANCE_NOT_VERIFIED" in codes(result)


def test_redistribution_unknown_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["redistribution_status"] = "unknown"
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "REDISTRIBUTION_UNKNOWN" in codes(result)


def test_not_permitted_does_not_by_itself_fail(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["redistribution_status"] = "not_permitted"
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert result.disposition == "PASS"


@pytest.mark.parametrize(
    "field",
    ["rights_evidence", "provenance_evidence"],
)
def test_bad_evidence_reference_fails_closed(
    tmp_path: Path,
    field: str,
) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row[field] = "../untracked-evidence.txt"
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "INVALID_EVIDENCE_REFERENCE" in codes(result)


def test_invalid_datetime_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    row = valid_row()
    row["acquired_or_generated_at"] = "2026-09-02"
    write_manifest(path, [row])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "INVALID_ACQUIRED_OR_GENERATED_AT" in codes(result)


def test_population_missing_source_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row("SRC-001")])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001", "SRC-002"],
    )

    assert "POPULATION_MISSING_SOURCES" in codes(result)


def test_population_undeclared_source_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row("SRC-001"), valid_row("SRC-002")])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )

    assert "POPULATION_UNDECLARED_SOURCES" in codes(result)


def test_validator_does_not_claim_rights_or_provenance(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    write_manifest(path, [valid_row()])

    result = module.validate_manifest(
        path,
        expected_source_ids=["SRC-001"],
    )
    doc = module.result_document(result)

    assert doc["disposition"] == "PASS"
    assert doc["rights_established"] is False
    assert doc["provenance_established"] is False
    assert doc["legal_clearance_established"] is False


def test_real_source_manifest_remains_absent() -> None:
    assert not (ROOT / "SOURCE_MANIFEST.csv").exists()


def test_no_provider_or_network_dependencies() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "requests." not in text
    assert "urllib.request" not in text
    assert "httpx" not in text
    assert "openai" not in text.lower()
    assert "nvidia" not in text.lower()
    assert "NvidiaNimProvider" not in text
