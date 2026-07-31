# Canada Acquisition Freeze v0.1

Freeze disposition: **PARTIAL**

Acquisition tool: `freeze_canada_corpus` version 0.1.0.

Every request in this freeze used the explicit acquisition target from the rights record. No provenance URL was requested as a fallback, and no source with a BLOCKED_PENDING_CLEARANCE disposition was requested at all.

A PARTIAL freeze is not convertible to COMPLETE by substituting a source, relaxing a disposition, or falling back to a provenance URL. COMPLETE requires that all 11 source units carry a permitted exact-byte acquisition.

Semantic implementation gate: **BLOCKED**.

## Source manifest limitation

SOURCE_MANIFEST.csv carries no path column, so `oic verify-manifest` cannot bind a recorded row to its committed bytes and reports RECORDED_NOT_VERIFIED rather than PASS. The schema was not changed and no field was invented; the frozen path is recorded in the notes column and byte-level verification is scripts/verify_canada_freeze.py. An internal-only freeze would have no faithful representation at all in this schema and would be left out pending an owner decision.

## Counts

| Measure | Value |
|---|---:|
| Source units | 11 |
| Acquired | 1 |
| Blocked, never requested | 10 |
| Committed to the repository | 1 |
| Stored internal-only | 0 |

## Frozen artifacts

| Source | Acquisition target | Final URL | Retrieved (UTC) | Content type | Bytes | SHA-256 | Disposition | Storage | Receipt |
|---|---|---|---|---|---:|---|---|---|---|
| CA-3 | `https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml` | `https://laws-lois.justice.gc.ca/eng/XML/SOR-87-402.xml` | 2026-07-31T14:35:22.379578Z | text/xml | 49977 | `6e89ad25847944ca2bd72bcbf02ec3d2942a234d373b6c10db44307e0fbdf2c3` | CLEAR_REPOSITORY_FREEZE | REPOSITORY_FROZEN | `OIC-CA-FREEZE-CA-3-v0.1` |

## Blocked source units

These were never requested. Their bytes do not exist anywhere in this repository or in any local evidence area.

- CA-1
- CA-2
- CA-4
- CA-5-APPROVALS
- CA-5-DELEGATION
- CA-5-LIMITS
- CA-5-SIGNING
- CA-6-ARCHIVE
- CA-6-CH6
- CA-6-GLOSSARY

## Offline verification

```bash
python scripts/verify_canada_freeze.py
```

The verifier performs no network I/O. It recomputes SHA-256 and SHA-512 over every committed artifact and requires agreement with the receipt, `INDEX.json`, `SHA256SUMS`, and `SHA512SUMS`.

