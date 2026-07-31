"""Render Morocco preflight canonical JSON files to deterministic Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "benchmarks/corpus/morocco/preflight-v0.1"
STEMS = (
    "OFFICIAL-SOURCE-REGISTER-v0.1",
    "NORMATIVE-SOURCE-MAP-v0.1",
    "PMP-MISSION-CANDIDATES-v0.1",
    "MISSION-SELECTION-SCORECARD-v0.1",
    "ACQUISITION-CONSTRAINTS-v0.1",
    "PREFLIGHT-DECISION-v0.1",
)


def _load(stem: str) -> dict[str, Any]:
    return json.loads((PREFLIGHT / f"{stem}.json").read_text(encoding="utf-8"))


def _cell(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value) or "—"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)
    return lines


def render_source_register(data: dict[str, Any]) -> str:
    sources = data["sources"]
    lines = [
        "# Morocco Official Source Register v0.1",
        "",
        f"Status: **{data['status']}**",
        "",
        "Engineering acquisition classifications only; they are not legal opinions.",
        "",
        "## Sources",
        "",
    ]
    lines += _table(
        ["ID", "Title", "Authority", "Lang", "Canonical", "Download", "Translation", "Disposition"],
        [
            [
                source["source_id"],
                source["complete_title"],
                source["issuing_authority"],
                source["language"],
                source["canonical_url"],
                source["download_url"],
                source["translation_status"],
                source["engineering_disposition"],
            ]
            for source in sources
        ],
    )
    lines += ["", "## Acquisition observations", ""]
    lines += _table(
        ["ID", "Public", "Login", "Robots", "Direct GET", "Human", "Crawl", "Risks", "Unresolved"],
        [
            [
                source["source_id"],
                source["public_accessibility"],
                source["login_requirement"],
                source["robots_observation"],
                source["one_direct_get_technically_possible"],
                source["human_browser_download_available"],
                source["automated_crawling_required"],
                source["acquisition_risks"],
                source["unresolved_issues"],
            ]
            for source in sources
        ],
    )
    return "\n".join(lines) + "\n"


def render_normative_map(data: dict[str, Any]) -> str:
    lines = [
        "# Morocco Normative Source Map v0.1",
        "",
        f"Status: **{data['status']}**",
        "",
        "No legal meaning or applicability conclusion is expressed.",
        "",
        "## Map",
        "",
    ]
    lines += _table(
        ["ID", "Role", "Authoritative", "Relationship"],
        [
            [
                entry["source_id"],
                entry["role"],
                entry["authoritative_for_semantics"],
                entry["relationship"],
            ]
            for entry in data["entries"]
        ],
    )
    lines += ["", "## Unresolved", ""] + [f"- {item}" for item in data["unresolved"]]
    return "\n".join(lines) + "\n"


def render_candidates(data: dict[str, Any]) -> str:
    lines = [
        "# PMP Mission Candidates v0.1",
        "",
        f"Status: **{data['status']}**",
        "",
        "No procurement is classified as compliant or non-compliant.",
        "",
        "## Candidates",
        "",
    ]
    lines += _table(
        [
            "ID",
            "Reference",
            "Buyer",
            "Procedure",
            "Deadline",
            "State",
            "Portal",
            "Objects",
            "Disposition",
        ],
        [
            [
                case["candidate_id"],
                case["reference"],
                case["public_buyer"],
                case["procedure_type"],
                case["submission_deadline"],
                case["state"],
                case["official_portal_url"],
                case["associated_public_objects"],
                case["engineering_disposition"],
            ]
            for case in data["candidates"]
        ],
    )
    lines += ["", "## Missing objects", ""]
    for case in data["candidates"]:
        lines += (
            [f"### {case['candidate_id']} — {case['reference']}", ""]
            + [f"- {item}" for item in case["missing_objects"]]
            + [""]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_scorecard(data: dict[str, Any]) -> str:
    dimensions = data["dimensions"]
    lines = [
        "# Morocco Mission Selection Scorecard v0.1",
        "",
        "Scores: 0 absent; 1 partial/uncertain; 2 present and official.",
        "",
        f"Rule: {data['selection_rule']}",
        "",
        "## Complete scorecard",
        "",
    ]
    lines += _table(
        ["Candidate", *dimensions, "Total", "Mandatory", "Nomination"],
        [
            [
                score["candidate_id"],
                *score["values"],
                score["total"],
                score["mandatory_minimum"],
                score["nomination"],
            ]
            for score in data["scores"]
        ],
    )
    lines += [
        "",
        f"Preferred: **{data['preferred']['mission_id']} → {data['preferred']['candidate_id']}**",
        "",
        f"Fallback: **{data['fallback']['candidate_id']}**",
        "",
    ]
    return "\n".join(lines)


def render_constraints(data: dict[str, Any]) -> str:
    lines = [
        "# Morocco Acquisition Constraints v0.1",
        "",
        f"Status: **{data['status']}**",
        "",
        f"No source bytes acquired: **{_cell(data['no_source_bytes_acquired'])}**",
        "",
        "## Constraints",
        "",
    ]
    lines += _table(
        [
            "Scope",
            "Disposition",
            "Robots",
            "Authentication",
            "Visible",
            "Direct GET",
            "Human",
            "Crawl",
            "Stability",
            "Blockers",
        ],
        [
            [
                item["scope"],
                item["disposition"],
                item["robots_observation"],
                item["authentication"],
                item["visible_download"],
                item["direct_get"],
                item["human_download"],
                item["crawl_required"],
                item["stability"],
                item["blockers"],
            ]
            for item in data["constraints"]
        ],
    )
    lines += ["", "## Prohibited", ""] + [f"- {item}" for item in data["prohibited"]]
    return "\n".join(lines) + "\n"


def render_decision(data: dict[str, Any]) -> str:
    preferred = data["preferred_mission"]
    return "\n".join(
        [
            "# Morocco Preflight Decision v0.1",
            "",
            f"Status: **{data['status']}**",
            "",
            f"Exact base: `{data['exact_base']}`",
            "",
            f"PMP candidates: **{data['pmp_candidate_count']}**",
            "",
            f"Preferred: **{preferred['mission_id']} — {preferred['reference']}**",
            "",
            f"Fallback: **{data['fallback_mission']['reference']}**",
            "",
            data["decision_basis"],
            "",
            f"No source bytes acquired: **{_cell(data['no_source_bytes_acquired'])}**",
            "",
            f"No semantic processing: **{_cell(data['no_semantic_processing'])}**",
            "",
            f"Semantic implementation gate: **{data['semantic_implementation_gate']}**",
            "",
            "## Owner decisions still required",
            "",
            *[f"- {item}" for item in data["next_owner_decisions"]],
            "",
        ]
    )


RENDERERS = {
    STEMS[0]: render_source_register,
    STEMS[1]: render_normative_map,
    STEMS[2]: render_candidates,
    STEMS[3]: render_scorecard,
    STEMS[4]: render_constraints,
    STEMS[5]: render_decision,
}


def render_all(*, check: bool) -> bool:
    clean = True
    for stem in STEMS:
        rendered = RENDERERS[stem](_load(stem))
        path = PREFLIGHT / f"{stem}.md"
        if check:
            clean = clean and path.exists() and path.read_text(encoding="utf-8") == rendered
        else:
            path.write_text(rendered, encoding="utf-8")
    return clean


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not render_all(check=args.check):
        print("Morocco preflight Markdown is stale")
        return 1
    print("Morocco preflight Markdown is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
