#!/usr/bin/env python3
"""Characterize OIC candidate-extraction behaviour on a frozen synthetic corpus.

Current work order: OIC-CANDIDATE-SEMANTICS-003 (pre-admission characterization).

This harness measures. It does not correct. Every metric below is an engineering
observation about what came back through the existing OIC candidate boundary on one
frozen corpus, under one implementation commit, one provider, one model, and one set of
run conditions. Nothing here admits, authorizes, ranks, repairs, or normalizes a model
answer, and no metric is evidence of semantic, institutional, or legal correctness.

Two deliberate constraints shape the design:

* The characterization unit is the candidate that survives ``propose_candidate_units``.
  The harness never grades raw provider text and never reaches around the boundary. A
  response the boundary refuses is recorded as a refusal, with its error preserved.
* Divergent answers stay divergent. No mapping collapses ``mandate`` into ``obligation``,
  no repair strips a forbidden field to rescue a response, and no canonicalization
  manufactures agreement between two different decompositions.

Live use needs a NVIDIA credential, read from the environment by the existing adapter and
never read, echoed, or persisted here. Unit tests drive the harness with fake providers
and perform no network I/O.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oic.candidate_extraction import CandidateBoundaryError, propose_candidate_units
from oic.model_provider import JsonObject, ModelProvider, ModelProviderError
from oic.nvidia_nim import DEFAULT_NIM_MODEL, NvidiaNimConfig, NvidiaNimProvider

WORK_ORDER = "OIC-CANDIDATE-SEMANTICS-003"

CLAIM_CEILING = (
    "Candidate extraction behavior has been characterized on the frozen "
    "OIC-CANDIDATE-SEMANTICS-003 synthetic corpus under the identified implementation "
    "commit, model, provider, and run conditions. This establishes no semantic "
    "correctness, institutional admission, authority, enforceability, runtime "
    "authorization, readiness, compliance, superiority, or independent validation."
)

# Engineering result states. None of these asserts institutional correctness, and the
# vocabulary deliberately excludes ADMITTED, AUTHORIZED, COMPLIANT, LEGALLY_VALID,
# CORRECT_POLICY, ALLOW and DENY.
# The suppression below is for the credential heuristic, which reads a constant ending
# in PASS as a password. This is a public result-state literal fixed by the work order.
STRUCTURAL_PASS = "STRUCTURAL_PASS"  # noqa: S105
BOUNDARY_REJECTED = "BOUNDARY_REJECTED"
PROVIDER_ERROR = "PROVIDER_ERROR"
EXPECTED_PRESENCE_OBSERVED = "EXPECTED_PRESENCE_OBSERVED"
PRESENCE_MISS = "PRESENCE_MISS"
EXPECTED_ABSENCE_OBSERVED = "EXPECTED_ABSENCE_OBSERVED"
FALSE_POSITIVE_OBSERVED = "FALSE_POSITIVE_OBSERVED"
TYPE_WITHIN_PREREGISTERED_SET = "TYPE_WITHIN_PREREGISTERED_SET"
TYPE_OUTSIDE_PREREGISTERED_SET = "TYPE_OUTSIDE_PREREGISTERED_SET"
REPEAT_STABLE = "REPEAT_STABLE"
REPEAT_VARIANT = "REPEAT_VARIANT"
NOT_OBSERVED = "NOT_OBSERVED"

# Where threshold material was seen. Observational only: nothing in OIC prescribes where
# a threshold belongs, and this harness must not start.
PLACEMENT_OBJECT = "THRESHOLD_IN_OBJECT"
PLACEMENT_CONDITIONS = "THRESHOLD_IN_CONDITIONS"
PLACEMENT_BOTH = "THRESHOLD_IN_OBJECT_AND_CONDITIONS"
PLACEMENT_OTHER_FIELD = "THRESHOLD_IN_OTHER_SEMANTIC_FIELD"
PLACEMENT_NEITHER = "THRESHOLD_ABSENT_FROM_CANDIDATE"

# Source-grounding observation states (OIC-CANDIDATE-SEMANTICS-002). Observational: an
# "unsupported" actor here is a corpus-relative observation, not an adjudication.
ACTOR_ABSENT_AS_PREREGISTERED = "ACTOR_ABSENT_AS_PREREGISTERED"
ACTOR_ASSERTED_WHERE_SOURCE_NAMES_NONE = "ACTOR_ASSERTED_WHERE_SOURCE_NAMES_NONE"
ELEMENT_PRESERVED = "ELEMENT_PRESERVED"
ELEMENT_OMITTED = "ELEMENT_OMITTED"
TARGET_PRESERVED = "TARGET_PRESERVED"
TARGET_OMITTED = "TARGET_OMITTED"
TRIGGER_RECORDED_AS_ACTION = "TRIGGER_RECORDED_AS_ACTION"
TRIGGER_NOT_RECORDED_AS_ACTION = "TRIGGER_NOT_RECORDED_AS_ACTION"

# Framing-separation observation states (OIC-CANDIDATE-SEMANTICS-004). Observational:
# "carries framing" is a corpus-relative record of what the span held, not a verdict.
FRAMING_SEPARATED = "SEPARABLE_FRAMING_EXCLUDED"
FRAMING_CARRIED = "SEPARABLE_FRAMING_CARRIED"
SPAN_WITHIN_BOUNDS = "SPAN_WITHIN_REGISTERED_BOUNDS"
SPAN_OUTSIDE_BOUNDS = "SPAN_OUTSIDE_REGISTERED_BOUNDS"
MATERIAL_COMPLETE = "MATERIAL_CONTENT_PRESERVED"
MATERIAL_UNDERREACH = "MATERIAL_CONTENT_LOST"

CLAIM_CEILING_004 = (
    "This experiment characterizes candidate-span framing separation under one frozen "
    "synthetic corpus, implementation commit, provider/model when run live, and bounded "
    "run conditions. It does not establish semantic correctness, institutional admission, "
    "authority, enforceability, legal interpretation, production readiness, runtime "
    "readiness, cross-model generalization, or independent validation."
)

CORPUS_INTACT = "INTACT"
CORPUS_DRIFT_ACKNOWLEDGED = "DRIFT_ACKNOWLEDGED"

#: Current model-proposed fields. Historical 002 metrics below retain their names solely
#: so old receipts remain interpretable; a 003 receipt never reports them as requirements.
SEMANTIC_FIELDS = ("candidate_span", "unit_type")
TEXTUAL_ROLE_FIELDS = ("candidate_span",)
#: Deterministic fields OIC controls. Excluded from every semantic projection, because a
#: projection carrying unit_id or source_anchors would measure OIC's determinism rather
#: than the model's stability.
OIC_CONTROLLED_FIELDS = (
    "unit_id",
    "interpretation_state",
    "epistemic_state",
    "source_anchors",
)

#: OIC-CANDIDATE-SEMANTICS-004 is the current corpus. Every earlier corpus stays in the
#: tree, unchanged, as the historical evidence its own receipt refers to.
DEFAULT_CORPUS = Path("benchmarks/characterization/candidate-semantics-004/CORPUS-v0.4.json")
DEFAULT_FREEZE = Path("benchmarks/characterization/candidate-semantics-004/CORPUS-FREEZE-v0.4.json")
DEFAULT_OUTPUT = Path(".local/candidate-semantics-receipts/OIC-CANDIDATE-SEMANTICS-004.json")
DEFAULT_RUNS_PER_SPECIMEN = 3


class CharacterizationError(RuntimeError):
    """Raised when the harness cannot run as specified."""


class CorpusIntegrityError(CharacterizationError):
    """Raised when the corpus on disk is not the corpus that was frozen."""


@dataclass(frozen=True, slots=True)
class Family:
    """One family membership: which family, what kind, and this specimen's role in it."""

    family_id: str
    family_kind: str
    role: str


@dataclass(frozen=True, slots=True)
class Specimen:
    """One frozen corpus specimen. Immutable: a run can never edit its own expectations."""

    specimen_id: str
    category: str
    source_text: str
    normative_expected: bool
    expected_candidate_count_min: int
    expected_candidate_count_max: int | None
    acceptable_unit_types: tuple[str, ...] | None
    families: tuple[Family, ...]
    threshold_markers: tuple[str, ...] | None
    characterization_notes: str
    claim_ceiling: str
    # OIC-CANDIDATE-SEMANTICS-002 source-grounding pre-registration. Optional so the
    # frozen OIC-CANDIDATE-SEMANTICS-001 corpus still loads unchanged as historical
    # evidence. Each *_spans list is disjunctive: one required element, several
    # acceptable renderings.
    actor_explicitly_named: bool | None = None
    target_explicitly_named: bool | None = None
    expected_target_spans: tuple[str, ...] | None = None
    required_condition_spans: tuple[str, ...] | None = None
    material_qualifier_spans: tuple[str, ...] | None = None
    non_operative_predicate_spans: tuple[str, ...] | None = None
    # 003 pre-registration. Each inner group is disjunctive; every group is material.
    material_span_groups: tuple[tuple[str, ...], ...] | None = None
    # Optional maximum proposition regions for bounded overreach observation.
    candidate_span_bounds: tuple[str, ...] | None = None
    diagnostic_tags: tuple[str, ...] = ()
    # OIC-CANDIDATE-SEMANTICS-004 framing pre-registration. Optional so every earlier
    # frozen corpus still loads unchanged as historical evidence.
    separable_framing_spans: tuple[str, ...] | None = None
    framing_expected_excluded: bool | None = None
    framing_structure: str | None = None

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Corpus:
    """A frozen corpus plus the digest of the exact bytes it was loaded from."""

    corpus_id: str
    corpus_version: str
    claim_ceiling: str
    specimens: tuple[Specimen, ...]
    sha256: str
    relpath: str


@dataclass(frozen=True, slots=True)
class Attempt:
    """One request for one specimen. Boundary refusals are recorded, never repaired."""

    specimen_id: str
    run_index: int
    boundary_result: str
    provider: str | None
    model: str | None
    request_id: str | None
    raw_content_sha256: str | None
    candidate_count: int | None
    candidates: tuple[JsonObject, ...]
    semantic_projections: tuple[JsonObject, ...]
    semantic_projection_sha256: str | None
    unit_types: tuple[str, ...]
    error_type: str | None
    error_message: str | None
    observed_at: str


