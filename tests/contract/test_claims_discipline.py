"""Contract tests that documentation added by this work order respects CLAIMS.md.

`CLAIMS.md` forbids a specific set of assertions at the current status. These tests scan
the documentation this work order introduced and fail if a forbidden claim appears in an
affirmative form. Phrases are permitted when they are being denied, which is how the
operator docs discuss the limitations at all.
"""

from __future__ import annotations

import json
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

GATE_F_EXCLUSIONS = (
    "semantic correctness",
    "model accuracy",
    "institutional validity",
    "legal effect",
    "provider qualification",
    "rights resolution",
    "ontology execution",
    "production compilation",
    "runtime authorization",
    "institutional-IR closure",
    "enterprise readiness",
    "benchmark superiority",
)


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
    assert "production semantic gate remains blocked" in plain
    assert "bounded_reference_implementation" in plain


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
    assert '\nlicense = "PolyForm-Noncommercial-1.0.0"' in pyproject
    assert "License ::" not in pyproject
    assert 'license-files = ["LICENSE"]' in pyproject


def test_static_claims_documents_are_unchanged_by_this_work_order(repo_root: Path) -> None:
    """The static claims documents remain byte-identical to their bootstrap versions.

    ADR-012 protects Class B artifacts procedurally rather than by digest registry, so
    This test protects CLAIMS.md, LIMITATIONS.md and OWNERS.md. STATUS.md intentionally
    evolves and is governed separately by semantic claims controls below.
    """
    import subprocess

    from oic.baseline import BOOTSTRAP_COMMIT

    for relpath in ("CLAIMS.md", "LIMITATIONS.md", "OWNERS.md"):
        committed = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "blob", f"{BOOTSTRAP_COMMIT}:{relpath}"],
            capture_output=True,
            check=True,
        ).stdout
        observed = (repo_root / relpath).read_bytes()
        assert observed == committed, relpath


#: Pre-merge wording that the completed PR #40 promotion makes false. A front-door
#: document that reintroduces any of these is stale and must fail closed.
STALE_PRE_MERGE_PHRASES = (
    "merge remains pending gate g and owner authorization",
    "merge pending gate g and owner authorization",
    "no merge is authorized",
    "gate g and owner merge authorization remain pending",
)


def _assert_promotion_claims(normalized: str, promotion: object) -> None:
    """Require the shipped text to carry the exact Gate G promotion anchors.

    Every anchor is read from the live capability matrix rather than hard-coded here,
    so changing an anchor in the matrix without changing the shipped document fails
    closed, and changing the document without the matrix fails closed too.
    """
    assert isinstance(promotion, dict), "missing gate_g_promotion_evidence"
    assert promotion.get("status") == "GATE_G_PASS"
    assert promotion.get("work_order") == "OIC-INDEPENDENT-GATE-G-001"
    detail = promotion.get("promotion")
    assert isinstance(detail, dict), "missing promotion detail"

    for key in ("candidate_commit", "candidate_tree"):
        value = promotion.get(key)
        assert isinstance(value, str) and value in normalized, (
            f"missing Gate G promotion anchor: {key}"
        )
    for key in ("merge_commit", "merge_first_parent", "merge_second_parent"):
        value = detail.get(key)
        assert isinstance(value, str) and value in normalized, (
            f"missing Gate G promotion anchor: {key}"
        )

    pull_request = detail.get("pull_request")
    assert isinstance(pull_request, int)
    assert f"pull request {pull_request}" in normalized, "missing pull request reference"
    approver = detail.get("approved_by")
    assert isinstance(approver, str) and approver.lower() in normalized
    merged_at = detail.get("merged_at")
    assert isinstance(merged_at, str) and merged_at.lower() in normalized

    assert "independent gate g validation passed" in normalized, (
        "missing independent Gate G validation statement"
    )
    assert promotion.get("exclusions") == list(GATE_F_EXCLUSIONS)

    for phrase in STALE_PRE_MERGE_PHRASES:
        assert phrase not in normalized, f"stale pre-merge assertion reintroduced: {phrase}"


