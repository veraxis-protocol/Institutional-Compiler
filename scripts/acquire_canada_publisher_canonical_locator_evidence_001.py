#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html.parser
import http.client
import json
import os
import re
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / (
    "benchmarks/preflight/corpus-rights-provenance-001/"
    "canada-publisher-canonical-locator-evidence-acquisition-001"
)
CONTRACT = BENCH / "ACQUISITION-CONTRACT-v0.1.json"
PREREG_FREEZE = BENCH / "PREREGISTRATION-FREEZE-v0.1.json"
NAV_SEED = ROOT / "benchmarks/corpus/canada/freeze-v0.1/INDEX.json"

CONTRACT_SHA256 = "95db83b9d6d8cf81d35c40af0064e0ddc27920ce178bbc6af2ac979f51e109ed"
PREREG_FREEZE_SHA256 = "d7e707469454d135ffed64730b9fc37b214528a4d89fe1f4da7e961564fff612"
NAV_SEED_SHA256 = "87649c72244d5a3f6d467258536db0bb7ef585907a30c7fca3056dfd7a976880"

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2_000_000
USER_AGENT = "Veraxis-OIC-Evidence-Acquisition/0.1"
ALLOWED_METHODS = frozenset({"GET", "HEAD"})

ESTABLISHED = "PUBLISHER_CANONICAL_LOCATOR_AUTHORITY_EVIDENCE_ESTABLISHED_CA3"
NOT_ESTABLISHED = (
    "PUBLISHER_CANONICAL_LOCATOR_AUTHORITY_EVIDENCE_NOT_ESTABLISHED_CA3"
)
INCOMPLETE = "ACQUISITION_INCOMPLETE_FAIL_CLOSED"

