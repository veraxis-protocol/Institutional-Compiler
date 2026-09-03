#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-external-rights-actor-qualification-001"
)

CONTRACT = BENCH / "QUALIFICATION-CONTRACT-v0.1.json"
INVENTORY = BENCH / "PUBLIC-AUTHORITY-EVIDENCE-INVENTORY-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"
RECEIPT_SCHEMA = BENCH / "PUBLIC-EVIDENCE-RECEIPT-SCHEMA-v0.1.json"

PRIOR_CA3_RESULT = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-publisher-canonical-locator-evidence-acquisition-001/"
    "EXECUTION-RESULT-v0.1.json"
)

CONTRACT_SHA256 = "2f4d2ab37a44063767274795cec75fce497235d34e8fab8dc42849813c66f2b0"
INVENTORY_SHA256 = "b5c440d78cf5ed01f29f57a17968b2703b6bc137c177d7c9009fe3784b2520ac"
PREREG_FREEZE_SHA256 = "aec9ac0705793a22cea9f4e5b7f91322e35a89a01ffbe680d40f2cf06ac8024b"
PRIOR_CA3_RESULT_SHA256 = "f796371b8ec92ad491d0f5bd2b8163e25974fbc1fc80cd117c427407d639a775"

ALLOWED_DOMAINS = frozenset({
    "justice.gc.ca",
    "www.justice.gc.ca",
    "laws-lois.justice.gc.ca",
})
MAX_REDIRECTS = 5

SUPPORTED = "CANDIDATE_INSTITUTIONAL_ACTOR_QUALIFICATION_SUPPORTED_CA3"
NOT_ESTABLISHED = (
    "CANDIDATE_INSTITUTIONAL_ACTOR_QUALIFICATION_NOT_ESTABLISHED_CA3"
)
INCOMPLETE = (
    "CANDIDATE_INSTITUTIONAL_ACTOR_QUALIFICATION_INCOMPLETE_FAIL_CLOSED"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_frozen_bytes() -> None:
    expected = {
        CONTRACT: CONTRACT_SHA256,
        INVENTORY: INVENTORY_SHA256,
        PREREG_FREEZE: PREREG_FREEZE_SHA256,
        PRIOR_CA3_RESULT: PRIOR_CA3_RESULT_SHA256,
    }
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise ValueError(f"frozen artifact digest mismatch: {path}")


def load_inventory() -> dict[str, Any]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.casefold() in ALLOWED_DOMAINS
        and parsed.username is None
        and parsed.password is None
    )


@dataclass(frozen=True)
class ResponseRecord:
    requested_url: str
    final_url: str
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    redirect_count: int

    def header_pairs(self) -> list[list[str]]:
        return [[k, v] for k, v in self.headers]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_once(url: str) -> ResponseRecord:
    if not allowed_url(url):
        raise ValueError("URL outside frozen HTTPS allowlist")

    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent":
                "Veraxis-OIC-Public-Authority-Evidence-Acquisition/0.1"
        },
    )
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirect(),
    )
    try:
        with opener.open(req, timeout=30) as response:
            headers = tuple((k, v) for k, v in response.headers.items())
            return ResponseRecord(
                requested_url=url,
                final_url=response.geturl(),
                status=int(response.status),
                headers=headers,
                body=response.read(),
                redirect_count=0,
            )
    except urllib.error.HTTPError as exc:
        headers = tuple((k, v) for k, v in exc.headers.items())
        body = exc.read()
        return ResponseRecord(
            requested_url=url,
            final_url=url,
            status=int(exc.code),
            headers=headers,
            body=body,
            redirect_count=0,
        )


