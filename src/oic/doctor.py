"""Environment diagnostics for the non-semantic foundation.

What this reports
-----------------
Python version, repository-root detection, the presence and version of local tools,
whether the infrastructure profiles (PostgreSQL, MinIO, OPA) are configured, and the
current state of the ZTL and VEIP boundaries and the semantic implementation gate.

Tri-state, never boolean
------------------------
Every check reports :class:`Availability` or :class:`Configured` - three states, one of
which is ``UNKNOWN``. Invariant I-03 says unknown never serializes as grounded false, and
that discipline applies to infrastructure data too, not only to institutional meaning. A
tool that is on ``PATH`` but whose version cannot be read is ``UNKNOWN``, not "absent"
and not "broken". :func:`DoctorReport.to_json` is asserted by the test suite to contain
no boolean values at all, so there is nowhere for an unknown to collapse into a false.

What this never reports
-----------------------
Production readiness, enterprise readiness, or compliance of any kind. ZTL and VEIP are
always reported as ``PROVISIONAL / NOT CONFIGURED`` and bounded semantic implementation
as owner-authorized. These governance states cannot be flipped by host state.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Final

from oic.errors import ConfigurationError
from oic.paths import find_repo_root

__all__ = [
    "COMPOSE_RELPATH",
    "PROVISIONAL_BOUNDARY_STATUS",
    "REQUIRED_PYTHON",
    "SEMANTIC_GATE_STATUS",
    "Availability",
    "BoundaryReport",
    "CheckResult",
    "Configured",
    "DoctorReport",
    "run_doctor",
]

#: Fixed governance strings. These are statements about `STATUS.md`, not about the host.
PROVISIONAL_BOUNDARY_STATUS: Final[str] = "PROVISIONAL / NOT CONFIGURED"
SEMANTIC_GATE_STATUS: Final[str] = "OWNER-AUTHORIZED BOUNDED IMPLEMENTATION"
REQUIRED_PYTHON: Final[str] = ">=3.12,<3.13"
COMPOSE_RELPATH: Final[str] = "docker/compose.yaml"

_PROBE_TIMEOUT_SECONDS: Final[float] = 20.0


class Availability(Enum):
    """Whether a local tool could be found and identified."""

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNKNOWN = "UNKNOWN"


class Configured(Enum):
    """Whether an infrastructure profile is declared in the repository."""

    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One diagnostic line."""

    name: str
    status: str
    value: str | None = None
    note: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return {"name": self.name, "note": self.note, "status": self.status, "value": self.value}

    def render(self) -> str:
        line = f"  {self.name:<28} {self.status}"
        if self.value:
            line += f"  {self.value}"
        if self.note:
            line += f"\n      {self.note}"
        return line


@dataclass(frozen=True, slots=True)
class BoundaryReport:
    """A provisional external boundary that must never be reported as active."""

    name: str
    status: str
    gate: str

    def to_json(self) -> dict[str, str]:
        return {"gate": self.gate, "name": self.name, "status": self.status}


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """Complete diagnostic output."""

    repository_root: str | None
    environment: tuple[CheckResult, ...]
    tools: tuple[CheckResult, ...]
    infrastructure: tuple[CheckResult, ...]
    boundaries: tuple[BoundaryReport, ...]
    gates: tuple[CheckResult, ...]
    notices: tuple[str, ...] = field(default=())

    def to_json(self) -> dict[str, Any]:
        """Deterministic JSON payload.

        Contains no boolean values by construction; see the module docstring.
        """
        return {
            "boundaries": [boundary.to_json() for boundary in self.boundaries],
            "environment": [check.to_json() for check in self.environment],
            "gates": [check.to_json() for check in self.gates],
            "infrastructure": [check.to_json() for check in self.infrastructure],
            "notices": list(self.notices),
            "repository_root": self.repository_root,
            "tools": [check.to_json() for check in self.tools],
        }


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------


def _probe_version(executable: str, args: Sequence[str]) -> CheckResult:
    """Locate a tool and read its version.

    Returns ``NOT_AVAILABLE`` only when the executable is genuinely absent from ``PATH``.
    A tool that is present but does not answer a version probe is ``UNKNOWN``: not
    finding an answer is not the same as finding a negative one.
    """
    location = shutil.which(executable)
    if location is None:
        return CheckResult(
            name=executable,
            status=Availability.NOT_AVAILABLE.value,
            note="not found on PATH",
        )
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv from a resolved absolute path
            [location, *args],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(
            name=executable,
            status=Availability.UNKNOWN.value,
            note=f"found on PATH but the version probe failed: {type(exc).__name__}",
        )
    if completed.returncode != 0:
        return CheckResult(
            name=executable,
            status=Availability.UNKNOWN.value,
            note=f"found on PATH but the version probe exited {completed.returncode}",
        )
    output = (completed.stdout or completed.stderr or "").strip()
    first_line = output.splitlines()[0].strip() if output else ""
    if not first_line:
        return CheckResult(
            name=executable,
            status=Availability.UNKNOWN.value,
            note="found on PATH but the version probe produced no output",
        )
    return CheckResult(
        name=executable,
        status=Availability.AVAILABLE.value,
        value=first_line,
    )


_TOOL_PROBES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("git", ("--version",)),
    ("python3", ("--version",)),
    ("ruff", ("--version",)),
    ("mypy", ("--version",)),
    ("pytest", ("--version",)),
    ("pre-commit", ("--version",)),
    ("cyclonedx-py", ("--version",)),
    ("docker", ("--version",)),
    ("opa", ("version",)),
)


