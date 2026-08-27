# Foundation setup and verification

Operator guide for the non-semantic infrastructure delivered by `CLAUDE-FABLE5-WO-001`.

> **What this is not.** This repository contains no compiler. It does not interpret
> institutional documents, determine authority, record admission, produce an Open Control
> Envelope, generate Rego, evaluate a control, or call ZTL or VEIP. The semantic
> implementation gate is **BLOCKED** (`STATUS.md`). Nothing here is a quality, security,
> enterprise-readiness, or legal-compliance claim.

---

## 1. Clean-clone setup

Requires **Python 3.12** (`>=3.12,<3.13`) and `git`. Nothing else needs to be installed
first — `pip` and `venv` ship with CPython.

```bash
git clone https://github.com/veraxis-protocol/Institutional-Compiler.git
cd Institutional-Compiler
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install --no-deps -e .
```

`--require-hashes` makes pip verify every downloaded artifact against the digests in the
lockfile and refuse to install anything that does not match. The second command installs
this package itself in editable mode; `--no-deps` is required because pip cannot combine
an editable install with hash checking.

Confirm the install:

```bash
oic --version
```

### Dependency workflow

`pyproject.toml` holds dependency *ranges*; `requirements/*.txt` are generated,
fully-pinned, hash-locked *resolutions*. See [ADR-011](../../adr/ADR-011.md) for why
pip-tools was chosen over Poetry, uv, PDM, and Hatch.

To change a dependency, edit the `.in` file and regenerate both locks:

```bash
pip-compile --generate-hashes --strip-extras --allow-unsafe --output-file=requirements/runtime.txt requirements/runtime.in
pip-compile --generate-hashes --strip-extras --allow-unsafe --output-file=requirements/dev.txt requirements/dev.in
```

Commit the regenerated locks in the same commit as the `.in` change.

---

## 2. Verification commands

Run all of these from the repository root with the virtualenv active.

| Command | Verifies | Passing exit code |
|---|---|---|
| `oic validate-schema` | All nine draft schemas are valid Draft 2020-12, offline | `0` |
| `oic verify-bootstrap` | The bootstrap commit still holds its recorded bytes | `0` |
| `oic verify-manifest` | Same as `verify-bootstrap` | `0` |
| `oic verify-manifest --all` | Bootstrap baseline plus both current-tree manifests | **`3`** — see below |
| `python -m pip check` | Declared metadata matches the installed environment | `0` |
| `bash scripts/wheel_smoke_test.sh` | Wheel builds, imports, and runs when installed | `0` |
| `oic doctor` | Environment, tool availability, gate state | `0` |
| `ruff check .` | Lint | `0` |
| `ruff format --check .` | Formatting | `0` |
| `mypy` | Strict type checking | `0` |
| `pytest` | Full test suite | `0` |
| `bash scripts/scan_forbidden_patterns.sh` | Credential tripwire | `0` |
| `bash scripts/generate_sbom.sh` | SBOM, licenses, dependency inventory | `0` |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | PASS |
| `1` | FAIL — a check failed |
| `2` | Usage or configuration error (bad argument, missing directory, unreadable manifest) |
| `3` | INCOMPLETE — nothing failed, but the evidence is not complete |

`3` is deliberately distinct from both `0` and `1`. A script that treats "did not fail" as
"passed" would report an empty corpus manifest as corpus-ready. Pass `--allow-incomplete`
to opt into exit `0` on INCOMPLETE; the result is still reported either way.

---

## 3. CLI examples

### Validate schemas

```bash
oic validate-schema
```

Validates every `*.schema.json` under `schemas/draft/`. References are resolved from a
registry built only from files on disk. A `$ref` written with an `http`/`https` scheme
that no local schema satisfies **fails the command**; nothing is fetched.

Against a different local directory:

```bash
oic validate-schema --schema-dir path/to/schemas
```

Deterministic machine-readable output:

```bash
oic --format json validate-schema
```

### Verify the bootstrap baseline

