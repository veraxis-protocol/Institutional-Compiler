#!/usr/bin/env python3
"""Characterize OIC candidate-extraction behaviour on a frozen synthetic corpus.

Work order: OIC-CANDIDATE-SEMANTICS-001 (pre-admission characterization).

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

WORK_ORDER = "OIC-CANDIDATE-SEMANTICS-001"

CLAIM_CEILING = (
    "Candidate extraction behavior has been characterized on the frozen "
    "OIC-CANDIDATE-SEMANTICS-001 synthetic corpus under the identified implementation "
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

CORPUS_INTACT = "INTACT"
CORPUS_DRIFT_ACKNOWLEDGED = "DRIFT_ACKNOWLEDGED"

#: Model-proposed semantic fields. The projection is exactly these, in this order.
SEMANTIC_FIELDS = (
    "unit_type",
    "actor",
    "action",
    "object",
    "conditions",
    "exceptions",
    "evidence_requirements",
)
#: Deterministic fields OIC controls. Excluded from every semantic projection, because a
#: projection carrying unit_id or source_anchors would measure OIC's determinism rather
#: than the model's stability.
OIC_CONTROLLED_FIELDS = (
    "unit_id",
    "interpretation_state",
    "epistemic_state",
    "source_anchors",
)

DEFAULT_CORPUS = Path("benchmarks/characterization/candidate-semantics-001/CORPUS-v0.1.json")
DEFAULT_FREEZE = Path("benchmarks/characterization/candidate-semantics-001/CORPUS-FREEZE-v0.1.json")
DEFAULT_OUTPUT = Path(".local/candidate-semantics-receipts/OIC-CANDIDATE-SEMANTICS-001.json")
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
    """Model-proposed fields only. OIC-controlled identity, state and anchors are dropped."""
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
        "note": (
            "The fixture states the test intent that these phrasings are equivalent. It "
            "does not establish that they are, and agreement here is not correctness."
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
    grouped = group_by_specimen(attempts)
    boundary = metric_boundary_acceptance(attempts)
    presence = metric_normative_presence(corpus, grouped)
    negatives = metric_negative_controls(corpus, grouped)
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
            "OIC-CANDIDATE-SEMANTICS-001 corpus. Requires NVIDIA_API_KEY in the local "
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
    print(
        "This is characterization, not adjudication. No result here establishes semantic "
        "correctness, admission, authority, or readiness."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
