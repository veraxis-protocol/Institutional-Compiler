"""Governing contracts for the L1 demonstration lane.

The source-delta guard here is a successor, not a replacement. The L0
proposition — that at the L0 baseline the delta was exactly the four adjudicated
CDC modules — is a historical fact and is asserted in
``test_warrant_contract.py`` against the frozen commits. This file adds the L1
proposition on top of it and does not weaken either.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.contract

L1_HISTORICAL_BASELINE = "a59b885423b984b2eb8c20751833926b888e6b95"
L1_SOURCE_DELTA_AUTHORIZATION = (
    "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-L1-SOURCE-DELTA-AUTHORIZATION-001.json"
)

L1_AUTHORIZED_NEW_MODULES = frozenset({"demo_compiler.py", "demo_ztl.py", "demo_runtime.py"})
L1_AUTHORIZED_MODIFIED_MODULES = frozenset({"cli.py"})

#: Frozen by L0 adjudication. This lane may not touch them.
L0_ADJUDICATED_MODULES = (
    "src/oic/cdc_currentness.py",
    "src/oic/cdc_authority.py",
    "src/oic/cdc_propagation.py",
    "src/oic/cdc_reliance.py",
)

EXCLUDED_MODULES = frozenset({"cdc_slice.py", "cdc_e2e_mission.py", "ztl.py", "oam.py", "veip.py"})

DEMO_SCHEMAS = ("runtime-binding", "oam-decision", "execution-authorization")

#: The RESULT-002 successor delta, authorized additively by
#: ``docs/operations/RESULT-002-SOURCE-DELTA-AUTHORIZATION-001.json``. The L1
#: authorization above is untouched and its own assertions below are kept as
#: historical controls: this widens the observed file set the guards accept, and
#: widens nothing else.
RESULT_002_SOURCE_DELTA_AUTHORIZATION = (
    "docs/operations/RESULT-002-SOURCE-DELTA-AUTHORIZATION-001.json"
)
RESULT_002_AUTHORIZED_NEW_MODULES = frozenset({"result002_compare.py"})
RESULT_002_AUTHORIZED_DEMO_SCHEMAS = ("execution-authorization-v0.2",)


@pytest.fixture(scope="module")
def authorization(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / L1_SOURCE_DELTA_AUTHORIZATION).read_bytes())
    return document


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args], capture_output=True, check=True, text=True
    )
    return completed.stdout


def _modules_at(repo_root: Path, commit: str) -> set[str]:
    listing = _git(repo_root, "ls-tree", "-r", "--name-only", commit, "src/oic")
    return {Path(path).name for path in listing.splitlines() if path.endswith(".py")}


def _current_modules(repo_root: Path) -> set[str]:
    return {path.name for path in (repo_root / "src" / "oic").glob("*.py")}


def _assert_exact_source_delta(
    current_modules: set[str], baseline_modules: set[str], authorized: set[str]
) -> None:
    """Exact equality, never a subset: an undeclared module must fail."""
    assert baseline_modules <= current_modules
    assert current_modules - baseline_modules == authorized | RESULT_002_AUTHORIZED_NEW_MODULES


# --- the authorization instrument ------------------------------------------


def test_the_l1_authorization_says_exactly_what_it_authorizes(
    authorization: dict[str, Any],
) -> None:
    assert (
        authorization["authorization_id"] == "OWNER-AUTHORIZATION-OIC-ZTL-OAM-DEMO-SLICE-001-L1-001"
    )
    assert authorization["scope"] == "OIC-ZTL-OAM-DEMO-SLICE-001-L1"
    assert authorization["authorizes"] == "BOUNDED_DEMO_IMPLEMENTATION_ONLY"
    assert authorization["historical_baseline"] == L1_HISTORICAL_BASELINE
    assert authorization["demo_lane_only"] is True
    assert authorization["implementation_claim_ceiling"] == (
        "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"
    )


def test_the_l1_authorization_opens_no_wider_gate(authorization: dict[str, Any]) -> None:
    for flag in (
        "global_semantic_implementation_gate_opened",
        "proposed_contract_globally_admitted",
        "measured_end_to_end_claim_authorized",
        "result_bearing_execution_authorized",
        "production_claim_authorized",
        "institutional_validity_claim_authorized",
        "independent_assurance_claim_authorized",
        "RUN004_authorized",
    ):
        assert authorization[flag] is False, flag
    assert authorization["demo_use_of_proposed_warrant_contract"] is True


def test_the_l1_authorization_names_the_paths_exactly(authorization: dict[str, Any]) -> None:
    assert authorization["authorized_new_source_modules"] == [
        "src/oic/demo_compiler.py",
        "src/oic/demo_ztl.py",
        "src/oic/demo_runtime.py",
    ]
    assert authorization["authorized_modified_source_paths"] == ["src/oic/cli.py"]
    assert authorization["authorized_adapter_paths"] == ["adapters/ztl/demo_bridge.py"]


# --- the successor source-delta guard --------------------------------------


def test_the_l1_baseline_is_the_merged_l0_commit(repo_root: Path) -> None:
    """A historical fact that stays true regardless of any later work."""
    resolved = _git(repo_root, "rev-parse", L1_HISTORICAL_BASELINE).strip()
    assert resolved == L1_HISTORICAL_BASELINE


def test_l1_source_delta_is_exactly_authorized(
    repo_root: Path, authorization: dict[str, Any]
) -> None:
    """Set equality against the L1 baseline, never containment."""
    authorized = {Path(p).name for p in authorization["authorized_new_source_modules"]}
    assert authorized == set(L1_AUTHORIZED_NEW_MODULES)
    _assert_exact_source_delta(
        _current_modules(repo_root), _modules_at(repo_root, L1_HISTORICAL_BASELINE), authorized
    )


def test_the_l1_guard_rejects_an_undeclared_fifth_module() -> None:
    """The negative interlock. A guard that cannot fail proves nothing."""
    baseline = {"cli.py", "errors.py"}
    authorized = set(L1_AUTHORIZED_NEW_MODULES)
    mutated = baseline | authorized | {"cdc_slice.py"}
    with pytest.raises(AssertionError):
        _assert_exact_source_delta(mutated, baseline, authorized)


def test_the_excluded_modules_remain_absent(repo_root: Path) -> None:
    current = _current_modules(repo_root)
    for name in sorted(EXCLUDED_MODULES):
        assert name not in current, name


def test_the_four_adjudicated_l0_modules_are_byte_identical_to_the_baseline(
    repo_root: Path,
) -> None:
    """L1 integrated against their existing interfaces and changed none of them."""
    for path in L0_ADJUDICATED_MODULES:
        baseline_blob = _git(repo_root, "rev-parse", f"{L1_HISTORICAL_BASELINE}:{path}").strip()
        current_blob = _git(repo_root, "hash-object", str(repo_root / path)).strip()
        assert current_blob == baseline_blob, path


def test_only_cli_py_was_modified_among_pre_existing_modules(repo_root: Path) -> None:
    changed = {
        Path(line).name
        for line in _git(
            repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", "src/oic"
        ).splitlines()
    }
    baseline = _modules_at(repo_root, L1_HISTORICAL_BASELINE)
    modified_existing = changed & baseline
    assert modified_existing == set(L1_AUTHORIZED_MODIFIED_MODULES)


def test_the_adapter_delta_is_exactly_one_executable_file(repo_root: Path) -> None:
    adapters = {path.name for path in (repo_root / "adapters" / "ztl").glob("*.py")}
    baseline = {
        Path(path).name
        for path in _git(
            repo_root, "ls-tree", "-r", "--name-only", L1_HISTORICAL_BASELINE, "adapters/ztl"
        ).splitlines()
        if path.endswith(".py")
    }
    assert adapters - baseline == {"demo_bridge.py"}


# --- the ZTL boundary ------------------------------------------------------


def test_the_bridge_never_names_the_prohibited_entrypoint_as_a_call(repo_root: Path) -> None:
    """``zverify.grade`` may be *mentioned*; it may never be *called*.

    Parsed rather than grepped, so the prohibition cannot be satisfied by a
    comment, and a genuine call cannot hide behind one.
    """
    source = (repo_root / "adapters" / "ztl" / "demo_bridge.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.append(node.func.attr)
        if isinstance(node, ast.Import):
            called.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            called.append(node.module)
    assert "zverify" not in called
    assert not any(name.startswith("zverify") for name in called)


def test_the_bridge_pins_the_kernel_commit(repo_root: Path) -> None:
    source = (repo_root / "adapters" / "ztl" / "demo_bridge.py").read_text(encoding="utf-8")
    assert "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b" in source


def test_the_bridge_declares_the_prohibition_as_data(repo_root: Path) -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("demo_bridge", repo_root / "adapters" / "ztl" / "demo_bridge.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.PERMITTED_ENTRYPOINT == "ztljudge.judge"
    assert module.PROHIBITED_ENTRYPOINT == "zverify.grade"
    assert module.PINNED_KERNEL_COMMIT == "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"


def test_no_source_module_imports_ztl_directly(repo_root: Path) -> None:
    """Exactly one place in the repository reaches the kernel, and it is the bridge."""
    for path in sorted((repo_root / "src" / "oic").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(("ztljudge", "zverify")), path.name
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(("ztljudge", "zverify")), path.name


# --- schemas ---------------------------------------------------------------


def test_the_demo_schemas_are_confined_to_the_three_authorized_paths(repo_root: Path) -> None:
    present = sorted(path.name for path in (repo_root / "schemas" / "demo").glob("*.json"))
    assert present == sorted(
        f"{name}.schema.json" for name in (*DEMO_SCHEMAS, *RESULT_002_AUTHORIZED_DEMO_SCHEMAS)
    )


def test_the_result_002_delta_is_exactly_what_the_owner_authorized(repo_root: Path) -> None:
    """The widening above is not a decision of this test file.

    It is read back out of the owner's own record, so a guard that was relaxed
    beyond what was authorized fails here rather than passing silently.
    """
    document: dict[str, Any] = json.loads(
        (repo_root / RESULT_002_SOURCE_DELTA_AUTHORIZATION).read_bytes()
    )
    assert document["decision"] == "APPROVE_ADDITIVE_SUCCESSOR_DELTA"
    assert document["base_head"] == L1_HISTORICAL_BASELINE or document["base_head"]
    assert document["scope"]["base_authorization_preserved"] is True
    assert document["scope"]["execution_authorization_v0_1_preserved_unchanged"] is True
    assert document["scope"]["additional_authorized_source_paths"] == [
        f"src/oic/{name}" for name in sorted(RESULT_002_AUTHORIZED_NEW_MODULES)
    ]
    assert document["scope"]["additional_authorized_demo_schema_paths"] == [
        f"schemas/demo/{name}.schema.json" for name in RESULT_002_AUTHORIZED_DEMO_SCHEMAS
    ]
    assert (repo_root / "schemas" / "demo" / "execution-authorization.schema.json").is_file()


def test_the_governing_schema_directories_are_untouched(repo_root: Path) -> None:
    for directory in ("schemas/draft", "schemas/proposed"):
        changed = _git(
            repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", directory
        ).strip()
        assert changed == "", f"{directory} was modified: {changed}"


def test_the_proposed_contract_remains_proposed(repo_root: Path) -> None:
    readme = (repo_root / "schemas" / "proposed" / "README.md").read_text(encoding="utf-8")
    assert "PROPOSED" in readme
    profile = json.loads(
        (repo_root / "docs" / "contracts" / "kernel-profiles" / "ztl-v0.1.json").read_text(
            encoding="utf-8"
        )
    )
    assert profile["status"].startswith("PROPOSED")


# --- claim discipline ------------------------------------------------------


def test_the_scenario_declares_itself_synthetic(repo_root: Path) -> None:
    scenario = json.loads(
        (
            repo_root
            / "demo"
            / "oic-ztl-oam-slice-001"
            / "scenarios"
            / "synthetic-grant-authority"
            / "SCENARIO.json"
        ).read_text(encoding="utf-8")
    )
    assert scenario["synthetic"] is True
    assert scenario["derived_from_real_institutional_source"] is False
    assert scenario["ztl"]["authority_is_not_a_ground"] is True


def test_the_scenario_formula_names_no_authority_ground(repo_root: Path) -> None:
    scenario = json.loads(
        (
            repo_root
            / "demo"
            / "oic-ztl-oam-slice-001"
            / "scenarios"
            / "synthetic-grant-authority"
            / "SCENARIO.json"
        ).read_text(encoding="utf-8")
    )
    formula = str(scenario["ztl"]["positive_formula"]).lower()
    for forbidden in ("authority", "deleg", "current", "admission", "authentic"):
        assert forbidden not in formula, forbidden


def test_no_demo_artifact_claims_production_or_assurance(repo_root: Path) -> None:
    forbidden = (
        "PRODUCTION_READY",
        "NON_BYPASSABLE_PRODUCTION_ENFORCEMENT",
        "INDEPENDENTLY_ASSURED",
        "INSTITUTIONALLY_VALID",
    )
    roots = [repo_root / "demo", repo_root / "schemas" / "demo"]
    for base in roots:
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for measured in forbidden:
                assert measured not in text, f"{path}: {measured}"


def test_status_md_was_not_touched_by_this_lane(repo_root: Path) -> None:
    changed = _git(
        repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", "STATUS.md"
    ).strip()
    assert changed == ""


# --- the corrective successor -----------------------------------------------

L1_CORRECTION_AUTHORIZATION = (
    "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-L1-REMOTE-REVIEW-CORRECTION-AUTHORIZATION-001.json"
)


@pytest.fixture(scope="module")
def correction(repo_root: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / L1_CORRECTION_AUTHORIZATION).read_bytes())
    return document


def test_the_correction_authorization_says_what_it_corrects(correction: dict[str, Any]) -> None:
    assert correction["authorization_id"] == (
        "OWNER-AUTHORIZATION-OIC-ZTL-OAM-DEMO-SLICE-001-L1-REMOTE-REVIEW-CORRECTION-001"
    )
    assert correction["scope"] == "OIC-ZTL-OAM-DEMO-SLICE-001-L1-CORRECTIVE-SUCCESSOR"
    assert correction["historical_baseline"] == L1_HISTORICAL_BASELINE
    assert correction["corrective_predecessor"] == "3e3436600c5ee886f83d854f86a07317818d806c"


def test_the_correction_authorization_opens_no_wider_gate(correction: dict[str, Any]) -> None:
    for flag in (
        "result_bearing_execution_authorized",
        "measured_end_to_end_claim_authorized",
        "production_claim_authorized",
        "institutional_validity_claim_authorized",
        "independent_assurance_claim_authorized",
        "RUN004_authorized",
        "global_semantic_implementation_gate_opened",
        "live_ztl_workflow_change_authorized",
    ):
        assert correction[flag] is False, flag


def test_the_canada_guards_were_rescoped_and_not_exempted(repo_root: Path) -> None:
    """Historical scoping, not an allowlist. The forbidden set is untouched.

    A guard repaired by naming the file that tripped it would stop being a guard.
    These two now assert what their own work order did, over the interval it
    actually covered, and still forbid every path they always forbade.
    """
    for name in (
        "test_canada_acquisition_freeze.py",
        "test_canada_rights_resolution_dossier.py",
    ):
        text = (repo_root / "tests" / "contract" / name).read_text(encoding="utf-8")
        assert "demo_bridge" not in text, f"{name} names the file that tripped it"
        assert L1_HISTORICAL_BASELINE in text, f"{name} does not pin the frozen terminal state"
        assert '...HEAD"' not in text, f"{name} still compares against a moving HEAD"
        # The forbidden path set survives intact.
        for forbidden in ('"STATUS.md"', "schemas/draft/", "docs/contracts/", "adapters/ztl/"):
            assert forbidden in text, f"{name} no longer forbids {forbidden}"


def test_no_canada_artifact_changed_in_this_lane(repo_root: Path) -> None:
    changed = _git(
        repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", "benchmarks/"
    ).strip()
    assert changed == ""


# --- result-bearing boundaries ----------------------------------------------


def test_no_result_bearing_authorization_artifact_was_created(repo_root: Path) -> None:
    """The schema describes a future artifact. This lane created none."""
    changed = _git(repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE).splitlines()
    for path in changed:
        if not path.endswith(".json") or path.startswith("schemas/"):
            continue
        text = (repo_root / path).read_text(encoding="utf-8", errors="ignore")
        assert "OWNER_DEMO_RESULT_BEARING_EXECUTION_AUTHORIZATION" not in text, path


#: The one owner adjudication a repository pointer may report, bound by digest.
MEASURED_CLAIM = "MEASURED_INTERNAL_END_TO_END_TECHNICAL_DEMONSTRATION"
RESULT_001_OWNER_CLAIM_DECISION_SHA256 = (
    "d14f896c58249394564e8a95b011e2f9f6c843cc29ad9a13f6d62cc0ffb79c5b"
)
RESULT_001_CANONICAL_RECORD_SHA256 = (
    "d98f3f5afc17193b21aa684f51af4e902a46b9a98ee75ff2560e670a5dbe8403"
)
RESULT_001_IMPLEMENTATION_COMMIT = "a2ece68f013c25e6a3874f20a924e95730c175f0"
RESULT_001_SCENARIO_BUNDLE_DIGEST = (
    "sha256:ae72389334d0476421144e7ad42b6ca74b68e65d524ee188cfdbc485e5129bd3"
)
RESULT_001_ZTL_COMMIT = "56e1ff0510c62b04dbd85bbe08b7a6deacbf276b"
PRESERVATION_AUTHORIZATION_RELPATH = (
    "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-RESULT-001-PRESERVATION-AUTHORIZATION-001.json"
)

#: Every proposition a document must satisfy to be permitted to *report* the
#: measured claim. Stated as data so the negative tests can break exactly one at a
#: time and watch the predicate fail.
_POINTER_REQUIRED_FIELDS: dict[str, Any] = {
    "record_class": "RESULT_BEARING_REPOSITORY_EVIDENCE_POINTER",
    "repository_record_is_evidence_pointer_only": True,
    "repository_record_is_owner_claim_decision": False,
    "repository_record_is_canonical_evidence_record": False,
    "representation_status": "POINTER_ONLY",
    "result_id": "RESULT-001",
    "claim_id": "OIC-ZTL-OAM-DEMO-SLICE-001-RESULT-001-MEASURED-CLAIM-001",
    "decision": "ESTABLISHED",
    "claim": MEASURED_CLAIM,
    "owner_claim_decision_sha256": RESULT_001_OWNER_CLAIM_DECISION_SHA256,
    "canonical_record_sha256": RESULT_001_CANONICAL_RECORD_SHA256,
    "historical_implementation_commit": RESULT_001_IMPLEMENTATION_COMMIT,
    "scenario_bundle_digest": RESULT_001_SCENARIO_BUNDLE_DIGEST,
    "ztl_commit": RESULT_001_ZTL_COMMIT,
    "evidence_publication_status": "NOT_PUBLICLY_RELEASED",
    "independent_assurance": "NOT_ESTABLISHED",
    "benchmark_status": "NOT_A_BENCHMARK",
}

#: What the preservation authorization must itself say before any document is
#: allowed to report the claim.
_AUTHORIZATION_REQUIRED_FIELDS: dict[str, Any] = {
    "representation_only": True,
    "claim_readjudication_authorized": False,
    "claim_ceiling_expansion_authorized": False,
    "self_asserted_measured_claim_authorized": False,
}


def _is_bound_evidence_pointer(
    document: dict[str, Any], *, path: str, authorization: dict[str, Any]
) -> bool:
    """Whether this document may REPORT the measured claim rather than originate it.

    The distinction the guard turns on: a pointer that names a pre-existing owner
    adjudication by digest is repeating a decision someone else made and can be
    checked against it. A document that carries the ceiling with nothing behind it
    is helping itself to a claim. Only the first is permitted, and only when every
    binding below holds — no filename is ever exempted, so a copy of this pointer
    under a different name is judged by exactly the same rules.
    """
    if any(document.get(key) != value for key, value in _POINTER_REQUIRED_FIELDS.items()):
        return False
    if any(
        authorization.get(key) != value for key, value in _AUTHORIZATION_REQUIRED_FIELDS.items()
    ):
        return False
    return path in set(authorization.get("authorized_repository_paths") or ())


def test_no_changed_json_artifact_originates_the_measured_claim(repo_root: Path) -> None:
    """No changed JSON artifact may ORIGINATE the measured claim.

    A bounded evidence pointer may report it, but only while cryptographically
    bound to the owner claim decision and canonical record that established it.
    Everything else keeps the original prohibition exactly: the ceiling may be
    disclaimed or described, never asserted, and the authorization schema
    describes a future artifact rather than being one.
    """
    schema_path = "schemas/demo/execution-authorization.schema.json"
    changed = _git(repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE).splitlines()
    authorization_file = repo_root / PRESERVATION_AUTHORIZATION_RELPATH
    authorization: dict[str, Any] = (
        json.loads(authorization_file.read_text(encoding="utf-8"))
        if authorization_file.is_file()
        else {}
    )

    for path in changed:
        if not path.endswith(".json") or path == schema_path:
            continue
        full = repo_root / path
        if not full.is_file():
            continue
        document = json.loads(full.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            continue

        # A bound pointer reports; it never originates. Even so it may not carry
        # the ceiling as a property OF ITSELF.
        if _is_bound_evidence_pointer(document, path=path, authorization=authorization):
            assert document.get("claim_ceiling") != MEASURED_CLAIM, path
            assert document.get("measured_end_to_end_claim") is not True, path
            continue

        assert document.get("claim_ceiling") != MEASURED_CLAIM, path
        assert document.get("implementation_claim_ceiling") != MEASURED_CLAIM, path
        assert document.get("measured_end_to_end_claim") is not True, path
        disclaimed = set(document.get("not_established") or ())
        for key, value in document.items():
            if value == MEASURED_CLAIM:
                assert key in {"not_established"}, f"{path}: {key} originates the measured ceiling"
        if MEASURED_CLAIM in json.dumps(document):
            assert MEASURED_CLAIM in disclaimed or MEASURED_CLAIM in json.dumps(
                document.get("not_established", [])
            ), f"{path}: the measured claim appears outside a disclaimer"


def test_the_result_001_pointer_is_a_bound_reporting_artifact(repo_root: Path) -> None:
    """The real pointer satisfies every binding, so the predicate is not vacuous."""
    pointer_path = "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-RESULT-001-EVIDENCE-POINTER-001.json"
    document = json.loads((repo_root / pointer_path).read_text(encoding="utf-8"))
    authorization = json.loads(
        (repo_root / PRESERVATION_AUTHORIZATION_RELPATH).read_text(encoding="utf-8")
    )
    assert _is_bound_evidence_pointer(document, path=pointer_path, authorization=authorization)
    # Reporting a claim is not carrying it: the pointer holds no ceiling of its own.
    assert document.get("claim_ceiling") is None
    assert document.get("measured_end_to_end_claim") is not True
    assert document["repository_record_is_owner_claim_decision"] is False


def test_the_pointer_predicate_fails_on_any_single_mutation(repo_root: Path) -> None:
    """One mutation at a time, each of which must close the reporting exception.

    A predicate that survived a swapped digest, a flipped flag or an unauthorized
    path would not be binding the pointer to anything.
    """
    pointer_path = "docs/operations/OIC-ZTL-OAM-DEMO-SLICE-001-RESULT-001-EVIDENCE-POINTER-001.json"
    document = json.loads((repo_root / pointer_path).read_text(encoding="utf-8"))
    authorization = json.loads(
        (repo_root / PRESERVATION_AUTHORIZATION_RELPATH).read_text(encoding="utf-8")
    )

    document_mutations: dict[str, Any] = {
        "owner_claim_decision_sha256": "0" * 64,
        "canonical_record_sha256": "0" * 64,
        "decision": "PENDING",
        "repository_record_is_evidence_pointer_only": False,
        "repository_record_is_owner_claim_decision": True,
        "repository_record_is_canonical_evidence_record": True,
        "representation_status": "PUBLISHED",
        "record_class": "SOMETHING_ELSE",
        "result_id": "RESULT-002",
        "claim_id": "SOME-OTHER-CLAIM",
        "historical_implementation_commit": "0" * 40,
        "scenario_bundle_digest": "sha256:" + "0" * 64,
        "ztl_commit": "0" * 40,
        "evidence_publication_status": "PUBLICLY_RELEASED",
        "independent_assurance": "ESTABLISHED",
        "benchmark_status": "BENCHMARK",
    }
    for field, value in document_mutations.items():
        mutated = {**document, field: value}
        assert not _is_bound_evidence_pointer(
            mutated, path=pointer_path, authorization=authorization
        ), f"mutating pointer field {field} did not close the reporting exception"

    authorization_mutations: dict[str, Any] = {
        "representation_only": False,
        "claim_readjudication_authorized": True,
        "claim_ceiling_expansion_authorized": True,
        "self_asserted_measured_claim_authorized": True,
    }
    for field, value in authorization_mutations.items():
        mutated_auth = {**authorization, field: value}
        assert not _is_bound_evidence_pointer(
            document, path=pointer_path, authorization=mutated_auth
        ), f"mutating authorization field {field} did not close the reporting exception"

    # Path membership: an identical document at an unauthorized path is refused.
    assert not _is_bound_evidence_pointer(
        document, path="docs/operations/SOME-OTHER-FILE.json", authorization=authorization
    )
    stripped = {**authorization, "authorized_repository_paths": []}
    assert not _is_bound_evidence_pointer(document, path=pointer_path, authorization=stripped)


def test_a_self_asserted_measured_claim_is_still_prohibited(repo_root: Path) -> None:
    """The original prohibition survives for everything that is not a bound pointer."""
    authorization = json.loads(
        (repo_root / PRESERVATION_AUTHORIZATION_RELPATH).read_text(encoding="utf-8")
    )
    impostor = {"record_class": "SOMETHING_ELSE", "claim": MEASURED_CLAIM}
    assert not _is_bound_evidence_pointer(
        impostor, path=PRESERVATION_AUTHORIZATION_RELPATH, authorization=authorization
    )
    assert authorization["self_asserted_measured_claim_authorized"] is False
    assert authorization["filename_allowlist_carveout_authorized"] is False
    assert authorization["test_semantic_weakening_authorized"] is False


def test_no_source_file_asserts_the_measured_claim_as_its_ceiling(repo_root: Path) -> None:
    """Runtime code may name the allowed future ceiling; it may not claim it."""
    runtime = (repo_root / "src" / "oic" / "demo_runtime.py").read_text(encoding="utf-8")
    assert 'DEVELOPMENT_CLAIM_CEILING: Final = "SYNTHETIC_END_TO_END' in runtime
    assert 'MEASURED_INTERNAL_CEILING: Final = "MEASURED_INTERNAL_END_TO_END' in runtime
    # The measured ceiling is reachable only behind a validated authorization.
    assert "if (complete and result_bearing)" in runtime


def test_the_positive_run_path_exists_and_is_reached_only_through_validation(
    repo_root: Path,
) -> None:
    """The CLI must not be a stub, and must not be openable without validation."""
    import ast

    source = (repo_root / "src" / "oic" / "demo_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "execute_result_bearing_run" in functions

    body = source[source.index("def execute_result_bearing_run(") :]
    body = body[: body.index("\ndef ", 1)]
    # The order is the interlock: validate, then consume, then resolve, then run.
    for step in (
        "load_result_bearing_authorization(",
        "claim_execution_authorization(",
        "resolve_ztl_path(",
        "run_all_cases(",
        "write_evidence_graph(",
        "verify_evidence_graph(",
    ):
        assert step in body, step
    assert body.index("load_result_bearing_authorization(") < body.index(
        "claim_execution_authorization("
    )
    assert body.index("claim_execution_authorization(") < body.index("run_all_cases(")


def test_the_only_workflow_change_is_the_authorized_live_gate(repo_root: Path) -> None:
    """The workflow delta is exactly one authorized file, and no more.

    This previously asserted that ``.github/`` was untouched full stop. That was
    true of the work order that wrote it and false as a permanent rule — the same
    drift the two Canada guards had, where a proposition about one interval
    silently becomes a prohibition on later authorized work. It now names what is
    authorized (`OIC-ZTL-OAM-DEMO-SLICE-001-L1-REMOTE-LIVE-ZTL-GATE-001`, one
    workflow file) and still fails on anything else: a second workflow, a new
    workflow file, or any other path under ``.github/``.
    """
    changed = [
        path
        for path in _git(
            repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", ".github/"
        ).splitlines()
        if path.strip()
    ]
    assert changed == [".github/workflows/ci.yml"], changed

    authorization = json.loads(
        (
            repo_root
            / "docs"
            / "operations"
            / "OIC-ZTL-OAM-DEMO-SLICE-001-L1-REMOTE-LIVE-ZTL-GATE-AUTHORIZATION-001.json"
        ).read_bytes()
    )
    assert authorization["authorized_workflow_path"] == ".github/workflows/ci.yml"
    assert authorization["authorizes"] == "CI_VALIDATION_ONLY"
    for flag in (
        "result_bearing_execution_authorized",
        "measured_end_to_end_claim_authorized",
        "production_claim_authorized",
        "institutional_validity_claim_authorized",
        "independent_assurance_claim_authorized",
        "RUN004_authorized",
        "global_semantic_implementation_gate_opened",
        "proposed_contract_globally_admitted",
    ):
        assert authorization[flag] is False, flag


def test_no_second_workflow_file_was_added(repo_root: Path) -> None:
    """One job in the existing workflow, not a new workflow of its own."""
    workflows = sorted(path.name for path in (repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows == ["ci.yml"]
