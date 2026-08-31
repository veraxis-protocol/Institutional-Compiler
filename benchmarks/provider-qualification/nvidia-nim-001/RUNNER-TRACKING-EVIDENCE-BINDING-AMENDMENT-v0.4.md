# OIC NVIDIA Provider Qualification 001 — Runner Tracking / Evidence Binding Amendment v0.4

Status: PRE-LIVE SUCCESSOR FREEZE

No provider or model call has been made under this work order.

This successor corrects one evidence-path defect discovered by the v0.3
contract gate: `RUN_LIVE.sh` was a package-only artifact while the repository
contract attempted to hash it as a repository-root file.

The live runner is now installed and committed as:

`benchmarks/provider-qualification/nvidia-nim-001/RUN_LIVE-v0.4.sh`

The contract hashes that tracked artifact and the execution manifest binds
`PLAN-FREEZE-v0.4.json`.

No provider request semantics changed. The endpoint, model, three probes,
token ceilings, response modes, 60-second timeout, 45-second latency headroom,
four-second pacing, zero retries, decision rule, and semantic authorization
rule are unchanged.

semantic_change = false
provider_call_made = false
model_call_made = false
independent_validation_claim = false
