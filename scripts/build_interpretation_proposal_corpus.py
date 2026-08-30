#!/usr/bin/env python3
"""Build the frozen Interpretation Proposal Characterization 001 corpus.

Design tooling. It carries a focused subset of the frozen Institutional IR 001 design
corpus into a characterization corpus, preserving the admitted candidate bytes, the
admission receipt and the source instance exactly, and attaching the preregistered
expected interpretation as evaluator-only gold.

The gold is metadata for the evaluator. It is never sent to a provider: the request body is
built by `oic.interpretation_proposal` from the candidate span alone, and a contract test
proves the gold text does not appear in it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.interpretation_proposal import SLOT_VOCABULARY  # noqa: E402 - path prepared above

DESIGN = ROOT / "design/institutional-ir-001"
OUT = ROOT / "benchmarks/characterization/interpretation-proposal-001"
CORPUS_PATH = OUT / "CORPUS-v0.1.json"
FREEZE_PATH = OUT / "CORPUS-FREEZE-v0.1.json"

CORPUS_ID = "OIC-INTERPRETATION-PROPOSAL-001-CORPUS-v0.1"
SOURCE_CORPUS = "design/institutional-ir-001/TEST-VECTORS-v0.1.json"
SOURCE_CORPUS_SHA256 = "5761b82cc67c8bfb139689d04c7ca36283d0c6e63fd8f82199b8a1fa9d013358"
PROPOSAL_SCHEMA_SHA256 = "0e71dc3fbd20d2b025549df565314c0f90f69d36ec2eb874915a865731c437df"
RULESET_SHA256 = "8ba398eb20d346d66ce49c0f638babe2167930a07c3bd2946757fa41d6ccb114"
RULESET_CANONICAL_DIGEST = "sha256:e3751aac77b2ef0a0cdad99aff44d47861cd6d7d39d044e485a520a452e75b71"

RUNS_PER_SPECIMEN = 3

#: The 29 ADMITTED design vectors carried into the live corpus, in the order the work
#: order names them. The five non-ADMITTED IR input-boundary vectors are deliberately
#: excluded: they test the IR seam, not proposal quality.
SELECTED = (
    "IIR-001",
    "IIR-002",
    "IIR-003",
    "IIR-004",
    "IIR-005",
    "IIR-006",
    "IIR-007",
    "IIR-008",
    "IIR-009",
    "IIR-010",
    "IIR-011",
    "IIR-012",
    "IIR-013",
    "IIR-014",
    "IIR-015",
    "IIR-016",
    "IIR-017",
    "IIR-018",
    "IIR-023",
    "IIR-024",
    "IIR-025",
    "IIR-026",
    "IIR-027",
    "IIR-028",
    "IIR-029",
    "IIR-030",
    "IIR-031",
    "IIR-032",
    "IIR-035",
)

#: Extra risk tags beyond the design corpus's own threat tags, naming the specific defect
#: each specimen is carried to expose.
SEMANTIC_RISK_TAGS: dict[str, tuple[str, ...]] = {
    "IIR-009": ("vague_temporal_normalization",),
    "IIR-015": ("passive_actor",),
    "IIR-016": ("bearer_counterparty_separation",),
    "IIR-017": ("ambiguity_overcommitment",),
    "IIR-018": ("ambiguity_overcommitment",),
    "IIR-024": ("definition_resolved_instead_of_surfaced",),
    "IIR-025": ("reference_resolved_instead_of_surfaced",),
    "IIR-026": ("reference_resolved_instead_of_surfaced",),
    "IIR-027": ("advisory_strengthening",),
    "IIR-028": ("permission_strengthening",),
    "IIR-029": ("invented_actor",),
    "IIR-030": ("dropped_exception",),
    "IIR-031": ("dropped_threshold",),
    "IIR-032": ("added_business_convention",),
    "IIR-035": ("explicit_not_established",),
}

CLAIM_CEILING = (
    "Characterization 001 measures one model and provider proposing provisional semantic "
    "structure over a small frozen synthetic admitted-candidate corpus. It does not "
    "establish canonical institutional meaning, semantic correctness generally, "
    "interpretation authority, legal interpretation, successful Institutional IR "
    "construction, model suitability for autonomous canonicalization, production "
    "readiness, cross-model generalization, or independent validation."
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _gold_from_unit(unit: dict[str, Any]) -> dict[str, Any]:
    """The preregistered expected interpretation, as evaluator-only metadata."""
    slots: dict[str, Any] = {}
    for assertion in unit["assertions"]:
        slots[assertion["slot"]] = {
            "status": assertion["interpretation_status"],
            "value": assertion["value"],
            "alternatives": [item["value"] for item in assertion["alternatives"]],
            "material_qualifiers": [
                {"qualifier_kind": item["qualifier_kind"], "text": item["text"]}
                for item in assertion["material_qualifiers"]
            ],
            "normalization": (
                None
                if assertion["normalization"] is None
                else {
                    "kind": assertion["normalization"]["kind"],
                    "raw_source_text": assertion["normalization"]["raw_source_text"],
                }
            ),
        }
    force = slots["normative_force"]
    return {
        "expected_force": force["value"],
        "expected_slots": slots,
        "expected_unresolved_references": [
            {
                "reference_text": reference["reference_text"],
                "reference_kind": reference["reference_kind"],
            }
            for reference in unit["unresolved_references"]
        ],
        "exception_closure": unit["exception_closure"],
    }


def build() -> dict[str, Any]:
    source = json.loads((ROOT / SOURCE_CORPUS).read_text(encoding="utf-8"))
    raw = (ROOT / SOURCE_CORPUS).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_CORPUS_SHA256:
        raise AssertionError("source IR design corpus digest does not match the pinned value")

    by_id = {vector["vector_id"]: vector for vector in source["vectors"]}
    missing = [identifier for identifier in SELECTED if identifier not in by_id]
    if missing:
        raise AssertionError(f"selected design vectors are absent from the corpus: {missing}")

    specimens: list[dict[str, Any]] = []
    for identifier in SELECTED:
        vector = by_id[identifier]
        receipts = vector["admission_receipts"]
        if vector["expected_boundary_rejection"] is not None:
            raise AssertionError(f"{identifier}: boundary vector may not enter the live corpus")
        if [receipt["admission_state"] for receipt in receipts] != ["ADMITTED"]:
            raise AssertionError(f"{identifier}: specimen is not a single ADMITTED receipt")
        if len(vector["expected_canonical_ir"]) != 1:
            raise AssertionError(f"{identifier}: expected exactly one canonical unit")

        receipt = receipts[0]
        admission_input = vector["admission_inputs"][0]
        candidate = admission_input["candidate"]
        unit = vector["expected_canonical_ir"][0]

        if candidate["candidate_span"] != vector["source_text"]:
            raise AssertionError(f"{identifier}: candidate span is not the admitted source text")

        specimens.append(
            {
                "specimen_id": identifier,
                "design_vector_id": identifier,
                "title": vector["title"],
                "category": vector["category"],
                "threat_tags": vector["threat_tags"],
                "semantic_risk_tags": list(SEMANTIC_RISK_TAGS.get(identifier, ())),
                "candidate": {
                    "unit_id": candidate["unit_id"],
                    "candidate_span": candidate["candidate_span"],
                    "unit_type": candidate["unit_type"],
                    "interpretation_state": candidate["interpretation_state"],
                    "epistemic_state": candidate["epistemic_state"],
                    "candidate_digest": "sha256:"
                    + hashlib.sha256(_canonical(candidate)).hexdigest(),
                },
                "admission": {
                    "admission_receipt_id": receipt["admission_receipt_id"],
                    "admission_state": receipt["admission_state"],
                    "reason_code": receipt["reason_code"],
                    "candidate_unit_id": receipt["candidate_unit_id"],
                    "candidate_projection_digest": receipt["candidate_projection_digest"],
                    "source_id": receipt["source_id"],
                    "source_version": receipt["source_version"],
                    "source_digest": receipt["source_digest"],
                    "evaluation_time": receipt["evaluation_time"],
                },
                "gold": _gold_from_unit(unit),
                "gold_is_evaluator_only": True,
            }
        )

    for specimen in specimens:
        slots = set(specimen["gold"]["expected_slots"])
        if slots != set(SLOT_VOCABULARY):
            raise AssertionError(f"{specimen['specimen_id']}: gold does not cover all slots")

    return {
        "corpus_id": CORPUS_ID,
        "work_order": "OIC-INTERPRETATION-PROPOSAL-CHARACTERIZATION-001",
        "act": "3_INTERPRETATION_PROPOSAL",
        "source_corpus": SOURCE_CORPUS,
        "source_corpus_sha256": SOURCE_CORPUS_SHA256,
        "proposal_schema": "design/institutional-ir-001/INTERPRETATION-PROPOSAL-v0.1.schema.json",
        "proposal_schema_sha256": PROPOSAL_SCHEMA_SHA256,
        "interpretation_ruleset": "design/institutional-ir-001/INTERPRETATION-RULESET-v0.1.json",
        "interpretation_ruleset_sha256": RULESET_SHA256,
        "interpretation_ruleset_canonical_digest": RULESET_CANONICAL_DIGEST,
        "slot_vocabulary": list(SLOT_VOCABULARY),
        "specimen_count": len(specimens),
        "runs_per_specimen": RUNS_PER_SPECIMEN,
        "planned_live_requests": len(specimens) * RUNS_PER_SPECIMEN,
        "include_provisional_unit_type_in_prompt": False,
        "unit_type_arm_rationale": (
            "Characterization 001 preregisters the candidate_span-only arm. The provisional "
            "unit_type is an earlier model's uncertain classification; passing it would let "
            "the interpretation stage inherit and reinforce a prior model's error before "
            "there is any evidence the hint helps. The harness supports the second arm so a "
            "later A/B can run it; that A/B is not run here."
        ),
        "gold_is_evaluator_only": True,
        "gold_never_sent_to_provider": True,
        "live_run_executed": False,
        "specimens": specimens,
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    corpus = build()
    CORPUS_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    raw = CORPUS_PATH.read_bytes()
    freeze = {
        "freeze_id": "OIC-INTERPRETATION-PROPOSAL-001-CORPUS-FREEZE-v0.1",
        "corpus_id": CORPUS_ID,
        "corpus_path": "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json",
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_bytes": len(raw),
        "specimen_count": corpus["specimen_count"],
        "runs_per_specimen": corpus["runs_per_specimen"],
        "planned_live_requests": corpus["planned_live_requests"],
        "selected_design_vector_ids": list(SELECTED),
        "source_corpus_sha256": SOURCE_CORPUS_SHA256,
        "proposal_schema_sha256": PROPOSAL_SCHEMA_SHA256,
        "interpretation_ruleset_sha256": RULESET_SHA256,
        "interpretation_ruleset_canonical_digest": RULESET_CANONICAL_DIGEST,
        "include_provisional_unit_type_in_prompt": False,
        "live_run_executed": False,
        "model_call_made": False,
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }
    FREEZE_PATH.write_text(
        json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"specimens: {corpus['specimen_count']}  "
        f"planned requests: {corpus['planned_live_requests']}"
    )
    print(f"corpus sha256: {freeze['corpus_sha256']}  bytes: {freeze['corpus_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
