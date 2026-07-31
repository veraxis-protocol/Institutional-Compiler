# TBS Terms Recapture Protocol v0.1

Status: **PROTOCOL_SPECIFIED_NOT_EXECUTED**  ·  Execution state: **NOT_EXECUTED**

Specify a deterministic recapture of the licence notice that the publishers of CA-1, CA-2 and CA-4 cite in their own page footers. The prior freeze could not reach it from the execution environment, so those three sources fail closed with no reuse-permission evidence.

Applies to: CA-1, CA-2, CA-4.

## Prior failure

- Evidence record: `CANADA-CA-TERMS`
- Requested URL: `https://www.canada.ca/en/transparency/terms.html`
- Captured: False  ·  HTTP status: None  ·  SHA-256: None

Recorded as an unreachable observation with no bytes and no hash. It is not a finding that reuse is prohibited and must not be read as one.

## Request specification

| Parameter | Value |
|---|---|
| Requested URL | `https://www.canada.ca/en/transparency/terms.html` |
| Method | GET |
| Permitted origin domains | www.canada.ca |
| Permitted redirect domains | www.canada.ca, canada.ca |
| Maximum redirects | 3 |
| Unapproved cross-origin redirect | REJECT_AND_RECORD_FAILURE |
| Required HTTP status | 200 |
| Required media type | text/html |
| Accept-Encoding | identity |
| Timeout | 60s |
| Maximum response bytes | 8388608 |

**Content signature.** Leading bytes, after stripping any UTF-8 BOM and leading whitespace, must begin with one of <!doctype html, <html. A response whose body is a WAF interstitial or an error page must be rejected even when the status line is 200.

Rejection markers, any of which invalidates a 200 response: `Request Rejected`, `Access Denied`, `support ID is`.

**Accept-Encoding rationale.** Bytes must be frozen as the origin serves them. Transport compression would make the recorded digest depend on the client's negotiation rather than on the resource.

## Required record fields

- `acquisition_tool`
- `acquisition_tool_version`
- `byte_length`
- `capture_utc`
- `content_type`
- `etag`
- `final_url`
- `http_status`
- `last_modified`
- `redirect_chain`
- `requested_url`
- `sha256`
- `sha512`

**Byte preservation.** Bytes are written verbatim. No normalization, re-encoding, whitespace change, HTML tidying, or character-set conversion is permitted before hashing or storage.

**Absent headers.** ETag and Last-Modified are recorded only when the origin returns them. A missing header is recorded as null and is never synthesized.

**Failure record.** Any failure writes a deterministic record carrying requested_url, the failure class, the exception type and message, and the capture_utc, with byte_length, sha256 and sha512 set to null. A failed recapture leaves CA-1, CA-2 and CA-4 BLOCKED_PENDING_CLEARANCE.

## Prohibited substitutions

- browser-rendered page text
- screenshots or images of the page
- prose copied or transcribed from a rendered view
- a cached or third-party mirror of the notice
- an archived snapshot in place of the live notice
- a different Government of Canada terms page substituted for the cited URL
- summarized or paraphrased terms in place of captured bytes

None of the above may stand in for captured bytes. A rights determination may cite only an artifact carrying a byte length and both digests.

## Storage and authorization

- Evidence bytes: .local/canada-rights-evidence/ (gitignored)
- Committed output: the evidence ledger record only; never the notice bytes
- Execution is NOT authorized by OIC-CORPUS-WO-009. This document specifies the protocol and stops there.
- A successful recapture does not by itself change any disposition. It unlocks the evidence-review worksheet, whose completion is a separate reviewed step.

