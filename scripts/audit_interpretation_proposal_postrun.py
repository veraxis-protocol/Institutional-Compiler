#!/usr/bin/env python3
"""Re-audit frozen Characterization 001 attempts without another model call.

The source receipt remains historical evidence.  This successor reads it only after
verifying its pinned SHA-256, preserves every historical metric under an unchanged
snapshot, and adds corrected measurement-layer projections.  It never imports a model
provider, constructs Institutional IR, or canonicalizes institutional meaning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"
OUTPUT_DIR = ROOT / "benchmarks/characterization/interpretation-proposal-001-postrun-audit"
OUTPUT = OUTPUT_DIR / "AUDIT.json"

WORK_ORDER = "OIC-INTERPRETATION-PROPOSAL-POSTRUN-AUDIT-001"
INSTRUMENT_SHA = "213ef5988f16f13cbf0b2e691b1873a740034a82"
RECEIPT_SHA256 = "29217e29207f7a1a5e32ae28bc7ae28cd9d33cc7acc591a9fb4aa0f38d59b7f5"
DISPOSITION = (
    "AMEND — INTERPRETATION PROPOSAL ARCHITECTURE RETAINED; "
    "CURRENT MODEL/PROMPT SEMANTICS NOT FREEZE-READY"
)

AMBIGUITY_CATEGORIES = (
    "ALTERNATIVES_SEPARATELY_SURFACED",
    "SINGLE_ALTERNATIVE_SELECTED",
    "ALTERNATIVES_CONJOINED_OR_COLLAPSED",
    "UNSUPPORTED_ALTERNATIVE",
    "AMBIGUOUS_SLOT_OMITTED",
)
ASSIGNMENT_CATEGORIES = (
    "UNGROUNDED_SOURCE_TEXT",
    "UNSUPPORTED_SEMANTIC_ASSIGNMENT",
    "WRONG_ROLE_ASSIGNMENT",
    "SUPPORTED_ROLE_ASSIGNMENT",
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(value: str) -> str:
    return " ".join(value.split()).casefold()


def compatible(left: str | None, right: str | None) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    lhs, rhs = key(left), key(right)
    return bool(lhs and rhs and (lhs in rhs or rhs in lhs))


def assertions(attempt: dict[str, Any], slot: str | None = None) -> list[dict[str, Any]]:
    proposal = attempt.get("proposal") or {}
    items = proposal.get("proposed_assertions", [])
    if slot is None:
        return list(items)
    return [item for item in items if item.get("slot") == slot]


def values(attempt: dict[str, Any], slot: str) -> list[str]:
    return [
        item["proposed_value"]
        for item in assertions(attempt, slot)
        if isinstance(item.get("proposed_value"), str) and item["proposed_value"].strip()
    ]


def accepted(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        attempt
        for attempt in receipt["attempts"]
        if attempt["outcome"] == "ACCEPTED" and attempt.get("proposal") is not None
    ]


def rescore_ambiguity(
    specimens: dict[str, dict[str, Any]], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: Counter[str] = Counter(dict.fromkeys(AMBIGUITY_CATEGORIES, 0))
    instances: list[dict[str, Any]] = []
    for attempt in attempts:
        specimen = specimens[attempt["specimen_id"]]
        for slot, gold in specimen["gold"]["expected_slots"].items():
            if gold["status"] != "AMBIGUOUS":
                continue
            alternatives = gold["alternatives"]
            proposed = values(attempt, slot)
            matches = [
                {
                    index
                    for index, alternative in enumerate(alternatives)
                    if compatible(value, alternative)
                }
                for value in proposed
            ]
            nonempty = [item for item in matches if item]
            surfaced = set().union(*nonempty) if nonempty else set()
            if not proposed:
                category = "AMBIGUOUS_SLOT_OMITTED"
            elif len(nonempty) >= 2 and len(surfaced) >= 2:
                category = "ALTERNATIVES_SEPARATELY_SURFACED"
            elif any(len(item) >= 2 for item in matches):
                category = "ALTERNATIVES_CONJOINED_OR_COLLAPSED"
            elif len(surfaced) == 1 and all(item <= surfaced for item in matches):
                category = "SINGLE_ALTERNATIVE_SELECTED"
            else:
                category = "UNSUPPORTED_ALTERNATIVE"
            counts[category] += 1
            instances.append(
                {
                    "specimen_id": attempt["specimen_id"],
                    "run_index": attempt["run_index"],
                    "slot": slot,
                    "gold_alternatives": alternatives,
                    "proposed_values": proposed,
                    "category": category,
                }
            )
    return {"counts": dict(counts), "instances": instances}


def _gold_values(specimen: dict[str, Any], slot: str) -> list[str]:
    gold = specimen["gold"]["expected_slots"][slot]
    if gold["status"] == "ESTABLISHED" and isinstance(gold["value"], str):
        return [gold["value"]]
    if gold["status"] == "AMBIGUOUS":
        return list(gold["alternatives"])
    return []


def audit_assignments(
    specimens: dict[str, dict[str, Any]], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: Counter[str] = Counter(dict.fromkeys(ASSIGNMENT_CATEGORIES, 0))
    counts["NO_SOURCE_QUOTE"] = 0
    instances: list[dict[str, Any]] = []
    for attempt in attempts:
        specimen = specimens[attempt["specimen_id"]]
        span = specimen["candidate"]["candidate_span"]
        for item in assertions(attempt):
            value, quote, slot = (
                item.get("proposed_value"),
                item.get("proposed_source_quote"),
                item["slot"],
            )
            if not isinstance(value, str) or not value.strip():
                continue
            if not isinstance(quote, str) or not quote.strip():
                category = "NO_SOURCE_QUOTE"
            elif key(quote) not in key(span):
                category = "UNGROUNDED_SOURCE_TEXT"
            else:
                gold = specimen["gold"]["expected_slots"][slot]
                expected = _gold_values(specimen, slot)
                if gold["status"] in {"NOT_ESTABLISHED", "NOT_APPLICABLE"}:
                    category = "UNSUPPORTED_SEMANTIC_ASSIGNMENT"
                elif (
                    slot == "normative_force" and value == specimen["gold"]["expected_force"]
                ) or any(compatible(value, candidate) for candidate in expected):
                    category = "SUPPORTED_ROLE_ASSIGNMENT"
                else:
                    other_roles = [
                        other
                        for other in specimen["gold"]["expected_slots"]
                        if other != slot
                        and any(
                            compatible(value, candidate) or compatible(quote, candidate)
                            for candidate in _gold_values(specimen, other)
                        )
                    ]
                    category = (
                        "WRONG_ROLE_ASSIGNMENT"
                        if other_roles
                        else "UNSUPPORTED_SEMANTIC_ASSIGNMENT"
                    )
            counts[category] += 1
            if category != "SUPPORTED_ROLE_ASSIGNMENT":
                instances.append(
                    {
                        "specimen_id": attempt["specimen_id"],
                        "run_index": attempt["run_index"],
                        "slot": slot,
                        "proposed_value": value,
                        "proposed_source_quote": quote,
                        "category": category,
                    }
                )
    return {"counts": dict(counts), "instances": instances}


def _moved_to_slot(attempt: dict[str, Any], expected: str, target: str) -> list[str]:
    return sorted(
        {
            item["slot"]
            for item in assertions(attempt)
            if item["slot"] != target
            and isinstance(item.get("proposed_value"), str)
            and compatible(item["proposed_value"], expected)
        }
    )


def audit_strengthening(
    specimens: dict[str, dict[str, Any]], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []

    def record(category: str, attempt: dict[str, Any], **details: object) -> None:
        counts[category] += 1
        instances.append(
            {
                "specimen_id": attempt["specimen_id"],
                "run_index": attempt["run_index"],
                "category": category,
                **details,
            }
        )

    for attempt in attempts:
        specimen = specimens[attempt["specimen_id"]]
        slots = specimen["gold"]["expected_slots"]
        for slot, omitted_category, moved_category in (
            ("condition", "CONDITION_OMITTED", "CONDITION_MOVED_TO_WRONG_ROLE"),
            ("exception", "EXCEPTION_OMITTED", "EXCEPTION_MOVED_TO_CONDITION"),
            (
                "temporal_qualifier",
                "TEMPORAL_QUALIFIER_OMITTED",
                "TEMPORAL_QUALIFIER_MOVED_TO_CONDITION",
            ),
        ):
            gold = slots[slot]
            if gold["status"] != "ESTABLISHED":
                continue
            expected = gold["value"]
            if any(compatible(value, expected) for value in values(attempt, slot)):
                continue
            moved = _moved_to_slot(attempt, expected, slot)
            if moved:
                record(moved_category, attempt, expected_value=expected, observed_slots=moved)
            else:
                record(omitted_category, attempt, expected_value=expected)

        quantum = slots["quantum"]
        comparators = [
            q["text"]
            for q in quantum.get("material_qualifiers", [])
            if q["qualifier_kind"] == "COMPARATOR"
        ]
        if quantum["status"] == "ESTABLISHED" and comparators:
            expected_numbers = re.findall(r"\d+(?:\.\d+)?", quantum["value"])
            for proposed in values(attempt, "quantum"):
                if (
                    expected_numbers
                    and all(number in proposed for number in expected_numbers)
                    and not any(key(comparator) in key(proposed) for comparator in comparators)
                ):
                    record(
                        "THRESHOLD_BROADENED_BY_COMPARATOR_LOSS",
                        attempt,
                        expected_value=quantum["value"],
                        proposed_value=proposed,
                        missing_comparators=comparators,
                    )
                    break

        bearer = slots["bearer"]
        counterparty = slots["counterparty"]
        if (
            bearer["status"] == "ESTABLISHED"
            and counterparty["status"] == "ESTABLISHED"
            and any(compatible(value, counterparty["value"]) for value in values(attempt, "bearer"))
        ):
            record(
                "RECIPIENT_PROMOTED_TO_BEARER",
                attempt,
                recipient=counterparty["value"],
            )
    return {"counts": dict(sorted(counts.items())), "instances": instances}


def reference_headline(receipt: dict[str, Any]) -> dict[str, int]:
    counts = receipt["metrics"]["K_unresolved_reference_recall"]["counts"]
    correct = counts.get("correct_kind", 0)
    wrong = counts.get("wrong_kind", 0)
    return {
        "expected": counts.get("expected", 0),
        "surfaced": correct + wrong,
        "correct_reference_kind": correct,
        "wrong_reference_kind": wrong,
        "omitted": counts.get("omitted", 0),
        "invented": counts.get("invented", 0),
        "semantically_resolved_instead_of_surfaced": counts.get("resolved_instead_of_surfaced", 0),
    }


def stability_headline(receipt: dict[str, Any]) -> dict[str, Any]:
    metric = receipt["metrics"]["M_repeat_stability"]
    denominator = len(metric)
    slots = sorted(
        next(
            value["per_slot_value_stable"]
            for value in metric.values()
            if "per_slot_value_stable" in value
        )
    )
    return {
        "specimen_denominator": denominator,
        "semantic_hash_stable_specimens": sum(
            bool(value.get("semantic_hash_stable")) for value in metric.values()
        ),
        "force_stable_specimens": sum(bool(value.get("force_stable")) for value in metric.values()),
        "slot_set_stable_specimens": sum(
            bool(value.get("slot_set_stable")) for value in metric.values()
        ),
        "per_slot_value_stable_specimens": {
            slot: sum(
                bool(value.get("per_slot_value_stable", {}).get(slot)) for value in metric.values()
            )
            for slot in slots
        },
        "provider_successful_runs_by_specimen": {
            specimen_id: value["accepted_runs"] for specimen_id, value in metric.items()
        },
        "IIR-032_note": "two provider-successful runs; all other specimens have three",
        "binding_note": (
            "Deterministic OIC binding is provenance stability, not model-semantic stability."
        ),
    }


def build_audit(receipt: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    specimens = {item["specimen_id"]: item for item in corpus["specimens"]}
    attempts = accepted(receipt)
    historical = receipt["metrics"]
    established = historical["E_established_slot_recall"]["per_slot"]
    established_headline = {
        "expected_established": sum(item["expected_established"] for item in established.values()),
        "compatible": sum(item["proposed_compatible"] for item in established.values()),
        "omitted": sum(item["omitted"] for item in established.values()),
        "incompatible": sum(item["incompatible"] for item in established.values()),
    }
    boundary = historical["A_provider_structural_boundary"]
    quote_grounding = historical["I_source_quote_grounding"]
    return {
        "work_order": WORK_ORDER,
        "source_instrument_sha": INSTRUMENT_SHA,
        "source_receipt_sha256": RECEIPT_SHA256,
        "source_corpus_sha256": receipt["corpus_sha256"],
        "provider": receipt["provider"],
        "model": receipt["model"],
        "historical_metrics": historical,
        "historical_metrics_canonical_sha256": hashlib.sha256(canonical(historical)).hexdigest(),
        "authoritative_observations": {
            "planned_requests": boundary["requests_planned"],
            "attempted": boundary["requests_attempted"],
            "accepted_proposals": boundary["accepted_proposals"],
            "provider_errors": boundary["provider_errors"],
            "boundary_rejections": boundary["proposal_boundary_rejected"],
            "source_quotes_grounded": quote_grounding["grounded"],
            "source_quotes_ungrounded": quote_grounding["ungrounded"],
        },
        "corrected_metrics": {
            "ambiguity": rescore_ambiguity(specimens, attempts),
            "source_text_and_semantic_assignment": audit_assignments(specimens, attempts),
            "semantic_strengthening": audit_strengthening(specimens, attempts),
            "established_slots": established_headline,
            "references": reference_headline(receipt),
            "repeat_stability": stability_headline(receipt),
        },
        "population_rate_claimed": False,
        "canonicalization_performed": False,
        "institutional_ir_runtime_implemented": False,
        "new_model_call_made": False,
        "owner_disposition": DISPOSITION,
        "limitations": [
            "One frozen run, one model/provider, 29 synthetic specimens; no population rate.",
            "Gold is preregistered design evidence, not independent semantic truth.",
            "Literal quote grounding does not establish correct semantic-role assignment.",
            "Corrected categories are deterministic measurement projections, not "
            "canonical meaning.",
        ],
        "claim_ceiling": (
            "A corrected audit interpretation of one frozen live characterization only; no "
            "semantic correctness, canonical institutional meaning, model authority, production "
            "readiness, cross-model generalization, canonicalization, Institutional IR runtime, "
            "legal interpretation, or independent validation is established."
        ),
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.receipt.is_file():
        raise SystemExit("FAIL source receipt is absent")
    if sha256(args.receipt) != RECEIPT_SHA256:
        raise SystemExit("FAIL source receipt SHA-256 differs from the frozen digest")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    audit = build_audit(receipt, corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS postrun audit written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