def _compose_profile(
    compose_text: str | None, service: str, *, absent_reason: str | None
) -> CheckResult:
    """Report whether an infrastructure service is declared in the compose file.

    A compose file that exists but cannot be read yields ``UNKNOWN``: failing to read a
    declaration is not evidence that the declaration is missing. Only a compose file that
    is genuinely absent, or present without the service, yields ``NOT_CONFIGURED``.
    """
    if compose_text is None:
        return CheckResult(
            name=f"{service} profile",
            status=(Configured.NOT_CONFIGURED if absent_reason else Configured.UNKNOWN).value,
            note=absent_reason or f"{COMPOSE_RELPATH} exists but could not be read",
        )
    if f"{service}:" in compose_text:
        return CheckResult(
            name=f"{service} profile",
            status=Configured.CONFIGURED.value,
            note=f"declared in {COMPOSE_RELPATH}; not started by this command",
        )
    return CheckResult(
        name=f"{service} profile",
        status=Configured.NOT_CONFIGURED.value,
        note=f"no '{service}' service in {COMPOSE_RELPATH}",
    )


def run_doctor(root: Path | None = None) -> DoctorReport:
    """Collect diagnostics. Reads only; starts nothing and contacts nothing."""
    notices: list[str] = []

    if root is not None:
        repository_root: Path | None = root
        root_check = CheckResult(
            name="repository root",
            status="DETECTED",
            value=str(root),
            note="supplied explicitly",
        )
    else:
        try:
            repository_root = find_repo_root()
            root_check = CheckResult(
                name="repository root",
                status="DETECTED",
                value=str(repository_root),
                note="located by walking up to BOOTSTRAP_MANIFEST.json",
            )
        except ConfigurationError as exc:
            repository_root = None
            root_check = CheckResult(
                name="repository root",
                status="NOT_DETECTED",
                note=str(exc),
            )

    python_version = platform.python_version()
    supported = sys.version_info[:2] == (3, 12)
    environment = (
        CheckResult(
            name="python version",
            status="SUPPORTED" if supported else "UNSUPPORTED",
            value=python_version,
            note=f"this work order requires Python {REQUIRED_PYTHON}",
        ),
        CheckResult(name="python executable", status="DETECTED", value=sys.executable),
        CheckResult(
            name="platform",
            status="DETECTED",
            value=f"{platform.system()} {platform.release()} ({platform.machine()})",
        ),
        root_check,
    )
    if not supported:
        notices.append(
            f"running on Python {python_version}; this work order targets {REQUIRED_PYTHON}"
        )

    tools = tuple(_probe_version(name, args) for name, args in _TOOL_PROBES)

    compose_text: str | None = None
    absent_reason: str | None = "repository root was not detected"
    if repository_root is not None:
        compose_path = repository_root / COMPOSE_RELPATH
        if compose_path.is_file():
            absent_reason = None
            try:
                compose_text = compose_path.read_text(encoding="utf-8")
            except OSError:
                compose_text = None
        else:
            absent_reason = f"{COMPOSE_RELPATH} is not present"

    infrastructure = (
        _compose_profile(compose_text, "postgres", absent_reason=absent_reason),
        _compose_profile(compose_text, "minio", absent_reason=absent_reason),
        _compose_profile(compose_text, "opa", absent_reason=absent_reason),
        CheckResult(
            name="infrastructure state",
            status="NOT_STARTED_BY_THIS_COMMAND",
            note=(
                "'oic doctor' inspects declarations only; it never starts, connects to, "
                "or queries a container"
            ),
        ),
    )

    boundaries = (
        BoundaryReport(
            name="ZTL",
            status=PROVISIONAL_BOUNDARY_STATUS,
            gate="pinned interface and verification dossier (ADR-009)",
        ),
        BoundaryReport(
            name="VEIP",
            status=PROVISIONAL_BOUNDARY_STATUS,
            gate="pinned public interfaces, fixtures, and conformance evidence (ADR-010)",
        ),
    )

    gates = (
        CheckResult(
            name="semantic implementation gate",
            status=SEMANTIC_GATE_STATUS,
            note="limited by Owner Decision 004; model output has no authority or admission rights",
        ),
        CheckResult(
            name="preflight corpus provenance",
            status="OPEN",
            note="benchmarks/preflight/SOURCE_MANIFEST.csv has no corpus rows",
        ),
        CheckResult(
            name="dependency status",
            status="PARTIAL",
            note="ZTL and VEIP dossiers remain open (DEPENDENCIES.md)",
        ),
        CheckResult(
            name="release status",
            status="OWNER-AUTHORIZED BOUNDED SEMANTIC IMPLEMENTATION - PRE-EXTERNAL-REVIEW",
            note=(
                "NOT PRODUCTION READY. This repository makes no quality, "
                "enterprise-readiness, security, or legal-compliance claim."
            ),
        ),
    )

    notices.append(
        "This command reports infrastructure state only. It performs no institutional "
        "interpretation, admission, or enforcement."
    )

    return DoctorReport(
        repository_root=str(repository_root) if repository_root is not None else None,
        environment=environment,
        tools=tools,
        infrastructure=infrastructure,
        boundaries=boundaries,
        gates=gates,
        notices=tuple(notices),
    )
