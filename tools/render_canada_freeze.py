#!/usr/bin/env python3
"""Render the Canada rights-clearance and acquisition-freeze Markdown from canonical JSON.

The JSON documents are authoritative. The Markdown is generated so a reader can
never be shown a disposition that the machine-readable record does not carry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FREEZE_RELDIR = Path("benchmarks/corpus/canada/freeze-v0.1")
RIGHTS_JSON = FREEZE_RELDIR / "RIGHTS-CLEARANCE-v0.1.json"
RIGHTS_MD = FREEZE_RELDIR / "RIGHTS-CLEARANCE-v0.1.md"
FREEZE_JSON = FREEZE_RELDIR / "ACQUISITION-FREEZE-v0.1.json"
FREEZE_MD = FREEZE_RELDIR / "ACQUISITION-FREEZE-v0.1.md"
INDEX_JSON = FREEZE_RELDIR / "INDEX.json"


def _cell(value: object) -> str:
    if isinstance(value, list):
        return "<br>".join(str(item).replace("|", "\\|") for item in value) or "—"
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_rights(document: dict[str, Any]) -> str:
    """Render the rights matrix, one row per source unit plus per-source detail."""
    lines = [
        "# Canada Corpus Rights Clearance v0.1",
        "",
        f"Status: **{document['status']}**",
        "",
        document["vocabulary_note"],
        "",
        document["counsel_review_note"],
        "",
        "## Disposition summary",
        "",
        "| Disposition | Count |",
        "|---|---:|",
    ]
    for disposition, count in document["disposition_counts"].items():
        lines.append(f"| {disposition} | {count} |")
    lines += [
        f"| **Total** | **{document['source_unit_count']}** |",
        "",
        "## Rights matrix",
        "",
        "| Source | Publisher | Automated retrieval | Internal research use |"
        " Public-repository redistribution | Disposition | Storage |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in document["records"]:
        lines.append(
            "| {source_id} | {publisher} | {automated_retrieval_permission} |"
            " {internal_research_use} | {public_repository_redistribution_permission} |"
            " **{reviewer_disposition}** | {storage_classification} |".format(
                **{key: _cell(value) for key, value in record.items()}
            )
        )
    lines += ["", "## Per-source evidence", ""]
    for record in document["records"]:
        lines += [
            f"### {record['source_id']} — {record['title']}",
            "",
            f"- Publisher: {_cell(record['publisher'])}",
            f"- Jurisdiction: {_cell(record['jurisdiction'])}",
            f"- Copyright owner: {_cell(record['copyright_owner'])}",
            f"- Authoritative-source status: {_cell(record['authoritative_source_status'])}",
            f"- Acquisition target: `{record['acquisition_target_url']}`"
            f" ({_cell(record['acquisition_target_role'])},"
            f" {_cell(record['acquisition_target_expected_content_type'])})",
            f"- Provenance URL (never an acquisition fallback): `{record['provenance_url']}`",
            f"- Rights-notice URL: `{record['rights_notice_url']}`",
            f"- Terms-of-use URL: `{record['terms_of_use_url']}`",
            f"- Evidence captured at: {_cell(record['evidence_capture_utc'])}",
            f"- Automated retrieval: **{_cell(record['automated_retrieval_permission'])}**"
            f" — {_cell(record['automated_retrieval_basis'])}",
            f"- Internal research use: **{_cell(record['internal_research_use'])}**"
            f" — {_cell(record['internal_research_use_basis'])}",
            f"- Machine processing: {_cell(record['machine_processing_permission'])}",
            "- Public-repository redistribution:"
            f" {_cell(record['public_repository_redistribution_permission'])}",
            f"- Attribution requirements: {_cell(record['attribution_requirements'])}",
            f"- Modification restrictions: {_cell(record['modification_restrictions'])}",
            f"- Third-party material: {_cell(record['third_party_material_flag'])}",
            f"- Personal information: {_cell(record['personal_information_flag'])}",
            f"- Logo, insignia, trademark: {_cell(record['logo_insignia_trademark_flag'])}",
            f"- Source-specific limitations: {_cell(record['source_specific_limitations'])}",
            f"- **Reviewer disposition: {record['reviewer_disposition']}**"
            f" — {_cell(record['disposition_basis'])}",
            f"- Storage classification: {_cell(record['storage_classification'])}",
            "",
            "Evidence hashes:",
            "",
            "| Evidence | Requested URL | HTTP | Captured | SHA-256 | Bytes |",
            "|---|---|---:|---|---|---:|",
        ]
        for evidence in record["evidence_hashes"]:
            lines.append(
                f"| {evidence['evidence_id']} | `{evidence['requested_url']}` |"
                f" {_cell(evidence['http_status'])} | {_cell(evidence['captured'])} |"
                f" `{_cell(evidence['sha256'])}` | {_cell(evidence['byte_length'])} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_freeze(record: dict[str, Any], index: dict[str, Any]) -> str:
    """Render the freeze record and the binding index of frozen artifacts."""
    lines = [
        "# Canada Acquisition Freeze v0.1",
        "",
        f"Freeze disposition: **{record['freeze_disposition']}**",
        "",
        f"Acquisition tool: `{record['acquisition_tool']}` "
        f"version {record['acquisition_tool_version']}.",
        "",
        record["no_fallback_note"],
        "",
        record["completion_note"],
        "",
        f"Semantic implementation gate: **{record['semantic_implementation_gate']}**.",
        "",
        "## Source manifest limitation",
        "",
        record["source_manifest_note"],
        "",
        "## Counts",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Source units | {record['source_unit_count']} |",
        f"| Acquired | {record['acquired_source_count']} |",
        f"| Blocked, never requested | {record['blocked_source_count']} |",
        f"| Committed to the repository | {len(record['committed_to_repository_source_ids'])} |",
        f"| Stored internal-only | {len(record['internal_only_source_ids'])} |",
        "",
        "## Frozen artifacts",
        "",
        "| Source | Acquisition target | Final URL | Retrieved (UTC) | Content type |"
        " Bytes | SHA-256 | Disposition | Storage | Receipt |",
        "|---|---|---|---|---|---:|---|---|---|---|",
    ]
    for entry in index["entries"]:
        lines.append(
            f"| {entry['source_id']} | `{entry['acquisition_target_url']}` |"
            f" `{entry['final_url']}` | {entry['retrieval_utc']} | {entry['content_type']} |"
            f" {entry['byte_length']} | `{entry['sha256']}` | {entry['rights_disposition']} |"
            f" {entry['storage_classification']} | `{entry['receipt_id']}` |"
        )
    lines += [
        "",
        "## Blocked source units",
        "",
        "These were never requested. Their bytes do not exist anywhere in this repository or in"
        " any local evidence area.",
        "",
    ]
    lines += [f"- {source_id}" for source_id in record["blocked_source_ids"]]
    lines += [
        "",
        "## Offline verification",
        "",
        "```bash",
        "python scripts/verify_canada_freeze.py",
        "```",
        "",
        "The verifier performs no network I/O. It recomputes SHA-256 and SHA-512 over every"
        " committed artifact and requires agreement with the receipt, `INDEX.json`, `SHA256SUMS`,"
        " and `SHA512SUMS`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def rendered(root: Path) -> dict[Path, str]:
    """Return the expected Markdown for every generated freeze document."""
    rights = json.loads((root / RIGHTS_JSON).read_text(encoding="utf-8"))
    freeze = json.loads((root / FREEZE_JSON).read_text(encoding="utf-8"))
    index = json.loads((root / INDEX_JSON).read_text(encoding="utf-8"))
    return {
        root / RIGHTS_MD: render_rights(rights),
        root / FREEZE_MD: render_freeze(freeze, index),
    }


def main(argv: list[str] | None = None) -> int:
    """Render or verify the generated Markdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    stale = []
    for path, expected in rendered(args.root).items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(path.name)
            continue
        path.write_text(expected, encoding="utf-8")
        print(f"rendered {path.name}")
    if args.check:
        if stale:
            print(f"out of date: {', '.join(stale)}; run tools/render_canada_freeze.py")
            return 1
        print("Canada freeze Markdown matches the canonical JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