def _assert_status_claims(text: str, capability_matrix: dict[str, object]) -> None:
    """Require the active bounded state and ceilings; reject affirmative escalation."""
    normalized = " ".join(text.lower().replace("*", "").split())
    state = capability_matrix["state"]
    gate = capability_matrix["production_semantic_gate"]
    ceilings = capability_matrix["ceilings"]
    evidence = capability_matrix.get("independent_validation_evidence")
    promotion = capability_matrix.get("gate_g_promotion_evidence")
    assert isinstance(state, str) and state.lower() in normalized
    assert isinstance(gate, str) and f"production semantic gate: {gate.lower()}" in normalized
    assert isinstance(ceilings, dict)
    required = {
        "nvidia": "nvidia: not_qualified",
        "canada_redistribution": "canada redistribution: unresolved",
        "ontology_007r1": "ontology 007r1: unexecuted and execution-unauthorized",
        "production_compilation": "production compilation and runtime authorization: unestablished",
        "runtime_authorization": "production compilation and runtime authorization: unestablished",
        "institutional_ir_closure": "institutional-ir closure: unestablished",
        "negative_stability_live_result": "negative-stability live outcome: deferred",
    }
    for key, phrase in required.items():
        assert key in ceilings and phrase in normalized, f"missing STATUS.md ceiling: {key}"
    independently_validated = ceilings.get("independent_validation")
    assert isinstance(independently_validated, bool)
    if independently_validated:
        assert isinstance(evidence, dict)
        assert evidence.get("status") == "GATE_F_PASS"
        assert evidence.get("work_order") == "OIC-INDEPENDENT-GATE-F-005"
        candidate = evidence.get("candidate_commit")
        tree = evidence.get("candidate_tree")
        assert isinstance(candidate, str) and candidate in normalized
        assert isinstance(tree, str) and tree in normalized
        assert "independent gate f repository validation passed" in normalized, (
            "missing STATUS.md independent Gate F validation statement"
        )
        assert "1714 passed, 0 failed, 0 errors, 1 declared skip, 93.5% coverage" in normalized
        assert "does not establish semantic correctness" in normalized
        assert evidence.get("exclusions") == list(GATE_F_EXCLUSIONS)
        for exclusion in GATE_F_EXCLUSIONS:
            assert exclusion.lower() in normalized
        _assert_promotion_claims(normalized, promotion)
    else:
        assert evidence is None
        assert promotion is None
        assert "pending independent validation" in normalized
    for phrase in FORBIDDEN_ABSOLUTELY:
        assert phrase not in normalized, f"forbidden STATUS.md claim: {phrase}"
    for phrase in (
        "production complete",
        "nvidia qualified",
        "redistribution authorized",
        "ontology 007r1 executed",
        "runtime authorized",
        "independently validated",
        "semantic correctness established",
        "gate g passed",
    ):
        assert phrase not in normalized, f"unsupported STATUS.md escalation: {phrase}"


