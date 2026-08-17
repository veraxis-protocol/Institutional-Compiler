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
    assert current_modules - baseline_modules == authorized


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
    assert present == sorted(f"{name}.schema.json" for name in DEMO_SCHEMAS)


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
            for token in forbidden:
                assert token not in text, f"{path}: {token}"


def test_status_md_was_not_touched_by_this_lane(repo_root: Path) -> None:
    changed = _git(
        repo_root, "diff", "--name-only", L1_HISTORICAL_BASELINE, "--", "STATUS.md"
    ).strip()
    assert changed == ""
