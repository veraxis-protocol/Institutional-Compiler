#!/usr/bin/env python3
"""Render the Canada rights-resolution dossier Markdown from its canonical JSON.

The JSON documents are authoritative. The English and French permission letters
are rendered from one shared record so their permission scope cannot drift.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RELDIR = Path("benchmarks/corpus/canada/rights-resolution-v0.1")
RECAPTURE = "TBS-TERMS-RECAPTURE-PROTOCOL-v0.1"
REVIEW = "TBS-RIGHTS-EVIDENCE-REVIEW-v0.1"
PERMISSION = "CANADABUYS-PERMISSION-REQUEST-v0.1"
COUNSEL = "CANADA-COUNSEL-REVIEW-DOSSIER-v0.1"
LEDGER = "CANADA-RIGHTS-RESOLUTION-LEDGER-v0.1"
REGISTER = "EXTERNAL-ACTION-REGISTER-v0.1"


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_recapture(doc: dict[str, Any]) -> str:
    """Render the recapture protocol."""
    request = doc["request"]
    prior = doc["prior_failure_reference"]
    lines = [
        "# TBS Terms Recapture Protocol v0.1",
        "",
        f"Status: **{doc['status']}**  ·  Execution state: **{doc['execution_state']}**",
        "",
        doc["purpose"],
        "",
        f"Applies to: {', '.join(doc['applies_to_source_ids'])}.",
        "",
        "## Prior failure",
        "",
        f"- Evidence record: `{prior['evidence_id']}`",
        f"- Requested URL: `{prior['requested_url']}`",
        f"- Captured: {prior['captured']}  ·  HTTP status: {prior['http_status']}"
        f"  ·  SHA-256: {prior['sha256']}",
        "",
        doc["prior_failure_note"],
        "",
        "## Request specification",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Requested URL | `{request['requested_url']}` |",
        f"| Method | {request['method']} |",
        f"| Permitted origin domains | {', '.join(request['permitted_origin_domains'])} |",
        f"| Permitted redirect domains | {', '.join(request['permitted_redirect_domains'])} |",
        f"| Maximum redirects | {request['maximum_redirect_count']} |",
        "| Unapproved cross-origin redirect | "
        f"{request['unapproved_cross_origin_redirect_handling']} |",
        f"| Required HTTP status | {request['required_http_status']} |",
        f"| Required media type | {request['required_media_type']} |",
        f"| Accept-Encoding | {request['accept_encoding']} |",
        f"| Timeout | {request['timeout_seconds']}s |",
        f"| Maximum response bytes | {request['maximum_response_bytes']} |",
        "",
        f"**Content signature.** {request['required_content_signature']}",
        "",
        "Rejection markers, any of which invalidates a 200 response: "
        + ", ".join(f"`{marker}`" for marker in request["rejection_markers"])
        + ".",
        "",
        f"**Accept-Encoding rationale.** {request['accept_encoding_rationale']}",
        "",
        "## Required record fields",
        "",
        *_bullets([f"`{field}`" for field in doc["record_fields_required"]]),
        "",
        f"**Byte preservation.** {doc['byte_preservation_rule']}",
        "",
        f"**Absent headers.** {doc['header_absence_rule']}",
        "",
        f"**Failure record.** {doc['failure_record_rule']}",
        "",
        "## Prohibited substitutions",
        "",
        *_bullets(doc["prohibited_substitutions"]),
        "",
        doc["prohibited_substitution_rule"],
        "",
        "## Storage and authorization",
        "",
        f"- Evidence bytes: {doc['storage_location']}",
        f"- Committed output: {doc['committed_output']}",
        f"- {doc['execution_authorization']}",
        f"- {doc['post_execution_gate']}",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_review(doc: dict[str, Any]) -> str:
    """Render the evidence-review worksheet."""
    lines = [
        "# TBS Rights Evidence Review v0.1",
        "",
        f"Status: **{doc['status']}**",
        "",
        f"Applies to: {', '.join(doc['applies_to_source_ids'])}. Depends on `{doc['depends_on']}`.",
        "",
        f"**Precondition.** {doc['precondition']}",
        "",
        f"**Fail-closed rule.** {doc['fail_closed_rule']}",
        "",
        "Allowed findings: " + ", ".join(f"`{value}`" for value in doc["allowed_findings"]) + ".",
        "",
        "Every completed cell must carry: "
        + ", ".join(f"`{field}`" for field in doc["required_cell_fields"])
        + ".",
        "",
        "## Worksheet",
        "",
        "| Dimension | Question | Evidence to examine | Finding |",
        "|---|---|---|---|",
    ]
    for row in doc["dimensions"]:
        lines.append(
            f"| `{row['dimension']}` | {row['question']} | {row['evidence_to_examine']} "
            f"| **{row['finding']}** |"
        )
    lines += [
        "",
        f"Every finding is `UNRESOLVED` because: {doc['dimensions'][0]['finding_reason']}",
        "",
        f"**Disposition gate.** {doc['disposition_gate']}",
        "",
        f"Current disposition of all three sources: "
        f"**{doc['current_disposition_of_all_three_sources']}**.",
        "",
        doc["not_a_legal_conclusion"],
        "",
    ]
    return "\n".join(lines) + "\n"


def render_permission(doc: dict[str, Any], language: str) -> str:
    """Render one language rendering of the permission request."""
    english = language == "en"
    tool = doc["acquisition_tool"]
    heading = (
        "# CanadaBuys Permission Request v0.1 (English)"
        if english
        else "# Demande d'autorisation CanadaBuys v0.1 (français)"
    )
    labels = {
        "status": "Status" if english else "État",
        "to": "To" if english else "Destinataire",
        "from": "From" if english else "Expéditeur",
        "why": "Why we are writing" if english else "Objet de la présente",
        "sources": "Source pages" if english else "Pages sources",
        "cats": "Permission requested" if english else "Autorisations demandées",
        "commit": "Our commitments" if english else "Nos engagements",
        "tool": "Acquisition tool" if english else "Outil d'acquisition",
        "resp": "Requested response" if english else "Réponse demandée",
        "sid": "Source",
        "title": "Title" if english else "Titre",
        "url": "URL",
    }
    lines = [
        heading,
        "",
        f"{labels['status']}: **{doc['status']}** — "
        + (
            "this letter has not been sent."
            if english
            else "la présente lettre n'a pas été envoyée."
        ),
        "",
        f"{labels['to']}: {doc['publisher']}",
        f"{labels['from']}: {doc['requesting_organization']}",
        "",
        f"## {labels['why']}",
        "",
        doc["reason_for_request"][language],
        "",
        f"## {labels['sources']}",
        "",
        f"| {labels['sid']} | {labels['title']} | {labels['url']} |",
        "|---|---|---|",
    ]
    for source in doc["requested_sources"]:
        lines.append(f"| {source['source_id']} | {source['title']} | `{source['url']}` |")
    lines += ["", f"## {labels['cats']}", ""]
    for number, category in enumerate(doc["permission_categories"], start=1):
        side = category[language]
        lines += [f"{number}. **{side['title']}** — {side['text']}", ""]
    lines += [f"## {labels['commit']}", ""]
    for statement in doc["statements"]:
        lines.append(f"- {statement[language]}")
    lines += [
        "",
        f"## {labels['tool']}",
        "",
        f"- `{tool['name']}` version {tool['version']}",
        f"- User-Agent: `{tool['user_agent']}`",
        f"- {tool['behaviour']}",
        "",
        f"## {labels['resp']}",
        "",
        doc["requested_response"][language],
        "",
    ]
    return "\n".join(lines) + "\n"


def render_counsel(doc: dict[str, Any]) -> str:
    """Render the counsel-review dossier."""
    lines = [
        "# Canada Counsel Review Dossier v0.1",
        "",
        f"Status: **{doc['status']}**  ·  Submission state: **{doc['submission_state']}**",
        "",
        f"Questions: **{doc['question_count']}**.",
        "",
        doc["engineering_not_legal_note"],
        "",
        "## Sections",
        "",
        "| Section | Title | Sources | Questions |",
        "|---|---|---|---:|",
    ]
    for section in doc["sections"]:
        lines.append(
            f"| {section['section']} | {section['title']} | "
            f"{', '.join(section['source_ids'])} | {section['question_count']} |"
        )
    lines.append("")
    for section in doc["sections"]:
        lines += [f"## Section {section['section']} — {section['title']}", ""]
        for item in doc["questions"]:
            if item["section"] != section["section"]:
                continue
            evidence = ", ".join(
                f"`{ref['evidence_id']}`"
                + (f" (`{ref['sha256'][:16]}…`)" if ref["sha256"] else " (not captured)")
                for ref in item["evidence_references"]
            )
            lines += [
                f"### {item['question_id']}",
                "",
                f"- Sources: {', '.join(item['source_ids'])}",
                *[f"- URL: `{url}`" for url in item["official_urls"]],
                f"- Evidence: {evidence}",
                f"- Current technical disposition: {item['current_technical_disposition']}",
                f"- Proposed operational use: {item['proposed_operational_use']}",
                f"- **Question: {item['unresolved_legal_question']}**",
                f"- If approved: {item['consequence_of_approval']}",
                f"- If denied: {item['consequence_of_denial']}",
                f"- Required disposition form: {item['required_counsel_disposition_form']}",
                "",
            ]
    return "\n".join(lines) + "\n"


def render_ledger(doc: dict[str, Any]) -> str:
    """Render the ten-source decision ledger."""
    rule = doc["transition_rule"]
    lines = [
        "# Canada Rights Resolution Ledger v0.1",
        "",
        f"Status: **{doc['status']}**",
        "",
        f"Unresolved source units: **{doc['unresolved_source_count']}**. "
        f"Excluded: {', '.join(doc['excluded_source_ids'])}.",
        "",
        doc["exclusion_note"],
        "",
        "## Ledger",
        "",
        "| Source | Publisher | Current state | Rights disposition | Blocking reason |"
        " Unlocking artifact |",
        "|---|---|---|---|---|---|",
    ]
    for row in doc["rows"]:
        lines.append(
            f"| {row['source_id']} | {row['publisher_group']} | **{row['current_state']}** |"
            f" {row['current_rights_disposition']} | {row['blocking_reason']} |"
            f" `{row['unlocking_artifact']}` |"
        )
    lines += [
        "",
        "## Allowed states",
        "",
        *_bullets([f"`{state}`" for state in doc["allowed_states"]]),
        "",
        "## Transition rule",
        "",
        "Every transition must record:",
        "",
        *_bullets([f"`{field}`" for field in rule["required_fields"]]),
        "",
        "Conditionally required:",
        "",
        *_bullets(
            [f"`{field}` — {why}" for field, why in rule["conditionally_required_fields"].items()]
        ),
        "",
        "**Owner assertion alone is insufficient: "
        f"{rule['owner_assertion_alone_is_insufficient']}.** {rule['owner_assertion_rule']}",
        "",
        f"**Dispositions do not move here.** {rule['disposition_change_rule']}",
        "",
        "## State gates",
        "",
        "| State | Gate |",
        "|---|---|",
    ]
    for state, gate in doc["state_gates"].items():
        lines.append(f"| `{state}` | {gate} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_register(doc: dict[str, Any]) -> str:
    """Render the external-action register."""
    lines = [
        "# External Action Register v0.1",
        "",
        f"Status: **{doc['status']}**  ·  Actions: **{doc['action_count']}**",
        "",
        doc["no_action_performed_note"],
        "",
        "| ID | Actor | Action | Blocks | Artifact | Authorized here | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for action in doc["actions"]:
        lines.append(
            f"| {action['action_id']} | {action['actor']} ({action['actor_detail']}) |"
            f" {action['action']} | {', '.join(action['blocks_source_ids'])} |"
            f" `{action['artifact']}` | {action['authorized_by_this_work_order']} |"
            f" {action['status']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def rendered(root: Path) -> dict[Path, str]:
    """Return the expected Markdown for every generated dossier document."""

    def load(name: str) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(
            (root / RELDIR / f"{name}.json").read_text(encoding="utf-8")
        )
        return data

    permission = load(PERMISSION)
    return {
        root / RELDIR / f"{RECAPTURE}.md": render_recapture(load(RECAPTURE)),
        root / RELDIR / f"{REVIEW}.md": render_review(load(REVIEW)),
        root / RELDIR / "CANADABUYS-PERMISSION-REQUEST-EN-v0.1.md": render_permission(
            permission, "en"
        ),
        root / RELDIR / "CANADABUYS-PERMISSION-REQUEST-FR-v0.1.md": render_permission(
            permission, "fr"
        ),
        root / RELDIR / f"{COUNSEL}.md": render_counsel(load(COUNSEL)),
        root / RELDIR / f"{LEDGER}.md": render_ledger(load(LEDGER)),
        root / RELDIR / f"{REGISTER}.md": render_register(load(REGISTER)),
    }


def main(argv: list[str] | None = None) -> int:
    """Render or verify the generated dossier Markdown."""
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
            print(f"out of date: {', '.join(stale)}; run tools/render_canada_dossier.py")
            return 1
        print("Canada dossier Markdown matches the canonical JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