# --------------------------------------------------------------------------
# Corpus loading and integrity
# --------------------------------------------------------------------------


def canonical_json_bytes(value: object) -> bytes:
    """Canonical UTF-8 JSON, array order preserved. Matches the repository convention."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CharacterizationError(message)


def _optional_str_tuple(value: object, label: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    _require(isinstance(value, list), f"{label} must be an array or null")
    entries = list(value) if isinstance(value, list) else []
    _require(all(isinstance(entry, str) for entry in entries), f"{label} must hold strings")
    return tuple(str(entry) for entry in entries)


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str), f"{label} must be a string or null")
    return str(value)


def _optional_bool(value: object, label: str) -> bool | None:
    if value is None:
        return None
    _require(isinstance(value, bool), f"{label} must be a boolean or null")
    return bool(value)


def _optional_span_groups(value: object, label: str) -> tuple[tuple[str, ...], ...] | None:
    if value is None:
        return None
    _require(isinstance(value, list), f"{label} must be an array or null")
    groups: list[tuple[str, ...]] = []
    for index, group in enumerate(value if isinstance(value, list) else []):
        parsed = _optional_str_tuple(group, f"{label}[{index}]")
        _require(bool(parsed), f"{label}[{index}] must not be empty")
        groups.append(parsed or ())
    _require(bool(groups), f"{label} must not be empty")
    return tuple(groups)


def _parse_family(value: object, label: str) -> Family:
    _require(isinstance(value, dict), f"{label} entry must be an object")
    record = value if isinstance(value, dict) else {}
    for key in ("family_id", "family_kind", "role"):
        _require(isinstance(record.get(key), str), f"{label} entry needs a string {key}")
    return Family(
        family_id=str(record["family_id"]),
        family_kind=str(record["family_kind"]),
        role=str(record["role"]),
    )


def _parse_specimen(value: object, index: int) -> Specimen:
    label = f"specimen[{index}]"
    _require(isinstance(value, dict), f"{label} must be an object")
    record: JsonObject = value if isinstance(value, dict) else {}
    required_strings = (
        "specimen_id",
        "category",
        "source_text",
        "characterization_notes",
        "claim_ceiling",
    )
    for key in required_strings:
        _require(isinstance(record.get(key), str), f"{label} needs a string {key}")
    _require(
        isinstance(record.get("normative_expected"), bool),
        f"{label} needs a boolean normative_expected",
    )
    minimum = record.get("expected_candidate_count_min")
    _require(
        isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= 0,
        f"{label} needs a non-negative expected_candidate_count_min",
    )
    maximum = record.get("expected_candidate_count_max")
    _require(
        maximum is None or (isinstance(maximum, int) and not isinstance(maximum, bool)),
        f"{label} expected_candidate_count_max must be an integer or null",
    )
    families_value = record.get("families", [])
    _require(isinstance(families_value, list), f"{label} families must be an array")
    families = tuple(
        _parse_family(entry, f"{label}.families")
        for entry in (families_value if isinstance(families_value, list) else [])
    )
    _require(bool(str(record["source_text"]).strip()), f"{label} source_text must not be empty")
    return Specimen(
        specimen_id=str(record["specimen_id"]),
        category=str(record["category"]),
        source_text=str(record["source_text"]),
        normative_expected=bool(record["normative_expected"]),
        expected_candidate_count_min=int(minimum) if isinstance(minimum, int) else 0,
        expected_candidate_count_max=int(maximum) if isinstance(maximum, int) else None,
        acceptable_unit_types=_optional_str_tuple(
            record.get("acceptable_unit_types"), f"{label}.acceptable_unit_types"
        ),
        families=families,
        threshold_markers=_optional_str_tuple(
            record.get("threshold_markers"), f"{label}.threshold_markers"
        ),
        characterization_notes=str(record["characterization_notes"]),
        claim_ceiling=str(record["claim_ceiling"]),
        actor_explicitly_named=_optional_bool(
            record.get("actor_explicitly_named"), f"{label}.actor_explicitly_named"
        ),
        target_explicitly_named=_optional_bool(
            record.get("target_explicitly_named"), f"{label}.target_explicitly_named"
        ),
        expected_target_spans=_optional_str_tuple(
            record.get("expected_target_spans"), f"{label}.expected_target_spans"
        ),
        required_condition_spans=_optional_str_tuple(
            record.get("required_condition_spans"), f"{label}.required_condition_spans"
        ),
        material_qualifier_spans=_optional_str_tuple(
            record.get("material_qualifier_spans"), f"{label}.material_qualifier_spans"
        ),
        non_operative_predicate_spans=_optional_str_tuple(
            record.get("non_operative_predicate_spans"),
            f"{label}.non_operative_predicate_spans",
        ),
        material_span_groups=_optional_span_groups(
            record.get("material_span_groups"), f"{label}.material_span_groups"
        ),
        candidate_span_bounds=_optional_str_tuple(
            record.get("candidate_span_bounds"), f"{label}.candidate_span_bounds"
        ),
        diagnostic_tags=_optional_str_tuple(
            record.get("diagnostic_tags", []), f"{label}.diagnostic_tags"
        )
        or (),
        separable_framing_spans=_optional_str_tuple(
            record.get("separable_framing_spans"), f"{label}.separable_framing_spans"
        ),
        framing_expected_excluded=_optional_bool(
            record.get("framing_expected_excluded"), f"{label}.framing_expected_excluded"
        ),
        framing_structure=_optional_string(
            record.get("framing_structure"), f"{label}.framing_structure"
        ),
    )


def load_corpus(path: Path, *, relpath: str | None = None) -> Corpus:
    """Load and shape-validate a frozen corpus, recording the digest of its exact bytes."""
    body = path.read_bytes()
    try:
        parsed: Any = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CharacterizationError(f"corpus at {path} is not valid UTF-8 JSON") from exc
    _require(isinstance(parsed, dict), "corpus root must be an object")
    document: JsonObject = parsed if isinstance(parsed, dict) else {}
    for key in ("corpus_id", "corpus_version", "claim_ceiling"):
        _require(isinstance(document.get(key), str), f"corpus needs a string {key}")
    specimens_value = document.get("specimens")
    _require(isinstance(specimens_value, list), "corpus needs a specimens array")
    raw_specimens = specimens_value if isinstance(specimens_value, list) else []
    _require(bool(raw_specimens), "corpus contains no specimens")
    specimens = tuple(_parse_specimen(entry, index) for index, entry in enumerate(raw_specimens))
    identifiers = [specimen.specimen_id for specimen in specimens]
    duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
    _require(not duplicates, f"corpus has duplicate specimen ids: {duplicates}")
    declared_count = document.get("specimen_count")
    if declared_count is not None:
        _require(
            declared_count == len(specimens),
            f"corpus specimen_count {declared_count!r} disagrees with {len(specimens)} specimens",
        )
    return Corpus(
        corpus_id=str(document["corpus_id"]),
        corpus_version=str(document["corpus_version"]),
        claim_ceiling=str(document["claim_ceiling"]),
        specimens=specimens,
        sha256=hashlib.sha256(body).hexdigest(),
        relpath=relpath if relpath is not None else path.as_posix(),
    )


def corpus_freeze_findings(corpus: Corpus, freeze: JsonObject) -> list[str]:
    """Differences between the corpus on disk and the frozen record. Empty means intact."""
    findings: list[str] = []
    recorded_digest = freeze.get("corpus_sha256")
    if recorded_digest != corpus.sha256:
        findings.append(
            f"corpus sha256 drift: frozen {recorded_digest!r}, on disk {corpus.sha256!r}"
        )
    recorded_count = freeze.get("specimen_count")
    if recorded_count != len(corpus.specimens):
        findings.append(
            f"specimen count drift: frozen {recorded_count!r}, on disk {len(corpus.specimens)}"
        )
    recorded_ids = freeze.get("specimen_ids")
    observed_ids = [specimen.specimen_id for specimen in corpus.specimens]
    if recorded_ids != observed_ids:
        findings.append("specimen id drift: frozen id list does not match the corpus on disk")
    recorded_sources = freeze.get("specimen_source_sha256")
    if isinstance(recorded_sources, dict):
        for specimen in corpus.specimens:
            frozen_digest = recorded_sources.get(specimen.specimen_id)
            if frozen_digest != specimen.source_sha256:
                findings.append(f"source text drift for {specimen.specimen_id}")
    else:
        findings.append("frozen record has no specimen_source_sha256 map")
    return findings


# --------------------------------------------------------------------------
# Semantic projection
# --------------------------------------------------------------------------


def semantic_projection(candidate: JsonObject) -> JsonObject:
    """Current model proposal only: literal span and provisional unit type."""
    missing = [name for name in SEMANTIC_FIELDS if name not in candidate]
    if missing:
        raise CharacterizationError(f"candidate is missing semantic fields: {missing}")
    return {name: candidate[name] for name in SEMANTIC_FIELDS}


def semantic_hash(projections: Sequence[JsonObject]) -> str:
    """Digest of the ordered projection list.

    Order-sensitive on purpose: two runs that return the same units in a different order
    have not returned the same answer, and smoothing that away would overstate stability.
    """
    canonical = json.dumps(
        list(projections), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def specimen_anchor(specimen: Specimen, *, corpus: Corpus) -> JsonObject:
    """The caller-controlled source anchor. Never model-supplied."""
    return {
        "anchor_id": f"{specimen.specimen_id}-A1",
        "source_id": f"{corpus.corpus_id}/{corpus.corpus_version}",
        "node_id": specimen.specimen_id,
        "content_hash": f"sha256:{specimen.source_sha256}",
        "quote": specimen.source_text,
    }


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_attempt(
    specimen: Specimen, *, corpus: Corpus, provider: ModelProvider, run_index: int
) -> Attempt:
    """One request through the existing boundary. Failures are recorded, never repaired."""
    try:
        result = propose_candidate_units(
            source_text=specimen.source_text,
            source_anchor=specimen_anchor(specimen, corpus=corpus),
            provider=provider,
        )
    except CandidateBoundaryError as exc:
        return _failed_attempt(specimen, run_index, BOUNDARY_REJECTED, exc)
    except ModelProviderError as exc:
        return _failed_attempt(specimen, run_index, PROVIDER_ERROR, exc)

    projections = tuple(semantic_projection(candidate) for candidate in result.candidates)
    return Attempt(
        specimen_id=specimen.specimen_id,
        run_index=run_index,
        boundary_result=STRUCTURAL_PASS,
        provider=result.provider,
        model=result.model,
        request_id=result.request_id,
        raw_content_sha256=result.raw_content_sha256,
        candidate_count=len(result.candidates),
        candidates=tuple(dict(candidate) for candidate in result.candidates),
        semantic_projections=projections,
        semantic_projection_sha256=semantic_hash(projections),
        unit_types=tuple(str(projection["unit_type"]) for projection in projections),
        error_type=None,
        error_message=None,
        observed_at=_now(),
    )


def _failed_attempt(
    specimen: Specimen, run_index: int, boundary_result: str, exc: Exception
) -> Attempt:
    return Attempt(
        specimen_id=specimen.specimen_id,
        run_index=run_index,
        boundary_result=boundary_result,
        provider=None,
        model=None,
        request_id=None,
        raw_content_sha256=None,
        candidate_count=None,
        candidates=(),
        semantic_projections=(),
        semantic_projection_sha256=None,
        unit_types=(),
        error_type=type(exc).__name__,
        error_message=str(exc),
        observed_at=_now(),
    )


def run_corpus(
    corpus: Corpus, *, provider: ModelProvider, runs_per_specimen: int
) -> tuple[Attempt, ...]:
    """Every specimen, ``runs_per_specimen`` times, in frozen corpus order."""
    _require(runs_per_specimen >= 1, "runs_per_specimen must be at least 1")
    return tuple(
        run_attempt(specimen, corpus=corpus, provider=provider, run_index=index)
        for specimen in corpus.specimens
        for index in range(1, runs_per_specimen + 1)
    )


def group_by_specimen(attempts: Sequence[Attempt]) -> dict[str, list[Attempt]]:
    """Attempts grouped by specimen, each group ordered by run index."""
    grouped: dict[str, list[Attempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.specimen_id, []).append(attempt)
    for group in grouped.values():
        group.sort(key=lambda item: item.run_index)
    return grouped


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def _accepted(attempts: Sequence[Attempt]) -> list[Attempt]:
    return [attempt for attempt in attempts if attempt.boundary_result == STRUCTURAL_PASS]


def metric_boundary_acceptance(attempts: Sequence[Attempt]) -> JsonObject:
    """A. How often a model response survived the existing candidate boundary."""
    accepted = sum(1 for item in attempts if item.boundary_result == STRUCTURAL_PASS)
    rejected = sum(1 for item in attempts if item.boundary_result == BOUNDARY_REJECTED)
    provider_errors = sum(1 for item in attempts if item.boundary_result == PROVIDER_ERROR)
    adjudicated = accepted + rejected
    return {
        "attempted": len(attempts),
        "boundary_accepted": accepted,
        "boundary_rejected": rejected,
        "provider_errors": provider_errors,
        "acceptance_rate_over_adjudicated": (accepted / adjudicated) if adjudicated else None,
        "acceptance_rate_denominator": "boundary_accepted + boundary_rejected",
        "rejection_error_types": dict(
            sorted(
                Counter(
                    item.error_type
                    for item in attempts
                    if item.boundary_result == BOUNDARY_REJECTED and item.error_type
                ).items()
            )
        ),
        "boundary_errors": [
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "error_type": item.error_type,
                "error_message": item.error_message,
            }
            for item in attempts
            if item.boundary_result != STRUCTURAL_PASS
        ],
        "note": (
            "A provider transport error is not a boundary rejection and is counted "
            "separately. No rejected response was repaired or retried."
        ),
    }


def metric_normative_presence(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """B. For positives: how often at least the declared minimum was returned."""
    per_specimen: list[JsonObject] = []
    total_runs = 0
    observed = 0
    misses = 0
    for specimen in corpus.specimens:
        if not specimen.normative_expected:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        hits = [
            item
            for item in accepted
            if (item.candidate_count or 0) >= specimen.expected_candidate_count_min
        ]
        total_runs += len(accepted)
        observed += len(hits)
        misses += len(accepted) - len(hits)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "category": specimen.category,
                "expected_candidate_count_min": specimen.expected_candidate_count_min,
                "accepted_runs": len(accepted),
                "runs_meeting_minimum": len(hits),
                "result": (
                    NOT_OBSERVED
                    if not accepted
                    else EXPECTED_PRESENCE_OBSERVED
                    if len(hits) == len(accepted)
                    else PRESENCE_MISS
                ),
            }
        )
    return {
        "positive_control_specimens": len(per_specimen),
        "accepted_runs": total_runs,
        "runs_meeting_minimum": observed,
        "presence_misses": misses,
        "per_specimen": per_specimen,
        "note": (
            "An engineering presence measurement over accepted runs only. It is not a "
            "measurement of normative or legal correctness."
        ),
    }


def metric_negative_controls(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """C. For negatives: how often any candidate was returned at all."""
    per_specimen: list[JsonObject] = []
    total_runs = 0
    false_positive_runs = 0
    for specimen in corpus.specimens:
        if specimen.normative_expected:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        positives = [item for item in accepted if (item.candidate_count or 0) >= 1]
        total_runs += len(accepted)
        false_positive_runs += len(positives)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "category": specimen.category,
                "accepted_runs": len(accepted),
                "runs_returning_candidates": len(positives),
                "observed_unit_types": sorted(
                    {unit_type for item in positives for unit_type in item.unit_types}
                ),
                "result": (
                    NOT_OBSERVED
                    if not accepted
                    else FALSE_POSITIVE_OBSERVED
                    if positives
                    else EXPECTED_ABSENCE_OBSERVED
                ),
            }
        )
    return {
        "negative_control_specimens": len(per_specimen),
        "accepted_runs": total_runs,
        "false_positive_runs": false_positive_runs,
        "false_positive_rate": (false_positive_runs / total_runs) if total_runs else None,
        "per_specimen": per_specimen,
    }


def metric_candidate_count_stability(grouped: dict[str, list[Attempt]]) -> JsonObject:
    """D. Repeated-run candidate-count distribution and exact stability."""
    per_specimen: list[JsonObject] = []
    for specimen_id, attempts in sorted(grouped.items()):
        accepted = _accepted(attempts)
        distribution = Counter(item.candidate_count for item in accepted)
        per_specimen.append(
            {
                "specimen_id": specimen_id,
                "accepted_runs": len(accepted),
                "count_distribution": {
                    str(key): value
                    for key, value in sorted(
                        distribution.items(), key=lambda pair: (pair[0] is None, pair[0])
                    )
                },
                "distinct_counts": len(distribution),
                "result": (
                    NOT_OBSERVED
                    if not accepted
                    else REPEAT_STABLE
                    if len(distribution) == 1
                    else REPEAT_VARIANT
                ),
            }
        )
    return {"per_specimen": per_specimen}


def metric_unit_type_observation(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """E. Observed unit types and whether they fall inside the preregistered set."""
    per_specimen: list[JsonObject] = []
    for specimen in corpus.specimens:
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        distribution = Counter(unit_type for item in accepted for unit_type in item.unit_types)
        acceptable = specimen.acceptable_unit_types
        outside = sorted(set(distribution) - set(acceptable)) if acceptable is not None else []
        if acceptable is None or not distribution:
            result = NOT_OBSERVED
        elif outside:
            result = TYPE_OUTSIDE_PREREGISTERED_SET
        else:
            result = TYPE_WITHIN_PREREGISTERED_SET
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "acceptable_unit_types": list(acceptable) if acceptable is not None else None,
                "observed_unit_type_distribution": dict(sorted(distribution.items())),
                "types_outside_preregistered_set": outside,
                "distinct_type_sets_across_runs": len(
                    {tuple(item.unit_types) for item in accepted}
                ),
                "result": result,
            }
        )
    return {
        "per_specimen": per_specimen,
        "note": (
            "No type is mapped onto another. mandate and obligation are reported as the "
            "distinct answers they are."
        ),
    }


def metric_semantic_stability(grouped: dict[str, list[Attempt]]) -> JsonObject:
    """F. Exact repeated-run stability of the canonical semantic projection."""
    per_specimen: list[JsonObject] = []
    for specimen_id, attempts in sorted(grouped.items()):
        accepted = _accepted(attempts)
        distribution = Counter(
            item.semantic_projection_sha256
            for item in accepted
            if item.semantic_projection_sha256 is not None
        )
        per_specimen.append(
            {
                "specimen_id": specimen_id,
                "accepted_runs": len(accepted),
                "semantic_hash_distribution": dict(sorted(distribution.items())),
                "distinct_semantic_hashes": len(distribution),
                "result": (
                    NOT_OBSERVED
                    if not distribution
                    else REPEAT_STABLE
                    if len(distribution) == 1
                    else REPEAT_VARIANT
                ),
            }
        )
    return {
        "per_specimen": per_specimen,
        "excluded_fields": list(OIC_CONTROLLED_FIELDS),
        "projected_fields": list(SEMANTIC_FIELDS),
        "note": (
            "Different semantic answers are never normalized into equivalence. The hash is "
            "order-sensitive, so a reordered set of units counts as a variant."
        ),
    }


def _family_view(specimen: Specimen, attempts: Sequence[Attempt], role: str) -> JsonObject:
    accepted = _accepted(attempts)
    return {
        "specimen_id": specimen.specimen_id,
        "role": role,
        "accepted_runs": len(accepted),
        "candidate_presence_observed": any((item.candidate_count or 0) >= 1 for item in accepted),
        "observed_counts": sorted(
            {item.candidate_count for item in accepted if item.candidate_count is not None}
        ),
        "observed_unit_types": sorted({unit for item in accepted for unit in item.unit_types}),
        "semantic_hashes": sorted(
            {
                item.semantic_projection_sha256
                for item in accepted
                if item.semantic_projection_sha256
            }
        ),
    }


def _families(corpus: Corpus, grouped: dict[str, list[Attempt]], kind: str) -> list[JsonObject]:
    by_family: dict[str, list[JsonObject]] = {}
    for specimen in corpus.specimens:
        for family in specimen.families:
            if family.family_kind != kind:
                continue
            by_family.setdefault(family.family_id, []).append(
                _family_view(specimen, grouped.get(specimen.specimen_id, []), family.role)
            )

    def agree(members: list[JsonObject], key: str) -> bool:
        return len({tuple(member[key]) for member in members}) == 1

    reports: list[JsonObject] = []
    for family_id, members in sorted(by_family.items()):
        reports.append(
            {
                "family_id": family_id,
                "family_kind": kind,
                "members": members,
                "presence_agreement": (
                    len({bool(member["candidate_presence_observed"]) for member in members}) == 1
                ),
                "count_set_agreement": agree(members, "observed_counts"),
                "unit_type_set_agreement": agree(members, "observed_unit_types"),
                "semantic_hash_set_agreement": agree(members, "semantic_hashes"),
            }
        )
    return reports


def metric_source_standing_invariance(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """G. Whether standing language alone changed the observed candidate behaviour."""
    return {
        "families": _families(corpus, grouped, "source_standing"),
        "note": (
            "Members of a source-standing family differ only in language about whether the "
            "source is draft, synthetic, hypothetical, unverified or non-authoritative. "
            "Disagreement is reported as an observation, not repaired."
        ),
    }


def metric_paraphrase_families(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """H. Agreement across phrasings the fixture intends as equivalent."""
    return {
        "families": _families(corpus, grouped, "paraphrase"),
        "candidate_stage_invariants": [
            "presence_agreement",
            "count_set_agreement",
            "unit_type_set_agreement",
        ],
        "not_required_at_candidate_stage": ["semantic_hash_set_agreement"],
        "note": (
            "The fixture states the test intent that these phrasings are equivalent. It "
            "does not establish that they are, and agreement here is not correctness. "
            "Exact semantic-hash agreement across materially different phrasings is NOT "
            "required at this stage: a source-grounded candidate quotes its own fragment, "
            "so different wording produces different spans by construction. Normalizing "
            "them is Institutional IR's job, after admission."
        ),
    }


def _placement(projection: JsonObject, markers: Sequence[str]) -> str:
    def holds(value: object) -> bool:
        if isinstance(value, str):
            return any(marker in value for marker in markers)
        if isinstance(value, list):
            return any(isinstance(entry, str) and holds(entry) for entry in value)
        return False

    in_object = holds(projection.get("object"))
    in_conditions = holds(projection.get("conditions"))
    if in_object and in_conditions:
        return PLACEMENT_BOTH
    if in_object:
        return PLACEMENT_OBJECT
    if in_conditions:
        return PLACEMENT_CONDITIONS
    others = [
        name
        for name in SEMANTIC_FIELDS
        if name not in {"object", "conditions"} and holds(projection.get(name))
    ]
    if others:
        return f"{PLACEMENT_OTHER_FIELD}:{','.join(others)}"
    return PLACEMENT_NEITHER


def metric_threshold_placement(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """I. Where threshold material actually appeared. Observation only."""
    per_specimen: list[JsonObject] = []
    for specimen in corpus.specimens:
        if not specimen.threshold_markers:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        distribution = Counter(
            _placement(projection, specimen.threshold_markers)
            for item in accepted
            for projection in item.semantic_projections
        )
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "threshold_markers": list(specimen.threshold_markers),
                "candidates_examined": sum(distribution.values()),
                "placement_distribution": dict(sorted(distribution.items())),
            }
        )
    return {
        "per_specimen": per_specimen,
        "note": (
            "OIC does not prescribe where a threshold belongs and this harness does not "
            "either. Placement is recorded exactly as returned."
        ),
    }


def metric_multi_unit(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """J. Whether fragments carrying more than one norm came back separated or collapsed."""
    per_specimen: list[JsonObject] = []
    for specimen in corpus.specimens:
        if specimen.expected_candidate_count_min < 2:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "expected_candidate_count_min": specimen.expected_candidate_count_min,
                "accepted_runs": len(accepted),
                "count_distribution": {
                    str(key): value
                    for key, value in sorted(
                        Counter(item.candidate_count for item in accepted).items(),
                        key=lambda pair: (pair[0] is None, pair[0]),
                    )
                },
                "runs_returning_separated_units": sum(
                    1 for item in accepted if (item.candidate_count or 0) >= 2
                ),
                "runs_returning_a_single_unit": sum(
                    1 for item in accepted if item.candidate_count == 1
                ),
                "observed_unit_types": sorted(
                    {unit for item in accepted for unit in item.unit_types}
                ),
            }
        )
    return {
        "per_specimen": per_specimen,
        "note": "Collapsed multi-norm fragments are recorded, never split by the harness.",
    }


# --------------------------------------------------------------------------
# Minimal source-candidate metrics (OIC-CANDIDATE-SEMANTICS-003)
# --------------------------------------------------------------------------


def metric_provider_errors(attempts: Sequence[Attempt]) -> JsonObject:
    """B. Provider/transport errors, separate from boundary refusals."""
    errors = [item for item in attempts if item.boundary_result == PROVIDER_ERROR]
    return {
        "provider_errors": len(errors),
        "error_rate": len(errors) / len(attempts) if attempts else None,
        "errors": [
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "error_type": item.error_type,
                "error_message": item.error_message,
            }
            for item in errors
        ],
    }


def metric_candidate_span_grounding(attempts: Sequence[Attempt]) -> JsonObject:
    """F. Recheck that every accepted 003 span is literal source material.

    The boundary already enforces this before an Attempt can be accepted. This metric
    records that mechanical invariant rather than claiming semantic sufficiency.
    """
    accepted = [item for item in attempts if item.boundary_result == STRUCTURAL_PASS]
    spans = [str(candidate["candidate_span"]) for item in accepted for candidate in item.candidates]
    return {
        "accepted_runs": len(accepted),
        "candidate_spans_examined": len(spans),
        "candidate_spans_passing_boundary_grounding": len(spans),
        "grounding_rule": (
            "collapse_whitespace(casefold(candidate_span)) is a substring of "
            "collapse_whitespace(casefold(source_text))"
        ),
        "note": "Boundary-refused responses are reported under metric A, never repaired.",
    }


def _candidate_spans(attempt: Attempt) -> tuple[str, ...]:
    return tuple(str(candidate["candidate_span"]) for candidate in attempt.candidates)


def _contains(haystack: str, needle: str) -> bool:
    return " ".join(needle.split()).casefold() in " ".join(haystack.split()).casefold()


def metric_material_span_completeness(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """G. Whether every preregistered material element remains in returned spans."""
    per_specimen: list[JsonObject] = []
    complete_runs = 0
    measured_runs = 0
    for specimen in corpus.specimens:
        groups = specimen.material_span_groups
        if not groups:
            continue
        run_reports: list[JsonObject] = []
        for attempt in _accepted(grouped.get(specimen.specimen_id, [])):
            spans = _candidate_spans(attempt)
            group_hits = [
                any(_contains(span, variant) for span in spans for variant in group)
                for group in groups
            ]
            complete = all(group_hits)
            measured_runs += 1
            complete_runs += int(complete)
            run_reports.append(
                {
                    "run_index": attempt.run_index,
                    "material_groups_preserved": sum(group_hits),
                    "material_groups_expected": len(groups),
                    "complete": complete,
                }
            )
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "material_span_groups": [list(group) for group in groups],
                "runs": run_reports,
            }
        )
    return {
        "measured_runs": measured_runs,
        "complete_runs": complete_runs,
        "incomplete_runs": measured_runs - complete_runs,
        "per_specimen": per_specimen,
        "note": "Each inner group is disjunctive; every registered group is material.",
    }


def metric_candidate_span_repeat_stability(
    grouped: dict[str, list[Attempt]],
) -> JsonObject:
    """H. Exact ordered span stability, with variation kept observational."""
    per_specimen: list[JsonObject] = []
    for specimen_id, attempts in sorted(grouped.items()):
        distribution = Counter(_candidate_spans(item) for item in _accepted(attempts))
        per_specimen.append(
            {
                "specimen_id": specimen_id,
                "distinct_ordered_span_sets": len(distribution),
                "distribution": [
                    {"candidate_spans": list(spans), "runs": count}
                    for spans, count in sorted(distribution.items())
                ],
                "result": NOT_OBSERVED
                if not distribution
                else (REPEAT_STABLE if len(distribution) == 1 else REPEAT_VARIANT),
            }
        )
    return {
        "per_specimen": per_specimen,
        "note": "Exact span variation is informative and is not automatically semantic failure.",
    }


def metric_advisory_candidate_presence(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """K. Presence and provisional typing on advisory controls."""
    per_specimen: list[JsonObject] = []
    misses = 0
    for specimen in corpus.specimens:
        if specimen.category != "advisory":
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        present = [item for item in accepted if (item.candidate_count or 0) > 0]
        misses += len(accepted) - len(present)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "accepted_runs": len(accepted),
                "runs_with_candidate": len(present),
                "provisional_unit_types": sorted(
                    {unit for item in present for unit in item.unit_types}
                ),
            }
        )
    return {"presence_misses": misses, "per_specimen": per_specimen}


def metric_candidate_span_overreach(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """M. Bounded observation against explicitly registered proposition regions."""
    per_specimen: list[JsonObject] = []
    examined = 0
    overreaching = 0
    for specimen in corpus.specimens:
        bounds = specimen.candidate_span_bounds
        if not bounds:
            continue
        spans = [
            span
            for attempt in _accepted(grouped.get(specimen.specimen_id, []))
            for span in _candidate_spans(attempt)
        ]
        outside = [span for span in spans if not any(_contains(bound, span) for bound in bounds)]
        examined += len(spans)
        overreaching += len(outside)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "candidate_span_bounds": list(bounds),
                "candidate_spans_examined": len(spans),
                "spans_outside_every_registered_bound": outside,
            }
        )
    return {
        "candidate_spans_examined": examined,
        "candidate_spans_outside_bounds": overreaching,
        "per_specimen": per_specimen,
        "note": (
            "Bounds are specimen-specific maximum proposition regions, not a universal "
            "shortest-span rule."
        ),
    }


# --------------------------------------------------------------------------
# Framing-separation metrics (OIC-CANDIDATE-SEMANTICS-004)
#
# Overreach and underreach are opposite failures and are counted separately on purpose.
# A span that sheds a draft prefix but also sheds the threshold has not separated framing
# successfully; it has traded one defect for a worse one, and metric J refuses to score it
# as a success.
# --------------------------------------------------------------------------


def _material_groups_missing(specimen: Specimen, spans: Sequence[str]) -> list[list[str]]:
    """Preregistered material groups absent from a run's spans, taken together."""
    return [
        list(group)
        for group in (specimen.material_span_groups or ())
        if not any(_contains(span, variant) for span in spans for variant in group)
    ]


