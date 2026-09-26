# Reproduce Instructions — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  

## Requirements

- Python 3.11+
- Network access to PyPI (for `openai-agents==0.22.3`)
- Dropbox access to retrieve `id:AdzSIi2kJ_kAAAAAAAA42Q` (or CDN access to download the ZIP)

## Steps

```bash
# 1. Download H1 ZIP from Dropbox (requires CDN access or owner's Dropbox credentials)
#    Expected SHA-256: abe14ef87dcdafcfb7260f525f8a9c313664ff3a10048f31591be07d18622567
wget -O VEIP_MCP_H1_PARSER_BUILD_2026-09-22_r2.zip <dropbox_download_url>
sha256sum VEIP_MCP_H1_PARSER_BUILD_2026-09-22_r2.zip
# Expected: abe14ef87dcdafcfb7260f525f8a9c313664ff3a10048f31591be07d18622567

# 2. Extract
unzip VEIP_MCP_H1_PARSER_BUILD_2026-09-22_r2.zip

# 3. Install SDK (exact version)
pip install openai-agents==0.22.3
# Verify wheel SHA-256: 41dec9e2e703db32a627bf0290f3721a6ca37405603a8cb654213356dbb8ee9d

# 4. Run baseline test suite
cd veip_mcp_h1_parser_2026-09-22
python -m pytest tests/ -v
# Expected: 25/25 PASS

# 5. Run live SDK probe
python probe/run_installed_sdk_probe.py
# Expected: {"result": "PASS", ...}

# 6. Verify determinism (parse same JSONL 3 times)
python -c "
import sys; sys.path.insert(0, '.')
from veip_trace_harness import parse_trace_jsonl, canonical_sha256
from pathlib import Path
p = Path('tests/fixtures/openai_agents_live_sdk/openai_agents_0.22.3_export.jsonl')
h1 = canonical_sha256(parse_trace_jsonl(p))
h2 = canonical_sha256(parse_trace_jsonl(p))
h3 = canonical_sha256(parse_trace_jsonl(p))
assert h1 == h2 == h3, 'Determinism FAIL'
print('Determinism PASS:', h1)
"
```

## Expected outputs (from this execution)

- Baseline: `25/25 PASS`
- Probe (any run): `{"result": "PASS", "record_count": 5, ...}`
- Determinism canonical_sha256: varies by run (timestamps differ); within-run consistency must hold
