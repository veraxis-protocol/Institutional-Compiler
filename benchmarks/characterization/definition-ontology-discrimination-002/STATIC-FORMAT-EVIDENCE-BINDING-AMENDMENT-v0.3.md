# OIC Definition Ontology Discrimination 002
## Static Format / Evidence Binding Amendment v0.3

Status: PRE-LIVE SUCCESSOR FREEZE

v0.2 passed:

- offline experiment preflight;
- all six targeted contract tests;
- Ruff lint.

Execution stopped before mypy, the full suite, verify/falsify,
commit, push, or any provider/model call because `ruff format --check`
reported that the instrument required formatting.

v0.3 performs only:

1. Ruff formatting of the instrument/test;
2. advancement of the current freeze binding from v0.2 to v0.3;
3. contract assertions preserving the historical v0.2 instrument digest.

The following remain byte-preserved:

- PLAN-v0.1.json;
- PREREGISTRATION.md;
- PLAN-FREEZE-v0.1.json;
- PLAN-FREEZE-v0.2.json.

No semantic hypothesis, specimen, arm, prompt, ordering rule,
adjudicability threshold, decision rule, provider prerequisite,
pacing rule, retry policy, production code, canonicalization,
or Institutional IR behavior changed.

semantic_change = false
static_format_and_evidence_binding_only_change = true
provider_call_made = false
model_call_made = false
live_run_executed = false
independent_validation_claim = false
