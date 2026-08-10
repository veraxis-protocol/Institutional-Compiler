# CDC-EXEC-VERTICAL-SLICE-001 first test failure

Classification: `NON_RESULT_BEARING_CONTRACT_TEST_INFRASTRUCTURE_FAILURE`

Exact attempted command:

```text
python -m pytest tests/unit/test_cdc_slice.py -q
```

Observed shell result:

```text
/bin/bash: line 1: 24999 Segmentation fault: 11  python -m pytest tests/unit/test_cdc_slice.py -q
```

Pytest produced no test-result summary. Therefore collected, passed, failed, and skipped counts
are `UNMEASURED`; this record is not evidence that any contract test passed or failed. No mission
execution was attempted. The command has not been rerun.

The first Ruff pass then reported four preparation defects: `UP035` for the `Mapping` import,
`S101` for a runtime assertion, and two `E501` line-length findings. These were preserved here
before mechanical remediation; none was a mission result or semantic test outcome.

The first strict-mypy pass reported one preparation defect at `cdc_slice.py:102`: unsupported
right operand type `object` for membership testing. It was preserved here before narrowing the
accepted stale-candidate collection types.

The next Ruff pass reported `UP038` on that type guard. It was preserved here before the
mechanically equivalent Python 3.12 union form was applied.
