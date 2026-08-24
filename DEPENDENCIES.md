# Dependency Status

Python development dependencies are declared in `requirements/dev.in` and resolved into
the hash-locked `requirements/dev.txt`. CI installs only from that lock, reviews dependency
changes, runs `pip-audit --skip-editable`, and generates a CycloneDX SBOM. Advisory data
and the GitHub dependency graph are external inputs, so an unavailable service is reported
as missing evidence rather than converted into a passing result.

| Dependency | Role | Status | Merge constraint |
|---|---|---|---|
| Docling | Document parsing/layout | Candidate for substantial reuse | Pin version, license, parser fixtures, sandbox limits |
| Akoma Ntoso / ELI / Web Annotation concepts | Source identity and anchoring | Borrow/rebuild | No full XML dependency required |
| LegalRuleML vocabulary | Normative types | Borrow/rebuild | OIC JSON-native IR remains canonical |
| OPA/Rego | First executable target | Candidate for substantial reuse | Pin version and conformance fixtures |
| PostgreSQL JSONB/edges | Reference persistence | Accepted design | Migration/version discipline required |
| ZTL | Logical warrant and T/F/Z/CANNOT | Project-controlled provisional dependency | No semantic integration merge before dossier and interface freeze |
| VEIP | Execution, evidence, reliance, correction continuity | Project-controlled provisional dependency | Adapter remains experimental until dossier freeze |
| Claude/model provider | Candidate extraction | Replaceable, untrusted semantic assistant | Structured output, no direct admission, provider-neutral contract |

## Required ZTL dossier fields

Repository/artifact location; owner; license; immutable version; interface schema; semantics; fixture hashes; conformance tests; failure behavior; security notes; known limitations; replacement strategy; independent reproduction status.

## Required VEIP dossier fields

Repository/spec locations; owner; license; immutable versions; lifecycle interface; evidence schema; fixtures; conformance tests; replay behavior; revocation/correction behavior; security notes; known limitations; replacement strategy.
