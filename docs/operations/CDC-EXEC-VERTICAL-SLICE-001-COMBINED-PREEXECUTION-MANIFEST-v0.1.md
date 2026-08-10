# CDC-EXEC-VERTICAL-SLICE-001 combined pre-execution manifest v0.1

## Repository construction

```text
verified_core_commit = 82f58d67de7177968e48454ef8044de83f964918
verified_core_tree = c66d9b5d398ff40e03cb15020c99b6b7caf4996f
claude_integration_commit = 14d0058e2693acbe6b61b2a700fba38a71b15e3b
claude_integration_tree = 02b243f9e0822e4b26c883d00785a442b14cb313
claude_integration_parent = 617370e53ee72910408ef3f5d34785f430085ce1
combined_implementation_commit = 58209f1f314edfb69e107de47291e370c70ccd82
combined_implementation_tree = 2c6ff2ae200115c038b05d60780a364668905622
combined_manifest_persistence_commit = SELF_EXCLUDED; reported with the frozen-head return
```

The Claude delta applied cleanly as exactly 12 added files, zero modified files, and zero changes to Codex-owned core files. The combined implementation commit is the normal cherry-pick child of the verified core. The later manifest-persistence commit cannot contain its own Git identity without an impossible self-reference; its exact commit and tree are therefore reported externally with the frozen return.

```text
src/oic/cdc_slice.py_blob = 4a78c648c07d64189838b788c3271e8fff11b883
tests/unit/test_cdc_slice.py_blob = d17c849f06a8427e972ee957e81a46ae803f5de5
core_blob_preserved = TRUE
core_unit_test_blob_preserved = TRUE
```

## Contract and environment

```text
owner_contract_sha256 = 93fa0cf467aa93df67079b24066bf3aeb40c70df768621ec6b8f6a8ace90300e
semantic_review_notes_sha256 = ac8e8c2488c35966508e824b665f0730d471835d15af5422ed5964729a138b41
candidate_001_manifest_sha256 = 29e05cd70e2708317867720931640332fa241941f19812ad02b6e13ba3dec46b
candidate_002_manifest_sha256 = ed21575a4a3037b3bd66c3a0f6db350f3b45c21d94e37e131bfde83e8bcb4520
python = Python 3.12.13
pytest = 8.4.2
PYTEST_INFRASTRUCTURE = RESOLVED_BY_VERIFIED_ENVIRONMENT_SUBSTITUTION
```

The combined verification used accepted Candidate 001. Its installed core source is blob-identical to the combined head; the combined-only integration consists of tests and non-result-bearing scripts and was loaded from this worktree.

## Immutable external governance coordinates

All six bytes were retrieved read-only from `inventor1975/ZTL` at their pinned commits and reproduced the designated SHA-256 values. They were not copied into runtime logic.

```text
semantic_oracle_commit = 2ce3bdab0acc6a0411f63a20e32164c1f0c8d4a9
semantic_oracle_sha256 = 392f298197632451df0bfa7379e0e5a8a7ef1fb440fda4a60ea2f4f8af683390
adjudication_protocol_commit = ff78860882748d3f03754f240e7a5c7f1873b174
adjudication_protocol_sha256 = 5884c984833b0495ea4d7fc6265a7440797fc2ab3d3a9641f505ebc637121cbf
merge_seam_checklist_commit = ff78860882748d3f03754f240e7a5c7f1873b174
merge_seam_checklist_sha256 = 48ea48fc41b6756de9cccf145bb4e89a16cc74ee8e51fabfc1715864bdf41206
fo_binding_commit = 0697ba01e8dc32d2c83366aae4da06a9d116b712
fo_binding_sha256 = 9032e5dec03c27678e3e77fa484613bd8354462db7f6cbaa98b9bd9398628561
adjudication_template_commit = 0697ba01e8dc32d2c83366aae4da06a9d116b712
adjudication_template_sha256 = 98724f81602570718420558cb78f211cbf881d35cf3f941602526122c217a076
merge_result_template_commit = 0697ba01e8dc32d2c83366aae4da06a9d116b712
merge_result_template_sha256 = a1e8aab67629714edab61b342d4c7371e28688e4d5e937c555600ea325bfed3c
GOVERNANCE_BYTES_LOCAL = VERIFIED_READ_ONLY_FROM_PINNED_REMOTE_COORDINATES
RUNTIME_IMPORT_DEPENDENCY_ON_ORACLE = FALSE
RUNTIME_WRITE_PATH_TO_ORACLE = FALSE
ORACLE_RESULT_PARAMETERIZATION = FALSE
```

