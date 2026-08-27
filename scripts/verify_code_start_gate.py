#!/usr/bin/env python3
"""Fail-closed verifier for the non-semantic code-start evidence package."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_ZTL = {
    "profile_id": "ztl-v0.1",
    "version": "0.1.0",
    "commit": "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b",
    "tag": "veraxis-ztl-input-v0.2-signed",
    "index": "ffadd65352d69ffcf55787c6dc26339e51eaed76b4c2ae789f7c813625247145",
}
STALE_ZTL_TEXT = (
    "current DRAFT evidence head",
    "still in DRAFT pull request #18",
    "must not merge before PR #18",
)
ADMITTED_PRE_GATE_HEAD = "4065e6a7c02badd3356f4c74be0815079d836aca"
ADMITTED_SRC_OIC_PATHS = frozenset(
    {
        "src/oic/__init__.py",
        "src/oic/baseline.py",
        "src/oic/cli.py",
        "src/oic/doctor.py",
        "src/oic/errors.py",
        "src/oic/hashing.py",
        "src/oic/manifests.py",
        "src/oic/paths.py",
        "src/oic/py.typed",
        "src/oic/schemas.py",
    }
)


class GateEvidenceError(ValueError):
    """Evidence fails a bounded gate invariant."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateEvidenceError(message)


