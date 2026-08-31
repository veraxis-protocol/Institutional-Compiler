# OIC NVIDIA Provider Qualification 002
## Static Format / Evidence Binding Amendment v0.3

Status: PRE-LIVE SUCCESSOR FREEZE

v0.2 passed:

- offline provider qualification preflight;
- all six targeted contract tests;
- Ruff lint.

Execution stopped before mypy, full locked suite, verify/falsify,
commit, push, remediation acknowledgement, or any provider/model call
because `ruff format --check` required formatting of the instrument
and contract test.

v0.3 performs only:

1. formatting using the repository's locked Ruff;
2. advancement of current evidence binding from v0.2 to v0.3;
3. preservation of the exact historical v0.2 instrument/test digests.

The following remain byte-preserved:

- PLAN-v0.1.json;
- PREREGISTRATION.md;
- PLAN-FREEZE-v0.1.json;
- PLAN-FREEZE-v0.2.json.

No provider endpoint, model, probe, output contract, timeout,
latency threshold, pacing, retry policy, remediation prerequisite,
semantic-successor target, authorization rule, or claim ceiling changed.

semantic_change = false
static_format_and_evidence_binding_only_change = true
provider_call_made = false
model_call_made = false
live_run_executed = false
remediation_marker_created = false
independent_validation_claim = false
