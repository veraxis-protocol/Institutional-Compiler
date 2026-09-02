# NVIDIA Provider Path Stop Rule 001

**Status:** `ACTIVE_PROVIDER_PATH_STOP_RULE`

## Decision

Do not create Q011.

Do not rerun Q009 or Q010.

Do not execute Ontology 007R1.

Do not perform another near-identical live provider qualification or
characterization on the unchanged NVIDIA endpoint/model/adapter path for the
purpose of obtaining authorization to run 007R1.

## Evidence

The closed evidence does not isolate one stable request-specific mechanism.

- Q009 closed `NOT_QUALIFIED` after a `JSON_MODE` provider timeout.
- Recovery Stability 002 completed 18 observations with 16 accepted and two
  provider-path failures on `PRODUCTION_TOKEN_RESERVATION`.
- Token-Reservation Localization 001 did not establish an association between
  `max_tokens` and provider failure.
- Q010 closed `NOT_QUALIFIED` after 8/9 accepted marker-valid observations;
  the sole failure occurred on `BASIC_TEXT`.

These frozen experiments are not pooled into a statistical estimate.

Their relevant methodological consequence is narrower: the observed failure
surface has moved across probe types and no causal mechanism has been
established.

Another unchanged qualification attempt would therefore increasingly test
whether we eventually obtain a favorable window rather than test a newly
motivated hypothesis.

That is not an acceptable basis for releasing a consequential semantic
experiment.

## 007R1 status

Ontology 007R1 remains intact.

Its semantic request population is frozen and preserved byte-identically from
Ontology 007.

Its semantic hypothesis has **not** been evaluated.

Provider-path failure is not semantic evidence against the syntactic
predicate-carrier hypothesis.

Therefore 007R1 is:

`BLOCKED_PROVIDER_PREREQUISITE / SEMANTICALLY_UNEVALUATED`

not:

`REFUTED`

## Material reopen requirement

The stop rule may be reconsidered only after a materially new provider-path
condition is established and independently evidenced.

Examples include:

1. a material endpoint/service/routing change;
2. a model identity or version change;
3. a transport-relevant provider-adapter change;
4. independently inspectable provider evidence of a relevant incident
   resolution or service change;
5. a material controlled execution-path/environment change;
6. selection of a materially different provider or endpoint.

None of those conditions automatically authorizes a live run.

A new work order must still be separately preregistered, statically frozen,
executed once, formally closed, and independently verified.

## Explicit non-triggers

The following do **not** reopen qualification:

- elapsed time;
- a desire for a PASS;
- successful ad-hoc calls;
- manual spot checks;
- changing only order or sample count;
- relaxing timeout or headroom;
- adding retries;
- relaxing the decision rule;
- reusing previously successful observations;
- rerunning the unchanged endpoint/model/adapter path.

## Scientific boundary

Provider root cause remains:

`NOT ESTABLISHED`

Ontology 007R1 semantic state remains:

`UNEVALUATED`

No production interpretation rule changes.

No canonicalization is authorized.

No Institutional IR is constructed.

No architecture change is authorized.

## Current operating state

The NVIDIA provider path is closed for further near-identical qualification
work for 007R1.

Unrelated offline OIC work may continue.

The provider gate may be reopened only through the material-change protocol
frozen in `STOP-RULE-v0.1.json`.

## Evidence bindings

- Q009 execution result SHA256: `aec9de532f179b0024eb4a0ea0574deb7a87bf82ea7a54dc45c5dc84b71f74c2`
- Recovery Stability 002 result SHA256: `b997d47e66652a2fc4ff99d7ae9d133cc2c28e2dcd49bc2b9a02bbd25ea22cf4`
- Localization 001 result SHA256: `95787c569b12eac46fef54a918818a4cc74a68bb105970225fa004e010c1589e`
- Q010 execution result SHA256: `81c0e223b0c9f244872ca8c6141f69b7b9d5c846763d7cf9cb476bf24c428051`
- Q010 adjudication SHA256: `161535fd8b9feddb252f7d7d4b9513d8649c45f79f8ec16bcaf9cd68021e8e02`
- 007R1 static freeze SHA256: `8411a24dc31f2975af51def6c2352ec284ec6490acdf3269859230412435050d`
