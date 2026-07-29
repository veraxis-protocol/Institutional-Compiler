"""Contract tests over the CI workflow's supply-chain guarantees.

These assert properties a reviewer would otherwise have to re-check by eye on every
change to the workflow: that actions stay pinned to immutable commit SHAs, that no job
acquires write permission, and that no release or deployment step appears.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.contract

WORKFLOW_RELPATH = "/".join((".github", "workflows", "ci.yml"))

REQUIRED_JOBS = {
    "bootstrap-integrity",
    "schema-validation",
    "lint",
    "typecheck",
    "test",
    "sbom",
}

#: `owner/repo@<40 hex>`, optionally followed by a `# vX.Y.Z` comment.
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w.-]+)*@[0-9a-f]{40}$")


@pytest.fixture(scope="module")
def workflow(repo_root: Path) -> dict[Any, Any]:
    yaml = pytest.importorskip("yaml", reason="PyYAML ships with pre-commit's dependencies")
    text = (repo_root / WORKFLOW_RELPATH).read_text(encoding="utf-8")
    document: dict[Any, Any] = yaml.safe_load(text)
    return document


@pytest.fixture(scope="module")
def workflow_text(repo_root: Path) -> str:
    return (repo_root / WORKFLOW_RELPATH).read_text(encoding="utf-8")


def _steps(workflow: dict[Any, Any]) -> list[dict[str, Any]]:
    return [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if isinstance(step, dict)
    ]


def test_all_required_jobs_are_present(workflow: dict[Any, Any]) -> None:
    assert set(workflow["jobs"]) >= REQUIRED_JOBS


def test_every_action_is_pinned_to_a_commit_sha(workflow: dict[Any, Any]) -> None:
    """A floating tag can be moved; a commit SHA cannot."""
    uses = [step["uses"] for step in _steps(workflow) if "uses" in step]
    assert uses, "workflow uses no actions; the assertion would be vacuous"
    unpinned = [ref for ref in uses if not PINNED_ACTION.match(ref)]
    assert unpinned == []


def test_workflow_permissions_are_read_only(workflow: dict[Any, Any]) -> None:
    assert workflow["permissions"] == {"contents": "read"}
    for name, job in workflow["jobs"].items():
        assert "permissions" not in job or job["permissions"] == {"contents": "read"}, name


def test_no_job_requests_write_permission(workflow_text: str) -> None:
    for scope in ("contents: write", "packages: write", "id-token: write", "write-all"):
        assert scope not in workflow_text


def test_no_secrets_are_referenced(workflow_text: str) -> None:
    """No job may consume a repository or organization secret.

    Matches the expression form specifically; the workflow's own prose says the word
    "secrets" while asserting it needs none.
    """
    assert re.search(r"\$\{\{\s*secrets\.", workflow_text) is None
    assert "GITHUB_TOKEN" not in workflow_text


def test_checkout_does_not_persist_credentials(workflow: dict[Any, Any]) -> None:
    checkouts = [step for step in _steps(workflow) if "actions/checkout" in step.get("uses", "")]
    assert checkouts
    for step in checkouts:
        assert step.get("with", {}).get("persist-credentials") is False


def test_dependencies_are_installed_with_hash_verification(workflow_text: str) -> None:
    assert "--require-hashes -r requirements/dev.txt" in workflow_text
    # A plain `pip install -r` without hash checking would defeat the lockfile.
    plain = re.findall(r"pip install (?!--require-hashes)(?!--no-deps)-r ", workflow_text)
    assert plain == []


def test_workflow_declares_no_release_or_deployment(workflow: dict[Any, Any]) -> None:
    forbidden_triggers = {"release", "workflow_dispatch", "schedule"}
    # PyYAML resolves the bare key `on:` to the boolean True, so check both spellings.
    triggers: Any = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict)
    assert forbidden_triggers.isdisjoint(triggers)
    assert set(triggers) == {"pull_request", "push"}
    for job in workflow["jobs"].values():
        assert "environment" not in job


def test_no_step_publishes_or_deploys(workflow_text: str) -> None:
    for phrase in (
        "twine upload",
        "pypi",
        "docker push",
        "gh release",
        "git push",
        "aws deploy",
        "kubectl",
    ):
        assert phrase not in workflow_text.lower()


def test_python_version_is_pinned_to_312(workflow: dict[Any, Any]) -> None:
    assert workflow["env"]["PYTHON_VERSION"] == "3.12"


def test_bootstrap_job_pins_the_governing_tdd_digest(workflow_text: str) -> None:
    """The literal digest must appear in the workflow, not only in a manifest.

    If someone rewrote BOOTSTRAP_MANIFEST.json and SHA256SUMS together, a check that only
    compared them to each other would still pass. This literal would not.
    """
    assert "2a4d802130d577e4fb8fee731174ae0f2172ef2d617e3b99f068545d2b9fbf77" in workflow_text


def test_manifest_step_asserts_the_incomplete_exit_code(workflow_text: str) -> None:
    """CI must pin the corpus manifest's expected exit code, not merely tolerate it."""
    assert '"${code}" -ne 3' in workflow_text


def test_secret_scan_documents_its_limitations(repo_root: Path) -> None:
    script = (repo_root / "scripts" / "scan_forbidden_patterns.sh").read_text(encoding="utf-8")
    assert "LIMITATIONS" in script
    assert "not evidence that the repository contains no secrets" in script
    assert "never" in script and "git history" in script
