#!/usr/bin/env python3
"""Serialize a raw observation into an empty adjudication-record input form.

This is a handoff, not a judgement. It copies observed fields into the shape the
frozen adjudication protocol expects and leaves every verdict slot empty. It
does **not** compute ``MATCH``, ``SEMANTIC_VIOLATION``, ``FORBIDDEN_PROMOTION``,
``PASS``, ``FAIL`` or ``INCOMPLETE`` — those belong to the adjudication layer and
to Vitaliy's oracle, which is external to this runtime.

The handoff ends at ``OBSERVATION_READY_FOR_ADJUDICATION``. Anything past that
line is someone else's authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "integration"))

from cdc_slice_observation import assert_no_adjudication  # noqa: E402

HANDOFF_STATE: Final = "OBSERVATION_READY_FOR_ADJUDICATION"

# Verdict slots are created empty and never filled here.
UNCOMPUTED: Final = "NOT_YET_ADJUDICATED"

VERDICT_SLOTS: Final[tuple[str, ...]] = (
    "match",
    "semantic_violation",
    "forbidden_promotion",
    "pass_fail",
    "completeness",
)


def to_adjudication_input(observation: dict[str, Any], oracle_case_ref: str) -> dict[str, Any]:
    """Build the adjudication-record input form from one observation.

    Observed fields are copied verbatim. Verdict slots are present but empty so
    the adjudicator fills them; this tool cannot.
    """
    assert_no_adjudication(observation)
    record: dict[str, Any] = {
        "schema_version": "CDC-SLICE-ADJUDICATION-INPUT-v0.1",
        "handoff_state": HANDOFF_STATE,
        "computed_by_handoff": [],
        "oracle_case_ref": oracle_case_ref,
        "observation": {
            "observation_id": observation.get("observation_id"),
            "case_id": observation.get("case_id"),
            "run_id": observation.get("run_id"),
            "observation_digest": observation.get("observation_digest"),
            "input_digests": observation.get("input_digests"),
            "precondition_record": observation.get("precondition_record"),
            "epistemic_state_observed": observation.get("epistemic_state_observed"),
            "operational_state_observed": observation.get("operational_state_observed"),
            "institutional_state_observed": observation.get("institutional_state_observed"),
            "transition_executed": observation.get("transition_executed"),
            "reason_codes": observation.get("reason_codes"),
            "preserved_artifact_refs": observation.get("preserved_artifact_refs"),
            "failure_refs": observation.get("failure_refs"),
            "side_effect_refs": observation.get("side_effect_refs"),
            "raw_output_refs": observation.get("raw_output_refs"),
        },
    }
    for slot in VERDICT_SLOTS:
        record[slot] = UNCOMPUTED
    return record


def main(argv: list[str] | None = None) -> int:
    """Serialize one observation for handoff."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--oracle-case-ref", required=True)
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.observation.is_file():
        print(
            "no observation supplied; handoff is refused. This tool serializes an "
            "existing observation and never produces one.",
            file=sys.stderr,
        )
        return 2

    observation: Any = json.loads(args.observation.read_text(encoding="utf-8"))
    record = to_adjudication_input(observation, args.oracle_case_ref)
    text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.destination is not None:
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        args.destination.write_text(text, encoding="utf-8")
        print(str(args.destination))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
