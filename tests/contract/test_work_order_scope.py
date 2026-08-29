"""The temporal property that historical work-order scope assertions depend on.

A closed work order's scope receipt is evidence about the exact range of history it
produced. Two things must hold at once, and this file proves both against synthetic
repositories built commit by commit, so neither is a claim about the real history:

A. A legitimate later commit, outside the frozen range, does **not** retroactively
   invalidate the receipt.
B. A mutation of the range being verified **does** fail — whether the mutation is a
   forbidden path inside the work order itself, or a rewrite of the recorded history.

Both directions are tested. A helper that returned an empty diff for everything would
satisfy A and fail B; one bound to ``HEAD`` satisfies B and fails A.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
try:
    from work_order_scope import (
        CLOSED_WORK_ORDERS,
        WorkOrder,
        WorkOrderHistoryError,
        assert_history_is_intact,
        changed_paths,
    )
finally:
    sys.path.pop(0)

pytestmark = pytest.mark.contract


def _git(repo: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", *argv],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit(repo: Path, message: str, files: Mapping[str, str]) -> str:
    for relpath, text in files.items():
        path = repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "contract-test@example.invalid")
    _git(repo, "config", "user.name", "Contract Test")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


# --------------------------------------------------------------------------
# A. A later authorized commit does not retroactively invalidate the receipt
# --------------------------------------------------------------------------


def test_a_later_commit_outside_the_range_does_not_change_the_recorded_scope(
    synthetic_repo: Path,
) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)

    before = changed_paths(synthetic_repo, work_order)
    assert before == ["corpus.json"]

    # A separately authorized, later commit touching a path the work order was forbidden
    # to touch. It is outside the frozen range, so the receipt still reads the same.
    _commit(synthetic_repo, "later authorized change", {"STATUS.md": "revised\n"})

    assert changed_paths(synthetic_repo, work_order) == before
    assert "STATUS.md" not in changed_paths(synthetic_repo, work_order)


def test_the_binding_is_what_makes_that_true_not_an_empty_diff(synthetic_repo: Path) -> None:
    """The same comparison against HEAD would have failed. That is the defect being fixed."""
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)
    _commit(synthetic_repo, "later authorized change", {"STATUS.md": "revised\n"})

    against_head = _git(synthetic_repo, "diff", "--name-only", f"{base}...HEAD").splitlines()
    assert "STATUS.md" in against_head
    assert "STATUS.md" not in changed_paths(synthetic_repo, work_order)


def test_many_later_commits_do_not_accumulate_into_the_recorded_scope(
    synthetic_repo: Path,
) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)

    for index in range(5):
        _commit(
            synthetic_repo,
            f"later change {index}",
            {f"src/oic/module_{index}.py": "value = 1\n"},
        )

    assert changed_paths(synthetic_repo, work_order) == ["corpus.json"]


# --------------------------------------------------------------------------
# B. A mutation of the verified state still fails
# --------------------------------------------------------------------------


def test_a_forbidden_path_inside_the_work_order_is_still_detected(synthetic_repo: Path) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    # This work order really did touch the frozen artifact. The receipt must say so.
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n", "STATUS.md": "edited\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)

    assert "STATUS.md" in changed_paths(synthetic_repo, work_order)


def test_rewriting_the_recorded_history_fails(synthetic_repo: Path) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)
    assert changed_paths(synthetic_repo, work_order) == ["corpus.json"]

    # Mutate the frozen range itself: same message, different content. The recorded tip
    # is no longer what this branch contains.
    _git(synthetic_repo, "reset", "-q", "--hard", base)
    rewritten = _commit(synthetic_repo, "work order", {"corpus.json": '{"tampered": true}\n'})
    assert rewritten != tip

    with pytest.raises(WorkOrderHistoryError, match="no longer an ancestor of HEAD"):
        changed_paths(synthetic_repo, work_order)


def test_dropping_the_work_order_from_the_branch_fails(synthetic_repo: Path) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    tip = _commit(synthetic_repo, "work order", {"corpus.json": "{}\n"})
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=tip)

    _git(synthetic_repo, "reset", "-q", "--hard", base)

    with pytest.raises(WorkOrderHistoryError, match="no longer an ancestor of HEAD"):
        changed_paths(synthetic_repo, work_order)


def test_an_unknown_recorded_commit_fails(synthetic_repo: Path) -> None:
    base = _commit(synthetic_repo, "base", {"STATUS.md": "frozen\n"})
    absent = "0" * 40
    work_order = WorkOrder(name="synthetic-v0.1", base=base, tip=absent)

    with pytest.raises(WorkOrderHistoryError, match="recorded tip commit"):
        changed_paths(synthetic_repo, work_order)


def test_a_tip_that_does_not_descend_from_the_base_fails(synthetic_repo: Path) -> None:
    root = _commit(synthetic_repo, "root", {"README.md": "root\n"})
    _git(synthetic_repo, "checkout", "-q", "-b", "left", root)
    left = _commit(synthetic_repo, "left", {"left.txt": "left\n"})
    _git(synthetic_repo, "checkout", "-q", "-b", "right", root)
    right = _commit(synthetic_repo, "right", {"right.txt": "right\n"})

    # HEAD is on `right`, so `right` is an ancestor of HEAD but does not descend from `left`.
    work_order = WorkOrder(name="synthetic-v0.1", base=left, tip=right)
    with pytest.raises(WorkOrderHistoryError, match="no longer descends from the recorded base"):
        changed_paths(synthetic_repo, work_order)


# --------------------------------------------------------------------------
# The real repository's recorded boundaries
# --------------------------------------------------------------------------


@pytest.mark.parametrize("work_order", CLOSED_WORK_ORDERS, ids=lambda wo: wo.name)
def test_recorded_boundaries_are_intact_in_this_repository(
    repo_root: Path, work_order: WorkOrder
) -> None:
    assert_history_is_intact(repo_root, work_order)
    assert len(work_order.base) == 40
    assert len(work_order.tip) == 40


@pytest.mark.parametrize("work_order", CLOSED_WORK_ORDERS, ids=lambda wo: wo.name)
def test_recorded_work_orders_are_closed_and_behind_head(
    repo_root: Path, work_order: WorkOrder
) -> None:
    """Every recorded work order is strictly historical, so the binding is load-bearing."""
    head = _git(repo_root, "rev-parse", "HEAD")
    assert work_order.tip != head
    assert changed_paths(repo_root, work_order), work_order.name
