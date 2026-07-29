# Continuous integration

Defined in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml). Runs on pull
requests and on pushes to `main`.

## Posture

- **Read-only.** Workflow permissions are `contents: read` and no job widens them. No job
  can push a commit, open a pull request, publish a package, or comment.
- **No secrets.** No job references `${{ secrets.* }}` or `GITHUB_TOKEN`. The workflow runs
  identically on a fork.
- **No release, no deployment, no mutation.** There is no publish step, no deploy step, no
  tag push, and no `release`, `schedule`, or `workflow_dispatch` trigger.
- **No external model calls.** Nothing contacts an LLM or model provider.
- **No network schema resolution.** Schema `$ref`s resolve from a local registry only.
- **Actions pinned to commit SHAs.** A floating tag can be moved by its publisher; a
  commit SHA cannot. The `# vX.Y.Z` comment is for humans and carries no authority.
- **Checkout does not persist credentials.** `persist-credentials: false` everywhere.

`tests/contract/test_ci_supply_chain.py` asserts each of these, so a reviewer does not
have to re-verify them by reading the YAML on every change.

## Jobs

| Job | What it does | Fails when |
|---|---|---|
| `bootstrap-integrity` | Checks the governing TDD digest, the bootstrap manifest, and all three manifests | TDD digest changed; a bootstrap-controlled file changed; `--all` did not exit exactly `3` |
| `schema-validation` | `oic validate-schema`, text and JSON | Any of the nine schemas is not valid Draft 2020-12, or a reference does not resolve locally |
| `lint` | `ruff check`, `ruff format --check`, credential scan | Any lint or format violation, or a credential pattern hit |
| `typecheck` | `mypy` in strict mode | Any type error |
| `test` | `pytest` with coverage | Any test failure |
| `sbom` | CycloneDX SBOM, license inventory, dependency inventory | Generation fails |

### Artifacts

`manifest-report` (JSON), `schema-report` (JSON), `test-results` (JUnit XML and coverage
XML), and `sbom` (CycloneDX JSON, `LICENSES.json`, `DEPENDENCY_INVENTORY.md`).

### Determinism

All dependency installs use `pip install --require-hashes -r requirements/dev.txt`, so
every artifact's digest is verified before installation. `PYTHONHASHSEED=0` and
`SOURCE_DATE_EPOCH` are fixed. The SBOM is generated with `--output-reproducible`, which
drops timestamps and random serial numbers, so an unchanged environment produces a
byte-identical SBOM.

## The TDD digest check

`bootstrap-integrity` compares `docs/tdd/TDD-OIC-001-v1.1.pdf` against the literal
`2a4d802130d577e4fb8fee731174ae0f2172ef2d617e3b99f068545d2b9fbf77`, written directly in
the workflow.

That duplication is deliberate. If someone rewrote both `BOOTSTRAP_MANIFEST.json` and
`docs/tdd/SHA256SUMS` to match a substituted PDF, a check that only compared the manifests
to each other would still pass. This literal would not. A failure here is a governance
event, not a build problem: do not update the literal to make CI green.

## Changing a bootstrap-controlled file

Every file recorded in `BOOTSTRAP_MANIFEST.json` has its digest verified on every run.
Editing one — including `README.md`, `STATUS.md`, `CLAIMS.md`, or any of the nine
schemas — fails `bootstrap-integrity` until the manifest is updated to match.

**No approved amendment mechanism currently exists in this repository.** Updating the
manifest to accommodate an edit would silently defeat the control it implements. Until an
authorized mechanism is defined, treat a `bootstrap-integrity` failure as evidence that a
controlled artifact changed and needs authorization under `GOVERNANCE.md`, not as a check
to work around.

This is why `CLAUDE-FABLE5-WO-001` left `STATUS.md` and `README.md` untouched: no gate row
in `STATUS.md` objectively changed state under this work order, so no edit was warranted,
and making one would have required an unauthorized manifest amendment. Defining that
mechanism needs architecture-lead adjudication.

## Credential pattern scan

`scripts/scan_forbidden_patterns.sh` greps tracked files for private-key blocks,
provider-shaped tokens (AWS, GitHub, Slack, Google, Stripe, bearer), credential-shaped
assignments, and a committed `.env`.

### Limitations — read before relying on it

It is a coarse tripwire, not a secret-scanning product. It does **not** detect:

- a secret committed in an **earlier commit** — it scans the working tree only, never git
  history;
- a secret that is base64-, hex-, or otherwise **encoded**;
- a secret **split across lines** or assembled at runtime;
- a **high-entropy** string matching no known pattern;
- a credential in a **binary** file;
- anything in a file **not tracked by git**.

It also produces false positives: any line resembling a credential assignment is flagged,
including fixtures and documentation. Suppress a reviewed false positive with an inline
`pragma: allowlist secret` comment and justify it in the pull request.

**Passing this check is not evidence that the repository contains no secrets.** Do not
describe it as secret scanning in any external material.

## Reproducing CI locally

```bash
oic validate-schema
oic verify-manifest --all          # expected exit 3
ruff check .
ruff format --check .
mypy
pytest --cov=oic --cov-report=term-missing
bash scripts/scan_forbidden_patterns.sh
bash scripts/generate_sbom.sh
```

Or install the git hooks, which run lint, format, types, and manifest verification before
each commit:

```bash
pre-commit install
```
