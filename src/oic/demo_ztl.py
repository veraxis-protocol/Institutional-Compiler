"""Warrant construction for the bounded demonstration lane.

This module is the OIC side of the ZTL boundary. It calls the pinned bridge,
takes the kernel result exactly as given, and builds a WarrantArtifact under the
repository's **proposed** warrant contract.

Scope of that use
-----------------
The proposed contract is used here for this demonstration lane only. Nothing in
this file admits it globally: it remains PROPOSED / NOT ADMITTED, and no schema
under ``schemas/proposed/`` is modified.

What a warrant is and is not
----------------------------
A warrant records what a *logic kernel* concluded about a formula under a
marking. It is not an institutional authorization, it does not establish source
authenticity, it does not determine currentness, and it performs no admission.
The kernel has no clock, no authority model and no notion of an institution;
every one of those lives on the OIC side and is bound to the warrant by
identifier, never inferred from it.

The mapping
-----------
    EARNED     -> ESTABLISHED
    ON CREDIT  -> CONDITIONALLY_SUPPORTED
    OPEN       -> UNRESOLVED
    REFUTED    -> REFUTED

Two transitions are prohibited outright and are checked rather than trusted:
``OPEN`` never becomes ``REFUTED`` (not established is not falsified), and
``ON CREDIT`` never becomes ``ESTABLISHED`` (a claim riding an unverified link is
not grounded). Both prohibitions are stated as data below so a test can assert
them without re-deriving the mapping.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from oic.errors import OICError

__all__ = [
    "BRIDGE_PATH",
    "CANONICALIZATION_PROFILE_ID",
    "DISPOSITION_TO_EPISTEMIC",
    "KERNEL_COMMIT",
    "KERNEL_NAME",
    "KERNEL_PROFILE_ID",
    "KERNEL_VERSION",
    "PERMITTED_DISPOSITION_GRADES",
    "PROHIBITED_TRANSITIONS",
    "BindingFinding",
    "KernelResult",
    "WarrantError",
    "build_warrant",
    "epistemic_status_for",
    "expected_formula_hash",
    "expected_output_hash",
    "invoke_kernel",
    "resolve_ztl_path",
    "validate_warrant_binding",
]

KERNEL_PROFILE_ID: Final = "ztl-v0.1"
CANONICALIZATION_PROFILE_ID: Final = "ztl-jcs-float-free-sha384-v0.1"
KERNEL_NAME: Final = "ztl"
KERNEL_VERSION: Final = "0.1"
KERNEL_COMMIT: Final = "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"

#: Where the one authorized bridge lives, relative to the repository root.
BRIDGE_PATH: Final = "adapters/ztl/demo_bridge.py"

#: Environment variable naming a local ZTL checkout. There is no default and no
#: bundled copy: the kernel is external, and pretending otherwise would make the
#: pin check meaningless.
ZTL_PATH_ENV: Final = "OIC_DEMO_ZTL_PATH"

DISPOSITION_TO_EPISTEMIC: Final[dict[str, str]] = {
    "EARNED": "ESTABLISHED",
    "ON CREDIT": "CONDITIONALLY_SUPPORTED",
    "OPEN": "UNRESOLVED",
    "REFUTED": "REFUTED",
}

#: Stated as data so the prohibition is testable, not merely documented.
PROHIBITED_TRANSITIONS: Final[tuple[tuple[str, str], ...]] = (
    ("OPEN", "REFUTED"),
    ("ON CREDIT", "ESTABLISHED"),
)


class WarrantError(OICError):
    """The kernel boundary refused, or a warrant could not be built honestly."""


def resolve_ztl_path(
    explicit: Path | None = None, *, environ: dict[str, str] | None = None
) -> Path:
    """Locate the external ZTL checkout, or refuse to guess."""
    import os

    if explicit is not None:
        return explicit
    env = os.environ if environ is None else environ
    value = env.get(ZTL_PATH_ENV)
    if not value:
        raise WarrantError(
            f"no ZTL checkout supplied; set {ZTL_PATH_ENV} to a checkout at {KERNEL_COMMIT}"
        )
    return Path(value)


def expected_formula_hash(rendered_formula: str) -> str:
    """SHA-384 over the UTF-8 bytes of the KERNEL-RENDERED formula.

    The caller's string is deliberately not hashed: ``p | q`` and ``(p \u2228 q)``
    are the same proposition, and two callers who wrote it differently must not
    disagree about its identity.
    """
    return "sha384:" + hashlib.sha384(rendered_formula.encode("utf-8")).hexdigest()


def expected_output_hash(
    *,
    rendered_formula: str,
    disposition: str,
    raw_verdict: str,
    warranty_grade: str,
    unverified_ground_ids: list[str],
) -> str:
    """SHA-256 over the declared five-field semantic output projection.

    ``why`` and ``marking`` are excluded: the first is presentational and may
    change without a profile bump, the second is input rather than output.
    """
    projection = {
        "kernel_rendered_formula": rendered_formula,
        "disposition": disposition,
        "raw_verdict": raw_verdict,
        "warranty_grade": warranty_grade,
        "unverified_ground_ids": list(unverified_ground_ids),
    }
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _input_hash(formula: str, marking: dict[str, str]) -> str:
    payload = json.dumps(
        {"formula": formula, "marking": marking},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class KernelResult:
    """One kernel invocation, carried without institutional interpretation.

    ``raw_verdict`` is operationally inert. It is retained so a third party can
    replay the invocation, and it is never mapped onto an execution disposition:
    ``T`` is not ALLOW and ``F`` is not BLOCK.
    """

    rendered_formula: str
    disposition: str
    raw_verdict: str
    warranty_grade: str
    unverified: tuple[str, ...]
    marking: dict[str, str]
    caller_formula: str
    kernel_commit: str

    @property
    def dependency_ids(self) -> tuple[str, ...]:
        """Every VERIFIED atom (marked T or F) of the evaluated formula.

        Deliberately an over-approximation: minimality is not claimed, because a
        redundant ground that stays load-bearing is safer than a dropped one that
        silently stops triggering recomputation.
        """
        return tuple(sorted(atom for atom, mark in self.marking.items() if mark in {"T", "F"}))


def invoke_kernel(
    *,
    formula: str,
    marking: dict[str, str],
    repo_root: Path,
    ztl_path: Path,
) -> KernelResult:
    """Call ``ztljudge.judge`` once, through the one authorized bridge.

    The bridge runs in its own process. That keeps the kernel's ``sys.path`` and
    imports out of this one, and makes the boundary something you can watch
    rather than something you have to trust.
    """
    bridge = repo_root / BRIDGE_PATH
    if not bridge.is_file():
        raise WarrantError(f"the authorized ZTL bridge is missing: {bridge}")
    request = json.dumps({"formula": formula, "marking": marking}, sort_keys=True)
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, in-repo script
            [sys.executable, str(bridge), "--ztl", str(ztl_path)],
            input=request,
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise WarrantError(f"the ZTL bridge could not be run: {error}") from error

    try:
        response: dict[str, Any] = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise WarrantError(
            f"the ZTL bridge returned no JSON (exit {completed.returncode}): "
            f"{completed.stderr.strip()}"
        ) from error

    if not response.get("ok"):
        raise WarrantError(
            f"the ZTL bridge refused: [{response.get('error_code')}] {response.get('error')}"
        )
    if response.get("entrypoint") != "ztljudge.judge":
        raise WarrantError(f"unexpected kernel entrypoint: {response.get('entrypoint')!r}")

    result = response["result"]
    return KernelResult(
        rendered_formula=str(result["formula"]),
        disposition=str(result["disposition"]),
        raw_verdict=str(result["verdict"]),
        warranty_grade=str(result["grade"]),
        unverified=tuple(str(atom) for atom in result["unverified"]),
        marking={str(k): str(v) for k, v in result["marking"].items()},
        caller_formula=formula,
        kernel_commit=str(response["kernel_commit"]),
    )


def epistemic_status_for(disposition: str) -> str:
    """Apply the frozen mapping, refusing anything outside the kernel vocabulary."""
    try:
        return DISPOSITION_TO_EPISTEMIC[disposition]
    except KeyError as error:
        raise WarrantError(f"disposition outside the kernel vocabulary: {disposition!r}") from error


def build_warrant(
    result: KernelResult,
    *,
    warrant_artifact_id: str,
    claim_id: str,
    ground_epoch: dict[str, Any],
    ground_set_hash: str,
    source_anchor_ids: list[str],
    admission_ids: list[str],
    generated_at: str,
    valid_from: str,
    valid_until: str | None,
    revocation_references: list[str],
) -> dict[str, Any]:
    """Build a WarrantArtifact under the proposed contract, for this lane only.

    Every field is either kernel output carried verbatim or an OIC-side identity
    the kernel could not have supplied. Nothing is invented in between.
    """
    epistemic = epistemic_status_for(result.disposition)
    if (result.disposition, epistemic) in PROHIBITED_TRANSITIONS:
        raise WarrantError(f"prohibited disposition transition {result.disposition} -> {epistemic}")

    unverified = list(result.unverified)
    return {
        "warrant_artifact_id": warrant_artifact_id,
        "schema_version": "0.1.0",
        "claim_id": claim_id,
        "kernel_profile_id": KERNEL_PROFILE_ID,
        "canonicalization_profile_id": CANONICALIZATION_PROFILE_ID,
        "formula": result.rendered_formula,
        "formula_hash": expected_formula_hash(result.rendered_formula),
        "disposition": result.disposition,
        # Retained for replay and operationally inert. Read `disposition`.
        "raw_verdict": result.raw_verdict,
        "warranty_grade": result.warranty_grade,
        "unverified_ground_ids": unverified,
        "dependency_ids": [atom for atom in result.dependency_ids if atom not in set(unverified)],
        "ground_epoch": ground_epoch,
        "ground_set_hash": ground_set_hash,
        "source_anchor_ids": source_anchor_ids,
        "admission_ids": admission_ids,
        "kernel_name": KERNEL_NAME,
        "kernel_version": KERNEL_VERSION,
        "kernel_commit": result.kernel_commit,
        "input_hash": _input_hash(result.caller_formula, result.marking),
        "output_hash": expected_output_hash(
            rendered_formula=result.rendered_formula,
            disposition=result.disposition,
            raw_verdict=result.raw_verdict,
            warranty_grade=result.warranty_grade,
            unverified_ground_ids=unverified,
        ),
        "generated_at": generated_at,
        "time_binding": {
            "source": "oic_system_clock",
            "reference": "oic-demo-declared-logical-time",
            # Null on purpose: an unattested clock is a stated weakness, not a
            # hidden one.
            "attestation_hash": None,
        },
        "valid_from": valid_from,
        "valid_until": valid_until,
        "revocation_references": revocation_references,
        "recomputation_reference": (
            f"ztl@{result.kernel_commit} judge("
            f"input_hash={_input_hash(result.caller_formula, result.marking)})"
        ),
        "limitations": [
            "Bounded synthetic demonstration lane. Not a general legal-language result.",
            "The proposed warrant contract is used for this lane only and remains "
            "PROPOSED / NOT ADMITTED globally.",
            "A logical warrant is not an institutional warrant: it establishes no "
            "authority, no currentness, no admission and no authenticity.",
            "raw_verdict is retained for replay and is operationally inert.",
        ],
    }


# ---------------------------------------------------------------------------
# Runtime warrant-binding validation
# ---------------------------------------------------------------------------

#: Disposition/grade pairs the pinned profile declares reachable. EARNED requires
#: hereditary by construction; a T verdict that is only sound is ON CREDIT. A pair
#: outside this table is not a stricter result, it is an impossible one.
PERMITTED_DISPOSITION_GRADES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("EARNED", "hereditary"),
        ("REFUTED", "hereditary"),
        ("ON CREDIT", "sound"),
        ("ON CREDIT", "until-verification"),
        ("OPEN", "hereditary"),
        ("OPEN", "sound"),
        ("OPEN", "until-verification"),
    }
)


@dataclass(frozen=True, slots=True)
class BindingFinding:
    """One reason a warrant is not usable against this runtime binding."""

    rule_id: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule_id}: {self.detail}"


def validate_warrant_binding(
    warrant: Mapping[str, Any],
    *,
    runtime_binding: Mapping[str, Any],
    control_envelope: Mapping[str, Any],
    envelope_digest: str,
    source_version_set_hash: str,
    admission_version: str,
    ground_set_hash: str,
    evaluated_at: str,
    schema: Mapping[str, Any],
) -> list[BindingFinding]:
    """Re-derive every binding a warrant claims, and report what does not hold.

    The runtime must not treat a warrant as usable merely because this same
    process just built it. Constructing an artifact and being entitled to rely on
    one are different acts, and if the second is skipped whenever the first
    happened locally then nothing is ever actually checked.

    This validator lives in the demo source lane deliberately. The repository's
    conformance validator under ``tests/contract/`` is a test-only helper and must
    not be imported by runtime code: a runtime whose contract lives in the test
    tree has no contract at all wherever the tests are not installed.
    """
    findings: list[BindingFinding] = []

    def fail(rule_id: str, detail: str) -> None:
        findings.append(BindingFinding(rule_id, detail))

    # WB-001 structural validity against the proposed contract.
    try:
        from jsonschema import Draft202012Validator

        Draft202012Validator(dict(schema)).validate(dict(warrant))
    except ImportError:  # pragma: no cover - jsonschema is a declared dependency
        fail("WB-001", "jsonschema is unavailable, so structural validity is unproven")
    except Exception as error:
        fail("WB-001", f"warrant does not validate against the proposed contract: {error}")

    # WB-002 profile identity. Dispositions and grades are not portable across
    # kernels, so a profile mismatch is a misbinding, not a detail.
    if warrant.get("kernel_profile_id") != runtime_binding.get("kernel_profile_id"):
        fail(
            "WB-002",
            f"kernel_profile_id {warrant.get('kernel_profile_id')!r} does not match the "
            f"binding's {runtime_binding.get('kernel_profile_id')!r}",
        )
    if warrant.get("canonicalization_profile_id") != runtime_binding.get(
        "canonicalization_profile_id"
    ):
        fail(
            "WB-002",
            "canonicalization_profile_id does not match the runtime binding",
        )

    # WB-003 the warrant must be about the formula this control bound.
    if warrant.get("formula_hash") != runtime_binding.get("bound_formula_hash"):
        fail(
            "WB-003",
            f"formula_hash {warrant.get('formula_hash')!r} is not the bound formula "
            f"{runtime_binding.get('bound_formula_hash')!r}",
        )
    if warrant.get("formula_hash") != expected_formula_hash(str(warrant.get("formula", ""))):
        fail("WB-003", "formula_hash does not recompute from the recorded rendered formula")

    # WB-004 kernel identity.
    if warrant.get("kernel_commit") != KERNEL_COMMIT:
        fail("WB-004", f"kernel_commit {warrant.get('kernel_commit')!r} is not the pinned commit")

    # WB-005 the warrant's anchors and admissions must be the ones that made the
    # grounds executable — not a superset, and not something else entirely.
    expected_anchors = {
        str(anchor["anchor_id"]) for anchor in control_envelope.get("source_anchors", [])
    }
    if set(warrant.get("source_anchor_ids") or ()) != expected_anchors:
        fail("WB-005", "source_anchor_ids are not exactly the admitted executable anchors")
    if set(warrant.get("admission_ids") or ()) != set(control_envelope.get("admission_ids") or ()):
        fail("WB-005", "admission_ids are not exactly the control's admissions")

    # WB-006 version bindings must recompute rather than be asserted.
    if runtime_binding.get("source_version_set_hash") != source_version_set_hash:
        fail("WB-006", "source version binding does not recompute")
    if runtime_binding.get("admission_version") != admission_version:
        fail("WB-006", "admission version binding does not recompute")
    if runtime_binding.get("envelope_hash") != envelope_digest:
        fail("WB-006", "envelope identity does not recompute")

    # WB-007 validity interval.
    valid_from = str(warrant.get("valid_from", ""))
    valid_until = warrant.get("valid_until")
    if valid_from and evaluated_at < valid_from:
        fail("WB-007", f"warrant is not yet valid at {evaluated_at}")
    if valid_until is not None and evaluated_at > str(valid_until):
        fail("WB-007", f"warrant expired before {evaluated_at}")

    # WB-008 ground-set identity.
    if warrant.get("ground_set_hash") != ground_set_hash:
        fail("WB-008", "ground_set_hash does not recompute from the evaluated grounds")

    # WB-009 the disposition/grade pair must be one the pinned profile can produce.
    pair = (str(warrant.get("disposition")), str(warrant.get("warranty_grade")))
    if pair not in PERMITTED_DISPOSITION_GRADES:
        fail("WB-009", f"disposition/grade pair {pair} is not reachable under {KERNEL_PROFILE_ID}")

    # WB-010 the ground partition must be a partition.
    dependencies = list(warrant.get("dependency_ids") or ())
    unverified = list(warrant.get("unverified_ground_ids") or ())
    overlap = set(dependencies) & set(unverified)
    if overlap:
        fail("WB-010", f"dependency_ids and unverified_ground_ids overlap: {sorted(overlap)}")

    # WB-011 the output projection must recompute from the recorded fields.
    recomputed = expected_output_hash(
        rendered_formula=str(warrant.get("formula", "")),
        disposition=str(warrant.get("disposition", "")),
        raw_verdict=str(warrant.get("raw_verdict", "")),
        warranty_grade=str(warrant.get("warranty_grade", "")),
        unverified_ground_ids=unverified,
    )
    if warrant.get("output_hash") != recomputed:
        fail("WB-011", "output_hash does not recompute from the recorded kernel output")

    return findings
