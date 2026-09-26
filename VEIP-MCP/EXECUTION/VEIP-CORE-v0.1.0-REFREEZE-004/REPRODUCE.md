# Reproduction Instructions — VEIP-CORE-v0.1.0-REFREEZE-004

**Engine version**: 0.1.0
**Python requirement**: 3.11+

## Prerequisites

1. Obtain the 7 frozen input files from Dropbox (see `01_INPUT_VERIFICATION.md`
   for Dropbox file IDs and binding hashes).
2. Verify all 7 SHA-256 hashes before proceeding.
3. For `VEIP_CORE_SCHEMA_v0.1.json` and `VEIP_REASON_CODE_REGISTRY_v0.1.json`:
   these files have CRLF line endings and must be obtained with byte-faithful
   copy. If downloading from Dropbox CDN: use direct binary download.
   If using Dropbox text extraction API: apply the CRLF recovery algorithm
   documented in `06_INTEGRITY_AUDIT.md` and verify the hash.

## Installation

```bash
cd veip-core
pip install -e .
```

## Run Full Test Suite

```bash
pytest tests/ -v
```

Expected: 20 tests PASS, 97 subtests PASS.

## Run Frozen Corpus Replay

```bash
python3 tools/replay_corpus.py > output.json
```

Expected: 56 fixtures processed, output is a JSON array with one entry per fixture.

## Run Conformance Runner (Requires Runner ZIP)

The external conformance runner must be extracted to `runner/extracted/` first:

```bash
cd runner
unzip VEIP_CONFORMANCE_RUNNER_v0.1.zip -d extracted/
cd ../veip-core
python3 tools/run_conformance.py
```

Expected: 56/56 PASS. Report written to `03_CONFORMANCE_REPORT.json`.

Note: The runner ZIP was not present in REFREEZE-004 due to a CDN block.
If reproducing in an environment with Dropbox CDN access, download from
`id:AdzSIi2kJ_kAAAAAAAAvHg` and verify SHA-256
`4f51176d07d5b2a8fcbcb07ca986326c58fb13542271bd2aae040bcf62bf1c9e`.

## Verify Determinism

Run the corpus replay twice and compare SHA-256 of the JSON outputs:

```bash
python3 tools/replay_corpus.py | python3 -c "
import json, hashlib, sys
data = sys.stdin.buffer.read()
print(hashlib.sha256(data).hexdigest())
"
```

Run this twice; the hashes must be identical.

## Verify Input Hashes

```bash
sha256sum inputs/*.json inputs/*.md
```

Compare against the binding hashes in `01_INPUT_VERIFICATION.md`.
