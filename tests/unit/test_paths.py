"""Tests for repository-root detection and manifest path containment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from oic.errors import ConfigurationError, UnsafeManifestPathError
from oic.paths import REPO_ROOT_ENV_VAR, find_repo_root, relative_to_root, safe_join


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    (tmp_path / "docs" / "tdd").mkdir(parents=True)
    return tmp_path


def test_find_repo_root_walks_upward(fake_root: Path) -> None:
    nested = fake_root / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == fake_root.resolve()


def test_find_repo_root_prefers_env_override(
    fake_root: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    monkeypatch.setenv(REPO_ROOT_ENV_VAR, str(fake_root))
    assert find_repo_root(elsewhere) == fake_root.resolve()


def test_find_repo_root_rejects_bad_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(REPO_ROOT_ENV_VAR, str(tmp_path))
    with pytest.raises(ConfigurationError) as excinfo:
        find_repo_root(tmp_path)
    assert excinfo.value.code == "OIC-1001"


def test_find_repo_root_raises_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(REPO_ROOT_ENV_VAR, raising=False)
    # tmp_path is outside any OIC checkout, but its ancestors are not guaranteed to be,
    # so assert on the error type via a directory we fully control.
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    try:
        root = find_repo_root(isolated)
    except ConfigurationError as exc:
        assert exc.code == "OIC-1001"
    else:  # pragma: no cover - only if the temp dir sits inside a checkout
        assert (root / "BOOTSTRAP_MANIFEST.json").is_file()


def test_safe_join_accepts_ordinary_relative_paths(fake_root: Path) -> None:
    joined = safe_join(fake_root, "docs/tdd/SHA256SUMS")
    assert joined == fake_root.resolve() / "docs" / "tdd" / "SHA256SUMS"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "../outside.txt",
        "docs/../../outside.txt",
        "/etc/passwd",
        "C:/Windows/system32/config",
        "https://example.com/policy.pdf",
        "file:///etc/passwd",
        "\\\\server\\share\\file",
        "docs/\x00evil",
    ],
)
def test_safe_join_rejects_unsafe_paths(fake_root: Path, raw: str) -> None:
    with pytest.raises(UnsafeManifestPathError) as excinfo:
        safe_join(fake_root, raw)
    assert excinfo.value.code == "OIC-1006"
    # The refusal must not echo file content, only the offending path.
    assert "refusing to resolve unsafe manifest path" in str(excinfo.value)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
def test_safe_join_rejects_symlink_escape(
    fake_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("x", encoding="utf-8")
    (fake_root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(UnsafeManifestPathError):
        safe_join(fake_root, "link/secret.txt")


def test_safe_join_allows_the_root_itself(fake_root: Path) -> None:
    assert safe_join(fake_root, ".") == fake_root.resolve()


def test_relative_to_root_is_posix_and_machine_independent(fake_root: Path) -> None:
    target = fake_root / "docs" / "tdd"
    assert relative_to_root(fake_root, target) == "docs/tdd"


def test_relative_to_root_falls_back_outside_root(
    fake_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside") / "x.txt"
    assert relative_to_root(fake_root, outside).endswith("x.txt")
