#!/usr/bin/env python3
"""Characterize model-proposed interpretation over the frozen admitted-candidate corpus.

The question: can a model propose useful semantic structure from an admitted candidate
without being allowed to establish canonical institutional meaning?

This instrument measures act 3 only. It compares provisional proposals against the
preregistered canonical design gold and reports what it finds. It never canonicalizes:
it assigns no interpretation status, issues no interpretation evidence or warrant, and
constructs no Institutional IR object. There is no repair anywhere - an ungrounded quote,
an invented actor and a dropped exception are recorded exactly as returned, because
repairing them before measurement is how an instrument comes to show nothing.

Aggregate scores hide defects. Every metric reports raw counts and named instances, the
force metric reports a confusion matrix rather than an accuracy, and the eleven critical
specimens are reported run by run.

Offline by default. `--live` is the owner's switch; without it no provider is constructed
and no request is made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oic.interpretation_proposal import (  # noqa: E402 - path prepared above
    FORCE_VALUES,
    SLOT_VOCABULARY,
    AdmittedCandidateBinding,
    InterpretationProposalError,
    ProposalBoundaryError,
    grounding_key,
    is_quote_grounded,
    propose_interpretation,
)
from oic.model_provider import (  # noqa: E402 - path prepared above
    ModelProvider,
    ModelProviderError,
)

WORK_ORDER = "OIC-INTERPRETATION-PROPOSAL-CHARACTERIZATION-001"
STARTING_SHA = "3194ef0fbe465a583f797aa52a35131f50b18aa0"

CORPUS_DIR = ROOT / "benchmarks/characterization/interpretation-proposal-001"
CORPUS_PATH = CORPUS_DIR / "CORPUS-v0.1.json"
FREEZE_PATH = CORPUS_DIR / "CORPUS-FREEZE-v0.1.json"
DESIGN = ROOT / "design/institutional-ir-001"
PROPOSAL_SCHEMA_PATH = DESIGN / "INTERPRETATION-PROPOSAL-v0.1.schema.json"
RULESET_PATH = DESIGN / "INTERPRETATION-RULESET-v0.1.json"
SOURCE_CORPUS_PATH = DESIGN / "TEST-VECTORS-v0.1.json"
INSTRUMENT_PATH = Path(__file__).resolve()

RECEIPT_PATH = (
    ROOT
    / ".local/interpretation-proposal-receipts"
    / "OIC-INTERPRETATION-PROPOSAL-CHARACTERIZATION-001.json"
)

PROPOSER_ID = "oic-interpretation-proposer-001"

#: The specimens whose every run is reported individually. CSEM history is the reason:
#: an aggregate that looks acceptable can hide a defect that occurs every single time.
CRITICAL_SPECIMENS: tuple[tuple[str, str], ...] = (
    ("IIR-015", "passive actor"),
    ("IIR-016", "bearer vs counterparty"),
    ("IIR-017", "ambiguity"),
    ("IIR-018", "ambiguity"),
    ("IIR-027", "advisory strengthening"),
    ("IIR-028", "permission strengthening"),
    ("IIR-029", "invented actor"),
    ("IIR-030", "dropped exception"),
    ("IIR-031", "dropped threshold"),
    ("IIR-032", "added business convention"),
    ("IIR-035", "explicit NOT_ESTABLISHED"),
)

ACCEPTED = "ACCEPTED"
BOUNDARY_REJECTED = "BOUNDARY_REJECTED"
PROVIDER_ERROR = "PROVIDER_ERROR"


# ---------------------------------------------------------------------------
# Governing artifact verification
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_governing_artifacts() -> dict[str, str]:
    """Refuse to run against anything but the frozen artifacts."""
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    digests = {
        "corpus_sha256": _sha256(CORPUS_PATH),
        "source_ir_design_corpus_sha256": _sha256(SOURCE_CORPUS_PATH),
        "proposal_schema_sha256": _sha256(PROPOSAL_SCHEMA_PATH),
        "interpretation_ruleset_sha256": _sha256(RULESET_PATH),
        "instrument_sha256": _sha256(INSTRUMENT_PATH),
    }
    expected = {
        "corpus_sha256": freeze["corpus_sha256"],
        "source_ir_design_corpus_sha256": freeze["source_corpus_sha256"],
        "proposal_schema_sha256": freeze["proposal_schema_sha256"],
        "interpretation_ruleset_sha256": freeze["interpretation_ruleset_sha256"],
    }
    for key, value in expected.items():
        if digests[key] != value:
            raise SystemExit(f"FAIL frozen artifact digest mismatch: {key}")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    selected = [specimen["specimen_id"] for specimen in corpus["specimens"]]
    if selected != freeze["selected_design_vector_ids"]:
        raise SystemExit("FAIL corpus specimen selection does not match the freeze")
    ruleset_digest = (
        "sha256:"
        + hashlib.sha256(
            _canonical(json.loads(RULESET_PATH.read_text(encoding="utf-8")))
        ).hexdigest()
    )
    if ruleset_digest != freeze["interpretation_ruleset_canonical_digest"]:
        raise SystemExit("FAIL interpretation ruleset canonical digest mismatch")
    digests["interpretation_ruleset_canonical_digest"] = ruleset_digest
    return digests


# ---------------------------------------------------------------------------
# Corpus and attempts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Specimen:
    """One frozen admitted specimen and its evaluator-only gold."""

    specimen_id: str
    title: str
    threat_tags: tuple[str, ...]
    semantic_risk_tags: tuple[str, ...]
    candidate_span: str
    unit_type: str
    binding: AdmittedCandidateBinding
    gold: dict[str, Any]

    @property
    def expected_force(self) -> str | None:
        force: str | None = self.gold["expected_force"]
        return force

    def gold_slot(self, slot: str) -> dict[str, Any]:
        entry: dict[str, Any] = self.gold["expected_slots"][slot]
        return entry


def load_specimens(corpus: dict[str, Any], *, include_unit_type: bool) -> tuple[Specimen, ...]:
    specimens: list[Specimen] = []
    for entry in corpus["specimens"]:
        admission = entry["admission"]
        if admission["admission_state"] != "ADMITTED":
            raise SystemExit(f"FAIL non-ADMITTED specimen in live corpus: {entry['specimen_id']}")
        candidate = entry["candidate"]
        specimens.append(
            Specimen(
                specimen_id=entry["specimen_id"],
                title=entry["title"],
                threat_tags=tuple(entry["threat_tags"]),
                semantic_risk_tags=tuple(entry["semantic_risk_tags"]),
                candidate_span=candidate["candidate_span"],
                unit_type=candidate["unit_type"],
                binding=AdmittedCandidateBinding(
                    admission_receipt_id=admission["admission_receipt_id"],
                    admission_state=admission["admission_state"],
                    candidate_unit_id=admission["candidate_unit_id"],
                    candidate_projection_digest=admission["candidate_projection_digest"],
                    candidate_span=candidate["candidate_span"],
                    provisional_unit_type=candidate["unit_type"] if include_unit_type else None,
                ),
                gold=entry["gold"],
            )
        )
    return tuple(specimens)


@dataclass(slots=True)
class Attempt:
    """One planned provider request and whatever came back."""

    specimen_id: str
    run_index: int
    outcome: str
    proposal: dict[str, Any] | None = None
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None
    raw_content_sha256: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "specimen_id": self.specimen_id,
            "run_index": self.run_index,
            "outcome": self.outcome,
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "raw_content_sha256": self.raw_content_sha256,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "proposal": self.proposal,
            "semantic_hash": None if self.proposal is None else semantic_hash(self.proposal),
        }


def execute_attempts(
    specimens: Sequence[Specimen], provider: ModelProvider, *, runs_per_specimen: int
) -> list[Attempt]:
    """Exactly one provider call per planned attempt. No retry, no backoff, no pacing."""
    attempts: list[Attempt] = []
    for specimen in specimens:
        for run_index in range(1, runs_per_specimen + 1):
            attempt = Attempt(
                specimen_id=specimen.specimen_id, run_index=run_index, outcome=PROVIDER_ERROR
            )
            try:
                result = propose_interpretation(
                    binding=specimen.binding, provider=provider, proposer_id=PROPOSER_ID
                )
            except ProposalBoundaryError as exc:
                attempt.outcome = BOUNDARY_REJECTED
                attempt.error_type = type(exc).__name__
                attempt.error_message = str(exc)
            except (InterpretationProposalError, ModelProviderError) as exc:
                attempt.outcome = PROVIDER_ERROR
                attempt.error_type = type(exc).__name__
                attempt.error_message = str(exc)
            else:
                attempt.outcome = ACCEPTED
                attempt.proposal = result.proposal
                attempt.provider = result.provider
                attempt.model = result.model
                attempt.request_id = result.request_id
                attempt.raw_content_sha256 = result.raw_content_sha256
            attempts.append(attempt)
    return attempts


# ---------------------------------------------------------------------------
# Semantic projection and hash
# ---------------------------------------------------------------------------


def semantic_projection(proposal: dict[str, Any]) -> dict[str, Any]:
    """Meaning-bearing content only, for run-to-run stability measurement.

    Excludes `proposal_id`, the proposer and every OIC binding field. This is a
    characterization artifact and is NOT the canonical IR `semantic_equivalence_key`; the
    two must never be conflated, because this one describes an untrusted suggestion.
    """
    assertions = sorted(
        (
            {
                "slot": item["slot"],
                "proposed_value": item["proposed_value"],
                "proposed_source_quote": item["proposed_source_quote"],
                "proposed_material_qualifiers": sorted(
                    item.get("proposed_material_qualifiers", [])
                ),
            }
            for item in proposal.get("proposed_assertions", [])
        ),
        key=lambda item: (
            item["slot"],
            item["proposed_value"] or "",
            item["proposed_source_quote"] or "",
        ),
    )
    references = sorted(
        (
            {"reference_text": item["reference_text"], "reference_kind": item["reference_kind"]}
            for item in proposal.get("proposed_unresolved_references", [])
        ),
        key=lambda item: (item["reference_text"], item["reference_kind"]),
    )
    return {"proposed_assertions": assertions, "proposed_unresolved_references": references}


def semantic_hash(proposal: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(semantic_projection(proposal))).hexdigest()


# ---------------------------------------------------------------------------
# Preregistered deterministic comparison
# ---------------------------------------------------------------------------


def compatible(proposed: str | None, expected: str | None) -> bool:
    """Preregistered comparison: containment either way after casefold and whitespace collapse.

    Deliberately not literal equality. Legitimate proposal values include semantic labels
    and role phrasings that differ in article or determiner from the gold wording ("the
    manager" against "manager"). Deliberately not a model judge either: the rule is fixed,
    inspectable, and identical on every run.
    """
    if proposed is None or expected is None:
        return False
    left, right = grounding_key(proposed), grounding_key(expected)
    if not left or not right:
        return False
    return left in right or right in left


def _assertions(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = proposal.get("proposed_assertions", [])
    return items


def _for_slot(proposal: dict[str, Any], slot: str) -> list[dict[str, Any]]:
    return [item for item in _assertions(proposal) if item["slot"] == slot]


def _values_for_slot(proposal: dict[str, Any], slot: str) -> list[str]:
    return [
        item["proposed_value"]
        for item in _for_slot(proposal, slot)
        if isinstance(item["proposed_value"], str) and item["proposed_value"].strip()
    ]


def _qualifier_texts(proposal: dict[str, Any], slot: str) -> list[str]:
    texts: list[str] = []
    for item in _for_slot(proposal, slot):
        texts.extend(item.get("proposed_material_qualifiers", []))
    return texts


def _accepted(attempts: Iterable[Attempt]) -> list[Attempt]:
    return [attempt for attempt in attempts if attempt.outcome == ACCEPTED and attempt.proposal]


# ---------------------------------------------------------------------------
# Metrics A - M
# ---------------------------------------------------------------------------


def metric_a_provider_boundary(attempts: Sequence[Attempt], planned: int) -> dict[str, Any]:
    """A. Provider and structural boundary. Provider errors stay separate from semantics."""
    outcomes = Counter(attempt.outcome for attempt in attempts)
    return {
        "requests_planned": planned,
        "requests_attempted": len(attempts),
        "provider_accepted": outcomes[ACCEPTED] + outcomes[BOUNDARY_REJECTED],
        "provider_errors": outcomes[PROVIDER_ERROR],
        "proposal_boundary_rejected": outcomes[BOUNDARY_REJECTED],
        "accepted_proposals": outcomes[ACCEPTED],
        "boundary_rejection_reasons": sorted(
            {
                f"{attempt.error_type}: {attempt.error_message}"
                for attempt in attempts
                if attempt.outcome == BOUNDARY_REJECTED
            }
        ),
    }


def metric_b_proposal_presence(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """B. Presence. An empty proposal is an observation, not automatically a failure."""
    per_specimen: dict[str, Any] = {}
    for specimen in specimens:
        runs = _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id)
        non_empty = sum(1 for run in runs if run.proposal and _assertions(run.proposal))
        per_specimen[specimen.specimen_id] = {
            "accepted_runs": len(runs),
            "runs_with_at_least_one_assertion": non_empty,
            "empty_proposal_runs": len(runs) - non_empty,
        }
    return per_specimen


def metric_c_force(specimens: Sequence[Specimen], attempts: Sequence[Attempt]) -> dict[str, Any]:
    """C. Force classification, as a confusion matrix. No aggregate accuracy without it."""
    labels = (*FORCE_VALUES, "OMITTED")
    matrix: dict[str, dict[str, int]] = {
        expected: dict.fromkeys(labels, 0) for expected in FORCE_VALUES
    }
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        expected = specimen.expected_force
        if expected is None:
            continue
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            values = _values_for_slot(run.proposal, "normative_force")
            observed = values[0] if values else "OMITTED"
            if observed not in labels:
                observed = "OMITTED"
            matrix[expected][observed] += 1
            if observed != expected:
                instances.append(
                    {
                        "specimen_id": specimen.specimen_id,
                        "run_index": run.run_index,
                        "expected_force": expected,
                        "proposed_force": observed,
                    }
                )
    return {"confusion_matrix": matrix, "mismatch_instances": instances}


def metric_d_invention(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """D. Unsupported semantic invention on slots the source does not supply."""
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            for slot in SLOT_VOCABULARY:
                gold = specimen.gold_slot(slot)
                if gold["status"] not in {"NOT_ESTABLISHED", "NOT_APPLICABLE"}:
                    continue
                for value in _values_for_slot(run.proposal, slot):
                    tag = f"{slot}:{gold['status']}"
                    counts[tag] += 1
                    kind = "invented_value"
                    if slot == "bearer":
                        counterparty = specimen.gold_slot("counterparty")
                        if counterparty["status"] == "ESTABLISHED" and compatible(
                            value, counterparty["value"]
                        ):
                            kind = "counterparty_proposed_as_bearer"
                        elif "passive_actor" in specimen.semantic_risk_tags or (
                            "invented_actor" in specimen.semantic_risk_tags
                        ):
                            kind = "invented_bearer_on_passive_voice"
                    elif slot == "condition":
                        kind = "invented_condition"
                    elif slot == "definiens":
                        kind = "inferred_definition_absent_from_source"
                    counts[kind] += 1
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "slot": slot,
                            "gold_status": gold["status"],
                            "proposed_value": value,
                            "kind": kind,
                        }
                    )
    return {"counts": dict(counts), "instances": instances}


def metric_e_established_recall(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """E. Recall over ESTABLISHED slots. Omission and incompatibility are not the same."""
    per_slot: dict[str, dict[str, int]] = {
        slot: {"expected_established": 0, "proposed_compatible": 0, "omitted": 0, "incompatible": 0}
        for slot in SLOT_VOCABULARY
    }
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            for slot in SLOT_VOCABULARY:
                gold = specimen.gold_slot(slot)
                if gold["status"] != "ESTABLISHED":
                    continue
                bucket = per_slot[slot]
                bucket["expected_established"] += 1
                values = _values_for_slot(run.proposal, slot)
                if not values:
                    bucket["omitted"] += 1
                    outcome = "omitted"
                elif any(compatible(value, gold["value"]) for value in values):
                    bucket["proposed_compatible"] += 1
                    outcome = "compatible"
                else:
                    bucket["incompatible"] += 1
                    outcome = "incompatible"
                if outcome != "compatible":
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "slot": slot,
                            "expected_value": gold["value"],
                            "proposed_values": values,
                            "outcome": outcome,
                        }
                    )
    return {"per_slot": per_slot, "instances": instances}


def metric_f_ambiguity(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """F. Overcommitment on AMBIGUOUS slots. Choosing one reading resolves nothing."""
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            for slot in SLOT_VOCABULARY:
                gold = specimen.gold_slot(slot)
                if gold["status"] != "AMBIGUOUS":
                    continue
                alternatives = gold["alternatives"]
                values = _values_for_slot(run.proposal, slot)
                matched = {
                    alternative
                    for alternative in alternatives
                    for value in values
                    if compatible(value, alternative)
                }
                unmatched = [
                    value
                    for value in values
                    if not any(compatible(value, alternative) for alternative in alternatives)
                ]
                if not values:
                    outcome = "omitted"
                elif unmatched:
                    outcome = "unsupported_alternative_proposed"
                elif len(matched) >= 2:
                    outcome = "alternatives_preserved"
                else:
                    outcome = "single_alternative_proposed"
                counts[outcome] += 1
                instances.append(
                    {
                        "specimen_id": specimen.specimen_id,
                        "run_index": run.run_index,
                        "slot": slot,
                        "gold_alternatives": alternatives,
                        "proposed_values": values,
                        "outcome": outcome,
                    }
                )
    return {"counts": dict(counts), "instances": instances}


def metric_g_role_separation(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """G. Bearer against counterparty: the observed semantic-role failure class."""
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        bearer_gold = specimen.gold_slot("bearer")
        counterparty_gold = specimen.gold_slot("counterparty")
        if "ESTABLISHED" not in {bearer_gold["status"], counterparty_gold["status"]}:
            continue
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            bearer_values = _values_for_slot(run.proposal, "bearer")
            counterparty_values = _values_for_slot(run.proposal, "counterparty")
            observed: list[str] = []
            if bearer_gold["status"] == "ESTABLISHED":
                if any(compatible(v, bearer_gold["value"]) for v in bearer_values):
                    observed.append("correct_bearer")
                elif not bearer_values:
                    observed.append("bearer_omitted")
            if counterparty_gold["status"] == "ESTABLISHED":
                if any(compatible(v, counterparty_gold["value"]) for v in counterparty_values):
                    observed.append("correct_counterparty")
                elif not counterparty_values:
                    observed.append("counterparty_omitted")
            swapped = (
                counterparty_gold["status"] == "ESTABLISHED"
                and any(compatible(v, counterparty_gold["value"]) for v in bearer_values)
            ) or (
                bearer_gold["status"] == "ESTABLISHED"
                and any(compatible(v, bearer_gold["value"]) for v in counterparty_values)
            )
            if swapped:
                observed.append("swapped")
            if (
                bearer_gold["status"] == "ESTABLISHED"
                and any(compatible(v, bearer_gold["value"]) for v in bearer_values)
                and any(compatible(v, bearer_gold["value"]) for v in counterparty_values)
            ):
                observed.append("duplicated_into_both")
            known = [bearer_gold["value"], counterparty_gold["value"]]
            for value in bearer_values + counterparty_values:
                if not any(compatible(value, entry) for entry in known if entry):
                    observed.append("unsupported_role_inserted")
                    break
            for outcome in observed:
                counts[outcome] += 1
            instances.append(
                {
                    "specimen_id": specimen.specimen_id,
                    "run_index": run.run_index,
                    "expected_bearer": bearer_gold["value"],
                    "expected_counterparty": counterparty_gold["value"],
                    "proposed_bearer": bearer_values,
                    "proposed_counterparty": counterparty_values,
                    "outcomes": observed,
                }
            )
    return {"counts": dict(counts), "instances": instances}


_QUALIFIER_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("condition", "condition"),
    ("exception", "exception"),
    ("temporal_qualifier", "temporal_qualifier"),
    ("quantum", "quantum"),
)


def _marker_texts(gold_slot: dict[str, Any], kinds: set[str]) -> list[str]:
    return [
        item["text"] for item in gold_slot["material_qualifiers"] if item["qualifier_kind"] in kinds
    ]


def metric_h_material_preservation(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """H. Material content, per category. Loss and misplacement are separate failures."""
    categories = (
        "condition",
        "exception",
        "temporal_qualifier",
        "quantum",
        "currency",
        "deadline",
        "discretion_advisory",
    )
    counts: dict[str, Counter[str]] = {category: Counter() for category in categories}
    instances: list[dict[str, Any]] = []

    def record(category: str, outcome: str, payload: dict[str, Any]) -> None:
        counts[category][outcome] += 1
        if outcome != "preserved":
            instances.append({"category": category, "outcome": outcome, **payload})

    for specimen in specimens:
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            proposal = run.proposal
            base = {"specimen_id": specimen.specimen_id, "run_index": run.run_index}

            for category, slot in _QUALIFIER_CATEGORIES:
                gold = specimen.gold_slot(slot)
                values = _values_for_slot(proposal, slot)
                if gold["status"] != "ESTABLISHED":
                    if values:
                        record(category, "invented", {**base, "slot": slot, "proposed": values})
                    continue
                expected = gold["value"]
                if any(compatible(value, expected) for value in values):
                    markers = _marker_texts(gold, {"COMPARATOR", "CURRENCY"})
                    haystack = " ".join(values + _qualifier_texts(proposal, slot))
                    missing = [
                        marker
                        for marker in markers
                        if grounding_key(marker) not in grounding_key(haystack)
                    ]
                    if missing:
                        record(
                            category,
                            "broadened",
                            {**base, "slot": slot, "missing_markers": missing},
                        )
                    else:
                        record(category, "preserved", {**base, "slot": slot})
                    continue
                elsewhere = [
                    other
                    for other in SLOT_VOCABULARY
                    if other != slot
                    and any(compatible(v, expected) for v in _values_for_slot(proposal, other))
                ]
                if elsewhere:
                    record(
                        category,
                        "moved_to_wrong_slot",
                        {**base, "slot": slot, "expected": expected, "found_under": elsewhere},
                    )
                elif values:
                    record(
                        category,
                        "moved_to_wrong_slot" if False else "omitted",
                        {**base, "slot": slot, "expected": expected, "proposed": values},
                    )
                else:
                    record(category, "omitted", {**base, "slot": slot, "expected": expected})

            quantum_gold = specimen.gold_slot("quantum")
            currency_markers = _marker_texts(quantum_gold, {"CURRENCY"})
            if currency_markers:
                haystack = " ".join(
                    _values_for_slot(proposal, "quantum") + _qualifier_texts(proposal, "quantum")
                )
                missing = [
                    marker
                    for marker in currency_markers
                    if grounding_key(marker) not in grounding_key(haystack)
                ]
                record(
                    "currency",
                    "omitted" if missing else "preserved",
                    {**base, "missing_markers": missing},
                )

            temporal_gold = specimen.gold_slot("temporal_qualifier")
            normalization = temporal_gold["normalization"]
            if normalization is not None and normalization["kind"] == "TIMESTAMP":
                raw = normalization["raw_source_text"]
                haystack = " ".join(_values_for_slot(proposal, "temporal_qualifier"))
                record(
                    "deadline",
                    "preserved" if grounding_key(raw) in grounding_key(haystack) else "omitted",
                    {**base, "expected_deadline": raw},
                )

            discretion = [
                item["text"]
                for slot in SLOT_VOCABULARY
                for item in specimen.gold_slot(slot)["material_qualifiers"]
                if item["qualifier_kind"] in {"DISCRETION", "HEDGE"}
            ]
            if discretion:
                everything = " ".join(
                    [
                        value
                        for slot in SLOT_VOCABULARY
                        for value in _values_for_slot(proposal, slot)
                    ]
                    + [
                        text
                        for slot in SLOT_VOCABULARY
                        for text in _qualifier_texts(proposal, slot)
                    ]
                )
                missing = [
                    marker
                    for marker in discretion
                    if grounding_key(marker) not in grounding_key(everything)
                ]
                record(
                    "discretion_advisory",
                    "omitted" if missing else "preserved",
                    {**base, "missing_markers": missing},
                )

    return {
        "counts": {category: dict(counter) for category, counter in counts.items()},
        "instances": instances,
    }


def metric_i_quote_grounding(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """I. Literal grounding of every non-null quote. Measured; never repaired."""
    grounded = 0
    ungrounded: list[dict[str, Any]] = []
    by_id = {specimen.specimen_id: specimen for specimen in specimens}
    for run in _accepted(attempts):
        if run.proposal is None:  # pragma: no cover - _accepted already excludes these
            continue
        span = by_id[run.specimen_id].candidate_span
        for item in _assertions(run.proposal):
            quote = item["proposed_source_quote"]
            if not isinstance(quote, str):
                continue
            if is_quote_grounded(quote, candidate_span=span):
                grounded += 1
            else:
                ungrounded.append(
                    {
                        "specimen_id": run.specimen_id,
                        "run_index": run.run_index,
                        "slot": item["slot"],
                        "quote": quote,
                    }
                )
    return {
        "grounded": grounded,
        "ungrounded": len(ungrounded),
        "ungrounded_instances": ungrounded,
    }


def metric_j_quote_support(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """J. Whether a quote supports the role it was offered for.

    Literal grounding is not enough: a recipient can be quoted as a bearer, and advisory
    wording can be quoted while proposing an obligation.
    """
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []
    by_id = {specimen.specimen_id: specimen for specimen in specimens}
    for run in _accepted(attempts):
        if run.proposal is None:  # pragma: no cover - _accepted already excludes these
            continue
        specimen = by_id[run.specimen_id]
        for item in _assertions(run.proposal):
            quote = item["proposed_source_quote"]
            slot = item["slot"]
            if not isinstance(quote, str) or not quote.strip():
                counts["no_quote"] += 1
                continue
            if slot == "normative_force":
                counts["force_span_quote"] += 1
                continue
            gold = specimen.gold_slot(slot)
            if gold["status"] == "ESTABLISHED" and compatible(quote, gold["value"]):
                counts["supports_proposed_role"] += 1
                continue
            other_roles = [
                other
                for other in SLOT_VOCABULARY
                if other != slot
                and specimen.gold_slot(other)["status"] == "ESTABLISHED"
                and compatible(quote, specimen.gold_slot(other)["value"])
            ]
            if other_roles:
                counts["supports_a_different_role"] += 1
                instances.append(
                    {
                        "specimen_id": run.specimen_id,
                        "run_index": run.run_index,
                        "slot": slot,
                        "quote": quote,
                        "actually_supports": other_roles,
                    }
                )
            elif gold["status"] == "ESTABLISHED":
                counts["does_not_support_proposed_role"] += 1
                instances.append(
                    {
                        "specimen_id": run.specimen_id,
                        "run_index": run.run_index,
                        "slot": slot,
                        "quote": quote,
                        "expected_value": gold["value"],
                    }
                )
            else:
                counts["no_gold_value_for_slot"] += 1
    return {"counts": dict(counts), "instances": instances}


def metric_k_reference_recall(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """K. References surfaced rather than resolved from general knowledge."""
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []
    for specimen in specimens:
        expected = specimen.gold["expected_unresolved_references"]
        if not expected:
            continue
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            proposed = run.proposal.get("proposed_unresolved_references", [])
            counts["expected"] += len(expected)
            counts["proposed"] += len(proposed)
            for entry in expected:
                match = next(
                    (
                        item
                        for item in proposed
                        if compatible(item["reference_text"], entry["reference_text"])
                    ),
                    None,
                )
                if match is None:
                    counts["omitted"] += 1
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "outcome": "omitted",
                            "expected": entry,
                        }
                    )
                elif match["reference_kind"] == entry["reference_kind"]:
                    counts["correct_kind"] += 1
                else:
                    counts["wrong_kind"] += 1
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "outcome": "wrong_kind",
                            "expected": entry,
                            "proposed": match,
                        }
                    )
            for item in proposed:
                if not any(
                    compatible(item["reference_text"], entry["reference_text"])
                    for entry in expected
                ):
                    counts["invented"] += 1
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "outcome": "invented",
                            "proposed": item,
                        }
                    )
            # A reference is resolved rather than surfaced when the slot that depends on
            # it acquires a value the admitted source never supplied.
            for slot in ("definiens",):
                gold = specimen.gold_slot(slot)
                if gold["status"] == "NOT_ESTABLISHED" and _values_for_slot(run.proposal, slot):
                    counts["resolved_instead_of_surfaced"] += 1
                    instances.append(
                        {
                            "specimen_id": specimen.specimen_id,
                            "run_index": run.run_index,
                            "outcome": "resolved_instead_of_surfaced",
                            "slot": slot,
                            "proposed": _values_for_slot(run.proposal, slot),
                        }
                    )
    return {"counts": dict(counts), "instances": instances}


_STRENGTHENING_FORCE_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("ADVISORY", "OBLIGATION", "advisory_to_obligation"),
    ("ADVISORY", "PROHIBITION", "advisory_to_prohibition"),
    ("PERMISSION", "OBLIGATION", "permission_to_obligation"),
    ("PERMISSION", "PROHIBITION", "permission_to_prohibition"),
    ("DELEGATION", "OBLIGATION", "delegation_collapsed_into_obligation"),
    ("CONSTITUTIVE_DEFINITION", "OBLIGATION", "definition_treated_as_mandate"),
    ("CONSTITUTIVE_DEFINITION", "PROHIBITION", "definition_treated_as_mandate"),
)


def metric_l_strengthening(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """L. Prohibited unwarranted strengthening, enumerated instance by instance."""
    counts: Counter[str] = Counter()
    instances: list[dict[str, Any]] = []

    def record(kind: str, payload: dict[str, Any]) -> None:
        counts[kind] += 1
        instances.append({"kind": kind, **payload})

    for specimen in specimens:
        expected_force = specimen.expected_force
        for run in _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id):
            if run.proposal is None:  # pragma: no cover - _accepted already excludes these
                continue
            proposal = run.proposal
            base = {"specimen_id": specimen.specimen_id, "run_index": run.run_index}
            forces = _values_for_slot(proposal, "normative_force")
            proposed_force = forces[0] if forces else None
            for source, target, kind in _STRENGTHENING_FORCE_PAIRS:
                if expected_force == source and proposed_force == target:
                    record(kind, {**base, "expected": source, "proposed": target})
            for slot, kind in (
                ("condition", "conditional_to_unconditional_by_dropped_condition"),
                ("exception", "exception_bearing_to_exceptionless_by_dropped_exception"),
                ("quantum", "threshold_bearing_to_unbounded_by_dropped_quantum"),
            ):
                gold = specimen.gold_slot(slot)
                if gold["status"] == "ESTABLISHED" and not _values_for_slot(proposal, slot):
                    record(kind, {**base, "slot": slot, "expected_value": gold["value"]})
            counterparty = specimen.gold_slot("counterparty")
            if counterparty["status"] == "ESTABLISHED" and any(
                compatible(value, counterparty["value"])
                for value in _values_for_slot(proposal, "bearer")
            ):
                record("recipient_promoted_to_bearer", {**base, "value": counterparty["value"]})
            definiens = specimen.gold_slot("definiens")
            if definiens["status"] == "NOT_ESTABLISHED" and _values_for_slot(proposal, "definiens"):
                record(
                    "undefined_supplied_from_general_knowledge",
                    {**base, "proposed": _values_for_slot(proposal, "definiens")},
                )
    return {"counts": dict(counts), "instances": instances}


def metric_m_repeat_stability(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """M. Run-to-run stability. OIC binding fields must be identical every time."""
    per_specimen: dict[str, Any] = {}
    for specimen in specimens:
        runs = _accepted(a for a in attempts if a.specimen_id == specimen.specimen_id)
        if not runs:
            per_specimen[specimen.specimen_id] = {"accepted_runs": 0}
            continue
        hashes = {semantic_hash(run.proposal) for run in runs if run.proposal}
        forces = {
            tuple(_values_for_slot(run.proposal, "normative_force")) for run in runs if run.proposal
        }
        slot_sets = {
            tuple(sorted({item["slot"] for item in _assertions(run.proposal)}))
            for run in runs
            if run.proposal
        }
        per_slot_stability: dict[str, bool] = {}
        for slot in SLOT_VOCABULARY:
            observed = {
                tuple(sorted(_values_for_slot(run.proposal, slot))) for run in runs if run.proposal
            }
            per_slot_stability[slot] = len(observed) == 1
        bindings = {
            (
                run.proposal["admission_receipt_id"],
                run.proposal["candidate_unit_id"],
                run.proposal["candidate_projection_digest"],
            )
            for run in runs
            if run.proposal
        }
        per_specimen[specimen.specimen_id] = {
            "accepted_runs": len(runs),
            "distinct_semantic_hashes": len(hashes),
            "semantic_hash_stable": len(hashes) == 1,
            "force_stable": len(forces) == 1,
            "slot_set_stable": len(slot_sets) == 1,
            "per_slot_value_stable": per_slot_stability,
            "oic_binding_deterministic": len(bindings) == 1,
        }
    return per_specimen


def critical_diagnostics(
    specimens: Sequence[Specimen], attempts: Sequence[Attempt]
) -> dict[str, Any]:
    """Every run of the eleven critical specimens, individually. No aggregation."""
    by_id = {specimen.specimen_id: specimen for specimen in specimens}
    sections: dict[str, Any] = {}
    for specimen_id, label in CRITICAL_SPECIMENS:
        specimen = by_id[specimen_id]
        runs: list[dict[str, Any]] = []
        for attempt in (a for a in attempts if a.specimen_id == specimen_id):
            entry: dict[str, Any] = {
                "run_index": attempt.run_index,
                "outcome": attempt.outcome,
                "error": attempt.error_message,
            }
            if attempt.proposal is not None:
                entry["proposed_force"] = _values_for_slot(attempt.proposal, "normative_force")
                entry["proposed_slots"] = {
                    slot: _values_for_slot(attempt.proposal, slot)
                    for slot in SLOT_VOCABULARY
                    if _for_slot(attempt.proposal, slot)
                }
                entry["proposed_references"] = attempt.proposal.get(
                    "proposed_unresolved_references", []
                )
                entry["semantic_hash"] = semantic_hash(attempt.proposal)
            runs.append(entry)
        sections[specimen_id] = {
            "diagnostic": label,
            "title": specimen.title,
            "candidate_span": specimen.candidate_span,
            "expected_force": specimen.expected_force,
            "expected_slots": {
                slot: specimen.gold_slot(slot)["status"] for slot in SLOT_VOCABULARY
            },
            "runs": runs,
        }
    return sections


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

LIMITATIONS: tuple[str, ...] = (
    "One model and one provider over 29 synthetic frozen specimens at three runs each. "
    "Not a population error rate and not cross-model generalization.",
    "The gold is the preregistered Institutional IR 001 design corpus, authored by the "
    "same process that designed the schemas. Agreement with it is not semantic truth.",
    "Comparison is preregistered containment after casefold and whitespace collapse. It "
    "will count some genuinely different phrasings as compatible and some acceptable "
    "paraphrases as incompatible.",
    "The candidate_span-only arm was preregistered. Whether the provisional unit_type "
    "hint helps or propagates error is unmeasured here.",
    "A proposal is act 3 only. Nothing measured here establishes canonical meaning, and "
    "no canonicalization decision was made or implemented.",
)

CLAIM_CEILING = (
    "Characterization 001 measures one model and provider proposing provisional semantic "
    "structure over a small frozen synthetic admitted-candidate corpus. It does not "
    "establish canonical institutional meaning, semantic correctness generally, "
    "interpretation authority, legal interpretation, successful Institutional IR "
    "construction, model suitability for autonomous canonicalization, production "
    "readiness, cross-model generalization, or independent validation."
)


def build_receipt(
    *,
    specimens: Sequence[Specimen],
    attempts: Sequence[Attempt],
    digests: dict[str, str],
    corpus: dict[str, Any],
    provider_name: str | None,
    model_name: str | None,
    live: bool,
) -> dict[str, Any]:
    planned = corpus["planned_live_requests"]
    return {
        "work_order": WORK_ORDER,
        "act": "3_INTERPRETATION_PROPOSAL",
        "starting_sha": STARTING_SHA,
        "final_instrument_sha256": digests["instrument_sha256"],
        "corpus_sha256": digests["corpus_sha256"],
        "source_ir_design_corpus_sha256": digests["source_ir_design_corpus_sha256"],
        "proposal_schema_sha256": digests["proposal_schema_sha256"],
        "interpretation_ruleset_sha256": digests["interpretation_ruleset_sha256"],
        "interpretation_ruleset_canonical_digest": digests[
            "interpretation_ruleset_canonical_digest"
        ],
        "provider": provider_name,
        "model": model_name,
        "live_run_executed": live,
        "runs_per_specimen": corpus["runs_per_specimen"],
        "specimen_count": corpus["specimen_count"],
        "planned_live_requests": planned,
        "include_provisional_unit_type_in_prompt": corpus[
            "include_provisional_unit_type_in_prompt"
        ],
        "retry_policy": "none; exactly one provider call per planned attempt",
        "attempts": [attempt.to_json() for attempt in attempts],
        "metrics": {
            "A_provider_structural_boundary": metric_a_provider_boundary(attempts, planned),
            "B_proposal_presence": metric_b_proposal_presence(specimens, attempts),
            "C_force_classification": metric_c_force(specimens, attempts),
            "D_unsupported_semantic_invention": metric_d_invention(specimens, attempts),
            "E_established_slot_recall": metric_e_established_recall(specimens, attempts),
            "F_ambiguity_overcommitment": metric_f_ambiguity(specimens, attempts),
            "G_bearer_counterparty_separation": metric_g_role_separation(specimens, attempts),
            "H_material_qualifier_preservation": metric_h_material_preservation(
                specimens, attempts
            ),
            "I_source_quote_grounding": metric_i_quote_grounding(specimens, attempts),
            "J_quote_to_value_support": metric_j_quote_support(specimens, attempts),
            "K_unresolved_reference_recall": metric_k_reference_recall(specimens, attempts),
            "L_strengthening_rate": metric_l_strengthening(specimens, attempts),
            "M_repeat_stability": metric_m_repeat_stability(specimens, attempts),
        },
        "critical_diagnostics": critical_diagnostics(specimens, attempts),
        "canonicalization_performed": False,
        "institutional_ir_constructed": False,
        "limitations": list(LIMITATIONS),
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Plan:
    specimens: tuple[Specimen, ...] = field(default_factory=tuple)
    corpus: dict[str, Any] = field(default_factory=dict)
    digests: dict[str, str] = field(default_factory=dict)


def preflight() -> _Plan:
    digests = verify_governing_artifacts()
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    specimens = load_specimens(
        corpus, include_unit_type=corpus["include_provisional_unit_type_in_prompt"]
    )
    if len(specimens) != corpus["specimen_count"]:
        raise SystemExit("FAIL specimen count does not match the corpus")
    if corpus["specimen_count"] * corpus["runs_per_specimen"] != corpus["planned_live_requests"]:
        raise SystemExit("FAIL planned request count is inconsistent")
    return _Plan(specimens=specimens, corpus=corpus, digests=digests)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="execute the preregistered live provider run. Owner-only.",
    )
    args = parser.parse_args(argv)

    plan = preflight()
    print(f"PASS frozen artifacts verified; {len(plan.specimens)} specimens")
    print(f"planned live requests: {plan.corpus['planned_live_requests']}")

    if not args.live:
        print("offline preflight only; no provider was constructed and no request was made")
        return 0

    # Imported here so an offline run never touches provider configuration.
    from oic.nvidia_nim import NvidiaNimProvider

    provider = NvidiaNimProvider()
    attempts = execute_attempts(
        plan.specimens, provider, runs_per_specimen=plan.corpus["runs_per_specimen"]
    )
    accepted = _accepted(attempts)
    receipt = build_receipt(
        specimens=plan.specimens,
        attempts=attempts,
        digests=plan.digests,
        corpus=plan.corpus,
        provider_name=accepted[0].provider if accepted else None,
        model_name=accepted[0].model if accepted else None,
        live=True,
    )
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"receipt written: {RECEIPT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