# Frozen Canada-only public-suffix subset. This is deliberately narrow.
# Any future seed outside these suffixes fails closed rather than guessing.
KNOWN_CA_PUBLIC_SUFFIXES = (
    "gc.ca",
    "ca",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bound_bytes_only() -> None:
    if sha256(CONTRACT) != CONTRACT_SHA256:
        raise SystemExit("FAIL: acquisition contract digest mismatch")
    if sha256(PREREG_FREEZE) != PREREG_FREEZE_SHA256:
        raise SystemExit("FAIL: preregistration freeze digest mismatch")
    if sha256(NAV_SEED) != NAV_SEED_SHA256:
        raise SystemExit("FAIL: navigation seed digest mismatch")


def _walk_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_objects(child)


def extract_ca3_navigation_seed(doc: Mapping[str, Any]) -> dict[str, Any]:
    matches = [
        obj for obj in _walk_objects(doc)
        if obj.get("source_id") == "CA-3"
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one CA-3 object, found {len(matches)}")

    obj = matches[0]
    allowed = {
        "source_id": obj.get("source_id"),
        "target_url": obj.get("target_url"),
        "final_url": obj.get("final_url"),
    }

    if allowed["source_id"] != "CA-3":
        raise ValueError("CA-3 source id drift")

    for key in ("target_url", "final_url"):
        value = allowed[key]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{key} must be string or null")

    if not allowed["target_url"] and not allowed["final_url"]:
        raise ValueError("CA-3 has no navigation URL")

    return allowed


def choose_navigation_url(seed: Mapping[str, Any]) -> str:
    raw = seed.get("final_url") or seed.get("target_url")
    if not isinstance(raw, str) or not raw:
        raise ValueError("no usable navigation URL")
    return normalize_https_url(raw)


def normalize_https_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        raise ValueError("URL must use https")
    if not parts.hostname:
        raise ValueError("URL missing hostname")
    if parts.username or parts.password:
        raise ValueError("credentialed URL forbidden")
    if parts.port not in (None, 443):
        raise ValueError("non-standard HTTPS port forbidden")
    if parts.fragment:
        parts = parts._replace(fragment="")
    return urlunsplit(parts)


def registrable_domain(hostname: str) -> str:
    host = hostname.rstrip(".").lower()
    labels = host.split(".")
    if len(labels) < 2:
        raise ValueError("hostname is not registrable")

    matched_suffix = None
    for suffix in KNOWN_CA_PUBLIC_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            suffix_labels = suffix.count(".") + 1
            if len(labels) <= suffix_labels:
                raise ValueError("hostname is itself a public suffix")
            matched_suffix = suffix
            break

    if matched_suffix is None:
        raise ValueError("hostname outside frozen Canada public-suffix subset")

    suffix_labels = matched_suffix.count(".") + 1
    return ".".join(labels[-(suffix_labels + 1):])


def same_registrable_domain(a: str, b: str) -> bool:
    return registrable_domain(a) == registrable_domain(b)


@dataclass(frozen=True)
class ResponseRecord:
    request_url: str
    status: int
    reason: str
    headers: tuple[tuple[str, str], ...]
    body: bytes

    @property
    def header_map(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for name, value in self.headers:
            out.setdefault(name.lower(), []).append(value)
        return out


class AcquisitionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        records: Sequence["ResponseRecord"] = (),
    ) -> None:
        super().__init__(message)
        self.records = tuple(records)


def _request_once(url: str, method: str = "GET") -> ResponseRecord:
    if method not in ALLOWED_METHODS:
        raise AcquisitionError("method outside allowlist")

    normalized = normalize_https_url(url)
    parts = urlsplit(normalized)
    host = parts.hostname
    assert host is not None

    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query

    context = ssl.create_default_context()
    conn = http.client.HTTPSConnection(
        host,
        port=443,
        timeout=20,
        context=context,
    )
    try:
        conn.request(
            method,
            path,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        resp = conn.getresponse()
        headers = tuple((k, v) for k, v in resp.getheaders())
        if method == "HEAD":
            body = b""
        else:
            body = resp.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise AcquisitionError("response exceeds maximum bytes")
        return ResponseRecord(
            request_url=normalized,
            status=resp.status,
            reason=resp.reason or "",
            headers=headers,
            body=body,
        )
    finally:
        conn.close()


def acquire_with_bounded_redirects(
    start_url: str,
    requester=_request_once,
) -> list[ResponseRecord]:
    current = normalize_https_url(start_url)
    seed_host = urlsplit(current).hostname
    assert seed_host is not None
    seed_registrable = registrable_domain(seed_host)

    records: list[ResponseRecord] = []

    for hop in range(MAX_REDIRECTS + 1):
        try:
            record = requester(current, "GET")
        except Exception as exc:
            inherited = (
                list(exc.records)
                if isinstance(exc, AcquisitionError)
                else []
            )
            if inherited:
                records.extend(inherited)
            raise AcquisitionError(
                f"request failed: {type(exc).__name__}: {exc}",
                records=records,
            ) from exc

        records.append(record)

        if record.status in {301, 302, 303, 307, 308}:
            locations = record.header_map.get("location", [])
            if len(locations) != 1:
                raise AcquisitionError(
                    "redirect must contain exactly one Location header",
                    records=records,
                )
            if hop >= MAX_REDIRECTS:
                raise AcquisitionError(
                    "maximum redirects exceeded",
                    records=records,
                )

            try:
                nxt = normalize_https_url(urljoin(current, locations[0]))
                next_host = urlsplit(nxt).hostname
                if next_host is None:
                    raise ValueError("redirect URL missing hostname")
                if registrable_domain(next_host) != seed_registrable:
                    raise ValueError(
                        "redirect escaped seed registrable-domain boundary"
                    )
            except Exception as exc:
                raise AcquisitionError(
                    f"redirect inadmissible: {type(exc).__name__}: {exc}",
                    records=records,
                ) from exc

            current = nxt
            continue

        return records

    raise AcquisitionError(
        "redirect loop exceeded",
        records=records,
    )


_LINK_SPLIT_RE = re.compile(r'\s*,\s*(?=<)')


def parse_link_header_canonicals(
    values: Sequence[str],
    base_url: str,
) -> list[str]:
    out: list[str] = []
    for header in values:
        # Conservative parser: a comma starts a new link-value only when the
        # next non-space character is "<". This avoids splitting quoted params.
        for item in _LINK_SPLIT_RE.split(header):
            item = item.strip()
            if not item.startswith("<") or ">" not in item:
                continue
            end = item.find(">")
            target = item[1:end].strip()
            params = item[end + 1 :].split(";")
            rel_tokens: list[str] = []
            for param in params:
                if "=" not in param:
                    continue
                key, value = param.split("=", 1)
                if key.strip().lower() != "rel":
                    continue
                value = value.strip().strip('"').strip("'")
                rel_tokens.extend(x.lower() for x in value.split())
            if "canonical" in rel_tokens:
                out.append(urljoin(base_url, target))
    return out


class CanonicalHTMLParser(html.parser.HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.canonicals: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "link":
            return
        d = {k.lower(): v for k, v in attrs}
        rel = d.get("rel") or ""
        href = d.get("href")
        if href and "canonical" in {x.lower() for x in rel.split()}:
            self.canonicals.append(urljoin(self.base_url, href))


def parse_html_canonicals(body: bytes, base_url: str) -> list[str]:
    # Canonical declaration discovery is intentionally limited to HTML bytes.
    # Decode fail-closed replacement is acceptable because malformed URLs will
    # fail later URL validation.
    text = body.decode("utf-8", errors="replace")
    parser = CanonicalHTMLParser(base_url)
    parser.feed(text)
    parser.close()
    return parser.canonicals


def canonical_declarations(record: ResponseRecord) -> list[dict[str, str]]:
    headers = record.header_map
    declarations: list[dict[str, str]] = []

    for url in parse_link_header_canonicals(
        headers.get("link", []),
        record.request_url,
    ):
        declarations.append({
            "evidence_type": "HTTP_LINK_HEADER_CANONICAL",
            "canonical_url": url,
        })

    content_types = headers.get("content-type", [])
    html_allowed = (
        not content_types
        or any(
            "text/html" in value.lower()
            or "application/xhtml+xml" in value.lower()
            for value in content_types
        )
    )
    if html_allowed and record.body:
        for url in parse_html_canonicals(record.body, record.request_url):
            declarations.append({
                "evidence_type": "HTML_LINK_REL_CANONICAL",
                "canonical_url": url,
            })

    return declarations


def evaluate_final_response(
    records: Sequence[ResponseRecord],
    publisher_identity_preexisting: bool = True,
) -> dict[str, Any]:
    if not records:
        return {
            "outcome": INCOMPLETE,
            "finding_count": 1,
            "findings": ["no response records"],
        }

    final = records[-1]
    if not (200 <= final.status < 300):
        return {
            "outcome": INCOMPLETE,
            "finding_count": 1,
            "findings": [f"final HTTP status not successful: {final.status}"],
        }

    declarations = canonical_declarations(final)
    findings: list[str] = []

    if len(declarations) == 0:
        return {
            "outcome": NOT_ESTABLISHED,
            "finding_count": 0,
            "findings": [],
            "declaration_count": 0,
            "canonical_declarations": [],
            "standing_requirements": {
                "actor_identity_evidence": False,
                "authority_basis_evidence_external_to_oic_evaluator": False,
                "completed_act_evidence": False,
                "ca3_scope_evidence": True,
                "target_field_scope_evidence": False,
                "act_integrity_or_digest_binding": True,
            },
        }

    if len(declarations) != 1:
        findings.append(
            f"expected exactly one canonical declaration, found {len(declarations)}"
        )
        return {
            "outcome": NOT_ESTABLISHED,
            "finding_count": len(findings),
            "findings": findings,
            "declaration_count": len(declarations),
            "canonical_declarations": declarations,
        }

    declaration = declarations[0]
    try:
        canonical = normalize_https_url(declaration["canonical_url"])
    except ValueError as exc:
        findings.append(f"canonical URL inadmissible: {exc}")
        return {
            "outcome": NOT_ESTABLISHED,
            "finding_count": len(findings),
            "findings": findings,
            "declaration_count": 1,
            "canonical_declarations": declarations,
        }

    final_host = urlsplit(final.request_url).hostname
    canonical_host = urlsplit(canonical).hostname
    assert final_host is not None and canonical_host is not None

    try:
        domain_ok = same_registrable_domain(final_host, canonical_host)
    except ValueError as exc:
        findings.append(f"canonical domain inadmissible: {exc}")
        domain_ok = False

    if not domain_ok:
        findings.append("canonical escaped publisher registrable-domain boundary")

    requirements = {
        "actor_identity_evidence": bool(
            publisher_identity_preexisting and domain_ok
        ),
        "authority_basis_evidence_external_to_oic_evaluator": domain_ok,
        "completed_act_evidence": True,
        "ca3_scope_evidence": True,
        "target_field_scope_evidence": True,
        "act_integrity_or_digest_binding": True,
    }

    established = (
        not findings
        and all(requirements.values())
        and len(declarations) == 1
    )

    return {
        "outcome": ESTABLISHED if established else NOT_ESTABLISHED,
        "finding_count": len(findings),
        "findings": findings,
        "declaration_count": 1,
        "canonical_declarations": [{
            **declaration,
            "canonical_url": canonical,
        }],
        "standing_requirements": requirements,
        "selected_field": "source_locator",
        "real_authority_act_created_by_oic": False,
        "declaration_value_created": False,
        "source_manifest_population_authorized": False,
    }


def response_receipt(records: Sequence[ResponseRecord]) -> dict[str, Any]:
    rows = []
    for idx, record in enumerate(records):
        header_bytes = json.dumps(
            list(record.headers),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        rows.append({
            "hop": idx,
            "request_url": record.request_url,
            "status": record.status,
            "reason": record.reason,
            "headers_sha256": sha256_bytes(header_bytes),
            "body_sha256": sha256_bytes(record.body),
            "body_bytes": len(record.body),
        })
    return {
        "response_count": len(rows),
        "responses": rows,
    }


def write_raw_evidence(
    directory: Path,
    records: Sequence[ResponseRecord],
    evaluation: Mapping[str, Any],
) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=False)
    digests: dict[str, str] = {}

    for idx, record in enumerate(records):
        header_path = directory / f"response-{idx:02d}-headers.json"
        body_path = directory / f"response-{idx:02d}-body.bin"

        header_path.write_text(
            json.dumps(list(record.headers), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        body_path.write_bytes(record.body)

        digests[header_path.name] = sha256(header_path)
        digests[body_path.name] = sha256(body_path)

    evaluation_path = directory / "parsed-evaluation.json"
    evaluation_path.write_text(
        json.dumps(dict(evaluation), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    digests[evaluation_path.name] = sha256(evaluation_path)
    return digests


def create_started_lock(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha256(path)


def execute_live(
    authorization_receipt: Path,
    evidence_dir: Path,
    started_lock: Path,
    *,
    seed_loader=load_json,
    acquirer=acquire_with_bounded_redirects,
) -> dict[str, Any]:
    verify_bound_bytes_only()

    if not authorization_receipt.is_file():
        raise SystemExit("FAIL: explicit authorization receipt missing")
    if evidence_dir.exists():
        raise SystemExit("FAIL: evidence directory already exists")

    # Verify that the evidence destination can be created before the irreversible
    # STARTED lock is consumed.
    evidence_parent = evidence_dir.parent
    evidence_parent.mkdir(parents=True, exist_ok=True)
    probe = evidence_parent / f".{evidence_dir.name}.write-probe"
    fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, b"preflight\n")
        os.fsync(fd)
    finally:
        os.close(fd)
        probe.unlink()

    # STARTED is permanent and created before semantic seed read or network I/O.
    started_sha = create_started_lock(
        started_lock,
        {
            "work_order":
                "OIC-CANADA-PUBLISHER-CANONICAL-LOCATOR-EVIDENCE-ACQUISITION-001",
            "status": "STARTED",
            "authorization_receipt_sha256": sha256(authorization_receipt),
            "navigation_seed_sha256": NAV_SEED_SHA256,
            "one_shot": True,
        },
    )

    navigation_seed_semantics_read = False
    network_request_made = False
    seed: dict[str, Any] | None = None
    records: list[ResponseRecord] = []

    try:
        seed_doc = seed_loader(NAV_SEED)
        navigation_seed_semantics_read = True
        seed = extract_ca3_navigation_seed(seed_doc)
        start_url = choose_navigation_url(seed)

        start_host = urlsplit(start_url).hostname
        if start_host is None:
            raise ValueError("navigation URL missing hostname")
        registrable_domain(start_host)

        network_request_made = True
        records = acquirer(start_url)
        if not records:
            raise AcquisitionError("acquirer returned zero response records")

        evaluation = evaluate_final_response(records)
        receipt = response_receipt(records)
        raw_digests = write_raw_evidence(evidence_dir, records, evaluation)

        return {
            "work_order":
                "OIC-CANADA-PUBLISHER-CANONICAL-LOCATOR-EVIDENCE-ACQUISITION-001",
            "status": "LIVE_ACQUISITION_EXECUTED",
            "outcome": evaluation["outcome"],
            "started_lock_sha256": started_sha,
            "authorization_receipt_sha256": sha256(authorization_receipt),
            "navigation_seed_sha256": NAV_SEED_SHA256,
            "navigation_seed_semantics_read": navigation_seed_semantics_read,
            "network_request_made": network_request_made,
            "response_records_received": len(records),
            "new_real_world_evidence_acquired": bool(records),
            "external_actor_contacted": False,
            "seed_metadata": seed,
            "response_receipt": receipt,
            "evaluation": evaluation,
            "raw_evidence_sha256": raw_digests,
            "real_authority_act_created_by_oic": False,
            "declaration_values_created": False,
            "source_manifest_created": False,
            "source_manifest_population_authorized": False,
        }
    except Exception as exc:
        partial_records = list(records)
        if isinstance(exc, AcquisitionError) and exc.records:
            partial_records = list(exc.records)

        findings = [f"{type(exc).__name__}: {exc}"]
        receipt = None
        raw_digests: dict[str, str] = {}

        if partial_records:
            incomplete_evaluation = {
                "outcome": INCOMPLETE,
                "finding_count": 1,
                "findings": findings,
                "declaration_value_created": False,
                "source_manifest_population_authorized": False,
            }
            try:
                receipt = response_receipt(partial_records)
                raw_digests = write_raw_evidence(
                    evidence_dir,
                    partial_records,
                    incomplete_evaluation,
                )
            except Exception as persistence_exc:
                findings.append(
                    "EVIDENCE_PERSISTENCE_FAILURE: "
                    f"{type(persistence_exc).__name__}: {persistence_exc}"
                )

        return {
            "work_order":
                "OIC-CANADA-PUBLISHER-CANONICAL-LOCATOR-EVIDENCE-ACQUISITION-001",
            "status": "LIVE_ACQUISITION_EXECUTED_FAIL_CLOSED",
            "outcome": INCOMPLETE,
            "started_lock_sha256": started_sha,
            "authorization_receipt_sha256": sha256(authorization_receipt),
            "navigation_seed_sha256": NAV_SEED_SHA256,
            "navigation_seed_semantics_read": navigation_seed_semantics_read,
            "network_request_made": network_request_made,
            "response_records_received": len(partial_records),
            "new_real_world_evidence_acquired": bool(partial_records),
            "external_actor_contacted": False,
            "seed_metadata": seed,
            "response_receipt": receipt,
            "raw_evidence_sha256": raw_digests,
            "finding_count": len(findings),
            "findings": findings,
            "real_authority_act_created_by_oic": False,
            "declaration_values_created": False,
            "source_manifest_created": False,
            "source_manifest_population_authorized": False,
        }

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-bound-input-bytes", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--authorization-receipt")
    parser.add_argument("--evidence-dir")
    parser.add_argument("--started-lock")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    verify_bound_bytes_only()

    if args.verify_bound_input_bytes:
        print("contract/prereg/navigation-seed bytes: HASH-VERIFIED ONLY")
        print("navigation-seed semantics read: FALSE")
        print("network requests: ZERO")
        return 0

    if not args.execute_live:
        print("publisher canonical-locator acquisition instrument static preflight: PASS")
        print("navigation-seed semantics read: FALSE")
        print("network requests: ZERO")
        print("new real-world evidence acquired: ZERO")
        return 0

    required = {
        "--authorization-receipt": args.authorization_receipt,
        "--evidence-dir": args.evidence_dir,
        "--started-lock": args.started_lock,
        "--output": args.output,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit("FAIL: missing live arguments: " + ", ".join(missing))

    result = execute_live(
        Path(args.authorization_receipt),
        Path(args.evidence_dir),
        Path(args.started_lock),
    )
    output = Path(args.output)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("outcome:", result["outcome"])
    print("STARTED lock consumed: TRUE")
    print("network request made:", result["network_request_made"])
    print("external actor contacted: FALSE")
    print("declaration values created: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
