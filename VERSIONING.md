# Versioning

OIC is `0.1.0a0`: pre-release infrastructure with provisional compatibility.
Pin an exact commit when reproducing it. Bounded candidate, admission-reference and
provisional interpretation APIs now exist; no production compiler/runtime contract exists.
The capability matrix records their source provenance and evidence ceilings. Frozen local
replay is not provider qualification or independent validation.

## Provisional public surfaces

- CLI commands, flags, structured output, and exit codes (`0` PASS, `1` FAIL,
  `2` usage/configuration error, `3` INCOMPLETE);
- Python infrastructure APIs under `oic`;
- draft schemas and their identifiers;
- bootstrap/current manifest formats and digest rules; and
- generated diagnostic, SBOM, and verification reports.

Before 1.0, any of these may change incompatibly through an explicit governed
pull request. Exit-code conflation—especially treating INCOMPLETE as PASS—is a
breaking defect. Digest scope or canonical identity changes require new artifact
identities and migration notes; existing bytes are not silently reinterpreted.

## Governed artifacts

- TDD: immutable versioned PDFs.
- Schemas: semantic versions; incompatible changes require migration notes and ADR.
- Open Control Envelopes: bind schema version, compiler version, source hashes, admission record, and test-suite hash.
- Admitted artifacts: never mutated in place; supersede with a new version.
- Experimental releases: `0.x` tags and explicit evidence/limitation manifests.

No release or attestation is authorized by this policy. The repository license
is PolyForm Noncommercial License 1.0.0; commercial use requires a separate
written license from Veraxis.
