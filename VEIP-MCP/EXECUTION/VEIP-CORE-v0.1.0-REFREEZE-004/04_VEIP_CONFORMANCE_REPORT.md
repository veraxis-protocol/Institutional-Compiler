# VEIP Conformance Report — VEIP-CORE-v0.1.0-REFREEZE-004

**Date**: 2026-09-22
**Engine version**: 0.1.0

## STOP Condition: Conformance Runner ZIP Unavailable

The externally supplied `VEIP_CONFORMANCE_RUNNER_v0.1.zip` cannot be
deposited into the `runner/` directory because the Dropbox CDN is blocked
in this execution environment.

**Artifact details:**
- Dropbox path: `/VEIP-MCP/VEIP_CONFORMANCE_RUNNER_v0.1.zip`
- Dropbox file ID: `id:AdzSIi2kJ_kAAAAAAAAvHg`
- Binding SHA-256: `4f51176d07d5b2a8fcbcb07ca986326c58fb13542271bd2aae040bcf62bf1c9e`
- Size: 29,973 bytes

**Blocked endpoints:**
- `https://content.dropboxapi.com/2/files/download` — HTTP 403 (proxy gateway)
- `https://dropboxusercontent.com` (CDN direct links) — HTTP 403 (proxy gateway)

**Why text extraction is not applicable:**
The artifact is a binary ZIP file. The Dropbox `fetch` MCP tool performs
text extraction (not binary download). Even if the ZIP happened to contain
readable bytes, the ZIP format requires byte-faithful transfer for the
archive to be valid; text extraction with CR-stripping and
potential encoding transformations would corrupt it. Per work-order rule:
"If exact binary copy is unavailable for any required artifact: STOP."

**The `runner/` directory is therefore empty.**

## Native Corpus Replay (Without External Runner)

Although the external conformance runner cannot be run in this environment,
the internal corpus replay was executed against all 56 frozen fixtures from
`VEIP_CANONICAL_FIXTURES_v0.3.json` using the native Python engine:

```
python3 tools/replay_corpus.py
```

All 56 fixtures produced output. Results stored in
`evidence/frozen_56_report.json` and `evidence/frozen_56_stdout.txt`.

Additionally, `pytest tests/test_core.py::FrozenConformanceTests` ran all
56 fixtures against their expected outputs, verifying:
- Correct `canonical_hash` for each adjudication result
- Correct `error_code` for all 4 engine-error fixtures
- Correct `reliance_projection`, `dimensions`, and `reason_codes`

See `evidence/native_tests.txt` for the full pytest output.

## Fixture Corpus Binding

The conformance runner ZIP is confirmed at the binding hash in Dropbox;
it was not modified. Its absence here is an infrastructure constraint, not
a content dispute.

Adversarial freeze audit for the fixture corpus:
- `inputs/VEIP_CANONICAL_FIXTURES_v0.3_ADVERSARIAL_FREEZE_AUDIT.md`
- SHA-256: `0dd75c830b63a3d74f73885793e3a1e5c231545cea4e14549e97690dcb0a75a6`
- Audit result: **475 PASS / 0 FAIL / 475 total — PASS**

---
**NOT SELF-ADJUDICATED**
