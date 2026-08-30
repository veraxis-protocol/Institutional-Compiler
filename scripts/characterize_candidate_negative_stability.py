#!/usr/bin/env python3
"""Paired A/B falsification over frozen negative controls.

Work order: OIC-CANDIDATE-NEGATIVE-STABILITY-001 (pre-admission).

One anomalous observation started this. The live OIC-CANDIDATE-SEMANTICS-004
characterization returned a candidate on CSEM-031 in one run of three, where
OIC-CANDIDATE-SEMANTICS-003 had returned none in every observed run. Either that is
ordinary provider variance already compatible with the candidate boundary, or the 004
framing-separation prompt weakened normative-vs-non-normative discovery. Nothing should be
"fixed" until it is known which, so this instrument measures and stops.

Two properties make the comparison worth trusting:

* **Each arm runs its own real code.** Both commits are checked out into isolated detached
  worktrees, and every request executes in a subprocess whose ``PYTHONPATH`` points at that
  worktree's ``src``. No prompt is copied, reconstructed, or approximated here; the arms
  differ by exactly what those two commits differ by.
* **The arms are interleaved.** Running all of one arm and then all of the other would
  confound a prompt difference with provider drift over the wall-clock hour the run takes.
  Odd run indices go 003 then 004, even run indices go 004 then 003, and the realized order
  is recorded.

Everything else is deliberately absent. No retry, no output repair, no fallback: a boundary
rejection and a provider error are each recorded as themselves and are each distinct from a
false positive. The credential is read from the environment by whichever adapter the arm
itself ships, and is never printed, logged, or written to the receipt.

This instrument performs no analysis beyond counting and one exact paired test. It reports
which preregistered band the observations fall into; it does not decide what to do about it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

WORK_ORDER = "OIC-CANDIDATE-NEGATIVE-STABILITY-001"
EXPERIMENT_VERSION = "v0.1"

#: The two authoritative arms. Fixed constants: the experiment is defined by them.
ARM_A_LABEL = "003"
ARM_B_LABEL = "004"
ARM_A_COMMIT = "db95d8fdf52b5ffb546b2ebd84bb9e035629c46f"
ARM_B_COMMIT = "11acd84b97bbdb3910c208e63b69b4fbb10be179"
ARM_LABELS = (ARM_A_LABEL, ARM_B_LABEL)
ARM_COMMITS = {ARM_A_LABEL: ARM_A_COMMIT, ARM_B_LABEL: ARM_B_COMMIT}

#: Files whose digest is recorded per arm, so the receipt shows what actually differed.
ARM_FINGERPRINT_FILES = ("src/oic/candidate_extraction.py", "src/oic/nvidia_nim.py")

DEFAULT_CORPUS = Path(
    "benchmarks/characterization/candidate-negative-stability-001/CORPUS-v0.1.json"
)
DEFAULT_FREEZE = Path(
    "benchmarks/characterization/candidate-negative-stability-001/CORPUS-FREEZE-v0.1.json"
)
DEFAULT_OUTPUT = Path(
    ".local/candidate-semantics-receipts/OIC-CANDIDATE-NEGATIVE-STABILITY-001.json"
)
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
DEFAULT_PACING_SECONDS = 4.0

# Outcome vocabulary. Nothing here asserts institutional correctness, and it deliberately
# excludes ADMITTED, AUTHORIZED, COMPLIANT, LEGALLY_VALID, ALLOW and DENY.
STRUCTURAL_PASS = "STRUCTURAL_PASS"  # noqa: S105 - result-state literal, not a credential
BOUNDARY_REJECTED = "BOUNDARY_REJECTED"
PROVIDER_ERROR = "PROVIDER_ERROR"

BAND_NO_MATERIAL = "NO_MATERIAL_REGRESSION_SIGNAL"
BAND_REGRESSION = "REGRESSION_SIGNAL"
BAND_INCONCLUSIVE = "INCONCLUSIVE"

CLAIM_CEILING = (
    "This experiment measures comparative negative-control discovery behavior between two "
    "exact frozen candidate prompts under one provider/model and one small frozen synthetic "
    "corpus. It does not establish semantic correctness, zero false-positive probability, "
    "production readiness, institutional admission, authority, enforceability, legal "
    "interpretation, cross-model generalization, statistical equivalence, or independent "
    "validation."
)


class ExperimentError(RuntimeError):
    """The experiment cannot run as specified."""


class CorpusIntegrityError(ExperimentError):
    """The corpus on disk is not the corpus that was frozen."""


@dataclass(frozen=True, slots=True)
class Specimen:
    """One frozen carried specimen. Immutable: a run cannot edit its own expectations."""

    specimen_id: str
    arm_role: str
    category: str
    source_text: str
    source_sha256: str
    normative_expected: bool
    repetitions_per_arm: int
    carried_from_corpus: str
    carried_from_commit: str


@dataclass(frozen=True, slots=True)
class Corpus:
    """The frozen micro-corpus plus the digest of the exact bytes it came from."""

    corpus_id: str
    corpus_version: str
    claim_ceiling: str
    specimens: tuple[Specimen, ...]
    sha256: str
    relpath: str

    @property
    def negatives(self) -> tuple[Specimen, ...]:
        return tuple(item for item in self.specimens if not item.normative_expected)

    @property
    def positives(self) -> tuple[Specimen, ...]:
        return tuple(item for item in self.specimens if item.normative_expected)


@dataclass(frozen=True, slots=True)
class PlannedRequest:
    """One (specimen, run_index, arm) triple in its realized execution order."""

    sequence: int
    specimen_id: str
    run_index: int
    arm: str


@dataclass(frozen=True, slots=True)
class Attempt:
    """One executed request. Failures are recorded, never retried or repaired."""

    sequence: int
    specimen_id: str
    run_index: int
    arm: str
    arm_commit: str
    normative_expected: bool
    outcome: str
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None
    raw_content_sha256: str | None = None
    candidate_count: int | None = None
    candidate_spans: tuple[str, ...] = ()
    unit_types: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None
    observed_at: str = ""
    source_sha256: str = ""
    candidates: tuple[dict[str, Any], ...] = field(default=())

    @property
    def accepted(self) -> bool:
        return self.outcome == STRUCTURAL_PASS

    @property
    def false_positive(self) -> bool:
        """A negative control that survived the boundary and still returned candidates."""
        return not self.normative_expected and self.accepted and (self.candidate_count or 0) > 0


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
        raise ExperimentError(message)


def _parse_specimen(value: object, index: int) -> Specimen:
    label = f"specimen[{index}]"
    _require(isinstance(value, dict), f"{label} must be an object")
    record: dict[str, Any] = value if isinstance(value, dict) else {}
    for key in (
        "specimen_id",
        "arm_role",
        "category",
        "source_text",
        "source_sha256",
        "carried_from_corpus",
        "carried_from_commit",
    ):
        _require(isinstance(record.get(key), str), f"{label} needs a string {key}")
    _require(
        isinstance(record.get("normative_expected"), bool),
        f"{label} needs a boolean normative_expected",
    )
    repetitions = record.get("repetitions_per_arm")
    _require(
        isinstance(repetitions, int) and not isinstance(repetitions, bool) and repetitions >= 1,
        f"{label} needs a positive repetitions_per_arm",
    )
    _require(bool(str(record["source_text"]).strip()), f"{label} source_text must not be empty")
    _require(
        record["arm_role"] in {"negative_control", "positive_sentinel"},
        f"{label} arm_role must be negative_control or positive_sentinel",
    )
    return Specimen(
        specimen_id=str(record["specimen_id"]),
        arm_role=str(record["arm_role"]),
        category=str(record["category"]),
        source_text=str(record["source_text"]),
        source_sha256=str(record["source_sha256"]),
        normative_expected=bool(record["normative_expected"]),
        repetitions_per_arm=int(repetitions) if isinstance(repetitions, int) else 1,
        carried_from_corpus=str(record["carried_from_corpus"]),
        carried_from_commit=str(record["carried_from_commit"]),
    )


def load_corpus(path: Path, *, relpath: str | None = None) -> Corpus:
    """Load and shape-validate the frozen corpus, recording its exact byte digest."""
    body = path.read_bytes()
    try:
        parsed: Any = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"corpus at {path} is not valid UTF-8 JSON") from exc
    _require(isinstance(parsed, dict), "corpus root must be an object")
    document: dict[str, Any] = parsed if isinstance(parsed, dict) else {}
    for key in ("corpus_id", "corpus_version", "claim_ceiling"):
        _require(isinstance(document.get(key), str), f"corpus needs a string {key}")
    raw_specimens = document.get("specimens")
    _require(isinstance(raw_specimens, list) and bool(raw_specimens), "corpus needs specimens")
    items = raw_specimens if isinstance(raw_specimens, list) else []
    specimens = tuple(_parse_specimen(entry, index) for index, entry in enumerate(items))
    identifiers = [item.specimen_id for item in specimens]
    duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
    _require(not duplicates, f"corpus has duplicate specimen ids: {duplicates}")
    declared = document.get("specimen_count")
    if declared is not None:
        _require(
            declared == len(specimens),
            f"corpus specimen_count {declared!r} disagrees with {len(specimens)} specimens",
        )
    for specimen in specimens:
        recomputed = hashlib.sha256(specimen.source_text.encode("utf-8")).hexdigest()
        _require(
            recomputed == specimen.source_sha256,
            f"{specimen.specimen_id} source_sha256 disagrees with its own source_text",
        )
    return Corpus(
        corpus_id=str(document["corpus_id"]),
        corpus_version=str(document["corpus_version"]),
        claim_ceiling=str(document["claim_ceiling"]),
        specimens=specimens,
        sha256=hashlib.sha256(body).hexdigest(),
        relpath=relpath if relpath is not None else path.as_posix(),
    )


def corpus_freeze_findings(corpus: Corpus, freeze: dict[str, Any]) -> list[str]:
    """Differences between the corpus on disk and its frozen record. Empty means intact."""
    findings: list[str] = []
    if freeze.get("corpus_sha256") != corpus.sha256:
        findings.append(
            f"corpus sha256 drift: frozen {freeze.get('corpus_sha256')!r}, "
            f"on disk {corpus.sha256!r}"
        )
    if freeze.get("specimen_count") != len(corpus.specimens):
        findings.append(
            f"specimen count drift: frozen {freeze.get('specimen_count')!r}, "
            f"on disk {len(corpus.specimens)}"
        )
    observed_ids = [item.specimen_id for item in corpus.specimens]
    if freeze.get("specimen_ids") != observed_ids:
        findings.append("specimen id drift: frozen id list does not match the corpus on disk")
    recorded_sources = freeze.get("specimen_source_sha256")
    if isinstance(recorded_sources, dict):
        for specimen in corpus.specimens:
            if recorded_sources.get(specimen.specimen_id) != specimen.source_sha256:
                findings.append(f"source text drift for {specimen.specimen_id}")
    else:
        findings.append("frozen record has no specimen_source_sha256 map")
    for label, key in ((ARM_A_LABEL, "arm_a_commit"), (ARM_B_LABEL, "arm_b_commit")):
        if freeze.get(key) != ARM_COMMITS[label]:
            findings.append(
                f"arm {label} drift: frozen {freeze.get(key)!r}, expected {ARM_COMMITS[label]!r}"
            )
    return findings


def verify_corpus_integrity(corpus: Corpus, freeze_path: Path) -> list[str]:
    """Refuse to run on drift. The authorized run needs no acknowledgement flag."""
    document: Any = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise CorpusIntegrityError(f"frozen record at {freeze_path} is not a JSON object")
    findings = corpus_freeze_findings(corpus, document)
    if findings:
        raise CorpusIntegrityError(
            "corpus does not match its frozen record; refusing to run.\n  - "
            + "\n  - ".join(findings)
            + "\nRe-freeze deliberately rather than running against a moved corpus."
        )
    return findings


# --------------------------------------------------------------------------
# Run plan
# --------------------------------------------------------------------------


def arm_order(run_index: int) -> tuple[str, str]:
    """Odd run index runs 003 first; even runs 004 first. Deterministic and balanced."""
    return (ARM_A_LABEL, ARM_B_LABEL) if run_index % 2 == 1 else (ARM_B_LABEL, ARM_A_LABEL)


def plan_requests(corpus: Corpus) -> tuple[PlannedRequest, ...]:
    """The full ordered request sequence, interleaved arm-by-arm within each run index."""
    planned: list[PlannedRequest] = []
    sequence = 0
    horizon = max(item.repetitions_per_arm for item in corpus.specimens)
    for run_index in range(1, horizon + 1):
        for specimen in corpus.specimens:
            if run_index > specimen.repetitions_per_arm:
                continue
            for arm in arm_order(run_index):
                sequence += 1
                planned.append(
                    PlannedRequest(
                        sequence=sequence,
                        specimen_id=specimen.specimen_id,
                        run_index=run_index,
                        arm=arm,
                    )
                )
    return tuple(planned)


def specimen_anchor(specimen: Specimen, corpus: Corpus, run_index: int) -> dict[str, Any]:
    """Deterministic anchor, identical across arms for the same specimen and run.

    Carries the full source quote. The arm label is deliberately absent: an anchor that
    differed between arms would make the comparison meaningless.
    """
    return {
        "anchor_id": f"{specimen.specimen_id}-A{run_index}",
        "source_id": f"{corpus.corpus_id}/{corpus.corpus_version}",
        "node_id": specimen.specimen_id,
        "content_hash": f"sha256:{specimen.source_sha256}",
        "quote": specimen.source_text,
    }


# --------------------------------------------------------------------------
# Arm isolation
# --------------------------------------------------------------------------


def _git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None:
        raise ExperimentError("git is required to materialize the experiment arms")
    return subprocess.run(  # noqa: S603 - resolved executable, literal arguments
        [executable, "-C", str(root), *argv], check=False, capture_output=True, text=True
    )


def require_clean_source_repository(root: Path) -> None:
    status = _git(root, "status", "--porcelain")
    if status.returncode != 0:
        raise ExperimentError("cannot read the source repository status")
    if status.stdout.strip():
        raise ExperimentError(
            "source repository is not clean; commit or stash before running the experiment"
        )


def require_commit_present(root: Path, commit: str) -> None:
    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    if resolved.returncode != 0:
        raise ExperimentError(f"required experiment commit is not present: {commit}")


def create_arm_worktree(root: Path, commit: str, destination: Path) -> None:
    """Detached worktree at an exact commit. Never mutates the historical commit."""
    if destination.exists():
        raise ExperimentError(
            f"arm worktree path already exists: {destination}. Remove it deliberately "
            "(git worktree remove) rather than letting this experiment delete it."
        )
    result = _git(root, "worktree", "add", "--detach", str(destination), commit)
    if result.returncode != 0:
        raise ExperimentError(
            f"could not create arm worktree at {destination}: {result.stderr.strip()}"
        )
    head = _git(destination, "rev-parse", "HEAD").stdout.strip()
    if head != commit:
        raise ExperimentError(
            f"arm worktree HEAD is {head!r}, expected {commit!r}; refusing to proceed"
        )


def remove_arm_worktree(root: Path, destination: Path) -> str:
    """Best-effort cleanup. Never deletes anything outside the worktree it created."""
    result = _git(root, "worktree", "remove", "--force", str(destination))
    if result.returncode == 0:
        return "removed"
    return f"NOT REMOVED: {destination} ({result.stderr.strip()})"


def arm_fingerprint(worktree: Path) -> dict[str, str]:
    """SHA-256 of the files that define what the arms differ by."""
    return {
        relpath: hashlib.sha256((worktree / relpath).read_bytes()).hexdigest()
        for relpath in ARM_FINGERPRINT_FILES
    }


# --------------------------------------------------------------------------
# Arm worker
#
# Executed as a subprocess with PYTHONPATH pointing at one arm's src, so `oic` resolves
# to that commit's real implementation. One request in, one JSON result out, no retry.
# --------------------------------------------------------------------------


class ArmBindingError(ExperimentError):
    """The worker resolved `oic` to something other than the arm it was given."""


def _bound_candidate_extraction(arm_src: str) -> ModuleType:
    """Import `oic.candidate_extraction` and PROVE it came from this arm's worktree.

    A near-miss during development made this non-negotiable: if `oic` is installed
    editable, a mistyped path silently resolves to the source repository instead, and the
    experiment would compare an arm against itself and report a confident null. So the
    worker refuses to answer a request it cannot prove came from the right tree.
    """
    # Imported inside the function on purpose: `oic` must resolve against the arm src
    # placed on sys.path for this subprocess only.
    import oic.candidate_extraction as module

    resolved = Path(module.__file__ or "").resolve()
    expected_root = Path(arm_src).resolve()
    if expected_root not in resolved.parents:
        raise ArmBindingError(
            f"oic.candidate_extraction resolved to {resolved}, which is not inside the "
            f"arm source root {expected_root}. Refusing to run: the arms would not be "
            "distinguishable."
        )
    return module


def _arm_binding_report(arm_src: str) -> dict[str, Any]:
    """What this arm actually bound to. Used by the orchestrator preflight."""
    module = _bound_candidate_extraction(arm_src)
    path = Path(module.__file__ or "").resolve()
    prompt = getattr(module, "_SYSTEM_PROMPT", None)
    return {
        "arm_src": str(Path(arm_src).resolve()),
        "resolved_module_path": str(path),
        "module_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "system_prompt_sha256": (
            hashlib.sha256(prompt.encode("utf-8")).hexdigest() if isinstance(prompt, str) else None
        ),
        "system_prompt_length": len(prompt) if isinstance(prompt, str) else None,
        "model_allowed_keys": sorted(getattr(module, "_MODEL_ALLOWED_KEYS", ())),
    }


def _run_arm_worker_from_stdin() -> int:
    request: Any = json.loads(sys.stdin.read())
    arm_src = str(request["arm_src"])
    payload: dict[str, Any]
    try:
        module = _bound_candidate_extraction(arm_src)
    except ArmBindingError as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "outcome": PROVIDER_ERROR,
                    "error_type": "ArmBindingError",
                    "error_message": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if request.get("verify_only"):
        sys.stdout.write(
            json.dumps(
                {"outcome": "ARM_BINDING", **_arm_binding_report(arm_src)}, ensure_ascii=False
            )
        )
        return 0

    from oic.model_provider import ModelProviderError
    from oic.nvidia_nim import NvidiaNimConfig, NvidiaNimProvider

    boundary_error = module.CandidateBoundaryError
    propose_candidate_units = module.propose_candidate_units
    provider = NvidiaNimProvider(NvidiaNimConfig(model=str(request["model"])))
    try:
        result = propose_candidate_units(
            source_text=str(request["source_text"]),
            source_anchor=dict(request["source_anchor"]),
            provider=provider,
        )
    except boundary_error as exc:
        payload = {
            "outcome": BOUNDARY_REJECTED,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    except ModelProviderError as exc:
        payload = {
            "outcome": PROVIDER_ERROR,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    else:
        candidates = [dict(item) for item in result.candidates]
        payload = {
            "outcome": STRUCTURAL_PASS,
            "provider": result.provider,
            "model": result.model,
            "request_id": result.request_id,
            "raw_content_sha256": result.raw_content_sha256,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "candidate_spans": [str(item.get("candidate_span", "")) for item in candidates],
            "unit_types": [str(item.get("unit_type", "")) for item in candidates],
        }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0


def verify_arm_binding(
    *, worktree: Path, script_path: Path, timeout_seconds: float = 60.0
) -> dict[str, Any]:
    """Ask a worker subprocess what it actually bound to, before any live request."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(worktree / "src")
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and script path
        [sys.executable, str(script_path), "--arm-worker"],
        input=json.dumps({"arm_src": str(worktree / "src"), "verify_only": True}),
        env=environment,
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise ExperimentError(
            f"arm binding probe failed for {worktree}: {completed.stderr.strip()[:2000]}"
        )
    report: Any = json.loads(completed.stdout)
    if report.get("outcome") != "ARM_BINDING":
        raise ExperimentError(
            f"arm binding probe for {worktree} returned {report.get('error_message')!r}"
        )
    return dict(report)


