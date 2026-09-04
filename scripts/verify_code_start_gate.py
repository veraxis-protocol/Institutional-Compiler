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
PROMOTION_BASE = "9ad37fc80d8f34318c6212ed702de5eab3551cf5"
PROMOTION_SOURCE = "3fcdec63b7e546d9b369e0e8664d5d67be6a3b54"
AUTHORIZED_PATHS_SHA256 = "23b12fef0f72c41e11456361132b522ca645555b793e93be10815fd9529f78c1"
HISTORICAL_GATE_SHA256 = "58231eeda2266eb58e2ec5ec4ac70d0f3bf40a47264b77a8d8f6c69db9a94896"
BOUNDED_SRC_OIC_PATHS = frozenset(
    {
        "src/oic/model_provider.py",
        "src/oic/frozen_synthetic_provider.py",
        "src/oic/candidate_extraction.py",
        "src/oic/review_docket.py",
        "src/oic/admission.py",
        "src/oic/interpretation_proposal.py",
        "src/oic/admission_specs/__init__.py",
        "src/oic/admission_specs/ADMISSION-INPUT-v0.1.schema.json",
        "src/oic/admission_specs/ADMISSION-RECEIPT-v0.1.schema.json",
        "src/oic/admission_specs/AUTHORITY-EVIDENCE-v0.1.schema.json",
        "src/oic/admission_specs/STATE-INPUT-MAPPING-v0.1.json",
    }
)
CEILINGS = {
    "nvidia": "NOT_QUALIFIED",
    "canada_redistribution": "UNRESOLVED",
    "ontology_007r1": "UNEXECUTED_EXECUTION_UNAUTHORIZED",
    "production_compilation": "UNESTABLISHED",
    "runtime_authorization": "UNESTABLISHED",
    "institutional_ir_closure": "UNESTABLISHED",
    "negative_stability_live_result": "DEFERRED",
    "independent_validation": False,
}
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
    current.update(
        path.relative_to(root).as_posix()
        for path in (root / "src/oic").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    admitted = ADMITTED_SRC_OIC_PATHS | BOUNDED_SRC_OIC_PATHS
    added = sorted(current - admitted)
    missing = sorted(path for path in admitted if not (root / path).is_file())
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


def validate_bounded_record(root: Path) -> None:
    """Validate the owner-pinned bounded surface, never a self-declared general OPEN gate."""
    record = json.loads((root / "docs/capabilities/CAPABILITY_MATRIX.json").read_bytes())
    _require(isinstance(record, dict), "invalid capability matrix")
    _require(
        set(record)
        == {
            "work_order",
            "promotion_base",
            "source_commit",
            "state",
            "production_semantic_gate",
            "authorized_maximum_paths",
            "actual_changed_paths",
            "source_provenance",
            "ceilings",
            "capabilities",
        },
        "capability matrix fields expanded",
    )
    capabilities = record.get("capabilities")
    names = [
        "grounded_candidate_extraction",
        "review_divergence",
        "synthetic_authority_evidence_admission",
        "provisional_eleven_slot_decomposition",
        "unresolved_reference_preservation",
        "offline_deterministic_receipt",
    ]
    _require(
        isinstance(capabilities, list) and len(capabilities) == len(names),
        "capability set expanded",
    )
    for capability, name in zip(capabilities, names, strict=True):
        _require(
            capability
            == {
                "name": name,
                "implemented": True,
                "tested": "LOCAL_TESTS_PASSED",
                "documented": True,
                "deferred": "generalization_and_independent_validation",
                "evidence_ceiling": (
                    "Synthetic frozen replay only; no model accuracy, institutional "
                    "meaning, legal validity, or runtime permission."
                ),
            },
            "capability claim expanded",
        )
    _require(record.get("work_order") == "OIC-SEMANTIC-PROMOTION-001", "wrong work order")
    _require(record.get("promotion_base") == PROMOTION_BASE, "wrong promotion base")
    _require(record.get("source_commit") == PROMOTION_SOURCE, "wrong promotion source")
    _require(record.get("state") == "BOUNDED_REFERENCE_IMPLEMENTATION", "bounded state expanded")
    _require(record.get("production_semantic_gate") == "BLOCKED", "production gate expanded")
    _require(record.get("ceilings") == CEILINGS, "evidence ceiling expanded")
    provenance = record.get("source_provenance")
    _require(
        hashlib.sha256(
            json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == "15d7ae49ade2bbbf0888803ef3e647c3eb9e0255f60c5da43f90726a2693f482",
        "source provenance changed",
    )
    for entry in provenance:
        _require(
            hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() == entry["sha256"],
            f"exact promoted source changed: {entry['path']}",
        )
    paths = record.get("authorized_maximum_paths")
    _require(isinstance(paths, list) and all(isinstance(p, str) for p in paths), "invalid paths")
    _require(
        hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest() == AUTHORIZED_PATHS_SHA256,
        "capability matrix cannot self-extend the owner allowlist",
    )
    _require(record.get("actual_changed_paths") == paths, "changed-path record differs")
    for path in paths:
        _require((root / path).is_file(), f"missing required bounded path: {path}")
    _require(not discover_unadmitted_production_paths(root), "unauthorized production surface")
    gate = root / "docs/gates/OIC-SEMANTIC-CODE-START-GATE-CLOSURE-v0.1.md"
    _require(
        hashlib.sha256(gate.read_bytes()).hexdigest() == HISTORICAL_GATE_SHA256,
        "historical gate receipt changed",
    )


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
    validate_bounded_record(root)


if __name__ == "__main__":
    try:
        load_and_validate(Path(__file__).resolve().parents[1])
    except (GateEvidenceError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL semantic code-start gate evidence: {exc}")
        sys.exit(1)
    print("PASS bounded reference implementation; broader production semantic gate BLOCKED")
