# OIC-CANDIDATE-LAYER-FREEZE-001

Authorization: **OWNER-AUTHORIZED CANDIDATE-LAYER BOUNDED FREEZE — PRE-ADMISSION**.

Freeze state: **FROZEN FOR SUCCESSOR ARCHITECTURE WORK**.

This package freezes the candidate-discovery boundary at implementation commit
`59c6b34a4972c7758ea1ef4c09fd26be5ddb507e`. It does not claim universal correctness or
permanent immutability. The bounded characterization program through
OIC-CANDIDATE-SEMANTICS-005 currently demonstrates no defect warranting another candidate
architecture or prompt revision before institutional admission design begins.

## Frozen boundary

```text
Source Fragment
  → model-proposed candidate_span + provisional unit_type
  → deterministic fail-closed source grounding
  → Candidate Normative Unit
  → review / admission boundary
```

The model proposes exactly `candidate_span` and `unit_type`. OIC controls exactly
`unit_id`, `interpretation_state`, `epistemic_state`, and `source_anchors`.

Grounding remains:

```text
collapse_whitespace(casefold(candidate_span))
  is a substring of
collapse_whitespace(casefold(source_text))
```

Candidate discovery establishes none of authority, admission, legal validity,
enforceability, institutional meaning, Institutional IR, runtime authorization, `ALLOW`,
or `DENY`.

## Pinned evidence

| Evidence | SHA-256 |
|---|---|
| Candidate Semantics 003 corpus | `8555d59112b07ee6c438136b79602c3b2658e2ff96abfa5deb4563a09883db5a` |
| Candidate Semantics 004 corpus | `594cbee619f467ef949690cd56014eb4f8b3c5ba9527596c6e4bef3f242d5386` |
| Candidate Semantics 005 corpus | `2d8c5f3f4be2028e00179b4b8eee464b325b8d9efbaf19875b8b783a6139dbf0` |
| Live Candidate Semantics 005 receipt | `a44b14b81dbd300d8a6d86e1e882ae0dc7eab152ea4f0823f227c71fce64f8bd` |
| Historical Negative Stability receipt | `3a1dfbb8d43e69800af4f38cf856907fdcdf82108e925723ee745df92ced1408` |

The receipts remain local, gitignored evidence. They are referenced cryptographically and
are not copied into this package. The Negative Stability result remains `INCONCLUSIVE`.

The live 005 characterization used provider `nvidia-nim`, model
`nvidia/nemotron-3.5-lightning-30b-a3b`, and three runs per specimen. It attempted 63
requests: 63 boundary accepted, zero rejected, zero provider errors, zero presence misses,
zero negative-control false positives, zero positive-boundary presence misses, zero spans
outside registered bounds, zero material-loss runs, and zero spans retaining separable
framing. All 45/45 candidate spans passed source grounding; all 36/36 measured
material-completeness runs were complete. The negative controls had 24 accepted runs and
zero false positives; positives had 39 accepted runs and zero presence misses.

Explicit observations:

- CSEM-031, CSEM-046, CSEM-047, and CSEM-048 returned zero candidates in 3/3 runs each.
- CSEM-049, CSEM-050, CSEM-051, and CSEM-052 returned a candidate in 3/3 runs each.
- No framing sentinel retained separable framing.
- CSEM-025 and CSEM-045 returned exactly two candidates in 3/3 runs each.

## Frozen semantic principles

1. Candidate discovery requires apparent normative or constitutive function.
2. Institutional vocabulary alone does not create normativity.
3. Candidate spans remain literal contiguous source text.
4. Material qualifiers remain inside the proposition.
5. Separable source-status framing remains in source context, not `candidate_span`.
6. Source standing does not suppress discovery.
7. Normativity does not require modal keywords.
8. Genuine definitions, delegations, and advisory propositions remain candidate material.
9. No semantic-role decomposition occurs pre-admission.
10. No deterministic semantic filtering, repair, trimming, or secondary classifier occurs after provider output.
11. Fail-closed source grounding remains authoritative.
12. Candidate identity remains source-instance-sensitive.

## Successor rule

A future candidate-layer revision requires a newly demonstrated defect, a new bounded work
order, explicit owner authorization, preservation of this record, and a new successor
version. This freeze does not state that revision is impossible.

The immediate successor seam is review and institutional admission design. Admission may
consume the frozen Candidate Normative Unit, but extraction and grounding confer no source
authority and no admission right.

## Claim ceiling

This bounded freeze records the current pre-admission candidate architecture and identified
characterization evidence. It does not establish universal semantic correctness, zero
defect probability, institutional admission, authority, legal validity, enforceability,
institutional meaning, Institutional IR, runtime authorization, production readiness,
cross-model generalization, or independent validation.

`independent_validation_claim = false`. **NOT SELF-ADJUDICATED.**