def discover_unadmitted_production_paths(root: Path) -> list[str]:
    """Compare tracked ``src/oic`` paths with the immutable pre-gate baseline."""
    git = shutil.which("git")
    if git is None:
        raise GateEvidenceError("cannot enumerate tracked src/oic production paths")
    result = subprocess.run(  # noqa: S603 - fixed executable and literal arguments
        [git, "-C", str(root.resolve()), "ls-files", "--", "src/oic"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GateEvidenceError("cannot enumerate tracked src/oic production paths")
    current = {line for line in result.stdout.splitlines() if line}
    added = sorted(current - ADMITTED_SRC_OIC_PATHS)
    missing = sorted(ADMITTED_SRC_OIC_PATHS - current)
    return added + [f"MISSING:{path}" for path in missing]


def validate_evidence(
    source_set: dict[str, Any],
    receipts: dict[str, Any],
    profile: dict[str, Any],
    veip: dict[str, Any],
    gate_text: str,
    source_bytes: dict[str, bytes],
    active_text: str,
    semantic_paths: list[str] | None = None,
) -> None:
    _require(
        source_set.get("global_manifest_status") == "INCOMPLETE", "global manifest state escalated"
    )
    by_id = {item["source_id"]: item for item in source_set.get("sources", [])}
    receipt_by_id = {item["source_id"]: item for item in receipts.get("receipts", [])}
    _require(
        len(by_id) == 4 and set(by_id) == set(receipt_by_id), "source/receipt provenance mismatch"
    )
    for source_id, item in by_id.items():
        payload = source_bytes.get(source_id)
        if payload is None:
            raise GateEvidenceError(f"missing source bytes: {source_id}")
        digest = hashlib.sha256(payload).hexdigest()
        _require(digest == item.get("sha256"), f"source digest mismatch: {source_id}")
        _require(
            digest == receipt_by_id[source_id].get("sha256"),
            f"receipt digest mismatch: {source_id}",
        )
        if source_id.startswith("SYN-"):
            _require(
                item.get("origin_classification") == "SYNTHETIC_FICTIONAL",
                "synthetic classification missing",
            )
            _require(
                item.get("benchmark_authority") == "SYNTHETIC_BENCHMARK_ONLY",
                "synthetic represented as real authority",
            )
            _require(
                item.get("issuer") == "Veraxis synthetic fixture generator",
                "synthetic issuer masquerades as government",
            )
            _require(
                str(item.get("effective_state", "")).startswith("SYNTHETIC_"),
                "fabricated government effective metadata",
            )
            decoded = payload.decode("utf-8")
            _require(
                "SYNTHETIC" in decoded and "fictional" in decoded.lower(),
                "source bytes lack synthetic warning",
            )
    ca3 = by_id["CA-3"]
    _require(
        ca3.get("origin_classification") == "REAL_PUBLIC_CANADIAN_SOURCE_UNOFFICIAL_COPY",
        "CA-3 provenance changed",
    )
    _require(
        ca3.get("effective_state") == "NOT_ESTABLISHED_NO_DATE_INVENTED",
        "CA-3 effective date invented",
    )

    _require(profile.get("profile_id") == EXPECTED_ZTL["profile_id"], "wrong ZTL profile")
    _require(profile.get("version") == EXPECTED_ZTL["version"], "wrong ZTL version")
    _require(profile.get("commit") == EXPECTED_ZTL["commit"], "wrong ZTL commit")
    _require(profile.get("signed_tag", {}).get("name") == EXPECTED_ZTL["tag"], "wrong ZTL tag")
    _require(
        profile.get("conformance_fixture_set", {}).get("index_sha256") == EXPECTED_ZTL["index"],
        "wrong ZTL fixture index",
    )
    _require(
        profile.get("tier_1_reproduction") == "NOT ESTABLISHED — DEFERRED TO EXPERIMENTAL RELEASE",
        "Tier-1 state escalated",
    )
    _require(
        profile.get("status") == "ADMITTED FOR BOUNDED SEMANTIC CODE START ONLY",
        "bounded ZTL admission missing",
    )
    _require(
        not any(marker.lower() in active_text.lower() for marker in STALE_ZTL_TEXT),
        "stale ZTL currentness text",
    )

    for field in (
        "executable_runtime_integration",
        "oic_has_veip_lifecycle_authority",
        "veip_reinterprets_ztl",
        "oic_self_authorizes_runtime_execution",
        "runtime_adapter_authorized",
        "lifecycle_execution_authorized",
        "runtime_import_authorized",
    ):
        _require(veip.get(field) is False, f"forbidden VEIP state: {field}")
    _require(
        veip.get("missing_lifecycle_integration") == "FAIL_CLOSED",
        "VEIP boundary is not fail-closed",
    )
    normalized_gate = gate_text.replace("*", "").upper()
    _require(
        "GLOBAL REPOSITORY COMPLETENESS" in normalized_gate and "INCOMPLETE" in normalized_gate,
        "global incompleteness not explicit",
    )
    _require(
        "READY FOR SEPARATE EXACT-HEAD REVIEW\nNOT OPEN" in normalized_gate, "gate language invalid"
    )
    _require(not semantic_paths, "semantic implementation appeared before gate opening")


def load_and_validate(root: Path) -> None:
    def load(path: str) -> dict[str, Any]:
        value: dict[str, Any] = json.loads((root / path).read_text(encoding="utf-8"))
        return value

    source_set = load("benchmarks/preflight/code-start-v0.1/SOURCE-SET.json")
    receipts = load("benchmarks/preflight/code-start-v0.1/PROVENANCE.json")
    profile = load("docs/contracts/kernel-profiles/ztl-v0.1.json")
    veip = load("docs/contracts/VEIP-CODE-START-BOUNDARY-v0.1.json")
    gate_text = (root / "docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md").read_text(
        encoding="utf-8"
    )
    active_text = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "docs/contracts/kernel-profiles/ztl-v0.1.json",
            "docs/contracts/WARRANT-CONTRACT-v0.1.md",
            "adr/ADR-013.md",
        )
    )
    source_bytes = {
        item["source_id"]: (root / item["path"]).read_bytes() for item in source_set["sources"]
    }
    semantic_paths = discover_unadmitted_production_paths(root)
    validate_evidence(
        source_set,
        receipts,
        profile,
        veip,
        gate_text,
        source_bytes,
        active_text,
        semantic_paths=semantic_paths,
    )


if __name__ == "__main__":
    try:
        load_and_validate(Path(__file__).resolve().parents[1])
    except (GateEvidenceError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL semantic code-start gate evidence: {exc}")
        sys.exit(1)
    print("PASS semantic code-start prerequisite evidence; gate remains NOT OPEN")