def metric_framing_separation(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """J. Whether separable source-standing framing stayed outside the candidate span.

    Reported per preregistered framing specimen. A span counts as a clean separation only
    when it carries no registered framing AND the run loses no preregistered material
    content, so shrinking a span past the proposition can never look like a success.
    """
    per_specimen: list[JsonObject] = []
    totals = {
        "candidate_spans_examined": 0,
        "spans_inside_acceptable_bounds": 0,
        "spans_containing_separable_framing": 0,
        "runs_dropping_material_content": 0,
        "spans_cleanly_separated": 0,
    }
    for specimen in corpus.specimens:
        if specimen.framing_expected_excluded is not True:
            continue
        framing = specimen.separable_framing_spans or ()
        bounds = specimen.candidate_span_bounds or ()
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        spans_examined: list[str] = []
        carrying: list[str] = []
        inside = 0
        runs_losing_material = 0
        run_reports: list[JsonObject] = []
        for attempt in accepted:
            spans = _candidate_spans(attempt)
            spans_examined.extend(spans)
            run_carrying = [
                span for span in spans if any(_contains(span, mark) for mark in framing)
            ]
            carrying.extend(run_carrying)
            run_inside = [span for span in spans if any(_contains(bound, span) for bound in bounds)]
            inside += len(run_inside)
            missing = _material_groups_missing(specimen, spans)
            runs_losing_material += int(bool(missing))
            run_reports.append(
                {
                    "run_index": attempt.run_index,
                    "candidate_spans": list(spans),
                    "spans_containing_separable_framing": run_carrying,
                    "spans_inside_acceptable_bounds": len(run_inside),
                    "material_groups_lost": missing,
                    "result": (
                        MATERIAL_UNDERREACH
                        if missing
                        else FRAMING_CARRIED
                        if run_carrying
                        else FRAMING_SEPARATED
                    ),
                }
            )
        clean = sum(
            len(report["candidate_spans"])
            for report in run_reports
            if report["result"] == FRAMING_SEPARATED
        )
        totals["candidate_spans_examined"] += len(spans_examined)
        totals["spans_inside_acceptable_bounds"] += inside
        totals["spans_containing_separable_framing"] += len(carrying)
        totals["runs_dropping_material_content"] += runs_losing_material
        totals["spans_cleanly_separated"] += clean
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "framing_structure": specimen.framing_structure,
                "separable_framing_spans": list(framing),
                "acceptable_proposition_bounds": list(bounds),
                "accepted_runs": len(accepted),
                "candidate_spans_examined": len(spans_examined),
                "spans_inside_acceptable_bounds": inside,
                "spans_containing_separable_framing": len(carrying),
                "observed_framing_carrying_spans": sorted(set(carrying)),
                "runs_dropping_material_proposition_content": runs_losing_material,
                "runs": run_reports,
                "result": (
                    NOT_OBSERVED
                    if not accepted
                    else MATERIAL_UNDERREACH
                    if runs_losing_material
                    else FRAMING_CARRIED
                    if carrying
                    else FRAMING_SEPARATED
                ),
            }
        )
    return {
        **totals,
        "measured_specimens": len(per_specimen),
        "per_specimen": per_specimen,
        "note": (
            "Excluding framing while losing material proposition content is recorded as "
            "MATERIAL_CONTENT_LOST, never as a separation success. Framing is asked for in "
            "the prompt contract and never removed after generation."
        ),
    }


