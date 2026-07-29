"""Shared test fixtures and the suite-wide network prohibition.

The work order requires that no test performs a network call and that schema validation
never resolves a reference over the network. Rather than trusting review to catch a
regression, the whole suite runs with outbound sockets disabled: any attempt to open one
raises ``NetworkAccessAttemptedError`` and fails the test that made it.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from oic.paths import find_repo_root

REPO_ROOT = find_repo_root(Path(__file__).parent)


class NetworkAccessAttemptedError(RuntimeError):
    """Raised when test code tries to open a socket."""


def _blocked(*args: object, **kwargs: object) -> NoReturn:
    del args, kwargs
    raise NetworkAccessAttemptedError(
        "network access is disabled for the OIC test suite; "
        "schema and manifest verification must be fully offline"
    )


@pytest.fixture(autouse=True, scope="session")
def _disable_network() -> Iterator[None]:
    """Disable outbound sockets for the entire session."""
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(socket, "socket", _blocked)
        patcher.setattr(socket, "create_connection", _blocked)
        yield


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The real repository root, for contract tests over governing artifacts."""
    return REPO_ROOT


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory holding checked-in byte-exact test fixtures."""
    return Path(__file__).parent / "fixtures"