def require_distinguishable_arms(bindings: dict[str, dict[str, Any]]) -> None:
    """Refuse to run an A/B whose arms are not provably different code.

    Without this the experiment can silently compare an arm against itself -- an editable
    install, a mistyped path, a stale worktree -- and produce a confident null result for
    entirely the wrong reason. A null is only meaningful once the arms are known to differ.
    """
    left = bindings[ARM_A_LABEL]
    right = bindings[ARM_B_LABEL]
    if left["resolved_module_path"] == right["resolved_module_path"]:
        raise ExperimentError(
            "both arms resolved oic.candidate_extraction to the same file "
            f"({left['resolved_module_path']}); the arms are not distinguishable"
        )
    if left["module_file_sha256"] == right["module_file_sha256"]:
        raise ExperimentError(
            "both arms have byte-identical candidate_extraction.py "
            f"(sha256={left['module_file_sha256']}); the arms are not distinguishable"
        )
    if (
        left["system_prompt_sha256"] is not None
        and left["system_prompt_sha256"] == right["system_prompt_sha256"]
    ):
        raise ExperimentError(
            "both arms produced the same system prompt digest "
            f"({left['system_prompt_sha256']}); the arms are not distinguishable"
        )


def _optional_text(value: object) -> str | None:
    return None if value is None else str(value)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def execute_request(
    planned: PlannedRequest,
    *,
    specimen: Specimen,
    corpus: Corpus,
    worktree: Path,
    model: str,
    script_path: Path,
    timeout_seconds: float,
) -> Attempt:
    """One request against one arm's real implementation. No retry, no repair."""
    payload = {
        "model": model,
        "arm_src": str(worktree / "src"),
        "source_text": specimen.source_text,
        "source_anchor": specimen_anchor(specimen, corpus, planned.run_index),
    }
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(worktree / "src")
    observed_at = _now()

    def failed(outcome: str, error_type: str, error_message: str) -> Attempt:
        return Attempt(
            sequence=planned.sequence,
            specimen_id=planned.specimen_id,
            run_index=planned.run_index,
            arm=planned.arm,
            arm_commit=ARM_COMMITS[planned.arm],
            normative_expected=specimen.normative_expected,
            source_sha256=specimen.source_sha256,
            observed_at=observed_at,
            outcome=outcome,
            error_type=error_type,
            error_message=error_message,
        )

    completed = subprocess.run(  # noqa: S603 - fixed interpreter and script path
        [sys.executable, str(script_path), "--arm-worker"],
        input=json.dumps(payload, ensure_ascii=False),
        env=environment,
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        return failed(
            PROVIDER_ERROR,
            "ArmWorkerFailure",
            (completed.stderr.strip() or "arm worker exited non-zero")[:2000],
        )
    try:
        result: Any = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return failed(PROVIDER_ERROR, "ArmWorkerOutputInvalid", "arm worker did not return JSON")
    outcome = str(result.get("outcome"))
    if outcome != STRUCTURAL_PASS:
        return failed(
            outcome,
            str(result.get("error_type") or "UnknownError"),
            str(result.get("error_message") or ""),
        )
    candidates = tuple(dict(item) for item in result.get("candidates", ()))
    return Attempt(
        sequence=planned.sequence,
        specimen_id=planned.specimen_id,
        run_index=planned.run_index,
        arm=planned.arm,
        arm_commit=ARM_COMMITS[planned.arm],
        normative_expected=specimen.normative_expected,
        source_sha256=specimen.source_sha256,
        observed_at=observed_at,
        outcome=STRUCTURAL_PASS,
        provider=_optional_text(result.get("provider")),
        model=_optional_text(result.get("model")),
        request_id=_optional_text(result.get("request_id")),
        raw_content_sha256=_optional_text(result.get("raw_content_sha256")),
        candidate_count=len(candidates),
        candidates=candidates,
        candidate_spans=tuple(str(span) for span in result.get("candidate_spans", ())),
        unit_types=tuple(str(unit) for unit in result.get("unit_types", ())),
    )


# --------------------------------------------------------------------------
# Measures
# --------------------------------------------------------------------------


def false_positive_records(attempts: Sequence[Attempt]) -> list[dict[str, Any]]:
    """Every individual false positive, in full. Never summarized away."""
    return [
        {
            "specimen_id": attempt.specimen_id,
            "run_index": attempt.run_index,
            "arm": attempt.arm,
            "arm_commit": attempt.arm_commit,
            "candidate_count": attempt.candidate_count,
            "candidate_spans": list(attempt.candidate_spans),
            "unit_types": list(attempt.unit_types),
            "request_id": attempt.request_id,
            "raw_content_sha256": attempt.raw_content_sha256,
            "source_sha256": attempt.source_sha256,
            "observed_at": attempt.observed_at,
        }
        for attempt in attempts
        if attempt.false_positive
    ]


def arm_summary(attempts: Sequence[Attempt], arm: str) -> dict[str, Any]:
    """Primary and secondary measures for one arm."""
    scoped = [item for item in attempts if item.arm == arm]
    negatives = [item for item in scoped if not item.normative_expected]
    positives = [item for item in scoped if item.normative_expected]
    accepted_negatives = [item for item in negatives if item.accepted]
    accepted_positives = [item for item in positives if item.accepted]
    false_positives = [item for item in negatives if item.false_positive]
    presence_misses = [item for item in accepted_positives if (item.candidate_count or 0) == 0]
    return {
        "arm": arm,
        "arm_commit": ARM_COMMITS[arm],
        "requests_attempted": len(scoped),
        "boundary_accepted": sum(1 for item in scoped if item.accepted),
        "boundary_rejected": sum(1 for item in scoped if item.outcome == BOUNDARY_REJECTED),
        "provider_errors": sum(1 for item in scoped if item.outcome == PROVIDER_ERROR),
        "negative_requests": len(negatives),
        "provider_successful_negative_runs": len(accepted_negatives),
        "false_positive_runs": len(false_positives),
        "false_positive_rate": (
            len(false_positives) / len(accepted_negatives) if accepted_negatives else None
        ),
        "false_positive_rate_denominator": "provider-successful negative runs",
        "positive_requests": len(positives),
        "provider_successful_positive_runs": len(accepted_positives),
        "positive_presence_misses": len(presence_misses),
        "candidate_count_distribution": {
            str(key): value
            for key, value in sorted(
                Counter(item.candidate_count for item in scoped if item.accepted).items(),
                key=lambda pair: (pair[0] is None, pair[0]),
            )
        },
        "provisional_unit_type_distribution": dict(
            sorted(Counter(unit for item in scoped for unit in item.unit_types).items())
        ),
        "false_positive_candidate_spans": sorted(
            {span for item in false_positives for span in item.candidate_spans}
        ),
        "false_positive_provisional_types": sorted(
            {unit for item in false_positives for unit in item.unit_types}
        ),
        "boundary_rejections": [
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "error_type": item.error_type,
                "error_message": item.error_message,
            }
            for item in scoped
            if item.outcome == BOUNDARY_REJECTED
        ],
        "provider_error_records": [
            {
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "error_type": item.error_type,
                "error_message": item.error_message,
            }
            for item in scoped
            if item.outcome == PROVIDER_ERROR
        ],
    }