def test_status_reports_active_bounded_state_and_ceilings(repo_root: Path) -> None:
    """The shipped STATUS.md must reflect the active matrix without claim escalation."""
    status = (repo_root / "STATUS.md").read_text(encoding="utf-8")
    matrix: dict[str, object] = json.loads(
        (repo_root / "docs/capabilities/CAPABILITY_MATRIX.json").read_text(encoding="utf-8")
    )
    _assert_status_claims(status, matrix)

    missing_ceiling = status.replace("NVIDIA: NOT_QUALIFIED and excluded from the demo. ", "")
    with pytest.raises(AssertionError, match="nvidia"):
        _assert_status_claims(missing_ceiling, matrix)

    forbidden_claim = status + "\nThe system is production complete.\n"
    with pytest.raises(AssertionError, match="production complete"):
        _assert_status_claims(forbidden_claim, matrix)

    validation_marker = "independent gate f repository validation passed"
    assert validation_marker in " ".join(status.lower().replace("*", "").split())
    missing_evidence, replacement_count = re.subn(
        re.escape(validation_marker),
        "repository validation marker removed",
        status,
        flags=re.IGNORECASE,
    )
    assert replacement_count > 0
    assert missing_evidence != status
    missing_normalized = " ".join(missing_evidence.lower().replace("*", "").split())
    assert validation_marker not in missing_normalized
    with pytest.raises(
        AssertionError,
        match=re.escape("missing STATUS.md independent Gate F validation statement"),
    ):
        _assert_status_claims(missing_evidence, matrix)

    forged_matrix = json.loads(json.dumps(matrix))
    forged_matrix["independent_validation_evidence"]["candidate_commit"] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_status_claims(status, forged_matrix)

    broad_claim = status + "\nThe implementation is independently validated.\n"
    with pytest.raises(AssertionError, match="independently validated"):
        _assert_status_claims(broad_claim, matrix)

    stale_claim = status + "\nMerge remains pending Gate G and owner authorization.\n"
    with pytest.raises(AssertionError, match="stale pre-merge assertion reintroduced"):
        _assert_status_claims(stale_claim, matrix)

    drifted_matrix = json.loads(json.dumps(matrix))
    drifted_matrix["gate_g_promotion_evidence"]["promotion"]["merge_commit"] = "0" * 40
    with pytest.raises(AssertionError, match="missing Gate G promotion anchor: merge_commit"):
        _assert_status_claims(status, drifted_matrix)

    removed_promotion = json.loads(json.dumps(matrix))
    del removed_promotion["gate_g_promotion_evidence"]
    with pytest.raises(AssertionError, match="missing gate_g_promotion_evidence"):
        _assert_status_claims(status, removed_promotion)

    gate_g_marker = "independent gate g validation passed"
    dropped_gate_g = re.sub(
        re.escape(gate_g_marker), "gate g marker removed", status, flags=re.IGNORECASE
    )
    assert dropped_gate_g != status
    with pytest.raises(
        AssertionError, match=re.escape("missing independent Gate G validation statement")
    ):
        _assert_status_claims(dropped_gate_g, matrix)

    pending_matrix = json.loads(json.dumps(matrix))
    pending_matrix["ceilings"]["independent_validation"] = False
    del pending_matrix["independent_validation_evidence"]
    del pending_matrix["gate_g_promotion_evidence"]
    pending_status = status.replace(
        "SCOPED INDEPENDENT GATE G VALIDATION PASSED AND MERGED TO MAIN",
        "PENDING INDEPENDENT VALIDATION",
    )
    _assert_status_claims(pending_status, pending_matrix)


def test_gate_f_exclusions_are_exact_and_present_in_both_front_doors(repo_root: Path) -> None:
    matrix = json.loads(
        (repo_root / "docs/capabilities/CAPABILITY_MATRIX.json").read_text(encoding="utf-8")
    )
    assert matrix["independent_validation_evidence"]["exclusions"] == list(GATE_F_EXCLUSIONS)
    for relpath in ("README.md", "STATUS.md"):
        normalized = " ".join((repo_root / relpath).read_text(encoding="utf-8").lower().split())
        for exclusion in GATE_F_EXCLUSIONS:
            assert exclusion.lower() in normalized, (
                f"missing {relpath} Gate F exclusion: {exclusion}"
            )


