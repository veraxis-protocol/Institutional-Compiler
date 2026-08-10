# CDC-EXEC-VERTICAL-SLICE-001 pytest diagnosis 001

Status: `DIAGNOSTIC_OBSERVATION — NOT REMEDIATION`

Snapshot under diagnosis:

```text
commit = 617370e53ee72910408ef3f5d34785f430085ce1
tree = 53557fa24d308a3f7e1c33dbf8adb44bf5d87072
baseline = 29daa374b7e5cdc30ca7788310fbabb85f19912b
```

## D-01 — interpreter identity

Command:

```text
.venv/bin/python -VV
```

Exit `0`; output:

```text
Python 3.12.2 | packaged by conda-forge | (main, Feb 16 2024, 21:00:12) [Clang 16.0.6 ]
```

Command:

```text
.venv/bin/python -c "import sys; print(sys.executable); print(sys.version)"
```

Exit `0`; output:

```text
/Users/arkadiymiteiko/Downloads/open-institutional-compiler/.venv/bin/python
3.12.2 | packaged by conda-forge | (main, Feb 16 2024, 21:00:12) [Clang 16.0.6 ]
```

## D-02 — basic pytest import

Command:

```text
.venv/bin/python -c "import pytest; print(pytest.__version__)"
```

Exit `0`; output:

```text
8.4.2
```

Classification `SEGFAULT_DURING_PYTEST_IMPORT` does not apply.

## D-03 — environment integrity

`.venv/bin/python -m pip check` exited `0`. Aside from the sandbox cache warning, its result was:

```text
No broken requirements found.
```

`.venv/bin/python -m pip freeze` exited `0` and reported:

```text
arrow==1.4.0
attrs==26.1.0
boolean.py==5.0
build==1.5.0
cfgv==3.5.0
chardet==5.2.0
click==8.4.2
coverage==7.15.2
cyclonedx-bom==7.3.1
cyclonedx-python-lib==11.11.0
defusedxml==0.7.1
distlib==0.4.3
filelock==3.32.0
fqdn==1.5.1
identify==2.6.19
idna==3.18
iniconfig==2.3.0
isoduration==20.11.0
jsonpointer==3.1.1
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
lark==1.3.1
librt==0.13.0
license-expression==30.4.4
lxml==6.1.1
mypy==1.20.2
mypy_extensions==1.1.0
nodeenv==1.10.0
-e git+https://github.com/veraxis-protocol/Institutional-Compiler.git@617370e53ee72910408ef3f5d34785f430085ce1#egg=oic
packageurl-python==0.17.6
packaging==25.0
pathspec==1.1.1
pip-licenses==5.5.5
pip-requirements-parser==32.0.1
pip-tools==7.6.0
platformdirs==4.11.0
pluggy==1.6.0
pre_commit==4.6.1
prettytable==3.18.0
py-serializable==2.1.0
Pygments==2.20.0
pyparsing==3.3.2
pyproject_hooks==1.2.0
pytest==8.4.2
pytest-cov==6.3.0
python-dateutil==2.9.0.post0
python-discovery==1.5.0
PyYAML==6.0.3
referencing==0.37.0
rfc3339-validator==0.1.4
rfc3986-validator==0.1.1
rfc3987-syntax==1.1.0
rpds-py==2026.6.3
ruff==0.12.12
setuptools==83.0.0
six==1.17.0
sortedcontainers==2.4.0
types-jsonschema==4.26.0.20260518
typing_extensions==4.16.0
tzdata==2026.3
uri-template==1.3.0
virtualenv==21.7.0
wcwidth==0.8.2
webcolors==25.10.0
wheel==0.47.0
```

## D-04 — faulthandler collection

Command:

```text
PYTHONFAULTHANDLER=1 .venv/bin/python -X faulthandler -m pytest --collect-only -q
```

Exit `139`. The recorded Python stack was:

