# Vitaliy Reznik / ZTL — Work Order 001

**Role:** ZTL owner and OIC semantic-boundary reviewer  
**Objective:** Freeze the smallest deterministic adapter contract OIC can rely upon without expanding ZTL's mandate.

## Required dossier

1. Canonical repository/artifact location.
2. Owner and maintainer.
3. License and reuse conditions.
4. Immutable release, tag, or commit.
5. Exact interface version.
6. Input schema for:
   - admitted proposition identifiers;
   - T/F/Z grounding values;
   - source-independent fact identifiers;
   - formula/dependency representation;
   - semantic epoch/version;
   - revocation/expiry inputs where supported.
7. Output schema for:
   - verdict;
   - dependency/warrant graph;
   - missing grounds;
   - contradiction;
   - CANNOT;
   - proof or reproduction references.
8. Error taxonomy and deterministic failure behavior.
9. Golden fixtures and hashes.
10. Conformance command and expected output.
11. Known limitations and explicit non-goals.
12. Independent reproduction status.
13. Replacement/fallback boundary if ZTL is unavailable.

## Locked responsibility boundary

ZTL may determine logical warrant from admitted grounds. It must not:

- authenticate sources;
- decide issuer authority;
- interpret policy prose;
- create institutional admission;
- convert unknown into grounded false;
- equate operational DENY with proven prohibition.

## First integration fixture

Provide one formula with:
- a positive T result;
- a negative F result;
- a missing-ground Z/CANNOT result;
- an epoch or revocation change;
- a machine-recomputable artifact.

## Acceptance

The adapter can be implemented by an engineer who has no private conversation context and obtains the same result from the pinned fixtures.
