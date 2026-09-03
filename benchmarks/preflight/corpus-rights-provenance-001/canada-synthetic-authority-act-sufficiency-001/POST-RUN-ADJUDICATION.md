# Canada Synthetic Authority-Act Sufficiency 001 — Post-Run Adjudication

**Final status:** `CLOSED_EXECUTED_SYNTHETIC_STRUCTURAL_SUFFICIENCY_SUPPORTED_CA3`

## Observation

The nine preregistered lowest-gap synthetic authority specimens were executed
against the frozen v0.2 standing discriminator.

Observed disposition:

`SYNTHETIC_AUTHORITY_ACT_STRUCTURAL_SUFFICIENCY_SUPPORTED_CA3`

- frozen specimens evaluated: `9/9`
- target fields covered: `6/6`
- structural-sufficiency passes: `9/9`
- bounded fact-lever minimality passes: `9/9`
- total independently added-lever ablations: `28`
- findings: `0`

## Specimen outcomes

- `SYN-PS-INSTITUTIONAL-PROVENANCE` / `provenance_status`: full completion `PASS`; added-lever ablations `3/3` fail closed; changed levers: `provenance_admission`, `provenance_identity`, `provenance_basis`; preexisting levers: `NONE`
- `SYN-RD-EXTERNAL-RIGHTS-AUTHORITY` / `redistribution_status`: full completion `PASS`; added-lever ablations `4/4` fail closed; changed levers: `counsel_disposition`, `counsel_identity`, `counsel_basis`, `counsel_fields[target_field]`; preexisting levers: `NONE`
- `SYN-RD-INSTITUTIONAL-ADJUDICATION` / `redistribution_status`: full completion `PASS`; added-lever ablations `3/3` fail closed; changed levers: `rights_adjudication`, `rights_identity`, `rights_basis`; preexisting levers: `NONE`
- `SYN-RB-EXTERNAL-RIGHTS-AUTHORITY` / `rights_basis`: full completion `PASS`; added-lever ablations `4/4` fail closed; changed levers: `counsel_disposition`, `counsel_identity`, `counsel_basis`, `counsel_fields[target_field]`; preexisting levers: `NONE`
- `SYN-RB-INSTITUTIONAL-ADJUDICATION` / `rights_basis`: full completion `PASS`; added-lever ablations `3/3` fail closed; changed levers: `rights_adjudication`, `rights_identity`, `rights_basis`; preexisting levers: `NONE`
- `SYN-RS-INSTITUTIONAL-ADJUDICATION` / `rights_status`: full completion `PASS`; added-lever ablations `3/3` fail closed; changed levers: `rights_adjudication`, `rights_identity`, `rights_basis`; preexisting levers: `NONE`
- `SYN-SK-INSTITUTIONAL-ADMISSION` / `source_kind`: full completion `PASS`; added-lever ablations `4/4` fail closed; changed levers: `institutional_admission`, `institutional_identity`, `institutional_basis`, `institutional_fields[target_field]`; preexisting levers: `NONE`
- `SYN-SK-SOURCE-ORIGIN` / `source_kind`: full completion `PASS`; added-lever ablations `3/3` fail closed; changed levers: `source_origin_decl`, `source_origin_identity`, `source_origin_basis`; preexisting levers: `NONE`
- `SYN-SL-PUBLISHER-CANONICAL` / `source_locator`: full completion `PASS`; added-lever ablations `1/1` fail closed; changed levers: `publisher_locator_decl`; preexisting levers: `publisher_identity`

## What was established

For every preregistered lowest-gap specimen:

1. the observed frozen baseline did not establish standing;
2. synthetically completing exactly the frozen discriminator fact levers
   produced standing recognition;
3. restoring any independently added lever to its observed baseline caused the
   channel to fail closed.

This establishes **structural sufficiency and bounded fact-lever minimality
under the frozen discriminator**.

## What was not established

This result does not establish:

- a real authority act;
- real institutional standing;
- lawful authority;
- the correct institutional actor;
- a preferred authority channel;
- any declaration value;
- rights or provenance truth;
- legal clearance;
- SOURCE_MANIFEST admissibility;
- causal root cause;
- cross-source generality.

## Important coupling boundary

The experiment intervened on independent v0.2 `Facts` levers.

It does not claim that every standing dimension is independently necessary.
Where one frozen fact lever satisfies multiple dimensions, those dimensions
remain coupled.

## Preexisting-fact boundary

Facts already true in the observed baseline were not counted as interventions
and were not ablated as though synthetically supplied.

This is material for the publisher-locator path, where publisher identity was
already present in the frozen baseline.

## Replay

The full deterministic execution was repeated once after the first result.

The replay was byte-for-byte identical to the tracked result.

No new observational evidence was consumed by either execution.

## Evidence bindings

- static implementation commit: `ab45a654954062529bb144e176aeee51d1e83347`
- execution result SHA256: `0335208b2fae5d4ad7be72d258ff31132f8debf6d8806f343c0042d212546721`

## State preserved

- real authority established: `FALSE`
- real authority act created: `FALSE`
- declaration values created: `FALSE`
- authority channel selected: `FALSE`
- new real derivation rule created: `FALSE`
- Candidate 002 adopted: `FALSE`
- SOURCE_MANIFEST.csv created: `FALSE`
- SOURCE_MANIFEST population authorized: `FALSE`
- rights established: `FALSE`
- provenance established: `FALSE`
- legal clearance established: `FALSE`
- causal root cause: `NOT_ESTABLISHED`

## Scientific meaning

The previous study established what was missing.

This study establishes that the frozen standing discriminator is not merely
rejecting everything: for every lowest-gap channel, there exists a bounded
synthetic construction that crosses the standing boundary, and every
independently added fact lever in that construction is load-bearing.

That closes the **structural recognizability** question for the lowest-gap CA-3
authority paths.

## Next scientific seam

The next question is no longer whether the standing boundary can recognize a
complete authority construction.

It is:

**Which of these structurally sufficient channel classes can be instantiated by
a real, externally established institutional authority act without OIC issuing
or inventing that authority?**

That is an external-authority acquisition/design problem, not another synthetic
discriminator problem.

It must be separately preregistered before any real authority engagement,
declaration materialization, or SOURCE_MANIFEST population.