```text
Fatal Python error: Segmentation fault

Current thread 0x00007ff85a74ea00 (most recent call first):
  File "<frozen importlib._bootstrap>", line 488 in _call_with_frames_removed
  File "<frozen importlib._bootstrap_external>", line 1289 in create_module
  File "<frozen importlib._bootstrap>", line 813 in module_from_spec
  File "<frozen importlib._bootstrap>", line 921 in _load_unlocked
  File "<frozen importlib._bootstrap>", line 1331 in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 1360 in _find_and_load
  File ".venv/lib/python3.12/site-packages/_pytest/capture.py", line 95 in _readline_workaround
  File ".venv/lib/python3.12/site-packages/_pytest/capture.py", line 161 in pytest_load_initial_conftests
  File ".venv/lib/python3.12/site-packages/pluggy/_callers.py", line 116 in _multicall
  File ".venv/lib/python3.12/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File ".venv/lib/python3.12/site-packages/pluggy/_hooks.py", line 512 in __call__
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 1431 in _preparse
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 1527 in parse
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 1146 in pytest_cmdline_parse
  File ".venv/lib/python3.12/site-packages/pluggy/_callers.py", line 121 in _multicall
  File ".venv/lib/python3.12/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File ".venv/lib/python3.12/site-packages/pluggy/_hooks.py", line 512 in __call__
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 342 in _prepareconfig
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 156 in main
  File ".venv/lib/python3.12/site-packages/_pytest/config/__init__.py", line 201 in console_main
  File ".venv/lib/python3.12/site-packages/pytest/__main__.py", line 9 in <module>
  File "<frozen runpy>", line 88 in _run_code
  File "<frozen runpy>", line 198 in _run_module_as_main
```

Absolute path prefixes are shortened above only for readability; the observed boundary and line
numbers are preserved. The raw tool return carried the full repository-prefixed paths.

## D-05 — third-party plugin autoload disabled

Command:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONFAULTHANDLER=1 .venv/bin/python -X faulthandler -m pytest --collect-only -q
```

Exit `139`, with the same `_pytest.capture._readline_workaround` stack boundary as D-04.
Disabling third-party plugin autoload is not sufficient to explain or avoid the failure.

## D-06 — pytest11 entry points

The installed entry-point enumeration exited `0` and returned exactly:

```text
pytest_cov|pytest_cov.plugin|pytest-cov|6.3.0
```

No plugin was loaded by this enumeration.

## D-07 — frozen-baseline control

A detached temporary worktree was created at exact baseline
`29daa374b7e5cdc30ca7788310fbabb85f19912b`. Using the same repository `.venv` interpreter, the
faulthandler collection command exited `139` with the same
`_pytest.capture._readline_workaround` stack boundary. The baseline contained no slice files.

This establishes that the failure is reproducible on the frozen pre-slice tree. It does not
establish the native root cause.

## D-08 — clean reconstructed environment

Not executed. D-07 was sufficient to support the authorized diagnostic category without mutating,
replacing, or comparing package installations. A clean comparator may be separately used if an
owner later requires deeper localization.

## Diagnostic disposition

```text
PYTEST_DIAGNOSIS = BASELINE_REPRODUCIBLE_FAILURE
PLUGIN_AUTOLOAD_SUFFICIENT_EXPLANATION = FALSE
SLICE_IMPORT_TRIGGER = NOT_SUPPORTED
NATIVE_ROOT_CAUSE = NOT_ESTABLISHED
PACKAGES_MODIFIED = 0
SOURCE_WORKAROUNDS = 0
RESULT_BEARING_EXECUTION_AUTHORIZED = FALSE
```

## Work Order 004 continuation

### Preserved failing environment

```text
python = /Users/arkadiymiteiko/Downloads/open-institutional-compiler/.venv/bin/python
python_build = Python 3.12.2 | packaged by conda-forge | Clang 16.0.6
platform = macOS-13.7.8-x86_64-i386-64bit
pytest = 8.4.2
pytest11 = pytest_cov|pytest_cov.plugin|pytest-cov|6.3.0
pip_check = No broken requirements found.
```

Capture-time environment whitelist:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
LC_CTYPE=C.UTF-8
TERM=dumb
VIRTUAL_ENV=ABSENT
PYTHONHOME=ABSENT
PYTHONPATH=ABSENT
CONDA_PREFIX=/opt/anaconda3
CONDA_DEFAULT_ENV=base
CONDA_SHLVL=1
CONDA_EXE=/opt/anaconda3/bin/conda
_CE_M=
_CE_CONDA=
DYLD_*=ABSENT
```

`PATH` was recorded by the diagnostic return and included system Python 3.13, the Codex runtime,
and `/opt/anaconda3`; every command here nevertheless used the exact absolute interpreter shown
above. No complete inherited environment or unrelated variable was captured.

### Capture matrix — slice snapshot

Every command had empty stdout, exit `139`, and stderr equal to the D-04 faulthandler stack above,
ending at `_pytest.capture._readline_workaround` while importing the native `readline` module:

```text
python -X faulthandler -m pytest --collect-only -q --capture=fd
python -X faulthandler -m pytest --collect-only -q --capture=sys
python -X faulthandler -m pytest --collect-only -q --capture=tee-sys
python -X faulthandler -m pytest --collect-only -q --capture=no
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -X faulthandler -m pytest --collect-only -q --capture=fd
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -X faulthandler -m pytest --collect-only -q --capture=no
```

