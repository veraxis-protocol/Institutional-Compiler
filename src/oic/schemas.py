"""Offline discovery and validation of the draft JSON Schemas.

Scope
-----
This module checks that each ``*.schema.json`` file *is* a well-formed JSON Schema
Draft 2020-12 document and that every ``$ref`` it contains resolves inside the local
schema set. It does not validate institutional instance data, construct Institutional IR
objects, or attribute meaning to any schema. The semantic gate is BLOCKED.

Offline guarantee
-----------------
All resolution happens through a :class:`referencing.Registry` built solely from files
discovered on disk. The registry has no ``retrieve`` callback, so an unresolvable
reference raises rather than triggering a fetch. The bundled Draft 2020-12 metaschema
ships with ``jsonschema``; validating against it is a local operation.

Reference policy
----------------
A ``$ref`` is classified by the *literal* string written in the schema, not by the URI it
resolves to:

* a relative reference or a bare fragment is a **local** reference and must resolve
  inside the registry;
* a reference written with an ``http``/``https`` scheme is an **external** reference. It
  is permitted only when it happens to be satisfied by a schema already in the registry
  (the draft schemas use absolute ``$id`` values, so sibling references resolve locally).
  Otherwise it is rejected unless ``allow_external_refs=True`` is passed explicitly.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from oic.errors import SchemaDiscoveryError, SchemaValidationError
from oic.paths import relative_to_root

__all__ = [
    "DEFAULT_SCHEMA_DIRECTORY",
    "SCHEMA_SUFFIX",
    "IssueCode",
    "SchemaIssue",
    "SchemaReport",
    "SchemaResult",
    "SchemaStatus",
    "discover_schemas",
    "validate_schema_directory",
]

SCHEMA_SUFFIX: Final[str] = ".schema.json"
DEFAULT_SCHEMA_DIRECTORY: Final[str] = "schemas/draft"

_EXTERNAL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https", "ftp", "ftps"})

# JSON documents are arbitrarily shaped; `Any` is the honest annotation at the boundary.
JsonValue = Any


class SchemaStatus(Enum):
    """Outcome of validating one schema, or a whole directory."""

    PASS = "PASS"  # noqa: S105 - status token, not a credential
    FAIL = "FAIL"


class IssueCode(Enum):
    """Machine-readable classification of a schema defect."""

    UNPARSEABLE_JSON = "UNPARSEABLE_JSON"
    NOT_AN_OBJECT = "NOT_AN_OBJECT"
    INVALID_METASCHEMA = "INVALID_METASCHEMA"
    UNRESOLVED_LOCAL_REF = "UNRESOLVED_LOCAL_REF"
    EXTERNAL_REF_BLOCKED = "EXTERNAL_REF_BLOCKED"
    DUPLICATE_SCHEMA_ID = "DUPLICATE_SCHEMA_ID"
    UNREADABLE = "UNREADABLE"


@dataclass(frozen=True, slots=True)
class SchemaIssue:
    """One defect, located by schema path and JSON pointer."""

    schema_path: str
    json_pointer: str
    code: IssueCode
    message: str

    def to_json(self) -> dict[str, str]:
        return {
            "code": self.code.value,
            "json_pointer": self.json_pointer,
            "message": self.message,
            "schema_path": self.schema_path,
        }

    def render(self) -> str:
        return f"{self.schema_path}{self.json_pointer or '#'}: [{self.code.value}] {self.message}"


@dataclass(frozen=True, slots=True)
class SchemaResult:
    """Validation outcome for a single schema file."""

    schema_path: str
    schema_id: str | None
    title: str | None
    status: SchemaStatus
    issues: tuple[SchemaIssue, ...]

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "issues": [issue.to_json() for issue in self.issues],
            "schema_id": self.schema_id,
            "schema_path": self.schema_path,
            "status": self.status.value,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class SchemaReport:
    """Validation outcome for a whole schema directory."""

    directory: str
    status: SchemaStatus
    results: tuple[SchemaResult, ...]
    external_refs_allowed: bool

    @property
    def issues(self) -> tuple[SchemaIssue, ...]:
        return tuple(issue for result in self.results for issue in result.issues)

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "directory": self.directory,
            "external_refs_allowed": self.external_refs_allowed,
            "results": [result.to_json() for result in self.results],
            "schema_count": len(self.results),
            "status": self.status.value,
        }

    def raise_for_status(self) -> None:
        """Raise the first issue as a :class:`SchemaValidationError`."""
        for issue in self.issues:
            raise SchemaValidationError(
                issue.message,
                schema_path=issue.schema_path,
                json_pointer=issue.json_pointer,
                detail=issue.code.value,
            )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_schemas(directory: Path) -> tuple[Path, ...]:
    """Return every ``*.schema.json`` file under ``directory``, deterministically ordered.

    Ordering is by POSIX relative path so results are identical on every platform and in
    every filesystem enumeration order.

    Raises:
        SchemaDiscoveryError: the directory is missing, is not a directory, or holds no
            schema files.
    """
    if not directory.exists():
        raise SchemaDiscoveryError(
            "schema directory not found",
            detail=directory.as_posix(),
        )
    if not directory.is_dir():
        raise SchemaDiscoveryError(
            "schema path is not a directory",
            detail=directory.as_posix(),
        )

    found = sorted(
        (path for path in directory.rglob(f"*{SCHEMA_SUFFIX}") if path.is_file()),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    if not found:
        raise SchemaDiscoveryError(
            "no schema files found",
            detail=f"{directory.as_posix()} contains no *{SCHEMA_SUFFIX} files",
        )
    return tuple(found)


# ---------------------------------------------------------------------------
# Reference walking
# ---------------------------------------------------------------------------


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _iter_refs(node: JsonValue, pointer: str = "") -> Iterator[tuple[str, str]]:
    """Yield ``(json_pointer, ref_string)`` for every ``$ref`` in the document."""
    if isinstance(node, Mapping):
        for key, value in node.items():
            child_pointer = f"{pointer}/{_escape_pointer_token(str(key))}"
            if key == "$ref" and isinstance(value, str):
                yield child_pointer, value
            else:
                yield from _iter_refs(value, child_pointer)
    elif isinstance(node, Sequence) and not isinstance(node, str | bytes):
        for index, value in enumerate(node):
            yield from _iter_refs(value, f"{pointer}/{index}")


def _is_external_ref(ref: str) -> bool:
    """True when the literal ``$ref`` string names a remote scheme."""
    return urlsplit(ref).scheme.lower() in _EXTERNAL_SCHEMES


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Loaded:
    path: Path
    display_path: str
    document: JsonValue


def _load(path: Path, display_path: str) -> tuple[_Loaded | None, SchemaIssue | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, SchemaIssue(
            schema_path=display_path,
            json_pointer="",
            code=IssueCode.UNREADABLE,
            message=f"could not read schema file: {type(exc).__name__}",
        )
    try:
        document: JsonValue = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, SchemaIssue(
            schema_path=display_path,
            json_pointer="",
            code=IssueCode.UNPARSEABLE_JSON,
            message=f"file is not valid UTF-8 JSON: {exc}",
        )
    if not isinstance(document, Mapping):
        return None, SchemaIssue(
            schema_path=display_path,
            json_pointer="",
            code=IssueCode.NOT_AN_OBJECT,
            message=f"schema document must be a JSON object, found {type(document).__name__}",
        )
    return _Loaded(path=path, display_path=display_path, document=document), None


def _build_registry(loaded: Sequence[_Loaded]) -> tuple[Registry, list[SchemaIssue]]:
    """Build a purely local registry keyed by ``$id`` and by file name.

    The registry has no retrieve callback, so nothing here can reach the network.
    """
    issues: list[SchemaIssue] = []
    seen_ids: dict[str, str] = {}
    resources: list[tuple[str, Resource]] = []

    for item in loaded:
        resource = Resource.from_contents(item.document, default_specification=DRAFT202012)
        schema_id = item.document.get("$id")
        if isinstance(schema_id, str) and schema_id:
            previous = seen_ids.get(schema_id)
            if previous is not None:
                issues.append(
                    SchemaIssue(
                        schema_path=item.display_path,
                        json_pointer="/$id",
                        code=IssueCode.DUPLICATE_SCHEMA_ID,
                        message=f"$id is already declared by {previous}",
                    )
                )
            else:
                seen_ids[schema_id] = item.display_path
                resources.append((schema_id, resource))
        # Also key by bare filename so a schema without an $id remains referenceable.
        resources.append((item.path.name, resource))

    return Registry().with_resources(resources), issues


def _validate_one(
    item: _Loaded,
    registry: Registry,
    *,
    allow_external_refs: bool,
) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []

    # 1. The document must itself satisfy the Draft 2020-12 metaschema.
    try:
        Draft202012Validator.check_schema(item.document)
    except SchemaError as exc:
        pointer = "".join(f"/{_escape_pointer_token(str(part))}" for part in exc.absolute_path)
        issues.append(
            SchemaIssue(
                schema_path=item.display_path,
                json_pointer=pointer,
                code=IssueCode.INVALID_METASCHEMA,
                message=exc.message,
            )
        )

    # 2. Every $ref must resolve inside the local registry.
    schema_id = item.document.get("$id")
    base_uri = schema_id if isinstance(schema_id, str) else item.path.name
    resolver = registry.resolver(base_uri=base_uri)

    for pointer, ref in _iter_refs(item.document):
        external = _is_external_ref(ref)
        try:
            resolver.lookup(ref)
        except Unresolvable:
            if external:
                if not allow_external_refs:
                    issues.append(
                        SchemaIssue(
                            schema_path=item.display_path,
                            json_pointer=pointer,
                            code=IssueCode.EXTERNAL_REF_BLOCKED,
                            message=(
                                f"external reference {ref!r} is not satisfied by any local "
                                "schema; network resolution is not permitted"
                            ),
                        )
                    )
            else:
                issues.append(
                    SchemaIssue(
                        schema_path=item.display_path,
                        json_pointer=pointer,
                        code=IssueCode.UNRESOLVED_LOCAL_REF,
                        message=f"local reference {ref!r} does not resolve",
                    )
                )
        except (TypeError, ValueError) as exc:
            # A syntactically unusable $ref (bad URI, bad JSON pointer) surfaces here
            # rather than as Unresolvable. Report it; never let it abort the run.
            issues.append(
                SchemaIssue(
                    schema_path=item.display_path,
                    json_pointer=pointer,
                    code=IssueCode.UNRESOLVED_LOCAL_REF,
                    message=f"reference {ref!r} is malformed: {type(exc).__name__}",
                )
            )

    return issues


def validate_schema_directory(
    directory: Path,
    *,
    root: Path | None = None,
    allow_external_refs: bool = False,
) -> SchemaReport:
    """Discover and validate every schema under ``directory``.

    Args:
        directory: directory to search recursively.
        root: base for rendering display paths. Defaults to ``directory``'s parent chain
            not being used, i.e. paths are shown relative to ``directory`` itself.
        allow_external_refs: when true, an unresolved reference written with a remote
            scheme is tolerated instead of reported. Off by default; turning it on does
            not enable fetching, it only stops the check from failing.

    Returns:
        A deterministic :class:`SchemaReport`.
    """
    paths = discover_schemas(directory)
    display_root = root if root is not None else directory

    loaded: list[_Loaded] = []
    load_issues: dict[str, list[SchemaIssue]] = {}
    order: list[str] = []

    for path in paths:
        display_path = relative_to_root(display_root, path)
        order.append(display_path)
        item, issue = _load(path, display_path)
        if issue is not None:
            load_issues.setdefault(display_path, []).append(issue)
        if item is not None:
            loaded.append(item)

    registry, registry_issues = _build_registry(loaded)
    for issue in registry_issues:
        load_issues.setdefault(issue.schema_path, []).append(issue)

    by_path: dict[str, SchemaResult] = {}
    for item in loaded:
        issues = list(load_issues.get(item.display_path, ()))
        issues.extend(_validate_one(item, registry, allow_external_refs=allow_external_refs))
        schema_id = item.document.get("$id")
        title = item.document.get("title")
        by_path[item.display_path] = SchemaResult(
            schema_path=item.display_path,
            schema_id=schema_id if isinstance(schema_id, str) else None,
            title=title if isinstance(title, str) else None,
            status=SchemaStatus.FAIL if issues else SchemaStatus.PASS,
            issues=tuple(issues),
        )

    for display_path, issues in load_issues.items():
        if display_path not in by_path:
            by_path[display_path] = SchemaResult(
                schema_path=display_path,
                schema_id=None,
                title=None,
                status=SchemaStatus.FAIL,
                issues=tuple(issues),
            )

    results = tuple(by_path[display_path] for display_path in order)
    status = (
        SchemaStatus.FAIL
        if any(result.status is SchemaStatus.FAIL for result in results)
        else SchemaStatus.PASS
    )
    return SchemaReport(
        directory=relative_to_root(display_root, directory),
        status=status,
        results=results,
        external_refs_allowed=allow_external_refs,
    )
