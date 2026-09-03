#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]

BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-source-origin-declaration-evidence-reanalysis-001"
)
CONTRACT = BENCH / "REANALYSIS-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"

PRIOR_DIR = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-publisher-canonical-locator-evidence-acquisition-001"
)
PRIOR_RESULT = PRIOR_DIR / "EXECUTION-RESULT-v0.1.json"

PRIOR_LOCAL = ROOT / (
    ".local/canada-publisher-canonical-locator-evidence-acquisition-001"
)
RAW_HEADERS = PRIOR_LOCAL / "raw-evidence/response-00-headers.json"
RAW_BODY = PRIOR_LOCAL / "raw-evidence/response-00-body.bin"
RAW_PRIOR_EVAL = PRIOR_LOCAL / "raw-evidence/parsed-evaluation.json"
PRIOR_RECEIPT = PRIOR_LOCAL / "EXECUTION-RECEIPT-v0.1.json"

CONTRACT_SHA256 = "1b74205729253d135473f3c061dbe26fa0b6bcad807443b4b056ebee2703cd0e"
PREREG_FREEZE_SHA256 = "c645a4754041d2c09ba275d6f7ade23f10914d6bf798196210980375681292da"
PRIOR_RESULT_SHA256 = "f796371b8ec92ad491d0f5bd2b8163e25974fbc1fc80cd117c427407d639a775"
RAW_HEADERS_SHA256 = "75309cc803a70525b3ad3b6a6057a53014025337012b8a39624c4dd8bd5aba80"
RAW_BODY_SHA256 = "6e89ad25847944ca2bd72bcbf02ec3d2942a234d373b6c10db44307e0fbdf2c3"
RAW_PRIOR_EVAL_SHA256 = "6f8d1d35105cffa8610dc69b0abccdf9313852023e46ae4d703d2813cbfa1775"
PRIOR_RECEIPT_SHA256 = "a3d734169f8f69b25ee477da6ce3ed4d6e9c020b026b5bcf816b0762bd696c81"

ALLOWED_VALUES = frozenset({"public", "synthetic"})
XML_EXACT_KEYS = frozenset({"source_kind", "source-kind", "sourceKind"})
HTML_NORMALIZED_KEYS = frozenset({"source_kind", "source-kind", "sourcekind"})
META_EXACT_KEYS = frozenset({"source_kind", "source-kind", "sourceKind"})
HEADER_KEYS = frozenset({"source-kind", "x-source-kind"})

ESTABLISHED = "SOURCE_ORIGIN_DECLARATION_AUTHORITY_EVIDENCE_ESTABLISHED_CA3"
NOT_ESTABLISHED = (
    "SOURCE_ORIGIN_DECLARATION_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3"
)
INCOMPLETE = "SOURCE_ORIGIN_DECLARATION_REANALYSIS_INCOMPLETE_FAIL_CLOSED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bound_input_bytes_only() -> None:
    expected = {
        CONTRACT: CONTRACT_SHA256,
        PREREG_FREEZE: PREREG_FREEZE_SHA256,
        PRIOR_RESULT: PRIOR_RESULT_SHA256,
        RAW_HEADERS: RAW_HEADERS_SHA256,
        RAW_BODY: RAW_BODY_SHA256,
        RAW_PRIOR_EVAL: RAW_PRIOR_EVAL_SHA256,
        PRIOR_RECEIPT: PRIOR_RECEIPT_SHA256,
    }
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise SystemExit(f"FAIL: digest mismatch: {path}")


def normalize_value(value: str) -> str | None:
    candidate = value.strip().casefold()
    return candidate if candidate in ALLOWED_VALUES else None


def local_name(name: str) -> str:
    if name.startswith("{") and "}" in name:
        return name.split("}", 1)[1]
    if ":" in name:
        return name.rsplit(":", 1)[1]
    return name


@dataclass(frozen=True)
class Declaration:
    evidence_type: str
    source_kind: str
    location: str

    def as_dict(self) -> dict[str, str]:
        return {
            "evidence_type": self.evidence_type,
            "source_kind": self.source_kind,
            "location": self.location,
        }