```bash
oic verify-bootstrap
oic verify-bootstrap --ref <commit-or-tag>
oic --format json verify-bootstrap
```

`BOOTSTRAP_MANIFEST.json` is **immutable historical evidence about the bootstrap commit**,
not a policy freezing every path it lists. Both the manifest and every artifact it names
are read from that commit through the local Git object database; the working tree is
neither read nor modified, and nothing touches the network.

This matters in practice. `adapters/ztl/README.md` is recorded in the manifest and was
legitimately rewritten later by PR #2. That change **must not** fail bootstrap
verification, and it does not, because the baseline is a statement about the past. See
[ADR-012](../../adr/ADR-012.md) for the artifact classes and the amendment rules.

The manifest is never rewritten to make a later working tree match. Doing so would
destroy the only record of what the bootstrap contained.

### Verify current-tree manifests

```bash
oic verify-manifest                    # bootstrap baseline (default)
oic verify-manifest --all              # baseline + SHA256SUMS + corpus manifest
oic verify-manifest --manifest docs/tdd/SHA256SUMS
oic --format json verify-manifest --all
```

Passing `--manifest BOOTSTRAP_MANIFEST.json` is refused with a pointer to
`verify-bootstrap`: comparing a historical manifest against the present tree is precisely
the error ADR-012 corrects.

Verification is strictly read-only. No manifest is rewritten, re-sorted, or repaired, and
no origin URL is ever fetched. Paths that are absolute, drive-qualified, contain `..`,
look like a URI, or resolve outside the repository (including through a symlink) are
**refused**, not sanitised.

### Diagnose the environment

```bash
oic doctor
oic --format json doctor
```

`doctor` reads only. It starts no container, opens no connection, and queries no service.
Every check is a tri-state — `AVAILABLE` / `NOT_AVAILABLE` / `UNKNOWN` for tools,
`CONFIGURED` / `NOT_CONFIGURED` / `UNKNOWN` for profiles. A tool on `PATH` whose version
probe fails is `UNKNOWN`, not absent. The report contains **no boolean fields at all**, so
an unknown has nowhere to collapse into a grounded false (invariant I-03).

---

## 4. The expected INCOMPLETE result

**`oic verify-manifest --all` exits `3`. This is correct, not a bug.**

`benchmarks/preflight/SOURCE_MANIFEST.csv` currently contains only its header row. There
are zero corpus source records. The verifier reports:

```
benchmarks/preflight/SOURCE_MANIFEST.csv  [source-manifest]
  0 entries
  note: 0 corpus source row(s) recorded
  note: origin URLs are recorded only; this verifier never fetches them
  note: preflight corpus manifest contains only its header: corpus provenance is NOT
        complete and this repository is not corpus-ready
  RESULT: INCOMPLETE
```

This matches `STATUS.md`, which records preflight corpus rights and provenance as **OPEN**.

Two design choices keep this honest:

1. An empty manifest can never aggregate to `PASS`; zero rows forces `INCOMPLETE`.
2. Even once rows exist, a row can never reach `PASS`. Corpus documents are not in the
   working tree, so a row with a well-formed digest reports `RECORDED_NOT_VERIFIED`.
   Recording a digest is not the same as verifying one.

CI asserts the exit code is exactly `3`, so a regression to `FAIL` and a premature jump to
`PASS` both break the build.

---

## 5. Docker Compose

Infrastructure only — PostgreSQL 17, MinIO, and OPA. No application, ZTL, or VEIP
container; no OPA policy or bundle; no database schema; no seed data. Starting the stack
enables no compiler behaviour.

```bash
cp docker/.env.example docker/.env    # then replace every CHANGEME value
docker compose -f docker/compose.yaml --env-file docker/.env up -d
docker compose -f docker/compose.yaml --env-file docker/.env ps
docker compose -f docker/compose.yaml --env-file docker/.env down
```

`docker compose ... down -v` additionally **deletes the named volumes and everything in
them**, with no undo and no backup.