def _normalize_readme_claims(text: str) -> str:
    """Remove presentation syntax while preserving the words that carry a claim."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.casefold()).split())


def _assert_readme_independent_validation_is_scoped(
    text: str, gate_f: dict[str, object], gate_g: dict[str, object]
) -> None:
    normalized = _normalize_readme_claims(text)
    subject = (
        r"(?:this\s+)?(?:current\s+repository(?:\s+head)?|repository\s+head|"
        r"current\s+(?:head|commit|revision|release)|release|main|implementation)"
    )
    validation = r"(?:independently\s+validated|independent\s+validation)"
    bridge = r"(?:\s+[a-z0-9]+){0,5}\s+"
    unscoped = re.search(
        rf"\b(?:{subject}{bridge}{validation}|{validation}{bridge}{subject})\b",
        normalized,
    )
    assert unscoped is None, f"unscoped README independent-validation claim: {unscoped.group(0)!r}"

    for label, marker, evidence in (
        (
            "Gate F",
            "independent gate f repository validation passed for candidate",
            gate_f,
        ),
        ("Gate G", "independent gate g validation passed for candidate", gate_g),
    ):
        candidate_commit = evidence["candidate_commit"]
        candidate_tree = evidence["candidate_tree"]
        assert isinstance(candidate_commit, str)
        assert isinstance(candidate_tree, str)
        scoped_claim = f"{marker} {candidate_commit} tree {candidate_tree}".lower()
        assert scoped_claim in normalized, (
            f"README.md {label} independent-validation statement is not bound "
            "to its exact candidate commit and tree"
        )


def test_readme_numeric_claims_are_bound_to_their_source_evidence(repo_root: Path) -> None:
    """Close GG001-M01: every README validation claim must name its source candidate.

    The Gate F and Gate G numeric results are only meaningful next to the exact commit
    and tree that produced them. This control reads the anchors from the live matrix,
    so stripping the citation from README.md while leaving the numbers in place fails
    closed, and so does changing an anchor in the matrix alone.
    """
    matrix = json.loads(
        (repo_root / "docs/capabilities/CAPABILITY_MATRIX.json").read_text(encoding="utf-8")
    )
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    normalized = " ".join(readme.lower().replace("*", "").split())

    gate_f = matrix["independent_validation_evidence"]
    gate_g = matrix["gate_g_promotion_evidence"]

    required_anchors = {
        "gate_f_candidate_commit": gate_f["candidate_commit"],
        "gate_f_candidate_tree": gate_f["candidate_tree"],
        "gate_g_candidate_commit": gate_g["candidate_commit"],
        "gate_g_candidate_tree": gate_g["candidate_tree"],
        "merge_commit": gate_g["promotion"]["merge_commit"],
        "merge_first_parent": gate_g["promotion"]["merge_first_parent"],
        "merge_second_parent": gate_g["promotion"]["merge_second_parent"],
    }
    for label, anchor in required_anchors.items():
        assert isinstance(anchor, str) and anchor.lower() in normalized, (
            f"README.md numeric claim is unscoped: missing {label}"
        )

    # A numeric result may not appear without the commit that produced it.
    gate_f_passed = gate_f["canonical_linux"]["passed"]
    gate_g_passed = gate_g["canonical_linux"]["passed"]
    for passed, anchor_label in (
        (gate_f_passed, "gate_f_candidate_commit"),
        (gate_g_passed, "gate_g_candidate_commit"),
    ):
        assert f"{passed} passed" in normalized, f"missing README result for {anchor_label}"

    _assert_readme_independent_validation_is_scoped(readme, gate_f, gate_g)

    unscoped_claims = (
        "This current repository head is independently validated.",
        "**THIS   CURRENT**\nrepository HEAD -- is independently validated!!!",
        "The current head is independently validated.",
        "This release has independent validation.",
        "*This   Implementation* is independently validated.",
        "Main is independently validated.",
    )
    for claim in unscoped_claims:
        mutated = f"{readme}\n{claim}\n"
        assert _normalize_readme_claims(claim) in _normalize_readme_claims(mutated)
        with pytest.raises(AssertionError, match="unscoped README independent-validation claim"):
            _assert_readme_independent_validation_is_scoped(mutated, gate_f, gate_g)

    scoped_claims = (
        "Independent Gate F repository validation passed for candidate "
        f"{gate_f['candidate_commit']} (tree {gate_f['candidate_tree']}).",
        "Independent Gate G validation passed for candidate "
        f"{gate_g['candidate_commit']} (tree {gate_g['candidate_tree']}).",
    )
    normalized_claims = _normalize_readme_claims(readme)
    for claim in scoped_claims:
        assert _normalize_readme_claims(claim) in normalized_claims


@pytest.mark.parametrize("mutation", ("delete", "substitute", "reorder", "add"))
def test_matrix_gate_f_exclusion_mutations_fail_closed(repo_root: Path, mutation: str) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bounded_gate_claims", repo_root / "scripts/verify_code_start_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evidence = json.loads(
        json.dumps(
            json.loads(
                (repo_root / "docs/capabilities/CAPABILITY_MATRIX.json").read_text(encoding="utf-8")
            )["independent_validation_evidence"]
        )
    )
    exclusions = evidence["exclusions"]
    if mutation == "delete":
        exclusions.pop(0)
    elif mutation == "substitute":
        exclusions[0] = "semantic validity"
    elif mutation == "reorder":
        exclusions[0], exclusions[1] = exclusions[1], exclusions[0]
    else:
        exclusions.append("production readiness")
    with pytest.raises(module.GateEvidenceError, match="evidence forged"):
        module.validate_independent_validation_evidence(evidence)


#: Anchors for the PR #41 continuity merge. These are deliberately literal rather than read
#: from the capability matrix: the matrix records the Gate F and Gate G candidates and is
#: outside the authorized path set for the work order that recorded this merge, so binding
#: the front doors to it here would couple two independently governed artifacts.
POST_MERGE_CONTINUITY_ANCHORS = (
    "8ebac66965997748061d8cc0f1bfde73cb7b216a",
    "4576fea067d33c2c0f8e8fc2d49bb506c52b2f1c",
    "c4a325c551ce8904dfcc5b9fe81b05109726a334",
    "6e450750d7b6b1d1f0b493b050ed7d866d42b264",
)

#: Prose the continuity merge record must carry in both front doors.
POST_MERGE_CONTINUITY_PHRASES = (
    "pull request 41",
    "sak001c-f01/sak001-f01 pending independent confirmation",
    "independent review does not cover merge commit",
)

#: Misclassified review wording. The claim controls read "independently validated" as an
#: unscoped assertion, so the front doors must phrase non-coverage a different way.
POST_MERGE_CONTINUITY_MISDESCRIPTIONS = (
    "is not independently validated",
    "are not independently validated",
)

#: References that identify the continuity candidate published as PR 41.
CONTINUITY_CANDIDATE_REFERENCES = (
    "4576fea067d33c2c0f8e8fc2d49bb506c52b2f1c",
    "pull request 41",
    "pr 41",
)

#: Verbs that assert a finding was disposed of by the text they appear in.
CLOSURE_MARKERS = ("clos", "resolv", "fixes", "fixed")

#: Characters of context inspected either side of a GG001-M01 mention. Wide enough to span a
#: sentence and its neighbour, so a claim split across a clause boundary is still caught.
GG001_CONTEXT = 240

#: The eight preregistered OIC-Bench benchmarks. Every one must remain an unmeasured target.
OIC_BENCH_ROWS = (
    "Source-supported executable fields",
    "Unsupported executable-field rate",
    "Unknown-to-false conversions",
    "Authority Reconstruction F1",
    "Ambiguity recall",
    "False-resolution rate",
    "Behavioral conformance",
    "Change-impact recall",
)

#: Markers for the bounded-results disclosure. Each states a fact that is true of the
#: bounded evidence and false of an OIC-Bench measurement.
BOUNDED_DISCLOSURE_PHRASES = (
    "nothing in oic-bench has been measured",
    "test counts measure the test suite",
    "they are not benchmark results",
)

#: Headings that open the bounded-results disclosure in each front door.
BOUNDED_DISCLOSURE_HEADINGS = {
    "README.md": "### What has actually been measured",
    "STATUS.md": "## Bounded results established, and what they are not",
}

#: Producing candidate commit to its tree. Every numeric bounded-result bullet must name a
#: candidate from this mapping together with that candidate's tree, so no figure can travel
#: without the exact repository state that produced it.
BOUNDED_RESULT_BINDINGS = {
    "c0108a7a80585d6f5732407d4904ba815073ecd2": "1d12b17aad7977c939090909171183be166cfd50",
    "a2b5053771ce510fb35ce09f3e99f545c21ac20e": "b8e31ec4786a2fd1aca976a6ff047deeee63ef15",
}

#: The absence statement must be bounded to the evidence universe and date that support it.
PRACTITIONER_BOUNDING_PHRASES = (
    "within the authorized oic evidence universe examined by oic-nim-evidence-crosswalk-001 "
    "as of 2026-09-07",
    "not a claim about any work outside it",
)

#: Substrings of the bounding phrases that survive on a single source line. The phrases above
#: are asserted against whitespace-normalized text so hard wrapping cannot defeat them; these
#: anchors exist so a mutation can delete a bound from the raw file.
PRACTITIONER_BOUNDING_LINE_ANCHORS = (
    "OIC-NIM-EVIDENCE-CROSSWALK-001 as of 2026-09-07",
    "not a claim about any",
)

#: Unbounded absolute phrasings of the same statement. These assert something about all work
#: everywhere, which no evidence in the authorized universe supports.
PRACTITIONER_UNBOUNDED_WORDINGS = (
    "exists, so no comparative statement is supported in either direction",
    "exists, so no comparative statement of any kind is supported",
)


def _bounded_result_bullets(text: str, relpath: str) -> list[str]:
    """Return the bullet items of the bounded-results disclosure, each joined to one line."""
    heading = BOUNDED_DISCLOSURE_HEADINGS[relpath]
    assert heading in text, f"missing bounded-results heading in {relpath}"
    section = text.split(heading, 1)[1]
    for line in section.splitlines():
        if line.startswith("#"):
            section = section.split("\n" + line, 1)[0]
            break
    bullets: list[str] = []
    for line in section.splitlines():
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line.startswith("  ") and bullets:
            bullets[-1] += " " + line.strip()
    assert bullets, f"no bounded-results bullets found in {relpath}"
    return bullets


def _assert_bounded_results_are_candidate_bound(text: str, relpath: str) -> None:
    """Every bounded-result bullet must carry its producing candidate commit and tree."""
    for bullet in _bounded_result_bullets(text, relpath):
        normalized = " ".join(bullet.lower().replace("`", "").split())
        cited = [c for c in BOUNDED_RESULT_BINDINGS if c in normalized]
        assert cited, f"bounded-result bullet names no producing candidate: {bullet[:80]!r}"
        for candidate in cited:
            tree = BOUNDED_RESULT_BINDINGS[candidate]
            assert tree in normalized, (
                f"bounded-result bullet cites candidate {candidate} without its tree {tree}"
            )


def _assert_practitioner_absence_is_bounded(text: str) -> None:
    """The practitioner/baseline absence statement must name its evidence universe and date."""
    normalized = " ".join(text.lower().replace("*", "").split())
    for phrase in PRACTITIONER_BOUNDING_PHRASES:
        assert phrase in normalized, f"practitioner absence statement is unbounded: {phrase}"
    for phrase in PRACTITIONER_UNBOUNDED_WORDINGS:
        assert phrase not in normalized, (
            f"practitioner absence statement asserts an unbounded universal: {phrase}"
        )


def _assert_post_merge_continuity(text: str) -> None:
    """Require the PR #41 continuity merge to be recorded, scoped and not overstated."""
    normalized = " ".join(text.lower().replace("*", "").split())
    for anchor in POST_MERGE_CONTINUITY_ANCHORS:
        assert anchor in normalized, f"missing continuity anchor: {anchor}"
    for phrase in POST_MERGE_CONTINUITY_PHRASES:
        assert phrase in normalized, f"missing continuity statement: {phrase}"
    for phrase in POST_MERGE_CONTINUITY_MISDESCRIPTIONS:
        assert phrase not in normalized, f"continuity merge is misdescribed: {phrase}"
    _assert_gg001_is_not_attributed_to_the_continuity_candidate(normalized)