def acquire_url(
    url: str,
    requester: Callable[[str], ResponseRecord] = _request_once,
) -> list[ResponseRecord]:
    if not allowed_url(url):
        raise ValueError("initial URL outside frozen HTTPS allowlist")

    records: list[ResponseRecord] = []
    current = url

    for hop in range(MAX_REDIRECTS + 1):
        rec = requester(current)
        records.append(
            ResponseRecord(
                requested_url=rec.requested_url,
                final_url=rec.final_url,
                status=rec.status,
                headers=rec.headers,
                body=rec.body,
                redirect_count=hop,
            )
        )

        if rec.status not in {301, 302, 303, 307, 308}:
            return records

        locations = [
            value
            for name, value in rec.headers
            if name.casefold() == "location"
        ]
        if len(locations) != 1:
            raise ValueError("redirect requires exactly one Location header")
        if hop >= MAX_REDIRECTS:
            raise ValueError("maximum redirects exceeded")

        nxt = urllib.parse.urljoin(current, locations[0])
        if not allowed_url(nxt):
            raise ValueError("redirect outside frozen HTTPS allowlist")
        current = nxt

    raise ValueError("unreachable redirect loop")


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def response_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    parser = TextExtractor()
    try:
        parser.feed(text)
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        pass
    return re.sub(r"\s+", " ", text).strip().casefold()


def contains_all(text: str, *phrases: str) -> bool:
    return all(p.casefold() in text for p in phrases)


def evaluate_public_evidence(
    responses: Mapping[str, ResponseRecord],
    *,
    ca3_final_url: str,
) -> dict[str, Any]:
    required_ids = {
        "JUS-TERMS",
        "JUS-CLEARANCE-FORM",
        "JUSTICE-LAWS-FAQ",
        "FEDERAL-LAW-ORDER",
    }
    if set(responses) != required_ids:
        return {
            "outcome": INCOMPLETE,
            "finding_count": 1,
            "findings": ["exact four-source response population required"],
            "qualification_findings": {},
            "candidate_actor_qualification_supported": False,
        }

    for source_id, rec in responses.items():
        if not allowed_url(rec.final_url):
            return {
                "outcome": INCOMPLETE,
                "finding_count": 1,
                "findings": [f"{source_id}: final URL outside allowlist"],
                "qualification_findings": {},
                "candidate_actor_qualification_supported": False,
            }
        if rec.status != 200:
            return {
                "outcome": INCOMPLETE,
                "finding_count": 1,
                "findings": [f"{source_id}: HTTP status {rec.status}"],
                "qualification_findings": {},
                "candidate_actor_qualification_supported": False,
            }

    terms = response_text(responses["JUS-TERMS"].body)
    clearance = response_text(responses["JUS-CLEARANCE-FORM"].body)
    faq = response_text(responses["JUSTICE-LAWS-FAQ"].body)
    order = response_text(responses["FEDERAL-LAW-ORDER"].body)

    actor_identity = (
        (
            "communications branch" in terms
            and "copyright administrator" in terms
        )
        or (
            "communications branch" in clearance
            and "copyright administrator" in clearance
        )
    )

    reproduction_role = (
        actor_identity
        and (
            (
                "permission" in terms
                and ("reproduce" in terms or "reproduction" in terms)
            )
            or (
                "copyright" in clearance
                and ("permission" in clearance or "clearance" in clearance)
            )
        )
    )

    justice_material_scope = (
        (
            "department of justice canada" in terms
            and ("material" in terms or "content" in terms)
        )
        or (
            "department of justice canada" in clearance
            and ("work" in clearance or "material" in clearance)
        )
    )

    exact_source_url_intake = (
        "url" in clearance
        and (
            "source" in clearance
            or "web page" in clearance
            or "website" in clearance
        )
        and (
            "copyright administrator" in clearance
            or "communications branch" in clearance
        )
    )

    order_recognized = (
        "reproduction of federal law order" in faq
        and ("acts" in faq or "regulations" in faq)
        and (
            "reproduce" in faq
            or "reproduction" in faq
            or "permission" in faq
        )
    )

    order_authority = (
        "reproduction of federal law order" in order
        and (
            contains_all(order, "without charge", "permission")
            or contains_all(order, "without charge", "reproduce")
        )
        and ("accurate" in order or "accuracy" in order)
        and (
            "official version" in order
            or "not an official version" in order
        )
    )

    ca3_parsed = urllib.parse.urlsplit(ca3_final_url)
    ca3_is_justice = (
        ca3_parsed.scheme == "https"
        and ca3_parsed.hostname == "laws-lois.justice.gc.ca"
        and ca3_parsed.path.casefold().endswith("/eng/xml/sor-87-402.xml")
    )

    findings = {
        "actor_identity_explicit": actor_identity,
        "copyright_or_reproduction_role_explicit": reproduction_role,
        "authority_basis_reference_present": order_authority,
        "justice_material_scope_explicit": justice_material_scope,
        "exact_source_url_intake_supported": exact_source_url_intake,
        "federal_law_reproduction_order_recognized":
            order_recognized and order_authority,
        "ca3_is_justice_laws_material": ca3_is_justice,
    }

    supported = all(findings.values())

    return {
        "outcome": SUPPORTED if supported else NOT_ESTABLISHED,
        "finding_count": 0,
        "findings": [],
        "qualification_findings": findings,
        "candidate_actor_qualification_supported": supported,
        "candidate_actor": (
            "Department of Justice Canada — Communications Branch — Copyright administrator"
        ),
        "qualification_class":
            "publisher_or_crown-copyright-licensing_authority_with_direct_disposition_authority",
        "rights_basis_value_observed": None,
        "redistribution_status_value_observed": None,
        "rights_disposition_request_send_authorized": False,
        "external_actor_contact_authorized": False,
        "source_manifest_population_authorized": False,
    }