def metric_framing_must_not_be_stripped(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """J2. Controls where framing-looking words are part of the proposition itself.

    The counterpart to J. A specimen whose source says something *about a draft* rather
    than *as a draft* must keep that language, and a span that sheds it is underreach.
    """
    per_specimen: list[JsonObject] = []
    losing = 0
    for specimen in corpus.specimens:
        if specimen.framing_expected_excluded is not False:
            continue
        if not specimen.material_span_groups:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        run_reports: list[JsonObject] = []
        for attempt in accepted:
            missing = _material_groups_missing(specimen, _candidate_spans(attempt))
            losing += int(bool(missing))
            run_reports.append(
                {
                    "run_index": attempt.run_index,
                    "candidate_spans": list(_candidate_spans(attempt)),
                    "material_groups_lost": missing,
                    "result": MATERIAL_UNDERREACH if missing else MATERIAL_COMPLETE,
                }
            )
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "framing_structure": specimen.framing_structure,
                "accepted_runs": len(accepted),
                "runs": run_reports,
            }
        )
    return {
        "measured_specimens": len(per_specimen),
        "runs_dropping_material_content": losing,
        "per_specimen": per_specimen,
        "note": (
            "These specimens register no separable framing. Language that merely looks "
            "like framing is material proposition content here and must stay in the span."
        ),
    }