def _assert_gg001_is_not_attributed_to_the_continuity_candidate(normalized: str) -> None:
    """Reject only a contextual misattribution of GG001-M01 to the continuity candidate.

    GG001-M01 is a real Gate G finding and the repository is free to discuss it accurately.
    What must fail closed is text that credits candidate 4576fea/PR 41 with disposing of it,
    because that candidate closes the state-acknowledgment finding SAK001C-F01/SAK001-F01.
    A bare prohibition on the identifier would forbid honest history, so the control is
    scoped to co-occurrence of the finding, a continuity reference and a closure verb.
    """
    start = 0
    while True:
        found = normalized.find("gg001-m01", start)
        if found < 0:
            return
        start = found + len("gg001-m01")
        window = normalized[max(0, found - GG001_CONTEXT) : start + GG001_CONTEXT]
        if not any(marker in window for marker in CLOSURE_MARKERS):
            continue
        cited = [ref for ref in CONTINUITY_CANDIDATE_REFERENCES if ref in window]
        assert not cited, (
            "continuity merge is misdescribed: GG001-M01 is attributed to the continuity "
            f"candidate near {cited[0]!r}"
        )


def _assert_bounded_results_disclosure(text: str) -> None:
    """Require the bounded-results disclosure and refuse a benchmark reading of it."""
    normalized = " ".join(text.lower().replace("*", "").split())
    for phrase in BOUNDED_DISCLOSURE_PHRASES:
        assert phrase in normalized, f"missing bounded-results disclosure: {phrase}"
    for candidate, passed in (
        ("c0108a7a80585d6f5732407d4904ba815073ecd2", "1714 passed"),
        ("a2b5053771ce510fb35ce09f3e99f545c21ac20e", "1720 passed"),
    ):
        assert candidate in normalized, f"bounded result is unscoped: missing {candidate}"
        assert passed in normalized, f"bounded result is missing its count: {passed}"


