# OIC Corpus Rights / Provenance Preflight 001

**Work order:** `OIC-CORPUS-RIGHTS-PROVENANCE-PREFLIGHT-001`

**Status:** `PREREGISTRATION_ONLY_NOT_EXECUTED`

## Purpose

Freeze the contract and fail-closed decision rule for the repository's still-open
preflight corpus rights/provenance gate before any corpus evidence is inspected,
classified, or populated.

`STATUS.md` requires a completed `SOURCE_MANIFEST.csv` for this gate. The
roadmap calls for one bounded public/synthetic procurement corpus and source
anchors.

## Authorized scope

This work order authorizes only:

1. freezing the `SOURCE_MANIFEST.csv` field contract;
2. freezing validation and adjudication rules;
3. later implementing an offline validator against those frozen rules; and
4. later evaluating a populated manifest under a separately authorized execution step.

This work order does **not** itself inspect corpus contents, populate the
manifest, establish rights, establish provenance, admit sources, alter
interpretation semantics, canonicalize institutional meaning, construct
Institutional IR, construct an Open Control Envelope, compile Rego, perform
runtime ALLOW/DENY, execute ZTL/VEIP, or make provider/model/network calls.

## Frozen manifest location

The gate evidence file is:

`SOURCE_MANIFEST.csv`

at repository root.

## Fail-closed decision rule

The gate may be adjudicated `PASS` only if every row in the completed manifest:

- satisfies the frozen field and value contract;
- has a unique non-empty `source_id`;
- uses `content_hash` in the exact `sha256:<64 lowercase hex>` form already
  used by `SourceDocument`;
- identifies the source as `public` or `synthetic`;
- identifies a specific rights basis and non-empty rights evidence;
- has `provenance_status=verified`;
- has `rights_status=verified`;
- does not have `redistribution_status=unknown`;
- identifies a repository-relative `local_path` for the bounded source object;
- and is within the explicitly declared bounded corpus population represented by
  the manifest.

The gate is `FAIL_CLOSED` if the manifest is absent, empty, malformed, contains
duplicate source IDs, contains an unsupported source kind, contains unknown or
unverified rights/provenance state, omits required evidence, contains an invalid
content hash, or contains any row whose required status cannot be established.

No missing value may be inferred. No public availability may be treated as a
rights grant. No synthetic label may be treated as proof of ownership. No
validator may silently repair or normalize evidence.

## Claim ceiling

A later `PASS` may establish only that the bounded corpus described by that
specific manifest satisfied this preflight documentation contract at the frozen
repository state. It does not establish legal advice, universal copyright
clearance, downstream redistribution rights beyond the recorded basis, semantic
correctness, institutional authority, benchmark validity, production readiness,
or enterprise readiness.

A `FAIL_CLOSED` result establishes only that the preflight evidence is
insufficient under the frozen contract; it does not establish infringement or
invalidity of the underlying source.

## Current state after this preregistration

- `SOURCE_MANIFEST.csv` remains unpopulated by this work order.
- Corpus rights/provenance gate remains `OPEN`.
- No corpus evidence has been adjudicated.
- No architecture authorization changes.
- No provider/model/network calls.
