# VEIP Dependency Inventory v0.1

**Status: PREFLIGHT EVIDENCE — NOT A DOSSIER COMPLETION, INTERFACE FREEZE, OR OWNER ATTESTATION**

Captured: 2026-07-29
Interim VEIP contract owner: Arkadiy Miteiko / Veraxis
Implementation support: Claude Fable 5
Architecture review: GPT-5.6 Thinking

## Scope and method

This inventory records repository-visible evidence at four exact default-branch commits. It
does not infer evidence from repository names, GitHub descriptions, marketing language, or
references to files that are not present at the pinned commit. The repositories were cloned
and inspected locally; GitHub repository, tag, release, and Actions metadata were queried
separately.

No VEIP repository was modified or executed by OIC. No interface is declared frozen.

## Repository pins

| Repository | Visibility | Default branch | Pinned head | Latest tag | Latest GitHub release |
|---|---|---|---|---|---|
| [`veraxis-protocol/veip-spec`](https://github.com/veraxis-protocol/veip-spec) | Public | `main` | [`b7bae309cd39b6be2f1669aff75c4feb9cf18668`](https://github.com/veraxis-protocol/veip-spec/commit/b7bae309cd39b6be2f1669aff75c4feb9cf18668) | None | None |
| [`veraxis-protocol/veip-sdk`](https://github.com/veraxis-protocol/veip-sdk) | Public | `main` | [`40bcb5708c8e3aadcb0e31d3190824ddc33f8fce`](https://github.com/veraxis-protocol/veip-sdk/commit/40bcb5708c8e3aadcb0e31d3190824ddc33f8fce) | None | None |
| [`veraxis-protocol/veip-verifier-core`](https://github.com/veraxis-protocol/veip-verifier-core) | Public | `main` | [`e8b985920b60ba74f2e0e014ee107a5c4937b1fc`](https://github.com/veraxis-protocol/veip-verifier-core/commit/e8b985920b60ba74f2e0e014ee107a5c4937b1fc) | None | None |
| [`veraxis-protocol/veip-registry`](https://github.com/veraxis-protocol/veip-registry) | Public | `main` | [`a0b70452d14c0b29da500d53714ae215b09bc43e`](https://github.com/veraxis-protocol/veip-registry/commit/a0b70452d14c0b29da500d53714ae215b09bc43e) | None | None |

The SHAs above are evidence pins selected for this inventory. They are not owner-attested
immutable VEIP versions.

## Cross-repository schema evidence

All located copies of `veip-evidence-pack.schema.json` have SHA-256:

`3ff025de2c91737e84aceae529e2da78a86622a26f7f5998b73ed880c15ebbf0`

Copies were found at:

- `veip-spec/schemas/veip-evidence-pack.schema.json`;
- `veip-sdk/veip_sdk/schemas/veip-evidence-pack.schema.json`;
- `veip-verifier-core/veip_verifier_core/schemas/veip-evidence-pack.schema.json`;
- `veip-registry/schemas/veip-evidence-pack.schema.json`;
- `veip-registry/veip_registry/schemas/veip-evidence-pack.schema.json`.

Byte identity is evidence of current copying consistency only. There is no tag, release, or
owner attestation freezing this schema for OIC.

## `veip-spec`

### Identity and version

- Canonical identifier: `veraxis-protocol/veip-spec`.
- Pin: `b7bae309cd39b6be2f1669aff75c4feb9cf18668`.
- Repository-visible version: `0.1.0 (Public Working Draft)` in
  [`README.md`](https://github.com/veraxis-protocol/veip-spec/blob/b7bae309cd39b6be2f1669aff75c4feb9cf18668/README.md)
  and `RELEASE_NOTES.md`.
- No Git tag and no GitHub release were present.
- The working-draft notice says breaking changes may occur before 1.0 and that Evidence Pack
  and supervisory semantics may still be clarified.

### License

- File: [`LICENSE`](https://github.com/veraxis-protocol/veip-spec/blob/b7bae309cd39b6be2f1669aff75c4feb9cf18668/LICENSE).
- SHA-256: `9e5f1b3c610b9c2da5c313bf81d577a7d1acec686bdb0384edefa6df0f90cd94`.
- GitHub detection: `CC-BY-4.0`.
- The file contains the Creative Commons Attribution 4.0 International text.
- Trademark and certification terms are separately referenced in `TRADEMARKS.md`.

### Specifications, schemas, and interfaces

- Present specification documents:
  - `spec/state-transition-model.md`;
  - `spec/formal-invariants.md`;
  - `spec/conformance-test-suite.md`;
  - `docs/architecture.md`;
  - `docs/public-working-draft.md`;
  - `profiles/README.md`.
- Present schema: `schemas/veip-evidence-pack.schema.json`, Draft 2020-12.
- The README links `spec/supervisory-verification-interface.md` and
  `spec/evidence-pack-schema.md`, but neither path exists at the pinned commit.
- The state model identifies `PROPOSED`, `ALLOW`, `DENY`, `ESCALATE`,
  `SUPERVISORY`, and `EXECUTED` concepts, but does not define expiry, revocation,
  correction, or reliance transitions.
- The Evidence Pack schema contains `authority`, `policy`, `action`, `decision`,
  `execution`, and `provenance`; it is not a separate action-proposal,
  runtime-decision-input, or execution-record schema.

### Tests, fixtures, and CI

- The conformance suite is a prose structure, not a populated normative vector set.
- No fixture or test-vector file was found.
- CI: `.github/workflows/ci.yml` runs `make check`.
- Latest `main` run at the pinned SHA:
  [`veip-spec-ci` failure](https://github.com/veraxis-protocol/veip-spec/actions/runs/22039264040).
- The Actions log endpoint returned HTTP 410 when queried, so the failure cause is not
  recoverable from current GitHub logs. The job metadata records `checks` as failed.

### Lifecycle and operational evidence

- Replay: prose requires identical-input reclassification equivalence.
- Revocation: no behavior found.
- Correction: no behavior found.
- Reliance: no behavior found.
- Expiry: authority validity windows are named by the conformance prose and schema, but no
  expiry transition or downstream effect is defined.
- Security: the VIP process names security review; release notes say cryptographic binding is
  unfinished. No `SECURITY.md` or consolidated threat model was found.
- Known limitations: cryptographic profiles unfinished; multi-registry federation conceptual
  only; Evidence Pack schema still subject to clarification; CTS vectors and supervisory
  semantics are not finalized.
- Replacement/fallback: ecosystem documents reference SDK, Verifier Core, and Registry layers.
  No fallback, migration, or replacement procedure is specified.

## `veip-sdk`

### Identity and version

- Canonical identifier: `veraxis-protocol/veip-sdk`.
- Pin: `40bcb5708c8e3aadcb0e31d3190824ddc33f8fce`.
- Package: `veip-sdk==0.1.0` in
  [`pyproject.toml`](https://github.com/veraxis-protocol/veip-sdk/blob/40bcb5708c8e3aadcb0e31d3190824ddc33f8fce/pyproject.toml).
- Declared specification binding: `0.1.0`.
- No Git tag and no GitHub release were present.

### License

- File: [`LICENSE`](https://github.com/veraxis-protocol/veip-sdk/blob/40bcb5708c8e3aadcb0e31d3190824ddc33f8fce/LICENSE).
- SHA-256: `c69f05da5e46c06a44686cfe335c8e739584707efe031d6390def3db4ce81b58`.
- GitHub detection and package metadata: MIT.
- The file contains the standard MIT grant and disclaimer.

### Interfaces, tests, fixtures, and CI

- `AuthorityEnvelope`: `scope_id`, `issuer`, `permitted_actions`, and boolean `valid`.
- `ActionProposal`: `action_type` and unconstrained dictionary `payload`.
- Classification implementation returns `DENY` for invalid authority, `ESCALATE` for an
  action not listed as permitted, and otherwise `ALLOW`. It does not emit `SUPERVISORY`.
- Evidence emission creates an Evidence Pack with default/generated policy, validity,
  context, executor, environment, and provenance values.
- Replay recomputes the SDK classifier from caller-supplied authority and proposal, then
  compares classification and action type.
- Three tests cover schema validation, version binding, and replay/tamper classification.
- No standalone fixture file was found.
- CI runs `make check`; the latest pinned-head run is
  [green](https://github.com/veraxis-protocol/veip-sdk/actions/runs/29104380724).

### Lifecycle and operational evidence

- Replay behavior is present but only compares schema version, classification, and action type;
  it does not compare the proposal payload or full execution record.
- Revocation, correction, reliance, expiry propagation, and replacement/fallback behavior were
  not found.
- Authority has a boolean `valid`; generated evidence writes a one-year `valid_to`, but no
  lifecycle behavior follows expiry or revocation.
- Security documentation is limited to README hardening gaps: cryptographic sealing, secure
  time, tamper-evident storage, operational resilience, independent review, and separation of
  duties are outside the repository's implemented scope.
- The README uses readiness-oriented language while listing substantial production controls as
  absent. This inventory treats the missing controls as the evidence-bearing statement and does
  not adopt the readiness characterization.
- Replacement references point to `veip-spec`, `veip-verifier-core`, and `veip-registry`;
  no fallback procedure exists.

## `veip-verifier-core`

### Identity and version

- Canonical identifier: `veraxis-protocol/veip-verifier-core`.
- Pin: `e8b985920b60ba74f2e0e014ee107a5c4937b1fc`.
- Package: `veip-verifier-core==0.1.0`.
- CLI surface: `veip-verify validate`, `replay`, and `schema`.
- No Git tag and no GitHub release were present.

### License

- File: [`LICENSE.md`](https://github.com/veraxis-protocol/veip-verifier-core/blob/e8b985920b60ba74f2e0e014ee107a5c4937b1fc/LICENSE.md).
- SHA-256: `2274cf035d708564b3a83080c00bbc1f24459aa58546ff67720a681472a30c1e`.
- GitHub detection: `NOASSERTION`.
- Package metadata points to this custom “VEIP License (Reference Implementation License)
  v0.1.0.”
- The text contains an MIT-like use/copy/modify/sell grant plus notice, certification,
  trademark, and modified-fork conditions.
- `veip-spec/docs/regulatory-positioning.md` characterizes this layer as preventing
  uncontrolled commercialization, while the license text expressly grants sale. The intended
  compatibility and commercialization boundary therefore requires qualified review and owner
  clarification; this inventory does not resolve it.

### Interfaces, tests, fixtures, and CI

- Validates the shared Evidence Pack schema.
- “Replay” canonicalizes and hashes the Evidence Pack after replacing
  `execution.outcome.result_ref` with a zero digest.
- Unless `--require-binding` is set, a pack with no binding returns success with
  `no binding present (not required)`.
- This differs materially from `veip-spec`/SDK replay, which means recomputing the decision from
  authority and proposal inputs.
- One JSON fixture and tests for CLI behavior, schema validation, and tamper detection are
  present. Compiled bytecode and generated egg metadata are also tracked.
- CI runs `make ci` on Python 3.10, 3.11, and 3.12; the latest pinned-head run is
  [green](https://github.com/veraxis-protocol/veip-verifier-core/actions/runs/27908778979).

### Lifecycle and operational evidence

- Replay/integrity verification is present as described above.
- Revocation, correction, reliance, expiry, and replacement/fallback behavior were not found.
- Failure behavior is explicit at the CLI: `0` pass, `2` verification failure, and `3`
  tool/runtime error.
- Security notes state that signing, key management, certificates, registry endorsement, and
  production WORM storage are absent.
- Known limitations say further hardening and conformance suites are expected.

## `veip-registry`

### Identity and version

- Canonical identifier: `veraxis-protocol/veip-registry`.
- Pin: `a0b70452d14c0b29da500d53714ae215b09bc43e`.
- Package and FastAPI application version: `veip-registry==0.1.0`.
- No Git tag and no GitHub release were present.

### License

- Files: `LICENSE` and `LICENSE.md`.
- Both are 12 bytes, contain only `MIT license`, and have SHA-256
  `456db14903330c8ebc89f5e4055dd03df6e5b70fecb4bd1320a69642ba71039c`.
- Package metadata points to `LICENSE.md`; GitHub reports `NOASSERTION`.
- No complete MIT grant, copyright notice, or disclaimer is present. The declared licensing
  intention is visible, but the repository does not contain complete license text.

### Interfaces, tests, fixtures, and CI

- HTTP surface: `POST /v1/evidence`, `GET /v1/evidence/{evidence_id}`, `/`, and `/healthz`.
- Intake validates the shared schema and stores by `evidence_id` in an in-memory dictionary.
- Retrieval returns the stored object.
- One JSON fixture and two tests cover successful intake/retrieval and schema validation.
- There is no test for duplicate IDs, missing IDs, retrieval misses, persistence, replay,
  revocation, correction, reliance, or operator replacement.
- CI runs `make ci`; the latest pinned-head run is
  [green](https://github.com/veraxis-protocol/veip-registry/actions/runs/22040584707).

### Lifecycle and operational evidence

- Replay is delegated conceptually to upstream/downstream verifier layers; the registry does
  not perform it.
- Revocation, correction, reliance, and expiry behavior were not found.
- `docs/threat-model.md` says duplicate `evidence_id` overwrite attempts are rejected with HTTP
  409. The implementation raises an uncaught `KeyError` on duplicate insertion and contains no
  409 handler. The documented and implemented failure behavior conflict.
- Retrieval checks for `None`, but `InMemoryStore.get` indexes the dictionary and raises
  `KeyError` on a miss; the documented 404 path is therefore not supported by the inspected
  storage implementation.
- Security notes explicitly omit authentication/authorization, rate limiting, abuse
  prevention, WORM guarantees, signatures, trusted time, replication, and availability.
- Known limitations identify the implementation as an in-memory reference stub.
- Replacement strategy is conceptual: `docs/operator-model.md` says clients can switch
  operators without reformatting Evidence Packs. No discovery, export, migration, failover, or
  continuity procedure is defined.

## Evidence summary

### Present

- Four public canonical repository candidates with exact commit pins.
- One byte-identical Draft 2020-12 Evidence Pack schema across all located copies.
- Package version `0.1.0` in SDK, Verifier Core, and Registry.
- Repository-specific tests and CI in each repository.
- SDK decision replay and Verifier Core integrity replay implementations.
- Evidence intake/retrieval stub in Registry.

### Missing

- Tags and GitHub releases for every repository.
- Owner-attested immutable version set.
- Standalone lifecycle, action-proposal, runtime-decision-input, and execution-record schemas.
- Reliance, expiry, revocation propagation, and correction behavior.
- Normative populated conformance vectors and a consolidated reproduction command.
- Operational registry replacement/fallback procedure.

### Conflicting

- “Replay” means decision recomputation in `veip-spec`/SDK but integrity-carrier verification in
  Verifier Core.
- Registry threat-model failure claims do not match the inspected duplicate/missing-key code.
- Verifier Core licensing narrative and repository license text need compatibility review.
- Registry declares MIT but contains only a 12-byte label rather than the MIT license text.

## Non-conclusion

This inventory does not establish completeness, conformance, certification, independent review,
license compatibility, interface freeze, or readiness for OIC integration. The OIC semantic
implementation gate remains **BLOCKED**.