@pytest.mark.parametrize("relpath", ("README.md", "STATUS.md"))
def test_post_merge_continuity_is_recorded_in_both_front_doors(
    repo_root: Path, relpath: str
) -> None:
    """Both front doors must record the PR #41 merge without overstating its review status.

    Fail-closed coverage: removing any anchor, dropping the non-coverage statement, or
    reattributing the candidate to Gate G finding GG001-M01 must each fail.
    """
    text = (repo_root / relpath).read_text(encoding="utf-8")
    _assert_post_merge_continuity(text)

    for anchor in POST_MERGE_CONTINUITY_ANCHORS:
        stripped = text.replace(anchor, "0" * 40)
        with pytest.raises(AssertionError, match="missing continuity anchor"):
            _assert_post_merge_continuity(stripped)

    dropped = re.sub(
        r"Independent review does not cover merge commit",
        "Review notes",
        text,
        flags=re.IGNORECASE,
    )
    assert dropped != text
    with pytest.raises(AssertionError, match="missing continuity statement"):
        _assert_post_merge_continuity(dropped)

    misattributed = text + "\nGG001-M01 is closed by pull request 41.\n"
    with pytest.raises(AssertionError, match="continuity merge is misdescribed"):
        _assert_post_merge_continuity(misattributed)

    misclassified = text + "\nThe current main is not independently validated.\n"
    with pytest.raises(AssertionError, match="continuity merge is misdescribed"):
        _assert_post_merge_continuity(misclassified)


