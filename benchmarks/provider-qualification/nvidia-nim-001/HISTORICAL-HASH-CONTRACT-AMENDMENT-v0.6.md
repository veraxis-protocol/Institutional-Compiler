# OIC NVIDIA Provider Qualification 001 — Historical Hash Contract Amendment v0.6

Status: PRE-LIVE SUCCESSOR FREEZE

The v0.5 instrument was intentionally changed only by Ruff formatting and was
correctly assigned a new instrument SHA-256.

The v0.5 contract nevertheless retained one stale assertion requiring the
current instrument bytes to equal the original v0.1 instrument hash.

That assertion is logically incompatible with an explicitly recorded
format-only successor.

v0.6 repairs the contract so:

- the v0.1 instrument hash remains explicitly frozen as historical evidence;
- v0.2-v0.4 continue chaining the original instrument hash;
- v0.5 records the authorized format-only transition;
- v0.6 requires current instrument bytes to match the v0.5/v0.6 instrument hash;
- the live runner and execution evidence bind v0.6.

No provider-request semantics changed.
No qualification decision rule changed.
No provider or model call has been made.

semantic_change = false
contract_logic_only_change = true
provider_call_made = false
model_call_made = false
independent_validation_claim = false
