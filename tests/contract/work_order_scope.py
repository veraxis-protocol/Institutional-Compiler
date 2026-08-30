"""Temporal binding for historical work-order scope assertions.

A work-order scope assertion is a statement about the exact range of history that
work order produced: ``base...tip``. It is evidence about a past state, so it must
be evaluated against that past state. Comparing an old work order's scope against
whatever the repository's ``HEAD`` happens to be today is a category error: a later,
separately authorized commit would retroactively falsify a receipt that was true
when it was issued, and the only way to keep the suite green would be to widen the
historical scope until it no longer says anything.

Binding the range to its recorded tip removes that pressure without removing
detection. The range is still anchored to the live repository on every run:

* ``base`` and ``tip`` must both resolve to real commits;
* ``tip`` must be a descendant of ``base``;
* ``tip`` must be an ancestor of the current ``HEAD``.

So the recorded history has to still be present, in the same shape, in the branch
under test. Amend it, rebase it, drop it, or reorder it and the recorded SHAs stop
describing this repository, and every assertion bound to that work order fails.
Mutate a file *inside* the recorded range and the tip's SHA changes, which fails
the same way. What the binding permits is exactly what should be permitted: new
commits after the tip.

This is only the temporal half of the guarantee. That frozen artifacts still hold
their frozen bytes *now* is a standing property of the working tree, checked
separately by the digest assertions in the contract suites (for example
``test_committed_bytes_match_every_receipt_and_both_hash_ledgers``). Neither check
substitutes for the other.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class WorkOrderHistoryError(AssertionError):
    """The recorded work-order history is not present in this repository as recorded."""


@dataclass(frozen=True)
class WorkOrder:
    """A closed work order, identified by the exact commit range it produced.

    ``base`` is the commit the work-order branch started from; ``tip`` is the commit
    that landed it. Both are full 40-character SHAs so the record is unambiguous.
    """

    name: str
    base: str
    tip: str


# The closed Canada work orders whose scope assertions the contract suites carry.
# Each ``tip`` is the merge commit that landed that work order on the trunk.
CANADA_ACQUISITION_PREFLIGHT = WorkOrder(
    name="corpus/canada-acquisition-preflight-v0.1",
    base="37d6fa4dd12f7f26c632169611b13c251bbec14a",
    tip="d99a38510e51a36972a414cadd0e44d49a04227c",
)
CANADA_RIGHTS_FREEZE = WorkOrder(
    name="corpus/canada-rights-freeze-v0.1",
    base="d99a38510e51a36972a414cadd0e44d49a04227c",
    tip="2dab50aa5e84cc2995bb8561a8d1fb63741e4a3a",
)
CANADA_RIGHTS_RESOLUTION_DOSSIER = WorkOrder(
    name="corpus/canada-rights-resolution-dossier-v0.1",
    base="2dab50aa5e84cc2995bb8561a8d1fb63741e4a3a",
    tip="29daa374b7e5cdc30ca7788310fbabb85f19912b",
)

# The closed admission design work orders. Each produced exactly one commit; their scope
# assertions are evidence about that commit, not about whatever HEAD later becomes.
ADMISSION_BOUNDARY_001_DESIGN = WorkOrder(
    name="design/admission-boundary-001-preregistration",
    base="6968dfc04f2108e910e1983b15262e2b26bf7fc9",
    tip="e445c25a4f657c59fbfe32617f46153ac678150c",
)
ADMISSION_DESIGN_CONSISTENCY_001 = WorkOrder(
    name="design/admission-design-consistency-001",
    base="e445c25a4f657c59fbfe32617f46153ac678150c",
    tip="9fa2c684841ea89632bfe0129f98177761d85d12",
)

CANDIDATE_SEMANTICS_005 = WorkOrder(
    name="semantics/candidate-semantics-005",
    base="11acd84b97bbdb3910c208e63b69b4fbb10be179",
    tip="59c6b34a4972c7758ea1ef4c09fd26be5ddb507e",
)

CLOSED_WORK_ORDERS = (
    CANADA_ACQUISITION_PREFLIGHT,
    CANADA_RIGHTS_FREEZE,
    CANADA_RIGHTS_RESOLUTION_DOSSIER,
    CANDIDATE_SEMANTICS_005,
    ADMISSION_BOUNDARY_001_DESIGN,
    ADMISSION_DESIGN_CONSISTENCY_001,
)


def _git(repo_root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def _require_commit(repo_root: Path, work_order: WorkOrder, role: str, sha: str) -> None:
    resolved = _git(repo_root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    if resolved.returncode != 0:
        raise WorkOrderHistoryError(
            f"{work_order.name}: recorded {role} commit {sha} is not present in this repository"
        )


def _require_ancestor(
    repo_root: Path, work_order: WorkOrder, ancestor: str, descendant: str, why: str
) -> None:
    if _git(repo_root, "merge-base", "--is-ancestor", ancestor, descendant).returncode != 0:
        raise WorkOrderHistoryError(f"{work_order.name}: {why} ({ancestor} -> {descendant})")


def assert_history_is_intact(repo_root: Path, work_order: WorkOrder) -> None:
    """Fail unless the recorded range still exists, in shape, in ``HEAD``'s ancestry."""
    _require_commit(repo_root, work_order, "base", work_order.base)
    _require_commit(repo_root, work_order, "tip", work_order.tip)
    _require_ancestor(
        repo_root,
        work_order,
        work_order.base,
        work_order.tip,
        "recorded tip no longer descends from the recorded base",
    )
    _require_ancestor(
        repo_root,
        work_order,
        work_order.tip,
        "HEAD",
        "recorded tip is no longer an ancestor of HEAD; the work-order history was rewritten",
    )


def changed_paths(repo_root: Path, work_order: WorkOrder) -> list[str]:
    """Paths the work order changed, as of the commit that landed it.

    Deliberately ``base...tip`` and never ``base...HEAD``: the scope of a closed work
    order is fixed at its tip, so later authorized commits are outside it.
    """
    assert_history_is_intact(repo_root, work_order)
    diff = _git(repo_root, "diff", "--name-only", f"{work_order.base}...{work_order.tip}")
    if diff.returncode != 0:
        raise WorkOrderHistoryError(
            f"{work_order.name}: could not diff {work_order.base}...{work_order.tip}: "
            f"{diff.stderr.strip()}"
        )
    return diff.stdout.splitlines()
