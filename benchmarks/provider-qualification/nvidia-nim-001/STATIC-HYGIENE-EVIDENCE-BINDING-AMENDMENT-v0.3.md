# NVIDIA Provider Qualification 001 — Static Hygiene and Evidence Binding Amendment v0.3

Status: PRE-LIVE SUCCESSOR FREEZE.

The provider qualification plan and live provider instrument remain unchanged from v0.1.
No provider call has been made. No semantic hypothesis is introduced.

v0.3 makes two non-semantic corrections before first live execution:

1. the subprocess test helper return annotation is narrowed from `Any` to `object` to satisfy Ruff ANN401;
2. the execution manifest binds the latest pre-live successor freeze (`PLAN-FREEZE-v0.3.json`) rather than the original v0.1 freeze.

Unchanged:
- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- timeout: 60 seconds
- probes: 3
- retries: 0
- pacing: 4 seconds
- qualification latency headroom: 45 seconds
- instrument sha256: `144393892d05fe4d2eb2d70f110164023c36e3d69e393c874227a432b2bb426f`
- plan sha256: `a72370f16e93048466ecc25d9d03b8d85d43e055b1f8d2d467750116c779c02e`
- provider_call_made: FALSE
- semantic_change: FALSE
