# Admission Boundary 001 Threat Model

## Protected properties

The boundary protects authority conservation, exact source-instance binding,
scope/time fidelity, fail-closed ambiguity, deterministic reconstruction, immutable
receipts, and the prohibition on model self-admission. It does not protect runtime
execution because admission is not an execution boundary.

## Actors and trust boundaries

* **Admission Authority:** trusted only for delegations within its documented
  institutional mandate.
* **Authority Registry/evidence custodian:** trusted to authenticate issuer and
  preserve versioned evidence, but not to extend an issuer's mandate.
* **Future deterministic evaluator:** trusted to execute a frozen ruleset, not to
  create evidence or make discretionary authority judgments.
* **Candidate-discovery model/provider:** untrusted for authority and admission.
* **Source publisher, cache, mirror, and requestor:** untrusted until exact identity,
  bytes, scope, lifecycle, and authority are registry-bound.

The critical trust crossings are model output into Candidate Normative Unit,
external source material into the source registry, institutional governance into an
admission warrant, registry evidence into the evaluator, and a positive receipt into
future IR construction.

## Preregistered adversarial cases

| Threat | Required treatment |
| --- | --- |
| Authoritative-looking fake memo | `SOURCE_NOT_REGISTERED`; visual style and vocabulary have no authority. |
| Perfectly grounded extraction from a draft | `MISSING_AUTHORITY_EVIDENCE` absent an exact draft-purpose warrant. |
| Valid policy with forged source metadata | `SOURCE_DIGEST_MISMATCH` or `SOURCE_VERSION_MISMATCH` before authority evaluation. |
| Valid authority but wrong version | `SOURCE_VERSION_MISMATCH`. |
| Expired source | `EXPIRED`. |
| Superseded source | `SUPERSEDED`. |
| Revoked source or warrant | `REVOKED`; a later receipt does not mutate a prior one. |
| Wrong department or jurisdiction | `OUT_OF_SCOPE`. |
| Policy copied to an unauthoritative website | `SOURCE_NOT_REGISTERED` for the copy; text identity does not transfer standing. |
| Legitimate policy quoted inside commentary | `MISSING_AUTHORITY_EVIDENCE` for the commentary source; quoted provenance cannot borrow the policy warrant. |
| Model labels descriptive text as mandate | Authority outcome is not strengthened by `unit_type`; with sufficient source authority it may be eligible for later interpretation, not declared semantically correct. |
| Model labels a valid mandate as advisory | Authority outcome is not weakened by `unit_type`; admission does not repair or approve semantic classification. |
| Source digest mismatch | `SOURCE_DIGEST_MISMATCH`. |
| Authority registry unavailable | `AUTHORITY_REGISTRY_UNAVAILABLE`; no cached guess. |
| Conflicting warrants | `CONFLICTING_AUTHORITY` unless a versioned institutional precedence rule uniquely resolves them. |
| Stale cached authority evidence | `AUTHORITY_EVIDENCE_STALE`. |

Additional vectors cover provenance without authority, not-yet-effective sources,
publication/effectiveness confusion, missing candidate anchors, warrant scope,
explicit institutional approval, deterministic repetition, and revocation after a
prior positive receipt.

## Attack paths and controls

1. **Prompt/style laundering:** an attacker makes text sound official and induces a
   high-confidence model label. Control: model confidence and `unit_type` are absent
   from the authority-evidence schema and ignored by admission.
2. **Provenance laundering:** an attacker preserves a perfect content trail to an
   unauthoritative copy. Control: exact source-instance registration plus authority
   basis and admission warrant are independently required.
3. **Version/digest substitution:** an attacker presents authorized metadata with
   different bytes. Control: candidate anchor, source registry, authority evidence,
   and warrant must agree on identity, version, and SHA-256 digest.
4. **Scope or time expansion:** an attacker reuses a warrant in another department,
   jurisdiction, or interval. Control: explicit requested scope and evaluation time
   are checked and bound into the receipt.
5. **Conflict hiding:** a requestor supplies only favorable evidence. Control: the
   evaluator resolves the institution-controlled registry as of evaluation time and
   fails closed when relevant overlap is unresolved.
6. **Revocation erasure:** a later state overwrites a prior positive record. Control:
   immutable receipts; new evidence and time produce a new receipt.
7. **Nondeterministic re-evaluation:** hidden clock, retrieval order, or model output
   changes a result. Control: canonical inputs, explicit time, ordered evidence,
   frozen ruleset digest, and content-derived receipt identity.
8. **Self-admission:** model output asserts it is authoritative. Control: only
   institution-issued, registry-authenticated evidence can support `ADMITTED`.

## Residual risks and unresolved institutional inputs

This design does not choose the institution's issuer-authentication mechanism,
evidence freshness duration, global authority hierarchy, conflict precedence rules,
jurisdiction vocabulary, scope taxonomy, governance process, or signature format.
Those must be owner-authorized and versioned before implementation. Until supplied,
the corresponding cases fail closed.

This threat model is preregistration, not proof of security or legal sufficiency.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`
