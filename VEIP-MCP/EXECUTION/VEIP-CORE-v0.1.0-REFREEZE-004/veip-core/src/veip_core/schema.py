"""Dependency-free validator for the exact keyword set used by the frozen schema."""

from __future__ import annotations

import json
from importlib.resources import files
import re
from typing import Any

from .canonical import dumps as canonical_dumps


class ValidationFailure(ValueError):
    pass


def _load_schema() -> dict[str, Any]:
    resource = files("veip_core").joinpath("data/VEIP_CORE_SCHEMA_v0.1.json")
    return json.loads(resource.read_text(encoding="utf-8"))


SCHEMA = _load_schema()


def _is_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False


def _resolve(reference: str) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not reference.startswith(prefix):
        raise ValidationFailure(f"Unsupported schema reference: {reference}")
    return SCHEMA["$defs"][reference[len(prefix):]]


def _validate(instance: Any, schema: dict[str, Any], path: str) -> None:
    if "$ref" in schema:
        _validate(instance, _resolve(schema["$ref"]), path)
        return

    if "oneOf" in schema:
        successes = 0
        for branch in schema["oneOf"]:
            try:
                _validate(instance, branch, path)
                successes += 1
            except ValidationFailure:
                pass
        if successes != 1:
            raise ValidationFailure(f"{path}: expected exactly one matching schema")

    expected_type = schema.get("type")
    if expected_type is not None and not _is_type(instance, expected_type):
        raise ValidationFailure(f"{path}: expected {expected_type}")

    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationFailure(f"{path}: value is not in enum")

    if isinstance(instance, str) and "pattern" in schema:
        if re.search(schema["pattern"], instance) is None:
            raise ValidationFailure(f"{path}: string does not match required pattern")

    if expected_type in ("integer", "number") and "minimum" in schema:
        if instance < schema["minimum"]:
            raise ValidationFailure(f"{path}: value is below minimum")

    if isinstance(instance, dict) and expected_type == "object":
        required = schema.get("required", [])
        missing = [name for name in required if name not in instance]
        if missing:
            raise ValidationFailure(f"{path}: missing required properties {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = [name for name in instance if name not in properties]
            if extras:
                raise ValidationFailure(f"{path}: additional properties not allowed {extras}")
        for name, value in instance.items():
            if name in properties:
                _validate(value, properties[name], f"{path}.{name}")

    if isinstance(instance, list) and expected_type == "array":
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for item in instance:
                marker = canonical_dumps(item)
                if marker in seen:
                    raise ValidationFailure(f"{path}: array items must be unique")
                seen.add(marker)
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(instance):
                _validate(item, item_schema, f"{path}[{index}]")


def validate_definition(instance: Any, definition_name: str) -> None:
    try:
        definition = SCHEMA["$defs"][definition_name]
    except KeyError as exc:
        raise ValueError(f"Unknown frozen schema definition: {definition_name}") from exc
    _validate(instance, definition, "$")


def matching_definition(instance: Any, names: tuple[str, ...]) -> str:
    matches: list[str] = []
    for name in names:
        try:
            validate_definition(instance, name)
            matches.append(name)
        except ValidationFailure:
            pass
    if len(matches) != 1:
        raise ValidationFailure("Root object does not match exactly one allowed entry-point schema")
    return matches[0]
