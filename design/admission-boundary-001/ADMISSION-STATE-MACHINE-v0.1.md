# Admission State Machine v0.1

## Frozen terminal states and reason codes

The outcome is one terminal state with one primary reason code. Except for
`ADMITTED`, every state fails closed: eligibility was not established, but the
underlying proposition was not transactionally denied.

| State | Primary reason code | Meaning |
| --- | --- | --- |
| `ADMITTED` | `OIC-ADM-0000` | Exact, active, scoped, unambiguous institutional authority and admission warrant established eligibility. |
| `CANDIDATE_INPUT_INVALID` | `OIC-ADM-1001` | Required candidate identity or source-anchor binding is absent or inconsistent. |
| `SOURCE_NOT_REGISTERED` | `OIC-ADM-1002` | No institution-controlled registry entry exists for the source identity. |
| `SOURCE_VERSION_MISMATCH` | `OIC-ADM-1003` | Candidate/source version differs from the registered warranted version. |
| `SOURCE_DIGEST_MISMATCH` | `OIC-ADM-1004` | Candidate/source bytes do not match the registered warranted digest. |
| `MISSING_AUTHORITY_EVIDENCE` | `OIC-ADM-1005` | A required institutional authority basis or admission warrant is absent. |
| `NOT_YET_EFFECTIVE` | `OIC-ADM-1006` | Adoption or publication occurred, but source or warrant effectiveness has not begun. |
| `EXPIRED` | `OIC-ADM-1007` | Source or warrant effectiveness ended before the evaluation time. |
| `SUPERSEDED` | `OIC-ADM-1008` | Applicable authoritative evidence establishes supersession as of evaluation time. |
| `REVOKED` | `OIC-ADM-1009` | Applicable source authority or admission warrant was revoked as of evaluation time. |
| `OUT_OF_SCOPE` | `OIC-ADM-1010` | Warranted jurisdiction or applicability scope does not cover the requested evaluation. |
| `CONFLICTING_AUTHORITY` | `OIC-ADM-1011` | Overlapping relevant evidence cannot be resolved by a preregistered institution-controlled precedence rule. |
| `AUTHORITY_REGISTRY_UNAVAILABLE` | `OIC-ADM-1012` | Required current registry evidence cannot be obtained or authenticated. |
| `AUTHORITY_EVIDENCE_STALE` | `OIC-ADM-1013` | Cached evidence exceeds the institution-defined freshness bound. |
| `ADMISSION_NOT_ESTABLISHED` | `OIC-ADM-1099` | An otherwise enumerated or disputed authority condition prevents a positive finding. |

The vocabulary deliberately contains neither runtime permission state. `ADMITTED`
means eligible for semantic interpretation only.

## Ordered deterministic evaluation

For one explicit `evaluation_time`, the future evaluator would perform these pure,
ordered checks. The first applicable terminal state is emitted, except that all
relevant authority records are collected before the conflict check.

1. **Candidate reference check.** Validate required Candidate Normative Unit fields
   and internally consistent source-anchor references without re-extracting,
   trimming, classifying, or semantically repairing the candidate.
2. **Registry availability and freshness.** Require authenticated institution-
   controlled registry evidence current under the configured freshness policy.
3. **Source registration.** Resolve the exact `source_id`.
4. **Version and digest binding.** Match candidate anchor, registered metadata, and
   authority evidence to the exact source version and SHA-256 digest.
5. **Authority-basis and warrant sufficiency.** Require an authenticated issuer,
   institution-recognized authority basis, and a machine-verifiable admission
   warrant binding the same source instance. Model confidence and candidate type are
   ignored.
6. **Scope.** Require both authority and warrant jurisdiction/applicability scope to
   cover the requested evaluation scope.
7. **Temporal lifecycle.** At `evaluation_time`, require adopted status, source and
   warrant effective intervals, and absence of applicable expiration,
   supersession, or revocation.
8. **Conflict.** Apply only an explicit, versioned institution-controlled precedence
   rule. If none uniquely resolves overlapping evidence—including a newer
   lower-authority source versus an older higher-authority source—emit
   `CONFLICTING_AUTHORITY`; never use recency alone.
9. **Positive result.** If every check passes, emit `ADMITTED` and a deterministic
   receipt.

The generic `ADMISSION_NOT_ESTABLISHED` state is a fail-safe for a condition not
covered by the frozen specific states. It must never be used to hide an available
specific reason.

## Temporal semantics

`evaluation_time` is mandatory, supplied as normalized RFC 3339 UTC, and included
in receipt identity. No evaluator wall clock is consulted. Source issuance,
adoption, publication, and effectiveness are distinct facts: publication alone
cannot satisfy `effective_from`.

Intervals are half-open: `effective_from <= evaluation_time < effective_until`
when an end exists. `revoked_at <= evaluation_time` yields `REVOKED`;
`superseded_at <= evaluation_time` yields `SUPERSEDED`. A revocation received after
a prior positive evaluation produces a new `REVOKED` receipt for a new evaluation;
the prior `ADMITTED` receipt remains immutable evidence of what was established at
its own evaluation time.

Source version is resolved as of `evaluation_time`, not as whichever version is
latest at retrieval. When version-as-of evidence is missing, admission fails closed.

## Source-standing conflicts

* Draft status lacks operative standing unless an explicit institutional warrant
  specifically authorizes that draft for the requested admission purpose; absent
  such a warrant, use `MISSING_AUTHORITY_EVIDENCE`.
* Commentary quoting authoritative policy retains commentary's own source identity;
  the quoted provenance cannot borrow the policy's warrant.
* Superseded, revoked, expired, and not-yet-effective conditions map to their exact
  terminal states.
* Overlapping warrants require a versioned institutional precedence rule. The model
  and evaluator may not improvise rank.
* Valid authority outside jurisdiction or applicability scope yields `OUT_OF_SCOPE`.
* Perfect provenance without an authority basis or admission warrant yields
  `MISSING_AUTHORITY_EVIDENCE`.

`NOT SELF-ADJUDICATED`
