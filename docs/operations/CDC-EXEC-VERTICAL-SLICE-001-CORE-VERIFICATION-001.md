# CDC-EXEC-VERTICAL-SLICE-001 core verification 001

Environment:

```text
environment_id = CDC-CORE-TEST-ENVIRONMENT-CANDIDATE-001
python = .venv-cdc-recovery-001/bin/python
python_build = Python 3.12.13 (main, Mar  3 2026, 15:03:16) [Clang 21.1.4 ]
environment_manifest_sha256 = 29e05cd70e2708317867720931640332fa241941f19812ad02b6e13ba3dec46b
```

The original forensic `.venv` remains preserved and failed. It was not repaired or used for these
successor verification observations.

## Preserved predecessor observation

The first clean-environment full-suite observation remains:

```text
collected = 1239
passed = 1236
failed = 2
skipped = 1
xfailed = 0
errors = 0
```

The two failures were the historical Canada guards later rebound under Owner Corrective Directive
005. This predecessor observation is not erased or normalized by the successor runs.

## Corrected verification sequence

```text
modified_canada_guards: collected=2 passed=2 failed=0 skipped=0 xfailed=0 errors=0
historical_guard_proofs: collected=6 passed=6 failed=0 skipped=0 xfailed=0 errors=0; deselected=79
slice_tests: collected=10 passed=10 failed=0 skipped=0 xfailed=0 errors=0
applicable_contract_tests: collected=667 passed=667 failed=0 skipped=0 xfailed=0 errors=0
```

## Full-suite successor run 1

```text
collected = 1245
passed = 1244
failed = 0
skipped = 1
xfailed = 0
errors = 0
duration = 58.02s
```

## Environment and source identity before reproduction

Immediately before run 2:

```text
environment_manifest_sha256 = 29e05cd70e2708317867720931640332fa241941f19812ad02b6e13ba3dec46b
guard_source_diff_sha256 = de61376f5d6d9271cf1b4a07e7de0e6605a18de3d80437709fce9ec32779c30f
```

No source or environment modification occurred between run 1 and run 2. The guard-source diff hash
was recomputed after run 2 and remained identical.

## Full-suite successor run 2

```text
collected = 1245
passed = 1244
failed = 0
skipped = 1
xfailed = 0
errors = 0
duration = 86.29s
```

The single skipped test remained explicitly reported:

```text
tests/contract/test_canada_acquisition_preflight.py:574
gitignored local receipts are intentionally unavailable in CI
```

## Closure boundary

```text
CORE_TEST_SURFACE_EXECUTED = TRUE
CORE_VERIFICATION = ESTABLISHED_AT_CDC_CORE_TEST_ENVIRONMENT_CANDIDATE_001
PYTEST_INFRASTRUCTURE_BLOCKER = CLOSED_BY_ENVIRONMENT_SUBSTITUTION
FORENSIC_ENVIRONMENT = PRESERVED_FAILED
RECOVERY_ENVIRONMENT = VERIFIED_FOR_CORE_TEST_EXECUTION
RESULT_BEARING_MISSION_EXECUTION = NOT_AUTHORIZED
```

This record establishes only the core verification gate. It does not authorize mission execution,
adversarial execution, CDC claims, VEIP conformance claims, Gate SAR-05 closure, publication, or
transmission.