The two import controls both exited `0`:

```text
python -X faulthandler -c "import pytest; print(pytest.__version__)"
stdout = 8.4.2
stderr = EMPTY

python -X faulthandler -c "import _pytest.capture; print('capture-import-ok')"
stdout = capture-import-ok
stderr = EMPTY
```

A final direct discriminator confirmed the imported native boundary:

```text
.venv/bin/python -X faulthandler -c "import readline; print(readline.__file__)"
exit = 139
stdout = EMPTY
stderr = Fatal Python error: Segmentation fault; importlib create_module stack

.venv-cdc-recovery-001/bin/python -X faulthandler -c "import readline; print(readline.__file__)"
exit = 1
stdout = EMPTY
stderr = AttributeError: module 'readline' has no attribute '__file__'
```

The recovery command's `AttributeError` occurred only after `import readline` completed; it is not
an import crash. The forensic interpreter crashes while creating its readline module. This supports
`NATIVE_EXTENSION_FAILURE` for the failing environment without identifying a deeper library or ABI
cause.

### Trivial external control

A temporary directory outside the repository contained only a one-line passing test and no OIC
imports. All four capture modes, plus plugin-disabled `--capture=no`, exited `139` with empty stdout
and the same faulthandler stderr boundary. Therefore the pytest runtime crashes without OIC or
repository tests.

### Frozen-baseline comparator

At exact baseline `29daa374b7e5cdc30ca7788310fbabb85f19912b`, all four capture modes exited
`139` with the same boundary. `BASELINE_FAILURE` and `SLICE_SNAPSHOT_FAILURE` are separately
observed and behaviorally identical for this matrix.

### Clean reconstructed environment

```text
environment_id = CDC-CORE-TEST-ENVIRONMENT-CANDIDATE-001
python = .venv-cdc-recovery-001/bin/python
python_build = Python 3.12.13 | Clang 21.1.4
requirements_dev_sha256 = cf211a43c0f96dfb45f00376bfa940dae9beefd8f1425d96ed6c9f8fa2cc1172
requirements_runtime_sha256 = 4840856b2fae0e793b061f5bf8ba87a5b180796177bdda45240ee7b0868e2d3f
pyproject_sha256 = be858356b8b2d519b538c79e624e0e600dbb0899802ecc636341f85b134654a2
pip_check = No broken requirements found.
```

Progression results:

```text
python_pytest_import: collected=0 passed=0 failed=0 skipped=0 xfailed=0 errors=0; exit=0
trivial_control: collected=1 passed=1 failed=0 skipped=0 xfailed=0 errors=0
repository_collection: collected=1239 passed=0 failed=0 skipped=0 xfailed=0 errors=0
baseline_targeted: collected=27 passed=27 failed=0 skipped=0 xfailed=0 errors=0
slice_unit: collected=10 passed=10 failed=0 skipped=0 xfailed=0 errors=0
relevant_contract: collected=667 passed=667 failed=0 skipped=0 xfailed=0 errors=0
full_suite: collected=1239 passed=1236 failed=2 skipped=1 xfailed=0 errors=0
```

The first genuine failure at the full-suite layer is preserved:

```text
tests/contract/test_canada_acquisition_freeze.py::test_status_and_draft_schemas_are_untouched
tests/contract/test_canada_rights_resolution_dossier.py::test_status_and_draft_schemas_are_unchanged
```

Both historical Canada-scope tests reject any post-`d99a385...` change beneath
`docs/contracts/`. The owner-attested slice contract and its semantic-review notes are exactly such
authorized additions. No test was weakened or changed under Work Order 004.

### Work Order 004 disposition

```text
PYTEST_RUNTIME_BLOCKER = LOCALIZED_TO_FORENSIC_CONDA_PYTHON_READLINE_INITIALIZATION_PATH
PYTEST_DIAGNOSIS = NATIVE_EXTENSION_FAILURE
CAPTURE_MODE_DISCRIMINATOR = NONE
PLUGIN_AUTOLOAD_CAUSAL_EXPLANATION = NOT_SUPPORTED
OIC_OR_REPOSITORY_TRIGGER = NOT_SUPPORTED
BASELINE_REPRODUCIBLE = TRUE
CLEAN_ENVIRONMENT_EXECUTES_TESTS = TRUE
FULL_SUITE_BLOCKER = TWO_HISTORICAL_DOCS_CONTRACT_GUARDS_REQUIRE_OWNER_REBIND
EXECUTION_CLEARANCE = FALSE
```
