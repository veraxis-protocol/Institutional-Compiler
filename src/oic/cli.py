"""The ``oic`` command-line shell.

Subcommands
-----------
``oic validate-schema``   validate JSON Schema documents, offline
``oic verify-bootstrap``  verify the historical bootstrap baseline from Git objects
``oic verify-manifest``   verify current-tree integrity manifests, read-only
``oic doctor``            report environment and gate state
``oic demo validate``     compile the bounded synthetic demo scenario; no execution
``oic demo run``          refuses unless an owner result-bearing authorization is supplied

The ``demo`` subcommands belong to the bounded OIC-ZTL-OAM demonstration lane. ``demo
validate`` compiles the synthetic scenario and reports what it produced; it evaluates no
logic and executes nothing. ``demo run`` is the claim-bearing path and is closed: without
an owner-issued result-bearing execution authorization it exits FAIL with
``RESULT_BEARING_EXECUTION_NOT_AUTHORIZED``. There is no flag that opens it.

Bootstrap verification is separate on purpose. ``BOOTSTRAP_MANIFEST.json`` is immutable
historical evidence about the bootstrap commit, not a policy freezing every path it lists
(ADR-012), so it is verified against the Git object tree at that commit rather than
against the working tree. ``verify-manifest`` handles the manifests that *do* describe the
present tree.

Exit codes
----------
=====  ==========================================================================
``0``  PASS - every selected check succeeded
``1``  FAIL - at least one check failed
``2``  usage or configuration error (bad arguments, missing directory, unreadable
       manifest). Also argparse's own usage exit.
``3``  INCOMPLETE - nothing failed, but the evidence is not complete. Currently
       raised by an integrity manifest with missing digests, and by the preflight
       corpus manifest, which today holds only its header.
=====  ==========================================================================

``3`` is deliberately distinct from both ``0`` and ``1``. A caller that treats "not
failing" as "passing" would report an empty corpus manifest as corpus-ready, which is
exactly the conflation this work order forbids. Scripts that want to allow incomplete
evidence must opt in explicitly (``--allow-incomplete``).

Output discipline
-----------------
``--format json`` emits a deterministic document: keys sorted, lists ordered by path, no
timestamps, no absolute paths, no hostnames. Byte-identical runs on the same tree produce
byte-identical output, which is what makes the CI diff meaningful.

No subcommand contacts the network, mutates a file, or makes any claim about quality,
compliance, or production readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from enum import IntEnum
from pathlib import Path
from typing import Any, Final, TextIO

from oic import __version__
from oic.baseline import (
    BOOTSTRAP_COMMIT,
    BaselineReport,
    BaselineStatus,
    BlobStatus,
    verify_bootstrap_baseline,
)
from oic.demo_runtime import (
    RESULT_BEARING_EXECUTION_NOT_AUTHORIZED,
    SCENARIO_ID,
    DemoRuntimeError,
    execute_result_bearing_run,
    validate_scenario,
)
from oic.doctor import DoctorReport, run_doctor
from oic.errors import ErrorCategory, OICError
from oic.manifests import (
    EntryStatus,
    ManifestKind,
    ManifestReport,
    VerificationStatus,
    verify_all,
    verify_manifest,
    worst_status,
)
from oic.paths import find_repo_root
from oic.schemas import (
    DEFAULT_SCHEMA_DIRECTORY,
    SchemaReport,
    SchemaStatus,
    validate_schema_directory,
)

__all__ = ["ExitCode", "build_parser", "main"]

PROGRAM: Final[str] = "oic"


class ExitCode(IntEnum):
    """Process exit codes. See the module docstring for the contract."""

    PASS = 0
    FAIL = 1
    USAGE = 2
    INCOMPLETE = 3


def _dump_json(payload: dict[str, Any], stream: TextIO) -> None:
    """Write a deterministic JSON document."""
    json.dump(payload, stream, indent=2, sort_keys=True, ensure_ascii=False)
    stream.write("\n")


def _resolve_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return find_repo_root()


# ---------------------------------------------------------------------------
# validate-schema
# ---------------------------------------------------------------------------


def _render_schema_report(report: SchemaReport, stream: TextIO) -> None:
    stream.write(f"Schema validation: {report.directory}\n")
    for result in report.results:
        stream.write(f"  {result.status.value:<5} {result.schema_path}\n")
        for issue in result.issues:
            stream.write(f"        {issue.json_pointer or '#'}  [{issue.code.value}] ")
            stream.write(f"{issue.message}\n")
    passed = sum(1 for result in report.results if result.status is SchemaStatus.PASS)
    stream.write(f"\n{passed}/{len(report.results)} schemas valid  ->  {report.status.value}\n")
    if report.external_refs_allowed:
        stream.write("NOTE: external references were permitted; no network access was performed.\n")


def _command_validate_schema(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    root = _resolve_root(args.repo_root)
    directory = args.schema_dir.resolve() if args.schema_dir else root / DEFAULT_SCHEMA_DIRECTORY
    report = validate_schema_directory(
        directory,
        root=root,
        allow_external_refs=args.allow_external_refs,
    )
    if args.format == "json":
        _dump_json(report.to_json(), stream)
    else:
        _render_schema_report(report, stream)
    return ExitCode.PASS if report.status is SchemaStatus.PASS else ExitCode.FAIL


# ---------------------------------------------------------------------------
# verify-bootstrap
# ---------------------------------------------------------------------------


def _render_baseline_report(report: BaselineReport, stream: TextIO) -> None:
    stream.write(f"Bootstrap baseline: {report.ref}\n")
    stream.write(f"  resolved commit: {report.resolved_commit}\n")
    for entry in report.entries:
        if entry.status is not BlobStatus.PASS:
            stream.write(f"{entry.render()}\n")
    passed = report.count(BlobStatus.PASS)
    stream.write(f"  {passed}/{len(report.entries)} artifacts match the recorded bytes\n")
    for note in report.notes:
        stream.write(f"  note: {note}\n")
    stream.write(f"  RESULT: {report.status.value}\n")


def _command_verify_bootstrap(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    root = _resolve_root(args.repo_root)
    report = verify_bootstrap_baseline(root, args.ref)
    if args.format == "json":
        _dump_json(report.to_json(), stream)
    else:
        _render_baseline_report(report, stream)
    return ExitCode.PASS if report.status is BaselineStatus.PASS else ExitCode.FAIL


# ---------------------------------------------------------------------------
# verify-manifest
# ---------------------------------------------------------------------------


def _render_manifest_report(report: ManifestReport, stream: TextIO) -> None:
    stream.write(f"\n{report.manifest_path}  [{report.kind.value}]\n")
    for entry in report.entries:
        if entry.status is not EntryStatus.PASS:
            stream.write(f"{entry.render()}\n")
    counts = ", ".join(
        f"{status.value}={report.count(status)}"
        for status in EntryStatus
        if report.count(status) > 0
    )
    stream.write(f"  {len(report.entries)} entr{'y' if len(report.entries) == 1 else 'ies'}")
    stream.write(f"  ({counts})\n" if counts else "\n")
    for note in report.notes:
        stream.write(f"  note: {note}\n")
    stream.write(f"  RESULT: {report.status.value}\n")


def _manifest_exit_code(status: VerificationStatus, *, allow_incomplete: bool) -> ExitCode:
    if status is VerificationStatus.FAIL:
        return ExitCode.FAIL
    if status is VerificationStatus.INCOMPLETE:
        return ExitCode.PASS if allow_incomplete else ExitCode.INCOMPLETE
    return ExitCode.PASS


def _command_verify_manifest(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    root = _resolve_root(args.repo_root)

    baseline: BaselineReport | None = None
    if args.all:
        # The bootstrap component of --all is historical baseline verification, read from
        # the Git object tree at the pinned commit (ADR-012). The other two components
        # describe the present tree and keep their current-tree behaviour.
        baseline = verify_bootstrap_baseline(root, args.ref)
        reports = verify_all(root)
    elif args.manifest is not None:
        kind = ManifestKind(args.kind) if args.kind else None
        reports = (verify_manifest(args.manifest.resolve(), root, kind),)
    else:
        baseline = verify_bootstrap_baseline(root, args.ref)
        reports = ()

    overall = worst_status(reports)
    if baseline is not None and baseline.status is BaselineStatus.FAIL:
        overall = VerificationStatus.FAIL

    if args.format == "json":
        payload: dict[str, Any] = {
            "manifests": [report.to_json() for report in reports],
            "status": overall.value,
        }
        if baseline is not None:
            payload["bootstrap_baseline"] = baseline.to_json()
        _dump_json(payload, stream)
    else:
        stream.write("Manifest verification\n")
        if baseline is not None:
            stream.write("\n")
            _render_baseline_report(baseline, stream)
        for report in reports:
            _render_manifest_report(report, stream)
        stream.write(f"\nOVERALL: {overall.value}\n")
        if overall is VerificationStatus.INCOMPLETE:
            stream.write("INCOMPLETE is not a pass. Evidence is missing, not merely unverified.\n")

    return _manifest_exit_code(overall, allow_incomplete=args.allow_incomplete)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def _render_doctor_report(report: DoctorReport, stream: TextIO) -> None:
    stream.write(f"oic doctor  (oic {__version__})\n")

    stream.write("\nEnvironment\n")
    for check in report.environment:
        stream.write(f"{check.render()}\n")

    stream.write("\nLocal tools\n")
    for check in report.tools:
        stream.write(f"{check.render()}\n")

    stream.write("\nInfrastructure profiles\n")
    for check in report.infrastructure:
        stream.write(f"{check.render()}\n")

    stream.write("\nProvisional boundaries\n")
    for boundary in report.boundaries:
        stream.write(f"  {boundary.name:<28} {boundary.status}\n")
        stream.write(f"      gate: {boundary.gate}\n")

    stream.write("\nGates\n")
    for check in report.gates:
        stream.write(f"{check.render()}\n")

    stream.write("\nNotices\n")
    for notice in report.notices:
        stream.write(f"  - {notice}\n")


def _command_doctor(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    # Pass the flag through unchanged so `doctor` performs (and reports on) its own
    # root detection when the operator did not supply one.
    report = run_doctor(args.repo_root.resolve() if args.repo_root else None)
    if args.format == "json":
        _dump_json(report.to_json(), stream)
    else:
        _render_doctor_report(report, stream)
    # `doctor` describes the environment; it does not adjudicate it. An absent optional
    # tool is information, not a failure, so this exits 0 unless the report itself could
    # not be produced.
    return ExitCode.PASS


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------


def _render_demo_validation(report: dict[str, Any], stream: TextIO) -> None:
    stream.write(f"Demo scenario: {report['scenario_id']}\n")
    stream.write(f"  scope:               {report['scope_ref']}\n")
    stream.write(f"  currentness index:   {report['currentness_index_digest']}\n")
    stream.write(f"  implementation:      {report['implementation_commit']}\n")
    stream.write(f"  scenario bundle:     {report['scenario_bundle_digest']}\n")
    stream.write(f"  expected ZTL commit: {report['expected_ztl_commit']}\n")
    evidence = report["evidence_observation"]
    stream.write(
        f"  evidence:            {evidence['observed_evidence_id']} "
        f"[{evidence['evidence_state']}] satisfaction={evidence['satisfaction']}\n"
    )
    for version, detail in sorted(report["versions"].items()):
        stream.write(f"\n  {version}\n")
        stream.write(f"    source            {detail['source_content_hash']}\n")
        stream.write(f"    candidates        {detail['candidates']}\n")
        stream.write(f"    admitted units    {len(detail['admitted_units'])}\n")
        stream.write(f"    executable        {', '.join(detail['executable_conditions'])}\n")
        stream.write(f"    envelope          {detail['envelope_id']}\n")
        stream.write(f"    envelope digest   {detail['envelope_digest']}\n")
    stream.write(f"\n  claim ceiling: {report['claim_ceiling']}\n")
    stream.write(
        "  Nothing was executed, ZTL was not invoked, and no result-bearing claim is made.\n"
    )


def _command_demo_validate(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    root = _resolve_root(args.repo_root)
    report = validate_scenario(root, args.scenario)
    if args.format == "json":
        _dump_json(report, stream)
    else:
        _render_demo_validation(report, stream)
    return ExitCode.PASS


#: Shell success for a result-bearing run. RESULT-001 completes under its own
#: status; RESULT-002 deliberately completes under a different one, because a
#: PASS-looking status must be unreachable when the frozen semantic comparator
#: says FAIL. Mapping only the first of them to exit 0 would have made a
#: successful RESULT-002 exit 1 — found by inspection of the frozen public path
#: before any authorization was issued, and corrected here without touching the
#: measurement. Every other status, including every RESULT-002 failure, remains
#: nonzero by falling through.
_SUCCESSFUL_RUN_STATUSES: Final = frozenset(
    {
        "RESULT_BEARING_EXECUTION_COMPLETE",
        "RESULT_002_MACHINE_COMPARED_CONFORMANCE_PASS",
    }
)


def _command_demo_run(args: argparse.Namespace, stream: TextIO) -> ExitCode:
    """The claim-bearing path. It opens only for a validated owner authorization.

    The full positive run is implemented in ``oic.demo_runtime`` and is reached
    only after every binding the authorization carries has been checked against
    observed state: the implementation commit, the scenario bundle digest, the
    kernel commit, the output directory, the claim ceiling and a clean worktree.
    Without such an artifact this exits FAIL and writes nothing.
    """
    root = _resolve_root(args.repo_root)
    if args.out is None:
        stream.write(
            f"{RESULT_BEARING_EXECUTION_NOT_AUTHORIZED}: no output directory was supplied\n"
        )
        return ExitCode.FAIL
    try:
        report = execute_result_bearing_run(
            repo_root=root,
            authorization_path=args.authorization,
            output_directory=args.out,
            ztl_path=args.ztl,
            scenario_id=args.scenario,
            claimed_at=args.claimed_at,
        )
    except DemoRuntimeError as error:
        stream.write(f"{error}\n")
        return ExitCode.FAIL
    if args.format == "json":
        _dump_json(report, stream)
    else:
        stream.write(f"{report['status']}\n")
        stream.write(f"  authorization: {report['authorization_id']}\n")
        stream.write(f"  cases:         {', '.join(report['cases'])}\n")
        stream.write(f"  package:       {report['package_verification']}\n")
    return ExitCode.PASS if report["status"] in _SUCCESSFUL_RUN_STATUSES else ExitCode.FAIL


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Open Institutional Compiler infrastructure tools. "
            "Schema validation, manifest verification, and environment diagnostics only: "
            "no document interpretation, admission, control generation, or enforcement."
        ),
        epilog="Exit codes: 0 PASS, 1 FAIL, 2 usage/configuration error, 3 INCOMPLETE.",
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        metavar="DIR",
        help="repository root (default: located by walking up to BOOTSTRAP_MANIFEST.json)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format; 'json' is deterministic and sorted (default: text)",
    )

    # The same global options are accepted after the subcommand as well, so both
    # `oic --format json verify-manifest --all` and `oic verify-manifest --all --format json`
    # work. argparse is strict about ordering by default, and the surprise cost a CI run:
    # the second form exited 2 with "unrecognized arguments" while looking correct.
    # SUPPRESS is essential here - without it, the subparser's own default would overwrite
    # a value the operator supplied before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo-root",
        type=Path,
        default=argparse.SUPPRESS,
        metavar="DIR",
        help=argparse.SUPPRESS,
    )
    common.add_argument(
        "--format",
        choices=("text", "json"),
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    schema = subparsers.add_parser(
        "validate-schema",
        parents=[common],
        help="validate JSON Schema Draft 2020-12 documents offline",
        description=(
            "Validate every *.schema.json under a local directory against the Draft "
            "2020-12 metaschema and resolve all references locally. Never accesses the "
            "network. Exits 0 only when every selected schema passes."
        ),
    )
    schema.add_argument(
        "--schema-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"local schema directory (default: {DEFAULT_SCHEMA_DIRECTORY})",
    )
    schema.add_argument(
        "--allow-external-refs",
        action="store_true",
        help=(
            "do not fail on a $ref written with a remote scheme that no local schema "
            "satisfies. This never enables fetching."
        ),
    )
    schema.set_defaults(handler=_command_validate_schema)

    bootstrap = subparsers.add_parser(
        "verify-bootstrap",
        parents=[common],
        help="verify the historical bootstrap baseline from the Git object database",
        description=(
            "Verify that the bootstrap commit still contains exactly the bytes recorded "
            "in BOOTSTRAP_MANIFEST.json. The manifest and every artifact it lists are "
            "read from the pinned commit through the local Git object database; the "
            "working tree is neither read nor modified, and no network access occurs. "
            "A file changed in a later commit does not affect this result (ADR-012)."
        ),
    )
    bootstrap.add_argument(
        "--ref",
        default=BOOTSTRAP_COMMIT,
        metavar="COMMIT",
        help=f"local commit or tag to verify (default: {BOOTSTRAP_COMMIT})",
    )
    bootstrap.set_defaults(handler=_command_verify_bootstrap)

    manifest = subparsers.add_parser(
        "verify-manifest",
        parents=[common],
        help="verify current-tree integrity manifests (read-only)",
        description=(
            "Verify recorded digests against the files on disk. Reports PASS, FAIL, and "
            "INCOMPLETE distinctly. Never writes to a manifest and never fetches a URL. "
            "With no arguments, and with --all, the bootstrap component is verified as a "
            "historical baseline rather than against the working tree (ADR-012)."
        ),
    )
    manifest.add_argument(
        "--manifest",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "local current-tree manifest to verify. BOOTSTRAP_MANIFEST.json is not "
            "accepted here; use 'oic verify-bootstrap'."
        ),
    )
    manifest.add_argument(
        "--ref",
        default=BOOTSTRAP_COMMIT,
        metavar="COMMIT",
        help=f"baseline commit for the bootstrap component (default: {BOOTSTRAP_COMMIT})",
    )
    manifest.add_argument(
        "--kind",
        choices=tuple(kind.value for kind in ManifestKind),
        default=None,
        help="manifest format (default: inferred from the file name)",
    )
    manifest.add_argument(
        "--all",
        action="store_true",
        help="verify every known manifest; the most severe result determines the exit code",
    )
    manifest.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="exit 0 instead of 3 when the result is INCOMPLETE (opt-in; still reported)",
    )
    manifest.set_defaults(handler=_command_verify_manifest)

    doctor = subparsers.add_parser(
        "doctor",
        parents=[common],
        help="report environment, infrastructure profiles, and gate state",
        description=(
            "Report the local environment and the current governance gates. Reads only: "
            "starts no container, opens no connection, and never reports the system as "
            "production-ready."
        ),
    )
    doctor.set_defaults(handler=_command_doctor)

    demo = subparsers.add_parser(
        "demo",
        parents=[common],
        help="bounded synthetic OIC-ZTL-OAM demonstration lane",
        description=(
            "The bounded synthetic demonstration lane. 'validate' compiles the scenario and "
            "reports what it produced without evaluating any logic or executing anything. "
            "'run' is the claim-bearing path and refuses unless a separate owner-issued "
            "result-bearing execution authorization is supplied. Nothing here performs a "
            "payment, a disbursement, an external transaction, or any legal act."
        ),
    )
    demo_commands = demo.add_subparsers(dest="demo_command", required=True)

    demo_validate = demo_commands.add_parser(
        "validate",
        parents=[common],
        help="compile the synthetic scenario; evaluates no logic and executes nothing",
    )
    demo_validate.add_argument(
        "--scenario",
        default=SCENARIO_ID,
        metavar="ID",
        help=f"scenario identifier (default: {SCENARIO_ID})",
    )
    demo_validate.set_defaults(handler=_command_demo_validate)

    demo_run = demo_commands.add_parser(
        "run",
        parents=[common],
        help="result-bearing execution; refuses without an owner authorization artifact",
        description=(
            "Refuses with RESULT_BEARING_EXECUTION_NOT_AUTHORIZED unless an owner-issued "
            "result-bearing execution authorization artifact is supplied. Development tests "
            "call the internal orchestration directly and never reach this command."
        ),
    )
    demo_run.add_argument(
        "--scenario",
        default=SCENARIO_ID,
        metavar="ID",
        help=f"scenario identifier (default: {SCENARIO_ID})",
    )
    demo_run.add_argument(
        "--out", type=Path, default=None, metavar="PATH", help="evidence output directory"
    )
    demo_run.add_argument(
        "--authorization",
        type=Path,
        default=None,
        metavar="PATH",
        help="owner-issued result-bearing execution authorization artifact",
    )
    demo_run.add_argument(
        "--ztl",
        type=Path,
        default=None,
        metavar="DIR",
        help="local ZTL checkout at the pinned commit (default: $OIC_DEMO_ZTL_PATH)",
    )
    demo_run.add_argument(
        "--claimed-at",
        default="1970-01-01T00:00:00Z",
        metavar="INSTANT",
        help="declared instant recorded on the single-use consumption record",
    )
    demo_run.set_defaults(handler=_command_demo_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code; never raises for expected errors."""
    parser = build_parser()
    args = parser.parse_args(argv)
    stream = sys.stdout
    try:
        result: ExitCode = args.handler(args, stream)
    except OICError as exc:
        print(str(exc), file=sys.stderr)
        # Operator mistakes are usage errors; contract violations are real failures.
        return int(ExitCode.USAGE if exc.category is ErrorCategory.OPERATOR else ExitCode.FAIL)
    return int(result)


if __name__ == "__main__":  # pragma: no cover - exercised via the console script
    raise SystemExit(main())