def write_raw_evidence(
    evidence_dir: Path,
    source_id: str,
    records: Sequence[ResponseRecord],
) -> dict[str, str]:
    source_dir = evidence_dir / source_id
    source_dir.mkdir(parents=True, exist_ok=False)
    digests: dict[str, str] = {}

    for idx, rec in enumerate(records):
        headers_name = f"response-{idx:02d}-headers.json"
        body_name = f"response-{idx:02d}-body.bin"
        headers_path = source_dir / headers_name
        body_path = source_dir / body_name

        headers_bytes = (
            json.dumps(
                {
                    "requested_url": rec.requested_url,
                    "final_url": rec.final_url,
                    "status": rec.status,
                    "headers": rec.header_pairs(),
                    "redirect_count": rec.redirect_count,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n"
        ).encode("utf-8")

        headers_path.write_bytes(headers_bytes)
        body_path.write_bytes(rec.body)

        digests[f"{source_id}/{headers_name}"] = sha256_bytes(headers_bytes)
        digests[f"{source_id}/{body_name}"] = sha256_bytes(rec.body)

    return digests


def create_started_lock(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha256_bytes(data)


def execute_live(
    *,
    authorization_receipt: Path,
    started_lock: Path,
    evidence_dir: Path,
    output: Path,
    requester: Callable[[str], ResponseRecord] = _request_once,
) -> dict[str, Any]:
    verify_frozen_bytes()

    if not authorization_receipt.is_file():
        raise SystemExit("FAIL: explicit authorization receipt missing")
    if started_lock.exists():
        raise SystemExit("FAIL: STARTED lock already exists; acquisition consumed")
    if evidence_dir.exists():
        raise SystemExit("FAIL: evidence directory already exists")
    if output.exists():
        raise SystemExit("FAIL: output already exists")

    inventory = load_inventory()
    sources = inventory["sources"]

    started_sha = create_started_lock(
        started_lock,
        {
            "work_order":
                "OIC-CANADA-EXTERNAL-RIGHTS-ACTOR-QUALIFICATION-001",
            "status": "STARTED",
            "one_shot": True,
            "authorization_receipt_sha256": sha256(authorization_receipt),
            "source_population": [x["source_id"] for x in sources],
        },
    )

    evidence_dir.mkdir(parents=True, exist_ok=False)
    raw_digests: dict[str, str] = {}
    terminal_records: dict[str, ResponseRecord] = {}
    acquisition_receipts: dict[str, Any] = {}

    try:
        for source in sources:
            source_id = source["source_id"]
            url = source["url"]
            records = acquire_url(url, requester=requester)
            raw_digests.update(write_raw_evidence(evidence_dir, source_id, records))
            terminal = records[-1]
            terminal_records[source_id] = terminal
            acquisition_receipts[source_id] = {
                "requested_url": url,
                "final_url": terminal.final_url,
                "status": terminal.status,
                "redirect_count": len(records) - 1,
                "response_count": len(records),
            }

        prior = json.loads(PRIOR_CA3_RESULT.read_text(encoding="utf-8"))
        ca3_final_url = prior["acquisition"]["seed_metadata"]["final_url"]

        evaluation = evaluate_public_evidence(
            terminal_records,
            ca3_final_url=ca3_final_url,
        )

        result = {
            "work_order":
                "OIC-CANADA-EXTERNAL-RIGHTS-ACTOR-QUALIFICATION-001",
            "status":
                "PUBLIC_QUALIFICATION_EVIDENCE_ACQUISITION_EXECUTED",
            "disposition":
                evaluation["outcome"],
            "started_lock_sha256":
                started_sha,
            "authorization_receipt_sha256":
                sha256(authorization_receipt),
            "public_get_requests_made":
                len(sources),
            "external_actor_contacted":
                False,
            "email_sent":
                False,
            "form_submitted":
                False,
            "rights_disposition_request_sent":
                False,
            "raw_evidence_sha256":
                raw_digests,
            "acquisition_receipts":
                acquisition_receipts,
            "evaluation":
                evaluation,
            "candidate_actor_qualification_supported":
                evaluation["candidate_actor_qualification_supported"],
            "rights_basis_value_observed":
                None,
            "redistribution_status_value_observed":
                None,
            "source_manifest_created":
                False,
            "source_manifest_population_authorized":
                False,
        }
    except Exception as exc:
        result = {
            "work_order":
                "OIC-CANADA-EXTERNAL-RIGHTS-ACTOR-QUALIFICATION-001",
            "status":
                "PUBLIC_QUALIFICATION_EVIDENCE_ACQUISITION_EXECUTED_FAIL_CLOSED",
            "disposition":
                INCOMPLETE,
            "started_lock_sha256":
                started_sha,
            "authorization_receipt_sha256":
                sha256(authorization_receipt),
            "public_get_requests_made":
                len(acquisition_receipts),
            "external_actor_contacted":
                False,
            "email_sent":
                False,
            "form_submitted":
                False,
            "rights_disposition_request_sent":
                False,
            "raw_evidence_sha256":
                raw_digests,
            "acquisition_receipts":
                acquisition_receipts,
            "finding_count":
                1,
            "findings":
                [f"{type(exc).__name__}: {exc}"],
            "candidate_actor_qualification_supported":
                False,
            "rights_basis_value_observed":
                None,
            "redistribution_status_value_observed":
                None,
            "source_manifest_created":
                False,
            "source_manifest_population_authorized":
                False,
        }

    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-frozen-bytes", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--authorization-receipt")
    parser.add_argument("--started-lock")
    parser.add_argument("--evidence-dir")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    verify_frozen_bytes()

    if args.verify_frozen_bytes:
        print("qualification contract/inventory/prereg/CA-3 binding: HASH-VERIFIED")
        print("real Justice Canada GET requests: ZERO")
        print("real public evidence acquired: ZERO")
        return 0

    if not args.execute_live:
        print("external rights actor qualification instrument static preflight: PASS")
        print("real Justice Canada GET requests: ZERO")
        print("external actor contact: ZERO")
        return 0

    required = [
        args.authorization_receipt,
        args.started_lock,
        args.evidence_dir,
        args.output,
    ]
    if any(x is None for x in required):
        raise SystemExit("FAIL: live execution paths required")

    result = execute_live(
        authorization_receipt=Path(args.authorization_receipt),
        started_lock=Path(args.started_lock),
        evidence_dir=Path(args.evidence_dir),
        output=Path(args.output),
    )
    print("disposition:", result["disposition"])
    print(
        "candidate qualification supported:",
        str(result["candidate_actor_qualification_supported"]).upper(),
    )
    print("external actor contacted: FALSE")
    print("email sent: FALSE")
    print("form submitted: FALSE")
    print("rights disposition request sent: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
