# Versioning

- TDD: immutable versioned PDFs.
- Schemas: semantic versions; incompatible changes require migration notes and ADR.
- Open Control Envelopes: bind schema version, compiler version, source hashes, admission record, and test-suite hash.
- Admitted artifacts: never mutated in place; supersede with a new version.
- Experimental releases: `0.x` tags and explicit evidence/limitation manifests.
