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
    "dependency-review",
    "advisory-scan",
    "bootstrap-integrity",
    "schema-validation",
    "lint",
    "typecheck",
    "test",
    "sbom",
    "compose-validation",
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
        allowed = (
            {"contents": "read", "pull-requests": "read"}
            if name == "dependency-review"
            else {"contents": "read"}
        )
        assert "permissions" not in job or job["permissions"] == allowed, name


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


def test_dependency_review_and_advisory_scan_are_present(
    workflow: dict[Any, Any], workflow_text: str, repo_root: Path
) -> None:
    review = workflow["jobs"]["dependency-review"]
    assert any("dependency-review-action" in step.get("uses", "") for step in review["steps"])
    audit = workflow["jobs"]["advisory-scan"]
    assert any("pip_audit" in str(step.get("run", "")) for step in audit["steps"])
    dev_input = (repo_root / "requirements/dev.in").read_text(encoding="utf-8")
    assert "pip-audit==2.10.1" in dev_input


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


def test_bootstrap_job_verifies_the_historical_baseline(workflow_text: str) -> None:
    """CI must verify the bootstrap from Git objects, not against the working tree.

    A working-tree comparison makes every listed path permanently immutable and fails
    the first time a Class C artifact legitimately changes (ADR-012).
    """
    assert "oic.cli verify-bootstrap" in workflow_text
    assert "verify-manifest --manifest BOOTSTRAP_MANIFEST.json" not in workflow_text


def test_jobs_needing_the_bootstrap_commit_fetch_full_history(workflow: dict[Any, Any]) -> None:
    """Baseline verification reads Git objects, so a shallow clone silently breaks it.

    actions/checkout defaults to fetch-depth 1, which omits the bootstrap commit
    entirely. Both jobs that touch the baseline must ask for full history.
    """
    for name in ("bootstrap-integrity", "test"):
        checkout = next(
            step
            for step in workflow["jobs"][name]["steps"]
            if "actions/checkout" in step.get("uses", "")
        )
        assert checkout.get("with", {}).get("fetch-depth") == 0, name


def test_cli_invocations_in_ci_place_global_flags_before_the_subcommand(
    workflow_text: str,
) -> None:
    """`--format` after the subcommand once exited 2 with "unrecognized arguments".

    The CLI now accepts either order, but CI keeps the canonical form so the workflow
    stays readable and does not depend on that tolerance.
    """
    bad = re.findall(r"oic\.cli\s+\S+.*?--format", workflow_text)
    assert bad == [], f"global flag placed after a subcommand: {bad}"


def test_every_locked_install_is_followed_by_pip_check(workflow_text: str) -> None:
    """Declared metadata and the installed environment must be proven consistent.

    `pyproject.toml` once declared a `referencing` range the lockfile did not satisfy;
    nothing failed until `pip check` was run by hand.
    """
    installs = workflow_text.count("pip install --require-hashes -r requirements/dev.txt")
    checks = workflow_text.count("python -m pip check")
    assert installs > 0
    assert checks >= installs, f"{installs} locked installs but only {checks} pip check runs"


def test_wheel_is_smoke_tested_but_never_published(workflow_text: str) -> None:
    assert "scripts/wheel_smoke_test.sh" in workflow_text
    for phrase in ("twine", "pypi", "--repository"):
        assert phrase not in workflow_text.lower()


def test_compose_job_runs_config_pull_start_health_and_cleanup(
    workflow: dict[Any, Any],
) -> None:
    """Structural assertions are not enough; CI must actually run the stack."""
    job = workflow["jobs"]["compose-validation"]
    steps = " ".join(str(step.get("run", "")) for step in job["steps"])
    for phrase in ("docker compose version", "config", "pull", "up -d", "ps"):
        assert phrase in steps, phrase
    assert "down -v --remove-orphans" in steps
    assert "State.Health.Status" in steps, "health must be asserted, not assumed"


def test_compose_job_always_tears_down(workflow: dict[Any, Any]) -> None:
    """Cleanup must run even when an earlier step fails, or runners leak volumes."""
    job = workflow["jobs"]["compose-validation"]
    teardown = [s for s in job["steps"] if "down -v" in str(s.get("run", ""))]
    assert teardown, "no teardown step"
    assert all(step.get("if") == "always()" for step in teardown)


def test_compose_job_uses_no_secret_and_no_real_env_file(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["compose-validation"]
    steps = " ".join(str(step.get("run", "")) for step in job["steps"])
    assert "docker/.env.example" in steps
    assert "docker/.env " not in steps
    assert "secrets." not in steps


def test_compose_job_adds_no_application_ztl_or_veip_container(workflow: dict[Any, Any]) -> None:
    job = workflow["jobs"]["compose-validation"]
    steps = " ".join(str(step.get("run", "")) for step in job["steps"]).lower()
    for forbidden in ("ztl", "veip", "rego", "policy", "--bundle"):
        assert forbidden not in steps


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