def metric_candidate_span_underreach(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """M. Material proposition content lost from the returned spans.

    Deliberately the mirror of the overreach metric and reported beside it. Metric G says
    whether a run was complete; this one names the groups that went missing and books the
    loss as underreach, so a shrinking span is never mistaken for a tightening one.
    """
    per_specimen: list[JsonObject] = []
    measured = 0
    underreaching = 0
    for specimen in corpus.specimens:
        if not specimen.material_span_groups:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        run_reports: list[JsonObject] = []
        for attempt in accepted:
            missing = _material_groups_missing(specimen, _candidate_spans(attempt))
            measured += 1
            underreaching += int(bool(missing))
            run_reports.append(
                {
                    "run_index": attempt.run_index,
                    "material_groups_lost": missing,
                    "result": MATERIAL_UNDERREACH if missing else MATERIAL_COMPLETE,
                }
            )
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "material_span_groups": [list(g) for g in specimen.material_span_groups],
                "runs": run_reports,
            }
        )
    return {
        "measured_runs": measured,
        "runs_losing_material_content": underreaching,
        "per_specimen": per_specimen,
        "note": (
            "Underreach and overreach are opposite defects. Overreach is metric M-prime "
            "(candidate_span_overreach); a run can exhibit both at once and each is "
            "counted where it belongs."
        ),
    }


# --------------------------------------------------------------------------
# Source-grounding metrics (OIC-CANDIDATE-SEMANTICS-002)
#
# Every one of these is an observation against what the corpus pre-registered about the
# SOURCE, not a judgement about the model. A specimen whose pre-registration is wrong
# produces a confidently wrong count, which is why the pre-registrations are frozen and
# separately tested.
# --------------------------------------------------------------------------


def _match(spans: Sequence[str], values: Sequence[object]) -> str | None:
    """First declared span found inside any candidate value. Literal, case-insensitive."""
    haystacks = [
        _grounding_key(value) for value in values if isinstance(value, str) and value.strip()
    ]
    for span in spans:
        needle = _grounding_key(span)
        if any(needle in haystack for haystack in haystacks):
            return span
    return None


def _grounding_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _textual_values(projection: JsonObject) -> list[object]:
    values: list[object] = []
    for name in TEXTUAL_ROLE_FIELDS:
        value = projection.get(name)
        if isinstance(value, list):
            values.extend(value)
        else:
            values.append(value)
    return values


def metric_unsupported_actor(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """K. Candidates asserting an actor on specimens whose source names none.

    Under the revised contract an ungrounded actor cannot survive the boundary at all, so
    anything counted here is a *grounded* span the model chose to read as an actor on a
    fragment the corpus records as naming nobody. That is a weaker and more honest finding
    than the pre-revision invention it replaces, and both are worth seeing.
    """
    per_specimen: list[JsonObject] = []
    asserted = 0
    examined = 0
    for specimen in corpus.specimens:
        if specimen.actor_explicitly_named is not False:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        candidates = [projection for item in accepted for projection in item.semantic_projections]
        with_actor = [
            projection for projection in candidates if projection.get("actor") is not None
        ]
        examined += len(candidates)
        asserted += len(with_actor)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "candidates_examined": len(candidates),
                "candidates_asserting_an_actor": len(with_actor),
                "asserted_actor_values": sorted(
                    {str(projection["actor"]) for projection in with_actor}
                ),
                "result": (
                    NOT_OBSERVED
                    if not candidates
                    else ACTOR_ASSERTED_WHERE_SOURCE_NAMES_NONE
                    if with_actor
                    else ACTOR_ABSENT_AS_PREREGISTERED
                ),
            }
        )
    return {
        "specimens_where_source_names_no_actor": len(per_specimen),
        "candidates_examined": examined,
        "candidates_asserting_an_actor": asserted,
        "per_specimen": per_specimen,
        "note": (
            "The boundary already refuses an actor that is not a verbatim source span, so "
            "an entirely invented participant fails the response and is counted under "
            "boundary rejections, not here."
        ),
    }


