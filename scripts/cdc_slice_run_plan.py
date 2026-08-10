#!/usr/bin/env python3
"""Generate the CDC vertical-slice run plan without executing it.

The plan enumerates what a future result-bearing run would do: which cases, in
which order, against which fixtures, requiring which environment, writing which
outputs. It resolves references and recomputes static fixture digests so a
missing prerequisite is visible before execution rather than during it.

It never calls ``evaluate_test_transition``, emits no institutional event, emits
no VEIP decision, writes no mission successor, produces no evidence pack and
performs no adjudication. Every output identifies itself as ``RUN_PLAN_ONLY``
with ``RESULT_BEARING = FALSE``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from cdc_slice_adversarial import (  # noqa: E402
    ADVERSARIAL_DENOMINATOR,
    ADVERSARIAL_PROBES_DEFINED,
    ADVERSARIAL_PROBES_EXECUTED,
    PROBES,
    probe_definitions,
)
from cdc_slice_corpus import (  # noqa: E402
    CONTROLS,
    PROCEDURES,
    S_CASES,
    corpus,
    fixture_record,
)
from cdc_slice_interlock import observe_clearance  # noqa: E402

from oic.cdc_slice import CONTRACT_ID, MISSION_ID  # noqa: E402

REQUIRED_ENVIRONMENT: dict[str, str] = {
    "python": ">=3.12,<3.13",
    "interpreter_note": "system Python 3.13 is not accepted for evidence-bearing execution",
    "dependency_pins": "requirements/runtime.txt at the implementation baseline",
    "dependency_note": "pins are controlling and are never upgraded by this tooling",
    "network": "disabled by the suite-wide socket prohibition in tests/conftest.py",
}

DECLARED_EXTERNAL_IDENTITIES: dict[str, Any] = {
    "semantic_oracle": {
        "commit": "2ce3bdab0acc6a0411f63a20e32164c1f0c8d4a9",
        "sha256": "392f298197632451df0bfa7379e0e5a8a7ef1fb440fda4a60ea2f4f8af683390",
        "resolution_state": "DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE",
    },
    "adjudication_protocol": {
        "commit": "ff78860882748d3f03754f240e7a5c7f1873b174",
        "sha256": "5884c984833b0495ea4d7fc6265a7440797fc2ab3d3a9641f505ebc637121cbf",
        "resolution_state": "DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE",
    },
    "merge_seam_checklist": {
        "commit": "ff78860882748d3f03754f240e7a5c7f1873b174",
        "sha256": "48ea48fc41b6756de9cccf145bb4e89a16cc74ee8e51fabfc1715864bdf41206",
        "resolution_state": "DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE",
    },
    "owner_contract": {
        "sha256": "93fa0cf467aa93df67079b24066bf3aeb40c70df768621ec6b8f6a8ace90300e",
        "resolution_state": "DECLARED",
    },
    "semantic_review_notes": {
        "sha256": "ac8e8c2488c35966508e824b665f0730d471835d15af5422ed5964729a138b41",
        "resolution_state": "DECLARED",
    },
}

FIRST_OBSERVATIONS: dict[str, str] = {
    "FO-1": "fe6aeee35c5aa097812e88128ca1f88bc5f5616171eaefc90a0ca91451ba644b",
    "FO-2": "9c1a3c56a03d0608c837a6ed0ec43e1b81d1caa25004b624c4151ff4c9c483f9",
    "FO-3": "5c4fd18587ef75d408a7d818c761ae5cbc2490be9ec0df81abe8f9602e2dc927",
}


def _missing_prerequisites(clearance: dict[str, object]) -> list[str]:
    """Everything that must exist before a result-bearing run may start."""
    missing: list[str] = []
    if clearance["execution_clearance_ref"] == "ABSENT":
        missing.append("owner execution-clearance reference")
    if clearance["pytest_infrastructure"] != "RESOLVED":
        missing.append("PYTEST_INFRASTRUCTURE = RESOLVED")
    for name, declared in DECLARED_EXTERNAL_IDENTITIES.items():
        if declared.get("resolution_state") == "DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE":
            missing.append(f"resolvable artifact for {name}")
    return missing


def build_plan(output_root: Path) -> dict[str, Any]:
    """Assemble the complete run plan as data."""
    clearance = observe_clearance().as_record()
    fixtures = corpus()
    probe_map = [
        {"probe_id": probe.probe_id, "s_case": probe.s_case, "oracle_case": probe.oracle_case}
        for probe in PROBES
    ]
    return {
        "artifact_kind": "RUN_PLAN_ONLY",
        "result_bearing": False,
        "contract_id": CONTRACT_ID,
        "mission_id": MISSION_ID,
        "generated_by": "scripts/cdc_slice_run_plan.py",
        "execution_order": [
            {"step": 1, "phase": "S-cases", "case_ids": list(S_CASES)},
            {"step": 2, "phase": "adversarial probes", "probe_ids": [p.probe_id for p in PROBES]},
            {"step": 3, "phase": "observation records", "count": len(S_CASES) + len(PROBES)},
            {"step": 4, "phase": "evidence package assembly", "count": 1},
            {"step": 5, "phase": "deliverable rendering", "count": 1},
        ],
        "population": {"procedures": list(PROCEDURES), "controls": list(CONTROLS)},
        "cases_defined": len(S_CASES),
        "fixtures": fixtures,
        "adversarial": {
            "probes_defined": ADVERSARIAL_PROBES_DEFINED,
            "probes_executed": ADVERSARIAL_PROBES_EXECUTED,
            "denominator": ADVERSARIAL_DENOMINATOR,
            "definition_count_is_not_denominator": True,
            "probe_to_case_map": probe_map,
            "definitions": probe_definitions(),
        },
        "required_environment": REQUIRED_ENVIRONMENT,
        "declared_external_identities": DECLARED_EXTERNAL_IDENTITIES,
        "first_observation_provenance": FIRST_OBSERVATIONS,
        "expected_output_locations": {
            "observations": str(output_root / "observations"),
            "evidence_package": str(output_root / "evidence-package"),
            "deliverable": str(output_root / "deliverable" / "orientation-note.md"),
        },
        "interlock": clearance,
        "missing_prerequisites": _missing_prerequisites(clearance),
        "mission_executions": 0,
        "observed_results": "NOT_YET_OBSERVED",
    }


def validate_references(plan: dict[str, Any]) -> list[str]:
    """Check that every fixture reference resolves inside its own case."""
    problems: list[str] = []
    for record in plan["fixtures"]:
        case_id = record["case_id"]
        recomputed = fixture_record(case_id)
        if recomputed["input_digests"] != record["input_digests"]:
            problems.append(f"{case_id}: fixture digests are not reproducible")
        for key in ("candidate_ref", "control_ref", "admission_ref", "warrant_ref"):
            if not record.get(key):
                problems.append(f"{case_id}: missing {key}")
        if not record.get("evidence_refs"):
            problems.append(f"{case_id}: missing evidence_refs")
        if record.get("expected_observed_result") != "NOT_CARRIED_IN_FIXTURE":
            problems.append(f"{case_id}: fixture carries an expected observed result")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Emit the run plan. Never executes the plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("build/cdc-slice"))
    parser.add_argument("--write", type=Path, default=None)
    args = parser.parse_args(argv)

    plan = build_plan(args.output_root)
    problems = validate_references(plan)
    plan["reference_validation"] = {
        "problems": problems,
        "status": "OK" if not problems else "PROBLEMS_FOUND",
    }

    text = json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(text, encoding="utf-8")
        print(str(args.write))
    else:
        print(text, end="")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
