"""Test-only validator for the semantic conformance rules.

**This is not runtime implementation and must never move into ``src/oic``.** It exists so
the rules declared in ``docs/contracts/ZTL-OCE-MAPPING-v0.1.json`` under
``semantic_conformance_rules`` are executable against the fixtures rather than only
readable. A rule nobody can run is a comment.

Why it is separate from the schemas
-----------------------------------
JSON Schema enforces structure, enums, nullability, local conditionals, and cross-field
constraints it can represent. It cannot express equality between two sibling arrays,
canonical ordering, binding across artifacts, or anything derived from the evaluated
marking. Those six rules live here. **A record passing the schema but failing one of these
is invalid**; structural validation alone is not conformance.

What SC-WA-002 does
-------------------
It **recomputes** both digests and compares them, rather than checking that the fields are
present. `formula_hash` is re-derived by SHA-384 over the UTF-8 bytes of the kernel-rendered
formula, and `output_hash` by SHA-256 over the declared five-field projection. A record
carrying a well-formed but wrong digest is rejected.

Scope
-----
Reads artifacts and returns findings. It calls nothing, evaluates no policy, and makes no
decision. When an adapter is eventually authorised, these rules become part of its
acceptance suite — they do not become part of it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "CANONICAL_TRIGGERS",
    "Finding",
    "check_runtime_decision",
    "check_warrant_artifact",
    "expected_formula_hash",
    "expected_output_hash",
]

#: Declared canonical order. Not merely "these five" — this order.
CANONICAL_TRIGGERS: tuple[str, ...] = (
    "ground_corrected",
    "ground_expired",
    "ground_revoked",
    "ground_verified",
    "relevant_epoch_changed",
)

_ZTL_PROFILE = "ztl-v0.1"

#: Fields the output projection includes. Everything else is excluded on purpose:
#: `why` is presentational, `marking` is input, and the OIC-enriched fields
#: (dependency_ids, generated_at, anchors, admissions) are not kernel output at all.
_OUTPUT_PROJECTION_FIELDS = (
    "kernel_rendered_formula",
    "disposition",
    "raw_verdict",
    "warranty_grade",
    "unverified_ground_ids",
)


def expected_formula_hash(rendered_formula: str) -> str:
    """SHA-384 over the UTF-8 bytes of the KERNEL-RENDERED formula.

    Not the caller's string. `(p \u2228 q)` and `p | q` are the same proposition and must
    not be the same digest input, or two callers who wrote it differently would disagree.
    """
    return "sha384:" + hashlib.sha384(rendered_formula.encode("utf-8")).hexdigest()


def expected_output_hash(warrant: dict[str, Any]) -> str:
    """SHA-256 over the declared semantic output projection.

    Serialised UTF-8, sorted keys, compact separators, no ASCII escaping, no whitespace.
    """
    projection = {
        "kernel_rendered_formula": warrant["formula"],
        "disposition": warrant["disposition"],
        "raw_verdict": warrant["raw_verdict"],
        "warranty_grade": warrant["warranty_grade"],
        "unverified_ground_ids": list(warrant["unverified_ground_ids"]),
    }
    assert set(projection) == set(_OUTPUT_PROJECTION_FIELDS)
    payload = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class Finding:
    """One semantic conformance violation."""

    rule_id: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule_id}: {self.detail}"


def check_runtime_decision(
    decision: dict[str, Any],
    *,
    expected_reason_codes: frozenset[str] | None = None,
    expected_applied_overlay_ids: list[str] | None = None,
) -> list[Finding]:
    """Apply SC-RD-001 to SC-RD-005.

    ``expected_reason_codes`` supplies the completeness half of SC-RD-004: the codes the
    mapping says this decision's matched stages must contribute -- the classification row's
    primary code **always**, plus every applied rule's policy code. Omit it to check only
    the uniqueness and ordering halves.

    ``expected_applied_overlay_ids`` supplies SC-RD-005: the overlays derivable from the
    envelope and kernel result. When given, the recorded list must equal it exactly,
    including order.
    """
    findings: list[Finding] = []
    conditional_allow = (
        decision.get("epistemic_status") == "CONDITIONALLY_SUPPORTED"
        and decision.get("execution_disposition") == "ALLOW"
    )

    # --- SC-RD-001 subscription ground coverage ---
    if conditional_allow:
        covered = decision.get("conditional_support_subscription_ground_ids")
        missing = decision.get("missing_ground_ids")
        if covered != missing:
            findings.append(
                Finding(
                    "SC-RD-001",
                    f"subscription covers {covered!r} but missing_ground_ids is {missing!r}; "
                    "they must be equal including order",
                )
            )

    # --- SC-RD-002 subscription trigger set ---
    if conditional_allow:
        triggers = tuple(decision.get("conditional_support_subscription_triggers") or ())
        if triggers != CANONICAL_TRIGGERS:
            findings.append(
                Finding(
                    "SC-RD-002",
                    f"triggers are {list(triggers)!r}; the canonical set and order is "
                    f"{list(CANONICAL_TRIGGERS)!r}",
                )
            )

    # --- SC-RD-003 overlay order ---
    applied = list(decision.get("applied_control_overlay_ids") or ())
    if len(applied) != len(set(applied)):
        findings.append(Finding("SC-RD-003", f"duplicate overlay identifier in {applied!r}"))
    if "DM-1" in applied:
        findings.append(Finding("SC-RD-003", "DM-1 is the identity overlay and is never recorded"))
    stages = ["WP" if identifier.startswith("WP-") else "DM" for identifier in applied]
    if stages != sorted(stages, key=lambda stage: 0 if stage == "WP" else 1):
        findings.append(
            Finding("SC-RD-003", f"stage-2 WP identifiers must precede stage-3 DM: {applied!r}")
        )
    if stages.count("DM") > 1:
        findings.append(
            Finding("SC-RD-003", f"at most one decision-mode overlay may apply: {applied!r}")
        )

    # --- SC-RD-004 reason-code canonicalisation ---
    codes = list(decision.get("reason_codes") or ())
    if len(codes) != len(set(codes)):
        findings.append(Finding("SC-RD-004", f"duplicate reason code in {codes!r}"))
    if codes != sorted(codes):
        findings.append(Finding("SC-RD-004", f"reason codes are not sorted: {codes!r}"))
    if expected_reason_codes is not None:
        absent = expected_reason_codes - set(codes)
        if absent:
            findings.append(
                Finding(
                    "SC-RD-004",
                    f"incomplete: matched stages require {sorted(absent)}, absent from {codes!r}",
                )
            )

    # --- SC-RD-005 overlay completeness ---
    if expected_applied_overlay_ids is not None and applied != expected_applied_overlay_ids:
        findings.append(
            Finding(
                "SC-RD-005",
                f"applied overlays are {applied!r}; the envelope and kernel result derive "
                f"{expected_applied_overlay_ids!r}",
            )
        )

    return findings


def check_warrant_artifact(
    warrant: dict[str, Any],
    *,
    marking: dict[str, str] | None = None,
    rendered_formula: str | None = None,
) -> list[Finding]:
    """Apply SC-WA-001 and SC-WA-002.

    ``marking`` is the kernel-echoed atom map, which is the only ground truth for the
    partition: OIC does not parse the formula.
    """
    findings: list[Finding] = []
    if warrant.get("kernel_profile_id") != _ZTL_PROFILE:
        return findings

    dependencies = list(warrant.get("dependency_ids") or ())
    unverified = list(warrant.get("unverified_ground_ids") or ())

    # --- SC-WA-001 ground partition ---
    for name, values in (("dependency_ids", dependencies), ("unverified_ground_ids", unverified)):
        if len(values) != len(set(values)):
            findings.append(Finding("SC-WA-001", f"duplicate identifier in {name}: {values!r}"))
    overlap = set(dependencies) & set(unverified)
    if overlap:
        findings.append(
            Finding(
                "SC-WA-001", f"dependency_ids and unverified_ground_ids overlap: {sorted(overlap)}"
            )
        )
    if marking is not None:
        verified_atoms = {atom for atom, value in marking.items() if value in {"T", "F"}}
        unverified_atoms = {atom for atom, value in marking.items() if value == "Z"}
        if set(dependencies) != verified_atoms:
            findings.append(
                Finding(
                    "SC-WA-001",
                    f"dependency_ids {sorted(dependencies)} are not exactly the T/F atoms "
                    f"{sorted(verified_atoms)}",
                )
            )
        if set(unverified) != unverified_atoms:
            findings.append(
                Finding(
                    "SC-WA-001",
                    f"unverified_ground_ids {sorted(unverified)} are not exactly the Z atoms "
                    f"{sorted(unverified_atoms)}",
                )
            )
        uncovered = set(marking) - set(dependencies) - set(unverified)
        if uncovered:
            findings.append(
                Finding(
                    "SC-WA-001",
                    f"formula atoms in neither array: {sorted(uncovered)}; such a ground "
                    "cannot trigger recomputation and cannot be revoked",
                )
            )

    # --- SC-WA-002 hash projections, RECOMPUTED ---
    for field in ("formula", "formula_hash", "output_hash"):
        if not warrant.get(field):
            findings.append(Finding("SC-WA-002", f"{field} is absent"))
            return findings

    if rendered_formula is not None and warrant["formula"] != rendered_formula:
        findings.append(
            Finding(
                "SC-WA-002",
                f"formula is {warrant['formula']!r}, not the kernel rendering {rendered_formula!r}",
            )
        )

    wanted_formula_hash = expected_formula_hash(warrant["formula"])
    if warrant["formula_hash"] != wanted_formula_hash:
        findings.append(
            Finding(
                "SC-WA-002",
                f"formula_hash is {warrant['formula_hash']}, recomputes to "
                f"{wanted_formula_hash} over the kernel-rendered formula "
                f"{warrant['formula']!r}",
            )
        )

    wanted_output_hash = expected_output_hash(warrant)
    if warrant["output_hash"] != wanted_output_hash:
        findings.append(
            Finding(
                "SC-WA-002",
                f"output_hash is {warrant['output_hash']}, recomputes to "
                f"{wanted_output_hash} over the declared projection "
                f"{list(_OUTPUT_PROJECTION_FIELDS)}",
            )
        )

    return findings
