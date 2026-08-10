#!/usr/bin/env bash
# Clean reproduction entry point for the CDC vertical slice.
#
# Steps 1-4 verify. Step 5 executes and is gated: without an owner
# execution-clearance reference this script stops at
#
#     PREPARATION_COMPLETE
#     EXECUTION_NOT_AUTHORIZED
#
# A clean stop there is the intended outcome of the preparation work order.
# No clearance reference is defined here, and none may be invented.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${CDC_SLICE_PYTHON:-python3.12}"
OUT_ROOT="${CDC_SLICE_OUT:-${REPO_ROOT}/build/cdc-slice}"

echo "== step 1: repository coordinate =="
git -C "${REPO_ROOT}" rev-parse HEAD
git -C "${REPO_ROOT}" rev-parse 'HEAD^{tree}'
git -C "${REPO_ROOT}" status --porcelain

echo "== step 2: environment identity =="
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "FAIL: ${PYTHON_BIN} not found; project pins >=3.12,<3.13" >&2
    exit 2
fi
"${PYTHON_BIN}" --version
VERSION_OK="$("${PYTHON_BIN}" -c 'import sys; print(1 if (3,12) <= sys.version_info < (3,13) else 0)')"
if [ "${VERSION_OK}" != "1" ]; then
    echo "FAIL: interpreter does not satisfy >=3.12,<3.13" >&2
    exit 2
fi

echo "== step 3: contract and oracle identities =="
"${PYTHON_BIN}" -c "
import sys
sys.path.insert(0, '${REPO_ROOT}/src')
from oic.cdc_slice import CONTRACT_ID, MISSION_ID
print('contract', CONTRACT_ID)
print('mission ', MISSION_ID)
print('oracle   2ce3bdab0acc6a0411f63a20e32164c1f0c8d4a9 DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE')
"

echo "== step 4: fixture corpus =="
"${PYTHON_BIN}" "${REPO_ROOT}/scripts/cdc_slice_run_plan.py" --output-root "${OUT_ROOT}" >/dev/null
echo "run plan generated and references validated (RUN_PLAN_ONLY, RESULT_BEARING=FALSE)"

echo "== step 5: execution =="
if [ -z "${CDC_SLICE_EXECUTION_CLEARANCE_REF:-}" ]; then
    echo "EXECUTION_CLEARANCE_REF = ABSENT"
    echo "RESULT_BEARING_ENTRYPOINT = BLOCKED"
    echo
    echo "PREPARATION_COMPLETE"
    echo "EXECUTION_NOT_AUTHORIZED"
    exit 0
fi

echo "clearance reference supplied; steps 5-7 are not implemented on this branch." >&2
echo "Result-bearing execution requires a separate owner authorization." >&2
exit 3
