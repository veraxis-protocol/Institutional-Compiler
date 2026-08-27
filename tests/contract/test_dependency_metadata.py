"""Contract tests keeping declared dependency metadata and the locked environment aligned.

The failure this prevents actually happened: ``pyproject.toml`` declared
``referencing>=0.35,<0.37`` while the lockfile installed ``0.37.0``. Nothing failed at
import time, so the mismatch was invisible until ``pip check`` was run by hand. These
tests make the disagreement a build failure.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from importlib.metadata import distribution, distributions
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

pytestmark = pytest.mark.contract

DISTRIBUTION = "oic"

#: Runtime dependencies this package imports directly and must therefore declare.
DIRECTLY_IMPORTED = {"jsonschema", "referencing"}


@pytest.fixture(scope="module")
def pyproject(repo_root: Path) -> dict[str, object]:
    return tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def declared_requirements(pyproject: dict[str, object]) -> list[Requirement]:
    project = pyproject["project"]
    assert isinstance(project, dict)
    return [Requirement(spec) for spec in project["dependencies"]]


def _locked_versions(repo_root: Path, lockfile: str) -> dict[str, str]:
    """Parse ``name==version`` pins out of a hash-pinned requirements file."""
    text = (repo_root / "requirements" / lockfile).read_text(encoding="utf-8")
    pins: dict[str, str] = {}
    for match in re.finditer(r"^([A-Za-z0-9._-]+)==([^\s\\]+)", text, re.MULTILINE):
        pins[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pins


# ---------------------------------------------------------------------------
# Declared vs installed
# ---------------------------------------------------------------------------


def test_pip_check_passes(repo_root: Path) -> None:
    """The installed environment must satisfy every declared requirement."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No broken requirements found" in result.stdout


def test_installed_versions_satisfy_declared_ranges(
    declared_requirements: list[Requirement],
) -> None:
    """Each declared range must actually admit the installed version."""
    violations: list[str] = []
    for requirement in declared_requirements:
        installed = Version(distribution(requirement.name).version)
        if not requirement.specifier.contains(installed, prereleases=True):
            violations.append(f"{requirement} but {requirement.name}=={installed} is installed")
    assert violations == []


def test_directly_imported_packages_are_declared(
    declared_requirements: list[Requirement],
) -> None:
    """A package imported by `oic` must be a declared dependency, not an accident.

    `referencing` arrives transitively through `jsonschema`, so omitting it would appear
    to work while leaving this package at the mercy of a jsonschema upgrade.
    """
    declared = {requirement.name.lower() for requirement in declared_requirements}
    assert declared >= DIRECTLY_IMPORTED


def test_source_only_imports_declared_third_party_packages(repo_root: Path) -> None:
    """No src module may import a third-party package outside the declared set."""
    stdlib = set(sys.stdlib_module_names)
    declared = DIRECTLY_IMPORTED | {"oic"}
    offenders: list[str] = []
    for module in sorted((repo_root / "src" / "oic").glob("*.py")):
        for match in re.finditer(
            r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", module.read_text("utf-8"), re.M
        ):
            top = match.group(1)
            if top not in stdlib and top not in declared and top != "__future__":
                offenders.append(f"{module.name}: {top}")
    assert offenders == []


# ---------------------------------------------------------------------------
# Declared vs locked
# ---------------------------------------------------------------------------


def test_lockfiles_satisfy_declared_ranges(
    repo_root: Path, declared_requirements: list[Requirement]
) -> None:
    for lockfile in ("runtime.txt", "dev.txt"):
        pins = _locked_versions(repo_root, lockfile)
        for requirement in declared_requirements:
            key = requirement.name.lower().replace("_", "-")
            assert key in pins, f"{key} is not pinned in {lockfile}"
            assert requirement.specifier.contains(Version(pins[key]), prereleases=True), (
                f"{lockfile} pins {key}=={pins[key]}, outside {requirement.specifier}"
            )


def test_runtime_in_and_pyproject_agree(repo_root: Path, pyproject: dict[str, object]) -> None:
    """The `.in` file and `pyproject.toml` must state the same ranges."""
    text = (repo_root / "requirements" / "runtime.in").read_text(encoding="utf-8")
    from_in = {
        Requirement(line.strip()).name.lower(): Requirement(line.strip())
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    project = pyproject["project"]
    assert isinstance(project, dict)
    from_toml = {
        Requirement(spec).name.lower(): Requirement(spec) for spec in project["dependencies"]
    }

    assert set(from_in) == set(from_toml)
    for name, requirement in from_toml.items():
        assert str(from_in[name].specifier) == str(requirement.specifier), name


def test_dev_lock_is_a_superset_of_the_runtime_lock(repo_root: Path) -> None:
    runtime = _locked_versions(repo_root, "runtime.txt")
    dev = _locked_versions(repo_root, "dev.txt")
    for name, version in runtime.items():
        assert name in dev, f"{name} is locked for runtime but absent from dev"
        assert dev[name] == version, f"{name}: runtime pins {version}, dev pins {dev[name]}"


def test_lockfiles_are_hash_pinned(repo_root: Path) -> None:
    for lockfile in ("runtime.txt", "dev.txt"):
        text = (repo_root / "requirements" / lockfile).read_text(encoding="utf-8")
        assert "--hash=sha256:" in text
        pins = _locked_versions(repo_root, lockfile)
        assert pins, f"{lockfile} contains no pins"
        # Every pinned distribution must carry at least one hash.
        assert text.count("--hash=sha256:") >= len(pins)


def test_installed_versions_match_the_dev_lock(repo_root: Path) -> None:
    """The environment running these tests must be the locked one."""
    pins = _locked_versions(repo_root, "dev.txt")
    installed = {
        dist.metadata["Name"].lower().replace("_", "-"): dist.version
        for dist in distributions()
        if dist.metadata["Name"]
    }
    drift = [
        f"{name}: locked {version}, installed {installed[name]}"
        for name, version in pins.items()
        if name in installed and installed[name] != version
    ]
    assert drift == []


# ---------------------------------------------------------------------------
# Boundary discipline
# ---------------------------------------------------------------------------


def test_no_forbidden_dependency_is_declared_or_locked(repo_root: Path) -> None:
    """No LLM SDK, model provider, web framework, database driver, or Docling."""
    forbidden = {
        "anthropic",
        "openai",
        "langchain",
        "llama-index",
        "transformers",
        "torch",
        "docling",
        "fastapi",
        "uvicorn",
        "starlette",
        "sqlalchemy",
        "psycopg",
        "psycopg2",
        "asyncpg",
        "boto3",
    }
    for lockfile in ("runtime.txt", "dev.txt"):
        pins = set(_locked_versions(repo_root, lockfile))
        overlap = sorted(forbidden & pins)
        assert overlap == [], f"{lockfile} locks forbidden dependencies: {overlap}"


def test_package_declares_polyform_license_file(
    repo_root: Path, pyproject: dict[str, object]
) -> None:
    project = pyproject["project"]
    assert isinstance(project, dict)
    assert "license" not in project
    assert project["license-files"] == ["LICENSE"]
    license_text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("# PolyForm Noncommercial License 1.0.0\n")
    classifiers = project.get("classifiers", [])
    assert isinstance(classifiers, list)
    assert not any("License" in str(item) for item in classifiers)