def _element_metric(
    corpus: Corpus,
    grouped: dict[str, list[Attempt]],
    *,
    spans_of: str,
    searched_fields: Sequence[str],
    label: str,
) -> JsonObject:
    per_specimen: list[JsonObject] = []
    examined = 0
    omitted = 0
    for specimen in corpus.specimens:
        spans = getattr(specimen, spans_of)
        if not spans:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        projections = [projection for item in accepted for projection in item.semantic_projections]
        preserved: list[str] = []
        missing = 0
        for projection in projections:
            values: list[object] = []
            for name in searched_fields:
                value = projection.get(name)
                if isinstance(value, list):
                    values.extend(value)
                else:
                    values.append(value)
            found = _match(spans, values)
            if found is None:
                missing += 1
            else:
                preserved.append(found)
        examined += len(projections)
        omitted += missing
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "declared_spans": list(spans),
                "searched_fields": list(searched_fields),
                "candidates_examined": len(projections),
                "candidates_preserving_the_element": len(preserved),
                "candidates_omitting_the_element": missing,
                "matched_renderings": sorted(set(preserved)),
                "result": (
                    NOT_OBSERVED
                    if not projections
                    else ELEMENT_OMITTED
                    if missing
                    else ELEMENT_PRESERVED
                ),
            }
        )
    return {
        "measured_specimens": len(per_specimen),
        "candidates_examined": examined,
        "candidates_omitting_the_element": omitted,
        "per_specimen": per_specimen,
        "element": label,
        "note": (
            "Each declared span list is disjunctive: one required element, several "
            "acceptable renderings. Matching is literal and case-insensitive; a model that "
            "restates the element in other words reads as omitted."
        ),
    }


def metric_condition_preservation(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """L. Explicit if/when/where/unless qualifiers reaching ``conditions``."""
    return _element_metric(
        corpus,
        grouped,
        spans_of="required_condition_spans",
        searched_fields=("conditions",),
        label="explicit qualifying clause, searched in conditions only",
    )


def metric_material_qualifier_preservation(
    corpus: Corpus, grouped: dict[str, list[Attempt]]
) -> JsonObject:
    """M. Thresholds and quantities surviving anywhere in the candidate."""
    return _element_metric(
        corpus,
        grouped,
        spans_of="material_qualifier_spans",
        searched_fields=TEXTUAL_ROLE_FIELDS,
        label="material quantitative or temporal qualifier, searched in every textual role",
    )


def metric_advisory_presence(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """N. Whether explicit recommendatory language is discoverable at all."""
    per_specimen: list[JsonObject] = []
    accepted_runs = 0
    misses = 0
    for specimen in corpus.specimens:
        if specimen.category != "advisory":
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        empty = [item for item in accepted if (item.candidate_count or 0) == 0]
        accepted_runs += len(accepted)
        misses += len(empty)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "accepted_runs": len(accepted),
                "runs_returning_no_candidate": len(empty),
                "observed_unit_types": sorted(
                    {unit for item in accepted for unit in item.unit_types}
                ),
                "result": (
                    NOT_OBSERVED
                    if not accepted
                    else PRESENCE_MISS
                    if empty
                    else EXPECTED_PRESENCE_OBSERVED
                ),
            }
        )
    return {
        "advisory_specimens": len(per_specimen),
        "accepted_runs": accepted_runs,
        "presence_misses": misses,
        "per_specimen": per_specimen,
        "note": (
            "OIC-CANDIDATE-SEMANTICS-001 recorded 3/3 presence misses on the single "
            "advisory specimen. This metric isolates that class."
        ),
    }


def metric_target_preservation(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """O. Explicit recipients reaching the ``target`` role."""
    per_specimen: list[JsonObject] = []
    examined = 0
    preserved_total = 0
    for specimen in corpus.specimens:
        if specimen.target_explicitly_named is not True:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        projections = [projection for item in accepted for projection in item.semantic_projections]
        spans = specimen.expected_target_spans or ()
        in_target = [
            projection
            for projection in projections
            if _match(spans, [projection.get("target")]) is not None
        ]
        elsewhere = [
            projection
            for projection in projections
            if projection not in in_target
            and _match(spans, _textual_values(projection)) is not None
        ]
        examined += len(projections)
        preserved_total += len(in_target)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "expected_target_spans": list(spans),
                "candidates_examined": len(projections),
                "candidates_carrying_it_in_target": len(in_target),
                "candidates_carrying_it_in_another_role": len(elsewhere),
                "candidates_dropping_it_entirely": len(projections)
                - len(in_target)
                - len(elsewhere),
                "observed_target_values": sorted(
                    {
                        str(projection["target"])
                        for projection in projections
                        if projection.get("target") is not None
                    }
                ),
                "result": (
                    NOT_OBSERVED
                    if not projections
                    else TARGET_PRESERVED
                    if len(in_target) == len(projections)
                    else TARGET_OMITTED
                ),
            }
        )
    return {
        "specimens_with_an_explicit_target": len(per_specimen),
        "candidates_examined": examined,
        "candidates_carrying_it_in_target": preserved_total,
        "per_specimen": per_specimen,
        "note": (
            "Carrying an explicit recipient in another role is reported separately from "
            "dropping it. Neither is corrected."
        ),
    }


def metric_evidence_duty_typing(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """P. How explicit record and proof duties were actually classified."""
    per_specimen: list[JsonObject] = []
    for specimen in corpus.specimens:
        if specimen.category != "evidence_duty":
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        projections = [projection for item in accepted for projection in item.semantic_projections]
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "candidates_examined": len(projections),
                "unit_type_distribution": dict(
                    sorted(Counter(str(item["unit_type"]) for item in projections).items())
                ),
                "candidates_typed_evidence_duty": sum(
                    1 for item in projections if item["unit_type"] == "evidence_duty"
                ),
                "candidates_populating_evidence_requirements": sum(
                    1 for item in projections if item.get("evidence_requirements")
                ),
                "candidates_with_a_null_action": sum(
                    1 for item in projections if item.get("action") is None
                ),
            }
        )
    return {
        "per_specimen": per_specimen,
        "note": (
            "OIC-CANDIDATE-SEMANTICS-001 recorded evidence_requirements populated while "
            "unit_type was condition and action was null. Those three are reported side by "
            "side so the pattern stays visible."
        ),
    }


def metric_operative_predicate(corpus: Corpus, grouped: dict[str, list[Attempt]]) -> JsonObject:
    """Q. Whether a trigger predicate was recorded as the operative action."""
    per_specimen: list[JsonObject] = []
    total = 0
    confused = 0
    for specimen in corpus.specimens:
        spans = specimen.non_operative_predicate_spans
        if not spans:
            continue
        accepted = _accepted(grouped.get(specimen.specimen_id, []))
        projections = [projection for item in accepted for projection in item.semantic_projections]
        hits = [
            projection
            for projection in projections
            if _match(spans, [projection.get("action")]) is not None
        ]
        total += len(projections)
        confused += len(hits)
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                "trigger_predicate_spans": list(spans),
                "candidates_examined": len(projections),
                "candidates_recording_the_trigger_as_action": len(hits),
                "observed_action_values": sorted(
                    {
                        str(projection["action"])
                        for projection in projections
                        if projection.get("action") is not None
                    }
                ),
                "result": (
                    NOT_OBSERVED
                    if not projections
                    else TRIGGER_RECORDED_AS_ACTION
                    if hits
                    else TRIGGER_NOT_RECORDED_AS_ACTION
                ),
            }
        )
    return {
        "measured_specimens": len(per_specimen),
        "candidates_examined": total,
        "candidates_recording_the_trigger_as_action": confused,
        "per_specimen": per_specimen,
    }


# --------------------------------------------------------------------------
# Receipt
# --------------------------------------------------------------------------


def implementation_git_sha(root: Path) -> JsonObject:
    """The commit the harness ran from, plus whether the worktree was dirty."""
    git = shutil.which("git")
    if git is None:
        return {"commit": None, "worktree_clean": None}

    def run(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - resolved executable, literal arguments
            [git, "-C", str(root), *argv], check=False, capture_output=True, text=True
        )

    head = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {
        "commit": head.stdout.strip() if head.returncode == 0 else None,
        "worktree_clean": status.returncode == 0 and not status.stdout.strip(),
    }


def historical_metric_names(receipt: JsonObject) -> tuple[str, ...]:
    """Read metric names from a historical receipt without reinterpreting them as 003.

    This intentionally does not run old role metrics against the current candidate schema.
    It preserves the versioned labels already recorded in 001/002 evidence.
    """
    work_order = receipt.get("work_order")
    if work_order not in {"OIC-CANDIDATE-SEMANTICS-001", "OIC-CANDIDATE-SEMANTICS-002"}:
        raise CharacterizationError("receipt is not a supported historical metric version")
    metrics = receipt.get("metrics")
    if not isinstance(metrics, dict):
        raise CharacterizationError("historical receipt has no metrics object")
    return tuple(str(name) for name in metrics)


def _attempt_evidence(attempts: Sequence[Attempt]) -> list[JsonObject]:
    return [
        {
            "specimen_id": attempt.specimen_id,
            "run_index": attempt.run_index,
            "boundary_result": attempt.boundary_result,
            "provider": attempt.provider,
            "model": attempt.model,
            "request_id": attempt.request_id,
            "raw_content_sha256": attempt.raw_content_sha256,
            "candidate_count": attempt.candidate_count,
            "candidates": list(attempt.candidates),
            "candidate_projections": list(attempt.semantic_projections),
            "candidate_projection_sha256": attempt.semantic_projection_sha256,
            "unit_types": list(attempt.unit_types),
            "error_type": attempt.error_type,
            "error_message": attempt.error_message,
            "observed_at": attempt.observed_at,
        }
        for attempt in attempts
    ]


