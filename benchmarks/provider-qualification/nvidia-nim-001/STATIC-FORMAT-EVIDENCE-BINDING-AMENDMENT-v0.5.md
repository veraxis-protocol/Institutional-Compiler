# OIC NVIDIA Provider Qualification 001 — Static Format / Evidence Binding Amendment v0.5

Status: PRE-LIVE SUCCESSOR FREEZE

The v0.4 pre-live gate passed all nine provider-qualification contract tests and
Ruff lint, but `ruff format --check` required formatting of the provider
qualification instrument.

v0.4 is preserved byte-for-byte.

v0.5 applies Ruff formatting only to the qualification instrument and advances
the tracked live runner and contract evidence binding to the resulting bytes.

No provider-request semantics changed.

Unchanged:
- endpoint
- model
- three-probe plan
- prompts
- response formats
- temperature
- token ceilings
- 60-second provider timeout
- four-second inter-probe pacing
- zero retries
- 45-second latency-headroom threshold
- qualification decision rule
- semantic-successor authorization rule

No provider or model call has been made under this work order.

semantic_change = false
format_only_change = true
provider_call_made = false
model_call_made = false
independent_validation_claim = false