def parse_header_declarations(
    headers: Sequence[Sequence[str]],
) -> list[Declaration]:
    out: list[Declaration] = []
    for idx, pair in enumerate(headers):
        if len(pair) != 2:
            continue
        name, raw_value = pair
        if not isinstance(name, str) or not isinstance(raw_value, str):
            continue
        if name.strip().casefold() not in HEADER_KEYS:
            continue
        value = normalize_value(raw_value)
        if value is not None:
            out.append(
                Declaration(
                    "HTTP_EXPLICIT_SOURCE_KIND_HEADER",
                    value,
                    f"header[{idx}]",
                )
            )
    return out


def _parse_xml_markup(body_text: str) -> tuple[bool, list[Declaration]]:
    try:
        root = ET.fromstring(body_text)
    except ET.ParseError:
        return False, []

    out: list[Declaration] = []

    for element_index, elem in enumerate(root.iter()):
        key = local_name(elem.tag)
        if key in XML_EXACT_KEYS:
            value = normalize_value("".join(elem.itertext()))
            if value is not None:
                out.append(
                    Declaration(
                        "MARKUP_EXPLICIT_SOURCE_KIND_ELEMENT",
                        value,
                        f"xml-element[{element_index}]/{key}",
                    )
                )

        for attr_name, raw_value in elem.attrib.items():
            attr_key = local_name(attr_name)
            if attr_key in XML_EXACT_KEYS:
                value = normalize_value(raw_value)
                if value is not None:
                    out.append(
                        Declaration(
                            "MARKUP_EXPLICIT_SOURCE_KIND_ATTRIBUTE",
                            value,
                            f"xml-attribute[{element_index}]/{attr_key}",
                        )
                    )

    return True, out


class ExplicitSourceKindHTMLParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.declarations: list[Declaration] = []
        self._element_stack: list[tuple[str, int, list[str]]] = []
        self._counter = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag_norm = tag.casefold()
        index = self._counter
        self._counter += 1

        attr_map = {k.casefold(): v for k, v in attrs}

        for attr_name, raw_value in attrs:
            if raw_value is None:
                continue
            if attr_name.casefold() in HTML_NORMALIZED_KEYS:
                value = normalize_value(raw_value)
                if value is not None:
                    self.declarations.append(
                        Declaration(
                            "MARKUP_EXPLICIT_SOURCE_KIND_ATTRIBUTE",
                            value,
                            f"html-attribute[{index}]/{attr_name}",
                        )
                    )

        if tag_norm == "meta":
            declared_key = attr_map.get("name") or attr_map.get("property")
            raw_content = attr_map.get("content")
            if declared_key in META_EXACT_KEYS and raw_content is not None:
                value = normalize_value(raw_content)
                if value is not None:
                    self.declarations.append(
                        Declaration(
                            "HTML_META_EXPLICIT_SOURCE_KIND",
                            value,
                            f"html-meta[{index}]/{declared_key}",
                        )
                    )

        self._element_stack.append((tag_norm, index, []))

    def handle_data(self, data: str) -> None:
        for _, _, chunks in self._element_stack:
            chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag_norm = tag.casefold()
        for pos in range(len(self._element_stack) - 1, -1, -1):
            open_tag, index, chunks = self._element_stack[pos]
            if open_tag != tag_norm:
                continue
            del self._element_stack[pos:]
            if open_tag in HTML_NORMALIZED_KEYS:
                value = normalize_value("".join(chunks))
                if value is not None:
                    self.declarations.append(
                        Declaration(
                            "MARKUP_EXPLICIT_SOURCE_KIND_ELEMENT",
                            value,
                            f"html-element[{index}]/{open_tag}",
                        )
                    )
            break


def parse_markup_declarations(body_text: str) -> list[Declaration]:
    is_xml, xml_declarations = _parse_xml_markup(body_text)
    if is_xml:
        return xml_declarations

    parser = ExplicitSourceKindHTMLParser()
    parser.feed(body_text)
    parser.close()
    return parser.declarations


LABEL_VALUE_RE = re.compile(
    r"(?m)(?<![\w-])"
    r"(source_kind|source-kind|source kind)"
    r"[ \t]*[:=][ \t]*"
    r"(public|synthetic)"
    r"(?=[ \t]*(?:$|[\r\n;,.]))"
)


def parse_exact_label_value_declarations(
    body_text: str,
) -> list[Declaration]:
    out: list[Declaration] = []
    for idx, match in enumerate(LABEL_VALUE_RE.finditer(body_text)):
        value = normalize_value(match.group(2))
        assert value is not None
        out.append(
            Declaration(
                "EXACT_SOURCE_KIND_LABEL_VALUE",
                value,
                f"body-label[{idx}]/{match.group(1)}",
            )
        )
    return out


