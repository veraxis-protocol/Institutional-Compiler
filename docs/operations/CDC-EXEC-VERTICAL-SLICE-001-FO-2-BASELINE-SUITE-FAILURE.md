# CDC-EXEC-VERTICAL-SLICE-001 FO-2 baseline suite failure

```text
observation_id = FO-2
observer = Claude Code
observation_time = 2026-08-10 before historical-guard rebind
baseline_commit = 29daa374b7e5cdc30ca7788310fbabb85f19912b
python = repository .venv / Python 3.12.2
command = python -m pytest -q
result = 1 failed, 1233 passed, 1 skipped in 80.02s
failing_test =
tests/contract/test_warrant_contract.py::test_this_work_order_added_no_source_module
```

```text
RECORD_CREATED_AFTER_OBSERVATION = TRUE
SOURCE = contemporaneous Claude return
RAW_LOG_FILE = NOT_BOUND_UNLESS_AVAILABLE
OBSERVATION_SUPERSEDED = FALSE
```

This provenance record is not the original raw log and makes no claim to be that log. The
historical-guard rebind occurred after FO-2. The rebind changes the guard's future scope; it does
not erase, supersede, reinterpret, or convert the observed FO-2 failure.

Repository chronology note: the first unverified preparation snapshot commit was created before
this provenance record was requested. That commit remains immutable. This record is persisted in
a normal child commit so the resulting provenance-complete snapshot tree preserves FO-1, FO-2,
and FO-3 without rewriting prior history.