def per_specimen_summary(corpus: Corpus, attempts: Sequence[Attempt]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for specimen in corpus.specimens:
        row: dict[str, Any] = {
            "specimen_id": specimen.specimen_id,
            "arm_role": specimen.arm_role,
            "normative_expected": specimen.normative_expected,
            "source_sha256": specimen.source_sha256,
        }
        for arm in ARM_LABELS:
            scoped = [
                item
                for item in attempts
                if item.specimen_id == specimen.specimen_id and item.arm == arm
            ]
            accepted = [item for item in scoped if item.accepted]
            row[f"arm_{arm}"] = {
                "requests": len(scoped),
                "provider_successful_runs": len(accepted),
                "boundary_rejected": sum(1 for item in scoped if item.outcome == BOUNDARY_REJECTED),
                "provider_errors": sum(1 for item in scoped if item.outcome == PROVIDER_ERROR),
                "false_positive_runs": sum(1 for item in scoped if item.false_positive),
                "presence_misses": (
                    sum(1 for item in accepted if (item.candidate_count or 0) == 0)
                    if specimen.normative_expected
                    else None
                ),
                "candidate_count_distribution": {
                    str(key): value
                    for key, value in sorted(
                        Counter(item.candidate_count for item in accepted).items(),
                        key=lambda pair: (pair[0] is None, pair[0]),
                    )
                },
                "observed_unit_types": sorted(
                    {unit for item in scoped for unit in item.unit_types}
                ),
            }
        rows.append(row)
    return rows


def exact_paired_p_value(discordant_a: int, discordant_b: int) -> float | None:
    """Two-sided exact binomial p over the discordant pairs. Standard library only.

    Descriptive evidence about whether the discordant split looks like a coin flip. It
    adjudicates nothing about semantic correctness, and with a handful of discordant pairs
    it is close to uninformative by construction.
    """
    total = discordant_a + discordant_b
    if total == 0:
        return None
    smaller = min(discordant_a, discordant_b)
    weight: int = sum(math.comb(total, k) for k in range(smaller + 1))
    tail: float = weight / float(2**total)
    return min(1.0, 2.0 * tail)


def paired_comparison(corpus: Corpus, attempts: Sequence[Attempt]) -> dict[str, Any]:
    """Outcome of each (specimen, run_index) pair under both arms.

    A pair counts only when both arms produced a provider-successful, boundary-accepted
    observation: a pair missing one side cannot say anything about a difference.
    """
    indexed = {
        (item.specimen_id, item.run_index, item.arm): item
        for item in attempts
        if not item.normative_expected
    }
    both_absent = 0
    only_a = 0
    only_b = 0
    both_present = 0
    unusable: list[dict[str, Any]] = []
    discordant: list[dict[str, Any]] = []
    for specimen in corpus.negatives:
        for run_index in range(1, specimen.repetitions_per_arm + 1):
            left = indexed.get((specimen.specimen_id, run_index, ARM_A_LABEL))
            right = indexed.get((specimen.specimen_id, run_index, ARM_B_LABEL))
            if left is None or right is None or not left.accepted or not right.accepted:
                unusable.append(
                    {
                        "specimen_id": specimen.specimen_id,
                        "run_index": run_index,
                        f"arm_{ARM_A_LABEL}_outcome": left.outcome if left else "MISSING",
                        f"arm_{ARM_B_LABEL}_outcome": right.outcome if right else "MISSING",
                    }
                )
                continue
            if left.false_positive and right.false_positive:
                both_present += 1
            elif left.false_positive:
                only_a += 1
                discordant.append(
                    {
                        "specimen_id": specimen.specimen_id,
                        "run_index": run_index,
                        "false_positive_arm": ARM_A_LABEL,
                        "candidate_spans": list(left.candidate_spans),
                        "unit_types": list(left.unit_types),
                    }
                )
            elif right.false_positive:
                only_b += 1
                discordant.append(
                    {
                        "specimen_id": specimen.specimen_id,
                        "run_index": run_index,
                        "false_positive_arm": ARM_B_LABEL,
                        "candidate_spans": list(right.candidate_spans),
                        "unit_types": list(right.unit_types),
                    }
                )
            else:
                both_absent += 1
    return {
        "both_correctly_absent": both_absent,
        f"arm_{ARM_A_LABEL}_false_positive_only": only_a,
        f"arm_{ARM_B_LABEL}_false_positive_only": only_b,
        "both_false_positive": both_present,
        "usable_pairs": both_absent + only_a + only_b + both_present,
        "unusable_pairs": unusable,
        "discordant_pairs": discordant,
        "discordant_total": only_a + only_b,
        "exact_two_sided_p_value": exact_paired_p_value(only_a, only_b),
        "p_value_note": (
            "Two-sided exact binomial over discordant pairs (McNemar-style), standard "
            "library only. Descriptive evidence about the discordant split. It does not "
            "adjudicate semantic correctness and is near-uninformative at these counts."
        ),
    }


def csem_031_report(attempts: Sequence[Attempt]) -> dict[str, Any]:
    """The trigger specimen, every attempt shown. Identical outputs are not collapsed."""
    scoped = sorted(
        (item for item in attempts if item.specimen_id == "CSEM-031"),
        key=lambda item: (item.arm, item.run_index),
    )
    per_arm: dict[str, Any] = {}
    for arm in ARM_LABELS:
        arm_attempts = [item for item in scoped if item.arm == arm]
        accepted = [item for item in arm_attempts if item.accepted]
        positives = [item for item in arm_attempts if item.false_positive]
        per_arm[f"arm_{arm}"] = {
            "arm_commit": ARM_COMMITS[arm],
            "attempts": len(arm_attempts),
            "provider_successful_runs": len(accepted),
            "false_positive_runs": len(positives),
            "false_positive_rate": (len(positives) / len(accepted)) if accepted else None,
        }
    return {
        "specimen_id": "CSEM-031",
        "why_this_specimen": (
            "The single anomalous negative-control observation in the live "
            "OIC-CANDIDATE-SEMANTICS-004 characterization. Every attempt is listed "
            "individually; repeated identical outputs are not collapsed."
        ),
        **per_arm,
        "all_attempts": [
            {
                "sequence": item.sequence,
                "arm": item.arm,
                "run_index": item.run_index,
                "outcome": item.outcome,
                "candidate_count": item.candidate_count,
                "candidate_spans": list(item.candidate_spans),
                "unit_types": list(item.unit_types),
                "request_id": item.request_id,
                "raw_content_sha256": item.raw_content_sha256,
                "error_type": item.error_type,
                "error_message": item.error_message,
                "observed_at": item.observed_at,
            }
            for item in scoped
        ],
    }


def positive_sentinel_report(corpus: Corpus, attempts: Sequence[Attempt]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_present = True
    for specimen in corpus.positives:
        entry: dict[str, Any] = {"specimen_id": specimen.specimen_id}
        for arm in ARM_LABELS:
            scoped = [
                item
                for item in attempts
                if item.specimen_id == specimen.specimen_id and item.arm == arm
            ]
            accepted = [item for item in scoped if item.accepted]
            misses = [item for item in accepted if (item.candidate_count or 0) == 0]
            if misses:
                all_present = False
            entry[f"arm_{arm}"] = {
                "provider_successful_runs": len(accepted),
                "runs_with_candidate": len(accepted) - len(misses),
                "presence_misses": len(misses),
                "observed_unit_types": sorted(
                    {unit for item in scoped for unit in item.unit_types}
                ),
            }
        rows.append(entry)
    return {
        "per_specimen": rows,
        "both_sentinels_present_in_every_provider_successful_run": all_present,
        "note": (
            "Sentinels are not the primary test. They exist to detect an accidental broad "
            "suppression of candidate discovery in either arm."
        ),
    }


def interpretation_band(
    corpus: Corpus, attempts: Sequence[Attempt], sentinels: dict[str, Any]
) -> dict[str, Any]:
    """Mechanically evaluate the preregistered bands. No architectural adjudication."""
    counts = {
        arm: sum(1 for item in attempts if item.arm == arm and item.false_positive)
        for arm in ARM_LABELS
    }
    delta = counts[ARM_B_LABEL] - counts[ARM_A_LABEL]
    per_specimen: list[dict[str, Any]] = []
    specimen_regression = False
    specimen_elevated = False
    for specimen in corpus.negatives:
        scoped = {
            arm: [
                item
                for item in attempts
                if item.specimen_id == specimen.specimen_id
                and item.arm == arm
                and item.false_positive
            ]
            for arm in ARM_LABELS
        }
        a_count = len(scoped[ARM_A_LABEL])
        b_count = len(scoped[ARM_B_LABEL])
        regression = b_count >= 4 and a_count <= 1
        elevated = b_count >= 3 and a_count <= 1
        specimen_regression = specimen_regression or regression
        specimen_elevated = specimen_elevated or elevated
        per_specimen.append(
            {
                "specimen_id": specimen.specimen_id,
                f"arm_{ARM_A_LABEL}_false_positives": a_count,
                f"arm_{ARM_B_LABEL}_false_positives": b_count,
                "triggers_specimen_regression_rule_b_ge_4_and_a_le_1": regression,
                "triggers_elevated_rule_b_ge_3_and_a_le_1": elevated,
            }
        )
    sentinels_ok = bool(sentinels["both_sentinels_present_in_every_provider_successful_run"])
    rule_regression_total = delta >= 5
    rule_no_material = delta <= 2 and not specimen_elevated and sentinels_ok
    if rule_regression_total or specimen_regression:
        band = BAND_REGRESSION
    elif rule_no_material:
        band = BAND_NO_MATERIAL
    else:
        band = BAND_INCONCLUSIVE
    return {
        "band": band,
        f"arm_{ARM_A_LABEL}_false_positive_events": counts[ARM_A_LABEL],
        f"arm_{ARM_B_LABEL}_false_positive_events": counts[ARM_B_LABEL],
        "delta_004_minus_003": delta,
        "rule_evaluations": {
            "regression_total_delta_ge_5": rule_regression_total,
            "regression_any_specimen_b_ge_4_and_a_le_1": specimen_regression,
            "no_material_delta_le_2": delta <= 2,
            "no_material_no_specimen_b_ge_3_and_a_le_1": not specimen_elevated,
            "no_material_both_sentinels_present": sentinels_ok,
        },
        "per_negative_specimen": per_specimen,
        "note": (
            "Engineering characterization bands, not statistical proof. The raw numbers "
            "beside the band are the evidence; the band is a mechanical restatement of the "
            "preregistered rules and decides no architecture."
        ),
    }


# --------------------------------------------------------------------------
# Receipt
# --------------------------------------------------------------------------


def build_receipt(
    *,
    corpus: Corpus,
    attempts: Sequence[Attempt],
    planned: Sequence[PlannedRequest],
    model: str,
    pacing_seconds: float,
    arm_fingerprints: dict[str, dict[str, str]],
    arm_bindings: dict[str, dict[str, Any]],
    arm_worktrees: dict[str, str],
    cleanup: dict[str, str],
    corpus_freeze_relpath: str,
    orchestrator_commit: dict[str, Any],
) -> dict[str, Any]:
    sentinels = positive_sentinel_report(corpus, attempts)
    return {
        "work_order": WORK_ORDER,
        "experiment_version": EXPERIMENT_VERSION,
        "generated_at": _now(),
        "independent_validation_claim": False,
        "self_adjudication": "NOT SELF-ADJUDICATED; engineering observations only.",
        "claim_ceiling": CLAIM_CEILING,
        "arms": {
            f"arm_{ARM_A_LABEL}": {
                "label": ARM_A_LABEL,
                "commit": ARM_A_COMMIT,
                "worktree": arm_worktrees.get(ARM_A_LABEL),
                "file_sha256": arm_fingerprints.get(ARM_A_LABEL, {}),
                "verified_binding": arm_bindings.get(ARM_A_LABEL, {}),
            },
            f"arm_{ARM_B_LABEL}": {
                "label": ARM_B_LABEL,
                "commit": ARM_B_COMMIT,
                "worktree": arm_worktrees.get(ARM_B_LABEL),
                "file_sha256": arm_fingerprints.get(ARM_B_LABEL, {}),
                "verified_binding": arm_bindings.get(ARM_B_LABEL, {}),
            },
            "arms_verified_distinguishable": True,
            "note": (
                "Each request executed in a subprocess whose PYTHONPATH pointed at that "
                "arm's worktree src, so oic.candidate_extraction was imported from the "
                "exact commit. No prompt was copied or reconstructed by this harness. "
                "Before the first request the orchestrator proved each arm resolved to a "
                "module inside its own worktree and that the two arms differ by file "
                "digest and system-prompt digest; every request re-checks its own binding "
                "and fails closed otherwise."
            ),
        },
        "orchestrator": orchestrator_commit,
        "corpus": {
            "corpus_id": corpus.corpus_id,
            "corpus_version": corpus.corpus_version,
            "corpus_relpath": corpus.relpath,
            "corpus_sha256": corpus.sha256,
            "corpus_freeze_relpath": corpus_freeze_relpath,
            "specimen_count": len(corpus.specimens),
            "specimen_ids": [item.specimen_id for item in corpus.specimens],
            "specimen_source_sha256": {
                item.specimen_id: item.source_sha256 for item in corpus.specimens
            },
            "claim_ceiling": corpus.claim_ceiling,
        },
        "run_conditions": {
            "model_provider": "nvidia-nim",
            "model": model,
            "pacing_seconds_after_each_request": pacing_seconds,
            "pacing_note": (
                "Client-side orchestration pacing only. It is not retry logic and no "
                "production file carries it."
            ),
            "retries": 0,
            "retry_note": "No retry exists. Every transport failure is one observation.",
            "planned_negative_requests": sum(
                item.repetitions_per_arm * 2 for item in corpus.negatives
            ),
            "planned_positive_requests": sum(
                item.repetitions_per_arm * 2 for item in corpus.positives
            ),
            "planned_total_requests": len(planned),
            "executed_total_requests": len(attempts),
            "interleaving_rule": (
                "For each (specimen_id, run_index): odd run index runs 003 then 004; even "
                "run index runs 004 then 003. Balanced and deterministic."
            ),
        },
        "engineering_gates": {
            "corpus_integrity": "INTACT",
            "executed_every_planned_request": len(attempts) == len(planned),
            "arm_worktree_cleanup": cleanup,
            "note": "Mechanical gates only; no semantic or institutional verdict.",
        },
        "actual_request_sequence": [
            {
                "sequence": item.sequence,
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "arm": item.arm,
            }
            for item in planned
        ],
        "attempts": [
            {
                "sequence": item.sequence,
                "specimen_id": item.specimen_id,
                "run_index": item.run_index,
                "arm": item.arm,
                "arm_commit": item.arm_commit,
                "normative_expected": item.normative_expected,
                "outcome": item.outcome,
                "provider": item.provider,
                "model": item.model,
                "request_id": item.request_id,
                "raw_content_sha256": item.raw_content_sha256,
                "source_sha256": item.source_sha256,
                "candidate_count": item.candidate_count,
                "candidate_spans": list(item.candidate_spans),
                "unit_types": list(item.unit_types),
                "candidates": list(item.candidates),
                "error_type": item.error_type,
                "error_message": item.error_message,
                "observed_at": item.observed_at,
                "false_positive": item.false_positive,
            }
            for item in attempts
        ],
        "primary_measure": {
            "question": (
                "Does 004 generate materially more false-positive candidate discoveries on "
                "the frozen negative controls than 003?"
            ),
            "false_positive_definition": (
                "normative_expected is false AND the response survived the existing "
                "candidate boundary AND candidate_count > 0. A boundary rejection is not a "
                "false positive; a provider error is not a false positive."
            ),
            f"arm_{ARM_A_LABEL}": arm_summary(attempts, ARM_A_LABEL),
            f"arm_{ARM_B_LABEL}": arm_summary(attempts, ARM_B_LABEL),
            "all_false_positive_observations": false_positive_records(attempts),
        },
        "per_specimen": per_specimen_summary(corpus, attempts),
        "paired_comparison": paired_comparison(corpus, attempts),
        "csem_031": csem_031_report(attempts),
        "positive_sentinels": sentinels,
        "interpretation": interpretation_band(corpus, attempts, sentinels),
        "limitations": [
            "One provider, one model, one endpoint, one corpus of five negative controls.",
            "Ten repetitions per negative specimen per arm cannot estimate a small "
            "false-positive rate with any precision; a rate of 1-in-50 is barely "
            "distinguishable from 1-in-500 at this sample size.",
            "temperature is whatever each frozen commit specifies (0.0), so observed "
            "variation is a floor rather than the model's full spread.",
            "The arms differ by one commit, which changed only the candidate prompt. Any "
            "difference observed is attributable to that diff, not to a prompt feature "
            "isolated in the abstract.",
            "Interleaving reduces but does not eliminate provider-time drift; a "
            "provider-side model update mid-run would confound both arms equally and is "
            "not detectable here.",
            "The exact paired p-value is descriptive only and is near-uninformative at "
            "these counts.",
            "Bands are preregistered engineering thresholds, not statistical inference, "
            "and were chosen before any data existed.",
            "Absence of a regression signal is not evidence of equivalence.",
        ],
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="characterize_candidate_negative_stability.py",
        description=(
            "Paired A/B falsification of candidate negative-control discovery between the "
            "OIC-CANDIDATE-SEMANTICS-003 and -004 candidate prompts. Requires NVIDIA_API_KEY "
            "in the local environment; the credential is read by each arm's own adapter and "
            "is never printed or written to the receipt."
        ),
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--pacing-seconds", type=float, default=DEFAULT_PACING_SECONDS)
    parser.add_argument("--request-timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--worktree-root",
        type=Path,
        default=None,
        help="Directory to create the two arm worktrees under. Defaults to a temp dir.",
    )
    parser.add_argument(
        "--arm-worker",
        action="store_true",
        help=argparse.SUPPRESS,  # internal: one request, executed inside an arm worktree
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.arm_worker:
        return _run_arm_worker_from_stdin()

    script_path = Path(__file__).resolve()
    root = script_path.parents[1]
    corpus_path = args.corpus if args.corpus.is_absolute() else root / args.corpus
    freeze_path = args.freeze if args.freeze.is_absolute() else root / args.freeze
    output_path = args.output if args.output.is_absolute() else root / args.output

    try:
        require_clean_source_repository(root)
        for commit in (ARM_A_COMMIT, ARM_B_COMMIT):
            require_commit_present(root, commit)
        corpus = load_corpus(corpus_path, relpath=args.corpus.as_posix())
        verify_corpus_integrity(corpus, freeze_path)
    except (ExperimentError, OSError) as exc:
        print(f"FAIL preflight: {exc}")
        return 1

    planned = plan_requests(corpus)
    by_id = {item.specimen_id: item for item in corpus.specimens}
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = args.worktree_root or (root.parent / f".oic-negative-stability-{stamp}")
    base = base if base.is_absolute() else Path.cwd() / base
    worktrees = {label: base / f"arm-{label}" for label in ARM_LABELS}
    created: list[str] = []
    fingerprints: dict[str, dict[str, str]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    cleanup: dict[str, str] = {}

    try:
        base.mkdir(parents=True, exist_ok=True)
        for label in ARM_LABELS:
            create_arm_worktree(root, ARM_COMMITS[label], worktrees[label])
            created.append(label)
            fingerprints[label] = arm_fingerprint(worktrees[label])
        for label in ARM_LABELS:
            bindings[label] = verify_arm_binding(worktree=worktrees[label], script_path=script_path)
        require_distinguishable_arms(bindings)
        print(f"Arms materialized under {base}")
        for label in ARM_LABELS:
            print(f"  arm {label} @ {ARM_COMMITS[label]}")
            for relpath, digest in sorted(fingerprints[label].items()):
                print(f"    {relpath}  sha256={digest}")
            binding = bindings[label]
            print(f"    bound module   {binding['resolved_module_path']}")
            print(f"    prompt sha256  {binding['system_prompt_sha256']}")
        print("Arms verified distinguishable.")
        print(
            f"Executing {len(planned)} requests against {args.model}, "
            f"pacing {args.pacing_seconds}s, no retries."
        )
        attempts: list[Attempt] = []
        for request in planned:
            attempt = execute_request(
                request,
                specimen=by_id[request.specimen_id],
                corpus=corpus,
                worktree=worktrees[request.arm],
                model=args.model,
                script_path=script_path,
                timeout_seconds=args.request_timeout_seconds,
            )
            attempts.append(attempt)
            marker = "FP" if attempt.false_positive else attempt.outcome
            print(
                f"[{request.sequence:>3}/{len(planned)}] arm={request.arm} "
                f"{request.specimen_id} run={request.run_index} -> {marker} "
                f"candidates={attempt.candidate_count}"
            )
            if args.pacing_seconds > 0:
                time.sleep(args.pacing_seconds)
    finally:
        for label in created:
            cleanup[label] = remove_arm_worktree(root, worktrees[label])
        if base.exists() and not any(base.iterdir()):
            base.rmdir()
        elif base.exists():
            cleanup["worktree_root"] = f"NOT REMOVED (not empty): {base}"

    head = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain")
    receipt = build_receipt(
        corpus=corpus,
        attempts=attempts,
        planned=planned,
        model=args.model,
        pacing_seconds=args.pacing_seconds,
        arm_fingerprints=fingerprints,
        arm_bindings=bindings,
        arm_worktrees={label: str(path) for label, path in worktrees.items()},
        cleanup=cleanup,
        corpus_freeze_relpath=args.freeze.as_posix(),
        orchestrator_commit={
            "commit": head.stdout.strip() if head.returncode == 0 else None,
            "worktree_clean": status.returncode == 0 and not status.stdout.strip(),
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json_bytes(receipt))

    interpretation = receipt["interpretation"]
    print(f"\nReceipt written to {output_path}")
    print(
        "OBSERVED  003 false positives={a}  004 false positives={b}  delta={d}".format(
            a=interpretation[f"arm_{ARM_A_LABEL}_false_positive_events"],
            b=interpretation[f"arm_{ARM_B_LABEL}_false_positive_events"],
            d=interpretation["delta_004_minus_003"],
        )
    )
    print(f"PREREGISTERED BAND  {interpretation['band']}")
    print(
        "This is characterization, not adjudication. The band restates the preregistered "
        "rules; it decides no architecture and authorizes no prompt change."
    )
    for label, state in sorted(cleanup.items()):
        if state != "removed":
            print(f"WARNING arm worktree cleanup: {label}: {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
