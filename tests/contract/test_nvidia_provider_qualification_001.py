"""Contract tests for OIC-NVIDIA-PROVIDER-QUALIFICATION-001.

The provider instrument imports urllib/ssl. Repository tests may monkeypatch socket symbols,
so dynamic instrument checks execute in a clean subprocess rather than importing the
instrument into the pytest interpreter. This is test isolation only; no provider request is
made by these contracts.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path("scripts/qualify_nvidia_provider_001.py")
PLAN = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-v0.1.json")
FREEZE_V1 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.1.json")
FREEZE_V2 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.2.json")
FREEZE_V3 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.3.json")
FREEZE_V4 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.4.json")
FREEZE_V5 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.5.json")
FREEZE_V6 = Path("benchmarks/provider-qualification/nvidia-nim-001/PLAN-FREEZE-v0.6.json")
RUNNER = Path("benchmarks/provider-qualification/nvidia-nim-001/RUN_LIVE-v0.6.sh")
BASE_SHA = "c4a87eb8483c3bd965612b601399463e005bd73e"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_python(code: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _instrument_eval(expression: str) -> object:
    code = f"""
import importlib.util
import json
import sys
from pathlib import Path
path = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location('_oic_nvidia_provider_qualification_001', path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print(json.dumps({expression}))
"""
    result = _clean_python(code)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_plan_and_successor_freeze_hashes_match() -> None:
    plan_bytes = (ROOT / PLAN).read_bytes()
    freeze_v1 = json.loads((ROOT / FREEZE_V1).read_text(encoding="utf-8"))
    freeze_v2 = json.loads((ROOT / FREEZE_V2).read_text(encoding="utf-8"))
    freeze_v3 = json.loads((ROOT / FREEZE_V3).read_text(encoding="utf-8"))
    freeze_v4 = json.loads((ROOT / FREEZE_V4).read_text(encoding="utf-8"))
    freeze_v5 = json.loads((ROOT / FREEZE_V5).read_text(encoding="utf-8"))
    freeze_v6 = json.loads((ROOT / FREEZE_V6).read_text(encoding="utf-8"))

    assert hashlib.sha256(plan_bytes).hexdigest() == freeze_v1["plan_sha256"]
    assert freeze_v2["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v3["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v4["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v5["plan_sha256"] == freeze_v1["plan_sha256"]
    assert freeze_v6["plan_sha256"] == freeze_v1["plan_sha256"]
    assert (
        freeze_v1["instrument_sha256"]
        == "144393892d05fe4d2eb2d70f110164023c36e3d69e393c874227a432b2bb426f"
    )
    assert freeze_v2["instrument_sha256"] == freeze_v1["instrument_sha256"]
    assert freeze_v3["instrument_sha256"] == freeze_v1["instrument_sha256"]
    assert freeze_v4["instrument_sha256"] == freeze_v1["instrument_sha256"]
    assert freeze_v5["prior_instrument_sha256"] == freeze_v4["instrument_sha256"]
    assert freeze_v6["instrument_sha256"] == freeze_v5["instrument_sha256"]
    assert _sha(ROOT / SCRIPT) == freeze_v6["instrument_sha256"]
    assert _sha(Path(__file__)) == freeze_v6["contract_test_sha256"]
    assert _sha(ROOT / RUNNER) == freeze_v6["live_runner_sha256"]
    assert (
        freeze_v1["base_sha"]
        == freeze_v2["base_sha"]
        == freeze_v3["base_sha"]
        == freeze_v4["base_sha"]
        == freeze_v5["base_sha"]
        == freeze_v6["base_sha"]
        == BASE_SHA
    )
    assert freeze_v2["supersedes_freeze_sha256"] == _sha(ROOT / FREEZE_V1)
    assert freeze_v3["supersedes_freeze_sha256"] == _sha(ROOT / FREEZE_V2)
    assert freeze_v4["supersedes_freeze_sha256"] == _sha(ROOT / FREEZE_V3)
    assert freeze_v5["supersedes_freeze_sha256"] == _sha(ROOT / FREEZE_V4)
    assert freeze_v6["supersedes_freeze_sha256"] == _sha(ROOT / FREEZE_V5)
    assert freeze_v6["semantic_change"] is False
    assert freeze_v6["provider_call_made"] is False
    assert freeze_v6["contract_logic_only_change"] is True


def test_exact_provider_path_is_frozen() -> None:
    plan = json.loads((ROOT / PLAN).read_text(encoding="utf-8"))
    assert plan["provider"] == {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "timeout_seconds": 60.0,
    }
    assert plan["planned_probe_count"] == 3
    assert plan["retries"] == 0
    assert plan["pacing_seconds"] == 4.0


def test_probe_three_uses_production_token_reservation() -> None:
    plan = json.loads((ROOT / PLAN).read_text(encoding="utf-8"))
    third = plan["probes"][2]
    assert third["probe_id"] == "PRODUCTION_TOKEN_RESERVATION"
    assert third["response_format"] == {"type": "json_object"}
    assert third["max_tokens"] == 4096


def test_offline_plan_matches_instrument_in_clean_process() -> None:
    plan = json.loads((ROOT / PLAN).read_text(encoding="utf-8"))
    observed = _instrument_eval(
        "{'base_sha': module.BASE_SHA, "
        "'probes': [item.to_plan_json() for item in module.PROBES], "
        "'planned': module.PLANNED_PROBES, "
        "'timeout': module.TIMEOUT_SECONDS, "
        "'headroom': module.LATENCY_HEADROOM_SECONDS}"
    )
    assert observed == {
        "base_sha": BASE_SHA,
        "probes": plan["probes"],
        "planned": 3,
        "timeout": 60.0,
        "headroom": 45.0,
    }


def test_offline_cli_constructs_no_provider() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.pop("NVIDIA_API_KEY", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected = "offline preflight only; no provider was constructed and no request was made"
    assert expected in result.stdout


def test_qualification_requires_three_clean_probes() -> None:
    result = _instrument_eval(
        "module.decide(["
        "{'outcome':'ACCEPTED','elapsed_seconds':1.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':2.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':3.0}])"
    )
    assert result == "QUALIFIED"

    failed = _instrument_eval(
        "module.decide(["
        "{'outcome':'ACCEPTED','elapsed_seconds':1.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':2.0},"
        "{'outcome':'PROVIDER_ERROR','elapsed_seconds':60.0}])"
    )
    assert failed == "NOT_QUALIFIED"


def test_latency_headroom_is_fail_closed() -> None:
    result = _instrument_eval(
        "module.decide(["
        "{'outcome':'ACCEPTED','elapsed_seconds':1.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':2.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':45.001}])"
    )
    assert result == "DEGRADED"


def test_missing_probe_is_not_qualified() -> None:
    result = _instrument_eval(
        "module.decide(["
        "{'outcome':'ACCEPTED','elapsed_seconds':1.0},"
        "{'outcome':'ACCEPTED','elapsed_seconds':2.0}])"
    )
    assert result == "NOT_QUALIFIED"


def test_receipt_is_local_evidence() -> None:
    observed = _instrument_eval(
        "{'receipt': str(module.RECEIPT_PATH), 'work_order': module.WORK_ORDER}"
    )
    assert ".local/provider-qualification-receipts" in observed["receipt"]
    assert observed["work_order"] == "OIC-NVIDIA-PROVIDER-QUALIFICATION-001"