def collect_declarations(
    headers: Sequence[Sequence[str]],
    body: bytes,
) -> list[Declaration]:
    try:
        body_text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("response body is not valid UTF-8") from exc

    declarations: list[Declaration] = []
    declarations.extend(parse_header_declarations(headers))
    declarations.extend(parse_markup_declarations(body_text))
    declarations.extend(parse_exact_label_value_declarations(body_text))
    return declarations


def evaluate_declarations(
    declarations: Sequence[Declaration],
    *,
    publisher_response_bound_to_ca3: bool,
    raw_integrity_bound: bool,
) -> dict[str, Any]:
    serialized = [d.as_dict() for d in declarations]
    values = [d.source_kind for d in declarations]

    if len(declarations) == 0:
        requirements = {
            "actor_identity_evidence": False,
            "authority_basis_evidence_external_to_oic_evaluator": False,
            "completed_act_evidence": False,
            "ca3_scope_evidence": publisher_response_bound_to_ca3,
            "target_field_scope_evidence": False,
            "act_integrity_or_digest_binding": raw_integrity_bound,
        }
        return {
            "outcome": NOT_ESTABLISHED,
            "declaration_count": 0,
            "declarations": [],
            "declared_values": [],
            "source_kind_value_observed": None,
            "source_kind_value_established": False,
            "standing_requirements": requirements,
            "finding_count": 0,
            "findings": [],
            "declaration_value_created_by_oic": False,
            "source_manifest_population_authorized": False,
        }

    if len(declarations) > 1:
        finding = (
            "multiple admissible explicit source_kind declarations; "
            "act identity is ambiguous"
        )
        if len(set(values)) > 1:
            finding = (
                "conflicting admissible explicit source_kind declarations"
            )
        return {
            "outcome": INCOMPLETE,
            "declaration_count": len(declarations),
            "declarations": serialized,
            "declared_values": values,
            "source_kind_value_observed": None,
            "source_kind_value_established": False,
            "standing_requirements": {
                "actor_identity_evidence": False,
                "authority_basis_evidence_external_to_oic_evaluator": False,
                "completed_act_evidence": False,
                "ca3_scope_evidence": publisher_response_bound_to_ca3,
                "target_field_scope_evidence": True,
                "act_integrity_or_digest_binding": raw_integrity_bound,
            },
            "finding_count": 1,
            "findings": [finding],
            "declaration_value_created_by_oic": False,
            "source_manifest_population_authorized": False,
        }

    declaration = declarations[0]
    requirements = {
        "actor_identity_evidence": publisher_response_bound_to_ca3,
        "authority_basis_evidence_external_to_oic_evaluator":
            publisher_response_bound_to_ca3,
        "completed_act_evidence": True,
        "ca3_scope_evidence": publisher_response_bound_to_ca3,
        "target_field_scope_evidence": True,
        "act_integrity_or_digest_binding": raw_integrity_bound,
    }

    if all(requirements.values()):
        return {
            "outcome": ESTABLISHED,
            "declaration_count": 1,
            "declarations": serialized,
            "declared_values": [declaration.source_kind],
            "source_kind_value_observed": declaration.source_kind,
            "source_kind_value_established": True,
            "standing_requirements": requirements,
            "finding_count": 0,
            "findings": [],
            "declaration_value_created_by_oic": False,
            "source_manifest_population_authorized": False,
        }

    return {
        "outcome": INCOMPLETE,
        "declaration_count": 1,
        "declarations": serialized,
        "declared_values": [declaration.source_kind],
        "source_kind_value_observed": declaration.source_kind,
        "source_kind_value_established": False,
        "standing_requirements": requirements,
        "finding_count": 1,
        "findings": ["explicit declaration observed but standing requirements incomplete"],
        "declaration_value_created_by_oic": False,
        "source_manifest_population_authorized": False,
    }