Full detail, port table, and image-pin provenance: [`docker/README.md`](../../docker/README.md)
and [`docker/IMAGES.md`](../../docker/IMAGES.md).

---

## 6. Continuous integration

Six jobs on pull requests and pushes to `main`: `bootstrap-integrity`,
`schema-validation`, `lint`, `typecheck`, `test`, `sbom`. See [`CI.md`](CI.md).

---

## 7. Rollback

Nothing in this work order runs in production, stores data, exposes a network service, or
changes any governing artifact, so rollback is a source-control operation only.

**Revert the whole change:**

```bash
git revert --no-commit <merge-commit-sha>
git commit -m "revert: roll back OIC non-semantic foundation"
```

Or before merge, simply close the pull request. The branch is additive: every file it adds
is new, and no bootstrap-controlled artifact is modified. Reverting returns the repository
to the bootstrap baseline with no cleanup, no migration, and no data loss.

**Roll back only a dependency change:** restore the previous `requirements/*.txt` and
`requirements/*.in` together, then reinstall:

```bash
git checkout <previous-sha> -- requirements/
python -m pip install --require-hashes -r requirements/dev.txt
```

**Discard the local infrastructure stack:**

```bash
docker compose -f docker/compose.yaml --env-file docker/.env down -v
```

This destroys local volume data (see above). It affects one developer's machine only.

**Blast radius.** A defect in this work order can cause a false PASS or a false FAIL in a
verification command, or a broken CI job. It cannot corrupt a governing artifact (every
write path is read-only), cannot leak data (nothing is transmitted), and cannot produce an
enforcement artifact (none exists to produce).

---

## 8. Current limitations

- **This is not a compiler.** No semantic implementation exists. See `LIMITATIONS.md`.
- **The semantic implementation gate is BLOCKED** and nothing here opens it.
- **Preflight corpus provenance is OPEN.** `SOURCE_MANIFEST.csv` has no rows.
- **ZTL and VEIP are PROVISIONAL / NOT CONFIGURED.** Their interfaces are unfrozen
  (ADR-009, ADR-010) and no adapter, container, or call exists.
- **Docker Compose is validated by CI, not locally here.** The `compose-validation` job
  resolves the configuration, pulls every digest-pinned image, starts all three services,
  waits for their healthchecks, and tears the stack down. Docker is unavailable in the
  authoring environment, so the local evidence remains structural contract tests; CI
  provides the executable evidence.
- **The credential scan is a coarse tripwire.** It does not scan git history, encoded
  values, or binaries. Passing it is not evidence that the repository contains no secrets.
- **No third-party license-compatibility determination has been made.** The repository
  is licensed under PolyForm Noncommercial License 1.0.0; dependency and corpus-source
  rights remain separately bounded and unadjudicated.
- **Verification means byte integrity only.** A digest match proves two byte sequences are
  identical. It establishes no source authority, institutional validity, or semantic
  equivalence.
- **Class B contracts are protected procedurally, not mechanically.** ADR-012 defines
  requirements, invariants, schemas, `STATUS.md`, `CLAIMS.md`, and the other governed
  contracts as Class B. They change only through reviewed pull requests; there is no
  machine-checked registry of their current expected digests. A governed-current-state
  registry is deliberately deferred to a separate work order.
- **Coverage is not a quality claim.** Infrastructure modules are covered at roughly 95%
  because the behaviour under test is small and deterministic. No test exists solely to
  raise that number, and the number says nothing about correctness of anything unbuilt.
- **README.md does not link to this document.** `README.md` is bootstrap-controlled and
  was deliberately left unmodified; see [`CI.md`](CI.md#changing-a-bootstrap-controlled-file).

## 9. Claims discipline

Every claim in this document is about the behaviour of checked-in code and can be
reproduced by running the commands above. Nothing here asserts that OIC is enterprise
ready, production ready, secure, compliant, independently reviewed, first, best, or
better than any other system. `CLAIMS.md` governs; where this document and `CLAIMS.md`
appear to differ, `CLAIMS.md` wins.
