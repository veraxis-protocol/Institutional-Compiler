"""Evidence-pack manifest projection and verification."""

from __future__ import annotations

from typing import Any

from .canonical import sha256
from .errors import EngineError

MANIFEST_FIELDS = (
    "evidence_id",
    "payload_sha256",
    "source_type",
    "channel_ref",
    "receipt",
    "observed_at",
    "subject_ref",
    "extent_ref",
    "run_id",
)


def manifest_projection(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected = [
        {key: reference[key] for key in MANIFEST_FIELDS if key in reference}
        for reference in references
    ]
    projected.sort(key=lambda item: item["evidence_id"].encode("utf-8"))
    return projected


def manifest_hash(references: list[dict[str, Any]]) -> str:
    return sha256(manifest_projection(references))


def verify_manifest(pack: dict[str, Any]) -> None:
    computed = manifest_hash(pack["references"])
    if computed != pack["manifest_sha256"]:
        raise EngineError(
            "MANIFEST_HASH_MISMATCH",
            "Evidence-pack manifest hash does not match the canonical nine-field projection.",
        )
