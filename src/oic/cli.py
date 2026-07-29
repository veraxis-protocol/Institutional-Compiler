"""The ``oic`` command-line shell.

Subcommands
-----------
``oic validate-schema``   validate JSON Schema documents, offline
``oic verify-manifest``   verify integrity manifests, read-only
``oic doctor``            report environment and gate state

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
from oic.doctor import DoctorReport, run_doctor
from oic.errors import ErrorCategory, OICError
from oic.manifests import (
    KNOWN_MANIFESTS,
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

    if args.all:
        reports = verify_all(root)
    elif args.manifest is not None:
        kind = ManifestKind(args.kind) if args.kind else None
        reports = (verify_manifest(args.manifest.resolve(), root, kind),)
    else:
        default_relpath, default_kind = KNOWN_MANIFESTS[0]
        reports = (verify_manifest(root / default_relpath, root, default_kind),)

    overall = worst_status(reports)

    if args.format == "json":
        _dump_json(
            {
                "manifests": [report.to_json() for report in reports],
                "status": overall.value,
            },
            stream,
        )
    else:
        stream.write("Manifest verification\n")
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    schema = subparsers.add_parser(
        "validate-schema",
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

    manifest = subparsers.add_parser(
        "verify-manifest",
        help="verify repository integrity manifests (read-only)",
        description=(
            "Verify recorded digests against the files on disk. Reports PASS, FAIL, and "
            "INCOMPLETE distinctly. Never writes to a manifest and never fetches a URL."
        ),
    )
    manifest.add_argument(
        "--manifest",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"local manifest to verify (default: {KNOWN_MANIFESTS[0][0]})",
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
        help="report environment, infrastructure profiles, and gate state",
        description=(
            "Report the local environment and the current governance gates. Reads only: "
            "starts no container, opens no connection, and never reports the system as "
            "production-ready."
        ),
    )
    doctor.set_defaults(handler=_command_doctor)

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
