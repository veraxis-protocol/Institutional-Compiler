#!/usr/bin/env bash
#
# Build a wheel and smoke-install it into a throwaway environment.
#
# What this proves that an editable install does not: the wheel's declared metadata is
# self-consistent, the package imports from an installed location rather than from the
# source tree, the console script is wired up, and `pip check` passes against only the
# locked runtime dependencies.
#
# The wheel is NEVER published. It is built into a temporary directory and discarded.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

work_dir="$(mktemp -d)"
cleanup() { rm -rf "${work_dir}"; }
trap cleanup EXIT

dist_dir="${work_dir}/dist"
venv_dir="${work_dir}/venv"

echo "==> Building wheel"
python -m build --wheel --outdir "${dist_dir}"

wheel="$(find "${dist_dir}" -name '*.whl' -print -quit)"
if [ -z "${wheel}" ]; then
  echo "::error::no wheel was produced"
  exit 1
fi
echo "built: $(basename "${wheel}")"

echo
echo "==> Creating an isolated environment"
python -m venv "${venv_dir}"
venv_python="${venv_dir}/bin/python"

echo
echo "==> Installing locked runtime dependencies (hash-verified)"
"${venv_python}" -m pip install --quiet --disable-pip-version-check \
  --require-hashes -r requirements/runtime.txt

echo
echo "==> Installing the wheel without dependency resolution"
# --no-deps proves the locked runtime set is sufficient on its own. If a dependency were
# missing from requirements/runtime.in, the import below would fail rather than pip
# quietly fetching it.
"${venv_python}" -m pip install --quiet --disable-pip-version-check --no-deps "${wheel}"

echo
echo "==> pip check"
"${venv_python}" -m pip check

echo
echo "==> Import from the installed location"
"${venv_python}" - <<'PY'
import pathlib
import oic

location = pathlib.Path(oic.__file__).resolve()
print(f"oic {oic.__version__} imported from {location}")
assert "site-packages" in location.parts, (
    f"expected an installed package, got {location}; the source tree shadowed the wheel"
)
PY

echo
echo "==> Admission evaluator runs from the installed package, with no design/ tree"
# The frozen admission specifications are read at runtime. If they were left out of the
# wheel, or if the evaluator silently fell back to the repository's design/ tree, this
# would fail: the working directory is moved away from the repository first, and both an
# ADMITTED and a fail-closed vector are driven through the real byte boundary.
cp design/admission-boundary-001/TEST-VECTORS-v0.2.json "${work_dir}/vectors.json"
(
  cd "${work_dir}"
  "${venv_python}" - <<'ADMISSION_SMOKE'
import json
import pathlib

import oic.admission as admission

location = pathlib.Path(admission.__file__).resolve()
assert "site-packages" in location.parts, f"expected an installed package, got {location}"
assert not pathlib.Path("design").exists(), "the design tree must not be reachable here"

corpus = json.loads(pathlib.Path("vectors.json").read_text(encoding="utf-8"))
vectors = {vector["vector_id"]: vector for vector in corpus["vectors"]}
for vector_id in ("ADM-001", "ADM-003"):
    vector = vectors[vector_id]
    payload = admission.canonical_json(vector["executable_input"])
    receipt = admission.evaluate_admission_bytes(payload)
    assert receipt.to_json() == vector["expected_receipt"], vector_id
    print(f"{vector_id}: {receipt.admission_state.value} {receipt.reason_code.value}")
print("admission evaluator reproduced both vectors from site-packages")
ADMISSION_SMOKE
)

echo
echo "==> Console script"
"${venv_dir}/bin/oic" --version
"${venv_dir}/bin/oic" --help > /dev/null
echo "oic --help exited 0"

echo
echo "Wheel smoke test passed. The wheel was not published."