@pytest.mark.parametrize("relpath", ("README.md", "STATUS.md"))
def test_bounded_results_disclosure_is_present_and_scoped(repo_root: Path, relpath: str) -> None:
    """Bounded results must be disclosed as bounded, with each figure bound to its candidate."""
    text = (repo_root / relpath).read_text(encoding="utf-8")
    _assert_bounded_results_disclosure(text)

    for phrase in BOUNDED_DISCLOSURE_PHRASES:
        removed = re.sub(re.escape(phrase), "removed", text, flags=re.IGNORECASE)
        assert removed != text, f"disclosure phrase not found for mutation: {phrase}"
        with pytest.raises(AssertionError, match="missing bounded-results disclosure"):
            _assert_bounded_results_disclosure(removed)

    unscoped = text.replace("c0108a7a80585d6f5732407d4904ba815073ecd2", "an earlier candidate")
    with pytest.raises(AssertionError, match="bounded result is unscoped"):
        _assert_bounded_results_disclosure(unscoped)


def test_oic_bench_rows_remain_unmeasured_targets(repo_root: Path) -> None:
    """All eight preregistered rows stay TARGET - NOT MEASURED, and the comparative target too.

    Promotion of any row is the single most consequential unsupported claim this repository
    could publish, so it fails closed here rather than depending on review.
    """
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    for row in OIC_BENCH_ROWS:
        pattern = re.compile(
            rf"^\|\s*{re.escape(row)}\s*\|[^|]*\|\s*TARGET - NOT MEASURED\s*\|$",
            re.MULTILINE,
        )
        assert pattern.search(readme), f"OIC-Bench row is not an unmeasured target: {row}"

    assert "PROVISIONAL TARGET - NOT MEASURED - NOT CALIBRATED" in readme, (
        "the provisional comparative target lost its uncalibrated status"
    )

    promoted = readme.replace(
        "| Ambiguity recall | >=0.85 | TARGET - NOT MEASURED |",
        "| Ambiguity recall | >=0.85 | MEASURED - 0.91 |",
    )
    assert promoted != readme
    pattern = re.compile(
        r"^\|\s*Ambiguity recall\s*\|[^|]*\|\s*TARGET - NOT MEASURED\s*\|$", re.MULTILINE
    )
    assert pattern.search(promoted) is None, "row promotion was not detected"


