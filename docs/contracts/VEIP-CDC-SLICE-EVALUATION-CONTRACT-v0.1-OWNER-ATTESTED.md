# VEIP-CDC-SLICE-EVALUATION-CONTRACT-v0.1

Status: OWNER_ATTESTED_FOR_CDC_EXEC_VERTICAL_SLICE_001_ONLY
Date: 2026-08-10

This is not:
- a new VEIP production specification;
- VEIP 1.0;
- production VEIP conformance;
- certification;
- real-world institutional authorization;
- CDC authority;
- production reliance semantics;
- runtime currentness;
- a replacement for the incomplete VEIP dependency dossier.

It is a bounded evaluation-profile contract connecting already-approved OIC/OAM semantics to the VEIP 0.1.0 Evidence Pack boundary for this synthetic/public execution slice.

## 4. Controlled object

The consequential VEIP-controlled action in this slice is not the underlying procurement-control evaluation.

It is the proposed institutional-state transition:

```text
APPLY_TEST_DISPOSITION(
    mission_id,
    ebawu_id,
    candidate_digest,
    reviewer_id,
    reviewer_role,
    authority_scope_ref,
    disposition
)
```

This avoids collapsing:

```text
deterministic evaluation
!=
ZTL warrant
!=
human disposition
!=
execution of the institutional-state transition
```

## 5. Required proposal input

A proposed test-disposition transition MUST bind at minimum:

```text
proposal_id
mission_id
ebawu_id
candidate_id
candidate_digest

reviewer_id
reviewer_role_assertion
authority_scope_ref
assurance_mode

requested_disposition

OIC_control_id
OIC_semantic_epoch
OIC_control_digest
source_anchor_refs
admission_record_ref

evidence_bundle_digest
deterministic_execution_result_ref
ZTL_warrant_ref
ZTL_warrant_digest

prior_institutional_state
requested_new_institutional_state

proposal_time
schema_version
```

For this test:

```text
assurance_mode = SYNTHETIC_EVALUATION_ONLY
authority_scope_ref = CDC-TEST-MISSION-001/TEST-REVIEWER
```

This is local test standing only. It does not prove legal competence, delegation or CDC authority.

## 6. Permitted TEST dispositions

Use only the OAM-controlled dispositions:

```text
ACCEPT_CANDIDATE
QUALIFY
DISMISS
REQUEST_EVIDENCE
ESCALATE
DEFER
```

No new disposition may be invented.

Their existing meanings remain controlling.

In particular:

```text
REQUEST_EVIDENCE -> unresolved; no PASS promotion
DISMISS -> cannot enter relied-upon outputs
ESCALATE -> blocks ordinary adoption path
DEFER -> no downstream eligibility until resumed
ACCEPT_CANDIDATE -> candidate use only; not automatically official
```

## 7. Deterministic test-transition gate

The VEIP evaluation-profile decision is:

```text
ALLOW
DENY
ESCALATE
```

`ALLOW` means only:

> the proposed TEST institutional-state transition satisfies the deterministic requirements of this slice contract and may be executed inside `CDC-TEST-MISSION-001`.

It does not mean legally authorized, CDC-approved, officially adopted or institutionally valid outside the synthetic evaluation.

### ALLOW requires all of:

1. mission matches `CDC-TEST-MISSION-001`;
2. candidate digest recomputes exactly;
3. referenced EBAWU exists;
4. OIC admitted-control binding exists;
5. required evidence references exist;
6. deterministic evaluation record exists;
7. ZTL/fallback warrant artifact exists where required;
8. reviewer role assertion exists;
9. authority scope equals the mission-scoped test-reviewer scope;
10. requested disposition is in the permitted set;
11. prior state equals the actual recorded prior state;
12. no conflicting supersession/correction makes the candidate stale;
13. all mandatory artifact hashes verify.

### DENY includes at minimum:

