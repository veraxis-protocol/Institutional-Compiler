"""A bank of admission probes: exact bytes paired with the outcome they must produce.

The probes are data, not assertions, so the same bank can be run against the real
evaluator and against a deliberately broken copy of it. That is what makes the mutation
suite meaningful: a mutant is killed by the properties this bank actually states, and a
survivor names a property nothing states.

Each probe is one single-fact edit of a frozen vector. `expected_state` of ``None`` means
the bytes must be refused at the input boundary — not evaluated into a terminal state.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from oic.admission import canonical_json, digest_of

_ROOT = Path(__file__).resolve().parents[2]
_CORPUS: dict[str, Any] = json.loads(
    (_ROOT / "design/admission-boundary-001/TEST-VECTORS-v0.2.json").read_text(encoding="utf-8")
)
_INPUTS: dict[str, dict[str, Any]] = {
    str(vector["vector_id"]): vector["executable_input"] for vector in _CORPUS["vectors"]
}

BOUNDARY = None
OTHER_DIGEST = "sha256:" + "0" * 64


@dataclass(frozen=True)
class Probe:
    """One exact payload and the outcome the contract requires for it."""

    name: str
    payload: bytes
    expected_state: str | None


def _base(vector_id: str = "ADM-001") -> dict[str, Any]:
    return copy.deepcopy(_INPUTS[vector_id])


def _seal(document: dict[str, Any]) -> bytes:
    """Recompute evidence digests and canonical order, as an evidence custodian would."""
    for item in document["authority_evidence"]:
        item.pop("evidence_digest", None)
        item["evidence_digest"] = digest_of(canonical_json(item))
    document["authority_evidence"].sort(
        key=lambda item: (item["evidence_id"], item["evidence_digest"])
    )
    return canonical_json(document)


def _edit(name: str, expected: str | None, change: Callable[[dict[str, Any]], None]) -> Probe:
    document = _base()
    change(document)
    return Probe(name=name, payload=_seal(document), expected_state=expected)


def _raw(name: str, expected: str | None, payload: bytes) -> Probe:
    return Probe(name=name, payload=payload, expected_state=expected)


def _registry(document: dict[str, Any]) -> dict[str, Any]:
    observation: dict[str, Any] = document["source_registration"]["registry_observation"]
    return observation


def _warrant(document: dict[str, Any], index: int = 0) -> dict[str, Any]:
    warrant: dict[str, Any] = document["authority_evidence"][index]["admission_warrant"]
    return warrant


def _unavailable_and_stale(document: dict[str, Any]) -> None:
    """Both conditions at once: precedence, not merely reachability, is under test."""
    _registry(document)["availability"] = "UNAVAILABLE"
    _registry(document)["freshness"] = "STALE"


def _registration_scope_narrower_than_the_evidence(document: dict[str, Any]) -> None:
    """The registration does not cover the request even though the evidence would."""
    evidence = document["authority_evidence"][0]
    evidence["applicability_scope"] = ["records", "wider"]
    _warrant(document)["applicability_scope"] = ["records", "wider"]
    document["evaluation_scope"]["applicability"] = "wider"


def _effective_exactly_now(document: dict[str, Any]) -> None:
    at = document["evaluation_time"]
    document["source_registration"]["effective_from"] = at
    document["authority_evidence"][0]["effective_from"] = at
    _warrant(document)["effective_from"] = at


def _warrant_revoked_without_a_timestamp(document: dict[str, Any]) -> None:
    _warrant(document)["status"] = "REVOKED"


def _evidence_and_warrant_version_differ(document: dict[str, Any]) -> None:
    document["authority_evidence"][0]["source_version"] = "other"
    _warrant(document)["source_version"] = "other"


def _evidence_and_warrant_digest_differ(document: dict[str, Any]) -> None:
    document["authority_evidence"][0]["source_digest"] = OTHER_DIGEST
    _warrant(document)["source_digest"] = OTHER_DIGEST


def _rival_authority(document: dict[str, Any]) -> None:
    rival = copy.deepcopy(document["authority_evidence"][0])
    rival["evidence_id"] = "AE-001-RIVAL"
    rival["authority_basis_ref"] = "charter:a-rival-basis"
    rival["admission_warrant"]["warrant_id"] = "AW-001-RIVAL"
    document["authority_evidence"].append(rival)


def _build_probes() -> tuple[Probe, ...]:
    admitted = canonical_json(_base())
    tampered = _base()
    tampered["authority_evidence"][0]["issuer_id"] = "a-different-issuer"
    forged_ruleset = _base()
    forged_ruleset["ruleset"]["ruleset_digest"] = OTHER_DIGEST

    return (
        # The control. Everything else is a departure from this one input.
        _raw("admitted_control", "ADMITTED", admitted),
        # Candidate reference.
        _edit(
            "no_source_anchor",
            "CANDIDATE_INPUT_INVALID",
            lambda d: d["candidate"].__setitem__("source_anchors", []),
        ),
        _edit(
            "anchor_names_a_different_source",
            "CANDIDATE_INPUT_INVALID",
            lambda d: d["candidate"]["source_anchors"][0].__setitem__("source_id", "elsewhere"),
        ),
        # Registry observation, including its precedence over everything below it.
        _edit(
            "registry_unavailable",
            "AUTHORITY_REGISTRY_UNAVAILABLE",
            lambda d: _registry(d).__setitem__("availability", "UNAVAILABLE"),
        ),
        _edit(
            "registry_unavailable_outranks_stale",
            "AUTHORITY_REGISTRY_UNAVAILABLE",
            _unavailable_and_stale,
        ),
        _edit(
            "evidence_stale",
            "AUTHORITY_EVIDENCE_STALE",
            lambda d: _registry(d).__setitem__("freshness", "STALE"),
        ),
        # Registration, version, and digest binding.
        _edit(
            "unregistered_source",
            "SOURCE_NOT_REGISTERED",
            lambda d: d["source_registration"].__setitem__("registered", False),
        ),
        _edit(
            "unregistered_source_with_evidence_present",
            "SOURCE_NOT_REGISTERED",
            lambda d: d["source_registration"].__setitem__("registered", False),
        ),
        _edit(
            "no_evidence_binds_the_registered_version",
            "SOURCE_VERSION_MISMATCH",
            _evidence_and_warrant_version_differ,
        ),
        _edit(
            "anchor_bytes_differ_from_the_registered_digest",
            "SOURCE_DIGEST_MISMATCH",
            lambda d: d["candidate"]["source_anchors"][0].__setitem__("content_hash", OTHER_DIGEST),
        ),
        _edit(
            "no_evidence_binds_the_registered_digest",
            "SOURCE_DIGEST_MISMATCH",
            _evidence_and_warrant_digest_differ,
        ),
        # Authority sufficiency and scope.
        _edit(
            "no_authority_evidence_at_all",
            "MISSING_AUTHORITY_EVIDENCE",
            lambda d: d.__setitem__("authority_evidence", []),
        ),
        _edit(
            "requested_applicability_outside_the_warrant",
            "OUT_OF_SCOPE",
            lambda d: d["evaluation_scope"].__setitem__("applicability", "elsewhere"),
        ),
        _edit(
            "requested_jurisdiction_outside_the_warrant",
            "OUT_OF_SCOPE",
            lambda d: d["evaluation_scope"].__setitem__("jurisdiction", "elsewhere"),
        ),
        _edit(
            "registration_scope_narrower_than_the_evidence",
            "OUT_OF_SCOPE",
            _registration_scope_narrower_than_the_evidence,
        ),
        # Temporal lifecycle, at and around the frozen half-open boundaries.
        _edit(
            "evaluation_time_precedes_effectiveness",
            "NOT_YET_EFFECTIVE",
            lambda d: d.__setitem__("evaluation_time", "2025-06-01T00:00:00Z"),
        ),
        _edit("effective_at_exactly_the_evaluation_instant", "ADMITTED", _effective_exactly_now),
        _edit(
            "effective_until_equals_the_evaluation_instant",
            "EXPIRED",
            lambda d: d["source_registration"].__setitem__("effective_until", d["evaluation_time"]),
        ),
        _edit(
            "superseded_at_equals_the_evaluation_instant",
            "SUPERSEDED",
            lambda d: d["source_registration"].__setitem__("superseded_at", d["evaluation_time"]),
        ),
        _edit(
            "revoked_at_equals_the_evaluation_instant",
            "REVOKED",
            lambda d: d["source_registration"].__setitem__("revoked_at", d["evaluation_time"]),
        ),
        _edit(
            "warrant_revoked_without_a_revocation_timestamp",
            "REVOKED",
            _warrant_revoked_without_a_timestamp,
        ),
        # Conflict and the generic fail-safe.
        _edit("two_operative_authority_bases", "CONFLICTING_AUTHORITY", _rival_authority),
        _edit(
            "suspended_warrant",
            "ADMISSION_NOT_ESTABLISHED",
            lambda d: _warrant(d).__setitem__("status", "SUSPENDED"),
        ),
        # The byte boundary. None of these may become a terminal state.
        _raw("trailing_newline", BOUNDARY, admitted + b"\n"),
        _raw("leading_whitespace", BOUNDARY, b" " + admitted),
        _raw("byte_order_mark", BOUNDARY, b"\xef\xbb\xbf" + admitted),
        _raw("not_utf8", BOUNDARY, b'{"a"\xff:1}'),
        _raw(
            "pretty_printed",
            BOUNDARY,
            json.dumps(_base(), sort_keys=True, indent=2).encode("utf-8"),
        ),
        _raw(
            "unsorted_keys",
            BOUNDARY,
            json.dumps(_base(), sort_keys=False, separators=(",", ":")).encode("utf-8"),
        ),
        _raw(
            "duplicate_object_key",
            BOUNDARY,
            b'{"evaluation_time":"2026-06-01T00:00:00Z",' + admitted[1:],
        ),
        _raw("tampered_evidence_body", BOUNDARY, canonical_json(tampered)),
        _raw("caller_selected_ruleset_digest", BOUNDARY, canonical_json(forged_ruleset)),
        _raw(
            "evidence_out_of_canonical_order",
            BOUNDARY,
            canonical_json(
                {
                    **_base("ADM-017"),
                    "authority_evidence": list(reversed(_base("ADM-017")["authority_evidence"])),
                }
            ),
        ),
    )


PROBES: tuple[Probe, ...] = _build_probes()


def run_probes(module: ModuleType) -> list[str]:
    """Return the names of probes ``module`` gets wrong. Empty means it satisfies them all."""
    boundary_error = module.AdmissionInputBoundaryError
    evaluate = module.evaluate_admission_bytes
    failures: list[str] = []
    for probe in PROBES:
        try:
            receipt = evaluate(probe.payload)
        except boundary_error:
            if probe.expected_state is not None:
                failures.append(probe.name)
            continue
        except Exception:  # any other failure is also a wrong answer
            failures.append(probe.name)
            continue
        if probe.expected_state is None or receipt.admission_state.value != probe.expected_state:
            failures.append(probe.name)
    return failures
