"""Behavioural tests for the credential pattern scan.

The scan runs in CI's `lint` job, so a false positive blocks every pull request and a
false negative defeats the control. Both directions are exercised here against throwaway
git repositories rather than against this checkout.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

SCRIPT_RELPATH = "scripts/scan_forbidden_patterns.sh"

ENV_EXAMPLE_PLACEHOLDERS = """\
POSTGRES_USER=oic_dev
POSTGRES_PASSWORD=CHANGEME_local_dev_only
MINIO_ROOT_PASSWORD=CHANGEME_local_dev_only
API_KEY=<replace-with-your-key>
"""


@pytest.fixture(scope="module")
def script(repo_root: Path) -> Path:
    path = repo_root / SCRIPT_RELPATH
    assert path.is_file()
    return path


def _scan(workspace: Path, script: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Build a throwaway git repo containing ``files`` and run the scan inside it."""
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=workspace, check=True)

    target_script = workspace / SCRIPT_RELPATH
    target_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(script, target_script)

    for relpath, content in files.items():
        destination = workspace / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    return subprocess.run(
        ["bash", SCRIPT_RELPATH],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# True positives
# ---------------------------------------------------------------------------


# Synthetic values only: the AWS entry is Amazon's own published example key id, and the
# rest are structurally valid but meaningless strings. None authenticates against
# anything. Each carries the allowlist pragma because it must trip the scan when written
# into a temporary repository, while this file itself is also scanned in CI.
PLANTED_CREDENTIALS: tuple[tuple[str, str], ...] = (
    ("aws", "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"),  # pragma: allowlist secret
    ("github", "tok: ghp_abcdefghijklmnopqrstuvwxyz0123456789AB\n"),  # pragma: allowlist secret
    ("stripe", "key = sk_live_abcdefghijklmnop0123\n"),  # pragma: allowlist secret
    ("google", "G=AIzaSyA1234567890abcdefghijklmnopqrstuvw\n"),  # pragma: allowlist secret
    ("private key", "-----BEGIN RSA PRIVATE KEY-----\nabc\n"),  # pragma: allowlist secret
    ("assignment", 'password = "correcthorsebatterystaple42"\n'),  # pragma: allowlist secret
)


@pytest.mark.parametrize(("label", "content"), PLANTED_CREDENTIALS)
def test_scan_detects_planted_credentials(
    tmp_path: Path, script: Path, label: str, content: str
) -> None:
    result = _scan(tmp_path, script, {"config.txt": content})
    assert result.returncode == 1, f"{label} was not detected:\n{result.stdout}"
    assert "FAILED" in result.stdout


def test_scan_rejects_a_committed_env_file(tmp_path: Path, script: Path) -> None:
    result = _scan(tmp_path, script, {".env": "POSTGRES_PASSWORD=whatever\n"})
    assert result.returncode == 1
    assert ".env is tracked by git" in result.stdout


# ---------------------------------------------------------------------------
# True negatives
# ---------------------------------------------------------------------------


def test_scan_permits_placeholder_values_in_an_env_example(tmp_path: Path, script: Path) -> None:
    """`.env.example` must stay readable.

    The scan documents placeholders as permitted; this asserts the implementation agrees,
    because a false positive here would block every pull request.
    """
    result = _scan(tmp_path, script, {"docker/.env.example": ENV_EXAMPLE_PLACEHOLDERS})
    assert result.returncode == 0, result.stdout
    assert "passed" in result.stdout


def test_scan_permits_a_reviewed_false_positive_pragma(tmp_path: Path, script: Path) -> None:
    content = 'password = "looks_like_a_real_secret_value"  # pragma: allowlist secret\n'
    result = _scan(tmp_path, script, {"fixture.py": content})
    assert result.returncode == 0, result.stdout


def test_scan_passes_on_an_ordinary_repository(tmp_path: Path, script: Path) -> None:
    result = _scan(tmp_path, script, {"README.md": "# hello\n", "main.py": "print(1)\n"})
    assert result.returncode == 0, result.stdout


# ---------------------------------------------------------------------------
# Honesty about scope
# ---------------------------------------------------------------------------


def test_scan_reports_its_limitations_on_success(tmp_path: Path, script: Path) -> None:
    """A passing run must not read as an assurance that no secrets exist."""
    result = _scan(tmp_path, script, {"README.md": "# hello\n"})
    assert result.returncode == 0
    assert "LIMITATIONS" in result.stdout
    assert "not" in result.stdout and "evidence that the repository contains no secrets" in (
        result.stdout
    )


def test_scan_does_not_claim_to_cover_git_history(tmp_path: Path, script: Path) -> None:
    result = _scan(tmp_path, script, {"README.md": "# hello\n"})
    assert "does" in result.stdout
    assert "git history" in result.stdout


def test_this_repository_passes_the_scan(repo_root: Path, script: Path) -> None:
    result = subprocess.run(
        ["bash", SCRIPT_RELPATH],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