def _build_receipt_004(
    *,
    corpus: Corpus,
    attempts: Sequence[Attempt],
    runs_per_specimen: int,
    provider_name: str,
    model: str,
    corpus_integrity: str,
    corpus_freeze_relpath: str,
    integrity_findings: Sequence[str],
    implementation: JsonObject,
) -> JsonObject:
    """OIC-CANDIDATE-SEMANTICS-004 metrics: 003's set plus explicit framing separation.

    Version-specific by design. 001, 002 and 003 receipts keep their own metric contracts
    and are never reinterpreted under this one.
    """
    grouped = group_by_specimen(attempts)
    boundary = metric_boundary_acceptance(attempts)
    provider_errors = metric_provider_errors(attempts)
    presence = metric_normative_presence(corpus, grouped)
    negatives = metric_negative_controls(corpus, grouped)
    framing = metric_framing_separation(corpus, grouped)
    underreach = metric_candidate_span_underreach(corpus, grouped)
    overreach = metric_candidate_span_overreach(corpus, grouped)
    return {
        "work_order": "OIC-CANDIDATE-SEMANTICS-004",
        "metric_contract": "candidate-semantics-004-a-through-m",
        "claim_ceiling": CLAIM_CEILING_004,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED; engineering observations only.",
        "generated_at": _now(),
        "implementation_git_sha": implementation.get("commit"),
        "implementation_worktree_clean": implementation.get("worktree_clean"),
        "candidate_contract": {
            "model_proposed_fields": ["candidate_span", "unit_type"],
            "oic_controlled_fields": [
                "unit_id",
                "interpretation_state",
                "epistemic_state",
                "source_anchors",
            ],
            "schema_changed_in_004": False,
            "framing_separation_mechanism": (
                "prompt contract only; no phrase list, no regex, no post-generation "
                "trimming, and no repair exists in production code"
            ),
        },
        "corpus": {
            "corpus_id": corpus.corpus_id,
            "corpus_version": corpus.corpus_version,
            "corpus_relpath": corpus.relpath,
            "corpus_sha256": corpus.sha256,
            "corpus_freeze_relpath": corpus_freeze_relpath,
            "specimen_count": len(corpus.specimens),
            "specimen_ids": [item.specimen_id for item in corpus.specimens],
            "claim_ceiling": corpus.claim_ceiling,
        },
        "engineering_gates": {
            "corpus_integrity": corpus_integrity,
            "corpus_integrity_findings": list(integrity_findings),
            "harness_executed_every_planned_request": len(attempts)
            == len(corpus.specimens) * runs_per_specimen,
            "note": "Mechanical gates only; no semantic or institutional verdict.",
        },
        "run_conditions": {
            "model_provider": provider_name,
            "model": model,
            "runs_per_specimen": runs_per_specimen,
            "total_requests_attempted": len(attempts),
            "statistical_note": "A bounded characterization sample; it certifies nothing.",
        },
        "metrics": {
            "a_boundary_acceptance": boundary,
            "b_provider_errors": provider_errors,
            "c_normative_candidate_presence": presence,
            "d_false_positives_on_negative_controls": negatives,
            "e_candidate_count_stability": metric_candidate_count_stability(grouped),
            "f_candidate_span_source_grounding": metric_candidate_span_grounding(attempts),
            "g_material_span_completeness": metric_material_span_completeness(corpus, grouped),
            "h_candidate_span_repeat_stability": metric_candidate_span_repeat_stability(grouped),
            "i_source_standing_invariance": metric_source_standing_invariance(corpus, grouped),
            "j_framing_separation": framing,
            "j2_framing_that_must_not_be_stripped": metric_framing_must_not_be_stripped(
                corpus, grouped
            ),
            "k_multi_unit_separation": metric_multi_unit(corpus, grouped),
            "l_advisory_presence": metric_advisory_candidate_presence(corpus, grouped),
            "m_candidate_span_underreach": underreach,
            "m_prime_candidate_span_overreach": overreach,
        },
        "overreach_versus_underreach": (
            "Opposite defects, counted separately. m_prime records a span reaching beyond "
            "a registered proposition bound; m records a run losing preregistered material "
            "content. A span that sheds framing and also sheds material content is booked "
            "under m and is never scored as a framing-separation success in j."
        ),
        "historical_metric_note": (
            "001, 002 and 003 metric labels retain their original meaning only inside "
            "their own frozen receipts. They are not 004 requirements and 004 does not "
            "reinterpret them."
        ),
        "evidence": _attempt_evidence(attempts),
        "engineering_summary": {
            "total_requests_attempted": len(attempts),
            "boundary_accepted": boundary["boundary_accepted"],
            "boundary_rejected": boundary["boundary_rejected"],
            "provider_errors": provider_errors["provider_errors"],
            "presence_misses": presence["presence_misses"],
            "false_positive_runs": negatives["false_positive_runs"],
            "candidate_spans_examined_for_framing": framing["candidate_spans_examined"],
            "spans_containing_separable_framing": framing["spans_containing_separable_framing"],
            "runs_losing_material_content": underreach["runs_losing_material_content"],
            "candidate_spans_outside_registered_bounds": overreach[
                "candidate_spans_outside_bounds"
            ],
            "note": "Observed counts only; not a verdict.",
        },
    }


def _build_receipt_003(
    *,
    corpus: Corpus,
    attempts: Sequence[Attempt],
    runs_per_specimen: int,
    provider_name: str,
    model: str,
    corpus_integrity: str,
    corpus_freeze_relpath: str,
    integrity_findings: Sequence[str],
    implementation: JsonObject,
) -> JsonObject:
    grouped = group_by_specimen(attempts)
    boundary = metric_boundary_acceptance(attempts)
    provider_errors = metric_provider_errors(attempts)
    presence = metric_normative_presence(corpus, grouped)
    negatives = metric_negative_controls(corpus, grouped)
    return {
        "work_order": WORK_ORDER,
        "metric_contract": "candidate-semantics-003-a-through-m",
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED; engineering observations only.",
        "generated_at": _now(),
        "implementation_git_sha": implementation.get("commit"),
        "implementation_worktree_clean": implementation.get("worktree_clean"),
        "corpus": {
            "corpus_id": corpus.corpus_id,
            "corpus_version": corpus.corpus_version,
            "corpus_relpath": corpus.relpath,
            "corpus_sha256": corpus.sha256,
            "corpus_freeze_relpath": corpus_freeze_relpath,
            "specimen_count": len(corpus.specimens),
            "specimen_ids": [item.specimen_id for item in corpus.specimens],
            "claim_ceiling": corpus.claim_ceiling,
        },
        "engineering_gates": {
            "corpus_integrity": corpus_integrity,
            "corpus_integrity_findings": list(integrity_findings),
            "harness_executed_every_planned_request": len(attempts)
            == len(corpus.specimens) * runs_per_specimen,
            "note": "Mechanical gates only; no semantic or institutional verdict.",
        },
        "run_conditions": {
            "model_provider": provider_name,
            "model": model,
            "runs_per_specimen": runs_per_specimen,
            "total_requests_attempted": len(attempts),
            "statistical_note": "A bounded characterization sample; it certifies nothing.",
        },
        "metrics": {
            "a_boundary_acceptance": boundary,
            "b_provider_errors": provider_errors,
            "c_normative_candidate_presence": presence,
            "d_false_positives_on_negative_controls": negatives,
            "e_candidate_count_stability": metric_candidate_count_stability(grouped),
            "f_candidate_span_source_grounding": metric_candidate_span_grounding(attempts),
            "g_material_span_completeness": metric_material_span_completeness(corpus, grouped),
            "h_candidate_span_repeat_stability": metric_candidate_span_repeat_stability(grouped),
            "i_source_standing_invariance": metric_source_standing_invariance(corpus, grouped),
            "j_paraphrase_family_compatibility": metric_paraphrase_families(corpus, grouped),
            "k_advisory_presence": metric_advisory_candidate_presence(corpus, grouped),
            "l_multi_unit_separation": metric_multi_unit(corpus, grouped),
            "m_candidate_span_overreach": metric_candidate_span_overreach(corpus, grouped),
        },
        "historical_metric_note": (
            "001/002 role metrics retain their original meaning only in their frozen "
            "receipts; they are not current 003 requirements."
        ),
        "evidence": _attempt_evidence(attempts),
        "engineering_summary": {
            "total_requests_attempted": len(attempts),
            "boundary_accepted": boundary["boundary_accepted"],
            "boundary_rejected": boundary["boundary_rejected"],
            "provider_errors": provider_errors["provider_errors"],
            "presence_misses": presence["presence_misses"],
            "false_positive_runs": negatives["false_positive_runs"],
            "note": "Observed counts only; not a verdict.",
        },
    }


