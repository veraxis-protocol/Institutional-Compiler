from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Protocol, cast

from pytest import MonkeyPatch


class HarnessModule(Protocol):
    CASES: tuple[tuple[str, str], ...]

    def actual_single_pass(self, returncode: int, output: str) -> tuple[bool, str]: ...

    def success_message(self, observed: int) -> str: ...


def load_harness() -> HarnessModule:
    path = Path(__file__).resolve().parents[2] / "scripts/falsify_infrastructure.py"
    spec = importlib.util.spec_from_file_location("oic_falsify_infrastructure", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(HarnessModule, module)


harness = load_harness()


def test_exactly_one_pass_is_accepted() -> None:
    accepted, detail = harness.actual_single_pass(0, ". [100%]\n1 passed in 0.01s\n")

    assert accepted is True
    assert detail == "expected selected=1 observed passed=1"


def test_skipped_selector_is_refused_despite_exit_zero() -> None:
    accepted, detail = harness.actual_single_pass(0, "s [100%]\n1 skipped in 0.01s\n")

    assert accepted is False
    assert "1 passed" in detail
    assert "skipped" in detail


def test_stale_selector_is_refused() -> None:
    accepted, detail = harness.actual_single_pass(
        4, "ERROR: not found: stale::selector\nno tests ran in 0.01s\n"
    )

    assert accepted is False
    assert detail == "pytest exit 4"


def test_success_count_follows_cases(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "CASES", (("one", "selector-one"), ("two", "selector-two")))

    assert harness.success_message(2) == (
        "PASS bounded infrastructure falsification: 2/2 expected checks observed"
    )
