"""Contract tests that documentation added by this work order respects CLAIMS.md.

`CLAIMS.md` forbids a specific set of assertions at the current status. These tests scan
the documentation this work order introduced and fail if a forbidden claim appears in an
affirmative form. Phrases are permitted when they are being denied, which is how the
operator docs discuss the limitations at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

#: Documentation added by this work order. Bootstrap-controlled files are excluded
#: because they are digest-verified and must not be edited here.
AUTHORED_DOCS = (
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "VERSIONING.md",
    "docs/SDLC-V1.2-STATUS.md",
    "docs/operations/FOUNDATION.md",
    "docs/operations/CI.md",
    "docker/README.md",
    "docker/IMAGES.md",
    "sbom/README.md",
    "adr/ADR-011.md",
    "tests/fixtures/hashing/README.md",
)

#: Claims forbidden outright at the current status. No negation rescues these.
FORBIDDEN_ABSOLUTELY = (
    "outperforms",
    "state-of-the-art",
    "state of the art",
    "world-class",
    "industry-leading",
    "best-in-class",
    "battle-tested",
    "the first institutional compiler",
    "the best institutional compiler",
    "legally compliant",
    "guarantees compliance",
    "guarantees legal",
    "eliminates human review",
    "autonomously determines",
)

#: Claims permitted only when denied. The preceding text must carry a negation.
FORBIDDEN_UNLESS_NEGATED = (
    "enterprise ready",
    "enterprise-ready",
    "production ready",
    "production-ready",
    "corpus-ready",
    "corpus ready",
    "independently reviewed",
    "independently verified",
)

#: Words that, appearing before a phrase, mark it as denied or counterfactual rather
#: than asserted. Deliberately generous: a false negative here is a missed guard, but a
#: false positive would push authors toward vaguer prose about the very limitations this
#: repository is obliged to state plainly.
NEGATIONS = (
    "not",
    "no ",
    "nothing",
    "never",
    "n't",
    "cannot",
    "without",
    "would",
    "wrongly",
    "until",
)

#: Characters of preceding context inspected for a negation. Wide enough to span a
#: sentence, since denials are often list-shaped ("nothing here asserts that OIC is X,
#: Y, or Z").
_CONTEXT = 220


@pytest.fixture(scope="module")
def documents(repo_root: Path) -> dict[str, str]:
    contents: dict[str, str] = {}
    for relpath in AUTHORED_DOCS:
        path = repo_root / relpath
        assert path.is_file(), f"expected authored document is missing: {relpath}"
        # Collapse hard-wrapped lines so prose assertions are not defeated by the
        # position of a line break.
        contents[relpath] = " ".join(path.read_text(encoding="utf-8").lower().split())
    return contents


@pytest.mark.parametrize("phrase", FORBIDDEN_ABSOLUTELY)
def test_no_absolutely_forbidden_claim_appears(documents: dict[str, str], phrase: str) -> None:
    offenders = [relpath for relpath, text in documents.items() if phrase in text]
    assert offenders == [], f"forbidden claim {phrase!r} appears in: {offenders}"


@pytest.mark.parametrize("phrase", FORBIDDEN_UNLESS_NEGATED)
def test_readiness_claims_appear_only_when_denied(documents: dict[str, str], phrase: str) -> None:
    """Every occurrence must be preceded by a negation within the same clause."""
    offenders: list[str] = []
    for relpath, text in documents.items():
        for match in re.finditer(re.escape(phrase), text):
            context = text[max(0, match.start() - _CONTEXT) : match.start()]
            if not any(negation in context for negation in NEGATIONS):
                offenders.append(f"{relpath}: ...{context}[{phrase}]")
    assert offenders == [], f"un-negated readiness claim: {offenders}"


def test_operator_guide_states_the_semantic_gate_is_blocked(documents: dict[str, str]) -> None:
    text = documents["docs/operations/FOUNDATION.md"]
    # Markdown emphasis may wrap either the word or the whole sentence, so match the
    # claim with emphasis markers stripped.
    plain = text.replace("*", "")
    assert "semantic implementation gate is blocked" in plain
    assert "no semantic implementation exists" in plain


def test_operator_guide_states_ztl_and_veip_are_provisional(documents: dict[str, str]) -> None:
    text = documents["docs/operations/FOUNDATION.md"]
    assert "provisional / not configured" in text
    assert "no adapter, container, or call exists" in text


def test_operator_guide_states_where_compose_evidence_comes_from(
    documents: dict[str, str],
) -> None:
    """Compose is exercised by CI, and the guide must say so rather than imply local proof."""
    text = documents["docs/operations/FOUNDATION.md"]
    assert "compose-validation" in text
    assert "docker is unavailable in the authoring environment" in text
    assert "ci provides the executable evidence" in text


def test_operator_guide_records_the_bootstrap_baseline_model(
    documents: dict[str, str],
) -> None:
    """The corrected model must be documented, not just implemented."""
    text = documents["docs/operations/FOUNDATION.md"]
    plain = text.replace("*", "")
    assert "immutable historical evidence about the bootstrap commit" in plain
    assert "neither read nor modified" in plain
    assert "adr-012" in plain
    assert "never rewritten to make a later working tree match" in plain


def test_operator_guide_records_the_class_b_gap(documents: dict[str, str]) -> None:
    """The procedural-only protection of governed contracts must be stated plainly."""
    text = documents["docs/operations/FOUNDATION.md"]
    assert "protected procedurally, not mechanically" in text
    assert "deferred to a separate work order" in text


def test_operator_guide_records_the_incomplete_corpus_result(documents: dict[str, str]) -> None:
    text = documents["docs/operations/FOUNDATION.md"]
    assert "exits `3`. this is correct, not a bug" in text
    assert "recording a digest is not the same as verifying one" in text


def test_operator_guide_documents_rollback(documents: dict[str, str]) -> None:
    text = documents["docs/operations/FOUNDATION.md"]
    assert "git revert" in text
    assert "blast radius" in text


def test_operator_guide_disclaims_coverage_as_a_quality_claim(documents: dict[str, str]) -> None:
    text = documents["docs/operations/FOUNDATION.md"]
    assert "coverage is not a quality claim" in text


def test_ci_guide_documents_secret_scan_limitations(documents: dict[str, str]) -> None:
    text = documents["docs/operations/CI.md"]
    assert "not evidence that the repository contains no secrets" in text
    assert "never git history" in text


def test_polyform_noncommercial_license_is_declared(repo_root: Path) -> None:
    """The owner-selected license is present without a conflicting grant."""
    license_text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("# PolyForm Noncommercial License 1.0.0\n")
    assert "https://polyformproject.org/licenses/noncommercial/1.0.0" in license_text
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert "\nlicense =" not in pyproject
    assert "License ::" not in pyproject
    assert 'license-files = ["LICENSE"]' in pyproject


def test_claims_bearing_documents_are_unchanged_by_this_work_order(repo_root: Path) -> None:
    """The Class B claims documents must be byte-identical to their bootstrap versions.

    ADR-012 protects Class B artifacts procedurally rather than by digest registry, so
    this test states the specific obligation for the documents that carry claims: this
    work order does not touch them. Compared against the blob at the bootstrap commit,
    not against a manifest, because the manifest describes that commit rather than now.
    """
    import subprocess

    from oic.baseline import BOOTSTRAP_COMMIT

    for relpath in ("CLAIMS.md", "LIMITATIONS.md", "STATUS.md", "OWNERS.md"):
        committed = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "blob", f"{BOOTSTRAP_COMMIT}:{relpath}"],
            capture_output=True,
            check=True,
        ).stdout
        assert (repo_root / relpath).read_bytes() == committed, relpath
