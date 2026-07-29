"""Typed error taxonomy for infrastructure and contract validation.

Scope discipline
----------------
These errors describe *infrastructure* and *contract* failures only: configuration,
discovery, schema well-formedness, manifest integrity, and hashing. They deliberately do
not describe institutional meaning. No error in this module may be used to assert that a
document was misinterpreted, that an authority is invalid, or that a legal conflict
exists; those are semantic concerns and the semantic gate is BLOCKED.

Categories
----------
``ErrorCategory.OPERATOR``
    The caller's environment, arguments, or configuration are wrong. The operator can fix
    it. Nothing about the repository contract is implicated.
``ErrorCategory.CONTRACT``
    A governing repository artifact does not hold: a schema is not valid, a manifest entry
    is missing, a digest does not match. The operator usually cannot fix this alone.
``ErrorCategory.INTERNAL``
    A defect in this package. Should not occur in normal operation.

Redaction
---------
Error messages carry paths, identifiers, digests, and counts. They never carry file
contents, environment variable values, or credential material. ``detail`` fields are
constructed by callers and are expected to honour that rule; ``redact`` is provided for
values that may be sensitive.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "ConfigurationError",
    "ContractViolationError",
    "DependencyUnavailableError",
    "ErrorCategory",
    "HashMismatchError",
    "ManifestEntryMissingError",
    "ManifestError",
    "OICError",
    "SchemaDiscoveryError",
    "SchemaValidationError",
    "UnsafeManifestPathError",
    "UnsupportedHashAlgorithmError",
    "redact",
]

_REDACTED = "<redacted>"
_DIGEST_PREVIEW_CHARS = 12


def redact(value: str | None) -> str:
    """Return a placeholder standing in for a value that must not be printed.

    The argument is accepted and discarded so call sites read naturally at the point
    where the sensitive value would otherwise have been interpolated.
    """
    del value
    return _REDACTED


def abbreviate_digest(digest: str) -> str:
    """Shorten a digest for messages while keeping it recognisable.

    Digests are not secret, but full 64-character hex strings make CLI output hard to
    scan. Mismatch errors carry both abbreviated forms so the difference is visible.
    """
    if len(digest) <= _DIGEST_PREVIEW_CHARS:
        return digest
    return f"{digest[:_DIGEST_PREVIEW_CHARS]}..."


class ErrorCategory(Enum):
    """Who is responsible for a failure."""

    OPERATOR = "OPERATOR"
    CONTRACT = "CONTRACT"
    INTERNAL = "INTERNAL"


class OICError(Exception):
    """Base class for every error raised by this package.

    Subclasses declare a stable machine-readable ``code`` and a ``category``. The string
    form is deterministic and safe to print from the CLI.
    """

    code: str = "OIC-0001"
    category: ErrorCategory = ErrorCategory.INTERNAL

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"[{self.code}] {self.message} ({self.detail})"
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"

    @property
    def cause(self) -> BaseException | None:
        """The underlying exception, when this error wraps one."""
        return self.__cause__

    def to_dict(self) -> dict[str, str | None]:
        """Deterministic mapping suitable for ``--format json`` output."""
        return {
            "code": self.code,
            "category": self.category.value,
            "message": self.message,
            "detail": self.detail,
            "cause_type": type(self.__cause__).__name__ if self.__cause__ else None,
        }


# ---------------------------------------------------------------------------
# Operator / configuration errors
# ---------------------------------------------------------------------------


class ConfigurationError(OICError):
    """The caller supplied an unusable path, argument, or environment."""

    code = "OIC-1001"
    category = ErrorCategory.OPERATOR


class SchemaDiscoveryError(OICError):
    """A schema directory is absent, unreadable, or contains no schema files."""

    code = "OIC-1002"
    category = ErrorCategory.OPERATOR


class ManifestError(OICError):
    """A manifest could not be read or parsed as its declared format."""

    code = "OIC-1003"
    category = ErrorCategory.OPERATOR


class UnsupportedHashAlgorithmError(OICError):
    """An algorithm other than SHA-256 was requested.

    v0.1 supports SHA-256 only. Widening this is a contract change, not an
    implementation detail.
    """

    code = "OIC-1004"
    category = ErrorCategory.OPERATOR


class DependencyUnavailableError(OICError):
    """A required local tool or library is not present.

    Absence is reported, never inferred as a negative result about the dependency.
    """

    code = "OIC-1005"
    category = ErrorCategory.OPERATOR


class UnsafeManifestPathError(ManifestError):
    """A manifest entry names a path that will not be resolved.

    Rejected forms: absolute paths, parent-directory traversal, drive-qualified paths,
    URIs with a scheme, and paths that resolve outside the repository root (including via
    symlink). The path is refused rather than sanitised.
    """

    code = "OIC-1006"
    category = ErrorCategory.OPERATOR


# ---------------------------------------------------------------------------
# Contract violations
# ---------------------------------------------------------------------------


class ContractViolationError(OICError):
    """A governing repository artifact does not hold."""

    code = "OIC-2001"
    category = ErrorCategory.CONTRACT


class SchemaValidationError(ContractViolationError):
    """A schema is not a valid JSON Schema Draft 2020-12 document.

    This concerns the schema document itself, not any institutional instance data.
    """

    code = "OIC-2002"
    category = ErrorCategory.CONTRACT

    def __init__(
        self,
        message: str,
        *,
        schema_path: str,
        json_pointer: str = "",
        detail: str | None = None,
    ) -> None:
        super().__init__(message, detail=detail)
        self.schema_path = schema_path
        self.json_pointer = json_pointer

    def __str__(self) -> str:
        pointer = self.json_pointer or "#"
        base = f"[{self.code}] {self.schema_path}{pointer}: {self.message}"
        return f"{base} ({self.detail})" if self.detail else base

    def to_dict(self) -> dict[str, str | None]:
        payload = super().to_dict()
        payload["schema_path"] = self.schema_path
        payload["json_pointer"] = self.json_pointer
        return payload


class ManifestEntryMissingError(ContractViolationError):
    """A manifest names a file that is not present in the working tree."""

    code = "OIC-2003"
    category = ErrorCategory.CONTRACT


class HashMismatchError(ContractViolationError):
    """A file's computed digest does not equal its recorded digest."""

    code = "OIC-2004"
    category = ErrorCategory.CONTRACT

    def __init__(
        self,
        *,
        subject: str,
        expected: str,
        actual: str,
        detail: str | None = None,
    ) -> None:
        message = (
            f"digest mismatch for {subject}: "
            f"expected {abbreviate_digest(expected)}, computed {abbreviate_digest(actual)}"
        )
        super().__init__(message, detail=detail)
        self.subject = subject
        self.expected = expected
        self.actual = actual

    def to_dict(self) -> dict[str, str | None]:
        payload = super().to_dict()
        payload["subject"] = self.subject
        payload["expected"] = self.expected
        payload["actual"] = self.actual
        return payload
