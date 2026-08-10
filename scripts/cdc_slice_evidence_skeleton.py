#!/usr/bin/env python3
"""Build the frozen evidence-package skeleton for the CDC vertical slice.

Sections 00-16 are created now and populated only with pre-execution static
identities. Every runtime-result slot is the explicit literal
``NOT_YET_OBSERVED``. No empty string and no fabricated digest is written for
evidence that does not exist yet — an absent digest must remain visibly absent,
because a placeholder hash is indistinguishable from a real one after the fact.

This script builds structure. It executes nothing, observes nothing and
adjudicates nothing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from cdc_slice_adversarial import probe_definitions  # noqa: E402
from cdc_slice_corpus import CONTROLS, PROCEDURES, S_CASES, corpus  # noqa: E402
from cdc_slice_interlock import observe_clearance  # noqa: E402
from cdc_slice_observation import unobserved  # noqa: E402

from oic.cdc_slice import CONTRACT_ID, MISSION_ID  # noqa: E402

NOT_YET_OBSERVED = "NOT_YET_OBSERVED"

SECTIONS: tuple[str, ...] = (
    "00-MANIFEST",
    "01-BASELINES",
    "02-CONTRACT",
    "03-SEMANTIC-ORACLE",
    "04-EXECUTION-ENVIRONMENT",
    "05-MISSION",
    "06-SOURCE-AND-ADMISSION",
    "07-CONTROLS",
    "08-POPULATION",
    "09-DETERMINISTIC-EXECUTION",
    "10-ZTL-WARRANTS",
    "11-HUMAN-DISPOSITIONS",
    "12-VEIP-TRANSITIONS",
    "13-CORRECTIONS",
    "14-ADVERSARIAL",
    "15-DELIVERABLE",
    "16-LIMITATIONS-AND-NONCLAIMS",
)

NONCLAIMS: tuple[str, ...] = (
    "not CDC deployment",
    "not CDC validation",
    "not production readiness",
    "not production VEIP conformance",
    "not legal authority",
    "not real-world reviewer identity",
    "not evidence sufficiency",
    "not official finding status",
    "not production reliance",
    "not runtime currentness",
    "not supplier replacement",
    "not CRC-wide scalability",
    "not offline/no-egress conformance",
    "not a full six-state VEIP SDK implementation",
    "not closure of GATE-SAR-05",
)


def _git(*args: str) -> str:
    # Fixed argv, no operator input; git is resolved from PATH in the dev environment.
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO_ROOT), *args],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else NOT_YET_OBSERVED


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def section_payloads() -> dict[str, Any]:
    """Static, pre-execution content for each section."""
    return {
        "01-BASELINES": {
            "implementation_baseline": "29daa374b7e5cdc30ca7788310fbabb85f19912b",
            "core_snapshot_provenance_complete": "673bb27b134e43369b4028e9f35af1a0c1a60734",
            "core_snapshot_state": {
                "ARTIFACT_STATE": "FROZEN",
                "CORE_VERIFICATION": "NOT_YET_ESTABLISHED",
                "EXECUTION_CLEARANCE": False,
            },
            "governance_baseline": "inventor1975/ZTL@4ef30437882c1c3be2a0de724bfb85b4026d4e2b",
            "claude_branch_head": _git("rev-parse", "HEAD"),
            "claude_branch_tree": _git("rev-parse", "HEAD^{tree}"),
            "first_observation_provenance": {
                "FO-1": "fe6aeee35c5aa097812e88128ca1f88bc5f5616171eaefc90a0ca91451ba644b",
                "FO-2": "9c1a3c56a03d0608c837a6ed0ec43e1b81d1caa25004b624c4151ff4c9c483f9",
                "FO-3": "5c4fd18587ef75d408a7d818c761ae5cbc2490be9ec0df81abe8f9602e2dc927",
            },
        },
        "02-CONTRACT": {
            "contract_id": CONTRACT_ID,
            "owner_contract_sha256": (
                "93fa0cf467aa93df67079b24066bf3aeb40c70df768621ec6b8f6a8ace90300e"
            ),
            "semantic_review_notes_sha256": (
                "ac8e8c2488c35966508e824b665f0730d471835d15af5422ed5964729a138b41"
            ),
            "semantic_contract_return": "SEMANTIC_CONTRACT_CONFORMANT_v0.1",
        },
        "03-SEMANTIC-ORACLE": {
            "oracle_commit": "2ce3bdab0acc6a0411f63a20e32164c1f0c8d4a9",
            "oracle_sha256": ("392f298197632451df0bfa7379e0e5a8a7ef1fb440fda4a60ea2f4f8af683390"),
            "adjudication_protocol_commit": "ff78860882748d3f03754f240e7a5c7f1873b174",
            "adjudication_protocol_sha256": (
                "5884c984833b0495ea4d7fc6265a7440797fc2ab3d3a9641f505ebc637121cbf"
            ),
            "merge_checklist_sha256": (
                "48ea48fc41b6756de9cccf145bb4e89a16cc74ee8e51fabfc1715864bdf41206"
            ),
            "resolution_state": "DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE",
            "oracle_is_external_to_runtime": True,
            "adjudication_result": NOT_YET_OBSERVED,
        },
        "04-EXECUTION-ENVIRONMENT": {
            "python_required": ">=3.12,<3.13",
            "python_observed": NOT_YET_OBSERVED,
            "dependency_pins": "requirements/runtime.txt at the implementation baseline",
            "network": "disabled by the suite-wide socket prohibition",
            "interlock": observe_clearance().as_record(),
        },
        "05-MISSION": {"mission_id": MISSION_ID, "mission_executions": 0},
        "06-SOURCE-AND-ADMISSION": {
            "fixtures": [
                {
                    "case_id": record["case_id"],
                    "admission_ref": record["admission_ref"],
                    "evidence_refs": record["evidence_refs"],
                }
                for record in corpus()
            ]
        },
        "07-CONTROLS": {"controls": list(CONTROLS)},
        "08-POPULATION": {"procedures": list(PROCEDURES), "fixtures": corpus()},
        "09-DETERMINISTIC-EXECUTION": {
            "case_ids": list(S_CASES),
            "results": NOT_YET_OBSERVED,
        },
        "10-ZTL-WARRANTS": {"warrant_artifacts": NOT_YET_OBSERVED},
        "11-HUMAN-DISPOSITIONS": {"dispositions": NOT_YET_OBSERVED},
        "12-VEIP-TRANSITIONS": {"transitions": NOT_YET_OBSERVED},
        "13-CORRECTIONS": {"corrections": NOT_YET_OBSERVED},
        "14-ADVERSARIAL": {
            "probes_defined": 7,
            "probes_executed": 0,
            "denominator": 0,
            "definitions": probe_definitions(),
            "observations": [unobserved(case_id) for case_id in S_CASES],
        },
        "15-DELIVERABLE": {
            "deliverable": NOT_YET_OBSERVED,
            "official_record": False,
        },
        "16-LIMITATIONS-AND-NONCLAIMS": {"nonclaims": list(NONCLAIMS)},
    }


def build(destination: Path) -> dict[str, Any]:
    """Create the skeleton and return its accounting."""
    if destination.exists():
        raise SystemExit(f"refusing to overwrite an existing skeleton: {destination}")
    payloads = section_payloads()
    written: list[str] = []
    for section in SECTIONS:
        directory = destination / section
        directory.mkdir(parents=True)
        if section == "00-MANIFEST":
            continue
        path = directory / "SECTION.json"
        path.write_bytes(_canonical(payloads[section]))
        written.append(f"{section}/SECTION.json")

    manifest = {
        "artifact_kind": "EVIDENCE_PACKAGE_SKELETON",
        "result_bearing": False,
        "sections": list(SECTIONS),
        "populated_sections": written,
        "runtime_result_slots": NOT_YET_OBSERVED,
        "note": (
            "Structure only. Runtime-result slots are the literal NOT_YET_OBSERVED. "
            "No empty string and no fabricated digest stands in for absent evidence."
        ),
    }
    (destination / "00-MANIFEST" / "SECTION.json").write_bytes(_canonical(manifest))
    return {"destination": str(destination), "sections": len(SECTIONS), "populated": len(written)}


def main(argv: list[str] | None = None) -> int:
    """Build the skeleton."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.destination), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