## Preserved first observations

```text
FO-1_sha256 = fe6aeee35c5aa097812e88128ca1f88bc5f5616171eaefc90a0ca91451ba644b
FO-2_sha256 = 9c1a3c56a03d0608c837a6ed0ec43e1b81d1caa25004b624c4151ff4c9c483f9
FO-3_sha256 = 5c4fd18587ef75d408a7d818c761ae5cbc2490be9ec0df81abe8f9602e2dc927
FO_integrity = PASS
```

No failure record was erased, relabeled, or replaced.

## Static and structural verification

```text
ruff_check = PASS
strict_mypy = PASS; 41 source files
git_diff_check = PASS
bash_syntax = PASS
ruff_format_check = PRE_EXISTING_EXCEPTION; 4 files would be reformatted
structural_tests = 13 passed
S_cases_defined = 8
S_cases_executed = 0
adversarial_probes_defined = 7
adversarial_probes_executed = 0
mission_executions = 0
adversarial_denominator = 0
run_plan_generation = PASS; RUN_PLAN_ONLY
evidence_skeleton = PASS; 17 sections, 16 populated
renderer_placeholder_smoke = PASS
observation_schema_validation = PASS
adjudication_handoff_serialization = PASS
execution_interlock_refusal = PASS
```

The format-only exception is unchanged from the verified core and covers `src/oic/cdc_slice.py`, `tests/contract/test_canada_acquisition_freeze.py`, `tests/contract/test_canada_rights_resolution_dossier.py`, and `tests/contract/test_warrant_contract.py`. Those verified historical/core files were not reformatted.

## Full software suite

```text
collected = 1258
passed = 1257
failed = 0
skipped = 1
errors = 0
duration = 50.71s
```

The skip remains `tests/contract/test_canada_acquisition_preflight.py:574`, where gitignored local receipts are intentionally unavailable in CI.

## Observation, adjudication, and dimensional typing

```text
RAW_OBSERVATION_SCHEMA_HAS_ADJUDICATION_FIELD = FALSE
ADJUDICATION_HANDOFF_COMPUTES_VERDICT = FALSE
ORACLE_REFERENCED_BY_RUNTIME_FIXTURE_AS_EXPECTED_RESULT = FALSE
EXPECTED_OBSERVED_RESULT_IN_FIXTURE = FALSE
requested_disposition_ESCALATE_is_institutional = TRUE
gate_decision_ESCALATE_is_operational = TRUE
the_two_fields_or_types_collapsed = FALSE
```

`expected_oracle_case_ref` remains a permitted external reference. No expected observed result is carried in a fixture.

## Interlock and authority ceiling

```text
PYTEST_INFRASTRUCTURE = RESOLVED
EXECUTION_CLEARANCE_REF = ABSENT
RESULT_BEARING_ENTRYPOINT = BLOCKED
EXECUTION_NOT_AUTHORIZED
mission_executions = 0
adversarial_executions = 0
adversarial_denominator = 0
MERGED_INTEGRATION_VERIFIED = FALSE
SEMANTIC_SEAM_VERIFIED = FALSE
SEMANTIC_SLICE_ACCEPTANCE = NOT_YET_MEASURED
GATE_SAR_05 = NOT_CLOSED
```

This manifest performs no semantic-seam adjudication and does not fill either frozen adjudication template.
