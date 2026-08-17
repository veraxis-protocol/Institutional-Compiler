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
    "PROHIBITED_TRANSITIONS",
    "KernelResult",
    "WarrantError",
    "build_warrant",
    "epistemic_status_for",
    "expected_formula_hash",
    "expected_output_hash",
    "invoke_kernel",
    "resolve_ztl_path",
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
