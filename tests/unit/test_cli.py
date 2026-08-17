"""Tests for the ``oic`` CLI shell: exit codes and deterministic output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oic.cli import ExitCode, main

SOURCE_MANIFEST_HEADER = (
    "source_id,title,issuer,source_type,official_url_or_origin,license_or_public_basis,"
    "acquired_at,sha256,effective_from,effective_until,supersedes,confidentiality,notes"
)


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    """Invoke the CLI and return ``(exit_code, stdout, stderr)``."""
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------------
# Exit code contract
# ---------------------------------------------------------------------------


def test_exit_code_values_are_the_documented_contract() -> None:
    assert (ExitCode.PASS, ExitCode.FAIL, ExitCode.USAGE, ExitCode.INCOMPLETE) == (0, 1, 2, 3)


# ---------------------------------------------------------------------------
# validate-schema
# ---------------------------------------------------------------------------


def test_validate_schema_succeeds_on_the_governing_set(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "validate-schema")
    assert code == ExitCode.PASS
    assert "9/9 schemas valid" in out
    assert "PASS" in out


def test_validate_schema_accepts_an_explicit_directory(
    capsys: pytest.CaptureFixture[str], repo_root: Path, fixtures_dir: Path
) -> None:
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "validate-schema",
        "--schema-dir",
        str(fixtures_dir / "schemas" / "valid"),
    )
    assert code == ExitCode.PASS
    assert "2/2 schemas valid" in out


def test_validate_schema_fails_on_a_broken_schema(
    capsys: pytest.CaptureFixture[str], repo_root: Path, fixtures_dir: Path
) -> None:
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "validate-schema",
        "--schema-dir",
        str(fixtures_dir / "schemas" / "invalid-metaschema"),
    )
    assert code == ExitCode.FAIL
    assert "INVALID_METASCHEMA" in out


def test_validate_schema_blocks_a_remote_reference(
    capsys: pytest.CaptureFixture[str], repo_root: Path, fixtures_dir: Path
) -> None:
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "validate-schema",
        "--schema-dir",
        str(fixtures_dir / "schemas" / "remote-ref"),
    )
    assert code == ExitCode.FAIL
    assert "EXTERNAL_REF_BLOCKED" in out


def test_validate_schema_missing_directory_is_a_usage_error(
    capsys: pytest.CaptureFixture[str], repo_root: Path, tmp_path: Path
) -> None:
    code, _, err = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "validate-schema",
        "--schema-dir",
        str(tmp_path / "absent"),
    )
    assert code == ExitCode.USAGE
    assert "OIC-1002" in err


def test_validate_schema_json_output_is_deterministic(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    args = ("--repo-root", str(repo_root), "--format", "json", "validate-schema")
    first_code, first_out, _ = run(capsys, *args)
    second_code, second_out, _ = run(capsys, *args)
    assert first_code == second_code == ExitCode.PASS
    assert first_out == second_out

    payload = json.loads(first_out)
    assert payload["status"] == "PASS"
    assert payload["schema_count"] == 9
    assert [result["schema_path"] for result in payload["results"]] == sorted(
        result["schema_path"] for result in payload["results"]
    )
    # Deterministic means no absolute paths and no timestamps leaked into the output.
    assert str(repo_root) not in first_out


# ---------------------------------------------------------------------------
# verify-manifest
# ---------------------------------------------------------------------------


def test_verify_manifest_defaults_to_the_bootstrap_baseline(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "verify-manifest")
    assert code == ExitCode.PASS
    assert "Bootstrap baseline" in out
    assert "RESULT: PASS" in out


def test_verify_bootstrap_passes_on_the_current_checkout(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "verify-bootstrap")
    assert code == ExitCode.PASS
    assert "8b06b8a7f1a319a0b5ceeea6857eefa30b9eb081" in out
    assert "the working tree was neither read nor modified" in out


def test_verify_bootstrap_rejects_an_unknown_ref(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, _, err = run(capsys, "--repo-root", str(repo_root), "verify-bootstrap", "--ref", "0" * 40)
    assert code == ExitCode.USAGE
    assert "could not be resolved" in err


def test_verify_bootstrap_json_output_is_deterministic(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    args = ("--repo-root", str(repo_root), "--format", "json", "verify-bootstrap")
    first_code, first_out, _ = run(capsys, *args)
    second_code, second_out, _ = run(capsys, *args)
    assert first_code == second_code == ExitCode.PASS
    assert first_out == second_out
    payload = json.loads(first_out)
    assert payload["status"] == "PASS"
    assert payload["resolved_commit"] == "8b06b8a7f1a319a0b5ceeea6857eefa30b9eb081"
    assert str(repo_root) not in first_out


def test_explicit_bootstrap_manifest_path_is_refused(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    """Comparing the historical manifest to the working tree must be refused (ADR-012)."""
    code, _, err = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "verify-manifest",
        "--manifest",
        str(repo_root / "BOOTSTRAP_MANIFEST.json"),
    )
    assert code == ExitCode.USAGE
    assert "verify-bootstrap" in err


def test_verify_manifest_all_reports_incomplete_with_exit_code_3(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    """The preflight corpus manifest is header-only, so --all is INCOMPLETE, not PASS."""
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "verify-manifest", "--all")
    assert code == ExitCode.INCOMPLETE
    assert code != ExitCode.PASS
    assert code != ExitCode.FAIL
    assert "OVERALL: INCOMPLETE" in out
    assert "INCOMPLETE is not a pass" in out


def test_allow_incomplete_downgrades_to_zero_but_still_reports(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "verify-manifest",
        "--all",
        "--allow-incomplete",
    )
    assert code == ExitCode.PASS
    assert "OVERALL: INCOMPLETE" in out


def test_verify_manifest_fails_on_a_tampered_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    (tmp_path / "doc.pdf").write_bytes(b"tampered")
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(f"{'0' * 64}  doc.pdf\n", encoding="utf-8")
    code, out, _ = run(
        capsys, "--repo-root", str(tmp_path), "verify-manifest", "--manifest", str(sums)
    )
    assert code == ExitCode.FAIL
    assert "HASH_MISMATCH" in out


def test_verify_manifest_accepts_an_explicit_path_and_kind(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "verify-manifest",
        "--manifest",
        str(repo_root / "docs" / "tdd" / "SHA256SUMS"),
        "--kind",
        "sha256sums",
    )
    assert code == ExitCode.PASS
    assert "SHA256SUMS" in out


def test_verify_manifest_incomplete_for_a_header_only_source_manifest(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    manifest = tmp_path / "SOURCE_MANIFEST.csv"
    manifest.write_text(SOURCE_MANIFEST_HEADER + "\n", encoding="utf-8")
    code, out, _ = run(
        capsys, "--repo-root", str(tmp_path), "verify-manifest", "--manifest", str(manifest)
    )
    assert code == ExitCode.INCOMPLETE
    assert "not corpus-ready" in out


def test_verify_manifest_missing_file_is_a_usage_error(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "BOOTSTRAP_MANIFEST.json").write_text("{}", encoding="utf-8")
    code, _, err = run(
        capsys,
        "--repo-root",
        str(tmp_path),
        "verify-manifest",
        "--manifest",
        str(tmp_path / "SHA256SUMS"),
    )
    assert code == ExitCode.USAGE
    assert "OIC-1003" in err


def test_verify_manifest_json_output_is_deterministic(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    args = ("--repo-root", str(repo_root), "--format", "json", "verify-manifest", "--all")
    first_code, first_out, _ = run(capsys, *args)
    second_code, second_out, _ = run(capsys, *args)
    assert first_code == second_code == ExitCode.INCOMPLETE
    assert first_out == second_out

    payload = json.loads(first_out)
    assert payload["status"] == "INCOMPLETE"
    kinds = [manifest["kind"] for manifest in payload["manifests"]]
    assert kinds == ["sha256sums", "source-manifest"]
    # The bootstrap component of --all is the historical baseline, reported separately.
    assert payload["bootstrap_baseline"]["status"] == "PASS"
    for manifest in payload["manifests"]:
        paths = [entry["path"] for entry in manifest["entries"]]
        assert paths == sorted(paths)
    assert str(repo_root) not in first_out


def test_json_manifest_output_never_reports_an_empty_corpus_as_pass(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    _, out, _ = run(
        capsys, "--repo-root", str(repo_root), "--format", "json", "verify-manifest", "--all"
    )
    payload = json.loads(out)
    source = next(m for m in payload["manifests"] if m["kind"] == "source-manifest")
    assert source["status"] == "INCOMPLETE"
    # The Canada rights freeze recorded CA-3 and left ten source units blocked. A recorded
    # row must never count as a verified one.
    assert source["entry_count"] == 1
    assert source["summary"]["PASS"] == 0
    assert source["summary"]["RECORDED_NOT_VERIFIED"] == 1


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_doctor_exits_zero_and_reports_the_gate(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "doctor")
    assert code == ExitCode.PASS
    assert "semantic implementation gate" in out
    assert "BLOCKED" in out


def test_doctor_text_output_marks_ztl_and_veip_provisional(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    _, out, _ = run(capsys, "--repo-root", str(repo_root), "doctor")
    for boundary in ("ZTL", "VEIP"):
        assert boundary in out
    assert out.count("PROVISIONAL / NOT CONFIGURED") == 2


def test_doctor_text_output_never_claims_production_readiness(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    _, out, _ = run(capsys, "--repo-root", str(repo_root), "doctor")
    lowered = out.lower()
    assert "not production ready" in lowered
    assert lowered.count("production ready") == lowered.count("not production ready")
    for phrase in ("enterprise-ready", "enterprise ready", "outperforms", "guarantees"):
        assert phrase not in lowered


def test_doctor_json_output_parses(capsys: pytest.CaptureFixture[str], repo_root: Path) -> None:
    code, out, _ = run(capsys, "--repo-root", str(repo_root), "--format", "json", "doctor")
    assert code == ExitCode.PASS
    payload = json.loads(out)
    assert {boundary["name"] for boundary in payload["boundaries"]} == {"ZTL", "VEIP"}
    gate = next(c for c in payload["gates"] if c["name"] == "semantic implementation gate")
    assert gate["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_no_subcommand_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == ExitCode.USAGE


def test_unknown_subcommand_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["nonsense"])
    assert excinfo.value.code == ExitCode.USAGE


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "oic" in capsys.readouterr().out


def test_help_text_disclaims_semantic_function(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "no document interpretation" in out
    assert "admission" in out


def test_no_semantic_subcommands_exist() -> None:
    """The CLI must expose infrastructure verbs only while the gate is BLOCKED."""
    from oic.cli import build_parser

    parser = build_parser()
    subparsers = [
        action for action in parser._actions if hasattr(action, "choices") and action.choices
    ]
    commands: set[str] = set()
    for action in subparsers:
        choices = action.choices
        if isinstance(choices, dict):
            commands.update(choices)
    # `demo` is a bounded synthetic lane, not a semantic verb over real documents:
    # `demo validate` compiles the checked-in synthetic scenario and executes nothing,
    # and `demo run` is closed. The forbidden general-purpose verbs stay forbidden.
    assert commands >= {"validate-schema", "verify-bootstrap", "verify-manifest", "doctor", "demo"}
    assert commands <= {
        "validate-schema",
        "verify-bootstrap",
        "verify-manifest",
        "doctor",
        "demo",
        "validate",
        "run",
    }
    forbidden = {"compile", "admit", "extract", "ingest", "generate-rego", "evaluate", "envelope"}
    assert forbidden.isdisjoint(commands)


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------


def test_demo_validate_compiles_and_executes_nothing(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    code, out, _ = run(
        capsys, "--repo-root", str(repo_root), "--format", "json", "demo", "validate"
    )
    assert code == ExitCode.PASS
    report = json.loads(out)
    assert report["execution_performed"] is False
    assert report["result_bearing_execution"] is False
    assert report["claim_ceiling"] == "SYNTHETIC_END_TO_END_PIPELINE_IMPLEMENTED_AND_TESTED"
    assert set(report["versions"]) == {"v1", "v2"}


def test_demo_validate_is_deterministic(
    capsys: pytest.CaptureFixture[str], repo_root: Path
) -> None:
    args = ("--repo-root", str(repo_root), "--format", "json", "demo", "validate")
    first_code, first_out, _ = run(capsys, *args)
    second_code, second_out, _ = run(capsys, *args)
    assert (first_code, first_out) == (second_code, second_out)


def test_demo_run_refuses_without_an_owner_authorization(
    capsys: pytest.CaptureFixture[str], repo_root: Path, tmp_path: Path
) -> None:
    """The claim-bearing path is closed, and says exactly why."""
    code, out, _ = run(
        capsys,
        "--repo-root",
        str(repo_root),
        "demo",
        "run",
        "--scenario",
        "synthetic-grant-authority",
        "--out",
        str(tmp_path / "evidence"),
    )
    assert code == ExitCode.FAIL
    assert "RESULT_BEARING_EXECUTION_NOT_AUTHORIZED" in out
    assert not (tmp_path / "evidence").exists()


def test_demo_run_refuses_an_authorization_that_does_not_authorize(
    capsys: pytest.CaptureFixture[str], repo_root: Path, tmp_path: Path
) -> None:
    path = tmp_path / "authorization.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "OIC-DEMO-EXECUTION-AUTHORIZATION-v0.1",
                "scenario_id": "synthetic-grant-authority",
                "result_bearing_execution_authorized": False,
            }
        ),
        encoding="utf-8",
    )
    code, out, _ = run(
        capsys, "--repo-root", str(repo_root), "demo", "run", "--authorization", str(path)
    )
    assert code == ExitCode.FAIL
    assert "RESULT_BEARING_EXECUTION_NOT_AUTHORIZED" in out
