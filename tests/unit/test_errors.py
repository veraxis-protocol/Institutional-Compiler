"""Tests for the infrastructure error taxonomy."""

from __future__ import annotations

import pytest

from oic.errors import (
    ConfigurationError,
    ContractViolationError,
    DependencyUnavailableError,
    ErrorCategory,
    HashMismatchError,
    ManifestEntryMissingError,
    ManifestError,
    OICError,
    SchemaDiscoveryError,
    SchemaValidationError,
    UnsafeManifestPathError,
    UnsupportedHashAlgorithmError,
    redact,
)

REQUIRED_TAXONOMY: list[type[OICError]] = [
    OICError,
    ConfigurationError,
    SchemaDiscoveryError,
    SchemaValidationError,
    ManifestError,
    ManifestEntryMissingError,
    HashMismatchError,
    UnsupportedHashAlgorithmError,
    DependencyUnavailableError,
    ContractViolationError,
]


def test_every_required_error_exists_and_subclasses_oicerror() -> None:
    for error_type in REQUIRED_TAXONOMY:
        assert issubclass(error_type, OICError)


def test_error_codes_are_unique_and_stable() -> None:
    codes = [error_type.code for error_type in REQUIRED_TAXONOMY]
    assert len(codes) == len(set(codes)), f"duplicate error codes: {codes}"
    # Codes are a machine-readable contract; changing one is a breaking change.
    assert ConfigurationError.code == "OIC-1001"
    assert SchemaDiscoveryError.code == "OIC-1002"
    assert ManifestError.code == "OIC-1003"
    assert UnsupportedHashAlgorithmError.code == "OIC-1004"
    assert DependencyUnavailableError.code == "OIC-1005"
    assert UnsafeManifestPathError.code == "OIC-1006"
    assert ContractViolationError.code == "OIC-2001"
    assert SchemaValidationError.code == "OIC-2002"
    assert ManifestEntryMissingError.code == "OIC-2003"
    assert HashMismatchError.code == "OIC-2004"


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        (ConfigurationError, ErrorCategory.OPERATOR),
        (SchemaDiscoveryError, ErrorCategory.OPERATOR),
        (ManifestError, ErrorCategory.OPERATOR),
        (UnsupportedHashAlgorithmError, ErrorCategory.OPERATOR),
        (DependencyUnavailableError, ErrorCategory.OPERATOR),
        (UnsafeManifestPathError, ErrorCategory.OPERATOR),
        (ContractViolationError, ErrorCategory.CONTRACT),
        (SchemaValidationError, ErrorCategory.CONTRACT),
        (ManifestEntryMissingError, ErrorCategory.CONTRACT),
        (HashMismatchError, ErrorCategory.CONTRACT),
    ],
)
def test_operator_errors_are_distinguished_from_contract_violations(
    error_type: type[OICError], expected: ErrorCategory
) -> None:
    assert error_type.category is expected


def test_string_form_is_deterministic() -> None:
    first = ConfigurationError("bad root", detail="missing marker")
    second = ConfigurationError("bad root", detail="missing marker")
    assert str(first) == str(second) == "[OIC-1001] bad root (missing marker)"
    assert str(ConfigurationError("bad root")) == "[OIC-1001] bad root"


def test_repr_does_not_include_detail_payload() -> None:
    error = ConfigurationError("bad root", detail="missing marker")
    assert repr(error) == "ConfigurationError(code='OIC-1001', message='bad root')"


def test_cause_is_preserved() -> None:
    original = OSError("disk gone")
    try:
        try:
            raise original
        except OSError as exc:
            raise ManifestError("cannot read manifest") from exc
    except ManifestError as exc:
        assert exc.cause is original
        assert exc.to_dict()["cause_type"] == "OSError"


def test_hash_mismatch_abbreviates_digests_in_message_but_keeps_them_in_payload() -> None:
    expected = "a" * 64
    actual = "b" * 64
    error = HashMismatchError(subject="docs/tdd/x.pdf", expected=expected, actual=actual)
    assert str(error) == (
        "[OIC-2004] digest mismatch for docs/tdd/x.pdf: "
        "expected aaaaaaaaaaaa..., computed bbbbbbbbbbbb..."
    )
    payload = error.to_dict()
    assert payload["expected"] == expected
    assert payload["actual"] == actual


def test_schema_validation_error_reports_path_and_pointer() -> None:
    error = SchemaValidationError(
        "'type' must be a string or array",
        schema_path="schemas/draft/x.schema.json",
        json_pointer="/properties/foo/type",
    )
    assert str(error) == (
        "[OIC-2002] schemas/draft/x.schema.json/properties/foo/type: "
        "'type' must be a string or array"
    )
    payload = error.to_dict()
    assert payload["schema_path"] == "schemas/draft/x.schema.json"
    assert payload["json_pointer"] == "/properties/foo/type"


def test_schema_validation_error_uses_hash_for_document_root() -> None:
    error = SchemaValidationError("bad", schema_path="a.json")
    assert str(error) == "[OIC-2002] a.json#: bad"


def test_to_dict_is_json_safe_and_deterministic() -> None:
    error = SchemaDiscoveryError("no schemas found", detail="schemas/draft")
    assert error.to_dict() == {
        "code": "OIC-1002",
        "category": "OPERATOR",
        "message": "no schemas found",
        "detail": "schemas/draft",
        "cause_type": None,
    }


def test_redact_never_returns_the_value() -> None:
    assert redact("hunter2") == "<redacted>"
    assert redact(None) == "<redacted>"


def test_no_semantic_error_classes_are_defined() -> None:
    """The bounded slice does not introduce authority or admission errors."""
    import oic.errors as errors_module

    forbidden = {
        "InvalidAuthority",
        "IncorrectInterpretation",
        "LegalConflict",
        "AdmissionError",
        "AuthorityError",
        "InterpretationError",
    }
    assert forbidden.isdisjoint(dir(errors_module))