@pytest.mark.parametrize("relpath", ("README.md", "STATUS.md"))
def test_gg001_control_permits_history_and_rejects_misattribution(
    repo_root: Path, relpath: str
) -> None:
    """GG001-M01 may be discussed accurately; crediting the continuity candidate must fail.

    The predecessor control banned the bare identifier, which would have forbidden honest
    history. This proves both halves: an accurate historical mention passes, and every way of
    attributing the finding to candidate 4576fea/PR 41 fails closed.
    """
    text = (repo_root / relpath).read_text(encoding="utf-8")
    _assert_post_merge_continuity(text)

    historical = text + (
        "\nGate G recorded finding GG001-M01 against candidate "
        "a2b5053771ce510fb35ce09f3e99f545c21ac20e as MINOR and non-blocking.\n"
    )
    _assert_post_merge_continuity(historical)

    unrelated_closure = text + (
        "\nGG001-M01 was resolved by a later work order that this document does not describe.\n"
    )
    _assert_post_merge_continuity(unrelated_closure)

    for reference in CONTINUITY_CANDIDATE_REFERENCES:
        misattributed = text + f"\nGG001-M01 is closed by {reference}.\n"
        with pytest.raises(AssertionError, match="GG001-M01 is attributed"):
            _assert_post_merge_continuity(misattributed)

        reversed_order = text + f"\n{reference} closes finding GG001-M01.\n"
        with pytest.raises(AssertionError, match="GG001-M01 is attributed"):
            _assert_post_merge_continuity(reversed_order)


@pytest.mark.parametrize("relpath", ("README.md", "STATUS.md"))
def test_every_bounded_result_bullet_is_candidate_and_tree_bound(
    repo_root: Path, relpath: str
) -> None:
    """No bounded figure may travel without the exact candidate commit and tree behind it."""
    text = (repo_root / relpath).read_text(encoding="utf-8")
    _assert_bounded_results_are_candidate_bound(text, relpath)

    bullets = _bounded_result_bullets(text, relpath)
    assert len(bullets) >= 5, f"expected the full bounded-results list in {relpath}"
    for candidate, tree in BOUNDED_RESULT_BINDINGS.items():
        assert any(candidate in b for b in bullets), f"no bullet cites candidate {candidate}"
        assert any(tree in b for b in bullets), f"no bullet cites tree {tree}"

    for tree in BOUNDED_RESULT_BINDINGS.values():
        stripped = text.replace(f", tree\n  `{tree}`", "").replace(f"tree\n  `{tree}`", "")
        assert stripped != text, f"tree citation not found for mutation: {tree}"
        with pytest.raises(AssertionError, match="without its tree"):
            _assert_bounded_results_are_candidate_bound(stripped, relpath)

    for candidate in BOUNDED_RESULT_BINDINGS:
        anonymised = text.replace(candidate, "an earlier candidate")
        with pytest.raises(AssertionError, match="names no producing candidate|without its tree"):
            _assert_bounded_results_are_candidate_bound(anonymised, relpath)


@pytest.mark.parametrize("relpath", ("README.md", "STATUS.md"))
def test_practitioner_absence_statement_is_bounded_to_its_evidence(
    repo_root: Path, relpath: str
) -> None:
    """The absence of a practitioner baseline is a fact about one evidence set on one date."""
    text = (repo_root / relpath).read_text(encoding="utf-8")
    _assert_practitioner_absence_is_bounded(text)

    for anchor in PRACTITIONER_BOUNDING_LINE_ANCHORS:
        assert anchor in text, f"bounding anchor not found for mutation: {anchor}"
        removed = text.replace(anchor, "removed")
        with pytest.raises(AssertionError, match="practitioner absence statement is unbounded"):
            _assert_practitioner_absence_is_bounded(removed)

    for phrase in PRACTITIONER_UNBOUNDED_WORDINGS:
        unbounded = text + f"\nNo practitioner study or baseline arm {phrase}.\n"
        with pytest.raises(AssertionError, match="asserts an unbounded universal"):
            _assert_practitioner_absence_is_bounded(unbounded)
