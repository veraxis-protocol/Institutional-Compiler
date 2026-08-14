"""Adversarial self-checks for the RUN-002 execution harness.

Every case goes through the harness's own pure verifier seams. The result-bearing
route is never invoked, the real src/ tree is never mutated, and no canonical
runtime path is written: the source-integrity cases run against an isolated
throwaway git repository.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REVIEW_DIR = pathlib.Path("/private/tmp/cdc-e2e-m12-run-002-execution-decision-review")
sys.path.insert(0, str(REVIEW_DIR))

import cdc_e2e_m12_run_002_execution_harness as harness  # noqa: E402

BASELINE = json.loads(
    (
        REVIEW_DIR / "CDC-END-TO-END-MISSION-001-M12-EXECUTION-DECISION-002.CANDIDATE-v0.1.json"
    ).read_bytes()
)


def _serialize(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _mutate(**changes: object) -> bytes:
    return _serialize({**BASELINE, **changes})


def _without(field: str) -> bytes:
    return _serialize({k: v for k, v in BASELINE.items() if k != field})


def _one_byte_variant() -> bytes:
    """Same parsed semantics, different bytes."""
    payload = _serialize(BASELINE)
    return payload[:-1] + b" \n"


CASES: list[tuple[str, bytes]] = [
    ("omitted_field", _without("successor_id")),
    ("unknown_field_added", _serialize({**BASELINE, "override": True})),
    ("one_byte_changed_semantics_equivalent", _one_byte_variant()),
    ("authorization_sha_changed", _mutate(authorization_sha256="0" * 64)),
    (
        "authorization_issuance_record_sha_changed",
        _mutate(authorization_issuance_record_sha256="0" * 64),
    ),
    ("instruction_sha_changed", _mutate(correction_instruction_sha256="0" * 64)),
    ("successor_changed", _mutate(successor_id="EBAWU-SOMETHING-ELSE")),
    ("implementation_commit_changed", _mutate(implementation_commit="0" * 40)),
    ("implementation_tree_changed", _mutate(implementation_tree="0" * 40)),
    ("environment_changed", _mutate(environment_manifest_sha256="0" * 64)),
    ("decision_value_changed", _mutate(decision="EXECUTE_TWICE")),
    ("single_use_false", _mutate(single_use=False)),
    ("automatic_retry_true", _mutate(automatic_retry_authorized=True)),
    ("claim_ceiling_changed", _mutate(claim_ceiling="PRODUCTION")),
]


def _source_integrity_case() -> dict[str, Any]:
    """Refusal when the src/ tree differs, in a throwaway repository."""
    executable = shutil.which("git")
    if executable is None:
        return {"case": "source_integrity", "skipped": "git unavailable"}
    with tempfile.TemporaryDirectory() as raw:
        repo = pathlib.Path(raw) / "fixture"
        (repo / "src" / "oic").mkdir(parents=True)
        (repo / "src" / "oic" / "module.py").write_text("ORIGINAL = 1\n")
        for command in (
            ["init", "-q"],
            ["config", "user.email", "selfcheck@example.invalid"],
            ["config", "user.name", "selfcheck"],
            ["add", "-A"],
            ["commit", "-q", "-m", "fixture baseline"],
        ):
            subprocess.run(  # noqa: S603
                [executable, "-C", str(repo), *command], check=True, capture_output=True
            )
        baseline_commit = subprocess.run(  # noqa: S603
            [executable, "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        clean = harness.verify_runtime_source(repo, baseline_commit)
        (repo / "src" / "oic" / "module.py").write_text("ORIGINAL = 2\n")
        tracked = harness.verify_runtime_source(repo, baseline_commit)
        (repo / "src" / "oic" / "module.py").write_text("ORIGINAL = 1\n")
        (repo / "src" / "oic" / "smuggled.py").write_text("BACKDOOR = True\n")
        untracked = harness.verify_runtime_source(repo, baseline_commit)
        return {
            "case": "source_integrity",
            "clean_fixture_matches": clean["matches"],
            "tracked_mutation_refused": not tracked["matches"],
            "tracked_differences": tracked["tracked_src_differences"],
            "untracked_file_refused": not untracked["matches"],
            "untracked_files": untracked["untracked_src_files"],
            "real_src_tree_mutated": False,
        }


def main() -> dict[str, Any]:
    results = []
    for name, payload in CASES:
        report = harness.verify_execution_decision(payload)
        results.append(
            {
                "case": name,
                "refused": not report["accepted"],
                "exact_identity": report["exact_identity"],
                "schema": report["schema"],
                "semantic_bindings": report["semantic_bindings"],
            }
        )
    baseline_report = harness.verify_execution_decision(_serialize(BASELINE))
    source = _source_integrity_case()
    return {
        "record_class": "M12_RUN_002_EXECUTION_HARNESS_ADVERSARIAL_SELFCHECK",
        "reviewed_candidate_accepted_by_verifier": baseline_report["accepted"],
        "reviewed_candidate_exact_identity": baseline_report["exact_identity"],
        "reviewed_candidate_schema": baseline_report["schema"],
        "reviewed_candidate_semantics": baseline_report["semantic_bindings"],
        "adversarial_cases": results,
        "adversarial_cases_total": len(results),
        "adversarial_cases_refused": sum(1 for item in results if item["refused"]),
        "all_adversarial_cases_refused": all(item["refused"] for item in results),
        "source_integrity": source,
        "result_bearing_functions_invoked": [],
        "canonical_paths_written": [],
        "real_src_tree_mutated": False,
        "result_bearing": False,
        "claim_ceiling": "SYNTHETIC_EVALUATION_ONLY",
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