- candidate/evidence digest mismatch;
- wrong mission;
- unauthorized reviewer scope;
- invalid state regression;
- disposition outside permitted set;
- control/version mismatch;
- attempted mutation of predecessor history.

### ESCALATE includes at minimum:

- required authority state unresolved;
- contradictory evidence requiring governed review;
- required semantics or mapping insufficient to determine the transition;
- any `CANNOT` condition not explicitly mapped to DENY.

No implicit ALLOW exists.

## 8. Execution record

If and only if the test transition is ALLOWed, execution produces:

```text
event_id
event_type
schema_version
mission_id
aggregate_id
aggregate_version

occurred_at
recorded_at
producer
producer_version
run_id
trace_id
parent_event_id

input_artifact_digests
output_artifact_digests

prior_state
new_state
reason_code

declared_actor
declared_role
authority_scope_ref
assurance_mode

candidate_digest
evidence_bundle_digest
OIC_control_digest
ZTL_warrant_digest
disposition

correction_ref
downstream_eligibility_refs
handoff_refs
reliance_impact_refs
```

This event is immutable after emission.

## 9. VEIP Evidence Pack mapping

For this slice the existing VEIP 0.1.0 Evidence Pack records:

```text
authority =
    declared TEST reviewer scope + validity/context

policy =
    mission charter +
    admitted OIC control/version/hash +
    applicable disposition contract

action =
    exact proposed APPLY_TEST_DISPOSITION action

decision =
    ALLOW / DENY / ESCALATE +
    reason code +
    evaluation time

execution =
    whether the state transition actually executed +
    executor +
    execution time +
    resulting state/event digest

provenance =
    system +
    build +
    implementation commit +
    environment +
    schema/profile versions
```

A VEIP verifier PASS means only that the pack satisfies implemented structural/integrity checks.

It does not establish institutional legitimacy, evidence sufficiency, legal authority, official status or downstream reliance.

## 10. Correction / supersession contract

Correction MUST NOT mutate the predecessor.

Correction creates:

```text
new_ebawu_or_successor_id
new_candidate_digest
supersedes
superseded_by
correction_reason
changed_fact_or_control_refs
prior_state
new_state
affected_output_refs
reliance_impact_refs
correction_event_id
```

The predecessor remains addressable and byte-preserved.

For the vertical slice, actual production reliance is not required.

Therefore:

```text
RELIED_UPON = NOT_REQUIRED_FOR_SLICE
PRODUCTION_RELIANCE_SEMANTICS = OUT_OF_SCOPE
```

A correction test may operate on an `ACCEPTED_CANDIDATE`, `QUALIFIED`, or other eligible synthetic state before any real reliance occurs.

Affected generated statements MUST become ineligible until regeneration or explicit human resolution.

## 11. Failure behavior

The slice is fail-closed against semantic promotion.

```text
missing evidence
    -> REQUEST_EVIDENCE / unresolved / Z / CANNOT as applicable
    -> no silent PASS

unsupported admission
    -> no truth-valued downstream reasoning

unauthorized reviewer
    -> DENY
    -> no institutional-state transition

candidate/evidence mutation
    -> DENY / integrity failure

unknown required transition condition
    -> ESCALATE or CANNOT
    -> no implicit fallback

execution failure
    -> prior institutional state preserved
    -> failure event preserved
    -> no fabricated completion
```

Candidate invariant under test:

**FAILURE-PRESERVING AVAILABILITY**

A system remains institutionally available only when failure can occur without causing loss of evidentiary state, unauthorized promotion, implicit fallback, or reconstruction of authority by assumption.

This remains a candidate invariant. This slice tests behavior consistent with it; it does not prove the invariant generally.

## 12. Explicit nonclaims

Successful execution of this contract does NOT establish:

```text
CDC deployment
CDC validation
production readiness
production VEIP conformance
legal authority
real-world reviewer identity
evidence sufficiency
official finding status
production reliance
runtime currentness
supplier replacement
CRC-wide scalability
offline/no-egress conformance
full six-state VEIP SDK implementation
```
