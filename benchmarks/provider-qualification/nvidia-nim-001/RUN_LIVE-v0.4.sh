#!/bin/bash
set -euo pipefail

REPO="$HOME/veraxis/Institutional-Compiler"
BRANCH="oic-nvidia-provider-qualification-001"
LOCKED_PY="/tmp/oic-definition-ontology-001-venv/bin/python"
RECEIPT=".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-001.json"
COPY="$HOME/Desktop/OIC-NVIDIA-PROVIDER-QUALIFICATION-001.json"
LOG="$HOME/Desktop/OIC-NVIDIA-PROVIDER-QUALIFICATION-001-LIVE.log"
MANIFEST="$HOME/Desktop/OIC-NVIDIA-PROVIDER-QUALIFICATION-001-EXECUTION-MANIFEST.json"

cd "$REPO"

echo "=== PROVIDER QUALIFICATION PRECONDITIONS ==="
test "$(git branch --show-current)" = "$BRANCH"
test -z "$(git status --porcelain --untracked-files=no)"
test -x "$LOCKED_PY"

if [ -e "$RECEIPT" ] || [ -e "$COPY" ]; then
  echo "STOP: provider qualification receipt already exists"
  ls -lh "$RECEIPT" "$COPY" 2>/dev/null || true
  exit 2
fi

export PYTHONPATH="$PWD/src"
PY="$LOCKED_PY"

"$PY" -u scripts/qualify_nvidia_provider_001.py

export NVIDIA_API_KEY="$(/usr/bin/textutil -convert txt -stdout "$HOME/Desktop/NVIDIA_API_KEY.rtf" 2>/dev/null | python3 -c 'import sys,re; s=sys.stdin.read(); m=re.search(r"nvapi-[A-Za-z0-9_-]+",s); print(m.group(0) if m else "")')"
if [ -z "$NVIDIA_API_KEY" ]; then
  echo "STOP: NVIDIA_API_KEY not found"
  exit 2
fi

export SSL_CERT_FILE="$($PY -c 'import certifi; print(certifi.where())')"

echo
echo "=== OIC NVIDIA PROVIDER QUALIFICATION 001 — LIVE ==="
echo "probes: 3"
echo "retries: 0"
echo "pacing: 4 seconds"
echo "semantic hypothesis: NONE"
echo

set +e
"$PY" -u scripts/qualify_nvidia_provider_001.py --live 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

unset NVIDIA_API_KEY
unset SSL_CERT_FILE

echo
echo "live exit code: $STATUS"
if [ "$STATUS" -ne 0 ]; then
  echo "QUALIFICATION DID NOT COMPLETE — DO NOT RERUN WITHOUT REVIEW"
  exit "$STATUS"
fi

if [ ! -f "$RECEIPT" ]; then
  echo "STOP: qualification returned success but receipt is absent"
  exit 2
fi

cp "$RECEIPT" "$COPY"

echo
echo "=== EXECUTION MANIFEST ==="
"$PY" - <<'PY'
from pathlib import Path
import hashlib
import json
import subprocess

root = Path.cwd()
receipt = root / ".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-001.json"
plan = root / "benchmarks/provider-qualification/nvidia-nim-001/PLAN-v0.1.json"
freeze = root / "benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.4.json"
instrument = root / "scripts/qualify_nvidia_provider_001.py"
log = Path.home() / "Desktop/OIC-NVIDIA-PROVIDER-QUALIFICATION-001-LIVE.log"
out = Path.home() / "Desktop/OIC-NVIDIA-PROVIDER-QUALIFICATION-001-EXECUTION-MANIFEST.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
manifest = {
    "work_order": "OIC-NVIDIA-PROVIDER-QUALIFICATION-001",
    "execution_commit_sha": subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip(),
    "receipt_sha256": sha(receipt),
    "plan_sha256": sha(plan),
    "freeze_sha256": sha(freeze),
    "instrument_sha256": sha(instrument),
    "live_log_sha256": sha(log),
    "disposition": receipt_data["disposition"],
    "semantic_successor_authorized": receipt_data["semantic_successor_authorized"],
    "semantic_hypothesis": None,
    "independent_validation_claim": False,
}
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2, sort_keys=True))
PY

echo
echo "=== FINAL ARTIFACT HASHES ==="
shasum -a 256 "$RECEIPT" "$COPY" "$MANIFEST" "$LOG"

echo
echo "=== QUALIFICATION RESULT ==="
"$PY" - <<'PY'
import json
from pathlib import Path
p = Path(".local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-001.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("disposition:", d["disposition"])
print("semantic successor authorized:", d["semantic_successor_authorized"])
for a in d["attempts"]:
    print(a["ordinal"], a["probe_id"], a["outcome"], a["elapsed_seconds"])
PY

echo
echo "PROVIDER QUALIFICATION COMPLETE — DO NOT RERUN THIS WORK ORDER"