def load_prior_binding() -> dict[str, Any]:
    prior = json.loads(PRIOR_RESULT.read_text(encoding="utf-8"))
    if prior["status"] != (
        "CLOSED_EXECUTED_PUBLISHER_CANONICAL_LOCATOR_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3"
    ):
        raise ValueError("prior acquisition closure status drift")
    if prior["one_shot"]["consumed"] is not True:
        raise ValueError("prior one-shot consumption state drift")
    if prior["one_shot"]["rerun_authorized"] is not False:
        raise ValueError("prior one-shot rerun state drift")
    if prior["acquisition"]["response_records_received"] != 1:
        raise ValueError("expected exactly one frozen response record")
    if prior["acquisition"]["seed_metadata"]["source_id"] != "CA-3":
        raise ValueError("prior response not bound to CA-3")
    return {
        "publisher_response_bound_to_ca3": True,
        "response_records_received": 1,
        "prior_one_shot_consumed": True,
        "prior_one_shot_rerun_authorized": False,
    }


def execute_reanalysis(output: Path) -> dict[str, Any]:
    verify_bound_input_bytes_only()
    binding = load_prior_binding()

    headers = json.loads(RAW_HEADERS.read_text(encoding="utf-8"))
    body = RAW_BODY.read_bytes()

    declarations = collect_declarations(headers, body)
    evaluation = evaluate_declarations(
        declarations,
        publisher_response_bound_to_ca3=binding[
            "publisher_response_bound_to_ca3"
        ],
        raw_integrity_bound=True,
    )

    result = {
        "work_order":
            "OIC-CANADA-SOURCE-ORIGIN-DECLARATION-EVIDENCE-REANALYSIS-001",
        "status":
            "EXECUTED_DETERMINISTIC_FROZEN_RESPONSE_REANALYSIS",
        "disposition":
            evaluation["outcome"],
        "selected_family":
            "EXPLICIT_SOURCE_ORIGIN_DECLARATION",
        "selected_field":
            "source_kind",
        "frozen_allowed_values":
            ["public", "synthetic"],
        "candidate_value_preselected":
            False,
        "prior_one_shot_consumed":
            True,
        "prior_one_shot_rerun_authorized":
            False,
        "new_network_acquisition":
            False,
        "new_observational_evidence_consumed":
            False,
        "raw_response_semantics_read":
            True,
        "prior_receipt_semantics_read":
            False,
        "raw_input_sha256": {
            "headers": RAW_HEADERS_SHA256,
            "body": RAW_BODY_SHA256,
            "prior_parsed_canonical_evaluation": RAW_PRIOR_EVAL_SHA256,
            "prior_execution_receipt": PRIOR_RECEIPT_SHA256,
        },
        "declaration_evaluation":
            evaluation,
        "source_origin_authority_evidence_established":
            evaluation["outcome"] == ESTABLISHED,
        "source_kind_value_observed":
            evaluation["source_kind_value_observed"],
        "source_kind_value_established":
            evaluation["source_kind_value_established"],
        "declaration_value_created_by_oic":
            False,
        "authority_channel_selected_for_manifest_population":
            False,
        "source_manifest_created":
            False,
        "source_manifest_population_authorized":
            False,
        "source_locator_established":
            False,
        "rights_established":
            False,
        "provenance_established":
            False,
        "redistribution_permission_established":
            False,
        "legal_clearance_established":
            False,
        "causal_root_cause":
            "NOT_ESTABLISHED",
        "cross_source_generality_established":
            False,
        "provider_model_network_calls":
            0,
    }

    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-bound-input-bytes", action="store_true")
    parser.add_argument("--execute-reanalysis", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    verify_bound_input_bytes_only()

    if args.verify_bound_input_bytes:
        print("contract/prereg/prior/raw bytes: HASH-VERIFIED ONLY")
        print("real raw response semantics read: FALSE")
        print("prior receipt semantics read: FALSE")
        print("network acquisition: ZERO")
        return 0

    if not args.execute_reanalysis:
        print("source-origin declaration reanalysis instrument static preflight: PASS")
        print("real raw response semantics read: FALSE")
        print("prior receipt semantics read: FALSE")
        print("network acquisition: ZERO")
        return 0

    if not args.output:
        raise SystemExit("FAIL: --output required for --execute-reanalysis")

    result = execute_reanalysis(Path(args.output))
    print("disposition:", result["disposition"])
    print(
        "source_kind value observed:",
        result["source_kind_value_observed"],
    )
    print(
        "source_kind value established:",
        result["source_kind_value_established"],
    )
    print("new network acquisition: FALSE")
    print("new observational evidence consumed: FALSE")
    print("declaration value created by OIC: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