def build_receipt(
    *,
    corpus: Corpus,
    attempts: Sequence[Attempt],
    runs_per_specimen: int,
    provider_name: str,
    model: str,
    corpus_integrity: str,
    corpus_freeze_relpath: str,
    integrity_findings: Sequence[str],
    implementation: JsonObject,
) -> JsonObject:
    """Assemble the machine-readable characterization receipt."""
    if corpus.corpus_version == "v0.4":
        return _build_receipt_004(
            corpus=corpus,
            attempts=attempts,
            runs_per_specimen=runs_per_specimen,
            provider_name=provider_name,
            model=model,
            corpus_integrity=corpus_integrity,
            corpus_freeze_relpath=corpus_freeze_relpath,
            integrity_findings=integrity_findings,
            implementation=implementation,
        )
    if corpus.corpus_version == "v0.3":
        return _build_receipt_003(
            corpus=corpus,
            attempts=attempts,
            runs_per_specimen=runs_per_specimen,
            provider_name=provider_name,
            model=model,
            corpus_integrity=corpus_integrity,
            corpus_freeze_relpath=corpus_freeze_relpath,
            integrity_findings=integrity_findings,
            implementation=implementation,
        )
    grouped = group_by_specimen(attempts)
    boundary = metric_boundary_acceptance(attempts)
    presence = metric_normative_presence(corpus, grouped)
    negatives = metric_negative_controls(corpus, grouped)
    actor = metric_unsupported_actor(corpus, grouped)
    conditions = metric_condition_preservation(corpus, grouped)
    qualifiers = metric_material_qualifier_preservation(corpus, grouped)
    advisory = metric_advisory_presence(corpus, grouped)
    targets = metric_target_preservation(corpus, grouped)
    trigger = metric_operative_predicate(corpus, grouped)
    grounding_summary = {
        "actor": actor["candidates_asserting_an_actor"],
        "condition": conditions["candidates_omitting_the_element"],
        "qualifier": qualifiers["candidates_omitting_the_element"],
        "advisory": advisory["presence_misses"],
        "target": targets["candidates_examined"] - targets["candidates_carrying_it_in_target"],
        "trigger": trigger["candidates_recording_the_trigger_as_action"],
    }
    return {
        "work_order": WORK_ORDER,
        "claim_ceiling": CLAIM_CEILING,
        "independent_validation_claim": False,
        "self_adjudication": (
            "This receipt reports engineering observations. It does not adjudicate "
            "semantic, institutional, or legal correctness, and no result here admits, "
            "authorizes, or confers authority on any candidate."
        ),
        "generated_at": _now(),
        "implementation_git_sha": implementation.get("commit"),
        "implementation_worktree_clean": implementation.get("worktree_clean"),
        "corpus": {
            "corpus_id": corpus.corpus_id,
            "corpus_version": corpus.corpus_version,
            "corpus_relpath": corpus.relpath,
            "corpus_sha256": corpus.sha256,
            "corpus_freeze_relpath": corpus_freeze_relpath,
            "specimen_count": len(corpus.specimens),
            "specimen_ids": [specimen.specimen_id for specimen in corpus.specimens],
            "claim_ceiling": corpus.claim_ceiling,
        },
        "engineering_gates": {
            "corpus_integrity": corpus_integrity,
            "corpus_integrity_findings": list(integrity_findings),
            "harness_executed_every_planned_request": len(attempts)
            == len(corpus.specimens) * runs_per_specimen,
            "note": (
                "These are mechanical gates over corpus integrity and harness execution "
                "only. They are deliberately separate from every semantic observation "
                "below and say nothing about extraction quality."
            ),
        },
        "run_conditions": {
            "model_provider": provider_name,
            "model": model,
            "runs_per_specimen": runs_per_specimen,
            "total_requests_attempted": len(attempts),
            "statistical_note": (
                f"{runs_per_specimen} runs per specimen is an initial stability probe. It "
                "is not a statistically sufficient sample and certifies nothing."
            ),
        },
        "metrics": {
            "a_boundary_acceptance": boundary,
            "b_normative_presence": presence,
            "c_negative_controls": negatives,
            "d_candidate_count_stability": metric_candidate_count_stability(grouped),
            "e_unit_type_observation": metric_unit_type_observation(corpus, grouped),
            "f_semantic_decomposition_stability": metric_semantic_stability(grouped),
            "g_source_standing_invariance": metric_source_standing_invariance(corpus, grouped),
            "h_paraphrase_families": metric_paraphrase_families(corpus, grouped),
            "i_threshold_placement": metric_threshold_placement(corpus, grouped),
            "j_multi_unit_behaviour": metric_multi_unit(corpus, grouped),
            "k_unsupported_actor": actor,
            "l_explicit_condition_preservation": conditions,
            "m_material_qualifier_preservation": qualifiers,
            "n_advisory_presence": advisory,
            "o_target_preservation": targets,
            "p_evidence_duty_typing": metric_evidence_duty_typing(corpus, grouped),
            "q_operative_predicate": trigger,
        },
        "measure_classification": {
            "primary": [
                "a_boundary_acceptance",
                "c_negative_controls",
                "d_candidate_count_stability",
                "e_unit_type_observation",
                "g_source_standing_invariance",
                "k_unsupported_actor",
                "l_explicit_condition_preservation",
                "m_material_qualifier_preservation",
                "n_advisory_presence",
                "o_target_preservation",
                "p_evidence_duty_typing",
                "q_operative_predicate",
            ],
            "secondary": [
                "b_normative_presence",
                "f_semantic_decomposition_stability",
                "h_paraphrase_families",
                "i_threshold_placement",
                "j_multi_unit_behaviour",
            ],
            "demoted": {
                "f_semantic_decomposition_stability": (
                    "Demoted from a primary measure by OIC-CANDIDATE-SEMANTICS-002. A "
                    "source-grounded candidate is a literal span of its own fragment, so "
                    "two defensible readings of one fragment legitimately hash "
                    "differently. Canonicalizing them is Institutional IR's job, after "
                    "admission, and is not implemented. The metric is still reported "
                    "because instability is informative; it is not a target."
                ),
                "h_paraphrase_families": (
                    "Exact semantic-hash agreement across materially different phrasings "
                    "is NOT required at the candidate stage and is reported for "
                    "information only. Presence, count and broadly compatible unit types "
                    "are the invariants this stage asks about."
                ),
            },
            "note": (
                "A classification of what this stage is entitled to ask about. No measure "
                "is a gate; the only gates in this receipt are the mechanical ones under "
                "engineering_gates."
            ),
        },
        "evidence": [
            {
                "specimen_id": attempt.specimen_id,
                "run_index": attempt.run_index,
                "boundary_result": attempt.boundary_result,
                "provider": attempt.provider,
                "model": attempt.model,
                "request_id": attempt.request_id,
                "raw_content_sha256": attempt.raw_content_sha256,
                "candidate_count": attempt.candidate_count,
                "candidates": list(attempt.candidates),
                "semantic_projections": list(attempt.semantic_projections),
                "semantic_projection_sha256": attempt.semantic_projection_sha256,
                "unit_types": list(attempt.unit_types),
                "error_type": attempt.error_type,
                "error_message": attempt.error_message,
                "observed_at": attempt.observed_at,
            }
            for attempt in attempts
        ],
        "engineering_summary": {
            "total_requests_attempted": len(attempts),
            "boundary_accepted": boundary["boundary_accepted"],
            "boundary_rejected": boundary["boundary_rejected"],
            "provider_errors": boundary["provider_errors"],
            "positive_control_accepted_runs": presence["accepted_runs"],
            "presence_misses": presence["presence_misses"],
            "negative_control_accepted_runs": negatives["accepted_runs"],
            "false_positive_runs": negatives["false_positive_runs"],
            "candidates_asserting_an_actor_where_source_names_none": grounding_summary["actor"],
            "candidates_omitting_an_explicit_condition": grounding_summary["condition"],
            "candidates_omitting_a_material_qualifier": grounding_summary["qualifier"],
            "advisory_presence_misses": grounding_summary["advisory"],
            "candidates_dropping_an_explicit_target": grounding_summary["target"],
            "candidates_recording_a_trigger_as_the_action": grounding_summary["trigger"],
            "note": (
                "A summary of counts observed on this corpus under these run conditions. "
                "It is not a verdict."
            ),
        },
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="characterize_candidate_semantics.py",
        description=(
            "Characterize OIC candidate extraction on the frozen "
            "OIC-CANDIDATE-SEMANTICS-003 corpus. Requires NVIDIA_API_KEY in the local "
            "environment for live runs; the credential is read by the existing adapter "
            "and is never printed or written to the receipt."
        ),
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--runs-per-specimen", type=int, default=DEFAULT_RUNS_PER_SPECIMEN)
    parser.add_argument("--model", default=DEFAULT_NIM_MODEL)
    parser.add_argument(
        "--allow-corpus-drift",
        action="store_true",
        help=(
            "Proceed despite corpus drift. The receipt is stamped DRIFT_ACKNOWLEDGED and "
            "every finding is recorded. Without this flag, drift stops the run."
        ),
    )
    return parser


def resolve_corpus_integrity(
    corpus: Corpus, freeze_path: Path, *, allow_drift: bool
) -> tuple[str, list[str]]:
    """Compare the corpus against its frozen record and decide whether to proceed."""
    freeze_document: Any = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not isinstance(freeze_document, dict):
        raise CorpusIntegrityError(f"frozen record at {freeze_path} is not a JSON object")
    findings = corpus_freeze_findings(corpus, freeze_document)
    if not findings:
        return CORPUS_INTACT, []
    if not allow_drift:
        raise CorpusIntegrityError(
            "corpus does not match its frozen record; refusing to run.\n  - "
            + "\n  - ".join(findings)
            + "\nRe-freeze deliberately, or pass --allow-corpus-drift to record the drift."
        )
    return CORPUS_DRIFT_ACKNOWLEDGED, findings


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    corpus_path = args.corpus if args.corpus.is_absolute() else root / args.corpus
    freeze_path = args.freeze if args.freeze.is_absolute() else root / args.freeze
    output_path = args.output if args.output.is_absolute() else root / args.output

    try:
        corpus = load_corpus(corpus_path, relpath=args.corpus.as_posix())
        integrity, findings = resolve_corpus_integrity(
            corpus, freeze_path, allow_drift=args.allow_corpus_drift
        )
    except (CharacterizationError, OSError) as exc:
        print(f"FAIL corpus integrity: {exc}")
        return 1

    if findings:
        print("WARNING corpus drift acknowledged; the receipt records every finding:")
        for finding in findings:
            print(f"  - {finding}")

    provider = NvidiaNimProvider(NvidiaNimConfig(model=args.model))
    print(
        f"Characterizing {len(corpus.specimens)} specimens x {args.runs_per_specimen} runs "
        f"against {args.model} via {provider.provider_name}."
    )
    attempts = run_corpus(corpus, provider=provider, runs_per_specimen=args.runs_per_specimen)
    receipt = build_receipt(
        corpus=corpus,
        attempts=attempts,
        runs_per_specimen=args.runs_per_specimen,
        provider_name=provider.provider_name,
        model=args.model,
        corpus_integrity=integrity,
        corpus_freeze_relpath=args.freeze.as_posix(),
        integrity_findings=findings,
        implementation=implementation_git_sha(root),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(receipt))
    summary = receipt["engineering_summary"]
    print(f"Receipt written to {output_path}")
    print(
        "OBSERVED  attempted={attempted}  accepted={accepted}  rejected={rejected}  "
        "provider_errors={errors}  presence_misses={misses}  "
        "false_positive_runs={positives}".format(
            attempted=summary["total_requests_attempted"],
            accepted=summary["boundary_accepted"],
            rejected=summary["boundary_rejected"],
            errors=summary["provider_errors"],
            misses=summary["presence_misses"],
            positives=summary["false_positive_runs"],
        )
    )
    if corpus.corpus_version != "v0.3":
        print(
            "HISTORICAL GROUNDING metrics retained under their original receipt version; "
            "they are not 003 candidate requirements."
        )
    print(
        "This is characterization, not adjudication. No result here establishes semantic "
        "correctness, admission, authority, or readiness."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
