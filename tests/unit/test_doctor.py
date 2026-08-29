"""Tests for environment diagnostics.

The load-bearing assertions here are the negative ones: that ``doctor`` never reports the
system as production-ready, never describes ZTL or VEIP as active, never reports the
semantic gate as anything but BLOCKED, and never collapses an unknown into a false.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from oic.doctor import (
    PROVISIONAL_BOUNDARY_STATUS,
    SEMANTIC_GATE_STATUS,
    Availability,
    Configured,
    DoctorReport,
    run_doctor,
)


@pytest.fixture(scope="module")
def report(repo_root: Path) -> DoctorReport:
    """One shared report.

    ``run_doctor`` shells out to every tool probe, so building it per test would make
    this module dominate the suite runtime. It reads only, so sharing is safe.
    """
    return run_doctor(repo_root)


def _walk(node: object) -> list[object]:
    """Flatten every value in a nested JSON structure."""
    if isinstance(node, dict):
        return [value for child in node.values() for value in _walk(child)]
    if isinstance(node, list):
        return [value for child in node for value in _walk(child)]
    return [node]


# ---------------------------------------------------------------------------
# Unknown is never false
# ---------------------------------------------------------------------------


def test_report_contains_no_boolean_values(report: DoctorReport) -> None:
    """Invariant I-03 applied to infrastructure data.

    If no field is a boolean, there is nowhere for an unknown state to collapse into a
    grounded false.
    """
    booleans = [value for value in _walk(report.to_json()) if isinstance(value, bool)]
    assert booleans == []


def test_tool_present_but_unqueryable_is_unknown_not_absent(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed probe must not be recorded as "the tool is missing"."""
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def _explode(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OSError("probe exploded")

    monkeypatch.setattr(subprocess, "run", _explode)
    result = run_doctor(repo_root)
    statuses = {check.status for check in result.tools}
    assert statuses == {Availability.UNKNOWN.value}
    assert Availability.NOT_AVAILABLE.value not in statuses


def test_probe_timeout_is_unknown(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def _timeout(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd="probe", timeout=1.0)

    monkeypatch.setattr(subprocess, "run", _timeout)
    result = run_doctor(repo_root)
    assert all(check.status == Availability.UNKNOWN.value for check in result.tools)


def test_nonzero_probe_exit_is_unknown(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def _nonzero(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        return subprocess.CompletedProcess(args=["probe"], returncode=127, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _nonzero)
    result = run_doctor(repo_root)
    assert all(check.status == Availability.UNKNOWN.value for check in result.tools)


def test_tool_absent_from_path_is_not_available(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = run_doctor(repo_root)
    assert all(check.status == Availability.NOT_AVAILABLE.value for check in result.tools)


def test_unreadable_compose_file_is_unknown_not_not_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    compose = tmp_path / "docker" / "compose.yaml"
    compose.parent.mkdir(parents=True)
    compose.write_text("services:\n  postgres:\n", encoding="utf-8")

    def _unreadable(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", _unreadable)
    result = run_doctor(tmp_path)
    profiles = [check for check in result.infrastructure if check.name.endswith("profile")]
    assert all(check.status == Configured.UNKNOWN.value for check in profiles)


# ---------------------------------------------------------------------------
# Required reporting
# ---------------------------------------------------------------------------


def test_reports_python_version(report: DoctorReport) -> None:
    check = next(c for c in report.environment if c.name == "python version")
    assert check.value is not None
    assert check.value.count(".") == 2


def test_reports_repository_root(report: DoctorReport, repo_root: Path) -> None:
    check = next(c for c in report.environment if c.name == "repository root")
    assert check.status == "DETECTED"
    assert report.repository_root == str(repo_root)


def test_root_detection_failure_is_reported_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    from oic.errors import ConfigurationError

    def _fail() -> Path:
        raise ConfigurationError("no root")

    monkeypatch.setattr("oic.doctor.find_repo_root", _fail)
    result = run_doctor(None)
    check = next(c for c in result.environment if c.name == "repository root")
    assert check.status == "NOT_DETECTED"
    assert result.repository_root is None


@pytest.mark.parametrize("tool", ["docker", "opa", "git"])
def test_reports_required_local_tools(report: DoctorReport, tool: str) -> None:
    names = {check.name for check in report.tools}
    assert tool in names


@pytest.mark.parametrize("service", ["postgres", "minio", "opa"])
def test_reports_infrastructure_profiles(report: DoctorReport, service: str) -> None:
    check = next(c for c in report.infrastructure if c.name == f"{service} profile")
    assert check.status == Configured.CONFIGURED.value
    assert check.note is not None
    assert "not started by this command" in check.note


def test_never_starts_infrastructure(report: DoctorReport) -> None:
    check = next(c for c in report.infrastructure if c.name == "infrastructure state")
    assert check.status == "NOT_STARTED_BY_THIS_COMMAND"


# ---------------------------------------------------------------------------
# Boundaries and gates
# ---------------------------------------------------------------------------


def test_ztl_and_veip_are_provisional_and_not_configured(report: DoctorReport) -> None:
    names = {boundary.name: boundary for boundary in report.boundaries}
    assert set(names) == {"ZTL", "VEIP"}
    for boundary in report.boundaries:
        assert boundary.status == PROVISIONAL_BOUNDARY_STATUS
        assert boundary.status == "PROVISIONAL / NOT CONFIGURED"


@pytest.mark.parametrize("forbidden", ["ACTIVE", "ENABLED", "INTEGRATED", "CONNECTED", "READY"])
def test_doctor_never_describes_ztl_or_veip_as_active(report: DoctorReport, forbidden: str) -> None:
    for boundary in report.boundaries:
        assert forbidden not in boundary.status.upper()
        assert forbidden not in boundary.gate.upper()


def test_semantic_gate_is_bounded_owner_authorized(report: DoctorReport) -> None:
    check = next(c for c in report.gates if c.name == "semantic implementation gate")
    assert check.status == SEMANTIC_GATE_STATUS == "OWNER-AUTHORIZED BOUNDED IMPLEMENTATION"


def test_corpus_and_dependency_gates_are_not_reported_complete(report: DoctorReport) -> None:
    statuses = {check.name: check.status for check in report.gates}
    assert statuses["preflight corpus provenance"] == "OPEN"
    assert statuses["dependency status"] == "PARTIAL"
    assert "COMPLETE" not in " ".join(statuses.values()).upper()


def test_release_status_states_not_production_ready(report: DoctorReport) -> None:
    check = next(c for c in report.gates if c.name == "release status")
    assert check.note is not None
    assert "NOT PRODUCTION READY" in check.note


# ---------------------------------------------------------------------------
# Forbidden claims
# ---------------------------------------------------------------------------

#: Phrases CLAIMS.md forbids at the current status.
FORBIDDEN_CLAIM_PHRASES = (
    "enterprise-ready",
    "enterprise ready",
    "production ready",
    "guarantees legal",
    "guarantees compliance",
    "legally compliant",
    "regulatory compliance",
    "eliminates human review",
    "autonomously determines",
    "first institutional compiler",
    "best institutional compiler",
    "outperforms",
    "state of the art",
    "state-of-the-art",
)


def _all_text(report: DoctorReport) -> str:
    return " ".join(str(value) for value in _walk(report.to_json()) if value is not None).lower()


@pytest.mark.parametrize("phrase", FORBIDDEN_CLAIM_PHRASES)
def test_doctor_output_contains_no_forbidden_claim(report: DoctorReport, phrase: str) -> None:
    text = _all_text(report)
    if phrase == "production ready":
        # The only permitted occurrence is the explicit negation.
        assert "not production ready" in text
        assert text.count("production ready") == text.count("not production ready")
    else:
        assert phrase not in text


def test_report_is_deterministic_for_static_sections(repo_root: Path) -> None:
    """Gate, boundary, and notice content must not vary between runs."""
    first = run_doctor(repo_root)
    second = run_doctor(repo_root)
    assert first.to_json()["gates"] == second.to_json()["gates"]
    assert first.to_json()["boundaries"] == second.to_json()["boundaries"]
    assert first.to_json()["notices"] == second.to_json()["notices"]
