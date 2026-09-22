# Reproduction Instructions — VEIP-CORE-v0.1.0-REFREEZE-003

## Prerequisites

- Python 3.11+
- Node.js 18+ (for differential testing)
- pip

## Setup

```bash
cd veip-core
pip install -e .
```

## Run Native Tests

```bash
cd veip-core
python3 -m pytest tests/ -v
```

Expected: `20 passed, 97 subtests passed`

## Run Conformance Runner

```bash
cd veip-core
python3 tools/run_conformance.py
```

Expected:
```
56 fixtures
56 PASS
0 FAIL
engine version: 0.1.0
```

## Run Determinism Check

```bash
cd veip-core
python3 tools/replay_corpus.py > /tmp/run1.json
python3 tools/replay_corpus.py > /tmp/run2.json
sha256sum /tmp/run1.json /tmp/run2.json
```

Expected: identical SHA-256 hashes.

## Run Differential Test

```bash
cd <package-root>
python3 tools/gen_differential_corpus.py
node tools/run_differential.js
```

```json
{"total": 999511, "pass": 999511, "fail": 0}
```

## Verify Corpus Integrity

```bash
sha256sum inputs/VEIP_CANONICAL_FIXTURES_v0.3.json
```

Expected: `75cd12bb8c0560addcbdcb8e1a8127628709379e4bf462046361981f1d24339d`
